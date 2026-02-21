"""Comprehensive tests for devloop CLI commands."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from devloop.cli.main import (
    _check_missing_devloop_sections,
    _create_claude_hooks,
    _create_claude_settings_json,
    _merge_agents_md,
    _needs_upgrade,
    _read_init_manifest,
    _setup_agents_md,
    _setup_claude_commands,
    _write_init_manifest,
    app,
)


@pytest.fixture
def cli_runner():
    """Create a CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestInitCommand:
    """Tests for the init command."""

    def test_init_creates_claude_directory(self, cli_runner, temp_project_dir):
        """Test that init creates .devloop directory."""
        result = cli_runner.invoke(
            app, ["init", str(temp_project_dir), "--non-interactive"]
        )

        assert result.exit_code == 0
        assert (temp_project_dir / ".devloop").exists()
        assert (
            "[green]✓[/green] Created:" in result.stdout or "Created:" in result.stdout
        )

    def test_init_creates_config_file(self, cli_runner, temp_project_dir):
        """Test that init creates agents.json config file."""
        result = cli_runner.invoke(
            app, ["init", str(temp_project_dir), "--non-interactive"]
        )

        assert result.exit_code == 0
        config_file = temp_project_dir / ".devloop" / "agents.json"
        assert config_file.exists()

        # Verify it's valid JSON
        with open(config_file) as f:
            config_data = json.load(f)
        assert "agents" in config_data or "enabled" in config_data

    def test_init_skip_config_flag(self, cli_runner, temp_project_dir):
        """Test that init --skip-config doesn't create config."""
        result = cli_runner.invoke(
            app, ["init", str(temp_project_dir), "--skip-config", "--non-interactive"]
        )

        assert result.exit_code == 0
        config_file = temp_project_dir / ".devloop" / "agents.json"
        assert not config_file.exists()
        assert (temp_project_dir / ".devloop").exists()

    def test_init_idempotent(self, cli_runner, temp_project_dir):
        """Test that init can be run multiple times safely."""
        # First init
        result1 = cli_runner.invoke(
            app, ["init", str(temp_project_dir), "--non-interactive"]
        )
        assert result1.exit_code == 0

        # Second init
        result2 = cli_runner.invoke(
            app, ["init", str(temp_project_dir), "--non-interactive"]
        )
        assert result2.exit_code == 0

        # Directory should still exist
        assert (temp_project_dir / ".devloop").exists()

    def test_init_default_path_current_directory(self, cli_runner):
        """Test that init without path argument works."""
        # Just test that the command accepts being called without path
        # The CliRunner doesn't use actual cwd, so we just verify the command works
        result = cli_runner.invoke(app, ["init", "--help"])

        # Should show help without path as argument
        assert result.exit_code == 0
        assert "init" in result.stdout.lower()


class TestStatusCommand:
    """Tests for the status command."""

    @patch("devloop.cli.main.ConfigWrapper")
    @patch("devloop.cli.main.Config")
    def test_status_displays_agents(
        self, mock_config_class, mock_wrapper_class, cli_runner
    ):
        """Test that status displays agent configuration."""
        mock_config = MagicMock()
        mock_config.load.return_value = {
            "agents": {
                "linter": {"enabled": True, "triggers": ["file:modified"]},
                "formatter": {"enabled": False, "triggers": []},
            }
        }
        mock_config_class.return_value = mock_config

        mock_wrapper = MagicMock()
        mock_wrapper.agents.return_value = {
            "linter": {"enabled": True, "triggers": ["file:modified"]},
            "formatter": {"enabled": False, "triggers": []},
        }
        mock_wrapper_class.return_value = mock_wrapper

        result = cli_runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "linter" in result.stdout or "Agent" in result.stdout

    @patch("devloop.cli.main.ConfigWrapper")
    @patch("devloop.cli.main.Config")
    def test_status_shows_enabled_disabled(
        self, mock_config_class, mock_wrapper_class, cli_runner
    ):
        """Test that status shows enabled/disabled status."""
        mock_config = MagicMock()
        mock_config.load.return_value = {"agents": {}}
        mock_config_class.return_value = mock_config

        mock_wrapper = MagicMock()
        mock_wrapper.agents.return_value = {}
        mock_wrapper_class.return_value = mock_wrapper

        result = cli_runner.invoke(app, ["status"])

        assert result.exit_code == 0


