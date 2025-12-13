"""Tests for provider abstraction layer."""

import pytest
from devloop.providers.artifactory_registry import ArtifactoryRegistry
from devloop.providers.ci_provider import (
    CIProvider,
    RunConclusion,
    RunStatus,
    WorkflowRun,
)
from devloop.providers.circleci_provider import CircleCIProvider
from devloop.providers.github_actions_provider import GitHubActionsProvider
from devloop.providers.gitlab_ci_provider import GitLabCIProvider
from devloop.providers.jenkins_provider import JenkinsProvider
from devloop.providers.provider_manager import ProviderManager
from devloop.providers.pypi_registry import PyPIRegistry
from devloop.providers.registry_provider import PackageRegistry


class TestCIProvider:
    """Tests for CI provider abstraction."""

    def test_github_actions_provider_initialization(self):
        """Test GitHub Actions provider can be initialized."""
        provider = GitHubActionsProvider()
        assert provider is not None
        assert provider.get_provider_name() == "GitHub Actions"

    def test_provider_manager_creation(self):
        """Test provider manager can be created."""
        manager = ProviderManager()
        assert manager is not None

    def test_provider_manager_get_ci_provider(self):
        """Test provider manager can get CI provider."""
        manager = ProviderManager()
        provider = manager.get_ci_provider("github")
        assert provider is not None
        assert isinstance(provider, CIProvider)

    def test_provider_manager_unknown_provider(self):
        """Test provider manager handles unknown providers."""
        manager = ProviderManager()
        provider = manager.get_ci_provider("unknown-ci")
        assert provider is None

    def test_provider_manager_list_ci_providers(self):
        """Test provider manager lists available CI providers."""
        manager = ProviderManager()
        providers = manager.list_ci_providers()
        assert "github" in providers
        assert "github-actions" in providers
        assert "gitlab" in providers
        assert "gitlab-ci" in providers
        assert "jenkins" in providers
        assert "circleci" in providers
        assert "circle-ci" in providers

    def test_provider_manager_list_registry_providers(self):
        """Test provider manager lists available registry providers."""
        manager = ProviderManager()
        providers = manager.list_registry_providers()
        assert "pypi" in providers
        assert "python" in providers
        assert "artifactory" in providers

    def test_workflow_run_creation(self):
        """Test WorkflowRun dataclass creation."""
        from datetime import datetime

        run = WorkflowRun(
            id="123",
            name="test-workflow",
            branch="main",
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.SUCCESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert run.id == "123"
        assert run.name == "test-workflow"
        assert run.status == RunStatus.COMPLETED
        assert run.conclusion == RunConclusion.SUCCESS

    def test_gitlab_ci_provider_initialization(self):
        """Test GitLab CI provider can be initialized."""
        provider = GitLabCIProvider()
        assert provider is not None
        assert provider.get_provider_name() == "GitLab CI"

    def test_jenkins_provider_initialization(self):
        """Test Jenkins provider can be initialized."""
        provider = JenkinsProvider()
        assert provider is not None
        assert provider.get_provider_name() == "Jenkins"

    def test_circleci_provider_initialization(self):
        """Test CircleCI provider can be initialized."""
        provider = CircleCIProvider()
        assert provider is not None
        assert provider.get_provider_name() == "CircleCI"

    def test_gitlab_provider_via_manager(self):
        """Test GitLab provider can be retrieved via manager."""
        manager = ProviderManager()
        provider = manager.get_ci_provider("gitlab")
        assert provider is not None
        assert isinstance(provider, GitLabCIProvider)

    def test_jenkins_provider_via_manager(self):
        """Test Jenkins provider can be retrieved via manager."""
        manager = ProviderManager()
        provider = manager.get_ci_provider("jenkins")
        assert provider is not None
        assert isinstance(provider, JenkinsProvider)

    def test_circleci_provider_via_manager(self):
        """Test CircleCI provider can be retrieved via manager."""
        manager = ProviderManager()
        provider = manager.get_ci_provider("circleci")
        assert provider is not None
        assert isinstance(provider, CircleCIProvider)

    def test_gitlab_status_mapping(self):
        """Test GitLab status mapping is correct."""
        provider = GitLabCIProvider()
        assert provider.STATUS_MAP["running"] == RunStatus.IN_PROGRESS
        assert provider.STATUS_MAP["success"] == RunStatus.COMPLETED
        assert provider.CONCLUSION_MAP["success"] == RunConclusion.SUCCESS
        assert provider.CONCLUSION_MAP["failed"] == RunConclusion.FAILURE

    def test_jenkins_status_mapping(self):
        """Test Jenkins status mapping is correct."""
        provider = JenkinsProvider()
        assert provider.STATUS_MAP["SUCCESS"] == RunStatus.COMPLETED
        assert provider.STATUS_MAP["FAILURE"] == RunStatus.COMPLETED
        assert provider.STATUS_MAP[None] == RunStatus.IN_PROGRESS
        assert provider.CONCLUSION_MAP["SUCCESS"] == RunConclusion.SUCCESS
        assert provider.CONCLUSION_MAP["FAILURE"] == RunConclusion.FAILURE

    def test_circleci_status_mapping(self):
        """Test CircleCI status mapping is correct."""
        provider = CircleCIProvider()
        assert provider.STATUS_MAP["running"] == RunStatus.IN_PROGRESS
        assert provider.STATUS_MAP["success"] == RunStatus.COMPLETED
        assert provider.CONCLUSION_MAP["success"] == RunConclusion.SUCCESS
        assert provider.CONCLUSION_MAP["failed"] == RunConclusion.FAILURE


class TestRegistryProvider:
    """Tests for registry provider abstraction."""

    def test_pypi_registry_initialization(self):
        """Test PyPI registry can be initialized."""
        registry = PyPIRegistry()
        assert registry is not None
        assert registry.get_provider_name() == "PyPI"

    def test_pypi_registry_get_package_url(self):
        """Test PyPI registry generates correct URLs."""
        registry = PyPIRegistry()
        url = registry.get_package_url("devloop", "0.1.0")
        assert "devloop" in url
        assert "0.1.0" in url

    def test_provider_manager_get_registry_provider(self):
        """Test provider manager can get registry provider."""
        manager = ProviderManager()
        provider = manager.get_registry_provider("pypi")
        assert provider is not None
        assert isinstance(provider, PackageRegistry)

    def test_provider_manager_unknown_registry(self):
        """Test provider manager handles unknown registries."""
        manager = ProviderManager()
        provider = manager.get_registry_provider("unknown-registry")
        assert provider is None

    def test_artifactory_registry_initialization(self):
        """Test Artifactory registry can be initialized."""
        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )
        assert registry is not None
        assert registry.get_provider_name() == "Artifactory"

    def test_artifactory_registry_get_package_url(self):
        """Test Artifactory registry generates correct URLs."""
        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )
        url = registry.get_package_url("my-package", "1.0.0")
        assert "artifactory" in url
        assert "my-package" in url
        assert "1.0.0" in url

    def test_artifactory_provider_via_manager(self):
        """Test Artifactory provider can be retrieved via manager."""
        manager = ProviderManager()
        provider = manager.get_registry_provider("artifactory")
        assert provider is not None
        assert isinstance(provider, ArtifactoryRegistry)

    def test_artifactory_version_extraction(self):
        """Test Artifactory version extraction from filenames."""
        assert (
            ArtifactoryRegistry._extract_version_from_name("package-1.0.0.jar")
            == "1.0.0"
        )
        assert (
            ArtifactoryRegistry._extract_version_from_name("lib-2.5.1.whl") == "2.5.1"
        )
        assert (
            ArtifactoryRegistry._extract_version_from_name("app-0.1.0-beta")
            == "0.1.0-beta"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
