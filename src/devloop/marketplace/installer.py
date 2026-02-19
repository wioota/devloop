"""Agent installation and dependency resolution."""

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .metadata import AgentMetadata
from .registry_client import RegistryClient

logger = logging.getLogger(__name__)


@dataclass
class InstallationRecord:
    """Record of an installed agent."""

    agent_name: str
    version: str
    installed_at: str
    location: Path
    dependencies: List[str]
    installed_by_user: bool = True  # vs installed as dependency


class AgentInstaller:
    """Install agents and resolve dependencies."""

    def __init__(self, install_dir: Path, registry_client: RegistryClient):
        """Initialize installer."""
        self.install_dir = install_dir
        self.registry_client = registry_client
        self.installed_agents: Dict[str, InstallationRecord] = {}
        self._load_installations()

    def _get_agents_dir(self) -> Path:
        """Get directory where agents are installed."""
        return self.install_dir / "agents"

    def _get_manifest_file(self) -> Path:
        """Get installation manifest file."""
        return self.install_dir / "manifest.json"

    def _load_installations(self) -> None:
        """Load installation manifest."""
        manifest_file = self._get_manifest_file()

        if not manifest_file.exists():
            self.installed_agents = {}
            return

        try:
            with open(manifest_file) as f:
                data = json.load(f)

            for agent_data in data.get("installed_agents", []):
                record = InstallationRecord(
                    agent_name=agent_data["agent_name"],
                    version=agent_data["version"],
                    installed_at=agent_data["installed_at"],
                    location=Path(agent_data["location"]),
                    dependencies=agent_data.get("dependencies", []),
                    installed_by_user=agent_data.get("installed_by_user", True),
                )
                self.installed_agents[agent_data["agent_name"]] = record

            logger.info(f"Loaded {len(self.installed_agents)} installed agents")
        except Exception as e:
            logger.error(f"Failed to load installations: {e}")
            self.installed_agents = {}

    def _save_installations(self) -> None:
        """Save installation manifest."""
        manifest_file = self._get_manifest_file()

        data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "installed_agents": [
                {
                    "agent_name": record.agent_name,
                    "version": record.version,
                    "installed_at": record.installed_at,
                    "location": str(record.location),
                    "dependencies": record.dependencies,
                    "installed_by_user": record.installed_by_user,
                }
                for record in self.installed_agents.values()
            ],
        }

        try:
            self._get_agents_dir().mkdir(parents=True, exist_ok=True)
            with open(manifest_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save installations: {e}")

    def resolve_dependencies(
        self, agent: AgentMetadata
    ) -> Tuple[List[AgentMetadata], List[str]]:
        """
        Resolve all dependencies for an agent.

        Returns (list of agents to install, list of error messages).
        """
        to_install = []
        errors = []
        visited: Set[str] = set()
        queue = [(agent, True)]  # (agent, installed_by_user)

        while queue:
            current_agent, is_user_requested = queue.pop(0)

            if current_agent.name in visited:
                continue

            visited.add(current_agent.name)

            # Check if already installed
            if current_agent.name in self.installed_agents:
                installed = self.installed_agents[current_agent.name]
                if installed.version == current_agent.version:
                    logger.debug(f"Agent {current_agent.name} already installed")
                    continue
                else:
                    errors.append(
                        f"Agent {current_agent.name} already installed with version "
                        f"{installed.version}, requested {current_agent.version}"
                    )
                    continue

            to_install.append(current_agent)

            # Add dependencies to queue
            for dep in current_agent.dependencies:
                if not dep.optional:  # Skip optional dependencies for now
                    dep_agent = self.registry_client.get_agent(dep.name)
                    if dep_agent:
                        queue.append((dep_agent, False))
                    else:
                        errors.append(f"Dependency {dep.name} not found in registry")

        return to_install, errors

    def install(
        self,
        agent_name: str,
        version: Optional[str] = None,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """
        Install an agent.

        Returns (success, message).
        """
        # Get agent metadata
        agent = self.registry_client.get_agent(agent_name, version)
        if not agent:
            return False, f"Agent {agent_name} not found"

        # Check if already installed
        if agent_name in self.installed_agents and not force:
            existing = self.installed_agents[agent_name]
            if existing.version == agent.version:
                return True, f"Agent {agent_name}@{agent.version} already installed"
            return False, (
                f"Agent {agent_name}@{existing.version} already installed. "
                "Use --force to upgrade"
            )

        # Resolve dependencies
        to_install, errors = self.resolve_dependencies(agent)
        if errors:
            logger.warning(f"Dependency resolution issues: {errors}")

        # Create backup if updating
        backup_dir = None
        if agent_name in self.installed_agents:
            backup_dir = self._create_backup(agent_name)

        try:
            # Install all agents in dependency order
            for install_agent in to_install:
                success, msg = self._install_agent(
                    install_agent, is_user_requested=(install_agent.name == agent_name)
                )
                if not success:
                    # Rollback on failure
                    if backup_dir:
                        self._restore_backup(agent_name, backup_dir)
                    return False, f"Failed to install {install_agent.name}: {msg}"

            # Record download
            self.registry_client.download_agent(agent_name)

            return (
                True,
                f"Successfully installed {agent_name}@{agent.version} and dependencies",
            )

        except Exception as e:
            # Rollback on error
            if backup_dir:
                self._restore_backup(agent_name, backup_dir)
            return False, f"Installation error: {str(e)}"
        finally:
            # Cleanup backup
            if backup_dir and backup_dir.exists():
                shutil.rmtree(backup_dir)

    def _install_agent(
        self, agent: AgentMetadata, is_user_requested: bool = True
    ) -> Tuple[bool, str]:
        """Install a single agent."""
        agent_dir = self._get_agents_dir() / agent.name

        try:
            # Create agent directory
            agent_dir.mkdir(parents=True, exist_ok=True)

            # Write metadata
            metadata_file = agent_dir / "agent.json"
            with open(metadata_file, "w") as f:
                f.write(agent.to_json())

            # In a real implementation, would download/clone the agent source
            # For now, just store metadata
            logger.info(f"Installed agent {agent.name}@{agent.version}")

            # Record installation
            self.installed_agents[agent.name] = InstallationRecord(
                agent_name=agent.name,
                version=agent.version,
                installed_at=datetime.now().isoformat(),
                location=agent_dir,
                dependencies=[d.name for d in agent.dependencies],
                installed_by_user=is_user_requested,
            )

            self._save_installations()
            return True, f"Installed {agent.name}"

        except Exception as e:
            logger.error(f"Failed to install {agent.name}: {e}")
            return False, str(e)

    def _create_backup(self, agent_name: str) -> Optional[Path]:
        """Create backup of installed agent."""
        agent_dir = self._get_agents_dir() / agent_name
        if not agent_dir.exists():
            return None

        backup_dir = (
            self.install_dir / f"backups/{agent_name}_{datetime.now().timestamp()}"
        )
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copytree(agent_dir, backup_dir / agent_name)
            logger.info(f"Created backup of {agent_name} at {backup_dir}")
            return backup_dir
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def _restore_backup(self, agent_name: str, backup_dir: Path) -> bool:
        """Restore agent from backup."""
        agent_dir = self._get_agents_dir() / agent_name

        try:
            if agent_dir.exists():
                shutil.rmtree(agent_dir)
            shutil.copytree(backup_dir / agent_name, agent_dir)
            logger.info(f"Restored {agent_name} from backup")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def uninstall(
        self, agent_name: str, remove_dependencies: bool = False
    ) -> Tuple[bool, str]:
        """Uninstall an agent."""
        if agent_name not in self.installed_agents:
            return False, f"Agent {agent_name} not installed"

        try:
            # Check if other agents depend on this
            dependents = self._find_dependents(agent_name)
            if dependents and not remove_dependencies:
                return False, (
                    f"Agent(s) depend on {agent_name}: {', '.join(dependents)}. "
                    "Use --force to remove anyway"
                )

            # Remove agent directory
            agent_dir = self._get_agents_dir() / agent_name
            if agent_dir.exists():
                shutil.rmtree(agent_dir)

            # Remove from installations
            del self.installed_agents[agent_name]
            self._save_installations()

            logger.info(f"Uninstalled {agent_name}")
            return True, f"Successfully uninstalled {agent_name}"

        except Exception as e:
            return False, f"Failed to uninstall {agent_name}: {str(e)}"

    def _find_dependents(self, agent_name: str) -> List[str]:
        """Find agents that depend on the given agent."""
        dependents = []
        for record in self.installed_agents.values():
            if agent_name in record.dependencies:
                dependents.append(record.agent_name)
        return dependents

    def list_installed(self) -> List[InstallationRecord]:
        """List all installed agents."""
        return sorted(self.installed_agents.values(), key=lambda r: r.agent_name)

    def get_installed(self, agent_name: str) -> Optional[InstallationRecord]:
        """Get installation record for an agent."""
        return self.installed_agents.get(agent_name)

    def is_installed(self, agent_name: str, version: Optional[str] = None) -> bool:
        """Check if agent is installed (optionally check version)."""
        if agent_name not in self.installed_agents:
            return False
        if version:
            return self.installed_agents[agent_name].version == version
        return True

    def get_installation_stats(self) -> Dict:
        """Get installation statistics."""
        total = len(self.installed_agents)
        user_installed = sum(
            1 for r in self.installed_agents.values() if r.installed_by_user
        )
        dependency_installed = total - user_installed

        return {
            "total_installed": total,
            "user_requested": user_installed,
            "as_dependencies": dependency_installed,
            "install_dir": str(self.install_dir),
        }
