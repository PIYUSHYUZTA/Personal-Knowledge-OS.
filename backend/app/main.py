"""
FastAPI application main entry point.
Sets up ASGI server, middleware, and route integration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.config import settings
from app.database.connection import init_db
from app.routes import auth, health
from app.services.llm_factory import LLMFactory
from app.core.security_hardening import SecurityMiddleware, RateLimiter
from app.core.task_scheduler import start_background_tasks, stop_background_tasks
from app.core.redis_pubsub import shutdown_redis_pubsub, get_redis_pubsub
from app.services.graph_events_broker import GraphEventBroker

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# ============================================================================
# LIFECYCLE EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle: startup and shutdown events.
    """
    # STARTUP
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"Embedding model: {settings.EMBEDDING_MODEL}")
    logger.info(f"AURA service enabled")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize LLM Factory (Multi-Model Support)
    try:
        LLMFactory.initialize()
        logger.info("LLM Factory initialized with multi-model support")
    except Exception as e:
        logger.error(f"LLM Factory initialization failed: {e}")

    # Start Background Tasks (Phase 5 - Knowledge Intelligence)
    try:
        start_background_tasks()
        logger.info("Background task scheduler started")
    except Exception as e:
        logger.warning(f"Background tasks warning: {e}")

    # Initialize Redis Pub/Sub (Phase 7a - Real-time graph updates)
    try:
        redis_pubsub = await get_redis_pubsub()
        GraphEventBroker.set_redis_pubsub(redis_pubsub)
        logger.info("Redis pub/sub + GraphEventBroker initialized")
    except Exception as e:
        logger.warning(f"Redis pub/sub initialization warning: {e}")

    # Start GraphUpdateBroadcaster (Phase 7a - Real-time WebSocket graph updates)
    try:
        from app.api.v1.stream import GraphUpdateBroadcaster
        await GraphUpdateBroadcaster.start()
        logger.info("GraphUpdateBroadcaster started")
    except Exception as e:
        logger.warning(f"GraphUpdateBroadcaster warning: {e}")

    yield

    # SHUTDOWN
    logger.info("Shutting down application...")

    # Stop GraphUpdateBroadcaster
    try:
        from app.api.v1.stream import GraphUpdateBroadcaster
        await GraphUpdateBroadcaster.stop()
        logger.info("GraphUpdateBroadcaster stopped")
    except Exception as e:
        logger.warning(f"Error stopping GraphUpdateBroadcaster: {e}")

    # Shutdown Redis Pub/Sub
    try:
        await shutdown_redis_pubsub()
        logger.info("Redis pub/sub shutdown complete")
    except Exception as e:
        logger.warning(f"Error shutting down Redis pub/sub: {e}")

    # Stop background tasks
    try:
        stop_background_tasks()
        logger.info("Background tasks stopped")
    except Exception as e:
        logger.warning(f"Error stopping background tasks: {e}")

# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.APP_NAME,
        description="A unified Personal Knowledge OS with semantic search and AI-powered insights",
        version=settings.APP_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )

    # ========================================================================
    # MIDDLEWARE
    # ========================================================================

    # Security & Rate Limiting
    rate_limiter = RateLimiter(
        requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    )
    app.add_middleware(SecurityMiddleware, rate_limiter=rate_limiter)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZIP compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ========================================================================
    # ROUTES
    # ========================================================================

    # Health & Status
    app.include_router(health.router)

    # Authentication
    app.include_router(auth.router)

    # Knowledge Management
    from app.routes import knowledge
    app.include_router(knowledge.router)

    # AURA Technical Reasoning Engine
    from app.routes import aura
    app.include_router(aura.router)

    # Streaming API (Phase 3 - Real-time responses)
    from app.api.v1 import stream
    app.include_router(stream.router)

    # Model Monitoring (Phase 4 - Cost tracking)
    from app.routes import monitoring
    app.include_router(monitoring.router)

    # Intelligence & Knowledge Synthesis (Phase 5 - Weekly reports)
    from app.routes import intelligence
    app.include_router(intelligence.router)

    # Knowledge Distillation (Phase 5 - Long-term memory compression)
    from app.routes import distillation
    app.include_router(distillation.router)

    # Heatmap & Expertise Analytics (Phase 5 - 3D visualization)
    from app.routes import heatmap
    app.include_router(heatmap.router)

    # Local Inference & Hybrid Gateway (Phase 6 - Edge computing)
    from app.routes import inference
    app.include_router(inference.router)

    # Code Sandbox Execution (Phase 6a - Verified computation)
    from app.routes import sandbox
    app.include_router(sandbox.router)

    # Web Research & Browser Agent (Phase 7a - Auto-learning from web)
    from app.routes import research
    app.include_router(research.router)

    # Skill Tracking & BCA Roadmap (Phase 6 - Study recommendations)
    from app.routes import skills
    app.include_router(skills.router)

    # Federated P2P Sync (Phase 6 - Multi-instance sync without cloud)
    from app.routes import sync
    app.include_router(sync.router)

    # ========================================================================
    # ROOT ENDPOINT
    # ========================================================================

    @app.get("/", tags=["Info"])
    async def root():
        """API root endpoint."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/api/docs",
            "status": "operational"
        }

    return app

# ============================================================================
# APPLICATION INSTANCE
# ============================================================================

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )
