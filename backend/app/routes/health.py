"""
Health check and status endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.connection import get_db
from sqlalchemy import text

router = APIRouter(tags=["Health"])

@router.get("/health", summary="Health check")
def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/status", summary="System status")
def system_status(db: Session = Depends(get_db)):
    """
    Get detailed system status.
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "operational",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/version", summary="API version")
def get_version():
    """Get API version."""
    return {
        "version": "1.0.0-alpha",
        "name": "PKOS - Personal Knowledge OS",
        "environment": "development"
    }
