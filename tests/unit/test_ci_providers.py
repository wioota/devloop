"""Unit tests for CI provider implementations with mocked external calls."""

import json
import subprocess
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError

import pytest

from devloop.providers.ci_provider import (
    RunConclusion,
    RunStatus,
    WorkflowDefinition,
    WorkflowRun,
)
from devloop.providers.circleci_provider import CircleCIProvider
from devloop.providers.github_actions_provider import GitHubActionsProvider
from devloop.providers.gitlab_ci_provider import GitLabCIProvider
from devloop.providers.jenkins_provider import JenkinsProvider


class TestGitHubActionsProvider:
    """Tests for GitHub Actions provider with mocked gh CLI."""

    @patch("subprocess.run")
    def test_is_available_with_auth(self, mock_run):
        """Test availability check when gh is installed and authenticated."""
        mock_run.return_value = Mock(returncode=0)
        provider = GitHubActionsProvider()
        assert provider.is_available() is True

    @patch("subprocess.run")
    def test_is_available_gh_not_installed(self, mock_run):
        """Test availability when gh CLI is not installed."""
        mock_run.side_effect = FileNotFoundError()
        provider = GitHubActionsProvider()
        assert provider.is_available() is False

    @patch("subprocess.run")
    def test_is_available_not_authenticated(self, mock_run):
        """Test availability when gh is not authenticated."""

        def side_effect(cmd, **kwargs):
            if "auth" in cmd:
                return Mock(returncode=1)
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        assert provider.is_available() is False

    @patch("subprocess.run")
    def test_list_runs_success(self, mock_run):
        """Test listing workflow runs with successful response."""
        runs_data = [
            {
                "databaseId": 12345,
                "name": "CI Build",
                "status": "completed",
                "conclusion": "success",
                "workflowName": "CI",
                "createdAt": "2024-01-01T10:00:00Z",
                "updatedAt": "2024-01-01T10:05:00Z",
                "url": "https://github.com/org/repo/actions/runs/12345",
            }
        ]

        def side_effect(cmd, **kwargs):
            if "run" in cmd and "list" in cmd:
                return Mock(
                    returncode=0,
                    stdout=json.dumps(runs_data),
                )
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        runs = provider.list_runs("main", limit=5)

        assert len(runs) == 1
        assert runs[0].id == "12345"
        assert runs[0].name == "CI Build"
        assert runs[0].status == RunStatus.COMPLETED
        assert runs[0].conclusion == RunConclusion.SUCCESS

    @patch("subprocess.run")
    def test_list_runs_empty_response(self, mock_run):
        """Test handling empty response from gh run list."""

        def side_effect(cmd, **kwargs):
            if "run" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout="")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        runs = provider.list_runs("main")

        assert runs == []

    @patch("subprocess.run")
    def test_list_runs_not_available(self, mock_run):
        """Test list_runs when provider is not available."""
        mock_run.side_effect = FileNotFoundError()
        provider = GitHubActionsProvider()
        runs = provider.list_runs("main")

        assert runs == []

    @patch("subprocess.run")
    def test_list_runs_timeout(self, mock_run):
        """Test handling timeout in list_runs."""

        def side_effect(cmd, **kwargs):
            if "run" in cmd and "list" in cmd:
                raise subprocess.TimeoutExpired(cmd, 10)
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        runs = provider.list_runs("main")

        assert runs == []

    @patch("subprocess.run")
    def test_list_runs_json_decode_error(self, mock_run):
        """Test handling malformed JSON in list_runs."""

        def side_effect(cmd, **kwargs):
            if "run" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout="invalid json{")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        runs = provider.list_runs("main")

        assert runs == []

    @patch("subprocess.run")
    def test_list_runs_filter_by_workflow(self, mock_run):
        """Test filtering runs by workflow name."""
        runs_data = [
            {
                "databaseId": 1,
                "name": "Build 1",
                "status": "completed",
                "conclusion": "success",
                "workflowName": "CI",
                "createdAt": "2024-01-01T10:00:00Z",
                "updatedAt": "2024-01-01T10:05:00Z",
            },
            {
                "databaseId": 2,
                "name": "Build 2",
                "status": "completed",
                "conclusion": "success",
                "workflowName": "Deploy",
                "createdAt": "2024-01-01T10:00:00Z",
                "updatedAt": "2024-01-01T10:05:00Z",
            },
        ]

        def side_effect(cmd, **kwargs):
            if "run" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout=json.dumps(runs_data))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        runs = provider.list_runs("main", workflow_name="CI")

        assert len(runs) == 1
        assert runs[0].id == "1"

    @patch("subprocess.run")
    def test_get_status_returns_latest_run(self, mock_run):
        """Test get_status returns the most recent run."""
        runs_data = [
            {
                "databaseId": 100,
                "name": "Latest Build",
                "status": "completed",
                "conclusion": "failure",
                "workflowName": "CI",
                "createdAt": "2024-01-02T10:00:00Z",
                "updatedAt": "2024-01-02T10:05:00Z",
            }
        ]

        def side_effect(cmd, **kwargs):
            if "run" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout=json.dumps(runs_data))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        status = provider.get_status("main")

        assert status is not None
        assert status.id == "100"
        assert status.conclusion == RunConclusion.FAILURE

    @patch("subprocess.run")
    def test_get_status_no_runs(self, mock_run):
        """Test get_status when no runs exist."""

        def side_effect(cmd, **kwargs):
            if "run" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout="[]")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        status = provider.get_status("main")

        assert status is None

    @patch("subprocess.run")
    def test_get_logs_success(self, mock_run):
        """Test getting logs for a run."""

        def side_effect(cmd, **kwargs):
            if "view" in cmd and "--log" in cmd:
                return Mock(returncode=0, stdout="Build logs here...")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        logs = provider.get_logs("12345")

        assert logs == "Build logs here..."

    @patch("subprocess.run")
    def test_get_logs_not_available(self, mock_run):
        """Test get_logs when provider is not available."""
        mock_run.side_effect = FileNotFoundError()
        provider = GitHubActionsProvider()
        logs = provider.get_logs("12345")

        assert logs is None

    @patch("subprocess.run")
    def test_get_logs_timeout(self, mock_run):
        """Test handling timeout in get_logs."""

        def side_effect(cmd, **kwargs):
            if "view" in cmd:
                raise subprocess.TimeoutExpired(cmd, 30)
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        logs = provider.get_logs("12345")

        assert logs is None

    @patch("subprocess.run")
    def test_rerun_success(self, mock_run):
        """Test rerunning a workflow."""

        def side_effect(cmd, **kwargs):
            if "rerun" in cmd:
                return Mock(returncode=0, stdout="")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        result = provider.rerun("12345")

        assert result is True

    @patch("subprocess.run")
    def test_rerun_failure(self, mock_run):
        """Test handling failed rerun."""

        def side_effect(cmd, **kwargs):
            if "rerun" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        result = provider.rerun("12345")

        assert result is False

    @patch("subprocess.run")
    def test_cancel_success(self, mock_run):
        """Test canceling a workflow run."""

        def side_effect(cmd, **kwargs):
            if "cancel" in cmd:
                return Mock(returncode=0, stdout="")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        result = provider.cancel("12345")

        assert result is True

    @patch("subprocess.run")
    def test_cancel_failure(self, mock_run):
        """Test handling failed cancel."""

        def side_effect(cmd, **kwargs):
            if "cancel" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        result = provider.cancel("12345")

        assert result is False

    @patch("subprocess.run")
    def test_get_workflows_success(self, mock_run):
        """Test getting workflow definitions."""
        workflows_data = [
            {"name": "CI", "path": ".github/workflows/ci.yml"},
            {"name": "Deploy", "path": ".github/workflows/deploy.yml"},
        ]

        def side_effect(cmd, **kwargs):
            if "workflow" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout=json.dumps(workflows_data))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        workflows = provider.get_workflows()

        assert len(workflows) == 2
        assert workflows[0].name == "CI"
        assert workflows[0].path == ".github/workflows/ci.yml"

    @patch("subprocess.run")
    def test_get_workflows_empty(self, mock_run):
        """Test get_workflows with no workflows."""

        def side_effect(cmd, **kwargs):
            if "workflow" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout="")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitHubActionsProvider()
        workflows = provider.get_workflows()

        assert workflows == []


