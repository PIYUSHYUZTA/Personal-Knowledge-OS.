"""
Background Task Scheduler for PKOS.

Manages recurring tasks like:
- Weekly Intelligence Reports (every Sunday)
- Knowledge Distillation (daily, low-resource)
- Cache maintenance and optimization
"""

from typing import Optional
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
from sqlalchemy import func, update, and_, or_

from app.database.connection import SessionLocal
from app.services.intelligence_synthesis import WeeklyIntelligenceReport, get_intelligence_cache
from app.models import User, GraphEntity
from app.config import settings

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Manages background scheduled tasks."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler(daemon=True)
        self.is_running = False

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self.is_running = True
            logger.info("✅ Task scheduler started")

            # Register all tasks
            self._register_tasks()

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Task scheduler stopped")

    def _register_tasks(self):
        """Register all scheduled tasks."""
        # Weekly Intelligence Report (every Sunday at 2 AM UTC)
        self.scheduler.add_job(
            self._generate_weekly_reports,
            trigger=CronTrigger(day_of_week="6", hour=2, minute=0),  # Sunday 2 AM
            id="weekly_intelligence_report",
            name="Generate Weekly Intelligence Reports",
            replace_existing=True,
        )

        logger.info("📅 Registered weekly intelligence report task (Sundays 2 AM UTC)")

        # Nightly stale-node decay (every day at configured UTC time)
        if settings.GRAPH_HEATMAP_NIGHTLY_DECAY_ENABLED:
            self.scheduler.add_job(
                self._run_nightly_heatmap_decay,
                trigger=CronTrigger(
                    hour=settings.GRAPH_HEATMAP_NIGHTLY_DECAY_HOUR_UTC,
                    minute=settings.GRAPH_HEATMAP_NIGHTLY_DECAY_MINUTE_UTC,
                ),
                id="nightly_heatmap_decay",
                name="Decay stale graph-entity heatmap weights",
                replace_existing=True,
            )
            logger.info(
                "📅 Registered nightly heatmap decay task "
                f"(daily {settings.GRAPH_HEATMAP_NIGHTLY_DECAY_HOUR_UTC:02d}:"
                f"{settings.GRAPH_HEATMAP_NIGHTLY_DECAY_MINUTE_UTC:02d} UTC, "
                f"inactive>={settings.GRAPH_HEATMAP_DECAY_INACTIVE_DAYS}d, "
                f"multiplier={settings.GRAPH_HEATMAP_DECAY_MULTIPLIER})"
            )

    async def _generate_weekly_reports(self):
        """Generate weekly intelligence reports for all users."""
        try:
            db_session = SessionLocal()

            # Get all active users
            users = db_session.query(User).filter(User.is_active == True).all()

            logger.info(f"🔄 Generating weekly reports for {len(users)} users...")

            for user in users:
                try:
                    # Generate report
                    report_gen = WeeklyIntelligenceReport(str(user.id), db_session)
                    report = report_gen.generate_weekly_report()

                    # Cache the report
                    cache = get_intelligence_cache()
                    cache.store_report(str(user.id), report)

                    logger.info(f"✅ Report generated for user {user.email}")

                except Exception as e:
                    logger.error(f"❌ Failed to generate report for user {user.email}: {e}")

            db_session.close()
            logger.info(f"✅ Weekly report generation complete")

        except Exception as e:
            logger.error(f"❌ Weekly report task failed: {e}", exc_info=True)

    def _run_nightly_heatmap_decay(self):
        """
        Apply decay to stale graph entities using one set-based DB update.

        Criteria:
        - entity.weight > 0
        - COALESCE(last_accessed_at, created_at) <= now - inactive_days
        """
        inactive_days = max(0, settings.GRAPH_HEATMAP_DECAY_INACTIVE_DAYS)
        decay_multiplier = max(0.0, min(settings.GRAPH_HEATMAP_DECAY_MULTIPLIER, 1.0))
        min_weight_floor = max(0.0, settings.GRAPH_HEATMAP_MIN_WEIGHT_FLOOR)
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=inactive_days)

        db_session = SessionLocal()
        try:
            stale_expr = func.coalesce(GraphEntity.last_accessed_at, GraphEntity.created_at)

            stmt = (
                update(GraphEntity)
                .where(
                    and_(
                        GraphEntity.weight > 0.0,
                        stale_expr <= cutoff_dt,
                    )
                )
                .values(
                    weight=func.greatest(
                        func.round(GraphEntity.weight * decay_multiplier, 4),
                        min_weight_floor,
                    )
                )
            )

            result = db_session.execute(stmt)
            db_session.commit()
            rows_updated = result.rowcount or 0
            sweep_time = (
                f"{settings.GRAPH_HEATMAP_NIGHTLY_DECAY_HOUR_UTC:02d}:"
                f"{settings.GRAPH_HEATMAP_NIGHTLY_DECAY_MINUTE_UTC:02d}"
            )

            logger.info(
                "✅ Nightly heatmap decay complete: "
                f"updated={rows_updated}, "
                f"inactive_days={inactive_days}, multiplier={decay_multiplier}, "
                f"min_floor={min_weight_floor}"
            )
            logger.info(
                "💓 Heatmap heartbeat: "
                f"{sweep_time} UTC sweep updated {rows_updated} rows"
            )
        except Exception as e:
            db_session.rollback()
            logger.error(f"❌ Nightly heatmap decay task failed: {e}", exc_info=True)
        finally:
            db_session.close()

    def get_job_status(self) -> dict:
        """Get status of all scheduled jobs."""
        return {
            "scheduler_running": self.scheduler.running,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
                for job in self.scheduler.get_jobs()
            ],
        }


# Global scheduler instance
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Get or create the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


def start_background_tasks():
    """Start all background tasks."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_background_tasks():
    """Stop all background tasks."""
    scheduler = get_scheduler()
    scheduler.stop()
