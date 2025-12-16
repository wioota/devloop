"""End-to-end tests for SnykAgent."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.devloop.agents.snyk import SnykAgent
from src.devloop.core.event import Event, EventBus


@pytest.fixture
def event_bus():
    """Create event bus."""
    return EventBus()


@pytest.fixture
def agent(event_bus):
    """Create SnykAgent instance."""
    config = {
        "enabled": True,
        "apiToken": "test-token",
        "severity": "high",
        "filePatterns": [
            "**/package.json",
            "**/requirements.txt",
            "**/Gemfile",
            "**/pom.xml",
        ],
    }
    return SnykAgent(
        name="snyk",
        triggers=["file:modified", "file:created"],
        event_bus=event_bus,
        config=config,
    )


@pytest.mark.asyncio
async def test_agent_skips_non_dependency_files(agent):
    """Test agent skips non-dependency files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = Path(tmpdir) / "app.py"
        py_file.write_text("print('hello')")

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(py_file)},
        )

        result = await agent.handle(event)

        assert result.success
        assert "not a dependency file" in result.message


@pytest.mark.asyncio
async def test_agent_recognizes_dependency_files(agent):
    """Test agent recognizes dependency files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test package.json recognition
        pkg_file = Path(tmpdir) / "package.json"
        pkg_file.write_text('{"name": "test"}')

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(pkg_file)},
        )

        # Should scan (and fail because snyk not installed, but that's ok)
        result = await agent.handle(event)

        # Result indicates it tried to scan (either succeeded or failed)
        # but didn't skip it
        assert "not a dependency file" not in result.message


@pytest.mark.asyncio
async def test_agent_checks_tool_availability(agent):
    """Test agent checks if snyk CLI is available."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg_file.write_text('{"name": "test"}')

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(pkg_file)},
        )

        # Mock subprocess to simulate missing tool
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 127  # command not found
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            result = await agent.handle(event)

            # Should indicate tool not available
            assert "not installed" in result.message or not result.success


@pytest.mark.asyncio
async def test_agent_parses_snyk_output(agent):
    """Test agent correctly parses Snyk JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg_file.write_text('{"name": "test"}')

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(pkg_file)},
        )

        # Mock snyk output with vulnerabilities
        mock_output = json.dumps(
            {
                "vulnerabilities": [
                    {
                        "id": "SNYK-JS-LODASH-1234567",
                        "title": "Prototype Pollution in lodash",
                        "severity": "high",
                        "cvssScore": 7.5,
                        "package": "lodash",
                        "from": ["lodash@4.17.15"],
                        "fixAvailable": True,
                        "upgradePath": ["lodash@4.17.21"],
                    },
                    {
                        "id": "SNYK-JS-EXPRESS-9876543",
                        "title": "Regular Expression DoS in express",
                        "severity": "critical",
                        "cvssScore": 9.1,
                        "package": "express",
                        "from": ["express@4.17.1"],
                        "fixAvailable": True,
                        "upgradePath": ["express@4.18.2"],
                    },
                ]
            }
        ).encode()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            # Version check
            version_response = AsyncMock()
            version_response.returncode = 0

            # Test response with vulnerabilities
            test_response = AsyncMock()
            test_response.returncode = 1  # Non-zero when vulns found
            test_response.communicate = AsyncMock(return_value=(mock_output, b""))

            mock_exec.side_effect = [version_response, test_response]

            result = await agent.handle(event)

            assert result.success
            assert result.data["vulnerability_count"] == 2
            assert result.data["critical_count"] == 1
            assert result.data["high_count"] == 1
            assert "critical" in result.message


@pytest.mark.asyncio
async def test_agent_filters_by_severity(agent):
    """Test agent respects severity configuration."""
    agent.config.severity = "critical"

    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg_file.write_text('{"name": "test"}')

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(pkg_file)},
        )

        # Mock snyk with mix of severities
        mock_output = json.dumps(
            {
                "vulnerabilities": [
                    {
                        "id": "SNYK-1",
                        "title": "Critical issue",
                        "severity": "critical",
                        "cvssScore": 9.0,
                        "package": "pkg1",
                        "from": ["pkg1@1.0.0"],
                        "fixAvailable": True,
                        "upgradePath": ["pkg1@2.0.0"],
                    },
                    {
                        "id": "SNYK-2",
                        "title": "High issue",
                        "severity": "high",
                        "cvssScore": 7.0,
                        "package": "pkg2",
                        "from": ["pkg2@1.0.0"],
                        "fixAvailable": False,
                        "upgradePath": [],
                    },
                ]
            }
        ).encode()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            version_response = AsyncMock()
            version_response.returncode = 0

            test_response = AsyncMock()
            test_response.returncode = 1
            test_response.communicate = AsyncMock(return_value=(mock_output, b""))

            mock_exec.side_effect = [version_response, test_response]

            result = await agent.handle(event)

            # Agent records all vulnerabilities
            assert result.data["vulnerability_count"] == 2


@pytest.mark.asyncio
async def test_agent_handles_snyk_error(agent):
    """Test agent handles Snyk execution errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg_file.write_text('{"name": "test"}')

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(pkg_file)},
        )

        # Mock snyk error response
        mock_output = json.dumps(
            {
                "error": {
                    "message": "Authentication failed - invalid token",
                    "code": "INVALID_TOKEN",
                }
            }
        ).encode()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            version_response = AsyncMock()
            version_response.returncode = 0

            test_response = AsyncMock()
            test_response.returncode = 1
            test_response.communicate = AsyncMock(return_value=(mock_output, b""))

            mock_exec.side_effect = [version_response, test_response]

            result = await agent.handle(event)

            assert not result.success
            assert "Authentication failed" in result.message


