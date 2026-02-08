"""Tests for MCP verification tools."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from devloop.mcp.tools import (
    ToolResult,
    run_formatter,
    run_linter,
    run_subprocess,
    run_tests,
    run_type_checker,
)


class TestRunSubprocess:
    """Tests for run_subprocess helper."""

    @pytest.mark.asyncio
    async def test_successful_command(self, tmp_path: Path) -> None:
        """Successfully runs a command and captures output."""
        result = await run_subprocess(["echo", "hello"], tmp_path)

        assert result.success is True
        assert "hello" in result.output
        assert result.return_code == 0
        assert result.command == "echo hello"

    @pytest.mark.asyncio
    async def test_failing_command(self, tmp_path: Path) -> None:
        """Handles commands that exit with non-zero status."""
        result = await run_subprocess(["false"], tmp_path)

        assert result.success is False
        assert result.return_code != 0

    @pytest.mark.asyncio
    async def test_command_not_found(self, tmp_path: Path) -> None:
        """Handles missing commands gracefully."""
        result = await run_subprocess(["nonexistent_command_xyz123"], tmp_path)

        assert result.success is False
        assert "not found" in result.output.lower()
        assert result.return_code == -1

    @pytest.mark.asyncio
    async def test_timeout(self, tmp_path: Path) -> None:
        """Handles command timeout."""
        result = await run_subprocess(["sleep", "10"], tmp_path, timeout=1)

        assert result.success is False
        assert "timed out" in result.output.lower()
        assert result.return_code == -1


class TestRunFormatter:
    """Tests for run_formatter tool."""

    @pytest.mark.asyncio
    async def test_default_paths(self, tmp_path: Path) -> None:
        """Uses default paths when none specified."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="formatted", return_code=0, command=""
            )

            await run_formatter(tmp_path)

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "src/" in args
            assert "tests/" in args

    @pytest.mark.asyncio
    async def test_custom_paths(self, tmp_path: Path) -> None:
        """Formats specified paths."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_formatter(tmp_path, paths=["custom/path.py"])

            args = mock_run.call_args[0][0]
            assert "custom/path.py" in args

    @pytest.mark.asyncio
    async def test_check_only_mode(self, tmp_path: Path) -> None:
        """Runs in check-only mode without modifying files."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_formatter(tmp_path, check_only=True)

            args = mock_run.call_args[0][0]
            assert "--check" in args


class TestRunLinter:
    """Tests for run_linter tool."""

    @pytest.mark.asyncio
    async def test_default_paths(self, tmp_path: Path) -> None:
        """Uses default paths when none specified."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_linter(tmp_path)

            args = mock_run.call_args[0][0]
            assert "ruff" in args
            assert "check" in args
            assert "src/" in args

    @pytest.mark.asyncio
    async def test_fix_mode(self, tmp_path: Path) -> None:
        """Runs with --fix flag when requested."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_linter(tmp_path, fix=True)

            args = mock_run.call_args[0][0]
            assert "--fix" in args

    @pytest.mark.asyncio
    async def test_custom_paths(self, tmp_path: Path) -> None:
        """Lints specified paths."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_linter(tmp_path, paths=["src/module.py"])

            args = mock_run.call_args[0][0]
            assert "src/module.py" in args


class TestRunTypeChecker:
    """Tests for run_type_checker tool."""

    @pytest.mark.asyncio
    async def test_default_paths(self, tmp_path: Path) -> None:
        """Uses default paths when none specified."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="Success", return_code=0, command=""
            )

            await run_type_checker(tmp_path)

            args = mock_run.call_args[0][0]
            assert "mypy" in args
            assert "src/" in args

    @pytest.mark.asyncio
    async def test_custom_paths(self, tmp_path: Path) -> None:
        """Type checks specified paths."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_type_checker(tmp_path, paths=["src/core/"])

            args = mock_run.call_args[0][0]
            assert "src/core/" in args

    @pytest.mark.asyncio
    async def test_longer_default_timeout(self, tmp_path: Path) -> None:
        """Uses longer timeout for type checking."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_type_checker(tmp_path)

            # Default timeout should be 120 seconds
            timeout = mock_run.call_args[0][2]
            assert timeout == 120


class TestRunTests:
    """Tests for run_tests tool."""

    @pytest.mark.asyncio
    async def test_runs_all_tests_by_default(self, tmp_path: Path) -> None:
        """Runs all tests when no paths specified."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="passed", return_code=0, command=""
            )

            await run_tests(tmp_path)

            args = mock_run.call_args[0][0]
            assert "pytest" in args
            assert "--no-cov" in args

    @pytest.mark.asyncio
    async def test_specific_paths(self, tmp_path: Path) -> None:
        """Runs tests in specified paths."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_tests(tmp_path, paths=["tests/unit/"])

            args = mock_run.call_args[0][0]
            assert "tests/unit/" in args

    @pytest.mark.asyncio
    async def test_marker_filtering(self, tmp_path: Path) -> None:
        """Filters tests by markers."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_tests(tmp_path, markers=["unit", "not slow"])

            args = mock_run.call_args[0][0]
            assert "-m" in args
            assert "unit" in args
            assert "not slow" in args

    @pytest.mark.asyncio
    async def test_keyword_filtering(self, tmp_path: Path) -> None:
        """Filters tests by keyword expression."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_tests(tmp_path, keyword="test_login")

            args = mock_run.call_args[0][0]
            assert "-k" in args
            assert "test_login" in args

    @pytest.mark.asyncio
    async def test_verbose_mode(self, tmp_path: Path) -> None:
        """Runs in verbose mode when requested."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_tests(tmp_path, verbose=True)

            args = mock_run.call_args[0][0]
            assert "-v" in args

    @pytest.mark.asyncio
    async def test_longer_default_timeout(self, tmp_path: Path) -> None:
        """Uses longer timeout for test runs."""
        with patch(
            "devloop.mcp.tools.run_subprocess", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = ToolResult(
                success=True, output="", return_code=0, command=""
            )

            await run_tests(tmp_path)

            # Default timeout should be 300 seconds
            timeout = mock_run.call_args[0][2]
            assert timeout == 300
