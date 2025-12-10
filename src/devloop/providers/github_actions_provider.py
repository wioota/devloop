"""GitHub Actions CI provider implementation."""

import json
import subprocess
from datetime import datetime
from typing import List, Optional

from devloop.providers.ci_provider import (
    CIProvider,
    RunConclusion,
    RunStatus,
    WorkflowDefinition,
    WorkflowRun,
)


class GitHubActionsProvider(CIProvider):
    """GitHub Actions CI provider using gh CLI."""

    def __init__(self, repo_url: Optional[str] = None):
        """Initialize GitHub Actions provider.

        Args:
            repo_url: Optional repository URL. If not provided, uses current git repo.
        """
        self.repo_url = repo_url
        self._gh_available = self._check_gh_available()
        self._authenticated = self._check_auth() if self._gh_available else False

    def get_status(self, branch: str) -> Optional[WorkflowRun]:
        """Get the latest workflow run status for a branch."""
        runs = self.list_runs(branch, limit=1)
        return runs[0] if runs else None

    def list_runs(
        self,
        branch: str,
        limit: int = 10,
        workflow_name: Optional[str] = None,
    ) -> List[WorkflowRun]:
        """List workflow runs for a branch."""
        if not self.is_available():
            return []

        try:
            cmd = [
                "gh",
                "run",
                "list",
                "--branch",
                branch,
                "--limit",
                str(limit),
                "--json",
                "status,conclusion,name,databaseId,createdAt,updatedAt,workflowName,url",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            if not result.stdout.strip():
                return []

            runs_data = json.loads(result.stdout)
            runs = []

            for run_data in runs_data:
                if workflow_name and run_data.get("workflowName") != workflow_name:
                    continue

                try:
                    run = WorkflowRun(
                        id=str(run_data.get("databaseId", "")),
                        name=run_data.get("name", "Unknown"),
                        branch=branch,
                        status=RunStatus(run_data.get("status", "queued")),
                        conclusion=(
                            RunConclusion(run_data.get("conclusion"))
                            if run_data.get("conclusion")
                            else None
                        ),
                        created_at=datetime.fromisoformat(
                            run_data.get("createdAt", "").replace("Z", "+00:00")
                        ),
                        updated_at=datetime.fromisoformat(
                            run_data.get("updatedAt", "").replace("Z", "+00:00")
                        ),
                        url=run_data.get("url"),
                    )
                    runs.append(run)
                except (ValueError, KeyError):
                    # Skip malformed entries
                    continue

            return runs

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
        ):
            return []

    def get_logs(self, run_id: str) -> Optional[str]:
        """Get logs for a specific run."""
        if not self.is_available():
            return None

        try:
            result = subprocess.run(
                ["gh", "run", "view", run_id, "--log"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            return result.stdout if result.stdout else None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    def rerun(self, run_id: str) -> bool:
        """Rerun a specific workflow run."""
        if not self.is_available():
            return False

        try:
            subprocess.run(
                ["gh", "run", "rerun", run_id],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def cancel(self, run_id: str) -> bool:
        """Cancel a running workflow."""
        if not self.is_available():
            return False

        try:
            subprocess.run(
                ["gh", "run", "cancel", run_id],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def get_workflows(self) -> List[WorkflowDefinition]:
        """Get all workflow definitions in the repository."""
        if not self.is_available():
            return []

        try:
            result = subprocess.run(
                ["gh", "workflow", "list", "--json", "name,path"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            if not result.stdout.strip():
                return []

            workflows_data = json.loads(result.stdout)
            workflows = []

            for wf_data in workflows_data:
                try:
                    workflow = WorkflowDefinition(
                        name=wf_data.get("name", "Unknown"),
                        path=wf_data.get("path", ""),
                        triggers=[],  # Would need to parse YAML to extract
                    )
                    workflows.append(workflow)
                except (ValueError, KeyError):
                    continue

            return workflows

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
        ):
            return []

    def is_available(self) -> bool:
        """Check if GitHub Actions is available and authenticated."""
        return self._gh_available and self._authenticated

    def get_provider_name(self) -> str:
        """Get human-readable provider name."""
        return "GitHub Actions"

    def _check_gh_available(self) -> bool:
        """Check if gh CLI is available."""
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _check_auth(self) -> bool:
        """Check if gh CLI is authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
