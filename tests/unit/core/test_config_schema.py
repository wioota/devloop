"""Tests for config schema validation and migration."""

import pytest
from devloop.core.config_schema import (
    CURRENT_SCHEMA_VERSION,
    MIN_SUPPORTED_VERSION,
    ConfigMigrationError,
    ConfigMigrator,
    ConfigValidationError,
    ConfigValidator,
    compare_versions,
    migrate_config,
    parse_version,
    validate_config,
)


class TestVersionParsing:
    """Test semantic version parsing."""

    def test_parse_valid_version(self):
        """Parse valid semantic version."""
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("0.0.1") == (0, 0, 1)
        assert parse_version("10.20.30") == (10, 20, 30)

    def test_parse_invalid_version(self):
        """Reject invalid version formats."""
        with pytest.raises(ValueError, match="Invalid version format"):
            parse_version("1.2")

        with pytest.raises(ValueError, match="Invalid version format"):
            parse_version("1.2.3.4")

        with pytest.raises(ValueError, match="Invalid version format"):
            parse_version("abc.def.ghi")

        with pytest.raises(ValueError, match="Invalid version format"):
            parse_version("")

    def test_compare_versions(self):
        """Compare semantic versions correctly."""
        # Equal
        assert compare_versions("1.2.3", "1.2.3") == 0

        # Less than
        assert compare_versions("1.2.3", "1.2.4") == -1
        assert compare_versions("1.2.3", "1.3.0") == -1
        assert compare_versions("1.2.3", "2.0.0") == -1

        # Greater than
        assert compare_versions("1.2.4", "1.2.3") == 1
        assert compare_versions("1.3.0", "1.2.3") == 1
        assert compare_versions("2.0.0", "1.2.3") == 1


class TestConfigValidator:
    """Test configuration validation."""

    def test_valid_minimal_config(self):
        """Validate minimal valid config."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {
                "linter": {
                    "enabled": True,
                    "triggers": ["file:modified"],
                    "config": {"autoFix": False},
                }
            },
            "global": {
                "mode": "report-only",
                "maxConcurrentAgents": 5,
                "notificationLevel": "summary",
            },
        }

        validator = ConfigValidator()
        assert validator.validate(config) is True
        assert len(validator.errors) == 0

    def test_missing_version(self):
        """Reject config without version field."""
        config = {
            "enabled": True,
            "agents": {},
            "global": {},
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("Missing required field: version" in e for e in validator.errors)

    def test_invalid_version_format(self):
        """Reject config with invalid version format."""
        config = {
            "version": "1.2",  # Invalid: only 2 parts
            "enabled": True,
            "agents": {},
            "global": {},
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("Invalid version format" in e for e in validator.errors)

    def test_old_version_rejected(self):
        """Reject config with version too old."""
        config = {
            "version": "0.9.0",  # Too old
            "enabled": True,
            "agents": {},
            "global": {},
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("too old" in e.lower() for e in validator.errors)

    def test_missing_required_fields(self):
        """Reject config missing required top-level fields."""
        config = {
            "version": "1.1.0",
            # Missing: enabled, agents, global
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("Missing required field: enabled" in e for e in validator.errors)
        assert any("Missing required field: agents" in e for e in validator.errors)
        assert any("Missing required field: global" in e for e in validator.errors)

    def test_invalid_enabled_type(self):
        """Reject config with non-boolean enabled field."""
        config = {
            "version": "1.1.0",
            "enabled": "yes",  # Should be boolean
            "agents": {},
            "global": {},
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("'enabled' must be a boolean" in e for e in validator.errors)

    def test_invalid_agents_type(self):
        """Reject config with non-dict agents field."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": ["linter", "formatter"],  # Should be dict
            "global": {},
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("'agents' must be a dictionary" in e for e in validator.errors)

    def test_invalid_global_type(self):
        """Reject config with non-dict global field."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {},
            "global": "default",  # Should be dict
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("'global' must be a dictionary" in e for e in validator.errors)

    def test_agent_missing_required_fields(self):
        """Reject agent config missing required fields."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {
                "linter": {
                    # Missing: enabled, triggers, config
                }
            },
            "global": {},
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("agents.linter.enabled is required" in e for e in validator.errors)
        assert any("agents.linter.triggers is required" in e for e in validator.errors)
        assert any("agents.linter.config is required" in e for e in validator.errors)

    def test_agent_invalid_types(self):
        """Reject agent config with invalid field types."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {
                "linter": {
                    "enabled": "yes",  # Should be boolean
                    "triggers": "file:modified",  # Should be list
                    "config": [],  # Should be dict
                }
            },
            "global": {},
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any(
            "agents.linter.enabled must be a boolean" in e for e in validator.errors
        )
        assert any(
            "agents.linter.triggers must be a list" in e for e in validator.errors
        )
        assert any(
            "agents.linter.config must be a dictionary" in e for e in validator.errors
        )

    def test_global_invalid_mode(self):
        """Reject config with invalid mode."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {},
            "global": {
                "mode": "aggressive",  # Invalid mode
            },
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("global.mode must be" in e for e in validator.errors)

    def test_global_invalid_max_concurrent_agents(self):
        """Reject config with invalid maxConcurrentAgents."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {},
            "global": {
                "maxConcurrentAgents": -1,  # Must be positive
            },
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any(
            "maxConcurrentAgents must be a positive integer" in e
            for e in validator.errors
        )

    def test_global_invalid_notification_level(self):
        """Reject config with invalid notificationLevel."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {},
            "global": {
                "notificationLevel": "verbose",  # Invalid level
            },
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("notificationLevel must be one of" in e for e in validator.errors)

    def test_resource_limits_validation(self):
        """Validate resource limits fields."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {},
            "global": {
                "resourceLimits": {
                    "maxCpu": 150,  # Invalid: >100
                    "maxMemory": -500,  # Invalid: negative
                    "enforcementAction": "kill",  # Invalid action
                }
            },
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any("maxCpu must be between 0 and 100" in e for e in validator.errors)
        assert any(
            "maxMemory must be a positive integer" in e for e in validator.errors
        )
        assert any("enforcementAction must be" in e for e in validator.errors)

    def test_autonomous_fixes_validation(self):
        """Validate autonomousFixes fields."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {},
            "global": {
                "autonomousFixes": {
                    "enabled": "yes",  # Should be boolean
                    "safetyLevel": "dangerous",  # Invalid level
                }
            },
        }

        validator = ConfigValidator()
        assert validator.validate(config) is False
        assert any(
            "autonomousFixes.enabled must be a boolean" in e for e in validator.errors
        )
        assert any("safetyLevel must be one of" in e for e in validator.errors)


