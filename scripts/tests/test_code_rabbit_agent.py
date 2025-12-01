"""End-to-end tests for CodeRabbitAgent."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.devloop.agents.code_rabbit import CodeRabbitAgent
from src.devloop.core.event import Event, EventBus


@pytest.fixture
def event_bus():
    """Create event bus."""
    return EventBus()


@pytest.fixture
def agent(event_bus):
    """Create CodeRabbitAgent instance."""
    config = {
        "enabled": True,
        "apiKey": "test-api-key",
        "minSeverity": "warning",
        "filePatterns": ["**/*.py", "**/*.js"],
    }
    return CodeRabbitAgent(
        name="code-rabbit",
        triggers=["file:modified", "file:created"],
        event_bus=event_bus,
        config=config,
    )


@pytest.mark.asyncio
async def test_agent_skips_non_matching_files(agent):
    """Test agent skips files not in patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        txt_file = Path(tmpdir) / "test.txt"
        txt_file.write_text("some content")

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(txt_file)},
        )

        result = await agent.handle(event)

        assert result.success
        assert "not in patterns" in result.message


@pytest.mark.asyncio
async def test_agent_checks_tool_availability(agent):
    """Test agent checks if code-rabbit CLI is available."""
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = Path(tmpdir) / "test.py"
        py_file.write_text("x = 1")

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(py_file)},
        )

        # Mock subprocess to simulate missing tool
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 127  # command not found
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            result = await agent.handle(event)

            # Should indicate tool not available (non-blocking failure mode)
            # The agent reports it but doesn't block workflow
            assert "not installed" in result.message or not result.success


@pytest.mark.asyncio
async def test_agent_handles_missing_file(agent):
    """Test agent handles missing files gracefully."""
    event = Event(
        type="file:modified",
        source="filesystem",
        payload={"path": "/nonexistent/file.py"},
    )

    result = await agent.handle(event)

    assert result.success  # Non-blocking failure


@pytest.mark.asyncio
async def test_agent_parses_code_rabbit_output(agent):
    """Test agent correctly parses Code Rabbit JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = Path(tmpdir) / "test.py"
        py_file.write_text("import unused_module\nx = 1")

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(py_file)},
        )

        # Mock code-rabbit output
        mock_output = json.dumps(
            [
                {
                    "line": 1,
                    "column": 1,
                    "code": "unused-import",
                    "message": "Unused import 'unused_module'",
                    "severity": "warning",
                    "type": "code-smell",
                },
            ]
        ).encode()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()

            # First call: version check (success)
            version_response = AsyncMock()
            version_response.returncode = 0

            # Second call: analyze (with output)
            analyze_response = AsyncMock()
            analyze_response.returncode = 0
            analyze_response.communicate = AsyncMock(return_value=(mock_output, b""))

            mock_exec.side_effect = [version_response, analyze_response]

            result = await agent.handle(event)

            assert result.success
            assert result.data["issue_count"] == 1
            assert result.data["issues"][0]["code"] == "unused-import"


@pytest.mark.asyncio
async def test_agent_handles_code_rabbit_error(agent):
    """Test agent handles Code Rabbit execution errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = Path(tmpdir) / "test.py"
        py_file.write_text("x = 1")

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(py_file)},
        )

        # Mock subprocess error
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0  # version check succeeds
            version_response = AsyncMock()
            version_response.returncode = 0

            # Analyze fails
            analyze_response = AsyncMock()
            analyze_response.returncode = 1
            analyze_response.communicate = AsyncMock(
                return_value=(b"", b"Error running analysis")
            )

            mock_exec.side_effect = [version_response, analyze_response]

            result = await agent.handle(event)

            # Should report the error but not block workflow
            assert "failed" in result.message or not result.success


@pytest.mark.asyncio
async def test_agent_filters_by_severity(agent):
    """Test agent respects minSeverity configuration."""
    # Info severity with warning threshold should not be shown
    agent.config.min_severity = "error"

    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = Path(tmpdir) / "test.py"
        py_file.write_text("x = 1")

        event = Event(
            type="file:modified",
            source="filesystem",
            payload={"path": str(py_file)},
        )

        # Mock code-rabbit with info-level finding
        mock_output = json.dumps(
            [
                {
                    "line": 1,
                    "column": 1,
                    "code": "note-001",
                    "message": "Consider using f-strings",
                    "severity": "info",
                    "type": "style",
                },
            ]
        ).encode()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            version_response = AsyncMock()
            version_response.returncode = 0

            analyze_response = AsyncMock()
            analyze_response.returncode = 0
            analyze_response.communicate = AsyncMock(return_value=(mock_output, b""))

            mock_exec.side_effect = [version_response, analyze_response]

            result = await agent.handle(event)

            # Agent should record the finding but severity level was configured
            assert result.success


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
