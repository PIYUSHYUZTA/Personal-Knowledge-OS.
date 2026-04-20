"""
Entity Extraction Pipeline.
Identifies concepts, technologies, and relationships from text chunks.
"""

from typing import List, Tuple, Dict, Any, Optional
import logging
import re

try:
    import spacy
except ImportError:
    spacy = None

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# ENTITY EXTRACTION STRATEGIES
# ============================================================================


class EntityType:
    """Entity type definitions for knowledge graph."""

    CONCEPT = "CONCEPT"  # Abstract ideas (REST, algorithm, recursion)
    TECHNOLOGY = "TECHNOLOGY"  # Tools and platforms (FastAPI, PostgreSQL)
    LANGUAGE = "LANGUAGE"  # Programming languages (Python, JavaScript)
    FRAMEWORK = "FRAMEWORK"  # Frameworks (React, Django)
    LIBRARY = "LIBRARY"  # Libraries (NumPy, requests)
    AUTHOR = "AUTHOR"  # People who created things
    METHODOLOGY = "METHODOLOGY"  # Design patterns, methodologies
    DATA_STRUCTURE = "DATA_STRUCTURE"  # Lists, trees, graphs, etc.


class EntityExtractor:
    """
    Extracts entities (concepts, technologies, etc.) from text.
    Uses spaCy NER + custom heuristics for domain-specific extraction.
    """

    # Domain-specific entity mappings
    TECHNOLOGY_KEYWORDS = {
        "fastapi",
        "django",
        "flask",
        "postgresql",
        "mongodb",
        "redis",
        "elasticsearch",
        "kafka",
        "docker",
        "kubernetes",
        "terraform",
        "react",
        "vue",
        "angular",
        "node.js",
        "ner",
        "nlp",
        "pytorch",
        "tensorflow",
        "scikit-learn",
        "pandas",
        "numpy",
        "neo4j",
    }

    LANGUAGE_KEYWORDS = {
        "python",
        "javascript",
        "typescript",
        "java",
        "c++",
        "c#",
        "go",
        "rust",
        "ruby",
        "php",
        "scala",
        "kotlin",
        "swift",
        "sql",
        "html",
        "css",
    }

    FRAMEWORK_KEYWORDS = {
        "django",
        "fastapi",
        "flask",
        "react",
        "vue",
        "angular",
        "spring",
        "rails",
        "laravel",
        "express",
    }

    METHODOLOGY_KEYWORDS = {
        "rest",
        "graphql",
        "microservices",
        "monolith",
        "serverless",
        "mvp",
        "ci/cd",
        "devops",
        "agile",
        "scrum",
        "kanban",
        "tdd",
        "bdd",
        "ddd",
        "solid",
        "dry",
        "kiss",
    }

    _nlp = None

    @classmethod
    def load_spacy_model(cls):
        """Load spaCy model for NER."""
        if cls._nlp is None and spacy:
            try:
                cls._nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy model loaded")
            except OSError:
                logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
                cls._nlp = None

        return cls._nlp

    @classmethod
    def extract_entities(cls, text: str) -> List[Tuple[str, str]]:
        """
        Extract entities from text.

        Returns:
            List of (entity_name, entity_type) tuples
        """
        entities = []

        # 1. Keyword-based extraction
        entities.extend(cls._extract_by_keywords(text))

        # 2. spaCy NER (if available)
        if spacy:
            entities.extend(cls._extract_by_spacy(text))

        # 3. Pattern-based extraction
        entities.extend(cls._extract_by_patterns(text))

        # Deduplicate and return
        seen = set()
        unique_entities = []

        for entity_name, entity_type in entities:
            key = (entity_name.lower(), entity_type)
            if key not in seen:
                seen.add(key)
                unique_entities.append((entity_name, entity_type))

        logger.info(f"Extracted {len(unique_entities)} entities from text")
        return unique_entities

    @classmethod
    def _extract_by_keywords(cls, text: str) -> List[Tuple[str, str]]:
        """Extract entities using predefined keywords."""
        entities = []
        text_lower = text.lower()

        # Technologies
        for keyword in cls.TECHNOLOGY_KEYWORDS:
            if keyword in text_lower:
                entities.append((keyword.title(), EntityType.TECHNOLOGY))

        # Languages
        for keyword in cls.LANGUAGE_KEYWORDS:
            if keyword in text_lower:
                entities.append((keyword.title(), EntityType.LANGUAGE))

        # Frameworks
        for keyword in cls.FRAMEWORK_KEYWORDS:
            if keyword in text_lower:
                entities.append((keyword.title(), EntityType.FRAMEWORK))

        # Methodologies
        for keyword in cls.METHODOLOGY_KEYWORDS:
            if keyword in text_lower:
                entities.append((keyword.upper(), EntityType.METHODOLOGY))

        return entities

    @classmethod
    def _extract_by_spacy(cls, text: str) -> List[Tuple[str, str]]:
        """Extract entities using spaCy NER."""
        nlp = cls.load_spacy_model()
        if not nlp:
            return []

        try:
            doc = nlp(text[:1000])  # Limit to first 1000 chars for performance

            entities = []
            for ent in doc.ents:
                # Map spaCy entity types to our types
                if ent.label_ in ["PERSON"]:
                    entities.append((ent.text, EntityType.AUTHOR))
                elif ent.label_ in ["ORG", "PRODUCT"]:
                    entities.append((ent.text, EntityType.TECHNOLOGY))
                elif ent.label_ in ["GPE"]:  # Geographic entities
                    entities.append((ent.text, EntityType.CONCEPT))

            return entities

        except Exception as e:
            logger.warning(f"spaCy extraction failed: {e}")
            return []

    @classmethod
    def _extract_by_patterns(cls, text: str) -> List[Tuple[str, str]]:
        """Extract entities using regex patterns."""
        entities = []

        # Pattern: CamelCase words (often class/concept names)
        camel_case_pattern = r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b"
        for match in re.finditer(camel_case_pattern, text):
            entity_name = match.group()
            if len(entity_name) > 2:  # Ignore very short matches
                entities.append((entity_name, EntityType.CONCEPT))

        # Pattern: SCREAMING_SNAKE_CASE (constants, acronyms)
        screaming_pattern = r"\b[A-Z]{2,}(?:_[A-Z0-9]+)*\b"
        for match in re.finditer(screaming_pattern, text):
            entity_name = match.group()
            if entity_name not in ["HTTP", "REST", "API", "SQL"]:  # Filter common acronyms
                entities.append((entity_name, EntityType.CONCEPT))

        # Pattern: quoted concepts ("vector embeddings", "semantic search")
        quoted_pattern = r'"([^"]+)"'
        for match in re.finditer(quoted_pattern, text):
            entity_name = match.group(1)
            if len(entity_name) > 3:
                entities.append((entity_name, EntityType.CONCEPT))

        return entities


