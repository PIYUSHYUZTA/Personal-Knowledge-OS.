"""
Redis Caching Service for Query Results and WebSocket State.
Improves performance for repeated queries and session management.
"""

import json
import logging
from typing import Optional, Any, Dict
from uuid import UUID
import redis
from datetime import timedelta

from app.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis caching layer for PKOS."""

    _client: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if cls._client is None:
            try:
                cls._client = redis.Redis(
                    host=settings.REDIS_HOST or "localhost",
                    port=settings.REDIS_PORT or 6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )

                # Test connection
                cls._client.ping()
                logger.info("Redis client initialized")

            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                cls._client = None

        return cls._client

    @classmethod
    def close(cls):
        """Close Redis connection."""
        if cls._client:
            cls._client.close()
            cls._client = None


class QueryCache:
    """Caches semantic search and technical reasoning results."""

    # Cache prefixes
    PREFIX_SEMANTIC_SEARCH = "search:semantic:"
    PREFIX_TECHNICAL_QUERY = "query:technical:"
    PREFIX_GRAPH_CONTEXT = "graph:context:"

    # TTL defaults (in seconds)
    TTL_SEARCH = 3600  # 1 hour
    TTL_QUERY = 7200  # 2 hours
    TTL_GRAPH = 1800  # 30 minutes

    @staticmethod
    def get_search_cache(
        user_id: UUID, query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached semantic search results.

        Args:
            user_id: User ID
            query: Search query string

        Returns:
            Cached results or None
        """
        client = RedisCache.get_client()
        if not client:
            return None

        try:
            cache_key = f"{QueryCache.PREFIX_SEMANTIC_SEARCH}{user_id}:{query}"
            cached = client.get(cache_key)

            if cached:
                logger.info(f"Cache hit for search query: {query}")
                return json.loads(cached)

            return None

        except Exception as e:
            logger.warning(f"Error retrieving search cache: {e}")
            return None

    @staticmethod
    def set_search_cache(user_id: UUID, query: str, results: Any, ttl: int = TTL_SEARCH):
        """
        Cache semantic search results.

        Args:
            user_id: User ID
            query: Search query string
            results: Results to cache
            ttl: Time to live in seconds
        """
        client = RedisCache.get_client()
        if not client:
            return

        try:
            cache_key = f"{QueryCache.PREFIX_SEMANTIC_SEARCH}{user_id}:{query}"
            client.setex(
                cache_key,
                ttl,
                json.dumps(results, default=str),
            )
            logger.info(f"Cached search results for query: {query}")

        except Exception as e:
            logger.warning(f"Error setting search cache: {e}")

    @staticmethod
    def get_technical_query_cache(user_id: UUID, query: str) -> Optional[str]:
        """
        Get cached technical reasoning response.

        Args:
            user_id: User ID
            query: Technical query

        Returns:
            Cached response or None
        """
        client = RedisCache.get_client()
        if not client:
            return None

        try:
            cache_key = f"{QueryCache.PREFIX_TECHNICAL_QUERY}{user_id}:{query}"
            cached = client.get(cache_key)

            if cached:
                logger.info(f"Cache hit for technical query: {query}")
                return cached

            return None

        except Exception as e:
            logger.warning(f"Error retrieving query cache: {e}")
            return None

    @staticmethod
    def set_technical_query_cache(user_id: UUID, query: str, response: str, ttl: int = TTL_QUERY):
        """
        Cache technical reasoning response.

        Args:
            user_id: User ID
            query: Technical query
            response: Generated response
            ttl: Time to live in seconds
        """
        client = RedisCache.get_client()
        if not client:
            return

        try:
            cache_key = f"{QueryCache.PREFIX_TECHNICAL_QUERY}{user_id}:{query}"
            client.setex(cache_key, ttl, response)
            logger.info(f"Cached technical response for query: {query}")

        except Exception as e:
            logger.warning(f"Error setting query cache: {e}")

    @staticmethod
    def get_graph_context_cache(user_id: UUID, concept: str) -> Optional[Dict]:
        """Get cached graph context for a concept."""
        client = RedisCache.get_client()
        if not client:
            return None

        try:
            cache_key = f"{QueryCache.PREFIX_GRAPH_CONTEXT}{user_id}:{concept}"
            cached = client.get(cache_key)

            if cached:
                return json.loads(cached)

            return None

        except Exception as e:
            logger.warning(f"Error retrieving graph cache: {e}")
            return None

    @staticmethod
    def set_graph_context_cache(
        user_id: UUID, concept: str, context: Dict, ttl: int = TTL_GRAPH
    ):
        """Cache graph context for a concept."""
        client = RedisCache.get_client()
        if not client:
            return

        try:
            cache_key = f"{QueryCache.PREFIX_GRAPH_CONTEXT}{user_id}:{concept}"
            client.setex(cache_key, ttl, json.dumps(context, default=str))

        except Exception as e:
            logger.warning(f"Error setting graph cache: {e}")

    @staticmethod
    def clear_user_cache(user_id: UUID) -> int:
        """
        Clear all cached data for a user.

        Returns:
            Number of keys deleted
        """
        client = RedisCache.get_client()
        if not client:
            return 0

        try:
            patterns = [
                f"{QueryCache.PREFIX_SEMANTIC_SEARCH}{user_id}:*",
                f"{QueryCache.PREFIX_TECHNICAL_QUERY}{user_id}:*",
                f"{QueryCache.PREFIX_GRAPH_CONTEXT}{user_id}:*",
            ]

            total_deleted = 0
            for pattern in patterns:
                keys = client.keys(pattern)
                if keys:
                    deleted = client.delete(*keys)
                    total_deleted += deleted

            logger.info(f"Cleared {total_deleted} cache keys for user {user_id}")
            return total_deleted

        except Exception as e:
            logger.warning(f"Error clearing user cache: {e}")
            return 0


