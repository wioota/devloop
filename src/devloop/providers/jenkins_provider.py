"""Jenkins CI provider implementation."""

import json
import os
import urllib.request
from base64 import b64encode
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


class JenkinsProvider(CIProvider):
    """Jenkins CI provider using Jenkins REST API."""

    # Mapping from Jenkins status to our RunStatus enum
    STATUS_MAP = {
        "SUCCESS": RunStatus.COMPLETED,
        "FAILURE": RunStatus.COMPLETED,
        "UNSTABLE": RunStatus.COMPLETED,
        "ABORTED": RunStatus.COMPLETED,
        "NOT_BUILT": RunStatus.COMPLETED,
        None: RunStatus.IN_PROGRESS,  # null result means in progress
    }

    # Mapping from Jenkins result to our RunConclusion enum
    CONCLUSION_MAP = {
        "SUCCESS": RunConclusion.SUCCESS,
        "FAILURE": RunConclusion.FAILURE,
        "UNSTABLE": RunConclusion.FAILURE,
        "ABORTED": RunConclusion.CANCELLED,
        "NOT_BUILT": RunConclusion.SKIPPED,
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        token: Optional[str] = None,
        job_name: Optional[str] = None,
    ):
        """Initialize Jenkins provider.

        Args:
            base_url: Jenkins server URL (e.g., https://jenkins.example.com)
            username: Jenkins username
            token: Jenkins API token
            job_name: Jenkins job name to monitor

        Environment variables (if args not provided):
            JENKINS_URL: Jenkins server URL
            JENKINS_USER: Jenkins username
            JENKINS_TOKEN: Jenkins API token
            JENKINS_JOB: Jenkins job name
        """
        self.base_url = (base_url or os.getenv("JENKINS_URL", "")).rstrip("/")
        self.username = username or os.getenv("JENKINS_USER")
        self.token = token or os.getenv("JENKINS_TOKEN")
        self.job_name = job_name or os.getenv("JENKINS_JOB")

        self._available = self._check_available()

    def get_status(self, branch: str) -> Optional[WorkflowRun]:
        """Get the latest build status for a branch."""
        runs = self.list_runs(branch, limit=1)
        return runs[0] if runs else None

    def list_runs(
        self,
        branch: str,
        limit: int = 10,
        workflow_name: Optional[str] = None,
    ) -> List[WorkflowRun]:
        """List builds for a branch."""
        if not self.is_available():
            return []

        if not self.job_name:
            return []

        try:
            # Get recent builds from Jenkins API
            url = f"{self.base_url}/job/{self.job_name}/api/json?tree=builds[number,result,timestamp,duration,url,actions[lastBuiltRevision[branch[name]]]]{{0,{limit}}}"
            data = self._make_request(url)

            if not data or "builds" not in data:
                return []

            runs = []
            for build in data["builds"]:
                try:
                    # Extract branch name from build actions
                    build_branch = self._extract_branch(build)

                    # Filter by branch if specified
                    if branch and build_branch != branch:
                        continue

                    jenkins_result = build.get("result")
                    status = self.STATUS_MAP.get(jenkins_result, RunStatus.QUEUED)

                    # Only set conclusion if build is completed
                    conclusion = None
                    if status == RunStatus.COMPLETED and jenkins_result:
                        conclusion = self.CONCLUSION_MAP.get(
                            jenkins_result, RunConclusion.NEUTRAL
                        )

                    # Jenkins timestamps are in milliseconds
                    timestamp_ms = build.get("timestamp", 0)
                    created_at = datetime.fromtimestamp(timestamp_ms / 1000)

                    # Calculate updated_at from timestamp + duration
                    duration_ms = build.get("duration", 0)
                    updated_at = datetime.fromtimestamp(
                        (timestamp_ms + duration_ms) / 1000
                    )

                    run = WorkflowRun(
                        id=str(build.get("number", "")),
                        name=f"{self.job_name} #{build.get('number', 'Unknown')}",
                        branch=build_branch or branch,
                        status=status,
                        conclusion=conclusion,
                        created_at=created_at,
                        updated_at=updated_at,
                        url=build.get("url"),
                        metadata={
                            "duration": duration_ms,
                            "result": jenkins_result,
                        },
                    )
                    runs.append(run)
                except (ValueError, KeyError):
                    # Skip malformed entries
                    continue

            return runs[:limit]

        except Exception:
            return []

    def get_logs(self, run_id: str) -> Optional[str]:
        """Get console output for a specific build."""
        if not self.is_available() or not self.job_name:
            return None

        try:
            url = f"{self.base_url}/job/{self.job_name}/{run_id}/consoleText"
            response = self._make_request(url, json_response=False)
            return response if isinstance(response, str) else None
        except Exception:
            return None

    def rerun(self, run_id: str) -> bool:
        """Rebuild a specific build."""
        if not self.is_available() or not self.job_name:
            return False

        try:
            url = f"{self.base_url}/job/{self.job_name}/{run_id}/rebuild"
            self._make_request(url, method="POST")
            return True
        except Exception:
            return False

    def cancel(self, run_id: str) -> bool:
        """Stop a running build."""
        if not self.is_available() or not self.job_name:
            return False

        try:
            url = f"{self.base_url}/job/{self.job_name}/{run_id}/stop"
            self._make_request(url, method="POST")
            return True
        except Exception:
            return False

    def get_workflows(self) -> List[WorkflowDefinition]:
        """Get all job definitions in Jenkins.

        Note: This returns the configured job, not all jobs in Jenkins.
        """
        if not self.is_available() or not self.job_name:
            return []

        try:
            workflow = WorkflowDefinition(
                name=self.job_name,
                path=f"job/{self.job_name}",
                triggers=["scm", "timer", "manual"],  # Common Jenkins triggers
            )
            return [workflow]
        except (ValueError, KeyError):
            return []

    def is_available(self) -> bool:
        """Check if Jenkins is available and authenticated."""
        return self._available

    def get_provider_name(self) -> str:
        """Get human-readable provider name."""
        return "Jenkins"

    def _check_available(self) -> bool:
        """Check if Jenkins is available and credentials are valid."""
        if not all([self.base_url, self.username, self.token]):
            return False

        try:
            # Test authentication with a simple API call
            url = f"{self.base_url}/api/json"
            self._make_request(url, timeout=5)
            return True
        except Exception:
            return False

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        timeout: int = 10,
        json_response: bool = True,
    ):
        """Make authenticated request to Jenkins API.

        Args:
            url: Request URL
            method: HTTP method
            timeout: Request timeout in seconds
            json_response: Whether to parse response as JSON

        Returns:
            Response data (dict if json_response=True, str otherwise)

        Raises:
            Exception on request failure
        """
        # Create authentication header
        credentials = f"{self.username}:{self.token}"
        auth_header = b64encode(credentials.encode()).decode()

        # Create request
        request = urllib.request.Request(
            url,
            method=method,
            headers={"Authorization": f"Basic {auth_header}"},
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content = response.read().decode("utf-8")
                if json_response:
                    return json.loads(content) if content else {}
                return content
        except (HTTPError, URLError, json.JSONDecodeError) as e:
            raise Exception(f"Jenkins API request failed: {e}")

    def _extract_branch(self, build: dict) -> Optional[str]:
        """Extract branch name from build data.

        Args:
            build: Build data from Jenkins API

        Returns:
            Branch name or None
        """
        try:
            actions = build.get("actions", [])
            for action in actions:
                if "lastBuiltRevision" in action:
                    branches = action["lastBuiltRevision"].get("branch", [])
                    if branches and len(branches) > 0:
                        branch_name = branches[0].get("name", "")
                        # Remove refs/heads/ prefix if present
                        if branch_name.startswith("refs/heads/"):
                            branch_name = branch_name.replace("refs/heads/", "")
                        return branch_name
        except (KeyError, IndexError, TypeError):
            pass
        return None
