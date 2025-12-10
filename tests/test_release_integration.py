"""Integration tests for release workflow with different providers.

These tests demonstrate the release workflow working with different CI and
registry providers to validate the provider-agnostic design.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from devloop.providers.ci_provider import RunConclusion, RunStatus, WorkflowRun
from devloop.release import ReleaseConfig, ReleaseManager


class TestGitHubActionsWithPyPIRelease:
    """Test release workflow with GitHub Actions CI and PyPI registry."""

    @pytest.fixture
    def github_ci_provider(self):
        """Mock GitHub Actions CI provider."""
        provider = Mock()
        provider.get_provider_name.return_value = "GitHub Actions"
        provider.is_available.return_value = True
        provider.get_status.return_value = WorkflowRun(
            id="run-123",
            name="CI",
            branch="main",
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.SUCCESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/example/actions/runs/123",
        )
        return provider

    @pytest.fixture
    def pypi_registry_provider(self):
        """Mock PyPI registry provider."""
        provider = Mock()
        provider.get_provider_name.return_value = "PyPI"
        provider.is_available.return_value = True
        provider.check_credentials.return_value = True
        provider.publish.return_value = True
        provider.get_package_url.return_value = "https://pypi.org/project/devloop/1.2.3"
        return provider

    @pytest.fixture
    def github_pypi_manager(self, github_ci_provider, pypi_registry_provider):
        """Mock provider manager with GitHub Actions and PyPI."""
        manager = Mock()
        manager.get_ci_provider.return_value = github_ci_provider
        manager.auto_detect_ci_provider.return_value = github_ci_provider
        manager.get_registry_provider.return_value = pypi_registry_provider
        manager.auto_detect_registry_provider.return_value = pypi_registry_provider
        return manager

    def test_github_pypi_release_workflow(self, github_pypi_manager):
        """Test complete release workflow with GitHub + PyPI."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=github_pypi_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=True,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    with patch(
                        "devloop.release.release_manager.subprocess.run"
                    ) as mock_subprocess:
                        mock_subprocess.side_effect = [
                            Mock(stdout="", returncode=0),  # Tag check
                            Mock(returncode=0),  # Tag creation
                            Mock(returncode=0),  # Tag push
                        ]

                        config = ReleaseConfig(
                            version="1.2.3",
                            branch="main",
                            ci_provider="github",
                            registry_provider="pypi",
                        )
                        manager = ReleaseManager(config)
                        result = manager.release()

                        # Verify successful release
                        assert result.success is True
                        assert result.tag_created is True
                        assert result.published is True
                        assert result.ci_provider_name == "GitHub Actions"
                        assert result.registry_provider_name == "PyPI"
                        assert result.version == "1.2.3"


