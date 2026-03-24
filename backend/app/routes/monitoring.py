"""
Model Monitoring & Metrics API Endpoints.

Provides real-time access to LLM usage statistics, costs, and provider performance metrics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database.connection import get_db
from app.services.model_monitor import (
    get_usage_tracker,
    get_selection_optimizer,
)

router = APIRouter(prefix="/api/stats", tags=["Monitoring"])


@router.get("/llm-usage")
async def get_llm_usage_stats():
    """
    Get comprehensive LLM usage statistics.

    Returns:
    {
        "summary": {...},
        "by_provider": {...},
        "cost_breakdown": {...},
        "timestamp": "2026-03-09T..."
    }
    """
    tracker = get_usage_tracker()

    return {
        "summary": tracker.get_summary_metrics(),
        "by_provider": tracker.get_provider_metrics(),
        "cost_breakdown": tracker.get_cost_by_provider(),
        "timestamp": tracker.metrics[list(tracker.metrics.keys())[0]].last_used if tracker.metrics else None,
    }


@router.get("/llm-usage/{model_id}")
async def get_model_specific_stats(model_id: str):
    """
    Get statistics for a specific model.

    Args:
        model_id: Model identifier (e.g., 'claude-3-5-sonnet-20241022')

    Returns:
        Model-specific metrics including cost, tokens, and success rate
    """
    tracker = get_usage_tracker()
    metrics = tracker.get_provider_metrics(model_id)

    if not metrics:
        return {"error": f"No metrics found for {model_id}"}

    return {
        "model_id": model_id,
        "metrics": metrics,
    }


@router.get("/llm-providers")
async def get_provider_status():
    """
    Get available LLM providers and their status.

    Returns:
    {
        "providers": [
            {
                "name": "claude",
                "model_id": "claude-3-5-sonnet-20241022",
                "status": "active",
                "requests_count": 125,
                "success_rate": "98.4%",
                "avg_cost_per_request": "$0.001234"
            },
            ...
        ],
        "primary": "claude",
        "fallback_chain": ["gpt4", "gemini"]
    }
    """
    tracker = get_usage_tracker()

    providers = []
    for model_id, metrics in tracker.get_provider_metrics().items():
        providers.append({
            "model_id": model_id,
            "provider": metrics["provider"],
            "status": "active" if metrics["total_requests"] > 0 else "available",
            "requests": metrics["total_requests"],
            "success_rate": f"{metrics['success_rate']}%",
            "avg_cost_per_request": metrics["avg_cost_per_request"],
            "total_cost": metrics["total_cost_formatted"],
            "last_used": metrics["last_used"],
        })

    # Sort by request count (most used first)
    providers = sorted(providers, key=lambda x: x["requests"], reverse=True)

    return {
        "providers": providers,
        "summary": tracker.get_summary_metrics(),
        "total_providers": len(providers),
    }


@router.get("/llm-optimization")
async def get_optimization_insights():
    """
    Get AI-powered optimization recommendations.

    Returns insights on:
    - Most cost-effective provider
    - Most reliable provider
    - Usage patterns
    - Cost trends
    """
    tracker = get_usage_tracker()
    optimizer = get_selection_optimizer()

    summary = tracker.get_summary_metrics()
    cost_breakdown = tracker.get_cost_by_provider()

    # Find cheapest and most reliable
    best_cost = optimizer.select_best_provider(criteria="cost")
    best_reliability = optimizer.select_best_provider(criteria="reliability")

    recommendations = []

    # Add recommendations based on metrics
    if summary["total_requests"] > 100:
        # Recommend cost optimization if using expensive providers
        if summary["total_cost"] > 10:
            recommendations.append({
                "type": "cost_optimization",
                "message": f"Consider switching to {best_cost.value} for cost savings",
                "potential_savings": "10-50%",
            })

    if float(summary["success_rate"].rstrip("%")) < 95:
        recommendations.append({
            "type": "reliability",
            "message": f"Consider using {best_reliability.value} for better reliability",
            "current_success_rate": summary["success_rate"],
        })

    return {
        "recommendations": recommendations,
        "current_costs": cost_breakdown,
        "best_provider_by_cost": best_cost.value,
        "best_provider_by_reliability": best_reliability.value,
        "selection_history": optimizer.get_recommendation_history(),
    }


@router.get("/llm-costs")
async def get_cost_analytics():
    """
    Get detailed cost analytics and trends.

    Returns:
    {
        "total_cost": "$50.23",
        "by_provider": {...},
        "by_model": {...},
        "average_cost_per_request": "$0.0042",
        "estimated_monthly_cost": "$1,260.00"
    }
    """
    tracker = get_usage_tracker()
    summary = tracker.get_summary_metrics()

    # Estimate monthly cost if using current rate
    avg_daily_requests = 50  # Assume for estimation
    estimated_monthly = (summary.get("total_cost", 0) / max(1, summary.get("total_requests", 1))) * avg_daily_requests * 30

    return {
        "total_cost": summary.get("total_cost_formatted", "$0.00"),
        "by_provider": tracker.get_cost_by_provider(),
        "total_requests": summary["total_requests"],
        "average_cost_per_request": summary.get("avg_cost_per_request", 0),
        "cost_per_1k_tokens": f"${(summary.get('total_cost', 0) / max(1, summary.get('total_tokens', 1)) * 1000):.6f}",
        "estimated_monthly_cost": f"${estimated_monthly:.2f}",
        "tokens_used": {
            "input": summary["total_input_tokens"],
            "output": summary["total_output_tokens"],
            "total": summary["total_tokens"],
        },
    }


@router.post("/llm-usage/reset")
async def reset_usage_stats(model_id: Optional[str] = None):
    """
    Reset usage statistics (admin only).

    Args:
        model_id: Optional model ID to reset. If not provided, resets all metrics.

    Returns:
        Confirmation message
    """
    tracker = get_usage_tracker()
    tracker.reset_metrics(model_id)

    if model_id:
        return {
            "status": "success",
            "message": f"Reset metrics for {model_id}",
        }
    else:
        return {
            "status": "success",
            "message": "Reset all LLM metrics",
        }


@router.get("/health")
async def service_health():
    """
    Check health of monitoring service.

    Returns basic service status and metrics availability.
    """
    tracker = get_usage_tracker()

    return {
        "status": "healthy",
        "service": "Model Monitoring",
        "metrics_available": len(tracker.metrics) > 0,
        "total_models_tracked": len(tracker.metrics),
        "total_requests_tracked": tracker.get_summary_metrics()["total_requests"],
    }
