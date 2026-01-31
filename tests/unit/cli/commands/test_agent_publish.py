"""Tests for agent_publish CLI commands."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestPublish:
    """Tests for publish command."""

    @pytest.fixture
    def mock_publisher(self):
        """Create mock AgentPublisher."""
        mock_pub = Mock()
        mock_pub.get_publish_readiness.return_value = {
            "ready": True,
            "errors": [],
            "warnings": [],
            "checks": {},
        }
        mock_pub.publish_agent.return_value = (True, "Published successfully")
        return mock_pub

    @pytest.fixture
    def mock_signer(self):
        """Create mock AgentSigner."""
        mock_sig = Mock()
        mock_signature = Mock()
        mock_signature.signer = "test-signer"
        mock_signature.checksum = "abc123" * 8
        mock_sig.sign_agent.return_value = (True, mock_signature)
        return mock_sig

    @pytest.fixture
    def agent_dir(self, tmp_path):
        """Create test agent directory."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "agent.json").write_text('{"name": "test"}')
        return agent_dir

    def test_publish_success(self, agent_dir, mock_publisher, mock_signer):
        """Test successful agent publish."""
        from devloop.cli.commands.agent_publish import publish

        with patch("devloop.marketplace.create_registry_client") as mock_client:
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.marketplace.AgentSigner",
                    return_value=mock_signer,
                ):
                    with patch("devloop.cli.commands.agent_publish.typer.echo"):
                        publish(
                            agent_dir=agent_dir,
                            force=False,
                            sign=True,
                            signer_id=None,
                            registry_dir=None,
                        )

                        # Should create client and publisher
                        mock_client.assert_called_once()
                        mock_publisher.get_publish_readiness.assert_called_once_with(
                            agent_dir
                        )
                        mock_publisher.publish_agent.assert_called_once_with(
                            agent_dir, force=False
                        )

    def test_publish_directory_not_found(self, tmp_path):
        """Test publish with non-existent directory."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import publish

        with patch("devloop.cli.commands.agent_publish.typer.echo"):
            with pytest.raises(typer_module.Exit) as exc_info:
                publish(
                    agent_dir=tmp_path / "nonexistent",
                    force=False,
                    sign=True,
                    signer_id=None,
                    registry_dir=None,
                )

            assert exc_info.value.exit_code == 1

    def test_publish_no_agent_json(self, tmp_path):
        """Test publish with missing agent.json."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import publish

        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()

        with patch("devloop.cli.commands.agent_publish.typer.echo"):
            with pytest.raises(typer_module.Exit) as exc_info:
                publish(
                    agent_dir=agent_dir,
                    force=False,
                    sign=True,
                    signer_id=None,
                    registry_dir=None,
                )

            assert exc_info.value.exit_code == 1

    def test_publish_with_force(self, agent_dir, mock_publisher, mock_signer):
        """Test publish with force flag."""
        from devloop.cli.commands.agent_publish import publish

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.marketplace.AgentSigner",
                    return_value=mock_signer,
                ):
                    with patch("devloop.cli.commands.agent_publish.typer.echo"):
                        publish(
                            agent_dir=agent_dir,
                            force=True,
                            sign=True,
                            signer_id=None,
                            registry_dir=None,
                        )

                        # Should call publish with force=True
                        mock_publisher.publish_agent.assert_called_once_with(
                            agent_dir, force=True
                        )

    def test_publish_no_sign(self, agent_dir, mock_publisher):
        """Test publish without signing."""
        from devloop.cli.commands.agent_publish import publish

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch("devloop.marketplace.AgentSigner") as MockSigner:
                    with patch("devloop.cli.commands.agent_publish.typer.echo"):
                        publish(
                            agent_dir=agent_dir,
                            force=False,
                            sign=False,
                            signer_id=None,
                            registry_dir=None,
                        )

                        # Should not create signer
                        MockSigner.assert_not_called()

    def test_publish_with_custom_signer(self, agent_dir, mock_publisher, mock_signer):
        """Test publish with custom signer ID."""
        from devloop.cli.commands.agent_publish import publish

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.marketplace.AgentSigner",
                    return_value=mock_signer,
                ) as MockSigner:
                    with patch("devloop.cli.commands.agent_publish.typer.echo"):
                        publish(
                            agent_dir=agent_dir,
                            force=False,
                            sign=True,
                            signer_id="custom-signer",
                            registry_dir=None,
                        )

                        # Should create signer with custom ID
                        MockSigner.assert_called_once_with("custom-signer")

    def test_publish_with_custom_registry(self, agent_dir, mock_publisher, mock_signer):
        """Test publish with custom registry directory."""
        from devloop.cli.commands.agent_publish import publish

        custom_registry = Path("/custom/registry")

        with patch("devloop.marketplace.create_registry_client") as mock_client:
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.marketplace.AgentSigner",
                    return_value=mock_signer,
                ):
                    with patch("devloop.cli.commands.agent_publish.typer.echo"):
                        publish(
                            agent_dir=agent_dir,
                            force=False,
                            sign=True,
                            signer_id=None,
                            registry_dir=custom_registry,
                        )

                        # Should create client with custom registry
                        mock_client.assert_called_once_with(custom_registry)

    def test_publish_readiness_errors(self, agent_dir, mock_publisher, mock_signer):
        """Test publish with readiness errors."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import publish

        mock_publisher.get_publish_readiness.return_value = {
            "ready": False,
            "errors": ["Missing required field: name", "Invalid version format"],
            "warnings": [],
            "checks": {},
        }

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch("devloop.cli.commands.agent_publish.typer.echo"):
                    with pytest.raises(typer_module.Exit) as exc_info:
                        publish(
                            agent_dir=agent_dir,
                            force=False,
                            sign=True,
                            signer_id=None,
                            registry_dir=None,
                        )

                    assert exc_info.value.exit_code == 1

    def test_publish_readiness_warnings(self, agent_dir, mock_publisher, mock_signer):
        """Test publish with readiness warnings."""
        from devloop.cli.commands.agent_publish import publish

        mock_publisher.get_publish_readiness.return_value = {
            "ready": True,
            "errors": [],
            "warnings": ["No README.md found", "Missing description"],
            "checks": {},
        }

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.marketplace.AgentSigner",
                    return_value=mock_signer,
                ):
                    with patch("devloop.cli.commands.agent_publish.typer.echo"):
                        publish(
                            agent_dir=agent_dir,
                            force=False,
                            sign=True,
                            signer_id=None,
                            registry_dir=None,
                        )

                        # Should continue despite warnings
                        mock_publisher.publish_agent.assert_called_once()

    def test_publish_sign_failure(self, agent_dir, mock_publisher, mock_signer):
        """Test publish when signing fails."""
        from devloop.cli.commands.agent_publish import publish

        mock_signer.sign_agent.return_value = (False, None)

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.marketplace.AgentSigner",
                    return_value=mock_signer,
                ):
                    with patch("devloop.cli.commands.agent_publish.typer.echo"):
                        publish(
                            agent_dir=agent_dir,
                            force=False,
                            sign=True,
                            signer_id=None,
                            registry_dir=None,
                        )

                        # Should continue despite sign failure
                        mock_publisher.publish_agent.assert_called_once()

    def test_publish_agent_failure(self, agent_dir, mock_publisher, mock_signer):
        """Test publish when publishing fails."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import publish

        mock_publisher.publish_agent.return_value = (False, "Version already exists")

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.marketplace.AgentSigner",
                    return_value=mock_signer,
                ):
                    with patch("devloop.cli.commands.agent_publish.typer.echo"):
                        with pytest.raises(typer_module.Exit) as exc_info:
                            publish(
                                agent_dir=agent_dir,
                                force=False,
                                sign=True,
                                signer_id=None,
                                registry_dir=None,
                            )

                        assert exc_info.value.exit_code == 1

    def test_publish_exception(self, agent_dir):
        """Test publish handles general exceptions."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import publish

        with patch(
            "devloop.marketplace.create_registry_client",
            side_effect=Exception("Connection error"),
        ):
            with patch("devloop.cli.commands.agent_publish.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    publish(
                        agent_dir=agent_dir,
                        force=False,
                        sign=True,
                        signer_id=None,
                        registry_dir=None,
                    )

                assert exc_info.value.exit_code == 1


class TestCheck:
    """Tests for check command."""

    @pytest.fixture
    def mock_publisher(self):
        """Create mock AgentPublisher."""
        mock_pub = Mock()
        mock_pub.get_publish_readiness.return_value = {
            "ready": True,
            "errors": [],
            "warnings": [],
            "checks": {"has_agent_json": True, "valid_version": True},
        }
        mock_pub.check_updates.return_value = {"has_updates": False}
        return mock_pub

    @pytest.fixture
    def agent_dir(self, tmp_path):
        """Create test agent directory."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "agent.json").write_text('{"name": "test"}')
        return agent_dir

    def test_check_success_ready(self, agent_dir, mock_publisher):
        """Test check when agent is ready."""
        from devloop.cli.commands.agent_publish import check

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch("devloop.cli.commands.agent_publish.typer.echo"):
                    check(agent_dir=agent_dir, registry_dir=None)

                    mock_publisher.get_publish_readiness.assert_called_once_with(
                        agent_dir
                    )

    def test_check_success_not_ready(self, agent_dir, mock_publisher):
        """Test check when agent is not ready."""
        from devloop.cli.commands.agent_publish import check

        mock_publisher.get_publish_readiness.return_value = {
            "ready": False,
            "errors": ["Missing required field"],
            "warnings": [],
            "checks": {"has_agent_json": True, "valid_version": False},
        }

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch("devloop.cli.commands.agent_publish.typer.echo"):
                    check(agent_dir=agent_dir, registry_dir=None)

    def test_check_directory_not_found(self, tmp_path):
        """Test check with non-existent directory."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import check

        with patch("devloop.cli.commands.agent_publish.typer.echo"):
            with pytest.raises(typer_module.Exit) as exc_info:
                check(agent_dir=tmp_path / "nonexistent", registry_dir=None)

            assert exc_info.value.exit_code == 1

    def test_check_no_agent_json(self, tmp_path):
        """Test check with missing agent.json."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import check

        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()

        with patch("devloop.cli.commands.agent_publish.typer.echo"):
            with pytest.raises(typer_module.Exit) as exc_info:
                check(agent_dir=agent_dir, registry_dir=None)

            assert exc_info.value.exit_code == 1

    def test_check_with_errors(self, agent_dir, mock_publisher):
        """Test check displays errors."""
        from devloop.cli.commands.agent_publish import check

        mock_publisher.get_publish_readiness.return_value = {
            "ready": False,
            "errors": ["Error 1", "Error 2"],
            "warnings": [],
            "checks": {},
        }

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.cli.commands.agent_publish.typer.echo"
                ) as mock_echo:
                    check(agent_dir=agent_dir, registry_dir=None)

                    # Should show errors
                    calls = [str(call) for call in mock_echo.call_args_list]
                    assert any("Error 1" in call for call in calls)

    def test_check_with_warnings(self, agent_dir, mock_publisher):
        """Test check displays warnings."""
        from devloop.cli.commands.agent_publish import check

        mock_publisher.get_publish_readiness.return_value = {
            "ready": True,
            "errors": [],
            "warnings": ["Warning 1", "Warning 2"],
            "checks": {},
        }

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.cli.commands.agent_publish.typer.echo"
                ) as mock_echo:
                    check(agent_dir=agent_dir, registry_dir=None)

                    # Should show warnings
                    calls = [str(call) for call in mock_echo.call_args_list]
                    assert any("Warning 1" in call for call in calls)

    def test_check_with_updates(self, agent_dir, mock_publisher):
        """Test check when updates are available."""
        from devloop.cli.commands.agent_publish import check

        mock_publisher.check_updates.return_value = {
            "has_updates": True,
            "published_version": "1.0.0",
            "local_version": "1.1.0",
        }

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.cli.commands.agent_publish.typer.echo"
                ) as mock_echo:
                    with patch(
                        "devloop.cli.commands.agent_publish.typer.secho"
                    ) as mock_secho:
                        check(agent_dir=agent_dir, registry_dir=None)

                        # Should show update info (via secho for colored output)
                        echo_calls = [str(call) for call in mock_echo.call_args_list]
                        secho_calls = [str(call) for call in mock_secho.call_args_list]
                        all_calls = echo_calls + secho_calls
                        assert any("Update available" in call for call in all_calls)

    def test_check_no_updates(self, agent_dir, mock_publisher):
        """Test check when no updates available."""
        from devloop.cli.commands.agent_publish import check

        mock_publisher.check_updates.return_value = {
            "has_updates": False,
            "local_version": "1.0.0",
        }

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch(
                    "devloop.cli.commands.agent_publish.typer.echo"
                ) as mock_echo:
                    check(agent_dir=agent_dir, registry_dir=None)

                    # Should show local version
                    calls = [str(call) for call in mock_echo.call_args_list]
                    assert any("Local version: 1.0.0" in call for call in calls)

    def test_check_custom_registry(self, agent_dir, mock_publisher):
        """Test check with custom registry directory."""
        from devloop.cli.commands.agent_publish import check

        custom_registry = Path("/custom/registry")

        with patch("devloop.marketplace.create_registry_client") as mock_client:
            with patch(
                "devloop.marketplace.AgentPublisher",
                return_value=mock_publisher,
            ):
                with patch("devloop.cli.commands.agent_publish.typer.echo"):
                    check(agent_dir=agent_dir, registry_dir=custom_registry)

                    mock_client.assert_called_once_with(custom_registry)

    def test_check_exception(self, agent_dir):
        """Test check handles general exceptions."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import check

        with patch(
            "devloop.marketplace.create_registry_client",
            side_effect=Exception("Connection error"),
        ):
            with patch("devloop.cli.commands.agent_publish.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    check(agent_dir=agent_dir, registry_dir=None)

                assert exc_info.value.exit_code == 1


class TestVersion:
    """Tests for version command."""

    @pytest.fixture
    def agent_dir(self, tmp_path):
        """Create test agent directory."""
        agent_dir = tmp_path / "test-agent"
        agent_dir.mkdir()
        (agent_dir / "agent.json").write_text('{"version": "1.0.0"}')
        return agent_dir

    def test_version_patch(self, agent_dir):
        """Test version bump with patch."""
        from devloop.cli.commands.agent_publish import version

        with patch("devloop.marketplace.VersionManager") as MockVersionMgr:
            MockVersionMgr.bump_version.return_value = "1.0.1"
            MockVersionMgr.update_agent_json.return_value = True

            with patch("devloop.cli.commands.agent_publish.typer.echo"):
                version(agent_dir=agent_dir, bump_type="patch")

                MockVersionMgr.bump_version.assert_called_once_with("1.0.0", "patch")
                MockVersionMgr.update_agent_json.assert_called_once_with(
                    agent_dir, "1.0.1"
                )

    def test_version_minor(self, agent_dir):
        """Test version bump with minor."""
        from devloop.cli.commands.agent_publish import version

        with patch("devloop.marketplace.VersionManager") as MockVersionMgr:
            MockVersionMgr.bump_version.return_value = "1.1.0"
            MockVersionMgr.update_agent_json.return_value = True

            with patch("devloop.cli.commands.agent_publish.typer.echo"):
                version(agent_dir=agent_dir, bump_type="minor")

                MockVersionMgr.bump_version.assert_called_once_with("1.0.0", "minor")

    def test_version_major(self, agent_dir):
        """Test version bump with major."""
        from devloop.cli.commands.agent_publish import version

        with patch("devloop.marketplace.VersionManager") as MockVersionMgr:
            MockVersionMgr.bump_version.return_value = "2.0.0"
            MockVersionMgr.update_agent_json.return_value = True

            with patch("devloop.cli.commands.agent_publish.typer.echo"):
                version(agent_dir=agent_dir, bump_type="major")

                MockVersionMgr.bump_version.assert_called_once_with("1.0.0", "major")

    def test_version_directory_not_found(self, tmp_path):
        """Test version with non-existent directory."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import version

        with patch("devloop.cli.commands.agent_publish.typer.echo"):
            with pytest.raises(typer_module.Exit) as exc_info:
                version(agent_dir=tmp_path / "nonexistent", bump_type="patch")

            assert exc_info.value.exit_code == 1

    def test_version_no_agent_json(self, tmp_path):
        """Test version with missing agent.json."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import version

        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()

        with patch("devloop.cli.commands.agent_publish.typer.echo"):
            with pytest.raises(typer_module.Exit) as exc_info:
                version(agent_dir=agent_dir, bump_type="patch")

            assert exc_info.value.exit_code == 1

    def test_version_invalid_bump_type(self, agent_dir):
        """Test version with invalid bump type."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import version

        with patch("devloop.cli.commands.agent_publish.typer.echo"):
            with pytest.raises(typer_module.Exit) as exc_info:
                version(agent_dir=agent_dir, bump_type="invalid")

            assert exc_info.value.exit_code == 1

    def test_version_update_failure(self, agent_dir):
        """Test version when update fails."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import version

        with patch("devloop.marketplace.VersionManager") as MockVersionMgr:
            MockVersionMgr.bump_version.return_value = "1.0.1"
            MockVersionMgr.update_agent_json.return_value = False

            with patch("devloop.cli.commands.agent_publish.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    version(agent_dir=agent_dir, bump_type="patch")

                assert exc_info.value.exit_code == 1

    def test_version_exception(self, agent_dir):
        """Test version handles general exceptions."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import version

        with patch(
            "devloop.marketplace.VersionManager.bump_version",
            side_effect=Exception("File error"),
        ):
            with patch("devloop.cli.commands.agent_publish.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    version(agent_dir=agent_dir, bump_type="patch")

                assert exc_info.value.exit_code == 1


class TestDeprecate:
    """Tests for deprecate command."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock DeprecationManager."""
        mock_mgr = Mock()
        mock_mgr.deprecate_agent.return_value = (True, "Agent deprecated successfully")
        return mock_mgr

    def test_deprecate_success(self, mock_manager):
        """Test successful agent deprecation."""
        from devloop.cli.commands.agent_publish import deprecate

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.DeprecationManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.agent_publish.typer.echo"):
                    deprecate(
                        agent_name="old-agent",
                        message="No longer maintained",
                        replacement=None,
                        registry_dir=None,
                    )

                    mock_manager.deprecate_agent.assert_called_once_with(
                        "old-agent",
                        "No longer maintained",
                        replacement=None,
                    )

    def test_deprecate_with_replacement(self, mock_manager):
        """Test deprecation with replacement agent."""
        from devloop.cli.commands.agent_publish import deprecate

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.DeprecationManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.agent_publish.typer.echo"):
                    deprecate(
                        agent_name="old-agent",
                        message="Use new-agent instead",
                        replacement="new-agent",
                        registry_dir=None,
                    )

                    mock_manager.deprecate_agent.assert_called_once_with(
                        "old-agent",
                        "Use new-agent instead",
                        replacement="new-agent",
                    )

    def test_deprecate_custom_registry(self, mock_manager):
        """Test deprecate with custom registry directory."""
        from devloop.cli.commands.agent_publish import deprecate

        custom_registry = Path("/custom/registry")

        with patch("devloop.marketplace.create_registry_client") as mock_client:
            with patch(
                "devloop.marketplace.DeprecationManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.agent_publish.typer.echo"):
                    deprecate(
                        agent_name="old-agent",
                        message="Deprecated",
                        replacement=None,
                        registry_dir=custom_registry,
                    )

                    mock_client.assert_called_once_with(custom_registry)

    def test_deprecate_failure(self, mock_manager):
        """Test deprecate when operation fails."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import deprecate

        mock_manager.deprecate_agent.return_value = (False, "Agent not found")

        with patch("devloop.marketplace.create_registry_client"):
            with patch(
                "devloop.marketplace.DeprecationManager",
                return_value=mock_manager,
            ):
                with patch("devloop.cli.commands.agent_publish.typer.echo"):
                    with pytest.raises(typer_module.Exit) as exc_info:
                        deprecate(
                            agent_name="old-agent",
                            message="Deprecated",
                            replacement=None,
                            registry_dir=None,
                        )

                    assert exc_info.value.exit_code == 1

    def test_deprecate_exception(self):
        """Test deprecate handles general exceptions."""
        import typer as typer_module

        from devloop.cli.commands.agent_publish import deprecate

        with patch(
            "devloop.marketplace.create_registry_client",
            side_effect=Exception("Connection error"),
        ):
            with patch("devloop.cli.commands.agent_publish.typer.echo"):
                with pytest.raises(typer_module.Exit) as exc_info:
                    deprecate(
                        agent_name="old-agent",
                        message="Deprecated",
                        replacement=None,
                        registry_dir=None,
                    )

                assert exc_info.value.exit_code == 1


class TestRegisterAgentCommands:
    """Tests for register_agent_commands function."""

    def test_register_agent_commands(self):
        """Test register_agent_commands adds typer app."""
        from devloop.cli.commands.agent_publish import register_agent_commands

        mock_main_app = Mock()

        register_agent_commands(mock_main_app)

        # Should call add_typer with app and name
        mock_main_app.add_typer.assert_called_once()
        call_args = mock_main_app.add_typer.call_args
        assert call_args[1]["name"] == "agent"
