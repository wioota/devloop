"""Tests for agent publishing and maintenance tools."""

import json
import pytest
import tempfile
from pathlib import Path

from devloop.marketplace.publisher import (
    AgentPackage,
    AgentPublisher,
    VersionManager,
    DeprecationManager,
)
from devloop.marketplace.registry_client import create_registry_client


@pytest.fixture
def temp_registry_dir():
    """Create temporary registry directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_agent_dir():
    """Create a temporary agent directory with valid structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agent_dir = Path(tmpdir)

        # Create agent.json
        agent_json = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test agent",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
        }

        with open(agent_dir / "agent.json", "w") as f:
            json.dump(agent_json, f)

        # Create README.md
        (agent_dir / "README.md").write_text("# Test Agent\n\nTest description")

        # Create __init__.py
        (agent_dir / "__init__.py").write_text("# Agent implementation")

        yield agent_dir


@pytest.fixture
def registry_client(temp_registry_dir):
    """Create registry client."""
    return create_registry_client(temp_registry_dir)


@pytest.fixture
def publisher(registry_client):
    """Create publisher instance."""
    return AgentPublisher(registry_client)


class TestAgentPackage:
    """Test AgentPackage class."""

    def test_package_initialization(self, temp_agent_dir):
        """Test initializing an agent package."""
        package = AgentPackage(temp_agent_dir)

        assert package.metadata.name == "test-agent"
        assert package.metadata.version == "1.0.0"

    def test_package_validation_valid(self, temp_agent_dir):
        """Test validating a valid package."""
        package = AgentPackage(temp_agent_dir)
        is_valid, errors = package.validate()

        assert is_valid is True
        assert len(errors) == 0

    def test_package_validation_missing_readme(self, temp_agent_dir):
        """Test validation with missing README."""
        (temp_agent_dir / "README.md").unlink()

        package = AgentPackage(temp_agent_dir)
        is_valid, errors = package.validate()

        assert is_valid is False
        assert any("README" in str(e) for e in errors)

    def test_package_validation_missing_implementation(self, temp_agent_dir):
        """Test validation with missing implementation."""
        (temp_agent_dir / "__init__.py").unlink()

        package = AgentPackage(temp_agent_dir)
        is_valid, errors = package.validate()

        assert is_valid is False
        assert any("implementation" in str(e).lower() for e in errors)

    def test_package_checksum(self, temp_agent_dir):
        """Test calculating package checksum."""
        package = AgentPackage(temp_agent_dir)
        checksum = package.get_checksum()

        assert len(checksum) == 64  # SHA256 hex length
        assert checksum.isalnum()

    def test_package_create_tarball(self, temp_agent_dir):
        """Test creating a tarball."""
        package = AgentPackage(temp_agent_dir)

        output_dir = Path(tempfile.gettempdir())
        tarball_path = package.create_tarball(output_dir)

        assert tarball_path.exists()
        assert tarball_path.name == "test-agent-1.0.0.tar.gz"

        # Clean up
        tarball_path.unlink()


class TestAgentPublisher:
    """Test AgentPublisher class."""

    def test_publish_valid_agent(self, publisher, temp_agent_dir):
        """Test publishing a valid agent."""
        success, message = publisher.publish_agent(temp_agent_dir)

        assert success is True
        assert "test-agent" in message

    def test_publish_invalid_agent(self, publisher, temp_agent_dir):
        """Test publishing an invalid agent."""
        # Make it invalid
        (temp_agent_dir / "README.md").unlink()

        success, message = publisher.publish_agent(temp_agent_dir)

        assert success is False
        assert "validation" in message.lower()

    def test_publish_duplicate_version(self, publisher, temp_agent_dir):
        """Test publishing duplicate version."""
        # Publish once
        success1, _ = publisher.publish_agent(temp_agent_dir)
        assert success1 is True

        # Try to publish again
        success2, message = publisher.publish_agent(temp_agent_dir)

        assert success2 is False
        assert "already published" in message.lower()

    def test_publish_force_override(self, publisher, temp_agent_dir):
        """Test force publishing to override existing."""
        # Publish once
        publisher.publish_agent(temp_agent_dir)

        # Force publish again
        success, message = publisher.publish_agent(temp_agent_dir, force=True)

        assert success is True

    def test_check_updates_new_agent(self, publisher, temp_agent_dir):
        """Test checking updates for new agent."""
        result = publisher.check_updates(temp_agent_dir)

        assert result["has_updates"] is False
        assert result["local_version"] == "1.0.0"

    def test_check_updates_with_published(self, publisher, temp_agent_dir):
        """Test checking updates with published version."""
        # Publish first
        publisher.publish_agent(temp_agent_dir)

        # Update local version
        agent_json = temp_agent_dir / "agent.json"
        with open(agent_json) as f:
            data = json.load(f)
        data["version"] = "2.0.0"
        with open(agent_json, "w") as f:
            json.dump(data, f)

        # Check updates
        result = publisher.check_updates(temp_agent_dir)

        assert result["has_updates"] is True
        assert result["local_version"] == "2.0.0"
        assert result["published_version"] == "1.0.0"

    def test_get_publish_readiness_ready(self, publisher, temp_agent_dir):
        """Test publish readiness for valid agent."""
        result = publisher.get_publish_readiness(temp_agent_dir)

        assert result["ready"] is True
        assert result["checks"]["metadata"] is True
        assert result["checks"]["implementation"] is True

    def test_get_publish_readiness_not_ready(self, publisher, temp_agent_dir):
        """Test publish readiness for invalid agent."""
        # Make it invalid
        (temp_agent_dir / "__init__.py").unlink()

        result = publisher.get_publish_readiness(temp_agent_dir)

        assert result["ready"] is False
        assert len(result["errors"]) > 0

    def test_get_publish_readiness_with_warnings(self, publisher, temp_agent_dir):
        """Test publish readiness with warnings."""
        # First publish
        publisher.publish_agent(temp_agent_dir)

        # Check readiness (should warn about duplicate version)
        result = publisher.get_publish_readiness(temp_agent_dir)

        assert len(result["warnings"]) > 0


