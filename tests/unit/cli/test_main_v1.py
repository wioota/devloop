"""Tests for main_v1 CLI (prototype version)."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default(self):
        """Test setup_logging with default (non-verbose) level."""
        from devloop.cli.main_v1 import setup_logging

        with patch("devloop.cli.main_v1.logging.basicConfig") as mock_config:
            setup_logging(verbose=False)

            # Should configure with INFO level
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == logging.INFO

    def test_setup_logging_verbose(self):
        """Test setup_logging with verbose mode."""
        from devloop.cli.main_v1 import setup_logging

        with patch("devloop.cli.main_v1.logging.basicConfig") as mock_config:
            setup_logging(verbose=True)

            # Should configure with DEBUG level
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == logging.DEBUG


class TestEvents:
    """Tests for events command."""

    def test_events(self):
        """Test events command shows not implemented message."""
        from devloop.cli.main_v1 import events

        with patch("devloop.cli.main_v1.console") as mock_console:
            events(count=10)

            # Should print not implemented message
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("not yet implemented" in call for call in calls)


class TestInit:
    """Tests for init command."""

    def test_init_success(self, tmp_path):
        """Test init creates .devloop directory."""
        from devloop.cli.main_v1 import init

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch("devloop.cli.main_v1.console") as mock_console:
            init(path=project_dir)

            # Should create .devloop directory
            claude_dir = project_dir / ".devloop"
            assert claude_dir.exists()
            assert claude_dir.is_dir()

            # Should print success message
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Created:" in call for call in calls)

    def test_init_already_exists(self, tmp_path):
        """Test init when .devloop directory already exists."""
        from devloop.cli.main_v1 import init

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        claude_dir = project_dir / ".devloop"
        claude_dir.mkdir()

        with patch("devloop.cli.main_v1.console") as mock_console:
            init(path=project_dir)

            # Should print warning message
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("already exists" in call for call in calls)


class TestVersion:
    """Tests for version command."""

    def test_version(self):
        """Test version command shows version information."""
        from devloop.cli.main_v1 import version

        with patch("devloop.cli.main_v1.console") as mock_console:
            with patch("devloop.__version__", "1.2.3"):
                version()

                # Should print version
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("1.2.3" in call for call in calls)
                assert any("PROTOTYPE" in call for call in calls)


class TestWatch:
    """Tests for watch command."""

    def test_watch_keyboard_interrupt(self, tmp_path):
        """Test watch handles keyboard interrupt gracefully."""
        from devloop.cli.main_v1 import watch

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        with patch("devloop.cli.main_v1.setup_logging"):
            with patch("devloop.cli.main_v1.console"):
                with patch(
                    "devloop.cli.main_v1.asyncio.run",
                    side_effect=KeyboardInterrupt(),
                ):
                    # Should not raise exception
                    watch(path=watch_dir, verbose=False)

    def test_watch_verbose(self, tmp_path):
        """Test watch with verbose flag."""
        from devloop.cli.main_v1 import watch

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        with patch("devloop.cli.main_v1.setup_logging") as mock_setup:
            with patch("devloop.cli.main_v1.console"):
                with patch(
                    "devloop.cli.main_v1.asyncio.run",
                    side_effect=KeyboardInterrupt(),
                ):
                    watch(path=watch_dir, verbose=True)

                    # Should call setup_logging with verbose=True
                    mock_setup.assert_called_once_with(True)


@pytest.mark.asyncio
class TestWatchAsync:
    """Tests for watch_async function."""

    async def test_watch_async_setup(self, tmp_path):
        """Test watch_async creates and starts components."""
        from devloop.cli.main_v1 import watch_async

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        # Mock all the components
        mock_event_bus = Mock()

        mock_fs_collector = Mock()
        mock_fs_collector.start = AsyncMock()
        mock_fs_collector.stop = AsyncMock()

        mock_echo_agent = Mock()
        mock_echo_agent.start = AsyncMock()
        mock_echo_agent.stop = AsyncMock()

        mock_logger_agent = Mock()
        mock_logger_agent.start = AsyncMock()
        mock_logger_agent.stop = AsyncMock()

        with patch("devloop.cli.main_v1.EventBus", return_value=mock_event_bus):
            with patch(
                "devloop.cli.main_v1.FileSystemCollector",
                return_value=mock_fs_collector,
            ):
                with patch(
                    "devloop.cli.main_v1.EchoAgent",
                    return_value=mock_echo_agent,
                ):
                    with patch(
                        "devloop.cli.main_v1.FileLoggerAgent",
                        return_value=mock_logger_agent,
                    ):
                        with patch("devloop.cli.main_v1.console"):
                            with patch("devloop.cli.main_v1.signal"):
                                with patch(
                                    "devloop.cli.main_v1.asyncio.Event"
                                ) as MockEvent:
                                    # Make shutdown_event.wait() return immediately
                                    mock_shutdown = Mock()
                                    mock_shutdown.wait = AsyncMock()
                                    MockEvent.return_value = mock_shutdown

                                    await watch_async(watch_dir)

                                    # Should start all components
                                    mock_fs_collector.start.assert_called_once()
                                    mock_echo_agent.start.assert_called_once()
                                    mock_logger_agent.start.assert_called_once()

                                    # Should stop all components
                                    mock_echo_agent.stop.assert_called_once()
                                    mock_logger_agent.stop.assert_called_once()
                                    mock_fs_collector.stop.assert_called_once()
