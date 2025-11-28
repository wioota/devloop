"""Tests for DocLifecycleAgent."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from datetime import datetime

from dev_agents.agents.doc_lifecycle import DocLifecycleAgent, DocLifecycleConfig
from dev_agents.core.event import Event


class TestDocLifecycleAgent:
    """Test DocLifecycleAgent functionality."""

    @pytest.fixture
    def agent(self):
        """Create a DocLifecycleAgent instance."""
        return DocLifecycleAgent()

    @pytest.fixture
    def sample_md_files(self, tmp_path):
        """Create sample markdown files for testing."""
        # Create test files
        root_file = tmp_path / "test.md"
        root_file.write_text("# Test Document\nThis is a test.")

        docs_file = tmp_path / "docs" / "guide.md"
        docs_file.parent.mkdir(exist_ok=True)
        docs_file.write_text("# Guide\nThis is a guide.")

        complete_file = tmp_path / "complete.md"
        complete_file.write_text(
            "# Complete Task - COMPLETE ✅\n**Date:** November 28, 2025"
        )

        return tmp_path, [root_file, docs_file, complete_file]

    def test_agent_initialization(self, agent):
        """Test agent initializes with correct defaults."""
        assert agent.name == "doc-lifecycle"
        assert "file:created:**.md" in agent.triggers
        assert "file:modified:**.md" in agent.triggers
        assert "schedule:daily" in agent.triggers

    def test_config_defaults(self):
        """Test default configuration values."""
        config = DocLifecycleConfig()
        assert config.mode == "report-only"
        assert config.scan_interval == 86400
        assert config.archival_age_days == 30
        assert config.root_md_limit == 10
        assert config.archive_dir == "docs/archive"
        assert config.enforce_docs_structure is True
        assert config.detect_duplicates is True
        assert config.similarity_threshold == 0.5
        assert len(config.completion_markers) == 4
        assert len(config.keep_in_root) > 0
        assert len(config.never_archive) > 0

    def test_find_markdown_files(self, agent, sample_md_files):
        """Test finding markdown files in project."""
        tmp_path, expected_files = sample_md_files

        with patch.object(agent, "project_root", tmp_path):
            found_files = agent._find_markdown_files()

        # Should find all .md files
        assert len(found_files) == 3
        file_names = {f.name for f in found_files}
        assert "test.md" in file_names
        assert "guide.md" in file_names
        assert "complete.md" in file_names

    def test_count_md_files(self, agent, sample_md_files):
        """Test counting markdown files."""
        tmp_path, expected_files = sample_md_files

        with patch.object(agent, "project_root", tmp_path):
            count = agent._count_md_files()

        assert count == 3

    def test_count_root_md_files(self, agent, sample_md_files):
        """Test counting root directory markdown files."""
        tmp_path, expected_files = sample_md_files

        with patch.object(agent, "project_root", tmp_path):
            count = agent._count_root_md_files()

        # Should count test.md and complete.md (in root), but not guide.md (in docs/)
        assert count == 2

    def test_is_temporary_file(self, agent):
        """Test temporary file detection."""
        # Test temporary files
        assert agent._is_temporary_file(Path("SESSION_STATUS.md"))
        assert agent._is_temporary_file(Path("FIX_SUMMARY.md"))

        # Test regular files
        assert not agent._is_temporary_file(Path("README.md"))
        assert not agent._is_temporary_file(Path("guide.md"))

    def test_get_file_age_days(self, agent, tmp_path):
        """Test calculating file age in days."""
        # Create a real temporary file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Set file modification time to 5 days ago
        import time

        five_days_ago = time.time() - (5 * 24 * 60 * 60)
        import os

        os.utime(test_file, (five_days_ago, five_days_ago))

        # Calculate expected age (should be approximately 5 days)
        age = agent._get_file_age_days(test_file)
        assert 4 <= age <= 6  # Allow small timing differences

    def test_suggest_archive_location(self, agent, tmp_path):
        """Test archive location suggestion."""
        test_file = tmp_path / "TEST_FILE.md"
        test_file.write_text("# Test")

        # Set modification time to November 2025
        nov_2025 = datetime(2025, 11, 15).timestamp()
        import os

        os.utime(test_file, (nov_2025, nov_2025))

        suggestion = agent._suggest_archive_location(test_file)
        assert "docs/archive/2025-11/test-file.md" in suggestion

    def test_suggest_docs_location(self, agent):
        """Test docs location suggestion."""
        # Test guide file
        guide_path = Path("user-guide.md")
        suggestion = agent._suggest_docs_location(guide_path)
        assert "docs/guides/user-guide.md" in suggestion

        # Test reference file
        ref_path = Path("api-reference.md")
        suggestion = agent._suggest_docs_location(ref_path)
        assert "docs/reference/api-reference.md" in suggestion

        # Test other file
        other_path = Path("something.md")
        suggestion = agent._suggest_docs_location(other_path)
        assert "docs/something.md" in suggestion

    def test_detect_duplicate_docs(self, agent):
        """Test duplicate documentation detection."""
        files = [
            Path("README.md"),
            Path("readme.md"),  # Duplicate of README.md
            Path("getting-started.md"),
            Path("GETTING_STARTED.md"),  # Duplicate of getting-started.md
            Path("unique.md"),  # Unique file
        ]

        duplicates = agent._detect_duplicate_docs(files)

        # Should find 2 duplicate groups
        assert len(duplicates) == 2

        # Check that duplicates are properly grouped
        duplicate_names = []
        for group in duplicates:
            group_names = [f.stem.lower().replace("_", "-") for f in group]
            duplicate_names.extend(group_names)

        assert "readme" in duplicate_names
        assert "getting-started" in duplicate_names

    @pytest.mark.asyncio
    async def test_analyze_file_completion_marker(self, agent, tmp_path):
        """Test analyzing file with completion marker."""
        # Create a real test file with completion marker
        test_file = tmp_path / "complete.md"
        test_file.write_text(
            "# Task Complete - COMPLETE ✅\n**Date:** November 28, 2025"
        )

        findings = await agent._analyze_file(test_file)

        assert len(findings) == 2  # One for completion marker, one for date stamp
        assert findings[0]["category"] == "archival"
        assert "COMPLETE ✅" in findings[0]["message"]
        assert findings[1]["category"] == "dated"

    @pytest.mark.asyncio
    async def test_analyze_file_location_issue(self, agent, tmp_path):
        """Test analyzing file that should be moved to docs/."""
        # Create a file in the tmp_path (which simulates root)
        test_file = tmp_path / "reference.md"
        test_file.write_text("# Reference Guide\nSome content.")

        # Mock the project root to be tmp_path
        with patch.object(agent, "project_root", tmp_path):
            findings = await agent._analyze_file(test_file)

        # Should find location issue since reference.md is in root but not in keep_in_root
        location_findings = [f for f in findings if f.get("category") == "location"]
        assert len(location_findings) == 1
        assert "should possibly be in docs/" in location_findings[0]["message"]

    @pytest.mark.asyncio
    async def test_scan_documentation(self, agent, sample_md_files):
        """Test full documentation scan."""
        tmp_path, expected_files = sample_md_files

        with patch.object(agent, "project_root", tmp_path):
            findings = await agent.scan_documentation()

        # Should find various issues (at least completion marker and location issues)
        assert len(findings) > 0

        # Check for archival finding from completion marker
        archival_findings = [f for f in findings if f.get("category") == "archival"]
        assert len(archival_findings) >= 1

        # Check for location finding for reference.md
        location_findings = [f for f in findings if f.get("category") == "location"]
        assert len(location_findings) >= 1

    @pytest.mark.asyncio
    async def test_handle_event(self, agent):
        """Test handling an event."""
        event = Event(type="schedule:daily", payload={})

        result = await agent.handle(event)

        assert result.success is True
        assert "Documentation scan complete" in result.message
        assert "findings" in result.data
        assert "total_md_files" in result.data

    @pytest.mark.asyncio
    async def test_auto_fix_archival(self, agent, tmp_path):
        """Test automatic fixing of archival issues."""
        # Set agent to auto-fix mode
        agent.config.mode = "auto-fix"

        # Create a real test file in the current working directory
        source_file = Path("test.md")
        source_file.write_text("# Test file")

        try:
            # Create a finding with auto_fixable flag
            finding = {
                "category": "archival",
                "file": str(source_file),
                "suggestion": "Archive to docs/archive/2025-11/test.md",
                "auto_fixable": True,
            }

            success = await agent.auto_fix(finding)

            # Should succeed and move the file
            assert success is True
            assert not source_file.exists()  # File should be moved
            assert (Path("docs/archive/2025-11/test.md")).exists()
        finally:
            # Clean up
            if source_file.exists():
                source_file.unlink()
            archive_path = Path("docs/archive/2025-11/test.md")
            if archive_path.exists():
                archive_path.unlink()
                # Remove empty directories
                import shutil

                shutil.rmtree("docs/archive/2025-11", ignore_errors=True)
                shutil.rmtree("docs/archive", ignore_errors=True)
                shutil.rmtree("docs", ignore_errors=True)

    @pytest.mark.asyncio
    async def test_auto_fix_non_archival(self, agent):
        """Test auto-fix with non-archival finding."""
        agent.config.mode = "auto-fix"

        finding = {"category": "location", "file": "/tmp/test.md"}  # Not archival

        success = await agent.auto_fix(finding)

        assert success is False
