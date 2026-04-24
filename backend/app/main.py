"""
FastAPI application main entry point.
Sets up ASGI server, middleware, and route integration.
"""

import os
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')

import json
import time

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database.connection import init_db
from app.routes import auth, health
from app.core.security_hardening import SecurityMiddleware, RateLimiter

# Optional imports - gracefully degrade if not installed
try:
    from app.services.llm_factory import LLMFactory
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False

try:
    from app.core.task_scheduler import start_background_tasks, stop_background_tasks
    _HAS_SCHEDULER = True
except ImportError:
    _HAS_SCHEDULER = False

try:
    from app.core.redis_pubsub import shutdown_redis_pubsub, get_redis_pubsub
    from app.services.graph_events_broker import GraphEventBroker
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class JSONEnvelopeMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that normalizes completed JSON HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(("/api/docs", "/api/redoc", "/api/openapi.json")):
            return await call_next(request)

        response = await call_next(request)
        if response.status_code in (status.HTTP_204_NO_CONTENT, status.HTTP_304_NOT_MODIFIED):
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        headers = dict(response.headers)
        headers.pop("content-length", None)

        try:
            payload = json.loads(body.decode() or "null")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )

        if isinstance(payload, dict) and "success" in payload:
            normalized = payload
        elif response.status_code < 400:
            message_text = payload.get("message", "OK") if isinstance(payload, dict) else "OK"
            normalized = {"success": True, "data": payload, "message": message_text}
            if isinstance(payload, dict):
                normalized.update(payload)
        else:
            normalized = payload

        return JSONResponse(
            content=normalized,
            status_code=response.status_code,
            headers=headers,
        )

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
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize LLM Factory (Multi-Model Support)
    if _HAS_LLM:
        try:
            LLMFactory.initialize()
            logger.info("LLM Factory initialized with multi-model support")
        except Exception as e:
            logger.warning(f"LLM Factory initialization skipped: {e}")

    # Start Background Tasks (Phase 5 - Knowledge Intelligence)
    if _HAS_SCHEDULER:
        try:
            start_background_tasks()
            logger.info("Background task scheduler started")
        except Exception as e:
            logger.warning(f"Background tasks warning: {e}")

    # Initialize Redis Pub/Sub (Phase 7a - Real-time graph updates)
    if _HAS_REDIS and settings.REDIS_ENABLED:
        try:
            redis_pubsub = await get_redis_pubsub()
            GraphEventBroker.set_redis_pubsub(redis_pubsub)
            logger.info("Redis pub/sub + GraphEventBroker initialized")
        except Exception as e:
            logger.warning(f"Redis pub/sub initialization warning: {e}")
    else:
        logger.info("Redis pub/sub disabled or not installed")

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
    if _HAS_REDIS:
        try:
            await shutdown_redis_pubsub()
            logger.info("Redis pub/sub shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down Redis pub/sub: {e}")

    # Stop background tasks
    if _HAS_SCHEDULER:
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

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        """Log every HTTP request with method, path, status, and duration."""
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "%s %s -> %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            message = "Internal server error"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": message,
                "code": exc.status_code,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Invalid request",
                "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Internal server error",
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )

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

    app.add_middleware(JSONEnvelopeMiddleware)
    # GZIP compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ========================================================================
    # ROUTES
    # ========================================================================

    # Health & Status (always available)
    app.include_router(health.router)

    # Authentication (always available)
    app.include_router(auth.router)

    # Optional routes — each wrapped in try/except so missing deps don't crash the app
    def _safe_include(module_path: str, attr: str = "router"):
        """Safely include a router module, skip if import fails."""
        try:
            import importlib
            mod = importlib.import_module(module_path)
            router = getattr(mod, attr)
            app.include_router(router)
            logger.debug(f"Loaded route: {module_path}")
        except Exception as e:
            logger.warning(f"Skipped route {module_path}: {e}")

    _safe_include("app.routes.knowledge")
    _safe_include("app.routes.aura")
    _safe_include("app.api.v1.stream")
    _safe_include("app.routes.monitoring")
    _safe_include("app.routes.intelligence")
    _safe_include("app.routes.distillation")
    _safe_include("app.routes.heatmap")
    _safe_include("app.routes.inference")
    _safe_include("app.routes.sandbox")
    _safe_include("app.routes.research")
    _safe_include("app.routes.skills")
    _safe_include("app.routes.sync")

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
