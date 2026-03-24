"""
Neo4j Index Management and Optimization.
Creates indexes on frequently queried entity types and relationships.
"""

from typing import List
import logging
from uuid import UUID

from app.services.graph_service import Neo4jGraphService

logger = logging.getLogger(__name__)


class Neo4jIndexManager:
    """
    Manages Neo4j indexes for performance optimization.

    Indexes are critical for graph databases to prevent full-graph scans
    when searching for entities or relationships.
    """

    # Index definitions
    INDEXES = [
        {
            "name": "entity_user_name",
            "cypher": "CREATE INDEX entity_user_name IF NOT EXISTS FOR (e:Entity) ON (e.user_id, e.name)",
            "description": "User + entity name for fast entity lookups",
        },
        {
            "name": "entity_type",
            "cypher": "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "description": "Entity type for domain-specific searches",
        },
        {
            "name": "relationship_type",
            "cypher": "CREATE INDEX relationship_type IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() ON (r.type)",
            "description": "Relationship type for filtering edges",
        },
        {
            "name": "entity_name_text",
            "cypher": "CREATE FULLTEXT INDEX entity_name_text IF NOT EXISTS FOR (e:Entity) ON EACH [e.name]",
            "description": "Full-text search on entity names (fuzzy matching)",
        },
    ]

    @staticmethod
    def create_all_indexes(user_id: UUID) -> List[bool]:
        """
        Create all recommended indexes for a user's graph.

        Returns:
            List of success booleans
        """
        graph_service = Neo4jGraphService(user_id)

        if not graph_service.driver:
            logger.error("Neo4j driver not available")
            return []

        results = []

        for index_def in Neo4jIndexManager.INDEXES:
            try:
                with graph_service.driver.session() as session:
                    session.run(index_def["cypher"])
                    logger.info(f"Created index: {index_def['name']}")
                    results.append(True)

            except Exception as e:
                logger.error(f"Failed to create index {index_def['name']}: {e}")
                results.append(False)

        return results

    @staticmethod
    def get_index_usage_stats(user_id: UUID) -> dict:
        """
        Get statistics about index usage and performance.

        Returns:
            Statistics about indexes and queries
        """
        graph_service = Neo4jGraphService(user_id)

        if not graph_service.driver:
            return {}

        try:
            with graph_service.driver.session() as session:
                # Get index information
                result = session.run(
                    "SHOW INDEXES YIELD name, entityType, labelsOrTypes, properties"
                )

                indexes = result.data()

                return {
                    "total_indexes": len(indexes),
                    "indexes": indexes,
                }

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}

    @staticmethod
    def optimize_index_stats(user_id: UUID) -> bool:
        """
        Update index statistics for query optimizer.

        Called periodically to help Neo4j optimize query plans.
        """
        graph_service = Neo4jGraphService(user_id)

        if not graph_service.driver:
            return False

        try:
            with graph_service.driver.session() as session:
                # Analyze the graph to update statistics
                session.run("ANALYZE")
                logger.info("Updated Neo4j index statistics")
                return True

        except Exception as e:
            logger.error(f"Error optimizing stats: {e}")
            return False


class Neo4jQueryOptimizer:
    """
    Optimizes Cypher queries for better performance.
    """

    @staticmethod
    def explain_query(user_id: UUID, cypher_query: str) -> dict:
        """
        Explain a Cypher query to understand execution plan.

        Returns:
            Query plan and statistics
        """
        graph_service = Neo4jGraphService(user_id)

        if not graph_service.driver:
            return {}

        try:
            with graph_service.driver.session() as session:
                result = session.run(f"EXPLAIN {cypher_query}")

                return {
                    "plan": str(result),
                    "status": "explained",
                }

        except Exception as e:
            logger.error(f"Error explaining query: {e}")
            return {"error": str(e)}
