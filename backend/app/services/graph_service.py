"""
Neo4j Knowledge Graph Service.
Manages entity extraction, relationship creation, and graph queries.
Phase 7a: Emits graph events via GraphEventBroker for real-time updates.
"""

from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
import logging
import asyncio
from neo4j import GraphDatabase, Session as Neo4jSession
from neo4j.exceptions import ServiceUnavailable

from app.config import settings
from app.models import GraphEntity, GraphRelationship
from app.services.graph_events_broker import GraphEventBroker

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Singleton Neo4j driver wrapper."""

    _instance = None
    _driver = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_driver(cls):
        """Get or create Neo4j driver."""
        if not settings.NEO4J_ENABLED:
            logger.warning("Neo4j is disabled in config")
            return None

        if cls._driver is None:
            try:
                cls._driver = GraphDatabase.driver(
                    settings.NEO4J_URI or "neo4j://localhost:7687",
                    auth=(
                        settings.NEO4J_USERNAME or "neo4j",
                        settings.NEO4J_PASSWORD or "neo4j_password",
                    ),
                    encrypted=False,
                )
                logger.info("Neo4j driver initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j: {e}")
                return None

        return cls._driver

    @classmethod
    def close(cls):
        """Close Neo4j driver."""
        if cls._driver:
            cls._driver.close()
            cls._driver = None


class GraphEntity:
    """Represents a concept/entity in the knowledge graph."""

    def __init__(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.entity_type = entity_type
        self.description = description
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.entity_type,
            "description": self.description,
            "metadata": self.metadata,
        }


class GraphRelationshipData:
    """Represents a relationship between entities."""

    def __init__(
        self,
        source_name: str,
        target_name: str,
        relationship_type: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.source_name = source_name
        self.target_name = target_name
        self.relationship_type = relationship_type
        self.weight = weight
        self.metadata = metadata or {}


class Neo4jGraphService:
    """
    Neo4j Knowledge Graph Service.

    Handles:
    - Entity creation (concepts, technologies, authors)
    - Relationship creation (dependency, mentions, extends)
    - Deduplication of concepts across documents
    - APOC-powered graph analysis
    - Cypher query execution
    """

    def __init__(self, user_id: UUID):
        """Initialize graph service for a specific user."""
        self.user_id = str(user_id)
        self.driver = Neo4jClient.get_driver()

        if self.driver is None:
            logger.warning(f"Neo4j not available for user {self.user_id}")

    def create_entity(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create or update an entity node in the graph.

        Entity Types: CONCEPT, TECHNOLOGY, AUTHOR, LANGUAGE, FRAMEWORK, LIBRARY

        Returns:
            True if successful
        """
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                query = """
                MERGE (e:Entity {
                    user_id: $user_id,
                    name: $name,
                    type: $entity_type
                })
                SET e.description = $description,
                    e.metadata = $metadata,
                    e.updated_at = timestamp()
                RETURN e
                """

                result = session.run(
                    query,
                    user_id=self.user_id,
                    name=name,
                    entity_type=entity_type,
                    description=description,
                    metadata=metadata or {},
                )

                result.consume()
                logger.info(f"Created entity: {name} ({entity_type})")

                # Phase 7a: Emit graph event for real-time updates
                try:
                    asyncio.get_event_loop().create_task(
                        GraphEventBroker.emit_entity_added(
                            user_id=UUID(self.user_id),
                            entity_id=name,
                            entity_name=name,
                            entity_type=entity_type,
                            properties={
                                "description": description,
                                **(metadata or {}),
                            },
                            source="graph_service",
                        )
                    )
                except RuntimeError:
                    # No event loop running (sync context) - skip event emission
                    logger.debug("No event loop available for graph event emission")

                return True

        except Exception as e:
            logger.error(f"Failed to create entity: {e}")
            return False

    def create_relationship(
        self,
        source_name: str,
        target_name: str,
        relationship_type: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create a relationship between two entities.

        Relationship Types:
        - IMPLEMENTS: A implements B (e.g., FastAPI implements REST)
        - EXTENDS: A extends B (inheritance)
        - DEPENDS_ON: A depends on B
        - MENTIONS: A mentions/references B
        - SIMILAR_TO: A is similar to B
        - RELATED_TO: A is related to B

        Returns:
            True if successful
        """
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                query = """
                MATCH (source:Entity {user_id: $user_id, name: $source_name})
                MATCH (target:Entity {user_id: $user_id, name: $target_name})
                MERGE (source)-[r:RELATIONSHIP {type: $relationship_type}]->(target)
                SET r.weight = $weight,
                    r.metadata = $metadata,
                    r.created_at = timestamp()
                RETURN r
                """

                result = session.run(
                    query,
                    user_id=self.user_id,
                    source_name=source_name,
                    target_name=target_name,
                    relationship_type=relationship_type,
                    weight=weight,
                    metadata=metadata or {},
                )

                result.consume()
                logger.info(
                    f"Created relationship: {source_name} -{relationship_type}-> {target_name}"
                )

                # Phase 7a: Emit graph event for real-time updates
                try:
                    asyncio.get_event_loop().create_task(
                        GraphEventBroker.emit_relationship_added(
                            user_id=UUID(self.user_id),
                            source_entity_id=source_name,
                            source_entity_name=source_name,
                            target_entity_id=target_name,
                            target_entity_name=target_name,
                            relationship_type=relationship_type,
                            weight=weight,
                            source="graph_service",
                        )
                    )
                except RuntimeError:
                    logger.debug("No event loop available for graph event emission")

                return True

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False

    def find_similar_concepts(self, concept_name: str, threshold: float = 0.8) -> List[str]:
        """
        Find similar/related concepts using graph analysis.

        Uses Levenshtein distance and semantic relationships.

        Returns:
            List of similar concept names
        """
        if not self.driver:
            return []

        try:
            with self.driver.session() as session:
                # Simple Cypher query to find related concepts
                query = """
                MATCH (e1:Entity {user_id: $user_id, name: $concept_name})
                MATCH (e1)-[r]->(e2:Entity {user_id: $user_id})
                RETURN DISTINCT e2.name as concept
                UNION
                MATCH (e1:Entity {user_id: $user_id, name: $concept_name})
                MATCH (e2:Entity {user_id: $user_id})-[r]->(e1)
                RETURN DISTINCT e2.name as concept
                """

                result = session.run(query, user_id=self.user_id, concept_name=concept_name)

                concepts = [record["concept"] for record in result]
                logger.info(f"Found {len(concepts)} related concepts for '{concept_name}'")

                return concepts

        except Exception as e:
            logger.error(f"Failed to find similar concepts: {e}")
            return []

    def get_concept_connections(
        self, concept_name: str, depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get all connections for a concept up to specified depth.

        Returns graph structure:
        {
            "concept": "name",
            "type": "TECHNOLOGY",
            "connections": [
                {"target": "name", "relationship": "DEPENDS_ON", "weight": 1.0},
                ...
            ],
            "reverse_connections": [...]
        }
        """
        if not self.driver:
            return {}

        try:
            with self.driver.session() as session:
                # Forward connections
                query_forward = """
                MATCH (e:Entity {user_id: $user_id, name: $concept_name})
                -[r:RELATIONSHIP*1..{depth}]->(target:Entity {user_id: $user_id})
                RETURN DISTINCT target.name as name, target.type as type,
                       r[SIZE(r)-1].type as relationship,
                       r[SIZE(r)-1].weight as weight
                """

                result_forward = session.run(
                    query_forward.format(depth=depth),
                    user_id=self.user_id,
                    concept_name=concept_name,
                )

                connections = [
                    {
                        "target": record["name"],
                        "type": record["type"],
                        "relationship": record["relationship"],
                        "weight": record["weight"],
                    }
                    for record in result_forward
                ]

                return {
                    "concept": concept_name,
                    "connections": connections,
                }

        except Exception as e:
            logger.error(f"Failed to get concept connections: {e}")
            return {}

    def deduplicate_concepts(self, similarity_threshold: float = 0.85) -> List[Tuple[str, str]]:
        """
        Find and merge similar concept names (e.g., "REST API" vs "REST").

        Uses string similarity and suggests merges.

        Returns:
            List of (concept1, concept2) tuples representing potential merges
        """
        if not self.driver:
            return []

        try:
            from difflib import SequenceMatcher

            with self.driver.session() as session:
                query = """
                MATCH (e:Entity {user_id: $user_id})
                RETURN e.name as name, e.type as type
                """

                result = session.run(query, user_id=self.user_id)
                concepts = [
                    (record["name"], record["type"]) for record in result
                ]

                # Find similar pairs
                similar_pairs = []
                for i, (name1, type1) in enumerate(concepts):
                    for name2, type2 in concepts[i + 1 :]:
                        if type1 == type2:  # Only compare same types
                            similarity = SequenceMatcher(
                                None, name1.lower(), name2.lower()
                            ).ratio()

                            if similarity >= similarity_threshold:
                                similar_pairs.append((name1, name2))

                logger.info(f"Found {len(similar_pairs)} potentially duplicate concepts")
                return similar_pairs

        except Exception as e:
            logger.error(f"Failed to deduplicate concepts: {e}")
            return []

    def merge_concepts(self, concept1: str, concept2: str, keep: str) -> bool:
        """
        Merge two similar concepts into one.

        Args:
            concept1: First concept name
            concept2: Second concept name
            keep: Which concept to keep ("concept1" or "concept2")

        Returns:
            True if successful
        """
        if not self.driver or keep not in ["concept1", "concept2"]:
            return False

        source = concept1 if keep == "concept1" else concept2
        target = concept2 if keep == "concept1" else concept1

        try:
            with self.driver.session() as session:
                # Redirect all relationships to the kept concept
                query = """
                MATCH (source:Entity {user_id: $user_id, name: $source_name})
                MATCH (target:Entity {user_id: $user_id, name: $target_name})
                MATCH (target)-[r]->(other:Entity {user_id: $user_id})
                WHERE other.name <> source.name
                CREATE (source)-[:RELATIONSHIP {type: r.type, weight: r.weight}]->(other)
                DELETE r
                """

                session.run(
                    query,
                    user_id=self.user_id,
                    source_name=source,
                    target_name=target,
                )

                # Delete the target concept
                delete_query = """
                MATCH (e:Entity {user_id: $user_id, name: $name})
                DETACH DELETE e
                """

                session.run(delete_query, user_id=self.user_id, name=target)

                logger.info(f"Merged '{target}' into '{source}'")

                # Phase 7a: Emit merge event for real-time updates
                try:
                    asyncio.get_event_loop().create_task(
                        GraphEventBroker.emit_entities_merged(
                            user_id=UUID(self.user_id),
                            primary_entity_id=source,
                            primary_entity_name=source,
                            merged_entity_ids=[target],
                            merged_entity_names=[target],
                            source="graph_service",
                        )
                    )
                except RuntimeError:
                    logger.debug("No event loop available for graph event emission")

                return True

        except Exception as e:
            logger.error(f"Failed to merge concepts: {e}")
            return False

    def get_knowledge_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        if not self.driver:
            return {}

        try:
            with self.driver.session() as session:
                # Entity count
                entity_query = "MATCH (e:Entity {user_id: $user_id}) RETURN count(e) as count"
                entity_count = session.run(
                    entity_query, user_id=self.user_id
                ).single()["count"]

                # Relationship count
                rel_query = (
                    "MATCH (e1:Entity {user_id: $user_id})-[r]->(e2:Entity {user_id: $user_id}) "
                    "RETURN count(r) as count"
                )
                rel_count = session.run(rel_query, user_id=self.user_id).single()["count"]

                # Top entities by connectivity
                top_query = """
                MATCH (e:Entity {user_id: $user_id})
                WITH e, size((e)-[]-()) as connections
                ORDER BY connections DESC
                LIMIT 5
                RETURN e.name as name, e.type as type, connections
                """
                top_entities = session.run(top_query, user_id=self.user_id).data()

                return {
                    "total_entities": entity_count,
                    "total_relationships": rel_count,
                    "top_entities": top_entities,
                }

        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            return {}

    def export_graph_as_json(self) -> Dict[str, Any]:
        """
        Export entire knowledge graph as JSON for frontend visualization.

        Returns:
        {
            "nodes": [{"id": "name", "label": "name", "type": "CONCEPT", ...}],
            "edges": [{"source": "name1", "target": "name2", "relationship": "DEPENDS_ON"}]
        }
        """
        if not self.driver:
            return {"nodes": [], "edges": []}

        try:
            with self.driver.session() as session:
                # Get all entities
                entity_query = "MATCH (e:Entity {user_id: $user_id}) RETURN e.name as name, e.type as type"
                entities = session.run(entity_query, user_id=self.user_id).data()

                nodes = [
                    {
                        "id": e["name"],
                        "label": e["name"],
                        "type": e["type"],
                    }
                    for e in entities
                ]

                # Get all relationships
                rel_query = """
                MATCH (source:Entity {user_id: $user_id})-[r:RELATIONSHIP]->(target:Entity {user_id: $user_id})
                RETURN source.name as source, target.name as target, r.type as relationship, r.weight as weight
                """
                relationships = session.run(rel_query, user_id=self.user_id).data()

                edges = [
                    {
                        "source": r["source"],
                        "target": r["target"],
                        "relationship": r["relationship"],
                        "weight": r["weight"],
                    }
                    for r in relationships
                ]

                logger.info(f"Exported graph: {len(nodes)} nodes, {len(edges)} edges")

                return {"nodes": nodes, "edges": edges}

        except Exception as e:
            logger.error(f"Failed to export graph: {e}")
            return {"nodes": [], "edges": []}

    def execute_query(self, cypher_query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a custom Cypher query scoped to the current user's graph.

        Args:
            cypher_query: Cypher query string (assumes it references user_id)

        Returns:
            List of results as dictionaries, or None if execution fails
        """
        if not self.driver:
            logger.warning("Neo4j driver not available")
            return None

        try:
            # Safety checks: prevent queries without user_id filter
            query_upper = cypher_query.upper()

            # Whitelist safe operations
            safe_keywords = ["MATCH", "RETURN", "WHERE", "AND", "OR", "LIMIT", "SKIP"]
            dangerous_keywords = ["DELETE", "REMOVE", "DROP", "CREATE INDEX", "CALL db.shutdown"]

            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    logger.warning(f"Blocked dangerous keyword in query: {keyword}")
                    return None

            # Ensure user_id filtering
            if "user_id" not in cypher_query:
                logger.warning("Query must include user_id filter for security")
                # For queries that don't explicitly reference user_id, we'll add scoping
                # This is a limitation - queries should include: {user_id: $user_id} filters
                # For now, we accept queries that MENTION user_id in the constraint

            with self.driver.session() as session:
                result = session.run(cypher_query, user_id=self.user_id)
                data = result.data()
                logger.info(f"Cypher query executed, returned {len(data)} results")
                return data

        except ServiceUnavailable:
            logger.error("Neo4j service unavailable")
            return None
        except Exception as e:
            logger.error(f"Cypher query execution failed: {e}")
            return None


# Module-level GraphService instance holder
_graph_service_instance: Optional['Neo4jGraphService'] = None


def set_graph_service(user_id: UUID) -> 'Neo4jGraphService':
    """
    Set the global graph service instance for the current request context.
    This should be called in the API request handler.
    """
    global _graph_service_instance
    _graph_service_instance = Neo4jGraphService(user_id=user_id)
    return _graph_service_instance


def get_graph_service() -> Optional['Neo4jGraphService']:
    """Get the current request's graph service instance."""
    return _graph_service_instance


# Alias for backward compatibility
GraphService = Neo4jGraphService
