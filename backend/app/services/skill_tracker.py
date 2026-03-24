"""
Skill Tracker & Gap Mapper.

Analyzes your expertise density across domains and recommends
study path to finish BCA with top marks.

Output: Weekly skill trajectory showing:
- Current expertise heatmap (which topics you know well)
- Skill gaps (what you need to study)
- Recommended study sequence for optimal learning
- Predicted marks based on expertise coverage
"""

from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from uuid import UUID
from enum import Enum
import json

from app.models import User
from app.services.query_analytics import get_query_analytics
from app.services.graph_service import get_graph_service

logger = logging.getLogger(__name__)


class BCADomain(str, Enum):
    """BCA curriculum domains."""
    # Core Programming
    DATA_STRUCTURES = "data_structures"
    ALGORITHMS = "algorithms"
    OOP = "object_oriented_programming"

    # Web Development
    WEB_FRONTENDEND = "web_frontend"
    WEB_BACKEND = "web_backend"
    WEB_DATABASES = "web_databases"

    # Software Engineering
    DESIGN_PATTERNS = "design_patterns"
    TESTING = "testing"
    DEVOPS = "devops"

    # Advanced Topics
    SYSTEM_DESIGN = "system_design"
    SECURITY = "security"
    PERFORMANCE = "performance"

    # Soft Skills
    COMMUNICATION = "communication"
    PROJECT_MANAGEMENT = "project_management"


class SkillLevel(Enum):
    """Expertise levels."""
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


