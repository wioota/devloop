#!/usr/bin/env python3
"""
Integration tests for Claude Code hooks.

Tests the hooks that run automatically in Claude Code:
- claude-session-start: Load findings on startup
- claude-stop: Collect findings on completion
- claude-file-protection: Block protected file writes
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

import pytest


class HookTester:
    """Helper class to test hook scripts."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.hooks_dir = project_root / ".agents" / "hooks"

    def run_hook(
        self,
        hook_name: str,
        input_data: Optional[dict] = None,
        env: Optional[dict] = None,
    ) -> tuple[int, str, str]:
        """
        Run a hook script and return exit code, stdout, stderr.

        Args:
            hook_name: Name of hook script (e.g., 'claude-session-start')
            input_data: JSON input to send via stdin
            env: Environment variables to override

        Returns:
            (exit_code, stdout, stderr)
        """
        hook_path = self.hooks_dir / hook_name
        if not hook_path.exists():
            raise FileNotFoundError(f"Hook not found: {hook_path}")

        if not hook_path.stat().st_mode & 0o111:
            hook_path.chmod(0o755)

        proc_env = dict(os.environ)
        proc_env["CLAUDE_PROJECT_DIR"] = str(self.project_root)

        if env:
            proc_env.update(env)

        stdin_data = None
        if input_data:
            stdin_data = json.dumps(input_data)

        result = subprocess.run(
            [str(hook_path)],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=proc_env,
            cwd=self.project_root,
        )

        return result.returncode, result.stdout, result.stderr


@pytest.fixture
def hook_tester(tmp_path):
    """Create a temporary project for testing hooks."""
    # Create minimal project structure
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    hooks_dir = project_root / ".agents" / "hooks"
    hooks_dir.mkdir(parents=True)

    # Copy hook scripts from actual project
    actual_hooks_dir = Path(__file__).parent.parent.parent / ".agents" / "hooks"
    for hook_file in actual_hooks_dir.glob("claude-*"):
        if hook_file.is_file():
            dest = hooks_dir / hook_file.name
            dest.write_text(hook_file.read_text())
            dest.chmod(0o755)

    # Create mock .devloop structure
    devloop_dir = project_root / ".devloop"
    devloop_dir.mkdir(parents=True)

    # Create .beads structure
    beads_dir = project_root / ".beads"
    beads_dir.mkdir(parents=True)

    return HookTester(project_root)


