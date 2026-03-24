"""
Agentic Reasoning with LangGraph.

Multi-step reasoning chains for complex problem-solving:
1. Search Vector DB for context
2. Verify facts against Neo4j knowledge graph
3. Synthesize code/solutions if needed
4. Final technical answer with confidence

State management with LangGraph - graph-based agent orchestration.
"""

from typing import Optional, Dict, Any, List, Annotated
import logging
from enum import Enum
from datetime import datetime
import json

from langchain.schema import HumanMessage, AIMessage
from langchain.tools import Tool
import operator

logger = logging.getLogger(__name__)


class ReasoningStep(str, Enum):
    """Reasoning pipeline steps."""
    ANALYZE = "analyze_query"  # Parse intent + complexity
    SEARCH = "search_knowledge"  # Vector DB search
    VERIFY = "verify_facts"  # Neo4j validation
    SYNTHESIZE = "synthesize"  # Generate solution
    FINALIZE = "finalize_response"  # Format output


class AgentState:
    """
    Graph state for multi-step reasoning.

    Tracks execution through the reasoning pipeline.
    """

    def __init__(self, user_query: str):
        self.user_query = user_query
        self.step = ReasoningStep.ANALYZE
        self.intermediate_results: Dict[str, Any] = {}
        self.confidence_scores: Dict[str, float] = {}
        self.tool_calls: List[str] = []
        self.errors: List[str] = []
        self.final_response = ""
        self.execution_time_ms = 0
        self.metadata = {
            "started_at": datetime.utcnow().isoformat(),
            "reasoning_path": [],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_query": self.user_query,
            "current_step": self.step.value,
            "intermediate_results": self.intermediate_results,
            "confidence_scores": self.confidence_scores,
            "tool_calls": self.tool_calls,
            "final_response": self.final_response,
            "metadata": self.metadata,
        }


class MultiStepReasoningChain:
    """
    LangGraph-style multi-step reasoning agent.

    Pipeline:
    1. ANALYZE: Parse query intent and complexity
    2. SEARCH: Get relevant knowledge chunks
    3. VERIFY: Cross-check facts in knowledge graph
    4. SYNTHESIZE: Generate answer/code if needed
    5. FINALIZE: Format and confidence-score response
    """

    def __init__(self, llm_provider, knowledge_service, graph_service):
        """Initialize reasoning chain."""
        self.llm = llm_provider
        self.knowledge_service = knowledge_service
        self.graph_service = graph_service

    async def reason(self, query: str) -> Dict[str, Any]:
        """
        Execute multi-step reasoning chain.

        Returns:
        {
            "response": "final answer",
            "reasoning_steps": [
                {"step": "analyze", "output": "Query is asking about..."},
                {"step": "search", "results": [...], "confidence": 0.85},
                {"step": "verify", "facts": [...], "confidence": 0.92},
                {"step": "synthesize", "code": "...", "explanation": "..."},
                {"step": "finalize", "answer": "...", "confidence": 0.89}
            ],
            "execution_time_ms": 2345,
            "confidence": 0.89
        }
        """
        import time
        start_time = time.time()

        state = AgentState(query)
        reasoning_steps = []

        try:
            # Step 1: ANALYZE
            logger.info(f"[ANALYZE] Query: {query}")
            analysis = await self._analyze_query(query)
            state.intermediate_results["analysis"] = analysis
            state.confidence_scores["analysis"] = analysis.get("confidence", 0.8)
            reasoning_steps.append({
                "step": "analyze",
                "output": analysis,
                "state": AgentState(query).to_dict()
            })
            state.metadata["reasoning_path"].append("analyze")

            # Step 2: SEARCH
            logger.info("[SEARCH] Searching knowledge base...")
            search_results = await self._search_knowledge(
                query,
                analysis.get("search_terms", [query])
            )
            state.intermediate_results["search"] = search_results
            state.confidence_scores["search"] = search_results.get("confidence", 0.7)
            reasoning_steps.append({
                "step": "search",
                "results_count": len(search_results.get("chunks", [])),
                "confidence": search_results.get("confidence", 0),
            })
            state.metadata["reasoning_path"].append("search")
            state.tool_calls.append("search_vector_db")

            # Step 3: VERIFY
            logger.info("[VERIFY] Verifying facts against knowledge graph...")
            verification = await self._verify_facts(
                query,
                search_results.get("chunks", []),
                analysis.get("entities", [])
            )
            state.intermediate_results["verify"] = verification
            state.confidence_scores["verify"] = verification.get("confidence", 0.8)
            reasoning_steps.append({
                "step": "verify",
                "facts_checked": len(verification.get("verified_facts", [])),
                "confidence": verification.get("confidence", 0),
            })
            state.metadata["reasoning_path"].append("verify")
            state.tool_calls.append("query_knowledge_graph")

            # Step 4: SYNTHESIZE
            logger.info("[SYNTHESIZE] Synthesizing response...")
            synthesis = await self._synthesize_answer(
                query,
                analysis,
                search_results,
                verification
            )
            state.intermediate_results["synthesize"] = synthesis
            state.confidence_scores["synthesize"] = synthesis.get("confidence", 0.8)
            reasoning_steps.append({
                "step": "synthesize",
                "code_generated": synthesis.get("has_code", False),
                "confidence": synthesis.get("confidence", 0),
            })
            state.metadata["reasoning_path"].append("synthesize")

            # Step 5: FINALIZE
            logger.info("[FINALIZE] Finalizing response...")
            final_response = await self._finalize_response(
                query,
                synthesis,
                state.confidence_scores
            )
            state.final_response = final_response.get("response", "")
            state.confidence_scores["final"] = final_response.get("confidence", 0.8)
            reasoning_steps.append({
                "step": "finalize",
                "response_length": len(state.final_response),
                "confidence": final_response.get("confidence", 0),
            })
            state.metadata["reasoning_path"].append("finalize")

            # Calculate overall confidence as weighted average
            overall_confidence = sum(state.confidence_scores.values()) / max(1, len(state.confidence_scores))

            elapsed_ms = (time.time() - start_time) * 1000

            return {
                "status": "success",
                "response": state.final_response,
                "reasoning_steps": reasoning_steps,
                "execution_time_ms": int(elapsed_ms),
                "confidence": round(overall_confidence, 3),
                "tools_used": list(set(state.tool_calls)),
                "metadata": state.metadata,
            }

        except Exception as e:
            logger.error(f"Error in reasoning chain: {e}", exc_info=True)
            elapsed_ms = (time.time() - start_time) * 1000

            return {
                "status": "error",
                "error": str(e),
                "response": f"Error during reasoning: {str(e)}",
                "reasoning_steps": reasoning_steps,
                "execution_time_ms": int(elapsed_ms),
                "confidence": 0.0,
            }

    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Step 1: Analyze query intent and extract key elements."""
        analyze_prompt = f"""