class TestGitLabCIProvider:
    """Tests for GitLab CI provider with mocked glab CLI."""

    @patch("subprocess.run")
    def test_is_available_with_auth(self, mock_run):
        """Test availability check when glab is installed and authenticated."""
        mock_run.return_value = Mock(returncode=0)
        provider = GitLabCIProvider()
        assert provider.is_available() is True

    @patch("subprocess.run")
    def test_is_available_glab_not_installed(self, mock_run):
        """Test availability when glab CLI is not installed."""
        mock_run.side_effect = FileNotFoundError()
        provider = GitLabCIProvider()
        assert provider.is_available() is False

    @patch("subprocess.run")
    def test_list_runs_success(self, mock_run):
        """Test listing pipeline runs with successful response."""
        pipelines_data = [
            {
                "id": 99999,
                "status": "success",
                "ref": "main",
                "sha": "abc123",
                "web_url": "https://gitlab.com/org/repo/-/pipelines/99999",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:05:00Z",
            }
        ]

        def side_effect(cmd, **kwargs):
            if "ci" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout=json.dumps(pipelines_data))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitLabCIProvider()
        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].id == "99999"
        assert runs[0].status == RunStatus.COMPLETED
        assert runs[0].conclusion == RunConclusion.SUCCESS

    @patch("subprocess.run")
    def test_list_runs_pending_status(self, mock_run):
        """Test handling pending pipeline status."""
        pipelines_data = [
            {
                "id": 100,
                "status": "pending",
                "ref": "main",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:00:00Z",
            }
        ]

        def side_effect(cmd, **kwargs):
            if "ci" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout=json.dumps(pipelines_data))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitLabCIProvider()
        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].status == RunStatus.QUEUED
        assert runs[0].conclusion is None

    @patch("subprocess.run")
    def test_list_runs_running_status(self, mock_run):
        """Test handling running pipeline status."""
        pipelines_data = [
            {
                "id": 100,
                "status": "running",
                "ref": "main",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:02:00Z",
            }
        ]

        def side_effect(cmd, **kwargs):
            if "ci" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout=json.dumps(pipelines_data))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitLabCIProvider()
        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].status == RunStatus.IN_PROGRESS
        assert runs[0].conclusion is None

    @patch("subprocess.run")
    def test_list_runs_failed_status(self, mock_run):
        """Test handling failed pipeline status."""
        pipelines_data = [
            {
                "id": 100,
                "status": "failed",
                "ref": "main",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:05:00Z",
            }
        ]

        def side_effect(cmd, **kwargs):
            if "ci" in cmd and "list" in cmd:
                return Mock(returncode=0, stdout=json.dumps(pipelines_data))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitLabCIProvider()
        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].status == RunStatus.COMPLETED
        assert runs[0].conclusion == RunConclusion.FAILURE

    @patch("subprocess.run")
    def test_get_logs_success(self, mock_run):
        """Test getting pipeline logs."""

        def side_effect(cmd, **kwargs):
            if "trace" in cmd:
                return Mock(returncode=0, stdout="Pipeline log output")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitLabCIProvider()
        logs = provider.get_logs("99999")

        assert logs == "Pipeline log output"

    @patch("subprocess.run")
    def test_rerun_success(self, mock_run):
        """Test retrying a pipeline."""

        def side_effect(cmd, **kwargs):
            if "retry" in cmd:
                return Mock(returncode=0, stdout="")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitLabCIProvider()
        result = provider.rerun("99999")

        assert result is True

    @patch("subprocess.run")
    def test_cancel_success(self, mock_run):
        """Test canceling a pipeline."""

        def side_effect(cmd, **kwargs):
            if "cancel" in cmd:
                return Mock(returncode=0, stdout="")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        provider = GitLabCIProvider()
        result = provider.cancel("99999")

        assert result is True

    @patch("subprocess.run")
    def test_get_workflows_returns_gitlab_ci(self, mock_run):
        """Test get_workflows returns GitLab CI workflow definition."""
        mock_run.return_value = Mock(returncode=0)
        provider = GitLabCIProvider()
        workflows = provider.get_workflows()

        assert len(workflows) == 1
        assert workflows[0].name == "GitLab CI Pipeline"
        assert workflows[0].path == ".gitlab-ci.yml"