class TestConfigMigrator:
    """Test configuration migration."""

    def test_no_migration_needed_for_current_version(self):
        """Don't migrate config already at current version."""
        config = {
            "version": CURRENT_SCHEMA_VERSION,
            "enabled": True,
            "agents": {},
            "global": {},
        }

        migrator = ConfigMigrator()
        assert migrator.needs_migration(config) is False

        migrated = migrator.migrate(config)
        assert migrated == config

    def test_migration_needed_for_old_version(self):
        """Detect when migration is needed."""
        config = {
            "version": "1.0.0",
            "enabled": True,
            "agents": {},
            "global": {},
        }

        migrator = ConfigMigrator()
        assert migrator.needs_migration(config) is True

    def test_migrate_1_0_to_1_1(self):
        """Migrate from 1.0.0 to 1.1.0."""
        config = {
            "version": "1.0.0",
            "enabled": True,
            "agents": {
                "linter": {
                    "enabled": True,
                    "triggers": ["file:modified"],
                    "config": {},
                }
            },
            "global": {
                "mode": "report-only",
            },
        }

        migrator = ConfigMigrator()
        migrated = migrator.migrate(config)

        # Version updated
        assert migrated["version"] == "1.1.0"

        # Daemon config added
        assert "daemon" in migrated["global"]
        assert migrated["global"]["daemon"]["heartbeatInterval"] == 30
        assert migrated["global"]["daemon"]["healthCheckEnabled"] is True

        # Existing fields preserved
        assert migrated["enabled"] is True
        assert "linter" in migrated["agents"]
        assert migrated["global"]["mode"] == "report-only"

    def test_missing_version_defaults_to_1_0(self):
        """Configs without version field treated as 1.0.0."""
        config = {
            # No version field
            "enabled": True,
            "agents": {},
            "global": {},
        }

        migrator = ConfigMigrator()
        assert migrator.needs_migration(config) is True


class TestValidateConfigFunction:
    """Test validate_config helper function."""

    def test_valid_config_returns_none(self):
        """Valid config returns None."""
        config = {
            "version": "1.1.0",
            "enabled": True,
            "agents": {},
            "global": {
                "mode": "report-only",
            },
        }

        result = validate_config(config, fail_fast=False)
        assert result is None

    def test_invalid_config_raises_with_fail_fast(self):
        """Invalid config raises exception with fail_fast=True."""
        config = {
            "version": "invalid",
            "enabled": True,
            "agents": {},
            "global": {},
        }

        with pytest.raises(ConfigValidationError, match="validation failed"):
            validate_config(config, fail_fast=True)

    def test_invalid_config_returns_errors_without_fail_fast(self):
        """Invalid config returns error list with fail_fast=False."""
        config = {
            "version": "invalid",
            "enabled": True,
            "agents": {},
            "global": {},
        }

        errors = validate_config(config, fail_fast=False)
        assert isinstance(errors, list)
        assert len(errors) > 0
        assert any("Invalid version format" in e for e in errors)


class TestMigrateConfigFunction:
    """Test migrate_config helper function."""

    def test_migrate_old_config(self):
        """Successfully migrate old config."""
        config = {
            "version": "1.0.0",
            "enabled": True,
            "agents": {},
            "global": {},
        }

        migrated = migrate_config(config)
        assert migrated["version"] == "1.1.0"
        assert "daemon" in migrated["global"]
