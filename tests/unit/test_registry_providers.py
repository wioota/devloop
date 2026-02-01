"""Unit tests for registry provider implementations with mocked external calls."""

import json
import os
import subprocess
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError

import pytest

from devloop.providers.artifactory_registry import ArtifactoryRegistry
from devloop.providers.pypi_registry import PyPIRegistry
from devloop.providers.registry_provider import PackageVersion


class TestPyPIRegistry:
    """Tests for PyPI registry provider with mocked subprocess calls."""

    @patch("subprocess.run")
    def test_poetry_available(self, mock_run):
        """Test checking if poetry is available."""
        mock_run.return_value = Mock(returncode=0)
        registry = PyPIRegistry()
        assert registry._poetry_available is True

    @patch("subprocess.run")
    def test_poetry_not_available(self, mock_run):
        """Test when poetry is not installed."""
        mock_run.side_effect = FileNotFoundError()
        registry = PyPIRegistry()
        assert registry._poetry_available is False

    @patch("subprocess.run")
    def test_is_available_success(self, mock_run):
        """Test is_available when PyPI is reachable."""

        def side_effect(cmd, **kwargs):
            if "curl" in cmd and "-o" in cmd:
                return Mock(returncode=0, stdout="200")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()
        assert registry.is_available() is True

    @patch("subprocess.run")
    def test_is_available_timeout(self, mock_run):
        """Test is_available when request times out."""

        def side_effect(cmd, **kwargs):
            if "curl" in cmd and "-o" in cmd:
                raise subprocess.TimeoutExpired(cmd, 5)
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()
        assert registry.is_available() is False

    @patch("subprocess.run")
    def test_get_versions_success(self, mock_run):
        """Test getting package versions from PyPI."""
        pypi_response = {
            "releases": {
                "1.0.0": [
                    {
                        "upload_time": "2024-01-01T10:00:00",
                        "filename": "package-1.0.0.tar.gz",
                    }
                ],
                "1.1.0": [
                    {
                        "upload_time": "2024-01-15T10:00:00",
                        "filename": "package-1.1.0.tar.gz",
                    }
                ],
                "2.0.0": [
                    {
                        "upload_time": "2024-02-01T10:00:00",
                        "filename": "package-2.0.0.tar.gz",
                    }
                ],
            }
        }

        def side_effect(cmd, **kwargs):
            if "curl" in cmd and "pypi" in str(cmd):
                return Mock(returncode=0, stdout=json.dumps(pypi_response))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()
        versions = registry.get_versions("test-package", limit=10)

        assert len(versions) == 3
        # Should be sorted newest first
        version_strings = [v.version for v in versions]
        assert "2.0.0" in version_strings
        assert "1.1.0" in version_strings
        assert "1.0.0" in version_strings

    @patch("subprocess.run")
    def test_get_versions_empty_response(self, mock_run):
        """Test handling empty response."""

        def side_effect(cmd, **kwargs):
            if "curl" in cmd:
                return Mock(returncode=0, stdout="")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()
        versions = registry.get_versions("nonexistent-package")

        assert versions == []

    @patch("subprocess.run")
    def test_get_versions_json_error(self, mock_run):
        """Test handling malformed JSON response."""

        def side_effect(cmd, **kwargs):
            if "curl" in cmd:
                return Mock(returncode=0, stdout="not valid json{")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()
        versions = registry.get_versions("test-package")

        assert versions == []

    @patch("subprocess.run")
    def test_get_versions_timeout(self, mock_run):
        """Test handling timeout."""

        def side_effect(cmd, **kwargs):
            if "curl" in cmd and "pypi" in str(cmd):
                raise subprocess.TimeoutExpired(cmd, 10)
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()
        versions = registry.get_versions("test-package")

        assert versions == []

    @patch("subprocess.run")
    def test_get_versions_limit(self, mock_run):
        """Test version limit is respected."""
        pypi_response = {
            "releases": {
                f"1.{i}.0": [{"upload_time": f"2024-01-{i+1:02d}T10:00:00"}]
                for i in range(20)
            }
        }

        def side_effect(cmd, **kwargs):
            if "curl" in cmd:
                return Mock(returncode=0, stdout=json.dumps(pypi_response))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()
        versions = registry.get_versions("test-package", limit=5)

        assert len(versions) == 5

    @patch("subprocess.run")
    def test_get_version_returns_latest(self, mock_run):
        """Test get_version returns the latest version."""
        pypi_response = {
            "releases": {
                "1.0.0": [{"upload_time": "2024-01-01T10:00:00"}],
                "2.0.0": [{"upload_time": "2024-02-01T10:00:00"}],
            }
        }

        def side_effect(cmd, **kwargs):
            if "curl" in cmd:
                return Mock(returncode=0, stdout=json.dumps(pypi_response))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()
        version = registry.get_version("test-package")

        assert version == "2.0.0"

    @patch("subprocess.run")
    def test_get_version_no_versions(self, mock_run):
        """Test get_version when no versions exist."""
        pypi_response = {"releases": {}}

        def side_effect(cmd, **kwargs):
            if "curl" in cmd:
                return Mock(returncode=0, stdout=json.dumps(pypi_response))
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()
        version = registry.get_version("nonexistent")

        assert version is None

    @patch.dict(os.environ, {"POETRY_PYPI_TOKEN_PYPI": "test-token"})
    @patch("subprocess.run")
    def test_check_credentials_env_var(self, mock_run):
        """Test check_credentials with environment variable."""
        mock_run.return_value = Mock(returncode=0)
        registry = PyPIRegistry()

        assert registry.check_credentials() is True

    @patch.dict(os.environ, {"PYPI_TOKEN": "test-token"}, clear=True)
    @patch("subprocess.run")
    def test_check_credentials_pypi_token_env(self, mock_run):
        """Test check_credentials with PYPI_TOKEN environment variable."""
        mock_run.return_value = Mock(returncode=0)
        registry = PyPIRegistry()

        assert registry.check_credentials() is True

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    def test_check_credentials_poetry_config(self, mock_run):
        """Test check_credentials falls back to poetry config."""

        def side_effect(cmd, **kwargs):
            if "config" in cmd and "pypi-token" in cmd:
                return Mock(returncode=0, stdout="pypi-token")
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()

        assert registry.check_credentials() is True

    @patch("subprocess.run")
    def test_check_credentials_not_available(self, mock_run):
        """Test check_credentials when poetry is not available."""
        mock_run.side_effect = FileNotFoundError()
        registry = PyPIRegistry()

        assert registry.check_credentials() is False

    @patch("subprocess.run")
    def test_publish_success(self, mock_run):
        """Test successful package publication."""
        mock_run.return_value = Mock(returncode=0)
        registry = PyPIRegistry(api_token="test-token")

        result = registry.publish("/path/to/package", "1.0.0")

        assert result is True
        # Should have called poetry build and poetry publish
        assert mock_run.call_count >= 2

    @patch("subprocess.run")
    def test_publish_poetry_not_available(self, mock_run):
        """Test publish when poetry is not available."""
        mock_run.side_effect = FileNotFoundError()
        registry = PyPIRegistry()

        result = registry.publish("/path/to/package", "1.0.0")

        assert result is False

    @patch("subprocess.run")
    def test_publish_build_failure(self, mock_run):
        """Test publish when build fails."""

        def side_effect(cmd, **kwargs):
            if "build" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return Mock(returncode=0)

        mock_run.side_effect = side_effect
        registry = PyPIRegistry()

        result = registry.publish("/path/to/package", "1.0.0")

        assert result is False

    def test_get_package_url(self):
        """Test getting package URL."""
        registry = PyPIRegistry()

        url = registry.get_package_url("devloop", "1.0.0")
        assert "devloop" in url
        assert "1.0.0" in url
        assert "pypi.org" in url

    def test_get_package_url_no_version(self):
        """Test getting package URL without version."""
        registry = PyPIRegistry()

        url = registry.get_package_url("devloop")
        assert "devloop" in url
        assert "pypi.org" in url

    def test_parse_version_key(self):
        """Test version key parsing for sorting."""
        assert PyPIRegistry._parse_version_key("1.0.0") == (1, 0, 0)
        assert PyPIRegistry._parse_version_key("2.1.3") == (2, 1, 3)
        assert PyPIRegistry._parse_version_key("10.20.30") == (10, 20, 30)

    def test_parse_version_key_with_prerelease(self):
        """Test version key parsing with prerelease tags."""
        # Should extract numeric part before alpha/beta/rc
        assert PyPIRegistry._parse_version_key("1.0.0a1") == (1, 0, 0)
        assert PyPIRegistry._parse_version_key("1.0.0b2") == (1, 0, 0)
        assert PyPIRegistry._parse_version_key("1.0.0rc1") == (1, 0, 0)

    def test_parse_version_key_invalid(self):
        """Test version key parsing with invalid version."""
        result = PyPIRegistry._parse_version_key("invalid")
        assert result == (0,)

    def test_get_provider_name(self):
        """Test getting provider name."""
        registry = PyPIRegistry()
        assert registry.get_provider_name() == "PyPI"


