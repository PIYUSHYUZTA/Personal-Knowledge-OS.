"""
Web Content Ingestion Bridge (Phase 7a).

Connects web research results to the knowledge base:
- Takes WebContent records
- Chunks content with attribution metadata
- Creates KnowledgeSource and KnowledgeChunk records
- Generates embeddings for semantic search
- Handles code block ingestion separately
- Integrates with entity extraction for graph updates
"""

import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any
from uuid import UUID
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    WebContent, KnowledgeSource, KnowledgeChunk,
    KnowledgeEmbedding, SourceType, VerificationStatus
)
from app.services.rag_ingestion import RecursiveCharacterSplitter, ChunkingConfig
from app.services.embedding_service import EmbeddingService
from app.services.entity_extraction import EntityExtractor, RelationshipExtractor, ChunkEntityProcessor

logger = logging.getLogger(__name__)


class AttributionBuilder:
    """Builds attribution metadata for chunks from web content."""

    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None

    @staticmethod
    def build_chunk_attribution(
        web_content: WebContent,
    ) -> Dict[str, Any]:
        """
        Build attribution metadata for a chunk from WebContent.

        Adds to chunk.metadata_:
        - source_url: Origin URL
        - retrieval_date: When fetched
        - domain: Extracted from URL
        - http_status: HTTP response code
        - parser: Extraction parser used
        - source_type: "WEB"
        """
        metadata_dict = {
            "source_url": web_content.source_url,
            "retrieval_date": web_content.metadata_.get("fetch_timestamp"),
            "domain": web_content.domain or AttributionBuilder.extract_domain(web_content.source_url),
            "http_status": web_content.metadata_.get("status_code"),
            "parser": web_content.metadata_.get("parser", "BeautifulSoup4"),
            "source_type": "WEB",
            # Standard chunk metadata
            "chunk_size": 0,  # Will be set per chunk
            "chunk_position": 0,  # Will be set per chunk
            "word_count": 0,  # Will be set per chunk
        }
        return metadata_dict


