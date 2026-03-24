"""
Parent-Document Retrieval Service.
Enhances RAG by retrieving surrounding context chunks.
"""

from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.models import KnowledgeChunk, KnowledgeEmbedding
from app.schemas import SearchResult
from app.services.embedding_service import EmbeddingService
import numpy as np

logger = logging.getLogger(__name__)


class ParentDocumentRetriever:
    """
    Implements parent-document retrieval strategy for RAG.

    When a small chunk is found, retrieve larger surrounding context
    (the "parent" chunk) for more complete information.
    """

    @staticmethod
    def get_parent_chunks(
        db: Session,
        user_id: UUID,
        source_id: UUID,
        target_chunk_index: int,
        context_range: int = 2,  # How many chunks before/after to include
    ) -> List[KnowledgeChunk]:
        """
        Get parent chunks (surrounding context) for a target chunk.

        Args:
            db: Database session
            user_id: User ID
            source_id: Source ID
            target_chunk_index: Index of target chunk
            context_range: Number of chunks before and after to retrieve

        Returns:
            List of chunks including target and surrounding context
        """
        try:
            # Get the chunk range
            min_index = max(0, target_chunk_index - context_range)
            max_index = target_chunk_index + context_range

            chunks = (
                db.query(KnowledgeChunk)
                .filter(
                    KnowledgeChunk.source_id == source_id,
                    KnowledgeChunk.user_id == user_id,
                    KnowledgeChunk.chunk_index >= min_index,
                    KnowledgeChunk.chunk_index <= max_index,
                )
                .order_by(KnowledgeChunk.chunk_index)
                .all()
            )

            logger.info(
                f"Retrieved {len(chunks)} parent chunks (range: {min_index}-{max_index})"
            )
            return chunks

        except Exception as e:
            logger.error(f"Error retrieving parent chunks: {e}")
            return []

    @staticmethod
    def merge_parent_chunks(chunks: List[KnowledgeChunk], separator: str = "\n\n") -> str:
        """
        Merge multiple chunks into a single parent document context.

        Args:
            chunks: List of chunks
            separator: Separator between chunks

        Returns:
            Merged text with page breaks preserved
        """
        merged_text = separator.join([c.chunk_text for c in chunks])
        return merged_text

    @staticmethod
    def semantic_search_with_parent_context(
        db: Session,
        user_id: UUID,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        context_range: int = 2,
    ) -> List[Tuple[SearchResult, str]]:
        """
        Semantic search that returns results with parent document context.

        Returns:
            List of (SearchResult, parent_context) tuples
        """
        from app.services.knowledge_service import KnowledgeService

        try:
            # Step 1: Get initial semantic search results
            initial_results = KnowledgeService.semantic_search(
                db, user_id, query, top_k=top_k, min_similarity=min_similarity
            )

            results_with_context = []

            # Step 2: For each result, retrieve parent context
            for result in initial_results:
                parent_chunks = ParentDocumentRetriever.get_parent_chunks(
                    db,
                    user_id,
                    result.source_id,
                    # Find the chunk index from the result
                    db.query(KnowledgeChunk)
                    .filter(KnowledgeChunk.id == result.chunk_id)
                    .first()
                    .chunk_index,
                    context_range=context_range,
                )

                if parent_chunks:
                    parent_context = ParentDocumentRetriever.merge_parent_chunks(
                        parent_chunks
                    )
                else:
                    parent_context = result.chunk_text

                results_with_context.append((result, parent_context))

            logger.info(f"Enriched {len(results_with_context)} results with parent context")
            return results_with_context

        except Exception as e:
            logger.error(f"Error in semantic search with context: {e}")
            return []

    @staticmethod
    def build_rag_context(
        results_with_context: List[Tuple[SearchResult, str]], max_tokens: int = 4000
    ) -> str:
        """
        Build complete RAG context from search results.

        Constructs a passage that can be passed to an LLM while
        respecting token limits.

        Args:
            results_with_context: Results with parent context
            max_tokens: Maximum tokens for context (rough estimate, ~4 chars/token)

        Returns:
            Formatted RAG context string
        """
        context_parts = []
        total_chars = 0
        char_limit = max_tokens * 4

        for result, parent_context in results_with_context:
            # Add source header
            source_header = f"[From: {result.file_name} (Similarity: {result.similarity_score:.2%})]"

            context_entry = f"{source_header}\n{parent_context}\n"

            if total_chars + len(context_entry) < char_limit:
                context_parts.append(context_entry)
                total_chars += len(context_entry)
            else:
                break  # Hit token limit

        rag_context = "\n---\n".join(context_parts)

        logger.info(f"Built RAG context: {len(rag_context)} chars ({len(context_parts)} sources)")
        return rag_context

    @staticmethod
    def find_semantic_paragraphs(
        db: Session,
        user_id: UUID,
        source_id: UUID,
        chunk_index: int,
    ) -> List[KnowledgeChunk]:
        """
        Find semantically related chunks (potential paragraph boundaries).

        Uses embedding similarity to identify chunks that form a cohesive unit.

        Returns:
            List of semantically related chunks
        """
        try:
            target_chunk = (
                db.query(KnowledgeChunk)
                .filter(
                    KnowledgeChunk.source_id == source_id,
                    KnowledgeChunk.user_id == user_id,
                    KnowledgeChunk.chunk_index == chunk_index,
                )
                .first()
            )

            if not target_chunk or not target_chunk.embedding:
                return []

            # Get target embedding
            target_embedding = np.frombuffer(
                target_chunk.embedding.embedding_vector, dtype=np.float32
            )

            # Get all chunks from same source
            all_chunks = (
                db.query(KnowledgeChunk)
                .filter(
                    KnowledgeChunk.source_id == source_id,
                    KnowledgeChunk.user_id == user_id,
                )
                .all()
            )

            # Calculate similarities
            semantic_chunks = []
            similarity_threshold = 0.75

            for chunk in all_chunks:
                if chunk.embedding:
                    chunk_embedding = np.frombuffer(
                        chunk.embedding.embedding_vector, dtype=np.float32
                    )

                    similarity = EmbeddingService.cosine_similarity(
                        target_embedding, chunk_embedding
                    )

                    if similarity >= similarity_threshold:
                        semantic_chunks.append(chunk)

            logger.info(f"Found {len(semantic_chunks)} semantically related chunks")
            return semantic_chunks

        except Exception as e:
            logger.error(f"Error finding semantic paragraphs: {e}")
            return []
