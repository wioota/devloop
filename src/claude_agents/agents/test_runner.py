"""Test runner agent - runs tests on file changes."""
import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from claude_agents.core.agent import Agent, AgentResult
from claude_agents.core.event import Event


class TestRunnerConfig:
    """Configuration for TestRunnerAgent."""

    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get("enabled", True)
        self.run_on_save = config.get("runOnSave", True)
        self.related_tests_only = config.get("relatedTestsOnly", True)
        self.test_frameworks = config.get("testFrameworks", {
            "python": "pytest",
            "javascript": "jest",
            "typescript": "jest"
        })
        self.test_patterns = config.get("testPatterns", {
            "python": ["**/test_*.py", "**/*_test.py"],
            "javascript": ["**/*.test.js", "**/*.spec.js"],
            "typescript": ["**/*.test.ts", "**/*.spec.ts"]
        })


class TestResult:
    """Result from running tests."""

    def __init__(
        self,
        success: bool,
        passed: int = 0,
        failed: int = 0,
        skipped: int = 0,
        duration: float = 0.0,
        failures: List[Dict[str, Any]] | None = None,
        error: str | None = None
    ):
        self.success = success
        self.passed = passed
        self.failed = failed
        self.skipped = skipped
        self.duration = duration
        self.failures = failures or []
        self.error = error

    @property
    def total(self) -> int:
        """Total tests run."""
        return self.passed + self.failed + self.skipped

    @property
    def all_passed(self) -> bool:
        """Check if all tests passed."""
        return self.failed == 0 and self.passed > 0


