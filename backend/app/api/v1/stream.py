"""
WebSocket Streaming Engine for Real-Time Technical Reasoning.
Token-by-token streaming of AI responses with agentic tool use.
Phase 7a: Includes GraphUpdateBroadcaster for real-time knowledge graph updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
import logging
import json
from typing import Optional, Dict, List
import asyncio
from uuid import UUID

from app.database.connection import get_db
from app.core.security import verify_token
from app.models import User
from app.services.hybrid_engine import HybridRetrievalEngine
from app.services.llm_factory import LLMFactory
from app.services.tool_executor import ToolExecutor, ToolCallParser, ToolDefinition
from app.services.graph_service import set_graph_service
from app.services.code_validator import SelfCorrectionMiddleware
from app.core.prompts import format_rag_prompt, detect_domain

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Streaming API"])


class StreamingContext:
    """Manages streaming state for a WebSocket connection."""

    def __init__(self, user_id: UUID, query: str):
        self.user_id = user_id
        self.query = query
        self.context_packet = None
        self.retrieved_sources = []
        self.token_count = 0
        self.confidence_score = 0.0
        self.tool_calls = []  # Track tool calls made during response
        self.tool_results = {}  # Results from tool executions

    def to_dict(self):
        return {
            "user_id": str(self.user_id),
            "query": self.query,
            "context_packet": self.context_packet,
            "sources": self.retrieved_sources,
            "tokens": self.token_count,
            "confidence": self.confidence_score,
            "tool_calls": len(self.tool_calls),
        }


class ConnectionManager:
    """Manages WebSocket connections for real-time communication."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Register a WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Unregister a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send message to all connections for a user."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")

    async def send_to_connection(self, websocket: WebSocket, message: dict):
        """Send message to single connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to connection: {e}")


# Global connection manager
manager = ConnectionManager()


@router.websocket("/stream/query")
async def websocket_query_stream(
    websocket: WebSocket,
    token: str = Query(None),
    db_session = Depends(get_db),
):
    """
    WebSocket endpoint for streaming technical reasoning responses.

    Protocol:
    1. Client connects and sends: {"message": "How to...?"}
    2. Server retrieves context and generates response with LLM Factory
    3. If LLM calls tools, execute them and feed results back
    4. Server streams tokens to client: {"type": "token", "content": "word"}
    5. Server sends: {"type": "sources", "content": [...]}
    6. Server sends: {"type": "complete", "confidence": 0.92}
    """

    # Verify user identity
    from app.core.security import verify_token as verify_jwt

    payload = verify_jwt(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = UUID(payload.get("sub"))
    user = db_session.query(User).filter(User.id == user_id).first()

    if not user:
        await websocket.close(code=4001, reason="User not found")
        return

    # Set up graph service context for this user
    set_graph_service(user_id)

    await manager.connect(websocket, str(user_id))

    try:
        while True:
            # Receive query from client
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await manager.send_to_connection(websocket, {"type": "pong"})
                continue

            query = data.get("message")
            if not query:
                await manager.send_to_connection(
                    websocket, {"type": "error", "content": "No message provided"}
                )
                continue

            logger.info(f"Streaming query from {user_id}: {query}")

            # Create streaming context
            context = StreamingContext(user_id, query)

            try:
                # Step 1: Hybrid retrieval (graph + vector combined)
                await manager.send_to_connection(
                    websocket,
                    {"type": "status", "content": "Retrieving knowledge..."},
                )

                context.context_packet = HybridRetrievalEngine.retrieve_hybrid_context(
                    db_session, user_id, query
                )

                context.retrieved_sources = [
                    {
                        "file_name": source.get("file_name"),
                        "chunk_text": source.get("chunk_text", "")[:200],
                        "similarity": source.get("similarity", ""),
                    }
                    for source in context.context_packet.get("semantic_results", [])
                ]

                # Send sources to client
                await manager.send_to_connection(
                    websocket,
                    {
                        "type": "sources",
                        "content": context.retrieved_sources,
                        "graph_context": context.context_packet.get("graph_context"),
                    },
                )

                # Step 2: Detect domain and prepare system prompt
                await manager.send_to_connection(
                    websocket, {"type": "status", "content": "Analyzing domain..."}
                )

                domain = detect_domain(query)
                rag_prompt = format_rag_prompt(
                    domain=domain,
                    query=query,
                    context=context.context_packet.get("rag_context", ""),
                )

                # Step 3: Generate response with LLM Factory
                await manager.send_to_connection(
                    websocket,
                    {"type": "status", "content": f"Generating response ({domain} domain)..."},
                )

                # Get LLM provider with tool support
                llm_provider = LLMFactory.get_provider()
                tool_executor = ToolExecutor()
                correction_middleware = SelfCorrectionMiddleware(enable_correction=True)
                tools = ToolDefinition.get_all_tools()

                # Generate response with streaming
                response_text = ""
                stop_reason = None
                tool_calls_list = []

                # For non-streaming first, to handle tool calls
                response = await llm_provider.generate(
                    prompt=query,
                    system_prompt=rag_prompt["system_prompt"],
                    tools=tools,
                    stream=False,
                )

                response_text = response.get("content", "")
                stop_reason = response.get("stop_reason")
                raw_tool_calls = response.get("tool_calls", [])

                # Apply self-correction validation and fix errors
                correction_result = await correction_middleware.process_response(
                    response_text,
                    language=domain,
                    context=context.context_packet.get("rag_context", "")
                )

                response_text = correction_result.get("text", response_text)

                # Send validation status if corrections were made
                if correction_result.get("corrected"):
                    await manager.send_to_connection(
                        websocket,
                        {
                            "type": "status",
                            "content": f"Self-correction applied ({correction_result['iterations']} iteration(s))",
                        },
                    )

                # Handle tool calls if present
                if raw_tool_calls and stop_reason == "tool_use":
                    await manager.send_to_connection(
                        websocket,
                        {
                            "type": "status",
                            "content": f"Executing {len(raw_tool_calls)} tool(s)...",
                        },
                    )

                    for tool_call in raw_tool_calls:
                        tool_name = tool_call.get("name")
                        tool_input = tool_call.get("input", {})

                        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

                        # Execute the tool
                        tool_result = await tool_executor.execute_tool(tool_name, tool_input)

                        context.tool_calls.append(
                            {
                                "name": tool_name,
                                "input": tool_input,
                                "result": tool_result,
                            }
                        )

                        context.tool_results[tool_name] = tool_result

                        # Send tool execution status
                        await manager.send_to_connection(
                            websocket,
                            {
                                "type": "status",
                                "content": f"Tool {tool_name}: {tool_result['status']}",
                            },
                        )

                # Step 4: Stream tokens
                await manager.send_to_connection(
                    websocket, {"type": "response_start"}
                )

                # Stream the response tokens
                buffered_response = ""
                words = response_text.split()
                for i, word in enumerate(words):
                    token_text = word + " "
                    buffered_response += token_text
                    context.token_count += 1

                    # Send token
                    await manager.send_to_connection(
                        websocket,
                        {
                            "type": "token",
                            "content": token_text,
                            "token_count": context.token_count,
                        },
                    )

                    # Small delay to simulate streaming
                    if i % 10 == 0:
                        await asyncio.sleep(0.01)

                # Calculate confidence based on context and tool usage
                base_confidence = context.context_packet.get("confidence", 0.8)
                tool_confidence_bonus = min(0.1, len(context.tool_calls) * 0.05)
                context.confidence_score = min(0.99, base_confidence + tool_confidence_bonus)

                # Step 5: Final metadata
                await manager.send_to_connection(
                    websocket,
                    {
                        "type": "complete",
                        "confidence": context.confidence_score,
                        "token_count": context.token_count,
                        "model": llm_provider.config.model_id,
                        "domain": domain,
                        "tools_used": len(context.tool_calls),
                    },
                )

                logger.info(
                    f"Streaming complete: {context.token_count} tokens, "
                    f"{len(context.tool_calls)} tools, confidence: {context.confidence_score:.2f}"
                )

            except Exception as e:
                logger.error(f"Error during stream processing: {e}", exc_info=True)
                await manager.send_to_connection(
                    websocket,
                    {
                        "type": "error",
                        "content": f"Error processing query: {str(e)}",
                    },
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket, str(user_id))
        logger.info(f"User {user_id} disconnected")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, str(user_id))


@router.get("/stream/status")
async def stream_status(token: str = Query(None)):
    """
    Get streaming engine status and active connections.
    """
    try:
        from app.core.security import verify_token as verify_jwt

        payload = verify_jwt(token)
        if not payload:
            return {"status": "unauthorized"}

        user_id = payload.get("sub")

        return {
            "status": "operational",
            "active_streams": len(manager.active_connections.get(user_id, [])),
            "total_connections": sum(
                len(conns) for conns in manager.active_connections.values()
            ),
        }

    except Exception as e:
        logger.error(f"Error getting stream status: {e}")
        return {"status": "error", "detail": str(e)}


# ============================================================================
# PHASE 7a: GRAPH UPDATE BROADCASTER
# ============================================================================


class GraphUpdateBroadcaster:
    """
    Broadcasts real-time graph updates to connected WebSocket clients.

    Listens to Redis pub/sub channel "graph:updates" and forwards
    graph_update messages to all connected users via ConnectionManager.

    Message types sent to clients:
    - {"type": "graph_update", "action": "entity_added", "node": {...}}
    - {"type": "graph_update", "action": "relationship_added", "edge": {...}}
    - {"type": "graph_update", "action": "entities_merged", "data": {...}}
    - {"type": "graph_update", "action": "graph_refresh", "data": {...}}
    """

    _instance = None
    _listening = False

    @classmethod
    async def start(cls) -> None:
        """
        Start listening to Redis pub/sub for graph events and broadcasting.

        Should be called during app startup after Redis is initialized.
        """
        if cls._listening:
            return

        try:
            from app.core.redis_pubsub import get_redis_pubsub

            redis_pubsub = await get_redis_pubsub()
            if redis_pubsub and redis_pubsub.redis_client:
                await redis_pubsub.subscribe("graph:updates", cls._handle_graph_event)
                cls._listening = True
                logger.info("GraphUpdateBroadcaster started listening on graph:updates")
            else:
                logger.warning("Redis not available, GraphUpdateBroadcaster not started")

        except Exception as e:
            logger.error(f"Failed to start GraphUpdateBroadcaster: {e}")

    @classmethod
    async def stop(cls) -> None:
        """Stop listening to graph update events."""
        if cls._listening:
            try:
                from app.core.redis_pubsub import get_redis_pubsub

                redis_pubsub = await get_redis_pubsub()
                if redis_pubsub:
                    await redis_pubsub.unsubscribe("graph:updates")
                cls._listening = False
                logger.info("GraphUpdateBroadcaster stopped")
            except Exception as e:
                logger.error(f"Error stopping GraphUpdateBroadcaster: {e}")

    @classmethod
    async def _handle_graph_event(cls, channel: str, message: str) -> None:
        """
        Handle incoming graph event from Redis pub/sub.

        Parses the event, determines the target user, and broadcasts
        the appropriate WebSocket message.
        """
        try:
            event_data = json.loads(message)

            user_id = event_data.get("user_id")
            event_type = event_data.get("event_type")
            data = event_data.get("data", {})

            if not user_id or not event_type:
                logger.warning(f"Invalid graph event: missing user_id or event_type")
                return

            # Build WebSocket message based on event type
            ws_message = cls._build_ws_message(event_type, data, event_data)

            if ws_message:
                await manager.broadcast_to_user(user_id, ws_message)
                logger.debug(f"Broadcast graph_update to user {user_id}: {event_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in graph event: {message[:100]}")
        except Exception as e:
            logger.error(f"Error handling graph event: {e}")

    @classmethod
    def _build_ws_message(
        cls, event_type: str, data: dict, full_event: dict
    ) -> Optional[dict]:
        """
        Build a WebSocket message from a graph event.

        Returns the message dict to send to the client, or None to skip.
        """
        if event_type == "entity_added":
            return {
                "type": "graph_update",
                "action": "entity_added",
                "node": {
                    "id": data.get("entity_id"),
                    "label": data.get("entity_name"),
                    "type": data.get("entity_type"),
                    "properties": data.get("properties", {}),
                },
                "timestamp": full_event.get("timestamp"),
            }

        elif event_type == "relationship_added":
            return {
                "type": "graph_update",
                "action": "relationship_added",
                "edge": {
                    "source": data.get("source_entity_name"),
                    "target": data.get("target_entity_name"),
                    "relationship": data.get("relationship_type"),
                    "weight": data.get("weight", 1.0),
                },
                "timestamp": full_event.get("timestamp"),
            }

        elif event_type == "entities_merged":
            return {
                "type": "graph_update",
                "action": "entities_merged",
                "data": {
                    "primary": data.get("primary_entity_name"),
                    "merged": data.get("merged_entity_names", []),
                },
                "timestamp": full_event.get("timestamp"),
            }

        elif event_type == "graph_refreshed":
            return {
                "type": "graph_update",
                "action": "graph_refresh",
                "data": data,
                "timestamp": full_event.get("timestamp"),
            }

        else:
            logger.debug(f"Unknown graph event type: {event_type}")
            return None


@router.websocket("/stream/graph")
async def websocket_graph_stream(
    websocket: WebSocket,
    token: str = Query(None),
):
    """
    WebSocket endpoint for real-time knowledge graph updates.

    Protocol:
    1. Client connects with JWT token
    2. Server sends graph updates as they occur:
       - {"type": "graph_update", "action": "entity_added", "node": {...}}
       - {"type": "graph_update", "action": "relationship_added", "edge": {...}}
       - {"type": "graph_update", "action": "entities_merged", "data": {...}}
    3. Client can send ping: {"type": "ping"} -> receives {"type": "pong"}
    4. Client can request full graph refresh: {"type": "refresh"}
    """
    from app.core.security import verify_token as verify_jwt

    payload = verify_jwt(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user_id = payload.get("sub")

    await manager.connect(websocket, user_id)

    # Send initial connection confirmation
    await manager.send_to_connection(
        websocket,
        {
            "type": "graph_connected",
            "user_id": user_id,
            "message": "Real-time graph updates active",
        },
    )

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await manager.send_to_connection(websocket, {"type": "pong"})

            elif data.get("type") == "refresh":
                # Client requests full graph data
                try:
                    from app.services.graph_service import Neo4jGraphService

                    graph_service = Neo4jGraphService(user_id=UUID(user_id))
                    graph_data = graph_service.export_graph_as_json()

                    await manager.send_to_connection(
                        websocket,
                        {
                            "type": "graph_update",
                            "action": "graph_refresh",
                            "data": graph_data,
                        },
                    )
                except Exception as e:
                    logger.error(f"Error refreshing graph: {e}")
                    await manager.send_to_connection(
                        websocket,
                        {"type": "error", "content": f"Graph refresh failed: {str(e)}"},
                    )

    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        logger.info(f"Graph stream disconnected for user {user_id}")

    except Exception as e:
        logger.error(f"Graph WebSocket error: {e}")
        await manager.disconnect(websocket, user_id)
