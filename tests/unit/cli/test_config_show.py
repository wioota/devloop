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
            "global": {
                "providers": {
                    "registry": {"provider": "pypi"},
                    "ci": {"provider": "github"},
                }
            }
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
            "global": {
                "providers": {
                    "registry": {"provider": "npm"},
                    "ci": {"provider": "github"},
                }
            }
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
            "global": {
                "providers": {
                    "registry": {"provider": "pypi"},
                    "ci": {"provider": "github"},
                }
            }
        }
        mock_config.config_path = tmp_path / ".devloop" / "agents.json"  # doesn't exist

        with patch("devloop.cli.main.Config", return_value=mock_config):
            result = runner.invoke(app, ["config-show"])

        assert result.exit_code == 0
        assert "default" in result.output.lower() or "agents.json" in result.output

    def test_shows_agents_json_source_when_file_exists(self, tmp_path: Path) -> None:
        agents_json = tmp_path / ".devloop" / "agents.json"
        agents_json.parent.mkdir(parents=True)
        agents_json.write_text("{}")

        mock_config = MagicMock()
        mock_config.project_yaml_path = None
        mock_config.load.return_value = {
            "global": {
                "providers": {
                    "registry": {"provider": "pypi"},
                    "ci": {"provider": "github"},
                }
            }
        }
        mock_config.config_path = agents_json

        with patch("devloop.cli.main.Config", return_value=mock_config):
            result = runner.invoke(app, ["config-show"])

        assert result.exit_code == 0
        assert "agents.json" in result.output
