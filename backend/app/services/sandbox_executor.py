"""
High-level sandbox execution service.
Orchestrates code execution, persistence, and knowledge integration.
"""

import logging
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.sandbox import SandboxExecution
from app.models import ExecutionResult, User
from app.config import settings
from app.services.redis_cache import RedisCache

logger = logging.getLogger(__name__)


class ExecutionRequest:
    """Request model for code execution."""

    def __init__(
        self,
        code: str,
        user_id: UUID,
        timeout_seconds: Optional[int] = None,
        include_in_knowledge_base: bool = False,
        conversation_id: Optional[UUID] = None,
    ):
        self.code = code
        self.user_id = user_id
        self.timeout_seconds = timeout_seconds or settings.SANDBOX_TIMEOUT_SECONDS
        self.include_in_knowledge_base = include_in_knowledge_base
        self.conversation_id = conversation_id


class SandboxExecutor:
    """Orchestrates sandbox execution, persistence, and caching."""

    CACHE_PREFIX = "execution:"
    CACHE_TTL = 3600  # 1 hour

    def __init__(self, db_session: Session):
        self.db = db_session
        self.cache = RedisCache()

    async def execute(self, request: ExecutionRequest) -> Dict[str, Any]:
        """
        Execute code and store results.

        Args:
            request: ExecutionRequest with code and metadata

        Returns:
            Dictionary with execution_id and status
        """
        execution_id = uuid4()

        # Check rate limit
        if not self._check_rate_limit(request.user_id):
            logger.warning(f"Rate limit exceeded for user {request.user_id}")
            return {
                "status": "error",
                "error": "Rate limit exceeded",
                "execution_id": str(execution_id),
            }

        try:
            # Create database record with PENDING status
            execution_record = ExecutionResult(
                id=execution_id,
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                input_code=request.code,
                status="pending",
                timeout_seconds=request.timeout_seconds,
                started_at=datetime.now(timezone.utc),
            )
            self.db.add(execution_record)
            self.db.commit()

            logger.info(f"Created execution record {execution_id} for user {request.user_id}")

            # Execute code asynchronously
            result = await SandboxExecution.execute(
                code=request.code,
                timeout_seconds=request.timeout_seconds,
                memory_limit_mb=settings.SANDBOX_MEMORY_LIMIT_MB,
                max_output_size=settings.SANDBOX_MAX_OUTPUT_SIZE,
                blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES,
            )

            # Update execution record with results
            execution_record.status = result["status"]
            execution_record.stdout = result.get("stdout")
            execution_record.stderr = result.get("stderr")
            execution_record.exit_code = result.get("exit_code")
            execution_record.execution_duration_ms = result.get("execution_duration_ms")
            execution_record.memory_peak_mb = result.get("memory_peak_mb")
            execution_record.completed_at = datetime.now(timezone.utc)

            self.db.commit()
            logger.info(f"Completed execution {execution_id} with status {result['status']}")

            # Cache result for 1 hour
            cache_key = f"{self.CACHE_PREFIX}{str(execution_id)}"
            self._cache_result(cache_key, {
                "id": str(execution_id),
                "status": result["status"],
                "stdout": result.get("stdout"),
                "stderr": result.get("stderr"),
                "exit_code": result.get("exit_code"),
                "execution_duration_ms": result.get("execution_duration_ms"),
                "memory_peak_mb": result.get("memory_peak_mb"),
                "created_at": execution_record.created_at.isoformat(),
            })

            # Optional: Ingest into knowledge base
            if request.include_in_knowledge_base and result["status"] == "success":
                self._ingest_to_knowledge_base(execution_id, request, result)

            return {
                "status": "success",
                "execution_id": str(execution_id),
                "result": result,
            }

        except Exception as e:
            logger.error(f"Execution orchestration failed: {str(e)}", exc_info=True)

            # Update record with error
            try:
                execution_record.status = "error"
                execution_record.stderr = str(e)
                execution_record.completed_at = datetime.now(timezone.utc)
                self.db.commit()
            except Exception:
                pass

            return {
                "status": "error",
                "error": f"Execution failed: {str(e)}",
                "execution_id": str(execution_id),
            }

    def get_result(self, execution_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve execution result from database or cache.

        Args:
            execution_id: UUID of execution to retrieve

        Returns:
            Execution result or None if not found
        """
        # Try cache first
        cache_key = f"{self.CACHE_PREFIX}{str(execution_id)}"
        cached = self._get_cached_result(cache_key)
        if cached:
            return cached

        # Query database
        try:
            record = self.db.query(ExecutionResult).filter(
                ExecutionResult.id == execution_id
            ).first()

            if not record:
                return None

            result = {
                "id": str(record.id),
                "status": record.status,
                "input_code": record.input_code,
                "stdout": record.stdout,
                "stderr": record.stderr,
                "exit_code": record.exit_code,
                "execution_duration_ms": record.execution_duration_ms,
                "memory_peak_mb": record.memory_peak_mb,
                "created_at": record.created_at.isoformat(),
            }

            # Cache for future requests
            self._cache_result(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to retrieve execution {execution_id}: {str(e)}")
            return None

    def list_user_executions(self, user_id: UUID, limit: int = 50) -> list:
        """
        Get recent executions for a user.

        Args:
            user_id: User UUID
            limit: Maximum number of results

        Returns:
            List of execution records
        """
        try:
            records = self.db.query(ExecutionResult).filter(
                ExecutionResult.user_id == user_id
            ).order_by(ExecutionResult.created_at.desc()).limit(limit).all()

            return [
                {
                    "id": str(r.id),
                    "status": r.status,
                    "execution_duration_ms": r.execution_duration_ms,
                    "memory_peak_mb": r.memory_peak_mb,
                    "created_at": r.created_at.isoformat(),
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f"Failed to list executions for user {user_id}: {str(e)}")
            return []

    def _check_rate_limit(self, user_id: UUID) -> bool:
        """Check if user has exceeded rate limits."""
        # TODO: Implement proper rate limiting with Redis
        # For now, allow all executions
        return True

    def _cache_result(self, cache_key: str, result: Dict) -> None:
        """Cache execution result in Redis."""
        try:
            self.cache.set(cache_key, result, ttl=self.CACHE_TTL)
        except Exception as e:
            logger.warning(f"Failed to cache execution result: {str(e)}")

    def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """Retrieve cached execution result."""
        try:
            return self.cache.get(cache_key)
        except Exception:
            return None

    def _ingest_to_knowledge_base(
        self,
        execution_id: UUID,
        request: ExecutionRequest,
        result: Dict[str, Any],
    ) -> None:
        """
        Ingest successful execution result into knowledge base.
        TODO: Implement integration with knowledge_service.py
        """
        logger.info(
            f"Preparing to ingest execution {execution_id} to knowledge base"
        )
        # Will be implemented in Phase 7
        pass
