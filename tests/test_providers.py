"""Tests for provider abstraction layer."""

import pytest

from devloop.providers.ci_provider import CIProvider, RunConclusion, RunStatus, WorkflowRun
from devloop.providers.github_actions_provider import GitHubActionsProvider
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

    def test_provider_manager_list_registry_providers(self):
        """Test provider manager lists available registry providers."""
        manager = ProviderManager()
        providers = manager.list_registry_providers()
        assert "pypi" in providers
        assert "python" in providers

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
