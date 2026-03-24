"""
Pydantic schemas for API request/response validation.
Separates data validation from business logic.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

# ============================================================================
# AUTH SCHEMAS
# ============================================================================

class UserCreate(BaseModel):
    """Request to create a new user account."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    """Request to login."""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """User data returned in responses."""
    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    profile_picture: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    """JWT token response after login."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds

class SessionResponse(BaseModel):
    """Session information."""
    id: UUID
    user_id: UUID
    created_at: datetime
    expires_at: datetime

# ============================================================================
# KNOWLEDGE SOURCE SCHEMAS
# ============================================================================

class KnowledgeSourceCreate(BaseModel):
    """Request to register a knowledge source."""
    file_name: str
    source_type: str  # "pdf", "text", "markdown", "code"
    metadata: Optional[Dict[str, Any]] = None

class KnowledgeSourceResponse(BaseModel):
    """Knowledge source in responses."""
    id: UUID
    file_name: str
    source_type: str
    file_size: Optional[int]
    chunks_count: int
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias="metadata_")
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# KNOWLEDGE CHUNK & EMBEDDING SCHEMAS
# ============================================================================

class KnowledgeChunkCreate(BaseModel):
    """Internal schema for creating chunks."""
    source_id: UUID
    chunk_text: str
    chunk_index: int
    metadata: Optional[Dict[str, Any]] = None

class KnowledgeChunkResponse(BaseModel):
    """Knowledge chunk in responses."""
    id: UUID
    source_id: UUID
    chunk_text: str
    chunk_index: int
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias="metadata_")
    created_at: datetime

    class Config:
        from_attributes = True

class SearchResult(BaseModel):
    """Single search result from semantic search."""
    chunk_id: UUID
    source_id: UUID
    file_name: str
    chunk_text: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]]

class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str = Field(..., min_length=3)
    top_k: int = Field(5, ge=1, le=50)
    min_similarity: float = Field(0.3, ge=0.0, le=1.0)

class SearchResponse(BaseModel):
    """Response with search results."""
    query: str
    results: List[SearchResult]
    total_results: int

# ============================================================================
# FILE INGESTION SCHEMAS
# ============================================================================

class IngestionRequest(BaseModel):
    """Request to ingest a file."""
    file_name: str
    source_type: str  # "pdf", "text", etc.
    chunk_size: Optional[int] = 512
    chunk_overlap: Optional[int] = 50

class IngestionProgress(BaseModel):
    """Real-time ingestion progress."""
    file_name: str
    status: str  # "processing", "embedding", "storing", "complete", "error"
    progress_percent: int = Field(..., ge=0, le=100)
    chunks_processed: int
    total_chunks: Optional[int]
    error_message: Optional[str] = None

class IngestionResponse(BaseModel):
    """Response after ingestion complete."""
    source_id: UUID
    file_name: str
    chunks_created: int
    embeddings_created: int
    status: str

# ============================================================================
# AURA - DUAL PERSONA SCHEMAS
# ============================================================================

class AuraQuery(BaseModel):
    """Query sent to AURA."""
    message: str = Field(..., min_length=1)
    context_window: Optional[int] = 5
    include_sources: bool = True

class AuraMessageResponse(BaseModel):
    """Single message in conversation."""
    id: UUID
    user_message: str
    aura_response: str
    persona_used: str  # "advisor" or "friend"
    retrieved_knowledge: List[SearchResult]
    confidence_score: float
    created_at: datetime

    class Config:
        from_attributes = True

class AuraStateResponse(BaseModel):
    """Current AURA state."""
    id: UUID
    current_persona: str
    context_window: int
    latest_message: Optional[AuraMessageResponse]

# ============================================================================
# KNOWLEDGE GRAPH SCHEMAS
# ============================================================================

class GraphEntityResponse(BaseModel):
    """Entity in knowledge graph."""
    id: UUID
    entity_name: str
    entity_type: str
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias="metadata_")

    class Config:
        from_attributes = True

class GraphRelationshipResponse(BaseModel):
    """Relationship between entities."""
    id: UUID
    source_entity: GraphEntityResponse
    target_entity: GraphEntityResponse
    relationship_type: str
    weight: float

    class Config:
        from_attributes = True

class GraphDataResponse(BaseModel):
    """Complete graph data for visualization."""
    entities: List[GraphEntityResponse]
    relationships: List[GraphRelationshipResponse]

# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# ============================================================================
# CODE SANDBOX EXECUTION SCHEMAS (Phase 6a)
# ============================================================================

class CodeExecutionRequest(BaseModel):
    """Request to execute Python code in sandbox."""
    code: str = Field(..., min_length=1, max_length=10000)
    timeout_seconds: Optional[int] = Field(30, ge=1, le=120)
    include_in_knowledge_base: bool = Field(False)

    class Config:
        json_schema_extra = {
            "example": {
                "code": "import numpy as np\nresult = np.array([1, 2, 3]).sum()\nprint(result)",
                "timeout_seconds": 30,
                "include_in_knowledge_base": False,
            }
        }

class ExecutionStartedResponse(BaseModel):
    """Response when execution is queued."""
    execution_id: UUID
    status: str = "queued"
    message: str = "Code execution queued"
    created_at: datetime

class CodeValidationResponse(BaseModel):
    """Response from code validation endpoint."""
    safe_to_execute: bool
    blocked_modules: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class ExecutionResultResponse(BaseModel):
    """Result of code execution."""
    execution_id: UUID
    status: str  # "success", "error", "timeout"
    input_code: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    execution_duration_ms: Optional[int] = None
    memory_peak_mb: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ExecutionListResponse(BaseModel):
    """Execution record in list response."""
    id: UUID
    status: str
    execution_duration_ms: Optional[int]
    memory_peak_mb: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# WEB RESEARCH SCHEMAS (Phase 7a)
# ============================================================================

class ResearchRequest(BaseModel):
    """Request to research a URL and extract content."""
    url: str = Field(..., min_length=10, max_length=2000)
    extract_code: bool = Field(True)
    validate_code: bool = Field(True)
    custom_selector: Optional[str] = Field(None)  # CSS selector for content extraction

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://react.dev/learn",
                "extract_code": True,
                "validate_code": True,
                "custom_selector": None,
            }
        }

class ResearchResponse(BaseModel):
    """Response from research operation."""
    web_content_id: UUID
    url: str
    title: Optional[str] = None
    status: str  # "complete", "error"
    chunks_created: int = 0
    codes_found: int = 0
    codes_validated: int = 0
    knowledge_source_id: Optional[UUID] = None
    created_at: datetime

class WebContentResponse(BaseModel):
    """Web content metadata and extraction details."""
    id: UUID
    source_url: str
    title: Optional[str] = None
    domain: Optional[str] = None
    status: str
    codes_validated: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime

    class Config:
        from_attributes = True

class CodeSnippetResponse(BaseModel):
    """Extracted and validated code snippet."""
    language: str
    code: str
    valid: bool
    index: int
    error: Optional[str] = None

