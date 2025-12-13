"""Provider manager for discovering and managing CI and registry providers."""

from typing import Any, Dict, Optional

from devloop.providers.artifactory_registry import ArtifactoryRegistry
from devloop.providers.ci_provider import CIProvider
from devloop.providers.circleci_provider import CircleCIProvider
from devloop.providers.github_actions_provider import GitHubActionsProvider
from devloop.providers.gitlab_ci_provider import GitLabCIProvider
from devloop.providers.jenkins_provider import JenkinsProvider
from devloop.providers.pypi_registry import PyPIRegistry
from devloop.providers.registry_provider import PackageRegistry


class ProviderManager:
    """Manages provider discovery, configuration, and instantiation."""

    # Built-in providers
    _CI_PROVIDERS = {
        "github": GitHubActionsProvider,
        "github-actions": GitHubActionsProvider,
        "gitlab": GitLabCIProvider,
        "gitlab-ci": GitLabCIProvider,
        "jenkins": JenkinsProvider,
        "circleci": CircleCIProvider,
        "circle-ci": CircleCIProvider,
    }

    _REGISTRY_PROVIDERS = {
        "pypi": PyPIRegistry,
        "python": PyPIRegistry,
        "artifactory": ArtifactoryRegistry,
    }

    def __init__(self):
        """Initialize provider manager."""
        self._ci_provider_cache: Optional[CIProvider] = None
        self._registry_provider_cache: Optional[PackageRegistry] = None

    def get_ci_provider(
        self,
        provider_name: str = "github",
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[CIProvider]:
        """Get a CI provider instance.

        Args:
            provider_name: Provider name (e.g., "github", "gitlab")
            config: Optional provider configuration

        Returns:
            CIProvider instance or None if provider not found
        """
        if config is None:
            config = {}

        provider_class = self._CI_PROVIDERS.get(provider_name.lower())
        if not provider_class:
            return None

        try:
            return provider_class(**config)
        except Exception:
            return None

    def get_registry_provider(
        self,
        provider_name: str = "pypi",
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[PackageRegistry]:
        """Get a registry provider instance.

        Args:
            provider_name: Provider name (e.g., "pypi", "artifactory")
            config: Optional provider configuration

        Returns:
            PackageRegistry instance or None if provider not found
        """
        if config is None:
            config = {}

        provider_class = self._REGISTRY_PROVIDERS.get(provider_name.lower())
        if not provider_class:
            return None

        try:
            return provider_class(**config)
        except Exception:
            return None

    def register_ci_provider(self, name: str, provider_class: type) -> None:
        """Register a custom CI provider.

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from CIProvider)
        """
        if not issubclass(provider_class, CIProvider):
            raise TypeError(f"{provider_class} must inherit from CIProvider")
        self._CI_PROVIDERS[name.lower()] = provider_class

    def register_registry_provider(self, name: str, provider_class: type) -> None:
        """Register a custom registry provider.

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from PackageRegistry)
        """
        if not issubclass(provider_class, PackageRegistry):
            raise TypeError(f"{provider_class} must inherit from PackageRegistry")
        self._REGISTRY_PROVIDERS[name.lower()] = provider_class

    def list_ci_providers(self) -> list[str]:
        """List available CI providers.

        Returns:
            List of provider names
        """
        return list(self._CI_PROVIDERS.keys())

    def list_registry_providers(self) -> list[str]:
        """List available registry providers.

        Returns:
            List of provider names
        """
        return list(self._REGISTRY_PROVIDERS.keys())

    def auto_detect_ci_provider(self) -> Optional[CIProvider]:
        """Auto-detect the CI provider based on repository structure and available tools.

        Detection priority:
        1. GitHub Actions (if gh CLI is available and authenticated)
        2. GitLab CI (if glab CLI is available and authenticated)
        3. Jenkins (if JENKINS_URL environment variable is set)
        4. CircleCI (if CIRCLECI_PROJECT_SLUG environment variable is set)

        Returns:
            Detected CIProvider instance or None if unable to detect
        """
        # Try GitHub Actions first (most common)
        gh_provider = self.get_ci_provider("github")
        if gh_provider and gh_provider.is_available():
            return gh_provider

        # Try GitLab CI
        gitlab_provider = self.get_ci_provider("gitlab")
        if gitlab_provider and gitlab_provider.is_available():
            return gitlab_provider

        # Try Jenkins
        jenkins_provider = self.get_ci_provider("jenkins")
        if jenkins_provider and jenkins_provider.is_available():
            return jenkins_provider

        # Try CircleCI
        circleci_provider = self.get_ci_provider("circleci")
        if circleci_provider and circleci_provider.is_available():
            return circleci_provider

        return None

    def auto_detect_registry_provider(self) -> Optional[PackageRegistry]:
        """Auto-detect the package registry provider.

        Returns:
            Detected PackageRegistry instance or None if unable to detect
        """
        # Try PyPI first (default for Python projects)
        pypi = self.get_registry_provider("pypi")
        if pypi and pypi.is_available():
            return pypi

        # Could add detection for other registries here
        return None


# Global provider manager instance
_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Get the global provider manager instance.

    Returns:
        ProviderManager instance
    """
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager
