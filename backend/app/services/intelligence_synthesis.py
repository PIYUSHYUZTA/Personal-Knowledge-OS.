"""
Knowledge Auto-Synthesis Service.

Automatically scans ingested data and generates weekly intelligence reports.
Identifies connections between documents, emerging expertise areas, and project relevance.
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session

from app.services.llm_factory import LLMFactory
from app.services.hybrid_engine import HybridRetrievalEngine
from app.services.graph_service import get_graph_service
from app.models import KnowledgeSource, KnowledgeChunk


logger = logging.getLogger(__name__)


class WeeklyIntelligenceReport:
    """Generates weekly intelligence reports analyzing ingested knowledge."""

    def __init__(self, user_id: str, db_session: Session):
        """Initialize report generator."""
        self.user_id = user_id
        self.db_session = db_session
        self.llm = LLMFactory.get_provider()
        self.graph_service = get_graph_service()

    def generate_weekly_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive weekly intelligence report.

        Returns:
        {
            "week_of": "2026-03-11",
            "summary": "3 new PDFs ingested, 15 new concepts extracted...",
            "ingested_sources": [{"title": "...", "topic": "..."}],
            "new_concepts": [{"name": "...", "source_count": 3}],
            "emerging_expertise": [{"area": "...", "confidence": 0.85}],
            "project_relevance": [{"project": "...", "relevance_score": 0.92}],
            "connection_map": {
                "clusters": [{"concepts": [...], "strength": 0.85}],
                "bridges": [{"concept1": "...", "concept2": "...", "distance": 2}]
            },
            "insights": ["Insight 1", "Insight 2"],
            "recommendations": ["Action 1", "Action 2"],
            "generated_at": "2026-03-11T..."
        }
        """
        report = {
            "week_of": (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())).strftime("%Y-%m-%d"),
            "generated_at": datetime.utcnow().isoformat(),
            "user_id": self.user_id,
        }

        try:
            # Step 1: Get sources ingested this week
            report["ingested_sources"] = self._get_weekly_sources()

            # Step 2: Extract new concepts
            report["new_concepts"] = self._extract_new_concepts(report["ingested_sources"])

            # Step 3: Identify emerging expertise
            report["emerging_expertise"] = self._identify_expertise_areas(report["new_concepts"])

            # Step 4: Build connection map
            report["connection_map"] = self._build_connection_map(report["new_concepts"])

            # Step 5: Generate project relevance analysis
            report["project_relevance"] = self._analyze_project_relevance(report["new_concepts"])

            # Step 6: Use LLM to synthesize insights
            report["summary"], report["insights"], report["recommendations"] = \
                self._synthesize_insights(report)

            logger.info(f"Generated weekly report for user {self.user_id}")
            return report

        except Exception as e:
            logger.error(f"Error generating weekly report: {e}", exc_info=True)
            return {"error": str(e), "week_of": report["week_of"]}

    def _get_weekly_sources(self) -> List[Dict[str, Any]]:
        """Get sources ingested in the past week."""
        one_week_ago = datetime.utcnow() - timedelta(days=7)

        sources = self.db_session.query(KnowledgeSource).filter(
            KnowledgeSource.user_id == self.user_id,
            KnowledgeSource.created_at >= one_week_ago,
        ).all()

        return [
            {
                "id": str(source.id),
                "title": source.file_name,
                "source_type": source.source_type,
                "size_bytes": source.file_size,
                "chunks_count": source.chunk_count,
                "ingested_at": source.created_at.isoformat(),
            }
            for source in sources
        ]

    def _extract_new_concepts(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract concepts from newly ingested sources."""
        if not sources:
            return []

        try:
            # Query concepts created in the past week
            one_week_ago = datetime.utcnow() - timedelta(days=7)

            # Use Neo4j to get entities created this week
            if self.graph_service:
                cypher = """
                MATCH (e:Entity {user_id: $user_id})
                WHERE e.updated_at > timestamp() - 7*24*60*60*1000
                WITH e, [(e)-[r:MENTIONS|IMPLEMENTS|DEPENDS_ON]-(e2) | e2.name] as neighbors
                RETURN e.name as name, e.type as type, e.description as description, neighbors
                LIMIT 50
                """

                results = self.graph_service.execute_query(cypher)

                return [
                    {
                        "name": r.get("name"),
                        "type": r.get("type"),
                        "description": r.get("description"),
                        "related_count": len(r.get("neighbors", [])),
                    }
                    for r in (results or [])
                ]
        except Exception as e:
            logger.warning(f"Could not extract concepts via Neo4j: {e}")

        return []

    def _identify_expertise_areas(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify emerging areas of expertise based on concept distribution."""
        if not concepts:
            return []

        # Group concepts by type
        expertise_areas = {}

        for concept in concepts:
            concept_type = concept.get("type", "UNKNOWN")
            if concept_type not in expertise_areas:
                expertise_areas[concept_type] = {"count": 0, "avg_relations": 0}

            expertise_areas[concept_type]["count"] += 1
            expertise_areas[concept_type]["avg_relations"] += concept.get("related_count", 0)

        # Convert to sorted list
        result = []
        for area_type, stats in expertise_areas.items():
            avg_relations = stats["avg_relations"] / max(1, stats["count"])

            # Calculate confidence (more relations = higher confidence in expertise)
            confidence = min(0.99, 0.5 + (avg_relations * 0.1))

            result.append({
                "area": area_type,
                "concept_count": stats["count"],
                "avg_connections": round(avg_relations, 2),
                "confidence": round(confidence, 2),
            })

        return sorted(result, key=lambda x: x["confidence"], reverse=True)

    def _build_connection_map(self, concepts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a connection map showing how concepts relate to each other."""
        if not self.graph_service or not concepts:
            return {"clusters": [], "bridges": []}

        try:
            # Find clusters (groups of related concepts)
            cypher = """
            MATCH (e:Entity {user_id: $user_id})-[r:RELATES_TO|IMPLEMENTS|DEPENDS_ON]-(e2:Entity {user_id: $user_id})
            WITH e, e2, count(r) as strength
            WHERE strength > 2
            RETURN e.name as concept1, e2.name as concept2, strength
            LIMIT 30
            """

            relationships = self.graph_service.execute_query(cypher) or []

            # Build clusters using simple grouping
            clusters = self._identify_clusters(concepts, relationships)
            bridges = [
                {
                    "concept1": r.get("concept1"),
                    "concept2": r.get("concept2"),
                    "strength": r.get("strength", 0),
                }
                for r in relationships[:10]
            ]

            return {
                "clusters": clusters,
                "bridges": bridges,
                "total_relationships": len(relationships),
            }

        except Exception as e:
            logger.warning(f"Could not build connection map: {e}")
            return {"clusters": [], "bridges": []}

    def _identify_clusters(
        self, concepts: List[Dict[str, Any]], relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify clusters of related concepts."""
        if not concepts:
            return []

        # Simple clustering: group by concept type
        clusters = {}

        for concept in concepts:
            concept_type = concept.get("type", "UNKNOWN")
            if concept_type not in clusters:
                clusters[concept_type] = []
            clusters[concept_type].append(concept.get("name"))

        return [
            {
                "topic": cluster_type,
                "concepts": concept_names,
                "strength": len(concept_names) / len(concepts),
            }
            for cluster_type, concept_names in clusters.items()
        ]

    def _analyze_project_relevance(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze relevance to potential projects based on concepts."""
        if not concepts:
            return []

        # Group concepts and suggest project areas
        project_mapping = {
            "TECHNOLOGY": "Software Development",
            "FRAMEWORK": "Web/App Development",
            "LANGUAGE": "Programming",
            "METHODOLOGY": "Project Management",
            "ARCHITECTURE": "System Design",
            "LIBRARY": "Development Tools",
        }

        projects = {}

        for concept in concepts:
            concept_type = concept.get("type", "")
            project = project_mapping.get(concept_type)

            if project:
                if project not in projects:
                    projects[project] = 0
                projects[project] += concept.get("related_count", 0) + 1

        # Convert to scored list
        return [
            {
                "project": project_name,
                "relevance_score": round(min(0.99, score / len(concepts)), 2),
                "strength": "high" if score > 5 else "medium" if score > 2 else "low",
            }
            for project_name, score in sorted(
                projects.items(), key=lambda x: x[1], reverse=True
            )
        ]

    async def _synthesize_insights(
        self, report: Dict[str, Any]
    ) -> tuple[str, List[str], List[str]]:
        """Use LLM to synthesize human-readable insights and recommendations."""
        try:
            # Build context
            sources_text = "\n".join(
                f"- {s['title']} ({s['chunks_count']} chunks)"
                for s in report.get("ingested_sources", [])[:10]
            )

            concepts_text = "\n".join(
                f"- {c['name']} ({c['type']}, {c['related_count']} relations)"
                for c in report.get("new_concepts", [])[:15]
            )

            expertise_text = "\n".join(
                f"- {e['area']}: {e['confidence']} confidence ({e['concept_count']} concepts)"
                for e in report.get("emerging_expertise", [])[:5]
            )

            synthesis_prompt = f"""
Analyze this weekly knowledge graph summary and provide insights:

INGESTED SOURCES (this week):
{sources_text or "No new sources"}

EXTRACTED CONCEPTS:
{concepts_text or "No new concepts"}

EMERGING EXPERTISE:
{expertise_text or "No expertise areas"}

CONNECTION STRENGTH: {report.get('connection_map', {}).get('total_relationships', 0)} relationships

Please provide:
1. A 2-3 sentence executive summary of what the user is learning this week
2. 3-4 key insights about their emerging expertise areas
3. 2-3 actionable recommendations for their next projects or studies

Format your response as:
SUMMARY: [summary here]
INSIGHTS:
- [insight 1]
- [insight 2]
- [insight 3]
RECOMMENDATIONS:
- [recommendation 1]
- [recommendation 2]
"""

            response = await self.llm.generate(
                prompt=synthesis_prompt,
                system_prompt="You are a knowledge analyst. Provide insightful, actionable intelligence."
            )

            response_text = response.get("content", "")

            # Parse response
            summary = ""
            insights = []
            recommendations = []

            if "SUMMARY:" in response_text:
                summary_start = response_text.find("SUMMARY:") + len("SUMMARY:")
                summary_end = response_text.find("INSIGHTS:", summary_start)
                summary = response_text[summary_start:summary_end].strip()

            if "INSIGHTS:" in response_text:
                insights_start = response_text.find("INSIGHTS:") + len("INSIGHTS:")
                insights_end = response_text.find("RECOMMENDATIONS:", insights_start)
                insights_text = response_text[insights_start:insights_end]
                insights = [line.strip("- ").strip() for line in insights_text.split("\n") if line.strip().startswith("-")]

            if "RECOMMENDATIONS:" in response_text:
                rec_start = response_text.find("RECOMMENDATIONS:") + len("RECOMMENDATIONS:")
                rec_text = response_text[rec_start:]
                recommendations = [line.strip("- ").strip() for line in rec_text.split("\n") if line.strip().startswith("-")]

            return summary, insights[:4], recommendations[:3]

        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e}")
            return "Weekly knowledge synthesis completed.", [], []


class IntelligenceReportCache:
    """Cache for weekly intelligence reports."""

    def __init__(self):
        """Initialize cache."""
        self.cache: Dict[str, Dict[str, Any]] = {}

    def get_latest_report(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest cached report for a user."""
        return self.cache.get(user_id)

    def store_report(self, user_id: str, report: Dict[str, Any]):
        """Store a report in cache."""
        self.cache[user_id] = report
        logger.info(f"Cached intelligence report for user {user_id}")

    def get_report_history(self, user_id: str, weeks: int = 4) -> List[Dict[str, Any]]:
        """Get historical reports (would be persisted in production)."""
        # In production, this would query a database table
        current = self.get_latest_report(user_id)
        if current:
            return [current]
        return []


# Global cache instance
_report_cache = IntelligenceReportCache()


def get_intelligence_cache() -> IntelligenceReportCache:
    """Get the global intelligence cache."""
    return _report_cache
