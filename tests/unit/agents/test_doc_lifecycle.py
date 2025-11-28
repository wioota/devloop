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
        complete_file.write_text("# Complete Task - COMPLETE ✅\n**Date:** November 28, 2025")

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

        with patch.object(agent, 'project_root', tmp_path):
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

        with patch.object(agent, 'project_root', tmp_path):
            count = agent._count_md_files()

        assert count == 3

    def test_count_root_md_files(self, agent, sample_md_files):
        """Test counting root directory markdown files."""
        tmp_path, expected_files = sample_md_files

        with patch.object(agent, 'project_root', tmp_path):
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

    def test_get_file_age_days(self, agent):
        """Test calculating file age in days."""
        # Create a mock file path
        mock_path = Path("test.md")

        # Mock the stat to return a specific modification time
        with patch.object(mock_path, 'stat') as mock_stat:
            # Set modification time to 5 days ago
            five_days_ago = datetime.now().timestamp() - (5 * 24 * 60 * 60)
            mock_stat.return_value.st_mtime = five_days_ago

            age = agent._get_file_age_days(mock_path)
            assert age == 5

    def test_suggest_archive_location(self, agent):
        """Test archive location suggestion."""
        mock_path = Path("TEST_FILE.md")

        with patch.object(mock_path, 'stat') as mock_stat:
            # Set modification time to November 2025
            nov_2025 = datetime(2025, 11, 15).timestamp()
            mock_stat.return_value.st_mtime = nov_2025

            suggestion = agent._suggest_archive_location(mock_path)
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
            Path("unique.md")  # Unique file
        ]

        duplicates = agent._detect_duplicate_docs(files)

        # Should find 2 duplicate groups
        assert len(duplicates) == 2

        # Check that duplicates are properly grouped
        duplicate_names = []
        for group in duplicates:
            group_names = [f.stem.lower().replace('_', '-') for f in group]
            duplicate_names.extend(group_names)

        assert "readme" in duplicate_names
        assert "getting-started" in duplicate_names

    @pytest.mark.asyncio
    async def test_analyze_file_completion_marker(self, agent):
        """Test analyzing file with completion marker."""
        # Create a test file with completion marker
        test_file = Path("complete.md")

        with patch.object(test_file, 'read_text', return_value="# Task Complete - COMPLETE ✅\n**Date:** November 28, 2025"):
            findings = await agent._analyze_file(test_file)

        assert len(findings) == 2  # One for completion marker, one for date stamp
        assert findings[0]["category"] == "archival"
        assert "COMPLETE ✅" in findings[0]["message"]
        assert findings[1]["category"] == "dated"

    @pytest.mark.asyncio
    async def test_analyze_file_location_issue(self, agent):
        """Test analyzing file that should be moved to docs/."""
        test_file = Path("reference.md")

        with patch.object(agent, 'project_root', Path("/tmp")):
            with patch.object(test_file, 'read_text', return_value="# Reference Guide\nSome content."):
                findings = await agent._analyze_file(test_file)

        # Should find location issue since reference.md is in root but not in keep_in_root
        location_findings = [f for f in findings if f.get("category") == "location"]
        assert len(location_findings) == 1
        assert "should possibly be in docs/" in location_findings[0]["message"]

    @pytest.mark.asyncio
    async def test_scan_documentation(self, agent, sample_md_files):
        """Test full documentation scan."""
        tmp_path, expected_files = sample_md_files

        with patch.object(agent, 'project_root', tmp_path):
            findings = await agent.scan_documentation()

        # Should find various issues
        assert len(findings) > 0

        # Check for root overflow finding
        overflow_findings = [f for f in findings if f.get("category") == "root_overflow"]
        assert len(overflow_findings) == 1
        assert "2 markdown files (limit: 10)" in overflow_findings[0]["message"]

    @pytest.mark.asyncio
    async def test_handle_event(self, agent):
        """Test handling an event."""
        event = Event(
            type="schedule:daily",
            payload={}
        )

        result = await agent.handle(event)

        assert result.success is True
        assert "Documentation scan complete" in result.message
        assert "findings" in result.data
        assert "total_md_files" in result.data

    @pytest.mark.asyncio
    async def test_auto_fix_archival(self, agent):
        """Test automatic fixing of archival issues."""
        # Set agent to auto-fix mode
        agent.config.mode = "auto-fix"

        # Create a mock finding
        finding = {
            "category": "archival",
            "file": "/tmp/test.md",
            "suggestion": "Archive to docs/archive/2025-11/test.md"
        }

        # Mock the file operations
        with patch('pathlib.Path.rename') as mock_rename, \
             patch('pathlib.Path.mkdir') as mock_mkdir:

            success = await agent.auto_fix(finding)

            assert success is True
            mock_mkdir.assert_called_once()
            mock_rename.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_fix_non_archival(self, agent):
        """Test auto-fix with non-archival finding."""
        agent.config.mode = "auto-fix"

        finding = {
            "category": "location",  # Not archival
            "file": "/tmp/test.md"
        }

        success = await agent.auto_fix(finding)

        assert success is False
