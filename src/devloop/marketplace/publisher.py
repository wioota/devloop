"""Tools for publishing agents to the marketplace."""

import json
import logging
import hashlib
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .metadata import AgentMetadata
from .registry_client import RegistryClient

logger = logging.getLogger(__name__)


class AgentPackage:
    """Represents an agent package ready for distribution."""

    def __init__(self, agent_dir: Path):
        """Initialize agent package.

        Args:
            agent_dir: Directory containing the agent (must have agent.json)
        """
        self.agent_dir = agent_dir
        self.metadata_file = agent_dir / "agent.json"

        if not self.metadata_file.exists():
            raise ValueError(f"No agent.json found in {agent_dir}")

        # Load metadata
        self.metadata = AgentMetadata.from_json_file(self.metadata_file)

    def validate(self) -> Tuple[bool, list]:
        """Validate agent package.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate metadata
        metadata_errors = self.metadata.validate()
        errors.extend([f"Metadata: {e}" for e in metadata_errors])

        # Check for required files
        if not (self.agent_dir / "README.md").exists():
            errors.append("Missing README.md")

        # Check agent implementation
        if not self._has_agent_implementation():
            errors.append(
                "Missing agent implementation (no __init__.py or main handler)"
            )

        return len(errors) == 0, errors

    def _has_agent_implementation(self) -> bool:
        """Check if agent has implementation files."""
        # Look for common patterns
        init_file = self.agent_dir / "__init__.py"
        if init_file.exists():
            return True

        # Check for main.py or agent.py
        for filename in ["main.py", "agent.py", "handler.py"]:
            if (self.agent_dir / filename).exists():
                return True

        return False

    def get_checksum(self) -> str:
        """Calculate SHA256 checksum of agent.json."""
        with open(self.metadata_file, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def create_tarball(self, output_dir: Path) -> Path:
        """Create compressed tarball of agent.

        Args:
            output_dir: Directory to save tarball

        Returns:
            Path to created tarball
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        tarball_name = f"{self.metadata.name}-{self.metadata.version}.tar.gz"
        tarball_path = output_dir / tarball_name

        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(self.agent_dir, arcname=self.metadata.name)

        logger.info(f"Created tarball: {tarball_path}")
        return tarball_path


