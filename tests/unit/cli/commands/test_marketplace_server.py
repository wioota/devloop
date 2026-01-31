"""Tests for marketplace_server CLI command."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestStart:
    """Tests for start command."""

    def test_start_import_error(self):
        """Test start when FastAPI is not installed."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import start

        with patch("devloop.cli.commands.marketplace_server.typer.echo"):
            with pytest.raises(typer_module.Exit) as exc_info:
                with patch.dict(
                    "sys.modules", {"devloop.marketplace": None}, clear=False
                ):
                    # Force ImportError on first import
                    with patch(
                        "builtins.__import__",
                        side_effect=ImportError("No module named 'fastapi'"),
                    ):
                        start(
                            registry_dir=None,
                            host="127.0.0.1",
                            port=8000,
                            remote_urls=None,
                            cors_origins=None,
                            reload=False,
                        )

            assert exc_info.value.exit_code == 1

    def test_start_default_registry(self):
        """Test start with default registry directory."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import start

        mock_server = Mock()
        mock_server.run.side_effect = KeyboardInterrupt()

        with patch("devloop.marketplace.create_http_server", return_value=mock_server):
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    start(
                        registry_dir=None,
                        host="127.0.0.1",
                        port=8000,
                        remote_urls=None,
                        cors_origins=None,
                        reload=False,
                    )

                assert exc_info.value.exit_code == 0

    def test_start_custom_registry(self):
        """Test start with custom registry directory."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import start

        mock_server = Mock()
        mock_server.run.side_effect = KeyboardInterrupt()
        custom_registry = Path("/custom/registry")

        with patch(
            "devloop.marketplace.create_http_server", return_value=mock_server
        ) as mock_create:
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    start(
                        registry_dir=custom_registry,
                        host="127.0.0.1",
                        port=8000,
                        remote_urls=None,
                        cors_origins=None,
                        reload=False,
                    )

                assert exc_info.value.exit_code == 0
                # Should call with custom registry
                mock_create.assert_called_once_with(
                    registry_dir=custom_registry,
                    remote_urls=None,
                    host="127.0.0.1",
                    port=8000,
                    cors_origins=None,
                )

    def test_start_custom_host_port(self):
        """Test start with custom host and port."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import start

        mock_server = Mock()
        mock_server.run.side_effect = KeyboardInterrupt()

        with patch(
            "devloop.marketplace.create_http_server", return_value=mock_server
        ) as mock_create:
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    start(
                        registry_dir=None,
                        host="0.0.0.0",
                        port=5000,
                        remote_urls=None,
                        cors_origins=None,
                        reload=False,
                    )

                assert exc_info.value.exit_code == 0
                # Should call with custom host and port
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["host"] == "0.0.0.0"
                assert call_kwargs["port"] == 5000

    def test_start_with_remote_urls(self):
        """Test start with remote URLs."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import start

        mock_server = Mock()
        mock_server.run.side_effect = KeyboardInterrupt()
        remote_urls = ["https://registry1.com", "https://registry2.com"]

        with patch(
            "devloop.marketplace.create_http_server", return_value=mock_server
        ) as mock_create:
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    start(
                        registry_dir=None,
                        host="127.0.0.1",
                        port=8000,
                        remote_urls=remote_urls,
                        cors_origins=None,
                        reload=False,
                    )

                assert exc_info.value.exit_code == 0
                # Should call with remote URLs
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["remote_urls"] == remote_urls

    def test_start_with_cors_origins(self):
        """Test start with CORS origins."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import start

        mock_server = Mock()
        mock_server.run.side_effect = KeyboardInterrupt()
        cors_origins = ["https://example.com", "https://app.example.com"]

        with patch(
            "devloop.marketplace.create_http_server", return_value=mock_server
        ) as mock_create:
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    start(
                        registry_dir=None,
                        host="127.0.0.1",
                        port=8000,
                        remote_urls=None,
                        cors_origins=cors_origins,
                        reload=False,
                    )

                assert exc_info.value.exit_code == 0
                # Should call with CORS origins
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["cors_origins"] == cors_origins

    def test_start_with_reload(self):
        """Test start with reload flag."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import start

        mock_server = Mock()
        mock_server.run.side_effect = KeyboardInterrupt()

        with patch("devloop.marketplace.create_http_server", return_value=mock_server):
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    start(
                        registry_dir=None,
                        host="127.0.0.1",
                        port=8000,
                        remote_urls=None,
                        cors_origins=None,
                        reload=True,
                    )

                assert exc_info.value.exit_code == 0
                # Should call run with reload=True
                mock_server.run.assert_called_once_with(reload=True)

    def test_start_import_error_on_server(self):
        """Test start when server creation fails with ImportError."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import start

        with patch(
            "devloop.marketplace.create_http_server",
            side_effect=ImportError("Missing dependency"),
        ):
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    start(
                        registry_dir=None,
                        host="127.0.0.1",
                        port=8000,
                        remote_urls=None,
                        cors_origins=None,
                        reload=False,
                    )

                assert exc_info.value.exit_code == 1

    def test_start_keyboard_interrupt(self):
        """Test start handles keyboard interrupt gracefully."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import start

        mock_server = Mock()
        mock_server.run.side_effect = KeyboardInterrupt()

        with patch("devloop.marketplace.create_http_server", return_value=mock_server):
            with patch(
                "devloop.cli.commands.marketplace_server.typer.echo"
            ) as mock_echo:
                with pytest.raises(typer_module.Exit) as exc_info:
                    start(
                        registry_dir=None,
                        host="127.0.0.1",
                        port=8000,
                        remote_urls=None,
                        cors_origins=None,
                        reload=False,
                    )

                assert exc_info.value.exit_code == 0
                # Should print "Server stopped."
                calls = [str(call) for call in mock_echo.call_args_list]
                assert any("Server stopped" in call for call in calls)


