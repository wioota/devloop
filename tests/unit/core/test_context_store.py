"""Unit tests for context store."""

import asyncio
import json
from pathlib import Path
from datetime import datetime, UTC
import tempfile
import shutil

import pytest

from devloop.core.context_store import (
    ContextStore,
    Finding,
    Severity,
    ScopeType,
    Tier,
    UserContext,
)


class TestFindingValidation:
    """Test Finding dataclass validation."""

    def test_valid_finding_minimal(self):
        """Test creating a valid finding with minimal parameters."""
        finding = Finding(
            id="test_001",
            agent="linter",
            timestamp=datetime.now(UTC).isoformat() + "Z",
            file="test.py",
        )
        assert finding.id == "test_001"
        assert finding.agent == "linter"
        assert finding.file == "test.py"
        assert finding.severity == Severity.INFO  # default

    def test_valid_finding_full(self):
        """Test creating a valid finding with all parameters."""
        finding = Finding(
            id="test_002",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="src/auth.py",
            line=42,
            column=10,
            severity=Severity.ERROR,
            blocking=True,
            category="type_error",
            message="Missing type annotation",
            detail="Parameter 'user' has no type annotation",
            suggestion="Add type: User",
            auto_fixable=False,
            fix_command=None,
            scope_type=ScopeType.CURRENT_FILE,
            caused_by_recent_change=True,
            is_new=True,
            relevance_score=0.95,
        )
        assert finding.severity == Severity.ERROR
        assert finding.blocking is True
        assert finding.relevance_score == 0.95

    def test_invalid_finding_missing_id(self):
        """Test that missing id raises ValueError."""
        with pytest.raises(ValueError, match="id must be a non-empty string"):
            Finding(
                id="",
                agent="linter",
                timestamp="2025-11-28T10:00:00Z",
                file="test.py",
            )

    def test_invalid_finding_missing_agent(self):
        """Test that missing agent raises ValueError."""
        with pytest.raises(ValueError, match="agent must be a non-empty string"):
            Finding(
                id="test_003",
                agent="",
                timestamp="2025-11-28T10:00:00Z",
                file="test.py",
            )

    def test_invalid_finding_missing_file(self):
        """Test that missing file raises ValueError."""
        with pytest.raises(ValueError, match="file must be a non-empty string"):
            Finding(
                id="test_004",
                agent="linter",
                timestamp="2025-11-28T10:00:00Z",
                file="",
            )

    def test_invalid_finding_negative_line(self):
        """Test that negative line raises ValueError."""
        with pytest.raises(ValueError, match="line must be non-negative"):
            Finding(
                id="test_005",
                agent="linter",
                timestamp="2025-11-28T10:00:00Z",
                file="test.py",
                line=-1,
            )

    def test_invalid_finding_relevance_out_of_range(self):
        """Test that relevance score out of range raises ValueError."""
        with pytest.raises(ValueError, match="relevance_score must be between"):
            Finding(
                id="test_006",
                agent="linter",
                timestamp="2025-11-28T10:00:00Z",
                file="test.py",
                relevance_score=1.5,
            )

    def test_string_enum_conversion(self):
        """Test that string severity is converted to enum."""
        finding = Finding(
            id="test_007",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity="error",  # string
        )
        assert finding.severity == Severity.ERROR
        assert isinstance(finding.severity, Severity)


