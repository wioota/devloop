"""PyPI package registry provider implementation."""

import json
import os
import subprocess
from typing import List, Optional

from devloop.providers.registry_provider import PackageRegistry, PackageVersion


class PyPIRegistry(PackageRegistry):
    """Python Package Index (PyPI) registry provider."""

    def __init__(
        self, index_url: str = "https://pypi.org", api_token: Optional[str] = None
    ):
        """Initialize PyPI registry provider.

        Args:
            index_url: PyPI index URL (default: official PyPI)
            api_token: Optional API token for authentication
        """
        self.index_url = index_url
        self.api_token = api_token
        self._poetry_available = self._check_poetry_available()

    def publish(self, package_path: str, version: str) -> bool:
        """Publish a package to PyPI.

        Args:
            package_path: Path to package to publish
            version: Version string

        Returns:
            True if publication was successful
        """
        if not self._poetry_available:
            return False

        try:
            # Build the package
            subprocess.run(
                ["poetry", "build"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=package_path,
                check=True,
            )

            # Publish using poetry
            cmd = ["poetry", "publish"]
            if self.api_token:
                cmd.extend(["-u", "__token__", "-p", self.api_token])

            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=package_path,
                check=True,
            )
            return True

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def get_version(self, package_name: str) -> Optional[str]:
        """Get the latest published version of a package."""
        versions = self.get_versions(package_name, limit=1)
        return versions[0].version if versions else None

    def get_versions(self, package_name: str, limit: int = 10) -> List[PackageVersion]:
        """Get version history for a package."""
        try:
            # Use PyPI JSON API
            url = f"{self.index_url.rstrip('/')}/pypi/{package_name}/json"

            result = subprocess.run(
                ["curl", "-s", url],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            if not result.stdout.strip():
                return []

            data = json.loads(result.stdout)
            releases = data.get("releases", {})

            versions = []
            for version, release_files in sorted(
                releases.items(),
                reverse=True,
                key=lambda x: self._parse_version_key(x[0]),
            ):
                if len(versions) >= limit:
                    break

                # Get the release info from the overall info
                release_info = data.get("releases", {}).get(version, [])
                if release_info:
                    # Use the upload time from the first file
                    upload_time = release_info[0].get("upload_time", "")

                    try:
                        pv = PackageVersion(
                            version=version,
                            released_at=upload_time,
                            url=f"{self.index_url}/project/{package_name}/{version}/",
                        )
                        versions.append(pv)
                    except (ValueError, KeyError):
                        continue

            return versions

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
        ):
            return []

    def check_credentials(self) -> bool:
        """Check if registry credentials are valid.

        Checks both environment variables and poetry config for PyPI tokens.
        Poetry supports tokens via:
        - Environment variable: POETRY_PYPI_TOKEN_PYPI
        - Config: poetry config pypi-token.pypi <token>
        """
        if not self._poetry_available:
            return False

        # Check environment variable first (Poetry reads this automatically)
        if os.environ.get("POETRY_PYPI_TOKEN_PYPI"):
            return True

        # Also check PYPI_TOKEN as a fallback
        if os.environ.get("PYPI_TOKEN"):
            return True

        try:
            # Fall back to checking poetry config
            result = subprocess.run(
                ["poetry", "config", "pypi-token.pypi"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0

        except subprocess.TimeoutExpired:
            return False

    def is_available(self) -> bool:
        """Check if PyPI is accessible."""
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", self.index_url],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip().startswith("2")
        except subprocess.TimeoutExpired:
            return False

    def get_provider_name(self) -> str:
        """Get human-readable provider name."""
        return "PyPI"

    def get_package_url(self, package_name: str, version: Optional[str] = None) -> str:
        """Get the URL for a package in the registry."""
        if version:
            return f"{self.index_url.rstrip('/')}/project/{package_name}/{version}/"
        else:
            return f"{self.index_url.rstrip('/')}/project/{package_name}/"

    @staticmethod
    def _parse_version_key(version: str) -> tuple:
        """Parse version string for sorting."""
        try:
            parts = version.split(".")
            return tuple(
                int(p.split("a")[0].split("b")[0].split("rc")[0]) for p in parts
            )
        except (ValueError, IndexError):
            return (0,)

    @staticmethod
    def _check_poetry_available() -> bool:
        """Check if Poetry CLI is available."""
        try:
            result = subprocess.run(
                ["poetry", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
