"""
SQLAlchemy ORM models for PKOS.
These define the data structure for all relational tables.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON, Enum, Boolean, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum

from app.database.connection import Base

# ============================================================================
# ENUMS
# ============================================================================

class SourceType(str, enum.Enum):
    """Types of knowledge sources."""
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"
    DOCUMENT = "document"
    WEB = "web"
    CODE = "code"

class PersonaType(str, enum.Enum):
    """AURA dual-persona types."""
    ADVISOR = "advisor"  # Technical, cold, efficient
    FRIEND = "friend"    # Empathetic, conversational, warm

class ExecutionStatus(str, enum.Enum):
    """Code sandbox execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"

class VerificationStatus(str, enum.Enum):
    """Code snippet verification status (Phase 6a sandbox)."""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    PENDING = "pending"

# ============================================================================
# USER & AUTHENTICATION
# ============================================================================

class User(Base):
    """User account and profile."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    profile_picture = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    knowledge_sources = relationship("KnowledgeSource", back_populates="user", cascade="all, delete-orphan")
    knowledge_chunks = relationship("KnowledgeChunk", back_populates="user", cascade="all, delete-orphan")
    knowledge_embeddings = relationship("KnowledgeEmbedding", back_populates="user", cascade="all, delete-orphan")
    aura_state = relationship("AuraState", back_populates="user", uselist=False, cascade="all, delete-orphan")
    conversation_history = relationship("ConversationHistory", back_populates="user", cascade="all, delete-orphan")
    graph_entities = relationship("GraphEntity", back_populates="user", cascade="all, delete-orphan")
    graph_relationships = relationship("GraphRelationship", back_populates="user", cascade="all, delete-orphan")
    execution_results = relationship("ExecutionResult", back_populates="user", cascade="all, delete-orphan")
    web_contents = relationship("WebContent", back_populates="user", cascade="all, delete-orphan")

class Session(Base):
    """User authentication sessions with MPC handshake."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token = Column(String(2000), unique=True, nullable=False)
    mpc_handshake_hash = Column(String(512), nullable=True)  # Hash of MPC secure exchange
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

# ============================================================================
# KNOWLEDGE & EMBEDDINGS
# ============================================================================

class KnowledgeSource(Base):
    """Top-level source (PDF, text file, URL, etc.)."""
    __tablename__ = "knowledge_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    file_name = Column(String(500), nullable=False)
    source_type = Column(Enum(SourceType), default=SourceType.PDF)
    file_size = Column(Integer, nullable=True)  # bytes
    chunks_count = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, default={})  # author, date, tags, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="knowledge_sources")
    chunks = relationship("KnowledgeChunk", back_populates="source", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    """Semantic chunks of knowledge (sections, paragraphs, entities)."""
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("knowledge_sources.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in source
    metadata_ = Column("metadata", JSON, default={})  # page_number, section_title, tags, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    source = relationship("KnowledgeSource", back_populates="chunks")
    user = relationship("User", back_populates="knowledge_chunks")
    embedding = relationship("KnowledgeEmbedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan")

class KnowledgeEmbedding(Base):
    """Vector embeddings for semantic search (pgvector)."""
    __tablename__ = "knowledge_embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String(36), ForeignKey("knowledge_chunks.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    # Vector stored as LargeBinary (serialized), pgvector extension handles it
    embedding_vector = Column(LargeBinary, nullable=False)  # 384-dim for all-MiniLM-L6-v2
    model_version = Column(String(100), default="sentence-transformers/all-MiniLM-L6-v2")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    chunk = relationship("KnowledgeChunk", back_populates="embedding")
    user = relationship("User", back_populates="knowledge_embeddings")

# ============================================================================
# AURA - DUAL PERSONA AI
# ============================================================================

class AuraState(Base):
    """AURA persona and conversation state."""
    __tablename__ = "aura_state"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    current_persona = Column(Enum(PersonaType), default=PersonaType.ADVISOR)
    context_window = Column(Integer, default=5)  # Number of recent messages to consider
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="aura_state")
    conversation_history = relationship("ConversationHistory", back_populates="aura_state", cascade="all, delete-orphan")

class ConversationHistory(Base):
    """Conversation history with AURA."""
    __tablename__ = "conversation_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    aura_state_id = Column(String(36), ForeignKey("aura_state.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    user_message = Column(Text, nullable=False)
    aura_response = Column(Text, nullable=False)
    persona_used = Column(Enum(PersonaType), nullable=False)
    retrieved_knowledge_ids = Column(JSON, default=[])  # Array of chunk IDs used
    confidence_score = Column(Float, default=0.0)  # How confident was AURA
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    aura_state = relationship("AuraState", back_populates="conversation_history")
    user = relationship("User", back_populates="conversation_history")

# ============================================================================
# KNOWLEDGE GRAPH
# ============================================================================

class GraphEntity(Base):
    """Named entities in the knowledge graph (people, places, concepts)."""
    __tablename__ = "graph_entities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    entity_name = Column(String(500), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False)  # PERSON, PLACE, CONCEPT, TOOL, etc.
    metadata_ = Column("metadata", JSON, default={})  # description, aliases, references
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Heatmap tracking (Phase 3.5)
    weight = Column(Float, default=0.0, nullable=False)          # Cumulative interaction-hit score
    last_accessed_at = Column(DateTime, nullable=True)  # Timestamp of last hit (for decay)

    # Relationships
    user = relationship("User", back_populates="graph_entities")
    relationships_from = relationship(
        "GraphRelationship",
        foreign_keys="GraphRelationship.source_entity_id",
        back_populates="source_entity"
    )
    relationships_to = relationship(
        "GraphRelationship",
        foreign_keys="GraphRelationship.target_entity_id",
        back_populates="target_entity"
    )

class GraphRelationship(Base):
    """Relationships between entities in the knowledge graph."""
    __tablename__ = "graph_relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    source_entity_id = Column(String(36), ForeignKey("graph_entities.id"), nullable=False)
    target_entity_id = Column(String(36), ForeignKey("graph_entities.id"), nullable=False)
    relationship_type = Column(String(100), nullable=False)  # "mentions", "extends", "contradicts", etc.
    weight = Column(Float, default=1.0)  # Relationship strength
    metadata_ = Column("metadata", JSON, default={})  # context, source chunks, etc.
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="graph_relationships")
    source_entity = relationship(
        "GraphEntity",
        foreign_keys=[source_entity_id],
        back_populates="relationships_from"
    )
    target_entity = relationship(
        "GraphEntity",
        foreign_keys=[target_entity_id],
        back_populates="relationships_to"
    )

