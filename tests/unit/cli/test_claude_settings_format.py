"""Tests that devloop generates valid Claude Code settings.json format.

Claude Code hooks schema (from https://code.claude.com/docs/en/hooks):
- Each hook type must be an array of matcher groups
- Each matcher group has an optional "matcher" (regex string) and required "hooks" array
- Each hook handler has "type" and "command" (for command hooks)

This test prevents regressions like the old object format:
    {"PostToolUse": {"hooks": [...]}}  # WRONG - causes "Expected array, but received object"
"""

import json
import subprocess
from pathlib import Path

import pytest

from devloop.cli.main import _create_claude_settings_json

# Valid hook event names per Claude Code docs
VALID_HOOK_EVENTS = {
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "PermissionRequest",
    "SessionStart",
    "SessionEnd",
    "Stop",
    "Notification",
    "SubagentStart",
    "SubagentStop",
    "UserPromptSubmit",
    "TeammateIdle",
    "TaskCompleted",
    "PreCompact",
}

VALID_HOOK_HANDLER_TYPES = {"command", "prompt", "agent"}


def _validate_claude_hooks_format(settings: dict) -> list[str]:
    """Validate that a settings dict conforms to Claude Code hooks schema.

    Based on https://code.claude.com/docs/en/hooks

    Returns a list of error strings (empty = valid).
    """
    errors = []

    if "hooks" not in settings:
        return errors  # No hooks is fine

    hooks = settings["hooks"]
    if not isinstance(hooks, dict):
        errors.append(f"hooks must be a dict, got {type(hooks).__name__}")
        return errors

    for hook_event, hook_entries in hooks.items():
        if hook_event not in VALID_HOOK_EVENTS:
            errors.append(f"Unknown hook event: {hook_event}")
            continue

        # Each hook event MUST be an array of matcher groups
        if not isinstance(hook_entries, list):
            errors.append(
                f"{hook_event}: must be an array, got {type(hook_entries).__name__}. "
                "This is the old object format that Claude Code no longer accepts."
            )
            continue

        for i, matcher_group in enumerate(hook_entries):
            prefix = f"{hook_event}[{i}]"

            if not isinstance(matcher_group, dict):
                errors.append(
                    f"{prefix}: matcher group must be a dict, got {type(matcher_group).__name__}"
                )
                continue

            # Must have "hooks" array
            if "hooks" not in matcher_group:
                errors.append(f"{prefix}: missing required 'hooks' key")
            elif not isinstance(matcher_group["hooks"], list):
                errors.append(
                    f"{prefix}.hooks: must be an array, "
                    f"got {type(matcher_group['hooks']).__name__}"
                )
            else:
                for j, handler in enumerate(matcher_group["hooks"]):
                    hprefix = f"{prefix}.hooks[{j}]"
                    if not isinstance(handler, dict):
                        errors.append(
                            f"{hprefix}: must be a dict, got {type(handler).__name__}"
                        )
                        continue
                    if "type" not in handler:
                        errors.append(f"{hprefix}: missing required 'type' key")
                    elif handler["type"] not in VALID_HOOK_HANDLER_TYPES:
                        errors.append(
                            f"{hprefix}: unknown type '{handler['type']}', "
                            f"expected one of {VALID_HOOK_HANDLER_TYPES}"
                        )
                    if handler.get("type") == "command" and "command" not in handler:
                        errors.append(f"{hprefix}: command hook missing 'command' key")
                    if handler.get("type") in ("prompt", "agent") and "prompt" not in handler:
                        errors.append(
                            f"{hprefix}: {handler['type']} hook missing 'prompt' key"
                        )

            # "matcher" is optional, but if present must be a string (regex)
            if "matcher" in matcher_group:
                if not isinstance(matcher_group["matcher"], str):
                    errors.append(
                        f"{prefix}.matcher: must be a regex string, "
                        f"got {type(matcher_group['matcher']).__name__}. "
                        "Per docs: 'The matcher field is a regex string'"
                    )

    return errors


