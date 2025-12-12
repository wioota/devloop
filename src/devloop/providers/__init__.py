"""Provider abstraction layers for CI systems and package registries."""

from devloop.providers.ci_provider import (
    CIProvider,
    RunConclusion,
    RunStatus,
    WorkflowDefinition,
    WorkflowRun,
)
from devloop.providers.circleci_provider import CircleCIProvider
from devloop.providers.github_actions_provider import GitHubActionsProvider
from devloop.providers.gitlab_ci_provider import GitLabCIProvider
from devloop.providers.jenkins_provider import JenkinsProvider
from devloop.providers.provider_manager import ProviderManager, get_provider_manager
from devloop.providers.pypi_registry import PyPIRegistry
from devloop.providers.registry_provider import PackageRegistry

__all__ = [
    # Base classes
    "CIProvider",
    "PackageRegistry",
    # Enums and data classes
    "RunStatus",
    "RunConclusion",
    "WorkflowRun",
    "WorkflowDefinition",
    # CI Providers
    "GitHubActionsProvider",
    "GitLabCIProvider",
    "JenkinsProvider",
    "CircleCIProvider",
    # Registry Providers
    "PyPIRegistry",
    # Manager
    "ProviderManager",
    "get_provider_manager",
]