Analyze this query and extract:
1. Intent (what is the user asking?)
2. Key concepts or entities mentioned
3. Search terms to use in vector DB
4. Complexity level (simple/moderate/complex)

Query: {query}

Respond JSON:
{{
    "intent": "...",
    "entities": ["entity1", "entity2"],
    "search_terms": ["term1", "term2"],
    "complexity": "moderate",
    "confidence": 0.9
}}"""

        response = await self.llm.generate(prompt=analyze_prompt)
        content = response.get("content", "{}")

        try:
            return json.loads(content)
        except:
            return {
                "intent": query,
                "entities": [],
                "search_terms": [query],
                "complexity": "moderate",
                "confidence": 0.6
            }

    async def _search_knowledge(self, query: str, search_terms: List[str]) -> Dict[str, Any]:
        """Step 2: Search vector DB for relevant context."""
        try:
            chunks = []
            for term in search_terms[:3]:  # Search top 3 terms
                try:
                    results = self.knowledge_service.search(
                        query=term,
                        limit=3,
                        threshold=0.5
                    )
                    chunks.extend(results)
                except:
                    pass

            # Deduplicate
            unique_chunks = {r.get("chunk_id"): r for r in chunks}

            return {
                "chunks": list(unique_chunks.values())[:10],
                "search_terms_used": search_terms,
                "confidence": min(0.95, 0.7 + (len(unique_chunks) * 0.05)),
            }

        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return {"chunks": [], "confidence": 0.0, "error": str(e)}

    async def _verify_facts(
        self,
        query: str,
        chunks: List[Dict],
        entities: List[str]
    ) -> Dict[str, Any]:
        """Step 3: Cross-check facts against Neo4j knowledge graph."""
        try:
            if not self.graph_service:
                return {"verified_facts": [], "confidence": 0.5}

            verified_facts = []

            for entity in entities[:5]:
                cypher = f"""
                MATCH (e:Entity)-[r]-(e2:Entity)
                WHERE e.name CONTAINS '{entity}'
                RETURN e.name as entity, r.type as relationship, e2.name as related
                LIMIT 5
                """

                try:
                    results = self.graph_service.execute_query(cypher)
                    verified_facts.extend(results or [])
                except:
                    pass

            return {
                "verified_facts": verified_facts[:10],
                "entities_checked": entities,
                "confidence": min(0.98, 0.7 + (len(verified_facts) * 0.05)),
            }

        except Exception as e:
            logger.warning(f"Verification failed: {e}")
            return {"verified_facts": [], "confidence": 0.5}

    async def _synthesize_answer(
        self,
        query: str,
        analysis: Dict[str, Any],
        search_results: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 4: Synthesize answer using context + reasoning."""
        context = {
            "chunks": search_results.get("chunks", [])[:5],
            "verified_facts": verification.get("verified_facts", [])[:5],
        }

        synthesis_prompt = f"""
Based on this context, answer the user's query with technical accuracy.

QUERY: {query}

KNOWLEDGE CONTEXT:
{json.dumps(context, indent=2)}

ANALYSIS: {json.dumps(analysis)}

Provide:
1. Direct answer to the query
2. Relevant code example if applicable
3. Key points to remember

Keep response concise but comprehensive."""

        response = await self.llm.generate(prompt=synthesis_prompt)

        return {
            "response_draft": response.get("content", ""),
            "has_code": "```" in response.get("content", ""),
            "confidence": 0.85,
        }

    async def _finalize_response(
        self,
        query: str,
        synthesis: Dict[str, Any],
        confidence_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Step 5: Finalize response with confidence scoring."""
        response_draft = synthesis.get("response_draft", "")

        # Calculate final confidence
        avg_confidence = sum(confidence_scores.values()) / max(1, len(confidence_scores))

        finalization_prompt = f"""
Review this response for quality and accuracy:

RESPONSE:
{response_draft}

Score from 0-1: How confident are you in this answer?
Respond with a single decimal 0.0-1.0"""

        confidence_response = await self.llm.generate(prompt=finalization_prompt)

        try:
            score = float(confidence_response.get("content", str(avg_confidence)).strip())
            final_confidence = min(0.99, max(0.1, score))
        except:
            final_confidence = avg_confidence

        # Add confidence disclaimer if low
        if final_confidence < 0.6:
            response_draft += f"\n\n⚠️ Confidence: {final_confidence:.1%}. Verify this information."

        return {
            "response": response_draft,
            "confidence": final_confidence,
        }