class TestClaudeSettingsFormat:
    """Validate that devloop generates Claude Code-compatible settings."""

    def test_create_claude_settings_produces_valid_format(self, tmp_path):
        """_create_claude_settings_json must produce valid hooks format."""
        _create_claude_settings_json(tmp_path)

        settings_file = tmp_path / ".claude" / "settings.json"
        assert settings_file.exists(), "settings.json was not created"

        settings = json.loads(settings_file.read_text())
        errors = _validate_claude_hooks_format(settings)
        assert errors == [], "Invalid Claude Code settings format:\n" + "\n".join(errors)

    def test_all_hook_types_are_arrays(self, tmp_path):
        """Every hook type value must be an array, not an object."""
        _create_claude_settings_json(tmp_path)

        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        for hook_type, value in settings.get("hooks", {}).items():
            assert isinstance(value, list), (
                f"hooks.{hook_type} is {type(value).__name__}, must be a list. "
                f"The old object format causes: 'Expected array, but received object'"
            )

    def test_matchers_are_regex_strings(self, tmp_path):
        """Matchers must be regex strings per Claude Code docs."""
        _create_claude_settings_json(tmp_path)

        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
        for hook_type, entries in settings.get("hooks", {}).items():
            for i, entry in enumerate(entries):
                if "matcher" in entry:
                    assert isinstance(entry["matcher"], str), (
                        f"hooks.{hook_type}[{i}].matcher is {type(entry['matcher']).__name__}, "
                        f'must be a string (e.g. "Edit|Write")'
                    )

    def test_committed_settings_json_is_valid(self):
        """The actual .claude/settings.json checked into the repo must be valid."""
        repo_root = Path(__file__).resolve().parents[3]
        settings_file = repo_root / ".claude" / "settings.json"

        if not settings_file.exists():
            pytest.skip("No .claude/settings.json in repo")

        settings = json.loads(settings_file.read_text())
        errors = _validate_claude_hooks_format(settings)
        assert errors == [], (
            "Committed .claude/settings.json has invalid format:\n" + "\n".join(errors)
        )

    def test_does_not_overwrite_existing_hooks(self, tmp_path):
        """Existing hooks in settings.json should not be overwritten."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        existing = {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [{"type": "command", "command": "echo custom"}],
                    }
                ]
            }
        }
        (claude_dir / "settings.json").write_text(json.dumps(existing))

        _create_claude_settings_json(tmp_path)

        settings = json.loads((claude_dir / "settings.json").read_text())

        # Existing PostToolUse should be preserved (not overwritten)
        assert settings["hooks"]["PostToolUse"] == existing["hooks"]["PostToolUse"]

        # Other hooks should be added
        assert "SessionStart" in settings["hooks"]
        assert "PreToolUse" in settings["hooks"]

        # Everything should still be valid format
        errors = _validate_claude_hooks_format(settings)
        assert errors == [], "Invalid format after merge:\n" + "\n".join(errors)


def _claude_cli_available() -> bool:
    """Check if the claude CLI is installed and callable."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


class TestClaudeSettingsViaCLI:
    """Validate settings using the actual Claude Code CLI."""

    @pytest.fixture
    def project_with_settings(self, tmp_path):
        """Create a project dir with devloop-generated settings."""
        _create_claude_settings_json(tmp_path)
        return tmp_path

    @pytest.mark.skipif(
        not _claude_cli_available(),
        reason="claude CLI not installed",
    )
    def test_claude_cli_accepts_generated_settings(self, project_with_settings):
        """Claude Code CLI should not report settings errors for our config.

        Runs 'claude -p' with --max-turns 1 and checks stderr for
        'Settings Error' which Claude Code prints when hooks are invalid.
        """
        result = subprocess.run(
            ["claude", "-p", "echo test", "--max-turns", "1"],
            cwd=str(project_with_settings),
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined = result.stdout + result.stderr
        assert "Settings Error" not in combined, (
            f"Claude Code reported settings errors for generated config:\n{combined}"
        )
        assert "Expected array, but received object" not in combined, (
            f"Claude Code rejected hooks format:\n{combined}"
        )