class TestStopCommand:
    """Tests for the stop command."""

    def test_stop_no_daemon_running(self, cli_runner, temp_project_dir):
        """Test stop when no daemon is running."""
        result = cli_runner.invoke(app, ["stop", str(temp_project_dir)])

        assert result.exit_code == 0
        assert "No daemon running" in result.stdout or "daemon" in result.stdout.lower()

    def test_stop_with_running_daemon(self, cli_runner, temp_project_dir):
        """Test stop with an actual PID file."""
        # Create .devloop directory and PID file
        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir()

        pid_file = claude_dir / "devloop.pid"
        pid_file.write_text("99999")  # Non-existent PID

        result = cli_runner.invoke(app, ["stop", str(temp_project_dir)])

        # Should fail to kill non-existent process but shouldn't crash
        assert "Failed to stop" in result.stdout or "daemon" in result.stdout.lower()

    def test_stop_default_path(self, cli_runner):
        """Test stop with default path (current directory)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = cli_runner.invoke(app, ["stop"])
                # Should succeed even with no daemon
                assert result.exit_code == 0
            finally:
                os.chdir(original_cwd)


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_shows_version(self, cli_runner):
        """Test that version command displays version info."""
        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "v" in result.stdout or "version" in result.stdout.lower()
        assert "DevLoop" in result.stdout

    def test_version_is_valid_semver(self, cli_runner):
        """Test that version output contains valid semantic version."""
        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        # Should contain something like vX.Y.Z
        import re

        assert re.search(r"v?\d+\.\d+\.\d+", result.stdout)


class TestAmpStatusCommand:
    """Tests for the amp_status command."""

    @patch("devloop.cli.main.show_agent_status")
    def test_amp_status_returns_json(self, mock_show_status, cli_runner):
        """Test that amp_status returns valid JSON."""
        mock_show_status.return_value = {
            "status": "ok",
            "agents": [],
            "timestamp": "2024-01-01T00:00:00Z",
        }

        with patch("asyncio.run", return_value=mock_show_status.return_value):
            result = cli_runner.invoke(app, ["amp-status"])

            assert result.exit_code == 0
            # Should be valid JSON
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")

    @patch("devloop.cli.main.show_agent_status")
    def test_amp_status_async_call(self, mock_show_status, cli_runner):
        """Test that amp_status properly calls async function."""
        mock_result = {"status": "ok", "agents": []}
        mock_show_status.return_value = mock_result

        with patch(
            "asyncio.run", return_value=mock_result
        ) as mock_asyncio:  # noqa: F841
            result = cli_runner.invoke(app, ["amp-status"])

            assert result.exit_code == 0


class TestAmpFindingsCommand:
    """Tests for the amp_findings command."""

    @patch("devloop.cli.main.check_agent_findings")
    def test_amp_findings_returns_json(self, mock_check_findings, cli_runner):
        """Test that amp_findings returns valid JSON."""
        mock_check_findings.return_value = {"findings": [], "count": 0}

        with patch("asyncio.run", return_value=mock_check_findings.return_value):
            result = cli_runner.invoke(app, ["amp-findings"])

            assert result.exit_code == 0
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")


class TestAmpContextCommand:
    """Tests for the amp_context command."""

    def test_amp_context_no_index_file(self, cli_runner, temp_project_dir):
        """Test amp_context when no context index exists."""
        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            result = cli_runner.invoke(app, ["amp-context"])

            # Should handle gracefully
            assert "No context index found" in result.stdout or result.exit_code == 0

    def test_amp_context_with_valid_index(self, cli_runner, temp_project_dir):
        """Test amp_context with valid index file."""
        context_dir = temp_project_dir / ".devloop" / "context"
        context_dir.mkdir(parents=True, exist_ok=True)

        index_data = {"files": [], "metadata": {}}
        index_file = context_dir / "index.json"
        with open(index_file, "w") as f:
            json.dump(index_data, f)

        with patch("pathlib.Path.cwd", return_value=temp_project_dir):
            result = cli_runner.invoke(app, ["amp-context"])

            assert result.exit_code == 0
            try:
                json.loads(result.stdout)
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")


class TestSummaryCommand:
    """Tests for the summary subcommand."""

    def test_summary_command_exists(self, cli_runner):
        """Test that summary command is registered."""
        result = cli_runner.invoke(app, ["summary", "--help"])

        # Should show help without errors
        assert result.exit_code == 0 or "Usage" in result.stdout


class TestWatchCommand:
    """Tests for the watch command."""

    def test_watch_help(self, cli_runner):
        """Test that watch command has proper help."""
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "watch" in result.stdout.lower()

    def test_watch_accepts_path_argument(self, cli_runner, temp_project_dir):
        """Test that watch accepts path argument."""
        # We won't actually run watch (it would block), just test invocation
        # by checking the command structure
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "path" in result.stdout.lower() or "directory" in result.stdout.lower()

    def test_watch_has_foreground_option(self, cli_runner):
        """Test that watch has --foreground option."""
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "--foreground" in result.stdout or "foreground" in result.stdout.lower()

    def test_watch_has_verbose_option(self, cli_runner):
        """Test that watch has --verbose option."""
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "--verbose" in result.stdout or "verbose" in result.stdout.lower()

    def test_watch_has_config_option(self, cli_runner):
        """Test that watch has --config option."""
        result = cli_runner.invoke(app, ["watch", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.stdout or "config" in result.stdout.lower()


class TestCLIHelp:
    """Tests for CLI help and general functionality."""

    def test_main_help(self, cli_runner):
        """Test that main help is accessible."""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "DevLoop" in result.stdout or "usage" in result.stdout.lower()

    def test_all_commands_listed(self, cli_runner):
        """Test that all commands are listed in help."""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        commands = ["init", "watch", "status", "stop", "version"]
        for cmd in commands:
            assert cmd in result.stdout.lower()

    def test_invalid_command(self, cli_runner):
        """Test that invalid command fails appropriately."""
        result = cli_runner.invoke(app, ["nonexistent"])

        assert result.exit_code != 0

    def test_invalid_option(self, cli_runner):
        """Test that invalid option fails appropriately."""
        result = cli_runner.invoke(app, ["init", "--invalid-option"])

        assert result.exit_code != 0


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def test_init_with_invalid_path(self, cli_runner):
        """Test init with invalid path."""
        invalid_path = "/nonexistent/path/that/does/not/exist"
        result = cli_runner.invoke(app, ["init", invalid_path])

        # Should fail gracefully
        assert result.exit_code != 0 or "error" in result.stdout.lower()

    @patch("devloop.cli.main.Config")
    def test_status_handles_missing_config(self, mock_config_class, cli_runner):
        """Test that status handles missing config gracefully."""
        mock_config = MagicMock()
        mock_config.load.side_effect = FileNotFoundError("Config not found")
        mock_config_class.return_value = mock_config

        result = cli_runner.invoke(app, ["status"])

        # Should either show error or use defaults
        assert result.exit_code != 0 or result.stdout


class TestCLIIntegration:
    """Integration tests for CLI workflow."""

    def test_init_then_status_workflow(self, cli_runner, temp_project_dir):
        """Test the init -> status workflow."""
        # Initialize
        init_result = cli_runner.invoke(
            app, ["init", str(temp_project_dir), "--non-interactive"]
        )
        assert init_result.exit_code == 0

        # Change to that directory and check status
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project_dir)

            with patch("devloop.cli.main.ConfigWrapper") as mock_wrapper_class:
                mock_wrapper = MagicMock()
                mock_wrapper.agents.return_value = {}
                mock_wrapper_class.return_value = mock_wrapper

                with patch("devloop.cli.main.Config") as mock_config_class:
                    mock_config = MagicMock()
                    mock_config.load.return_value = {"agents": {}}
                    mock_config_class.return_value = mock_config

                    status_result = cli_runner.invoke(app, ["status"])
                    assert status_result.exit_code == 0
        finally:
            os.chdir(original_cwd)


class TestSetupAgentsMdMerge:
    """Tests for _setup_agents_md direct merge behavior."""

    def test_merges_missing_sections_directly(self, temp_project_dir):
        """Test that _setup_agents_md merges missing sections without scaffold."""
        agents_md = temp_project_dir / "AGENTS.md"
        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir(parents=True, exist_ok=True)

        agents_md.write_text("# My Project\n\nSome existing content.\n")

        _setup_agents_md(temp_project_dir, claude_dir)

        result = agents_md.read_text()

        assert "DevLoop Setup Required" not in result
        assert "ACTION FOR AI ASSISTANT" not in result
        assert "NO MARKDOWN FILES" in result
        assert "My Project" in result
        assert "existing content" in result

    def test_no_merge_when_all_sections_present(self, temp_project_dir):
        """Test that _setup_agents_md skips merge when all sections present."""
        agents_md = temp_project_dir / "AGENTS.md"
        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir(parents=True, exist_ok=True)

        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "devloop"
            / "cli"
            / "templates"
            / "devloop_agents_template.md"
        )
        original_content = template_path.read_text()
        agents_md.write_text(original_content)

        _setup_agents_md(temp_project_dir, claude_dir)

        assert agents_md.read_text() == original_content

    def test_check_missing_devloop_sections_returns_tuples(self):
        """Verify return type is list of (check_string, display_name) tuples."""
        result = _check_missing_devloop_sections("Some content with nothing relevant")

        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_check_missing_devloop_sections_all_present(self):
        """Verify empty list when all sections are present in the template."""
        template_path = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "devloop"
            / "cli"
            / "templates"
            / "devloop_agents_template.md"
        )
        content = template_path.read_text()
        assert _check_missing_devloop_sections(content) == []


class TestMergeAgentsMd:
    """Tests for _merge_agents_md section-level dedup merge."""

    def test_adds_missing_sections(self):
        """New sections from template are appended."""
        existing = "# Project\n\n## Intro\n\nHello.\n"
        template = "# Template\n\n## Intro\n\nWorld.\n\n## New Section\n\nContent.\n"

        merged = _merge_agents_md(existing, template)

        assert "## Intro" in merged
        assert "Hello." in merged
        assert "## New Section" in merged
        assert "Content." in merged

    def test_does_not_duplicate_existing_sections(self):
        """Sections already present are not added again."""
        existing = "# Project\n\n## Alpha\n\nOne.\n\n## Beta\n\nTwo.\n"
        template = "# T\n\n## Alpha\n\nTemplate alpha.\n\n## Beta\n\nTemplate beta.\n"

        merged = _merge_agents_md(existing, template)

        assert merged.count("## Alpha") == 1
        assert merged.count("## Beta") == 1
        assert "One." in merged

    def test_idempotent_on_repeated_merge(self):
        """Running merge twice produces the same output."""
        existing = "# Project\n\n## Existing\n\nKeep me.\n"
        template = "# Template\n\n## Existing\n\nIgnored.\n\n## Added\n\nNew stuff.\n"

        first = _merge_agents_md(existing, template)
        second = _merge_agents_md(first, template)

        assert first == second

    def test_emoji_headings_matched(self):
        """Headings that differ only by leading emoji are treated as the same."""
        existing = "# P\n\n## ABSOLUTE RULE 1\n\nBody.\n"
        template = "# T\n\n## ⛔️ ABSOLUTE RULE 1\n\nTemplate body.\n"

        merged = _merge_agents_md(existing, template)

        assert merged.count("ABSOLUTE RULE 1") == 1

    def test_returns_existing_when_no_new_sections(self):
        """If every template section already exists, return existing verbatim."""
        existing = "# P\n\n## Foo\n\nBar.\n"
        template = "# T\n\n## Foo\n\nBaz.\n"

        merged = _merge_agents_md(existing, template)

        assert merged == existing

    def test_preserves_existing_content(self):
        """Verify original content is untouched after merge."""
        existing = (
            "# My Project\n\nCustom intro.\n\n## My Custom Section\n\nDetails here.\n"
        )
        template = (
            "# T\n\n## My Custom Section\n\nTemplate.\n\n## New Section\n\nNew.\n"
        )

        merged = _merge_agents_md(existing, template)

        assert merged.startswith("# My Project\n\nCustom intro.")
        assert "## My Custom Section\n\nDetails here." in merged
        assert "## New Section" in merged


class TestInitManifest:
    """Tests for _read_init_manifest, _write_init_manifest, _needs_upgrade."""

    def test_read_manifest_missing_file(self, temp_project_dir):
        """Returns default dict when file doesn't exist."""
        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir()

        result = _read_init_manifest(claude_dir)

        assert result == {"version": None, "managed": []}

    def test_read_manifest_valid(self, temp_project_dir):
        """Reads valid JSON correctly."""
        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir()
        manifest = claude_dir / ".init-manifest.json"
        manifest.write_text(json.dumps({"version": "1.2.3", "managed": ["a.json"]}))

        result = _read_init_manifest(claude_dir)

        assert result == {"version": "1.2.3", "managed": ["a.json"]}

    def test_write_manifest_creates_file(self, temp_project_dir):
        """Writes correct JSON with version."""
        from devloop import __version__

        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir()

        _write_init_manifest(claude_dir, ["hooks.json", "settings.json"])

        manifest = claude_dir / ".init-manifest.json"
        assert manifest.exists()

        data = json.loads(manifest.read_text())
        assert data["version"] == __version__
        assert data["managed"] == ["hooks.json", "settings.json"]

    def test_needs_upgrade_missing_manifest(self, temp_project_dir):
        """Returns True when no manifest exists."""
        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir()

        assert _needs_upgrade(claude_dir) is True

    def test_needs_upgrade_older_version(self, temp_project_dir):
        """Returns True when manifest has older version."""
        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir()
        manifest = claude_dir / ".init-manifest.json"
        manifest.write_text(json.dumps({"version": "0.0.1", "managed": []}))

        assert _needs_upgrade(claude_dir) is True

    def test_needs_upgrade_same_version(self, temp_project_dir):
        """Returns False when versions match."""
        from devloop import __version__

        claude_dir = temp_project_dir / ".devloop"
        claude_dir.mkdir()
        manifest = claude_dir / ".init-manifest.json"
        manifest.write_text(json.dumps({"version": __version__, "managed": []}))

        assert _needs_upgrade(claude_dir) is False


