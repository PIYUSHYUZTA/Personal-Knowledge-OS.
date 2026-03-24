"""
Hybrid Retrieval Engine: Combines pgvector semantic search + Neo4j graph queries.
Returns unified "Context Packet" for LLM reasoning.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.services.knowledge_service import KnowledgeService
from app.services.graph_service import Neo4jGraphService
from app.services.parent_retrieval import ParentDocumentRetriever
from app.schemas import SearchResult

logger = logging.getLogger(__name__)


class HybridContextPacket:
    """
    Unified context packet combining semantic + graph data.

    Structure:
    {
        "semantic_results": [SearchResult with parent context, ...],
        "graph_context": {
            "entities": [Entity, ...],
            "relationships": [Relationship, ...],
            "connected_concepts": [name, ...]
        },
        "synthesis": {
            "key_themes": [theme, ...],
            "critical_relationships": [(source, target, type), ...],
            "knowledge_gaps": [gap, ...]
        }
    }
    """

    def __init__(self):
        self.semantic_results = []
        self.graph_context = {
            "entities": [],
            "relationships": [],
            "connected_concepts": [],
        }
        self.synthesis = {
            "key_themes": [],
            "critical_relationships": [],
            "knowledge_gaps": [],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "semantic_results": [
                {
                    "chunk_id": str(r.chunk_id),
                    "source_id": str(r.source_id),
                    "file_name": r.file_name,
                    "chunk_text": r.chunk_text,
                    "similarity_score": r.similarity_score,
                }
                for r in self.semantic_results
            ],
            "graph_context": self.graph_context,
            "synthesis": self.synthesis,
        }

    def to_rag_prompt(self, max_chars: int = 8000) -> str:
        """
        Convert context packet to RAG prompt format for LLM.

        Format:
        SOURCES:
        [List of retrieved documents]

        RELATIONSHIPS:
        [Concepts and how they connect]

        SYNTHESIS:
        [Key themes and critical relationships]
        """
        prompt_parts = []

        # Part 1: Semantic sources
        prompt_parts.append("## KNOWLEDGE BASE SOURCES\n")
        char_count = 0

        for result in self.semantic_results:
            source_text = f"**From {result.file_name}** (Similarity: {result.similarity_score:.1%})\n{result.chunk_text}\n\n"
            if char_count + len(source_text) < max_chars:
                prompt_parts.append(source_text)
                char_count += len(source_text)

        # Part 2: Graph context
        if self.graph_context["relationships"]:
            prompt_parts.append("\n## CONCEPT RELATIONSHIPS\n")
            for rel in self.graph_context["relationships"][:10]:  # Limit to top 10
                rel_text = f"- {rel['source']} **{rel['type']}** {rel['target']}\n"
                if char_count + len(rel_text) < max_chars:
                    prompt_parts.append(rel_text)
                    char_count += len(rel_text)

        # Part 3: Synthesis
        if self.synthesis["key_themes"]:
            prompt_parts.append("\n## KEY THEMES\n")
            for theme in self.synthesis["key_themes"][:5]:
                theme_text = f"- {theme}\n"
                if char_count + len(theme_text) < max_chars:
                    prompt_parts.append(theme_text)
                    char_count += len(theme_text)

        return "".join(prompt_parts)


class HybridRetrievalEngine:
    """
    Hybrid retrieval combining semantic search (pgvector) + structural search (Neo4j).
    """

    @staticmethod
    def retrieve_hybrid_context(
        db: Session,
        user_id: UUID,
        query: str,
        top_k: int = 5,
        graph_depth: int = 2,
        min_similarity: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Retrieve hybrid context packet combining semantic + graph data.

        Args:
            db: Database session
            user_id: User ID
            query: Query string
            top_k: Top K semantic results
            graph_depth: Depth for graph traversal
            min_similarity: Minimum similarity threshold

        Returns:
            Context packet dictionary
        """
        try:
            packet = HybridContextPacket()

            logger.info(f"Starting hybrid retrieval for query: {query}")

            # === PHASE 1: SEMANTIC SEARCH + PARENT RETRIEVAL ===
            logger.info("Phase 1: Semantic search with parent context")

            results_with_context = ParentDocumentRetriever.semantic_search_with_parent_context(
                db,
                user_id,
                query,
                top_k=top_k,
                min_similarity=min_similarity,
                context_range=2,
            )

            # Store semantic results
            for result, parent_context in results_with_context:
                packet.semantic_results.append(result)

            logger.info(f"Retrieved {len(packet.semantic_results)} semantic results")

            # === PHASE 2: GRAPH CONTEXT RETRIEVAL ===
            logger.info("Phase 2: Graph context retrieval")

            graph_service = Neo4jGraphService(user_id)

            # Extract key concepts from query
            from app.services.entity_extraction import EntityExtractor

            query_entities = EntityExtractor.extract_entities(query)
            key_concepts = [e[0] for e in query_entities]

            logger.info(f"Extracted {len(key_concepts)} key concepts from query")

            # For each key concept, retrieve graph context
            for concept in key_concepts[:5]:  # Limit to top 5 concepts
                try:
                    connections = graph_service.get_concept_connections(
                        concept, depth=graph_depth
                    )

                    if connections.get("connections"):
                        packet.graph_context["connected_concepts"].append(concept)

                        for conn in connections["connections"][:10]:
                            packet.graph_context["relationships"].append(
                                {
                                    "source": concept,
                                    "target": conn["target"],
                                    "type": conn.get("relationship", "RELATED_TO"),
                                    "weight": conn.get("weight", 1.0),
                                }
                            )

                except Exception as e:
                    logger.warning(f"Error retrieving graph context for {concept}: {e}")

            logger.info(
                f"Retrieved {len(packet.graph_context['relationships'])} relationships"
            )

            # === PHASE 3: SYNTHESIS ===
            logger.info("Phase 3: Context synthesis")

            packet.synthesis["key_themes"] = HybridRetrievalEngine._extract_themes(
                packet.semantic_results
            )

            packet.synthesis["critical_relationships"] = (
                HybridRetrievalEngine._rank_relationships(
                    packet.graph_context["relationships"]
                )
            )

            packet.synthesis["knowledge_gaps"] = HybridRetrievalEngine._identify_gaps(
                query, packet.semantic_results, packet.graph_context["relationships"]
            )

            logger.info("Hybrid context retrieval complete")

            return packet.to_dict()

        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            return {
                "semantic_results": [],
                "graph_context": {"entities": [], "relationships": []},
                "synthesis": {"key_themes": [], "critical_relationships": []},
            }

    @staticmethod
    def _extract_themes(results: List[SearchResult]) -> List[str]:
        """Extract major themes from semantic results."""
        themes = set()

        for result in results:
            # Extract themes from chunk text (simple heuristic)
            words = result.chunk_text.lower().split()

            # Common theme keywords
            theme_keywords = {
                "design": ["architecture", "design", "pattern", "structure"],
                "optimization": ["optimize", "performance", "efficient", "fast"],
                "security": ["secure", "encrypt", "authentication", "authorization"],
                "scalability": ["scale", "distribute", "parallel", "concurrent"],
                "persistence": ["database", "storage", "persistence", "state"],
            }

            for theme, keywords in theme_keywords.items():
                if any(keyword in words for keyword in keywords):
                    themes.add(theme)

        return sorted(list(themes))

    @staticmethod
    def _rank_relationships(relationships: List[Dict]) -> List[tuple]:
        """Rank relationships by weight and relevance."""
        sorted_rels = sorted(
            relationships, key=lambda x: x.get("weight", 1.0), reverse=True
        )

        # Return top 10 as tuples
        return [
            (rel["source"], rel["target"], rel["type"]) for rel in sorted_rels[:10]
        ]

    @staticmethod
    def _identify_gaps(
        query: str, results: List[SearchResult], relationships: List[Dict]
    ) -> List[str]:
        """Identify knowledge gaps based on query and retrieval."""
        gaps = []

        # If very few results, indicate potential gap
        if len(results) < 2:
            gaps.append(f"Limited knowledge base coverage for '{query}'")

        # If no relationships found but query asks about connections
        if not relationships and any(
            word in query.lower() for word in ["how", "relate", "connect", "depend"]
        ):
            gaps.append("No relationship data found - consider linking related concepts")

        # Check for common CS domains not covered
        cs_domains = [
            "database",
            "security",
            "performance",
            "scalability",
            "testing",
        ]
        for domain in cs_domains:
            if domain in query.lower() and not any(
                domain in r.chunk_text.lower() for r in results
            ):
                gaps.append(f"Limited coverage of {domain} best practices")

        return gaps

    @staticmethod
    def format_for_prompt(packet: Dict[str, Any]) -> str:
        """
        Format context packet for LLM prompt injection.

        Returns markdown-formatted context for injection into system prompt.
        """
        lines = []

        lines.append("# KNOWLEDGE BASE CONTEXT\n")

        # Semantic results
        if packet.get("semantic_results"):
            lines.append("## Retrieved Chunks\n")
            for i, result in enumerate(packet["semantic_results"][:3], 1):
                lines.append(
                    f"{i}. **{result['file_name']}** (relevance: {result['similarity_score']:.0%})\n"
                )
                lines.append(f"   {result['chunk_text'][:300]}...\n\n")

        # Graph context
        if packet.get("graph_context", {}).get("relationships"):
            lines.append("## Related Concepts and Relationships\n")
            for rel in packet["graph_context"]["relationships"][:5]:
                lines.append(
                    f"- {rel['source']} **{rel['type']}** {rel['target']}\n"
                )
            lines.append("\n")

        # Synthesis
        if packet.get("synthesis", {}).get("key_themes"):
            lines.append("## Key Themes\n")
            for theme in packet["synthesis"]["key_themes"]:
                lines.append(f"- {theme}\n")

        return "".join(lines)
