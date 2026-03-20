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
