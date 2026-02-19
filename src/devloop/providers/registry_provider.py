"""Abstract base class for package registry providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PackageVersion:
    """Represents a package version in a registry."""

    version: str
    released_at: str
    url: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RegistryCredentials:
    """Credentials for accessing a package registry."""

    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None
    endpoint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PackageRegistry(ABC):
    """Abstract base class for package registry providers."""

    @abstractmethod
    def publish(self, package_path: str, version: str) -> bool:
        """Publish a package to the registry.

        Args:
            package_path: Path to package to publish
            version: Version string

        Returns:
            True if publication was successful
        """
        pass

    @abstractmethod
    def get_version(self, package_name: str) -> Optional[str]:
        """Get the latest published version of a package.

        Args:
            package_name: Package name

        Returns:
            Version string or None if package not found
        """
        pass

    @abstractmethod
    def get_versions(self, package_name: str, limit: int = 10) -> list[PackageVersion]:
        """Get version history for a package.

        Args:
            package_name: Package name
            limit: Maximum number of versions to return

        Returns:
            List of PackageVersion objects
        """
        pass

    @abstractmethod
    def check_credentials(self) -> bool:
        """Check if registry credentials are valid.

        Returns:
            True if credentials are valid and authenticated
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if registry is available and accessible.

        Returns:
            True if registry is available
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get human-readable provider name.

        Returns:
            Provider name (e.g., "PyPI", "Artifactory")
        """
        pass

    @abstractmethod
    def get_package_url(self, package_name: str, version: Optional[str] = None) -> str:
        """Get the URL for a package in the registry.

        Args:
            package_name: Package name
            version: Optional specific version

        Returns:
            URL string
        """
        pass