class TestJenkinsProvider:
    """Tests for Jenkins provider with mocked HTTP requests."""

    def test_is_available_no_config(self):
        """Test availability without configuration."""
        provider = JenkinsProvider()
        assert provider.is_available() is False

    @patch("urllib.request.urlopen")
    def test_is_available_with_valid_config(self, mock_urlopen):
        """Test availability with valid configuration."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"server": "jenkins"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="secret",
            job_name="my-job",
        )
        assert provider.is_available() is True

    @patch("urllib.request.urlopen")
    def test_is_available_auth_failure(self, mock_urlopen):
        """Test availability with authentication failure."""
        mock_urlopen.side_effect = HTTPError(
            "https://jenkins.example.com/api/json",
            401,
            "Unauthorized",
            {},
            None,
        )

        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="bad-token",
        )
        assert provider.is_available() is False

    @patch("urllib.request.urlopen")
    def test_list_runs_success(self, mock_urlopen):
        """Test listing builds with successful response."""
        builds_data = {
            "builds": [
                {
                    "number": 123,
                    "result": "SUCCESS",
                    "timestamp": 1704103200000,  # 2024-01-01 10:00:00 UTC
                    "duration": 300000,  # 5 minutes
                    "url": "https://jenkins.example.com/job/my-job/123/",
                    "actions": [
                        {"lastBuiltRevision": {"branch": [{"name": "refs/heads/main"}]}}
                    ],
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(builds_data).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="secret",
            job_name="my-job",
        )
        # Force available state
        provider._available = True

        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].id == "123"
        assert runs[0].status == RunStatus.COMPLETED
        assert runs[0].conclusion == RunConclusion.SUCCESS
        assert runs[0].branch == "main"

    @patch("urllib.request.urlopen")
    def test_list_runs_in_progress(self, mock_urlopen):
        """Test handling in-progress builds."""
        builds_data = {
            "builds": [
                {
                    "number": 124,
                    "result": None,  # null result means in progress
                    "timestamp": 1704103200000,
                    "duration": 0,
                    "url": "https://jenkins.example.com/job/my-job/124/",
                    "actions": [
                        {"lastBuiltRevision": {"branch": [{"name": "refs/heads/main"}]}}
                    ],
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(builds_data).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="secret",
            job_name="my-job",
        )
        provider._available = True

        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].status == RunStatus.IN_PROGRESS
        assert runs[0].conclusion is None

    @patch("urllib.request.urlopen")
    def test_list_runs_failure(self, mock_urlopen):
        """Test handling failed builds."""
        builds_data = {
            "builds": [
                {
                    "number": 125,
                    "result": "FAILURE",
                    "timestamp": 1704103200000,
                    "duration": 60000,
                    "url": "https://jenkins.example.com/job/my-job/125/",
                    "actions": [
                        {"lastBuiltRevision": {"branch": [{"name": "refs/heads/main"}]}}
                    ],
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(builds_data).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="secret",
            job_name="my-job",
        )
        provider._available = True

        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].status == RunStatus.COMPLETED
        assert runs[0].conclusion == RunConclusion.FAILURE

    def test_list_runs_no_job_name(self):
        """Test list_runs without job name configured."""
        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="secret",
        )
        provider._available = True

        runs = provider.list_runs("main")
        assert runs == []

    @patch("urllib.request.urlopen")
    def test_get_logs_success(self, mock_urlopen):
        """Test getting build console output."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"Build console output..."
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="secret",
            job_name="my-job",
        )
        provider._available = True

        logs = provider.get_logs("123")
        assert logs == "Build console output..."

    @patch("urllib.request.urlopen")
    def test_rerun_success(self, mock_urlopen):
        """Test rebuilding a build."""
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="secret",
            job_name="my-job",
        )
        provider._available = True

        result = provider.rerun("123")
        assert result is True

    @patch("urllib.request.urlopen")
    def test_cancel_success(self, mock_urlopen):
        """Test stopping a build."""
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="secret",
            job_name="my-job",
        )
        provider._available = True

        result = provider.cancel("123")
        assert result is True

    def test_get_workflows_returns_job(self):
        """Test get_workflows returns configured job."""
        provider = JenkinsProvider(
            base_url="https://jenkins.example.com",
            username="admin",
            token="secret",
            job_name="my-job",
        )
        provider._available = True

        workflows = provider.get_workflows()
        assert len(workflows) == 1
        assert workflows[0].name == "my-job"

    def test_extract_branch_success(self):
        """Test extracting branch from build data."""
        provider = JenkinsProvider()
        build_data = {
            "actions": [
                {"lastBuiltRevision": {"branch": [{"name": "refs/heads/feature/test"}]}}
            ]
        }

        branch = provider._extract_branch(build_data)
        assert branch == "feature/test"

    def test_extract_branch_no_revision(self):
        """Test extracting branch when no revision data exists."""
        provider = JenkinsProvider()
        build_data = {"actions": []}

        branch = provider._extract_branch(build_data)
        assert branch is None


