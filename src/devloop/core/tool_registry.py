"""
Tool Registry System for DevLoop

Provides a modular, extensible registry for managing development tools
(formatters, linters, type checkers, test runners, security scanners).

Supports multiple runners (Poetry, pip, npm, yarn, direct execution) with
graceful degradation when tools are unavailable.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of a development tool."""

    name: str
    """Tool name (e.g., 'black', 'ruff', 'mypy')."""

    tool_type: str
    """Tool type: formatter, linter, typecheck, test, security."""

    description: str = ""
    """Human-readable description."""

    languages: List[str] = field(default_factory=list)
    """Languages this tool supports (e.g., ['python', 'javascript'])."""

    runners: Dict[str, str] = field(default_factory=dict)
    """Runner command templates by type: poetry, pip, npm, yarn, direct."""

    check_command: Optional[str] = None
    """Command to check if tool is available (default: tool --version)."""

    config_files: List[str] = field(default_factory=list)
    """Config files this tool looks for (e.g., ['pyproject.toml', '.ruff.toml'])."""

    priority: int = 50
    """Priority when multiple tools of same type available (0-100, higher=preferred)."""

    auto_fixable: bool = False
    """Whether tool can automatically fix issues."""

    fix_command_template: Optional[str] = None
    """Template for auto-fix command (e.g., '{runner} {name} --fix {paths}')."""

    def __post_init__(self):
        """Validate tool definition."""
        if not self.name:
            raise ValueError("Tool name is required")
        if not self.tool_type:
            raise ValueError("Tool type is required")
        if self.tool_type not in {
            "formatter",
            "linter",
            "typecheck",
            "test",
            "security",
        }:
            raise ValueError(
                f"Invalid tool type: {self.tool_type}. "
                "Must be one of: formatter, linter, typecheck, test, security"
            )


@dataclass
class ToolRunnerConfig:
    """Configuration for a specific runner (Poetry, pip, etc)."""

    name: str
    """Runner name: poetry, pip, npm, yarn, direct."""

    available: bool
    """Whether this runner is available on the system."""

    version: Optional[str] = None
    """Runner version."""

    check_command: str = ""
    """Command to verify runner availability."""

    def __post_init__(self):
        """Validate runner config."""
        valid_runners = {"poetry", "pip", "npm", "yarn", "direct"}
        if self.name not in valid_runners:
            raise ValueError(
                f"Invalid runner: {self.name}. Must be one of: {valid_runners}"
            )


