"""CircleCI provider implementation."""

import json
import os
import urllib.request
from datetime import datetime
from typing import List, Optional
from urllib.error import HTTPError, URLError

from devloop.providers.ci_provider import (
    CIProvider,
    RunConclusion,
    RunStatus,
    WorkflowDefinition,
    WorkflowRun,
)


class CircleCIProvider(CIProvider):
    """CircleCI provider using CircleCI API v2."""

    API_BASE = "https://circleci.com/api/v2"

    # Mapping from CircleCI status to our RunStatus enum
    STATUS_MAP = {
        "success": RunStatus.COMPLETED,
        "failed": RunStatus.COMPLETED,
        "error": RunStatus.COMPLETED,
        "canceled": RunStatus.COMPLETED,
        "not_run": RunStatus.COMPLETED,
        "running": RunStatus.IN_PROGRESS,
        "on_hold": RunStatus.QUEUED,
        "queued": RunStatus.QUEUED,
        "not_running": RunStatus.QUEUED,
    }

    # Mapping from CircleCI status to our RunConclusion enum
    CONCLUSION_MAP = {
        "success": RunConclusion.SUCCESS,
        "failed": RunConclusion.FAILURE,
        "error": RunConclusion.FAILURE,
        "canceled": RunConclusion.CANCELLED,
        "not_run": RunConclusion.SKIPPED,
    }

    def __init__(
        self,
        project_slug: Optional[str] = None,
        token: Optional[str] = None,
    ):
        """Initialize CircleCI provider.

        Args:
            project_slug: CircleCI project slug (e.g., "gh/username/repo")
            token: CircleCI API token

        Environment variables (if args not provided):
            CIRCLECI_PROJECT_SLUG: Project slug (gh/username/repo or bb/username/repo)
            CIRCLECI_TOKEN: CircleCI API token
        """
        self.project_slug = project_slug or os.getenv("CIRCLECI_PROJECT_SLUG")
        self.token = token or os.getenv("CIRCLECI_TOKEN")

        self._available = self._check_available()

    def get_status(self, branch: str) -> Optional[WorkflowRun]:
        """Get the latest pipeline status for a branch."""
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
            # Get recent pipelines from CircleCI API
            params = {"branch": branch} if branch else {}
            url = f"{self.API_BASE}/project/{self.project_slug}/pipeline"

            # Add query parameters
            if params:
                query = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{query}"

            data = self._make_request(url)

            if not data or "items" not in data:
                return []

            runs = []
            count = 0

            for pipeline in data["items"]:
                if count >= limit:
                    break

                try:
                    pipeline_id = pipeline.get("id")

                    # Get workflows for this pipeline
                    workflows_url = f"{self.API_BASE}/pipeline/{pipeline_id}/workflow"
                    workflows_data = self._make_request(workflows_url)

                    if not workflows_data or "items" not in workflows_data:
                        continue

                    for workflow in workflows_data["items"]:
                        if count >= limit:
                            break

                        # Filter by workflow name if specified
                        if workflow_name and workflow.get("name") != workflow_name:
                            continue

                        circleci_status = workflow.get("status", "queued").lower()
                        status = self.STATUS_MAP.get(circleci_status, RunStatus.QUEUED)

                        # Only set conclusion if workflow is completed
                        conclusion = None
                        if status == RunStatus.COMPLETED:
                            conclusion = self.CONCLUSION_MAP.get(
                                circleci_status, RunConclusion.NEUTRAL
                            )

                        run = WorkflowRun(
                            id=workflow.get("id", ""),
                            name=workflow.get("name", "Unknown"),
                            branch=pipeline.get("vcs", {}).get("branch", branch),
                            status=status,
                            conclusion=conclusion,
                            created_at=datetime.fromisoformat(
                                workflow.get("created_at", "").replace("Z", "+00:00")
                            ),
                            updated_at=datetime.fromisoformat(
                                workflow.get(
                                    "stopped_at", workflow.get("created_at", "")
                                ).replace("Z", "+00:00")
                            ),
                            url=f"https://app.circleci.com/pipelines/{self.project_slug}/{pipeline.get('number', '')}/workflows/{workflow.get('id', '')}",
                            metadata={
                                "pipeline_id": pipeline_id,
                                "pipeline_number": pipeline.get("number"),
                                "vcs_revision": pipeline.get("vcs", {}).get("revision"),
                            },
                        )
                        runs.append(run)
                        count += 1

                except (ValueError, KeyError):
                    # Skip malformed entries
                    continue

            return runs

        except Exception:
            return []

    def get_logs(self, run_id: str) -> Optional[str]:
        """Get logs for a specific workflow run.

        Note: CircleCI doesn't provide workflow-level logs directly.
        You need to fetch logs for individual jobs within the workflow.
        This returns a summary instead.
        """
        if not self.is_available():
            return None

        try:
            # Get workflow details
            url = f"{self.API_BASE}/workflow/{run_id}"
            workflow_data = self._make_request(url)

            if not workflow_data:
                return None

            # Get jobs for this workflow
            jobs_url = f"{self.API_BASE}/workflow/{run_id}/job"
            jobs_data = self._make_request(jobs_url)

            if not jobs_data or "items" not in jobs_data:
                return None

            # Build a summary of jobs
            logs = [f"Workflow: {workflow_data.get('name', 'Unknown')}"]
            logs.append(f"Status: {workflow_data.get('status', 'Unknown')}")
            logs.append("\nJobs:")

            for job in jobs_data["items"]:
                job_name = job.get("name", "Unknown")
                job_status = job.get("status", "Unknown")
                logs.append(f"  - {job_name}: {job_status}")

            return "\n".join(logs)

        except Exception:
            return None

    def rerun(self, run_id: str) -> bool:
        """Rerun a specific workflow.

        Note: CircleCI requires rerunning from the workflow ID.
        """
        if not self.is_available():
            return False

        try:
            url = f"{self.API_BASE}/workflow/{run_id}/rerun"
            self._make_request(url, method="POST")
            return True
        except Exception:
            return False

    def cancel(self, run_id: str) -> bool:
        """Cancel a running workflow."""
        if not self.is_available():
            return False

        try:
            url = f"{self.API_BASE}/workflow/{run_id}/cancel"
            self._make_request(url, method="POST")
            return True
        except Exception:
            return False

    def get_workflows(self) -> List[WorkflowDefinition]:
        """Get all workflow definitions in the repository.

        Note: CircleCI doesn't provide a direct API to list workflow definitions.
        This returns workflows from recent pipelines as a proxy.
        """
        if not self.is_available():
            return []

        try:
            # Get recent pipelines
            url = f"{self.API_BASE}/project/{self.project_slug}/pipeline"
            data = self._make_request(url)

            if not data or "items" not in data:
                return []

            # Collect unique workflow names from recent pipelines
            workflow_names = set()

            for pipeline in data["items"][:5]:  # Check last 5 pipelines
                try:
                    pipeline_id = pipeline.get("id")
                    workflows_url = f"{self.API_BASE}/pipeline/{pipeline_id}/workflow"
                    workflows_data = self._make_request(workflows_url)

                    if workflows_data and "items" in workflows_data:
                        for workflow in workflows_data["items"]:
                            workflow_names.add(workflow.get("name", "Unknown"))
                except Exception:
                    continue

            # Create workflow definitions
            workflows = []
            for name in workflow_names:
                workflow = WorkflowDefinition(
                    name=name,
                    path=".circleci/config.yml",
                    triggers=["push", "schedule", "api"],  # Common triggers
                )
                workflows.append(workflow)

            return workflows

        except Exception:
            return []

    def is_available(self) -> bool:
        """Check if CircleCI is available and authenticated."""
        return self._available

    def get_provider_name(self) -> str:
        """Get human-readable provider name."""
        return "CircleCI"

    def _check_available(self) -> bool:
        """Check if CircleCI is available and credentials are valid."""
        if not all([self.project_slug, self.token]):
            return False

        try:
            # Test authentication with a simple API call
            url = f"{self.API_BASE}/project/{self.project_slug}"
            self._make_request(url, timeout=5)
            return True
        except Exception:
            return False

    def _make_request(
        self, url: str, method: str = "GET", timeout: int = 10
    ) -> Optional[dict]:
        """Make authenticated request to CircleCI API.

        Args:
            url: Request URL
            method: HTTP method
            timeout: Request timeout in seconds

        Returns:
            Response data as dict

        Raises:
            Exception on request failure
        """
        # Create request with authentication
        request = urllib.request.Request(
            url,
            method=method,
            headers={
                "Circle-Token": self.token,
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content = response.read().decode("utf-8")
                return json.loads(content) if content else {}
        except (HTTPError, URLError, json.JSONDecodeError) as e:
            raise Exception(f"CircleCI API request failed: {e}")
