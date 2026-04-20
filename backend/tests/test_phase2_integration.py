"""
Integration tests for Phase 2: Knowledge Graph, Entity Extraction, and Technical Reasoning.
"""

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, MagicMock

from app.services.entity_extraction import (
    EntityExtractor,
    RelationshipExtractor,
    ChunkEntityProcessor,
)
from app.services.technical_reasoning import (
    TechnicalReasoningEngine,
    TechnicalReasoningContext,
)
from app.services.parent_retrieval import ParentDocumentRetriever
from app.models import KnowledgeChunk, KnowledgeSource
from app.schemas import SearchResult


class TestEntityExtraction:
    """Test entity extraction from text chunks."""

    def test_technology_keyword_detection(self):
        """Detect technology entities from text."""
        text = "FastAPI is a web framework for building REST APIs with Python."

        entities = EntityExtractor.extract_entities(text)
        entity_names = [e[0] for e in entities]

        assert any("FastAPI" in name for name in entity_names)
        assert any("Python" in name for name in entity_names)
        assert any("REST" in name for name in entity_names)

    def test_methodology_extraction(self):
        """Extract software methodologies from text."""
        text = "Implement microservices architecture using RESTful APIs and CI/CD pipelines."

        entities = EntityExtractor.extract_entities(text)
        entity_types = {e[1] for e in entities}

        assert "METHODOLOGY" in entity_types

    def test_framework_detection(self):
        """Detect frameworks in text."""
        text = "Use Django for backend and React for frontend development."

        entities = EntityExtractor.extract_entities(text)
        entity_names = {e[0] for e in entities}

        assert any("Django" in name for name in entity_names)
        assert any("React" in name for name in entity_names)

    def test_camel_case_concept_extraction(self):
        """Extract CamelCase concept names."""
        text = "Implement VectorEmbedding and SemanticSearch using TransformerModels."

        entities = EntityExtractor.extract_entities(text)

        # Should detect camel case entities
        assert len(entities) > 0

    def test_quoted_concept_extraction(self):
        """Extract quoted concepts."""
        text = 'The "knowledge graph" stores "entity relationships" for "semantic reasoning".'

        entities = EntityExtractor.extract_entities(text)
        entity_names = {e[0].lower() for e in entities}

        assert any("knowledge graph" in name for name in entity_names)


class TestRelationshipExtraction:
    """Test relationship extraction between entities."""

    def test_implements_relationship(self):
        """Extract 'implements' relationships."""
        text = "FastAPI implements Rest architecture."
        entities = [("FastAPI", "FRAMEWORK"), ("Rest", "METHODOLOGY")]

        relationships = RelationshipExtractor.extract_relationships(text, entities)

        assert len(relationships) > 0
        assert any(rel[2] == "IMPLEMENTS" for rel in relationships)

    def test_depends_on_relationship(self):
        """Extract dependency relationships."""
        text = "React depends on JavaScript for runtime execution."
        entities = [("React", "FRAMEWORK"), ("JavaScript", "LANGUAGE")]

        relationships = RelationshipExtractor.extract_relationships(text, entities)

        # Should detect dependency
        assert len(relationships) > 0

    def test_extends_relationship(self):
        """Extract inheritance relationships."""
        text = "FastAPI extends Starlette framework."
        entities = [("FastAPI", "FRAMEWORK"), ("Starlette", "FRAMEWORK")]

        relationships = RelationshipExtractor.extract_relationships(text, entities)

        assert any(rel[2] == "EXTENDS" for rel in relationships)


