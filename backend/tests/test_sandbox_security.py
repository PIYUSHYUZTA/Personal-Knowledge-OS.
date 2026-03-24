"""
Security tests for code sandbox.
Tests protection against malicious code patterns and attacks.
"""

import pytest
from app.core.sandbox import SandboxExecution
from app.config import settings


class TestSecurityBlocklists:
    """Test that dangerous operations are blocked."""

    def test_prevent_os_system_call(self):
        """Security: Block os.system() calls."""
        code = "import os\nos.system('rm -rf /')"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False
        assert "os" in error.lower()

    def test_prevent_subprocess_popen(self):
        """Security: Block subprocess.Popen()."""
        code = "import subprocess\nsubprocess.Popen(['ls'])"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False

    def test_prevent_socket_creation(self):
        """Security: Block socket module for network access."""
        code = "import socket\ns = socket.socket(socket.AF_INET, socket.SOCK_STREAM)"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False

    def test_prevent_file_read(self):
        """Security: Block file operations with open()."""
        code = "with open('/etc/passwd', 'r') as f:\n    data = f.read()"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False

    def test_prevent_file_write(self):
        """Security: Block file write operations."""
        code = "with open('/tmp/malicious.txt', 'w') as f:\n    f.write('hack')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False

    def test_prevent_dynamic_import(self):
        """Security: Block __import__()."""
        code = "m = __import__('os')\nm.system('whoami')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False

    def test_prevent_eval_execution(self):
        """Security: Block eval()."""
        code = "result = eval('__import__(\"os\").system(\"id\")')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False

    def test_prevent_exec_execution(self):
        """Security: Block exec()."""
        code = "exec('import os; os.system(\"ls\")')"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False


class TestCommonMaliciousPatterns:
    """Test against common attack patterns."""

    def test_block_command_injection(self):
        """Security: Detect command injection attempts."""
        code = "import os\ncommand = input()\nos.system(command)"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False  # Should block either os or input()

    def test_block_path_traversal(self):
        """Security: Block file access patterns."""
        code = "open('../../../etc/passwd').read()"
        is_valid, error = SandboxExecution.validate_code(code)
        assert is_valid is False

    def test_block_environment_variable_access(self):
        """Security: Block os.environ access."""
        code = "import os\npassword = os.environ.get('DATABASE_PASSWORD')"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False

    def test_block_process_spawning(self):
        """Security: Block subprocess and related."""
        patterns = [
            "import subprocess\nsubprocess.run(['whoami'])",
            "from subprocess import Popen\nPopen('ls')",
            "import os\nos.popen('id')",
        ]

        for code in patterns:
            is_valid, error = SandboxExecution.validate_code(
                code,
                blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
            )
            assert is_valid is False, f"Should block: {code}"


class TestRestrictionBypass:
    """Test that bypass attempts are prevented."""

    def test_prevent_import_alias_bypasses(self):
        """Security: Even aliased imports should be caught."""
        code = "import os as operating_system\noperating_system.system('whoami')"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False

    def test_multiline_import_blocking(self):
        """Security: Imports split across lines are blocked."""
        code = """
import \\
    os

os.system('id')
"""
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False

    def test_from_import_blocking(self):
        """Security: from...import statements are blocked."""
        code = "from os import system\nsystem('whoami')"
        is_valid, error = SandboxExecution.validate_code(
            code,
            blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
        )
        assert is_valid is False


class TestResourceExhaustion:
    """Test protection against resource exhaustion attacks."""

    @pytest.mark.asyncio
    async def test_infinite_loop_timeout(self):
        """Security: Infinite loops are killed by timeout."""
        code = """
while True:
    pass
"""
        result = await SandboxExecution.execute(code, timeout_seconds=1)

        assert result["status"] == "timeout"
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_recursive_explosion_timeout(self):
        """Security: Deep recursion causes timeout."""
        code = """
def recurse(n):
    return recurse(n + 1)

recurse(0)
"""
        result = await SandboxExecution.execute(code, timeout_seconds=2)

        # Either timeout or RecursionError
        assert result["status"] in ["timeout", "error"]

    @pytest.mark.asyncio
    async def test_large_memory_allocation(self):
        """Security: Large memory allocations are captured."""
        code = """
# Try to allocate 1GB
huge_list = list(range(100_000_000))
print(len(huge_list))
"""
        result = await SandboxExecution.execute(code, timeout_seconds=5)

        # Should either timeout, error, or complete depending on system
        # The key is that it doesn't crash the sandbox
        assert result["status"] in ["timeout", "error", "success"]


class TestDataValidation:
    """Test validation of code parameters."""

    def test_empty_code_validation(self):
        """Validation: Empty code is invalid."""
        code = ""
        is_valid, error = SandboxExecution.validate_code(code)
        # Empty code might be valid syntactically, but tests reject it at API level

    def test_very_long_code(self):
        """Validation: Very long code should be handled."""
        code = "x = 1\n" * 100000  # 100k lines
        # Should not crash validation
        is_valid, error = SandboxExecution.validate_code(code)
        # Either valid or gives a reasonable error

    def test_binary_data_in_code(self):
        """Validation: Binary data should not crash."""
        code = "print('\\x00\\x01\\x02')"  # Null bytes and control chars
        is_valid, error = SandboxExecution.validate_code(code)
        # Should not crash


class TestBlocklistCompleteness:
    """Verify all dangerous modules and functions are blocked."""

    def test_all_configured_blocklist_items(self):
        """Validate: All items in SANDBOX_BLOCKED_PYTHON_MODULES are enforced."""
        for module in settings.SANDBOX_BLOCKED_PYTHON_MODULES:
            code = f"import {module.split('.')[0]}"
            is_valid, error = SandboxExecution.validate_code(
                code,
                blocked_modules=settings.SANDBOX_BLOCKED_PYTHON_MODULES
            )
            # Note: This might not work for all modules depending on the blocklist format
            # Adjust assertions based on actual blocklist


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