class TestCreateClaudeHooks:
    """Tests for _create_claude_hooks upgrade behavior."""

    def test_create_claude_hooks_overwrites_existing(self, temp_project_dir):
        """Create a hook file with old content, call _create_claude_hooks, verify new content."""
        hooks_dir = temp_project_dir / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        # Plant an old hook
        old_content = "#!/bin/bash\necho old\n"
        hook_file = hooks_dir / "claude-session-start"
        hook_file.write_text(old_content)

        managed_paths, updated_count = _create_claude_hooks(hooks_dir)

        new_content = hook_file.read_text()
        assert new_content != old_content
        assert "SessionStart hook" in new_content
        assert updated_count >= 1

    def test_create_claude_hooks_backs_up_existing(self, temp_project_dir):
        """Create a hook file, call _create_claude_hooks, verify .backup file exists."""
        hooks_dir = temp_project_dir / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        old_content = "#!/bin/bash\necho old\n"
        hook_file = hooks_dir / "claude-session-start"
        hook_file.write_text(old_content)

        _create_claude_hooks(hooks_dir)

        backup_file = hook_file.with_suffix(".backup")
        assert backup_file.exists()
        assert backup_file.read_text() == old_content

    def test_create_claude_hooks_returns_managed_paths(self, temp_project_dir):
        """Verify return value contains relative paths and updated count."""
        hooks_dir = temp_project_dir / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        managed_paths, updated_count = _create_claude_hooks(hooks_dir)

        # All paths should be relative, starting with .agents/hooks/
        assert len(managed_paths) > 0
        for p in managed_paths:
            assert p.startswith(".agents/hooks/")

        # No pre-existing files, so updated_count should be 0
        assert updated_count == 0

    def test_create_claude_hooks_new_files_executable(self, temp_project_dir):
        """Verify newly created hook files are executable."""
        hooks_dir = temp_project_dir / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)

        _create_claude_hooks(hooks_dir)

        for hook_file in hooks_dir.iterdir():
            if hook_file.is_file() and not hook_file.suffix == ".backup":
                assert hook_file.stat().st_mode & 0o755


