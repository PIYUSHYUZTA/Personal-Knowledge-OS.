"""
Agentic Tool Executor Service.

Enables LLMs to invoke external tools:
- search_vector_db: Semantic search across knowledge base
- query_knowledge_graph: Graph database queries with Cypher
- read_local_file: Read files from knowledge base directory
"""

from typing import Optional, List, Dict, Any
import logging
import os
from pathlib import Path
import json

from app.services.knowledge_service import KnowledgeService
from app.services.graph_service import get_graph_service

logger = logging.getLogger(__name__)


class ToolDefinition:
    """JSON schema for tool definitions that LLMs understand."""

    SEARCH_VECTOR_DB = {
        "name": "search_vector_db",
        "description": "Search the knowledge base using semantic similarity. Returns relevant documents and their source context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (e.g., 'database indexing strategies', 'authentication patterns')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5
                },
                "threshold": {
                    "type": "number",
                    "description": "Similarity threshold (0-1, default: 0.5)",
                    "default": 0.5
                }
            },
            "required": ["query"]
        }
    }

    QUERY_KNOWLEDGE_GRAPH = {
        "name": "query_knowledge_graph",
        "description": "Query the knowledge graph (Neo4j) using Cypher. Use for finding relationships between concepts, entities, and technologies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cypher_query": {
                    "type": "string",
                    "description": "Cypher query (e.g., 'MATCH (e:Entity)-[r:RELATES_TO]->(e2:Entity) RETURN e.name, r.type, e2.name LIMIT 10')"
                }
            },
            "required": ["cypher_query"]
        }
    }

    READ_LOCAL_FILE = {
        "name": "read_local_file",
        "description": "Read the content of a file from the knowledge base. Use when you need to examine specific document content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file relative to knowledge base directory (e.g., 'README.md', 'docs/architecture.md')"
                }
            },
            "required": ["file_path"]
        }
    }

    @staticmethod
    def get_all_tools() -> List[Dict[str, Any]]:
        """Return all tool definitions for LLM context."""
        return [
            ToolDefinition.SEARCH_VECTOR_DB,
            ToolDefinition.QUERY_KNOWLEDGE_GRAPH,
            ToolDefinition.READ_LOCAL_FILE,
        ]


