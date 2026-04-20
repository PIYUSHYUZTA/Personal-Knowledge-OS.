"""
Test suite for AURA dual-persona logic.
Validates persona detection, switching, and response generation.
"""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch

from app.services.aura_service import AuraService, PersonaType
from app.models import User, AuraState, ConversationHistory


class TestAuraPersonaDetection:
    """Test automatic persona detection based on query keywords."""

    def test_advisor_keyword_detection(self):
        """Queries with technical keywords should trigger Advisor persona."""
        technical_queries = [
            "How do I implement a REST API?",
            "Explain the architecture of the system",
            "Debug this code snippet for me",
            "What's the best way to optimize this?",
            "How should I structure the database?",
        ]

        for query in technical_queries:
            persona = AuraService.detect_persona(query)
            assert persona == PersonaType.ADVISOR, f"Failed for query: {query}"

    def test_friend_keyword_detection(self):
        """Queries with emotional keywords should trigger Friend persona."""
        empathetic_queries = [
            "I'm feeling overwhelmed with the project",
            "Why is this so complicated?",
            "Can you help me understand this better?",
            "I need some motivation to keep going",
            "I feel very unsure about my approach",
        ]

        for query in empathetic_queries:
            persona = AuraService.detect_persona(query)
            assert persona == PersonaType.FRIEND, f"Failed for query: {query}"

    def test_mixed_keywords_defaults_to_advisor(self):
        """If keywords are mixed or absent, default to Advisor."""
        neutral_queries = [
            "Tell me about Python",
            "What is machine learning?",
            "Summarize this document",
        ]

        for query in neutral_queries:
            persona = AuraService.detect_persona(query)
            assert persona == PersonaType.ADVISOR, f"Failed for query: {query}"

    def test_case_insensitivity(self):
        """Persona detection should be case-insensitive."""
        query_lower = "how do i debug this"
        query_upper = "HOW DO I DEBUG THIS"
        query_mixed = "HoW dO i DeBuG tHiS"

        for query in [query_lower, query_upper, query_mixed]:
            persona = AuraService.detect_persona(query)
            assert persona == PersonaType.ADVISOR


class TestAuraStateManagement:
    """Test AURA state creation and persistence."""

    def test_get_or_create_aura_state(self):
        """Should create new AURA state if none exists."""
        # Mock database session
        db_mock = Mock(spec=Session)
        db_mock.query.return_value.filter.return_value.first.return_value = None

        user_id = uuid4()

        # Patch db.add and db.commit
        db_mock.add = Mock()
        db_mock.commit = Mock()
        db_mock.refresh = Mock()

        state = AuraService.get_or_create_aura_state(db_mock, user_id)

        assert state.user_id == user_id
        assert state.current_persona == PersonaType.ADVISOR
        assert state.context_window == 5

    def test_retrieve_existing_aura_state(self):
        """Should return existing AURA state if already created."""
        db_mock = Mock(spec=Session)

        existing_state = Mock(spec=AuraState)
        existing_state.current_persona = PersonaType.FRIEND
        existing_state.context_window = 7

        db_mock.query.return_value.filter.return_value.first.return_value = existing_state

        user_id = uuid4()
        state = AuraService.get_or_create_aura_state(db_mock, user_id)

        assert state == existing_state
        assert state.current_persona == PersonaType.FRIEND


class TestAuraResponseGeneration:
    """Test response generation with persona-specific tone."""

    def test_advisor_response_generation(self):
        """Advisor persona should generate technical, precise responses."""
        db_mock = Mock(spec=Session)

        # Mock AURA state
        aura_state_mock = Mock(spec=AuraState)
        aura_state_mock.current_persona = PersonaType.ADVISOR

        with patch.object(
            AuraService, "get_or_create_aura_state", return_value=aura_state_mock
        ):
            db_mock.commit = Mock()

            response, persona, confidence = AuraService.generate_response(
                db_mock,
                user_id=uuid4(),
                query="How do I implement async/await in Python?",
                retrieved_results=[],
            )

            assert persona == PersonaType.ADVISOR
            assert confidence > 0.5
            assert "Analysis" in response or "Technical" in response
            assert isinstance(response, str)

    def test_friend_response_generation(self):
        """Friend persona should generate warm, empathetic responses."""
        db_mock = Mock(spec=Session)

        # Mock AURA state
        aura_state_mock = Mock(spec=AuraState)
        aura_state_mock.current_persona = PersonaType.FRIEND

        with patch.object(
            AuraService, "get_or_create_aura_state", return_value=aura_state_mock
        ):
            db_mock.commit = Mock()

            response, persona, confidence = AuraService.generate_response(
                db_mock,
                user_id=uuid4(),
                query="I'm struggling to understand this concept",
                retrieved_results=[],
            )

            assert persona == PersonaType.FRIEND
            assert confidence > 0.5
            assert "help" in response.lower() or "understand" in response.lower()

    def test_response_with_retrieved_context(self):
        """Responses should incorporate retrieved knowledge chunks."""
        from app.schemas import SearchResult

        db_mock = Mock(spec=Session)
        aura_state_mock = Mock(spec=AuraState)

        with patch.object(
            AuraService, "get_or_create_aura_state", return_value=aura_state_mock
        ):
            db_mock.commit = Mock()

            # Create mock search results
            result = SearchResult(
                chunk_id=uuid4(),
                source_id=uuid4(),
                file_name="test.pdf",
                chunk_text="This is relevant information about the topic.",
                similarity_score=0.85,
                metadata={"page": 1},
            )

            response, _, _ = AuraService.generate_response(
                db_mock,
                user_id=uuid4(),
                query="What is the main topic?",
                retrieved_results=[result],
            )

            assert "relevant information" in response.lower() or (
                "knowledge base" in response.lower()
            )


