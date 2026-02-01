"""Tests for event collectors."""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.collectors.base import BaseCollector
from devloop.collectors.filesystem import FileSystemCollector
from devloop.collectors.git import GitCollector
from devloop.collectors.manager import CollectorManager
from devloop.collectors.process import HAS_PSUTIL, ProcessCollector
from devloop.collectors.system import SystemCollector
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

    def test_create_collector_exception(self):
        """Test handling exception during collector creation."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Mock a collector class that raises an exception
        mock_class = MagicMock(side_effect=ValueError("Creation failed"))
        manager._collector_classes["failing"] = mock_class

        collector = manager.create_collector("failing")
        assert collector is None

    @pytest.mark.asyncio
    async def test_start_collector_not_found(self):
        """Test starting a collector that doesn't exist."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        result = await manager.start_collector("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_start_collector_exception(self):
        """Test handling exception during collector start."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Create a collector
        collector = manager.create_collector("filesystem")
        # Mock start to raise exception
        collector.start = AsyncMock(side_effect=RuntimeError("Start failed"))

        result = await manager.start_collector("filesystem")
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_collector_not_found(self):
        """Test stopping a collector that doesn't exist."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        result = await manager.stop_collector("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_collector_exception(self):
        """Test handling exception during collector stop."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        collector = manager.create_collector("filesystem")
        collector.stop = AsyncMock(side_effect=RuntimeError("Stop failed"))

        result = await manager.stop_collector("filesystem")
        assert result is False

    @pytest.mark.asyncio
    async def test_start_all(self):
        """Test starting all collectors."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Create collectors
        fs_collector = manager.create_collector("filesystem")
        git_collector = manager.create_collector("git")

        # Mock start methods
        fs_collector.start = AsyncMock()
        git_collector.start = AsyncMock()

        await manager.start_all()

        assert manager._running
        assert fs_collector.start.called
        assert git_collector.start.called

    @pytest.mark.asyncio
    async def test_start_all_already_running(self):
        """Test start_all when already running."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)
        manager._running = True

        # Should return immediately
        await manager.start_all()
        # No collectors created, nothing should happen

    @pytest.mark.asyncio
    async def test_stop_all(self):
        """Test stopping all collectors."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Create and mock collectors
        fs_collector = manager.create_collector("filesystem")
        fs_collector.start = AsyncMock()
        fs_collector.stop = AsyncMock()
        fs_collector._running = True

        manager._running = True

        await manager.stop_all()

        assert not manager._running
        assert fs_collector.stop.called

    @pytest.mark.asyncio
    async def test_stop_all_not_running(self):
        """Test stop_all when not running."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)
        manager._running = False

        await manager.stop_all()
        # Should return immediately

    @pytest.mark.asyncio
    async def test_safe_stop_collector_exception(self):
        """Test _safe_stop_collector handles exceptions."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        # Create a mock collector that raises on stop
        mock_collector = MagicMock()
        mock_collector.name = "test"
        mock_collector.stop = AsyncMock(side_effect=RuntimeError("Stop error"))

        # Should not raise
        await manager._safe_stop_collector(mock_collector)

    def test_get_collector(self):
        """Test getting a collector by name."""
        event_bus = EventBus()
        manager = CollectorManager(event_bus)

        manager.create_collector("filesystem")

        collector = manager.get_collector("filesystem")
        assert collector is not None
        assert collector.name == "filesystem"

        # Non-existent collector
        assert manager.get_collector("nonexistent") is None