class AgentPublisher:
    """Tools for publishing agents to the marketplace."""

    def __init__(self, registry_client: RegistryClient):
        """Initialize publisher.

        Args:
            registry_client: Registry client for publishing
        """
        self.client = registry_client

    def publish_agent(
        self,
        agent_dir: Path,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """Publish an agent to the marketplace.

        Args:
            agent_dir: Directory containing agent
            force: Force publish even if version exists

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create and validate package
            package = AgentPackage(agent_dir)
            is_valid, errors = package.validate()

            if not is_valid:
                return False, f"Package validation failed: {', '.join(errors)}"

            # Check if agent already exists
            existing = self.client.local.get_agent(package.metadata.name)
            if existing and existing.version == package.metadata.version and not force:
                return (
                    False,
                    f"Agent {package.metadata.name}@{package.metadata.version} "
                    "already published. Use --force to override.",
                )

            # Register in marketplace
            success = self.client.local.register_agent(package.metadata)
            if not success:
                return False, f"Failed to register agent: {package.metadata.name}"

            logger.info(
                f"Published agent: {package.metadata.name}@{package.metadata.version}"
            )
            return True, f"Published {package.metadata.name}@{package.metadata.version}"

        except Exception as e:
            logger.error(f"Failed to publish agent: {e}")
            return False, f"Publication failed: {str(e)}"

    def check_updates(
        self,
        agent_dir: Path,
    ) -> Dict[str, Any]:
        """Check if agent has updates available.

        Args:
            agent_dir: Directory containing agent

        Returns:
            Dict with update information
        """
        try:
            package = AgentPackage(agent_dir)

            # Get published version
            published = self.client.local.get_agent(package.metadata.name)

            if not published:
                return {
                    "has_updates": False,
                    "reason": "Agent not published",
                    "local_version": package.metadata.version,
                }

            # Compare versions
            local_parts = tuple(map(int, package.metadata.version.split(".")))
            published_parts = tuple(map(int, published.version.split(".")))

            has_updates = local_parts > published_parts

            return {
                "has_updates": has_updates,
                "local_version": package.metadata.version,
                "published_version": published.version,
                "local_parts": local_parts,
                "published_parts": published_parts,
            }

        except Exception as e:
            logger.error(f"Failed to check updates: {e}")
            return {
                "has_updates": False,
                "error": str(e),
            }

    def get_publish_readiness(self, agent_dir: Path) -> Dict[str, Any]:
        """Check if agent is ready for publishing.

        Args:
            agent_dir: Directory containing agent

        Returns:
            Dict with readiness checks
        """
        result: Dict[str, Any] = {
            "ready": True,
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        try:
            package = AgentPackage(agent_dir)

            # 1. Metadata validation
            is_valid, metadata_errors = package.validate()
            result["checks"]["metadata"] = is_valid
            if not is_valid:
                result["ready"] = False
                result["errors"].extend(metadata_errors)

            # 2. Version check
            existing = self.client.local.get_agent(package.metadata.name)
            if existing:
                if existing.version == package.metadata.version:
                    result["checks"]["version"] = False
                    result["warnings"].append(
                        f"Version {package.metadata.version} already exists. "
                        "Consider bumping version."
                    )
                elif tuple(map(int, existing.version.split("."))) > tuple(
                    map(int, package.metadata.version.split("."))
                ):
                    result["checks"]["version"] = False
                    result["errors"].append(
                        f"Local version is older than published version "
                        f"({package.metadata.version} < {existing.version})"
                    )
                else:
                    result["checks"]["version"] = True
            else:
                result["checks"]["version"] = True

            # 3. Documentation check
            readme_exists = (package.agent_dir / "README.md").exists()
            result["checks"]["documentation"] = readme_exists
            if not readme_exists:
                result["warnings"].append("Missing README.md for documentation")

            # 4. Source code check
            has_implementation = package._has_agent_implementation()
            result["checks"]["implementation"] = has_implementation
            if not has_implementation:
                result["errors"].append("No agent implementation found")
                result["ready"] = False

        except Exception as e:
            result["ready"] = False
            result["checks"]["validation"] = False
            result["errors"].append(f"Error: {str(e)}")

        return result


class VersionManager:
    """Manage agent versioning."""

    @staticmethod
    def bump_version(
        current_version: str,
        bump_type: str = "patch",
    ) -> str:
        """Bump semantic version.

        Args:
            current_version: Current version string (X.Y.Z)
            bump_type: Type of bump - major, minor, or patch

        Returns:
            New version string
        """
        parts = list(map(int, current_version.split(".")))

        if bump_type == "major":
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif bump_type == "minor":
            parts[1] += 1
            parts[2] = 0
        elif bump_type == "patch":
            parts[2] += 1
        else:
            raise ValueError(f"Unknown bump type: {bump_type}")

        return ".".join(map(str, parts))

    @staticmethod
    def update_agent_json(agent_dir: Path, version: str) -> bool:
        """Update version in agent.json.

        Args:
            agent_dir: Directory containing agent
            version: New version

        Returns:
            Success indicator
        """
        agent_json = agent_dir / "agent.json"

        try:
            with open(agent_json) as f:
                data = json.load(f)

            data["version"] = version

            with open(agent_json, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Updated agent version to {version}")
            return True

        except Exception as e:
            logger.error(f"Failed to update agent.json: {e}")
            return False


class DeprecationManager:
    """Manage agent deprecation."""

    def __init__(self, registry_client: RegistryClient):
        """Initialize deprecation manager.

        Args:
            registry_client: Registry client
        """
        self.client = registry_client

    def deprecate_agent(
        self,
        name: str,
        message: str,
        replacement: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Deprecate an agent.

        Args:
            name: Agent name
            message: Deprecation message
            replacement: Suggested replacement agent name

        Returns:
            Tuple of (success, message)
        """
        if replacement:
            full_message = f"{message} Use {replacement} instead."
        else:
            full_message = message

        success = self.client.local.deprecate_agent(name, full_message)

        if success:
            return True, f"Deprecated {name}: {full_message}"
        else:
            return False, f"Failed to deprecate {name}"

    def get_deprecation_info(self, name: str) -> Dict[str, Any]:
        """Get deprecation information for an agent.

        Args:
            name: Agent name

        Returns:
            Dict with deprecation info
        """
        agent = self.client.local.get_agent(name)

        if not agent:
            return {
                "found": False,
                "name": name,
            }

        return {
            "found": True,
            "name": agent.name,
            "version": agent.version,
            "deprecated": agent.deprecated,
            "deprecation_message": agent.deprecation_message,
            "updated_at": agent.updated_at,
        }

    def undeprecate_agent(self, name: str) -> Tuple[bool, str]:
        """Remove deprecation from an agent.

        Args:
            name: Agent name

        Returns:
            Tuple of (success, message)
        """
        agent = self.client.local.get_agent(name)

        if not agent:
            return False, f"Agent not found: {name}"

        # Update metadata
        agent.deprecated = False
        agent.deprecation_message = None
        agent.updated_at = datetime.now().isoformat()

        success = self.client.local.register_agent(agent)

        if success:
            return True, f"Removed deprecation from {name}"
        else:
            return False, f"Failed to update {name}"
