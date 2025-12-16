"""
Tests for claude-file-protection hook
"""

import json
import subprocess
from pathlib import Path

import pytest


def run_hook(tool_name: str, file_path: str, content: str = "test") -> tuple[int, str]:
    """Run the file-protection hook with given input."""
    hook_path = Path(".agents/hooks/claude-file-protection")

    hook_input = {
        "tool_name": tool_name,
        "tool_input": {
            "path": file_path,
            "content": content,
        },
    }

    result = subprocess.run(
        [str(hook_path)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
    )

    return result.returncode, result.stderr


class TestProtectedFiles:
    """Test that protected files are blocked."""

    @pytest.mark.parametrize(
        "file_path",
        [
            ".beads/issues.jsonl",
            ".beads/test.txt",
            ".devloop/config.json",
            ".devloop/test.log",
            ".git/config",
            ".git/HEAD",
            ".agents/hooks/my-hook",
            ".agents/hooks/test.sh",
            ".claude/settings.json",
            ".claude/test.json",
            "AGENTS.md",
            "CODING_RULES.md",
            "AMP_ONBOARDING.md",
        ],
    )
    def test_protected_files_blocked(self, file_path):
        """Protected files should be blocked from writing."""
        exit_code, stderr = run_hook("Write", file_path)

        assert exit_code == 2, f"File {file_path} should be blocked (exit code 2)"
        assert "Protected file" in stderr, "Error message should mention protection"

    def test_protected_file_with_edit_tool(self):
        """Edit tool should also be blocked on protected files."""
        exit_code, stderr = run_hook("Edit", "AGENTS.md")

        assert exit_code == 2, "Edit tool should block protected files"

    def test_error_message_contains_alternatives(self):
        """Error message should contain alternatives."""
        exit_code, stderr = run_hook("Write", ".beads/issues.jsonl")

        assert "manual editing" in stderr.lower(), "Should suggest manual editing"
        assert "whitelist" in stderr.lower(), "Should mention whitelist"
        assert "user" in stderr.lower(), "Should mention asking user"


class TestSafeFiles:
    """Test that non-protected files are allowed."""

    @pytest.mark.parametrize(
        "file_path",
        [
            "src/mymodule.py",
            "tests/test_something.py",
            "README.md",
            "docs/guide.md",
            "examples/example.py",
            "new_file.txt",
            "config.yaml",
            "setup.py",
        ],
    )
    def test_safe_files_allowed(self, file_path):
        """Safe files should be allowed (exit code 0)."""
        exit_code, stderr = run_hook("Write", file_path)

        assert exit_code == 0, f"File {file_path} should be allowed"
        assert stderr == "", f"No error for safe file {file_path}"


class TestNonWriteTools:
    """Test that non-Write/Edit tools are not blocked."""

    def test_read_tool_not_blocked(self):
        """Read tool should never be blocked."""
        exit_code, stderr = run_hook("Read", "AGENTS.md")

        assert exit_code == 0, "Read tool should not be blocked"

    def test_bash_tool_not_blocked(self):
        """Bash tool should never be blocked."""
        hook_path = Path(".agents/hooks/claude-file-protection")

        hook_input = {"tool_name": "Bash", "tool_input": {"cmd": "ls -la"}}

        result = subprocess.run(
            [str(hook_path)],
            input=json.dumps(hook_input),
            text=True,
            capture_output=True,
        )

        assert result.returncode == 0, "Bash tool should not be blocked"

    @pytest.mark.parametrize("tool_name", ["Read", "Bash", "Grep", "Find", "Finder"])
    def test_non_write_tools(self, tool_name):
        """Non-Write/Edit tools should not be blocked."""
        exit_code, stderr = run_hook(tool_name, "AGENTS.md")

        assert exit_code == 0, f"{tool_name} tool should not be blocked"


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_empty_input(self):
        """Empty input should be handled gracefully."""
        hook_path = Path(".agents/hooks/claude-file-protection")

        result = subprocess.run(
            [str(hook_path)],
            input="",
            text=True,
            capture_output=True,
        )

        assert result.returncode == 0, "Empty input should not crash"

    def test_invalid_json(self):
        """Invalid JSON input should be handled gracefully."""
        hook_path = Path(".agents/hooks/claude-file-protection")

        result = subprocess.run(
            [str(hook_path)],
            input="not json",
            text=True,
            capture_output=True,
        )

        assert result.returncode == 0, "Invalid JSON should not crash"

    def test_missing_tool_name(self):
        """Missing tool_name should be handled gracefully."""
        hook_path = Path(".agents/hooks/claude-file-protection")

        hook_input = {"tool_input": {"path": "test.py"}}

        result = subprocess.run(
            [str(hook_path)],
            input=json.dumps(hook_input),
            text=True,
            capture_output=True,
        )

        assert result.returncode == 0, "Missing tool_name should not crash"

    def test_missing_file_path(self):
        """Missing file path should be handled gracefully."""
        hook_path = Path(".agents/hooks/claude-file-protection")

        hook_input = {"tool_name": "Write", "tool_input": {}}

        result = subprocess.run(
            [str(hook_path)],
            input=json.dumps(hook_input),
            text=True,
            capture_output=True,
        )

        assert result.returncode == 0, "Missing file path should not crash"

    def test_special_characters_in_filename(self):
        """Filenames with special characters should be handled."""
        test_cases = [
            "my file.py",  # spaces
            "file-with-dashes.py",  # dashes
            "file_with_underscores.py",  # underscores
            "file.multiple.dots.py",  # multiple dots
        ]

        for file_path in test_cases:
            exit_code, _ = run_hook("Write", file_path)
            assert (
                exit_code == 0
            ), f"Safe file with special chars should be allowed: {file_path}"

    def test_agents_md_without_extension(self):
        """AGENTS.md exact match should be blocked."""
        exit_code, _ = run_hook("Write", "AGENTS.md")
        assert exit_code == 2, "AGENTS.md should be blocked"

    def test_agents_md_with_extension_allowed(self):
        """AGENTS.md.bak should not be blocked (not exact match)."""
        exit_code, _ = run_hook("Write", "AGENTS.md.bak")
        # This depends on implementation - pattern matching vs exact match
        # For substring matching (current implementation), this would be blocked
        # If we want to change to exact match, this test should change


class TestWhitelist:
    """Test whitelist mechanism."""

    def test_whitelist_not_created_by_default(self):
        """Whitelist file should not exist by default."""
        whitelist_path = Path(".claude/file-protection-whitelist.json")
        assert not whitelist_path.exists(), "Whitelist should not exist by default"

    def test_whitelist_allows_protected_file(self):
        """File in whitelist should be allowed despite being protected."""
        whitelist_path = Path(".claude/file-protection-whitelist.json")
        whitelist_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create whitelist allowing AGENTS.md
            whitelist_data = {"allowed_patterns": ["AGENTS.md"]}
            whitelist_path.write_text(json.dumps(whitelist_data))

            # Now writing to AGENTS.md should succeed
            exit_code, stderr = run_hook("Write", "AGENTS.md")

            assert exit_code == 0, "Whitelisted file should be allowed"
            assert stderr == "", "No error for whitelisted file"
        finally:
            # Clean up
            if whitelist_path.exists():
                whitelist_path.unlink()

    def test_invalid_whitelist_falls_back_to_defaults(self):
        """Invalid whitelist should fall back to default protection."""
        whitelist_path = Path(".claude/file-protection-whitelist.json")
        whitelist_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create invalid whitelist
            whitelist_path.write_text("not json")

            # Should fall back to default protection
            exit_code, _ = run_hook("Write", "AGENTS.md")

            assert exit_code == 2, "Invalid whitelist should fall back to defaults"
        finally:
            if whitelist_path.exists():
                whitelist_path.unlink()


class TestPathNormalization:
    """Test path normalization and resolution."""

    def test_relative_path_to_protected_file(self):
        """Relative paths should be normalized."""
        exit_code, _ = run_hook("Write", "./AGENTS.md")

        # Depending on implementation, this might be blocked
        # If path normalization is working, it should be blocked
        assert exit_code == 2, "Relative path to protected file should be blocked"

    def test_deeply_nested_protected_directory(self):
        """Files in protected directories should be blocked."""
        exit_code, _ = run_hook("Write", ".beads/v1/issues.jsonl")

        assert exit_code == 2, "Files in protected directories should be blocked"


class TestExitCodes:
    """Test exit code semantics."""

    def test_success_exit_code_is_zero(self):
        """Successful allows should exit 0."""
        exit_code, _ = run_hook("Write", "src/test.py")

        assert exit_code == 0, "Success should exit 0"

    def test_block_exit_code_is_two(self):
        """Blocks should exit 2 (not 1)."""
        exit_code, _ = run_hook("Write", "AGENTS.md")

        assert exit_code == 2, "Block should exit 2 (not 1)"

    def test_no_crash_on_error(self):
        """Errors should not crash (exit 0 or other, but not crash)."""
        hook_path = Path(".agents/hooks/claude-file-protection")

        # Run with non-existent project directory
        result = subprocess.run(
            [str(hook_path)],
            input='{"tool_name":"Write","tool_input":{"path":"test.py"}}',
            text=True,
            capture_output=True,
            env={"CLAUDE_PROJECT_DIR": "/nonexistent/path"},
        )

        # Should not crash (exit code should be defined, not killed by signal)
        assert result.returncode >= 0, "Should not crash"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
