"""Tests for ClaudeCodeAdapter"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from devloop.core.claude_adapter import ClaudeCodeAdapter


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project structure"""
    context_dir = tmp_path / ".claude" / "context"
    context_dir.mkdir(parents=True)

    agents_dir = tmp_path / ".agents" / "hooks"
    agents_dir.mkdir(parents=True)

    return tmp_path


@pytest.fixture
def adapter(temp_project):
    """Create a ClaudeCodeAdapter instance"""
    return ClaudeCodeAdapter(project_root=temp_project)


class TestInitialization:
    """Test adapter initialization"""

    def test_init_with_project_root(self, temp_project):
        adapter = ClaudeCodeAdapter(project_root=temp_project)
        assert adapter.project_root == temp_project
        assert adapter.context_dir == temp_project / ".claude" / "context"

    def test_init_without_project_root(self):
        adapter = ClaudeCodeAdapter()
        assert adapter.project_root == Path.cwd()

    def test_verify_script_path(self, adapter, temp_project):
        assert adapter.verify_script == temp_project / ".agents" / "verify-common-checks"

    def test_extract_script_path(self, adapter, temp_project):
        assert adapter.extract_script == temp_project / ".agents" / "hooks" / "extract-findings-to-beads"


class TestCheckResults:
    """Test check_results method"""

    def test_no_index_file(self, adapter):
        result = adapter.check_results()
        assert result["status"] == "no_results"
        assert result["actionable"] is False
        assert "haven't run yet" in result["message"]

    def test_no_actionable_items(self, adapter, temp_project):
        # Create index with no check_now items
        index_data = {
            "check_now": {"count": 0},
            "last_updated": "2024-01-01T00:00:00"
        }
        index_file = temp_project / ".claude" / "context" / "index.json"
        index_file.write_text(json.dumps(index_data))

        result = adapter.check_results()
        assert result["status"] == "success"
        assert result["actionable"] is False
        assert result["check_now_count"] == 0
        assert "No immediate issues" in result["display"]

    def test_with_actionable_items(self, adapter, temp_project):
        # Create index with check_now items
        index_data = {
            "check_now": {
                "count": 2,
                "severity_breakdown": {"error": 1, "warning": 1}
            },
            "last_updated": "2024-01-01T00:00:00"
        }
        index_file = temp_project / ".claude" / "context" / "index.json"
        index_file.write_text(json.dumps(index_data))

        # Create immediate findings
        immediate_data = {
            "findings": [
                {
                    "file": "test.py",
                    "severity": "error",
                    "message": "Test error",
                    "line": 10
                }
            ]
        }
        immediate_file = temp_project / ".claude" / "context" / "immediate.json"
        immediate_file.write_text(json.dumps(immediate_data))

        result = adapter.check_results()
        assert result["status"] == "success"
        assert result["actionable"] is True
        assert result["check_now_count"] == 2
        assert "immediate issue(s) found" in result["display"]

    def test_error_reading_index(self, adapter, temp_project):
        # Create invalid JSON file
        index_file = temp_project / ".claude" / "context" / "index.json"
        index_file.write_text("invalid json")

        result = adapter.check_results()
        assert result["status"] == "error"
        assert "Failed to check results" in result["message"]


class TestGetDetailedFindings:
    """Test get_detailed_findings method"""

    def test_get_all_tiers(self, adapter, temp_project):
        # Create findings for different tiers
        for tier in ["immediate", "relevant", "background", "auto_fixed"]:
            tier_file = temp_project / ".claude" / "context" / f"{tier}.json"
            tier_file.write_text(json.dumps({
                "findings": [{"agent": "test", "message": f"{tier} finding"}]
            }))

        result = adapter.get_detailed_findings("all")
        assert result["status"] == "success"
        assert "immediate" in result["findings"]
        assert "relevant" in result["findings"]
        assert "background" in result["findings"]
        assert "auto_fixed" in result["findings"]

    def test_get_specific_tier(self, adapter, temp_project):
        immediate_file = temp_project / ".claude" / "context" / "immediate.json"
        immediate_file.write_text(json.dumps({
            "findings": [{"agent": "linter", "message": "lint error"}]
        }))

        result = adapter.get_detailed_findings("immediate")
        assert result["status"] == "success"
        assert "immediate" in result["findings"]
        assert len(result["findings"]["immediate"]) == 1

    def test_no_findings_files(self, adapter):
        result = adapter.get_detailed_findings("all")
        assert result["status"] == "success"
        # Should return empty lists for all tiers
        for tier_findings in result["findings"].values():
            assert tier_findings == []


