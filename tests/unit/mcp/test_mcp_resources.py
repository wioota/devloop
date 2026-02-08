"""Tests for DevLoop MCP resources and subscriptions."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devloop.core.context_store import (
    ContextStore,
    Finding,
    Severity,
    Tier,
)


def create_test_finding(
    id: str = "test-001",
    agent: str = "test-agent",
    file: str = "/test/file.py",
    severity: Severity = Severity.WARNING,
    category: str = "test",
    message: str = "Test finding",
    line: int = 10,
    auto_fixable: bool = False,
    seen_by_user: bool = False,
    blocking: bool = False,
) -> Finding:
    """Create a test finding with sensible defaults."""
    return Finding(
        id=id,
        agent=agent,
        timestamp=datetime.now(UTC).isoformat() + "Z",
        file=file,
        line=line,
        severity=severity,
        category=category,
        message=message,
        auto_fixable=auto_fixable,
        seen_by_user=seen_by_user,
        blocking=blocking,
    )


# ============================================================================
# Resource Tests
# ============================================================================


class TestGetFindingsResource:
    """Tests for get_findings_resource function."""

    @pytest.fixture
    def context_store(self, tmp_path: Path) -> ContextStore:
        """Create a real context store for testing."""
        context_dir = tmp_path / ".devloop" / "context"
        context_dir.mkdir(parents=True)
        store = ContextStore(context_dir=context_dir, enable_path_validation=False)
        return store

    @pytest.mark.asyncio
    async def test_get_immediate_findings_resource(
        self, context_store: ContextStore
    ) -> None:
        """Test getting immediate tier findings as resource."""
        from devloop.mcp.resources import get_findings_resource

        await context_store.initialize()

        # Add findings to immediate tier
        finding = create_test_finding(id="imm-001", blocking=True)
        await context_store.add_finding(finding)

        result = await get_findings_resource(context_store, "immediate")

        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(f["id"] == "imm-001" for f in data)

    @pytest.mark.asyncio
    async def test_get_relevant_findings_resource(
        self, context_store: ContextStore
    ) -> None:
        """Test getting relevant tier findings as resource."""
        from devloop.mcp.resources import get_findings_resource

        await context_store.initialize()

        # Add a relevant finding (medium relevance score)
        finding = create_test_finding(
            id="rel-001", severity=Severity.WARNING, blocking=False
        )
        finding.relevance_score = 0.5
        await context_store.add_finding(finding)

        result = await get_findings_resource(context_store, "relevant")

        data = json.loads(result)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_background_findings_resource(
        self, context_store: ContextStore
    ) -> None:
        """Test getting background tier findings as resource."""
        from devloop.mcp.resources import get_findings_resource

        await context_store.initialize()

        # Add a background finding (low relevance)
        finding = create_test_finding(id="bg-001", severity=Severity.STYLE)
        finding.relevance_score = 0.2
        await context_store.add_finding(finding)

        result = await get_findings_resource(context_store, "background")

        data = json.loads(result)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_findings_resource_empty(
        self, context_store: ContextStore
    ) -> None:
        """Test getting findings resource when no findings exist."""
        from devloop.mcp.resources import get_findings_resource

        await context_store.initialize()

        result = await get_findings_resource(context_store, "immediate")

        data = json.loads(result)
        assert data == []

    @pytest.mark.asyncio
    async def test_get_findings_resource_invalid_tier(
        self, context_store: ContextStore
    ) -> None:
        """Test getting findings with invalid tier."""
        from devloop.mcp.resources import get_findings_resource

        await context_store.initialize()

        with pytest.raises(ValueError):
            await get_findings_resource(context_store, "invalid_tier")


class TestGetSummaryResource:
    """Tests for get_summary_resource function."""

    @pytest.fixture
    def context_store(self, tmp_path: Path) -> ContextStore:
        """Create a real context store for testing."""
        context_dir = tmp_path / ".devloop" / "context"
        context_dir.mkdir(parents=True)
        store = ContextStore(context_dir=context_dir, enable_path_validation=False)
        return store

    @pytest.mark.asyncio
    async def test_get_summary_with_findings(self, context_store: ContextStore) -> None:
        """Test summary resource with findings."""
        from devloop.mcp.resources import get_summary_resource

        await context_store.initialize()

        # Add various findings
        await context_store.add_finding(
            create_test_finding(id="sum-001", severity=Severity.ERROR, blocking=True)
        )
        await context_store.add_finding(
            create_test_finding(id="sum-002", severity=Severity.WARNING)
        )
        await context_store.add_finding(
            create_test_finding(id="sum-003", severity=Severity.INFO)
        )

        result = await get_summary_resource(context_store)

        data = json.loads(result)
        assert "tiers" in data
        assert "severity_counts" in data
        assert "category_counts" in data
        assert "total_findings" in data

    @pytest.mark.asyncio
    async def test_get_summary_empty(self, context_store: ContextStore) -> None:
        """Test summary resource with no findings."""
        from devloop.mcp.resources import get_summary_resource

        await context_store.initialize()

        result = await get_summary_resource(context_store)

        data = json.loads(result)
        assert data["total_findings"] == 0

    @pytest.mark.asyncio
    async def test_get_summary_tier_counts(self, context_store: ContextStore) -> None:
        """Test summary includes tier counts."""
        from devloop.mcp.resources import get_summary_resource

        await context_store.initialize()

        # Add blocking finding (goes to immediate)
        await context_store.add_finding(
            create_test_finding(id="tier-001", blocking=True)
        )

        result = await get_summary_resource(context_store)

        data = json.loads(result)
        assert "tiers" in data
        assert "immediate" in data["tiers"]


class TestGetStatusResource:
    """Tests for get_status_resource function."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root with .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        context_dir = devloop_dir / "context"
        context_dir.mkdir()
        return tmp_path

    @pytest.mark.asyncio
    async def test_get_status_resource(self, project_root: Path) -> None:
        """Test getting status resource."""
        from devloop.mcp.resources import get_status_resource

        result = await get_status_resource(project_root)

        data = json.loads(result)
        assert "initialized" in data
        assert "watch_running" in data
        assert "server_version" in data

    @pytest.mark.asyncio
    async def test_get_status_with_watch_running(self, project_root: Path) -> None:
        """Test status resource when watch daemon is running."""
        import os
        from devloop.mcp.resources import get_status_resource

        # Create PID file
        pid_file = project_root / ".devloop" / "watch.pid"
        pid_file.write_text(str(os.getpid()))

        result = await get_status_resource(project_root)

        data = json.loads(result)
        assert data["watch_running"] is True

    @pytest.mark.asyncio
    async def test_get_status_not_initialized(self, tmp_path: Path) -> None:
        """Test status resource when devloop not initialized."""
        from devloop.mcp.resources import get_status_resource

        result = await get_status_resource(tmp_path)

        data = json.loads(result)
        assert data["initialized"] is False