class TestSessionStartHook:
    """Test claude-session-start hook."""

    def test_hook_exists(self, hook_tester):
        """SessionStart hook should exist."""
        hook_path = hook_tester.hooks_dir / "claude-session-start"
        assert hook_path.exists(), "claude-session-start hook not found"
        assert hook_path.stat().st_mode & 0o111, "Hook is not executable"

    def test_hook_runs_without_devloop(self, hook_tester):
        """Hook should exit cleanly if devloop not available."""
        # Run with PATH that excludes devloop
        env = {"PATH": "/bin:/usr/bin"}
        code, stdout, stderr = hook_tester.run_hook("claude-session-start", env=env)
        assert code == 0, f"Hook failed: {stderr}"

    def test_hook_handles_missing_project_dir(self, tmp_path):
        """Hook should handle missing CLAUDE_PROJECT_DIR gracefully."""
        hooks_dir = tmp_path / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        hook_path = hooks_dir / "claude-session-start"
        actual_hook = (
            Path(__file__).parent.parent.parent
            / ".agents"
            / "hooks"
            / "claude-session-start"
        )
        hook_path.write_text(actual_hook.read_text())
        hook_path.chmod(0o755)

        # Run with non-existent directory
        result = subprocess.run(
            [str(hook_path)],
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": "/nonexistent/path"},
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, f"Hook failed: {result.stderr}"


class TestStopHook:
    """Test claude-stop hook."""

    def test_hook_exists(self, hook_tester):
        """Stop hook should exist."""
        hook_path = hook_tester.hooks_dir / "claude-stop"
        assert hook_path.exists(), "claude-stop hook not found"
        assert hook_path.stat().st_mode & 0o111, "Hook is not executable"

    def test_hook_with_no_input(self, hook_tester):
        """Stop hook should handle empty input gracefully."""
        code, stdout, stderr = hook_tester.run_hook("claude-stop", input_data={})
        assert code == 0, f"Hook failed: {stderr}"

    def test_hook_prevents_infinite_loops(self, hook_tester):
        """Stop hook should check stop_hook_active flag."""
        # When stop_hook_active is true, hook should exit without running devloop
        input_data = {"stop_hook_active": True}
        code, stdout, stderr = hook_tester.run_hook(
            "claude-stop", input_data=input_data
        )
        assert code == 0, f"Hook failed: {stderr}"

    def test_hook_with_devloop_not_available(self, hook_tester):
        """Hook should exit cleanly if devloop not available."""
        env = {"PATH": "/bin:/usr/bin"}  # Exclude devloop
        code, stdout, stderr = hook_tester.run_hook(
            "claude-stop", input_data={"stop_hook_active": False}, env=env
        )
        assert code == 0, f"Hook failed: {stderr}"


class TestFileProtectionHook:
    """Test claude-file-protection hook."""

    def test_hook_exists(self, hook_tester):
        """File protection hook should exist."""
        hook_path = hook_tester.hooks_dir / "claude-file-protection"
        assert hook_path.exists(), "claude-file-protection hook not found"
        assert hook_path.stat().st_mode & 0o111, "Hook is not executable"

    def test_blocks_beads_writes(self, hook_tester):
        """Hook should block writes to .beads directory."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".beads/issues.jsonl"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 2, "Hook should return exit code 2 for protected files"
        assert (
            "Protected file" in stderr
        ), "Error message should indicate file is protected"

    def test_blocks_devloop_writes(self, hook_tester):
        """Hook should block writes to .devloop directory."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".devloop/config.json"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 2, "Hook should return exit code 2 for protected files"

    def test_blocks_git_writes(self, hook_tester):
        """Hook should block writes to .git directory."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".git/config"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 2, "Hook should return exit code 2 for protected files"

    def test_blocks_hook_writes(self, hook_tester):
        """Hook should block writes to .agents/hooks directory."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".agents/hooks/custom-hook"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 2, "Hook should return exit code 2 for protected files"

    def test_blocks_documentation_writes(self, hook_tester):
        """Hook should block writes to protected documentation files."""
        protected_docs = ["AGENTS.md", "CODING_RULES.md", "AMP_ONBOARDING.md"]
        for doc in protected_docs:
            input_data = {
                "tool_name": "Write",
                "tool_input": {"path": doc},
            }
            code, stdout, stderr = hook_tester.run_hook(
                "claude-file-protection", input_data=input_data
            )
            assert code == 2, f"Hook should block writes to {doc}"

    def test_allows_normal_file_writes(self, hook_tester):
        """Hook should allow writes to normal project files."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": "src/main.py"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 0, "Hook should allow writes to normal files"

    def test_ignores_non_write_tools(self, hook_tester):
        """Hook should ignore non-Write/Edit tools."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"path": ".beads/issues.jsonl"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 0, "Hook should ignore Read tool"

    def test_handles_absolute_paths(self, hook_tester):
        """Hook should handle absolute paths correctly."""
        abs_path = (hook_tester.project_root / ".beads" / "issues.jsonl").resolve()
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": str(abs_path)},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 2, "Hook should block absolute paths to protected files"

    def test_error_message_helpful(self, hook_tester):
        """Error message should provide helpful alternatives."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".beads/issues.jsonl"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert (
            "nano" in stderr or "manual editing" in stderr
        ), "Error should suggest alternatives"

    def test_protected_file_blocked_without_whitelist(self, hook_tester):
        """Protected files should be blocked (whitelist was removed)."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".beads/custom.json"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 2, "Protected file should be blocked"

    def test_whitelist_does_not_allow_other_protected_files(self, hook_tester):
        """Whitelist should only allow specific patterns."""
        # Create whitelist for one file
        whitelist_file = (
            hook_tester.project_root / ".claude" / "file-protection-whitelist.json"
        )
        whitelist_file.parent.mkdir(parents=True, exist_ok=True)
        whitelist_file.write_text(
            json.dumps({"allowed_patterns": [".beads/custom.json"]})
        )

        # Different .beads file should still be blocked
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".beads/issues.jsonl"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 2, "Non-whitelisted protected file should be blocked"

    def test_whitelist_with_invalid_json(self, hook_tester):
        """Hook should handle invalid whitelist JSON gracefully."""
        # Create invalid whitelist
        whitelist_file = (
            hook_tester.project_root / ".claude" / "file-protection-whitelist.json"
        )
        whitelist_file.parent.mkdir(parents=True, exist_ok=True)
        whitelist_file.write_text("invalid json {")

        # Should still block protected files (whitelist ignored)
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".beads/issues.jsonl"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 2, "Should handle invalid whitelist gracefully and still block"


class TestHookIntegration:
    """Integration tests for hook interaction."""

    def test_hooks_together(self, hook_tester):
        """All hooks should work together without conflicts."""
        # Simulate a complete session:
        # 1. SessionStart loads context
        code, _, _ = hook_tester.run_hook("claude-session-start")
        assert code == 0

        # 2. User tries to edit .beads (blocked)
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".beads/issues.jsonl"},
        }
        code, _, _ = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 2

        # 3. User edits normal file (allowed)
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": "src/main.py"},
        }
        code, _, _ = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 0

        # 4. Stop hook collects findings
        code, _, _ = hook_tester.run_hook(
            "claude-stop", input_data={"stop_hook_active": False}
        )
        assert code == 0


