"""
Weekly Intelligence Report API Endpoints.

Exposes generated intelligence reports and connection maps.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.security import verify_token, extract_user_id_from_token
from app.models import User
from app.services.intelligence_synthesis import WeeklyIntelligenceReport, get_intelligence_cache
from app.core.task_scheduler import get_scheduler

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence"])


@router.get("/weekly-report")
async def get_weekly_report(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get the latest weekly intelligence report for the authenticated user.

    Returns:
    {
        "week_of": "2026-03-09",
        "summary": "3 new PDFs on web development ingested this week...",
        "ingested_sources": [{...}],
        "new_concepts": [{...}],
        "emerging_expertise": [{...}],
        "connection_map": {...},
        "insights": [...],
        "recommendations": [...],
        "generated_at": "2026-03-11T..."
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

    # Try to get cached report
    cache = get_intelligence_cache()
    cached_report = cache.get_latest_report(str(user_id))

    if cached_report:
        return {
            "status": "success",
            "source": "cached",
            "report": cached_report,
        }

    # If no cached report, generate one now
    try:
        report_gen = WeeklyIntelligenceReport(str(user_id), db_session)
        report = report_gen.generate_weekly_report()

        # Cache it
        cache.store_report(str(user_id), report)

        return {
            "status": "success",
            "source": "generated",
            "report": report,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}",
        )


@router.post("/regenerate-report")
async def regenerate_weekly_report(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Force regenerate the weekly intelligence report.

    Useful for testing or when new data was just ingested.
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
        report_gen = WeeklyIntelligenceReport(str(user_id), db_session)
        report = report_gen.generate_weekly_report()

        # Cache it
        cache = get_intelligence_cache()
        cache.store_report(str(user_id), report)

        return {
            "status": "success",
            "message": "Report regenerated",
            "report": report,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}",
        )


@router.get("/connection-map")
async def get_connection_map(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get the connection map from the latest weekly report.

    Shows how concepts relate to each other and form expertise clusters.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Get cached report
    cache = get_intelligence_cache()
    report = cache.get_latest_report(str(user_id))

    if not report:
        # Generate new report
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            report_gen = WeeklyIntelligenceReport(str(user_id), db_session)
            report = report_gen.generate_weekly_report()
            cache.store_report(str(user_id), report)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating report: {str(e)}",
            )

    return {
        "status": "success",
        "week_of": report.get("week_of"),
        "connection_map": report.get("connection_map", {}),
        "clusters": report.get("connection_map", {}).get("clusters", []),
        "bridges": report.get("connection_map", {}).get("bridges", []),
    }


@router.get("/expertise-areas")
async def get_expertise_areas(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get emerging expertise areas from the latest weekly report.

    Shows where your knowledge is deepening and how confident the system is.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Get cached report
    cache = get_intelligence_cache()
    report = cache.get_latest_report(str(user_id))

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No weekly report available. Check back Sunday morning.",
        )

    return {
        "status": "success",
        "week_of": report.get("week_of"),
        "expertise_areas": report.get("emerging_expertise", []),
        "project_relevance": report.get("project_relevance", []),
    }


@router.get("/insights")
async def get_weekly_insights(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get AI-generated insights and recommendations from the latest report.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Get cached report
    cache = get_intelligence_cache()
    report = cache.get_latest_report(str(user_id))

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No weekly report available.",
        )

    return {
        "status": "success",
        "week_of": report.get("week_of"),
        "summary": report.get("summary", ""),
        "insights": report.get("insights", []),
        "recommendations": report.get("recommendations", []),
        "generated_at": report.get("generated_at"),
    }


@router.get("/scheduler-status")
async def get_scheduler_status():
    """
    Get the status of the background task scheduler.

    Shows when the next weekly report will be generated.
    """
    scheduler = get_scheduler()
    status = scheduler.get_job_status()

    return {
        "scheduler_running": status["scheduler_running"],
        "jobs": status["jobs"],
        "message": "Weekly reports are automatically generated on Sundays at 2 AM UTC",
    }
