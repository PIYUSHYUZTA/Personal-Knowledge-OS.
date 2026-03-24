"""
Advanced RAG (Retrieval-Augmented Generation) Ingestion Service.

Handles:
- PDF extraction with PyMuPDF (fitz)
- Recursive character splitting with overlap
- Metadata extraction and enrichment
- Vector embedding generation
- pgvector indexing
- Semantic chunking strategies
"""

import logging
import fitz  # PyMuPDF
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.orm import Session
import numpy as np

from app.config import settings
from app.models import KnowledgeSource, KnowledgeChunk, KnowledgeEmbedding, SourceType
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


# ============================================================================
# CHUNKING STRATEGIES
# ============================================================================


class ChunkingConfig(BaseModel):
    """Configuration for chunking behavior."""

    chunk_size: int = 512
    chunk_overlap: int = 50
    strategy: str = "recursive"  # "fixed", "recursive", "semantic", "page"


class RecursiveCharacterSplitter:
    """
    Splits text recursively by a list of separators.
    Tries to keep semantically meaningful chunks together.
    """

    SEPARATORS = [
        "\n\n",  # Paragraph breaks
        "\n",  # Line breaks
        ". ",  # Sentence breaks
        " ",  # Word breaks
        "",  # Character breaks (fallback)
    ]

    @staticmethod
    def split_text(
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Split text recursively while preserving semantic boundaries.

        Args:
            text: Input text
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            separators: Custom separators (defaults to SEPARATORS)

        Returns:
            List of text chunks
        """
        if separators is None:
            separators = RecursiveCharacterSplitter.SEPARATORS

        final_chunks = []
        separator = separators[-1]

        # Find the right separator to split on
        for _s in separators:
            if _s == "":
                separator = _s
                break
            if _s in text:
                separator = _s
                break

        # Split on the separator
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        # Filter out empty splits
        good_splits = [s for s in splits if s.strip()]

        # Merge small splits
        merged_text = ""
        for split in good_splits:
            if len(merged_text) + len(split) < chunk_size:
                merged_text += split + separator
            else:
                if merged_text:
                    final_chunks.append(merged_text.strip())
                merged_text = split + separator

        if merged_text:
            final_chunks.append(merged_text.strip())

        # Add overlaps
        output = []
        for i, chunk in enumerate(final_chunks):
            if i > 0 and chunk_overlap > 0:
                # Add context from previous chunk
                prev_chunk = final_chunks[i - 1]
                overlap_text = prev_chunk[-chunk_overlap:] if len(prev_chunk) > chunk_overlap else prev_chunk
                output.append(overlap_text + " " + chunk)
            else:
                output.append(chunk)

        return output


class SemanticSplitter:
    """
    Splits text based on semantic meaning using sentence boundaries
    and paragraph structure.
    """

    @staticmethod
    def split_text(
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ) -> List[str]:
        """
        Split text by paragraphs and sentences.

        Args:
            text: Input text
            chunk_size: Target chunk size
            chunk_overlap: Overlap size

        Returns:
            List of semantically meaningful chunks
        """
        # Split by paragraphs
        paragraphs = text.split("\n\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # If adding this paragraph would exceed chunk_size, save current chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Add overlap from previous chunk
                if chunk_overlap > 0:
                    overlap = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                    current_chunk = overlap + " " + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


# ============================================================================
# PDF EXTRACTION
# ============================================================================


class PDFExtractor:
    """Extract text and metadata from PDF files using PyMuPDF."""

    @staticmethod
    def extract_text_with_metadata(pdf_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text and metadata from PDF.

        Returns:
            (full_text, metadata_dict)
        """
        try:
            doc = fitz.open(pdf_path)

            # Extract metadata
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "pages": doc.page_count,
                "file_size": Path(pdf_path).stat().st_size,
            }

            # Extract text with page information
            full_text = ""
            page_breaks = {}

            for page_idx in range(doc.page_count):
                page = doc[page_idx]
                text = page.get_text()

                # Mark page boundaries
                full_text += f"\n[PAGE {page_idx + 1}]\n"
                full_text += text

                page_breaks[page_idx] = len(full_text)

            doc.close()

            metadata["page_breaks"] = page_breaks
            return full_text, metadata

        except Exception as e:
            logger.error(f"PDF extraction failed for {pdf_path}: {e}")
            raise


class PDFParser:
    """
    Parse PDF files and extract structured information.
    Handles text, images, tables (basic support).
    """

    @staticmethod
    def parse_pdf(pdf_path: str, include_images: bool = False) -> Dict[str, Any]:
        """
        Comprehensive PDF parsing.

        Returns:
            {
                "text": str,
                "metadata": dict,
                "images": list (optional),
                "tables": list (optional),
                "toc": list,
            }
        """
        doc = fitz.open(pdf_path)

        result = {
            "text": "",
            "metadata": {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "pages": doc.page_count,
            },
            "pages": [],
            "toc": doc.get_toc(),
        }

        for page_idx, page in enumerate(doc):
            page_data = {
                "page_num": page_idx + 1,
                "text": page.get_text(),
                "height": page.rect.height,
                "width": page.rect.width,
            }

            result["text"] += page_data["text"] + "\n"
            result["pages"].append(page_data)

        doc.close()

        return result


