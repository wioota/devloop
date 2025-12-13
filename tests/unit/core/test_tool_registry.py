"""Tests for the tool registry system."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from devloop.core.tool_registry import ToolDefinition, ToolRegistry, ToolRunnerConfig


class TestToolDefinition:
    """Tests for ToolDefinition."""

    def test_tool_definition_valid(self):
        """Test creating a valid tool definition."""
        tool = ToolDefinition(
            name="black",
            tool_type="formatter",
            description="Python formatter",
            languages=["python"],
            runners={"poetry": "poetry run black"},
        )
        assert tool.name == "black"
        assert tool.tool_type == "formatter"
        assert tool.description == "Python formatter"
        assert tool.languages == ["python"]
        assert tool.runners == {"poetry": "poetry run black"}

    def test_tool_definition_missing_name(self):
        """Test that name is required."""
        with pytest.raises(ValueError, match="Tool name is required"):
            ToolDefinition(name="", tool_type="formatter")

    def test_tool_definition_missing_type(self):
        """Test that tool type is required."""
        with pytest.raises(ValueError, match="Tool type is required"):
            ToolDefinition(name="black", tool_type="")

    def test_tool_definition_invalid_type(self):
        """Test that tool type must be valid."""
        with pytest.raises(ValueError, match="Invalid tool type"):
            ToolDefinition(name="black", tool_type="invalid")

    def test_tool_definition_valid_types(self):
        """Test all valid tool types."""
        for tool_type in ["formatter", "linter", "typecheck", "test", "security"]:
            tool = ToolDefinition(name="test", tool_type=tool_type)
            assert tool.tool_type == tool_type


class TestToolRunnerConfig:
    """Tests for ToolRunnerConfig."""

    def test_runner_config_valid(self):
        """Test creating a valid runner config."""
        config = ToolRunnerConfig(
            name="poetry",
            available=True,
            version="1.0.0",
            check_command="poetry --version",
        )
        assert config.name == "poetry"
        assert config.available is True
        assert config.version == "1.0.0"

    def test_runner_config_invalid_name(self):
        """Test that runner name must be valid."""
        with pytest.raises(ValueError, match="Invalid runner"):
            ToolRunnerConfig(name="invalid", available=True)

    def test_runner_config_valid_names(self):
        """Test all valid runner names."""
        for runner in ["poetry", "pip", "npm", "yarn", "direct"]:
            config = ToolRunnerConfig(name=runner, available=True)
            assert config.name == runner


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_registry_builtin_tools(self):
        """Test that built-in tools are loaded."""
        registry = ToolRegistry()
        assert "black" in registry.tools
        assert "ruff" in registry.tools
        assert "mypy" in registry.tools
        assert "pytest" in registry.tools
        assert "eslint" in registry.tools

    def test_registry_get_tool(self):
        """Test retrieving a tool."""
        registry = ToolRegistry()
        black = registry.get_tool("black")
        assert black is not None
        assert black.name == "black"
        assert black.tool_type == "formatter"

    def test_registry_get_nonexistent_tool(self):
        """Test retrieving a non-existent tool."""
        registry = ToolRegistry()
        tool = registry.get_tool("nonexistent")
        assert tool is None

    def test_registry_get_tools_by_type(self):
        """Test getting tools by type."""
        registry = ToolRegistry()
        formatters = registry.get_tools_by_type("formatter")
        assert len(formatters) > 0
        assert all(t.tool_type == "formatter" for t in formatters)

    def test_registry_get_tools_by_language(self):
        """Test getting tools by language."""
        registry = ToolRegistry()
        python_tools = registry.get_tools_by_language("python")
        assert len(python_tools) > 0
        assert all("python" in t.languages for t in python_tools)

    def test_registry_tools_sorted_by_priority(self):
        """Test that tools are sorted by priority."""
        registry = ToolRegistry()
        formatters = registry.get_tools_by_type("formatter")
        priorities = [t.priority for t in formatters]
        assert priorities == sorted(priorities, reverse=True)

    def test_registry_available_runners(self):
        """Test that runners are detected."""
        registry = ToolRegistry()
        assert len(registry.available_runners) > 0
        # Direct execution should always be available
        assert "direct" in registry.available_runners
        assert registry.available_runners["direct"].available is True

    def test_registry_load_custom_tools(self):
        """Test loading custom tools from file."""
        with TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "tools.json"
            registry_file.write_text(
                json.dumps(
                    {
                        "tools": [
                            {
                                "name": "custom-tool",
                                "tool_type": "linter",
                                "description": "Custom tool",
                                "languages": ["python"],
                                "runners": {"direct": "custom-tool"},
                            }
                        ]
                    }
                )
            )

            registry = ToolRegistry(registry_file=registry_file)
            custom = registry.get_tool("custom-tool")
            assert custom is not None
            assert custom.name == "custom-tool"

    def test_registry_load_invalid_file(self):
        """Test that loading invalid file raises error."""
        with TemporaryDirectory() as tmpdir:
            registry_file = Path(tmpdir) / "invalid.json"
            registry_file.write_text("{invalid json")

            with pytest.raises(ValueError, match="Invalid registry file"):
                ToolRegistry(registry_file=registry_file)

    def test_registry_get_runner_command(self):
        """Test getting runner command for a tool."""
        registry = ToolRegistry()
        black = registry.get_tool("black")
        cmd = registry.get_runner_command(black)
        assert cmd is not None
        # Should be one of the available runners
        assert cmd in black.runners.values()

    def test_registry_get_available_tools(self):
        """Test getting available tools of a type."""
        registry = ToolRegistry()
        available = registry.get_available_tools("formatter")
        # At least one formatter should be available (direct execution)
        assert len(available) > 0

    def test_registry_get_best_tool(self):
        """Test getting highest-priority available tool."""
        registry = ToolRegistry()
        best = registry.get_best_tool("formatter")
        # Should return highest priority formatter
        assert best is not None
        all_formatters = registry.get_available_tools("formatter")
        assert best == all_formatters[0]

    def test_registry_list_tools_by_type(self):
        """Test listing tools grouped by type."""
        registry = ToolRegistry()
        tools = registry.list_tools(by_type=True)
        assert "formatter" in tools
        assert "linter" in tools
        assert "typecheck" in tools
        assert "test" in tools
        assert "security" in tools
        # Each tool should have name and description
        for tool_info in tools["formatter"]:
            assert "name" in tool_info
            assert "description" in tool_info
            assert "priority" in tool_info

    def test_registry_list_tools_flat(self):
        """Test listing tools flat."""
        registry = ToolRegistry()
        tools = registry.list_tools(by_type=False)
        assert "black" in tools
        assert tools["black"]["type"] == "formatter"
        assert "description" in tools["black"]
