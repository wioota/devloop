"""CI Monitor Agent - Monitors GitHub Actions CI status."""

import json
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from devloop.core.agent import Agent, AgentResult
from devloop.core.context_store import Finding, Severity
from devloop.core.event import Event


class CIMonitorAgent(Agent):
    """Monitors GitHub Actions CI status and reports failures."""

    def __init__(
        self,
        name: str,
        triggers: List[str],
        event_bus: Any,
        check_interval: int = 300,
    ):  # 5 minutes default
        """
        Initialize CI monitor agent.

        Args:
            name: Agent name
            triggers: Event triggers for this agent
            event_bus: Event bus for publishing events
            check_interval: How often to check CI status (in seconds)
        """
        super().__init__(name, triggers, event_bus)
        self.check_interval = check_interval
        self.last_check: Optional[datetime] = None
        self.last_status: Optional[dict] = None

    async def handle(self, event: Event) -> AgentResult:
        """Handle events and check CI status."""
        # Check if it's time for periodic check
        should_check = False

        if event.type == "time:tick":
            should_check = self._should_check_now()
        elif event.type == "git:post-push":
            # Always check after push
            should_check = True

        if not should_check:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="Not time to check CI yet",
            )

        # Check CI status
        try:
            status = await self._check_ci_status()
            self.last_check = datetime.now()
            self.last_status = status

            if not status:
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0,
                    message="No CI runs found",
                )

            # Analyze status and create findings
            findings = self._analyze_ci_status(status)

            if findings:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    duration=0,
                    message=f"CI issues detected: {len(findings)} workflows need attention",
                    data={"findings": findings},
                )
            else:
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0,
                    message="CI status: All checks passing",
                )

        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                error=f"Failed to check CI status: {e}",
            )

    def _should_check_now(self) -> bool:
        """Determine if we should check CI now based on interval."""
        if self.last_check is None:
            return True

        time_since_check = datetime.now() - self.last_check
        return time_since_check > timedelta(seconds=self.check_interval)

    async def _check_ci_status(self) -> Optional[dict]:
        """
        Check CI status using gh CLI.

        Returns:
            CI status dict or None if unavailable
        """
        # Check if gh CLI is available
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        # Check if authenticated
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
        except subprocess.TimeoutExpired:
            return None

        # Get current branch
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            branch = result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

        # Get latest workflow runs
        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--branch",
                    branch,
                    "--limit",
                    "5",
                    "--json",
                    "status,conclusion,name,databaseId,createdAt,workflowName",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )

            if result.stdout.strip():
                runs = json.loads(result.stdout)
                return {
                    "branch": branch,
                    "runs": runs,
                    "checked_at": datetime.now().isoformat(),
                }
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
        ):
            return None

        return None

    def _analyze_ci_status(self, status: dict) -> list[Finding]:
        """Analyze CI status and create findings for issues."""
        findings = []
        runs = status.get("runs", [])
        branch = status.get("branch", "unknown")

        # Group runs by workflow
        workflows: Dict[str, list] = {}
        for run in runs:
            workflow_name = run.get("workflowName", run.get("name", "Unknown"))
            if workflow_name not in workflows:
                workflows[workflow_name] = []
            workflows[workflow_name].append(run)

        # Check each workflow's latest run
        for workflow_name, workflow_runs in workflows.items():
            latest_run = workflow_runs[0]  # Already sorted by createdAt descending
            conclusion = latest_run.get("conclusion")
            status_val = latest_run.get("status")
            run_id = latest_run.get("databaseId", "unknown")

            if conclusion == "failure":
                findings.append(
                    Finding(
                        id=f"ci-{run_id}",
                        agent="ci-monitor",
                        timestamp=datetime.now().isoformat(),
                        file=".github/workflows/ci.yml",
                        category="ci",
                        severity=Severity.ERROR,
                        message=f"CI workflow '{workflow_name}' failed on branch '{branch}' (Run #{run_id})",
                        suggestion=f"View details: gh run view {run_id}\nRerun: gh run rerun {run_id}",
                        auto_fixable=False,
                    )
                )
            elif status_val == "in_progress":
                findings.append(
                    Finding(
                        id=f"ci-{run_id}",
                        agent="ci-monitor",
                        timestamp=datetime.now().isoformat(),
                        file=".github/workflows/ci.yml",
                        category="ci",
                        severity=Severity.INFO,
                        message=f"CI workflow '{workflow_name}' is running on branch '{branch}' (Run #{run_id})",
                        suggestion=f"Watch progress: gh run watch {run_id}",
                        auto_fixable=False,
                    )
                )

        return findings