class WebIngestionBridge:
    """
    Bridges web research results to knowledge base.
    Orchestrates the ingestion pipeline for WebContent records.
    """

    @staticmethod
    async def ingest_web_content(
        db: Session,
        web_content: WebContent,
        chunk_config: Optional[ChunkingConfig] = None,
        extract_entities: bool = True,
    ) -> Tuple[KnowledgeSource, List[KnowledgeChunk], List[KnowledgeEmbedding]]:
        """
        Ingest WebContent record into knowledge base.

        Args:
            db: Database session
            web_content: WebContent record to ingest
            chunk_config: Chunking configuration
            extract_entities: Whether to extract entities for graph

        Returns:
            (source, chunks, embeddings)

        Raises:
            ValueError: If content is empty or verification fails
        """
        if chunk_config is None:
            chunk_config = ChunkingConfig()

        logger.info(f"Starting web ingestion for {web_content.source_url}")

        try:
            # === STEP 1: Validate content ===
            if not web_content.content_text or not web_content.content_text.strip():
                raise ValueError("WebContent has no content to ingest")

            # === STEP 2: Create Knowledge Source ===
            source = KnowledgeSource(
                user_id=web_content.user_id,
                file_name=web_content.title or web_content.source_url,
                source_type=SourceType.WEB,
                file_size=len(web_content.content_text),
                metadata_={
                    "source_url": web_content.source_url,
                    "domain": web_content.domain,
                    "parser": web_content.metadata_.get("parser", "BeautifulSoup4"),
                    "extraction_method": web_content.metadata_.get("extraction_method"),
                    "fetch_timestamp": web_content.metadata_.get("fetch_timestamp"),
                    "http_status": web_content.metadata_.get("status_code"),
                    "content_type": web_content.metadata_.get("content_type"),
                    "text_length": len(web_content.content_text),
                    "word_count": len(web_content.content_text.split()),
                },
            )

            db.add(source)
            db.flush()  # Get source.id
            logger.info(f"Created knowledge source: {source.id}")

            # === STEP 3: Link WebContent to KnowledgeSource ===
            web_content.source_id = source.id
            db.add(web_content)

            # === STEP 4: Chunk web content ===
            logger.info(f"Chunking web content with strategy: {chunk_config.strategy}")

            chunks_text = RecursiveCharacterSplitter.split_text(
                web_content.content_text,
                chunk_size=chunk_config.chunk_size,
                chunk_overlap=chunk_config.chunk_overlap,
            )

            logger.info(f"Created {len(chunks_text)} chunks from web content")

            # === STEP 5: Create Chunk Objects with Attribution ===
            chunks = []
            attribution = AttributionBuilder.build_chunk_attribution(web_content)

            for idx, chunk_text in enumerate(chunks_text):
                if not chunk_text.strip():
                    continue

                # Build metadata with attribution
                chunk_metadata = attribution.copy()
                chunk_metadata["chunk_size"] = len(chunk_text)
                chunk_metadata["chunk_position"] = idx
                chunk_metadata["word_count"] = len(chunk_text.split())

                chunk = KnowledgeChunk(
                    source_id=source.id,
                    user_id=web_content.user_id,
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    metadata_=chunk_metadata,
                )
                db.add(chunk)
                chunks.append(chunk)

            db.flush()  # Get chunk.ids
            logger.info(f"Created {len(chunks)} chunk records with attribution")

            # === STEP 6: Ingest Code Blocks (if verified) ===
            if web_content.code_blocks_json:
                logger.info(f"Ingesting {len(web_content.code_blocks_json)} verified code blocks")
                code_chunks = await WebIngestionBridge._ingest_code_blocks(
                    db=db,
                    web_content=web_content,
                    source=source,
                    chunk_config=chunk_config,
                )
                chunks.extend(code_chunks)

            # === STEP 7: Generate Embeddings ===
            logger.info(f"Generating embeddings for {len(chunks)} chunks")

            chunk_texts = [c.chunk_text for c in chunks]
            embedding_vectors = EmbeddingService.encode(chunk_texts)

            embeddings = []
            for chunk, embedding_vector in zip(chunks, embedding_vectors):
                # Ensure embedding is float32 for pgvector
                embedding_bytes = embedding_vector.astype("float32").tobytes()

                embedding = KnowledgeEmbedding(
                    chunk_id=chunk.id,
                    user_id=web_content.user_id,
                    embedding_vector=embedding_bytes,
                    model_version=settings.EMBEDDING_MODEL,
                )
                db.add(embedding)
                embeddings.append(embedding)

            logger.info(f"Generated {len(embeddings)} embeddings")

            # === STEP 8: Update Source and Commit ===
            source.chunks_count = len(chunks)

            db.commit()
            logger.info(
                f"Successfully ingested web content from {web_content.source_url}: "
                f"{len(chunks)} chunks, {len(embeddings)} embeddings"
            )

            # === STEP 9: Extract Entities for Graph (Async) ===
            if extract_entities and settings.NEO4J_ENABLED:
                logger.info("Triggering entity extraction for graph integration")
                try:
                    await WebIngestionBridge._extract_and_store_entities(
                        chunks=chunks,
                        user_id=web_content.user_id,
                    )
                except Exception as e:
                    logger.error(f"Entity extraction failed (non-fatal): {e}")

            return source, chunks, embeddings

        except Exception as e:
            logger.error(f"Web ingestion failed: {e}")
            db.rollback()
            raise

    @staticmethod
    async def _ingest_code_blocks(
        db: Session,
        web_content: WebContent,
        source: KnowledgeSource,
        chunk_config: ChunkingConfig,
    ) -> List[KnowledgeChunk]:
        """
        Ingest verified code blocks as separate chunks.

        Creates chunks marked with "is_code_block" in metadata.
        """
        code_chunks = []

        try:
            for idx, code_block in enumerate(web_content.code_blocks_json):
                if not code_block.get("valid", False):
                    continue  # Skip unverified

                code_text = code_block.get("code", "")
                language = code_block.get("language", "plaintext")

                if not code_text.strip():
                    continue

                # Build metadata with attribution
                attribution = AttributionBuilder.build_chunk_attribution(web_content)
                chunk_metadata = attribution.copy()
                chunk_metadata.update({
                    "chunk_size": len(code_text),
                    "chunk_position": idx,
                    "word_count": len(code_text.split()),
                    "is_code_block": True,
                    "code_language": language,
                    "code_index": code_block.get("index", idx),
                })

                chunk = KnowledgeChunk(
                    source_id=source.id,
                    user_id=web_content.user_id,
                    chunk_text=code_text,
                    chunk_index=idx,
                    metadata_=chunk_metadata,
                )
                db.add(chunk)
                code_chunks.append(chunk)

            db.flush()
            logger.info(f"Created {len(code_chunks)} code block chunks")

        except Exception as e:
            logger.error(f"Code block ingestion failed: {e}")

        return code_chunks

    @staticmethod
    async def _extract_and_store_entities(
        chunks: List[KnowledgeChunk],
        user_id: UUID,
    ) -> None:
        """
        Extract entities and relationships from chunks and store in Neo4j graph.

        Emits GraphEventBroker events for each entity/relationship created,
        enabling real-time WebSocket updates to the 3D knowledge map.
        """
        from app.services.graph_service import Neo4jGraphService

        graph_service = Neo4jGraphService(user_id=user_id)

        if not graph_service.driver:
            logger.warning("Neo4j not available, skipping entity extraction")
            return

        total_entities = 0
        total_relationships = 0

        for chunk in chunks:
            result = ChunkEntityProcessor.process_chunk(
                text=chunk.chunk_text,
                chunk_id=str(chunk.id),
            )

            # Create entity nodes in Neo4j
            for entity_name, entity_type in result.get("entities", []):
                success = graph_service.create_entity(
                    name=entity_name,
                    entity_type=entity_type,
                    description=None,
                    metadata_={
                        "source_chunk_id": str(chunk.id),
                        "source_type": "WEB",
                    },
                )
                if success:
                    total_entities += 1

            # Create relationships
            for source_name, target_name, rel_type, confidence in result.get("relationships", []):
                success = graph_service.create_relationship(
                    source_name=source_name,
                    target_name=target_name,
                    relationship_type=rel_type,
                    weight=confidence,
                    metadata_={
                        "source_chunk_id": str(chunk.id),
                        "extraction_confidence": confidence,
                    },
                )
                if success:
                    total_relationships += 1

        logger.info(
            f"Entity extraction complete: {total_entities} entities, "
            f"{total_relationships} relationships from {len(chunks)} chunks"
        )

    @staticmethod
    async def ingest_web_content_by_id(
        db: Session,
        web_content_id: UUID,
        chunk_config: Optional[ChunkingConfig] = None,
        extract_entities: bool = True,
    ) -> Tuple[Optional[KnowledgeSource], List[KnowledgeChunk], List[KnowledgeEmbedding]]:
        """
        Ingest WebContent by ID (look up in database first).

        Returns:
            (source, chunks, embeddings) or (None, [], []) if not found
        """
        try:
            web_content = db.query(WebContent).filter(WebContent.id == web_content_id).first()
            if not web_content:
                logger.warning(f"WebContent {web_content_id} not found")
                return None, [], []

            # Check verification status
            if web_content.verification_status == VerificationStatus.FAILED:
                logger.warning(
                    f"WebContent {web_content_id} has FAILED verification, skipping ingestion"
                )
                return None, [], []

            return await WebIngestionBridge.ingest_web_content(
                db=db,
                web_content=web_content,
                chunk_config=chunk_config,
                extract_entities=extract_entities,
            )
        except Exception as e:
            logger.error(f"Failed to ingest web content by ID {web_content_id}: {e}")
            return None, [], []
