"""
Knowledge Map Heatmap API Endpoints.

Exposes expertise heatmaps and cluster analysis for 3D visualization.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.connection import get_db
from app.core.security import verify_token
from app.models import User
from app.services.query_analytics import get_query_analytics

router = APIRouter(prefix="/api/heatmap", tags=["Heatmap"])


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class InteractionHitRequest(BaseModel):
    entity_name: str = Field(..., min_length=1, max_length=500)
    hit_weight: float = Field(default=1.0, ge=0.0, le=10.0)


# ---------------------------------------------------------------------------
# POST /record-interaction   – UI click or programmatic trigger
# ---------------------------------------------------------------------------

@router.post("/record-interaction", status_code=status.HTTP_204_NO_CONTENT)
async def record_node_interaction(
    body: InteractionHitRequest,
    authorization: str = Header(..., alias="Authorization"),
    db_session: Session = Depends(get_db),
):
    """
    Record that the user interacted with a named entity node.

    Increments `weight` on the matching GraphEntity row so the Three.js
    visualiser can reflect updated emissive intensity on the next render.

    Payload:
        { "entity_name": "PostgreSQL", "hit_weight": 1.0 }
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    token_str = authorization.split(" ", 1)[1]
    payload = verify_token(token_str)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    from app.services.knowledge_service import KnowledgeService
    KnowledgeService.record_interaction_hit(
        db=db_session,
        user_id=user_id,
        entity_name=body.entity_name,
        hit_weight=body.hit_weight,
    )
    # 204 – no body


# ---------------------------------------------------------------------------
# POST /apply-decay   – Run decay pass (called by scheduler or admin)
# ---------------------------------------------------------------------------

@router.post("/apply-decay")
async def run_knowledge_decay(
    authorization: str = Header(..., alias="Authorization"),
    half_life_days: float = 14.0,
    db_session: Session = Depends(get_db),
):
    """
    Trigger a knowledge-decay pass for the authenticated user.

    Decays all GraphEntity weights using exponential half-life:
        new_weight = weight * 2^(-days_elapsed / half_life_days)

    Intended to be called nightly by the task scheduler.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    token_str = authorization.split(" ", 1)[1]
    payload = verify_token(token_str)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    from app.services.knowledge_service import KnowledgeService
    updated = KnowledgeService.apply_knowledge_decay(
        db=db_session,
        user_id=user_id,
        half_life_days=half_life_days,
    )
    return {"status": "success", "entities_updated": updated, "half_life_days": half_life_days}


@router.get("/expertise")
async def get_expertise_heatmap(
    token: str,
    days: int = 30,
    db_session: Session = Depends(get_db),
):
    """
    Get the expertise heatmap showing which knowledge areas are most frequently queried.

    Returns:
    {
        "nodes": [
            {
                "name": "database",
                "frequency": 45,
                "heatmap_value": 0.95,
                "intensity": "high"
            },
            ...
        ],
        "max_frequency": 47,
        "heatmap_type": "expertise"
    }
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))
    user = db_session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        analytics = get_query_analytics(user_id, db_session)
        heatmap = analytics.get_query_heatmap(days=days)

        return {
            "status": "success",
            "heatmap": heatmap,
            "period_days": days,
            "visualization_hint": "Make nodes brighter/larger based on heatmap_value (0-1)",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating heatmap: {str(e)}",
        )


@router.get("/clusters")
async def get_expertise_clusters(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get expertise clusters showing related areas of knowledge.

    Returns groups of concepts that are frequently accessed together.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))
    user = db_session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        analytics = get_query_analytics(user_id, db_session)
        clusters = analytics.get_expertise_clusters()

        return {
            "status": "success",
            "clusters": clusters,
            "total_clusters": len(clusters),
            "visualization_hint": "Group 3D nodes by cluster and color by similarity",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting clusters: {str(e)}",
        )


