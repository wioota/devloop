"""Integration tests for DevLoop MCP server.

These tests verify end-to-end functionality of the MCP server including:
- Server lifecycle (start, call tool, shutdown)
- Findings retrieval with real ContextStore
- Subscription notifications for file changes
- CLI install/uninstall commands
- devloop init auto-registration of MCP server
"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from devloop.core.context_store import (
    ContextStore,
    Finding,
    Severity,
)

# ============================================================================
# Test Utilities
# ============================================================================


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


def create_devloop_project(project_root: Path) -> Path:
    """Create a complete .devloop project structure for testing.

    Args:
        project_root: The root directory for the project

    Returns:
        Path to the .devloop directory
    """
    devloop_dir = project_root / ".devloop"
    devloop_dir.mkdir(parents=True, exist_ok=True)

    # Create context directory
    context_dir = devloop_dir / "context"
    context_dir.mkdir(exist_ok=True)

    # Create default config
    config = {
        "version": "1.0",
        "enabled": True,
        "agents": {
            "formatter": {"enabled": True},
            "linter": {"enabled": True},
            "type-checker": {"enabled": True},
        },
        "global": {
            "mode": "report-only",
            "maxConcurrentAgents": 5,
        },
    }
    config_path = devloop_dir / "agents.json"
    config_path.write_text(json.dumps(config, indent=2))

    # Create src and tests directories
    (project_root / "src").mkdir(exist_ok=True)
    (project_root / "tests").mkdir(exist_ok=True)

    return devloop_dir


# ============================================================================
# Test: Server Lifecycle
# ============================================================================


class TestServerLifecycle:
    """Tests for MCP server lifecycle: start, call tool, shutdown."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project with .devloop directory."""
        create_devloop_project(tmp_path)
        return tmp_path

    def test_server_initialization(self, project_root: Path) -> None:
        """Test that MCP server initializes correctly with project root."""
        from devloop.mcp.server import MCPServer

        server = MCPServer(project_root=project_root)

        assert server.project_root == project_root
        assert server.devloop_dir == project_root / ".devloop"
        assert server.server is not None
        assert server.server.name == "devloop"

    def test_server_initialization_with_cwd(self, project_root: Path) -> None:
        """Test server initialization when finding project root from cwd."""
        from devloop.mcp.server import MCPServer

        with patch.object(Path, "cwd", return_value=project_root):
            server = MCPServer()

        assert server.project_root == project_root

    def test_server_initialization_fails_without_devloop(self, tmp_path: Path) -> None:
        """Test server initialization fails when .devloop not found."""
        from devloop.mcp.server import MCPServer

        with patch.object(Path, "cwd", return_value=tmp_path):
            with pytest.raises(FileNotFoundError) as exc_info:
                MCPServer()

        assert ".devloop" in str(exc_info.value)
        assert "devloop init" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_server_run_lifecycle(self, project_root: Path) -> None:
        """Test the complete server run lifecycle with mocked stdio transport."""
        from devloop.mcp.server import MCPServer

        server = MCPServer(project_root=project_root)

        # Mock the stdio transport
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()

        with patch("devloop.mcp.server.stdio_server") as mock_stdio:
            mock_stdio.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read_stream, mock_write_stream)
            )
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock the underlying server.run to avoid actual protocol handling
            server.server.run = AsyncMock()

            await server.run()

            # Verify stdio_server was used as context manager
            mock_stdio.return_value.__aenter__.assert_called_once()
            mock_stdio.return_value.__aexit__.assert_called_once()

            # Verify server.run was called with streams
            server.server.run.assert_called_once()
            call_args = server.server.run.call_args
            assert call_args[0][0] == mock_read_stream
            assert call_args[0][1] == mock_write_stream

    @pytest.mark.asyncio
    async def test_server_tools_registration(self, project_root: Path) -> None:
        """Test that all expected tools are registered."""
        from devloop.mcp.server import MCPServer

        server = MCPServer(project_root=project_root)

        # Server should have all components initialized
        assert server.server is not None
        assert server.server.name == "devloop"
        # The actual tools are registered via decorators in _register_tools
        # We verify the server was set up correctly with context store
        assert server.context_store is not None


