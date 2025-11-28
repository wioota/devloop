#!/usr/bin/env python3
"""Performance Profiler Agent - Analyzes code complexity and performance."""

import asyncio
import json
import subprocess  # nosec B404 - Required for running performance analysis tools
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..core.agent import Agent, AgentResult
from ..core.context_store import context_store
from ..core.event import Event


@dataclass
class PerformanceConfig:
    """Configuration for performance profiling."""

    complexity_threshold: int = 10  # McCabe complexity threshold
    min_lines_threshold: int = 50  # Minimum lines to analyze
    enabled_tools: List[str] = None  # ["radon", "flake8-complexity"]
    exclude_patterns: List[str] = None
    max_issues: int = 50

    def __post_init__(self):
        if self.enabled_tools is None:
            self.enabled_tools = ["radon"]
        if self.exclude_patterns is None:
            self.exclude_patterns = ["test*", "*_test.py", "*/tests/*", "__init__.py"]


class PerformanceResult:
    """Performance analysis result."""

    def __init__(
        self, tool: str, metrics: List[Dict[str, Any]], errors: List[str] = None
    ):
        self.tool = tool
        self.metrics = metrics
        self.errors = errors or []
        self.timestamp = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "functions_analyzed": len(self.metrics),
            "metrics": self.metrics,
            "errors": self.errors,
            "complexity_summary": self._get_complexity_summary(),
            "high_complexity_functions": self._get_high_complexity_functions(),
        }

    def _get_complexity_summary(self) -> Dict[str, Any]:
        if not self.metrics:
            return {
                "average_complexity": 0,
                "max_complexity": 0,
                "high_complexity_count": 0,
            }

        complexities = [m.get("complexity", 0) for m in self.metrics]
        high_complexity = [c for c in complexities if c >= 10]

        return {
            "average_complexity": round(sum(complexities) / len(complexities), 1),
            "max_complexity": max(complexities),
            "high_complexity_count": len(high_complexity),
            "total_functions": len(self.metrics),
        }

    def _get_high_complexity_functions(self) -> List[Dict[str, Any]]:
        """Get functions with high complexity."""
        return [m for m in self.metrics if m.get("complexity", 0) >= 10]


class PerformanceProfilerAgent(Agent):
    """Agent for analyzing code performance and complexity."""

    def __init__(self, config: Dict[str, Any], event_bus):
        super().__init__(
            "performance-profiler", ["file:modified", "file:created"], event_bus
        )
        self.config = PerformanceConfig(**config)

    async def handle(self, event: Event) -> AgentResult:
        """Handle file change events by analyzing performance."""

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

        # Only analyze Python files
        if path.suffix != ".py":
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.0,
                message=f"Skipped non-Python file: {file_path}",
            )

        # Check if file is large enough to analyze
        if not self._should_analyze_file(path):
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.0,
                message=f"File too small to analyze: {file_path}",
            )

        # Check if file matches exclude patterns
        if self._should_exclude_file(str(path)):
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.0,
                message=f"Excluded file: {file_path}",
            )

        # Run performance analysis
        results = await self._run_performance_analysis(path)

        summary = results._get_complexity_summary()
        high_complexity = results._get_high_complexity_functions()

        agent_result = AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.0,  # Would be calculated in real implementation
            message=f"Analyzed {path} with {results.tool}",
            data={
                "file": str(path),
                "tool": results.tool,
                "functions_analyzed": len(results.metrics),
                "metrics": results.metrics,
                "complexity_summary": summary,
                "high_complexity_functions": high_complexity,
                "errors": results.errors,
            },
        )

        # Write to context store for Claude Code integration
        context_store.write_finding(agent_result)

        return agent_result

    def _should_analyze_file(self, file_path: Path) -> bool:
        """Check if file is large enough to analyze."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return len(lines) >= self.config.min_lines_threshold
        except Exception:
            return False

    def _should_exclude_file(self, file_path: str) -> bool:
        """Check if file should be excluded from analysis."""
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

    async def _run_performance_analysis(self, file_path: Path) -> PerformanceResult:
        """Run performance analysis tools."""
        results = []

        # Try radon first (good for complexity analysis)
        if "radon" in self.config.enabled_tools:
            radon_result = await self._run_radon(file_path)
            if radon_result:
                results.append(radon_result)

        # If no results from primary tools, return empty
        if results:
            return results[0]  # Return first successful result

        return PerformanceResult(
            "none", [], ["No performance analysis tools available"]
        )

    async def _run_radon(self, file_path: Path) -> Optional[PerformanceResult]:
        """Run Radon complexity analysis."""
        try:
            # Check if radon is available
            result = subprocess.run(
            [sys.executable, "-c", "import radon"], capture_output=True, text=True
            )  # nosec B603 - Running trusted system Python with safe arguments
            if result.returncode != 0:
                return PerformanceResult(
                    "radon", [], ["Radon not installed - run: pip install radon"]
                )

            # Run radon cc (complexity) command
            cmd = [
                sys.executable,
                "-m",
                "radon",
                "cc",
                "-j",  # JSON output
                str(file_path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=file_path.parent,
            )

            stdout, stderr = await process.communicate()

            metrics = []

            if process.returncode == 0:
                try:
                    data = json.loads(stdout.decode())

                    # Parse radon output
                    for file_name, file_data in data.items():
                        for function_data in file_data:
                            metrics.append(
                                {
                                    "name": function_data.get("name", ""),
                                    "type": function_data.get("type", ""),
                                    "complexity": function_data.get("complexity", 0),
                                    "line_number": function_data.get("lineno", 0),
                                    "end_line": function_data.get("endline", 0),
                                    "rank": function_data.get("rank", ""),
                                    "file": file_name,
                                }
                            )

                    return PerformanceResult("radon", metrics[: self.config.max_issues])

                except json.JSONDecodeError:
                    return PerformanceResult(
                        "radon",
                        [],
                        [f"Failed to parse radon output: {stdout.decode()[:200]}"],
                    )

            else:
                error_msg = stderr.decode().strip()
                return PerformanceResult("radon", [], [f"Radon failed: {error_msg}"])

        except Exception as e:
            return PerformanceResult("radon", [], [f"Radon execution error: {str(e)}"])
