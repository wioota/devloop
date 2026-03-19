# Per-Project Config (devloop.yaml) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Walk up from cwd to find a `devloop.yaml` file and deep-merge its values on top of `agents.json`, so per-project overrides (e.g. `registry: {provider: npm}`) work automatically.

**Architecture:** New `src/devloop/core/project_config.py` module holds discovery + merge logic. `Config.load()` calls it after loading `agents.json`. New `devloop config show` CLI command shows resolved config with source annotations.

**Tech Stack:** Python 3.11, PyYAML (already used in `src/devloop/cli/agent_rules.py`), Typer, Rich.

---

### Task 1: `project_config.py` — discovery, YAML loading, deep merge

**Files:**
- Create: `src/devloop/core/project_config.py`
- Modify: `pyproject.toml` (add `pyyaml` to runtime deps)
- Test: `tests/unit/core/test_project_config.py` (create)

**Context:** This module does three things: walk up the directory tree to find `devloop.yaml`, load and parse it (with graceful error handling), and deep-merge overrides dict onto a base dict. Git root is the ceiling for walk-up (via `git rev-parse --show-toplevel`). If git is unavailable, use filesystem root as ceiling.

**Step 1: Write the failing tests**

Create `tests/unit/core/test_project_config.py`:

```python
"""Tests for per-project devloop.yaml discovery and merging."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from devloop.core.project_config import deep_merge, find_project_yaml, load_project_yaml


class TestFindProjectYaml:
    def test_finds_yaml_in_current_dir(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "devloop.yaml"
        yaml_file.write_text("registry:\n  provider: npm\n")
        with patch("devloop.core.project_config._git_root", return_value=tmp_path):
            result = find_project_yaml(tmp_path)
        assert result == yaml_file

    def test_finds_yaml_in_parent(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "devloop.yaml"
        yaml_file.write_text("registry:\n  provider: npm\n")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with patch("devloop.core.project_config._git_root", return_value=tmp_path):
            result = find_project_yaml(subdir)
        assert result == yaml_file

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        with patch("devloop.core.project_config._git_root", return_value=tmp_path):
            result = find_project_yaml(tmp_path)
        assert result is None

    def test_stops_at_git_root(self, tmp_path: Path) -> None:
        # yaml above git root should NOT be found
        above_root = tmp_path
        git_root = tmp_path / "project"
        git_root.mkdir()
        above_yaml = above_root / "devloop.yaml"
        above_yaml.write_text("registry:\n  provider: npm\n")
        with patch("devloop.core.project_config._git_root", return_value=git_root):
            result = find_project_yaml(git_root)
        assert result is None

    def test_prefers_closer_yaml(self, tmp_path: Path) -> None:
        parent_yaml = tmp_path / "devloop.yaml"
        parent_yaml.write_text("registry:\n  provider: pypi\n")
        subdir = tmp_path / "sub"
        subdir.mkdir()
        child_yaml = subdir / "devloop.yaml"
        child_yaml.write_text("registry:\n  provider: npm\n")
        with patch("devloop.core.project_config._git_root", return_value=tmp_path):
            result = find_project_yaml(subdir)
        assert result == child_yaml


class TestLoadProjectYaml:
    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        p = tmp_path / "devloop.yaml"
        p.write_text("registry:\n  provider: npm\n")
        result = load_project_yaml(p)
        assert result == {"registry": {"provider": "npm"}}

    def test_returns_empty_on_invalid_yaml(self, tmp_path: Path, caplog) -> None:
        p = tmp_path / "devloop.yaml"
        p.write_text(": invalid: yaml: {{{\n")
        result = load_project_yaml(p)
        assert result == {}
        assert "Invalid YAML" in caplog.text

    def test_warns_on_unknown_keys(self, tmp_path: Path, caplog) -> None:
        p = tmp_path / "devloop.yaml"
        p.write_text("unknown_key: value\n")
        result = load_project_yaml(p)
        assert result == {}
        assert "unknown" in caplog.text.lower()

    def test_returns_empty_on_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "devloop.yaml"
        p.write_text("")
        result = load_project_yaml(p)
        assert result == {}


class TestDeepMerge:
    def test_scalar_override(self) -> None:
        base = {"a": 1}
        overrides = {"a": 2}
        assert deep_merge(base, overrides) == {"a": 2}

    def test_nested_merge(self) -> None:
        base = {"providers": {"registry": {"provider": "pypi"}, "ci": {"provider": "github"}}}
        overrides = {"providers": {"registry": {"provider": "npm"}}}
        result = deep_merge(base, overrides)
        assert result["providers"]["registry"]["provider"] == "npm"
        assert result["providers"]["ci"]["provider"] == "github"

    def test_does_not_mutate_base(self) -> None:
        base = {"a": {"b": 1}}
        deep_merge(base, {"a": {"b": 2}})
        assert base["a"]["b"] == 1

    def test_adds_new_keys(self) -> None:
        base = {"a": 1}
        overrides = {"b": 2}
        assert deep_merge(base, overrides) == {"a": 1, "b": 2}
```

**Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/unit/core/test_project_config.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'devloop.core.project_config'`

**Step 3: Add `pyyaml` to pyproject.toml runtime deps**

In `pyproject.toml`, under `[tool.poetry.dependencies]`, add after `mcp = "^1.0.0"`:
```toml
pyyaml = "^6.0"
```

**Step 4: Create `src/devloop/core/project_config.py`**

```python
"""Per-project devloop.yaml discovery and configuration merging."""
from __future__ import annotations

import copy
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# Keys allowed in devloop.yaml overrides (top-level)
_ALLOWED_KEYS = {"registry", "ci", "release"}


def _git_root(start: Path) -> Optional[Path]:
    """Return git repository root, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def find_project_yaml(start_dir: Path) -> Optional[Path]:
    """Walk up from start_dir to git root, return first devloop.yaml found."""
    ceiling = _git_root(start_dir) or Path(start_dir.root)
    current = start_dir.resolve()
    ceiling = ceiling.resolve()

    while True:
        candidate = current / "devloop.yaml"
        if candidate.exists():
            return candidate
        if current == ceiling or current.parent == current:
            return None
        current = current.parent


def load_project_yaml(path: Path) -> Dict[str, Any]:
    """Load devloop.yaml, returning only recognized override keys.

    Returns empty dict on parse errors or unrecognized content (with warnings).
    """
    try:
        content = path.read_text()
        if not content.strip():
            return {}
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            logger.warning("devloop.yaml: expected a mapping, ignoring")
            return {}
    except yaml.YAMLError as e:
        logger.warning("Invalid YAML in %s: %s — ignoring", path, e)
        return {}
    except OSError as e:
        logger.warning("Could not read %s: %s — ignoring", path, e)
        return {}

    unknown = set(data.keys()) - _ALLOWED_KEYS
    if unknown:
        logger.warning(
            "devloop.yaml: unknown keys %s — ignoring file (allowed: %s)",
            sorted(unknown),
            sorted(_ALLOWED_KEYS),
        )
        return {}

    return data


def deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Return a new dict merging overrides onto base (deep for nested dicts)."""
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result
```

**Step 5: Run tests to verify they pass**

```bash
poetry run pytest tests/unit/core/test_project_config.py -v
```
Expected: all tests PASS.

**Step 6: Commit**

```bash
git add src/devloop/core/project_config.py tests/unit/core/test_project_config.py pyproject.toml
git commit -m "feat: add project_config module for devloop.yaml discovery and merging"
```

---

### Task 2: Wire devloop.yaml into `Config.load()`

**Files:**
- Modify: `src/devloop/core/config.py` (lines 107–151)
- Test: `tests/unit/core/test_config.py` (add new test class at end of file)

**Context:** After loading `agents.json`, call `find_project_yaml(Path.cwd())`. If found, load it and deep-merge the overrides into the `global.providers` section of the config dict. Store the discovered path in `self.project_yaml_path` so the `config show` command can display it. Never fail if the YAML is bad — just log and continue.

The mapping from `devloop.yaml` keys to `agents.json` paths:
- `registry` → `global.providers.registry`
- `ci` → `global.providers.ci`
- `release` → `global.release` (add this top-level key if not present)

**Step 1: Write the failing tests**

Add this class at the end of `tests/unit/core/test_config.py`:

```python
class TestConfigProjectYaml:
    def test_project_yaml_overrides_registry(self, tmp_path: Path) -> None:
        agents_json = tmp_path / ".devloop" / "agents.json"
        agents_json.parent.mkdir()
        base = Config()._get_default_config()
        agents_json.write_text(json.dumps(base))

        yaml_file = tmp_path / "devloop.yaml"
        yaml_file.write_text("registry:\n  provider: npm\n")

        from unittest.mock import patch
        from devloop.core.project_config import find_project_yaml

        with patch("devloop.core.config.find_project_yaml", return_value=yaml_file):
            cfg = Config(str(agents_json))
            result = cfg.load()

        assert result["global"]["providers"]["registry"]["provider"] == "npm"

    def test_project_yaml_path_stored(self, tmp_path: Path) -> None:
        agents_json = tmp_path / ".devloop" / "agents.json"
        agents_json.parent.mkdir()
        agents_json.write_text(json.dumps(Config()._get_default_config()))

        yaml_file = tmp_path / "devloop.yaml"
        yaml_file.write_text("ci:\n  provider: gitlab\n")

        from unittest.mock import patch
        with patch("devloop.core.config.find_project_yaml", return_value=yaml_file):
            cfg = Config(str(agents_json))
            cfg.load()

        assert cfg.project_yaml_path == yaml_file

    def test_no_project_yaml_leaves_config_unchanged(self, tmp_path: Path) -> None:
        agents_json = tmp_path / ".devloop" / "agents.json"
        agents_json.parent.mkdir()
        base = Config()._get_default_config()
        agents_json.write_text(json.dumps(base))

        from unittest.mock import patch
        with patch("devloop.core.config.find_project_yaml", return_value=None):
            cfg = Config(str(agents_json))
            result = cfg.load()

        assert result["global"]["providers"]["registry"]["provider"] == "pypi"
        assert cfg.project_yaml_path is None

    def test_invalid_project_yaml_falls_through(self, tmp_path: Path) -> None:
        agents_json = tmp_path / ".devloop" / "agents.json"
        agents_json.parent.mkdir()
        agents_json.write_text(json.dumps(Config()._get_default_config()))

        yaml_file = tmp_path / "devloop.yaml"
        yaml_file.write_text(": bad yaml {{{\n")

        from unittest.mock import patch
        with patch("devloop.core.config.find_project_yaml", return_value=yaml_file):
            cfg = Config(str(agents_json))
            result = cfg.load()  # must not raise

        assert result["global"]["providers"]["registry"]["provider"] == "pypi"
