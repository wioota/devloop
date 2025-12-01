"""Tests for event collectors."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.collectors.base import BaseCollector
from devloop.collectors.filesystem import FileSystemCollector
from devloop.collectors.git import GitCollector
from devloop.collectors.manager import CollectorManager
from devloop.collectors.process import ProcessCollector, HAS_PSUTIL
from devloop.core.event import EventBus


class TestBaseCollector:
    """Test base collector functionality."""

    def test_init(self):
        """Test base collector initialization."""
        event_bus = EventBus()
        config = {"test": "value"}

        # Create a concrete subclass for testing
        class TestCollector(BaseCollector):
            async def start(self):
                pass

            async def stop(self):
                pass

        collector = TestCollector("test", event_bus, config)

        assert collector.name == "test"
        assert collector.event_bus == event_bus
        assert collector.config == config
        assert not collector.is_running

    @pytest.mark.asyncio
    async def test_emit_event(self):
        """Test event emission."""
        event_bus = EventBus()

        # Create a concrete subclass for testing
        class TestCollector(BaseCollector):
            async def start(self):
                pass

            async def stop(self):
                pass

        collector = TestCollector("test", event_bus)

        # Mock the event bus emit method
        event_bus.emit = AsyncMock()

        await collector._emit_event(
            "test:event", {"key": "value"}, "high", "test_source"
        )

        # Check that emit was called
        assert event_bus.emit.called
        event = event_bus.emit.call_args[0][0]

        assert event.type == "test:event"
        assert event.payload == {"key": "value"}
        assert event.source == "test_source"
        assert event.priority.value == 2  # HIGH priority


class TestFileSystemCollector:
    """Test filesystem collector."""

    def test_init(self):
        """Test filesystem collector initialization."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        assert collector.name == "filesystem"  # Inferred from class name
        assert collector.event_bus == event_bus
        assert collector.watch_paths == ["."]
        assert len(collector.ignore_patterns) > 0

    def test_should_ignore(self):
        """Test path ignoring logic."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        # Should ignore git files
        assert collector.should_ignore("/path/.git/config")

        # Should ignore pycache
        assert collector.should_ignore("/path/__pycache__/module.pyc")

        # Should not ignore regular files
        assert not collector.should_ignore("/path/src/main.py")

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the collector."""
        event_bus = EventBus()

        with tempfile.TemporaryDirectory() as temp_dir:
            collector = FileSystemCollector(
                event_bus, config={"watch_paths": [temp_dir]}
            )

            # Start the collector
            await collector.start()
            assert collector._running

            # Stop the collector
            await collector.stop()
            assert not collector._running


class TestGitCollector:
    """Test git collector."""

    def test_init(self):
        """Test git collector initialization."""
        event_bus = EventBus()
        collector = GitCollector(event_bus)

        assert collector.name == "git"
        assert collector.event_bus == event_bus
        assert len(collector.git_hooks) > 0
        assert "pre-commit" in collector.git_hooks

    @patch("subprocess.run")
    def test_is_git_repo(self, mock_run):
        """Test git repository detection."""
        event_bus = EventBus()
        collector = GitCollector(event_bus)

        # Mock successful git command
        mock_run.return_value.returncode = 0
        assert collector._is_git_repo()

        # Mock failed git command
        mock_run.return_value.returncode = 1
        assert not collector._is_git_repo()

    @patch("subprocess.run")
    def test_install_hook(self, mock_run):
        """Test hook installation."""

        event_bus = EventBus()
        collector = GitCollector(event_bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            hooks_dir = repo_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)

            collector.repo_path = repo_path

            # Test hook installation
            result = collector._install_hook("pre-commit")
            assert result

            hook_path = hooks_dir / "pre-commit"
            assert hook_path.exists()
            assert hook_path.stat().st_mode & 0o755  # executable

            content = hook_path.read_text()
            assert "Claude Agents Git Hook" in content

    @pytest.mark.asyncio
    async def test_emit_git_event(self):
        """Test manual git event emission."""
        event_bus = EventBus()
        collector = GitCollector(event_bus)

        event_bus.emit = AsyncMock()

        payload = {"repo": "test", "branch": "main"}
        await collector.emit_git_event("push", payload)

        assert event_bus.emit.called
        event = event_bus.emit.call_args[0][0]
        assert event.type == "git:push"
        assert event.payload == payload


class TestProcessCollector:
    """Test process collector."""

    def test_init(self):
        """Test process collector initialization."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)

        assert collector.name == "process"
        assert collector.event_bus == event_bus
        assert len(collector.monitoring_patterns) > 0

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_should_monitor_process(self):
        """Test process monitoring logic."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)

        # Mock process
        mock_process = MagicMock()
        mock_process.name.return_value = "pytest"
        mock_process.cmdline.return_value = ["pytest", "test_file.py"]

        assert collector._should_monitor_process(mock_process)

        # Test non-monitored process
        mock_process.name.return_value = "unknown_process"
        mock_process.cmdline.return_value = ["unknown", "arg"]

        assert not collector._should_monitor_process(mock_process)

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the process collector."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)

        # Start the collector
        await collector.start()
        assert collector._running

        # Stop the collector
        await collector.stop()
        assert not collector._running

    @pytest.mark.asyncio
    async def test_emit_process_event(self):
        """Test manual process event emission."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)

        event_bus.emit = AsyncMock()

        payload = {"pid": 123, "name": "test_process"}
        await collector.emit_process_event("started", payload)

        assert event_bus.emit.called
        event = event_bus.emit.call_args[0][0]
        assert event.type == "process:started"
        assert event.payload == payload


class TestCollectorManager:
    """Test collector manager."""

    def test_init(self):
        """Test collector manager initialization."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        assert manager.event_bus == event_bus
        assert len(manager._collector_classes) == 4  # filesystem, git, process, system
        assert not manager._running

    def test_register_collector_class(self):
        """Test registering a new collector class."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Register a mock collector class
        mock_class = MagicMock()
        manager.register_collector_class("mock", mock_class)

        assert "mock" in manager._collector_classes

    def test_create_collector(self):
        """Test creating a collector instance."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Create filesystem collector
        collector = manager.create_collector("filesystem", {"test": "config"})

        assert collector is not None
        assert collector.name == "filesystem"
        assert collector.config == {"test": "config"}
        assert "filesystem" in manager.collectors

    def test_create_unknown_collector(self):
        """Test creating an unknown collector type."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        collector = manager.create_collector("unknown")

        assert collector is None

    @pytest.mark.asyncio
    async def test_start_stop_collector(self):
        """Test starting and stopping individual collectors."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Create a collector
        collector = manager.create_collector("filesystem")
        assert collector is not None

        # Mock the collector's start/stop methods
        collector.start = AsyncMock()
        collector.stop = AsyncMock()

        # Start the collector
        result = await manager.start_collector("filesystem")
        assert result
        assert collector.start.called

        # Stop the collector
        result = await manager.stop_collector("filesystem")
        assert result
        assert collector.stop.called

    def test_get_status(self):
        """Test getting collector status."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Create collectors
        manager.create_collector("filesystem")
        manager.create_collector("git")

        status = manager.get_status()

        assert "filesystem" in status
        assert "git" in status
        assert status["filesystem"]["type"] == "FileSystemCollector"

    def test_list_methods(self):
        """Test listing methods."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Available collectors
        available = manager.list_available_collectors()
        assert len(available) == 4
        assert "filesystem" in available

        # Create a collector
        manager.create_collector("filesystem")

        # Active collectors
        active = manager.list_active_collectors()
        assert "filesystem" in active