class TestContextStoreBasicOperations:
    """Test basic context store operations."""

    @pytest.fixture
    def temp_context_dir(self):
        """Create a temporary context directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def store(self, temp_context_dir):
        """Create a context store with temp directory."""
        return ContextStore(context_dir=temp_context_dir)

    @pytest.mark.asyncio
    async def test_initialize_creates_directory(self, store, temp_context_dir):
        """Test that initialize creates the context directory."""
        await store.initialize()
        assert temp_context_dir.exists()
        assert temp_context_dir.is_dir()

    @pytest.mark.asyncio
    async def test_add_finding_creates_files(self, store, temp_context_dir):
        """Test that adding a finding creates the tier file."""
        await store.initialize()

        finding = Finding(
            id="test_008",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            line=10,
            severity=Severity.ERROR,
            blocking=True,
            message="Test error",
            relevance_score=0.9,
        )

        await store.add_finding(finding)

        # Should be in immediate tier
        immediate_file = temp_context_dir / "immediate.json"
        assert immediate_file.exists()

        # Check contents
        data = json.loads(immediate_file.read_text())
        assert data["tier"] == "immediate"
        assert data["count"] == 1
        assert len(data["findings"]) == 1
        assert data["findings"][0]["id"] == "test_008"

    @pytest.mark.asyncio
    async def test_index_created(self, store, temp_context_dir):
        """Test that index file is created and updated."""
        await store.initialize()

        finding = Finding(
            id="test_009",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.WARNING,
            message="Test warning",
            relevance_score=0.5,
        )

        await store.add_finding(finding)

        # Check index exists
        index_file = temp_context_dir / "index.json"
        assert index_file.exists()

        # Check index contents
        index = json.loads(index_file.read_text())
        assert "last_updated" in index
        assert "check_now" in index
        assert "mention_if_relevant" in index

        # This should be in relevant tier (score 0.5)
        assert index["mention_if_relevant"]["count"] == 1

    @pytest.mark.asyncio
    async def test_get_findings(self, store, temp_context_dir):
        """Test retrieving findings from store."""
        await store.initialize()

        # Add multiple findings
        finding1 = Finding(
            id="test_010",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.ERROR,
            blocking=True,
            relevance_score=0.9,
        )

        finding2 = Finding(
            id="test_011",
            agent="formatter",
            timestamp="2025-11-28T10:00:00Z",
            file="other.py",
            severity=Severity.STYLE,
            auto_fixable=True,
            relevance_score=0.3,
        )

        await store.add_finding(finding1)
        await store.add_finding(finding2)

        # Get all findings
        all_findings = await store.get_findings()
        assert len(all_findings) == 2

        # Get immediate tier only
        immediate = await store.get_findings(tier=Tier.IMMEDIATE)
        assert len(immediate) == 1
        assert immediate[0].id == "test_010"

    @pytest.mark.asyncio
    async def test_clear_findings(self, store, temp_context_dir):
        """Test clearing findings from store."""
        await store.initialize()

        finding = Finding(
            id="test_012",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.WARNING,
            relevance_score=0.5,
        )

        await store.add_finding(finding)

        # Verify it's there
        findings = await store.get_findings()
        assert len(findings) == 1

        # Clear all
        count = await store.clear_findings()
        assert count == 1

        # Verify it's gone
        findings = await store.get_findings()
        assert len(findings) == 0


class TestRelevanceScoring:
    """Test relevance scoring algorithm."""

    def test_compute_relevance_current_file_editing(self):
        """Test relevance when finding is in currently editing file."""
        store = ContextStore()
        finding = Finding(
            id="test_013",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="auth.py",
            severity=Severity.ERROR,
        )
        user_context = UserContext(
            currently_editing=["auth.py"],
            phase="active_coding",
        )

        score = store.compute_relevance(finding, user_context)
        # current file (0.5) + error (0.3) - active coding (-0.2) = 0.6
        assert score >= 0.5  # At least file scope points

    def test_compute_relevance_blocking_error(self):
        """Test relevance for blocking errors."""
        store = ContextStore()
        finding = Finding(
            id="test_014",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.ERROR,
            blocking=True,
            is_new=False,  # Explicitly set to avoid default
        )
        user_context = UserContext()

        score = store.compute_relevance(finding, user_context)
        # blocking (0.4) - active_coding (-0.2) = 0.2
        assert score >= 0.2

    def test_compute_relevance_recent_change(self):
        """Test relevance boost for recent changes."""
        store = ContextStore()
        finding = Finding(
            id="test_015",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.WARNING,
            is_new=True,
            caused_by_recent_change=True,
        )
        user_context = UserContext()

        score = store.compute_relevance(finding, user_context)
        # warning (0.15) + fresh (0.3) - active_coding (-0.2) = 0.25
        assert score >= 0.24  # Allow for floating point precision

    def test_compute_relevance_pre_commit_phase(self):
        """Test relevance boost during pre-commit phase."""
        store = ContextStore()
        finding = Finding(
            id="test_016",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.WARNING,
        )
        user_context = UserContext(
            phase="pre_commit",
        )

        score = store.compute_relevance(finding, user_context)
        # Pre-commit phase adds 0.2
        assert score > 0.0


class TestTierAssignment:
    """Test tier assignment logic."""

    def test_blocking_always_immediate(self):
        """Test that blocking findings always go to immediate."""
        store = ContextStore()
        finding = Finding(
            id="test_017",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            blocking=True,
            relevance_score=0.1,  # Even with low score
        )

        tier = store.assign_tier(finding)
        assert tier == Tier.IMMEDIATE

    def test_high_relevance_immediate(self):
        """Test that high relevance goes to immediate."""
        store = ContextStore()
        finding = Finding(
            id="test_018",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.ERROR,
            relevance_score=0.85,
        )

        tier = store.assign_tier(finding)
        assert tier == Tier.IMMEDIATE

    def test_medium_relevance_relevant(self):
        """Test that medium relevance goes to relevant."""
        store = ContextStore()
        finding = Finding(
            id="test_019",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.WARNING,
            relevance_score=0.5,
        )

        tier = store.assign_tier(finding)
        assert tier == Tier.RELEVANT

    def test_low_relevance_background(self):
        """Test that low relevance goes to background."""
        store = ContextStore()
        finding = Finding(
            id="test_020",
            agent="linter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.INFO,
            relevance_score=0.2,
        )

        tier = store.assign_tier(finding)
        assert tier == Tier.BACKGROUND

    def test_auto_fixable_style_auto_fixed(self):
        """Test that auto-fixable style issues go to auto_fixed."""
        store = ContextStore()
        finding = Finding(
            id="test_021",
            agent="formatter",
            timestamp="2025-11-28T10:00:00Z",
            file="test.py",
            severity=Severity.STYLE,
            auto_fixable=True,
            relevance_score=0.3,
        )

        tier = store.assign_tier(finding)
        assert tier == Tier.AUTO_FIXED


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
