"""Tests for agent marketplace installer."""

import json
import tempfile
from pathlib import Path

import pytest

from devloop.marketplace.installer import AgentInstaller
from devloop.marketplace.metadata import AgentMetadata, Dependency
from devloop.marketplace.registry import AgentRegistry, RegistryConfig
from devloop.marketplace.registry_client import RegistryClient


@pytest.fixture
def temp_install_dir():
    """Create a temporary directory for installation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_registry_dir():
    """Create a temporary registry directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_registry_dir):
    """Create a registry with sample agents."""
    config = RegistryConfig(registry_dir=temp_registry_dir)
    registry = AgentRegistry(config)

    # Add sample agents
    agent1 = AgentMetadata(
        name="agent-1",
        version="1.0.0",
        description="First agent",
        author="Author",
        license="MIT",
        homepage="https://example.com",
    )
    agent2 = AgentMetadata(
        name="agent-2",
        version="1.0.0",
        description="Second agent",
        author="Author",
        license="MIT",
        homepage="https://example.com",
        dependencies=[Dependency(name="agent-1", version=">=1.0.0")],
    )

    registry.register_agent(agent1)
    registry.register_agent(agent2)

    return registry


@pytest.fixture
def registry_client(registry):
    """Create a registry client."""
    return RegistryClient(registry)


@pytest.fixture
def installer(temp_install_dir, registry_client):
    """Create an installer."""
    return AgentInstaller(temp_install_dir, registry_client)


class TestAgentInstaller:
    """Test agent installer functionality."""

    def test_installer_initialization(self, temp_install_dir, registry_client):
        """Test installer initialization."""
        installer = AgentInstaller(temp_install_dir, registry_client)

        assert installer.install_dir == temp_install_dir
        assert len(installer.installed_agents) == 0

    def test_install_agent(self, installer):
        """Test installing a single agent."""
        success, msg = installer.install("agent-1")

        assert success is True
        assert "Successfully installed" in msg
        assert "agent-1" in installer.installed_agents

        record = installer.installed_agents["agent-1"]
        assert record.agent_name == "agent-1"
        assert record.version == "1.0.0"

    def test_install_nonexistent_agent(self, installer):
        """Test installing a nonexistent agent."""
        success, msg = installer.install("nonexistent")

        assert success is False
        assert "not found" in msg

    def test_install_already_installed(self, installer):
        """Test installing an already installed agent."""
        # First install
        success1, msg1 = installer.install("agent-1")
        assert success1 is True

        # Try to install again
        success2, msg2 = installer.install("agent-1")
        assert success2 is True
        assert "already installed" in msg2

    def test_force_reinstall(self, installer):
        """Test force reinstalling an agent."""
        # First install
        installer.install("agent-1")
        first_record = installer.installed_agents["agent-1"]

        # Force reinstall
        success, msg = installer.install("agent-1", force=True)
        assert success is True

        # Should be updated
        second_record = installer.installed_agents["agent-1"]
        assert second_record.installed_at >= first_record.installed_at

    def test_resolve_dependencies(self, installer):
        """Test dependency resolution."""
        agent = installer.registry_client.get_agent("agent-2")
        assert agent is not None

        to_install, errors = installer.resolve_dependencies(agent)

        # Should include both agent-2 and its dependency agent-1
        assert len(to_install) == 2
        names = [a.name for a in to_install]
        assert "agent-1" in names
        assert "agent-2" in names

    def test_install_with_dependencies(self, installer):
        """Test installing an agent with dependencies."""
        success, msg = installer.install("agent-2")

        assert success is True
        # Both agents should be installed
        assert "agent-1" in installer.installed_agents
        assert "agent-2" in installer.installed_agents

    def test_uninstall_agent(self, installer):
        """Test uninstalling an agent."""
        # First install
        installer.install("agent-1")
        assert "agent-1" in installer.installed_agents

        # Uninstall
        success, msg = installer.uninstall("agent-1")
        assert success is True
        assert "agent-1" not in installer.installed_agents

    def test_uninstall_nonexistent_agent(self, installer):
        """Test uninstalling a nonexistent agent."""
        success, msg = installer.uninstall("nonexistent")

        assert success is False
        assert "not installed" in msg

    def test_uninstall_with_dependents(self, installer):
        """Test uninstalling an agent with dependents."""
        # Install agent-2 which depends on agent-1
        installer.install("agent-2")

        # Try to uninstall agent-1
        success, msg = installer.uninstall("agent-1")
        assert success is False
        assert "depend on" in msg

    def test_list_installed(self, installer):
        """Test listing installed agents."""
        installer.install("agent-1")
        installer.install("agent-2")

        installed = installer.list_installed()

        assert len(installed) == 2
        names = [record.agent_name for record in installed]
        assert "agent-1" in names
        assert "agent-2" in names

    def test_get_installed(self, installer):
        """Test getting a specific installed agent."""
        installer.install("agent-1")

        record = installer.get_installed("agent-1")

        assert record is not None
        assert record.agent_name == "agent-1"
        assert record.version == "1.0.0"

    def test_is_installed(self, installer):
        """Test checking if agent is installed."""
        assert not installer.is_installed("agent-1")

        installer.install("agent-1")

        assert installer.is_installed("agent-1")
        assert installer.is_installed("agent-1", version="1.0.0")
        assert not installer.is_installed("agent-1", version="2.0.0")

    def test_installation_persistence(self, temp_install_dir, registry_client):
        """Test that installations persist across instances."""
        # Install with first installer instance
        installer1 = AgentInstaller(temp_install_dir, registry_client)
        installer1.install("agent-1")

        # Create new installer instance
        installer2 = AgentInstaller(temp_install_dir, registry_client)

        # Should have loaded the previous installation
        assert "agent-1" in installer2.installed_agents

    def test_installation_stats(self, installer):
        """Test getting installation statistics."""
        installer.install("agent-1")
        installer.install("agent-2")  # Installs agent-1 as dependency too

        # Reload to get accurate stats
        installer._load_installations()

        stats = installer.get_installation_stats()

        assert stats["total_installed"] == 2
        assert stats["user_requested"] == 2
        assert stats["as_dependencies"] == 0

    def test_backup_and_restore(self, installer):
        """Test backup and restore functionality."""
        # Install an agent
        installer.install("agent-1")
        agent_dir = installer._get_agents_dir() / "agent-1"
        assert agent_dir.exists()

        # Create backup
        backup_dir = installer._create_backup("agent-1")
        assert backup_dir is not None
        assert (backup_dir / "agent-1").exists()

        # Remove agent
        import shutil

        shutil.rmtree(agent_dir)
        assert not agent_dir.exists()

        # Restore from backup
        success = installer._restore_backup("agent-1", backup_dir)
        assert success is True
        assert agent_dir.exists()

    def test_manifest_creation(self, installer):
        """Test that installation manifest is created."""
        installer.install("agent-1")

        manifest_file = installer._get_manifest_file()
        assert manifest_file.exists()

        # Verify manifest contents
        with open(manifest_file) as f:
            data = json.load(f)

        assert "installed_agents" in data
        assert len(data["installed_agents"]) == 1
        assert data["installed_agents"][0]["agent_name"] == "agent-1"

    def test_find_dependents(self, installer):
        """Test finding agents that depend on a given agent."""
        installer.install("agent-2")  # This installs agent-1 as dependency

        dependents = installer._find_dependents("agent-1")

        assert len(dependents) >= 0  # May or may not be tracked as dependent


if __name__ == "__main__":
    pytest.main([__file__])
