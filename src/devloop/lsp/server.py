"""DevLoop Language Server implementation."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from lsprotocol.types import (
    TEXT_DOCUMENT_CODE_ACTION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    CodeAction,
    CodeActionKind,
    CodeActionOptions,
    CodeActionParams,
    Command,
    Diagnostic,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    InitializeParams,
    MessageType,
    Range,
)
from pygls.server import LanguageServer

from devloop.core.auto_fix import apply_fix
from devloop.core.context_store import ContextStore
from devloop.core.event import Event, EventBus
from devloop.lsp.mapper import FindingMapper

logger = logging.getLogger(__name__)


class DevLoopLanguageServer(LanguageServer):
    """DevLoop Language Server for IDE integration."""

    def __init__(self, *args, **kwargs):
        super().__init__("devloop-lsp", "v0.1", *args, **kwargs)

        # DevLoop components
        self.context_store: Optional[ContextStore] = None
        self.event_bus: Optional[EventBus] = None

        # Diagnostic cache (uri -> diagnostics)
        self.diagnostics_cache: Dict[str, List[Diagnostic]] = {}

        # Track open documents
        self.open_documents: set[str] = set()

        # Setup handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up LSP protocol handlers."""

        @self.feature("initialize")
        async def on_initialize(params: InitializeParams):
            """Handle initialization request."""
            logger.info("DevLoop LSP server initializing...")

            # Initialize DevLoop components
            await self._initialize_devloop()

            # Subscribe to DevLoop events
            await self._subscribe_to_events()

            return {
                "capabilities": {
                    "textDocumentSync": {
                        "openClose": True,
                        "change": 1,  # Full document sync
                        "save": {"includeText": False},
                    },
                    "codeActionProvider": CodeActionOptions(
                        code_action_kinds=[
                            CodeActionKind.QuickFix,
                            CodeActionKind.SourceFixAll,
                        ],
                        resolve_provider=True,
                    ),
                }
            }

        @self.feature(TEXT_DOCUMENT_DID_OPEN)
        async def on_did_open(params: DidOpenTextDocumentParams):
            """Handle document open event."""
            uri = params.text_document.uri
            self.open_documents.add(uri)
            logger.info(f"Document opened: {uri}")

            # Send initial diagnostics for this file
            await self._publish_diagnostics_for_uri(uri)

        @self.feature(TEXT_DOCUMENT_DID_CHANGE)
        async def on_did_change(params: DidChangeTextDocumentParams):
            """Handle document change event."""
            # For now, we don't update diagnostics on every change
            # They will update when agents run on save or in background
            pass

        @self.feature(TEXT_DOCUMENT_DID_SAVE)
        async def on_did_save(params: DidSaveTextDocumentParams):
            """Handle document save event."""
            uri = params.text_document.uri
            logger.info(f"Document saved: {uri}")

            # Trigger re-scan by publishing file:modified event
            file_path = self._uri_to_path(uri)
            if file_path and self.event_bus:
                await self.event_bus.publish(
                    Event(
                        type="file:modified",
                        payload={"path": str(file_path)},
                        source="lsp-server",
                    )
                )

        @self.feature(TEXT_DOCUMENT_CODE_ACTION)
        async def on_code_action(params: CodeActionParams) -> List[CodeAction]:
            """Provide code actions for diagnostics."""
            uri = params.text_document.uri
            actions = []

            # Get diagnostics at the requested range
            diagnostics = self.diagnostics_cache.get(uri, [])

            for diagnostic in diagnostics:
                # Check if diagnostic is in the requested range
                if self._ranges_overlap(diagnostic.range, params.range):
                    # Get finding data from diagnostic
                    data = diagnostic.data
                    if not data:
                        continue

                    # Create quick fix action if auto-fixable
                    if data.get("auto_fixable"):
                        action = CodeAction(
                            title=f"Fix: {diagnostic.message[:50]}...",
                            kind=CodeActionKind.QuickFix,
                            diagnostics=[diagnostic],
                            command=Command(
                                title="Apply DevLoop fix",
                                command="devloop.applyFix",
                                arguments=[data.get("finding_id")],
                            ),
                        )
                        actions.append(action)

                    # Add dismiss action
                    dismiss_action = CodeAction(
                        title="Dismiss this finding",
                        kind=CodeActionKind.QuickFix,
                        diagnostics=[diagnostic],
                        command=Command(
                            title="Dismiss finding",
                            command="devloop.dismissFinding",
                            arguments=[data.get("finding_id")],
                        ),
                    )
                    actions.append(dismiss_action)

            return actions

        @self.command("devloop.applyFix")
        async def apply_fix_command(args: List[str]) -> None:
            """Apply a DevLoop auto-fix."""
            if not args:
                return

            finding_id = args[0]
            logger.info(f"Applying fix for finding: {finding_id}")

            try:
                # Apply the fix
                success = await apply_fix(finding_id)

                if success:
                    self.show_message("Fix applied successfully", MessageType.Info)
                    # Refresh diagnostics
                    await self._refresh_all_diagnostics()
                else:
                    self.show_message("Failed to apply fix", MessageType.Error)
            except Exception as e:
                logger.error(f"Error applying fix: {e}")
                self.show_message(f"Error: {str(e)}", MessageType.Error)

        @self.command("devloop.dismissFinding")
        async def dismiss_finding_command(args: List[str]) -> None:
            """Dismiss a finding."""
            if not args:
                return

            finding_id = args[0]
            logger.info(f"Dismissing finding: {finding_id}")

            # TODO: Implement finding dismissal in context store
            # For now, just remove from diagnostics
            self.show_message("Finding dismissed", MessageType.Info)
            await self._refresh_all_diagnostics()

    async def _initialize_devloop(self):
        """Initialize DevLoop components."""
        try:
            # Get or create context store
            self.context_store = ContextStore()

            # Get or create event bus
            self.event_bus = EventBus()

            logger.info("DevLoop components initialized")
        except Exception as e:
            logger.error(f"Failed to initialize DevLoop: {e}")
            self.show_message(
                f"Failed to initialize DevLoop: {str(e)}", MessageType.Error
            )

    async def _subscribe_to_events(self):
        """Subscribe to DevLoop events."""
        if not self.event_bus:
            return

        # Subscribe to agent completion events
        await self.event_bus.subscribe("agent:*:completed", self._on_agent_completed)

        # Subscribe to finding events
        await self.event_bus.subscribe("finding:created", self._on_finding_created)
        await self.event_bus.subscribe("finding:resolved", self._on_finding_resolved)

        logger.info("Subscribed to DevLoop events")

    async def _on_agent_completed(self, event: Event):
        """Handle agent completion event."""
        logger.info(f"Agent completed: {event.payload.get('agent_name')}")

        # Refresh diagnostics for affected files
        await self._refresh_all_diagnostics()

    async def _on_finding_created(self, event: Event):
        """Handle finding created event."""
        finding_data = event.payload.get("finding")
        if not finding_data:
            return

        # Refresh diagnostics for the file
        file_path = finding_data.get("file")
        if file_path:
            uri = self._path_to_uri(Path(file_path))
            await self._publish_diagnostics_for_uri(uri)

    async def _on_finding_resolved(self, event: Event):
        """Handle finding resolved event."""
        finding_id = event.payload.get("finding_id")
        logger.info(f"Finding resolved: {finding_id}")

        # Refresh all diagnostics
        await self._refresh_all_diagnostics()

    async def _publish_diagnostics_for_uri(self, uri: str):
        """Publish diagnostics for a specific file URI.

        Args:
            uri: File URI to publish diagnostics for
        """
        if not self.context_store:
            return

        file_path = self._uri_to_path(uri)
        if not file_path:
            return

        try:
            # Get findings for this file
            all_findings = await self.context_store.get_findings(tier="immediate")

            # Filter findings for this file
            file_findings = [f for f in all_findings if f.file == str(file_path)]

            # Convert to diagnostics
            diagnostics = FindingMapper.to_diagnostics(file_findings)

            # Cache diagnostics
            self.diagnostics_cache[uri] = diagnostics

            # Publish to client
            self.publish_diagnostics(uri, diagnostics)

            logger.info(f"Published {len(diagnostics)} diagnostics for {uri}")
        except Exception as e:
            logger.error(f"Error publishing diagnostics for {uri}: {e}")

    async def _refresh_all_diagnostics(self):
        """Refresh diagnostics for all open documents."""
        for uri in self.open_documents:
            await self._publish_diagnostics_for_uri(uri)

    def _uri_to_path(self, uri: str) -> Optional[Path]:
        """Convert file URI to Path.

        Args:
            uri: File URI (e.g., file:///path/to/file.py)

        Returns:
            Path object or None if invalid
        """
        if not uri.startswith("file://"):
            return None

        try:
            # Remove file:// prefix and decode
            path_str = uri[7:]  # Remove "file://"
            return Path(path_str)
        except Exception:
            return None

    def _path_to_uri(self, path: Path) -> str:
        """Convert Path to file URI.

        Args:
            path: File path

        Returns:
            File URI
        """
        return f"file://{path.absolute()}"

    def _ranges_overlap(self, range1: Range, range2: Range) -> bool:
        """Check if two ranges overlap.

        Args:
            range1: First range
            range2: Second range

        Returns:
            True if ranges overlap
        """
        # Check if range1 ends before range2 starts
        if range1.end.line < range2.start.line or (
            range1.end.line == range2.start.line
            and range1.end.character <= range2.start.character
        ):
            return False

        # Check if range2 ends before range1 starts
        if range2.end.line < range1.start.line or (
            range2.end.line == range1.start.line
            and range2.end.character <= range1.start.character
        ):
            return False

        return True


def main():
    """Main entry point for the LSP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    server = DevLoopLanguageServer()
    server.start_io()


if __name__ == "__main__":
    main()