class TestRunnerAgent(Agent):
    """Agent that runs tests when files change."""

    def __init__(
        self,
        name: str,
        triggers: List[str],
        event_bus,
        config: Dict[str, Any] | None = None
    ):
        super().__init__(name, triggers, event_bus)
        self.config = TestRunnerConfig(config or {})

    async def handle(self, event: Event) -> AgentResult:
        """Handle file change event by running tests."""
        if not self.config.run_on_save:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="Run on save disabled"
            )

        # Extract file path
        file_path = event.payload.get("path")
        if not file_path:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="No file path in event"
            )

        path = Path(file_path)

        # Determine if this is a test file or source file
        is_test_file = self._is_test_file(path)

        # Get test framework
        framework = self._get_test_framework(path)
        if not framework:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"No test framework configured for {path.suffix}"
            )

        # Determine which tests to run
        if is_test_file:
            # Run this specific test file
            test_files = [path]
        elif self.config.related_tests_only:
            # Find related test files
            test_files = self._find_related_tests(path)
            if not test_files:
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0,
                    message=f"No tests found for {path.name}"
                )
        else:
            # Run all tests
            test_files = []

        # Run tests
        result = await self._run_tests(framework, test_files, path)

        # Build result message
        if result.error:
            message = f"Test error: {result.error}"
            success = False
        elif result.all_passed:
            message = f"✓ {result.passed} test(s) passed"
            success = True
        elif result.failed > 0:
            message = f"✗ {result.failed} test(s) failed, {result.passed} passed"
            success = False
        else:
            message = "No tests run"
            success = True

        return AgentResult(
            agent_name=self.name,
            success=success,
            duration=result.duration,
            message=message,
            data={
                "file": str(path),
                "framework": framework,
                "passed": result.passed,
                "failed": result.failed,
                "skipped": result.skipped,
                "total": result.total,
                "failures": result.failures
            },
            error=result.error
        )

    def _is_test_file(self, path: Path) -> bool:
        """Check if file is a test file."""
        name = path.name
        return (
            name.startswith("test_") or
            name.endswith("_test.py") or
            ".test." in name or
            ".spec." in name
        )

    def _get_test_framework(self, path: Path) -> Optional[str]:
        """Get test framework for file type."""
        suffix = path.suffix.lstrip(".")

        extension_map = {
            "py": "python",
            "js": "javascript",
            "jsx": "javascript",
            "ts": "typescript",
            "tsx": "typescript",
        }

        language = extension_map.get(suffix)
        if language:
            return self.config.test_frameworks.get(language)

        return None

    def _find_related_tests(self, path: Path) -> List[Path]:
        """Find test files related to a source file."""
        test_files = []

        # For Python: test_<name>.py or <name>_test.py
        if path.suffix == ".py":
            stem = path.stem
            test_dir = path.parent / "tests"
            possible_tests = [
                path.parent / f"test_{stem}.py",
                path.parent / f"{stem}_test.py",
                test_dir / f"test_{stem}.py",
                test_dir / f"{stem}_test.py",
            ]
            test_files.extend([t for t in possible_tests if t.exists()])

        # For JS/TS: <name>.test.js/ts or <name>.spec.js/ts
        elif path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
            stem = path.stem
            ext = path.suffix
            possible_tests = [
                path.parent / f"{stem}.test{ext}",
                path.parent / f"{stem}.spec{ext}",
                path.parent / "__tests__" / f"{stem}.test{ext}",
            ]
            test_files.extend([t for t in possible_tests if t.exists()])

        return test_files

    async def _run_tests(
        self,
        framework: str,
        test_files: List[Path],
        source_path: Path
    ) -> TestResult:
        """Run tests using the specified framework."""
        try:
            if framework == "pytest":
                return await self._run_pytest(test_files, source_path)
            elif framework == "jest":
                return await self._run_jest(test_files, source_path)
            else:
                return TestResult(
                    success=False,
                    error=f"Unknown framework: {framework}"
                )

        except Exception as e:
            self.logger.error(f"Error running {framework}: {e}")
            return TestResult(success=False, error=str(e))

    async def _run_pytest(self, test_files: List[Path], source_path: Path) -> TestResult:
        """Run pytest."""
        try:
            # Get updated environment with venv bin in PATH
            import os
            env = os.environ.copy()
            venv_bin = Path(__file__).parent.parent.parent.parent / ".venv" / "bin"
            if venv_bin.exists():
                env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

            # Check if pytest is installed
            check = await asyncio.create_subprocess_exec(
                "pytest", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            await check.communicate()

            if check.returncode != 0:
                return TestResult(success=False, error="pytest not installed")

            # Build command
            cmd = ["pytest", "-v", "--tb=short"]

            if test_files:
                # Run specific test files
                cmd.extend([str(f) for f in test_files])
            else:
                # Run all tests in project
                cmd.append(str(source_path.parent))

            # Run pytest
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            stdout, stderr = await proc.communicate()
            output = stdout.decode() if stdout else ""

            # Parse output
            passed = self._count_pattern(output, r"(\d+) passed")
            failed = self._count_pattern(output, r"(\d+) failed")
            skipped = self._count_pattern(output, r"(\d+) skipped")

            # Extract duration
            duration_match = re.search(r"in ([\d.]+)s", output)
            duration = float(duration_match.group(1)) if duration_match else 0.0

            success = proc.returncode == 0

            return TestResult(
                success=success,
                passed=passed,
                failed=failed,
                skipped=skipped,
                duration=duration
            )

        except FileNotFoundError:
            return TestResult(success=False, error="pytest command not found")

    async def _run_jest(self, test_files: List[Path], source_path: Path) -> TestResult:
        """Run jest."""
        try:
            # Get updated environment with venv bin in PATH
            import os
            env = os.environ.copy()
            venv_bin = Path(__file__).parent.parent.parent.parent / ".venv" / "bin"
            if venv_bin.exists():
                env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

            # Check if jest is installed
            check = await asyncio.create_subprocess_exec(
                "jest", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            await check.communicate()

            if check.returncode != 0:
                return TestResult(success=False, error="jest not installed")

            # Build command
            cmd = ["jest", "--json"]

            if test_files:
                cmd.extend([str(f) for f in test_files])

            # Run jest
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            stdout, stderr = await proc.communicate()

            # Parse JSON output
            if stdout:
                try:
                    results = json.loads(stdout.decode())
                    return TestResult(
                        success=results.get("success", False),
                        passed=results.get("numPassedTests", 0),
                        failed=results.get("numFailedTests", 0),
                        skipped=results.get("numPendingTests", 0),
                        duration=results.get("startTime", 0)
                    )
                except json.JSONDecodeError:
                    pass

            return TestResult(success=proc.returncode == 0)

        except FileNotFoundError:
            return TestResult(success=False, error="jest command not found")

    def _count_pattern(self, text: str, pattern: str) -> int:
        """Count occurrences of a pattern in text."""
        match = re.search(pattern, text)
        return int(match.group(1)) if match else 0