class ToolRegistry:
    """Registry for managing development tools and runners."""

    BUILTIN_TOOLS = {
        "black": ToolDefinition(
            name="black",
            tool_type="formatter",
            description="Python code formatter",
            languages=["python"],
            runners={
                "poetry": "poetry run black",
                "pip": "black",
                "direct": "black",
            },
            config_files=["pyproject.toml", ".black.toml"],
            priority=100,
            auto_fixable=True,
            fix_command_template="{runner} {paths}",
        ),
        "ruff": ToolDefinition(
            name="ruff",
            tool_type="linter",
            description="Fast Python linter",
            languages=["python"],
            runners={
                "poetry": "poetry run ruff check",
                "pip": "ruff check",
                "direct": "ruff check",
            },
            config_files=["pyproject.toml", "ruff.toml", ".ruff.toml"],
            priority=95,
            auto_fixable=True,
            fix_command_template="{runner} {paths} --fix",
        ),
        "mypy": ToolDefinition(
            name="mypy",
            tool_type="typecheck",
            description="Python static type checker",
            languages=["python"],
            runners={
                "poetry": "poetry run mypy",
                "pip": "mypy",
                "direct": "mypy",
            },
            config_files=["pyproject.toml", "mypy.ini", ".mypy.ini"],
            priority=90,
        ),
        "pytest": ToolDefinition(
            name="pytest",
            tool_type="test",
            description="Python testing framework",
            languages=["python"],
            runners={
                "poetry": "poetry run pytest",
                "pip": "pytest",
                "direct": "pytest",
            },
            config_files=["pyproject.toml", "pytest.ini", "setup.cfg"],
            priority=95,
        ),
        "eslint": ToolDefinition(
            name="eslint",
            tool_type="linter",
            description="JavaScript linter",
            languages=["javascript", "typescript"],
            runners={
                "npm": "npm run eslint",
                "yarn": "yarn eslint",
                "direct": "eslint",
            },
            config_files=[".eslintrc.json", ".eslintrc.js", "package.json"],
            priority=90,
            auto_fixable=True,
            fix_command_template="{runner} {paths} --fix",
        ),
        "prettier": ToolDefinition(
            name="prettier",
            tool_type="formatter",
            description="JavaScript/TypeScript formatter",
            languages=["javascript", "typescript"],
            runners={
                "npm": "npm run prettier",
                "yarn": "yarn prettier",
                "direct": "prettier",
            },
            config_files=[".prettierrc", ".prettierrc.json", "package.json"],
            priority=90,
            auto_fixable=True,
            fix_command_template="{runner} {paths} --write",
        ),
        "bandit": ToolDefinition(
            name="bandit",
            tool_type="security",
            description="Python security linter",
            languages=["python"],
            runners={
                "poetry": "poetry run bandit",
                "pip": "bandit",
                "direct": "bandit",
            },
            config_files=["pyproject.toml", ".bandit"],
            priority=80,
        ),
    }

    def __init__(self, registry_file: Optional[Path] = None):
        """Initialize tool registry.

        Args:
            registry_file: Path to custom tool registry file (YAML/JSON).
                          If not provided, uses built-in tools only.
        """
        self.registry_file = registry_file
        self.tools: Dict[str, ToolDefinition] = self.BUILTIN_TOOLS.copy()
        self.available_runners: Dict[str, ToolRunnerConfig] = {}

        if registry_file and registry_file.exists():
            self._load_custom_tools(registry_file)

        self._detect_available_runners()

    def _load_custom_tools(self, registry_file: Path) -> None:
        """Load custom tools from registry file.

        Args:
            registry_file: Path to registry file (JSON).

        Raises:
            ValueError: If registry file is invalid.
        """
        try:
            with open(registry_file) as f:
                data = json.load(f)

            if "tools" in data:
                for tool_data in data["tools"]:
                    tool = ToolDefinition(**tool_data)
                    self.tools[tool.name] = tool
                    logger.info(f"Loaded custom tool: {tool.name}")
        except Exception as e:
            logger.error(f"Failed to load custom tools from {registry_file}: {e}")
            raise ValueError(f"Invalid registry file: {e}") from e

    def _detect_available_runners(self) -> None:
        """Detect available runners on the system."""
        runner_checks = {
            "poetry": ("poetry", "--version"),
            "pip": ("pip", "--version"),
            "npm": ("npm", "--version"),
            "yarn": ("yarn", "--version"),
        }

        import subprocess

        for runner_name, cmd in runner_checks.items():
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split("\n")[0]
                    self.available_runners[runner_name] = ToolRunnerConfig(
                        name=runner_name,
                        available=True,
                        version=version,
                        check_command=" ".join(cmd),
                    )
                    logger.debug(f"Found {runner_name}: {version}")
            except Exception as e:
                logger.debug(f"{runner_name} not available: {e}")

        # Direct execution is always "available"
        self.available_runners["direct"] = ToolRunnerConfig(
            name="direct",
            available=True,
            check_command="direct tool execution",
        )

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name.

        Args:
            name: Tool name.

        Returns:
            Tool definition or None if not found.
        """
        return self.tools.get(name)

    def get_tools_by_type(self, tool_type: str) -> List[ToolDefinition]:
        """Get all tools of a specific type, sorted by priority.

        Args:
            tool_type: Tool type (formatter, linter, typecheck, test, security).

        Returns:
            List of tool definitions, sorted by priority (highest first).
        """
        tools = [t for t in self.tools.values() if t.tool_type == tool_type]
        return sorted(tools, key=lambda t: t.priority, reverse=True)

    def get_tools_by_language(self, language: str) -> List[ToolDefinition]:
        """Get all tools that support a specific language.

        Args:
            language: Programming language.

        Returns:
            List of tool definitions.
        """
        return [t for t in self.tools.values() if language in t.languages]

    def get_available_tools(self, tool_type: str) -> List[ToolDefinition]:
        """Get available tools of a type that have a runner available.

        Args:
            tool_type: Tool type.

        Returns:
            List of available tool definitions, sorted by priority.
        """
        tools = self.get_tools_by_type(tool_type)
        available = []

        for tool in tools:
            # Check if tool has a runner available
            for runner_name in tool.runners.keys():
                if runner_name in self.available_runners:
                    if self.available_runners[runner_name].available:
                        available.append(tool)
                        break

        return available

    def get_best_tool(self, tool_type: str) -> Optional[ToolDefinition]:
        """Get highest-priority available tool of a type.

        Args:
            tool_type: Tool type.

        Returns:
            Highest-priority available tool, or None if none available.
        """
        available = self.get_available_tools(tool_type)
        return available[0] if available else None

    def get_runner_command(self, tool: ToolDefinition) -> Optional[str]:
        """Get the command to run a tool using the best available runner.

        Args:
            tool: Tool definition.

        Returns:
            Runner command, or None if no runner available.
        """
        # Try runners in priority order (poetry, pip, npm, yarn, direct)
        runner_priority = ["poetry", "pip", "npm", "yarn", "direct"]

        for runner_name in runner_priority:
            if runner_name in tool.runners:
                if runner_name in self.available_runners:
                    if self.available_runners[runner_name].available:
                        return tool.runners[runner_name]

        return None

    def list_tools(self, by_type: bool = True) -> Dict[str, Any]:
        """List all registered tools.

        Args:
            by_type: If True, group by tool type. Otherwise, list all.

        Returns:
            Dictionary of tool information.
        """
        if by_type:
            result = {}
            for tool_type in {
                "formatter",
                "linter",
                "typecheck",
                "test",
                "security",
            }:
                tools = self.get_tools_by_type(tool_type)
                result[tool_type] = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "priority": t.priority,
                        "available": bool(
                            self.get_runner_command(t)
                        ),  # Check if tool can be run
                        "runners": list(t.runners.keys()),
                        "auto_fixable": t.auto_fixable,
                    }
                    for t in tools
                ]
            return result
        else:
            return {
                tool.name: {
                    "type": tool.tool_type,
                    "description": tool.description,
                    "priority": tool.priority,
                    "available": bool(self.get_runner_command(tool)),
                    "runners": list(tool.runners.keys()),
                    "auto_fixable": tool.auto_fixable,
                }
                for tool in self.tools.values()
            }
