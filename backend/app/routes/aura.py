"""
AURA Route - Refactored Technical Reasoning Interface.
Replaced dual-persona logic with single technical reasoning engine.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status, WebSocket
from sqlalchemy.orm import Session
import logging

from app.database.connection import get_db
from app.schemas import AuraQuery, AuraMessageResponse
from app.core.security import verify_token
from app.models import User
from app.services.technical_reasoning import TechnicalReasoningEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aura", tags=["Technical Reasoning"])


def get_current_user(token: str = Query(None), db: Session = Depends(get_db)) -> User:
    """Extract user from JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required",
        )

    from app.core.security import verify_token

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

    from uuid import UUID
    user = db.query(User).filter(User.id == UUID(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.post(
    "/query",
    summary="Technical reasoning query",
    description="Submit a technical question for analysis",
)
def technical_query(
    request: AuraQuery,
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Submit a technical query to the reasoning engine.

    **Request Body:**
    - message: Technical question
    - context_window: Number of previous messages for context (optional)
    - include_sources: Whether to include source documents (optional)

    **Returns:**
    - Comprehensive technical response with reasoning
    - Retrieved knowledge sources
    - Confidence score
    """
    try:
        user = get_current_user(token, db)

        logger.info(f"Technical query from user {user.id}: {request.message}")

        # Process query through technical reasoning engine
        response, confidence = TechnicalReasoningEngine.process_technical_query(
            db,
            user.id,
            request.message,
            use_parent_context=request.include_sources,
            context_range=2,
        )

        return {
            "message": response,
            "confidence": confidence,
            "model": "Technical Reasoning Engine",
            "reasoning_type": "Knowledge-Augmented Technical Analysis",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in technical query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing technical query",
        )


@router.get(
    "/history",
    summary="Get conversation history",
    description="Retrieve technical reasoning conversation history",
)
def get_history(
    limit: int = Query(10, ge=1, le=100),
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get technical reasoning conversation history.

    **Query Parameters:**
    - limit: Maximum number of conversations (1-100)
    - token: JWT access token

    **Returns:**
    - List of recent interactions
    """
    try:
        user = get_current_user(token, db)

        from app.models import ConversationHistory

        conversations = (
            db.query(ConversationHistory)
            .filter(ConversationHistory.user_id == user.id)
            .order_by(ConversationHistory.created_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "total": len(conversations),
            "conversations": [
                {
                    "id": str(c.id),
                    "query": c.user_message,
                    "response": c.aura_response,
                    "confidence": c.confidence_score,
                    "created_at": c.created_at.isoformat(),
                    "sources_used": len(c.retrieved_knowledge_ids),
                }
                for c in conversations
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching conversation history",
        )


@router.get(
    "/stats",
    summary="Technical reasoning statistics",
    description="Get reasoning engine performance stats",
)
def get_stats(
    token: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get technical reasoning statistics for current user.

    **Query Parameters:**
    - token: JWT access token

    **Returns:**
    - Query count
    - Average confidence
    - Top domains
    """
    try:
        user = get_current_user(token, db)

        from app.models import ConversationHistory
        import statistics

        conversations = (
            db.query(ConversationHistory)
            .filter(ConversationHistory.user_id == user.id)
            .all()
        )

        if not conversations:
            return {
                "total_queries": 0,
                "average_confidence": 0.0,
                "total_sources_used": 0,
            }

        confidence_scores = [c.confidence_score for c in conversations]
        total_sources = sum(len(c.retrieved_knowledge_ids) for c in conversations)

        return {
            "total_queries": len(conversations),
            "average_confidence": statistics.mean(confidence_scores),
            "median_confidence": statistics.median(confidence_scores),
            "total_sources_used": total_sources,
            "avg_sources_per_query": total_sources / len(conversations),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching statistics",
        )