class RelationshipExtractor:
    """
    Extracts relationships between entities.
    Uses pattern matching and dependency parsing.
    """

    RELATIONSHIP_PATTERNS = [
        # "A implements B"
        (r"(\w+)\s+implements\s+(\w+)", "IMPLEMENTS"),
        # "A extends B"
        (r"(\w+)\s+extends\s+(\w+)", "EXTENDS"),
        # "A depends on B"
        (r"(\w+)\s+depends\s+on\s+(\w+)", "DEPENDS_ON"),
        # "A uses B"
        (r"(\w+)\s+uses\s+(\w+)", "USES"),
        # "A is based on B"
        (r"(\w+)\s+is\s+based\s+on\s+(\w+)", "BASED_ON"),
        # "A integrates B"
        (r"(\w+)\s+integrates\s+(\w+)", "INTEGRATES"),
    ]

    @classmethod
    def extract_relationships(
        cls, text: str, entities: List[Tuple[str, str]]
    ) -> List[Tuple[str, str, str, float]]:
        """
        Extract relationships between entities.

        Args:
            text: Source text
            entities: List of extracted entities

        Returns:
            List of (source, target, relationship_type, confidence) tuples
        """
        relationships = []
        entity_names = {e[0].lower() for e in entities}

        for pattern, rel_type in cls.RELATIONSHIP_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source = match.group(1)
                target = match.group(2)

                # Check if both entities exist
                if source.lower() in entity_names and target.lower() in entity_names:
                    relationships.append((source, target, rel_type, 0.9))

        logger.info(f"Extracted {len(relationships)} relationships from text")
        return relationships


class ChunkEntityProcessor:
    """
    Process chunks to extract entities and relationships.
    This is the main entry point for the entity extraction pipeline.
    """

    @staticmethod
    def process_chunk(text: str, chunk_id: str) -> Dict[str, Any]:
        """
        Process a chunk to extract entities and relationships.

        Returns:
        {
            "chunk_id": str,
            "entities": [(name, type), ...],
            "relationships": [(source, target, type, confidence), ...],
            "key_concepts": [str, ...]
        }
        """
        try:
            # Extract entities
            entities = EntityExtractor.extract_entities(text)

            # Extract relationships
            relationships = RelationshipExtractor.extract_relationships(text, entities)

            # Identify key concepts (most frequent entity types)
            concepts = [e[0] for e in entities if e[1] == EntityType.CONCEPT]

            return {
                "chunk_id": chunk_id,
                "entities": entities,
                "relationships": relationships,
                "key_concepts": list(set(concepts)),  # Deduplicate
                "entity_count": len(entities),
                "relationship_count": len(relationships),
            }

        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            return {
                "chunk_id": chunk_id,
                "entities": [],
                "relationships": [],
                "key_concepts": [],
                "entity_count": 0,
                "relationship_count": 0,
            }

    @staticmethod
    def batch_process_chunks(chunks: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        Process multiple chunks efficiently.

        Args:
            chunks: List of (text, chunk_id) tuples

        Returns:
            List of processed chunk results
        """
        results = []

        for text, chunk_id in chunks:
            result = ChunkEntityProcessor.process_chunk(text, chunk_id)
            results.append(result)

        logger.info(f"Processed {len(chunks)} chunks for entity extraction")
        return results

    @staticmethod
    def extract_cross_document_concepts(
        all_results: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """
        Find concepts that appear in multiple documents.

        Returns:
        {
            "concept": [chunk_id1, chunk_id2, ...],
            ...
        }
        """
        concept_locations = {}

        for result in all_results:
            for concept in result.get("key_concepts", []):
                if concept not in concept_locations:
                    concept_locations[concept] = []

                concept_locations[concept].append(result["chunk_id"])

        # Filter to concepts appearing in multiple documents
        cross_doc_concepts = {
            k: v for k, v in concept_locations.items() if len(set(v)) > 1
        }

        logger.info(
            f"Found {len(cross_doc_concepts)} concepts appearing in multiple documents"
        )

        return cross_doc_concepts
