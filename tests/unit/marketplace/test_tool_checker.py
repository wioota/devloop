"""Tests for ToolDependencyChecker."""

from unittest.mock import MagicMock, patch

import pytest

from devloop.marketplace.metadata import ToolDependency
from devloop.marketplace.tool_checker import ToolDependencyChecker


@pytest.fixture
def checker():
    return ToolDependencyChecker()


def test_binary_present(checker):
    dep = ToolDependency(type="binary")
    with patch(
        "devloop.marketplace.tool_checker.shutil.which",
        return_value="/usr/bin/shellcheck",
    ):
        result = checker.check_one("shellcheck", dep)
    assert result.present is True
    assert result.name == "shellcheck"


def test_binary_missing(checker):
    dep = ToolDependency(type="binary", install_hint="apt-get install shellcheck")
    with patch("devloop.marketplace.tool_checker.shutil.which", return_value=None):
        result = checker.check_one("shellcheck", dep)
    assert result.present is False
    assert result.remediation == "apt-get install shellcheck"


def test_binary_missing_no_hint(checker):
    dep = ToolDependency(type="binary")
    with patch("devloop.marketplace.tool_checker.shutil.which", return_value=None):
        result = checker.check_one("mytool", dep)
    assert result.present is False
    assert "mytool" in result.remediation


def test_python_package_present(checker):
    dep = ToolDependency(type="python", package="bandit", min_version="1.7.0")
    with patch(
        "devloop.marketplace.tool_checker.importlib.metadata.version",
        return_value="1.8.0",
    ):
        result = checker.check_one("bandit", dep)
    assert result.present is True
    assert result.found_version == "1.8.0"


def test_python_package_missing(checker):
    dep = ToolDependency(type="python", package="bandit")
    with patch(
        "devloop.marketplace.tool_checker.importlib.metadata.version",
        side_effect=Exception("not found"),
    ):
        result = checker.check_one("bandit", dep)
    assert result.present is False
    assert "pip install bandit" in result.remediation


def test_npm_global_present(checker):
    dep = ToolDependency(type="npm-global")
    with patch(
        "devloop.marketplace.tool_checker.shutil.which",
        return_value="/usr/local/bin/prettier",
    ):
        result = checker.check_one("prettier", dep)
    assert result.present is True


def test_npm_global_missing(checker):
    dep = ToolDependency(type="npm-global")
    with patch("devloop.marketplace.tool_checker.shutil.which", return_value=None):
        result = checker.check_one("prettier", dep)
    assert result.present is False
    assert "npm install -g prettier" in result.remediation


def test_docker_image_present(checker):
    dep = ToolDependency(type="docker")
    with patch(
        "devloop.marketplace.tool_checker.shutil.which", return_value="/usr/bin/docker"
    ):
        with patch("devloop.marketplace.tool_checker.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = checker.check_one("ubuntu:22.04", dep)
    assert result.present is True


def test_docker_missing_daemon(checker):
    dep = ToolDependency(type="docker")
    with patch("devloop.marketplace.tool_checker.shutil.which", return_value=None):
        result = checker.check_one("ubuntu:22.04", dep)
    assert result.present is False
    assert "docker" in result.remediation.lower()


def test_docker_subprocess_exception_returns_not_present(checker):
    """If docker inspect raises, treat image as not present."""
    dep = ToolDependency(type="docker")
    with patch(
        "devloop.marketplace.tool_checker.shutil.which", return_value="/usr/bin/docker"
    ):
        with patch(
            "devloop.marketplace.tool_checker.subprocess.run",
            side_effect=Exception("timeout"),
        ):
            result = checker.check_one("ubuntu:22.04", dep)
    assert result.present is False


def test_check_multiple(checker):
    deps = {
        "bandit": ToolDependency(type="python", package="bandit"),
        "shellcheck": ToolDependency(type="binary"),
    }
    with patch(
        "devloop.marketplace.tool_checker.importlib.metadata.version",
        return_value="1.8.0",
    ):
        with patch("devloop.marketplace.tool_checker.shutil.which", return_value=None):
            results = checker.check(deps)
    assert len(results) == 2
    bandit = next(r for r in results if r.name == "bandit")
    shellcheck = next(r for r in results if r.name == "shellcheck")
    assert bandit.present is True
    assert shellcheck.present is False


def test_version_check_failure_treated_as_present(checker):
    """If we can't determine version, still mark as present."""
    dep = ToolDependency(type="binary", min_version="1.0.0")
    with patch(
        "devloop.marketplace.tool_checker.shutil.which", return_value="/usr/bin/mytool"
    ):
        with patch(
            "devloop.marketplace.tool_checker.subprocess.run",
            side_effect=Exception("timeout"),
        ):
            result = checker.check_one("mytool", dep)
    assert result.present is True
    assert result.version_unverifiable is True


def test_unknown_type_returns_not_present(checker):
    dep = ToolDependency(type="unknown-type")
    result = checker.check_one("sometool", dep)
    assert result.present is False
    assert (
        "unknown-type" in result.remediation.lower()
        or "unknown" in result.remediation.lower()
    )
