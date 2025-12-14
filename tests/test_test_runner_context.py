"""Tests for TestRunnerAgent project context integration."""

import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock

from devloop.agents.test_runner import TestRunnerAgent


class TestTestRunnerAgentContext:
    """Test TestRunnerAgent with project context."""

    def test_initializes_project_context(self):
        """Test that TestRunnerAgent initializes ProjectContext."""
        event_bus = MagicMock()
        agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus)

        assert hasattr(agent, "project_context")
        assert agent.project_context is not None

    def test_is_excluded_with_site_packages(self):
        """Test that site-packages paths are excluded."""
        event_bus = MagicMock()
        agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus)

        # Test path that should be excluded
        site_packages_path = Path(
            "/home/user/.venv/lib/python3.12/site-packages/devloop/tests/test_foo.py"
        )

        assert agent._is_excluded(site_packages_path) is True

    def test_is_excluded_with_venv(self):
        """Test that .venv paths are excluded."""
        event_bus = MagicMock()
        agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus)

        venv_path = Path("/home/user/project/.venv/devloop/tests/test_foo.py")

        assert agent._is_excluded(venv_path) is True

    def test_is_not_excluded_normal_path(self):
        """Test that normal test paths are not excluded."""
        event_bus = MagicMock()
        agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus)

        normal_path = Path("/home/user/project/tests/test_foo.py")

        assert agent._is_excluded(normal_path) is False

    def test_matches_pattern_simple(self):
        """Test simple pattern matching."""
        event_bus = MagicMock()
        agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus)

        assert agent._matches_pattern("/foo/bar.py", "*.py") is True
        assert agent._matches_pattern("/foo/bar.js", "*.py") is False

    def test_matches_pattern_recursive(self):
        """Test recursive ** pattern matching."""
        event_bus = MagicMock()
        agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus)

        pattern = "**/site-packages/**"

        assert (
            agent._matches_pattern(
                "/home/user/.venv/lib/python3.12/site-packages/foo/bar.py", pattern
            )
            is True
        )
        assert (
            agent._matches_pattern("/home/user/project/tests/test_foo.py", pattern)
            is False
        )

    def test_find_related_tests_filters_excluded(self):
        """Test that _find_related_tests filters excluded paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create source file
            src_file = project_root / "foo.py"
            src_file.write_text("# source")

            # Create test in normal location (should be found)
            tests_dir = project_root / "tests"
            tests_dir.mkdir()
            normal_test = tests_dir / "test_foo.py"
            normal_test.write_text("# test")

            # Create test in site-packages (should be excluded)
            site_packages_dir = (
                project_root / ".venv" / "lib" / "python3.12" / "site-packages"
            )
            site_packages_dir.mkdir(parents=True)
            excluded_test = site_packages_dir / "test_foo.py"
            excluded_test.write_text("# excluded test")

            # Create agent with project root
            event_bus = MagicMock()
            agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus)
            # Override project context to use temp dir
            from devloop.core.project_context import ProjectContext

            agent.project_context = ProjectContext(project_root)

            # Find related tests
            related = agent._find_related_tests(src_file)

            # Should find normal test but not excluded test
            assert normal_test in related
            assert excluded_test not in related

    def test_custom_test_paths_config(self):
        """Test that custom testPaths configuration works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create source file
            src_file = project_root / "foo.py"
            src_file.write_text("# source")

            # Create custom test directory
            custom_test_dir = project_root / "my_tests"
            custom_test_dir.mkdir()
            custom_test = custom_test_dir / "test_foo.py"
            custom_test.write_text("# test")

            # Create agent with custom test paths
            event_bus = MagicMock()
            config = {"testPaths": [str(custom_test_dir)]}
            agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus, config)

            # Find related tests
            related = agent._find_related_tests(src_file)

            # Should find test in custom directory
            assert custom_test in related

    def test_custom_exclude_patterns(self):
        """Test that custom excludePaths configuration works."""
        event_bus = MagicMock()
        config = {"excludePaths": ["**/custom-exclude/**"]}
        agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus, config)

        excluded_path = Path("/home/user/project/custom-exclude/test_foo.py")

        assert agent._is_excluded(excluded_path) is True

    def test_respect_site_packages_disabled(self):
        """Test that respectSitePackages: false disables site-packages exclusion."""
        event_bus = MagicMock()
        config = {
            "projectContext": {"respectSitePackages": False},
            "excludePaths": [],  # No other exclusions
        }
        agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus, config)

        # Verify config was set correctly
        assert agent.config.respect_site_packages is False
        assert agent.config.exclude_paths == []

    def test_backward_compatibility_no_context_config(self):
        """Test that agents work without projectContext config."""
        event_bus = MagicMock()
        # Old-style config without projectContext
        config = {"runOnSave": True, "relatedTestsOnly": True}

        agent = TestRunnerAgent("test-runner", ["file:modified"], event_bus, config)

        # Should still work with defaults
        assert agent.project_context is not None
        assert agent.config.auto_detect_context is True
        assert agent.config.respect_site_packages is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
