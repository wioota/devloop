"""Tests for release workflow management."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from devloop.providers.ci_provider import RunConclusion, RunStatus, WorkflowRun
from devloop.providers.registry_provider import PackageVersion
from devloop.release import ReleaseConfig, ReleaseManager, ReleaseResult


class TestReleaseConfig:
    """Test ReleaseConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ReleaseConfig(version="1.0.0")
        assert config.version == "1.0.0"
        assert config.branch == "main"
        assert config.tag_prefix == "v"
        assert config.create_tag is True
        assert config.publish is True
        assert config.ci_provider is None
        assert config.registry_provider is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = ReleaseConfig(
            version="2.0.0",
            branch="release",
            tag_prefix="release-",
            create_tag=False,
            publish=False,
            ci_provider="github",
            registry_provider="pypi",
        )
        assert config.version == "2.0.0"
        assert config.branch == "release"
        assert config.tag_prefix == "release-"
        assert config.create_tag is False
        assert config.publish is False


class TestReleaseManager:
    """Test ReleaseManager class."""

    @pytest.fixture
    def mock_ci_provider(self):
        """Create mock CI provider."""
        provider = Mock()
        provider.get_provider_name.return_value = "GitHub Actions"
        provider.is_available.return_value = True
        provider.get_status.return_value = WorkflowRun(
            id="run-123",
            name="CI",
            branch="main",
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.SUCCESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/example/actions/runs/123",
        )
        return provider

    @pytest.fixture
    def mock_registry_provider(self):
        """Create mock registry provider."""
        provider = Mock()
        provider.get_provider_name.return_value = "PyPI"
        provider.is_available.return_value = True
        provider.check_credentials.return_value = True
        provider.publish.return_value = True
        provider.get_package_url.return_value = "https://pypi.org/project/devloop/1.0.0"
        return provider

    @pytest.fixture
    def mock_provider_manager(self, mock_ci_provider, mock_registry_provider):
        """Create mock provider manager."""
        manager = Mock()
        manager.get_ci_provider.return_value = mock_ci_provider
        manager.auto_detect_ci_provider.return_value = mock_ci_provider
        manager.get_registry_provider.return_value = mock_registry_provider
        manager.auto_detect_registry_provider.return_value = mock_registry_provider
        return manager

    def test_get_ci_provider(self, mock_provider_manager):
        """Test getting CI provider."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            config = ReleaseConfig(version="1.0.0")
            manager = ReleaseManager(config)

            provider = manager.get_ci_provider()
            assert provider is not None
            assert provider.get_provider_name() == "GitHub Actions"

    def test_get_registry_provider(self, mock_provider_manager):
        """Test getting registry provider."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            config = ReleaseConfig(version="1.0.0")
            manager = ReleaseManager(config)

            provider = manager.get_registry_provider()
            assert provider is not None
            assert provider.get_provider_name() == "PyPI"

    def test_pre_release_checks_pass(self, mock_provider_manager):
        """Test all pre-release checks pass."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=True,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    config = ReleaseConfig(version="1.0.0")
                    manager = ReleaseManager(config)

                    result = manager.run_pre_release_checks()

                    assert result.success is True
                    assert len(result.checks) == 5
                    assert all(check.passed for check in result.checks)
                    assert result.ci_provider_name == "GitHub Actions"
                    assert result.registry_provider_name == "PyPI"

    def test_pre_release_checks_dirty_git(self, mock_provider_manager):
        """Test pre-release checks fail with dirty git."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=False,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    config = ReleaseConfig(version="1.0.0")
                    manager = ReleaseManager(config)

                    result = manager.run_pre_release_checks()

                    assert result.success is False
                    assert any(
                        check.check_name == "git_clean" and not check.passed
                        for check in result.checks
                    )

    def test_pre_release_checks_wrong_branch(self, mock_provider_manager):
        """Test pre-release checks fail on wrong branch."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=True,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="develop",
                ):
                    config = ReleaseConfig(version="1.0.0", branch="main")
                    manager = ReleaseManager(config)

                    result = manager.run_pre_release_checks()

                    assert result.success is False
                    assert any(
                        check.check_name == "correct_branch" and not check.passed
                        for check in result.checks
                    )

    def test_pre_release_checks_ci_failed(self, mock_provider_manager):
        """Test pre-release checks fail when CI fails."""
        mock_ci = mock_provider_manager.auto_detect_ci_provider.return_value
        mock_ci.get_status.return_value = WorkflowRun(
            id="run-123",
            name="CI",
            branch="main",
            status=RunStatus.COMPLETED,
            conclusion=RunConclusion.FAILURE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            url="https://github.com/example/actions/runs/123",
        )

        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=True,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    config = ReleaseConfig(version="1.0.0")
                    manager = ReleaseManager(config)

                    result = manager.run_pre_release_checks()

                    assert result.success is False
                    assert any(
                        check.check_name == "ci_status" and not check.passed
                        for check in result.checks
                    )

    def test_pre_release_checks_invalid_version(self, mock_provider_manager):
        """Test pre-release checks fail with invalid version."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=True,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    config = ReleaseConfig(version="invalid-version")
                    manager = ReleaseManager(config)

                    result = manager.run_pre_release_checks()

                    assert result.success is False
                    assert any(
                        check.check_name == "version_format" and not check.passed
                        for check in result.checks
                    )

    def test_validate_version_format(self, mock_provider_manager):
        """Test version format validation."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            config = ReleaseConfig(version="1.0.0")
            manager = ReleaseManager(config)

            assert manager._validate_version_format() is True

            manager.config.version = "1.0"
            assert manager._validate_version_format() is False

            manager.config.version = "v1.0.0"
            assert manager._validate_version_format() is False

    @patch("devloop.release.release_manager.subprocess.run")
    def test_create_release_tag(self, mock_subprocess, mock_provider_manager):
        """Test creating release tag."""
        # First call returns empty (tag doesn't exist), second call succeeds
        mock_subprocess.side_effect = [
            Mock(stdout="", returncode=0),  # Tag check
            Mock(returncode=0),  # Tag creation
        ]

        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            config = ReleaseConfig(version="1.0.0")
            manager = ReleaseManager(config)

            result = manager.create_release_tag()

            assert result.success is True
            assert result.tag_created is True
            assert result.url == "refs/tags/v1.0.0"

    @patch("devloop.release.release_manager.subprocess.run")
    def test_create_release_tag_already_exists(self, mock_subprocess, mock_provider_manager):
        """Test creating tag when tag already exists."""
        mock_subprocess.return_value = Mock(stdout="v1.0.0\n", returncode=0)

        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            config = ReleaseConfig(version="1.0.0")
            manager = ReleaseManager(config)

            result = manager.create_release_tag()

            assert result.success is False
            assert "already exists" in result.error

    def test_publish_release(self, mock_provider_manager):
        """Test publishing release."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            config = ReleaseConfig(version="1.0.0")
            manager = ReleaseManager(config)

            result = manager.publish_release()

            assert result.success is True
            assert result.published is True
            assert result.registry_provider_name == "PyPI"
            assert "pypi.org" in result.url

    def test_publish_release_no_provider(self, mock_provider_manager):
        """Test publishing fails when no registry provider."""
        mock_provider_manager.auto_detect_registry_provider.return_value = None

        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            config = ReleaseConfig(version="1.0.0")
            manager = ReleaseManager(config)

            result = manager.publish_release()

            assert result.success is False
            assert "no package registry" in result.error.lower()

    @patch("devloop.release.release_manager.subprocess.run")
    def test_full_release_workflow(self, mock_subprocess, mock_provider_manager):
        """Test complete release workflow."""
        mock_subprocess.side_effect = [
            Mock(stdout="", returncode=0),  # Tag check
            Mock(returncode=0),  # Tag creation
            Mock(returncode=0),  # Tag push
        ]

        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=True,
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    config = ReleaseConfig(version="1.0.0")
                    manager = ReleaseManager(config)

                    result = manager.release()

                    assert result.success is True
                    assert result.tag_created is True
                    assert result.published is True
                    assert len(result.checks) == 5

    @patch("devloop.release.release_manager.subprocess.run")
    def test_full_release_workflow_checks_fail(
        self, mock_subprocess, mock_provider_manager
    ):
        """Test release workflow stops if checks fail."""
        with patch(
            "devloop.release.release_manager.get_provider_manager",
            return_value=mock_provider_manager,
        ):
            with patch(
                "devloop.release.release_manager.ReleaseManager._check_git_clean",
                return_value=False,  # Dirty git
            ):
                with patch(
                    "devloop.release.release_manager.ReleaseManager._get_current_branch",
                    return_value="main",
                ):
                    config = ReleaseConfig(version="1.0.0")
                    manager = ReleaseManager(config)

                    result = manager.release()

                    assert result.success is False
                    # git tag commands should not be called if checks fail
                    tag_calls = [
                        call for call in mock_subprocess.call_args_list
                        if call and "tag" in str(call)
                    ]
                    assert len(tag_calls) == 0
