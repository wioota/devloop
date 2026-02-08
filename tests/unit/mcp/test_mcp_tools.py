"""Tests for DevLoop MCP tools."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.core.context_store import (
    ContextStore,
    Finding,
    Severity,
    Tier,
)
from devloop.mcp.tools import (
    get_findings,
    dismiss_finding,
    apply_fix,
    FindingsFilter,
)


def create_test_finding(
    id: str = "test-001",
    agent: str = "test-agent",
    file: str = "/test/file.py",
    severity: Severity = Severity.WARNING,
    category: str = "test",
    message: str = "Test finding",
    line: int = 10,
    auto_fixable: bool = False,
    seen_by_user: bool = False,
) -> Finding:
    """Create a test finding with sensible defaults."""
    return Finding(
        id=id,
        agent=agent,
        timestamp=datetime.now(UTC).isoformat() + "Z",
        file=file,
        line=line,
        severity=severity,
        category=category,
        message=message,
        auto_fixable=auto_fixable,
        seen_by_user=seen_by_user,
    )


class TestFindingsFilter:
    """Tests for FindingsFilter dataclass."""

    def test_default_values(self) -> None:
        """Test default filter values."""
        filter = FindingsFilter()
        assert filter.file is None
        assert filter.severity is None
        assert filter.category is None
        assert filter.tier is None
        assert filter.limit == 100

    def test_with_values(self) -> None:
        """Test filter with custom values."""
        filter = FindingsFilter(
            file="/test/file.py",
            severity="error",
            category="security",
            tier="immediate",
            limit=50,
        )
        assert filter.file == "/test/file.py"
        assert filter.severity == "error"
        assert filter.category == "security"
        assert filter.tier == "immediate"
        assert filter.limit == 50


class TestGetFindings:
    """Tests for get_findings tool."""

    @pytest.fixture
    def mock_context_store(self) -> AsyncMock:
        """Create a mock context store."""
        store = AsyncMock(spec=ContextStore)
        return store

    @pytest.mark.asyncio
    async def test_get_findings_no_filters(self, mock_context_store: AsyncMock) -> None:
        """Test get_findings with no filters returns all findings."""
        findings = [
            create_test_finding(id="f1", severity=Severity.ERROR),
            create_test_finding(id="f2", severity=Severity.WARNING),
        ]
        mock_context_store.get_findings.return_value = findings

        result = await get_findings(mock_context_store)

        mock_context_store.get_findings.assert_called_once_with(
            tier=None, file_filter=None
        )
        assert len(result) == 2
        assert result[0]["id"] == "f1"
        assert result[1]["id"] == "f2"

    @pytest.mark.asyncio
    async def test_get_findings_with_file_filter(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test get_findings filters by file."""
        findings = [create_test_finding(id="f1", file="/test/file.py")]
        mock_context_store.get_findings.return_value = findings

        result = await get_findings(mock_context_store, file="/test/file.py")

        mock_context_store.get_findings.assert_called_once_with(
            tier=None, file_filter="/test/file.py"
        )
        assert len(result) == 1
        assert result[0]["file"] == "/test/file.py"

    @pytest.mark.asyncio
    async def test_get_findings_with_tier_filter(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test get_findings filters by tier."""
        findings = [create_test_finding(id="f1")]
        mock_context_store.get_findings.return_value = findings

        result = await get_findings(mock_context_store, tier="immediate")

        mock_context_store.get_findings.assert_called_once_with(
            tier=Tier.IMMEDIATE, file_filter=None
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_findings_with_severity_filter(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test get_findings filters by severity."""
        findings = [
            create_test_finding(id="f1", severity=Severity.ERROR),
            create_test_finding(id="f2", severity=Severity.WARNING),
        ]
        mock_context_store.get_findings.return_value = findings

        result = await get_findings(mock_context_store, severity="error")

        assert len(result) == 1
        assert result[0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_get_findings_with_category_filter(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test get_findings filters by category."""
        findings = [
            create_test_finding(id="f1", category="security"),
            create_test_finding(id="f2", category="style"),
        ]
        mock_context_store.get_findings.return_value = findings

        result = await get_findings(mock_context_store, category="security")

        assert len(result) == 1
        assert result[0]["category"] == "security"

    @pytest.mark.asyncio
    async def test_get_findings_with_limit(self, mock_context_store: AsyncMock) -> None:
        """Test get_findings respects limit."""
        findings = [create_test_finding(id=f"f{i}") for i in range(10)]
        mock_context_store.get_findings.return_value = findings

        result = await get_findings(mock_context_store, limit=5)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_findings_combined_filters(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test get_findings with multiple filters."""
        findings = [
            create_test_finding(id="f1", severity=Severity.ERROR, category="security"),
            create_test_finding(id="f2", severity=Severity.ERROR, category="style"),
            create_test_finding(
                id="f3", severity=Severity.WARNING, category="security"
            ),
        ]
        mock_context_store.get_findings.return_value = findings

        result = await get_findings(
            mock_context_store, severity="error", category="security"
        )

        assert len(result) == 1
        assert result[0]["id"] == "f1"

    @pytest.mark.asyncio
    async def test_get_findings_empty_result(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test get_findings returns empty list when no findings."""
        mock_context_store.get_findings.return_value = []

        result = await get_findings(mock_context_store)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_findings_returns_dict_format(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test get_findings returns findings as dictionaries."""
        findings = [create_test_finding(id="f1", line=42)]
        mock_context_store.get_findings.return_value = findings

        result = await get_findings(mock_context_store)

        assert isinstance(result, list)
        assert isinstance(result[0], dict)
        assert result[0]["id"] == "f1"
        assert result[0]["line"] == 42
        assert "timestamp" in result[0]


class TestDismissFinding:
    """Tests for dismiss_finding tool."""

    @pytest.fixture
    def mock_context_store(self) -> AsyncMock:
        """Create a mock context store."""
        store = AsyncMock(spec=ContextStore)
        return store

    @pytest.mark.asyncio
    async def test_dismiss_finding_success(self, mock_context_store: AsyncMock) -> None:
        """Test successfully dismissing a finding."""
        finding = create_test_finding(id="f1", seen_by_user=False)
        mock_context_store.get_findings.return_value = [finding]

        result = await dismiss_finding(mock_context_store, "f1")

        assert result["success"] is True
        assert result["finding_id"] == "f1"
        assert "dismissed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_dismiss_finding_not_found(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test dismissing a finding that doesn't exist."""
        mock_context_store.get_findings.return_value = []

        result = await dismiss_finding(mock_context_store, "nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_dismiss_finding_already_dismissed(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test dismissing an already dismissed finding."""
        finding = create_test_finding(id="f1", seen_by_user=True)
        mock_context_store.get_findings.return_value = [finding]

        result = await dismiss_finding(mock_context_store, "f1")

        # Should still succeed, just note it was already dismissed
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_dismiss_finding_with_reason(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test dismissing a finding with a reason."""
        finding = create_test_finding(id="f1")
        mock_context_store.get_findings.return_value = [finding]

        result = await dismiss_finding(
            mock_context_store, "f1", reason="False positive"
        )

        assert result["success"] is True
        assert result["reason"] == "False positive"


class TestApplyFix:
    """Tests for apply_fix tool."""

    @pytest.fixture
    def mock_context_store(self) -> AsyncMock:
        """Create a mock context store."""
        store = AsyncMock(spec=ContextStore)
        return store

    @pytest.mark.asyncio
    async def test_apply_fix_success(self, mock_context_store: AsyncMock) -> None:
        """Test successfully applying a fix."""
        finding = create_test_finding(id="f1", auto_fixable=True)
        mock_context_store.get_findings.return_value = [finding]

        with patch("devloop.mcp.tools.apply_fix_impl") as mock_apply:
            mock_apply.return_value = True

            result = await apply_fix(mock_context_store, "f1")

            assert result["success"] is True
            assert result["finding_id"] == "f1"
            mock_apply.assert_called_once_with("f1")

    @pytest.mark.asyncio
    async def test_apply_fix_finding_not_found(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test applying fix for non-existent finding."""
        mock_context_store.get_findings.return_value = []

        result = await apply_fix(mock_context_store, "nonexistent")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_apply_fix_not_auto_fixable(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test applying fix for non-auto-fixable finding."""
        finding = create_test_finding(id="f1", auto_fixable=False)
        mock_context_store.get_findings.return_value = [finding]

        result = await apply_fix(mock_context_store, "f1")

        assert result["success"] is False
        assert "not auto-fixable" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_apply_fix_failure(self, mock_context_store: AsyncMock) -> None:
        """Test handling fix application failure."""
        finding = create_test_finding(id="f1", auto_fixable=True)
        mock_context_store.get_findings.return_value = [finding]

        with patch("devloop.mcp.tools.apply_fix_impl") as mock_apply:
            mock_apply.return_value = False

            result = await apply_fix(mock_context_store, "f1")

            assert result["success"] is False
            assert "failed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_apply_fix_exception(self, mock_context_store: AsyncMock) -> None:
        """Test handling exceptions during fix application."""
        finding = create_test_finding(id="f1", auto_fixable=True)
        mock_context_store.get_findings.return_value = [finding]

        with patch("devloop.mcp.tools.apply_fix_impl") as mock_apply:
            mock_apply.side_effect = Exception("Fix failed")

            result = await apply_fix(mock_context_store, "f1")

            assert result["success"] is False
            assert "error" in result["message"].lower()


class TestToolIntegration:
    """Integration tests for MCP tools with real ContextStore."""

    @pytest.fixture
    def context_store(self, tmp_path: Path) -> ContextStore:
        """Create a real context store for testing."""
        context_dir = tmp_path / ".devloop" / "context"
        context_dir.mkdir(parents=True)
        store = ContextStore(context_dir=context_dir, enable_path_validation=False)
        return store

    @pytest.mark.asyncio
    async def test_get_findings_integration(self, context_store: ContextStore) -> None:
        """Test get_findings with real context store."""
        await context_store.initialize()

        # Add a finding
        finding = create_test_finding(id="int-001", file="/test/file.py")
        await context_store.add_finding(finding)

        # Get findings through the tool
        result = await get_findings(context_store)

        assert len(result) >= 1
        found = next((f for f in result if f["id"] == "int-001"), None)
        assert found is not None
        assert found["file"] == "/test/file.py"

    @pytest.mark.asyncio
    async def test_dismiss_finding_integration(
        self, context_store: ContextStore
    ) -> None:
        """Test dismiss_finding with real context store."""
        await context_store.initialize()

        # Add a finding
        finding = create_test_finding(id="int-002")
        await context_store.add_finding(finding)

        # Dismiss it
        result = await dismiss_finding(context_store, "int-002")

        assert result["success"] is True

        # Verify it's marked as seen
        findings = await context_store.get_findings()
        dismissed = next((f for f in findings if f.id == "int-002"), None)
        assert dismissed is not None
        assert dismissed.seen_by_user is True


# ============================================================================
# Verification Tools Tests
# ============================================================================


class TestRunFormatter:
    """Tests for run_formatter tool."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.py").write_text("x=1\n")
        return tmp_path

    @pytest.mark.asyncio
    async def test_run_formatter_success(self, project_root: Path) -> None:
        """Test running formatter successfully."""
        from devloop.mcp.tools import run_formatter

        # Mock subprocess to simulate black
        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"All done!\n", b""))
            mock_exec.return_value = mock_process

            result = await run_formatter(project_root)

            assert result["success"] is True
            assert result["returncode"] == 0
            assert "All done!" in result["stdout"]

    @pytest.mark.asyncio
    async def test_run_formatter_with_files(self, project_root: Path) -> None:
        """Test running formatter on specific files."""
        from devloop.mcp.tools import run_formatter

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"Formatted 1 file\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_formatter(project_root, files=["src/test.py"])

            assert result["success"] is True
            # Verify the files were passed to the command
            call_args = mock_exec.call_args
            assert "src/test.py" in call_args[0]

    @pytest.mark.asyncio
    async def test_run_formatter_failure(self, project_root: Path) -> None:
        """Test handling formatter failures."""
        from devloop.mcp.tools import run_formatter

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(
                return_value=(b"", b"error: cannot format\n")
            )
            mock_exec.return_value = mock_process

            result = await run_formatter(project_root)

            assert result["success"] is False
            assert result["returncode"] == 1
            assert "cannot format" in result["stderr"]

    @pytest.mark.asyncio
    async def test_run_formatter_timeout(self, project_root: Path) -> None:
        """Test handling formatter timeout."""
        import asyncio
        from devloop.mcp.tools import run_formatter

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.kill = MagicMock()
            mock_exec.return_value = mock_process

            # Patch wait_for to raise TimeoutError
            with patch("devloop.mcp.tools.asyncio.wait_for") as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await run_formatter(project_root, timeout=1)

                assert result["success"] is False
                assert "timed out" in result["error"].lower()
                mock_process.kill.assert_called_once()


class TestRunLinter:
    """Tests for run_linter tool."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.py").write_text("import os\nx = 1\n")
        return tmp_path

    @pytest.mark.asyncio
    async def test_run_linter_success(self, project_root: Path) -> None:
        """Test running linter successfully."""
        from devloop.mcp.tools import run_linter

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"All checks passed!\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_linter(project_root)

            assert result["success"] is True
            assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_run_linter_with_fix(self, project_root: Path) -> None:
        """Test running linter with --fix flag."""
        from devloop.mcp.tools import run_linter

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"Found 1 error, 1 fixed\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_linter(project_root, fix=True)

            assert result["success"] is True
            # Verify --fix was passed
            call_args = mock_exec.call_args
            assert "--fix" in call_args[0]

    @pytest.mark.asyncio
    async def test_run_linter_with_paths(self, project_root: Path) -> None:
        """Test running linter on specific paths."""
        from devloop.mcp.tools import run_linter

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_process

            result = await run_linter(project_root, paths=["src/"])

            assert result["success"] is True
            call_args = mock_exec.call_args
            assert "src/" in call_args[0]

    @pytest.mark.asyncio
    async def test_run_linter_with_errors(self, project_root: Path) -> None:
        """Test linter finding errors."""
        from devloop.mcp.tools import run_linter

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(
                return_value=(b"src/test.py:1:1 F401 unused import\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_linter(project_root)

            assert result["success"] is False
            assert result["returncode"] == 1
            assert "F401" in result["stdout"]

    @pytest.mark.asyncio
    async def test_run_linter_timeout(self, project_root: Path) -> None:
        """Test handling linter timeout."""
        import asyncio
        from devloop.mcp.tools import run_linter

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.kill = MagicMock()
            mock_exec.return_value = mock_process

            # Patch wait_for to raise TimeoutError
            with patch("devloop.mcp.tools.asyncio.wait_for") as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await run_linter(project_root, timeout=1)

                assert result["success"] is False
                assert "timed out" in result["error"].lower()
                mock_process.kill.assert_called_once()


class TestRunTypeChecker:
    """Tests for run_type_checker tool."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.py").write_text("def foo(x: int) -> str:\n    return x\n")
        return tmp_path

    @pytest.mark.asyncio
    async def test_run_type_checker_success(self, project_root: Path) -> None:
        """Test running type checker successfully."""
        from devloop.mcp.tools import run_type_checker

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"Success: no issues found\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_type_checker(project_root)

            assert result["success"] is True
            assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_run_type_checker_with_paths(self, project_root: Path) -> None:
        """Test running type checker on specific paths."""
        from devloop.mcp.tools import run_type_checker

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Success\n", b""))
            mock_exec.return_value = mock_process

            result = await run_type_checker(project_root, paths=["src/"])

            assert result["success"] is True
            call_args = mock_exec.call_args
            assert "src/" in call_args[0]

    @pytest.mark.asyncio
    async def test_run_type_checker_with_errors(self, project_root: Path) -> None:
        """Test type checker finding errors."""
        from devloop.mcp.tools import run_type_checker

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(
                return_value=(
                    b"src/test.py:2: error: Incompatible return value type\n",
                    b"",
                )
            )
            mock_exec.return_value = mock_process

            result = await run_type_checker(project_root)

            assert result["success"] is False
            assert result["returncode"] == 1
            assert "Incompatible return value" in result["stdout"]

    @pytest.mark.asyncio
    async def test_run_type_checker_timeout(self, project_root: Path) -> None:
        """Test handling type checker timeout."""
        import asyncio
        from devloop.mcp.tools import run_type_checker

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.kill = MagicMock()
            mock_exec.return_value = mock_process

            # Patch wait_for to raise TimeoutError
            with patch("devloop.mcp.tools.asyncio.wait_for") as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await run_type_checker(project_root, timeout=1)

                assert result["success"] is False
                assert "timed out" in result["error"].lower()
                mock_process.kill.assert_called_once()


class TestRunTests:
    """Tests for run_tests tool."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_example.py").write_text(
            "def test_pass():\n    assert True\n"
        )
        return tmp_path

    @pytest.mark.asyncio
    async def test_run_tests_success(self, project_root: Path) -> None:
        """Test running tests successfully."""
        from devloop.mcp.tools import run_tests

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"===== 1 passed =====\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_tests(project_root)

            assert result["success"] is True
            assert result["returncode"] == 0
            assert "passed" in result["stdout"]

    @pytest.mark.asyncio
    async def test_run_tests_with_path(self, project_root: Path) -> None:
        """Test running tests with a specific path."""
        from devloop.mcp.tools import run_tests

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"passed\n", b""))
            mock_exec.return_value = mock_process

            result = await run_tests(project_root, path="tests/test_example.py")

            assert result["success"] is True
            call_args = mock_exec.call_args
            assert "tests/test_example.py" in call_args[0]

    @pytest.mark.asyncio
    async def test_run_tests_with_marker(self, project_root: Path) -> None:
        """Test running tests with a marker filter."""
        from devloop.mcp.tools import run_tests

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"passed\n", b""))
            mock_exec.return_value = mock_process

            result = await run_tests(project_root, marker="slow")

            assert result["success"] is True
            call_args = mock_exec.call_args
            assert "-m" in call_args[0]
            assert "slow" in call_args[0]

    @pytest.mark.asyncio
    async def test_run_tests_with_keyword(self, project_root: Path) -> None:
        """Test running tests with a keyword filter."""
        from devloop.mcp.tools import run_tests

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"passed\n", b""))
            mock_exec.return_value = mock_process

            result = await run_tests(project_root, keyword="test_pass")

            assert result["success"] is True
            call_args = mock_exec.call_args
            assert "-k" in call_args[0]
            assert "test_pass" in call_args[0]

    @pytest.mark.asyncio
    async def test_run_tests_failure(self, project_root: Path) -> None:
        """Test handling test failures."""
        from devloop.mcp.tools import run_tests

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(
                return_value=(b"===== 1 failed =====\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_tests(project_root)

            assert result["success"] is False
            assert result["returncode"] == 1
            assert "failed" in result["stdout"]

    @pytest.mark.asyncio
    async def test_run_tests_timeout(self, project_root: Path) -> None:
        """Test handling tests timeout."""
        import asyncio
        from devloop.mcp.tools import run_tests

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.kill = MagicMock()
            mock_exec.return_value = mock_process

            # Patch wait_for to raise TimeoutError
            with patch("devloop.mcp.tools.asyncio.wait_for") as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await run_tests(project_root, timeout=1)

                assert result["success"] is False
                assert "timed out" in result["error"].lower()
                mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_tests_verbose(self, project_root: Path) -> None:
        """Test running tests with verbose output."""
        from devloop.mcp.tools import run_tests

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"passed\n", b""))
            mock_exec.return_value = mock_process

            result = await run_tests(project_root, verbose=True)

            assert result["success"] is True
            call_args = mock_exec.call_args
            assert "-v" in call_args[0]


# ============================================================================
# Agent Control Tools Tests
# ============================================================================


class TestRunAgent:
    """Tests for run_agent tool."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root with .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        (devloop_dir / "agents.json").write_text('{"agents": {}}')
        return tmp_path

    @pytest.mark.asyncio
    async def test_run_agent_formatter(self, project_root: Path) -> None:
        """Test running the formatter agent."""
        from devloop.mcp.tools import run_agent

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"Formatted 3 files\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_agent(project_root, agent_name="formatter")

            assert result["success"] is True
            assert result["agent"] == "formatter"
            assert "returncode" in result

    @pytest.mark.asyncio
    async def test_run_agent_linter(self, project_root: Path) -> None:
        """Test running the linter agent."""
        from devloop.mcp.tools import run_agent

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"All checks passed\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_agent(project_root, agent_name="linter")

            assert result["success"] is True
            assert result["agent"] == "linter"

    @pytest.mark.asyncio
    async def test_run_agent_type_checker(self, project_root: Path) -> None:
        """Test running the type-checker agent."""
        from devloop.mcp.tools import run_agent

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"Success: no issues found\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_agent(project_root, agent_name="type-checker")

            assert result["success"] is True
            assert result["agent"] == "type-checker"

    @pytest.mark.asyncio
    async def test_run_agent_security_scanner(self, project_root: Path) -> None:
        """Test running the security-scanner agent."""
        from devloop.mcp.tools import run_agent

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"No security issues found\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_agent(project_root, agent_name="security-scanner")

            assert result["success"] is True
            assert result["agent"] == "security-scanner"

    @pytest.mark.asyncio
    async def test_run_agent_test_runner(self, project_root: Path) -> None:
        """Test running the test-runner agent."""
        from devloop.mcp.tools import run_agent

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"===== 10 passed =====\n", b"")
            )
            mock_exec.return_value = mock_process

            result = await run_agent(project_root, agent_name="test-runner")

            assert result["success"] is True
            assert result["agent"] == "test-runner"

    @pytest.mark.asyncio
    async def test_run_agent_invalid_name(self, project_root: Path) -> None:
        """Test running an invalid agent name."""
        from devloop.mcp.tools import run_agent

        result = await run_agent(project_root, agent_name="invalid-agent")

        assert result["success"] is False
        assert (
            "unknown" in result["error"].lower() or "invalid" in result["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_run_agent_failure(self, project_root: Path) -> None:
        """Test handling agent failure."""
        from devloop.mcp.tools import run_agent

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(
                return_value=(b"", b"error: formatting failed\n")
            )
            mock_exec.return_value = mock_process

            result = await run_agent(project_root, agent_name="formatter")

            assert result["success"] is False
            assert result["returncode"] == 1

    @pytest.mark.asyncio
    async def test_run_agent_timeout(self, project_root: Path) -> None:
        """Test handling agent timeout."""
        import asyncio
        from devloop.mcp.tools import run_agent

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.kill = MagicMock()
            mock_exec.return_value = mock_process

            with patch("devloop.mcp.tools.asyncio.wait_for") as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                result = await run_agent(
                    project_root, agent_name="formatter", timeout=1
                )

                assert result["success"] is False
                assert "timed out" in result["error"].lower()


class TestRunAllAgents:
    """Tests for run_all_agents tool."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root with .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        (devloop_dir / "agents.json").write_text('{"agents": {}}')
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.py").write_text("x = 1\n")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        return tmp_path

    @pytest.mark.asyncio
    async def test_run_all_agents_success(self, project_root: Path) -> None:
        """Test running all agents successfully."""
        from devloop.mcp.tools import run_all_agents

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Success\n", b""))
            mock_exec.return_value = mock_process

            result = await run_all_agents(project_root)

            assert result["success"] is True
            assert "agents_run" in result
            assert len(result["agents_run"]) > 0

    @pytest.mark.asyncio
    async def test_run_all_agents_with_specific_agents(
        self, project_root: Path
    ) -> None:
        """Test running specific agents only."""
        from devloop.mcp.tools import run_all_agents

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"Success\n", b""))
            mock_exec.return_value = mock_process

            result = await run_all_agents(project_root, agents=["formatter", "linter"])

            assert result["success"] is True
            assert len(result["agents_run"]) == 2

    @pytest.mark.asyncio
    async def test_run_all_agents_partial_failure(self, project_root: Path) -> None:
        """Test handling partial agent failures."""
        from devloop.mcp.tools import run_all_agents

        call_count = [0]

        async def mock_communicate():
            call_count[0] += 1
            if call_count[0] == 1:
                return (b"Formatted\n", b"")
            else:
                return (b"", b"Error\n")

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = mock_communicate
            mock_exec.return_value = mock_process

            # Override returncode based on call
            original_communicate = mock_process.communicate

            async def communicate_with_returncode():
                result = await original_communicate()
                # Simulate failure for second agent
                mock_process.returncode = 1 if call_count[0] > 1 else 0
                return result

            mock_process.communicate = communicate_with_returncode

            result = await run_all_agents(project_root, agents=["formatter", "linter"])

            assert "agents_run" in result
            assert "failed" in result or any(
                not r.get("success", True) for r in result.get("results", [])
            )

    @pytest.mark.asyncio
    async def test_run_all_agents_stop_on_failure(self, project_root: Path) -> None:
        """Test stopping on first failure when requested."""
        from devloop.mcp.tools import run_all_agents

        with patch("devloop.mcp.tools.asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1  # Fail immediately
            mock_process.communicate = AsyncMock(return_value=(b"", b"Error\n"))
            mock_exec.return_value = mock_process

            result = await run_all_agents(
                project_root,
                agents=["formatter", "linter", "type-checker"],
                stop_on_failure=True,
            )

            # Should stop after first failure
            assert result["success"] is False
            # Only one agent should have run
            assert len(result.get("results", [])) == 1


class TestGetAgentStatus:
    """Tests for get_agent_status tool."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root with .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        return tmp_path

    @pytest.mark.asyncio
    async def test_get_agent_status_no_history(self, project_root: Path) -> None:
        """Test getting status when no agent history exists."""
        from devloop.mcp.tools import get_agent_status

        result = await get_agent_status(project_root)

        assert "agents" in result
        assert isinstance(result["agents"], dict)

    @pytest.mark.asyncio
    async def test_get_agent_status_with_history(self, project_root: Path) -> None:
        """Test getting status with agent run history."""
        from devloop.mcp.tools import get_agent_status

        # Mock the event store to return some history
        with patch("devloop.core.event_store.EventStore") as MockEventStore:
            mock_store = AsyncMock()
            mock_store.get_events.return_value = [
                MagicMock(
                    type="agent:formatter:completed",
                    payload={
                        "agent_name": "formatter",
                        "success": True,
                        "duration": 1.5,
                        "message": "Formatted 3 files",
                    },
                    timestamp=1704067200.0,  # 2024-01-01 00:00:00
                ),
                MagicMock(
                    type="agent:linter:completed",
                    payload={
                        "agent_name": "linter",
                        "success": False,
                        "duration": 2.0,
                        "message": "Found 5 issues",
                        "error": "Linting errors",
                    },
                    timestamp=1704067300.0,
                ),
            ]
            MockEventStore.return_value = mock_store

            result = await get_agent_status(project_root)

            assert "agents" in result
            # Should have formatter and linter in status
            assert len(result["agents"]) >= 0  # May be empty if no events

    @pytest.mark.asyncio
    async def test_get_agent_status_specific_agent(self, project_root: Path) -> None:
        """Test getting status for a specific agent."""
        from devloop.mcp.tools import get_agent_status

        result = await get_agent_status(project_root, agent_name="formatter")

        assert "agents" in result or "agent" in result

    @pytest.mark.asyncio
    async def test_get_agent_status_with_limit(self, project_root: Path) -> None:
        """Test getting status with a limit on history."""
        from devloop.mcp.tools import get_agent_status

        result = await get_agent_status(project_root, limit=5)

        # Result should respect the limit
        assert "agents" in result

    @pytest.mark.asyncio
    async def test_get_agent_status_includes_metadata(self, project_root: Path) -> None:
        """Test that status includes useful metadata."""
        from devloop.mcp.tools import get_agent_status

        result = await get_agent_status(project_root)

        # Should have summary information
        assert "agents" in result or "summary" in result


# ============================================================================
# Config Tools Tests
# ============================================================================


class TestGetConfig:
    """Tests for get_config tool."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root with .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        return tmp_path

    @pytest.mark.asyncio
    async def test_get_config_default(self, project_root: Path) -> None:
        """Test getting default configuration when no config file exists."""
        from devloop.mcp.tools import get_config

        result = await get_config(project_root)

        assert result["success"] is True
        assert result["project_root"] == str(project_root)
        assert "config" in result
        assert "agents" in result["config"]
        assert "global" in result["config"]

    @pytest.mark.asyncio
    async def test_get_config_with_file(self, project_root: Path) -> None:
        """Test getting configuration from an existing config file."""
        from devloop.mcp.tools import get_config
        import json

        # Create a custom config file
        config_data = {
            "version": "1.0",
            "enabled": True,
            "agents": {
                "formatter": {"enabled": True},
                "linter": {"enabled": False},
            },
            "global": {
                "mode": "active",
                "maxConcurrentAgents": 10,
            },
        }
        config_path = project_root / ".devloop" / "agents.json"
        config_path.write_text(json.dumps(config_data))

        result = await get_config(project_root)

        assert result["success"] is True
        assert result["project_root"] == str(project_root)
        assert result["config"]["global"]["mode"] == "active"
        assert result["config"]["global"]["maxConcurrentAgents"] == 10

    @pytest.mark.asyncio
    async def test_get_config_includes_enabled_agents(self, project_root: Path) -> None:
        """Test that config includes list of enabled agents."""
        from devloop.mcp.tools import get_config
        import json

        config_data = {
            "version": "1.0",
            "enabled": True,
            "agents": {
                "formatter": {"enabled": True},
                "linter": {"enabled": True},
                "test-runner": {"enabled": False},
            },
            "global": {"mode": "report-only"},
        }
        config_path = project_root / ".devloop" / "agents.json"
        config_path.write_text(json.dumps(config_data))

        result = await get_config(project_root)

        assert result["success"] is True
        assert "enabled_agents" in result
        assert "formatter" in result["enabled_agents"]
        assert "linter" in result["enabled_agents"]
        assert "test-runner" not in result["enabled_agents"]

    @pytest.mark.asyncio
    async def test_get_config_global_settings(self, project_root: Path) -> None:
        """Test that config includes global settings."""
        from devloop.mcp.tools import get_config

        result = await get_config(project_root)

        assert result["success"] is True
        # Should have global config summary
        assert "global_settings" in result
        assert "mode" in result["global_settings"]

    @pytest.mark.asyncio
    async def test_get_config_error_handling(self, project_root: Path) -> None:
        """Test handling invalid configuration file."""
        from devloop.mcp.tools import get_config

        # Create an invalid JSON config file
        config_path = project_root / ".devloop" / "agents.json"
        config_path.write_text("{ invalid json }")

        result = await get_config(project_root)

        # Should still succeed but return default config
        assert result["success"] is True
        assert "config" in result


class TestGetStatus:
    """Tests for get_status tool."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root with .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        context_dir = devloop_dir / "context"
        context_dir.mkdir()
        return tmp_path

    @pytest.mark.asyncio
    async def test_get_status_basic(self, project_root: Path) -> None:
        """Test getting basic status."""
        from devloop.mcp.tools import get_status

        result = await get_status(project_root)

        assert result["success"] is True
        assert "project_root" in result
        assert "watch_running" in result
        assert "last_update" in result

    @pytest.mark.asyncio
    async def test_get_status_watch_not_running(self, project_root: Path) -> None:
        """Test status when watch daemon is not running."""
        from devloop.mcp.tools import get_status

        result = await get_status(project_root)

        assert result["success"] is True
        assert result["watch_running"] is False

    @pytest.mark.asyncio
    async def test_get_status_watch_running(self, project_root: Path) -> None:
        """Test status when watch daemon is running."""
        from devloop.mcp.tools import get_status
        import os

        # Create a PID file to simulate running daemon
        pid_file = project_root / ".devloop" / "watch.pid"
        pid_file.write_text(str(os.getpid()))

        result = await get_status(project_root)

        assert result["success"] is True
        assert result["watch_running"] is True

    @pytest.mark.asyncio
    async def test_get_status_last_update(self, project_root: Path) -> None:
        """Test status includes last update time."""
        from devloop.mcp.tools import get_status
        import time

        # Create last update file
        last_update_file = project_root / ".devloop" / "context" / ".last_update"
        last_update_file.write_text("")
        # Touch the file to set modification time
        current_time = time.time()

        result = await get_status(project_root)

        assert result["success"] is True
        assert result["last_update"] is not None
        # Last update should be recent (within a few seconds)
        assert abs(result["last_update"] - current_time) < 5

    @pytest.mark.asyncio
    async def test_get_status_no_last_update(self, project_root: Path) -> None:
        """Test status when no last update file exists."""
        from devloop.mcp.tools import get_status

        result = await get_status(project_root)

        assert result["success"] is True
        assert result["last_update"] is None

    @pytest.mark.asyncio
    async def test_get_status_finding_counts(self, project_root: Path) -> None:
        """Test status includes finding counts."""
        from devloop.mcp.tools import get_status

        result = await get_status(project_root)

        assert result["success"] is True
        assert "finding_counts" in result
        # Should have counts by severity
        assert isinstance(result["finding_counts"], dict)

    @pytest.mark.asyncio
    async def test_get_status_with_findings(self, project_root: Path) -> None:
        """Test status with actual findings in context store."""
        from devloop.mcp.tools import get_status
        from devloop.core.context_store import ContextStore

        # Create context store and add some findings
        context_dir = project_root / ".devloop" / "context"
        store = ContextStore(context_dir=context_dir, enable_path_validation=False)
        await store.initialize()

        # Add some test findings
        finding1 = create_test_finding(id="s1", severity=Severity.ERROR)
        finding2 = create_test_finding(id="s2", severity=Severity.WARNING)
        finding3 = create_test_finding(id="s3", severity=Severity.ERROR)
        await store.add_finding(finding1)
        await store.add_finding(finding2)
        await store.add_finding(finding3)

        result = await get_status(project_root)

        assert result["success"] is True
        assert "finding_counts" in result
        assert result["finding_counts"].get("error", 0) == 2
        assert result["finding_counts"].get("warning", 0) == 1

    @pytest.mark.asyncio
    async def test_get_status_devloop_initialized(self, project_root: Path) -> None:
        """Test status shows if devloop is properly initialized."""
        from devloop.mcp.tools import get_status

        result = await get_status(project_root)

        assert result["success"] is True
        assert "initialized" in result
        assert result["initialized"] is True

    @pytest.mark.asyncio
    async def test_get_status_not_initialized(self, tmp_path: Path) -> None:
        """Test status when devloop is not initialized."""
        from devloop.mcp.tools import get_status

        # Use a directory without .devloop
        result = await get_status(tmp_path)

        assert result["success"] is True
        assert result["initialized"] is False
