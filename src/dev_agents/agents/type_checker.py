#!/usr/bin/env python3
"""Type Checker Agent - Runs static type checking on code."""

import logging
import subprocess  # nosec B404 - Required for running type checking tools
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..core.agent import Agent, AgentResult
from ..core.event import Event


@dataclass
class TypeCheckerConfig:
    """Configuration for type checking."""

    enabled_tools: List[str] = None  # ["mypy", "pyright", "pyre"]
    strict_mode: bool = False
    show_error_codes: bool = True
    exclude_patterns: List[str] = None
    max_issues: int = 50

    def __post_init__(self):
        if self.enabled_tools is None:
            self.enabled_tools = ["mypy"]
        if self.exclude_patterns is None:
            self.exclude_patterns = ["test*", "*_test.py", "*/tests/*"]


class TypeCheckResult:
    """Type check result."""

    def __init__(
        self, tool: str, issues: List[Dict[str, Any]], errors: List[str] = None
    ):
        self.tool = tool
        self.issues = issues
        self.errors = errors or []
        self.timestamp = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "issues_found": len(self.issues),
            "issues": self.issues,
            "errors": self.errors,
            "severity_breakdown": self._get_severity_breakdown(),
            "summary": f"Found {len(self.issues)} type issues",
        }

    def _get_severity_breakdown(self) -> Dict[str, int]:
        breakdown = {"error": 0, "warning": 0, "note": 0, "unknown": 0}
        for issue in self.issues:
            severity = issue.get("severity", "unknown").lower()
            breakdown[severity] = breakdown.get(severity, 0) + 1
        return breakdown


class TypeCheckerAgent(Agent):
    """Agent for running type checkers on code."""

    def __init__(self, config: Dict[str, Any], event_bus):
        super().__init__("type-checker", ["file:modified", "file:created"], event_bus)
        self.config = TypeCheckerConfig(**config)
        self.logger = logging.getLogger(f"agent.{self.name}")

    async def handle(self, event: Event) -> AgentResult:
        """Handle file change events by running type checks."""
        try:
            file_path = event.payload.get("path")
            if not file_path:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    duration=0.0,
                    message="No file path in event",
                )

            path = Path(file_path)
            if not path.exists():
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    duration=0.0,
                    message=f"File does not exist: {file_path}",
                )

            # Only check Python files for now
            if path.suffix != ".py":
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0.0,
                    message=f"Skipped non-Python file: {file_path}",
                )

            # Check if file matches exclude patterns
            if self._should_exclude_file(str(path)):
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0.0,
                    message=f"Excluded file: {file_path}",
                )

            # Run type check
            results = await self._run_type_check(path)

            agent_result = AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.0,  # Would be calculated in real implementation
                message=f"Type checked {file_path} with {results.tool}",
                data={
                    "file": str(path),
                    "tool": results.tool,
                    "issues_found": len(results.issues),
                    "issues": results.issues,
                    "severity_breakdown": results._get_severity_breakdown(),
                    "errors": results.errors,
                },
            )

            return agent_result
        except Exception as e:
            self.logger.error(
                f"Error handling type check for {event.payload.get('path', 'unknown')}: {e}",
                exc_info=True,
            )
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message=f"Type check failed: {str(e)}",
                error=str(e),
            )

    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from type checking."""
        if not self.config.exclude_patterns:
            return False
        for pattern in self.config.exclude_patterns:
            if pattern.startswith("*") and pattern.endswith("*"):
                if pattern[1:-1] in file_path:
                    return True
            elif pattern.startswith("*"):
                if file_path.endswith(pattern[1:]):
                    return True
            elif pattern.endswith("*"):
                if file_path.startswith(pattern[:-1]):
                    return True
            elif pattern == file_path:
                return True
        return False

    async def _run_type_check(self, file_path: Path) -> TypeCheckResult:
        """Run type checking tools."""
        results = []

        # Try mypy first (most common Python type checker)
        if "mypy" in self.config.enabled_tools:
            mypy_result = self._run_mypy(file_path)
            if mypy_result:
                results.append(mypy_result)

        # If no results from primary tools, return empty
        if results:
            return results[0]  # Return first successful result

        return TypeCheckResult("none", [], ["No type checking tools available"])

    def _run_mypy(self, file_path: Path) -> Optional[TypeCheckResult]:
        """Run MyPy type checker."""
        try:
            # Check if mypy is available
            result = subprocess.run(
            [sys.executable, "-c", "import mypy"], capture_output=True, text=True
            )  # nosec B603 - Running trusted system Python with safe arguments
            if result.returncode != 0:
                return TypeCheckResult(
                    "mypy", [], ["MyPy not installed - run: pip install mypy"]
                )

            cmd = [
                sys.executable,
                "-m",
                "mypy",
                str(file_path),
                "--show-error-codes",
                "--no-error-summary",
            ]

            if self.config.strict_mode:
                cmd.append("--strict")

            # Run mypy in subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=file_path.parent,
            )  # nosec B603 - Running mypy with controlled command arguments
            issues = []

            # Parse mypy output (line by line)
            output_lines = result.stdout.strip().split("\n")
            for line in output_lines:
                if line.strip() and not line.startswith("Success:"):
                    # Parse mypy error format: file:line: error: message [error-code]
                    parts = line.split(":", 3)
                    if len(parts) >= 4:
                        filename = parts[0].strip()
                        try:
                            line_number = int(parts[1].strip())
                        except ValueError:
                            line_number = 0

                        error_type = parts[2].strip()
                        message_and_code = parts[3].strip()

                        # Extract error code if present
                        error_code = ""
                        if "[" in message_and_code and "]" in message_and_code:
                            message, code_part = message_and_code.rsplit("[", 1)
                            error_code = code_part.rstrip("]")
                            message = message.strip()
                        else:
                            message = message_and_code

                        issues.append(
                            {
                                "filename": filename,
                                "line_number": line_number,
                                "severity": error_type,
                                "message": message,
                                "error_code": error_code,
                                "tool": "mypy",
                            }
                        )

            return TypeCheckResult("mypy", issues[: self.config.max_issues])

        except Exception as e:
            return TypeCheckResult("mypy", [], [f"MyPy execution error: {str(e)}"])
