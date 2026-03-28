"""Tests for per-project devloop.yaml discovery and merging."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch


from devloop.core.project_config import (
    _git_root,
    deep_merge,
    find_project_yaml,
    load_project_yaml,
)


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


class TestLoadProjectYamlEdgeCases:
    def test_returns_empty_on_non_dict_yaml(self, tmp_path: Path, caplog) -> None:
        """YAML that parses successfully but yields a list (not a dict) should warn and return {}."""
        p = tmp_path / "devloop.yaml"
        p.write_text("- item1\n- item2\n")
        result = load_project_yaml(p)
        assert result == {}
        assert "expected a mapping" in caplog.text

    def test_returns_empty_on_oserror(self, tmp_path: Path, caplog) -> None:
        """PermissionError when reading the file should warn and return {}."""
        p = tmp_path / "devloop.yaml"
        p.write_text("registry:\n  provider: npm\n")
        with patch.object(
            Path, "read_text", side_effect=PermissionError("Permission denied")
        ):
            result = load_project_yaml(p)
        assert result == {}
        assert "Could not read" in caplog.text


class TestGitRoot:
    def test_returns_path_in_git_repo(self, tmp_path: Path) -> None:
        """_git_root returns the repo root for a directory inside a git repo."""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        result = _git_root(tmp_path)
        assert result is not None
        assert result == tmp_path.resolve()

    def test_returns_none_for_non_git_directory(self, tmp_path: Path) -> None:
        """_git_root returns None when the directory is not inside a git repo."""
        non_git = tmp_path / "not_a_repo"
        non_git.mkdir()
        # Patch subprocess.run to simulate git returning non-zero exit code
        with patch("devloop.core.project_config.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 128
            result = _git_root(non_git)
        assert result is None

    def test_returns_none_when_git_not_in_path(self, tmp_path: Path) -> None:
        """_git_root returns None when git executable is not found."""
        with patch(
            "devloop.core.project_config.subprocess.run",
            side_effect=FileNotFoundError("git not found"),
        ):
            result = _git_root(tmp_path)
        assert result is None


class TestDeepMerge:
    def test_scalar_override(self) -> None:
        base = {"a": 1}
        overrides = {"a": 2}
        assert deep_merge(base, overrides) == {"a": 2}

    def test_nested_merge(self) -> None:
        base = {
            "providers": {
                "registry": {"provider": "pypi"},
                "ci": {"provider": "github"},
            }
        }
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
