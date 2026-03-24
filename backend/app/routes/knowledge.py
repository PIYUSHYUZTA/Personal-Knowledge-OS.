"""
Knowledge management API routes.
Endpoints for file ingestion, search, and knowledge retrieval.
"""

from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import logging
from pathlib import Path

from app.database.connection import get_db
from app.schemas import (
    SearchRequest,
    SearchResponse,
    KnowledgeSourceResponse,
    IngestionRequest,
    IngestionResponse,
    IngestionProgress,
    GraphDataResponse,
    GraphEntityResponse,
    GraphRelationshipResponse,
)
from app.services.knowledge_service import KnowledgeService
from app.services.rag_ingestion import RAGIngestionService, ChunkingConfig
from app.core.security import verify_token
from app.models import User, GraphEntity, GraphRelationship
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Management"])

# ============================================================================
# HELPER - Get current user
# ============================================================================


def get_current_user(token: str = Query(None), db: Session = Depends(get_db)) -> User:
    """Extract user from JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required",
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return db.query(User).filter(User.id == user_id).first()


# ============================================================================
# SEMANTIC SEARCH
# ============================================================================


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search across knowledge base",
    description="Search user's knowledge base using semantic similarity",
)
def semantic_search(
    request: SearchRequest,
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Perform semantic search across all user's knowledge.

    **Request Body:**
    - query: Search query (min 3 chars)
    - top_k: Number of results (1-50)
    - min_similarity: Minimum similarity score (0-1)

    **Returns:**
    - query: Original search query
    - results: List of SearchResult objects
    - total_results: Number of results found
    """
    try:
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        logger.info(f"Semantic search for user {user.id}: {request.query}")

        results = KnowledgeService.semantic_search(
            db,
            user.id,
            request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
        )

        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        )


# ============================================================================
# KNOWLEDGE SOURCES
# ============================================================================


@router.get(
    "/sources",
    response_model=List[KnowledgeSourceResponse],
    summary="List all knowledge sources",
    description="Get all uploaded files and sources",
)
def get_sources(
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get all knowledge sources for current user.

    **Query Parameters:**
    - token: JWT access token

    **Returns:**
    - List of KnowledgeSource objects
    """
    try:
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        sources = KnowledgeService.get_knowledge_sources(db, user.id)

        return [KnowledgeSourceResponse.model_validate(s) for s in sources]

    except Exception as e:
        logger.error(f"Get sources error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch sources",
        )


@router.delete(
    "/sources/{source_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete knowledge source",
    description="Remove a file and all associated chunks",
)
def delete_source(
    source_id: str,
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Delete a knowledge source and all associated data.

    **Path Parameters:**
    - source_id: UUID of source to delete

    **Query Parameters:**
    - token: JWT access token

    **Returns:**
    - Success message
    """
    try:
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        from uuid import UUID

        success = KnowledgeService.delete_source(db, UUID(source_id), user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found",
            )

        return {"message": "Source deleted successfully"}

    except Exception as e:
        logger.error(f"Delete source error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Delete failed",
        )


# ============================================================================
# FILE INGESTION
# ============================================================================


@router.post(
    "/upload",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest file",
    description="Upload PDF, text, or markdown file for ingestion",
)
async def upload_file(
    file: UploadFile,
    chunk_size: int = Query(512),
    chunk_overlap: int = Query(50),
    token: str = Query(None),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Upload a file for ingestion into knowledge base.

    **Form Data:**
    - file: PDF, TXT, or Markdown file

    **Query Parameters:**
    - chunk_size: Size of text chunks (default 512)
    - chunk_overlap: Overlap between chunks (default 50)
    - token: JWT access token

    **Returns:**
    - source_id: UUID of created source
    - file_name: Name of uploaded file
    - chunks_created: Number of chunks created
    - embeddings_created: Number of embeddings generated
    - status: "complete" or "error"
    """

    try:
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided",
            )

        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        allowed_exts = [f".{ext}" for ext in settings.ALLOWED_EXTENSIONS]

        if file_ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_exts)}",
            )

        # Save uploaded file temporarily
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        temp_path = upload_dir / f"{user.id}_{file.filename}"

        try:
            # Write file
            contents = await file.read()
            if len(contents) > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_PAYLOAD_TOO_LARGE,
                    detail=f"File too large (max {settings.MAX_FILE_SIZE} bytes)",
                )

            with open(temp_path, "wb") as f:
                f.write(contents)

            logger.info(f"File uploaded: {temp_path}")

            # Ingest based on file type
            chunk_config = ChunkingConfig(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                strategy="recursive",
            )

            if file_ext == ".pdf":
                source, chunks, embeddings = RAGIngestionService.ingest_pdf(
                    db,
                    user.id,
                    str(temp_path),
                    file.filename,
                    chunk_config,
                )
            else:
                # Read as text
                with open(temp_path, "r", encoding="utf-8") as f:
                    text = f.read()

                source_type = file_ext.strip(".").lower()
                source, chunks, embeddings = RAGIngestionService.ingest_text_content(
                    db,
                    user.id,
                    text,
                    file.filename,
                    source_type=source_type,
                    chunk_config=chunk_config,
                )

            logger.info(f"Ingestion complete: {len(chunks)} chunks, {len(embeddings)} embeddings")

            return IngestionResponse(
                source_id=source.id,
                file_name=file.filename,
                chunks_created=len(chunks),
                embeddings_created=len(embeddings),
                status="complete",
            )

        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload/ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        )


# ============================================================================
# KNOWLEDGE GRAPH
# ============================================================================


@router.get(
    "/graph",
    response_model=GraphDataResponse,
    summary="Get knowledge graph",
    description="Retrieve entities and relationships for visualization",
)
def get_graph(
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get knowledge graph data (entities and relationships).

    For Phase 1: Returns empty graph (Neo4j integration in Phase 2)

    **Query Parameters:**
    - token: JWT access token

    **Returns:**
    - entities: List of graph entities
    - relationships: List of relationships
    """
    try:
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        entities = db.query(GraphEntity).filter(GraphEntity.user_id == user.id).all()
        relationships = db.query(GraphRelationship).filter(
            GraphRelationship.user_id == user.id
        ).all()

        return GraphDataResponse(
            entities=[GraphEntityResponse.model_validate(e) for e in entities],
            relationships=[GraphRelationshipResponse.model_validate(r) for r in relationships],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get graph error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch graph",
        )


# ============================================================================
# KNOWLEDGE STATISTICS
# ============================================================================


@router.get(
    "/stats",
    summary="Knowledge base statistics",
    description="Get overview of ingested knowledge",
)
def get_stats(
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get statistics about user's knowledge base.

    **Query Parameters:**
    - token: JWT access token

    **Returns:**
    - total_files: Number of sources
    - total_chunks: Total chunks
    - by_type: Breakdown by source type
    """
    try:
        user = get_current_user(token, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        from app.services.rag_ingestion import RAGIngestionService

        stats = RAGIngestionService.get_ingestion_stats(db, user.id)
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch stats",
        )