class TestCircleCIProvider:
    """Tests for CircleCI provider with mocked HTTP requests."""

    def test_is_available_no_config(self):
        """Test availability without configuration."""
        provider = CircleCIProvider()
        assert provider.is_available() is False

    @patch("urllib.request.urlopen")
    def test_is_available_with_valid_config(self, mock_urlopen):
        """Test availability with valid configuration."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"slug": "gh/org/repo"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = CircleCIProvider(
            project_slug="gh/org/repo",
            token="test-token",
        )
        assert provider.is_available() is True

    @patch("urllib.request.urlopen")
    def test_is_available_auth_failure(self, mock_urlopen):
        """Test availability with authentication failure."""
        mock_urlopen.side_effect = HTTPError(
            "https://circleci.com/api/v2/project/gh/org/repo",
            401,
            "Unauthorized",
            {},
            None,
        )

        provider = CircleCIProvider(
            project_slug="gh/org/repo",
            token="bad-token",
        )
        assert provider.is_available() is False

    @patch("urllib.request.urlopen")
    def test_list_runs_success(self, mock_urlopen):
        """Test listing workflow runs with successful response."""
        pipelines_data = {
            "items": [
                {
                    "id": "pipeline-123",
                    "number": 42,
                    "vcs": {"branch": "main", "revision": "abc123"},
                }
            ]
        }
        workflows_data = {
            "items": [
                {
                    "id": "workflow-456",
                    "name": "build-and-test",
                    "status": "success",
                    "created_at": "2024-01-01T10:00:00Z",
                    "stopped_at": "2024-01-01T10:05:00Z",
                }
            ]
        }

        call_count = [0]

        def mock_urlopen_side_effect(request, **kwargs):
            call_count[0] += 1
            mock_response = MagicMock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)

            if "pipeline" in request.full_url and "workflow" not in request.full_url:
                mock_response.read.return_value = json.dumps(pipelines_data).encode()
            else:
                mock_response.read.return_value = json.dumps(workflows_data).encode()

            return mock_response

        mock_urlopen.side_effect = mock_urlopen_side_effect

        provider = CircleCIProvider(
            project_slug="gh/org/repo",
            token="test-token",
        )
        provider._available = True

        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].id == "workflow-456"
        assert runs[0].name == "build-and-test"
        assert runs[0].status == RunStatus.COMPLETED
        assert runs[0].conclusion == RunConclusion.SUCCESS

    @patch("urllib.request.urlopen")
    def test_list_runs_running_status(self, mock_urlopen):
        """Test handling running workflow status."""
        pipelines_data = {"items": [{"id": "pipeline-123"}]}
        workflows_data = {
            "items": [
                {
                    "id": "workflow-456",
                    "name": "build",
                    "status": "running",
                    "created_at": "2024-01-01T10:00:00Z",
                }
            ]
        }

        def mock_urlopen_side_effect(request, **kwargs):
            mock_response = MagicMock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)

            if "pipeline" in request.full_url and "workflow" not in request.full_url:
                mock_response.read.return_value = json.dumps(pipelines_data).encode()
            else:
                mock_response.read.return_value = json.dumps(workflows_data).encode()

            return mock_response

        mock_urlopen.side_effect = mock_urlopen_side_effect

        provider = CircleCIProvider(
            project_slug="gh/org/repo",
            token="test-token",
        )
        provider._available = True

        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].status == RunStatus.IN_PROGRESS
        assert runs[0].conclusion is None

    @patch("urllib.request.urlopen")
    def test_list_runs_failed_status(self, mock_urlopen):
        """Test handling failed workflow status."""
        pipelines_data = {"items": [{"id": "pipeline-123"}]}
        workflows_data = {
            "items": [
                {
                    "id": "workflow-456",
                    "name": "build",
                    "status": "failed",
                    "created_at": "2024-01-01T10:00:00Z",
                    "stopped_at": "2024-01-01T10:03:00Z",
                }
            ]
        }

        def mock_urlopen_side_effect(request, **kwargs):
            mock_response = MagicMock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)

            if "pipeline" in request.full_url and "workflow" not in request.full_url:
                mock_response.read.return_value = json.dumps(pipelines_data).encode()
            else:
                mock_response.read.return_value = json.dumps(workflows_data).encode()

            return mock_response

        mock_urlopen.side_effect = mock_urlopen_side_effect

        provider = CircleCIProvider(
            project_slug="gh/org/repo",
            token="test-token",
        )
        provider._available = True

        runs = provider.list_runs("main")

        assert len(runs) == 1
        assert runs[0].status == RunStatus.COMPLETED
        assert runs[0].conclusion == RunConclusion.FAILURE

    @patch("urllib.request.urlopen")
    def test_get_logs_success(self, mock_urlopen):
        """Test getting workflow logs."""
        workflow_data = {"name": "build-and-test", "status": "success"}
        jobs_data = {
            "items": [
                {"name": "build", "status": "success"},
                {"name": "test", "status": "success"},
            ]
        }

        call_count = [0]

        def mock_urlopen_side_effect(request, **kwargs):
            call_count[0] += 1
            mock_response = MagicMock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)

            if "/job" in request.full_url:
                mock_response.read.return_value = json.dumps(jobs_data).encode()
            else:
                mock_response.read.return_value = json.dumps(workflow_data).encode()

            return mock_response

        mock_urlopen.side_effect = mock_urlopen_side_effect

        provider = CircleCIProvider(
            project_slug="gh/org/repo",
            token="test-token",
        )
        provider._available = True

        logs = provider.get_logs("workflow-456")

        assert "build-and-test" in logs
        assert "build: success" in logs
        assert "test: success" in logs

    @patch("urllib.request.urlopen")
    def test_rerun_success(self, mock_urlopen):
        """Test rerunning a workflow."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "queued"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = CircleCIProvider(
            project_slug="gh/org/repo",
            token="test-token",
        )
        provider._available = True

        result = provider.rerun("workflow-456")
        assert result is True

    @patch("urllib.request.urlopen")
    def test_cancel_success(self, mock_urlopen):
        """Test canceling a workflow."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "canceled"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = CircleCIProvider(
            project_slug="gh/org/repo",
            token="test-token",
        )
        provider._available = True

        result = provider.cancel("workflow-456")
        assert result is True

    @patch("urllib.request.urlopen")
    def test_get_workflows_success(self, mock_urlopen):
        """Test getting workflow definitions."""
        pipelines_data = {"items": [{"id": "pipeline-1"}, {"id": "pipeline-2"}]}
        workflows_data_1 = {"items": [{"name": "build-and-test"}]}
        workflows_data_2 = {"items": [{"name": "deploy"}]}

        call_count = [0]

        def mock_urlopen_side_effect(request, **kwargs):
            call_count[0] += 1
            mock_response = MagicMock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)

            if (
                "project" in request.full_url
                and "pipeline" in request.full_url
                and "workflow" not in request.full_url
            ):
                mock_response.read.return_value = json.dumps(pipelines_data).encode()
            elif "pipeline-1" in request.full_url:
                mock_response.read.return_value = json.dumps(workflows_data_1).encode()
            else:
                mock_response.read.return_value = json.dumps(workflows_data_2).encode()

            return mock_response

        mock_urlopen.side_effect = mock_urlopen_side_effect

        provider = CircleCIProvider(
            project_slug="gh/org/repo",
            token="test-token",
        )
        provider._available = True

        workflows = provider.get_workflows()

        assert len(workflows) >= 1
        workflow_names = [w.name for w in workflows]
        assert "build-and-test" in workflow_names or "deploy" in workflow_names


class TestWorkflowDataClasses:
    """Tests for workflow-related data classes."""

    def test_workflow_run_creation(self):
        """Test WorkflowRun dataclass creation."""
        run = WorkflowRun(
            id="123",
            name="CI Build",
            branch="main",
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.SUCCESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://example.com/run/123",
        )

        assert run.id == "123"
        assert run.name == "CI Build"
        assert run.status == RunStatus.COMPLETED
        assert run.conclusion == RunConclusion.SUCCESS
        assert run.metadata == {}

    def test_workflow_run_with_metadata(self):
        """Test WorkflowRun with custom metadata."""
        run = WorkflowRun(
            id="123",
            name="CI Build",
            branch="main",
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.SUCCESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"sha": "abc123", "actor": "test-user"},
        )

        assert run.metadata["sha"] == "abc123"
        assert run.metadata["actor"] == "test-user"

    def test_workflow_definition_creation(self):
        """Test WorkflowDefinition dataclass creation."""
        workflow = WorkflowDefinition(
            name="CI",
            path=".github/workflows/ci.yml",
            triggers=["push", "pull_request"],
        )

        assert workflow.name == "CI"
        assert workflow.path == ".github/workflows/ci.yml"
        assert "push" in workflow.triggers
        assert workflow.metadata == {}

    def test_run_status_enum_values(self):
        """Test RunStatus enum values."""
        assert RunStatus.IN_PROGRESS.value == "in_progress"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.QUEUED.value == "queued"

    def test_run_conclusion_enum_values(self):
        """Test RunConclusion enum values."""
        assert RunConclusion.SUCCESS.value == "success"
        assert RunConclusion.FAILURE.value == "failure"
        assert RunConclusion.CANCELLED.value == "cancelled"
        assert RunConclusion.TIMED_OUT.value == "timed_out"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
