"""
Redis Pub/Sub Integration (Phase 7a).

Handles real-time event messaging through Redis pub/sub.
Enables distributed communication for graph updates across multiple backend instances.

Channels:
- graph:updates - Graph change events (entity/relationship additions)
"""

import logging
import json
import asyncio
from typing import Dict, Callable, Optional, Any
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisPubSubManager:
    """
    Manages Redis pub/sub subscriptions for real-time updates.

    Handles:
    - Connection management
    - Channel subscriptions
    - Message routing to handlers
    - Graceful shutdown
    """

    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.pubsub = None
        self.subscriptions: Dict[str, list[Callable]] = {}
        self._listening_task = None
        self._is_running = False

    async def connect(self) -> None:
        """Connect to Redis and initialize pub/sub."""
        if not settings.REDIS_ENABLED:
            logger.warning("Redis is disabled in config, pub/sub will not be available")
            return

        try:
            # Connect to Redis
            self.redis_client = await redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            )

            # Test connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")

            # Create pub/sub client
            self.pubsub = self.redis_client.pubsub()

            # Start listening for messages
            self._is_running = True
            self._listening_task = asyncio.create_task(self._listen_for_messages())

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            self.pubsub = None

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        self._is_running = False

        if self._listening_task:
            await asyncio.sleep(0.1)  # Let task finish gracefully
            if not self._listening_task.done():
                self._listening_task.cancel()

        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()

        if self.redis_client:
            await self.redis_client.close()

        logger.info("Disconnected from Redis")

    async def subscribe(self, channel: str, handler: Callable) -> None:
        """
        Subscribe to a channel with a message handler.

        Args:
            channel: Channel name (e.g., "graph:updates")
            handler: Async function to call on message: handler(channel, message)
        """
        if not self.pubsub:
            logger.warning("Redis pub/sub not initialized")
            return

        try:
            # Register handler
            if channel not in self.subscriptions:
                self.subscriptions[channel] = []
            self.subscriptions[channel].append(handler)

            # Subscribe to channel
            await self.pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")

        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        if self.pubsub:
            try:
                await self.pubsub.unsubscribe(channel)
                if channel in self.subscriptions:
                    del self.subscriptions[channel]
                logger.info(f"Unsubscribed from {channel}")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from {channel}: {e}")

    async def publish(self, channel: str, message: str) -> int:
        """
        Publish message to channel.

        Args:
            channel: Channel name
            message: Message data (usually JSON string)

        Returns:
            Number of subscribers who received the message
        """
        if not self.redis_client:
            logger.warning("Redis not connected, cannot publish")
            return 0

        try:
            count = await self.redis_client.publish(channel, message)
            logger.debug(f"Published to {channel}: {len(message)} bytes, {count} subscribers")
            return count
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return 0

    async def _listen_for_messages(self) -> None:
        """
        Listen for messages on subscribed channels.

        Continuously reads from pub/sub and dispatches to handlers.
        """
        if not self.pubsub:
            return

        try:
            async for message in self.pubsub.listen():
                if not self._is_running:
                    break

                try:
                    if message["type"] == "message":
                        channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                        data = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]

                        # Dispatch to handlers
                        if channel in self.subscriptions:
                            for handler in self.subscriptions[channel]:
                                try:
                                    if asyncio.iscoroutinefunction(handler):
                                        await handler(channel, data)
                                    else:
                                        handler(channel, data)
                                except Exception as e:
                                    logger.error(f"Error in message handler for {channel}: {e}")
                except Exception as e:
                    logger.error(f"Error processing pub/sub message: {e}")

        except asyncio.CancelledError:
            logger.info("Message listener task cancelled")
        except Exception as e:
            logger.error(f"Error in message listening loop: {e}")

    @asynccontextmanager
    async def connect_context(self):
        """Context manager for temporary Redis connections."""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()


# Singleton instance
_redis_pubsub_manager: Optional[RedisPubSubManager] = None


async def get_redis_pubsub() -> RedisPubSubManager:
    """Get or create the Redis pub/sub manager singleton."""
    global _redis_pubsub_manager
    if _redis_pubsub_manager is None:
        _redis_pubsub_manager = RedisPubSubManager()
        await _redis_pubsub_manager.connect()
    return _redis_pubsub_manager


async def initialize_redis_pubsub() -> None:
    """Initialize Redis pub/sub during application startup."""
    manager = await get_redis_pubsub()
    logger.info("Redis pub/sub initialized")


async def shutdown_redis_pubsub() -> None:
    """Shutdown Redis pub/sub during application shutdown."""
    global _redis_pubsub_manager
    if _redis_pubsub_manager:
        await _redis_pubsub_manager.disconnect()
        _redis_pubsub_manager = None
    logger.info("Redis pub/sub shutdown complete")
