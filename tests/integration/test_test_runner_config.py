"""Tests for TestRunnerConfig class."""

import pytest
from devloop.agents.test_runner import TestRunnerConfig


class TestTestRunnerConfig:
    """Test the TestRunnerConfig class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = TestRunnerConfig({})

        assert config.enabled is True
        assert config.run_on_save is True
        assert config.related_tests_only is True
        assert config.auto_detect_frameworks is True

    def test_test_paths_default_empty(self):
        """Test that testPaths defaults to empty list (auto-detect)."""
        config = TestRunnerConfig({})

        assert config.test_paths == []

    def test_test_paths_custom(self):
        """Test custom testPaths configuration."""
        config = TestRunnerConfig({"testPaths": ["tests/", "test/"]})

        assert config.test_paths == ["tests/", "test/"]

    def test_exclude_paths_default(self):
        """Test that excludePaths has sensible defaults."""
        config = TestRunnerConfig({})

        assert "**/site-packages/**" in config.exclude_paths
        assert "**/.venv/**" in config.exclude_paths
        assert "**/venv/**" in config.exclude_paths
        assert "**/.tox/**" in config.exclude_paths
        assert "**/env/**" in config.exclude_paths

    def test_exclude_paths_custom(self):
        """Test custom excludePaths configuration."""
        config = TestRunnerConfig({"excludePaths": ["**/node_modules/**"]})

        assert config.exclude_paths == ["**/node_modules/**"]

    def test_project_context_defaults(self):
        """Test default projectContext configuration."""
        config = TestRunnerConfig({})

        assert config.auto_detect_context is True
        assert config.devloop_development is False
        assert config.respect_site_packages is True

    def test_project_context_custom(self):
        """Test custom projectContext configuration."""
        config = TestRunnerConfig(
            {
                "projectContext": {
                    "autoDetect": False,
                    "devloopDevelopment": True,
                    "respectSitePackages": False,
                }
            }
        )

        assert config.auto_detect_context is False
        assert config.devloop_development is True
        assert config.respect_site_packages is False

    def test_project_context_partial(self):
        """Test partial projectContext configuration with defaults."""
        config = TestRunnerConfig({"projectContext": {"devloopDevelopment": True}})

        assert config.auto_detect_context is True  # default
        assert config.devloop_development is True  # custom
        assert config.respect_site_packages is True  # default

    def test_backward_compatibility_no_new_fields(self):
        """Test that old configs without new fields still work."""
        old_config = {
            "runOnSave": True,
            "relatedTestsOnly": True,
            "testFrameworks": {"python": "pytest"},
        }

        config = TestRunnerConfig(old_config)

        # Old fields work
        assert config.run_on_save is True
        assert config.related_tests_only is True
        assert config.test_frameworks == {"python": "pytest"}

        # New fields have defaults
        assert config.test_paths == []
        assert "**/site-packages/**" in config.exclude_paths
        assert config.auto_detect_context is True
        assert config.devloop_development is False

    def test_full_configuration(self):
        """Test full configuration with all fields."""
        full_config = {
            "runOnSave": False,
            "relatedTestsOnly": False,
            "testFrameworks": {"python": "pytest", "javascript": "jest"},
            "testPaths": ["tests/", "spec/"],
            "excludePaths": [
                "**/site-packages/**",
                "**/.venv/**",
                "**/custom-exclude/**",
            ],
            "projectContext": {
                "autoDetect": True,
                "devloopDevelopment": True,
                "respectSitePackages": True,
            },
        }

        config = TestRunnerConfig(full_config)

        assert config.run_on_save is False
        assert config.related_tests_only is False
        assert config.test_frameworks == {"python": "pytest", "javascript": "jest"}
        assert config.test_paths == ["tests/", "spec/"]
        assert config.exclude_paths == [
            "**/site-packages/**",
            "**/.venv/**",
            "**/custom-exclude/**",
        ]
        assert config.auto_detect_context is True
        assert config.devloop_development is True
        assert config.respect_site_packages is True

    def test_devloop_development_mode(self):
        """Test configuration for devloop development mode."""
        devloop_config = {
            "projectContext": {
                "autoDetect": True,
                "devloopDevelopment": True,
                "respectSitePackages": True,
            }
        }

        config = TestRunnerConfig(devloop_config)

        assert config.devloop_development is True
        assert config.auto_detect_context is True

    def test_user_project_mode(self):
        """Test configuration for user project mode."""
        user_config = {
            "projectContext": {
                "autoDetect": True,
                "devloopDevelopment": False,
                "respectSitePackages": True,
            }
        }

        config = TestRunnerConfig(user_config)

        assert config.devloop_development is False
        assert config.respect_site_packages is True
        assert "**/site-packages/**" in config.exclude_paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