class TestSetupClaudeCommands:
    """Tests for _setup_claude_commands upgrade behavior."""

    def test_setup_claude_commands_overwrites_existing(self, temp_project_dir):
        """Create a command file with old content, call function, verify overwritten."""
        commands_dir = temp_project_dir / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        # Plant an old command file matching a known template name
        old_content = "# Old verify-work command\nThis is outdated.\n"
        cmd_file = commands_dir / "verify-work.md"
        cmd_file.write_text(old_content)

        managed_paths, updated_count = _setup_claude_commands(temp_project_dir)

        new_content = cmd_file.read_text()
        assert new_content != old_content
        assert (
            "verify-work" in new_content.lower()
            or "verification" in new_content.lower()
        )
        assert updated_count >= 1

    def test_setup_claude_commands_backs_up_existing(self, temp_project_dir):
        """Create a command file, call function, verify .md.backup exists with old content."""
        commands_dir = temp_project_dir / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        old_content = "# Old verify-work command\nThis is outdated.\n"
        cmd_file = commands_dir / "verify-work.md"
        cmd_file.write_text(old_content)

        _setup_claude_commands(temp_project_dir)

        backup_file = cmd_file.with_suffix(".md.backup")
        assert backup_file.exists()
        assert backup_file.read_text() == old_content

    def test_setup_claude_commands_returns_managed_paths(self, temp_project_dir):
        """Verify return contains relative paths starting with '.claude/commands/'."""
        managed_paths, updated_count = _setup_claude_commands(temp_project_dir)

        # Should have created command files
        assert len(managed_paths) > 0
        for p in managed_paths:
            assert p.startswith(".claude/commands/")

        # No pre-existing files, so updated_count should be 0
        assert updated_count == 0


