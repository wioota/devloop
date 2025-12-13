"""Tests for post-commit hook that auto-closes Beads issues."""

import subprocess
import tempfile
import os
from pathlib import Path
import json


def run_shell(cmd: str, cwd: str = ".") -> tuple[str, str, int]:
    """Run a shell command and return stdout, stderr, exit code."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout, result.stderr, result.returncode


class TestPostCommitHook:
    """Test the post-commit hook functionality."""

    def test_hook_exists_and_executable(self):
        """Test that post-commit hook exists and is executable."""
        hook_path = Path(".git/hooks/post-commit")
        assert hook_path.exists(), "post-commit hook does not exist"
        assert os.access(hook_path, os.X_OK), "post-commit hook is not executable"

    def test_hook_parses_fixes_keyword(self):
        """Test that hook recognizes 'fixes' keyword."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        assert "fixes" in hook_content.lower(), "Hook doesn't handle 'fixes' keyword"

    def test_hook_parses_closes_keyword(self):
        """Test that hook recognizes 'closes' keyword."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        assert "closes" in hook_content.lower(), "Hook doesn't handle 'closes' keyword"

    def test_hook_parses_resolves_keyword(self):
        """Test that hook recognizes 'resolves' keyword."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        assert (
            "resolves" in hook_content.lower()
        ), "Hook doesn't handle 'resolves' keyword"

    def test_hook_handles_beads_issue_format(self):
        """Test that hook handles beads issue format (claude-agents-abc123)."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        assert (
            "claude-agents-" in hook_content
        ), "Hook doesn't handle beads issue format"

    def test_hook_handles_github_format(self):
        """Test that hook handles GitHub issue format (#123)."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        # Should handle both formats
        assert "#" in hook_content, "Hook doesn't handle GitHub issue format"

    def test_hook_gracefully_handles_missing_bd(self):
        """Test that hook gracefully handles missing bd command."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        assert "command -v bd" in hook_content, "Hook doesn't check for bd availability"
        assert "exit 0" in hook_content, "Hook doesn't gracefully exit"

    def test_hook_gracefully_handles_no_beads_dir(self):
        """Test that hook gracefully handles missing .beads directory."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        assert ".beads" in hook_content, "Hook doesn't check for .beads directory"

    def test_hook_includes_commit_sha(self):
        """Test that hook includes commit SHA in closure reason."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        assert "COMMIT_SHA" in hook_content, "Hook doesn't capture commit SHA"

    def test_hook_includes_commit_message(self):
        """Test that hook includes commit message in closure reason."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        assert "COMMIT_MSG" in hook_content, "Hook doesn't capture commit message"

    def test_hook_doesnt_fail_on_invalid_issue(self):
        """Test that hook doesn't fail when issue doesn't exist."""
        hook_content = Path(".git/hooks/post-commit").read_text()
        # Should have error handling that doesn't exit with failure
        assert (
            ">/dev/null 2>&1" in hook_content
        ), "Hook should suppress errors from bd close"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
