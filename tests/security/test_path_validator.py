"""Tests for path validation and symlink protection."""

import pytest
from devloop.security.path_validator import (
    PathTraversalError,
    PathValidationError,
    PathValidator,
    SymlinkError,
    is_safe_path,
    safe_path_join,
    validate_safe_patterns,
)


class TestPathValidator:
    """Test PathValidator class."""

    def test_initialize_with_valid_root(self, tmp_path):
        """Initialize with valid project root."""
        validator = PathValidator(tmp_path)

        assert validator.project_root == tmp_path.resolve()
        assert validator.allow_symlinks is False

    def test_initialize_with_nonexistent_root(self, tmp_path):
        """Raise error for nonexistent project root."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(PathValidationError, match="does not exist"):
            PathValidator(nonexistent)

    def test_initialize_with_file_as_root(self, tmp_path):
        """Raise error when root is a file, not directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("data")

        with pytest.raises(PathValidationError, match="not a directory"):
            PathValidator(file_path)

    def test_resolve_path_simple(self, tmp_path):
        """Resolve simple path."""
        validator = PathValidator(tmp_path)

        file_path = tmp_path / "file.txt"
        file_path.write_text("data")

        resolved = validator.resolve_path(file_path)

        assert resolved == file_path.resolve()
        assert resolved.is_absolute()

    def test_resolve_path_with_relative_components(self, tmp_path):
        """Resolve path with .. and . components."""
        validator = PathValidator(tmp_path)

        # Create nested directory
        nested = tmp_path / "subdir" / "nested"
        nested.mkdir(parents=True)

        # Path with relative components
        relative_path = nested / ".." / "." / "nested"

        resolved = validator.resolve_path(relative_path)

        assert resolved == nested.resolve()

    def test_resolve_path_rejects_symlink(self, tmp_path):
        """Reject symlinks when not allowed."""
        validator = PathValidator(tmp_path, allow_symlinks=False)

        # Create target and symlink
        target = tmp_path / "target.txt"
        target.write_text("data")

        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target)

        with pytest.raises(SymlinkError, match="Symlinks not allowed"):
            validator.resolve_path(symlink)

    def test_resolve_path_allows_symlink_if_enabled(self, tmp_path):
        """Allow symlinks when explicitly enabled."""
        validator = PathValidator(tmp_path, allow_symlinks=True)

        # Create target and symlink
        target = tmp_path / "target.txt"
        target.write_text("data")

        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target)

        resolved = validator.resolve_path(symlink)

        # Should resolve to target
        assert resolved == target.resolve()

    def test_is_within_project_valid(self, tmp_path):
        """Check path is within project."""
        validator = PathValidator(tmp_path)

        file_path = tmp_path / "subdir" / "file.txt"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("data")

        assert validator.is_within_project(file_path) is True

    def test_is_within_project_outside(self, tmp_path):
        """Detect path outside project."""
        project = tmp_path / "project"
        project.mkdir()

        validator = PathValidator(project)

        outside = tmp_path / "outside.txt"
        outside.write_text("data")

        assert validator.is_within_project(outside) is False

    def test_validate_success(self, tmp_path):
        """Successfully validate safe path."""
        validator = PathValidator(tmp_path)

        file_path = tmp_path / "safe" / "file.txt"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("data")

        validated = validator.validate(file_path)

        assert validated == file_path.resolve()

    def test_validate_path_traversal_with_dotdot(self, tmp_path):
        """Detect path traversal with ..."""
        project = tmp_path / "project"
        project.mkdir()

        validator = PathValidator(project)

        # Try to escape with ../
        malicious = project / ".." / ".." / "etc" / "passwd"

        with pytest.raises(PathTraversalError, match="outside project directory"):
            validator.validate(malicious)

    def test_validate_path_traversal_with_symlink(self, tmp_path):
        """Detect path traversal via symlink."""
        project = tmp_path / "project"
        project.mkdir()

        validator = PathValidator(project, allow_symlinks=False)

        # Create symlink pointing outside project
        outside = tmp_path / "outside"
        outside.mkdir()

        symlink = project / "escape"
        symlink.symlink_to(outside)

        with pytest.raises(SymlinkError, match="Symlinks not allowed"):
            validator.validate(symlink)

    def test_validate_blocked_pattern(self, tmp_path):
        """Block paths matching blocked patterns."""
        validator = PathValidator(
            tmp_path,
            blocked_patterns=["*.exe", "*.sh", "*.dll"],
        )

        malicious = tmp_path / "malware.exe"
        malicious.write_bytes(b"MZ...")  # PE header

        with pytest.raises(PathValidationError, match="blocked pattern"):
            validator.validate(malicious)

    def test_validate_multiple_success(self, tmp_path):
        """Validate multiple paths."""
        validator = PathValidator(tmp_path)

        paths = [
            tmp_path / "file1.txt",
            tmp_path / "file2.txt",
            tmp_path / "subdir" / "file3.txt",
        ]

        for p in paths:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("data")

        validated = validator.validate_multiple(paths)

        assert len(validated) == 3
        assert all(p.is_absolute() for p in validated)

    def test_validate_multiple_fails_on_invalid(self, tmp_path):
        """Fail validation if any path is invalid."""
        project = tmp_path / "project"
        project.mkdir()

        validator = PathValidator(project)

        paths = [
            project / "safe.txt",
            tmp_path / "outside.txt",  # Outside project!
        ]

        for p in paths:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("data")

        with pytest.raises(PathValidationError):
            validator.validate_multiple(paths)

    def test_match_pattern_simple(self, tmp_path):
        """Match path against simple pattern."""
        validator = PathValidator(tmp_path)

        python_file = tmp_path / "test.py"
        python_file.write_text("# code")

        assert validator.match_pattern(python_file, "*.py") is True
        assert validator.match_pattern(python_file, "*.txt") is False

    def test_match_pattern_glob(self, tmp_path):
        """Match path against glob pattern."""
        validator = PathValidator(tmp_path)

        nested = tmp_path / "src" / "module" / "file.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("# code")

        assert validator.match_pattern(nested, "**/*.py") is True
        assert validator.match_pattern(nested, "src/**/*.py") is True
        assert validator.match_pattern(nested, "tests/**/*.py") is False

    def test_filter_paths_include(self, tmp_path):
        """Filter paths by include patterns."""
        validator = PathValidator(tmp_path)

        files = [
            tmp_path / "file.py",
            tmp_path / "file.txt",
            tmp_path / "file.js",
        ]

        for f in files:
            f.write_text("data")

        filtered = validator.filter_paths(files, include_patterns=["*.py", "*.js"])

        assert len(filtered) == 2
        assert all(f.suffix in [".py", ".js"] for f in filtered)

    def test_filter_paths_exclude(self, tmp_path):
        """Filter paths by exclude patterns."""
        validator = PathValidator(tmp_path)

        files = [
            tmp_path / "test.py",
            tmp_path / "__pycache__" / "cache.pyc",
            tmp_path / ".git" / "config",
        ]

        for f in files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("data")

        filtered = validator.filter_paths(files, exclude_patterns=["*.pyc", ".git/**"])

        # Should exclude .pyc and .git files
        assert len(filtered) == 1
        assert filtered[0].name == "test.py"

    def test_filter_paths_skips_invalid(self, tmp_path):
        """Skip invalid paths without raising error."""
        project = tmp_path / "project"
        project.mkdir()

        validator = PathValidator(project)

        paths = [
            project / "valid.txt",
            tmp_path / "outside.txt",  # Invalid, will be skipped
        ]

        for p in paths:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("data")

        filtered = validator.filter_paths(paths)

        # Only valid path should be included
        assert len(filtered) == 1
        assert filtered[0].name == "valid.txt"