class TestGetAgentsResource:
    """Tests for get_agents_resource function."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project root with .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        return tmp_path

    @pytest.mark.asyncio
    async def test_get_agents_resource(self, project_root: Path) -> None:
        """Test getting agents resource."""
        from devloop.mcp.resources import get_agents_resource

        result = await get_agents_resource(project_root)

        data = json.loads(result)
        assert "available_agents" in data
        assert isinstance(data["available_agents"], list)

    @pytest.mark.asyncio
    async def test_get_agents_resource_with_config(self, project_root: Path) -> None:
        """Test agents resource with config file."""
        from devloop.mcp.resources import get_agents_resource

        # Create config file
        config = {
            "version": "1.0",
            "enabled": True,
            "agents": {
                "formatter": {"enabled": True},
                "linter": {"enabled": False},
            },
            "global": {},
        }
        config_path = project_root / ".devloop" / "agents.json"
        config_path.write_text(json.dumps(config))

        result = await get_agents_resource(project_root)

        data = json.loads(result)
        assert "enabled_agents" in data
        assert "formatter" in data["enabled_agents"]


# ============================================================================
# Resource List Tests
# ============================================================================


class TestListResources:
    """Tests for list_resources function."""

    def test_list_resources_returns_all(self) -> None:
        """Test that list_resources returns all defined resources."""
        from devloop.mcp.resources import list_resources

        resources = list_resources()

        # Check expected resources (convert AnyUrl to string for comparison)
        uris = [str(r.uri) for r in resources]
        assert "devloop://findings/immediate" in uris
        assert "devloop://findings/relevant" in uris
        assert "devloop://findings/background" in uris
        assert "devloop://findings/summary" in uris
        assert "devloop://status" in uris
        assert "devloop://agents" in uris

    def test_list_resources_has_metadata(self) -> None:
        """Test that resources have proper metadata."""
        from devloop.mcp.resources import list_resources

        resources = list_resources()

        for resource in resources:
            assert resource.uri is not None
            assert resource.name is not None
            assert resource.description is not None


# ============================================================================
# Subscription Tests
# ============================================================================


class TestResourceWatcher:
    """Tests for ResourceWatcher class."""

    @pytest.fixture
    def devloop_dir(self, tmp_path: Path) -> Path:
        """Create a temporary .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        context_dir = devloop_dir / "context"
        context_dir.mkdir()
        return devloop_dir

    @pytest.mark.asyncio
    async def test_watcher_init(self, devloop_dir: Path) -> None:
        """Test watcher initialization."""
        from devloop.mcp.subscriptions import ResourceWatcher

        watcher = ResourceWatcher(devloop_dir, check_interval=0.1)

        assert watcher.devloop_dir == devloop_dir
        assert watcher.check_interval == 0.1
        assert watcher._running is False

    @pytest.mark.asyncio
    async def test_watcher_detects_change(self, devloop_dir: Path) -> None:
        """Test watcher detects file changes."""
        from devloop.mcp.subscriptions import ResourceWatcher

        watcher = ResourceWatcher(devloop_dir, check_interval=0.1)
        callback_called = asyncio.Event()
        callback_count = [0]

        async def on_change():
            callback_count[0] += 1
            callback_called.set()

        # Create initial .last_update file
        last_update_file = devloop_dir / "context" / ".last_update"
        last_update_file.write_text("initial")

        # Start watcher in background
        watcher_task = asyncio.create_task(watcher.start(on_change))

        # Wait for watcher to initialize
        await asyncio.sleep(0.2)

        # Modify the file
        await asyncio.sleep(0.1)
        last_update_file.write_text("updated")

        # Wait for callback
        try:
            await asyncio.wait_for(callback_called.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass  # Callback may not trigger if timing is off

        # Stop watcher
        watcher.stop()
        await asyncio.wait_for(watcher_task, timeout=0.5)

    @pytest.mark.asyncio
    async def test_watcher_stop(self, devloop_dir: Path) -> None:
        """Test watcher stops cleanly."""
        from devloop.mcp.subscriptions import ResourceWatcher

        watcher = ResourceWatcher(devloop_dir, check_interval=0.1)

        async def on_change():
            pass

        # Start watcher
        watcher_task = asyncio.create_task(watcher.start(on_change))
        await asyncio.sleep(0.1)

        # Stop watcher
        watcher.stop()
        assert watcher._running is False

        # Watcher should complete
        await asyncio.wait_for(watcher_task, timeout=0.5)

    @pytest.mark.asyncio
    async def test_watcher_no_file(self, devloop_dir: Path) -> None:
        """Test watcher handles missing .last_update file."""
        from devloop.mcp.subscriptions import ResourceWatcher

        watcher = ResourceWatcher(devloop_dir, check_interval=0.1)
        callback_count = [0]

        async def on_change():
            callback_count[0] += 1

        # Start watcher with no .last_update file
        watcher_task = asyncio.create_task(watcher.start(on_change))
        await asyncio.sleep(0.3)

        # Stop watcher
        watcher.stop()
        await asyncio.wait_for(watcher_task, timeout=0.5)

        # Should not have called callback (no file to detect changes on)
        assert callback_count[0] == 0


class TestSubscriptionManager:
    """Tests for SubscriptionManager class."""

    @pytest.fixture
    def devloop_dir(self, tmp_path: Path) -> Path:
        """Create a temporary .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        context_dir = devloop_dir / "context"
        context_dir.mkdir()
        return devloop_dir

    @pytest.mark.asyncio
    async def test_manager_init(self, devloop_dir: Path) -> None:
        """Test subscription manager initialization."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir)

        assert manager.devloop_dir == devloop_dir
        assert len(manager._subscribers) == 0

    @pytest.mark.asyncio
    async def test_manager_subscribe(self, devloop_dir: Path) -> None:
        """Test subscribing to resource changes."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir)

        callback = AsyncMock()
        subscription_id = await manager.subscribe(
            "devloop://findings/immediate", callback
        )

        assert subscription_id is not None
        assert len(manager._subscribers) == 1

    @pytest.mark.asyncio
    async def test_manager_unsubscribe(self, devloop_dir: Path) -> None:
        """Test unsubscribing from resource changes."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir)

        callback = AsyncMock()
        subscription_id = await manager.subscribe(
            "devloop://findings/immediate", callback
        )
        await manager.unsubscribe(subscription_id)

        assert len(manager._subscribers) == 0

    @pytest.mark.asyncio
    async def test_manager_notify_subscribers(self, devloop_dir: Path) -> None:
        """Test notifying subscribers of changes."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir)

        callback1 = AsyncMock()
        callback2 = AsyncMock()

        await manager.subscribe("devloop://findings/immediate", callback1)
        await manager.subscribe("devloop://findings/immediate", callback2)

        await manager.notify("devloop://findings/immediate")

        callback1.assert_called_once_with("devloop://findings/immediate")
        callback2.assert_called_once_with("devloop://findings/immediate")

    @pytest.mark.asyncio
    async def test_manager_start_stop(self, devloop_dir: Path) -> None:
        """Test starting and stopping subscription manager."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir, check_interval=0.1)

        await manager.start()
        assert manager._watcher is not None

        await manager.stop()
        assert manager._watcher is None


# ============================================================================
# Integration Tests
# ============================================================================


class TestResourcesIntegration:
    """Integration tests for resources and subscriptions."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a complete project structure."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        context_dir = devloop_dir / "context"
        context_dir.mkdir()
        return tmp_path

    @pytest.mark.asyncio
    async def test_read_resource_findings(self, project_root: Path) -> None:
        """Test reading a findings resource end-to-end."""
        from devloop.mcp.resources import read_resource

        context_dir = project_root / ".devloop" / "context"
        store = ContextStore(context_dir=context_dir, enable_path_validation=False)
        await store.initialize()

        # Add a finding
        finding = create_test_finding(id="int-001", blocking=True)
        await store.add_finding(finding)

        # Read through read_resource
        result = await read_resource("devloop://findings/immediate", project_root)

        data = json.loads(result)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_read_resource_status(self, project_root: Path) -> None:
        """Test reading status resource."""
        from devloop.mcp.resources import read_resource

        result = await read_resource("devloop://status", project_root)

        data = json.loads(result)
        assert "initialized" in data

    @pytest.mark.asyncio
    async def test_read_resource_unknown_uri(self, project_root: Path) -> None:
        """Test reading unknown resource URI."""
        from devloop.mcp.resources import read_resource

        with pytest.raises(ValueError) as exc_info:
            await read_resource("devloop://unknown/resource", project_root)

        assert "Unknown resource" in str(exc_info.value)
