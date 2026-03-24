"""
Query Analytics Service.

Tracks which knowledge areas are queried most frequently.
Used to generate expertise heatmaps in the 3D UI.
Phase 7a/3.5: Adds interaction hit tracking and knowledge decay for heatmap intensity.
"""

from typing import Dict, Any, List, Optional
import logging
import math
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from uuid import UUID
from collections import defaultdict

from app.config import settings
from app.models import User, ConversationHistory
from app.services.graph_service import get_graph_service

logger = logging.getLogger(__name__)

# Phase 3.5: Knowledge decay half-life in days
# After this many days without interaction, a node's intensity drops by 50%
DECAY_HALF_LIFE_DAYS = 14


class InteractionTracker:
    """
    Tracks concept interaction hits for heatmap intensity.

    Every time a concept is retrieved in search or referenced in a query,
    its hit count increments. A decay factor reduces intensity for stale nodes.
    """

    # In-memory interaction store keyed by (user_id, concept_name)
    _hits: Dict[str, Dict[str, "InteractionRecord"]] = {}

    @classmethod
    def record_hit(cls, user_id: UUID, concept_name: str, hit_weight: float = 1.0) -> None:
        """
        Record an interaction hit for a concept.

        Args:
            user_id: User who interacted
            concept_name: Concept name (lowercased)
            hit_weight: Weight of the hit (search retrieval=1.0, UI click=0.5)
        """
        key = str(user_id)
        concept = concept_name.lower()

        if key not in cls._hits:
            cls._hits[key] = {}

        if concept not in cls._hits[key]:
            cls._hits[key][concept] = InteractionRecord(concept)

        cls._hits[key][concept].add_hit(hit_weight)

    @classmethod
    def get_intensity(
        cls,
        user_id: UUID,
        concept_name: str,
        half_life_days: float = DECAY_HALF_LIFE_DAYS,
    ) -> float:
        """
        Get the decayed intensity for a concept (0.0 to 1.0).

        Applies exponential decay based on time since last interaction.
        """
        key = str(user_id)
        concept = concept_name.lower()

        record = cls._hits.get(key, {}).get(concept)
        if not record:
            return 0.0

        return record.get_decayed_intensity(half_life_days)

    @classmethod
    def get_all_intensities(
        cls,
        user_id: UUID,
        half_life_days: float = DECAY_HALF_LIFE_DAYS,
    ) -> Dict[str, float]:
        """Get decayed intensities for all concepts of a user."""
        key = str(user_id)
        records = cls._hits.get(key, {})

        return {
            concept: record.get_decayed_intensity(half_life_days)
            for concept, record in records.items()
        }

    @classmethod
    def get_all_records(cls, user_id: UUID) -> Dict[str, Dict[str, Any]]:
        """Get all interaction records for a user (for API responses)."""
        key = str(user_id)
        records = cls._hits.get(key, {})

        return {
            concept: record.to_dict()
            for concept, record in records.items()
        }

    @classmethod
    def clear_user(cls, user_id: UUID) -> None:
        """Clear all interaction data for a user."""
        key = str(user_id)
        cls._hits.pop(key, None)


class InteractionRecord:
    """Single concept's interaction history."""

    def __init__(self, concept_name: str):
        self.concept_name = concept_name
        self.total_hits: float = 0.0
        self.hit_count: int = 0
        self.first_seen: datetime = datetime.now(timezone.utc)
        self.last_seen: datetime = datetime.now(timezone.utc)

    def add_hit(self, weight: float = 1.0) -> None:
        """Add an interaction hit."""
        self.total_hits += weight
        self.hit_count += 1
        self.last_seen = datetime.now(timezone.utc)

    def get_decayed_intensity(self, half_life_days: float = DECAY_HALF_LIFE_DAYS) -> float:
        """
        Get intensity with exponential decay applied.

        Formula: intensity = raw_score * 2^(-days_since_last / half_life)
        """
        now = datetime.now(timezone.utc)
        days_since_last = (now - self.last_seen).total_seconds() / 86400.0

        # Raw score: log-scaled hit count (prevents runaway values)
        raw_score = math.log1p(self.total_hits) / math.log1p(50)  # Normalize around 50 hits
        raw_score = min(1.0, raw_score)

        # Apply exponential decay
        decay_factor = math.pow(2, -days_since_last / max(half_life_days, 0.01))

        return round(raw_score * decay_factor, 4)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "concept": self.concept_name,
            "total_hits": self.total_hits,
            "hit_count": self.hit_count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "current_intensity": self.get_decayed_intensity(),
        }


