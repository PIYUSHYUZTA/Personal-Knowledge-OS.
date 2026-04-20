"""
FastAPI routes for code sandbox execution.
Provides endpoints for submitting, polling, and validating code execution.
"""

import logging
from uuid import UUID
from fastapi import APIRouter, Query, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.security import verify_token, extract_user_id_from_token
from app.core.sandbox import SandboxExecution
from app.services.sandbox_executor import SandboxExecutor, ExecutionRequest
from app.schemas import (
    CodeExecutionRequest,
    ExecutionStartedResponse,
    CodeValidationResponse,
    ExecutionResultResponse,
    ExecutionListResponse,
)
from app.models import ExecutionResult, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sandbox", tags=["Code Sandbox"])


# ============================================================================
# SYNCHRONOUS ENDPOINTS
# ============================================================================


@router.post("/execute", response_model=ExecutionStartedResponse)
async def execute_code(
    request: CodeExecutionRequest,
    token: str = Query(...),
    db_session: Session = Depends(get_db),
):
    """
    Submit code for execution in isolated sandbox.
    Returns immediately with execution_id. Use GET /result/{id} to poll for results.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        # Validate UUID format (User IDs are stored as strings)
        UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format")
    
    user = db_session.query(User).filter(User.id == user_id_str).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        executor = SandboxExecutor(db_session)
        exec_request = ExecutionRequest(
            code=request.code,
            user_id=user_id_str,
            timeout_seconds=request.timeout_seconds,
            include_in_knowledge_base=request.include_in_knowledge_base,
        )

        result = await executor.execute(exec_request)

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))

        return ExecutionStartedResponse(
            execution_id=UUID(result["execution_id"]),
            status="queued",
            message="Code execution queued successfully",
            created_at=result.get("created_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execution submission failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Execution failed: {str(e)}"
        )


@router.get("/result/{execution_id}", response_model=ExecutionResultResponse)
def get_execution_result(
    execution_id: UUID,
    token: str = Query(...),
    db_session: Session = Depends(get_db),
):
    """
    Retrieve result of a completed execution.
    Returns 202 Accepted if still running.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        executor = SandboxExecutor(db_session)
        result = executor.get_result(execution_id)

        if not result:
            raise HTTPException(status_code=404, detail="Execution not found")

        # Verify user owns this execution
        record = db_session.query(ExecutionResult).filter(
            ExecutionResult.id == execution_id
        ).first()
        if record and str(record.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if still running
        if result.get("status") == "pending":
            raise HTTPException(status_code=202, detail="Still running")

        return ExecutionResultResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve result")


@router.get("/history", response_model=list[ExecutionListResponse])
def get_execution_history(
    token: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    db_session: Session = Depends(get_db),
):
    """
    Get recent execution history for authenticated user.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        executor = SandboxExecutor(db_session)
        executions = executor.list_user_executions(user_id, limit=limit)
        return executions

    except Exception as e:
        logger.error(f"Failed to get execution history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


@router.post("/validate", response_model=CodeValidationResponse)
def validate_code(
    request: CodeExecutionRequest,
    token: str = Query(...),
    db_session: Session = Depends(get_db),
):
    """
    Validate code for safety before execution.
    Useful for IDE integration and quick feedback.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        from app.config import settings

        is_safe, error_msg = SandboxExecution.validate_code(
            code=request.code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES,
        )

        return CodeValidationResponse(
            safe_to_execute=is_safe,
            issues=[error_msg] if error_msg else [],
            warnings=[],
        )

    except Exception as e:
        logger.error(f"Code validation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Validation failed")


# ============================================================================
# WEBSOCKET STREAMING
# ============================================================================


@router.websocket("/ws/execute")
async def websocket_execute_stream(
    websocket: WebSocket,
    token: str = Query(...),
    db_session: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time execution streaming.
    Client sends code, receives status updates and output tokens.
    """
    # Verify authentication
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = extract_user_id_from_token(payload)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logger.info(f"WebSocket connection established for user {user_id}")

    try:
        # Receive execution request from client
        data = await websocket.receive_json()
        code = data.get("code")
        timeout_seconds = data.get("timeout_seconds", 30)
        include_in_knowledge_base = data.get("include_in_knowledge_base", False)

        if not code:
            await websocket.send_json({
                "type": "error",
                "content": "No code provided",
            })
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
            return

        # Send validation status
        await websocket.send_json({
            "type": "status",
            "content": "Validating code...",
        })

        # Validate code
        from app.config import settings

        is_safe, error_msg = SandboxExecution.validate_code(
            code=code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES,
        )

        if not is_safe:
            await websocket.send_json({
                "type": "error",
                "content": f"Validation failed: {error_msg}",
            })
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
            return

        # Send execution status
        await websocket.send_json({
            "type": "status",
            "content": "Executing code...",
        })

        # Execute code
        executor = SandboxExecutor(db_session)
        exec_request = ExecutionRequest(
            code=code,
            user_id=user_id,
            timeout_seconds=timeout_seconds,
            include_in_knowledge_base=include_in_knowledge_base,
        )

        result = await executor.execute(exec_request)

        # Send result
        if result["status"] == "error":
            await websocket.send_json({
                "type": "error",
                "content": result.get("error", "Unknown error"),
            })
        else:
            execution_result = result.get("result", {})

            # Send stdout if available
            if execution_result.get("stdout"):
                await websocket.send_json({
                    "type": "output",
                    "content": execution_result["stdout"],
                })

            # Send stderr if available
            if execution_result.get("stderr"):
                await websocket.send_json({
                    "type": "error",
                    "content": execution_result["stderr"],
                })

            # Send completion
            await websocket.send_json({
                "type": "complete",
                "status": execution_result.get("status"),
                "exit_code": execution_result.get("exit_code"),
                "execution_duration_ms": execution_result.get("execution_duration_ms"),
                "memory_peak_mb": execution_result.get("memory_peak_mb"),
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Server error: {str(e)}",
            })
        except Exception:
            pass
        finally:
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
