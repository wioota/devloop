"""
Tool Runner - Execute tools from the tool registry with error handling.
"""

import logging
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from devloop.core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class ToolRunResult:
    """Result of running a tool."""

    tool_name: str
    """Name of the tool that was run."""

    success: bool
    """Whether the tool ran successfully."""

    exit_code: int
    """Exit code from the tool."""

    stdout: str
    """Standard output."""

    stderr: str
    """Standard error."""

    command: str
    """The command that was executed."""

    error_message: Optional[str] = None
    """Error message if tool failed."""


class ToolRunner:
    """Execute tools from the registry."""

    def __init__(self, registry: ToolRegistry, cwd: Optional[Path] = None):
        """Initialize tool runner.

        Args:
            registry: Tool registry instance.
            cwd: Working directory for tool execution (default: current directory).
        """
        self.registry = registry
        self.cwd = cwd or Path.cwd()

    def run_tool(
        self,
        tool_name: str,
        paths: Optional[List[str]] = None,
        check: bool = True,
    ) -> ToolRunResult:
        """Run a tool from the registry.

        Args:
            tool_name: Name of tool to run.
            paths: File/directory paths to pass to tool (default: None).
            check: If True, raise on non-zero exit. Otherwise, return result.

        Returns:
            ToolRunResult with execution details.

        Raises:
            ValueError: If tool not found or not available.
            subprocess.CalledProcessError: If check=True and tool fails.
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        runner_cmd = self.registry.get_runner_command(tool)
        if not runner_cmd:
            raise ValueError(
                f"No available runner for tool: {tool_name}. "
                f"Tool requires one of: {list(tool.runners.keys())}"
            )

        # Build command
        cmd = [runner_cmd]
        if paths:
            cmd.extend(paths)

        logger.info(f"Running {tool_name}: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.cwd),
                capture_output=True,
                text=True,
                check=False,
            )

            tool_result = ToolRunResult(
                tool_name=tool_name,
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                command=" ".join(cmd),
                error_message=None if result.returncode == 0 else result.stderr,
            )

            if check and result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    cmd,
                    output=result.stdout,
                    stderr=result.stderr,
                )

            return tool_result

        except subprocess.TimeoutExpired as e:
            return ToolRunResult(
                tool_name=tool_name,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                command=" ".join(cmd),
                error_message=f"Tool execution timed out: {e}",
            )
        except Exception as e:
            return ToolRunResult(
                tool_name=tool_name,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                command=" ".join(cmd),
                error_message=f"Failed to run tool: {e}",
            )

    def run_tool_type(
        self,
        tool_type: str,
        paths: Optional[List[str]] = None,
        stop_on_first_failure: bool = True,
    ) -> List[ToolRunResult]:
        """Run all available tools of a specific type.

        Args:
            tool_type: Tool type (formatter, linter, typecheck, test, security).
            paths: File/directory paths to pass to tools.
            stop_on_first_failure: If True, stop on first failure. Otherwise, run all.

        Returns:
            List of ToolRunResult for each tool executed.
        """
        available_tools = self.registry.get_available_tools(tool_type)
        if not available_tools:
            logger.warning(f"No available tools for type: {tool_type}")
            return []

        results = []
        for tool in available_tools:
            try:
                result = self.run_tool(tool.name, paths, check=False)
                results.append(result)

                if not result.success and stop_on_first_failure:
                    logger.warning(f"Tool {tool.name} failed, stopping")
                    break

            except Exception as e:
                logger.error(f"Error running {tool.name}: {e}")
                results.append(
                    ToolRunResult(
                        tool_name=tool.name,
                        success=False,
                        exit_code=-1,
                        stdout="",
                        stderr="",
                        command="",
                        error_message=str(e),
                    )
                )

                if stop_on_first_failure:
                    break

        return results

    def run_best_tool(
        self,
        tool_type: str,
        paths: Optional[List[str]] = None,
    ) -> Optional[ToolRunResult]:
        """Run the highest-priority available tool of a type.

        Args:
            tool_type: Tool type.
            paths: File/directory paths to pass to tool.

        Returns:
            ToolRunResult, or None if no tools available.
        """
        best_tool = self.registry.get_best_tool(tool_type)
        if not best_tool:
            logger.warning(f"No available tools for type: {tool_type}")
            return None

        return self.run_tool(best_tool.name, paths, check=False)

    def can_auto_fix(self, tool_name: str) -> bool:
        """Check if a tool can automatically fix issues.

        Args:
            tool_name: Name of tool.

        Returns:
            True if tool is auto-fixable and available.
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return False
        if not tool.auto_fixable:
            return False
        runner_cmd = self.registry.get_runner_command(tool)
        return runner_cmd is not None

    def auto_fix(
        self,
        tool_name: str,
        paths: Optional[List[str]] = None,
    ) -> ToolRunResult:
        """Automatically fix issues found by a tool.

        Args:
            tool_name: Name of tool.
            paths: File/directory paths to fix.

        Returns:
            ToolRunResult from the auto-fix command.

        Raises:
            ValueError: If tool not found, not available, or not auto-fixable.
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        if not tool.auto_fixable:
            raise ValueError(f"Tool is not auto-fixable: {tool_name}")

        if not tool.fix_command_template:
            raise ValueError(f"No fix command template for: {tool_name}")

        runner_cmd = self.registry.get_runner_command(tool)
        if not runner_cmd:
            raise ValueError(f"No available runner for: {tool_name}")

        # Build fix command from template
        fix_cmd = tool.fix_command_template.format(
            runner=runner_cmd,
            name=tool_name,
            paths=" ".join(paths) if paths else ".",
        )

        logger.info(f"Running auto-fix for {tool_name}: {fix_cmd}")

        try:
            result = subprocess.run(
                shlex.split(fix_cmd),
                cwd=str(self.cwd),
                capture_output=True,
                text=True,
                check=False,
            )

            return ToolRunResult(
                tool_name=tool_name,
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                command=fix_cmd,
                error_message=None if result.returncode == 0 else result.stderr,
            )

        except Exception as e:
            return ToolRunResult(
                tool_name=tool_name,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                command=fix_cmd,
                error_message=f"Failed to run auto-fix: {e}",
            )