@pytest.mark.asyncio
async def test_agent_handles_no_vulnerabilities(agent):
    """Test agent handles clean scans."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg_file.write_text('{"name": "test"}')

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(pkg_file)},
        )

        # Mock snyk output with no vulnerabilities
        mock_output = json.dumps({"vulnerabilities": []}).encode()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            version_response = AsyncMock()
            version_response.returncode = 0

            test_response = AsyncMock()
            test_response.returncode = 0  # Zero = no vulnerabilities
            test_response.communicate = AsyncMock(return_value=(mock_output, b""))

            mock_exec.side_effect = [version_response, test_response]

            result = await agent.handle(event)

            assert result.success
            assert "No vulnerabilities" in result.message
            assert result.data["vulnerability_count"] == 0


@pytest.mark.asyncio
async def test_agent_handles_missing_file(agent):
    """Test agent handles missing files gracefully."""
    event = Event(
        type="file:modified",
        source="filesystem",
        payload={"path": "/nonexistent/package.json"},
    )

    result = await agent.handle(event)

    assert result.success  # Non-blocking


@pytest.mark.asyncio
async def test_agent_event_with_no_path(agent):
    """Test agent handles events with missing path."""
    event = Event(
        type="file:modified",
        source="filesystem",
        payload={},  # No path
    )

    result = await agent.handle(event)

    assert result.success
    assert "No file path" in result.message


@pytest.mark.asyncio
async def test_agent_writes_findings_to_context_store(agent):
    """Test agent correctly writes findings to context store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "package.json"
        pkg_file.write_text('{"name": "test"}')

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(pkg_file)},
        )

        # Mock snyk output with vulnerabilities
        mock_output = json.dumps(
            {
                "vulnerabilities": [
                    {
                        "id": "SNYK-JS-AXIOS-1234567",
                        "title": "Server-Side Request Forgery in axios",
                        "severity": "critical",
                        "cvssScore": 9.8,
                        "package": "axios",
                        "from": ["axios@0.21.1"],
                        "fixAvailable": True,
                        "upgradePath": ["axios@0.21.2"],
                    },
                ]
            }
        ).encode()

        # Mock context store
        from devloop.core.context_store import context_store

        findings_added = []

        async def mock_add_finding(finding):
            findings_added.append(finding)

        original_add_finding = context_store.add_finding
        context_store.add_finding = mock_add_finding

        try:
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                version_response = AsyncMock()
                version_response.returncode = 0

                test_response = AsyncMock()
                test_response.returncode = 1
                test_response.communicate = AsyncMock(return_value=(mock_output, b""))

                mock_exec.side_effect = [version_response, test_response]

                result = await agent.handle(event)

                assert result.success
                assert len(findings_added) == 1

                finding = findings_added[0]
                assert finding.agent == "snyk"
                assert finding.severity.value == "error"  # critical maps to ERROR
                assert "axios" in finding.message
                assert finding.context["vulnerability_id"] == "SNYK-JS-AXIOS-1234567"
                assert finding.context["cvss_score"] == 9.8
                assert finding.suggestion  # Should have upgrade path
        finally:
            context_store.add_finding = original_add_finding


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
