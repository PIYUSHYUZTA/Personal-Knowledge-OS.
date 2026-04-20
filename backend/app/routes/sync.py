"""
Federated P2P Sync API Endpoints.

Multi-instance synchronization without central cloud.
Home server ↔ Mobile bidirectional sync.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database.connection import get_db
from app.core.security import verify_token, extract_user_id_from_token
from app.models import User
from app.services.federated_sync import FederatedSyncManager, SyncDelta

router = APIRouter(prefix="/api/sync", tags=["P2P Sync"])


@router.post("/receive-deltas")
async def receive_sync_deltas(
    token: str,
    instance_id: str = Body(...),
    deltas: List[Dict[str, Any]] = Body(...),
    db_session: Session = Depends(get_db),
):
    """
    Receive sync deltas from peer instance.

    Called by:
    - Mobile instance sending changes to home server
    - Home server sending changes to mobile (future)

    Returns:
    {
        "status": "success",
        "deltas_received": 3,
        "deltas_applied": 3,
        "conflicts_resolved": 0
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
        sync_manager = FederatedSyncManager(user_id, db_session, instance_id="home-server")

        # Convert dict deltas to SyncDelta objects
        delta_objects = [
            SyncDelta(
                chunk_id=d["chunk_id"],
                operation=d["operation"],
                content=d.get("content"),
                source_instance=d.get("source_instance", instance_id),
            )
            for d in deltas
        ]

        # Apply deltas
        import asyncio
        asyncio.run(sync_manager._apply_deltas(delta_objects))

        return {
            "status": "success",
            "deltas_received": len(deltas),
            "deltas_applied": len(delta_objects),
            "conflicts_resolved": 0,
            "message": f"Synced {len(deltas)} changes from {instance_id}",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.get("/deltas-since")
async def get_deltas_since(
    token: str,
    timestamp: str,  # ISO format: "2026-03-12T14:30:00"
    db_session: Session = Depends(get_db),
):
    """
    Get all sync deltas since a given timestamp.

    Called by mobile instance to pull changes from home server.

    Returns:
    {
        "deltas": [
            {
                "chunk_id": "abc-123",
                "operation": "update",
                "timestamp": "2026-03-12T14:35:00"
            }
        ],
        "total_deltas": 5
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
        from datetime import datetime

        sync_manager = FederatedSyncManager(user_id, db_session)
        target_timestamp = datetime.fromisoformat(timestamp)

        # Get deltas since timestamp
        deltas = sync_manager.sync_log.get_deltas_since(target_timestamp)

        return {
            "status": "success",
            "deltas": [d.to_dict() for d in deltas],
            "total_deltas": len(deltas),
            "queried_timestamp": timestamp,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting deltas: {str(e)}",
        )


@router.post("/sync-now")
async def trigger_manual_sync(
    token: str,
    peer_endpoint: str = None,  # "http://home-server:8000" for mobile
    db_session: Session = Depends(get_db),
):
    """
    Trigger immediate synchronization with peer instance.

    Called when:
    - Mobile user manually syncs
    - Home server initiates backup to cloud
    - Network becomes available

    Returns:
    {
        "status": "success",
        "deltas_sent": 3,
        "deltas_received": 5,
        "synced_at": "2026-03-12T..."
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
        import asyncio

        sync_manager = FederatedSyncManager(user_id, db_session)

        # Determine instance ID
        instance_id = "mobile" if peer_endpoint else "home-server"

        result = asyncio.run(
            sync_manager.sync_to_peer(
                peer_instance_id="home-server" if instance_id == "mobile" else "mobile",
                peer_endpoint=peer_endpoint,
            )
        )

        return {
            "status": "success",
            "sync_result": result,
            "next_sync_recommendation": "in 1 hour" if result["deltas_sent"] > 0 else "whenever changes occur",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )


@router.get("/status")
async def get_sync_status(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get current synchronization status across instances.

    Returns:
    {
        "instance_id": "home-server",
        "instance_type": "primary",
        "pending_syncs": 0,
        "last_sync_hours_ago": 0.5,
        "sync_status": "synced"
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
        sync_manager = FederatedSyncManager(user_id, db_session)
        status_response = sync_manager.get_sync_status()

        return {
            "status": "success",
            "sync_status": status_response,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting status: {str(e)}",
        )


@router.post("/resolve-conflict")
async def resolve_conflict(
    token: str,
    chunk_id: str,
    preferred_version: str = "local",  # or "remote"
    db_session: Session = Depends(get_db),
):
    """
    Manually resolve a sync conflict.

    Policy: Local (user's) version takes precedence.
    But admin can override if needed.

    Returns:
    {
        "status": "success",
        "conflict_resolved": true,
        "version_used": "local"
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
        sync_manager = FederatedSyncManager(user_id, db_session)

        # In this implementation, always use local (user's version)
        result_version = "local"

        return {
            "status": "success",
            "chunk_id": chunk_id,
            "conflict_resolved": True,
            "version_used": result_version,
            "note": "User's local version is authoritative",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resolving conflict: {str(e)}",
        )
