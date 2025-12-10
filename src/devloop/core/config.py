"""Configuration management for devloop."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from dataclasses import dataclass


@dataclass
class ResourceLimitConfig:
    """Configuration for agent resource limits.

    Resource Limits:
    - max_cpu_percent: Maximum CPU percentage per agent (0-100, or None for unlimited)
    - max_memory_mb: Maximum memory in MB per agent (or None for unlimited)
    - check_interval_seconds: How often to check resource usage (default: 10s)
    - enforcement_action: What to do when limits exceeded ("pause" or "warn")
    - resume_threshold_percent: Percentage below limit to resume (default: 80%)
    """

    max_cpu_percent: Optional[float] = None
    max_memory_mb: Optional[int] = None
    check_interval_seconds: int = 10
    enforcement_action: str = "pause"
    resume_threshold_percent: float = 0.8

    def __post_init__(self):
        if self.max_cpu_percent is not None and (
            self.max_cpu_percent <= 0 or self.max_cpu_percent > 100
        ):
            raise ValueError(
                f"max_cpu_percent must be between 0 and 100, got {self.max_cpu_percent}"
            )
        if self.max_memory_mb is not None and self.max_memory_mb <= 0:
            raise ValueError(
                f"max_memory_mb must be positive, got {self.max_memory_mb}"
            )
        if self.check_interval_seconds <= 0:
            raise ValueError(
                f"check_interval_seconds must be positive, got {self.check_interval_seconds}"
            )
        if self.enforcement_action not in ["pause", "warn"]:
            raise ValueError(
                f"enforcement_action must be 'pause' or 'warn', got {self.enforcement_action}"
            )
        if not (0 < self.resume_threshold_percent < 1):
            raise ValueError(
                f"resume_threshold_percent must be between 0 and 1, got {self.resume_threshold_percent}"
            )


@dataclass
class AutonomousFixesConfig:
    """Configuration for autonomous fix application.

    Safety Levels:
    - safe_only: Only apply whitespace, formatting, and trivial fixes
    - medium_risk: Include import organization and common linting fixes
    - all: Apply all auto-fixable issues (use with caution)

    IMPORTANT: opt_in must be explicitly set to True to enable auto-fixes.
    This prevents accidental code modifications.
    """

    enabled: bool = False
    safety_level: str = "safe_only"
    opt_in: bool = False  # CRITICAL: Must be explicitly enabled per project

    def __post_init__(self):
        if self.safety_level not in ["safe_only", "medium_risk", "all"]:
            raise ValueError(f"Invalid safety_level: {self.safety_level}")


@dataclass
class GlobalConfig:
    """Global configuration."""

    mode: str = "report-only"
    max_concurrent_agents: int = 5
    notification_level: str = "summary"
    context_store_enabled: bool = True
    context_store_path: str = ".devloop/context"
    autonomous_fixes: Optional[AutonomousFixesConfig] = None
    resource_limits: Optional[ResourceLimitConfig] = None

    def __post_init__(self):
        if self.mode not in ["report-only", "active"]:
            raise ValueError(f"Invalid mode: {self.mode}")
        if self.notification_level not in ["none", "summary", "detailed"]:
            raise ValueError(f"Invalid notification_level: {self.notification_level}")
        if self.autonomous_fixes is None:
            self.autonomous_fixes = AutonomousFixesConfig()
        if self.resource_limits is None:
            self.resource_limits = ResourceLimitConfig()


class Config:
    """Main configuration manager."""

    def __init__(self, config_path: str = ".devloop/agents.json"):
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        # Always reload for development - remove caching for now
        if not self.config_path.exists():
            # Return default config
            return self._get_default_config()
        else:
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")
                return self._get_default_config()

    def get_global_config(self) -> GlobalConfig:
        """Get global configuration."""
        config = self.load()
        global_config = config.get("global", {})

        autonomous_fixes_config = global_config.get("autonomousFixes", {})
        autonomous_fixes = AutonomousFixesConfig(
            enabled=autonomous_fixes_config.get("enabled", False),
            safety_level=autonomous_fixes_config.get("safetyLevel", "safe_only"),
            opt_in=autonomous_fixes_config.get("optIn", False),
        )

        resource_limits_config = global_config.get("resourceLimits", {})
        resource_limits = ResourceLimitConfig(
            max_cpu_percent=resource_limits_config.get("maxCpu"),
            max_memory_mb=resource_limits_config.get("maxMemory"),
            check_interval_seconds=resource_limits_config.get(
                "checkIntervalSeconds", 10
            ),
            enforcement_action=resource_limits_config.get("enforcementAction", "pause"),
            resume_threshold_percent=resource_limits_config.get(
                "resumeThresholdPercent", 0.8
            ),
        )

        return GlobalConfig(
            mode=global_config.get("mode", "report-only"),
            max_concurrent_agents=global_config.get("maxConcurrentAgents", 5),
            notification_level=global_config.get("notificationLevel", "summary"),
            context_store_enabled=global_config.get("contextStore", {}).get(
                "enabled", True
            ),
            context_store_path=global_config.get("contextStore", {}).get(
                "path", ".devloop/context"
            ),
            autonomous_fixes=autonomous_fixes,
            resource_limits=resource_limits,
        )

    @staticmethod
    def default_config() -> "Config":
        """Get default configuration instance."""
        config = Config()
        config._config = config._get_default_config()
        return config

    def save(self, path: Path) -> None:
        """Save configuration to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._config, f, indent=2)

    def _get_default_config(
        self, optional_agents: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """Get default configuration.

        Args:
            optional_agents: Dict mapping optional agent names to whether they should be enabled.
                           Supported: {"snyk": bool, "code-rabbit": bool, "ci-monitor": bool}
        """
        if optional_agents is None:
            optional_agents = {}

        agents = {
            "linter": {
                "enabled": True,
                "triggers": ["file:modified", "file:created"],
                "config": {
                    "autoFix": False,
                    "reportOnly": True,
                    "filePatterns": ["**/*.py", "**/*.js", "**/*.ts"],
                    "linters": {
                        "python": "ruff",
                        "javascript": "eslint",
                        "typescript": "eslint",
                    },
                },
            },
            "formatter": {
                "enabled": True,
                "triggers": ["file:modified"],
                "config": {
                    "formatOnSave": False,
                    "reportOnly": True,
                    "filePatterns": ["**/*.py", "**/*.js", "**/*.ts"],
                    "formatters": {
                        "python": "black",
                        "javascript": "prettier",
                        "typescript": "prettier",
                    },
                },
            },
            "test-runner": {
                "enabled": True,
                "triggers": ["file:modified", "file:created"],
                "config": {
                    "runOnSave": True,
                    "relatedTestsOnly": True,
                    "testFrameworks": {
                        "python": "pytest",
                        "javascript": "jest",
                        "typescript": "jest",
                    },
                },
            },
            "agent-health-monitor": {
                "enabled": True,
                "triggers": ["agent:*:completed"],
                "config": {"monitorAllAgents": True, "autoFixOnFailure": True},
            },
            "type-checker": {
                "enabled": True,
                "triggers": ["file:modified", "file:created"],
                "config": {
                    "enabled_tools": ["mypy"],
                    "strict_mode": False,
                    "show_error_codes": True,
                    "exclude_patterns": ["test_*", "*_test.py", "*/tests/*"],
                    "max_issues": 50,
                },
            },
            "security-scanner": {
                "enabled": True,
                "triggers": ["file:modified", "file:created"],
                "config": {
                    "enabled_tools": ["bandit"],
                    "severity_threshold": "medium",
                    "confidence_threshold": "medium",
                    "exclude_patterns": ["test_*", "*_test.py", "*/tests/*"],
                    "max_issues": 50,
                },
            },
            "git-commit-assistant": {
                "enabled": True,
                "triggers": ["git:pre-commit", "git:commit"],
                "config": {
                    "conventional_commits": True,
                    "max_message_length": 72,
                    "include_breaking_changes": True,
                    "analyze_file_changes": True,
                    "auto_generate_scope": True,
                    "common_types": [
                        "feat",
                        "fix",
                        "docs",
                        "style",
                        "refactor",
                        "test",
                        "chore",
                        "perf",
                        "ci",
                        "build",
                    ],
                },
            },
            "performance-profiler": {
                "enabled": True,
                "triggers": ["file:modified", "file:created"],
                "config": {
                    "complexity_threshold": 10,
                    "min_lines_threshold": 50,
                    "enabled_tools": ["radon"],
                    "exclude_patterns": [
                        "test_*",
                        "*_test.py",
                        "*/tests/*",
                        "__init__.py",
                    ],
                    "max_issues": 50,
                },
            },
        }

        # Add optional agents if enabled
        if optional_agents.get("snyk", False):
            agents["snyk"] = {
                "enabled": True,
                "triggers": ["file:modified", "file:created"],
                "config": {
                    "severity_threshold": "medium",
                    "api_token_env_var": "SNYK_TOKEN",
                },
            }

        if optional_agents.get("code-rabbit", False):
            agents["code-rabbit"] = {
                "enabled": True,
                "triggers": ["file:modified", "file:created"],
                "config": {
                    "api_key_env_var": "CODE_RABBIT_API_KEY",
                    "min_severity": "medium",
                },
            }

        if optional_agents.get("ci-monitor", False):
            agents["ci-monitor"] = {
                "enabled": True,
                "triggers": ["git:post-push"],
                "config": {
                    "check_interval_seconds": 30,
                    "ci_provider": "github",
                    "ci_config": {},
                },
            }

        return {
            "version": "1.0.0",
            "enabled": True,
            "agents": agents,
            "global": {
                "mode": "report-only",
                "maxConcurrentAgents": 5,
                "notificationLevel": "summary",
                "resourceLimits": {
                    "maxCpu": 50,
                    "maxMemory": 500,
                    "checkIntervalSeconds": 10,
                    "enforcementAction": "pause",
                    "resumeThresholdPercent": 0.8,
                },
                "logging": {},
                "contextStore": {"enabled": True, "path": ".devloop/context"},
                "autonomousFixes": {"enabled": True, "safetyLevel": "safe_only"},
                "providers": {
                    "ci": {
                        "provider": "github",
                        "config": {},
                    },
                    "registry": {
                        "provider": "pypi",
                        "config": {},
                    },
                },
            },
            "eventSystem": {"collectors": {}, "dispatcher": {}, "store": {}},
        }


class ConfigWrapper:
    """Wrapper around config dictionary to provide object-like access."""

    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict

    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if an agent is enabled."""
        agents = self._config.get("agents", {})
        agent_config = agents.get(agent_name, {})
        return agent_config.get("enabled", False)

    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific agent."""
        agents = self._config.get("agents", {})
        return agents.get(agent_name)

    def get_global_config(self) -> GlobalConfig:
        """Get global configuration."""
        global_config = self._config.get("global", {})
        autonomous_fixes_config = global_config.get("autonomousFixes", {})
        autonomous_fixes = AutonomousFixesConfig(
            enabled=autonomous_fixes_config.get("enabled", False),
            safety_level=autonomous_fixes_config.get("safetyLevel", "safe_only"),
        )

        resource_limits_config = global_config.get("resourceLimits", {})
        resource_limits = ResourceLimitConfig(
            max_cpu_percent=resource_limits_config.get("maxCpu"),
            max_memory_mb=resource_limits_config.get("maxMemory"),
            check_interval_seconds=resource_limits_config.get(
                "checkIntervalSeconds", 10
            ),
            enforcement_action=resource_limits_config.get("enforcementAction", "pause"),
            resume_threshold_percent=resource_limits_config.get(
                "resumeThresholdPercent", 0.8
            ),
        )

        return GlobalConfig(
            mode=global_config.get("mode", "report-only"),
            max_concurrent_agents=global_config.get("maxConcurrentAgents", 5),
            notification_level=global_config.get("notificationLevel", "summary"),
            context_store_enabled=global_config.get("contextStore", {}).get(
                "enabled", True
            ),
            context_store_path=global_config.get("contextStore", {}).get(
                "path", ".devloop/context"
            ),
            autonomous_fixes=autonomous_fixes,
            resource_limits=resource_limits,
        )

    def agents(self):
        """Get agents dictionary."""
        return self._config.get("agents", {})


# Global config instance
config = Config()