class TestChunkEntityProcessing:
    """Test batch processing of chunks for entity extraction."""

    def test_process_single_chunk(self):
        """Process a single chunk for entities."""
        chunk_text = "PostgreSQL with pgvector enables semantic search on embeddings."
        chunk_id = str(uuid4())

        result = ChunkEntityProcessor.process_chunk(chunk_text, chunk_id)

        assert result["chunk_id"] == chunk_id
        assert len(result["entities"]) > 0
        assert "entity_count" in result
        assert "key_concepts" in result

    def test_batch_process_chunks(self):
        """Process multiple chunks efficiently."""
        chunks = [
            ("FastAPI: A modern web framework", "chunk-1"),
            ("PostgreSQL: A relational database", "chunk-2"),
            ("Neo4j: A graph database for relationships", "chunk-3"),
        ]

        results = ChunkEntityProcessor.batch_process_chunks(chunks)

        assert len(results) == 3
        assert all("entities" in r for r in results)
        assert all(r["entity_count"] > 0 for r in results)

    def test_cross_document_concept_detection(self):
        """Detect concepts appearing across multiple documents."""
        results = [
            {
                "chunk_id": "doc1-chunk1",
                "key_concepts": ["PostgreSQL", "Indexing", "Query Optimization"],
            },
            {
                "chunk_id": "doc2-chunk3",
                "key_concepts": ["PostgreSQL", "Performance", "Scaling"],
            },
            {
                "chunk_id": "doc3-chunk5",
                "key_concepts": ["Caching", "Performance", "Redis"],
            },
        ]

        cross_doc = ChunkEntityProcessor.extract_cross_document_concepts(results)

        # PostgreSQL and Performance appear in multiple documents
        assert "PostgreSQL" in cross_doc
        assert "Performance" in cross_doc
        assert len(cross_doc["PostgreSQL"]) == 2


class TestTechnicalReasoningEngine:
    """Test technical reasoning pipeline."""

    def test_query_analysis(self):
        """Analyze technical query for domain identification."""
        db_mock = Mock(spec=Session)

        query = "How do I optimize database queries in PostgreSQL?"
        results = [
            SearchResult(
                chunk_id=uuid4(),
                source_id=uuid4(),
                file_name="db_optimization.pdf",
                chunk_text="Use indexes and query planning.",
                similarity_score=0.85,
                metadata={},
            )
        ]

        context = TechnicalReasoningEngine.analyze_query(db_mock, uuid4(), query, results)

        assert "database" in context.identified_domains
        assert "optimization" in context.key_concerns
        assert context.requires_knowledge_base is True

    def test_response_generation_with_context(self):
        """Generate technical response with knowledge base context."""
        query = "Explain vector embeddings"
        results = [
            SearchResult(
                chunk_id=uuid4(),
                source_id=uuid4(),
                file_name="embeddings.pdf",
                chunk_text="Vector embeddings represent text as high-dimensional vectors.",
                similarity_score=0.9,
                metadata={},
            )
        ]

        context = TechnicalReasoningContext(query, results)

        response, confidence = TechnicalReasoningEngine.generate_technical_response(
            context, parent_context="Detailed explanation from PDF..."
        )

        assert len(response) > 0
        assert confidence > 0
        assert "Technical Analysis" in response

    def test_domain_specific_guidance(self):
        """Test domain-specific technical guidance."""
        security_query = "How to prevent SQL injection?"
        results = []

        context = TechnicalReasoningEngine.analyze_query(Mock(spec=Session), uuid4(), security_query, results)

        response, _ = TechnicalReasoningEngine.generate_technical_response(context)

        # Should include security recommendations
        assert ("security" in context.identified_domains) or ("Security" in response)

    def test_performance_optimization_guidance(self):
        """Test performance optimization recommendations."""
        perf_query = "How to optimize API response times?"
        results = []

        context = TechnicalReasoningEngine.analyze_query(Mock(spec=Session), uuid4(), perf_query, results)

        response, _ = TechnicalReasoningEngine.generate_technical_response(context)

        assert "performance" in context.key_concerns


