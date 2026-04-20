"""
Technical Reasoning Engine for PKOS.
Replaces dual-persona AURA with a single, high-performance technical reasoning system.

This is a unified engine optimized for:
- Computer Science fundamentals
- Software engineering best practices
- System architecture analysis
- Performance optimization recommendations
- Security vulnerability identification
"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.models import ConversationHistory, User
from app.schemas import SearchResult
from app.services.knowledge_service import KnowledgeService
from app.services.parent_retrieval import ParentDocumentRetriever
from app.services.llm_factory import LLMFactory
import asyncio

logger = logging.getLogger(__name__)


class TechnicalReasoningContext:
    """Context for technical reasoning."""

    def __init__(self, query: str, retrieved_results: List[SearchResult]):
        self.query = query
        self.retrieved_results = retrieved_results
        self.context = None
        self.key_concerns = []
        self.recommended_approach = None
        self.identified_domains = []


class TechnicalReasoningEngine:
    """
    High-performance technical reasoning engine for computer science queries.

    Optimized for:
    - Accurate, precise answers
    - Complete technical details
    - Best practice recommendations
    - Clear architectural guidance
    """

    # Technical reasoning rules and patterns
    TECHNICAL_DOMAINS = {
        "database": [
            "database",
            "query optimization",
            "indexing strategies",
            "normalization",
            "transaction management",
            "sql",
        ],
        "system_design": [
            "scalability",
            "load balancing",
            "caching",
            "replication",
            "partitioning",
        ],
        "security": [
            "security",
            "encryption",
            "authentication",
            "authorization",
            "injection attacks",
            "sql injection",
            "xss",
            "csrf",
        ],
        "performance": [
            "performance",
            "optimize",
            "latency",
            "throughput",
            "memory usage",
            "cpu optimization",
            "profiling",
        ],
        "architecture": [
            "microservices",
            "monolith",
            "serverless",
            "event-driven",
            "middleware",
        ],
    }

    @staticmethod
    def analyze_query(
        db: Session,
        user_id: UUID,
        query: str,
        retrieved_results: List[SearchResult],
    ) -> TechnicalReasoningContext:
        """
        Analyze a technical query and prepare reasoning context.

        Args:
            db: Database session
            user_id: User ID
            query: Technical question
            retrieved_results: Semantically similar chunks from knowledge base

        Returns:
            TechnicalReasoningContext with analysis
        """
        context = TechnicalReasoningContext(query, retrieved_results)

        # Identify technical domain
        query_lower = query.lower()
        context.identified_domains = []

        for domain, keywords in TechnicalReasoningEngine.TECHNICAL_DOMAINS.items():
            if any(keyword in query_lower for keyword in keywords):
                context.identified_domains.append(domain)

        # Determine if query requires live context from knowledge base
        context.requires_knowledge_base = len(retrieved_results) > 0

        # Identify key concerns from query
        if "why" in query_lower:
            context.key_concerns.append("explanation")
        if "how" in query_lower:
            context.key_concerns.append("implementation")
        if "best" in query_lower or "optimal" in query_lower or "optimize" in query_lower:
            context.key_concerns.append("optimization")
        if "secure" in query_lower or "security" in query_lower:
            context.key_concerns.append("security")
        if "performance" in query_lower or "optimize" in query_lower or "latency" in query_lower:
            context.key_concerns.append("performance")

        logger.info(
            f"Analyzed query: domains={context.identified_domains}, concerns={context.key_concerns}"
        )

        return context

    @staticmethod
    def generate_technical_response(
        context: TechnicalReasoningContext,
        parent_context: Optional[str] = None,
    ) -> Tuple[str, float]:
        """
        Generate a technically rigorous response with parent document context.

        Args:
            context: TechnicalReasoningContext from analysis
            parent_context: Parent document context for enrichment

        Returns:
            (response_text, confidence_score)
        """
        query = context.query
        response_parts = []

        # Attempt to use LLMFactory for real response
        prompt = f"Query: {query}\n\nContext:\n{parent_context or context.retrieved_results}"
        try:
            provider = LLMFactory.get_provider()
            llm_response = asyncio.run(provider.generate(
                prompt=prompt,
                system_prompt="You are AURA, a highly intelligent personal knowledge OS assistant."
            ))
            response = llm_response.get("content", str(llm_response))
            confidence = 0.95
        except Exception as e:
            logger.warning(f"Using fallback response due to LLM error: {e}")
            if not context.retrieved_results:
                # No knowledge base context available
                response = TechnicalReasoningEngine._generate_general_response(query)
                confidence = 0.5
            else:
                # Build knowledge-based response
                response_parts.append("## Technical Analysis\n")

                # Add explicit answer
                response_parts.append(f"**Query**: {query}\n")

                if parent_context:
                    response_parts.append("### Relevant Context from Knowledge Base\n")
                    response_parts.append(f"```\n{parent_context[:1000]}\n```\n")

                # Domain-specific analysis
                if "database" in context.identified_domains:
                    response_parts.append(
                        "\n### Database Considerations\n"
                        "- Use appropriate indexes for query optimization\n"
                        "- Consider normalized vs denormalized schemas\n"
                        "- Implement query caching where beneficial\n"
                    )

                if "security" in context.identified_domains:
                    response_parts.append(
                        "\n### Security Recommendations\n"
                        "- Validate and sanitize all inputs\n"
                        "- Use parameterized queries to prevent SQL injection\n"
                        "- Implement proper authentication and authorization\n"
                        "- Apply principle of least privilege\n"
                    )

                if "performance" in context.identified_domains:
                    response_parts.append(
                        "\n### Performance Optimization\n"
                        "- Profile before optimizing\n"
                        "- Use caching strategically\n"
                        "- Consider async/await for I/O operations\n"
                        "- Monitor key metrics\n"
                    )

                # Key technical details
                response_parts.append("\n### Key Technical Details\n")
                for result in context.retrieved_results[:3]:
                    response_parts.append(f"- {result.chunk_text[:200]}...\n")

                # Add references
                response_parts.append("\n### References\n")
                unique_sources = set(r.file_name for r in context.retrieved_results)
                for source in unique_sources:
                    response_parts.append(f"- {source}\n")

                response = "".join(response_parts)
                confidence = min(1.0, 0.7 + (len(context.retrieved_results) * 0.1))

        logger.info(f"Generated technical response: {len(response)} chars, confidence={confidence:.2f}")
        return response, confidence

    @staticmethod
    def _generate_general_response(query: str) -> str:
        """Generate response when no knowledge base context available."""
        return f"""# Technical Response