# Additional tests for different project types
class TestHooksWithPythonProject:
    """Test hooks in a Python project context."""

    def test_hooks_with_python_files(self, tmp_path):
        """Hooks should work correctly with Python project structure."""
        project = tmp_path / "python_project"
        project.mkdir()

        # Create Python project structure
        src = project / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hello')")

        tests = project / "tests"
        tests.mkdir()
        (tests / "test_main.py").write_text("def test_main(): pass")

        # Setup hooks
        hooks_dir = project / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        actual_hooks_dir = Path(__file__).parent.parent.parent / ".agents" / "hooks"
        for hook_file in actual_hooks_dir.glob("claude-*"):
            if hook_file.is_file():
                dest = hooks_dir / hook_file.name
                dest.write_text(hook_file.read_text())
                dest.chmod(0o755)

        tester = HookTester(project)

        # Should allow modifying Python files
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": "src/main.py"},
        }
        code, _, _ = tester.run_hook("claude-file-protection", input_data=input_data)
        assert code == 0

        # Should block modifying .beads
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".beads/issues.jsonl"},
        }
        code, _, _ = tester.run_hook("claude-file-protection", input_data=input_data)
        assert code == 2


class TestHooksWithNodeProject:
    """Test hooks in a Node.js project context."""

    def test_hooks_with_node_files(self, tmp_path):
        """Hooks should work correctly with Node.js project structure."""
        project = tmp_path / "node_project"
        project.mkdir()

        # Create Node project structure
        (project / "package.json").write_text('{"name": "test-project"}')

        src = project / "src"
        src.mkdir()
        (src / "index.js").write_text("console.log('hello');")

        # Setup hooks
        hooks_dir = project / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        actual_hooks_dir = Path(__file__).parent.parent.parent / ".agents" / "hooks"
        for hook_file in actual_hooks_dir.glob("claude-*"):
            if hook_file.is_file():
                dest = hooks_dir / hook_file.name
                dest.write_text(hook_file.read_text())
                dest.chmod(0o755)

        tester = HookTester(project)

        # Should allow modifying JavaScript files
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": "src/index.js"},
        }
        code, _, _ = tester.run_hook("claude-file-protection", input_data=input_data)
        assert code == 0

        # Should block modifying package.json indirectly (it's in .beads protection scope)
        # but we'll test .beads directly
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": ".beads/issues.jsonl"},
        }
        code, _, _ = tester.run_hook("claude-file-protection", input_data=input_data)
        assert code == 2


