"""Tests for devloop configuration management."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devloop.core.config import (
    AutonomousFixesConfig,
    Config,
    ConfigWrapper,
    GlobalConfig,
    ResourceLimitConfig,
)

# ---------------------------------------------------------------------------
# ResourceLimitConfig validation
# ---------------------------------------------------------------------------


class TestResourceLimitConfig:
    def test_default_values(self) -> None:
        cfg = ResourceLimitConfig()
        assert cfg.max_cpu_percent is None
        assert cfg.max_memory_mb is None
        assert cfg.check_interval_seconds == 10
        assert cfg.enforcement_action == "pause"
        assert cfg.resume_threshold_percent == 0.8

    def test_valid_cpu_percent(self) -> None:
        cfg = ResourceLimitConfig(max_cpu_percent=50.0)
        assert cfg.max_cpu_percent == 50.0

    def test_invalid_cpu_percent_zero(self) -> None:
        with pytest.raises(ValueError, match="max_cpu_percent"):
            ResourceLimitConfig(max_cpu_percent=0)

    def test_invalid_cpu_percent_over_100(self) -> None:
        with pytest.raises(ValueError, match="max_cpu_percent"):
            ResourceLimitConfig(max_cpu_percent=101)

    def test_invalid_memory_negative(self) -> None:
        with pytest.raises(ValueError, match="max_memory_mb"):
            ResourceLimitConfig(max_memory_mb=-1)

    def test_invalid_check_interval(self) -> None:
        with pytest.raises(ValueError, match="check_interval_seconds"):
            ResourceLimitConfig(check_interval_seconds=0)

    def test_invalid_enforcement_action(self) -> None:
        with pytest.raises(ValueError, match="enforcement_action"):
            ResourceLimitConfig(enforcement_action="kill")

    def test_invalid_resume_threshold_zero(self) -> None:
        with pytest.raises(ValueError, match="resume_threshold_percent"):
            ResourceLimitConfig(resume_threshold_percent=0)

    def test_invalid_resume_threshold_one(self) -> None:
        with pytest.raises(ValueError, match="resume_threshold_percent"):
            ResourceLimitConfig(resume_threshold_percent=1.0)


# ---------------------------------------------------------------------------
# AutonomousFixesConfig validation
# ---------------------------------------------------------------------------


class TestAutonomousFixesConfig:
    def test_default_values(self) -> None:
        cfg = AutonomousFixesConfig()
        assert cfg.enabled is False
        assert cfg.safety_level == "safe_only"
        assert cfg.opt_in is False

    def test_valid_safety_levels(self) -> None:
        for level in ("safe_only", "medium_risk", "all"):
            cfg = AutonomousFixesConfig(safety_level=level)
            assert cfg.safety_level == level

    def test_invalid_safety_level(self) -> None:
        with pytest.raises(ValueError, match="Invalid safety_level"):
            AutonomousFixesConfig(safety_level="yolo")


# ---------------------------------------------------------------------------
# GlobalConfig validation
# ---------------------------------------------------------------------------


class TestGlobalConfig:
    def test_default_values(self) -> None:
        cfg = GlobalConfig()
        assert cfg.mode == "report-only"
        assert cfg.max_concurrent_agents == 5
        assert cfg.autonomous_fixes is not None
        assert cfg.resource_limits is not None

    def test_invalid_mode(self) -> None:
        with pytest.raises(ValueError, match="Invalid mode"):
            GlobalConfig(mode="turbo")

    def test_invalid_notification_level(self) -> None:
        with pytest.raises(ValueError, match="Invalid notification_level"):
            GlobalConfig(notification_level="verbose")

    def test_autonomous_fixes_defaults_created(self) -> None:
        cfg = GlobalConfig()
        assert isinstance(cfg.autonomous_fixes, AutonomousFixesConfig)

    def test_resource_limits_defaults_created(self) -> None:
        cfg = GlobalConfig()
        assert isinstance(cfg.resource_limits, ResourceLimitConfig)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestConfigLoad:
    def test_load_returns_default_when_no_file(self, tmp_path: Path) -> None:
        cfg = Config(config_path=str(tmp_path / "nonexistent.json"))
        result = cfg.load()
        assert "version" in result
        assert "agents" in result
        assert "global" in result

    def test_load_reads_valid_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "agents.json"
        config_data = {
            "version": "1.0.0",
            "enabled": True,
            "agents": {},
            "global": {"mode": "report-only"},
        }
        config_file.write_text(json.dumps(config_data))

        cfg = Config(config_path=str(config_file))
        result = cfg.load(validate=False, migrate=False)
        assert result["version"] == "1.0.0"

    def test_load_returns_default_on_invalid_json(self, tmp_path: Path) -> None:
        config_file = tmp_path / "agents.json"
        config_file.write_text("not valid json {{{")

        cfg = Config(config_path=str(config_file))
        result = cfg.load()
        assert "version" in result  # Got default config

    def test_load_with_migration(self, tmp_path: Path) -> None:
        config_file = tmp_path / "agents.json"
        # Write config with old version to trigger migration
        config_data = {
            "version": "1.0.0",
            "enabled": True,
            "agents": {},
            "global": {},
        }
        config_file.write_text(json.dumps(config_data))

        cfg = Config(config_path=str(config_file))
        result = cfg.load(validate=False, migrate=True)
        # migrate_config should bump version to current
        assert result["version"] == "1.1.0"


# ---------------------------------------------------------------------------
# Config.get_global_config
# ---------------------------------------------------------------------------


class TestConfigGetGlobalConfig:
    def test_get_global_config_from_default(self, tmp_path: Path) -> None:
        cfg = Config(config_path=str(tmp_path / "nonexistent.json"))
        global_cfg = cfg.get_global_config()
        assert isinstance(global_cfg, GlobalConfig)
        assert global_cfg.mode == "report-only"

    def test_get_global_config_with_custom_values(self, tmp_path: Path) -> None:
        config_file = tmp_path / "agents.json"
        config_data = {
            "version": "1.0.0",
            "enabled": True,
            "agents": {},
            "global": {
                "mode": "active",
                "maxConcurrentAgents": 10,
                "notificationLevel": "detailed",
                "autonomousFixes": {
                    "enabled": True,
                    "safetyLevel": "medium_risk",
                    "optIn": True,
                },
                "resourceLimits": {
                    "maxCpu": 75,
                    "maxMemory": 1024,
                    "checkIntervalSeconds": 5,
                    "enforcementAction": "warn",
                    "resumeThresholdPercent": 0.7,
                },
                "contextStore": {"enabled": False, "path": "/custom/path"},
            },
        }
        config_file.write_text(json.dumps(config_data))

        cfg = Config(config_path=str(config_file))
        global_cfg = cfg.get_global_config()
        assert global_cfg.mode == "active"
        assert global_cfg.max_concurrent_agents == 10
        assert global_cfg.notification_level == "detailed"
        assert global_cfg.context_store_enabled is False
        assert global_cfg.context_store_path == "/custom/path"
        assert global_cfg.autonomous_fixes.enabled is True
        assert global_cfg.autonomous_fixes.safety_level == "medium_risk"
        assert global_cfg.resource_limits.max_cpu_percent == 75
        assert global_cfg.resource_limits.max_memory_mb == 1024


# ---------------------------------------------------------------------------
# Config.default_config and save
# ---------------------------------------------------------------------------


class TestConfigDefaultAndSave:
    def test_default_config_factory(self) -> None:
        cfg = Config.default_config()
        assert cfg._config is not None
        assert "agents" in cfg._config

    def test_save_creates_file(self, tmp_path: Path) -> None:
        cfg = Config.default_config()
        out_path = tmp_path / "subdir" / "agents.json"
        cfg.save(out_path)
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert "agents" in data


# ---------------------------------------------------------------------------
# Config._get_default_config with optional agents
# ---------------------------------------------------------------------------


class TestDefaultConfigOptionalAgents:
    def test_default_has_standard_agents(self) -> None:
        cfg = Config()
        result = cfg._get_default_config()
        assert "linter" in result["agents"]
        assert "formatter" in result["agents"]
        assert "test-runner" in result["agents"]
        assert "snyk" not in result["agents"]

    def test_optional_snyk_agent(self) -> None:
        cfg = Config()
        result = cfg._get_default_config(optional_agents={"snyk": True})
        assert "snyk" in result["agents"]
        assert result["agents"]["snyk"]["enabled"] is True

    def test_optional_code_rabbit_agent(self) -> None:
        cfg = Config()
        result = cfg._get_default_config(optional_agents={"code-rabbit": True})
        assert "code-rabbit" in result["agents"]

    def test_optional_ci_monitor_agent(self) -> None:
        cfg = Config()
        result = cfg._get_default_config(optional_agents={"ci-monitor": True})
        assert "ci-monitor" in result["agents"]


# ---------------------------------------------------------------------------
# ConfigWrapper
# ---------------------------------------------------------------------------


class TestConfigWrapper:
    @pytest.fixture
    def wrapper(self) -> ConfigWrapper:
        return ConfigWrapper(
            {
                "agents": {
                    "linter": {"enabled": True, "config": {"autoFix": False}},
                    "formatter": {"enabled": False},
                },
                "global": {
                    "mode": "active",
                    "maxConcurrentAgents": 3,
                    "notificationLevel": "detailed",
                    "autonomousFixes": {"enabled": True, "safetyLevel": "all"},
                    "resourceLimits": {"maxCpu": 80, "maxMemory": 256},
                    "contextStore": {"enabled": True, "path": ".devloop/ctx"},
                },
            }
        )

    def test_is_agent_enabled_true(self, wrapper: ConfigWrapper) -> None:
        assert wrapper.is_agent_enabled("linter") is True

    def test_is_agent_enabled_false(self, wrapper: ConfigWrapper) -> None:
        assert wrapper.is_agent_enabled("formatter") is False

    def test_is_agent_enabled_missing(self, wrapper: ConfigWrapper) -> None:
        assert wrapper.is_agent_enabled("nonexistent") is False

    def test_get_agent_config(self, wrapper: ConfigWrapper) -> None:
        cfg = wrapper.get_agent_config("linter")
        assert cfg is not None
        assert cfg["config"]["autoFix"] is False

    def test_get_agent_config_missing(self, wrapper: ConfigWrapper) -> None:
        assert wrapper.get_agent_config("nonexistent") is None

    def test_get_global_config(self, wrapper: ConfigWrapper) -> None:
        global_cfg = wrapper.get_global_config()
        assert global_cfg.mode == "active"
        assert global_cfg.max_concurrent_agents == 3
        assert global_cfg.resource_limits.max_cpu_percent == 80

    def test_agents_property(self, wrapper: ConfigWrapper) -> None:
        agents = wrapper.agents()
        assert "linter" in agents
        assert "formatter" in agents
