"""MCP tool implementations for DevLoop.

Provides tools for code verification, formatting, linting, type checking,
and testing that can be invoked by MCP clients.
"""

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ToolResult:
    """Result from running a verification tool."""

    success: bool
    output: str
    return_code: int
    command: str


async def run_subprocess(
    args: list[str],
    cwd: Path,
    timeout: int = 60,
) -> ToolResult:
    """Run a subprocess asynchronously with timeout.

    Args:
        args: Command and arguments to run.
        cwd: Working directory for the command.
        timeout: Timeout in seconds (default 60).

    Returns:
        ToolResult with success status, output, and return code.
    """
    command_str = " ".join(args)
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
        output = stdout.decode("utf-8", errors="replace")
        return_code = process.returncode or 0
        return ToolResult(
            success=return_code == 0,
            output=output,
            return_code=return_code,
            command=command_str,
        )
    except asyncio.TimeoutError:
        if process:
            process.kill()
        return ToolResult(
            success=False,
            output=f"Command timed out after {timeout} seconds",
            return_code=-1,
            command=command_str,
        )
    except FileNotFoundError:
        return ToolResult(
            success=False,
            output=f"Command not found: {args[0]}",
            return_code=-1,
            command=command_str,
        )
    except Exception as e:
        return ToolResult(
            success=False,
            output=f"Error running command: {e}",
            return_code=-1,
            command=command_str,
        )


async def run_formatter(
    project_root: Path,
    paths: Optional[list[str]] = None,
    check_only: bool = False,
    timeout: int = 60,
) -> ToolResult:
    """Run the black formatter on specified files or project.

    Args:
        project_root: Root directory of the project.
        paths: Specific paths to format. Defaults to ["src/", "tests/"].
        check_only: If True, only check formatting without modifying files.
        timeout: Timeout in seconds.

    Returns:
        ToolResult with formatting status and output.
    """
    if paths is None:
        paths = ["src/", "tests/"]

    args = ["poetry", "run", "black"]
    if check_only:
        args.append("--check")
    args.extend(paths)

    return await run_subprocess(args, project_root, timeout)


async def run_linter(
    project_root: Path,
    paths: Optional[list[str]] = None,
    fix: bool = False,
    timeout: int = 60,
) -> ToolResult:
    """Run the ruff linter on specified files or project.

    Args:
        project_root: Root directory of the project.
        paths: Specific paths to lint. Defaults to ["src/", "tests/"].
        fix: If True, automatically fix fixable issues.
        timeout: Timeout in seconds.

    Returns:
        ToolResult with linting status and output.
    """
    if paths is None:
        paths = ["src/", "tests/"]

    args = ["poetry", "run", "ruff", "check"]
    if fix:
        args.append("--fix")
    args.extend(paths)

    return await run_subprocess(args, project_root, timeout)


async def run_type_checker(
    project_root: Path,
    paths: Optional[list[str]] = None,
    timeout: int = 120,
) -> ToolResult:
    """Run mypy type checker on specified files or project.

    Args:
        project_root: Root directory of the project.
        paths: Specific paths to check. Defaults to ["src/"].
        timeout: Timeout in seconds (default 120 for large projects).

    Returns:
        ToolResult with type checking status and output.
    """
    if paths is None:
        paths = ["src/"]

    args = ["poetry", "run", "mypy"]
    args.extend(paths)

    return await run_subprocess(args, project_root, timeout)


async def run_tests(
    project_root: Path,
    paths: Optional[list[str]] = None,
    markers: Optional[list[str]] = None,
    keyword: Optional[str] = None,
    verbose: bool = False,
    timeout: int = 300,
) -> ToolResult:
    """Run pytest on specified files or project.

    Args:
        project_root: Root directory of the project.
        paths: Specific test paths to run. Defaults to running all tests.
        markers: Pytest markers to filter tests (e.g., ["unit", "not slow"]).
        keyword: Keyword expression to filter tests.
        verbose: If True, run with verbose output.
        timeout: Timeout in seconds (default 300 for test suites).

    Returns:
        ToolResult with test status and output.
    """
    args = ["poetry", "run", "pytest", "--no-cov"]

    if verbose:
        args.append("-v")

    if markers:
        for marker in markers:
            args.extend(["-m", marker])

    if keyword:
        args.extend(["-k", keyword])

    if paths:
        args.extend(paths)

    return await run_subprocess(args, project_root, timeout)