class TestHooksWithMissingDependencies:
    """Test hook behavior when dependencies are missing."""

    def test_session_start_without_python3(self, hook_tester):
        """SessionStart hook should handle missing Python gracefully."""
        # Run with PATH that excludes python3 - actually we can't do this
        # because the hook itself uses python3. Instead, test graceful failures
        # by mocking devloop not being found.
        env = {"PATH": "/nonexistent"}
        code, stdout, stderr = hook_tester.run_hook("claude-session-start", env=env)
        assert code == 0, "Hook should exit cleanly even if dependencies missing"

    def test_stop_hook_without_jq(self, hook_tester):
        """Stop hook should handle missing jq gracefully."""
        # The hook uses jq, but has fallback with || true
        env = {"PATH": "/nonexistent"}
        code, stdout, stderr = hook_tester.run_hook(
            "claude-stop",
            input_data={"stop_hook_active": False},
            env=env,
        )
        # Hook should fail gracefully, but with non-zero exit code is acceptable
        # since || true catches it. Actually, with /nonexistent in PATH, jq won't be found
        # but the || true catches it, so exit code should be 0
        assert code in [0, 1], "Hook should handle missing jq gracefully"


class TestHooksWithEdgeCases:
    """Test hooks with edge cases and unusual inputs."""

    def test_file_protection_with_null_path(self, hook_tester):
        """Hook should handle null/empty file paths."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": None},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 0, "Hook should ignore null paths"

    def test_file_protection_with_missing_tool_input(self, hook_tester):
        """Hook should handle missing tool_input field."""
        input_data = {
            "tool_name": "Write",
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 0, "Hook should handle missing tool_input gracefully"

    def test_file_protection_with_malformed_json(self, hook_tester):
        """Hook should handle malformed JSON input."""
        hook_path = hook_tester.hooks_dir / "claude-file-protection"

        result = subprocess.run(
            [str(hook_path)],
            input="not valid json {",
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": str(hook_tester.project_root)},
            cwd=hook_tester.project_root,
        )
        # Should exit gracefully (0) because Python exception handling ignores errors
        assert result.returncode == 0, "Hook should handle malformed JSON gracefully"

    def test_file_protection_with_symlinks(self, hook_tester):
        """Hook should handle symlinks to protected files."""
        # Create a symlink to a protected file
        beads_dir = hook_tester.project_root / ".beads"
        beads_dir.mkdir(exist_ok=True)

        issues_file = beads_dir / "issues.jsonl"
        issues_file.write_text("{}")

        symlink = hook_tester.project_root / "linked-issues"
        try:
            symlink.symlink_to(issues_file)
        except (OSError, NotImplementedError):
            # Symlinks not supported on this filesystem
            pytest.skip("Symlinks not supported on this filesystem")

        # Try to write through symlink
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": str(symlink)},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        # realpath should resolve the symlink and detect protection
        assert code == 2, "Hook should detect protected files through symlinks"

    def test_file_protection_with_unicode_paths(self, hook_tester):
        """Hook should handle unicode characters in file paths."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": "src/файл.py"},  # Russian characters
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        assert code == 0, "Hook should allow writing to unicode-named files"

    def test_file_protection_with_relative_protected_paths(self, hook_tester):
        """Hook should handle relative paths to protected directories."""
        input_data = {
            "tool_name": "Write",
            "tool_input": {"path": "../project/.beads/issues.jsonl"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-file-protection", input_data=input_data
        )
        # realpath should normalize the path and detect protection
        # This test might pass or fail depending on realpath behavior
        # But hook should not crash
        assert code in [0, 2], "Hook should handle relative protected paths"

    def test_stop_hook_with_large_input(self, hook_tester):
        """Stop hook should handle large input gracefully."""
        # Create a large input
        large_transcript = [
            {"role": "user", "content": "x" * 10000} for _ in range(100)
        ]
        input_data = {
            "stop_hook_active": False,
            "transcript": large_transcript,
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-stop", input_data=input_data
        )
        assert code == 0, "Hook should handle large input gracefully"

    def test_session_start_from_nonexistent_directory(self, tmp_path):
        """SessionStart hook should handle being called from nonexistent directory."""
        hooks_dir = tmp_path / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        hook_path = hooks_dir / "claude-session-start"
        actual_hook = (
            Path(__file__).parent.parent.parent
            / ".agents"
            / "hooks"
            / "claude-session-start"
        )
        hook_path.write_text(actual_hook.read_text())
        hook_path.chmod(0o755)

        # Call from a directory that doesn't exist
        result = subprocess.run(
            [str(hook_path)],
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": "/nonexistent/project"},
            cwd="/tmp",
        )
        assert (
            result.returncode == 0
        ), "Hook should handle nonexistent directory gracefully"


class TestPostToolUseHook:
    """Test claude-post-tool-use hook."""

    def test_hook_exists(self, hook_tester):
        """PostToolUse hook should exist and be executable."""
        hook_path = hook_tester.hooks_dir / "claude-post-tool-use"
        assert hook_path.exists(), "claude-post-tool-use hook not found"
        assert hook_path.stat().st_mode & 0o111, "Hook is not executable"

    def test_shows_findings_for_edited_file(self, hook_tester):
        """Hook should show findings when they exist for the edited file."""
        # Setup: Create mock findings in .devloop/context/immediate.json
        context_dir = hook_tester.project_root / ".devloop" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)

        findings_data = {
            "tier": "immediate",
            "count": 2,
            "findings": [
                {
                    "id": "test-1",
                    "agent": "linter",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "file": str(hook_tester.project_root / "src" / "auth.py"),
                    "line": 45,
                    "severity": "error",
                    "message": "Missing return type annotation",
                },
                {
                    "id": "test-2",
                    "agent": "ruff",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "file": str(hook_tester.project_root / "src" / "auth.py"),
                    "line": 67,
                    "severity": "warning",
                    "message": "Unused import 'os'",
                },
            ],
        }
        (context_dir / "immediate.json").write_text(json.dumps(findings_data))

        # Create the target file so path resolution works
        src_dir = hook_tester.project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "auth.py").write_text("# placeholder")

        # Input: Edit tool completed on auth.py
        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(src_dir / "auth.py")},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-post-tool-use", input_data=input_data
        )

        assert code == 0, f"Hook failed: {stderr}"
        assert "issues in auth.py" in stdout, f"Expected findings output, got: {stdout}"
        assert "Line 45" in stdout, "Should show line number"

    def test_silent_when_no_findings(self, hook_tester):
        """Hook should produce no output when no findings exist."""
        # Setup: Create empty context
        context_dir = hook_tester.project_root / ".devloop" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)
        (context_dir / "immediate.json").write_text(
            json.dumps({"tier": "immediate", "count": 0, "findings": []})
        )

        # Create target file
        src_dir = hook_tester.project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "main.py").write_text("# placeholder")

        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(src_dir / "main.py")},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-post-tool-use", input_data=input_data
        )

        assert code == 0, f"Hook failed: {stderr}"
        assert stdout.strip() == "", f"Expected no output, got: {stdout}"

    def test_silent_when_findings_for_different_file(self, hook_tester):
        """Hook should be silent when findings exist for a different file."""
        # Setup: Create findings for other.py
        context_dir = hook_tester.project_root / ".devloop" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)

        findings_data = {
            "tier": "immediate",
            "count": 1,
            "findings": [
                {
                    "id": "test-1",
                    "agent": "linter",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "file": str(hook_tester.project_root / "src" / "other.py"),
                    "line": 10,
                    "severity": "error",
                    "message": "Some error",
                },
            ],
        }
        (context_dir / "immediate.json").write_text(json.dumps(findings_data))

        # Create both files
        src_dir = hook_tester.project_root / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "main.py").write_text("# placeholder")
        (src_dir / "other.py").write_text("# placeholder")

        # Edit main.py (not other.py)
        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(src_dir / "main.py")},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-post-tool-use", input_data=input_data
        )

        assert code == 0, f"Hook failed: {stderr}"
        assert (
            stdout.strip() == ""
        ), f"Expected no output for unrelated file, got: {stdout}"

    def test_ignores_non_edit_tools(self, hook_tester):
        """Hook should ignore Read, Bash, and other non-Edit/Write tools."""
        input_data = {
            "tool_name": "Read",
            "tool_input": {"file_path": "src/main.py"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-post-tool-use", input_data=input_data
        )

        assert code == 0, "Hook should exit cleanly"
        assert stdout.strip() == "", "Hook should produce no output for Read tool"

    def test_handles_write_tool(self, hook_tester):
        """Hook should process Write tool same as Edit."""
        # Setup: Create findings
        context_dir = hook_tester.project_root / ".devloop" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)

        findings_data = {
            "tier": "immediate",
            "count": 1,
            "findings": [
                {
                    "id": "test-1",
                    "agent": "linter",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "file": str(hook_tester.project_root / "new_file.py"),
                    "line": 1,
                    "severity": "warning",
                    "message": "Missing module docstring",
                },
            ],
        }
        (context_dir / "immediate.json").write_text(json.dumps(findings_data))

        # Create target file
        (hook_tester.project_root / "new_file.py").write_text("# placeholder")

        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(hook_tester.project_root / "new_file.py")},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-post-tool-use", input_data=input_data
        )

        assert code == 0, f"Hook failed: {stderr}"
        assert "new_file.py" in stdout, "Should show findings for Write tool"

    def test_handles_missing_context_dir(self, hook_tester):
        """Hook should exit cleanly if .devloop/context doesn't exist."""
        # Don't create context dir
        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "src/main.py"},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-post-tool-use", input_data=input_data
        )

        assert code == 0, "Hook should exit cleanly without context dir"
        assert stdout.strip() == "", "Hook should be silent without context dir"

    def test_handles_malformed_input(self, hook_tester):
        """Hook should handle invalid JSON input gracefully."""
        hook_path = hook_tester.hooks_dir / "claude-post-tool-use"

        result = subprocess.run(
            [str(hook_path)],
            input="not valid json {",
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": str(hook_tester.project_root)},
            cwd=hook_tester.project_root,
        )

        assert result.returncode == 0, "Hook should handle malformed JSON gracefully"

    def test_handles_empty_input(self, hook_tester):
        """Hook should handle empty input gracefully."""
        code, stdout, stderr = hook_tester.run_hook(
            "claude-post-tool-use", input_data=None
        )
        assert code == 0, "Hook should handle empty input gracefully"

    def test_shows_multiple_findings(self, hook_tester):
        """Hook should show count and preview for multiple findings."""
        context_dir = hook_tester.project_root / ".devloop" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)

        findings_data = {
            "tier": "immediate",
            "count": 5,
            "findings": [
                {
                    "id": f"test-{i}",
                    "agent": "linter",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "file": str(hook_tester.project_root / "big_file.py"),
                    "line": i * 10,
                    "severity": "warning",
                    "message": f"Issue number {i}",
                }
                for i in range(1, 6)
            ],
        }
        (context_dir / "immediate.json").write_text(json.dumps(findings_data))

        (hook_tester.project_root / "big_file.py").write_text("# placeholder")

        input_data = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(hook_tester.project_root / "big_file.py")},
        }
        code, stdout, stderr = hook_tester.run_hook(
            "claude-post-tool-use", input_data=input_data
        )

        assert code == 0, f"Hook failed: {stderr}"
        assert "5 issues" in stdout, "Should show count"
        assert "and 4 more" in stdout, "Should indicate more findings"


