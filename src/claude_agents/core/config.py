"""Configuration management for claude-agents."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from dataclasses import dataclass


@dataclass
class AutonomousFixesConfig:
    """Configuration for autonomous fix application."""
    enabled: bool = False
    safety_level: str = "safe_only"

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
    context_store_path: str = ".claude/context"
    autonomous_fixes: AutonomousFixesConfig = None

    def __post_init__(self):
        if self.mode not in ["report-only", "active"]:
            raise ValueError(f"Invalid mode: {self.mode}")
        if self.notification_level not in ["none", "summary", "detailed"]:
            raise ValueError(f"Invalid notification_level: {self.notification_level}")
        if self.autonomous_fixes is None:
            self.autonomous_fixes = AutonomousFixesConfig()


class Config:
    """Main configuration manager."""

    def __init__(self, config_path: str = ".claude/agents.json"):
        self.config_path = Path(config_path)
        self._config = None

    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            # Return default config
            self._config = self._get_default_config()
        else:
            try:
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")
                self._config = self._get_default_config()

        return self._config

    def get_global_config(self) -> GlobalConfig:
        """Get global configuration."""
        config = self.load()
        global_config = config.get("global", {})

        autonomous_fixes_config = global_config.get("autonomousFixes", {})
        autonomous_fixes = AutonomousFixesConfig(
            enabled=autonomous_fixes_config.get("enabled", False),
            safety_level=autonomous_fixes_config.get("safetyLevel", "safe_only")
        )

        return GlobalConfig(
            mode=global_config.get("mode", "report-only"),
            max_concurrent_agents=global_config.get("maxConcurrentAgents", 5),
            notification_level=global_config.get("notificationLevel", "summary"),
            context_store_enabled=global_config.get("contextStore", {}).get("enabled", True),
            context_store_path=global_config.get("contextStore", {}).get("path", ".claude/context"),
            autonomous_fixes=autonomous_fixes
        )

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "version": "1.0.0",
            "enabled": True,
            "agents": {
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
                            "typescript": "eslint"
                        }
                    }
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
                            "typescript": "prettier"
                        }
                    }
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
                            "typescript": "jest"
                        }
                    }
                },
                "agent-health-monitor": {
                    "enabled": True,
                    "triggers": ["agent:*:completed"],
                    "config": {
                        "monitorAllAgents": True,
                        "autoFixOnFailure": True
                    }
                },
                "type-checker": {
                    "enabled": True,
                    "triggers": ["file:modified", "file:created"],
                    "config": {
                        "enabledTools": ["mypy"],
                        "strictMode": false,
                        "showErrorCodes": true,
                        "excludePatterns": ["test_*", "*_test.py", "*/tests/*"],
                        "maxIssues": 50
                    }
                },
                "security-scanner": {
                    "enabled": True,
                    "triggers": ["file:modified", "file:created"],
                    "config": {
                        "enabledTools": ["bandit"],
                        "severityThreshold": "medium",
                        "confidenceThreshold": "medium",
                        "excludePatterns": ["test_*", "*_test.py", "*/tests/*"],
                        "maxIssues": 50
                    }
                }
            },
            "global": {
                "mode": "report-only",
                "maxConcurrentAgents": 5,
                "notificationLevel": "summary",
                "resourceLimits": {},
                "logging": {},
                "contextStore": {
                    "enabled": True,
                    "path": ".claude/context"
                },
                "autonomousFixes": {
                    "enabled": True,
                    "safetyLevel": "safe_only"
                }
            },
            "eventSystem": {
                "collectors": {},
                "dispatcher": {},
                "store": {}
            }
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
            safety_level=autonomous_fixes_config.get("safetyLevel", "safe_only")
        )

        return GlobalConfig(
            mode=global_config.get("mode", "report-only"),
            max_concurrent_agents=global_config.get("maxConcurrentAgents", 5),
            notification_level=global_config.get("notificationLevel", "summary"),
            context_store_enabled=global_config.get("contextStore", {}).get("enabled", True),
            context_store_path=global_config.get("contextStore", {}).get("path", ".claude/context"),
            autonomous_fixes=autonomous_fixes
        )

    def agents(self):
        """Get agents dictionary."""
        return self._config.get("agents", {})


# Global config instance
config = Config()
