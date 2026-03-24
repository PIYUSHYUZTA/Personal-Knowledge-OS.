"""
Graph Events Broker (Phase 7a).

Event emission system for knowledge graph updates.
Enables real-time notifications when entities and relationships are added to the graph.

Pattern:
1. Services call GraphEventBroker methods when graph changes occur
2. Broker emits events to Redis pub/sub
3. WebSocket connections listen to pub/sub and broadcast to clients
4. Frontend receives real-time updates for 3D visualization
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
from uuid import UUID
from enum import Enum

logger = logging.getLogger(__name__)


class GraphEventType(str, Enum):
    """Types of graph events."""
    ENTITY_ADDED = "entity_added"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_DELETED = "entity_deleted"
    RELATIONSHIP_ADDED = "relationship_added"
    RELATIONSHIP_UPDATED = "relationship_updated"
    RELATIONSHIP_DELETED = "relationship_deleted"
    ENTITIES_MERGED = "entities_merged"
    GRAPH_REFRESHED = "graph_refreshed"


class GraphEvent:
    """Represents a graph change event."""

    def __init__(
        self,
        event_type: GraphEventType,
        user_id: UUID,
        data: Dict[str, Any],
        source: str = "graph_service",
    ):
        self.event_type = event_type
        self.user_id = user_id
        self.data = data
        self.source = source
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_id = f"{event_type}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "user_id": str(self.user_id),
            "timestamp": self.timestamp,
            "source": self.source,
            "data": self.data,
        }

    def to_json(self) -> str:
        """Serialize event to JSON."""
        return json.dumps(self.to_dict())


class GraphEventBroker:
    """
    Broker for graph change events.

    Manages event emission, subscription, and routing.
    Integrates with Redis pub/sub for distributed messaging.
    """

    # Class-level registry of event listeners (for in-process observation)
    _listeners: Dict[UUID, List[Callable]] = {}

    # Redis pub/sub manager (set during initialization)
    _redis_pubsub = None

    @classmethod
    def set_redis_pubsub(cls, redis_pubsub):
        """Register Redis pub/sub manager for event publication."""
        cls._redis_pubsub = redis_pubsub
        logger.info("GraphEventBroker connected to Redis pub/sub")

    @classmethod
    async def emit_event(cls, event: GraphEvent) -> None:
        """
        Emit a graph event to all listeners.

        Args:
            event: GraphEvent object to emit

        Publishes to:
        1. Redis pub/sub (if configured)
        2. Local listeners (synchronous callbacks)
        """
        try:
            # Log the event
            logger.debug(f"Emitting graph event: {event.event_type.value} for user {event.user_id}")

            # Publish to Redis pub/sub if available
            if cls._redis_pubsub:
                try:
                    await cls._redis_pubsub.publish("graph:updates", event.to_json())
                except Exception as e:
                    logger.error(f"Failed to publish to Redis pub/sub: {e}")

            # Notify local listeners
            if event.user_id in cls._listeners:
                for callback in cls._listeners[event.user_id]:
                    try:
                        # Handle both sync and async callbacks
                        import inspect

                        if inspect.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Error in event callback: {e}")

        except Exception as e:
            logger.error(f"Error emitting event: {e}")

    @classmethod
    async def emit_entity_added(
        cls,
        user_id: UUID,
        entity_id: str,
        entity_name: str,
        entity_type: str,
        properties: Optional[Dict[str, Any]] = None,
        source: str = "graph_service",
    ) -> None:
        """
        Emit entity_added event.

        Args:
            user_id: User who owns the entity
            entity_id: Neo4j entity ID
            entity_name: Entity name
            entity_type: Entity type (CONCEPT, TOOL, PERSON, etc.)
            properties: Additional neo4j properties
            source: Source of the event (for debugging)
        """
        event = GraphEvent(
            event_type=GraphEventType.ENTITY_ADDED,
            user_id=user_id,
            data={
                "entity_id": entity_id,
                "entity_name": entity_name,
                "entity_type": entity_type,
                "properties": properties or {},
            },
            source=source,
        )
        await cls.emit_event(event)

    @classmethod
    async def emit_relationship_added(
        cls,
        user_id: UUID,
        source_entity_id: str,
        source_entity_name: str,
        target_entity_id: str,
        target_entity_name: str,
        relationship_type: str,
        weight: float = 1.0,
        source: str = "graph_service",
    ) -> None:
        """
        Emit relationship_added event.

        Args:
            user_id: User who owns the relationship
            source_entity_id: Source entity Neo4j ID
            source_entity_name: Source entity name
            target_entity_id: Target entity Neo4j ID
            target_entity_name: Target entity name
            relationship_type: Type of relationship
            weight: Relationship strength
            source: Source of the event
        """
        event = GraphEvent(
            event_type=GraphEventType.RELATIONSHIP_ADDED,
            user_id=user_id,
            data={
                "source_entity_id": source_entity_id,
                "source_entity_name": source_entity_name,
                "target_entity_id": target_entity_id,
                "target_entity_name": target_entity_name,
                "relationship_type": relationship_type,
                "weight": weight,
            },
            source=source,
        )
        await cls.emit_event(event)

    @classmethod
    async def emit_entities_merged(
        cls,
        user_id: UUID,
        primary_entity_id: str,
        primary_entity_name: str,
        merged_entity_ids: List[str],
        merged_entity_names: List[str],
        source: str = "graph_service",
    ) -> None:
        """
        Emit entities_merged event (deduplication).

        Args:
            user_id: User who owns the entities
            primary_entity_id: Primary entity that remains
            primary_entity_name: Primary entity name
            merged_entity_ids: IDs of merged entities
            merged_entity_names: Names of merged entities
            source: Source of the event
        """
        event = GraphEvent(
            event_type=GraphEventType.ENTITIES_MERGED,
            user_id=user_id,
            data={
                "primary_entity_id": primary_entity_id,
                "primary_entity_name": primary_entity_name,
                "merged_entity_ids": merged_entity_ids,
                "merged_entity_names": merged_entity_names,
            },
            source=source,
        )
        await cls.emit_event(event)

    @classmethod
    def subscribe(cls, user_id: UUID, callback: Callable) -> str:
        """
        Subscribe a callback to graph events for a user.

        Args:
            user_id: User to track events for
            callback: Function to call when event occurs

        Returns:
            Subscription ID (for unsubscribing)
        """
        if user_id not in cls._listeners:
            cls._listeners[user_id] = []

        cls._listeners[user_id].append(callback)
        logger.debug(f"Added event listener for user {user_id}")

        return f"subscription_{user_id}_{len(cls._listeners[user_id])}"

    @classmethod
    def unsubscribe(cls, user_id: UUID, callback: Callable) -> None:
        """
        Unsubscribe a callback.

        Args:
            user_id: User
            callback: Callback to remove
        """
        if user_id in cls._listeners:
            try:
                cls._listeners[user_id].remove(callback)
                logger.debug(f"Removed event listener for user {user_id}")
            except ValueError:
                pass

    @classmethod
    def get_listener_count(cls, user_id: Optional[UUID] = None) -> int:
        """Get number of active listeners."""
        if user_id:
            return len(cls._listeners.get(user_id, []))
        return sum(len(listeners) for listeners in cls._listeners.values())