class TestVersionManager:
    """Test VersionManager class."""

    def test_bump_patch_version(self):
        """Test bumping patch version."""
        new_version = VersionManager.bump_version("1.0.0", "patch")
        assert new_version == "1.0.1"

    def test_bump_minor_version(self):
        """Test bumping minor version."""
        new_version = VersionManager.bump_version("1.0.0", "minor")
        assert new_version == "1.1.0"

    def test_bump_major_version(self):
        """Test bumping major version."""
        new_version = VersionManager.bump_version("1.0.0", "major")
        assert new_version == "2.0.0"

    def test_bump_version_multiple_times(self):
        """Test bumping version multiple times."""
        version = "1.0.0"
        version = VersionManager.bump_version(version, "patch")
        assert version == "1.0.1"

        version = VersionManager.bump_version(version, "patch")
        assert version == "1.0.2"

        version = VersionManager.bump_version(version, "minor")
        assert version == "1.1.0"

    def test_update_agent_json_version(self, temp_agent_dir):
        """Test updating version in agent.json."""
        success = VersionManager.update_agent_json(temp_agent_dir, "2.0.0")

        assert success is True

        # Verify update
        with open(temp_agent_dir / "agent.json") as f:
            data = json.load(f)
        assert data["version"] == "2.0.0"

    def test_update_agent_json_nonexistent_dir(self):
        """Test updating version in nonexistent directory."""
        nonexistent = Path("/nonexistent/path")
        success = VersionManager.update_agent_json(nonexistent, "2.0.0")

        assert success is False


class TestDeprecationManager:
    """Test DeprecationManager class."""

    def test_deprecate_agent(self, registry_client, temp_agent_dir):
        """Test deprecating an agent."""
        publisher = AgentPublisher(registry_client)
        manager = DeprecationManager(registry_client)

        # First publish
        publisher.publish_agent(temp_agent_dir)

        # Then deprecate
        success, message = manager.deprecate_agent(
            "test-agent", "This agent is no longer maintained"
        )

        assert success is True
        assert "test-agent" in message

    def test_deprecate_with_replacement(self, registry_client, temp_agent_dir):
        """Test deprecating with replacement suggestion."""
        publisher = AgentPublisher(registry_client)
        manager = DeprecationManager(registry_client)

        # Publish first
        publisher.publish_agent(temp_agent_dir)

        # Deprecate with replacement
        success, message = manager.deprecate_agent(
            "test-agent", "Use new-agent instead", replacement="new-agent"
        )

        assert success is True

    def test_get_deprecation_info_active(self, registry_client, temp_agent_dir):
        """Test getting deprecation info for active agent."""
        publisher = AgentPublisher(registry_client)
        manager = DeprecationManager(registry_client)

        # Publish agent
        publisher.publish_agent(temp_agent_dir)

        # Get info
        info = manager.get_deprecation_info("test-agent")

        assert info["found"] is True
        assert info["deprecated"] is False

    def test_get_deprecation_info_deprecated(self, registry_client, temp_agent_dir):
        """Test getting deprecation info for deprecated agent."""
        publisher = AgentPublisher(registry_client)
        manager = DeprecationManager(registry_client)

        # Publish and deprecate
        publisher.publish_agent(temp_agent_dir)
        manager.deprecate_agent("test-agent", "No longer maintained")

        # Get info
        info = manager.get_deprecation_info("test-agent")

        assert info["found"] is True
        assert info["deprecated"] is True

    def test_get_deprecation_info_nonexistent(self, registry_client):
        """Test getting deprecation info for nonexistent agent."""
        manager = DeprecationManager(registry_client)
        info = manager.get_deprecation_info("nonexistent")

        assert info["found"] is False

    def test_undeprecate_agent(self, registry_client, temp_agent_dir):
        """Test removing deprecation."""
        publisher = AgentPublisher(registry_client)
        manager = DeprecationManager(registry_client)

        # Publish and deprecate
        publisher.publish_agent(temp_agent_dir)
        manager.deprecate_agent("test-agent", "Test")

        # Undeprecate
        success, message = manager.undeprecate_agent("test-agent")

        assert success is True

        # Verify
        info = manager.get_deprecation_info("test-agent")
        assert info["deprecated"] is False


if __name__ == "__main__":
    pytest.main([__file__])
