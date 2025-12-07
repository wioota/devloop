"""Security and safety tests for auto-fix functionality."""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.core.auto_fix import AutoFix
from devloop.core.backup_manager import BackupManager
from devloop.core.config import AutonomousFixesConfig
from devloop.core.context_store import Finding


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        test_file = project_root / "test.py"
        test_file.write_text("print('Hello')\n")
        yield project_root


@pytest.fixture
def auto_fix_instance(temp_project):
    """Create an AutoFix instance."""
    return AutoFix(project_root=temp_project)


@pytest.fixture
def safe_config():
    """Create safe autonomous fixes configuration."""
    return AutonomousFixesConfig(enabled=True, safety_level="safe_only", opt_in=True)


@pytest.fixture
def unsafe_config():
    """Create configuration without opt-in."""
    return AutonomousFixesConfig(enabled=True, safety_level="safe_only", opt_in=False)


def make_finding(
    file_path: str,
    message: str = "test",
    agent: str = "formatter",
    severity: str = "info",
    auto_fixable: bool = True,
    context: dict = None,
) -> Finding:
    """Helper to create test findings."""
    return Finding(
        id=f"test-{hash(message) % 1000}",
        agent=agent,
        timestamp=datetime.now().isoformat(),
        file=file_path,
        message=message,
        severity=severity,
        auto_fixable=auto_fixable,
        context=context or {},
    )


def test_requires_explicit_opt_in(auto_fix_instance, temp_project):
    """Test that auto-fixes require explicit opt-in."""
    test_file = temp_project / "test.py"

    finding = make_finding(
        file_path=str(test_file), message="would format with black", agent="formatter"
    )

    unsafe_config = AutonomousFixesConfig(
        enabled=True, safety_level="safe_only", opt_in=False  # Not opted in
    )

    # Should not apply fix without opt-in
    with patch.object(
        auto_fix_instance, "_execute_fix", new_callable=AsyncMock
    ) as mock_execute:
        result = asyncio.run(
            auto_fix_instance._apply_single_fix("formatter", finding, unsafe_config)
        )

        # Execute should not be called
        mock_execute.assert_not_called()


