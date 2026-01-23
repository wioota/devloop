"""Tests for release CLI commands."""

from unittest.mock import Mock, patch

import pytest

from devloop.cli.commands.release import check, publish


class TestPublish:
    """Tests for publish command."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock ReleaseManager."""
        mock_mgr = Mock()

        # Mock pre-release checks result
        mock_check = Mock()
        mock_check.check_name = "Git Clean"
        mock_check.passed = True
        mock_check.message = "Working directory is clean"

        mock_checks_result = Mock()
        mock_checks_result.success = True
        mock_checks_result.checks = [mock_check]
        mock_checks_result.ci_provider_name = "GitHub Actions"
        mock_checks_result.registry_provider_name = "PyPI"

        mock_mgr.run_pre_release_checks.return_value = mock_checks_result

        # Mock tag result
        mock_tag_result = Mock()
        mock_tag_result.success = True
        mock_tag_result.url = "https://github.com/org/repo/releases/tag/v1.0.0"

        mock_mgr.create_release_tag.return_value = mock_tag_result

        # Mock publish result
        mock_pub_result = Mock()
        mock_pub_result.success = True
        mock_pub_result.registry_provider_name = "PyPI"
        mock_pub_result.url = "https://pypi.org/project/devloop/1.0.0/"

        mock_mgr.publish_release.return_value = mock_pub_result

        return mock_mgr

    def test_publish_success_full_workflow(self, mock_manager):
        """Test successful full release workflow."""
        with patch("devloop.cli.commands.release.ReleaseConfig") as MockConfig:
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=False,
                        skip_tag=False,
                        skip_publish=False,
                        dry_run=False,
                    )

                    assert result == 0
                    MockConfig.assert_called_once()
                    mock_manager.run_pre_release_checks.assert_called_once()
                    mock_manager.create_release_tag.assert_called_once()
                    mock_manager.publish_release.assert_called_once()

    def test_publish_with_custom_branch(self, mock_manager):
        """Test publish with custom branch."""
        with patch("devloop.cli.commands.release.ReleaseConfig") as MockConfig:
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="2.0.0",
                        branch="release",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=False,
                        skip_tag=False,
                        skip_publish=False,
                        dry_run=False,
                    )

                    assert result == 0
                    config_call = MockConfig.call_args[1]
                    assert config_call["version"] == "2.0.0"
                    assert config_call["branch"] == "release"

    def test_publish_with_custom_providers(self, mock_manager):
        """Test publish with custom CI and registry providers."""
        with patch("devloop.cli.commands.release.ReleaseConfig") as MockConfig:
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider="github",
                        registry_provider="pypi",
                        skip_checks=False,
                        skip_tag=False,
                        skip_publish=False,
                        dry_run=False,
                    )

                    assert result == 0
                    config_call = MockConfig.call_args[1]
                    assert config_call["ci_provider"] == "github"
                    assert config_call["registry_provider"] == "pypi"

    def test_publish_skip_tag(self, mock_manager):
        """Test publish with skip_tag option."""
        with patch("devloop.cli.commands.release.ReleaseConfig") as MockConfig:
            # Mock config with create_tag=False
            mock_config = Mock()
            mock_config.create_tag = False
            mock_config.publish = True
            MockConfig.return_value = mock_config

            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=False,
                        skip_tag=True,
                        skip_publish=False,
                        dry_run=False,
                    )

                    assert result == 0
                    config_call = MockConfig.call_args[1]
                    assert config_call["create_tag"] is False
                    mock_manager.create_release_tag.assert_not_called()

    def test_publish_skip_publish(self, mock_manager):
        """Test publish with skip_publish option."""
        with patch("devloop.cli.commands.release.ReleaseConfig") as MockConfig:
            # Mock config with publish=False
            mock_config = Mock()
            mock_config.create_tag = True
            mock_config.publish = False
            MockConfig.return_value = mock_config

            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=False,
                        skip_tag=False,
                        skip_publish=True,
                        dry_run=False,
                    )

                    assert result == 0
                    config_call = MockConfig.call_args[1]
                    assert config_call["publish"] is False
                    mock_manager.publish_release.assert_not_called()

    def test_publish_dry_run(self, mock_manager):
        """Test publish in dry-run mode."""
        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=False,
                        skip_tag=False,
                        skip_publish=False,
                        dry_run=True,
                    )

                    assert result == 0
                    mock_manager.run_pre_release_checks.assert_called_once()
                    # Should not create tag or publish in dry-run
                    mock_manager.create_release_tag.assert_not_called()
                    mock_manager.publish_release.assert_not_called()

    def test_publish_checks_failed_without_skip(self, mock_manager):
        """Test publish when pre-release checks fail."""
        # Mock failed checks
        mock_check = Mock()
        mock_check.check_name = "Git Clean"
        mock_check.passed = False
        mock_check.message = "Uncommitted changes"

        mock_checks_result = Mock()
        mock_checks_result.success = False
        mock_checks_result.checks = [mock_check]

        mock_manager.run_pre_release_checks.return_value = mock_checks_result

        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=False,
                        skip_tag=False,
                        skip_publish=False,
                        dry_run=False,
                    )

                    assert result == 1
                    # Should not proceed to tag or publish
                    mock_manager.create_release_tag.assert_not_called()
                    mock_manager.publish_release.assert_not_called()

    def test_publish_checks_failed_with_skip(self, mock_manager):
        """Test publish when checks fail but skip_checks is True."""
        # Mock failed checks
        mock_check = Mock()
        mock_check.check_name = "Git Clean"
        mock_check.passed = False
        mock_check.message = "Uncommitted changes"

        mock_checks_result = Mock()
        mock_checks_result.success = False
        mock_checks_result.checks = [mock_check]
        mock_checks_result.ci_provider_name = None
        mock_checks_result.registry_provider_name = None

        mock_manager.run_pre_release_checks.return_value = mock_checks_result

        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=True,
                        skip_tag=False,
                        skip_publish=False,
                        dry_run=False,
                    )

                    assert result == 0
                    # Should proceed despite failed checks
                    mock_manager.create_release_tag.assert_called_once()
                    mock_manager.publish_release.assert_called_once()

    def test_publish_tag_creation_fails(self, mock_manager):
        """Test publish when tag creation fails."""
        mock_tag_result = Mock()
        mock_tag_result.success = False
        mock_tag_result.error = "Tag already exists"

        mock_manager.create_release_tag.return_value = mock_tag_result

        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=False,
                        skip_tag=False,
                        skip_publish=False,
                        dry_run=False,
                    )

                    assert result == 1
                    # Should not proceed to publish if tag fails
                    mock_manager.publish_release.assert_not_called()

    def test_publish_publishing_fails(self, mock_manager):
        """Test publish when publishing to registry fails."""
        mock_pub_result = Mock()
        mock_pub_result.success = False
        mock_pub_result.error = "Authentication failed"

        mock_manager.publish_release.return_value = mock_pub_result

        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=False,
                        skip_tag=False,
                        skip_publish=False,
                        dry_run=False,
                    )

                    assert result == 1

    def test_publish_with_url_in_results(self, mock_manager):
        """Test publish displays URLs when available."""
        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = publish(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                        skip_checks=False,
                        skip_tag=False,
                        skip_publish=False,
                        dry_run=False,
                    )

                    assert result == 0