class TestParentDocumentRetrieval:
    """Test parent document retrieval for RAG enrichment."""

    def test_parent_chunk_retrieval(self):
        """Retrieve surrounding context around target chunk."""
        db_mock = Mock(spec=Session)

        # Mock chunks
        mock_chunks = []
        for i in range(5):
            mock_chunk = Mock(spec=KnowledgeChunk)
            mock_chunk.id = uuid4()
            mock_chunk.chunk_index = i
            mock_chunk.chunk_text = f"Chunk {i} text"
            mock_chunks.append(mock_chunk)

        # Mock query
        db_mock.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            mock_chunks
        )

        source_id = uuid4()
        user_id = uuid4()
        target_index = 2

        chunks = ParentDocumentRetriever.get_parent_chunks(
            db_mock, user_id, source_id, target_index, context_range=2
        )

        assert len(chunks) >= 1

    def test_chunk_merging(self):
        """Merge chunks into cohesive parent context."""
        chunks = []
        for i in range(3):
            chunk = Mock(spec=KnowledgeChunk)
            chunk.chunk_text = f"Part {i} of the explanation. "
            chunks.append(chunk)

        merged = ParentDocumentRetriever.merge_parent_chunks(chunks)

        assert "Part 0" in merged
        assert "Part 2" in merged
        assert len(merged) > 0

    def test_rag_context_building(self):
        """Build RAG context respecting token limits."""
        results_with_context = [
            (
                SearchResult(
                    chunk_id=uuid4(),
                    source_id=uuid4(),
                    file_name="file1.pdf",
                    chunk_text="First result",
                    similarity_score=0.9,
                    metadata={},
                ),
                "Parent context from file 1...",
            ),
            (
                SearchResult(
                    chunk_id=uuid4(),
                    source_id=uuid4(),
                    file_name="file2.pdf",
                    chunk_text="Second result",
                    similarity_score=0.8,
                    metadata={},
                ),
                "Parent context from file 2...",
            ),
        ]

        context = ParentDocumentRetriever.build_rag_context(
            results_with_context, max_tokens=1000
        )

        assert "file1.pdf" in context
        assert "Parent context" in context


class TestEndToEndPipeline:
    """End-to-end integration tests."""

    def test_knowledge_graph_construction(self):
        """Test complete knowledge graph construction from chunks."""
        chunks = [
            "FastAPI is a Python framework for building REST APIs.",
            "PostgreSQL provides vector support for semantic search.",
            "FastAPI integrates well with PostgreSQL databases.",
        ]

        all_results = []
        for i, chunk_text in enumerate(chunks):
            result = ChunkEntityProcessor.process_chunk(chunk_text, f"chunk-{i}")
            all_results.append(result)

        # Should detect that FastAPI and PostgreSQL appear together
        cross_doc = ChunkEntityProcessor.extract_cross_document_concepts(all_results)

        # Both should appear in multiple chunks
        assert len(all_results) == 3
        assert all(r["entity_count"] > 0 for r in all_results)

    def test_technical_reasoning_with_knowledge_base(self):
        """Test full technical reasoning with knowledge base enrichment."""
        db_mock = Mock(spec=Session)

        # Mock user
        user_id = uuid4()

        # Mock search results
        search_results = [
            SearchResult(
                chunk_id=uuid4(),
                source_id=uuid4(),
                file_name="best_practices.pdf",
                chunk_text="Always use indexing for frequently queried columns.",
                similarity_score=0.85,
                metadata={},
            ),
            SearchResult(
                chunk_id=uuid4(),
                source_id=uuid4(),
                file_name="optimization.pdf",
                chunk_text="Query optimization reduces latency significantly.",
                similarity_score=0.81,
                metadata={},
            ),
        ]

        # Analyze
        context = TechnicalReasoningEngine.analyze_query(
            db_mock, user_id, "How to optimize database queries?", search_results
        )

        # Generate response
        response, confidence = TechnicalReasoningEngine.generate_technical_response(
            context, parent_context="Parent context from knowledge base..."
        )

        assert len(response) > 0
        assert confidence > 0.7
        assert "Technical Analysis" in response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
