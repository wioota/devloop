"""Tests for summary CLI command."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import typer

from devloop.cli.commands.summary import agent_summary


class TestAgentSummary:
    """Tests for agent_summary command."""

    @pytest.fixture
    def mock_context_store(self):
        """Create mock context store."""
        mock_store = Mock()
        mock_store.base_path = "/fake/path/.devloop/context"
        return mock_store

    @pytest.fixture
    def mock_generator(self):
        """Create mock summary generator."""
        mock_gen = Mock()
        mock_gen.generate_summary = AsyncMock(
            return_value={
                "scope": "recent",
                "findings": [],
                "summary": "No findings",
            }
        )
        return mock_gen

    def test_agent_summary_default_scope(self, mock_context_store, mock_generator):
        """Test agent_summary with default scope (recent)."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryFormatter"
                ) as MockFormatter:
                    MockFormatter.format_markdown.return_value = (
                        "# Summary\nNo findings"
                    )
                    with patch("devloop.cli.commands.summary.console"):
                        with patch(
                            "devloop.cli.commands.summary.asyncio.run"
                        ) as mock_run:
                            mock_run.return_value = {
                                "scope": "recent",
                                "findings": [],
                            }

                            agent_summary(scope="recent")

                            mock_run.assert_called_once()
                            MockFormatter.format_markdown.assert_called_once()

    def test_agent_summary_with_agent_filter(self, mock_context_store, mock_generator):
        """Test agent_summary with agent filter."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryFormatter"
                ) as MockFormatter:
                    MockFormatter.format_markdown.return_value = "# Summary"
                    with patch("devloop.cli.commands.summary.console"):
                        with patch(
                            "devloop.cli.commands.summary.asyncio.run"
                        ) as mock_run:
                            mock_run.return_value = {"scope": "recent"}

                            agent_summary(scope="recent", agent="linter")

                            # Check that filters were passed
                            _call_args = mock_run.call_args[0][0]
                            # The coroutine is passed, we can't easily check its args
                            mock_run.assert_called_once()

    def test_agent_summary_with_severity_filter(
        self, mock_context_store, mock_generator
    ):
        """Test agent_summary with severity filter."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryFormatter"
                ) as MockFormatter:
                    MockFormatter.format_markdown.return_value = "# Summary"
                    with patch("devloop.cli.commands.summary.console"):
                        with patch(
                            "devloop.cli.commands.summary.asyncio.run"
                        ) as mock_run:
                            mock_run.return_value = {"scope": "recent"}

                            agent_summary(scope="today", severity="error")

                            mock_run.assert_called_once()

    def test_agent_summary_with_category_filter(
        self, mock_context_store, mock_generator
    ):
        """Test agent_summary with category filter."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryFormatter"
                ) as MockFormatter:
                    MockFormatter.format_markdown.return_value = "# Summary"
                    with patch("devloop.cli.commands.summary.console"):
                        with patch(
                            "devloop.cli.commands.summary.asyncio.run"
                        ) as mock_run:
                            mock_run.return_value = {"scope": "recent"}

                            agent_summary(scope="session", category="security")

                            mock_run.assert_called_once()

    def test_agent_summary_with_all_filters(self, mock_context_store, mock_generator):
        """Test agent_summary with all filters combined."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryFormatter"
                ) as MockFormatter:
                    MockFormatter.format_markdown.return_value = "# Summary"
                    with patch("devloop.cli.commands.summary.console"):
                        with patch(
                            "devloop.cli.commands.summary.asyncio.run"
                        ) as mock_run:
                            mock_run.return_value = {"scope": "all"}

                            agent_summary(
                                scope="all",
                                agent="formatter",
                                severity="warning",
                                category="style",
                            )

                            mock_run.assert_called_once()

    def test_agent_summary_devloop_dir_detection_cwd(
        self, mock_context_store, mock_generator
    ):
        """Test devloop directory detection from current working directory."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryFormatter"
                ) as MockFormatter:
                    MockFormatter.format_markdown.return_value = "# Summary"
                    with patch("devloop.cli.commands.summary.console"):
                        with patch(
                            "devloop.cli.commands.summary.asyncio.run"
                        ) as mock_run:
                            mock_run.return_value = {"scope": "recent"}

                            # Mock Path.exists() to simulate .devloop in cwd
                            with patch.object(Path, "exists", return_value=True):
                                agent_summary(scope="recent")

                                MockFormatter.format_markdown.assert_called_once()
                                # Check that devloop_dir was passed
                                call_args = MockFormatter.format_markdown.call_args
                                assert call_args[0][1] is not None

    def test_agent_summary_devloop_dir_detection_parent(
        self, mock_context_store, mock_generator
    ):
        """Test devloop directory detection from parent directory."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryFormatter"
                ) as MockFormatter:
                    MockFormatter.format_markdown.return_value = "# Summary"
                    with patch("devloop.cli.commands.summary.console"):
                        with patch(
                            "devloop.cli.commands.summary.asyncio.run"
                        ) as mock_run:
                            mock_run.return_value = {"scope": "recent"}

                            # Mock first path not existing, second path existing
                            exists_calls = [False, True]
                            with patch.object(
                                Path, "exists", side_effect=lambda: exists_calls.pop(0)
                            ):
                                agent_summary(scope="recent")

                                MockFormatter.format_markdown.assert_called_once()

    def test_agent_summary_devloop_dir_from_context_dir(
        self, mock_context_store, mock_generator
    ):
        """Test devloop directory inference from context directory."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryFormatter"
                ) as MockFormatter:
                    MockFormatter.format_markdown.return_value = "# Summary"
                    with patch("devloop.cli.commands.summary.console"):
                        with patch(
                            "devloop.cli.commands.summary.asyncio.run"
                        ) as mock_run:
                            mock_run.return_value = {"scope": "recent"}

                            # All initial paths don't exist, but context dir exists
                            def exists_side_effect(self):
                                return ".devloop/context" in str(self)

                            with patch.object(Path, "exists", exists_side_effect):
                                agent_summary(scope="recent")

                                MockFormatter.format_markdown.assert_called_once()

    def test_agent_summary_error_handling(self, mock_context_store, mock_generator):
        """Test agent_summary error handling."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch("devloop.cli.commands.summary.console") as mock_console:
                    with patch("devloop.cli.commands.summary.asyncio.run") as mock_run:
                        mock_run.side_effect = Exception("Database error")

                        with pytest.raises(typer.Exit):
                            agent_summary(scope="recent")

                        # Should print error message
                        mock_console.print.assert_called()
                        error_msg = str(mock_console.print.call_args[0][0])
                        assert "Error" in error_msg or "error" in error_msg.lower()

    def test_agent_summary_different_scopes(self, mock_context_store, mock_generator):
        """Test agent_summary with different scope values."""
        scopes = ["recent", "today", "session", "all"]

        for scope in scopes:
            with patch(
                "devloop.cli.commands.summary.context_store", mock_context_store
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryGenerator",
                    return_value=mock_generator,
                ):
                    with patch(
                        "devloop.cli.commands.summary.SummaryFormatter"
                    ) as MockFormatter:
                        MockFormatter.format_markdown.return_value = (
                            f"# {scope} Summary"
                        )
                        with patch("devloop.cli.commands.summary.console"):
                            with patch(
                                "devloop.cli.commands.summary.asyncio.run"
                            ) as mock_run:
                                mock_run.return_value = {"scope": scope}

                                agent_summary(scope=scope)

                                mock_run.assert_called_once()

    def test_agent_summary_no_devloop_dir(self, mock_context_store, mock_generator):
        """Test agent_summary when no devloop directory is found."""
        with patch("devloop.cli.commands.summary.context_store", mock_context_store):
            with patch(
                "devloop.cli.commands.summary.SummaryGenerator",
                return_value=mock_generator,
            ):
                with patch(
                    "devloop.cli.commands.summary.SummaryFormatter"
                ) as MockFormatter:
                    MockFormatter.format_markdown.return_value = "# Summary"
                    with patch("devloop.cli.commands.summary.console"):
                        with patch(
                            "devloop.cli.commands.summary.asyncio.run"
                        ) as mock_run:
                            mock_run.return_value = {"scope": "recent"}

                            # Mock all paths not existing
                            with patch.object(Path, "exists", return_value=False):
                                agent_summary(scope="recent")

                                # Should still work with devloop_dir=None
                                MockFormatter.format_markdown.assert_called_once()
                                call_args = MockFormatter.format_markdown.call_args
                                # devloop_dir should be None
                                assert call_args[0][1] is None