class TestAuraConversationHistory:
    """Test conversation history storage and retrieval."""

    def test_save_conversation(self):
        """Should save conversation to database with all metadata."""
        db_mock = Mock(spec=Session)

        # Mock AURA state retrieval
        aura_state_mock = Mock(spec=AuraState)
        aura_state_mock.id = uuid4()

        with patch.object(
            AuraService, "get_or_create_aura_state", return_value=aura_state_mock
        ):
            db_mock.add = Mock()
            db_mock.commit = Mock()
            db_mock.refresh = Mock()

            user_id = uuid4()
            conversation = AuraService.save_conversation(
                db_mock,
                user_id=user_id,
                user_message="How do I learn Python?",
                aura_response="Here's a comprehensive guide...",
                persona_used=PersonaType.ADVISOR,
                retrieved_knowledge_ids=[uuid4(), uuid4()],
                confidence_score=0.82,
            )

            assert conversation.user_message == "How do I learn Python?"
            assert conversation.aura_response == "Here's a comprehensive guide..."
            assert conversation.persona_used == PersonaType.ADVISOR
            assert conversation.confidence_score == 0.82
            assert len(conversation.retrieved_knowledge_ids) == 2

    def test_get_conversation_context(self):
        """Should retrieve last N conversations for context."""
        db_mock = Mock(spec=Session)

        # Create mock conversations
        conv_mocks = [Mock(spec=ConversationHistory) for _ in range(5)]

        db_mock.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            conv_mocks
        )

        user_id = uuid4()
        conversations = AuraService.get_conversation_context(db_mock, user_id, limit=5)

        assert len(conversations) == 5


class TestPersonaConsistency:
    """Test that persona selections are consistent and appropriate."""

    def test_advisor_tone_consistency(self):
        """Advisor responses should maintain technical tone."""
        advisor_keywords = ["technical", "analysis", "recommendation", "implement"]

        query = "How do I optimize database queries?"
        persona = AuraService.detect_persona(query)

        response, detected_persona, _ = AuraService.generate_response(
            Mock(spec=Session),
            user_id=uuid4(),
            query=query,
            retrieved_results=[],
        )

        assert detected_persona == PersonaType.ADVISOR
        # Check that response contains technical language
        response_lower = response.lower()
        has_technical_language = any(kw in response_lower for kw in advisor_keywords)
        assert has_technical_language or "technical" in response_lower

    def test_friend_tone_consistency(self):
        """Friend responses should maintain empathetic tone."""
        empathetic_keywords = ["understand", "help", "support", "encouragement"]

        query = "I'm struggling with this concept"
        persona = AuraService.detect_persona(query)

        response, detected_persona, _ = AuraService.generate_response(
            Mock(spec=Session),
            user_id=uuid4(),
            query=query,
            retrieved_results=[],
        )

        assert detected_persona == PersonaType.FRIEND
        # Check that response contains empathetic language
        response_lower = response.lower()
        has_empathetic_language = any(kw in response_lower for kw in empathetic_keywords)
        assert has_empathetic_language or "here to" in response_lower


class TestPersonaTransitions:
    """Test smooth transitions between personas."""

    def test_persona_switching_in_conversation(self):
        """User should be able to switch personas within same session."""
        db_mock = Mock(spec=Session)
        aura_state_mock = Mock(spec=AuraState)

        with patch.object(
            AuraService, "get_or_create_aura_state", return_value=aura_state_mock
        ):
            db_mock.commit = Mock()

            user_id = uuid4()

            # First message: technical
            _, persona1, _ = AuraService.generate_response(
                db_mock, user_id, "Debug this code", []
            )
            assert persona1 == PersonaType.ADVISOR

            # Second message: emotional
            _, persona2, _ = AuraService.generate_response(
                db_mock, user_id, "I'm stuck and frustrated", []
            )
            assert persona2 == PersonaType.FRIEND

            # Personas should be different
            assert persona1 != persona2


class TestMPCSecurityIntegration:
    """Test MPC security layer with AURA."""

    def test_aura_response_with_mpc_enabled(self):
        """AURA should work seamlessly with MPC security."""
        from app.core.security import generate_mpc_handshake, compute_mpc_hash

        # Generate MPC challenge
        with patch('app.core.security.settings.MPC_ENABLED', True):
            challenge = generate_mpc_handshake()
        assert challenge  # Should be non-empty

        # Compute MPC hash
        hash_value = compute_mpc_hash(challenge)
        assert hash_value is not None
        assert len(hash_value) > 0

        # AURA should continue functioning with MPC enabled
        db_mock = Mock(spec=Session)
        aura_state_mock = Mock(spec=AuraState)

        with patch.object(
            AuraService, "get_or_create_aura_state", return_value=aura_state_mock
        ):
            db_mock.commit = Mock()

            response, persona, confidence = AuraService.generate_response(
                db_mock,
                user_id=uuid4(),
                query="Test query with MPC enabled",
                retrieved_results=[],
            )

            assert response is not None
            assert persona in [PersonaType.ADVISOR, PersonaType.FRIEND]
            assert confidence > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
