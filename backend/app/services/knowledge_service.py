"""
Knowledge service: semantic search, RAG retrieval, knowledge management.
Phase 7a: Attribution display and citation generation.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
import math
import numpy as np
import logging

from app.models import KnowledgeChunk, KnowledgeEmbedding, KnowledgeSource, User, GraphEntity as GraphEntityORM
from app.schemas import SearchResult
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class CitationFormatter:
    """Formats attribution metadata into human-readable citations."""

    @staticmethod
    def format_citation(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Generate a citation string from chunk metadata.

        Returns:
            Citation string like "Source: developer.mozilla.org (Retrieved: 2026-03-11)"
            or None if no attribution data available
        """
        if not metadata:
            return None

        source_url = metadata.get("source_url")
        domain = metadata.get("domain")
        retrieval_date = metadata.get("retrieval_date")
        source_type = metadata.get("source_type", "UNKNOWN")

        if not source_url and not domain:
            return None

        # Build citation parts
        parts = []

        # Source identifier
        if domain:
            parts.append(f"Source: {domain}")
        elif source_url:
            parts.append(f"Source: {source_url[:80]}")

        # Retrieval date
        if retrieval_date:
            # Parse ISO date and format for display
            date_str = retrieval_date
            if "T" in str(date_str):
                date_str = str(date_str).split("T")[0]
            parts.append(f"Retrieved: {date_str}")

        # Source type indicator
        if source_type == "WEB":
            parts.append("[Web]")

        return " | ".join(parts) if parts else None

    @staticmethod
    def build_rag_context_with_citations(
        results: List[SearchResult],
    ) -> str:
        """
        Build RAG context string with inline citations for LLM consumption.

        Returns:
            Formatted context string with numbered citations
        """
        if not results:
            return ""

        context_parts = []
        citations = []

        for idx, result in enumerate(results, 1):
            # Add chunk text with reference number
            context_parts.append(f"[{idx}] {result.chunk_text}")

            # Build citation for this chunk
            citation = CitationFormatter.format_citation(result.metadata)
            if citation:
                citations.append(f"[{idx}] {citation}")

        # Combine context and citations
        context = "\n\n".join(context_parts)

        if citations:
            context += "\n\n--- Sources ---\n"
            context += "\n".join(citations)

        return context