class TestGitLabCIWithPyPIRelease:
    """Test release workflow with GitLab CI and PyPI registry.

    This demonstrates that the same workflow works with different CI providers.
    """

    @pytest.fixture
    def gitlab_ci_provider(self):
        """Mock GitLab CI provider."""
        provider = Mock()
        provider.get_provider_name.return_value = "GitLab CI"
        provider.is_available.return_value = True
        provider.get_status.return_value = WorkflowRun(
            id="pipeline-456",
            name="CI/CD",
            branch="main",
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.SUCCESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://gitlab.com/example/project/-/pipelines/456",
        )
        return provider

    @pytest.fixture
    def pypi_registry_provider(self):
        """Mock PyPI registry provider."""
        provider = Mock()
        provider.get_provider_name.return_value = "PyPI"
        provider.is_available.return_value = True
        provider.check_credentials.return_value = True
        provider.publish.return_value = True
        provider.get_package_url.return_value = "https://pypi.org/project/devloop/2.0.0"
        return provider

    @pytest.fixture
    def gitlab_pypi_manager(self, gitlab_ci_provider, pypi_registry_provider):
        """Mock provider manager with GitLab CI and PyPI."""
        manager = Mock()
        manager.get_ci_provider.return_value = gitlab_ci_provider
        manager.auto_detect_ci_provider.return_value = gitlab_ci_provider
        manager.get_registry_provider.return_value = pypi_registry_provider
        manager.auto_detect_registry_provider.return_value = pypi_registry_provider
        return manager

    def test_gitlab_pypi_release_workflow(self, gitlab_pypi_manager):
        """Test complete release workflow with GitLab CI + PyPI."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=gitlab_pypi_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=True,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    with patch(
                        "devloop.release.release_manager.subprocess.run"
                    ) as mock_subprocess:
                        mock_subprocess.side_effect = [
                            Mock(stdout="", returncode=0),  # Tag check
                            Mock(returncode=0),  # Tag creation
                            Mock(returncode=0),  # Tag push
                        ]

                        config = ReleaseConfig(
                            version="2.0.0",
                            branch="main",
                            ci_provider="gitlab",
                            registry_provider="pypi",
                        )
                        manager = ReleaseManager(config)
                        result = manager.release()

                        # Verify successful release with GitLab CI
                        assert result.success is True
                        assert result.tag_created is True
                        assert result.published is True
                        assert result.ci_provider_name == "GitLab CI"
                        assert result.registry_provider_name == "PyPI"
                        assert result.version == "2.0.0"


class TestMultipleRegistryRelease:
    """Test publishing to multiple registries with the same release tag."""

    @pytest.fixture
    def ci_provider(self):
        """Mock CI provider."""
        provider = Mock()
        provider.get_provider_name.return_value = "GitHub Actions"
        provider.is_available.return_value = True
        provider.get_status.return_value = WorkflowRun(
            id="run-123",
            name="CI",
            branch="main",
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.SUCCESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/example/actions/runs/123",
        )
        return provider

    @pytest.fixture
    def pypi_registry_provider(self):
        """Mock PyPI registry provider."""
        provider = Mock()
        provider.get_provider_name.return_value = "PyPI"
        provider.is_available.return_value = True
        provider.check_credentials.return_value = True
        provider.publish.return_value = True
        provider.get_package_url.return_value = "https://pypi.org/project/devloop/1.5.0"
        return provider

    @pytest.fixture
    def artifactory_registry_provider(self):
        """Mock Artifactory registry provider."""
        provider = Mock()
        provider.get_provider_name.return_value = "Artifactory"
        provider.is_available.return_value = True
        provider.check_credentials.return_value = True
        provider.publish.return_value = True
        provider.get_package_url.return_value = (
            "https://artifactory.example.com/artifactory/repo/devloop/1.5.0"
        )
        return provider

    @pytest.fixture
    def multi_registry_manager(
        self, ci_provider, pypi_registry_provider, artifactory_registry_provider
    ):
        """Mock provider manager with multiple registries."""
        manager = Mock()
        manager.get_ci_provider.return_value = ci_provider
        manager.auto_detect_ci_provider.return_value = ci_provider

        def get_registry(name):
            if name == "pypi":
                return pypi_registry_provider
            elif name == "artifactory":
                return artifactory_registry_provider
            return None

        manager.get_registry_provider.side_effect = get_registry
        manager.auto_detect_registry_provider.return_value = pypi_registry_provider
        return manager

    def test_publish_to_multiple_registries(self, multi_registry_manager):
        """Test publishing same version to multiple registries."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=multi_registry_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=True,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    with patch(
                        "devloop.release.release_manager.subprocess.run"
                    ) as mock_subprocess:
                        mock_subprocess.side_effect = [
                            Mock(stdout="", returncode=0),  # Tag check
                            Mock(returncode=0),  # Tag creation
                            Mock(returncode=0),  # Tag push
                        ]

                        # Release to PyPI
                        config_pypi = ReleaseConfig(
                            version="1.5.0",
                            registry_provider="pypi",
                        )
                        manager_pypi = ReleaseManager(config_pypi)
                        result_pypi = manager_pypi.publish_release()
                        assert result_pypi.success is True
                        assert result_pypi.registry_provider_name == "PyPI"

                        # Release to Artifactory with same version
                        config_artifactory = ReleaseConfig(
                            version="1.5.0",
                            create_tag=False,  # Tag already exists
                            registry_provider="artifactory",
                        )
                        manager_artifactory = ReleaseManager(config_artifactory)
                        result_artifactory = manager_artifactory.publish_release()
                        assert result_artifactory.success is True
                        assert result_artifactory.registry_provider_name == "Artifactory"


class TestReleaseCheckCommand:
    """Test the 'devloop release check' command functionality."""

    def test_check_command_finds_ready_status(self):
        """Test that check command properly validates release readiness."""
        mock_ci = Mock()
        mock_ci.get_provider_name.return_value = "GitHub Actions"
        mock_ci.is_available.return_value = True
        mock_ci.get_status.return_value = WorkflowRun(
            id="run-789",
            name="CI",
            branch="main",
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.SUCCESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/example/actions/runs/789",
        )

        mock_registry = Mock()
        mock_registry.get_provider_name.return_value = "PyPI"
        mock_registry.is_available.return_value = True
        mock_registry.check_credentials.return_value = True

        mock_manager = Mock()
        mock_manager.get_ci_provider.return_value = mock_ci
        mock_manager.auto_detect_ci_provider.return_value = mock_ci
        mock_manager.get_registry_provider.return_value = mock_registry
        mock_manager.auto_detect_registry_provider.return_value = mock_registry

        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=True,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    config = ReleaseConfig(
                        version="3.0.0",
                        create_tag=False,
                        publish=False,
                    )
                    manager = ReleaseManager(config)
                    result = manager.run_pre_release_checks()

                    # Verify all checks pass
                    assert result.success is True
                    assert all(check.passed for check in result.checks)
                    assert len(result.checks) == 5  # All checks