class TestCheck:
    """Tests for check command."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock ReleaseManager."""
        mock_mgr = Mock()

        # Mock pre-release checks result
        mock_check = Mock()
        mock_check.check_name = "Git Clean"
        mock_check.passed = True
        mock_check.message = "Working directory is clean"
        mock_check.details = None

        mock_checks_result = Mock()
        mock_checks_result.success = True
        mock_checks_result.checks = [mock_check]
        mock_checks_result.ci_provider_name = "GitHub Actions"
        mock_checks_result.registry_provider_name = "PyPI"

        mock_mgr.run_pre_release_checks.return_value = mock_checks_result

        return mock_mgr

    def test_check_all_passed(self, mock_manager):
        """Test check when all checks pass."""
        with patch("devloop.cli.commands.release.ReleaseConfig") as MockConfig:
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = check(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                    )

                    assert result == 0
                    MockConfig.assert_called_once()
                    config_call = MockConfig.call_args[1]
                    # Check command should not create tag or publish
                    assert config_call["create_tag"] is False
                    assert config_call["publish"] is False

    def test_check_with_custom_branch(self, mock_manager):
        """Test check with custom branch."""
        with patch("devloop.cli.commands.release.ReleaseConfig") as MockConfig:
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = check(
                        version="2.0.0",
                        branch="release",
                        ci_provider=None,
                        registry_provider=None,
                    )

                    assert result == 0
                    config_call = MockConfig.call_args[1]
                    assert config_call["version"] == "2.0.0"
                    assert config_call["branch"] == "release"

    def test_check_with_custom_providers(self, mock_manager):
        """Test check with custom CI and registry providers."""
        with patch("devloop.cli.commands.release.ReleaseConfig") as MockConfig:
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = check(
                        version="1.0.0",
                        branch="main",
                        ci_provider="github",
                        registry_provider="artifactory",
                    )

                    assert result == 0
                    config_call = MockConfig.call_args[1]
                    assert config_call["ci_provider"] == "github"
                    assert config_call["registry_provider"] == "artifactory"

    def test_check_some_failed(self, mock_manager):
        """Test check when some checks fail."""
        # Mock failed checks
        mock_check1 = Mock()
        mock_check1.check_name = "Git Clean"
        mock_check1.passed = True
        mock_check1.message = "OK"

        mock_check2 = Mock()
        mock_check2.check_name = "CI Status"
        mock_check2.passed = False
        mock_check2.message = "CI is failing"
        mock_check2.details = "Last build failed with errors"

        mock_checks_result = Mock()
        mock_checks_result.success = False
        mock_checks_result.checks = [mock_check1, mock_check2]

        mock_manager.run_pre_release_checks.return_value = mock_checks_result

        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = check(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                    )

                    assert result == 1

    def test_check_displays_provider_info(self, mock_manager):
        """Test check displays provider information."""
        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console") as mock_console:
                    result = check(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                    )

                    assert result == 0
                    # Should print provider info
                    mock_console.print.assert_called()

    def test_check_no_provider_names(self, mock_manager):
        """Test check when no provider names are available."""
        mock_checks_result = Mock()
        mock_checks_result.success = True
        mock_checks_result.checks = []
        mock_checks_result.ci_provider_name = None
        mock_checks_result.registry_provider_name = None

        mock_manager.run_pre_release_checks.return_value = mock_checks_result

        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = check(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                    )

                    assert result == 0

    def test_check_failed_with_details(self, mock_manager):
        """Test check displays details for failed checks."""
        mock_check = Mock()
        mock_check.check_name = "Registry Auth"
        mock_check.passed = False
        mock_check.message = "Authentication failed"
        mock_check.details = "Invalid token or credentials"

        mock_checks_result = Mock()
        mock_checks_result.success = False
        mock_checks_result.checks = [mock_check]

        mock_manager.run_pre_release_checks.return_value = mock_checks_result

        with patch("devloop.cli.commands.release.ReleaseConfig"):
            with patch(
                "devloop.cli.commands.release.ReleaseManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.release.console"):
                    result = check(
                        version="1.0.0",
                        branch="main",
                        ci_provider=None,
                        registry_provider=None,
                    )

                    assert result == 1