**Query**: {query}

Your knowledge base doesn't contain directly relevant information for this query. However, here are general technical considerations:

1. **Check Prerequisites**: Ensure you understand foundational concepts
2. **Narrow the Scope**: Break complex problems into smaller components
3. **Research Best Practices**: Look for industry-standard approaches
4. **Validate with Tests**: Verify your implementation with comprehensive tests
5. **Document Decisions**: Record architectural decisions and tradeoffs

**Recommendation**: Add relevant technical documentation to your knowledge base for more targeted responses.
"""

    @staticmethod
    def save_technical_interaction(
        db: Session,
        user_id: UUID,
        user_query: str,
        reasoning_response: str,
        retrieved_sources: List[SearchResult],
        confidence_score: float,
    ) -> bool:
        """
        Save technical reasoning interaction to conversation history.

        Args:
            db: Database session
            user_id: User ID
            user_query: Original query
            reasoning_response: Generated response
            retrieved_sources: Sources used
            confidence_score: Confidence in response

        Returns:
            True if saved successfully
        """
        try:
            from app.models import AuraState

            # Get or create AURA state (keeping for backward compatibility)
            aura_state = (
                db.query(AuraState).filter(AuraState.user_id == user_id).first()
            )

            if not aura_state:
                aura_state = AuraState(user_id=user_id)
                db.add(aura_state)
                db.flush()

            # Create conversation record
            conversation = ConversationHistory(
                aura_state_id=aura_state.id,
                user_id=user_id,
                user_message=user_query,
                aura_response=reasoning_response,
                persona_used="TECHNICAL",  # Technical reasoning engine
                retrieved_knowledge_ids=[r.chunk_id for r in retrieved_sources],
                confidence_score=confidence_score,
            )

            db.add(conversation)
            db.commit()

            logger.info("Saved technical interaction to conversation history")
            return True

        except Exception as e:
            logger.error(f"Error saving interaction: {e}")
            db.rollback()
            return False

    @staticmethod
    def process_technical_query(
        db: Session,
        user_id: UUID,
        query: str,
        use_parent_context: bool = True,
        context_range: int = 2,
    ) -> Tuple[str, float]:
        """
        End-to-end technical query processing pipeline.

        Args:
            db: Database session
            user_id: User ID
            query: Technical question
            use_parent_context: Whether to retrieve parent document context
            context_range: Context range for parent retrieval

        Returns:
            (response, confidence)
        """
        try:
            # Step 1: Semantic search
            retrieved_results = KnowledgeService.semantic_search(
                db, user_id, query, top_k=5, min_similarity=0.3
            )

            # Step 2: Analyze query and retrieve context
            context = TechnicalReasoningEngine.analyze_query(
                db, user_id, query, retrieved_results
            )

            parent_context = None
            if use_parent_context and retrieved_results:
                results_with_context = ParentDocumentRetriever.semantic_search_with_parent_context(
                    db, user_id, query, context_range=context_range
                )

                if results_with_context:
                    parent_context = ParentDocumentRetriever.build_rag_context(
                        results_with_context
                    )

            # Step 3: Generate technical response
            response, confidence = TechnicalReasoningEngine.generate_technical_response(
                context, parent_context
            )

            # Step 4: Save interaction
            TechnicalReasoningEngine.save_technical_interaction(
                db, user_id, query, response, retrieved_results, confidence
            )

            return response, confidence

        except Exception as e:
            logger.error(f"Error processing technical query: {e}")
            return "Error processing your query. Please try again.", 0.0
