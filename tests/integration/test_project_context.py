"""Tests for project context detection."""

import tempfile
from pathlib import Path
import pytest

from devloop.core.project_context import ProjectContext


class TestProjectContext:
    """Test the ProjectContext class."""

    def test_detects_devloop_repository_via_pyproject_toml(self):
        """Test detection via pyproject.toml with name='devloop'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create pyproject.toml with devloop name
            pyproject = project_root / "pyproject.toml"
            pyproject.write_text("""
[tool.poetry]
name = "devloop"
version = "0.1.0"
""")

            context = ProjectContext(project_root)
            assert context.is_devloop_repository() is True

    def test_detects_devloop_repository_via_git_remote(self):
        """Test detection via git remote URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create git config with devloop remote
            git_dir = project_root / ".git"
            git_dir.mkdir()
            git_config = git_dir / "config"
            git_config.write_text("""
[remote "origin"]
    url = https://github.com/wioota/devloop.git
    fetch = +refs/heads/*:refs/remotes/origin/*
""")

            context = ProjectContext(project_root)
            assert context.is_devloop_repository() is True

    def test_detects_devloop_repository_via_marker_file(self):
        """Test detection via .devloop-repository-marker file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create marker file
            marker = project_root / ".devloop-repository-marker"
            marker.write_text("This is the devloop source repository")

            context = ProjectContext(project_root)
            assert context.is_devloop_repository() is True

    def test_not_devloop_repository(self):
        """Test that user projects are not detected as devloop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create a user project pyproject.toml
            pyproject = project_root / "pyproject.toml"
            pyproject.write_text("""
[tool.poetry]
name = "my-app"
version = "1.0.0"
""")

            context = ProjectContext(project_root)
            assert context.is_devloop_repository() is False

    def test_get_test_root_for_devloop_repository(self):
        """Test that devloop repository uses tests/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create marker to identify as devloop
            marker = project_root / ".devloop-repository-marker"
            marker.write_text("devloop")

            # Create tests directory
            tests_dir = project_root / "tests"
            tests_dir.mkdir()

            context = ProjectContext(project_root)
            test_root = context.get_test_root()

            assert test_root == tests_dir

    def test_get_test_root_for_user_project_with_tests_dir(self):
        """Test that user projects use tests/ if available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create user project
            pyproject = project_root / "pyproject.toml"
            pyproject.write_text('[tool.poetry]\nname = "user-app"')

            # Create tests directory
            tests_dir = project_root / "tests"
            tests_dir.mkdir()

            context = ProjectContext(project_root)
            test_root = context.get_test_root()

            assert test_root == tests_dir

    def test_get_test_root_for_user_project_with_test_dir(self):
        """Test that user projects use test/ (singular) if available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create test directory (singular)
            test_dir = project_root / "test"
            test_dir.mkdir()

            context = ProjectContext(project_root)
            test_root = context.get_test_root()

            assert test_root == test_dir

    def test_get_test_root_for_user_project_with_spec_dir(self):
        """Test that user projects use spec/ if available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create spec directory
            spec_dir = project_root / "spec"
            spec_dir.mkdir()

            context = ProjectContext(project_root)
            test_root = context.get_test_root()

            assert test_root == spec_dir

    def test_get_test_root_defaults_to_project_root(self):
        """Test that test root defaults to project root if no test dir found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            context = ProjectContext(project_root)
            test_root = context.get_test_root()

            assert test_root == project_root

    def test_get_exclude_patterns_for_devloop_repository(self):
        """Test that devloop repository has no exclusions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create marker to identify as devloop
            marker = project_root / ".devloop-repository-marker"
            marker.write_text("devloop")

            context = ProjectContext(project_root)
            patterns = context.get_exclude_patterns()

            assert patterns == []

    def test_get_exclude_patterns_for_user_project(self):
        """Test that user projects exclude site-packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create user project
            pyproject = project_root / "pyproject.toml"
            pyproject.write_text('[tool.poetry]\nname = "user-app"')

            context = ProjectContext(project_root)
            patterns = context.get_exclude_patterns()

            # Should exclude devloop tests from site-packages
            assert "**/site-packages/devloop/tests/**" in patterns
            assert "**/.venv/**/devloop/tests/**" in patterns
            assert "**/venv/**/devloop/tests/**" in patterns

    def test_get_project_type_python(self):
        """Test detection of Python projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create pyproject.toml
            pyproject = project_root / "pyproject.toml"
            pyproject.write_text('[tool.poetry]\nname = "app"')

            context = ProjectContext(project_root)
            assert context.get_project_type() == "python"

    def test_get_project_type_python_setup_py(self):
        """Test detection of Python projects via setup.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create setup.py
            setup_py = project_root / "setup.py"
            setup_py.write_text("from setuptools import setup\nsetup()")

            context = ProjectContext(project_root)
            assert context.get_project_type() == "python"

    def test_get_project_type_javascript(self):
        """Test detection of JavaScript projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create package.json
            package_json = project_root / "package.json"
            package_json.write_text('{"name": "app"}')

            context = ProjectContext(project_root)
            assert context.get_project_type() == "javascript"

    def test_get_project_type_rust(self):
        """Test detection of Rust projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create Cargo.toml
            cargo_toml = project_root / "Cargo.toml"
            cargo_toml.write_text('[package]\nname = "app"')

            context = ProjectContext(project_root)
            assert context.get_project_type() == "rust"

    def test_get_project_type_go(self):
        """Test detection of Go projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create go.mod
            go_mod = project_root / "go.mod"
            go_mod.write_text("module example.com/app\n\ngo 1.21")

            context = ProjectContext(project_root)
            assert context.get_project_type() == "go"

    def test_get_project_type_unknown(self):
        """Test that unknown projects return 'unknown'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            context = ProjectContext(project_root)
            assert context.get_project_type() == "unknown"

    def test_caching_is_devloop_repository(self):
        """Test that is_devloop_repository() results are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create marker file
            marker = project_root / ".devloop-repository-marker"
            marker.write_text("devloop")

            context = ProjectContext(project_root)

            # First call
            result1 = context.is_devloop_repository()
            assert result1 is True

            # Remove marker file
            marker.unlink()

            # Second call should still return True (cached)
            result2 = context.is_devloop_repository()
            assert result2 is True

    def test_caching_project_type(self):
        """Test that get_project_type() results are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create pyproject.toml
            pyproject = project_root / "pyproject.toml"
            pyproject.write_text('[tool.poetry]\nname = "app"')

            context = ProjectContext(project_root)

            # First call
            type1 = context.get_project_type()
            assert type1 == "python"

            # Remove pyproject.toml
            pyproject.unlink()

            # Second call should still return "python" (cached)
            type2 = context.get_project_type()
            assert type2 == "python"

    def test_clear_cache(self):
        """Test that clear_cache() invalidates cached results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create marker file
            marker = project_root / ".devloop-repository-marker"
            marker.write_text("devloop")

            context = ProjectContext(project_root)

            # First call (caches result)
            result1 = context.is_devloop_repository()
            assert result1 is True

            # Remove marker and clear cache
            marker.unlink()
            context.clear_cache()

            # Second call should re-detect
            result2 = context.is_devloop_repository()
            assert result2 is False

    def test_defaults_to_current_directory(self):
        """Test that ProjectContext defaults to current directory."""
        context = ProjectContext()
        assert context.project_root == Path.cwd()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
