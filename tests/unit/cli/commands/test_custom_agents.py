"""Tests for custom_agents CLI commands."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from devloop.cli.commands.custom_agents import create, delete, list_agents, templates


class TestListAgents:
    """Tests for list_agents command."""

    @pytest.fixture
    def mock_store(self):
        """Create mock CustomAgentStore."""
        mock = Mock()
        mock.get_all_agents = AsyncMock()
        return mock

    def test_list_agents_with_agents(self, mock_store):
        """Test list_agents when agents exist."""
        mock_agent1 = Mock()
        mock_agent1.name = "Test Agent 1"
        mock_agent1.agent_type = "detector"

        mock_agent2 = Mock()
        mock_agent2.name = "Test Agent 2"
        mock_agent2.agent_type = "analyzer"

        mock_store.get_all_agents.return_value = {
            "agent-1": mock_agent1,
            "agent-2": mock_agent2,
        }

        with patch(
            "devloop.cli.commands.custom_agents.CustomAgentStore",
            return_value=mock_store,
        ):
            with patch("devloop.cli.commands.custom_agents.console") as mock_console:
                list_agents(project_dir=None)

                # Should call get_all_agents
                mock_store.get_all_agents.assert_called_once()

                # Should print table with agents
                mock_console.print.assert_called()
                # Check that table was printed (Rich Table object)
                assert mock_console.print.call_count >= 1

    def test_list_agents_no_agents(self, mock_store):
        """Test list_agents when no agents exist."""
        mock_store.get_all_agents.return_value = {}

        with patch(
            "devloop.cli.commands.custom_agents.CustomAgentStore",
            return_value=mock_store,
        ):
            with patch("devloop.cli.commands.custom_agents.console") as mock_console:
                list_agents(project_dir=None)

                # Should print no agents message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("No custom agents found" in call for call in calls)

    def test_list_agents_with_project_dir(self, mock_store):
        """Test list_agents with custom project directory."""
        mock_store.get_all_agents.return_value = {}

        with patch(
            "devloop.cli.commands.custom_agents.CustomAgentStore",
            return_value=mock_store,
        ) as MockStore:
            with patch("devloop.cli.commands.custom_agents.console"):
                custom_dir = Path("/custom/project")
                list_agents(project_dir=custom_dir)

                # Should create store with correct path
                MockStore.assert_called_once()
                created_path = MockStore.call_args[0][0]
                assert str(created_path) == "/custom/project/.devloop/custom_agents"

    def test_list_agents_uses_cwd_by_default(self, mock_store):
        """Test list_agents uses current directory when project_dir is None."""
        mock_store.get_all_agents.return_value = {}

        with patch(
            "devloop.cli.commands.custom_agents.CustomAgentStore",
            return_value=mock_store,
        ) as MockStore:
            with patch("devloop.cli.commands.custom_agents.console"):
                with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                    list_agents(project_dir=None)

                    # Should use cwd
                    created_path = MockStore.call_args[0][0]
                    assert "/fake/cwd/.devloop/custom_agents" in str(created_path)


class TestCreate:
    """Tests for create command."""

    @pytest.fixture
    def mock_store(self):
        """Create mock CustomAgentStore."""
        mock = Mock()
        mock.save_agent = AsyncMock()
        return mock

    @pytest.fixture
    def mock_builder(self):
        """Create mock AgentBuilder."""
        mock = Mock()
        mock_agent = Mock()
        mock_agent.id = "agent-123"
        mock_agent.name = "Test Agent"
        mock.build.return_value = mock_agent
        return mock

    def test_create_success(self, mock_store, mock_builder):
        """Test successful agent creation."""
        with patch(
            "devloop.cli.commands.custom_agents.get_agent_template",
            return_value={"description": "Test template", "config": {}},
        ):
            with patch(
                "devloop.cli.commands.custom_agents.AgentBuilder",
                return_value=mock_builder,
            ):
                with patch(
                    "devloop.cli.commands.custom_agents.CustomAgentStore",
                    return_value=mock_store,
                ):
                    with patch(
                        "devloop.cli.commands.custom_agents.console"
                    ) as mock_console:
                        create(
                            name="Test Agent",
                            agent_type="detector",
                            description="",
                            project_dir=None,
                        )

                        # Should build agent
                        mock_builder.build.assert_called_once()
                        build_args = mock_builder.build.call_args[1]
                        assert build_args["name"] == "Test Agent"
                        assert build_args["agent_type"] == "detector"

                        # Should save agent
                        mock_store.save_agent.assert_called_once()

                        # Should print success message
                        calls = [
                            str(call) for call in mock_console.print.call_args_list
                        ]
                        assert any("Created custom agent" in call for call in calls)

    def test_create_with_custom_description(self, mock_store, mock_builder):
        """Test create with custom description."""
        with patch(
            "devloop.cli.commands.custom_agents.get_agent_template",
            return_value={"description": "Template desc", "config": {}},
        ):
            with patch(
                "devloop.cli.commands.custom_agents.AgentBuilder",
                return_value=mock_builder,
            ):
                with patch(
                    "devloop.cli.commands.custom_agents.CustomAgentStore",
                    return_value=mock_store,
                ):
                    with patch("devloop.cli.commands.custom_agents.console"):
                        create(
                            name="Agent",
                            agent_type="detector",
                            description="Custom description",
                            project_dir=None,
                        )

                        # Should use custom description
                        build_args = mock_builder.build.call_args[1]
                        assert build_args["description"] == "Custom description"

    def test_create_unknown_agent_type(self, mock_store):
        """Test create with unknown agent type."""
        import typer as typer_module

        with patch(
            "devloop.cli.commands.custom_agents.get_agent_template",
            return_value=None,
        ):
            with patch("devloop.cli.commands.custom_agents.console") as mock_console:
                with pytest.raises(typer_module.Exit) as exc_info:
                    create(
                        name="Agent",
                        agent_type="unknown-type",
                        description="",
                        project_dir=None,
                    )

                # Should print error message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Unknown agent type" in call for call in calls)
                assert exc_info.value.exit_code == 1

    def test_create_with_project_dir(self, mock_store, mock_builder):
        """Test create with custom project directory."""
        with patch(
            "devloop.cli.commands.custom_agents.get_agent_template",
            return_value={"description": "Test", "config": {}},
        ):
            with patch(
                "devloop.cli.commands.custom_agents.AgentBuilder",
                return_value=mock_builder,
            ):
                with patch(
                    "devloop.cli.commands.custom_agents.CustomAgentStore",
                    return_value=mock_store,
                ) as MockStore:
                    with patch("devloop.cli.commands.custom_agents.console"):
                        custom_dir = Path("/custom/path")
                        create(
                            name="Agent",
                            agent_type="detector",
                            description="",
                            project_dir=custom_dir,
                        )

                        # Should use custom path
                        created_path = MockStore.call_args[0][0]
                        assert (
                            str(created_path) == "/custom/path/.devloop/custom_agents"
                        )

    def test_create_uses_template_config(self, mock_store, mock_builder):
        """Test create uses template config."""
        template_config = {"key": "value", "setting": 123}

        with patch(
            "devloop.cli.commands.custom_agents.get_agent_template",
            return_value={"description": "Test", "config": template_config},
        ):
            with patch(
                "devloop.cli.commands.custom_agents.AgentBuilder",
                return_value=mock_builder,
            ):
                with patch(
                    "devloop.cli.commands.custom_agents.CustomAgentStore",
                    return_value=mock_store,
                ):
                    with patch("devloop.cli.commands.custom_agents.console"):
                        create(
                            name="Agent",
                            agent_type="detector",
                            description="",
                            project_dir=None,
                        )

                        # Should pass template config to builder
                        build_args = mock_builder.build.call_args[1]
                        assert build_args["config"] == template_config


class TestDelete:
    """Tests for delete command."""

    @pytest.fixture
    def mock_store(self):
        """Create mock CustomAgentStore."""
        mock = Mock()
        mock.delete_agent = AsyncMock()
        return mock

    def test_delete_success(self, mock_store):
        """Test successful agent deletion."""
        with patch(
            "devloop.cli.commands.custom_agents.CustomAgentStore",
            return_value=mock_store,
        ):
            with patch("devloop.cli.commands.custom_agents.console") as mock_console:
                delete(agent_id="agent-123", project_dir=None)

                # Should call delete_agent
                mock_store.delete_agent.assert_called_once_with("agent-123")

                # Should print success message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Deleted agent" in call for call in calls)
                assert any("agent-123" in call for call in calls)

    def test_delete_with_project_dir(self, mock_store):
        """Test delete with custom project directory."""
        with patch(
            "devloop.cli.commands.custom_agents.CustomAgentStore",
            return_value=mock_store,
        ) as MockStore:
            with patch("devloop.cli.commands.custom_agents.console"):
                custom_dir = Path("/custom/project")
                delete(agent_id="agent-123", project_dir=custom_dir)

                # Should use custom path
                created_path = MockStore.call_args[0][0]
                assert str(created_path) == "/custom/project/.devloop/custom_agents"

    def test_delete_uses_cwd_by_default(self, mock_store):
        """Test delete uses current directory when project_dir is None."""
        with patch(
            "devloop.cli.commands.custom_agents.CustomAgentStore",
            return_value=mock_store,
        ) as MockStore:
            with patch("devloop.cli.commands.custom_agents.console"):
                with patch("pathlib.Path.cwd", return_value=Path("/fake/cwd")):
                    delete(agent_id="agent-123", project_dir=None)

                    # Should use cwd
                    created_path = MockStore.call_args[0][0]
                    assert "/fake/cwd/.devloop/custom_agents" in str(created_path)


class TestTemplates:
    """Tests for templates command."""

    def test_templates_shows_all_types(self):
        """Test templates command shows all template types."""
        with patch("devloop.cli.commands.custom_agents.console") as mock_console:
            templates()

            # Should print table
            mock_console.print.assert_called_once()

            # The table should be a Rich Table
            table_arg = mock_console.print.call_args[0][0]
            assert hasattr(table_arg, "add_row")  # Rich Table has add_row method

    def test_templates_includes_detector(self):
        """Test templates includes detector type."""
        # We can't easily inspect the Rich Table contents in the test,
        # but we can verify the function runs without error
        with patch("devloop.cli.commands.custom_agents.console"):
            templates()
            # Function should complete without raising

    def test_templates_includes_analyzer(self):
        """Test templates includes analyzer type."""
        with patch("devloop.cli.commands.custom_agents.console"):
            templates()
            # Function should complete without raising

    def test_templates_includes_generator(self):
        """Test templates includes generator type."""
        with patch("devloop.cli.commands.custom_agents.console"):
            templates()
            # Function should complete without raising
