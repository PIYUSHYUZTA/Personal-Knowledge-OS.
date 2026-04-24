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
import os

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
        logger.info("Generating technical response via LLM")
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
        # Structured prompt for architectural rigor
        system_prompt = (
            "You are AURA (Architectural Unified Reasoning Assistant), a high-end technical expert. "
            "Provide precise, rigorous analysis based ONLY on the provided context. "
            "If the answer is not in the context, use your internal knowledge to provide a general "
            "architectural best practice but clearly state it is not in the user's knowledge base. "
            "Focus on: Scalability, Security, Performance, and Clean Architecture."
        )

        prompt = (
            f"USER QUERY: {query}\n\n"
            f"TECHNICAL CONTEXT:\n{parent_context or context.retrieved_results}\n\n"
            "INSTRUCTIONS:\n"
            "1. Analyze the query against the provided context.\n"
            "2. Identify key architectural concerns.\n"
            "3. Propose an optimal technical approach.\n"
            "4. Highlight any security or performance tradeoffs.\n"
            "5. If context is missing, provide industry-standard best practices.\n"
            "\nRESPONSE STRUCTURE:\n"
            "## Technical Analysis\n[Your analysis]\n"
            "### Architectural Approach\n[Details]\n"
            "### Performance & Security\n[Tradeoffs]\n"
        )

        try:
            if os.getenv("AURA_ENABLE_LLM_RESPONSES", "false").lower() != "true":
                return TechnicalReasoningEngine._generate_contextual_response(
                    context,
                    parent_context,
                )

            # Inform LLM if grounding context is missing
            current_system_prompt = system_prompt
            if not context.retrieved_results:
                logger.info("No knowledge base context found; generating general technical response via LLM")
                current_system_prompt += " NOTE: No specific user documents were found. Provide a general technical answer but acknowledge that it is not grounded in the user's specific knowledge base."

            provider = LLMFactory.get_provider()
            try:
                asyncio.get_running_loop()
                raise RuntimeError("Synchronous technical response called from an active event loop")
            except RuntimeError as loop_error:
                if "active event loop" in str(loop_error):
                    raise

            llm_response = asyncio.run(provider.generate(
                prompt=prompt,
                system_prompt=current_system_prompt
            ))
            response = llm_response.get("content", str(llm_response))
            confidence = 0.95 if context.retrieved_results else 0.7
            return response, confidence

        except Exception as e:
            import traceback
            logger.error(f"TECHNICAL REASONING ERROR: {e}")
            logger.error(traceback.format_exc())
            logger.warning(f"Using manual fallback response due to error: {e}")
            
            # Static fallback if LLM fails
            if not context.retrieved_results:
                return TechnicalReasoningEngine._generate_general_response(query), 0.5

            # Manual construction if LLM fails but we HAVE context
            response_parts = ["## Technical Analysis (Manual Fallback)\n"]
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
                )

            return "\n".join(response_parts), 0.6

        except Exception as e:
            import traceback
            logger.error(f"TECHNICAL REASONING ERROR: {e}")
            logger.error(traceback.format_exc())
            return TechnicalReasoningEngine._generate_general_response(query), 0.5

    @staticmethod
    def _generate_contextual_response(
        context: TechnicalReasoningContext,
        parent_context: Optional[str] = None,
    ) -> Tuple[str, float]:
        """Generate a deterministic technical answer without external LLM latency."""
        query = context.query
        response_parts = ["## Technical Analysis\n", f"**Query**: {query}\n"]

        if parent_context:
            response_parts.append("### Relevant Knowledge Base Context\n")
            response_parts.append(parent_context[:1500])
            response_parts.append("\n")
        elif context.retrieved_results:
            response_parts.append("### Relevant Knowledge Base Context\n")
            for result in context.retrieved_results[:3]:
                response_parts.append(f"- {result.file_name}: {result.chunk_text}\n")
        else:
            response_parts.append(
                "This answer is based on general engineering practice because no matching knowledge-base context was found.\n"
            )

        response_parts.append("### Architectural Approach\n")
        if "security" in context.identified_domains:
            response_parts.append(
                "- Validate and parameterize all inputs; avoid string-built queries.\n"
                "- Use least-privilege credentials and keep sensitive details out of responses and logs.\n"
            )
        if "database" in context.identified_domains:
            response_parts.append(
                "- Add indexes for frequently filtered or joined columns.\n"
                "- Check query plans before changing schema or denormalizing data.\n"
            )
        if "performance" in context.identified_domains:
            response_parts.append(
                "- Measure latency first, cache stable reads, and remove expensive work from request paths.\n"
                "- Keep response payloads compact and paginate large datasets.\n"
            )
        if not context.identified_domains:
            response_parts.append(
                "- Break the problem into validation, data access, business logic, and operational concerns.\n"
            )

        response_parts.append("### Performance & Security\n")
        response_parts.append(
            "Prefer explicit validation, bounded resource usage, consistent error handling, and tests around failure paths.\n"
        )

        confidence = 0.85 if context.retrieved_results else 0.65
        return "\n".join(response_parts), confidence

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
            from app.models import KnowledgeSource

            has_sources = db.query(KnowledgeSource.id).filter(KnowledgeSource.user_id == user_id).first()
            retrieved_results = []
            if has_sources:
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
