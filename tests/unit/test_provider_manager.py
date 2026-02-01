"""Unit tests for provider manager with mocked providers."""

from unittest.mock import Mock, patch

import pytest

from devloop.providers.ci_provider import CIProvider
from devloop.providers.provider_manager import ProviderManager, get_provider_manager
from devloop.providers.registry_provider import PackageRegistry


class TestProviderManager:
    """Tests for ProviderManager class."""

    def test_get_ci_provider_with_config(self):
        """Test getting CI provider with configuration."""
        manager = ProviderManager()
        # GitHub Actions provider accepts repo_url config
        provider = manager.get_ci_provider(
            "github", config={"repo_url": "https://github.com/org/repo"}
        )
        assert provider is not None

    def test_get_ci_provider_invalid_config(self):
        """Test getting CI provider with invalid config that causes exception."""
        manager = ProviderManager()
        # Pass invalid config that will cause an exception during instantiation
        # We need to mock the provider class to raise an exception
        with patch.dict(
            manager._CI_PROVIDERS,
            {"test-provider": Mock(side_effect=ValueError("Invalid config"))},
        ):
            provider = manager.get_ci_provider("test-provider")
            assert provider is None

    def test_get_registry_provider_with_config(self):
        """Test getting registry provider with configuration."""
        manager = ProviderManager()
        provider = manager.get_registry_provider(
            "pypi", config={"index_url": "https://test.pypi.org"}
        )
        assert provider is not None

    def test_get_registry_provider_invalid_config(self):
        """Test getting registry provider with invalid config."""
        manager = ProviderManager()
        with patch.dict(
            manager._REGISTRY_PROVIDERS,
            {"test-registry": Mock(side_effect=ValueError("Invalid config"))},
        ):
            provider = manager.get_registry_provider("test-registry")
            assert provider is None

    def test_register_ci_provider_success(self):
        """Test registering a custom CI provider."""
        manager = ProviderManager()

        class CustomCIProvider(CIProvider):
            def get_status(self, branch):
                return None

            def list_runs(self, branch, limit=10, workflow_name=None):
                return []

            def get_logs(self, run_id):
                return None

            def rerun(self, run_id):
                return False

            def cancel(self, run_id):
                return False

            def get_workflows(self):
                return []

            def is_available(self):
                return True

            def get_provider_name(self):
                return "Custom CI"

        manager.register_ci_provider("custom", CustomCIProvider)
        assert "custom" in manager.list_ci_providers()

        # Should be able to get the registered provider
        provider = manager.get_ci_provider("custom")
        assert provider is not None
        assert provider.get_provider_name() == "Custom CI"

    def test_register_ci_provider_invalid_class(self):
        """Test registering an invalid CI provider class."""
        manager = ProviderManager()

        class NotAProvider:
            pass

        with pytest.raises(TypeError, match="must inherit from CIProvider"):
            manager.register_ci_provider("invalid", NotAProvider)

    def test_register_registry_provider_success(self):
        """Test registering a custom registry provider."""
        manager = ProviderManager()

        class CustomRegistry(PackageRegistry):
            def publish(self, package_path, version):
                return True

            def get_version(self, package_name):
                return "1.0.0"

            def get_versions(self, package_name, limit=10):
                return []

            def check_credentials(self):
                return True

            def is_available(self):
                return True

            def get_provider_name(self):
                return "Custom Registry"

            def get_package_url(self, package_name, version=None):
                return f"https://custom/{package_name}"

        manager.register_registry_provider("custom", CustomRegistry)
        assert "custom" in manager.list_registry_providers()

        provider = manager.get_registry_provider("custom")
        assert provider is not None
        assert provider.get_provider_name() == "Custom Registry"

    def test_register_registry_provider_invalid_class(self):
        """Test registering an invalid registry provider class."""
        manager = ProviderManager()

        class NotARegistry:
            pass

        with pytest.raises(TypeError, match="must inherit from PackageRegistry"):
            manager.register_registry_provider("invalid", NotARegistry)

    @patch("devloop.providers.provider_manager.ProviderManager.get_ci_provider")
    def test_auto_detect_ci_provider_github(self, mock_get_ci):
        """Test auto-detecting GitHub Actions provider."""
        manager = ProviderManager()

        mock_github = Mock()
        mock_github.is_available.return_value = True

        def mock_get_provider(name, config=None):
            if name == "github":
                return mock_github
            return None

        mock_get_ci.side_effect = mock_get_provider

        result = manager.auto_detect_ci_provider()
        assert result == mock_github

    @patch("devloop.providers.provider_manager.ProviderManager.get_ci_provider")
    def test_auto_detect_ci_provider_gitlab(self, mock_get_ci):
        """Test auto-detecting GitLab CI provider when GitHub not available."""
        manager = ProviderManager()

        mock_github = Mock()
        mock_github.is_available.return_value = False

        mock_gitlab = Mock()
        mock_gitlab.is_available.return_value = True

        def mock_get_provider(name, config=None):
            if name == "github":
                return mock_github
            if name == "gitlab":
                return mock_gitlab
            return None

        mock_get_ci.side_effect = mock_get_provider

        result = manager.auto_detect_ci_provider()
        assert result == mock_gitlab

    @patch("devloop.providers.provider_manager.ProviderManager.get_ci_provider")
    def test_auto_detect_ci_provider_jenkins(self, mock_get_ci):
        """Test auto-detecting Jenkins provider."""
        manager = ProviderManager()

        mock_github = Mock()
        mock_github.is_available.return_value = False

        mock_gitlab = Mock()
        mock_gitlab.is_available.return_value = False

        mock_jenkins = Mock()
        mock_jenkins.is_available.return_value = True

        def mock_get_provider(name, config=None):
            if name == "github":
                return mock_github
            if name == "gitlab":
                return mock_gitlab
            if name == "jenkins":
                return mock_jenkins
            return None

        mock_get_ci.side_effect = mock_get_provider

        result = manager.auto_detect_ci_provider()
        assert result == mock_jenkins

    @patch("devloop.providers.provider_manager.ProviderManager.get_ci_provider")
    def test_auto_detect_ci_provider_circleci(self, mock_get_ci):
        """Test auto-detecting CircleCI provider."""
        manager = ProviderManager()

        mock_github = Mock()
        mock_github.is_available.return_value = False

        mock_gitlab = Mock()
        mock_gitlab.is_available.return_value = False

        mock_jenkins = Mock()
        mock_jenkins.is_available.return_value = False

        mock_circleci = Mock()
        mock_circleci.is_available.return_value = True

        def mock_get_provider(name, config=None):
            if name == "github":
                return mock_github
            if name == "gitlab":
                return mock_gitlab
            if name == "jenkins":
                return mock_jenkins
            if name == "circleci":
                return mock_circleci
            return None

        mock_get_ci.side_effect = mock_get_provider

        result = manager.auto_detect_ci_provider()
        assert result == mock_circleci

    @patch("devloop.providers.provider_manager.ProviderManager.get_ci_provider")
    def test_auto_detect_ci_provider_none_available(self, mock_get_ci):
        """Test auto-detect when no providers are available."""
        manager = ProviderManager()

        mock_provider = Mock()
        mock_provider.is_available.return_value = False

        mock_get_ci.return_value = mock_provider

        result = manager.auto_detect_ci_provider()
        assert result is None

    @patch("devloop.providers.provider_manager.ProviderManager.get_registry_provider")
    def test_auto_detect_registry_provider_pypi(self, mock_get_registry):
        """Test auto-detecting PyPI registry."""
        manager = ProviderManager()

        mock_pypi = Mock()
        mock_pypi.is_available.return_value = True

        mock_get_registry.return_value = mock_pypi

        result = manager.auto_detect_registry_provider()
        assert result == mock_pypi

    @patch("devloop.providers.provider_manager.ProviderManager.get_registry_provider")
    def test_auto_detect_registry_provider_none_available(self, mock_get_registry):
        """Test auto-detect registry when none available."""
        manager = ProviderManager()

        mock_pypi = Mock()
        mock_pypi.is_available.return_value = False

        mock_get_registry.return_value = mock_pypi

        result = manager.auto_detect_registry_provider()
        assert result is None


class TestGetProviderManager:
    """Tests for get_provider_manager global function."""

    def test_get_provider_manager_creates_singleton(self):
        """Test that get_provider_manager creates a singleton instance."""
        # Reset the global manager
        import devloop.providers.provider_manager as pm

        pm._manager = None

        manager1 = get_provider_manager()
        manager2 = get_provider_manager()

        assert manager1 is manager2
        assert isinstance(manager1, ProviderManager)

    def test_get_provider_manager_returns_existing(self):
        """Test that get_provider_manager returns existing instance."""
        import devloop.providers.provider_manager as pm

        existing = ProviderManager()
        pm._manager = existing

        result = get_provider_manager()
        assert result is existing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