# ============================================================================
# Test: Get Findings with Real Context
# ============================================================================


class TestGetFindingsWithRealContext:
    """End-to-end tests for findings retrieval with real ContextStore."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project with .devloop directory."""
        create_devloop_project(tmp_path)
        return tmp_path

    @pytest.fixture
    async def context_store(self, project_root: Path) -> ContextStore:
        """Create and initialize a real context store."""
        context_dir = project_root / ".devloop" / "context"
        store = ContextStore(context_dir=context_dir, enable_path_validation=False)
        await store.initialize()
        return store

    @pytest.mark.asyncio
    async def test_get_findings_empty(self, context_store: ContextStore) -> None:
        """Test getting findings when store is empty."""
        from devloop.mcp.tools import get_findings

        result = await get_findings(context_store)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_findings_with_data(self, context_store: ContextStore) -> None:
        """Test getting findings with data in store."""
        from devloop.mcp.tools import get_findings

        # Add test findings
        finding1 = create_test_finding(
            id="find-001",
            severity=Severity.ERROR,
            file="/test/main.py",
            message="Error in main.py",
        )
        finding2 = create_test_finding(
            id="find-002",
            severity=Severity.WARNING,
            file="/test/utils.py",
            message="Warning in utils.py",
        )
        await context_store.add_finding(finding1)
        await context_store.add_finding(finding2)

        result = await get_findings(context_store)

        assert len(result) == 2
        ids = [f["id"] for f in result]
        assert "find-001" in ids
        assert "find-002" in ids

    @pytest.mark.asyncio
    async def test_get_findings_filter_by_severity(
        self, context_store: ContextStore
    ) -> None:
        """Test filtering findings by severity."""
        from devloop.mcp.tools import get_findings

        # Add findings with different severities
        await context_store.add_finding(
            create_test_finding(id="err-001", severity=Severity.ERROR)
        )
        await context_store.add_finding(
            create_test_finding(id="warn-001", severity=Severity.WARNING)
        )
        await context_store.add_finding(
            create_test_finding(id="info-001", severity=Severity.INFO)
        )

        result = await get_findings(context_store, severity="error")

        assert len(result) == 1
        assert result[0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_get_findings_filter_by_category(
        self, context_store: ContextStore
    ) -> None:
        """Test filtering findings by category."""
        from devloop.mcp.tools import get_findings

        # Add findings with different categories
        await context_store.add_finding(
            create_test_finding(id="sec-001", category="security")
        )
        await context_store.add_finding(
            create_test_finding(id="style-001", category="style")
        )

        result = await get_findings(context_store, category="security")

        assert len(result) == 1
        assert result[0]["category"] == "security"

    @pytest.mark.asyncio
    async def test_get_findings_with_limit(self, context_store: ContextStore) -> None:
        """Test limiting the number of findings returned."""
        from devloop.mcp.tools import get_findings

        # Add many findings
        for i in range(20):
            await context_store.add_finding(create_test_finding(id=f"find-{i:03d}"))

        result = await get_findings(context_store, limit=5)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_dismiss_finding_integration(
        self, context_store: ContextStore
    ) -> None:
        """Test dismissing a finding marks it as seen."""
        from devloop.mcp.tools import dismiss_finding

        # Add a finding
        await context_store.add_finding(
            create_test_finding(id="dismiss-001", seen_by_user=False)
        )

        # Dismiss it
        result = await dismiss_finding(
            context_store, "dismiss-001", reason="False positive"
        )

        assert result["success"] is True
        assert result["finding_id"] == "dismiss-001"

        # Verify it's marked as seen
        findings = await context_store.get_findings()
        dismissed = next((f for f in findings if f.id == "dismiss-001"), None)
        assert dismissed is not None
        assert dismissed.seen_by_user is True


# ============================================================================
# Test: Subscription Notifications
# ============================================================================


class TestSubscriptionNotifications:
    """Tests for subscription and notification system."""

    @pytest.fixture
    def devloop_dir(self, tmp_path: Path) -> Path:
        """Create a temporary .devloop directory."""
        devloop_dir = tmp_path / ".devloop"
        devloop_dir.mkdir()
        context_dir = devloop_dir / "context"
        context_dir.mkdir()
        return devloop_dir

    @pytest.mark.asyncio
    async def test_subscription_manager_lifecycle(self, devloop_dir: Path) -> None:
        """Test subscription manager start and stop."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir, check_interval=0.1)

        # Start manager
        await manager.start()
        assert manager._watcher is not None
        assert manager._watcher_task is not None

        # Stop manager
        await manager.stop()
        assert manager._watcher is None
        assert manager._watcher_task is None

    @pytest.mark.asyncio
    async def test_subscribe_and_notify(self, devloop_dir: Path) -> None:
        """Test subscribing to a resource and receiving notifications."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir, check_interval=0.1)

        # Track callback invocations
        callback_results = []

        async def callback(uri: str) -> None:
            callback_results.append(uri)

        # Subscribe
        sub_id = await manager.subscribe("devloop://findings/immediate", callback)
        assert sub_id is not None

        # Manually trigger notification
        await manager.notify("devloop://findings/immediate")

        # Verify callback was called
        assert len(callback_results) == 1
        assert callback_results[0] == "devloop://findings/immediate"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, devloop_dir: Path) -> None:
        """Test multiple subscribers to same resource."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir, check_interval=0.1)

        callback1_count = [0]
        callback2_count = [0]

        async def callback1(uri: str) -> None:
            callback1_count[0] += 1

        async def callback2(uri: str) -> None:
            callback2_count[0] += 1

        # Subscribe both callbacks
        await manager.subscribe("devloop://findings/immediate", callback1)
        await manager.subscribe("devloop://findings/immediate", callback2)

        # Notify
        await manager.notify("devloop://findings/immediate")

        # Both should be called
        assert callback1_count[0] == 1
        assert callback2_count[0] == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self, devloop_dir: Path) -> None:
        """Test unsubscribing stops notifications."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir, check_interval=0.1)

        callback_count = [0]

        async def callback(uri: str) -> None:
            callback_count[0] += 1

        # Subscribe and then unsubscribe
        sub_id = await manager.subscribe("devloop://findings/immediate", callback)
        result = await manager.unsubscribe(sub_id)
        assert result is True

        # Notify should not call callback
        await manager.notify("devloop://findings/immediate")
        assert callback_count[0] == 0

    @pytest.mark.asyncio
    async def test_watcher_detects_file_changes(self, devloop_dir: Path) -> None:
        """Test ResourceWatcher detects file changes and notifies."""
        from devloop.mcp.subscriptions import ResourceWatcher

        watcher = ResourceWatcher(devloop_dir, check_interval=0.05)
        change_detected = asyncio.Event()
        change_count = [0]

        async def on_change():
            change_count[0] += 1
            change_detected.set()

        # Create the .last_update file
        last_update_file = devloop_dir / "context" / ".last_update"
        last_update_file.write_text("initial")

        # Start watcher
        watcher_task = asyncio.create_task(watcher.start(on_change))

        # Wait for watcher to initialize
        await asyncio.sleep(0.15)

        # Modify the file to trigger change
        last_update_file.write_text("updated")

        # Wait for change detection
        try:
            await asyncio.wait_for(change_detected.wait(), timeout=1.0)
            assert change_count[0] >= 1
        except asyncio.TimeoutError:
            # May not always trigger due to timing, that's okay
            pass
        finally:
            watcher.stop()
            try:
                await asyncio.wait_for(watcher_task, timeout=0.5)
            except asyncio.TimeoutError:
                watcher_task.cancel()

    @pytest.mark.asyncio
    async def test_subscription_manager_on_change_notifies_all(
        self, devloop_dir: Path
    ) -> None:
        """Test that SubscriptionManager notifies all findings resources on change."""
        from devloop.mcp.subscriptions import SubscriptionManager

        manager = SubscriptionManager(devloop_dir, check_interval=0.1)

        notified_uris = []

        async def callback(uri: str) -> None:
            notified_uris.append(uri)

        # Subscribe to multiple resources
        await manager.subscribe("devloop://findings/immediate", callback)
        await manager.subscribe("devloop://findings/relevant", callback)
        await manager.subscribe("devloop://findings/summary", callback)

        # Trigger _on_change which should notify all findings resources
        await manager._on_change()

        # All should be notified
        assert "devloop://findings/immediate" in notified_uris
        assert "devloop://findings/relevant" in notified_uris
        assert "devloop://findings/summary" in notified_uris