class KnowledgeService:
    """Manages knowledge retrieval and semantic search."""

    @staticmethod
    def semantic_search(
        db: Session,
        user_id: UUID,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[SearchResult]:
        """
        Perform semantic search on user's knowledge base.

        Args:
            db: Database session
            user_id: User to search within
            query: Search query string
            top_k: Number of top results to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of SearchResult objects sorted by relevance
        """
        try:
            # Encode the query into embedding
            query_embedding = EmbeddingService.encode_single(query)

            # Get all embeddings for the user's knowledge
            embeddings_db = db.query(KnowledgeEmbedding).join(
                KnowledgeChunk
            ).filter(
                KnowledgeChunk.user_id == user_id
            ).all()

            if not embeddings_db:
                logger.info(f"No embeddings found for user {user_id}")
                return []

            # Compute similarities
            similarities = []
            for emb in embeddings_db:
                # In production, use actual vector similarity from pgvector
                # For now, use numpy-based similarity
                chunk_embedding = np.frombuffer(emb.embedding_vector, dtype=np.float32)
                similarity = EmbeddingService.cosine_similarity(
                    query_embedding,
                    chunk_embedding
                )

                if similarity >= min_similarity:
                    similarities.append((emb, similarity))

            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Build result objects
            results = []
            for emb, similarity_score in similarities[:top_k]:
                chunk = emb.chunk
                source = chunk.source

                result = SearchResult(
                    chunk_id=chunk.id,
                    source_id=source.id,
                    file_name=source.file_name,
                    chunk_text=chunk.chunk_text[:500],  # Truncate for preview
                    similarity_score=min(1.0, max(0.0, similarity_score)),
                    metadata=chunk.metadata_
                )
                results.append(result)

            logger.info(f"Search query '{query}' returned {len(results)} results")

            # Phase 3.5: Auto-bump entity weights for concepts named in the query
            KnowledgeService._bump_entities_for_query(db, user_id, query)

            return results

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []

    # -------------------------------------------------------------------------
    # Phase 3.5 – Expertise Heatmap Tracking
    # -------------------------------------------------------------------------

    @staticmethod
    def _bump_entities_for_query(db: Session, user_id: UUID, query: str) -> None:
        """Internal: bump weights of entities whose names appear as words in the query."""
        from app.config import settings
        if not settings.GRAPH_HEATMAP_ENABLED:
            return
        try:
            # Tokenise the query into meaningful words (>3 chars)
            query_terms = list({
                t.strip(".,;:!?'\"").lower()
                for t in query.split()
                if len(t.strip(".,;:!?'\"")) > 3
            })
            if not query_terms:
                return
            matching = (
                db.query(GraphEntityORM)
                .filter(
                    GraphEntityORM.user_id == user_id,
                    func.lower(GraphEntityORM.entity_name).in_(query_terms),
                )
                .all()
            )
            now = datetime.now(timezone.utc)
            for entity in matching:
                entity.weight = (entity.weight or 0.0) + 1.0
                entity.last_accessed_at = now
            if matching:
                db.commit()
                logger.debug(
                    f"Auto-bumped {len(matching)} entity weights for query '{query[:40]}'"
                )
        except Exception as bump_err:
            logger.warning(f"Failed to auto-bump entity weights: {bump_err}")
            try:
                db.rollback()
            except Exception:
                pass

    @staticmethod
    def record_interaction_hit(
        db: Session,
        user_id: UUID,
        entity_name: str,
        hit_weight: float = 1.0,
    ) -> None:
        """
        Explicitly record an interaction hit on a named entity node.

        Called when:
        - A node is clicked in the 3D graph UI  (hit_weight=0.5)
        - The heatmap API receives a POST /record-interaction (hit_weight=1.0)

        The weight attribute is the raw cumulative score used by the decay formula.
        """
        from app.config import settings
        if not settings.GRAPH_HEATMAP_ENABLED:
            return
        try:
            entity = (
                db.query(GraphEntityORM)
                .filter(
                    GraphEntityORM.user_id == user_id,
                    func.lower(GraphEntityORM.entity_name) == entity_name.lower(),
                )
                .first()
            )
            if entity:
                entity.weight = (entity.weight or 0.0) + hit_weight
                entity.last_accessed_at = datetime.now(timezone.utc)
                db.commit()
                logger.debug(
                    f"Interaction hit recorded for '{entity_name}': weight={entity.weight:.2f}"
                )
        except Exception as e:
            logger.error(f"record_interaction_hit error for '{entity_name}': {e}")
            db.rollback()

    @staticmethod
    def apply_knowledge_decay(
        db: Session,
        user_id: UUID,
        half_life_days: Optional[float] = None,
    ) -> int:
        """
        Apply exponential time-based decay to every GraphEntity weight for a user.

        Formula: new_weight = weight * 2^(-days_elapsed / half_life)

        Nodes that haven't been accessed in `half_life_days` days lose half their
        intensity.  This keeps the heatmap accurate over time.

        Returns:
            Number of entity rows updated.
        """
        from app.config import settings
        if not settings.GRAPH_HEATMAP_ENABLED:
            return 0
        if half_life_days is None:
            half_life_days = settings.GRAPH_HEATMAP_DECAY_HALF_LIFE_DAYS

        now = datetime.now(timezone.utc)
        try:
            entities = (
                db.query(GraphEntityORM)
                .filter(
                    GraphEntityORM.user_id == user_id,
                    GraphEntityORM.weight > 0.0,
                )
                .all()
            )
            updated = 0
            for entity in entities:
                ref_date = entity.last_accessed_at or entity.created_at
                days_elapsed = (now - ref_date).total_seconds() / 86400.0
                decay_factor = math.pow(2, -days_elapsed / max(half_life_days, 0.01))
                entity.weight = round((entity.weight or 0.0) * decay_factor, 4)
                updated += 1
            db.commit()
            logger.info(
                f"Knowledge decay applied to {updated} entities for user {user_id} "
                f"(half_life={half_life_days}d)"
            )
            return updated
        except Exception as e:
            logger.error(f"apply_knowledge_decay error: {e}")
            db.rollback()
            return 0

    @staticmethod
    def get_knowledge_sources(db: Session, user_id: UUID) -> List[KnowledgeSource]:
        """Get all knowledge sources for a user."""
        return db.query(KnowledgeSource).filter(
            KnowledgeSource.user_id == user_id
        ).all()

    @staticmethod
    def get_source_chunks(
        db: Session,
        source_id: UUID,
        user_id: UUID
    ) -> List[KnowledgeChunk]:
        """Get all chunks for a specific source."""
        return db.query(KnowledgeChunk).filter(
            KnowledgeChunk.source_id == source_id,
            KnowledgeChunk.user_id == user_id
        ).order_by(KnowledgeChunk.chunk_index).all()

    @staticmethod
    def delete_source(db: Session, source_id: UUID, user_id: UUID) -> bool:
        """
        Delete a knowledge source and all associated chunks/embeddings.

        Returns:
            True if successful
        """
        try:
            source = db.query(KnowledgeSource).filter(
                KnowledgeSource.id == source_id,
                KnowledgeSource.user_id == user_id
            ).first()

            if not source:
                return False

            db.delete(source)  # Cascade deletes chunks and embeddings
            db.commit()

            logger.info(f"Deleted source {source_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting source: {e}")
            db.rollback()
            return False

    @staticmethod
    def get_knowledge_stats(db: Session, user_id: UUID) -> dict:
        """Get statistics about user's knowledge base."""
        sources_count = db.query(KnowledgeSource).filter(
            KnowledgeSource.user_id == user_id
        ).count()

        chunks_count = db.query(KnowledgeChunk).filter(
            KnowledgeChunk.user_id == user_id
        ).count()

        embeddings_count = db.query(KnowledgeEmbedding).filter(
            KnowledgeEmbedding.user_id == user_id
        ).count()

        return {
            "sources": sources_count,
            "chunks": chunks_count,
            "embeddings": embeddings_count,
            "last_ingestion": None  # Can be added if needed
        }

    @staticmethod
    def semantic_search_with_citations(
        db: Session,
        user_id: UUID,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Semantic search with formatted citations for LLM context.

        Returns:
            {
                "results": List[SearchResult],
                "rag_context": str,  # Formatted context with inline citations
                "citations": List[str],  # Individual citation strings
                "total_results": int,
            }
        """
        results = KnowledgeService.semantic_search(
            db=db,
            user_id=user_id,
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        # Build RAG context with citations
        rag_context = CitationFormatter.build_rag_context_with_citations(results)

        # Extract individual citations
        citations = []
        for result in results:
            citation = CitationFormatter.format_citation(result.metadata)
            if citation:
                citations.append(citation)

        return {
            "results": results,
            "rag_context": rag_context,
            "citations": citations,
            "total_results": len(results),
        }

    @staticmethod
    def get_unverified_snippets(
        db: Session,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        Get all unverified code snippets awaiting student review.

        Returns list of unverified snippets with source URLs and error reasons.
        """
        from app.models import WebContent, VerificationStatus

        web_contents = db.query(WebContent).filter(
            WebContent.user_id == user_id,
            WebContent.verification_status.in_([
                VerificationStatus.UNVERIFIED,
                VerificationStatus.FAILED,
            ]),
        ).order_by(WebContent.created_at.desc()).all()

        snippets = []
        for wc in web_contents:
            if not wc.unverified_codes:
                continue

            for code_block in wc.unverified_codes:
                snippets.append({
                    "web_content_id": str(wc.id),
                    "source_url": wc.source_url,
                    "domain": wc.domain,
                    "title": wc.title,
                    "code": code_block.get("code", ""),
                    "language": code_block.get("language", "plaintext"),
                    "error": code_block.get("error", "Unknown validation error"),
                    "retrieved_at": wc.metadata_.get("fetch_timestamp"),
                    "tag": "unverified_snippet",
                })

        return snippets