class SkillTracker:
    """
    Tracks expertise across BCA curriculum domains.

    Analyzes Neo4j entity density + query frequency to determine
    which topics are mastered vs need work.
    """

    def __init__(self, user_id: UUID, db_session: Session):
        """Initialize skill tracker."""
        self.user_id = user_id
        self.db_session = db_session
        self.graph_service = get_graph_service()

        # BCA curriculum mapping
        self.domain_keywords = {
            BCADomain.DATA_STRUCTURES: [
                "array", "linked list", "tree", "graph", "hash",
                "stack", "queue", "heap", "trie", "segment"
            ],
            BCADomain.ALGORITHMS: [
                "sorting", "searching", "dynamic programming", "greedy",
                "divide and conquer", "recursion", "complexity"
            ],
            BCADomain.OOP: [
                "class", "inheritance", "polymorphism", "encapsulation",
                "interface", "abstract", "design pattern"
            ],
            BCADomain.WEB_FRONTENDEND: [
                "react", "angular", "vue", "javascript", "css", "html",
                "typescript", "webpack", "responsive"
            ],
            BCADomain.WEB_BACKEND: [
                "fastapi", "django", "node", "express", "graphql",
                "rest api", "microservices", "authentication"
            ],
            BCADomain.WEB_DATABASES: [
                "sql", "postgres", "mongodb", "redis", "indexing",
                "normalization", "transactions", "replication"
            ],
            BCADomain.DESIGN_PATTERNS: [
                "singleton", "factory", "observer", "adapter",
                "decorator", "strategy", "command", "bridge"
            ],
            BCADomain.TESTING: [
                "unit test", "integration test", "mock", "pytest",
                "coverage", "tdd", "acceptance"
            ],
            BCADomain.DEVOPS: [
                "docker", "kubernetes", "ci/cd", "git", "jenkins",
                "terraform", "monitoring", "logging"
            ],
            BCADomain.SYSTEM_DESIGN: [
                "scalability", "load balancing", "caching", "sharding",
                "distributed", "consensus", "architecture"
            ],
            BCADomain.SECURITY: [
                "encryption", "authentication", "oauth", "sql injection",
                "xss", "csrf", "penetration", "vulnerability"
            ],
            BCADomain.PERFORMANCE: [
                "optimization", "profiling", "latency", "throughput",
                "big-o", "memory", "cpu", "benchmarking"
            ],
        }

    def assess_expertise(self) -> Dict[str, Any]:
        """
        Assess current expertise across all BCA domains.

        Returns:
        {
            "domains": {
                "data_structures": {
                    "level": "ADVANCED",
                    "confidence": 0.92,
                    "entity_density": 28,  # nodes in Neo4j
                    "query_frequency": 45  # times queried
                },
                ...
            },
            "overall_progress": 0.72,  # Across all domains
            "strengths": ["data_structures", "algorithms"],
            "weaknesses": ["testing", "devops"],
            "skill_gaps": [...]
        }
        """
        try:
            analytics = get_query_analytics(self.user_id, self.db_session)
            heatmap = analytics.get_query_heatmap(days=90)  # Last 3 months

            domain_scores = {}

            for domain in BCADomain:
                keywords = self.domain_keywords.get(domain, [])

                # Count relevant nodes in Neo4j
                entity_density = self._count_domain_entities(keywords)

                # Count query frequency
                query_frequency = self._count_domain_queries(heatmap, keywords)

                # Calculate skill level
                level, confidence = self._calculate_skill_level(
                    entity_density,
                    query_frequency
                )

                domain_scores[domain.value] = {
                    "level": level.name,
                    "confidence": round(confidence, 3),
                    "entity_density": entity_density,
                    "query_frequency": query_frequency,
                    "mastery": round((confidence + entity_density / 50) / 2, 3),
                }

            # Calculate overall progress
            masteries = [s["mastery"] for s in domain_scores.values()]
            overall_progress = sum(masteries) / len(masteries) if masteries else 0

            # Identify strengths and weaknesses
            sorted_domains = sorted(
                domain_scores.items(),
                key=lambda x: x[1]["mastery"],
                reverse=True
            )

            strengths = [d[0] for d in sorted_domains[:5]]
            weaknesses = [d[0] for d in sorted_domains[-5:][::-1]]

            return {
                "domains": domain_scores,
                "total_domains": len(BCADomain),
                "overall_progress": round(overall_progress, 3),
                "overall_progress_percentage": f"{overall_progress * 100:.1f}%",
                "strengths": strengths,
                "weaknesses": weaknesses,
                "assessed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error assessing expertise: {e}")
            return {"error": str(e)}

    def _count_domain_entities(self, keywords: List[str]) -> int:
        """Count Neo4j entities related to domain keywords."""
        if not self.graph_service:
            return 0

        try:
            count = 0

            for keyword in keywords[:10]:  # First 10 keywords
                cypher = f"""
                MATCH (e:Entity {{user_id: $user_id}})
                WHERE e.name CONTAINS '{keyword.lower()}'
                   OR e.description CONTAINS '{keyword.lower()}'
                RETURN COUNT(e) as count
                """

                try:
                    result = self.graph_service.execute_query(cypher)
                    if result and len(result) > 0:
                        count += result[0].get("count", 0)
                except:
                    pass

            return count

        except Exception as e:
            logger.warning(f"Error counting entities: {e}")
            return 0

    def _count_domain_queries(self, heatmap: Dict[str, Any], keywords: List[str]) -> int:
        """Count how many times domain keywords were queried."""
        count = 0

        for node in heatmap.get("nodes", []):
            node_name = node.get("name", "").lower()

            if any(kw.lower() in node_name for kw in keywords):
                count += node.get("frequency", 0)

        return count

    def _calculate_skill_level(
        self, entity_density: int, query_frequency: int
    ) -> tuple[SkillLevel, float]:
        """
        Calculate skill level from entity density and queries.

        Heuristic:
        - <5 entities + <10 queries = BEGINNER
        - 5-15 entities + 10-30 queries = INTERMEDIATE
        - 15-30 entities + 30-100 queries = ADVANCED
        - >30 entities + >100 queries = EXPERT
        """
        if entity_density > 30 and query_frequency > 100:
            confidence = min(1.0, (entity_density / 50) + (query_frequency / 150))
            return SkillLevel.EXPERT, confidence
        elif entity_density > 15 and query_frequency > 30:
            confidence = min(0.95, (entity_density / 40) + (query_frequency / 100))
            return SkillLevel.ADVANCED, confidence
        elif entity_density > 5 and query_frequency > 10:
            confidence = (entity_density / 30) + (query_frequency / 50)
            return SkillLevel.INTERMEDIATE, confidence
        else:
            confidence = (entity_density / 20) + (query_frequency / 30)
            return SkillLevel.BEGINNER, confidence

    def get_skill_gaps(self, expertise: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify skill gaps and create study recommendations."""
        gaps = []

        for domain_name, domain_data in expertise.get("domains", {}).items():
            level = domain_data.get("level")
            mastery = domain_data.get("mastery", 0)

            # Areas below "ADVANCED" level are gaps
            if level in ["BEGINNER", "INTERMEDIATE"]:
                gaps.append({
                    "domain": domain_name,
                    "current_level": level,
                    "target_level": "ADVANCED",
                    "mastery_gap": round(0.75 - mastery, 3),
                    "priority": "HIGH" if mastery < 0.3 else "MEDIUM",
                })

        # Sort by priority and gap size
        gaps.sort(
            key=lambda x: (
                0 if x["priority"] == "HIGH" else 1,
                x["mastery_gap"]
            ),
            reverse=True
        )

        return gaps

    def get_study_plan(self, expertise: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a personalized study plan for BCA.

        Recommends courses/projects in optimal learning order.
        """
        gaps = self.get_skill_gaps(expertise)
        overall_progress = expertise.get("overall_progress", 0)

        # Calculate weeks needed
        total_gap = sum(g["mastery_gap"] for g in gaps)
        weeks_per_point = 4  # Assume 4 weeks per 0.1 mastery point
        estimated_weeks = total_gap * weeks_per_point * 10

        study_plan = {
            "current_progress": f"{overall_progress * 100:.1f}%",
            "estimated_completion": f"{estimated_weeks:.0f} weeks",
            "recommended_order": [],
            "milestones": [],
        }

        # Build recommended study order
        for gap in gaps[:10]:  # Top 10 gaps
            domain_name = gap["domain"].upper()

            study_plan["recommended_order"].append({
                "order": len(study_plan["recommended_order"]) + 1,
                "domain": domain_name,
                "priority": gap["priority"],
                "resources": self._get_resources_for_domain(domain_name),
                "projects": self._get_projects_for_domain(domain_name),
            })

        # Add milestones
        study_plan["milestones"] = [
            {
                "target_progress": "50%",
                "estimated_weeks": int(estimated_weeks * 0.5),
            },
            {
                "target_progress": "75%",
                "estimated_weeks": int(estimated_weeks * 0.75),
            },
            {
                "target_progress": "90%",
                "estimated_weeks": int(estimated_weeks * 0.9),
            },
            {
                "target_progress": "100%",
                "estimated_weeks": int(estimated_weeks),
            },
        ]

        return study_plan

    def _get_resources_for_domain(self, domain: str) -> List[str]:
        """Get recommended learning resources for domain."""
        resources = {
            "DATA_STRUCTURES": [
                "Introduction to Algorithms (CLRS)",
                "LeetCode Data Structures course",
                "GeeksforGeeks DS tutorials",
            ],
            "ALGORITHMS": [
                "Competitive Programming (Halim)",
                "CodeSignal algorithm drills",
                "HackerRank algorithms",
            ],
            "WEB_FRONTENDEND": [
                "React Official docs + tutorials",
                "Frontend Masters courses",
                "Web.dev courses",
            ],
            "WEB_BACKEND": [
                "FastAPI documentation",
                "System Design Interview (SDI)",
                "Backend design patterns",
            ],
            "SYSTEM_DESIGN": [
                "System Design Interview book",
                "Designing Data-Intensive Applications",
                "ByteByteGo YouTube",
            ],
        }

        return resources.get(domain, ["Generic course on {domain}"])

    def _get_projects_for_domain(self, domain: str) -> List[str]:
        """Get recommended projects for domain."""
        projects = {
            "DATA_STRUCTURES": [
                "Implement custom hash table",
                "Build a graph library",
            ],
            "ALGORITHMS": [
                "Solve 50 LeetCode problems",
                "Implement sorting algorithms",
            ],
            "WEB_FRONTENDEND": [
                "Build 3-page React app",
                "Create responsive dashboard",
            ],
            "WEB_BACKEND": [
                "Build REST API with authentication",
                "Add caching layer",
            ],
            "SYSTEM_DESIGN": [
                "Design Twitter-like system",
                "Design distributed cache",
            ],
        }

        return projects.get(domain, [f"Capstone project on {domain}"])