@router.get("/summary")
async def get_expertise_summary(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get a comprehensive expertise summary with heatmap and clusters.

    Provides all data needed for the 3D knowledge map visualization.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))
    user = db_session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        analytics = get_query_analytics(user_id, db_session)
        summary = analytics.get_expertise_summary()

        return {
            "status": "success",
            "summary": summary,
            "user": {
                "id": str(user_id),
                "email": user.email,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting summary: {str(e)}",
        )


@router.get("/knowledge-map-enhanced")
async def get_enhanced_knowledge_map(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get complete knowledge map data WITH heatmap values for 3D visualization.

    Combines graph structure (nodes/edges) with expertise heatmap data.
    Phase 3.5: Uses decay-based intensity and Three.js color grading.

    Returns:
    {
        "nodes": [
            {
                "id": "postgres",
                "label": "postgres",
                "type": "TECHNOLOGY",
                "query_frequency": 42,
                "heatmap_intensity": 0.89,
                "glow_color": "#ffffff",
                "glow_tier": "hot",
                "emissive_intensity": 0.89
            },
            ...
        ],
        "edges": [...],
        "heatmap_range": {"min": 0, "max": 47}
    }
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))
    user = db_session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        from app.services.graph_service import get_graph_service

        graph_service = get_graph_service()
        analytics = get_query_analytics(user_id, db_session)

        # Get base graph
        if graph_service:
            graph_data = graph_service.export_graph_as_json()
        else:
            graph_data = {"nodes": [], "edges": []}

        # Get heatmap (Phase 3.5: now includes decay intensity and color grading)
        heatmap = analytics.get_query_heatmap(days=30)

        # Augment nodes with heatmap data
        heatmap_map = {node["name"]: node for node in heatmap.get("nodes", [])}
        max_frequency = heatmap.get("max_frequency", 1)

        for node in graph_data.get("nodes", []):
            node_name = node.get("label", "").lower()
            heatmap_data = heatmap_map.get(node_name)

            if heatmap_data:
                node["query_frequency"] = heatmap_data["frequency"]
                node["heatmap_intensity"] = heatmap_data["heatmap_value"]
                node["decay_intensity"] = heatmap_data.get("decay_intensity", 0)
                node["glow_color"] = heatmap_data.get("glow_color", "#2979ff")
                node["glow_tier"] = heatmap_data.get("glow_tier", "cold")
                # Three.js emissive intensity: maps directly to heatmap value
                node["emissive_intensity"] = heatmap_data["heatmap_value"]
            else:
                node["query_frequency"] = 0
                node["heatmap_intensity"] = 0
                node["decay_intensity"] = 0
                node["glow_color"] = "#1a237e"  # Deep blue for unknown
                node["glow_tier"] = "cold"
                node["emissive_intensity"] = 0.05  # Minimal glow

        return {
            "status": "success",
            "graph": graph_data,
            "heatmap_range": {
                "min": 0,
                "max": max_frequency,
            },
            "color_scale": {
                "cold": {"color": "#2979ff", "label": "New/Rarely Accessed", "range": "0.0-0.3"},
                "warm": {"color": "#00e5ff", "label": "Moderately Integrated", "range": "0.3-0.7"},
                "hot": {"color": "#ffffff", "label": "Core Expertise", "range": "0.7-1.0"},
            },
            "visualization_instructions": {
                "node_size": "Scale by query_frequency",
                "node_glow": "Use emissive_intensity for Three.js MeshStandardMaterial.emissiveIntensity",
                "node_color": "Use glow_color for emissive color",
                "hover_info": "Show query_frequency and glow_tier on hover",
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting enhanced map: {str(e)}",
        )


class InteractionLegacyRequest(BaseModel):
    concept_name: str
    interaction_type: str = "click"

@router.post("/interaction")
async def record_node_interaction_legacy(
    body: InteractionLegacyRequest,
    authorization: str = Header(..., alias="Authorization"),
    db_session: Session = Depends(get_db),
):
    """
    Record a UI interaction with a knowledge graph node (Phase 3.5).

    Called when a user clicks or hovers on a node in the 3D graph,
    increasing its heatmap intensity.

    Args:
        concept_name: The concept node that was interacted with
        interaction_type: "click" (weight 0.5) or "search" (weight 1.0)
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    token_str = authorization.split(" ", 1)[1]
    payload = verify_token(token_str)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))

    hit_weights = {"click": 0.5, "search": 1.0, "view": 0.2}
    weight = hit_weights.get(body.interaction_type, 0.3)

    from app.services.query_analytics import InteractionTracker

    InteractionTracker.record_hit(user_id, body.concept_name, hit_weight=weight)

    return {
        "status": "recorded",
        "concept": body.concept_name,
        "interaction_type": body.interaction_type,
        "weight": weight,
    }
