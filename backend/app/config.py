from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    Supports both .env files and environment variable overrides.
    """

    # Application
    APP_NAME: str = "PKOS - Personal Knowledge OS"
    APP_VERSION: str = "1.0.0-alpha"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # Database - PostgreSQL + pgvector
    DATABASE_URL: str = "postgresql:///pkos_db"

    # Vector Store
    VECTOR_STORE_TYPE: str = "pgvector"  # "pgvector" or "chromadb"
    CHROMADB_PATH: str = "./data/chromadb" if VECTOR_STORE_TYPE == "chromadb" else ""

    # Embedding Model
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Security & JWT
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MPC (Multi-Party Computation) - Phase 2
    MPC_ENABLED: bool = False
    MPC_PRIVATE_KEY: Optional[str] = None
    MPC_SERVER_ENDPOINTS: list = []

    # File Upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: list = ["pdf", "txt", "md", "docx"]
    UPLOAD_DIR: str = "./data/uploads"

    # PDF Processing
    PDF_EXTRACTION_METHOD: str = "pdfplumber"  # "pypdf" or "pdfplumber"
    OCR_ENABLED: bool = False
    TESSERACT_CMD: Optional[str] = None

    # Chunking Strategy
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # Neo4j (Knowledge Graph - Phase 2)
    NEO4J_ENABLED: bool = False
    NEO4J_URI: Optional[str] = "neo4j://localhost:7687"
    NEO4J_USERNAME: Optional[str] = "neo4j"
    NEO4J_PASSWORD: Optional[str] = None

    # AURA (AI Service)
    AURA_MODEL_TYPE: str = "local"  # "local", "openai", "anthropic"
    AURA_MAX_CONTEXT_WINDOW: int = 8000
    AURA_RESPONSE_TEMPERATURE: float = 0.7
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    CLAUDE_API_KEY: Optional[str] = None

    # Code Sandbox (Phase 6a - Python-only)
    SANDBOX_ENABLED: bool = True
    SANDBOX_TIMEOUT_SECONDS: int = 30  # Max execution time per script
    SANDBOX_MEMORY_LIMIT_MB: int = 512  # Max resident memory allowed
    SANDBOX_MAX_OUTPUT_SIZE: int = 1024 * 1024  # 1MB max combined stdout + stderr
    SANDBOX_ALLOWED_LIBRARIES: list = [
        "numpy", "pandas", "scipy", "matplotlib",  # Data science essentials
        "sympy", "math", "statistics",             # Math/computation
        "json", "csv", "re", "collections",        # Standard utilities
        "datetime", "time", "random"                # Common modules
    ]
    SANDBOX_BLOCKED_PYTHON_MODULES: list = [
        "os", "sys.exit", "subprocess", "socket",  # System access
        "eval", "exec", "__import__", "compile",   # Dynamic execution
        "open", "file", "input", "raw_input"       # I/O operations
    ]
    # Rate limiting for sandbox execution
    SANDBOX_RATE_LIMIT_PER_MINUTE: int = 10
    SANDBOX_RATE_LIMIT_PER_HOUR: int = 100

    # Web Scraping & Research (Phase 7a)
    WEB_RESEARCH_ENABLED: bool = True
    WEB_CONTENT_TIMEOUT: int = 30  # seconds per request
    WEB_CONTENT_MAX_SIZE: int = 10 * 1024 * 1024  # 10 MB
    WEB_CONTENT_USER_AGENT: str = "PKOS-Research/1.0 (+https://github.com/piyushnawani/pkos)"
    WEB_SCRAPER_RATE_LIMIT: int = 2  # requests per second per user
    WEB_CONTENT_CACHE_TTL: int = 86400  # 24 hours
    WEB_CONTENT_CHUNK_SIZE: int = 512  # Same as default
    WEB_CONTENT_CHUNK_OVERLAP: int = 50

    # URL patterns to trust (documentation sites)
    WEB_TRUSTED_DOMAINS: list = [
        "docs.python.org",
        "developer.mozilla.org",
        "react.dev",
        "nodejs.org",
        "stackoverflow.com",
        "github.com",
        "en.wikipedia.org",
        "www.python.org",
    ]

    # Domains to exclude
    WEB_BLOCKED_DOMAINS: list = [
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "tiktok.com",
        "pinterest.com",
    ]

    # Redis Cache (Phase 3)
    REDIS_ENABLED: bool = False
    REDIS_HOST: Optional[str] = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"

    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]

    # Feature Flags
    FEATURE_KNOWLEDGE_GRAPH: bool = True
    FEATURE_LIVE_SEARCH: bool = True
    FEATURE_AURA_STREAMING: bool = True

    # Phase 7a Feature Flags
    PHASE_7A_AUTO_INGEST: bool = True          # Auto-ingest web research into knowledge base
    PHASE_7A_EXTRACT_ENTITIES: bool = True      # Extract entities from web content for graph
    PHASE_7A_BROADCAST_UPDATES: bool = True     # Broadcast graph updates via WebSocket
    PHASE_7A_REQUIRE_VERIFIED_CODE: bool = True # Block unverified code from ingestion

    # Graph Heatmap & Visualization (Phase 3.5)
    GRAPH_HEATMAP_ENABLED: bool = True          # Enable expertise heatmap tracking
    GRAPH_HEATMAP_DECAY_HALF_LIFE_DAYS: float = 14.0  # Days until intensity halves
    GRAPH_HEATMAP_NIGHTLY_DECAY_ENABLED: bool = True  # Run stale-node decay as nightly background task
    GRAPH_HEATMAP_NIGHTLY_DECAY_HOUR_UTC: int = 3     # 24h UTC hour for nightly decay
    GRAPH_HEATMAP_NIGHTLY_DECAY_MINUTE_UTC: int = 0   # UTC minute for nightly decay
    GRAPH_HEATMAP_DECAY_INACTIVE_DAYS: int = 7        # Decay nodes untouched for >= N days
    GRAPH_HEATMAP_DECAY_MULTIPLIER: float = 0.95      # Per-run multiplier for stale node weights
    GRAPH_HEATMAP_MIN_WEIGHT_FLOOR: float = 0.01      # Prevent weights from dropping to zero after decay
    GRAPH_RENDER_QUALITY: str = "high"          # "low", "medium", "high" - affects client-side rendering
    GRAPH_MAX_VISIBLE_NODES: int = 500          # Max nodes rendered in 3D view
    GRAPH_WEBSOCKET_BATCH_SIZE: int = 10        # Batch N node updates before broadcasting

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
