"""Prerequisite validation for DevLoop installation."""

import shutil
from typing import Any, Dict, List, Tuple

from rich.console import Console

console = Console()


class PrerequisiteChecker:
    """Validates that required tools are available for DevLoop features."""

    # Required tools for core functionality
    REQUIRED_TOOLS = {
        "gh": {
            "description": "GitHub CLI (for CI/CD integration)",
            "install_url": "https://cli.github.com",
            "critical": False,  # Pre-push hook can work without it
        },
        "bd": {
            "description": "Beads (for task management integration)",
            "install_url": "https://github.com/wioota/devloop",
            "critical": False,  # Pre-commit hook can work without it
        },
    }

    # Optional tools (agents can degrade if missing)
    OPTIONAL_TOOLS = {
        "snyk": {
            "description": "Snyk CLI (for security scanning)",
            "install_url": "https://snyk.io/download/",
        },
        "poetry": {
            "description": "Poetry (for dependency management)",
            "install_url": "https://python-poetry.org/docs/#installation",
        },
    }

    @staticmethod
    def check_tool_available(tool_name: str) -> bool:
        """Check if a tool is available in PATH."""
        return shutil.which(tool_name) is not None

    @classmethod
    def check_prerequisites(cls) -> Dict[str, bool]:
        """Check all prerequisites and return availability status.

        Returns:
            Dict mapping tool name to availability (True if available)
        """
        results = {}
        for tool_name in cls.REQUIRED_TOOLS:
            results[tool_name] = cls.check_tool_available(tool_name)
        return results

    @classmethod
    def check_optional_prerequisites(cls) -> Dict[str, bool]:
        """Check optional tools availability."""
        results = {}
        for tool_name in cls.OPTIONAL_TOOLS:
            results[tool_name] = cls.check_tool_available(tool_name)
        return results

    @classmethod
    def validate_for_git_hooks(cls, interactive: bool = True) -> Tuple[bool, List[str]]:
        """Validate prerequisites for git hook installation.

        Returns:
            Tuple of (all_available, missing_tools)
        """
        required = cls.check_prerequisites()
        missing = [tool for tool, available in required.items() if not available]

        if missing:
            if interactive:
                cls._show_missing_tools_warning(missing)
            return False, missing

        return True, []

    @classmethod
    def _show_missing_tools_warning(cls, missing_tools: List[str]) -> None:
        """Display warning about missing tools with installation instructions."""
        console.print(
            "\n[yellow]⚠️  Missing required tools for pre-push CI verification[/yellow]\n"
        )

        for tool in missing_tools:
            info = cls.REQUIRED_TOOLS.get(tool, {})
            console.print(f"  [red]✗[/red] {tool}: {info.get('description', tool)}")
            console.print(
                f"    Install: {info.get('install_url', 'See documentation')}\n"
            )

        console.print(
            "[cyan]Note:[/cyan] DevLoop will work without these tools, but pre-push CI "
            "verification will be unavailable."
        )
        console.print(
            "      You can install them later and they'll be detected automatically.\n"
        )

    @classmethod
    def get_installation_instructions(cls, tool_name: str) -> str:
        """Get installation instructions for a specific tool."""
        tools: Dict[str, Dict[str, Any]] = {**cls.REQUIRED_TOOLS, **cls.OPTIONAL_TOOLS}
        if tool_name not in tools:
            return f"See documentation for {tool_name}"

        info = tools[tool_name]
        if tool_name == "gh":
            return f"""
# Install GitHub CLI
# See: {info["install_url"]}

# Ubuntu/Debian:
sudo apt-get install -y gh

# macOS:
brew install gh
"""
        elif tool_name == "bd":
            return f"""
# Install Beads (bd)
# See: {info["install_url"]}

pip install beads-mcp
"""

        return f"Visit: {info['install_url']}"

    @classmethod
    def show_installation_guide(cls, missing_tools: List[str]) -> None:
        """Display installation guide for missing tools."""
        console.print("\n[cyan]Installation Guide[/cyan]\n")

        for tool in missing_tools:
            console.print(f"[yellow]{tool}:[/yellow]")
            console.print(cls.get_installation_instructions(tool))
            console.print()


def validate_prerequisites(interactive: bool = True) -> bool:
    """Main entry point for prerequisite validation.

    Args:
        interactive: If True, show warnings and installation guides

    Returns:
        True if all prerequisites met, False otherwise
    """
    checker = PrerequisiteChecker()
    all_available, missing = checker.validate_for_git_hooks(interactive=interactive)

    return all_available
