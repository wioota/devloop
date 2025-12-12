"""Tool dependency management and version verification.

Provides:
- Tool availability detection
- Version checking and compatibility validation
- Graceful fallbacks for missing tools
- Startup health checks
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class ToolInfo:
    """Information about an external tool dependency."""

    name: str
    description: str
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    install_url: str = ""
    critical: bool = False
    command: Optional[str] = None  # Override command to check (e.g., "python -m ruff")
    version_flag: str = "--version"  # Flag to get version

    def __post_init__(self):
        if self.command is None:
            self.command = self.name


class ToolDependencyManager:
    """Manages external tool dependencies for DevLoop."""

    # Core Python-based tools (provided by dev dependencies)
    PYTHON_TOOLS = {
        "ruff": ToolInfo(
            name="ruff",
            description="Fast Python linter",
            min_version="0.1.0",
            critical=True,
            command="python -m ruff",
        ),
        "black": ToolInfo(
            name="black",
            description="Python code formatter",
            min_version="23.0.0",
            critical=True,
            command="python -m black",
        ),
        "mypy": ToolInfo(
            name="mypy",
            description="Static type checker for Python",
            min_version="1.0.0",
            critical=True,
            command="python -m mypy",
        ),
        "pytest": ToolInfo(
            name="pytest",
            description="Python test framework",
            min_version="7.0.0",
            critical=True,
            command="python -m pytest",
        ),
        "bandit": ToolInfo(
            name="bandit",
            description="Security issue scanner for Python",
            min_version="1.7.0",
            critical=False,
            command="python -m bandit",
        ),
    }

    # External CLI tools (optional)
    EXTERNAL_TOOLS = {
        "gh": ToolInfo(
            name="gh",
            description="GitHub CLI for repository operations",
            min_version="2.0.0",
            install_url="https://cli.github.com",
            critical=False,
        ),
        "git": ToolInfo(
            name="git",
            description="Version control system",
            min_version="2.20.0",
            install_url="https://git-scm.com",
            critical=True,
        ),
        "python": ToolInfo(
            name="python",
            description="Python interpreter",
            min_version="3.11.0",
            install_url="https://python.org",
            critical=True,
        ),
        "poetry": ToolInfo(
            name="poetry",
            description="Python dependency manager",
            min_version="1.2.0",
            install_url="https://python-poetry.org",
            critical=False,
        ),
    }

    # Optional security/analysis tools
    OPTIONAL_TOOLS = {
        "snyk": ToolInfo(
            name="snyk",
            description="Vulnerability scanner",
            install_url="https://snyk.io",
        ),
        "eslint": ToolInfo(
            name="eslint",
            description="JavaScript linter",
            install_url="https://eslint.org",
        ),
        "prettier": ToolInfo(
            name="prettier",
            description="Code formatter for JavaScript/TypeScript",
            install_url="https://prettier.io",
        ),
    }

    @staticmethod
    def check_tool_available(tool_name: str, command: Optional[str] = None) -> bool:
        """Check if a tool is available in PATH."""
        cmd = command or tool_name
        # For compound commands (e.g., "python -m mypy"), check first part
        tool = cmd.split()[0]
        return shutil.which(tool) is not None

    @staticmethod
    def get_tool_version(
        tool_name: str, command: Optional[str] = None
    ) -> Optional[str]:
        """Get version of an installed tool."""
        try:
            cmd = command or tool_name
            result = subprocess.run(
                f"{cmd} --version",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return None

            # Extract version from output (handles various formats)
            output = result.stdout + result.stderr
            match = re.search(r"(\d+\.\d+\.\d+|\d+\.\d+)", output)
            return match.group(1) if match else None
        except (subprocess.TimeoutExpired, Exception):
            return None

    @staticmethod
    def parse_version(version_str: Optional[str]) -> Tuple[int, ...]:
        """Parse version string into tuple for comparison."""
        if not version_str:
            return (0, 0, 0)
        parts = version_str.split(".")
        try:
            return tuple(int(p) for p in parts[:3])
        except ValueError:
            return (0, 0, 0)

    @classmethod
    def check_version_compatibility(
        cls,
        tool_name: str,
        min_version: Optional[str] = None,
        max_version: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Check if tool version meets requirements.

        Returns:
            Tuple of (compatible, installed_version)
        """
        tool = cls._get_tool_info(tool_name)
        if not tool:
            return False, None

        installed = cls.get_tool_version(tool_name, tool.command)
        if not installed:
            return False, None

        min_v = min_version or tool.min_version
        max_v = max_version or tool.max_version

        installed_tuple = cls.parse_version(installed)
        min_tuple = cls.parse_version(min_v)
        max_tuple = cls.parse_version(max_v)

        if installed_tuple < min_tuple:
            return False, installed

        if max_v and installed_tuple > max_tuple:
            return False, installed

        return True, installed

    @classmethod
    def _get_tool_info(cls, tool_name: str) -> Optional[ToolInfo]:
        """Get tool info from any category."""
        for tool in [cls.PYTHON_TOOLS, cls.EXTERNAL_TOOLS, cls.OPTIONAL_TOOLS]:
            if tool_name in tool:
                return tool[tool_name]
        return None

    @classmethod
    def check_all_tools(cls) -> Dict[str, Dict[str, Any]]:
        """Check all tools and return status."""
        results = {}

        for category, tools in [
            ("python", cls.PYTHON_TOOLS),
            ("external", cls.EXTERNAL_TOOLS),
            ("optional", cls.OPTIONAL_TOOLS),
        ]:
            for tool_name, tool_info in tools.items():
                available = cls.check_tool_available(tool_info.name, tool_info.command)
                version = None
                compatible = False

                if available:
                    version = cls.get_tool_version(tool_info.name, tool_info.command)
                    compatible, _ = cls.check_version_compatibility(tool_name)

                results[tool_name] = {
                    "available": available,
                    "version": version,
                    "compatible": compatible,
                    "description": tool_info.description,
                    "critical": tool_info.critical,
                    "category": category,
                }

        return results

    @classmethod
    def startup_check(cls, fail_on_missing_critical: bool = False) -> bool:
        """Perform startup health check of all tools.

        Returns:
            True if all critical tools available, False otherwise
        """
        results = cls.check_all_tools()
        critical_failures = [
            name
            for name, info in results.items()
            if info["critical"] and not info["available"]
        ]

        if critical_failures:
            console.print(
                "[red]✗ Critical tools missing:[/red] " + ", ".join(critical_failures)
            )
            if fail_on_missing_critical:
                return False

            console.print(
                "[yellow]Warning: Some critical tools are missing. "
                "Install with:[/yellow]"
            )
            for tool in critical_failures:
                info = cls._get_tool_info(tool)
                if info:
                    console.print(f"  {info.install_url}")

        return not fail_on_missing_critical

    @classmethod
    def show_compatibility_matrix(cls):
        """Display tool compatibility matrix."""
        results = cls.check_all_tools()

        table = Table(title="Tool Dependency Status")
        table.add_column("Tool", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Version", style="green")
        table.add_column("Min Required", style="yellow")
        table.add_column("Critical", style="red")

        for tool_name, info in sorted(results.items()):
            tool = cls._get_tool_info(tool_name)
            status = "✓" if info["compatible"] else ("⚠" if info["available"] else "✗")
            version = info["version"] or "—"
            min_req = tool.min_version if tool else "—"
            critical = "Yes" if info["critical"] else "No"

            table.add_row(tool_name, status, version, min_req, critical)

        console.print(table)

    @classmethod
    def save_compatibility_report(cls, path: Path) -> None:
        """Save compatibility report to JSON file."""
        results = cls.check_all_tools()
        report = {
            "timestamp": Path(".").resolve(),
            "tools": results,
            "summary": {
                "critical_ok": sum(
                    1
                    for info in results.values()
                    if info["critical"] and info["available"]
                ),
                "optional_ok": sum(
                    1
                    for info in results.values()
                    if not info["critical"] and info["available"]
                ),
            },
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2))
        console.print(f"[green]✓[/green] Report saved to {path}")