# ============================================================================
# CODE SANDBOX EXECUTION
# ============================================================================

class ExecutionResult(Base):
    """Sandbox execution history and results (Phase 6a: Python-only)."""
    __tablename__ = "execution_results"

    # Identity & relationships
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(String(36), ForeignKey("conversation_history.id"), nullable=True)

    # Code (Python-only in Phase 6a)
    input_code = Column(Text, nullable=False)

    # Execution timeline
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    execution_duration_ms = Column(Integer, nullable=True)

    # Results
    status = Column(String(20), nullable=False, index=True)  # "success", "error", "timeout"
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)

    # Resources
    memory_peak_mb = Column(Float, nullable=True)

    # Metadata
    timeout_seconds = Column(Integer, nullable=True)
    in_knowledge_base = Column(Boolean, default=False)  # Was it ingested?
    knowledge_chunk_id = Column(String(36), nullable=True)  # Link to KB chunk
    metadata_ = Column("metadata", JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="execution_results")
    conversation = relationship("ConversationHistory")

# ============================================================================
# WEB CONTENT & RESEARCH (Phase 7a)
# ============================================================================

class WebContent(Base):
    """Ingested web content from research operations."""
    __tablename__ = "web_content"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # URL tracking
    source_url = Column(String(2000), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, unique=True)  # SHA256 of content

    # Content metadata
    title = Column(String(500), nullable=True)
    domain = Column(String(255), nullable=True)  # "docs.python.org"

    # Phase 7a: Extracted content storage
    content_text = Column(Text, nullable=True)  # Full extracted text from page
    code_blocks_json = Column(JSON, default=[])  # Array of extracted code blocks with validation status

    # Phase 7a: Code verification status
    verification_status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING, index=True)
    unverified_codes = Column(JSON, default=[])  # Array of failed code snippets with error reasons

    # Metadata - stores fetch/extraction details
    metadata_ = Column("metadata", JSON, default={})
    # Example fields:
    # {
    #     "fetch_timestamp": "2026-03-11T14:30:00Z",
    #     "status_code": 200,
    #     "content_type": "text/html",
    #     "final_url": "redirected_url",
    #     "parser": "BeautifulSoup4",
    #     "extraction_method": "css_selector",
    #     "character_count": 5000,
    #     "language": "en",
    #     "encoding": "utf-8",
    #     "error_message": null,
    #     "trigger_type": "manual"  # "manual" or "automatic"
    # }

    # Knowledge integration
    source_id = Column(String(36), ForeignKey("knowledge_sources.id"), nullable=True)
    knowledge_source = relationship("KnowledgeSource")

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="web_contents")