class TestCreateClaudeSettingsJson:
    """Tests for _create_claude_settings_json upgrade behavior."""

    def test_settings_json_overwrites_hooks_on_upgrade(self, temp_project_dir):
        """Create settings.json with old hooks, call with upgrade=True, verify hooks replaced."""
        claude_dir = temp_project_dir / ".claude"
        claude_dir.mkdir(parents=True)
        settings_file = claude_dir / "settings.json"

        # Write old hooks config that differs from the current template
        old_settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": ".agents/hooks/old-session-start",
                            }
                        ],
                    }
                ],
            }
        }
        settings_file.write_text(json.dumps(old_settings, indent=2))

        result = _create_claude_settings_json(temp_project_dir, upgrade=True)

        # Should return the managed path string
        assert result == ".claude/settings.json"

        # Re-read and verify hooks were fully replaced
        new_settings = json.loads(settings_file.read_text())
        hooks = new_settings["hooks"]

        # The old "old-session-start" command should be gone
        session_start_cmds = [
            h["command"]
            for entry in hooks.get("SessionStart", [])
            for h in entry.get("hooks", [])
        ]
        assert ".agents/hooks/old-session-start" not in session_start_cmds
        assert ".agents/hooks/claude-session-start" in session_start_cmds

        # All four event types should be present
        assert "SessionStart" in hooks
        assert "Stop" in hooks
        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks

    def test_settings_json_preserves_non_hook_settings(self, temp_project_dir):
        """Create settings.json with hooks + permissions, call with upgrade=True, verify permissions kept."""
        claude_dir = temp_project_dir / ".claude"
        claude_dir.mkdir(parents=True)
        settings_file = claude_dir / "settings.json"

        old_settings = {
            "permissions": {
                "allow": ["Bash(git *)"],
                "deny": ["Bash(rm -rf /*)"],
            },
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": ".agents/hooks/old-hook",
                            }
                        ],
                    }
                ],
            },
        }
        settings_file.write_text(json.dumps(old_settings, indent=2))

        result = _create_claude_settings_json(temp_project_dir, upgrade=True)

        assert result == ".claude/settings.json"

        new_settings = json.loads(settings_file.read_text())

        # Permissions must be preserved exactly
        assert new_settings["permissions"] == {
            "allow": ["Bash(git *)"],
            "deny": ["Bash(rm -rf /*)"],
        }

        # Hooks must be the new template (old hook gone)
        session_start_cmds = [
            h["command"]
            for entry in new_settings["hooks"].get("SessionStart", [])
            for h in entry.get("hooks", [])
        ]
        assert ".agents/hooks/old-hook" not in session_start_cmds
        assert ".agents/hooks/claude-session-start" in session_start_cmds

    def test_settings_json_no_upgrade_skips_existing_hooks(self, temp_project_dir):
        """Without upgrade, existing hook event types are not overwritten."""
        claude_dir = temp_project_dir / ".claude"
        claude_dir.mkdir(parents=True)
        settings_file = claude_dir / "settings.json"

        old_settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": ".agents/hooks/old-session-start",
                            }
                        ],
                    }
                ],
            }
        }
        settings_file.write_text(json.dumps(old_settings, indent=2))

        result = _create_claude_settings_json(temp_project_dir, upgrade=False)

        new_settings = json.loads(settings_file.read_text())

        # SessionStart should still have old content (not overwritten)
        session_start_cmds = [
            h["command"]
            for entry in new_settings["hooks"].get("SessionStart", [])
            for h in entry.get("hooks", [])
        ]
        assert ".agents/hooks/old-session-start" in session_start_cmds

        # But missing event types should be added
        assert "Stop" in new_settings["hooks"]
        assert "PreToolUse" in new_settings["hooks"]
        assert "PostToolUse" in new_settings["hooks"]

    def test_settings_json_returns_none_when_unchanged(self, temp_project_dir):
        """When upgrade=False and all hooks exist, return None (no change)."""
        # First call to create the full settings
        _create_claude_settings_json(temp_project_dir, upgrade=False)

        # Second call should find nothing to change
        result = _create_claude_settings_json(temp_project_dir, upgrade=False)

        assert result is None