class TestGetAgentInsights:
    """Test get_agent_insights method"""

    def test_no_index_file(self, adapter):
        result = adapter.get_agent_insights()
        assert result["status"] == "no_results"
        assert "haven't run yet" in result["insights"][0]

    def test_lint_insights_no_issues(self, adapter, temp_project):
        self._create_index_and_findings(temp_project, [])

        result = adapter.get_agent_insights("lint")
        assert result["status"] == "success"
        assert result["query_type"] == "lint"
        assert "No linting issues" in result["insights"][0]

    def test_lint_insights_with_issues(self, adapter, temp_project):
        findings = [
            {
                "agent": "linter",
                "severity": "error",
                "message": "Missing semicolon",
                "file": "test.py",
                "auto_fixable": True
            },
            {
                "agent": "linter",
                "severity": "warning",
                "message": "Unused variable",
                "file": "test.py",
                "auto_fixable": False
            }
        ]
        self._create_index_and_findings(temp_project, findings)

        result = adapter.get_agent_insights("lint")
        assert result["status"] == "success"
        assert "2 linting issue(s)" in result["insights"][0]
        assert any("1 errors" in insight for insight in result["insights"])
        assert any("1 warnings" in insight for insight in result["insights"])
        assert any("auto-fix" in insight for insight in result["insights"])

    def test_test_insights(self, adapter, temp_project):
        findings = [
            {
                "agent": "test-runner",
                "message": "Test failed: test_something"
            }
        ]
        self._create_index_and_findings(temp_project, findings)

        result = adapter.get_agent_insights("test")
        assert result["status"] == "success"
        assert "1 test issue(s)" in result["insights"][0]

    def test_security_insights(self, adapter, temp_project):
        findings = [
            {
                "agent": "security-scanner",
                "severity": "high",
                "message": "SQL injection risk",
                "blocking": True
            }
        ]
        self._create_index_and_findings(temp_project, findings)

        result = adapter.get_agent_insights("security")
        assert result["status"] == "success"
        assert "1 security issue(s)" in result["insights"][0]
        assert any("high-priority" in insight for insight in result["insights"])

    def test_format_insights(self, adapter, temp_project):
        findings = [
            {
                "agent": "formatter",
                "message": "Line too long"
            }
        ]
        self._create_index_and_findings(temp_project, findings)

        result = adapter.get_agent_insights("format")
        assert result["status"] == "success"
        assert "1 formatting issue(s)" in result["insights"][0]

    def test_general_insights_no_issues(self, adapter, temp_project):
        index_data = {
            "check_now": {"count": 0},
            "last_updated": "2024-01-01T00:00:00"
        }
        index_file = temp_project / ".claude" / "context" / "index.json"
        index_file.write_text(json.dumps(index_data))

        result = adapter.get_agent_insights("general")
        assert result["status"] == "success"
        assert "All background checks passed" in result["insights"][0]

    def test_general_insights_with_issues(self, adapter, temp_project):
        index_data = {
            "check_now": {
                "count": 3,
                "severity_breakdown": {"error": 2, "warning": 1}
            },
            "last_updated": "2024-01-01T00:00:00"
        }
        index_file = temp_project / ".claude" / "context" / "index.json"
        index_file.write_text(json.dumps(index_data))

        immediate_findings = [
            {"agent": "linter", "message": "Error 1", "auto_fixable": True},
            {"agent": "linter", "message": "Error 2", "auto_fixable": False},
            {"agent": "test-runner", "message": "Test failed", "auto_fixable": False}
        ]
        immediate_file = temp_project / ".claude" / "context" / "immediate.json"
        immediate_file.write_text(json.dumps({"findings": immediate_findings}))

        result = adapter.get_agent_insights("general")
        assert result["status"] == "success"
        assert "3 immediate issue(s)" in result["insights"][0]
        assert any("auto-fixed" in insight for insight in result["insights"])

    def test_insights_error_handling(self, adapter, temp_project):
        # Create invalid JSON
        index_file = temp_project / ".claude" / "context" / "index.json"
        index_file.write_text("invalid")

        result = adapter.get_agent_insights()
        assert result["status"] == "error"
        assert "Error:" in result["insights"][0]

    @staticmethod
    def _create_index_and_findings(temp_project, findings):
        """Helper to create index and findings files"""
        index_data = {
            "check_now": {"count": len(findings)},
            "last_updated": "2024-01-01T00:00:00"
        }
        index_file = temp_project / ".claude" / "context" / "index.json"
        index_file.write_text(json.dumps(index_data))

        immediate_file = temp_project / ".claude" / "context" / "immediate.json"
        immediate_file.write_text(json.dumps({"findings": findings}))

        relevant_file = temp_project / ".claude" / "context" / "relevant.json"
        relevant_file.write_text(json.dumps({"findings": []}))


