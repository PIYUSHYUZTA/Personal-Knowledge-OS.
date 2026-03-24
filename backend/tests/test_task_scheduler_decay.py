"""Tests for nightly graph heatmap decay scheduling logic."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import sys
import types

from sqlalchemy.orm import declarative_base
from sqlalchemy import Boolean, Column, DateTime, Float, Integer


if "apscheduler.schedulers.background" not in sys.modules:
    apscheduler_module = types.ModuleType("apscheduler")
    schedulers_module = types.ModuleType("apscheduler.schedulers")
    background_module = types.ModuleType("apscheduler.schedulers.background")
    triggers_module = types.ModuleType("apscheduler.triggers")
    cron_module = types.ModuleType("apscheduler.triggers.cron")

    class _BackgroundSchedulerStub:
        def __init__(self, daemon=True):
            self.daemon = daemon
            self.running = False

        def start(self):
            self.running = True

        def shutdown(self):
            self.running = False

        def add_job(self, *args, **kwargs):
            return None

        def get_jobs(self):
            return []

    class _CronTriggerStub:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    background_module.BackgroundScheduler = _BackgroundSchedulerStub
    cron_module.CronTrigger = _CronTriggerStub

    sys.modules["apscheduler"] = apscheduler_module
    sys.modules["apscheduler.schedulers"] = schedulers_module
    sys.modules["apscheduler.schedulers.background"] = background_module
    sys.modules["apscheduler.triggers"] = triggers_module
    sys.modules["apscheduler.triggers.cron"] = cron_module

if "app.services.intelligence_synthesis" not in sys.modules:
    intelligence_stub = types.ModuleType("app.services.intelligence_synthesis")

    class _WeeklyIntelligenceReportStub:
        def __init__(self, user_id, session):
            self.user_id = user_id
            self.session = session

        def generate_weekly_report(self):
            return {}

    class _CacheStub:
        def store_report(self, user_id, report):
            return None

    intelligence_stub.WeeklyIntelligenceReport = _WeeklyIntelligenceReportStub
    intelligence_stub.get_intelligence_cache = lambda: _CacheStub()
    sys.modules["app.services.intelligence_synthesis"] = intelligence_stub

if "app.database.connection" not in sys.modules:
    db_connection_stub = types.ModuleType("app.database.connection")
    db_connection_stub.Base = declarative_base()
    db_connection_stub.SessionLocal = lambda: None
    sys.modules["app.database.connection"] = db_connection_stub

if "app.models" not in sys.modules:
    models_stub = types.ModuleType("app.models")
    Base = sys.modules["app.database.connection"].Base

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        is_active = Column(Boolean, default=True)

    class GraphEntity(Base):
        __tablename__ = "graph_entities"
        id = Column(Integer, primary_key=True)
        weight = Column(Float, nullable=False)
        created_at = Column(DateTime(timezone=True), nullable=False)
        last_accessed_at = Column(DateTime(timezone=True), nullable=True)

    models_stub.User = User
    models_stub.GraphEntity = GraphEntity
    sys.modules["app.models"] = models_stub

from app.core import task_scheduler as task_scheduler_module
from app.core.task_scheduler import TaskScheduler


@dataclass
class MockGraphEntityRow:
    """In-memory row model for decay simulation in mocked DB session."""

    weight: float
    created_at: datetime
    last_accessed_at: datetime | None = None


class MockResult:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount


class MockSession:
    """Session double that simulates stale-vs-active updates and returns rowcount."""

    def __init__(self, rows, inactive_days: int, multiplier: float, min_floor: float):
        self.rows = rows
        self.inactive_days = inactive_days
        self.multiplier = multiplier
        self.min_floor = min_floor
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.last_stmt = None

    def execute(self, stmt):
        self.last_stmt = stmt
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=self.inactive_days)
        updated = 0

        for row in self.rows:
            stale_dt = row.last_accessed_at or row.created_at
            if row.weight > 0.0 and stale_dt <= cutoff_dt:
                row.weight = max(round(row.weight * self.multiplier, 4), self.min_floor)
                updated += 1

        return MockResult(updated)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_nightly_decay_updates_only_stale_rows_and_clamps_min_floor(monkeypatch, caplog):
    """Stale rows decay, active rows are preserved, and low values clamp to floor."""
    now = datetime.now(timezone.utc)
    stale_old = MockGraphEntityRow(weight=0.4, created_at=now - timedelta(days=120))
    stale_tiny = MockGraphEntityRow(weight=0.001, created_at=now - timedelta(days=95))
    active_recent = MockGraphEntityRow(weight=0.9, created_at=now - timedelta(days=1))
    active_zero = MockGraphEntityRow(weight=0.0, created_at=now - timedelta(days=200))

    inactive_days = 7
    multiplier = 0.5
    min_floor = 0.01

    mock_session = MockSession(
        rows=[stale_old, stale_tiny, active_recent, active_zero],
        inactive_days=inactive_days,
        multiplier=multiplier,
        min_floor=min_floor,
    )

    monkeypatch.setattr(task_scheduler_module, "SessionLocal", lambda: mock_session)
    monkeypatch.setattr(task_scheduler_module.settings, "GRAPH_HEATMAP_DECAY_INACTIVE_DAYS", inactive_days, raising=False)
    monkeypatch.setattr(task_scheduler_module.settings, "GRAPH_HEATMAP_DECAY_MULTIPLIER", multiplier, raising=False)
    monkeypatch.setattr(task_scheduler_module.settings, "GRAPH_HEATMAP_MIN_WEIGHT_FLOOR", min_floor, raising=False)
    monkeypatch.setattr(task_scheduler_module.settings, "GRAPH_HEATMAP_NIGHTLY_DECAY_HOUR_UTC", 3, raising=False)
    monkeypatch.setattr(task_scheduler_module.settings, "GRAPH_HEATMAP_NIGHTLY_DECAY_MINUTE_UTC", 0, raising=False)

    with caplog.at_level(logging.INFO):
        TaskScheduler()._run_nightly_heatmap_decay()

    assert stale_old.weight == 0.2
    assert stale_tiny.weight == 0.01
    assert active_recent.weight == 0.9
    assert active_zero.weight == 0.0

    assert mock_session.committed is True
    assert mock_session.rolled_back is False
    assert mock_session.closed is True

    assert mock_session.last_stmt is not None
    assert "greatest" in str(mock_session.last_stmt).lower()
    assert "round" in str(mock_session.last_stmt).lower()

    assert "03:00 UTC sweep updated 2 rows" in caplog.text
