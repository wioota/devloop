"""GitLab CI provider implementation."""

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


class GitLabCIProvider(CIProvider):
    """GitLab CI provider using glab CLI."""

    # Mapping from GitLab status to our RunStatus enum
    STATUS_MAP = {
        "running": RunStatus.IN_PROGRESS,
        "pending": RunStatus.QUEUED,
        "created": RunStatus.QUEUED,
        "waiting_for_resource": RunStatus.QUEUED,
        "preparing": RunStatus.QUEUED,
        "scheduled": RunStatus.QUEUED,
        "success": RunStatus.COMPLETED,
        "failed": RunStatus.COMPLETED,
        "canceled": RunStatus.COMPLETED,
        "skipped": RunStatus.COMPLETED,
        "manual": RunStatus.COMPLETED,
    }

    # Mapping from GitLab status to our RunConclusion enum
    CONCLUSION_MAP = {
        "success": RunConclusion.SUCCESS,
        "failed": RunConclusion.FAILURE,
        "canceled": RunConclusion.CANCELLED,
        "skipped": RunConclusion.SKIPPED,
        "manual": RunConclusion.NEUTRAL,
    }

    def __init__(self, project_id: Optional[str] = None):
        """Initialize GitLab CI provider.

        Args:
            project_id: Optional GitLab project ID. If not provided, uses current git repo.
        """
        self.project_id = project_id
        self._glab_available = self._check_glab_available()
        self._authenticated = self._check_auth() if self._glab_available else False

    def get_status(self, branch: str) -> Optional[WorkflowRun]:
        """Get the latest pipeline run status for a branch."""
        runs = self.list_runs(branch, limit=1)
        return runs[0] if runs else None

    def list_runs(
        self,
        branch: str,
        limit: int = 10,
        workflow_name: Optional[str] = None,
    ) -> List[WorkflowRun]:
        """List pipeline runs for a branch."""
        if not self.is_available():
            return []

        try:
            cmd = [
                "glab",
                "ci",
                "list",
                "--per-page",
                str(limit),
                "--output",
                "json",
            ]

            # Add branch filter if specified
            if branch:
                cmd.extend(["--ref", branch])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            if not result.stdout.strip():
                return []

            pipelines_data = json.loads(result.stdout)
            runs = []

            for pipeline in pipelines_data:
                try:
                    gitlab_status = pipeline.get("status", "pending").lower()
                    status = self.STATUS_MAP.get(gitlab_status, RunStatus.QUEUED)

                    # Only set conclusion if pipeline is completed
                    conclusion = None
                    if status == RunStatus.COMPLETED:
                        conclusion = self.CONCLUSION_MAP.get(
                            gitlab_status, RunConclusion.NEUTRAL
                        )

                    run = WorkflowRun(
                        id=str(pipeline.get("id", "")),
                        name=f"Pipeline #{pipeline.get('id', 'Unknown')}",
                        branch=pipeline.get("ref", branch),
                        status=status,
                        conclusion=conclusion,
                        created_at=datetime.fromisoformat(
                            pipeline.get("created_at", "").replace("Z", "+00:00")
                        ),
                        updated_at=datetime.fromisoformat(
                            pipeline.get("updated_at", "").replace("Z", "+00:00")
                        ),
                        url=pipeline.get("web_url"),
                        metadata={"sha": pipeline.get("sha")},
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
        """Get logs for a specific pipeline run."""
        if not self.is_available():
            return None

        try:
            result = subprocess.run(
                ["glab", "ci", "trace", run_id],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            return result.stdout if result.stdout else None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    def rerun(self, run_id: str) -> bool:
        """Retry a specific pipeline run."""
        if not self.is_available():
            return False

        try:
            subprocess.run(
                ["glab", "ci", "retry", run_id],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def cancel(self, run_id: str) -> bool:
        """Cancel a running pipeline."""
        if not self.is_available():
            return False

        try:
            subprocess.run(
                ["glab", "ci", "cancel", run_id],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def get_workflows(self) -> List[WorkflowDefinition]:
        """Get all pipeline definitions in the repository.

        Note: GitLab CI uses .gitlab-ci.yml for pipeline definitions.
        This method returns a single workflow definition representing the main pipeline.
        """
        if not self.is_available():
            return []

        # GitLab uses a single .gitlab-ci.yml file rather than multiple workflow files
        # We return a single workflow representing the main pipeline
        try:
            workflow = WorkflowDefinition(
                name="GitLab CI Pipeline",
                path=".gitlab-ci.yml",
                triggers=[
                    "push",
                    "merge_request",
                    "tag",
                    "schedule",
                ],  # Common triggers
            )
            return [workflow]
        except (ValueError, KeyError):
            return []

    def is_available(self) -> bool:
        """Check if GitLab CI is available and authenticated."""
        return self._glab_available and self._authenticated

    def get_provider_name(self) -> str:
        """Get human-readable provider name."""
        return "GitLab CI"

    def _check_glab_available(self) -> bool:
        """Check if glab CLI is available."""
        try:
            result = subprocess.run(
                ["glab", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _check_auth(self) -> bool:
        """Check if glab CLI is authenticated."""
        try:
            result = subprocess.run(
                ["glab", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