class TestArtifactoryRegistry:
    """Tests for Artifactory registry provider with mocked HTTP requests."""

    def test_is_available_no_config(self):
        """Test availability without configuration."""
        registry = ArtifactoryRegistry()
        assert registry.is_available() is False

    def test_is_available_no_auth(self):
        """Test availability without authentication."""
        registry = ArtifactoryRegistry(base_url="https://artifactory.example.com")
        assert registry.is_available() is False

    @patch("urllib.request.urlopen")
    def test_is_available_with_token(self, mock_urlopen):
        """Test availability with API token."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )
        assert registry.is_available() is True

    @patch("urllib.request.urlopen")
    def test_is_available_with_basic_auth(self, mock_urlopen):
        """Test availability with username/password."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            username="admin",
            password="secret",
            repo="generic-repo",
        )
        assert registry.is_available() is True

    @patch("urllib.request.urlopen")
    def test_is_available_auth_failure(self, mock_urlopen):
        """Test availability with authentication failure."""
        mock_urlopen.side_effect = HTTPError(
            "https://artifactory.example.com/artifactory/api/system/ping",
            401,
            "Unauthorized",
            {},
            None,
        )

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="bad-token",
            repo="generic-repo",
        )
        assert registry.is_available() is False

    @patch("urllib.request.urlopen")
    def test_get_versions_success(self, mock_urlopen):
        """Test getting package versions from Artifactory."""
        aql_response = {
            "results": [
                {
                    "name": "package-2.0.0.jar",
                    "modified": "2024-02-01T10:00:00Z",
                    "sha256": "abc123",
                    "size": 1024,
                    "repo": "generic-repo",
                },
                {
                    "name": "package-1.0.0.jar",
                    "modified": "2024-01-01T10:00:00Z",
                    "sha256": "def456",
                    "size": 512,
                    "repo": "generic-repo",
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(aql_response).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )
        registry._available = True

        versions = registry.get_versions("package")

        assert len(versions) == 2
        assert versions[0].version == "2.0.0"
        assert versions[1].version == "1.0.0"

    @patch("urllib.request.urlopen")
    def test_get_versions_empty(self, mock_urlopen):
        """Test getting versions when no packages found."""
        aql_response = {"results": []}

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(aql_response).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )
        registry._available = True

        versions = registry.get_versions("nonexistent")

        assert versions == []

    def test_get_versions_not_available(self):
        """Test get_versions when registry is not available."""
        registry = ArtifactoryRegistry()
        versions = registry.get_versions("package")
        assert versions == []

    @patch("urllib.request.urlopen")
    def test_get_versions_limit(self, mock_urlopen):
        """Test version limit is respected."""
        aql_response = {
            "results": [
                {
                    "name": f"package-1.{i}.0.jar",
                    "modified": f"2024-01-{i+1:02d}T10:00:00Z",
                }
                for i in range(20)
            ]
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(aql_response).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )
        registry._available = True

        versions = registry.get_versions("package", limit=5)

        assert len(versions) == 5

    @patch("urllib.request.urlopen")
    def test_get_version_returns_latest(self, mock_urlopen):
        """Test get_version returns the latest version."""
        aql_response = {
            "results": [
                {"name": "package-2.0.0.jar", "modified": "2024-02-01T10:00:00Z"},
                {"name": "package-1.0.0.jar", "modified": "2024-01-01T10:00:00Z"},
            ]
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(aql_response).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )
        registry._available = True

        version = registry.get_version("package")

        assert version == "2.0.0"

    @patch("urllib.request.urlopen")
    def test_check_credentials_success(self, mock_urlopen):
        """Test check_credentials with valid token."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
        )

        assert registry.check_credentials() is True

    @patch("urllib.request.urlopen")
    def test_check_credentials_failure(self, mock_urlopen):
        """Test check_credentials with invalid token."""
        mock_urlopen.side_effect = HTTPError(
            "https://artifactory.example.com/artifactory/api/system/ping",
            401,
            "Unauthorized",
            {},
            None,
        )

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="bad-token",
        )

        assert registry.check_credentials() is False

    def test_check_credentials_no_url(self):
        """Test check_credentials without base URL."""
        registry = ArtifactoryRegistry()
        assert registry.check_credentials() is False

    @patch("urllib.request.urlopen")
    @patch("builtins.open", create=True)
    def test_publish_success(self, mock_open, mock_urlopen):
        """Test successful package publication."""
        mock_open.return_value.__enter__ = Mock(
            return_value=MagicMock(read=Mock(return_value=b"package contents"))
        )
        mock_open.return_value.__exit__ = Mock(return_value=False)

        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )
        registry._available = True

        result = registry.publish("/path/to/package.jar", "1.0.0")

        assert result is True

    def test_publish_not_available(self):
        """Test publish when registry is not available."""
        registry = ArtifactoryRegistry()
        result = registry.publish("/path/to/package.jar", "1.0.0")
        assert result is False

    def test_publish_no_repo(self):
        """Test publish without repo configured."""
        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
        )
        registry._available = True

        result = registry.publish("/path/to/package.jar", "1.0.0")
        assert result is False

    def test_get_package_url(self):
        """Test getting package URL."""
        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )

        url = registry.get_package_url("my-package", "1.0.0")
        assert "artifactory" in url
        assert "my-package" in url
        assert "1.0.0" in url

    def test_get_package_url_no_version(self):
        """Test getting package URL without version."""
        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            repo="generic-repo",
        )

        url = registry.get_package_url("my-package")
        assert "artifactory" in url
        assert "my-package" in url

    def test_get_provider_name(self):
        """Test getting provider name."""
        registry = ArtifactoryRegistry()
        assert registry.get_provider_name() == "Artifactory"

    def test_extract_version_from_name(self):
        """Test extracting version from filename."""
        assert (
            ArtifactoryRegistry._extract_version_from_name("package-1.0.0.jar")
            == "1.0.0"
        )
        assert (
            ArtifactoryRegistry._extract_version_from_name("lib-2.5.1.whl") == "2.5.1"
        )
        assert (
            ArtifactoryRegistry._extract_version_from_name("app-10.20.30.tar.gz")
            == "10.20.30"
        )

    def test_extract_version_from_name_with_suffix(self):
        """Test extracting version with prerelease suffix."""
        assert (
            ArtifactoryRegistry._extract_version_from_name("package-1.0.0-beta.jar")
            == "1.0.0-beta"
        )
        assert (
            ArtifactoryRegistry._extract_version_from_name("package-2.0.0-alpha1.jar")
            == "2.0.0-alpha1"
        )

    def test_extract_version_from_name_no_version(self):
        """Test extracting version when no version pattern found."""
        assert ArtifactoryRegistry._extract_version_from_name("package.jar") is None
        assert ArtifactoryRegistry._extract_version_from_name("no-version-here") is None

    def test_get_auth_headers_token(self):
        """Test auth headers with API token."""
        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
        )

        headers = registry._get_auth_headers()
        assert "X-JFrog-Art-Api" in headers
        assert headers["X-JFrog-Art-Api"] == "test-token"

    def test_get_auth_headers_basic(self):
        """Test auth headers with basic auth."""
        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            username="admin",
            password="secret",
        )

        headers = registry._get_auth_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    def test_get_auth_headers_token_priority(self):
        """Test that token takes priority over basic auth."""
        registry = ArtifactoryRegistry(
            base_url="https://artifactory.example.com/artifactory",
            api_token="test-token",
            username="admin",
            password="secret",
        )

        headers = registry._get_auth_headers()
        assert "X-JFrog-Art-Api" in headers
        assert "Authorization" not in headers


class TestPackageVersion:
    """Tests for PackageVersion data class."""

    def test_package_version_creation(self):
        """Test PackageVersion creation."""
        pv = PackageVersion(
            version="1.0.0",
            released_at="2024-01-01T10:00:00Z",
            url="https://example.com/package/1.0.0",
        )

        assert pv.version == "1.0.0"
        assert pv.released_at == "2024-01-01T10:00:00Z"
        assert pv.url == "https://example.com/package/1.0.0"

    def test_package_version_with_checksum(self):
        """Test PackageVersion with checksum."""
        pv = PackageVersion(
            version="1.0.0",
            released_at="2024-01-01T10:00:00Z",
            url="https://example.com/package/1.0.0",
            checksum="sha256:abc123",
        )

        assert pv.checksum == "sha256:abc123"

    def test_package_version_with_metadata(self):
        """Test PackageVersion with metadata."""
        pv = PackageVersion(
            version="1.0.0",
            released_at="2024-01-01T10:00:00Z",
            url="https://example.com/package/1.0.0",
            metadata={"size": 1024, "downloads": 100},
        )

        assert pv.metadata["size"] == 1024
        assert pv.metadata["downloads"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