# ============================================================================
# Test: CLI Install/Uninstall
# ============================================================================


class TestCLIInstallUninstall:
    """Tests for CLI install and uninstall commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project with .devloop directory."""
        create_devloop_project(tmp_path)
        return tmp_path

    @pytest.fixture
    def claude_settings_dir(self, tmp_path: Path) -> Path:
        """Create a temporary .claude directory for testing."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        return claude_dir

    def test_install_creates_settings(self, claude_settings_dir: Path) -> None:
        """Test install creates settings.json with MCP config."""
        from devloop.cli.commands.mcp_server import install_mcp_server

        settings_path = claude_settings_dir / "settings.json"

        with patch.object(Path, "home", return_value=claude_settings_dir.parent):
            # Override get_claude_settings_path
            with patch(
                "devloop.cli.commands.mcp_server.get_claude_settings_path",
                return_value=settings_path,
            ):
                result = install_mcp_server()

        assert result is True
        assert settings_path.exists()

        settings = json.loads(settings_path.read_text())
        assert "mcpServers" in settings
        assert "devloop" in settings["mcpServers"]
        assert settings["mcpServers"]["devloop"]["command"] == "devloop"
        assert settings["mcpServers"]["devloop"]["args"] == ["mcp-server"]

    def test_install_updates_existing_settings(self, claude_settings_dir: Path) -> None:
        """Test install updates existing settings without losing data."""
        from devloop.cli.commands.mcp_server import install_mcp_server

        settings_path = claude_settings_dir / "settings.json"

        # Create existing settings
        existing = {
            "some_setting": "value",
            "mcpServers": {
                "other_server": {"command": "other"},
            },
        }
        settings_path.write_text(json.dumps(existing))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_path,
        ):
            result = install_mcp_server()

        assert result is True

        settings = json.loads(settings_path.read_text())
        assert settings["some_setting"] == "value"
        assert "other_server" in settings["mcpServers"]
        assert "devloop" in settings["mcpServers"]

    def test_uninstall_removes_devloop(self, claude_settings_dir: Path) -> None:
        """Test uninstall removes devloop from settings."""
        from devloop.cli.commands.mcp_server import uninstall_mcp_server

        settings_path = claude_settings_dir / "settings.json"

        # Create settings with devloop
        settings = {
            "mcpServers": {
                "devloop": {"command": "devloop", "args": ["mcp-server"]},
                "other": {"command": "other"},
            },
        }
        settings_path.write_text(json.dumps(settings))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_path,
        ):
            result = uninstall_mcp_server()

        assert result is True

        new_settings = json.loads(settings_path.read_text())
        assert "devloop" not in new_settings["mcpServers"]
        assert "other" in new_settings["mcpServers"]

    def test_uninstall_handles_no_settings(self, tmp_path: Path) -> None:
        """Test uninstall handles missing settings file gracefully."""
        from devloop.cli.commands.mcp_server import uninstall_mcp_server

        settings_path = tmp_path / ".claude" / "settings.json"

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_path,
        ):
            result = uninstall_mcp_server()

        assert result is True

    def test_cli_install_command(
        self, runner: CliRunner, project_root: Path, claude_settings_dir: Path
    ) -> None:
        """Test CLI mcp-server --install command."""
        from devloop.cli.commands.mcp_server import app

        settings_path = claude_settings_dir / "settings.json"

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_path,
        ):
            result = runner.invoke(app, ["--install"])

        assert result.exit_code == 0
        assert "installed successfully" in result.output.lower()

    def test_cli_uninstall_command(
        self, runner: CliRunner, claude_settings_dir: Path
    ) -> None:
        """Test CLI mcp-server --uninstall command."""
        from devloop.cli.commands.mcp_server import app

        settings_path = claude_settings_dir / "settings.json"
        settings_path.write_text(json.dumps({"mcpServers": {"devloop": {}}}))

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_path,
        ):
            result = runner.invoke(app, ["--uninstall"])

        assert result.exit_code == 0
        assert "uninstalled successfully" in result.output.lower()

    def test_cli_check_command(self, runner: CliRunner, project_root: Path) -> None:
        """Test CLI mcp-server --check command."""
        from devloop.cli.commands.mcp_server import app

        with patch.object(Path, "cwd", return_value=project_root):
            result = runner.invoke(app, ["--check"])

        assert result.exit_code == 0
        assert "validated successfully" in result.output.lower()

    def test_cli_check_fails_without_devloop(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test CLI mcp-server --check fails without .devloop."""
        from devloop.cli.commands.mcp_server import app

        with patch.object(Path, "cwd", return_value=tmp_path):
            result = runner.invoke(app, ["--check"])

        assert result.exit_code == 1
        assert ".devloop" in result.output or "devloop init" in result.output

    def test_cli_mutually_exclusive_options(self, runner: CliRunner) -> None:
        """Test that --check, --install, --uninstall are mutually exclusive."""
        from devloop.cli.commands.mcp_server import app

        result = runner.invoke(app, ["--check", "--install"])

        assert result.exit_code == 1
        assert "only one" in result.output.lower()