```

**Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/unit/core/test_config.py::TestConfigProjectYaml -v 2>&1 | head -20
```
Expected: `AttributeError: 'Config' object has no attribute 'project_yaml_path'`

**Step 3: Modify `Config.__init__` and `Config.load()` in `src/devloop/core/config.py`**

At top of file, add import after existing imports (line 14):
```python
from .project_config import deep_merge, find_project_yaml, load_project_yaml
```

In `Config.__init__` (line 110-112), add the new attribute:
```python
def __init__(self, config_path: str = ".devloop/agents.json"):
    self.config_path = Path(config_path)
    self._config: Optional[Dict[str, Any]] = None
    self.project_yaml_path: Optional[Path] = None
```

In `Config.load()`, after `return config` on the happy path (currently line 144), apply project yaml. Replace:
```python
                # Validate config
                if validate:
                    validate_config(config, fail_fast=True)

                return config
```
with:
```python
                # Validate config
                if validate:
                    validate_config(config, fail_fast=True)

                # Apply per-project devloop.yaml overrides
                config = self._apply_project_yaml(config)

                return config
```

Also update the default-config return path (line 130):
```python
        if not self.config_path.exists():
            # Return default config
            config = self._get_default_config()
            return self._apply_project_yaml(config)
```

Add the new method to `Config` class (after `_migrate_if_needed`, before `get_global_config`):
```python
def _apply_project_yaml(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """Find and apply devloop.yaml overrides onto config."""
    yaml_path = find_project_yaml(Path.cwd())
    self.project_yaml_path = yaml_path
    if yaml_path is None:
        return config

    overrides = load_project_yaml(yaml_path)
    if not overrides:
        return config

    # Map devloop.yaml keys to config paths
    global_providers = config.setdefault("global", {}).setdefault("providers", {})
    if "registry" in overrides:
        global_providers["registry"] = deep_merge(
            global_providers.get("registry", {}), overrides["registry"]
        )
    if "ci" in overrides:
        global_providers["ci"] = deep_merge(
            global_providers.get("ci", {}), overrides["ci"]
        )
    if "release" in overrides:
        config["release"] = deep_merge(
            config.get("release", {}), overrides["release"]
        )

    return config
```

**Step 4: Run tests**