class QueryAnalytics:
    """Tracks and analyzes query patterns for expertise detection."""

    def __init__(self, user_id: UUID, db_session: Session):
        """Initialize query analytics."""
        self.user_id = user_id
        self.db_session = db_session
        self.graph_service = get_graph_service()
        self.query_cache: Dict[str, int] = defaultdict(int)

    def track_query(self, query: str, response_text: str):
        """
        Track a query and its response.

        Analyzes which concepts/entities were involved in the response.
        Records interaction hits for heatmap intensity (Phase 3.5).
        """
        try:
            # Extract key concepts from query + response
            concepts = self._extract_query_concepts(query, response_text)

            for concept in concepts:
                self.query_cache[concept] += 1
                # Phase 3.5: Record interaction hit for heatmap decay tracking
                InteractionTracker.record_hit(self.user_id, concept, hit_weight=1.0)
                logger.debug(f"Tracked concept: {concept}")

        except Exception as e:
            logger.warning(f"Error tracking query: {e}")

    def _extract_query_concepts(self, query: str, response: str) -> List[str]:
        """Extract concept mentions from query and response."""
        # Simple implementation: look for known entities
        concepts = []

        combined = f"{query} {response}".lower()

        # Look for common concept patterns
        # In production, this would use spaCy NER or LLM
        keywords = [
            "database",
            "api",
            "architecture",
            "security",
            "performance",
            "optimization",
            "testing",
            "deployment",
            "authentication",
            "caching",
            "scaling",
            "monitoring",
        ]

        for keyword in keywords:
            if keyword in combined:
                concepts.append(keyword)

        return list(set(concepts))

    def get_query_heatmap(self, days: int = 30) -> Dict[str, Any]:
        """
        Get query frequency heatmap for the past N days.

        Returns data for 3D visualization: concept -> frequency score (0-1).
        Phase 3.5: Integrates decay-based intensities from InteractionTracker.
        """
        try:
            if not self.graph_service:
                return {"nodes": [], "max_frequency": 0}

            # Get entities from graph
            cypher = """
            MATCH (e:Entity {user_id: $user_id})
            RETURN e.name as name, e.type as type
            LIMIT 100
            """

            entities = self.graph_service.execute_query(cypher) or []

            # Get query history from database
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            conversations = self.db_session.query(ConversationHistory).filter(
                ConversationHistory.user_id == self.user_id,
                ConversationHistory.created_at >= cutoff_date,
            ).all()

            # Count mentions
            mention_counts: Dict[str, int] = defaultdict(int)

            for conv in conversations:
                query_text = (conv.user_query or "").lower()
                response_text = (conv.assistant_response or "").lower()
                combined = f"{query_text} {response_text}"

                for entity in entities:
                    entity_name = (entity.get("name") or "").lower()
                    if entity_name and entity_name in combined:
                        mention_counts[entity_name] += 1

            if not mention_counts:
                return {"nodes": [], "max_frequency": 0}

            # Normalize to 0-1 scale
            max_freq = max(mention_counts.values())

            # Phase 3.5: Get decay-based intensities
            decay_intensities = InteractionTracker.get_all_intensities(self.user_id)

            nodes = []

            for entity_name, count in mention_counts.items():
                frequency_score = count / max(1, max_freq)

                # Phase 3.5: Blend frequency score with decay intensity
                decay_intensity = decay_intensities.get(entity_name, 0.0)
                # Weighted blend: 60% frequency, 40% decay-based recency
                blended_intensity = (0.6 * frequency_score) + (0.4 * decay_intensity)
                blended_intensity = min(1.0, blended_intensity)

                # Phase 3.5: Color grading based on intensity
                if blended_intensity > 0.7:
                    glow_tier = "hot"       # Bright White/Neon - core expertise
                    glow_color = "#ffffff"
                elif blended_intensity > 0.4:
                    glow_tier = "warm"      # Cyan/Neutral - moderate
                    glow_color = "#00e5ff"
                else:
                    glow_tier = "cold"      # Blue/Cold - new or rarely accessed
                    glow_color = "#2979ff"

                nodes.append({
                    "name": entity_name,
                    "frequency": count,
                    "heatmap_value": round(blended_intensity, 3),
                    "decay_intensity": round(decay_intensity, 3),
                    "glow_tier": glow_tier,
                    "glow_color": glow_color,
                    "intensity": "high" if blended_intensity > 0.7 else "medium" if blended_intensity > 0.3 else "low",
                })

            # Sort by frequency
            nodes = sorted(nodes, key=lambda x: x["frequency"], reverse=True)

            return {
                "nodes": nodes,
                "max_frequency": max_freq,
                "total_mentions": sum(mention_counts.values()),
                "unique_concepts": len(mention_counts),
                "heatmap_type": "expertise",
            }

        except Exception as e:
            logger.error(f"Error generating heatmap: {e}")
            return {"nodes": [], "max_frequency": 0}

    def get_expertise_clusters(self) -> List[Dict[str, Any]]:
        """
        Identify clusters of related expertise.

        Returns groups of concepts that are frequently queried together.
        """
        try:
            if not self.graph_service:
                return []

            # Use Neo4j to find connected entities
            cypher = """
            MATCH (e1:Entity {user_id: $user_id})-[r:RELATES_TO|IMPLEMENTS|DEPENDS_ON]-(e2:Entity {user_id: $user_id})
            WITH e1, e2, count(r) as strength
            WHERE strength > 1
            RETURN e1.name as concept1, e2.name as concept2, strength
            LIMIT 50
            """

            relationships = self.graph_service.execute_query(cypher) or []

            # Build clusters from relationships
            clusters = self._group_related_concepts(relationships)

            return clusters

        except Exception as e:
            logger.error(f"Error identifying expertise clusters: {e}")
            return []

    def _group_related_concepts(self, relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group related concepts into clusters."""
        clusters = defaultdict(set)

        for rel in relationships:
            c1 = rel.get("concept1")
            c2 = rel.get("concept2")

            # Simple clustering: add to same cluster if connected
            clusters[c1].add(c2)
            clusters[c2].add(c1)

        # Convert to list
        cluster_list = []
        seen = set()

        for concept, related in clusters.items():
            if concept not in seen:
                cluster = {
                    "primary": concept,
                    "related": list(related),
                    "size": len(related) + 1,
                }
                cluster_list.append(cluster)
                seen.update(related)

        return sorted(cluster_list, key=lambda x: x["size"], reverse=True)

    def get_expertise_summary(self) -> Dict[str, Any]:
        """Get summary of user's expertise areas based on query patterns."""
        heatmap = self.get_query_heatmap(days=30)
        clusters = self.get_expertise_clusters()

        # Extract top expertise areas
        top_expertise = heatmap.get("nodes", [])[:10]

        return {
            "expertise_areas": [
                {
                    "name": exp.get("name"),
                    "confidence": exp.get("heatmap_value", 0),
                    "mentions": exp.get("frequency", 0),
                }
                for exp in top_expertise
            ],
            "expertise_clusters": clusters[:5],
            "heatmap_data": heatmap,
            "total_queries_analyzed": heatmap.get("total_mentions", 0),
        }


# Global analytics instance cache
_analytics_cache: Dict[str, QueryAnalytics] = {}


def get_query_analytics(user_id: UUID, db_session: Session) -> QueryAnalytics:
    """Get or create query analytics for a user."""
    key = str(user_id)
    if key not in _analytics_cache:
        _analytics_cache[key] = QueryAnalytics(user_id, db_session)
    return _analytics_cache[key]
