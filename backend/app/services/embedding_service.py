"""
Embedding service: generate embeddings using sentence-transformers.
Handles vector generation for semantic search.
"""

from typing import List
import numpy as np
import logging

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")

from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Generates and manages embeddings for semantic search."""

    _model = None

    @classmethod
    def load_model(cls):
        """Lazy load embedding model."""
        if cls._model is None:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        return cls._model

    @classmethod
    def encode(cls, texts: List[str]) -> np.ndarray:
        """
        Encode texts into embeddings.

        Args:
            texts: List of text strings to encode

        Returns:
            numpy array of shape (len(texts), embedding_dimension)
        """
        model = cls.load_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings

    @classmethod
    def encode_single(cls, text: str) -> np.ndarray:
        """Encode a single text string."""
        return cls.encode([text])[0]

    @classmethod
    def cosine_similarity(cls, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.

        Returns:
            float between -1 and 1, where 1 means identical
        """
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))

    @classmethod
    def get_dimension(cls) -> int:
        """Get embedding dimension."""
        return settings.EMBEDDING_DIMENSION