```bash
poetry run pytest tests/unit/core/test_config.py -v
```
Expected: all tests PASS (new + existing).

**Step 5: Commit**

```bash
git add src/devloop/core/config.py tests/unit/core/test_config.py
git commit -m "feat: wire devloop.yaml overrides into Config.load()"
```

---

### Task 3: `devloop config show` CLI command

**Files:**
- Modify: `src/devloop/cli/main.py` (add new command after `status` at line 1691)
- Test: `tests/unit/cli/test_config_show.py` (create)

**Context:** Show the resolved provider settings with a `[source]` column. Source is `[devloop.yaml]` if that file contributed the value, `[agents.json]` if it came from the file, or `[default]` if using built-in defaults. Use Rich table. Command name: `config-show` (Typer converts `_` to `-`).

**Step 1: Write the failing tests**

Create `tests/unit/cli/test_config_show.py`:

```python
"""Tests for devloop config-show command."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from devloop.cli.main import app

runner = CliRunner()


class TestConfigShow:
    def test_shows_registry_provider(self, tmp_path: Path) -> None:
        mock_config = MagicMock()
        mock_config.project_yaml_path = None
        mock_config.load.return_value = {
            "global": {"providers": {"registry": {"provider": "pypi"}, "ci": {"provider": "github"}}}
        }
        mock_config.config_path = tmp_path / ".devloop" / "agents.json"

        with patch("devloop.cli.main.Config", return_value=mock_config):
            result = runner.invoke(app, ["config-show"])

        assert result.exit_code == 0
        assert "registry.provider" in result.output
        assert "pypi" in result.output

    def test_shows_yaml_source_annotation(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "devloop.yaml"
        yaml_file.write_text("registry:\n  provider: npm\n")

        mock_config = MagicMock()
        mock_config.project_yaml_path = yaml_file
        mock_config.load.return_value = {
            "global": {"providers": {"registry": {"provider": "npm"}, "ci": {"provider": "github"}}}
        }
        mock_config.config_path = tmp_path / ".devloop" / "agents.json"

        with patch("devloop.cli.main.Config", return_value=mock_config):
            result = runner.invoke(app, ["config-show"])

        assert result.exit_code == 0
        assert "devloop.yaml" in result.output
        assert "npm" in result.output

    def test_shows_default_when_no_agents_json(self, tmp_path: Path) -> None:
        mock_config = MagicMock()
        mock_config.project_yaml_path = None
        mock_config.load.return_value = {
            "global": {"providers": {"registry": {"provider": "pypi"}, "ci": {"provider": "github"}}}
        }
        mock_config.config_path = tmp_path / ".devloop" / "agents.json"  # doesn't exist

        with patch("devloop.cli.main.Config", return_value=mock_config):
            result = runner.invoke(app, ["config-show"])

        assert result.exit_code == 0
        assert "default" in result.output.lower() or "agents.json" in result.output
```

**Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/unit/cli/test_config_show.py -v 2>&1 | head -20
```
Expected: FAIL — `config-show` command does not exist yet.

**Step 3: Add `config_show` command to `src/devloop/cli/main.py`**

Insert after the `status()` function (after line 1690):

```python
@app.command()
def config_show(
    path: Path = typer.Argument(Path.cwd(), help="Project directory"),
) -> None:
    """Show resolved configuration with source annotations."""
    config_manager = Config()
    config_dict = config_manager.load()

    providers = config_dict.get("global", {}).get("providers", {})
    release = config_dict.get("release", {})

    yaml_path = config_manager.project_yaml_path
    agents_json_exists = config_manager.config_path.exists()

    def source(key: str) -> str:
        """Determine source label for a provider key."""
        if yaml_path is not None and key in ("registry", "ci", "release"):
            return f"[devloop.yaml]"
        if agents_json_exists:
            return "[agents.json]"
        return "[default]"

    table = Table(title="Resolved Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="yellow")

    registry = providers.get("registry", {})
    ci = providers.get("ci", {})

    rows = [
        ("registry.provider", registry.get("provider", "—"), source("registry")),
        ("ci.provider", ci.get("provider", "—"), source("ci")),
        ("release.branch", release.get("branch", "—"), source("release")),
        ("release.tag_prefix", release.get("tag_prefix", "—"), source("release")),
    ]

    for key, value, src in rows:
        table.add_row(key, str(value), src)

    console.print(table)
    if yaml_path:
        console.print(f"\n[dim]devloop.yaml: {yaml_path}[/dim]")
```

**Step 4: Run tests**

```bash
poetry run pytest tests/unit/cli/test_config_show.py -v
```
Expected: all PASS.

**Step 5: Run full test suite to check for regressions**

```bash
poetry run pytest tests/unit/ -x -q 2>&1 | tail -10
```
Expected: all existing tests still PASS.

**Step 6: Commit**

```bash
git add src/devloop/cli/main.py tests/unit/cli/test_config_show.py
git commit -m "feat: add devloop config-show command with source annotations"
```

---

### Task 4: Auto-detection advisory for npm projects

**Files:**
- Modify: `src/devloop/core/config.py` (`_apply_project_yaml` method)
- Test: `tests/unit/core/test_config.py` (add tests to `TestConfigProjectYaml`)

**Context:** If no `devloop.yaml` was found AND a `package.json` exists at the git root, emit a `logger.warning` advisory suggesting the user add a `devloop.yaml`. This is purely advisory — never changes config behavior. Only warn once per `Config.load()` call.

**Step 1: Write the failing test**

Add to `TestConfigProjectYaml` in `tests/unit/core/test_config.py`:

```python
    def test_advisory_warning_for_npm_project(self, tmp_path: Path, caplog) -> None:
        import logging
        agents_json = tmp_path / ".devloop" / "agents.json"
        agents_json.parent.mkdir()
        agents_json.write_text(json.dumps(Config()._get_default_config()))

        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "my-app"}')

        from unittest.mock import patch
        from devloop.core import project_config as pc

        with patch("devloop.core.config.find_project_yaml", return_value=None), \
             patch("devloop.core.project_config._git_root", return_value=tmp_path), \
             caplog.at_level(logging.WARNING, logger="devloop.core.config"):
            cfg = Config(str(agents_json))
            cfg.load()

        assert "npm" in caplog.text.lower() or "package.json" in caplog.text

    def test_no_advisory_when_yaml_present(self, tmp_path: Path, caplog) -> None:
        import logging
        agents_json = tmp_path / ".devloop" / "agents.json"
        agents_json.parent.mkdir()
        agents_json.write_text(json.dumps(Config()._get_default_config()))

        yaml_file = tmp_path / "devloop.yaml"
        yaml_file.write_text("registry:\n  provider: npm\n")
        (tmp_path / "package.json").write_text('{"name": "my-app"}')

        from unittest.mock import patch
        with patch("devloop.core.config.find_project_yaml", return_value=yaml_file), \
             caplog.at_level(logging.WARNING, logger="devloop.core.config"):
            cfg = Config(str(agents_json))
            cfg.load()

        assert "package.json" not in caplog.text
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/unit/core/test_config.py::TestConfigProjectYaml::test_advisory_warning_for_npm_project -v
```
Expected: FAIL — no warning emitted yet.

**Step 3: Add advisory detection to `_apply_project_yaml`**

In the `_apply_project_yaml` method in `src/devloop/core/config.py`, after `if yaml_path is None: return config`, add:

```python
    def _apply_project_yaml(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Find and apply devloop.yaml overrides onto config."""
        from .project_config import _git_root  # local import to avoid circular at module level

        yaml_path = find_project_yaml(Path.cwd())
        self.project_yaml_path = yaml_path
        if yaml_path is None:
            # Advisory: detect npm project without devloop.yaml
            git_root = _git_root(Path.cwd())
            if git_root and (git_root / "package.json").exists():
                logger.warning(
                    "Detected npm project (package.json found). "
                    "Consider adding a devloop.yaml with: registry:\\n  provider: npm"
                )
            return config
        # ... rest unchanged
```

**Step 4: Run tests**

```bash
poetry run pytest tests/unit/core/test_config.py -v -k "ProjectYaml"
```
Expected: all PASS.

**Step 5: Run full unit suite**

```bash
poetry run pytest tests/unit/ -x -q 2>&1 | tail -10
```
Expected: all PASS.

**Step 6: Commit and push**

```bash
git add src/devloop/core/config.py tests/unit/core/test_config.py
git commit -m "feat: advisory warning for npm projects missing devloop.yaml"
git push origin main
```

---

### Final verification

```bash
poetry run pytest tests/unit/core/test_project_config.py tests/unit/core/test_config.py tests/unit/cli/test_config_show.py -v
```
Expected: all tests PASS, no regressions.