class WebSocketSessionManager:
    """Manages WebSocket session state in Redis."""

    PREFIX_SESSION = "ws:session:"

    @staticmethod
    def create_session(user_id: UUID, session_id: str) -> bool:
        """Create a new WebSocket session."""
        client = RedisCache.get_client()
        if not client:
            return False

        try:
            session_key = f"{WebSocketSessionManager.PREFIX_SESSION}{session_id}"
            session_data = {
                "user_id": str(user_id),
                "created_at": json.dumps({"now": "now"}, default=str),
                "message_count": 0,
            }

            client.setex(
                session_key,
                3600,  # 1 hour TTL for session
                json.dumps(session_data),
            )

            logger.info(f"Created WebSocket session {session_id}")
            return True

        except Exception as e:
            logger.warning(f"Error creating session: {e}")
            return False

    @staticmethod
    def increment_message_count(session_id: str) -> bool:
        """Increment message counter for session."""
        client = RedisCache.get_client()
        if not client:
            return False

        try:
            session_key = f"{WebSocketSessionManager.PREFIX_SESSION}{session_id}"
            client.hincrby(session_key, "message_count", 1)
            return True

        except Exception as e:
            logger.warning(f"Error incrementing message count: {e}")
            return False

    @staticmethod
    def get_session_stats(session_id: str) -> Optional[Dict]:
        """Get session statistics."""
        client = RedisCache.get_client()
        if not client:
            return None

        try:
            session_key = f"{WebSocketSessionManager.PREFIX_SESSION}{session_id}"
            session_data = client.get(session_key)

            if session_data:
                return json.loads(session_data)

            return None

        except Exception as e:
            logger.warning(f"Error getting session stats: {e}")
            return None

    @staticmethod
    def destroy_session(session_id: str) -> bool:
        """Destroy a WebSocket session."""
        client = RedisCache.get_client()
        if not client:
            return False

        try:
            session_key = f"{WebSocketSessionManager.PREFIX_SESSION}{session_id}"
            client.delete(session_key)
            logger.info(f"Destroyed WebSocket session {session_id}")
            return True

        except Exception as e:
            logger.warning(f"Error destroying session: {e}")
            return False