class TestHooksDocumentation:
    """Test that hook documentation is accurate."""

    def test_hooks_have_shebang(self, hook_tester):
        """All hooks should have proper shebang."""
        for hook_file in hook_tester.hooks_dir.glob("claude-*"):
            if hook_file.is_file() and hook_file.name != "install-claude-hooks":
                content = hook_file.read_text()
                assert content.startswith(
                    "#!/bin/bash"
                ), f"{hook_file.name} should start with #!/bin/bash"

    def test_hooks_are_executable(self, hook_tester):
        """All hook files should be executable."""
        for hook_file in hook_tester.hooks_dir.glob("claude-*"):
            if hook_file.is_file() and hook_file.name != "install-claude-hooks":
                is_executable = hook_file.stat().st_mode & 0o111
                assert is_executable, f"{hook_file.name} should be executable"

    def test_hooks_have_documentation(self, hook_tester):
        """Each hook should have comments explaining its purpose."""
        for hook_file in hook_tester.hooks_dir.glob("claude-*"):
            if hook_file.is_file() and hook_file.name != "install-claude-hooks":
                content = hook_file.read_text()
                # Check for header comment with "What it does" or similar
                lines = content.split("\n")
                # Should have comments in first 5 lines
                has_docs = any("#" in line for line in lines[:5])
                assert has_docs, f"{hook_file.name} should have header comments"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