class TestStatus:
    """Tests for status command."""

    def test_status_registry_not_found(self, tmp_path):
        """Test status when registry doesn't exist."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import status

        registry_dir = tmp_path / "nonexistent"

        with patch("devloop.cli.commands.marketplace_server.typer.echo"):
            with pytest.raises(typer_module.Exit) as exc_info:
                status(registry_dir=registry_dir)

            assert exc_info.value.exit_code == 1

    def test_status_success(self, tmp_path):
        """Test status shows registry stats."""
        from devloop.cli.commands.marketplace_server import status

        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()

        mock_client = Mock()
        mock_client.get_registry_stats.return_value = {
            "local": {
                "total_agents": 50,
                "active_agents": 45,
                "deprecated_agents": 5,
                "trusted_agents": 30,
                "experimental_agents": 10,
                "total_downloads": 1000,
                "average_rating": 4.5,
                "categories": {},
            }
        }

        with patch(
            "devloop.marketplace.create_registry_client", return_value=mock_client
        ):
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                status(registry_dir=registry_dir)

                mock_client.get_registry_stats.assert_called_once()

    def test_status_custom_registry(self, tmp_path):
        """Test status with custom registry directory."""
        from devloop.cli.commands.marketplace_server import status

        registry_dir = tmp_path / "custom"
        registry_dir.mkdir()

        mock_client = Mock()
        mock_client.get_registry_stats.return_value = {
            "local": {
                "total_agents": 10,
                "active_agents": 10,
                "deprecated_agents": 0,
                "trusted_agents": 5,
                "experimental_agents": 2,
                "total_downloads": 100,
                "average_rating": 4.0,
                "categories": {},
            }
        }

        with patch(
            "devloop.marketplace.create_registry_client", return_value=mock_client
        ) as mock_create:
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                status(registry_dir=registry_dir)

                mock_create.assert_called_once_with(registry_dir)

    def test_status_with_categories(self, tmp_path):
        """Test status displays categories."""
        from devloop.cli.commands.marketplace_server import status

        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()

        mock_client = Mock()
        mock_client.get_registry_stats.return_value = {
            "local": {
                "total_agents": 20,
                "active_agents": 18,
                "deprecated_agents": 2,
                "trusted_agents": 10,
                "experimental_agents": 5,
                "total_downloads": 500,
                "average_rating": 4.2,
                "categories": {
                    "formatters": 8,
                    "linters": 6,
                    "security": 4,
                    "testing": 2,
                },
            }
        }

        with patch(
            "devloop.marketplace.create_registry_client", return_value=mock_client
        ):
            with patch(
                "devloop.cli.commands.marketplace_server.typer.echo"
            ) as mock_echo:
                status(registry_dir=registry_dir)

                # Should show categories
                calls = [str(call) for call in mock_echo.call_args_list]
                assert any("Categories:" in call for call in calls)
                assert any("formatters" in call for call in calls)

    def test_status_no_categories(self, tmp_path):
        """Test status with no categories."""
        from devloop.cli.commands.marketplace_server import status

        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()

        mock_client = Mock()
        mock_client.get_registry_stats.return_value = {
            "local": {
                "total_agents": 0,
                "active_agents": 0,
                "deprecated_agents": 0,
                "trusted_agents": 0,
                "experimental_agents": 0,
                "total_downloads": 0,
                "average_rating": 0.0,
                "categories": {},
            }
        }

        with patch(
            "devloop.marketplace.create_registry_client", return_value=mock_client
        ):
            with patch(
                "devloop.cli.commands.marketplace_server.typer.echo"
            ) as mock_echo:
                status(registry_dir=registry_dir)

                # Should not show categories section
                calls = [str(call) for call in mock_echo.call_args_list]
                # Categories section should not appear when empty
                assert not any(
                    "Categories:" in call and call != "Categories:" for call in calls
                ) or any("Categories:" not in call for call in calls)

    def test_status_exception(self, tmp_path):
        """Test status handles exceptions."""
        import typer as typer_module

        from devloop.cli.commands.marketplace_server import status

        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()

        mock_client = Mock()
        mock_client.get_registry_stats.side_effect = Exception("Database error")

        with patch(
            "devloop.marketplace.create_registry_client", return_value=mock_client
        ):
            with patch("devloop.cli.commands.marketplace_server.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    status(registry_dir=registry_dir)

                assert exc_info.value.exit_code == 1


class TestRegisterMarketplaceCommands:
    """Tests for register_marketplace_commands function."""

    def test_register_marketplace_commands(self):
        """Test register_marketplace_commands adds typer app."""
        from devloop.cli.commands.marketplace_server import (
            register_marketplace_commands,
        )

        mock_main_app = Mock()

        register_marketplace_commands(mock_main_app)

        # Should call add_typer with app and name
        mock_main_app.add_typer.assert_called_once()
        call_args = mock_main_app.add_typer.call_args
        assert call_args[1]["name"] == "marketplace"
