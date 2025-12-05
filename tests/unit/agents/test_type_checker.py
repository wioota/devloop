"""Unit tests for TypeCheckerAgent."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from devloop.agents.type_checker import TypeCheckerAgent, TypeCheckerConfig
from devloop.core.event import Event


class TestTypeCheckerConfig:
    """Test TypeCheckerConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = TypeCheckerConfig(**{})

        assert config.enabled_tools == ["mypy"]
        assert config.strict_mode is False
        assert config.show_error_codes is True
        assert config.exclude_patterns == ["test*", "*_test.py", "*/tests/*"]
        assert config.max_issues == 50

    def test_custom_config(self):
        """Test custom configuration."""
        custom_config = {
            "enabled_tools": ["mypy", "pyright"],
            "strict_mode": True,
            "show_error_codes": False,
            "exclude_patterns": ["custom_*"],
            "max_issues": 100,
        }
        config = TypeCheckerConfig(**custom_config)

        assert config.enabled_tools == ["mypy", "pyright"]
        assert config.strict_mode is True
        assert config.show_error_codes is False
        assert config.exclude_patterns == ["custom_*"]
        assert config.max_issues == 100


class TestTypeCheckerAgent:
    """Test TypeCheckerAgent functionality."""

    @pytest.fixture
    def agent(self):
        """Create a type checker agent for testing."""
        config = {
            "enabled_tools": ["mypy"],
            "strict_mode": False,
            "show_error_codes": True,
        }
        return TypeCheckerAgent(config, MagicMock())

    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.name == "type-checker"
        assert "file:modified" in agent.triggers
        assert "file:created" in agent.triggers
        assert isinstance(agent.config, TypeCheckerConfig)

    def test_is_test_file_exclusion(self, agent):
        """Test that test files are excluded."""
        test_files = [
            Path("test_file.py"),
            Path("my_test.py"),
            Path("tests/test_example.py"),
            Path("src/tests/type_test.py"),
        ]

        for test_file in test_files:
            assert agent._should_exclude_file(
                str(test_file)
            ), f"Should exclude {test_file}"

    def test_non_test_file_inclusion(self, agent):
        """Test that non-test files are not excluded."""
        regular_files = [
            Path("main.py"),
            Path("types.py"),
            Path("src/utils/helpers.py"),
            Path("lib/types/definitions.py"),
        ]

        for regular_file in regular_files:
            assert not agent._should_exclude_file(
                str(regular_file)
            ), f"Should not exclude {regular_file}"

    @pytest.mark.asyncio
    async def test_handle_non_python_file(self, agent):
        """Test handling of non-Python files."""
        # Create a temporary non-Python file
        non_py_file = Path("temp_styles.css")
        non_py_file.write_text("body { color: red; }")

        try:
            event = Event(
                type="file:modified", payload={"path": str(non_py_file)}, source="test"
            )

            result = await agent.handle(event)

            assert result.success is True
            assert "Skipped non-Python file" in result.message
            assert result.agent_name == "type-checker"

        finally:
            non_py_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_handle_missing_file(self, agent):
        """Test handling of missing files."""
        event = Event(
            type="file:modified", payload={"path": "nonexistent.py"}, source="test"
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
                type="file:modified", payload={"path": str(test_file)}, source="test"
            )

            result = await agent.handle(event)

            assert result.success is True
            assert "Excluded file" in result.message

        finally:
            test_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    @patch("devloop.agents.type_checker.TypeCheckerAgent._run_type_check")
    async def test_handle_python_file(self, mock_check, agent):
        """Test handling of Python files."""
        # Create a temporary Python file
        py_file = Path("temp_file.py")
        py_file.write_text("def hello() -> str: return 'world'")

        try:
            # Mock the type check
            mock_result = MagicMock()
            mock_result.issues = []
            mock_result.errors = []
            mock_result.tool = "mypy"
            mock_result._get_severity_breakdown.return_value = {
                "error": 0,
                "warning": 0,
                "note": 0,
            }
            mock_check.return_value = mock_result

            event = Event(
                type="file:modified", payload={"path": str(py_file)}, source="test"
            )

            result = await agent.handle(event)

            assert result.success is True
            assert "mypy" in result.message
            assert result.data["tool"] == "mypy"
            assert result.data["file"] == str(py_file)

            mock_check.assert_called_once()

        finally:
            py_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_mypy_tool_check(self, agent):
        """Test mypy tool availability checking."""
        # Test when mypy is available
        mock_result_available = MagicMock(exit_code=0, stdout="", stderr="")
        mock_result_success = MagicMock(
            exit_code=0, stdout="Success: no issues found", stderr=""
        )

        with patch.object(
            agent.sandbox,
            "run_sandboxed",
            side_effect=[mock_result_available, mock_result_success],
        ):
            result = await agent._run_mypy(Path("test.py"))
            assert result is not None
            assert "mypy" in result.tool

        # Test when mypy is not available
        mock_result_unavailable = MagicMock(
            exit_code=1, stdout="", stderr="ModuleNotFoundError"
        )

        with patch.object(
            agent.sandbox, "run_sandboxed", return_value=mock_result_unavailable
        ):
            result = await agent._run_mypy(Path("test.py"))
            assert result is not None
            assert "not installed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_mypy_output_parsing(self, agent):
        """Test parsing of mypy output."""
        mypy_output = """test.py:5: error: Argument 1 to "len" has incompatible type "int"; expected "Sized"  [arg-type]
test.py:10: note: Revealed type is "builtins.int"
Found 1 error in 1 file (checked 1 source file)
"""
        # Mock sandbox to return mypy output
        mock_check_result = MagicMock(exit_code=0, stdout="", stderr="")
        mock_mypy_result = MagicMock(exit_code=1, stdout=mypy_output, stderr="")

        with patch.object(
            agent.sandbox,
            "run_sandboxed",
            side_effect=[mock_check_result, mock_mypy_result],
        ):
            result = await agent._run_mypy(Path("test.py"))

            assert result.tool == "mypy"
            assert len(result.issues) == 2  # One error, one note
            assert result.issues[0]["severity"] == "error"
            assert result.issues[0]["line_number"] == 5
            assert "arg-type" in result.issues[0]["error_code"]
            assert result.issues[1]["severity"] == "note"

    @pytest.mark.asyncio
    async def test_strict_mode_flag(self, agent):
        """Test that strict mode adds the --strict flag."""
        agent.config.strict_mode = True

        mock_check_result = MagicMock(exit_code=0, stdout="", stderr="")
        mock_mypy_result = MagicMock(exit_code=0, stdout="", stderr="")

        with patch.object(
            agent.sandbox,
            "run_sandboxed",
            side_effect=[mock_check_result, mock_mypy_result],
        ) as mock_sandbox:
            result = await agent._run_mypy(Path("test.py"))  # noqa: F841

            # Check that run_sandboxed was called twice (availability check + mypy run)
            assert mock_sandbox.call_count == 2

            # Check that --strict was in the mypy command (second call)
            mypy_call = mock_sandbox.call_args_list[1]
            cmd = mypy_call[0][0]  # First positional arg is the command
            assert (
                "--strict" in cmd
            ), f"--strict not found in mypy command. Command: {cmd}"