class TestSafePathJoin:
    """Test safe_path_join function."""

    def test_safe_join_simple(self, tmp_path):
        """Join paths safely."""
        result = safe_path_join(tmp_path, "subdir", "file.txt")

        expected = tmp_path / "subdir" / "file.txt"
        assert result == expected.resolve()

    def test_safe_join_prevents_traversal(self, tmp_path):
        """Prevent path traversal in join."""
        with pytest.raises(PathTraversalError, match="Path traversal detected"):
            safe_path_join(tmp_path, "..", "..", "etc", "passwd")

    def test_safe_join_prevents_absolute_path(self, tmp_path):
        """Prevent absolute path injection."""
        with pytest.raises(PathTraversalError, match="Path traversal detected"):
            safe_path_join(tmp_path, "/etc/passwd")


class TestIsSafePath:
    """Test is_safe_path function."""

    def test_safe_path_within_root(self, tmp_path):
        """Path within root is safe."""
        safe = tmp_path / "subdir" / "file.txt"
        assert is_safe_path(safe, tmp_path) is True

    def test_unsafe_path_outside_root(self, tmp_path):
        """Path outside root is unsafe."""
        outside = tmp_path / ".." / ".." / "etc" / "passwd"
        assert is_safe_path(outside, tmp_path) is False

    def test_safe_path_handles_symlinks(self, tmp_path):
        """Handle symlinks correctly."""
        # Create directory structure
        project = tmp_path / "project"
        project.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()

        # Symlink from project to outside
        escape = project / "escape"
        escape.symlink_to(outside)

        # Symlink resolves outside project
        assert is_safe_path(escape, project) is False


