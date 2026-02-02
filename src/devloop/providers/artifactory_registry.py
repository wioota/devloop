"""Artifactory package registry provider implementation."""

import json
import os
import urllib.request
from base64 import b64encode
from typing import List, Optional
from urllib.error import HTTPError, URLError

from devloop.providers.registry_provider import PackageRegistry, PackageVersion


class ArtifactoryRegistry(PackageRegistry):
    """Artifactory package registry provider."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        repo: Optional[str] = None,
    ):
        """Initialize Artifactory registry provider.

        Args:
            base_url: Artifactory base URL (e.g., https://artifactory.example.com/artifactory)
            api_token: Artifactory API token
            username: Optional username (alternative to api_token)
            password: Optional password (alternative to api_token)
            repo: Default repository name (can be overridden per call)

        Environment variables (if args not provided):
            ARTIFACTORY_URL: Artifactory base URL
            ARTIFACTORY_TOKEN: Artifactory API token
            ARTIFACTORY_USER: Username
            ARTIFACTORY_PASSWORD: Password
            ARTIFACTORY_REPO: Default repository
        """
        self.base_url = (base_url or os.getenv("ARTIFACTORY_URL", "")).rstrip("/")
        self.api_token = api_token or os.getenv("ARTIFACTORY_TOKEN")
        self.username = username or os.getenv("ARTIFACTORY_USER")
        self.password = password or os.getenv("ARTIFACTORY_PASSWORD")
        self.repo = repo or os.getenv("ARTIFACTORY_REPO")

        self._available = self._check_available()

    def publish(self, package_path: str, version: str) -> bool:
        """Publish a package to Artifactory.

        Args:
            package_path: Path to package to publish
            version: Version string

        Returns:
            True if publication was successful
        """
        if not self.is_available() or not self.repo:
            return False

        try:
            # Read package file
            with open(package_path, "rb") as f:
                package_data = f.read()

            # Extract package name from path
            package_name = os.path.basename(package_path)

            # Build upload URL
            url = f"{self.base_url}/{self.repo}/{package_name}"

            # Create request with auth
            request = urllib.request.Request(
                url,
                data=package_data,
                method="PUT",
                headers=self._get_auth_headers(),
            )

            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status in (200, 201)

        except (HTTPError, URLError, OSError, Exception):
            return False

    def get_version(self, package_name: str) -> Optional[str]:
        """Get the latest published version of a package.

        Args:
            package_name: Package name

        Returns:
            Version string or None if package not found
        """
        versions = self.get_versions(package_name, limit=1)
        return versions[0].version if versions else None

    def get_versions(self, package_name: str, limit: int = 10) -> List[PackageVersion]:
        """Get version history for a package.

        Args:
            package_name: Package name
            limit: Maximum number of versions to return

        Returns:
            List of PackageVersion objects
        """
        if not self.is_available() or not self.repo:
            return []

        try:
            # Use Artifactory AQL for listing versions
            # Query format: items.find({"name": "<package>", "repo": "<repo>"})
            aql_query = (
                f'items.find({{"name": "{package_name}*", "repo": "{self.repo}"}})'
            )

            url = f"{self.base_url}/api/search/aql"
            request = urllib.request.Request(
                url,
                data=aql_query.encode(),
                method="POST",
                headers={
                    **self._get_auth_headers(),
                    "Content-Type": "text/plain",
                },
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())

            versions = []
            results = data.get("results", [])

            # Sort by modified date (newest first)
            results.sort(
                key=lambda x: x.get("modified", ""),
                reverse=True,
            )

            for item in results[:limit]:
                try:
                    version_str = self._extract_version_from_name(item.get("name", ""))
                    if version_str:
                        pv = PackageVersion(
                            version=version_str,
                            released_at=item.get("modified", ""),
                            url=f"{self.base_url}/{self.repo}/{item.get('name', '')}",
                            checksum=item.get("sha256"),
                            metadata={
                                "size": item.get("size"),
                                "repo": item.get("repo"),
                            },
                        )
                        versions.append(pv)
                except (ValueError, KeyError):
                    continue

            return versions

        except (HTTPError, URLError, json.JSONDecodeError, Exception):
            return []

    def check_credentials(self) -> bool:
        """Check if registry credentials are valid.

        Returns:
            True if credentials are valid and authenticated
        """
        if not self.base_url:
            return False

        try:
            url = f"{self.base_url}/api/system/ping"
            request = urllib.request.Request(
                url,
                method="GET",
                headers=self._get_auth_headers(),
            )

            with urllib.request.urlopen(request, timeout=5) as response:
                return bool(response.status == 200)

        except (HTTPError, URLError, Exception):
            return False

    def is_available(self) -> bool:
        """Check if Artifactory is available and accessible.

        Returns:
            True if registry is available
        """
        return self._available

    def get_provider_name(self) -> str:
        """Get human-readable provider name.

        Returns:
            Provider name
        """
        return "Artifactory"

    def get_package_url(self, package_name: str, version: Optional[str] = None) -> str:
        """Get the URL for a package in the registry.

        Args:
            package_name: Package name
            version: Optional specific version

        Returns:
            URL string
        """
        if version:
            return f"{self.base_url}/{self.repo}/{package_name}-{version}"
        else:
            return f"{self.base_url}/{self.repo}/{package_name}"

    def _check_available(self) -> bool:
        """Check if Artifactory is available and credentials are valid."""
        if not self.base_url:
            return False

        # Check if we have at least one auth method
        has_auth = self.api_token or (self.username and self.password)
        if not has_auth:
            return False

        return self.check_credentials()

    def _get_auth_headers(self) -> dict:
        """Get authorization headers for Artifactory API.

        Returns:
            Dictionary with auth headers
        """
        headers = {}

        if self.api_token:
            # Token-based authentication
            headers["X-JFrog-Art-Api"] = self.api_token
        elif self.username and self.password:
            # Basic authentication
            credentials = f"{self.username}:{self.password}"
            auth_header = b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {auth_header}"

        return headers

    @staticmethod
    def _extract_version_from_name(filename: str) -> Optional[str]:
        """Extract version string from package filename.

        Args:
            filename: Package filename

        Returns:
            Version string or None
        """
        # Common patterns: package-1.0.0.jar, package-1.0.0.whl, etc.
        import re

        # Look for version pattern: dash followed by semver
        match = re.search(r"-(\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)", filename)
        if match:
            return match.group(1)

        return None
