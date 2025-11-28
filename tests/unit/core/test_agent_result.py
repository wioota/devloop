"""Unit tests for AgentResult dataclass."""

import pytest
from dev_agents.core.agent import AgentResult


class TestAgentResultValidCreation:
    """Test valid AgentResult creation scenarios."""

    def test_minimal_valid_creation(self):
        """Test creating AgentResult with all required parameters."""
        result = AgentResult(
            agent_name="test-agent",
            success=True,
            duration=1.5
        )

        assert result.agent_name == "test-agent"
        assert result.success is True
        assert result.duration == 1.5
        assert result.message == ""
        assert result.data is None
        assert result.error is None

    def test_full_valid_creation(self):
        """Test creating AgentResult with all parameters."""
        result = AgentResult(
            agent_name="test-agent",
            success=False,
            duration=2.5,
            message="Test failed",
            data={"issues": [1, 2, 3]},
            error="Some error occurred"
        )

        assert result.agent_name == "test-agent"
        assert result.success is False
        assert result.duration == 2.5
        assert result.message == "Test failed"
        assert result.data == {"issues": [1, 2, 3]}
        assert result.error == "Some error occurred"

    def test_zero_duration(self):
        """Test that zero duration is valid."""
        result = AgentResult(
            agent_name="test-agent",
            success=True,
            duration=0.0
        )

        assert result.duration == 0.0

    def test_integer_duration(self):
        """Test that integer duration is accepted."""
        result = AgentResult(
            agent_name="test-agent",
            success=True,
            duration=5
        )

        assert result.duration == 5

    def test_empty_data_dict(self):
        """Test that empty data dict is valid."""
        result = AgentResult(
            agent_name="test-agent",
            success=True,
            duration=1.0,
            data={}
        )

        assert result.data == {}


class TestAgentResultInvalidCreation:
    """Test invalid AgentResult creation scenarios."""

    def test_missing_duration_parameter(self):
        """Test that missing duration parameter raises TypeError."""
        with pytest.raises(TypeError, match="missing 1 required positional argument: 'duration'"):
            AgentResult(
                agent_name="test-agent",
                success=True
                # duration is missing!
            )

    def test_invalid_agent_name_type(self):
        """Test that non-string agent_name raises TypeError."""
        with pytest.raises(TypeError, match="agent_name must be a string"):
            AgentResult(
                agent_name=123,  # Should be string
                success=True,
                duration=1.0
            )

    def test_empty_agent_name(self):
        """Test that empty agent_name raises ValueError."""
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            AgentResult(
                agent_name="",
                success=True,
                duration=1.0
            )

    def test_invalid_success_type(self):
        """Test that non-boolean success raises TypeError."""
        with pytest.raises(TypeError, match="success must be a boolean"):
            AgentResult(
                agent_name="test-agent",
                success="yes",  # Should be bool
                duration=1.0
            )

    def test_invalid_duration_type_string(self):
        """Test that string duration raises TypeError."""
        with pytest.raises(TypeError, match="duration must be a number"):
            AgentResult(
                agent_name="test-agent",
                success=True,
                duration="1.5"  # Should be number
            )

    def test_invalid_duration_type_none(self):
        """Test that None duration raises TypeError with helpful message."""
        with pytest.raises(TypeError, match="duration must be a number.*Did you forget"):
            AgentResult(
                agent_name="test-agent",
                success=True,
                duration=None  # Should be number
            )

    def test_negative_duration(self):
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError, match="duration must be non-negative"):
            AgentResult(
                agent_name="test-agent",
                success=True,
                duration=-1.0
            )

    def test_invalid_message_type(self):
        """Test that non-string message raises TypeError."""
        with pytest.raises(TypeError, match="message must be a string"):
            AgentResult(
                agent_name="test-agent",
                success=True,
                duration=1.0,
                message=123  # Should be string
            )

    def test_invalid_data_type(self):
        """Test that non-dict data raises TypeError."""
        with pytest.raises(TypeError, match="data must be a dict or None"):
            AgentResult(
                agent_name="test-agent",
                success=True,
                duration=1.0,
                data=[1, 2, 3]  # Should be dict or None
            )

    def test_invalid_error_type(self):
        """Test that non-string error raises TypeError."""
        with pytest.raises(TypeError, match="error must be a string or None"):
            AgentResult(
                agent_name="test-agent",
                success=True,
                duration=1.0,
                error={"msg": "error"}  # Should be string or None
            )


class TestAgentResultEdgeCases:
    """Test edge cases for AgentResult."""

    def test_very_long_agent_name(self):
        """Test that very long agent names are accepted."""
        long_name = "a" * 1000
        result = AgentResult(
            agent_name=long_name,
            success=True,
            duration=1.0
        )

        assert result.agent_name == long_name

    def test_very_long_message(self):
        """Test that very long messages are accepted."""
        long_message = "x" * 10000
        result = AgentResult(
            agent_name="test-agent",
            success=True,
            duration=1.0,
            message=long_message
        )

        assert result.message == long_message

    def test_very_large_duration(self):
        """Test that very large durations are accepted."""
        result = AgentResult(
            agent_name="test-agent",
            success=True,
            duration=999999.999
        )

        assert result.duration == 999999.999

    def test_unicode_agent_name(self):
        """Test that unicode agent names are accepted."""
        result = AgentResult(
            agent_name="测试-агент-🤖",
            success=True,
            duration=1.0
        )

        assert result.agent_name == "测试-агент-🤖"

    def test_complex_nested_data(self):
        """Test that complex nested data structures are accepted."""
        complex_data = {
            "level1": {
                "level2": {
                    "level3": ["a", "b", {"level4": True}]
                }
            },
            "list": [1, 2, 3],
            "mixed": {"str": "value", "int": 42, "bool": False}
        }
        result = AgentResult(
            agent_name="test-agent",
            success=True,
            duration=1.0,
            data=complex_data
        )

        assert result.data == complex_data

    def test_multiline_error_message(self):
        """Test that multiline error messages are accepted."""
        multiline_error = """Line 1: Error occurred
Line 2: Stack trace
Line 3: More details"""
        result = AgentResult(
            agent_name="test-agent",
            success=False,
            duration=1.0,
            error=multiline_error
        )

        assert result.error == multiline_error


class TestAgentResultSuccessFailureScenarios:
    """Test common success and failure scenarios."""

    def test_successful_agent_result(self):
        """Test typical successful agent result."""
        result = AgentResult(
            agent_name="linter",
            success=True,
            duration=0.5,
            message="No issues found",
            data={"issues": [], "files_checked": 1}
        )

        assert result.success is True
        assert result.error is None

    def test_failed_agent_result(self):
        """Test typical failed agent result."""
        result = AgentResult(
            agent_name="linter",
            success=False,
            duration=0.3,
            message="Linting failed",
            error="Tool not found"
        )

        assert result.success is False
        assert result.error is not None

    def test_successful_with_warnings(self):
        """Test successful result that includes warnings in data."""
        result = AgentResult(
            agent_name="type-checker",
            success=True,
            duration=2.0,
            message="Type checked with warnings",
            data={
                "issues": [
                    {"severity": "warning", "message": "Unused import"}
                ],
                "warnings": 1,
                "errors": 0
            }
        )

        assert result.success is True
        assert result.data["warnings"] == 1

    def test_early_return_pattern(self):
        """Test early return pattern used in agents."""
        # This pattern is used when agents skip processing
        result = AgentResult(
            agent_name="security-scanner",
            success=True,
            duration=0.0,
            message="Skipped non-Python file"
        )

        assert result.success is True
        assert result.duration == 0.0
        assert result.data is None