class TestValidateSafePatterns:
    """Test validate_safe_patterns function."""

    def test_valid_patterns(self):
        """Accept valid patterns."""
        patterns = ["*.py", "**/*.txt", "src/**/*.js"]

        validated = validate_safe_patterns(patterns)

        assert validated == patterns

    def test_reject_parent_directory_reference(self):
        """Reject patterns with ../."""
        patterns = ["../*.py"]

        with pytest.raises(PathValidationError, match="parent directory reference"):
            validate_safe_patterns(patterns)

    def test_reject_absolute_paths(self):
        """Reject absolute path patterns."""
        patterns = ["/etc/*.conf"]

        with pytest.raises(PathValidationError, match="absolute path"):
            validate_safe_patterns(patterns)


class TestMaliciousSymlinkScenarios:
    """Test with malicious symlink setups."""

    def test_symlink_to_sensitive_file(self, tmp_path):
        """Prevent access to sensitive files via symlink."""
        project = tmp_path / "project"
        project.mkdir()

        # Simulate /etc/passwd
        sensitive = tmp_path / "passwd"
        sensitive.write_text("root:x:0:0:root:/root:/bin/bash")

        # Create symlink to sensitive file
        malicious = project / "passwords.txt"
        malicious.symlink_to(sensitive)

        validator = PathValidator(project, allow_symlinks=False)

        # Should reject symlink
        with pytest.raises(SymlinkError):
            validator.validate(malicious)

    def test_symlink_chain_escape(self, tmp_path):
        """Prevent escape via chained symlinks."""
        project = tmp_path / "project"
        project.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()

        # Chain: link1 -> link2 -> outside
        link1 = project / "link1"
        link2 = project / "link2"

        link2.symlink_to(outside)
        link1.symlink_to(link2)

        validator = PathValidator(project, allow_symlinks=False)

        with pytest.raises(SymlinkError):
            validator.validate(link1)

    def test_symlink_in_parent_directory(self, tmp_path):
        """Detect symlink in parent path component."""
        project = tmp_path / "project"
        project.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "data.txt").write_text("sensitive")

        # Symlink a parent directory
        escape_dir = project / "escape_dir"
        escape_dir.symlink_to(outside)

        # Try to access file through symlinked directory
        malicious = escape_dir / "data.txt"

        validator = PathValidator(project, allow_symlinks=False)

        # Should reject - either as SymlinkError or PathTraversalError (both are valid)
        with pytest.raises((SymlinkError, PathTraversalError)):
            validator.validate(malicious)

    def test_relative_symlink_escape(self, tmp_path):
        """Prevent escape via relative symlink."""
        project = tmp_path / "project"
        project.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()

        # Relative symlink escaping project
        escape = project / "escape"
        escape.symlink_to("../outside")

        validator = PathValidator(project, allow_symlinks=False)

        with pytest.raises(SymlinkError):
            validator.validate(escape)

    def test_symlink_to_absolute_path(self, tmp_path):
        """Prevent symlink to absolute path outside project."""
        project = tmp_path / "project"
        project.mkdir()

        # Symlink to absolute path (system directory)
        evil = project / "system"
        evil.symlink_to("/etc")

        validator = PathValidator(project, allow_symlinks=False)

        with pytest.raises(SymlinkError):
            validator.validate(evil)

    def test_time_of_check_time_of_use_symlink_race(self, tmp_path):
        """Test TOCTOU protection with symlinks."""
        project = tmp_path / "project"
        project.mkdir()

        # Create normal file
        normal = project / "file.txt"
        normal.write_text("data")

        validator = PathValidator(project, allow_symlinks=False)

        # Validate normal file
        validated = validator.validate(normal)
        assert validated == normal.resolve()

        # Now replace with symlink (simulating TOCTOU race)
        normal.unlink()
        outside = tmp_path / "outside.txt"
        outside.write_text("sensitive")
        normal.symlink_to(outside)

        # Re-validation should fail
        with pytest.raises(SymlinkError):
            validator.validate(normal)
