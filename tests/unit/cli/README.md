# CLI Test Suite

Comprehensive test coverage for the dev-agents CLI commands.

## Test Files

### test_main_commands.py (30 tests)

Tests for the main CLI entry point (`dev_agents.cli.main`).

#### Test Classes

**TestInitCommand** (5 tests)
- `test_init_creates_claude_directory` - Verifies .claude directory creation
- `test_init_creates_config_file` - Verifies agents.json config creation
- `test_init_skip_config_flag` - Tests --skip-config option
- `test_init_idempotent` - Ensures init can be run multiple times
- `test_init_default_path_current_directory` - Tests default path behavior

**TestStatusCommand** (2 tests)
- `test_status_displays_agents` - Verifies agent status is displayed
- `test_status_shows_enabled_disabled` - Verifies enabled/disabled indicators

**TestStopCommand** (3 tests)
- `test_stop_no_daemon_running` - Handles gracefully when no daemon exists
- `test_stop_with_running_daemon` - Tests stopping with PID file
- `test_stop_default_path` - Tests default path behavior

**TestVersionCommand** (2 tests)
- `test_version_shows_version` - Displays version info
- `test_version_is_valid_semver` - Validates semantic versioning

**TestAmpStatusCommand** (2 tests)
- `test_amp_status_returns_json` - Returns valid JSON
- `test_amp_status_async_call` - Properly calls async functions

**TestAmpFindingsCommand** (1 test)
- `test_amp_findings_returns_json` - Returns valid JSON output

**TestAmpContextCommand** (2 tests)
- `test_amp_context_no_index_file` - Handles missing context gracefully
- `test_amp_context_with_valid_index` - Reads and displays context JSON

**TestSummaryCommand** (1 test)
- `test_summary_command_exists` - Verifies summary command registration

**TestWatchCommand** (5 tests)
- `test_watch_help` - Displays help properly
- `test_watch_accepts_path_argument` - Accepts path argument
- `test_watch_has_foreground_option` - Has --foreground option
- `test_watch_has_verbose_option` - Has --verbose option
- `test_watch_has_config_option` - Has --config option

**TestCLIHelp** (4 tests)
- `test_main_help` - Main help is accessible
- `test_all_commands_listed` - All commands appear in help
- `test_invalid_command` - Invalid commands fail properly
- `test_invalid_option` - Invalid options fail properly

**TestCLIErrorHandling** (2 tests)
- `test_init_with_invalid_path` - Handles invalid paths gracefully
- `test_status_handles_missing_config` - Handles missing config gracefully

**TestCLIIntegration** (1 test)
- `test_init_then_status_workflow` - Tests init -> status workflow

### test_summary_command.py (5 tests)

Tests for the summary subcommand (`dev_agents.cli.commands.summary`).

#### Test Classes

**TestSummaryCommand** (4 tests)
- `test_summary_help` - Displays help properly
- `test_summary_accepts_scope` - Accepts scope arguments
- `test_summary_accepts_agent_filter` - Accepts --agent option
- `test_summary_accepts_severity_filter` - Accepts --severity option

**TestSummaryIntegration** (1 test)
- `test_summary_command_exists` - Verifies agent-summary command registration

## Running the Tests

Run all CLI tests:
```bash
poetry run pytest tests/unit/cli/ -v
```

Run specific test class:
```bash
poetry run pytest tests/unit/cli/test_main_commands.py::TestInitCommand -v
```

Run with coverage:
```bash
poetry run pytest tests/unit/cli/ --cov=dev_agents.cli --cov-report=html
```

## Test Coverage

- **Commands Tested**: init, watch, status, stop, version, summary, amp-status, amp-findings, amp-context
- **Options Tested**: --skip-config, --foreground, --verbose, --config, --agent, --severity, --category
- **Error Cases**: Invalid paths, missing files, missing config, non-existent daemons
- **Integration**: init -> status workflow, command chaining

## Known Issues

None currently - all tests passing (35/35).

## Adding New Tests

When adding new CLI features:

1. Determine which test file to add to
2. Create a test class for the feature
3. Use `CliRunner` fixture for testing
4. Mock external dependencies (file I/O, async functions)
5. Test both happy path and error cases
6. Run: `poetry run pytest tests/unit/cli/ -v` to verify

Example:
```python
def test_new_feature(self, cli_runner):
    """Test description."""
    result = cli_runner.invoke(app, ["command", "arg"])
    
    assert result.exit_code == 0
    assert "expected output" in result.stdout
```

## References

- [Typer Testing](https://typer.tiangolo.com/tutorial/testing/)
- [CliRunner Documentation](https://typer.tiangolo.com/tutorial/testing/)
- [Pytest Documentation](https://docs.pytest.org/en/latest/)