class TestPrivateMethods:
    """Test private helper methods"""

    def test_get_findings_no_file(self, adapter):
        result = adapter._get_findings("nonexistent")
        assert result == []

    def test_get_findings_valid_file(self, adapter, temp_project):
        findings = [{"agent": "test", "message": "finding"}]
        tier_file = temp_project / ".claude" / "context" / "test.json"
        tier_file.write_text(json.dumps({"findings": findings}))

        result = adapter._get_findings("test")
        assert result == findings

    def test_get_findings_invalid_json(self, adapter, temp_project):
        tier_file = temp_project / ".claude" / "context" / "test.json"
        tier_file.write_text("invalid json")

        result = adapter._get_findings("test")
        assert result == []

    def test_format_immediate_display_no_findings(self, adapter):
        check_now = {"count": 0}
        result = adapter._format_immediate_display(check_now, [])
        assert "No immediate issues" in result

    def test_format_immediate_display_with_findings(self, adapter):
        check_now = {"count": 2}
        findings = [
            {
                "file": "test.py",
                "severity": "error",
                "message": "Error message",
                "line": 10
            },
            {
                "file": "test.py",
                "severity": "warning",
                "message": "Warning message",
                "line": 20
            }
        ]

        result = adapter._format_immediate_display(check_now, findings)
        assert "2 immediate issue(s)" in result
        assert "test.py" in result
        assert "Error message" in result
        assert "Warning message" in result
        assert ":10" in result

    def test_format_immediate_display_many_files(self, adapter):
        check_now = {"count": 5}
        findings = [
            {"file": f"file{i}.py", "severity": "error", "message": f"Error {i}"}
            for i in range(5)
        ]

        result = adapter._format_immediate_display(check_now, findings)
        # Should only show first 3 files
        assert "and 2 more files" in result

    def test_create_detailed_summary(self, adapter):
        findings = {
            "immediate": [
                {"agent": "linter", "message": "Error 1"},
                {"agent": "linter", "message": "Error 2"},
                {"agent": "test-runner", "message": "Test failed"}
            ],
            "relevant": [
                {"agent": "formatter", "message": "Format issue"}
            ],
            "background": [],
            "auto_fixed": []
        }

        result = adapter._create_detailed_summary(findings)
        assert "IMMEDIATE (3 findings)" in result
        assert "RELEVANT (1 findings)" in result
        assert "linter: 2 findings" in result
        assert "test-runner: 1 findings" in result


class TestRunVerification:
    """Test run_verification method"""

    def test_verify_script_not_found(self, adapter):
        result = adapter.run_verification()
        assert result["status"] == "error"
        assert "not found" in result["message"]
        assert result["verified"] is False
        assert result["can_proceed"] is False

    @patch("subprocess.run")
    def test_verification_passed(self, mock_run, adapter, temp_project):
        # Create verify script
        verify_script = temp_project / ".agents" / "verify-common-checks"
        verify_script.touch()

        mock_run.return_value = Mock(
            returncode=0,
            stdout="✅ All checks passed\n",
            stderr=""
        )

        result = adapter.run_verification()
        assert result["status"] == "success"
        assert result["verified"] is True
        assert result["can_proceed"] is True
        assert "All checks passed" in result["message"]

    @patch("subprocess.run")
    def test_verification_failed(self, mock_run, adapter, temp_project):
        # Create verify script
        verify_script = temp_project / ".agents" / "verify-common-checks"
        verify_script.touch()

        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="❌ FAIL: Tests failed\n⚠️ Warning: Coverage low\n"
        )

        result = adapter.run_verification()
        assert result["status"] == "failed"
        assert result["verified"] is False
        assert result["can_proceed"] is False
        assert len(result["blocking_issues"]) > 0
        assert len(result["warnings"]) > 0

    @patch("subprocess.run")
    def test_verification_timeout(self, mock_run, adapter, temp_project):
        # Create verify script
        verify_script = temp_project / ".agents" / "verify-common-checks"
        verify_script.touch()

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="verify", timeout=120)

        result = adapter.run_verification()
        assert result["status"] == "timeout"
        assert result["verified"] is False
        assert "timed out" in result["message"]

    @patch("subprocess.run")
    def test_verification_exception(self, mock_run, adapter, temp_project):
        # Create verify script
        verify_script = temp_project / ".agents" / "verify-common-checks"
        verify_script.touch()

        mock_run.side_effect = Exception("Test error")

        result = adapter.run_verification()
        assert result["status"] == "error"
        assert result["verified"] is False
        assert "Test error" in result["message"]


