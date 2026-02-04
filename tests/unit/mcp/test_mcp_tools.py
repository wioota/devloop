"""Tests for DevLoop MCP tools."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.core.context_store import (
    ContextStore,
    Finding,
    Severity,
    ScopeType,
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
    async def test_get_findings_no_filters(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test get_findings with no filters returns all findings."""
        findings = [
            create_test_finding(id="f1", severity=Severity.ERROR),
            create_test_finding(id="f2", severity=Severity.WARNING),
        ]
        mock_context_store.get_findings.return_value = findings

        result = await get_findings(mock_context_store)

        mock_context_store.get_findings.assert_called_once_with(tier=None, file_filter=None)
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

        result = await get_findings(
            mock_context_store, file="/test/file.py"
        )

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
    async def test_get_findings_with_limit(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test get_findings respects limit."""
        findings = [
            create_test_finding(id=f"f{i}") for i in range(10)
        ]
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
            create_test_finding(id="f3", severity=Severity.WARNING, category="security"),
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
    async def test_dismiss_finding_success(
        self, mock_context_store: AsyncMock
    ) -> None:
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
    async def test_apply_fix_success(
        self, mock_context_store: AsyncMock
    ) -> None:
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
    async def test_apply_fix_failure(
        self, mock_context_store: AsyncMock
    ) -> None:
        """Test handling fix application failure."""
        finding = create_test_finding(id="f1", auto_fixable=True)
        mock_context_store.get_findings.return_value = [finding]

        with patch("devloop.mcp.tools.apply_fix_impl") as mock_apply:
            mock_apply.return_value = False

            result = await apply_fix(mock_context_store, "f1")

            assert result["success"] is False
            assert "failed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_apply_fix_exception(
        self, mock_context_store: AsyncMock
    ) -> None:
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
        store = ContextStore(
            context_dir=context_dir, enable_path_validation=False
        )
        return store

    @pytest.mark.asyncio
    async def test_get_findings_integration(
        self, context_store: ContextStore
    ) -> None:
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