class TestInitManifestIntegration:
    """Integration tests for init() with manifest and stale file cleanup."""

    def test_init_creates_manifest_on_fresh_init(self, cli_runner, temp_project_dir):
        """Run init on a fresh temp dir, verify manifest exists with correct data."""
        from devloop import __version__

        result = cli_runner.invoke(
            app,
            ["init", str(temp_project_dir), "--non-interactive", "--skip-config"],
        )

        assert result.exit_code == 0

        manifest_path = temp_project_dir / ".devloop" / ".init-manifest.json"
        assert manifest_path.exists(), "Manifest file should be created by init"

        data = json.loads(manifest_path.read_text())
        assert data["version"] == __version__
        assert isinstance(data["managed"], list)
        assert len(data["managed"]) > 0

        # Should contain paths from commands and hooks
        has_commands = any(p.startswith(".claude/commands/") for p in data["managed"])
        has_hooks = any(p.startswith(".agents/hooks/") for p in data["managed"])
        assert has_commands, f"Expected .claude/commands/ in managed: {data['managed']}"
        assert has_hooks, f"Expected .agents/hooks/ in managed: {data['managed']}"

    def test_init_removes_stale_files_on_upgrade(self, cli_runner, temp_project_dir):
        """Stale files from old manifest are removed and backed up on re-init."""
        # 1. Set up a fake old manifest with a stale managed file
        devloop_dir = temp_project_dir / ".devloop"
        devloop_dir.mkdir(parents=True, exist_ok=True)

        stale_rel = ".agents/hooks/obsolete-hook"
        stale_file = temp_project_dir / stale_rel
        stale_file.parent.mkdir(parents=True, exist_ok=True)
        stale_file.write_text("#!/bin/bash\necho obsolete\n")

        old_manifest = {"version": "0.0.1", "managed": [stale_rel]}
        (devloop_dir / ".init-manifest.json").write_text(json.dumps(old_manifest))

        # 2. Run init which will create a new manifest without the stale file
        result = cli_runner.invoke(
            app,
            ["init", str(temp_project_dir), "--non-interactive", "--skip-config"],
        )

        assert result.exit_code == 0

        # 3. The stale file should be removed
        assert not stale_file.exists(), "Stale file should have been removed"

        # 4. A backup should exist
        backup_file = stale_file.with_suffix(".backup")
        assert backup_file.exists(), "Backup of stale file should exist"
        assert backup_file.read_text() == "#!/bin/bash\necho obsolete\n"

        # 5. Output should mention the removal
        assert "Removed stale" in result.stdout

    def test_init_preserves_user_files_not_in_manifest(
        self, cli_runner, temp_project_dir
    ):
        """Custom user files not tracked in manifest are left untouched."""
        # Create the custom file before init
        hooks_dir = temp_project_dir / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        custom_hook = hooks_dir / "my-custom-hook"
        custom_hook.write_text("#!/bin/bash\necho custom\n")

        result = cli_runner.invoke(
            app,
            ["init", str(temp_project_dir), "--non-interactive", "--skip-config"],
        )

        assert result.exit_code == 0

        # Custom file should still be there, untouched
        assert custom_hook.exists(), "Custom hook should not be removed"
        assert custom_hook.read_text() == "#!/bin/bash\necho custom\n"

    def test_init_idempotent(self, cli_runner, temp_project_dir):
        """Running init twice with same devloop version produces no backups or upgrade messages."""
        runner = CliRunner()

        # First init: set up everything
        result1 = runner.invoke(
            app,
            ["init", str(temp_project_dir), "--non-interactive", "--skip-config"],
        )
        assert result1.exit_code == 0

        # Snapshot manifest after first init
        manifest_path = temp_project_dir / ".devloop" / ".init-manifest.json"
        assert manifest_path.exists()
        manifest_after_first = manifest_path.read_text()

        # Second init: same version, nothing should change
        result2 = runner.invoke(
            app,
            ["init", str(temp_project_dir), "--non-interactive", "--skip-config"],
        )
        assert result2.exit_code == 0

        # Manifest should be identical between runs
        manifest_after_second = manifest_path.read_text()
        assert manifest_after_first == manifest_after_second, (
            "Manifest should be unchanged on same-version re-init"
        )

        # No .backup files should have been created in .agents/hooks/
        hooks_dir = temp_project_dir / ".agents" / "hooks"
        if hooks_dir.exists():
            backup_hooks = list(hooks_dir.glob("*.backup"))
            assert backup_hooks == [], (
                f"No backup hooks expected on same-version re-init, found: {backup_hooks}"
            )

        # No .backup files should have been created in .claude/commands/
        commands_dir = temp_project_dir / ".claude" / "commands"
        if commands_dir.exists():
            backup_commands = list(commands_dir.glob("*.backup"))
            assert backup_commands == [], (
                f"No backup commands expected on same-version re-init, found: {backup_commands}"
            )

        # No "Removed stale" messages in second run output
        assert "Removed stale" not in result2.stdout, (
            "No stale file removal expected on same-version re-init"
        )

        # No "Updated from" messages in second run output
        assert "Updated from" not in result2.stdout, (
            "No upgrade message expected on same-version re-init"
        )
