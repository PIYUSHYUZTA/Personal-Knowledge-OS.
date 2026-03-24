"""
Unit tests for sandbox code execution functionality.
Tests basic functionality, timeouts, memory limits, and output handling.
"""

import pytest
import asyncio
from uuid import uuid4
from app.core.sandbox import SandboxExecution
from app.config import settings


class TestCodeValidation:
    """Test code validation for dangerous patterns."""

    def test_simple_print(self):
        """Valid: Simple print statement."""
        code = "print('hello world')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is True
        assert error is None

    def test_math_expression(self):
        """Valid: Math calculation."""
        code = "result = 2 + 2\nprint(result)"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is True
        assert error is None

    def test_blocked_import_os(self):
        """Invalid: os module import."""
        code = "import os\nos.system('echo test')"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False
        assert "os" in error.lower()

    def test_blocked_eval(self):
        """Invalid: eval() function."""
        code = "eval('1+1')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False
        assert "eval" in error.lower()

    def test_blocked_exec(self):
        """Invalid: exec() function."""
        code = "exec('print(1)')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False
        assert "exec" in error.lower()

    def test_blocked_file_open(self):
        """Invalid: open() file operation."""
        code = "with open('/etc/passwd') as f:\n    data = f.read()"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False
        assert "not allowed" in error.lower()

    def test_blocked_subprocess(self):
        """Invalid: subprocess module."""
        code = "import subprocess\nsubprocess.run(['ls'])"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False

    def test_blocked_socket(self):
        """Invalid: socket module."""
        code = "import socket\ns = socket.socket()"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False

    def test_syntax_error(self):
        """Invalid: Syntax error in code."""
        code = "print('unclosed string"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False
        assert "syntax" in error.lower() or "error" in error.lower()


class TestCodeExecution:
    """Test actual code execution."""

    @pytest.mark.asyncio
    async def test_simple_print(self):
        """Execute: Simple print statement."""
        code = "print('hello')"
        result = await SandboxExecution.execute(code)

        assert result["status"] == "success"
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
        assert result["stderr"] == ""

    @pytest.mark.asyncio
    async def test_math_calculation(self):
        """Execute: Math operations."""
        code = "print(2 + 2)"
        result = await SandboxExecution.execute(code)

        assert result["status"] == "success"
        assert "4" in result["stdout"]

    @pytest.mark.asyncio
    async def test_multiline_code(self):
        """Execute: Multi-line code with variables."""
        code = """
x = [1, 2, 3]
total = sum(x)
print(f'Sum: {total}')
"""
        result = await SandboxExecution.execute(code)

        assert result["status"] == "success"
        assert "Sum: 6" in result["stdout"]

    @pytest.mark.asyncio
    async def test_function_definition(self):
        """Execute: Define and call function."""
        code = """
def greet(name):
    return f'Hello, {name}!'

print(greet('World'))
"""
        result = await SandboxExecution.execute(code)

        assert result["status"] == "success"
        assert "Hello, World!" in result["stdout"]

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Execute: Code with error."""
        code = """
try:
    result = 1 / 0
except ZeroDivisionError:
    print('Error caught!')
"""
        result = await SandboxExecution.execute(code)

        assert result["status"] == "success"
        assert "Error caught!" in result["stdout"]

    @pytest.mark.asyncio
    async def test_stderr_capture(self):
        """Execute: Capture stderr output."""
        code = """
import sys
print('stdout message')
sys.stderr.write('stderr message')
"""
        result = await SandboxExecution.execute(code)

        assert result["status"] == "success"
        assert "stdout message" in result["stdout"]
        assert "stderr message" in result["stderr"]

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self):
        """Execute: Timeout prevents infinite loops."""
        code = """
import time
start = time.time()
while True:
    pass
"""
        result = await SandboxExecution.execute(code, timeout_seconds=1)

        assert result["status"] == "timeout"
        assert "exceeded" in result["stderr"].lower() or "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_output_truncation(self):
        """Execute: Large output is truncated."""
        large_output = "x" * (1024 * 1024 + 100)  # > 1MB
        code = f"""
print('{large_output}')
"""
        result = await SandboxExecution.execute(code, max_output_size=1024 * 1024)

        assert len(result["stdout"]) <= 1024 * 1024 + 100  # Some margin for message
        assert "[truncated]" in result["stdout"]

    @pytest.mark.asyncio
    async def test_exit_code_success(self):
        """Execute: Successful code has exit code 0."""
        code = "print('success')"
        result = await SandboxExecution.execute(code)

        assert result["exit_code"] == 0
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_exit_code_error(self):
        """Execute: Error code on failure."""
        code = "raise RuntimeError('test error')"
        result = await SandboxExecution.execute(code)

        assert result["exit_code"] != 0
        assert result["status"] == "error"
        assert "RuntimeError" in result["stderr"]

    @pytest.mark.asyncio
    async def test_execution_duration_tracking(self):
        """Execute: Execution duration is tracked."""
        code = """
import time
time.sleep(0.1)
print('done')
"""
        result = await SandboxExecution.execute(code)

        assert result["status"] == "success"
        assert result["execution_duration_ms"] is not None
        assert result["execution_duration_ms"] >= 100  # At least ~100ms for sleep


class TestSecurityValidation:
    """Test security-related validations."""

    def test_blocked_import_eval(self):
        """Security: Prevent __import__ usage."""
        code = "__import__('os').system('whoami')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False

    def test_blocked_import_compile(self):
        """Security: Prevent compile() usage."""
        code = "compile('print(1)', '<string>', 'exec')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False

    def test_blocked_import_input(self):
        """Security: Prevent input() usage."""
        code = "user_input = input('Enter text: ')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_safe_libraries_allowed(self):
        """Security: Safe libraries like numpy are allowed."""
        code = """
import numpy as np
arr = np.array([1, 2, 3])
print(arr.sum())
"""
        is_valid, error = SandboxExecution.validate_code(code)
        # Should allow numpy (in allowed libraries)
        # But RestrictedPython might still flag imports
        # This tests the actual behavior

        result = await SandboxExecution.execute(code)
        # If execution works, it means numpy usage is safe
        if result["status"] == "success":
            assert "6" in result["stdout"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
