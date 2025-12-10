"""CI Monitor Agent - Monitors CI system status (platform-agnostic)."""

import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from devloop.core.agent import Agent, AgentResult
from devloop.core.context_store import Finding, Severity
from devloop.core.event import Event
from devloop.providers.ci_provider import CIProvider, RunConclusion, RunStatus
from devloop.providers.provider_manager import get_provider_manager


class CIMonitorAgent(Agent):
    """Monitors CI status and reports failures (provider-agnostic)."""

    def __init__(
        self,
        name: str,
        triggers: List[str],
        event_bus: Any,
        check_interval: int = 300,
        ci_provider: Optional[CIProvider] = None,
        provider_name: str = "github",
    ):
        """
        Initialize CI monitor agent.

        Args:
            name: Agent name
            triggers: Event triggers for this agent
            event_bus: Event bus for publishing events
            check_interval: How often to check CI status (in seconds)
            ci_provider: Optional pre-configured CIProvider. If not provided, auto-detects.
            provider_name: CI provider name (e.g., "github", "gitlab") if ci_provider not provided
        """
        super().__init__(name, triggers, event_bus)
        self.check_interval = check_interval
        self.last_check: Optional[datetime] = None
        self.last_status: Optional[dict] = None

        # Use provided provider or auto-detect
        if ci_provider:
            self.provider: Optional[CIProvider] = ci_provider
        else:
            manager = get_provider_manager()
            provider = manager.get_ci_provider(provider_name)
            if provider:
                self.provider = provider
            else:
                # Fall back to auto-detection
                self.provider = manager.auto_detect_ci_provider()

    async def handle(self, event: Event) -> AgentResult:
        """Handle events and check CI status."""
        if not self.provider:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                error="No CI provider available",
            )

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
            branch = self._get_current_branch()
            if not branch:
                return AgentResult(
                    agent_name=self.name,
                    success=False,
                    duration=0,
                    error="Could not determine current branch",
                )

            # Check if provider is available
            if not self.provider.is_available():
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0,
                    message=f"CI provider '{self.provider.get_provider_name()}' not available",
                )

            # Get latest runs
            runs = self.provider.list_runs(branch, limit=5)
            self.last_check = datetime.now()

            if not runs:
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0,
                    message="No CI runs found",
                )

            # Analyze status and create findings
            findings = self._analyze_runs(runs)

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

    def _get_current_branch(self) -> Optional[str]:
        """Get the current git branch."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    def _analyze_runs(self, runs: List) -> list[Finding]:
        """Analyze CI runs and create findings for issues."""
        findings: list[Finding] = []

        # Ensure provider is available for messages
        if not self.provider:
            return findings

        # Group runs by workflow name
        workflows: Dict[str, list] = {}
        for run in runs:
            workflow_name = run.name
            if workflow_name not in workflows:
                workflows[workflow_name] = []
            workflows[workflow_name].append(run)

        # Check each workflow's latest run
        for workflow_name, workflow_runs in workflows.items():
            latest_run = workflow_runs[0]

            if latest_run.conclusion == RunConclusion.FAILURE:
                findings.append(
                    Finding(
                        id=f"ci-{latest_run.id}",
                        agent="ci-monitor",
                        timestamp=datetime.now().isoformat(),
                        file=".github/workflows/ci.yml",
                        category="ci",
                        severity=Severity.ERROR,
                        message=f"CI workflow '{workflow_name}' failed on branch '{latest_run.branch}' (Run #{latest_run.id})",
                        suggestion=f"View details: {latest_run.url}\nProvider: {self.provider.get_provider_name()}",
                        auto_fixable=False,
                    )
                )
            elif latest_run.status == RunStatus.IN_PROGRESS:
                findings.append(
                    Finding(
                        id=f"ci-{latest_run.id}",
                        agent="ci-monitor",
                        timestamp=datetime.now().isoformat(),
                        file=".github/workflows/ci.yml",
                        category="ci",
                        severity=Severity.INFO,
                        message=f"CI workflow '{workflow_name}' is running on branch '{latest_run.branch}' (Run #{latest_run.id})",
                        suggestion=f"Watch progress at: {latest_run.url}",
                        auto_fixable=False,
                    )
                )

        return findings
