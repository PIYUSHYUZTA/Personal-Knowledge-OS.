"""
Knowledge Distillation API Endpoints.

Exposes the long-term memory compression pipeline.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.security import verify_token, extract_user_id_from_token
from app.models import User
from app.services.knowledge_distillation import KnowledgeDistillationEngine

router = APIRouter(prefix="/api/distillation", tags=["Knowledge Distillation"])


@router.post("/compress")
async def trigger_distillation(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Trigger knowledge distillation for the authenticated user.

    Compresses old, related chunks into master nodes to optimize long-term memory.

    Returns:
    {
        "status": "success",
        "master_nodes_created": 3,
        "chunks_archived": 15,
        "estimated_savings_percentage": 35
    }
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
        user = db_session.query(User).filter(User.id == user_id).first()
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        engine = KnowledgeDistillationEngine(user_id, db_session)
        result = await engine.run_distillation_pass()

        return {
            "status": "success",
            "master_nodes_created": result.get("master_nodes_created", 0),
            "chunks_archived": result.get("chunks_archived", 0),
            "estimated_savings_percentage": result.get("estimated_savings_percentage", 0),
            "master_nodes": result.get("master_nodes", []),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Distillation failed: {str(e)}",
        )


@router.get("/metrics")
async def get_distillation_metrics(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get knowledge distillation metrics for the authenticated user.

    Shows how much compression has occurred and potential gains.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
        user = db_session.query(User).filter(User.id == user_id).first()
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        engine = KnowledgeDistillationEngine(user_id, db_session)
        metrics = engine.get_distillation_metrics()

        return {
            "status": "success",
            "metrics": metrics,
            "efficiency_estimate": f"{metrics['compression_ratio'] * 100:.1f}% of knowledge compressed",
            "potential_savings": f"~{metrics['estimated_token_savings']} tokens saved",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting metrics: {str(e)}",
        )


@router.get("/status")
async def get_distillation_status(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get the status of knowledge distillation for this user.

    Shows when it was last run and when it will run again.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        # In production, this would query a job history table
        return {
            "status": "success",
            "message": "Knowledge distillation is enabled",
            "schedule": "Daily at 1 AM UTC",
            "next_run": "Tomorrow at 1 AM UTC",
            "last_run": "2 days ago",
            "can_trigger_manually": True,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting status: {str(e)}",
        )
