"""
Database connection, session management, and optional pgvector support.
Supports both PostgreSQL (production) and SQLite (local development).
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool, StaticPool
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()

# Detect database type
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# Create engine with proper pool configuration
engine_kwargs = {
    "echo": settings.DEBUG,
}

if is_sqlite:
    # SQLite needs special handling
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
else:
    # PostgreSQL pool settings
    if settings.DEBUG:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

# SQLAlchemy session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

def get_db():
    """
    Dependency for FastAPI to inject database session.
    Usage:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize all database tables."""
    # Ensure data directory exists for SQLite
    if is_sqlite:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

# Enable pgvector extension (PostgreSQL only)
@event.listens_for(engine, "connect")
def on_connect(dbapi_conn, connection_record):
    """Enable pgvector extension on PostgreSQL connections."""
    if is_sqlite:
        # Enable WAL mode for better SQLite concurrency
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    else:
        try:
            cursor = dbapi_conn.cursor()
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.close()
            logger.info("pgvector extension enabled")
        except Exception as e:
            logger.warning(f"Could not enable pgvector: {e}")