# ============================================================================
# RAG INGESTION SERVICE
# ============================================================================


class RAGIngestionService:
    """
    Production-grade RAG ingestion pipeline.
    Handles PDF → Chunks → Embeddings → pgvector in one unified flow.
    """

    @staticmethod
    def ingest_pdf(
        db: Session,
        user_id: UUID,
        file_path: str,
        file_name: str,
        chunk_config: Optional[ChunkingConfig] = None,
    ) -> Tuple[KnowledgeSource, List[KnowledgeChunk], List[KnowledgeEmbedding]]:
        """
        Full ingestion pipeline: PDF → Parse → Chunk → Embed → Index.

        Args:
            db: Database session
            user_id: User ID
            file_path: Path to PDF file
            file_name: Original file name
            chunk_config: Chunking configuration

        Returns:
            (source, chunks, embeddings)
        """

        if chunk_config is None:
            chunk_config = ChunkingConfig()

        logger.info(f"Starting RAG ingestion for {file_name}")

        try:
            # === STEP 1: PDF Extraction ===
            logger.info(f"Extracting PDF text from {file_path}")
            text, pdf_metadata = PDFExtractor.extract_text_with_metadata(file_path)

            if not text.strip():
                raise ValueError("PDF extraction resulted in empty text")

            logger.info(f"Extracted {len(text)} characters from {pdf_metadata['pages']} pages")

            # === STEP 2: Create Knowledge Source ===
            source = KnowledgeSource(
                user_id=user_id,
                file_name=file_name,
                source_type=SourceType.PDF,
                file_size=pdf_metadata.get("file_size", 0),
                metadata_={
                    "extraction_method": "PyMuPDF",
                    "pages": pdf_metadata.get("pages", 0),
                    "author": pdf_metadata.get("author", ""),
                    "title": pdf_metadata.get("title", ""),
                    "text_length": len(text),
                },
            )

            db.add(source)
            db.flush()  # Get source.id
            logger.info(f"Created knowledge source: {source.id}")

            # === STEP 3: Semantic Chunking ===
            logger.info(f"Chunking text with strategy: {chunk_config.strategy}")

            if chunk_config.strategy == "semantic":
                chunks_text = SemanticSplitter.split_text(
                    text,
                    chunk_size=chunk_config.chunk_size,
                    chunk_overlap=chunk_config.chunk_overlap,
                )
            elif chunk_config.strategy == "recursive":
                chunks_text = RecursiveCharacterSplitter.split_text(
                    text,
                    chunk_size=chunk_config.chunk_size,
                    chunk_overlap=chunk_config.chunk_overlap,
                )
            else:
                # Fallback to recursive
                chunks_text = RecursiveCharacterSplitter.split_text(
                    text,
                    chunk_size=chunk_config.chunk_size,
                    chunk_overlap=chunk_config.chunk_overlap,
                )

            logger.info(f"Created {len(chunks_text)} chunks")

            # === STEP 4: Create Chunk Objects ===
            chunks = []
            for idx, chunk_text in enumerate(chunks_text):
                if not chunk_text.strip():
                    continue

                chunk = KnowledgeChunk(
                    source_id=source.id,
                    user_id=user_id,
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    metadata_={
                        "chunk_size": len(chunk_text),
                        "chunk_position": idx,
                        "word_count": len(chunk_text.split()),
                    },
                )
                db.add(chunk)
                chunks.append(chunk)

            db.flush()  # Get chunk.ids
            logger.info(f"Created {len(chunks)} chunk records")

            # === STEP 5: Generate Embeddings ===
            logger.info(f"Generating embeddings for {len(chunks)} chunks")

            chunk_texts = [c.chunk_text for c in chunks]
            embedding_vectors = EmbeddingService.encode(chunk_texts)

            embeddings = []
            for chunk, embedding_vector in zip(chunks, embedding_vectors):
                # Ensure embedding is float32 for pgvector
                embedding_bytes = embedding_vector.astype("float32").tobytes()

                embedding = KnowledgeEmbedding(
                    chunk_id=chunk.id,
                    user_id=user_id,
                    embedding_vector=embedding_bytes,
                    model_version=settings.EMBEDDING_MODEL,
                )
                db.add(embedding)
                embeddings.append(embedding)

            logger.info(f"Generated {len(embeddings)} embeddings")

            # === STEP 6: Update Source and Commit ===
            source.chunks_count = len(chunks)

            db.commit()
            logger.info(f"Successfully ingested {file_name}: {len(chunks)} chunks, {len(embeddings)} embeddings")

            return source, chunks, embeddings

        except Exception as e:
            logger.error(f"RAG ingestion failed: {e}")
            db.rollback()
            raise

    @staticmethod
    def ingest_text_content(
        db: Session,
        user_id: UUID,
        text: str,
        file_name: str,
        source_type: str = "text",
        chunk_config: Optional[ChunkingConfig] = None,
    ) -> Tuple[KnowledgeSource, List[KnowledgeChunk], List[KnowledgeEmbedding]]:
        """
        Ingest raw text content (non-PDF).

        Args:
            db: Database session
            user_id: User ID
            text: Text content
            file_name: Source name
            source_type: "text", "markdown", "code", etc.
            chunk_config: Chunking configuration

        Returns:
            (source, chunks, embeddings)
        """

        if chunk_config is None:
            chunk_config = ChunkingConfig()

        logger.info(f"Starting text ingestion for {file_name}")

        try:
            # Create knowledge source
            source = KnowledgeSource(
                user_id=user_id,
                file_name=file_name,
                source_type=SourceType[source_type.upper()],
                metadata_={
                    "text_length": len(text),
                    "word_count": len(text.split()),
                },
            )

            db.add(source)
            db.flush()

            # Chunk text
            chunks_text = RecursiveCharacterSplitter.split_text(
                text,
                chunk_size=chunk_config.chunk_size,
                chunk_overlap=chunk_config.chunk_overlap,
            )

            # Create chunk objects
            chunks = []
            for idx, chunk_text in enumerate(chunks_text):
                if not chunk_text.strip():
                    continue

                chunk = KnowledgeChunk(
                    source_id=source.id,
                    user_id=user_id,
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    metadata_={
                        "chunk_size": len(chunk_text),
                        "chunk_position": idx,
                        "word_count": len(chunk_text.split()),
                    },
                )
                db.add(chunk)
                chunks.append(chunk)

            db.flush()

            # Generate embeddings
            chunk_texts = [c.chunk_text for c in chunks]
            embedding_vectors = EmbeddingService.encode(chunk_texts)

            embeddings = []
            for chunk, embedding_vector in zip(chunks, embedding_vectors):
                embedding_bytes = embedding_vector.astype("float32").tobytes()

                embedding = KnowledgeEmbedding(
                    chunk_id=chunk.id,
                    user_id=user_id,
                    embedding_vector=embedding_bytes,
                    model_version=settings.EMBEDDING_MODEL,
                )
                db.add(embedding)
                embeddings.append(embedding)

            source.chunks_count = len(chunks)

            db.commit()
            logger.info(f"Successfully ingested {file_name}")

            return source, chunks, embeddings

        except Exception as e:
            logger.error(f"Text ingestion failed: {e}")
            db.rollback()
            raise

    @staticmethod
    def batch_ingest(
        db: Session,
        user_id: UUID,
        file_paths: List[str],
        chunk_config: Optional[ChunkingConfig] = None,
    ) -> List[Tuple[KnowledgeSource, List[KnowledgeChunk], List[KnowledgeEmbedding]]]:
        """
        Ingest multiple files in batch.

        Args:
            db: Database session
            user_id: User ID
            file_paths: List of file paths
            chunk_config: Chunking configuration

        Returns:
            List of (source, chunks, embeddings) tuples
        """

        results = []

        for file_path in file_paths:
            try:
                file_path_obj = Path(file_path)

                if file_path_obj.suffix.lower() == ".pdf":
                    result = RAGIngestionService.ingest_pdf(
                        db,
                        user_id,
                        file_path,
                        file_path_obj.name,
                        chunk_config,
                    )
                else:
                    # Read as text
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()

                    result = RAGIngestionService.ingest_text_content(
                        db,
                        user_id,
                        text,
                        file_path_obj.name,
                        source_type=file_path_obj.suffix.strip(".").lower(),
                        chunk_config=chunk_config,
                    )

                results.append(result)
                logger.info(f"Successfully processed {file_path_obj.name}")

            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue

        return results

    @staticmethod
    def get_ingestion_stats(db: Session, user_id: UUID) -> Dict[str, Any]:
        """Get statistics about user's ingested knowledge."""
        sources = db.query(KnowledgeSource).filter(KnowledgeSource.user_id == user_id).all()

        total_chunks = sum(s.chunks_count for s in sources)
        total_files = len(sources)

        # Group by source type
        by_type = {}
        for source in sources:
            stype = source.source_type.value
            if stype not in by_type:
                by_type[stype] = 0
            by_type[stype] += 1

        return {
            "total_files": total_files,
            "total_chunks": total_chunks,
            "by_type": by_type,
            "sources": [
                {
                    "id": str(s.id),
                    "file_name": s.file_name,
                    "chunks_count": s.chunks_count,
                    "created_at": s.created_at.isoformat(),
                }
                for s in sources
            ],
        }
