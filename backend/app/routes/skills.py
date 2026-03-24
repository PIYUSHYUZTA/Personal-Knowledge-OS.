"""
Skill Tracker API Endpoints.

BCA curriculum-aware expertise assessment and study recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.connection import get_db
from app.core.security import verify_token
from app.models import User
from app.services.skill_tracker import SkillTracker

router = APIRouter(prefix="/api/skills", tags=["Skill Tracking"])


@router.get("/assessment")
async def get_skill_assessment(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get comprehensive skill assessment across BCA domains.

    Returns expertise level, density, and query frequency for each topic.

    Example:
    {
        "domains": {
            "data_structures": {
                "level": "ADVANCED",
                "confidence": 0.92,
                "entity_density": 28,
                "query_frequency": 45,
                "mastery": 0.88
            },
            ...
        },
        "overall_progress": "72%",
        "strengths": ["data_structures", "algorithms"],
        "weaknesses": ["devops", "testing"]
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
        tracker = SkillTracker(user_id, db_session)
        expertise = tracker.assess_expertise()

        return {
            "status": "success",
            "expertise": expertise,
            "user": {"id": str(user_id), "email": user.email},
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting assessment: {str(e)}",
        )


@router.get("/gaps")
async def get_skill_gaps(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get identified skill gaps and what needs improvement.

    Returns domains rated BEGINNER or INTERMEDIATE with priorities.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))
    user = db_session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        tracker = SkillTracker(user_id, db_session)
        expertise = tracker.assess_expertise()
        gaps = tracker.get_skill_gaps(expertise)

        return {
            "status": "success",
            "total_gaps": len(gaps),
            "gaps": gaps,
            "high_priority_count": len([g for g in gaps if g["priority"] == "HIGH"]),
            "message": f"{len([g for g in gaps if g['priority'] == 'HIGH'])} high-priority areas to study",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting gaps: {str(e)}",
        )


@router.get("/study-plan")
async def get_personalized_study_plan(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get a personalized study plan optimized for BCA completion.

    Returns recommended learning order with resources and projects.

    Example:
    {
        "current_progress": "72%",
        "estimated_completion": "18 weeks",
        "recommended_order": [
            {
                "order": 1,
                "domain": "TESTING",
                "priority": "HIGH",
                "resources": ["Pytest book", "Real Python testing course"],
                "projects": ["Write tests for existing code", "TDD kata"]
            },
            ...
        ],
        "milestones": [
            {"target_progress": "50%", "estimated_weeks": 9},
            {"target_progress": "75%", "estimated_weeks": 13},
            ...
        ]
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
        tracker = SkillTracker(user_id, db_session)
        expertise = tracker.assess_expertise()
        plan = tracker.get_study_plan(expertise)

        return {
            "status": "success",
            "study_plan": plan,
            "disclaimer": "This plan is optimized for finishing BCA with top marks. Adjust based on your pace.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting study plan: {str(e)}",
        )


@router.get("/trajectory")
async def get_skill_trajectory(
    token: str,
    days: int = 90,
    db_session: Session = Depends(get_db),
):
    """
    Get historical skill development trajectory.

    Shows how expertise has grown over time.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))

    # In production, would query skill history table
    return {
        "status": "success",
        "message": "Trajectory tracking coming soon",
        "note": "Currently supports point-in-time assessments. Historical tracking will be added.",
    }


@router.get("/summary")
async def get_skill_summary(
    token: str,
    db_session: Session = Depends(get_db),
):
    """
    Get a quick summary of your BCA readiness.

    Returns overall progress, key strengths, and next steps.
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    user_id = UUID(payload.get("sub"))
    user = db_session.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        tracker = SkillTracker(user_id, db_session)
        expertise = tracker.assess_expertise()
        gaps = tracker.get_skill_gaps(expertise)

        overall_progress = expertise.get("overall_progress", 0)
        progress_emoji = ""

        if overall_progress < 0.3:
            progress_emoji = "🟡 Just Starting"
        elif overall_progress < 0.6:
            progress_emoji = "🟠 Building Foundation"
        elif overall_progress < 0.8:
            progress_emoji = "🟢 On Track"
        else:
            progress_emoji = "🟢 Well Prepared"

        return {
            "status": "success",
            "overall_progress": f"{overall_progress * 100:.1f}%",
            "progress_stage": progress_emoji,
            "bca_readiness": "Good" if overall_progress > 0.7 else "Needs Work",
            "key_strengths": expertise.get("strengths", []),
            "priority_areas": [g["domain"] for g in gaps[:3]],
            "top_tip": f"Focus on {gaps[0]['domain'].replace('_', ' ').title()} next for maximum impact",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting summary: {str(e)}",
        )