class ToolExecutor:
    """Executes tool calls from LLM responses."""

    def __init__(self):
        self.knowledge_service = KnowledgeService()
        # Knowledge base directory for file operations
        self.kb_base_path = Path(os.getenv("KB_BASE_PATH", "./knowledge_base"))

    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool call from the LLM.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool execution result with status and data
        """
        try:
            if tool_name == "search_vector_db":
                return await self._search_vector_db(tool_input)
            elif tool_name == "query_knowledge_graph":
                return await self._query_knowledge_graph(tool_input)
            elif tool_name == "read_local_file":
                return self._read_local_file(tool_input)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown tool: {tool_name}",
                    "data": None
                }
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return {
                "status": "error",
                "error": str(e),
                "data": None
            }

    async def _search_vector_db(
        self,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Search vector database using semantic similarity."""
        query = params.get("query", "")
        limit = params.get("limit", 5)
        threshold = params.get("threshold", 0.5)

        if not query:
            return {
                "status": "error",
                "error": "Query parameter is required",
                "data": None
            }

        try:
            results = await self.knowledge_service.search(
                query=query,
                limit=limit,
                threshold=threshold
            )

            # Format results for LLM consumption
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "source": result.get("source_id"),
                    "content": result.get("content", "")[:500],  # Truncate to 500 chars
                    "similarity": round(result.get("similarity", 0), 3),
                    "chunk_id": result.get("chunk_id")
                })

            return {
                "status": "success",
                "error": None,
                "data": {
                    "query": query,
                    "result_count": len(formatted_results),
                    "results": formatted_results,
                    "threshold": threshold
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Vector search failed: {str(e)}",
                "data": None
            }

    async def _query_knowledge_graph(
        self,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Query Neo4j knowledge graph using Cypher."""
        cypher_query = params.get("cypher_query", "")

        if not cypher_query:
            return {
                "status": "error",
                "error": "cypher_query parameter is required",
                "data": None
            }

        try:
            graph_service = get_graph_service()
            if not graph_service:
                return {
                    "status": "error",
                    "error": "Graph service not initialized. Set user context first.",
                    "data": None
                }

            # Execute Cypher query (with safety limit of 100 results)
            if "LIMIT" not in cypher_query.upper():
                cypher_query += " LIMIT 100"

            results = graph_service.execute_query(cypher_query)

            if results is None:
                return {
                    "status": "error",
                    "error": "Graph query execution failed",
                    "data": None
                }

            return {
                "status": "success",
                "error": None,
                "data": {
                    "query": cypher_query,
                    "result_count": len(results) if results else 0,
                    "results": results[:50] if results else []  # Limit to 50 results for context
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Graph query failed: {str(e)}",
                "data": None
            }

    def _read_local_file(
        self,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read a file from the knowledge base directory."""
        file_path = params.get("file_path", "")

        if not file_path:
            return {
                "status": "error",
                "error": "file_path parameter is required",
                "data": None
            }

        try:
            # Prevent directory traversal attacks
            full_path = (self.kb_base_path / file_path).resolve()

            if not str(full_path).startswith(str(self.kb_base_path.resolve())):
                return {
                    "status": "error",
                    "error": "Access denied: Path traversal detected",
                    "data": None
                }

            if not full_path.exists():
                return {
                    "status": "error",
                    "error": f"File not found: {file_path}",
                    "data": None
                }

            if not full_path.is_file():
                return {
                    "status": "error",
                    "error": f"Not a file: {file_path}",
                    "data": None
                }

            # Read file (limit to 10KB to prevent large context)
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if len(content) > 10240:  # 10KB limit
                content = content[:10240] + "\n\n... [truncated]"

            return {
                "status": "success",
                "error": None,
                "data": {
                    "file_path": str(file_path),
                    "file_size": len(content),
                    "content": content
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"File read failed: {str(e)}",
                "data": None
            }


class ToolCallResponse:
    """Represents a tool call extracted from LLM response."""

    def __init__(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_use_id: Optional[str] = None
    ):
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.tool_use_id = tool_use_id  # Claude-specific ID for tracking
        self.result: Optional[Dict[str, Any]] = None
        self.executed = False

    def __repr__(self):
        return f"ToolCall({self.tool_name}, executed={self.executed})"


class ToolCallParser:
    """Parses tool calls from different LLM providers."""

    @staticmethod
    def parse_claude_tools(response_content: List[Any]) -> List[ToolCallResponse]:
        """Extract tool calls from Claude API response."""
        tool_calls = []

        for block in response_content:
            if block.type == "tool_use":
                tool_calls.append(
                    ToolCallResponse(
                        tool_name=block.name,
                        tool_input=block.input,
                        tool_use_id=block.id
                    )
                )

        return tool_calls

    @staticmethod
    def parse_openai_tools(tool_calls: Optional[List[Any]]) -> List[ToolCallResponse]:
        """Extract tool calls from OpenAI API response."""
        if not tool_calls:
            return []

        parsed = []
        for call in tool_calls:
            parsed.append(
                ToolCallResponse(
                    tool_name=call.function.name,
                    tool_input=json.loads(call.function.arguments),
                    tool_use_id=call.id
                )
            )

        return parsed

    @staticmethod
    def parse_gemini_tools(response_parts: Optional[List[Any]]) -> List[ToolCallResponse]:
        """Extract tool calls from Gemini API response."""
        if not response_parts:
            return []

        parsed = []
        for part in response_parts:
            if hasattr(part, "function_call"):
                parsed.append(
                    ToolCallResponse(
                        tool_name=part.function_call.name,
                        tool_input=dict(part.function_call.args)
                    )
                )

        return parsed
