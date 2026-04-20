"""
AURA service: dual-persona AI logic (Advisor vs Friend).
Handles persona switching based on query context and user preferences.
"""

from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.models import AuraState, ConversationHistory, PersonaType, User
from app.schemas import AuraMessageResponse, SearchResult
from app.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)

class AuraService:
    """AURA AI service with dual-persona logic."""

    # Persona characteristics
    PERSONAS = {
        PersonaType.ADVISOR: {
            "name": "Technical Advisor",
            "description": "Precise, technical, efficient communication",
            "tone": "professional",
            "keywords": ["explain", "how", "technical", "debug", "implement", "architecture"],
            "max_context": 10,
        },
        PersonaType.FRIEND: {
            "name": "Supportive Friend",
            "description": "Empathetic, conversational, warm communication",
            "tone": "friendly",
            "keywords": ["feel", "help", "understand", "why", "motivat", "encourage", "struggling", "stuck", "frustrate"],
            "max_context": 5,
        }
    }

    @staticmethod
    def get_or_create_aura_state(db: Session, user_id: UUID) -> AuraState:
        """Get existing AURA state or create new one."""
        state = db.query(AuraState).filter(AuraState.user_id == user_id).first()

        if not state:
            state = AuraState(
                user_id=user_id,
                current_persona=PersonaType.ADVISOR,
                context_window=5
            )
            db.add(state)
            db.commit()
            db.refresh(state)

        return state

    @staticmethod
    def detect_persona(query: str) -> PersonaType:
        """
        Automatically detect appropriate persona based on query content.

        Uses simple keyword matching; can be upgraded to ML-based classification.

        Returns:
            PersonaType.ADVISOR or PersonaType.FRIEND
        """
        query_lower = query.lower()

        advisor_score = 0
        friend_score = 0

        # Check for persona keywords
        for keyword in AuraService.PERSONAS[PersonaType.ADVISOR]["keywords"]:
            if keyword in query_lower:
                advisor_score += 1

        for keyword in AuraService.PERSONAS[PersonaType.FRIEND]["keywords"]:
            if keyword in query_lower:
                friend_score += 1

        # Default to advisor if no clear preference
        if advisor_score >= friend_score:
            return PersonaType.ADVISOR
        else:
            return PersonaType.FRIEND

    @staticmethod
    def generate_response(
        db: Session,
        user_id: UUID,
        query: str,
        retrieved_results: List[SearchResult]
    ) -> Tuple[str, PersonaType, float]:
        """
        Generate AURA response with persona-appropriate tone.

        In production, this would integrate with an LLM (OpenAI, Anthropic, local Ollama, etc.).
        For now, returns a template response.

        Args:
            db: Database session
            user_id: User ID
            query: User's query
            retrieved_results: Search results from knowledge base

        Returns:
            (response_text, persona_used, confidence_score)
        """
        try:
            # Get or create AURA state
            aura_state = AuraService.get_or_create_aura_state(db, user_id)

            # Detect appropriate persona
            detected_persona = AuraService.detect_persona(query)
            aura_state.current_persona = detected_persona
            db.commit()

            # Get persona definition
            persona_info = AuraService.PERSONAS[detected_persona]

            # Build context from retrieved results
            context = ""
            if retrieved_results:
                context = "Based on your knowledge base:\n"
                for i, result in enumerate(retrieved_results[:3], 1):
                    context += f"\n{i}. {result.chunk_text[:200]}..."

            # Generate persona-appropriate response
            if detected_persona == PersonaType.ADVISOR:
                response = f"""**Technical Analysis**

Query: {query}

{context if context else "No directly relevant information found in knowledge base."}

**Recommendation:** Review the retrieved documents and search for more specific technical details if needed.

---
*In production, this would be powered by a state-of-the-art language model for more comprehensive analysis.*"""
                confidence = 0.65

            else:  # FRIEND persona
                response = f"""I understand you're asking about: *{query}*

Let me help you with this!

{context if context else "While I don't have direct information in your knowledge base, let's think through this together."}

**What would help:**
- Is there a specific aspect you'd like me to explore deeper?
- Would you like to add more resources to your knowledge base?
- How are you feeling about this topic?

I'm here to support your learning journey! 🌟

---
*In production, this would be personalized by advanced AI for genuine conversation.*"""
                confidence = 0.58

            return response, detected_persona, confidence

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I encountered an error processing your query. Please try again.", PersonaType.ADVISOR, 0.0

    @staticmethod
    def save_conversation(
        db: Session,
        user_id: UUID,
        user_message: str,
        aura_response: str,
        persona_used: PersonaType,
        retrieved_knowledge_ids: List[UUID],
        confidence_score: float
    ) -> ConversationHistory:
        """Save conversation to history."""
        aura_state = AuraService.get_or_create_aura_state(db, user_id)

        conversation = ConversationHistory(
            aura_state_id=aura_state.id,
            user_id=user_id,
            user_message=user_message,
            aura_response=aura_response,
            persona_used=persona_used,
            retrieved_knowledge_ids=retrieved_knowledge_ids,
            confidence_score=confidence_score
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        return conversation

    @staticmethod
    def get_conversation_context(
        db: Session,
        user_id: UUID,
        limit: int = 5
    ) -> List[ConversationHistory]:
        """Get recent conversation history for context."""
        return db.query(ConversationHistory).filter(
            ConversationHistory.user_id == user_id
        ).order_by(ConversationHistory.created_at.desc()).limit(limit).all()
