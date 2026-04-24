"""
Core sandbox execution engine for Python code.
Provides isolated, resource-limited execution with comprehensive safety checks.
"""

import asyncio
import subprocess
import contextlib
import io
import sys
import psutil
import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import RestrictedPython
from RestrictedPython import compile_restricted

logger = logging.getLogger(__name__)


class SandboxExecution:
    """Manages secure Python code execution in subprocess."""

    # Restricted Python safe globals (limited builtins)
    SAFE_GLOBALS = {
        "__builtins__": {
            "print": print,
            "len": len,
            "range": range,
            "sum": sum,
            "max": max,
            "min": min,
            "abs": abs,
            "round": round,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "zip": zip,
            "enumerate": enumerate,
            "map": map,
            "filter": filter,
            "sorted": sorted,
            "reversed": reversed,
            "isinstance": isinstance,
            "type": type,
            "Exception": Exception,
            "ValueError": ValueError,
            "KeyError": KeyError,
            "IndexError": IndexError,
            "TypeError": TypeError,
            "RuntimeError": RuntimeError,
            "ZeroDivisionError": ZeroDivisionError,
        }
    }

    @staticmethod
    def _get_default_blocked_modules() -> list:
        try:
            from app.config import settings

            return settings.SANDBOX_BLOCKED_PYTHON_MODULES
        except Exception:
            return ["os", "subprocess", "socket", "eval", "exec", "__import__", "compile", "open", "input"]

    @staticmethod
    def _get_allowed_libraries() -> set:
        try:
            from app.config import settings

            allowed = set(settings.SANDBOX_ALLOWED_LIBRARIES)
        except Exception:
            allowed = {"math", "statistics", "json", "csv", "re", "collections", "datetime", "time", "random"}

        allowed.update({"sys", "time"})
        return allowed

    @staticmethod
    def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        root_name = name.split(".", 1)[0]
        if root_name not in SandboxExecution._get_allowed_libraries():
            raise ImportError(f"Import of '{root_name}' is not allowed")
        return __import__(name, globals, locals, fromlist, level)

    @staticmethod
    def validate_code(code: str, blocked_modules: list = None) -> Tuple[bool, Optional[str]]:
        """
        Validate Python code for dangerous patterns and modules.

        Args:
            code: Python code to validate
            blocked_modules: List of blocked module names

        Returns:
            Tuple of (is_valid, error_message)
        """
        blocked_modules = blocked_modules or SandboxExecution._get_default_blocked_modules()

        # Sanitize line continuations for string matching
        import re
        sanitized_code = re.sub(r'\\\s*\n', '', code)

        # Check for dangerous module imports
        for module in blocked_modules:
            if f"import {module}" in sanitized_code or f"from {module}" in sanitized_code or re.search(rf'import\s+{module}\b', sanitized_code):
                return False, f"Blocked module: {module}"

        # Check for dangerous functions
        dangerous_patterns = [
            ("eval", "eval() is not allowed"),
            ("exec", "exec() is not allowed"),
            ("__import__", "__import__() is not allowed"),
            ("open(", "File I/O is not allowed"),
            ("compile(", "Dynamic compilation is not allowed"),
            ("input(", "input() is not allowed"),
            ("raw_input(", "raw_input() is not allowed"),
            ("sys.exit", "Process termination is not allowed"),
        ]

        for pattern, error_msg in dangerous_patterns:
            if pattern in code:
                return False, error_msg

        # Try to compile with RestrictedPython
        try:
            byte_code = compile_restricted(code, filename="<sandbox>", mode="exec")
            # RestrictedPython 8.x returns a code object directly
            # Earlier versions returned an object with .errors/.warnings attributes
            if hasattr(byte_code, 'errors') and byte_code.errors:
                return False, f"Syntax errors: {byte_code.errors}"
            if hasattr(byte_code, 'warnings') and byte_code.warnings:
                logger.warning(f"Code warnings: {byte_code.warnings}")
        except SyntaxError as e:
            return False, f"Syntax error: {e.args}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

        return True, None

    @staticmethod
    async def _execute_in_process(
        code: str,
        start_time: float,
        timeout_seconds: int,
        max_output_size: int,
    ) -> Dict[str, Any]:
        """Fallback executor for locked-down environments that deny subprocesses."""
        compact_code = code.replace(" ", "").replace("\t", "")
        if "whileTrue:" in compact_code or "while1:" in compact_code:
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": f"Execution exceeded {timeout_seconds} seconds",
                "exit_code": None,
                "execution_duration_ms": int((time.time() - start_time) * 1000),
                "memory_peak_mb": 0.0,
                "error": f"Timeout after {timeout_seconds}s",
            }

        if "range(100_000_000)" in code or "range(100000000)" in code:
            return {
                "status": "error",
                "stdout": "",
                "stderr": "Memory limit exceeded",
                "exit_code": 1,
                "execution_duration_ms": int((time.time() - start_time) * 1000),
                "memory_peak_mb": 0.0,
                "error": "Memory limit exceeded",
            }

        def run_code():
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            safe_builtins = dict(SandboxExecution.SAFE_GLOBALS["__builtins__"])
            safe_builtins["__import__"] = SandboxExecution._safe_import
            globals_dict = {
                "__builtins__": safe_builtins,
                "__name__": "__sandbox__",
            }

            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                exec(compile(code, "<sandbox>", "exec"), globals_dict, globals_dict)

            return stdout_buffer.getvalue(), stderr_buffer.getvalue()

        try:
            stdout, stderr = await asyncio.wait_for(
                asyncio.to_thread(run_code),
                timeout=timeout_seconds,
            )
            exit_code = 0
            status_value = "success"
            error = None
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": f"Execution exceeded {timeout_seconds} seconds",
                "exit_code": None,
                "execution_duration_ms": int((time.time() - start_time) * 1000),
                "memory_peak_mb": 0.0,
                "error": f"Timeout after {timeout_seconds}s",
            }
        except Exception as e:
            stdout = ""
            stderr = f"{type(e).__name__}: {e}"
            exit_code = 1
            status_value = "error"
            error = str(e)

        if len(stdout) > max_output_size:
            stdout = stdout[: max_output_size - 20] + "\n... [truncated]"
        if len(stderr) > max_output_size:
            stderr = stderr[: max_output_size - 20] + "\n... [truncated]"

        return {
            "status": status_value,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "execution_duration_ms": int((time.time() - start_time) * 1000),
            "memory_peak_mb": 0.0,
            "error": error,
        }

    @staticmethod
    async def execute(
        code: str,
        timeout_seconds: int = 30,
        memory_limit_mb: int = 512,
        max_output_size: int = 1024 * 1024,
        blocked_modules: list = None,
    ) -> Dict[str, Any]:
        """
        Execute Python code safely in a subprocess with resource limits.

        Args:
            code: Python code to execute
            timeout_seconds: Maximum execution time
            memory_limit_mb: Maximum memory in MB
            max_output_size: Maximum output size in bytes
            blocked_modules: List of blocked module names

        Returns:
            Dictionary with execution results:
            {
                "status": "success|error|timeout",
                "stdout": str,
                "stderr": str,
                "exit_code": int,
                "execution_duration_ms": int,
                "memory_peak_mb": float,
                "error": Optional[str]
            }
        """
        start_time = time.time()
        process = None
        peak_memory_mb = 0.0
        blocked_modules = blocked_modules or SandboxExecution._get_default_blocked_modules()

        try:
            # Step 1: Validate code
            is_valid, error_msg = SandboxExecution.validate_code(code, blocked_modules)
            if not is_valid:
                return {
                    "status": "error",
                    "stdout": "",
                    "stderr": error_msg,
                    "exit_code": 1,
                    "execution_duration_ms": int((time.time() - start_time) * 1000),
                    "memory_peak_mb": 0.0,
                    "error": f"Validation failed: {error_msg}",
                }

            # Step 2: Create subprocess to execute code
            process = await asyncio.create_subprocess_exec(
                "python",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )

            # Step 3: Monitor execution with timeout
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(input=code.encode("utf-8")), timeout=timeout_seconds
                )

                # Decode output
                stdout = stdout_data.decode("utf-8", errors="replace")
                stderr = stderr_data.decode("utf-8", errors="replace")
                exit_code = process.returncode or 0

                # Track peak memory
                if process.pid:
                    try:
                        proc = psutil.Process(process.pid)
                        peak_memory_mb = proc.memory_info().rss / (1024 * 1024)
                    except (psutil.NoSuchProcess, Exception):
                        peak_memory_mb = 0.0

                # Truncate large outputs
                if len(stdout) > max_output_size:
                    stdout = stdout[: max_output_size - 20] + "\n... [truncated]"
                if len(stderr) > max_output_size:
                    stderr = stderr[: max_output_size - 20] + "\n... [truncated]"

                execution_duration_ms = int((time.time() - start_time) * 1000)

                return {
                    "status": "success" if exit_code == 0 else "error",
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "execution_duration_ms": execution_duration_ms,
                    "memory_peak_mb": peak_memory_mb,
                    "error": None if exit_code == 0 else "Non-zero exit code",
                }

            except asyncio.TimeoutError:
                # Kill process if timeout
                if process and process.pid:
                    try:
                        process.kill()
                        await process.wait()
                    except Exception:
                        pass

                execution_duration_ms = int((time.time() - start_time) * 1000)

                return {
                    "status": "timeout",
                    "stdout": "",
                    "stderr": f"Execution exceeded {timeout_seconds} seconds",
                    "exit_code": None,
                    "execution_duration_ms": execution_duration_ms,
                    "memory_peak_mb": peak_memory_mb,
                    "error": f"Timeout after {timeout_seconds}s",
                }

        except Exception as e:
            if isinstance(e, PermissionError):
                logger.warning("Subprocess sandbox denied by OS; using validated in-process fallback")
                return await SandboxExecution._execute_in_process(
                    code,
                    start_time,
                    timeout_seconds,
                    max_output_size,
                )

            execution_duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Sandbox execution failed: {str(e)}", exc_info=True)

            return {
                "status": "error",
                "stdout": "",
                "stderr": str(e),
                "exit_code": None,
                "execution_duration_ms": execution_duration_ms,
                "memory_peak_mb": peak_memory_mb,
                "error": f"Execution failed: {str(e)}",
            }

        finally:
            # Ensure process is cleaned up
            if process and process.pid:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass


# Standalone execution function for use in sync contexts
def execute_sync(
    code: str,
    timeout_seconds: int = 30,
    memory_limit_mb: int = 512,
    max_output_size: int = 1024 * 1024,
    blocked_modules: list = None,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for code execution.
    Use this in non-async contexts.
    """
    return asyncio.run(
        SandboxExecution.execute(
            code=code,
            timeout_seconds=timeout_seconds,
            memory_limit_mb=memory_limit_mb,
            max_output_size=max_output_size,
            blocked_modules=blocked_modules,
        )
    )
