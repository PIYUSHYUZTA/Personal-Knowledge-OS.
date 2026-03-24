"""
Ingestion service: PDF parsing, semantic chunking, and embedding generation.
Handles the pipeline from raw PDF to vector embeddings.
"""

from typing import List, Tuple, Optional
from uuid import UUID
from sqlalchemy.orm import Session
import logging

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from app.config import settings
from app.models import KnowledgeSource, KnowledgeChunk, KnowledgeEmbedding, SourceType
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class ChunkingStrategy:
    """Semantic chunking strategies."""

    @staticmethod
    def by_size(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        Split text into fixed-size chunks with overlap.

        Preserves word boundaries when possible.
        """
        chunks = []
        position = 0

        while position < len(text):
            # Find end position
            end = position + chunk_size

            # If not at end, try to break at word boundary
            if end < len(text):
                # Look back for last space
                last_space = text.rfind(" ", position, end)
                if last_space > position:
                    end = last_space

            chunk = text[position:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move position with overlap
            position = end - overlap
            if position <= 0:
                position = end

        return chunks

    @staticmethod
    def by_paragraphs(text: str, min_size: int = 100) -> List[str]:
        """
        Split by paragraphs (double newlines).
        Merge small paragraphs with neighbors.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) < min_size and current_chunk:
                current_chunk += "\n\n" + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

class IngestionService:
    """Handles PDF ingestion and knowledge base building."""

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """
        Extract text from PDF file.

        Uses pdfplumber if available (better), falls back to pypdf.
        """
        if settings.PDF_EXTRACTION_METHOD == "pdfplumber" and pdfplumber:
            try:
                with pdfplumber.open(file_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                    return text
            except Exception as e:
                logger.warning(f"pdfplumber extraction failed: {e}")

        if PdfReader:
            try:
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                return text
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                raise

        raise RuntimeError("No PDF extraction library available")

    @staticmethod
    def ingest_pdf(
        db: Session,
        user_id: UUID,
        file_path: str,
        file_name: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> Tuple[KnowledgeSource, List[KnowledgeChunk], List[KnowledgeEmbedding]]:
        """
        Complete ingestion pipeline: extract, chunk, embed, store.

        Returns:
            (source, chunks, embeddings)
        """
        try:
            logger.info(f"Starting ingestion for {file_name}")

            # Extract text from PDF
            text = IngestionService.extract_text_from_pdf(file_path)
            logger.info(f"Extracted {len(text)} characters from PDF")

            # Create knowledge source
            source = KnowledgeSource(
                user_id=user_id,
                file_name=file_name,
                source_type=SourceType.PDF,
                metadata_={
                    "extraction_method": settings.PDF_EXTRACTION_METHOD,
                    "original_path": file_path,
                    "text_length": len(text)
                }
            )
            db.add(source)
            db.flush()  # Get source.id without committing

            # Chunk the text
            chunks_text = ChunkingStrategy.by_size(text, chunk_size, chunk_overlap)
            logger.info(f"Created {len(chunks_text)} chunks")

            # Create chunk objects
            chunks = []
            for idx, chunk_text in enumerate(chunks_text):
                chunk = KnowledgeChunk(
                    source_id=source.id,
                    user_id=user_id,
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    metadata_={
                        "chunk_size": len(chunk_text),
                        "chunk_position": idx
                    }
                )
                db.add(chunk)
                chunks.append(chunk)

            db.flush()  # Get chunk.ids

            # Generate embeddings
            embeddings = []
            embedding_texts = [c.chunk_text for c in chunks]

            try:
                logger.info(f"Generating embeddings for {len(chunks)} chunks...")
                embedding_vectors = EmbeddingService.encode(embedding_texts)

                for chunk, embedding_vector in zip(chunks, embedding_vectors):
                    # Convert numpy array to bytes for storage
                    embedding_bytes = embedding_vector.astype('float32').tobytes()

                    embedding = KnowledgeEmbedding(
                        chunk_id=chunk.id,
                        user_id=user_id,
                        embedding_vector=embedding_bytes,
                        model_version=settings.EMBEDDING_MODEL
                    )
                    db.add(embedding)
                    embeddings.append(embedding)

                logger.info(f"Generated {len(embeddings)} embeddings")

            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                # Continue without embeddings for now
                pass

            # Update source with chunk count
            source.chunks_count = len(chunks)

            # Commit everything
            db.commit()
            logger.info(f"Successfully ingested {file_name}")

            return source, chunks, embeddings

        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            db.rollback()
            raise

    @staticmethod
    def ingest_text(
        db: Session,
        user_id: UUID,
        text: str,
        file_name: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> Tuple[KnowledgeSource, List[KnowledgeChunk], List[KnowledgeEmbedding]]:
        """Ingest plain text content."""
        logger.info(f"Starting text ingestion for {file_name}")

        # Create knowledge source
        source = KnowledgeSource(
            user_id=user_id,
            file_name=file_name,
            source_type=SourceType.TEXT,
            metadata_={"text_length": len(text)}
        )
        db.add(source)
        db.flush()

        # Chunk the text
        chunks_text = ChunkingStrategy.by_size(text, chunk_size, chunk_overlap)

        chunks = []
        for idx, chunk_text in enumerate(chunks_text):
            chunk = KnowledgeChunk(
                source_id=source.id,
                user_id=user_id,
                chunk_text=chunk_text,
                chunk_index=idx
            )
            db.add(chunk)
            chunks.append(chunk)

        db.flush()

        # Generate embeddings
        embeddings = []
        embedding_texts = [c.chunk_text for c in chunks]

        try:
            embedding_vectors = EmbeddingService.encode(embedding_texts)

            for chunk, embedding_vector in zip(chunks, embedding_vectors):
                embedding_bytes = embedding_vector.astype('float32').tobytes()
                embedding = KnowledgeEmbedding(
                    chunk_id=chunk.id,
                    user_id=user_id,
                    embedding_vector=embedding_bytes,
                    model_version=settings.EMBEDDING_MODEL
                )
                db.add(embedding)
                embeddings.append(embedding)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")

        source.chunks_count = len(chunks)
        db.commit()

        logger.info(f"Successfully ingested {file_name} with {len(chunks)} chunks")
        return source, chunks, embeddings
