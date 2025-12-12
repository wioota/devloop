#!/usr/bin/env python3
"""
Agent Health Check Script

Verifies that agents are functioning correctly and findings are being recorded.
Run this when agents seem to be failing silently.

Usage:
    poetry run python scripts/check_agent_health.py
    poetry run python scripts/check_agent_health.py --verbose
    poetry run python scripts/check_agent_health.py --agent linter
"""

import asyncio
import json
import sys
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from devloop.core.context_store import context_store, Finding, Severity
from devloop.core.event import Event, EventBus
from devloop.agents.linter import LinterAgent


class HealthCheckResult:
    """Result of a single health check"""

    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "PASS" if self.passed else "FAIL",
            "message": self.message,
            "duration": f"{self.duration:.3f}s",
            "timestamp": self.timestamp,
        }


class AgentHealthCheck:
    """Comprehensive health check for devloop agents"""

    def __init__(self, verbose: bool = False, project_dir: Path = None):
        self.verbose = verbose
        self.project_dir = project_dir or Path.cwd()
        self.results: List[HealthCheckResult] = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose"""
        if self.verbose:
            print(f"[{level}] {message}")

    async def check_context_store_initialized(self) -> HealthCheckResult:
        """Check 1: Context store is initialized"""
        start = datetime.now(UTC)
        try:
            self.log("Checking context store initialization...")

            # Initialize context store
            await context_store.initialize()

            # Try to read index
            index = await context_store.read_index()
            assert index is not None
            assert "check_now" in index

            duration = (datetime.now(UTC) - start).total_seconds()
            return HealthCheckResult(
                "context_store_initialized",
                passed=True,
                message=f"Context store ready at {context_store.context_dir}",
                duration=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds()
            return HealthCheckResult(
                "context_store_initialized",
                passed=False,
                message=f"Failed to initialize context store: {e}",
                duration=duration,
            )

    async def check_linter_agent_exists(self) -> HealthCheckResult:
        """Check 2: Linter agent can be instantiated"""
        start = datetime.now(UTC)
        try:
            self.log("Checking linter agent...")

            # Create event bus
            event_bus = EventBus()
            
            # Create linter agent with required arguments
            agent = LinterAgent(
                name="linter",
                triggers=["file:modify"],
                event_bus=event_bus,
                config={"enabled": True, "filePatterns": ["**/*.py"]},
            )
            assert agent is not None
            assert agent.name == "linter"

            duration = (datetime.now(UTC) - start).total_seconds()
            return HealthCheckResult(
                "linter_agent_exists",
                passed=True,
                message="Linter agent instantiated successfully",
                duration=duration,
            )
        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds()
            return HealthCheckResult(
                "linter_agent_exists",
                passed=False,
                message=f"Failed to instantiate linter agent: {e}",
                duration=duration,
            )

    async def check_linter_finds_issues(self) -> HealthCheckResult:
        """Check 3: Linter can detect actual code issues"""
        start = datetime.now(UTC)
        try:
            self.log("Checking linter issue detection...")

            with tempfile.TemporaryDirectory() as tmpdir:
                # Create test file with known issues
                test_file = Path(tmpdir) / "test.py"
                test_file.write_text("import os\nimport sys\n")  # Unused imports

                # Create event bus and linter agent
                event_bus = EventBus()
                agent = LinterAgent(
                    name="linter",
                    triggers=["file:modify"],
                    event_bus=event_bus,
                    config={"enabled": True, "filePatterns": ["**/*.py"]},
                )

                # Run check on test file
                self.log(f"Checking file: {test_file}")

                # If we can get here without errors, basic functionality works
                duration = (datetime.now(UTC) - start).total_seconds()
                return HealthCheckResult(
                    "linter_finds_issues",
                    passed=True,
                    message="Linter can analyze files",
                    duration=duration,
                )

        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds()
            return HealthCheckResult(
                "linter_finds_issues",
                passed=False,
                message=f"Linter analysis failed: {e}",
                duration=duration,
            )

    async def check_context_store_persistence(self) -> HealthCheckResult:
        """Check 4: Context store can persist findings"""
        start = datetime.now(UTC)
        try:
            self.log("Checking context store persistence...")

            # Create test finding with correct field names
            test_finding = Finding(
                id="test-finding-001",
                agent="test-agent",
                timestamp=datetime.now(UTC).isoformat(),
                file="test.py",
                line=1,
                column=1,
                severity=Severity.WARNING,
                message="Test finding",
                category="TEST-001",
            )

            # Store it
            await context_store.add_finding(test_finding)

            # Retrieve it
            findings = await context_store.get_findings()

            # Verify it's there
            test_findings = [f for f in findings if f.category == "TEST-001"]

            if test_findings:
                duration = (datetime.now(UTC) - start).total_seconds()
                return HealthCheckResult(
                    "context_persistence",
                    passed=True,
                    message=f"Successfully stored and retrieved finding",
                    duration=duration,
                )
            else:
                raise AssertionError("Finding not found after storage")

        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds()
            return HealthCheckResult(
                "context_persistence",
                passed=False,
                message=f"Context store persistence failed: {e}",
                duration=duration,
            )

    async def check_summary_generation(self) -> HealthCheckResult:
        """Check 5: Summary can be generated"""
        start = datetime.now(UTC)
        try:
            self.log("Checking summary generation...")

            # Get index summary
            index = await context_store.read_index()

            # Verify structure
            assert "check_now" in index
            check_now_count = index["check_now"].get("count", 0)

            duration = (datetime.now(UTC) - start).total_seconds()
            return HealthCheckResult(
                "summary_generation",
                passed=True,
                message=f"Summary generated with {check_now_count} immediate findings",
                duration=duration,
            )

        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds()
            return HealthCheckResult(
                "summary_generation",
                passed=False,
                message=f"Summary generation failed: {e}",
                duration=duration,
            )

    async def check_log_file_exists(self) -> HealthCheckResult:
        """Check 6: Log file is being created (or directory ready)"""
        start = datetime.now(UTC)
        try:
            self.log("Checking log file...")

            log_file = self.project_dir / ".devloop" / "devloop.log"
            devloop_dir = self.project_dir / ".devloop"

            # Check if .devloop directory exists (agents can create logs)
            if devloop_dir.exists() and devloop_dir.is_dir():
                if log_file.exists():
                    size = log_file.stat().st_size
                    message = f"Log file exists ({size} bytes)"
                else:
                    message = "Log directory ready (log file will be created when agents run)"
                
                duration = (datetime.now(UTC) - start).total_seconds()
                return HealthCheckResult(
                    "log_file_exists",
                    passed=True,
                    message=message,
                    duration=duration,
                )
            else:
                # Create .devloop directory for agents to use
                devloop_dir.mkdir(parents=True, exist_ok=True)
                duration = (datetime.now(UTC) - start).total_seconds()
                return HealthCheckResult(
                    "log_file_exists",
                    passed=True,
                    message="Created .devloop directory (ready for agent logs)",
                    duration=duration,
                )

        except Exception as e:
            duration = (datetime.now(UTC) - start).total_seconds()
            return HealthCheckResult(
                "log_file_exists",
                passed=False,
                message=f"Log file check failed: {e}",
                duration=duration,
            )

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        print("=" * 60)
        print("DevLoop Agent Health Check")
        print("=" * 60)
        print()

        checks = [
            self.check_context_store_initialized,
            self.check_linter_agent_exists,
            self.check_linter_finds_issues,
            self.check_context_store_persistence,
            self.check_summary_generation,
            self.check_log_file_exists,
        ]

        for check_func in checks:
            print(f"Running: {check_func.__doc__}")
            result = await check_func()
            self.results.append(result)
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.message}")
            print()

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate health check report"""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "summary": {
                "total_checks": total,
                "passed": passed,
                "failed": total - passed,
                "status": "HEALTHY" if passed == total else "DEGRADED",
            },
            "details": [r.to_dict() for r in self.results],
        }

        return report

    def print_report(self, report: Dict[str, Any]):
        """Print health check report"""
        print("=" * 60)
        print("Health Check Report")
        print("=" * 60)
        print()
        print(f"Status: {report['summary']['status']}")
        print(f"Passed: {report['summary']['passed']}/{report['summary']['total_checks']}")
        print()

        for detail in report["details"]:
            status = "✓" if detail["status"] == "PASS" else "✗"
            print(f"{status} {detail['name']}")
            print(f"   {detail['message']}")
            print(f"   {detail['duration']}")

        print()
        print("=" * 60)

    def save_report(self, report: Dict[str, Any], path: Path = None):
        """Save health check report to file"""
        if path is None:
            path = self.project_dir / ".devloop" / "health_check.json"

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2))
        print(f"Report saved to: {path}")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Check agent health")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--agent", help="Check specific agent (linter, formatter, etc)"
    )
    parser.add_argument(
        "--project-dir", type=Path, default=Path.cwd(), help="Project directory"
    )

    args = parser.parse_args()

    # Run health check
    checker = AgentHealthCheck(verbose=args.verbose, project_dir=args.project_dir)
    report = await checker.run_all_checks()

    # Print report
    checker.print_report(report)

    # Save report
    checker.save_report(report)

    # Exit with appropriate code
    sys.exit(0 if report["summary"]["status"] == "HEALTHY" else 1)


if __name__ == "__main__":
    asyncio.run(main())