class TestExtractFindings:
    """Test extract_findings method"""

    def test_extract_script_not_found(self, adapter):
        result = adapter.extract_findings()
        assert result["status"] == "error"
        assert "not found" in result["message"]
        assert result["extracted"] is False
        assert result["issues_created"] == 0

    @patch("subprocess.run")
    def test_extraction_success(self, mock_run, adapter, temp_project):
        # Create extract script
        extract_script = temp_project / ".agents" / "hooks" / "extract-findings-to-beads"
        extract_script.touch()

        mock_run.return_value = Mock(
            returncode=0,
            stdout="Created formatter issue: claude-agents-abc123\nCreated linter issue: claude-agents-xyz789\n",
            stderr=""
        )

        result = adapter.extract_findings()
        assert result["status"] == "success"
        assert result["extracted"] is True
        assert result["issues_created"] == 2
        assert "claude-agents-abc123" in result["issue_ids"]
        assert "claude-agents-xyz789" in result["issue_ids"]

    @patch("subprocess.run")
    def test_extraction_no_issues(self, mock_run, adapter, temp_project):
        # Create extract script
        extract_script = temp_project / ".agents" / "hooks" / "extract-findings-to-beads"
        extract_script.touch()

        mock_run.return_value = Mock(
            returncode=0,
            stdout="No findings to extract\n",
            stderr=""
        )

        result = adapter.extract_findings()
        assert result["status"] == "success"
        assert result["issues_created"] == 0

    @patch("subprocess.run")
    def test_extraction_timeout(self, mock_run, adapter, temp_project):
        # Create extract script
        extract_script = temp_project / ".agents" / "hooks" / "extract-findings-to-beads"
        extract_script.touch()

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="extract", timeout=60)

        result = adapter.extract_findings()
        assert result["status"] == "timeout"
        assert result["extracted"] is False


class TestVerifyAndExtract:
    """Test verify_and_extract combined workflow"""

    @patch.object(ClaudeCodeAdapter, "run_verification")
    @patch.object(ClaudeCodeAdapter, "extract_findings")
    def test_combined_workflow_success(self, mock_extract, mock_verify, adapter):
        mock_verify.return_value = {
            "status": "success",
            "verified": True,
            "blocking_issues": [],
            "warnings": []
        }

        mock_extract.return_value = {
            "status": "success",
            "extracted": True,
            "issues_created": 2,
            "issue_ids": ["issue-1", "issue-2"]
        }

        result = adapter.verify_and_extract()
        assert result["status"] == "success"
        assert result["verified"] is True
        assert result["can_save"] is True
        assert result["summary"]["checks_passed"] is True
        assert result["summary"]["beads_issues_created"] == 2

    @patch.object(ClaudeCodeAdapter, "run_verification")
    @patch.object(ClaudeCodeAdapter, "extract_findings")
    def test_combined_workflow_verification_failed(self, mock_extract, mock_verify, adapter):
        mock_verify.return_value = {
            "status": "failed",
            "verified": False,
            "blocking_issues": ["Error 1", "Error 2"],
            "warnings": ["Warning 1"]
        }

        mock_extract.return_value = {
            "status": "success",
            "issues_created": 2
        }

        result = adapter.verify_and_extract()
        assert result["status"] == "failed"
        assert result["verified"] is False
        assert result["can_save"] is False
        assert result["summary"]["issues_found"] == 2
        assert result["summary"]["warnings"] == 1
