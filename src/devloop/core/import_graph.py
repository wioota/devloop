"""Python import graph analysis for affected test discovery.

Builds a reverse dependency graph from Python source files using AST parsing.
When a file changes, walks the graph to find all test files that transitively
depend on it.
"""

from __future__ import annotations

import ast
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class ImportGraph:
    """Reverse dependency graph for Python imports.

    Builds a mapping of file → [files that import it] by parsing import
    statements with ast. Supports incremental updates when files change.

    Args:
        project_root: Root directory of the project.
        src_dirs: List of source directories to scan (e.g. [project/src]).
    """

    def __init__(self, project_root: Path, src_dirs: list[Path] | None = None):
        self.project_root = project_root.resolve()
        self.src_dirs = [d.resolve() for d in (src_dirs or [])]

        # Forward map: file → set of resolved file paths it imports
        self._imports: dict[Path, set[Path]] = {}

        # Reverse map: file → set of files that import it
        self._importers: dict[Path, set[Path]] = defaultdict(set)

    def build(self) -> None:
        """Scan all .py files and build the full import graph."""
        py_files = self._discover_py_files()

        for py_file in py_files:
            self._index_file(py_file)

    def update_file(self, path: Path) -> None:
        """Re-parse a single file and update its edges in the graph."""
        resolved = path.resolve()

        # Remove old edges for this file
        self._remove_edges(resolved)

        # Re-index if file still exists
        if resolved.exists():
            self._index_file(resolved)

    def remove_file(self, path: Path) -> None:
        """Remove a file and all its edges from the graph."""
        resolved = path.resolve()
        self._remove_edges(resolved)
        self._imports.pop(resolved, None)
        self._importers.pop(resolved, None)

    def get_affected_tests(self, changed_file: Path) -> list[Path]:
        """Find all test files that transitively depend on changed_file.

        Does a BFS on the reverse import graph starting from changed_file,
        collecting any reachable files that match test naming conventions.
        """
        resolved = changed_file.resolve()
        visited: set[Path] = set()
        queue = [resolved]
        test_files: list[Path] = []

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if current != resolved and self._is_test_file(current):
                test_files.append(current)

            # Walk reverse edges: who imports this file?
            for importer in self._importers.get(current, set()):
                if importer not in visited:
                    queue.append(importer)

        return sorted(test_files)

    def _discover_py_files(self) -> list[Path]:
        """Find all .py files in the project."""
        py_files: list[Path] = []
        scan_dirs = self.src_dirs + [self.project_root / "tests"]

        for scan_dir in scan_dirs:
            if scan_dir.exists():
                py_files.extend(scan_dir.rglob("*.py"))

        # Also scan project root for top-level .py files
        py_files.extend(self.project_root.glob("*.py"))

        return [f.resolve() for f in py_files]

    def _index_file(self, path: Path) -> None:
        """Parse a file's imports and add edges to the graph."""
        resolved = path.resolve()
        imports = self._parse_imports(resolved)
        resolved_imports: set[Path] = set()

        for module_name, is_relative, level in imports:
            target = self._resolve_import(module_name, resolved, is_relative, level)
            if target and target.exists():
                target = target.resolve()
                resolved_imports.add(target)
                self._importers[target].add(resolved)

        self._imports[resolved] = resolved_imports

    def _remove_edges(self, path: Path) -> None:
        """Remove all forward edges from a file (its imports)."""
        old_imports = self._imports.pop(path, set())
        for target in old_imports:
            self._importers[target].discard(path)

    def _parse_imports(self, path: Path) -> list[tuple[str, bool, int]]:
        """Parse import statements from a Python file using AST.

        Returns list of (module_name, is_relative, level) tuples.
        """
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, OSError) as e:
            logger.debug(f"Skipping {path}: {e}")
            return []

        imports: list[tuple[str, bool, int]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, False, 0))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                level = node.level or 0
                is_relative = level > 0
                imports.append((module, is_relative, level))

        return imports

    def _resolve_import(
        self, module_name: str, importing_file: Path, is_relative: bool, level: int
    ) -> Path | None:
        """Resolve a module name to a file path.

        Uses path math against project root and src dirs. Does not use importlib.
        """
        if is_relative:
            return self._resolve_relative_import(module_name, importing_file, level)

        # Absolute import: try each src dir, then project root
        parts = module_name.split(".") if module_name else []
        if not parts:
            return None

        search_dirs = self.src_dirs + [self.project_root]

        for base in search_dirs:
            result = self._find_module_file(base, parts)
            if result:
                return result

        return None

    def _resolve_relative_import(
        self, module_name: str, importing_file: Path, level: int
    ) -> Path | None:
        """Resolve a relative import (from .foo import bar)."""
        # Start from the importing file's directory
        base = importing_file.parent

        # Go up 'level - 1' directories (level=1 means current package)
        for _ in range(level - 1):
            base = base.parent

        parts = module_name.split(".") if module_name else []
        if not parts:
            # from . import something → refers to __init__.py
            init = base / "__init__.py"
            return init if init.exists() else None

        return self._find_module_file(base, parts)

    def _find_module_file(self, base: Path, parts: list[str]) -> Path | None:
        """Find a module file given a base directory and dotted name parts.

        Checks for:
        - base/parts[0]/parts[1]/.../parts[-1].py  (module file)
        - base/parts[0]/parts[1]/.../parts[-1]/__init__.py  (package)
        """
        target = base
        for part in parts:
            target = target / part

        # Check module file
        module_file = target.with_suffix(".py")
        if module_file.exists():
            return module_file

        # Check package __init__.py
        init_file = target / "__init__.py"
        if init_file.exists():
            return init_file

        return None

    @staticmethod
    def _is_test_file(path: Path) -> bool:
        """Check if a file is a test file by naming convention."""
        name = path.name
        return name.startswith("test_") or name.endswith("_test.py")
