"""Unit tests for SecurityScannerAgent."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from dev_agents.agents.security_scanner import SecurityScannerAgent, SecurityConfig
from dev_agents.core.event import Event


class TestSecurityConfig:
    """Test SecurityConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = SecurityConfig()

        assert config.enabled_tools == ["bandit"]
        assert config.severity_threshold == "medium"
        assert config.confidence_threshold == "medium"
        assert config.exclude_patterns == ["test*", "*_test.py", "*/tests/*"]
        assert config.max_issues == 50

    def test_custom_config(self):
        """Test custom configuration."""
        custom_config = {
            "enabled_tools": ["bandit", "safety"],
            "severity_threshold": "high",
            "confidence_threshold": "high",
            "exclude_patterns": ["custom_*"],
            "max_issues": 100
        }
        config = SecurityConfig(**custom_config)

        assert config.enabled_tools == ["bandit", "safety"]
        assert config.severity_threshold == "high"
        assert config.confidence_threshold == "high"
        assert config.exclude_patterns == ["custom_*"]
        assert config.max_issues == 100


class TestSecurityScannerAgent:
    """Test SecurityScannerAgent functionality."""

    @pytest.fixture
    def agent(self):
        """Create a security scanner agent for testing."""
        config = {
            "enabled_tools": ["bandit"],
            "severity_threshold": "medium",
            "confidence_threshold": "medium"
        }
        return SecurityScannerAgent(config, MagicMock())

    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return MagicMock()

    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.name == "security-scanner"
        assert "file:modified" in agent.triggers
        assert "file:created" in agent.triggers
        assert isinstance(agent.config, SecurityConfig)

    def test_is_test_file_exclusion(self, agent):
        """Test that test files are excluded."""
        test_files = [
            Path("test_file.py"),
            Path("my_test.py"),
            Path("tests/test_example.py"),
            Path("src/tests/security_test.py")
        ]

        for test_file in test_files:
            assert agent._should_exclude_file(str(test_file)), f"Should exclude {test_file}"

    def test_non_test_file_inclusion(self, agent):
        """Test that non-test files are not excluded."""
        regular_files = [
            Path("main.py"),
            Path("security.py"),
            Path("src/utils/helpers.py"),
            Path("lib/security/crypto.py")
        ]

        for regular_file in regular_files:
            assert not agent._should_exclude_file(str(regular_file)), f"Should not exclude {regular_file}"

    @pytest.mark.asyncio
    async def test_handle_non_python_file(self, agent):
        """Test handling of non-Python files."""
        # Create a temporary non-Python file
        non_py_file = Path("temp_styles.css")
        non_py_file.write_text("body { color: red; }")

        try:
            event = Event(
                type="file:modified",
                payload={"path": str(non_py_file)},
                source="test"
            )

            result = await agent.handle(event)

            assert result.success is True
            assert "Skipped non-Python file" in result.message
            assert result.agent_name == "security-scanner"

        finally:
            non_py_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_handle_missing_file(self, agent):
        """Test handling of missing files."""
        event = Event(
            type="file:modified",
            payload={"path": "nonexistent.py"},
            source="test"
        )

        result = await agent.handle(event)

        assert result.success is False
        assert "does not exist" in result.message

    @pytest.mark.asyncio
    async def test_handle_test_file(self, agent):
        """Test handling of test files (should be excluded)."""
        # Create a temporary test file
        test_file = Path("temp_test.py")
        test_file.write_text("# Test file")

        try:
            event = Event(
                type="file:modified",
                payload={"path": str(test_file)},
                source="test"
            )

            result = await agent.handle(event)

            assert result.success is True
            assert "Excluded file" in result.message

        finally:
            test_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    @patch('dev_agents.agents.security_scanner.SecurityScannerAgent._run_security_scan')
    async def test_handle_python_file(self, mock_scan, agent):
        """Test handling of Python files."""
        # Create a temporary Python file
        py_file = Path("temp_file.py")
        py_file.write_text("print('hello')")

        try:
            # Mock the security scan
            mock_result = MagicMock()
            mock_result.issues = []
            mock_result.errors = []
            mock_result.tool = "bandit"
            mock_result._get_severity_breakdown.return_value = {"low": 0, "medium": 0, "high": 0}
            mock_result._get_confidence_breakdown.return_value = {"low": 0, "medium": 0, "high": 0}
            mock_scan.return_value = mock_result

            event = Event(
                type="file:modified",
                payload={"path": str(py_file)},
                source="test"
            )

            result = await agent.handle(event)

            assert result.success is True
            assert "bandit" in result.message
            assert result.data["tool"] == "bandit"
            assert result.data["file"] == str(py_file)

            mock_scan.assert_called_once()

        finally:
            py_file.unlink(missing_ok=True)

    def test_filter_issues_by_severity(self, agent):
        """Test filtering issues by severity threshold."""
        issues = [
            {"severity": "low", "confidence": "high", "code": "B101"},
            {"severity": "medium", "confidence": "high", "code": "B102"},
            {"severity": "high", "confidence": "high", "code": "B103"},
        ]

        # Test medium threshold (should include medium and high)
        agent.config.severity_threshold = "medium"
        agent.config.confidence_threshold = "medium"

        filtered = agent._filter_issues(issues)
        assert len(filtered) == 2
        assert all(issue["severity"] in ["medium", "high"] for issue in filtered)

    def test_filter_issues_by_confidence(self, agent):
        """Test filtering issues by confidence threshold."""
        issues = [
            {"severity": "high", "confidence": "low", "code": "B101"},
            {"severity": "high", "confidence": "medium", "code": "B102"},
            {"severity": "high", "confidence": "high", "code": "B103"},
        ]

        # Test medium threshold (should include medium and high)
        agent.config.severity_threshold = "low"
        agent.config.confidence_threshold = "medium"

        filtered = agent._filter_issues(issues)
        assert len(filtered) == 2
        assert all(issue["confidence"] in ["medium", "high"] for issue in filtered)

    def test_max_issues_limit(self, agent):
        """Test that max_issues limit is respected."""
        issues = [
            {"severity": "high", "confidence": "high", "code": f"B10{i}"}
            for i in range(10)
        ]

        agent.config.max_issues = 5
        filtered = agent._filter_issues(issues)

        assert len(filtered) == 5

    @pytest.mark.asyncio
    async def test_bandit_tool_check(self, agent):
        """Test bandit tool availability checking."""
        with patch('subprocess.run') as mock_run:
            # Test when bandit is available
            mock_run.return_value = MagicMock(returncode=0)
            result = await agent._run_bandit(Path("test.py"))
            assert result is not None
            assert "bandit" in result.tool

            # Test when bandit is not available
            mock_run.return_value = MagicMock(returncode=1)
            result = await agent._run_bandit(Path("test.py"))
            assert result is not None
            assert "not installed" in result.errors[0]
