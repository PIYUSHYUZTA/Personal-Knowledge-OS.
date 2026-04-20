"""
Local Inference Gateway API Endpoints.

Exposes hybrid inference with cost tracking and routing insights.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.security import verify_token, extract_user_id_from_token
from app.models import User
from app.services.local_inference import HybridInferenceGateway, InferenceRoute
from app.services.llm_factory import LLMFactory

router = APIRouter(prefix="/api/inference", tags=["Local Inference"])

# Global gateway instance
_gateway: HybridInferenceGateway = None


def get_gateway() -> HybridInferenceGateway:
    """Get or initialize hybrid inference gateway."""
    global _gateway
    if _gateway is None:
        from app.services.local_inference import LocalInferenceEngine
        local_engine = LocalInferenceEngine()
        cloud_provider = LLMFactory.get_provider()
        _gateway = HybridInferenceGateway(local_engine, cloud_provider)
    return _gateway


@router.post("/query")
async def hybrid_inference(
    token: str,
    query: str,
    system_prompt: str = None,
    force_local: bool = False,
    force_cloud: bool = False,
    db_session: Session = Depends(get_db),
):
    """
    Execute a query using hybrid inference gateway.

    Routes automatically:
    - Simple/moderate queries → Local Mistral (free, fast)
    - Complex queries → Cloud Claude/GPT-4o (better reasoning)
    - Sensitive data → Local only (privacy preserved)

    Returns:
    {
        "content": "response text",
        "route": "local",  # or "cloud"
        "model": "mistral",
        "inference_time_ms": 1250,
        "cost": "$0.00",
        "decision_reasoning": "Simple query, using local inference"
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
        gateway = get_gateway()

        result = await gateway.infer(
            prompt=query,
            system_prompt=system_prompt,
            force_local=force_local,
            force_cloud=force_cloud,
        )

        return {
            "status": "success",
            "result": result,
            "user_id": str(user_id),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failed: {str(e)}",
        )


@router.get("/status")
async def check_local_inference_status():
    """
    Check if local inference (Ollama) is available and running.

    Returns:
    {
        "status": "success",
        "local_available": true,
        "models_available": ["mistral:latest", "llama2:latest"],
        "default_model": "mistral",
        "message": "Ready for local inference"
    }
    """
    try:
        gateway = get_gateway()
        is_available = await gateway.local_engine.check_availability()

        return {
            "status": "success",
            "local_available": is_available,
            "models_available": gateway.local_engine.available_models,
            "default_model": gateway.local_engine.default_model,
            "message": "Local inference ready" if is_available else "Ollama not running",
            "setup_docs": "/docs/LOCAL_INFERENCE.md" if not is_available else None,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking status: {str(e)}",
        )


@router.get("/usage-stats")
async def get_inference_usage_stats(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get inference usage statistics across local and cloud.

    Shows cost savings from using local models.

    Returns:
    {
        "local_inference": {
            "requests": 342,
            "tokens": 45821,
            "cost": "$0.00",
            "percentage": "87.3%"
        },
        "cloud_inference": {
            "requests": 50,
            "tokens": 12341,
            "cost": "$0.18",
            "percentage": "12.7%"
        },
        "cost_savings": "$4.32"
    }
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        gateway = get_gateway()
        stats = gateway.get_usage_stats()

        return {
            "status": "success",
            "stats": stats,
            "message": f"Local inference saving ~${stats['cost_savings']} vs cloud-only",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting stats: {str(e)}",
        )


@router.post("/setup-ollama")
async def get_ollama_setup_instructions():
    """
    Get setup instructions for Ollama.

    Returns markdown with complete setup steps.
    """
    from app.services.local_inference import OLLAMA_SETUP

    return {
        "status": "success",
        "instructions": OLLAMA_SETUP,
        "estimated_cost_savings": "$50-100/year per home server",
    }