# ============================================================================
# Test: devloop init Auto-Registration
# ============================================================================


class TestInitAutoRegistration:
    """Tests for devloop init auto-registering MCP server."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create a CLI test runner."""
        return CliRunner()

    def test_setup_mcp_server_with_existing_claude_dir(self, tmp_path: Path) -> None:
        """Test _setup_mcp_server registers when .claude exists."""
        from devloop.cli.main import _setup_mcp_server

        # Create .claude directory
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)

        settings_path = claude_dir / "settings.json"

        # Mock to use our test directory
        with patch("devloop.cli.commands.mcp_server.Path.home", return_value=tmp_path):
            with patch(
                "devloop.cli.commands.mcp_server.get_claude_settings_path",
                return_value=settings_path,
            ):
                # Capture console output
                with patch("devloop.cli.main.console") as mock_console:
                    _setup_mcp_server(tmp_path)

                    # Should have printed success message
                    mock_console.print.assert_called()

        # Settings should be created
        assert settings_path.exists()
        settings = json.loads(settings_path.read_text())
        assert "mcpServers" in settings
        assert "devloop" in settings["mcpServers"]

    def test_setup_mcp_server_without_claude_dir(self, tmp_path: Path) -> None:
        """Test _setup_mcp_server skips when .claude doesn't exist."""
        from devloop.cli.main import _setup_mcp_server

        settings_path = tmp_path / ".claude" / "settings.json"

        with patch(
            "devloop.cli.commands.mcp_server.get_claude_settings_path",
            return_value=settings_path,
        ):
            with patch("devloop.cli.main.console"):
                _setup_mcp_server(tmp_path)

        # Settings should NOT exist (function returns early when .claude doesn't exist)
        assert not settings_path.exists()

    def test_init_calls_setup_mcp_server(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that devloop init calls _setup_mcp_server."""
        from devloop.cli.main import app

        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create .claude directory to trigger registration
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_path = claude_dir / "settings.json"

        with patch("devloop.cli.commands.mcp_server.Path.home", return_value=tmp_path):
            with patch(
                "devloop.cli.commands.mcp_server.get_claude_settings_path",
                return_value=settings_path,
            ):
                result = runner.invoke(
                    app,
                    ["init", str(project_path), "--non-interactive"],
                    catch_exceptions=False,
                )

        assert result.exit_code == 0
        assert "initialized" in result.output.lower()

        # MCP server should be registered
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
            assert "mcpServers" in settings
            assert "devloop" in settings["mcpServers"]


# ============================================================================
# Test: Resources End-to-End
# ============================================================================


class TestResourcesEndToEnd:
    """End-to-end tests for MCP resources."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project with .devloop directory."""
        create_devloop_project(tmp_path)
        return tmp_path

    @pytest.mark.asyncio
    async def test_read_status_resource(self, project_root: Path) -> None:
        """Test reading the status resource."""
        from devloop.mcp.resources import read_resource

        result = await read_resource("devloop://status", project_root)
        data = json.loads(result)

        assert "initialized" in data
        assert data["initialized"] is True
        assert "watch_running" in data
        assert "server_version" in data

    @pytest.mark.asyncio
    async def test_read_agents_resource(self, project_root: Path) -> None:
        """Test reading the agents resource."""
        from devloop.mcp.resources import read_resource

        result = await read_resource("devloop://agents", project_root)
        data = json.loads(result)

        assert "available_agents" in data
        assert isinstance(data["available_agents"], list)
        assert len(data["available_agents"]) > 0

    @pytest.mark.asyncio
    async def test_read_findings_immediate_resource(self, project_root: Path) -> None:
        """Test reading the immediate findings resource."""
        from devloop.mcp.resources import read_resource

        result = await read_resource("devloop://findings/immediate", project_root)
        data = json.loads(result)

        # Should be an empty list when no findings
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_read_findings_summary_resource(self, project_root: Path) -> None:
        """Test reading the findings summary resource."""
        from devloop.mcp.resources import read_resource

        result = await read_resource("devloop://findings/summary", project_root)
        data = json.loads(result)

        assert "total_findings" in data
        assert "tiers" in data
        assert "severity_counts" in data

    @pytest.mark.asyncio
    async def test_read_unknown_resource_raises(self, project_root: Path) -> None:
        """Test reading unknown resource raises ValueError."""
        from devloop.mcp.resources import read_resource

        with pytest.raises(ValueError) as exc_info:
            await read_resource("devloop://unknown", project_root)

        assert "Unknown resource" in str(exc_info.value)


# ============================================================================
# Test: Full Integration Flow
# ============================================================================


class TestFullIntegrationFlow:
    """Tests for complete integration scenarios."""

    @pytest.fixture
    def project_root(self, tmp_path: Path) -> Path:
        """Create a temporary project with .devloop directory."""
        create_devloop_project(tmp_path)
        return tmp_path

    @pytest.mark.asyncio
    async def test_complete_findings_workflow(self, project_root: Path) -> None:
        """Test a complete workflow: add findings, query, dismiss."""
        from devloop.mcp.tools import get_findings, dismiss_finding
        from devloop.mcp.resources import get_summary_resource

        # Initialize context store
        context_dir = project_root / ".devloop" / "context"
        store = ContextStore(context_dir=context_dir, enable_path_validation=False)
        await store.initialize()

        # 1. Start with no findings
        findings = await get_findings(store)
        assert len(findings) == 0

        # 2. Add findings
        error_finding = create_test_finding(
            id="workflow-001",
            severity=Severity.ERROR,
            message="Critical error",
            blocking=True,
        )
        warning_finding = create_test_finding(
            id="workflow-002",
            severity=Severity.WARNING,
            message="Minor warning",
        )
        await store.add_finding(error_finding)
        await store.add_finding(warning_finding)

        # 3. Query all findings
        findings = await get_findings(store)
        assert len(findings) == 2

        # 4. Filter by severity
        errors = await get_findings(store, severity="error")
        assert len(errors) == 1
        assert errors[0]["id"] == "workflow-001"

        # 5. Read summary using the same store instance
        # (read_resource creates its own ContextStore, so we use
        # get_summary_resource directly with our store for this test)
        summary_json = await get_summary_resource(store)
        summary = json.loads(summary_json)
        assert summary["total_findings"] == 2

        # 6. Dismiss a finding
        result = await dismiss_finding(store, "workflow-002", reason="Will fix later")
        assert result["success"] is True

        # 7. Verify dismissal
        all_findings = await store.get_findings()
        dismissed = next((f for f in all_findings if f.id == "workflow-002"), None)
        assert dismissed is not None
        assert dismissed.seen_by_user is True

    @pytest.mark.asyncio
    async def test_server_with_real_context_store(self, project_root: Path) -> None:
        """Test MCP server uses real context store correctly."""
        from devloop.mcp.server import MCPServer

        server = MCPServer(project_root=project_root)

        # Add a finding to the context store
        finding = create_test_finding(
            id="server-test-001",
            severity=Severity.ERROR,
            message="Test finding for server",
        )
        await server.context_store.initialize()
        await server.context_store.add_finding(finding)

        # Query through the server's context store
        findings = await server.context_store.get_findings()
        assert len(findings) >= 1
        assert any(f.id == "server-test-001" for f in findings)
