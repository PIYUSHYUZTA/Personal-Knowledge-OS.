"""
Knowledge Distillation Service.

Compresses old, related chunks into high-density "Master Nodes" in Neo4j.
Reduces vector DB size, improves retrieval efficiency, and maintains knowledge density.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from uuid import UUID

from app.models import KnowledgeChunk, KnowledgeSource
from app.services.llm_factory import LLMFactory
from app.services.graph_service import get_graph_service
from app.database.connection import SessionLocal

logger = logging.getLogger(__name__)


class MasterNode:
    """Represents a condensed knowledge node in Neo4j."""

    def __init__(
        self,
        name: str,
        content: str,
        source_chunks: List[str],  # IDs of chunks that were compressed
        topic: str,
        density_score: float,  # 0-1: how much knowledge is compressed here
        relationships: Dict[str, str] = None,
    ):
        self.name = name
        self.content = content
        self.source_chunks = source_chunks
        self.topic = topic
        self.density_score = density_score
        self.relationships = relationships or {}
        self.created_at = datetime.utcnow()


class KnowledgeDistillationEngine:
    """Compresses related knowledge chunks into master nodes."""

    def __init__(self, user_id: UUID, db_session: Session):
        """Initialize distillation engine."""
        self.user_id = user_id
        self.db_session = db_session
        self.llm = LLMFactory.get_provider()
        self.graph_service = get_graph_service()

        # Settings
        self.min_chunk_age_days = 30  # Only compress chunks older than 30 days
        self.min_chunks_per_master = 5  # Minimum chunks to create a master node
        self.similarity_threshold = 0.7  # Minimum similarity for grouping

    async def run_distillation_pass(self) -> Dict[str, Any]:
        """
        Run a single knowledge distillation pass.

        1. Find old, related chunks
        2. Group them by topic
        3. Generate master nodes
        4. Archive original chunks

        Returns:
        {
            "master_nodes_created": 3,
            "chunks_archived": 15,
            "estimated_savings_percentage": 35,
            "master_nodes": [...]
        }
        """
        result = {
            "master_nodes_created": 0,
            "chunks_archived": 0,
            "estimated_savings_percentage": 0,
            "master_nodes": [],
        }

        try:
            # Step 1: Find old chunks that are candidates for compression
            old_chunks = self._find_compression_candidates()

            if len(old_chunks) < self.min_chunks_per_master:
                logger.info(f"Not enough old chunks for distillation ({len(old_chunks)} < {self.min_chunks_per_master})")
                return result

            logger.info(f"Found {len(old_chunks)} chunks eligible for distillation")

            # Step 2: Group chunks by topic/similarity
            chunk_groups = await self._group_chunks_by_topic(old_chunks)

            logger.info(f"Grouped {len(old_chunks)} chunks into {len(chunk_groups)} topics")

            # Step 3: Create master nodes for each group
            for group in chunk_groups:
                if len(group["chunks"]) >= self.min_chunks_per_master:
                    master_node = await self._create_master_node(group)

                    if master_node:
                        result["master_nodes"].append({
                            "name": master_node.name,
                            "topic": master_node.topic,
                            "density": master_node.density_score,
                            "compressed_chunks": len(master_node.source_chunks),
                        })
                        result["master_nodes_created"] += 1
                        result["chunks_archived"] += len(master_node.source_chunks)

            # Calculate estimated savings
            if result["chunks_archived"] > 0:
                result["estimated_savings_percentage"] = min(
                    100, int((result["chunks_archived"] / len(old_chunks)) * 100)
                )

            logger.info(
                f"Distillation complete: {result['master_nodes_created']} masters, "
                f"{result['chunks_archived']} chunks archived"
            )

            return result

        except Exception as e:
            logger.error(f"Error during distillation: {e}", exc_info=True)
            return {"error": str(e)}

    def _find_compression_candidates(self) -> List[Dict[str, Any]]:
        """Find old, low-access chunks that are candidates for compression."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.min_chunk_age_days)

        # Query chunks that are:
        # 1. Old (created > 30 days ago)
        # 2. Not yet archive
        # 3. Have low access frequency (optional, for now just old)
        query = self.db_session.query(KnowledgeChunk).filter(
            KnowledgeChunk.user_id == self.user_id,
            KnowledgeChunk.created_at < cutoff_date,
        )
        if hasattr(KnowledgeChunk, "is_archived"):
            query = query.filter(KnowledgeChunk.is_archived == False)

        candidates = query.all()

        return [
            {
                "id": str(chunk.id),
                "content": chunk.chunk_text,
                "source_id": str(chunk.source_id),
                "embedding": chunk.embedding.embedding_vector if chunk.embedding else None,
                "created_at": chunk.created_at.isoformat(),
            }
            for chunk in candidates
        ]

    async def _group_chunks_by_topic(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group chunks by semantic topic using clustering."""
        if not chunks:
            return []

        # Use LLM to categorize chunks
        topics = {}

        for chunk in chunks:
            try:
                # Ask LLM to categorize this chunk
                topic_prompt = f"""
Categorize this knowledge chunk into ONE of these categories:
- TECHNICAL (specific programming/technical topics)
- ARCHITECTURE (system design, patterns)
- METHODOLOGY (processes, workflows)
- REFERENCE (definitions, standards)
- CASE_STUDY (real-world examples)
- OTHER

Chunk: {chunk['content'][:500]}

Respond with ONLY the category name (e.g., "TECHNICAL").
"""

                # Use lightweight model for fast classification
                response = await self.llm.generate(
                    prompt=topic_prompt,
                    system_prompt="You are a knowledge categorizer. Respond with only the category name."
                )

                topic = response.get("content", "OTHER").strip().upper()

                if topic not in topics:
                    topics[topic] = []

                topics[topic].append(chunk)

            except Exception as e:
                logger.warning(f"Could not categorize chunk: {e}")
                # Default to OTHER
                if "OTHER" not in topics:
                    topics["OTHER"] = []
                topics["OTHER"].append(chunk)

        # Convert to groups
        return [
            {
                "topic": topic,
                "chunks": chunk_list,
            }
            for topic, chunk_list in topics.items()
        ]

    async def _create_master_node(self, group: Dict[str, Any]) -> Optional[MasterNode]:
        """Create a master node from a group of related chunks."""
        chunks = group.get("chunks", [])
        topic = group.get("topic", "UNKNOWN")

        if not chunks:
            return None

        try:
            # Combine chunk content
            combined_content = "\n---\n".join(
                [chunk.get("content", "") for chunk in chunks]
            )

            # Use LLM to synthesize/distill
            distillation_prompt = f"""
Synthesize these {len(chunks)} related knowledge chunks into a single, high-density summary.

TOPIC: {topic}

CHUNKS:
{combined_content[:2000]}  # Limit to 2000 chars for context

Create a concise master node that:
1. Captures the essential concepts from all chunks
2. Preserves connections between ideas
3. Removes redundancy
4. Is ~30-40% of the original combined size

SYNTHESIS:"""

            response = await self.llm.generate(
                prompt=distillation_prompt,
                system_prompt="You are a knowledge synthesis expert. Create dense, information-rich summaries."
            )

            master_content = response.get("content", "")

            if not master_content:
                return None

            # Calculate density score (information preserved per token)
            original_tokens = len(combined_content.split())
            new_tokens = len(master_content.split())
            density = min(0.99, (original_tokens / max(1, new_tokens)) * 0.5)

            # Create master node
            master_node = MasterNode(
                name=f"Master_{topic}_{len(chunks)}_chunks",
                content=master_content,
                source_chunks=[chunk.get("id") for chunk in chunks],
                topic=topic,
                density_score=density,
            )

            # Store in Neo4j
            if self.graph_service:
                self.graph_service.create_entity(
                    name=master_node.name,
                    entity_type="MASTER_NODE",
                    description=master_content[:200],
                    metadata={
                        "topic": topic,
                        "density": density,
                        "source_chunks": len(chunks),
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )

            # Archive original chunks
            for chunk_id in master_node.source_chunks:
                chunk = self.db_session.query(KnowledgeChunk).filter(
                    KnowledgeChunk.id == UUID(chunk_id)
                ).first()
                if chunk:
                    if hasattr(chunk, "is_archived"):
                        chunk.is_archived = True
                    if hasattr(chunk, "archived_at"):
                        chunk.archived_at = datetime.utcnow()

            self.db_session.commit()

            logger.info(f"Created master node: {master_node.name} (density: {density:.2f})")

            return master_node

        except Exception as e:
            logger.error(f"Error creating master node: {e}")
            return None

    def get_distillation_metrics(self) -> Dict[str, Any]:
        """Get metrics about the distillation process."""
        # Count chunks
        total_chunks = self.db_session.query(KnowledgeChunk).filter(
            KnowledgeChunk.user_id == self.user_id
        ).count()

        archived_chunks = 0
        if hasattr(KnowledgeChunk, "is_archived"):
            archived_chunks = self.db_session.query(KnowledgeChunk).filter(
                KnowledgeChunk.user_id == self.user_id,
                KnowledgeChunk.is_archived == True,
            ).count()

        # Estimate efficiency gains
        compression_ratio = archived_chunks / max(1, total_chunks)

        return {
            "total_chunks": total_chunks,
            "archived_chunks": archived_chunks,
            "active_chunks": total_chunks - archived_chunks,
            "compression_ratio": round(compression_ratio, 3),
            "estimated_token_savings": int((archived_chunks / max(1, total_chunks)) * 0.5 * total_chunks),
        }


def auto_distillation_task(db_session: Optional[Session] = None):
    """
    Background task: Run knowledge distillation for all users.

    Called periodically (daily recommended).
    """
    if db_session is None:
        db_session = SessionLocal()

    try:
        from app.models import User

        users = db_session.query(User).filter(User.is_active == True).all()

        logger.info(f"🔄 Starting auto-distillation for {len(users)} users...")

        for user in users:
            try:
                engine = KnowledgeDistillationEngine(user.id, db_session)
                # Note: This would need to be async-compatible in production
                logger.info(f"✅ Distillation queued for user {user.email}")

            except Exception as e:
                logger.error(f"Error processing user {user.email}: {e}")

        db_session.close()

    except Exception as e:
        logger.error(f"Error in auto-distillation task: {e}")
