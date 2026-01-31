"""Tests for DevLoop LSP server."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from lsprotocol.types import (
    MessageType,
    Position,
    Range,
)

from devloop.core.context_store import Finding, Severity
from devloop.core.event import Event
from devloop.lsp.server import DevLoopLanguageServer


def _make_finding(**kwargs):
    """Helper to create a Finding with default timestamp."""
    if "timestamp" not in kwargs:
        kwargs["timestamp"] = datetime.now().isoformat()
    return Finding(**kwargs)


class TestDevLoopLanguageServer:
    """Tests for DevLoopLanguageServer class."""

    @pytest.fixture
    def server(self):
        """Create a DevLoopLanguageServer instance."""
        return DevLoopLanguageServer()

    def test_server_initialization(self, server):
        """Test server initializes with correct attributes."""
        assert server.name == "devloop-lsp"
        assert server.version == "v0.1"
        assert server.context_store is None
        assert server.event_bus is None
        assert server.diagnostics_cache == {}
        assert server.open_documents == set()

    def test_uri_to_path_valid(self, server):
        """Test converting valid file URI to path."""
        uri = "file:///home/user/project/test.py"
        path = server._uri_to_path(uri)

        assert path is not None
        assert isinstance(path, Path)
        assert str(path) == "/home/user/project/test.py"

    def test_uri_to_path_invalid(self, server):
        """Test converting invalid URI returns None."""
        # Not a file:// URI
        uri = "https://example.com/file.py"
        path = server._uri_to_path(uri)
        assert path is None

        # Invalid format
        uri = "not-a-uri"
        path = server._uri_to_path(uri)
        assert path is None

    def test_path_to_uri(self, server):
        """Test converting path to file URI."""
        path = Path("/home/user/project/test.py")
        uri = server._path_to_uri(path)

        assert uri.startswith("file://")
        assert "/home/user/project/test.py" in uri

    def test_ranges_overlap_true(self, server):
        """Test range overlap detection - overlapping ranges."""
        range1 = Range(
            start=Position(line=5, character=0), end=Position(line=10, character=0)
        )
        range2 = Range(
            start=Position(line=7, character=0), end=Position(line=12, character=0)
        )

        assert server._ranges_overlap(range1, range2) is True
        assert server._ranges_overlap(range2, range1) is True

    def test_ranges_overlap_false(self, server):
        """Test range overlap detection - non-overlapping ranges."""
        range1 = Range(
            start=Position(line=5, character=0), end=Position(line=10, character=0)
        )
        range2 = Range(
            start=Position(line=15, character=0), end=Position(line=20, character=0)
        )

        assert server._ranges_overlap(range1, range2) is False
        assert server._ranges_overlap(range2, range1) is False

    def test_ranges_overlap_adjacent(self, server):
        """Test range overlap detection - adjacent ranges."""
        range1 = Range(
            start=Position(line=5, character=0), end=Position(line=10, character=0)
        )
        range2 = Range(
            start=Position(line=10, character=0), end=Position(line=15, character=0)
        )

        # Adjacent ranges should not overlap
        assert server._ranges_overlap(range1, range2) is False

    def test_ranges_overlap_same_line(self, server):
        """Test range overlap on same line."""
        range1 = Range(
            start=Position(line=5, character=0), end=Position(line=5, character=10)
        )
        range2 = Range(
            start=Position(line=5, character=5), end=Position(line=5, character=15)
        )

        assert server._ranges_overlap(range1, range2) is True

    @pytest.mark.asyncio
    async def test_initialize_devloop(self, server):
        """Test DevLoop component initialization."""
        with patch("devloop.lsp.server.ContextStore") as MockContextStore, patch(
            "devloop.lsp.server.EventBus"
        ) as MockEventBus:
            mock_context_store = MockContextStore.return_value
            mock_event_bus = MockEventBus.return_value

            await server._initialize_devloop()

            assert server.context_store == mock_context_store
            assert server.event_bus == mock_event_bus
            MockContextStore.assert_called_once()
            MockEventBus.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_devloop_error_handling(self, server):
        """Test DevLoop initialization handles errors gracefully."""
        with patch("devloop.lsp.server.ContextStore") as MockContextStore:
            MockContextStore.side_effect = Exception("Init failed")
            server.show_message = Mock()

            await server._initialize_devloop()

            # Should handle error and show message
            server.show_message.assert_called_once()
            args = server.show_message.call_args[0]
            assert "Failed to initialize DevLoop" in args[0]
            assert args[1] == MessageType.Error

    @pytest.mark.asyncio
    async def test_subscribe_to_events(self, server):
        """Test event subscription."""
        mock_event_bus = AsyncMock()
        server.event_bus = mock_event_bus

        await server._subscribe_to_events()

        # Should subscribe to 3 event types
        assert mock_event_bus.subscribe.call_count == 3
        calls = mock_event_bus.subscribe.call_args_list

        # Check event patterns
        patterns = [call[0][0] for call in calls]
        assert "agent:*:completed" in patterns
        assert "finding:created" in patterns
        assert "finding:resolved" in patterns

    @pytest.mark.asyncio
    async def test_subscribe_to_events_no_event_bus(self, server):
        """Test event subscription when event bus is None."""
        server.event_bus = None

        # Should not raise error
        await server._subscribe_to_events()

    @pytest.mark.asyncio
    async def test_on_agent_completed(self, server):
        """Test agent completion event handler."""
        server._refresh_all_diagnostics = AsyncMock()

        event = Event(
            type="agent:linter:completed",
            payload={"agent_name": "linter"},
            source="test",
        )

        await server._on_agent_completed(event)

        server._refresh_all_diagnostics.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_finding_created(self, server):
        """Test finding created event handler."""
        server._publish_diagnostics_for_uri = AsyncMock()

        event = Event(
            type="finding:created",
            payload={"finding": {"file": "/test/file.py", "message": "Issue"}},
            source="test",
        )

        await server._on_finding_created(event)

        server._publish_diagnostics_for_uri.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_finding_created_no_file(self, server):
        """Test finding created event without file path."""
        server._publish_diagnostics_for_uri = AsyncMock()

        event = Event(
            type="finding:created",
            payload={"finding": {"message": "Issue"}},  # No file
            source="test",
        )

        await server._on_finding_created(event)

        # Should not publish diagnostics
        server._publish_diagnostics_for_uri.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_finding_resolved(self, server):
        """Test finding resolved event handler."""
        server._refresh_all_diagnostics = AsyncMock()

        event = Event(
            type="finding:resolved",
            payload={"finding_id": "test-123"},
            source="test",
        )

        await server._on_finding_resolved(event)

        server._refresh_all_diagnostics.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_diagnostics_for_uri(self, server):
        """Test publishing diagnostics for a file URI."""
        # Setup mocks
        mock_context_store = AsyncMock()
        mock_finding = _make_finding(
            id="test-1",
            agent="linter",
            category="style",
            severity=Severity.WARNING,
            message="Test issue",
            file="/home/user/project/test.py",
            line=10,
        )
        mock_context_store.get_findings.return_value = [mock_finding]
        server.context_store = mock_context_store
        server.publish_diagnostics = Mock()

        uri = "file:///home/user/project/test.py"

        await server._publish_diagnostics_for_uri(uri)

        # Should get findings and publish diagnostics
        mock_context_store.get_findings.assert_called_once()
        server.publish_diagnostics.assert_called_once()

        # Check diagnostics cache
        assert uri in server.diagnostics_cache
        assert len(server.diagnostics_cache[uri]) == 1

    @pytest.mark.asyncio
    async def test_publish_diagnostics_filters_by_file(self, server):
        """Test diagnostics are filtered to only include matching file."""
        mock_context_store = AsyncMock()
        findings = [
            _make_finding(
                id="f1",
                agent="linter",
                category="style",
                severity=Severity.WARNING,
                message="Issue 1",
                file="/home/user/project/test.py",
                line=10,
            ),
            _make_finding(
                id="f2",
                agent="linter",
                category="style",
                severity=Severity.WARNING,
                message="Issue 2",
                file="/home/user/project/other.py",  # Different file
                line=5,
            ),
        ]
        mock_context_store.get_findings.return_value = findings
        server.context_store = mock_context_store
        server.publish_diagnostics = Mock()

        uri = "file:///home/user/project/test.py"

        await server._publish_diagnostics_for_uri(uri)

        # Should only publish diagnostics for test.py
        assert len(server.diagnostics_cache[uri]) == 1
        assert server.diagnostics_cache[uri][0].message == "Issue 1"

    @pytest.mark.asyncio
    async def test_publish_diagnostics_no_context_store(self, server):
        """Test publishing diagnostics when context store is None."""
        server.context_store = None
        server.publish_diagnostics = Mock()

        uri = "file:///home/user/project/test.py"

        await server._publish_diagnostics_for_uri(uri)

        # Should not publish anything
        server.publish_diagnostics.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_diagnostics_error_handling(self, server):
        """Test error handling in publish diagnostics."""
        mock_context_store = AsyncMock()
        mock_context_store.get_findings.side_effect = Exception("Database error")
        server.context_store = mock_context_store
        server.publish_diagnostics = Mock()

        uri = "file:///home/user/project/test.py"

        # Should not raise exception
        await server._publish_diagnostics_for_uri(uri)

        # Should not publish diagnostics
        server.publish_diagnostics.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_all_diagnostics(self, server):
        """Test refreshing diagnostics for all open documents."""
        server.open_documents = {
            "file:///test1.py",
            "file:///test2.py",
            "file:///test3.py",
        }
        server._publish_diagnostics_for_uri = AsyncMock()

        await server._refresh_all_diagnostics()

        # Should publish for all open documents
        assert server._publish_diagnostics_for_uri.call_count == 3

    @pytest.mark.asyncio
    async def test_refresh_all_diagnostics_empty(self, server):
        """Test refreshing with no open documents."""
        server.open_documents = set()
        server._publish_diagnostics_for_uri = AsyncMock()

        await server._refresh_all_diagnostics()

        # Should not publish anything
        server._publish_diagnostics_for_uri.assert_not_called()


# TODO: Add handler and command tests
# These tests need more work to properly test the internal LSP handler registration
# For now, the helper method tests provide good coverage of the core functionality