class TestSystemCollector:
    """Test system collector."""

    def test_init(self):
        """Test system collector initialization."""
        event_bus = EventBus()
        collector = SystemCollector(event_bus)

        assert collector.name == "system"
        assert collector.event_bus == event_bus
        assert collector.check_interval == 30
        assert collector.cpu_threshold == 80
        assert collector.memory_threshold == 85

    def test_init_with_config(self):
        """Test system collector with custom config."""
        event_bus = EventBus()
        config = {
            "check_interval": 60,
            "cpu_threshold": 90,
            "memory_threshold": 95,
            "idle_threshold": 600,
        }
        collector = SystemCollector(event_bus, config)

        assert collector.check_interval == 60
        assert collector.cpu_threshold == 90
        assert collector.memory_threshold == 95
        assert collector.idle_threshold == 600

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_get_system_stats(self):
        """Test getting system statistics."""
        event_bus = EventBus()
        collector = SystemCollector(event_bus)

        stats = collector._get_system_stats()

        assert "cpu_percent" in stats
        assert "memory_percent" in stats
        assert "memory_used" in stats
        assert "memory_total" in stats
        assert "disk_usage" in stats
        assert "timestamp" in stats

    def test_get_system_stats_no_psutil(self):
        """Test getting system stats when psutil not available."""
        event_bus = EventBus()
        collector = SystemCollector(event_bus)
        collector._psutil_available = False

        stats = collector._get_system_stats()
        assert stats == {}

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    @pytest.mark.asyncio
    async def test_check_high_cpu(self):
        """Test high CPU detection."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = SystemCollector(event_bus, {"cpu_threshold": 50})
        collector._psutil_available = True
        collector._last_cpu_percent = 40

        # Mock psutil to return high CPU
        with patch("devloop.collectors.system.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 90
            mock_mem = MagicMock()
            mock_mem.percent = 50
            mock_mem.used = 1000
            mock_mem.total = 2000
            mock_psutil.virtual_memory.return_value = mock_mem
            mock_disk = MagicMock()
            mock_disk.percent = 30
            mock_psutil.disk_usage.return_value = mock_disk
            mock_psutil.getloadavg.return_value = (1.0, 1.0, 1.0)

            await collector._check_system_resources()

            # Should have emitted high_cpu event
            assert event_bus.emit.called
            event = event_bus.emit.call_args[0][0]
            assert event.type == "system:high_cpu"

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    @pytest.mark.asyncio
    async def test_check_low_memory(self):
        """Test low memory detection."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = SystemCollector(event_bus, {"memory_threshold": 50})
        collector._psutil_available = True
        collector._last_memory_percent = 40

        with patch("devloop.collectors.system.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 30
            mock_mem = MagicMock()
            mock_mem.percent = 90  # High memory
            mock_mem.used = 1800
            mock_mem.total = 2000
            mock_psutil.virtual_memory.return_value = mock_mem
            mock_disk = MagicMock()
            mock_disk.percent = 30
            mock_psutil.disk_usage.return_value = mock_disk
            mock_psutil.getloadavg.return_value = (1.0, 1.0, 1.0)

            await collector._check_system_resources()

            # Should have emitted low_memory event
            assert event_bus.emit.called
            event = event_bus.emit.call_args[0][0]
            assert event.type == "system:low_memory"

    @pytest.mark.asyncio
    async def test_check_system_resources_no_psutil(self):
        """Test check_system_resources when psutil not available."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = SystemCollector(event_bus)
        collector._psutil_available = False

        await collector._check_system_resources()

        # Should not emit any events
        assert not event_bus.emit.called

    @pytest.mark.asyncio
    async def test_check_idle_detection(self):
        """Test idle system detection."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = SystemCollector(event_bus, {"idle_threshold": 1})
        collector._psutil_available = True
        collector._is_idle = False
        collector._last_idle_time = time.time() - 10  # 10 seconds ago

        with patch("devloop.collectors.system.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 2  # Low CPU (idle)
            mock_mem = MagicMock()
            mock_mem.percent = 50
            mock_mem.used = 1000
            mock_mem.total = 2000
            mock_psutil.virtual_memory.return_value = mock_mem
            mock_disk = MagicMock()
            mock_disk.percent = 30
            mock_psutil.disk_usage.return_value = mock_disk
            mock_psutil.getloadavg.return_value = (0.1, 0.1, 0.1)

            await collector._check_system_resources()

            # Should have emitted idle event
            assert event_bus.emit.called
            event = event_bus.emit.call_args[0][0]
            assert event.type == "system:idle"

    @pytest.mark.asyncio
    async def test_check_active_after_idle(self):
        """Test active detection after idle."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = SystemCollector(event_bus)
        collector._psutil_available = True
        collector._is_idle = True  # Was idle

        with patch("devloop.collectors.system.psutil") as mock_psutil:
            mock_psutil.cpu_percent.return_value = 50  # Active CPU
            mock_mem = MagicMock()
            mock_mem.percent = 50
            mock_mem.used = 1000
            mock_mem.total = 2000
            mock_psutil.virtual_memory.return_value = mock_mem
            mock_disk = MagicMock()
            mock_disk.percent = 30
            mock_psutil.disk_usage.return_value = mock_disk
            mock_psutil.getloadavg.return_value = (1.0, 1.0, 1.0)

            await collector._check_system_resources()

            # Should have emitted active event
            assert event_bus.emit.called
            event = event_bus.emit.call_args[0][0]
            assert event.type == "system:active"

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the system collector."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = SystemCollector(event_bus, {"check_interval": 1})

        # Start
        await collector.start()
        assert collector.is_running
        assert collector._monitoring_task is not None

        # Give it a moment to run
        await asyncio.sleep(0.1)

        # Stop
        await collector.stop()
        assert not collector.is_running

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test start when already running."""
        event_bus = EventBus()
        collector = SystemCollector(event_bus)
        collector._set_running(True)

        await collector.start()
        # Should return immediately, not create a new task

    @pytest.mark.asyncio
    async def test_start_no_psutil(self):
        """Test start when psutil not available."""
        event_bus = EventBus()
        collector = SystemCollector(event_bus)
        collector._psutil_available = False

        await collector.start()
        assert not collector.is_running

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stop when not running."""
        event_bus = EventBus()
        collector = SystemCollector(event_bus)

        await collector.stop()
        # Should return immediately

    @pytest.mark.asyncio
    async def test_emit_system_event(self):
        """Test manual system event emission."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = SystemCollector(event_bus)

        await collector.emit_system_event("test", {"key": "value"})

        assert event_bus.emit.called
        event = event_bus.emit.call_args[0][0]
        assert event.type == "system:test"

    @pytest.mark.asyncio
    async def test_get_system_stats_error(self):
        """Test error handling in get_system_stats."""
        event_bus = EventBus()
        collector = SystemCollector(event_bus)
        collector._psutil_available = True

        with patch("devloop.collectors.system.psutil") as mock_psutil:
            mock_psutil.cpu_percent.side_effect = RuntimeError("Error")

            stats = collector._get_system_stats()
            assert stats == {}


class TestProcessCollectorExtended:
    """Extended tests for process collector."""

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_should_monitor_by_cmdline(self):
        """Test process monitoring by command line."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)

        mock_process = MagicMock()
        mock_process.name.return_value = "some_random_name"
        mock_process.cmdline.return_value = ["python", "manage.py", "test"]

        assert collector._should_monitor_process(mock_process)

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_should_not_monitor_access_denied(self):
        """Test handling AccessDenied when checking process."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)

        with patch("devloop.collectors.process.psutil") as mock_psutil:
            mock_process = MagicMock()
            mock_process.cmdline.side_effect = mock_psutil.AccessDenied()

            result = collector._should_monitor_process(mock_process)
            assert result is False

    def test_should_monitor_no_psutil(self):
        """Test _should_monitor_process when psutil not available."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)
        collector._psutil_available = False

        result = collector._should_monitor_process(MagicMock())
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_process_completion_test(self):
        """Test categorizing test process completion."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = ProcessCollector(event_bus)

        process_data = {
            "info": {"name": "pytest", "cmdline": ["pytest", "test.py"]},
            "start_time": time.time() - 5,
        }

        await collector._handle_process_completion(123, process_data)

        assert event_bus.emit.called
        event = event_bus.emit.call_args[0][0]
        assert event.type == "test:completed"

    @pytest.mark.asyncio
    async def test_handle_process_completion_lint(self):
        """Test categorizing lint process completion."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = ProcessCollector(event_bus)

        process_data = {
            "info": {"name": "ruff", "cmdline": ["ruff", "check", "."]},
            "start_time": time.time() - 2,
        }

        await collector._handle_process_completion(123, process_data)

        assert event_bus.emit.called
        event = event_bus.emit.call_args[0][0]
        assert event.type == "lint:completed"

    @pytest.mark.asyncio
    async def test_handle_process_completion_format(self):
        """Test categorizing format process completion."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = ProcessCollector(event_bus)

        process_data = {
            "info": {"name": "black", "cmdline": ["black", "."]},
            "start_time": time.time() - 1,
        }

        await collector._handle_process_completion(123, process_data)

        assert event_bus.emit.called
        event = event_bus.emit.call_args[0][0]
        assert event.type == "format:completed"

    @pytest.mark.asyncio
    async def test_handle_process_completion_build(self):
        """Test categorizing build process completion."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = ProcessCollector(event_bus)

        process_data = {
            "info": {"name": "cargo", "cmdline": ["cargo", "build"]},
            "start_time": time.time() - 10,
        }

        await collector._handle_process_completion(123, process_data)

        assert event_bus.emit.called
        event = event_bus.emit.call_args[0][0]
        assert event.type == "build:completed"

    @pytest.mark.asyncio
    async def test_handle_process_completion_exception(self):
        """Test exception handling in process completion."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock(side_effect=RuntimeError("Emit error"))

        collector = ProcessCollector(event_bus)

        process_data = {
            "info": {"name": "test", "cmdline": []},
            "start_time": time.time(),
        }

        # Should not raise
        await collector._handle_process_completion(123, process_data)

    @pytest.mark.asyncio
    async def test_start_no_psutil(self):
        """Test start when psutil not available."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)
        collector._psutil_available = False

        await collector.start()
        assert not collector.is_running

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test start when already running."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)
        collector._set_running(True)

        await collector.start()

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stop when not running."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)

        await collector.stop()

    @pytest.mark.asyncio
    async def test_monitor_processes_no_psutil(self):
        """Test monitor loop when psutil not available."""
        event_bus = EventBus()
        collector = ProcessCollector(event_bus)
        collector._psutil_available = False

        await collector._monitor_processes()


class TestFileSystemCollectorExtended:
    """Extended tests for filesystem collector."""

    def test_should_ignore_node_modules(self):
        """Test ignoring node_modules."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        assert collector.should_ignore("/path/node_modules/package/file.js")

    def test_should_ignore_venv(self):
        """Test ignoring virtual environments."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        assert collector.should_ignore("/path/.venv/lib/python/site-packages")
        assert collector.should_ignore("/path/venv/bin/python")

    def test_on_created_directory(self):
        """Test that directory creation is ignored."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = "/path/new_dir"

        collector.on_created(mock_event)
        # No event should be emitted

    def test_on_created_ignored_path(self):
        """Test that ignored paths don't emit events."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "/path/.git/config"

        collector.on_created(mock_event)
        # No event should be emitted

    @pytest.mark.asyncio
    async def test_on_created_outside_project(self):
        """Test that paths outside project are ignored."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "/etc/passwd"

        collector.on_created(mock_event)
        # No event should be emitted

    def test_on_modified_directory(self):
        """Test that directory modification is ignored."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = "/path/dir"

        collector.on_modified(mock_event)

    def test_on_deleted_directory(self):
        """Test that directory deletion is ignored."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = "/path/dir"

        collector.on_deleted(mock_event)

    def test_on_moved_directory(self):
        """Test that directory move is ignored."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = "/path/dir"

        collector.on_moved(mock_event)

    @pytest.mark.asyncio
    async def test_emit_event_sync_no_loop(self):
        """Test emit_event_sync when no loop available."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)
        collector._loop = None

        # Should not raise
        collector._emit_event_sync("test:event", "/path/file.py")

    @pytest.mark.asyncio
    async def test_emit_event_sync_with_extra(self):
        """Test emit_event_sync with extra payload."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        collector = FileSystemCollector(event_bus)
        collector._loop = asyncio.get_running_loop()

        collector._emit_event_sync(
            "file:moved", "/path/old.py", {"dest_path": "/path/new.py"}
        )

        # Wait for coroutine to be scheduled
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_start_nonexistent_path(self):
        """Test starting with nonexistent watch path."""
        event_bus = EventBus()
        collector = FileSystemCollector(
            event_bus, config={"watch_paths": ["/nonexistent/path"]}
        )

        await collector.start()
        assert collector._running

        await collector.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test start when already running."""
        event_bus = EventBus()

        with tempfile.TemporaryDirectory() as temp_dir:
            collector = FileSystemCollector(
                event_bus, config={"watch_paths": [temp_dir]}
            )
            collector._set_running(True)

            await collector.start()
            # Should return immediately

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stop when not running."""
        event_bus = EventBus()
        collector = FileSystemCollector(event_bus)

        await collector.stop()


class TestGitCollectorExtended:
    """Extended tests for git collector."""

    def test_get_hooks_dir(self):
        """Test getting hooks directory."""
        event_bus = EventBus()
        collector = GitCollector(event_bus, config={"repo_path": "/tmp/test"})

        hooks_dir = collector._get_hooks_dir()
        assert str(hooks_dir).endswith(".git/hooks")

    @patch("subprocess.run")
    def test_is_git_repo_exception(self, mock_run):
        """Test is_git_repo when git command fails."""
        mock_run.side_effect = FileNotFoundError()

        event_bus = EventBus()
        collector = GitCollector(event_bus)

        assert not collector._is_git_repo()

    def test_install_hook_exception(self):
        """Test hook installation failure."""
        event_bus = EventBus()
        collector = GitCollector(event_bus)
        collector.repo_path = Path("/nonexistent/path")

        result = collector._install_hook("pre-commit")
        assert result is False

    def test_install_hook_backup_original(self):
        """Test hook installation with existing hook backup."""
        event_bus = EventBus()
        collector = GitCollector(event_bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            hooks_dir = repo_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)

            # Create an existing hook
            existing_hook = hooks_dir / "pre-commit"
            existing_hook.write_text("#!/bin/bash\necho original")
            existing_hook.chmod(0o755)

            collector.repo_path = repo_path

            result = collector._install_hook("pre-commit")
            assert result

            # Original should be backed up
            backup_path = hooks_dir / "pre-commit.original"
            assert backup_path.exists()

    def test_uninstall_hooks(self):
        """Test hook uninstallation."""
        event_bus = EventBus()
        collector = GitCollector(event_bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            hooks_dir = repo_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)

            collector.repo_path = repo_path

            # Install a hook first
            collector._install_hook("pre-commit")
            assert "pre-commit" in collector.installed_hooks

            # Uninstall
            collector._uninstall_hooks()
            assert len(collector.installed_hooks) == 0

    def test_uninstall_hooks_with_original(self):
        """Test uninstalling hooks with original backup."""
        event_bus = EventBus()
        collector = GitCollector(event_bus)

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            hooks_dir = repo_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)

            # Create original backup
            hook_path = hooks_dir / "pre-commit"
            original_path = hooks_dir / "pre-commit.original"
            hook_path.write_text("#!/bin/bash\n# new hook")
            original_path.write_text("#!/bin/bash\n# original")

            collector.repo_path = repo_path
            collector.installed_hooks = {"pre-commit": hook_path}

            collector._uninstall_hooks()

            # Original should be restored
            assert hook_path.exists()
            assert "original" in hook_path.read_text()

    @patch("subprocess.run")
    @pytest.mark.asyncio
    async def test_start_not_git_repo(self, mock_run):
        """Test starting in non-git directory."""
        mock_run.return_value.returncode = 1

        event_bus = EventBus()
        collector = GitCollector(event_bus)

        await collector.start()
        assert not collector.is_running

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test start when already running."""
        event_bus = EventBus()
        collector = GitCollector(event_bus)
        collector._set_running(True)

        await collector.start()

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stop when not running."""
        event_bus = EventBus()
        collector = GitCollector(event_bus)

        await collector.stop()

    @patch("subprocess.run")
    @pytest.mark.asyncio
    async def test_start_with_auto_install(self, mock_run):
        """Test starting with auto hook installation."""
        mock_run.return_value.returncode = 0

        event_bus = EventBus()

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            hooks_dir = repo_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)

            collector = GitCollector(
                event_bus,
                config={"repo_path": str(repo_path), "auto_install_hooks": True},
            )

            await collector.start()
            assert collector.is_running

            # Should have installed hooks
            assert len(collector.installed_hooks) > 0

            await collector.stop()

    @patch("subprocess.run")
    @pytest.mark.asyncio
    async def test_start_without_auto_install(self, mock_run):
        """Test starting without auto hook installation."""
        mock_run.return_value.returncode = 0

        event_bus = EventBus()

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            hooks_dir = repo_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True)

            collector = GitCollector(
                event_bus,
                config={"repo_path": str(repo_path), "auto_install_hooks": False},
            )

            await collector.start()
            assert collector.is_running

            # Should not have installed hooks
            assert len(collector.installed_hooks) == 0

            await collector.stop()


class TestBaseCollectorExtended:
    """Extended tests for base collector."""

    def test_set_running(self):
        """Test setting running state."""
        event_bus = EventBus()

        class TestCollector(BaseCollector):
            async def start(self):
                pass

            async def stop(self):
                pass

        collector = TestCollector("test", event_bus)

        assert not collector.is_running
        collector._set_running(True)
        assert collector.is_running
        collector._set_running(False)
        assert not collector.is_running

    @pytest.mark.asyncio
    async def test_emit_event_normal_priority(self):
        """Test event emission with normal priority."""
        event_bus = EventBus()
        event_bus.emit = AsyncMock()

        class TestCollector(BaseCollector):
            async def start(self):
                pass

            async def stop(self):
                pass

        collector = TestCollector("test", event_bus)

        await collector._emit_event("test:event", {"key": "value"}, "normal")

        assert event_bus.emit.called
        event = event_bus.emit.call_args[0][0]
        assert event.priority.value == 1  # NORMAL priority
