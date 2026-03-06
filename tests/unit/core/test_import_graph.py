"""Tests for Python import graph analysis."""

import pytest
from pathlib import Path

from devloop.core.import_graph import ImportGraph


@pytest.fixture
def project(tmp_path):
    """Create a minimal Python project structure."""
    src = tmp_path / "src"
    src.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    return tmp_path


def _write(path: Path, content: str) -> Path:
    """Helper to write a Python file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestBuildGraph:
    """Tests for full graph building at startup."""

    def test_empty_project(self, project):
        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()
        assert graph.get_affected_tests(project / "src" / "foo.py") == []

    def test_single_direct_import(self, project):
        _write(project / "src" / "utils.py", "def helper(): pass")
        _write(
            project / "tests" / "test_utils.py",
            "from src.utils import helper\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        affected = graph.get_affected_tests(project / "src" / "utils.py")
        assert project / "tests" / "test_utils.py" in affected

    def test_transitive_dependency(self, project):
        """Change utils.py → service.py imports utils → test_service.py imports service."""
        _write(project / "src" / "utils.py", "def helper(): pass")
        _write(
            project / "src" / "service.py",
            "from src.utils import helper\n",
        )
        _write(
            project / "tests" / "test_service.py",
            "from src.service import helper\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        affected = graph.get_affected_tests(project / "src" / "utils.py")
        assert project / "tests" / "test_service.py" in affected

    def test_no_affected_tests(self, project):
        """File with no dependents returns empty list."""
        _write(project / "src" / "orphan.py", "x = 1")
        _write(project / "tests" / "test_other.py", "def test_something(): pass")

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        assert graph.get_affected_tests(project / "src" / "orphan.py") == []

    def test_multiple_test_files(self, project):
        """One source file imported by multiple test files."""
        _write(project / "src" / "utils.py", "def helper(): pass")
        _write(
            project / "tests" / "test_a.py",
            "from src.utils import helper\n",
        )
        _write(
            project / "tests" / "test_b.py",
            "from src.utils import helper\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        affected = graph.get_affected_tests(project / "src" / "utils.py")
        assert len(affected) == 2
        assert project / "tests" / "test_a.py" in affected
        assert project / "tests" / "test_b.py" in affected


class TestCircularImports:
    def test_circular_does_not_loop(self, project):
        """Circular imports must not cause infinite recursion."""
        _write(project / "src" / "a.py", "from src.b import y\nx = 1")
        _write(project / "src" / "b.py", "from src.a import x\ny = 2")
        _write(
            project / "tests" / "test_a.py",
            "from src.a import x\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        affected = graph.get_affected_tests(project / "src" / "b.py")
        assert project / "tests" / "test_a.py" in affected


class TestIncrementalUpdate:
    def test_update_adds_new_dependency(self, project):
        """Adding an import to a file updates the graph."""
        _write(project / "src" / "utils.py", "def helper(): pass")
        _write(project / "src" / "service.py", "x = 1")
        _write(
            project / "tests" / "test_service.py",
            "from src.service import x\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        # Initially utils.py has no test dependents
        assert graph.get_affected_tests(project / "src" / "utils.py") == []

        # Now service.py starts importing utils
        _write(
            project / "src" / "service.py",
            "from src.utils import helper\nx = 1\n",
        )
        graph.update_file(project / "src" / "service.py")

        # Now utils.py should be linked to test_service.py transitively
        affected = graph.get_affected_tests(project / "src" / "utils.py")
        assert project / "tests" / "test_service.py" in affected

    def test_update_removes_dependency(self, project):
        """Removing an import from a file updates the graph."""
        _write(project / "src" / "utils.py", "def helper(): pass")
        _write(
            project / "src" / "service.py",
            "from src.utils import helper\n",
        )
        _write(
            project / "tests" / "test_service.py",
            "from src.service import helper\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        # utils.py affects test_service.py transitively
        assert project / "tests" / "test_service.py" in graph.get_affected_tests(
            project / "src" / "utils.py"
        )

        # Remove the import
        _write(project / "src" / "service.py", "x = 1\n")
        graph.update_file(project / "src" / "service.py")

        # utils.py should no longer affect test_service.py
        assert graph.get_affected_tests(project / "src" / "utils.py") == []


class TestRemoveFile:
    def test_remove_cleans_edges(self, project):
        _write(project / "src" / "utils.py", "def helper(): pass")
        _write(
            project / "tests" / "test_utils.py",
            "from src.utils import helper\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        assert len(graph.get_affected_tests(project / "src" / "utils.py")) == 1

        graph.remove_file(project / "tests" / "test_utils.py")
        assert graph.get_affected_tests(project / "src" / "utils.py") == []


class TestPackageImports:
    def test_init_package_resolution(self, project):
        """Importing a package resolves to __init__.py."""
        pkg = project / "src" / "mypkg"
        _write(pkg / "__init__.py", "from .core import thing\n")
        _write(pkg / "core.py", "thing = 1")
        _write(
            project / "tests" / "test_mypkg.py",
            "from src.mypkg import thing\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        affected = graph.get_affected_tests(pkg / "__init__.py")
        assert project / "tests" / "test_mypkg.py" in affected

    def test_relative_imports(self, project):
        """Relative imports within a package are tracked."""
        pkg = project / "src" / "mypkg"
        _write(pkg / "__init__.py", "")
        _write(pkg / "utils.py", "x = 1")
        _write(pkg / "service.py", "from .utils import x\n")
        _write(
            project / "tests" / "test_service.py",
            "from src.mypkg.service import x\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        affected = graph.get_affected_tests(pkg / "utils.py")
        assert project / "tests" / "test_service.py" in affected


class TestImportStatements:
    """Test various import statement forms."""

    def test_import_statement(self, project):
        """Plain 'import foo' is tracked."""
        _write(project / "src" / "utils.py", "x = 1")
        _write(
            project / "tests" / "test_utils.py",
            "import src.utils\n",
        )

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()

        affected = graph.get_affected_tests(project / "src" / "utils.py")
        assert project / "tests" / "test_utils.py" in affected

    def test_syntax_error_skipped(self, project):
        """Files with syntax errors are skipped without crashing."""
        _write(project / "src" / "broken.py", "def f(\n")  # syntax error
        _write(project / "src" / "good.py", "x = 1")

        graph = ImportGraph(project, src_dirs=[project / "src"])
        graph.build()  # should not raise

        assert graph.get_affected_tests(project / "src" / "good.py") == []