@pytest.mark.skip(reason="Integration test needs refactoring - TODO follow-up")
def test_creates_backup_before_fix(auto_fix_instance, temp_project):
    """Test that backup is created before applying fix."""
    test_file = temp_project / "test.py"
    original_content = test_file.read_text()

    finding = make_finding(
        file_path=str(test_file), message="would format with black", agent="formatter"
    )

    config = AutonomousFixesConfig(enabled=True, safety_level="safe_only", opt_in=True)

    # Mock _execute_fix to always succeed
    with patch.object(
        auto_fix_instance, "_execute_fix", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = True

        result = asyncio.run(
            auto_fix_instance._apply_single_fix("formatter", finding, config)
        )

        assert result is True

    # Verify backup was created
    history = auto_fix_instance._backup_manager.get_change_history()
    assert len(history) > 0
    assert history[-1]["file_path"] == "test.py"
    assert history[-1]["fix_type"] == "formatter"


def test_aborts_fix_if_backup_fails(auto_fix_instance, temp_project):
    """Test that fix is aborted if backup creation fails."""
    test_file = temp_project / "test.py"

    finding = make_finding(
        file_path=str(test_file), message="would format with black", agent="formatter"
    )

    config = AutonomousFixesConfig(enabled=True, safety_level="safe_only", opt_in=True)

    # Mock backup creation to fail
    with patch.object(
        auto_fix_instance._backup_manager, "create_backup"
    ) as mock_backup:
        mock_backup.return_value = None  # Backup failed

        with patch.object(
            auto_fix_instance, "_execute_fix", new_callable=AsyncMock
        ) as mock_execute:
            result = asyncio.run(
                auto_fix_instance._apply_single_fix("formatter", finding, config)
            )

            # Fix should not be applied
            assert result is False
            mock_execute.assert_not_called()


@pytest.mark.skip(reason="Integration test needs refactoring - TODO follow-up")
def test_rollback_functionality(auto_fix_instance, temp_project):
    """Test that rollback restores original state."""
    test_file = temp_project / "test.py"
    original_content = test_file.read_text()

    finding = make_finding(
        file_path=str(test_file), message="would format with black", agent="formatter"
    )

    config = AutonomousFixesConfig(enabled=True, safety_level="safe_only", opt_in=True)

    # Apply fix (mocked to modify file)
    async def mock_execute_fix(agent_type, finding):
        # Simulate modification
        test_file.write_text("modified content\n")
        return True

    with patch.object(auto_fix_instance, "_execute_fix", new=mock_execute_fix):
        result = asyncio.run(
            auto_fix_instance._apply_single_fix("formatter", finding, config)
        )
        assert result is True

    # File should be modified
    assert test_file.read_text() != original_content

    # Rollback
    success = auto_fix_instance.rollback_last()
    assert success

    # File should be restored
    assert test_file.read_text() == original_content


def test_safety_level_filtering(auto_fix_instance):
    """Test that safety level filtering works correctly."""
    # Test safe_only level
    finding_safe = make_finding(
        file_path="test.py", message="would format with black", agent="formatter"
    )

    finding_risky = make_finding(
        file_path="test.py",
        message="unused variable x",
        severity="warning",
        agent="linter",
    )

    # safe_only should allow formatting
    assert auto_fix_instance._is_safe_for_config("formatter", finding_safe, "safe_only")

    # safe_only should not allow removing unused variables
    assert not auto_fix_instance._is_safe_for_config(
        "linter", finding_risky, "safe_only"
    )


@pytest.mark.skip(reason="Integration test needs refactoring - TODO follow-up")
def test_prevents_duplicate_fixes(auto_fix_instance, temp_project):
    """Test that the same fix is not applied multiple times."""
    test_file = temp_project / "test.py"

    finding = make_finding(
        file_path=str(test_file), message="would format with black", agent="formatter"
    )

    config = AutonomousFixesConfig(enabled=True, safety_level="safe_only", opt_in=True)

    with patch.object(
        auto_fix_instance, "_execute_fix", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = True

        # Apply fix first time
        result1 = asyncio.run(
            auto_fix_instance._apply_single_fix("formatter", finding, config)
        )
        assert result1 is True

        # Try to apply again
        result2 = asyncio.run(
            auto_fix_instance._apply_single_fix("formatter", finding, config)
        )
        assert result2 is False

        # Execute should only be called once
        assert mock_execute.call_count == 1


@pytest.mark.skip(reason="Integration test needs refactoring - TODO follow-up")
def test_tracks_applied_fixes(auto_fix_instance, temp_project):
    """Test that applied fixes are tracked."""
    test_file = temp_project / "test.py"

    finding = make_finding(
        file_path=str(test_file), message="would format with black", agent="formatter"
    )

    config = AutonomousFixesConfig(enabled=True, safety_level="safe_only", opt_in=True)

    with patch.object(
        auto_fix_instance, "_execute_fix", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = True

        result = asyncio.run(
            auto_fix_instance._apply_single_fix("formatter", finding, config)
        )
        assert result is True

    # Verify fix is tracked
    applied_fixes = auto_fix_instance.get_applied_fixes()
    assert len(applied_fixes) == 1
    assert applied_fixes[0]["finding_id"] == "test-1"
    assert applied_fixes[0]["agent_type"] == "formatter"
    assert applied_fixes[0]["file"] == str(test_file)
    assert "backup_id" in applied_fixes[0]


@pytest.mark.skip(reason="Integration test needs refactoring - TODO follow-up")
def test_rollback_all_session(auto_fix_instance, temp_project):
    """Test rolling back all fixes from a session."""
    test_file1 = temp_project / "test1.py"
    test_file2 = temp_project / "test2.py"

    test_file1.write_text("original1\n")
    test_file2.write_text("original2\n")

    finding1 = make_finding(
        file_path=str(test_file1), message="format test1", agent="formatter"
    )

    finding2 = make_finding(
        file_path=str(test_file2), message="format test2", agent="formatter"
    )

    config = AutonomousFixesConfig(enabled=True, safety_level="safe_only", opt_in=True)

    # Apply fixes (mocked to modify files)
    async def mock_execute_fix(agent_type, finding):
        file_path = Path(finding.file)
        file_path.write_text(f"modified {file_path.name}\n")
        return True

    with patch.object(auto_fix_instance, "_execute_fix", new=mock_execute_fix):
        asyncio.run(auto_fix_instance._apply_single_fix("formatter", finding1, config))
        asyncio.run(auto_fix_instance._apply_single_fix("formatter", finding2, config))

    # Files should be modified
    assert test_file1.read_text() != "original1\n"
    assert test_file2.read_text() != "original2\n"

    # Rollback all
    rolled_back = auto_fix_instance.rollback_all_session()
    assert rolled_back == 2

    # Files should be restored
    assert test_file1.read_text() == "original1\n"
    assert test_file2.read_text() == "original2\n"

    # Applied fixes should be cleared
    assert len(auto_fix_instance.get_applied_fixes()) == 0


def test_rejects_error_findings(auto_fix_instance):
    """Test that findings with errors are rejected."""
    finding = make_finding(
        file_path="test.py",
        message="syntax error in file",
        severity="error",
        agent="linter",
    )

    # Should be rejected regardless of safety level
    assert not auto_fix_instance._is_safe_for_config("linter", finding, "safe_only")
    assert not auto_fix_instance._is_safe_for_config("linter", finding, "medium_risk")
    assert not auto_fix_instance._is_safe_for_config("linter", finding, "all")


@pytest.mark.skip(reason="Integration test needs refactoring - TODO follow-up")
def test_metadata_in_backup(auto_fix_instance, temp_project):
    """Test that comprehensive metadata is stored in backups."""
    test_file = temp_project / "test.py"

    finding = make_finding(
        file_path=str(test_file),
        message="would format with black",
        agent="formatter",
        context={"formatter": "black"},
    )

    config = AutonomousFixesConfig(enabled=True, safety_level="safe_only", opt_in=True)

    with patch.object(
        auto_fix_instance, "_execute_fix", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = True

        asyncio.run(auto_fix_instance._apply_single_fix("formatter", finding, config))

    # Get the backup metadata
    history = auto_fix_instance._backup_manager.get_change_history()
    assert len(history) > 0

    latest_backup = history[-1]
    assert latest_backup["metadata"]["finding_id"] == "test-1"
    assert latest_backup["metadata"]["severity"] == "info"
    assert latest_backup["metadata"]["safety_level"] == "safe_only"
    assert "context" in latest_backup["metadata"]


# Integration test with pytest-asyncio
pytest_plugins = ("pytest_asyncio",)
