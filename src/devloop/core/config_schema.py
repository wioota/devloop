"""Config schema validation and versioning system."""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Current config schema version
CURRENT_SCHEMA_VERSION = "1.1.0"

# Minimum supported version (older versions require migration)
MIN_SUPPORTED_VERSION = "1.0.0"


class ConfigValidationError(Exception):
    """Raised when config validation fails."""

    pass


class ConfigMigrationError(Exception):
    """Raised when config migration fails."""

    pass


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string.

    Args:
        version: Version string like "1.2.3"

    Returns:
        Tuple of (major, minor, patch)

    Raises:
        ValueError: If version format is invalid
    """
    try:
        parts = version.split(".")
        if len(parts) != 3:
            raise ValueError(f"Version must have 3 parts: {version}")
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid version format: {version}") from e


def compare_versions(v1: str, v2: str) -> int:
    """Compare two semantic versions.

    Args:
        v1: First version
        v2: Second version

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    parts1 = parse_version(v1)
    parts2 = parse_version(v2)

    if parts1 < parts2:
        return -1
    elif parts1 > parts2:
        return 1
    else:
        return 0


class ConfigValidator:
    """Validates DevLoop configuration against schema."""

    def __init__(self):
        self.errors: List[str] = []

    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise (errors stored in self.errors)
        """
        self.errors = []

        # Check version field exists
        if "version" not in config:
            self.errors.append("Missing required field: version")
            return False

        version = config["version"]
        if not isinstance(version, str):
            self.errors.append(
                f"version must be a string, got {type(version).__name__}"
            )
            return False

        # Validate version format
        try:
            parse_version(version)
        except ValueError as e:
            self.errors.append(f"Invalid version format: {e}")
            return False

        # Check version is supported
        if compare_versions(version, MIN_SUPPORTED_VERSION) < 0:
            self.errors.append(
                f"Config version {version} is too old (minimum: {MIN_SUPPORTED_VERSION}). "
                "Migration required."
            )
            return False

        # Validate top-level structure
        required_fields = ["enabled", "agents", "global"]
        for field in required_fields:
            if field not in config:
                self.errors.append(f"Missing required field: {field}")

        # Validate 'enabled' field
        if "enabled" in config and not isinstance(config["enabled"], bool):
            self.errors.append(
                f"'enabled' must be a boolean, got {type(config['enabled']).__name__}"
            )

        # Validate 'agents' section
        if "agents" in config:
            if not isinstance(config["agents"], dict):
                self.errors.append(
                    f"'agents' must be a dictionary, got {type(config['agents']).__name__}"
                )
            else:
                self._validate_agents(config["agents"])

        # Validate 'global' section
        if "global" in config:
            if not isinstance(config["global"], dict):
                self.errors.append(
                    f"'global' must be a dictionary, got {type(config['global']).__name__}"
                )
            else:
                self._validate_global(config["global"])

        return len(self.errors) == 0

    def _validate_agents(self, agents: Dict[str, Any]) -> None:
        """Validate agents section."""
        for agent_name, agent_config in agents.items():
            if not isinstance(agent_config, dict):
                self.errors.append(
                    f"agents.{agent_name} must be a dictionary, got {type(agent_config).__name__}"
                )
                continue

            # Required fields for each agent
            if "enabled" not in agent_config:
                self.errors.append(f"agents.{agent_name}.enabled is required")
            elif not isinstance(agent_config["enabled"], bool):
                self.errors.append(f"agents.{agent_name}.enabled must be a boolean")

            if "triggers" not in agent_config:
                self.errors.append(f"agents.{agent_name}.triggers is required")
            elif not isinstance(agent_config["triggers"], list):
                self.errors.append(f"agents.{agent_name}.triggers must be a list")

            if "config" not in agent_config:
                self.errors.append(f"agents.{agent_name}.config is required")
            elif not isinstance(agent_config["config"], dict):
                self.errors.append(f"agents.{agent_name}.config must be a dictionary")

    def _validate_global(self, global_config: Dict[str, Any]) -> None:
        """Validate global section."""
        # Mode validation
        if "mode" in global_config:
            if global_config["mode"] not in ["report-only", "active"]:
                self.errors.append(
                    f"global.mode must be 'report-only' or 'active', got '{global_config['mode']}'"
                )

        # Max concurrent agents validation
        if "maxConcurrentAgents" in global_config:
            max_concurrent = global_config["maxConcurrentAgents"]
            if not isinstance(max_concurrent, int) or max_concurrent <= 0:
                self.errors.append(
                    f"global.maxConcurrentAgents must be a positive integer, got {max_concurrent}"
                )

        # Notification level validation
        if "notificationLevel" in global_config:
            valid_levels = ["none", "summary", "detailed"]
            level = global_config["notificationLevel"]
            if level not in valid_levels:
                self.errors.append(
                    f"global.notificationLevel must be one of {valid_levels}, got '{level}'"
                )

        # Resource limits validation
        if "resourceLimits" in global_config:
            self._validate_resource_limits(global_config["resourceLimits"])

        # Autonomous fixes validation
        if "autonomousFixes" in global_config:
            self._validate_autonomous_fixes(global_config["autonomousFixes"])

    def _validate_resource_limits(self, limits: Any) -> None:
        """Validate resourceLimits section."""
        if not isinstance(limits, dict):
            self.errors.append(
                f"global.resourceLimits must be a dictionary, got {type(limits).__name__}"
            )
            return

        if "maxCpu" in limits:
            max_cpu = limits["maxCpu"]
            if max_cpu is not None and (
                not isinstance(max_cpu, (int, float)) or max_cpu <= 0 or max_cpu > 100
            ):
                self.errors.append(
                    f"global.resourceLimits.maxCpu must be between 0 and 100, got {max_cpu}"
                )

        if "maxMemory" in limits:
            max_memory = limits["maxMemory"]
            if max_memory is not None and (
                not isinstance(max_memory, int) or max_memory <= 0
            ):
                self.errors.append(
                    f"global.resourceLimits.maxMemory must be a positive integer, got {max_memory}"
                )

        if "enforcementAction" in limits:
            action = limits["enforcementAction"]
            if action not in ["pause", "warn"]:
                self.errors.append(
                    f"global.resourceLimits.enforcementAction must be 'pause' or 'warn', got '{action}'"
                )

    def _validate_autonomous_fixes(self, fixes: Any) -> None:
        """Validate autonomousFixes section."""
        if not isinstance(fixes, dict):
            self.errors.append(
                f"global.autonomousFixes must be a dictionary, got {type(fixes).__name__}"
            )
            return

        if "enabled" in fixes and not isinstance(fixes["enabled"], bool):
            self.errors.append("global.autonomousFixes.enabled must be a boolean")

        if "safetyLevel" in fixes:
            valid_levels = ["safe_only", "medium_risk", "all"]
            level = fixes["safetyLevel"]
            if level not in valid_levels:
                self.errors.append(
                    f"global.autonomousFixes.safetyLevel must be one of {valid_levels}, got '{level}'"
                )


class ConfigMigrator:
    """Migrates DevLoop configuration between schema versions."""

    def __init__(self):
        self.migrations = {
            "1.0.0": self._migrate_1_0_to_1_1,
            # Add more migrations as needed
        }

    def needs_migration(self, config: Dict[str, Any]) -> bool:
        """Check if config needs migration.

        Args:
            config: Configuration dictionary

        Returns:
            True if migration needed, False otherwise
        """
        if "version" not in config:
            return True

        version = config["version"]
        return compare_versions(version, CURRENT_SCHEMA_VERSION) < 0

    def migrate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate config to current schema version.

        Args:
            config: Configuration dictionary

        Returns:
            Migrated configuration

        Raises:
            ConfigMigrationError: If migration fails
        """
        if not self.needs_migration(config):
            return config

        # Get current version (default to 1.0.0 if missing)
        current_version = config.get("version", "1.0.0")

        logger.info(
            f"Migrating config from version {current_version} to {CURRENT_SCHEMA_VERSION}"
        )

        # Apply migrations in sequence
        migrated_config = config.copy()

        while compare_versions(migrated_config["version"], CURRENT_SCHEMA_VERSION) < 0:
            version = migrated_config["version"]

            if version not in self.migrations:
                raise ConfigMigrationError(
                    f"No migration path from version {version} to {CURRENT_SCHEMA_VERSION}"
                )

            migration_func = self.migrations[version]
            migrated_config = migration_func(migrated_config)

            logger.info(f"Migrated config to version {migrated_config['version']}")

        return migrated_config

    def _migrate_1_0_to_1_1(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from version 1.0.0 to 1.1.0.

        Changes in 1.1.0:
        - Added daemon health checking support
        - Added daemon supervision configuration
        - Updated resource limits with more granular controls

        Args:
            config: Configuration in version 1.0.0 format

        Returns:
            Configuration in version 1.1.0 format
        """
        migrated = config.copy()

        # Update version
        migrated["version"] = "1.1.0"

        # Add daemon health checking config to global if not present
        if "global" not in migrated:
            migrated["global"] = {}

        global_config = migrated["global"]

        # Add daemon supervision settings
        if "daemon" not in global_config:
            global_config["daemon"] = {
                "heartbeatInterval": 30,  # seconds
                "healthCheckEnabled": True,
            }

        # No breaking changes - existing configs work as-is
        return migrated


def validate_config(
    config: Dict[str, Any], fail_fast: bool = True
) -> Optional[List[str]]:
    """Validate configuration and optionally fail fast.

    Args:
        config: Configuration dictionary
        fail_fast: If True, raise exception on validation error

    Returns:
        List of error messages if fail_fast=False, None if valid

    Raises:
        ConfigValidationError: If fail_fast=True and validation fails
    """
    validator = ConfigValidator()

    if not validator.validate(config):
        error_msg = "Configuration validation failed:\n" + "\n".join(
            f"  - {error}" for error in validator.errors
        )

        if fail_fast:
            raise ConfigValidationError(error_msg)
        else:
            return validator.errors

    return None


def migrate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate configuration to current schema version.

    Args:
        config: Configuration dictionary

    Returns:
        Migrated configuration

    Raises:
        ConfigMigrationError: If migration fails
    """
    migrator = ConfigMigrator()
    return migrator.migrate(config)
