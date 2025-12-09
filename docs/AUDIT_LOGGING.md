# Audit Logging System

DevLoop includes a comprehensive audit logging system that tracks all agent actions, file modifications, fixes applied, and errors for security, compliance, and incident investigation.

## Overview

The audit logging system provides:

- **Immutable audit trail** of all agent operations
- **File modification tracking** with before/after content and diffs
- **Fix validation** for quality assurance
- **Error tracking** for debugging and monitoring
- **Queryable audit logs** via CLI and programmatic APIs

## Architecture

### Core Components

- **AgentAuditLogger**: Main logger class that maintains append-only audit log
- **AuditEntry**: Data structure for each logged action
- **FileModification**: Details of file changes including diffs and hashes
- **ActionType**: Enumeration of auditable action types

### Log Storage

Audit logs are stored in **append-only JSONL format** for:
- Immutability (no records can be modified or deleted)
- Compliance (audit trail for regulatory requirements)
- Ease of processing (line-delimited JSON for streaming)
- Git-friendly format (human-readable and diff-friendly)

**Default location**: `.devloop/agent-audit.log`

Each line is a complete JSON object representing one audit entry.

## Action Types

The system tracks the following action types:

- **FILE_MODIFIED**: File was modified by an agent
- **FILE_CREATED**: New file was created
- **FILE_DELETED**: File was deleted
- **COMMAND_EXECUTED**: External command was run
- **FIX_APPLIED**: Agent applied an auto-fix to code
- **FINDING_REPORTED**: Agent reported a finding (lint error, type error, etc.)
- **CONFIG_CHANGED**: Configuration was modified
- **ERROR_OCCURRED**: Agent encountered an error

## Usage

### Programmatic API

#### Log an agent action

```python
from devloop.core.agent_audit_logger import get_agent_audit_logger, ActionType

audit_logger = get_agent_audit_logger()

# Log a simple action
audit_logger.log_action(
    agent_name="formatter",
    action_type=ActionType.FILE_MODIFIED,
    message="Formatted file with black",
    success=True,
    duration_ms=150,
)
```

#### Log file modification with diff

```python
from pathlib import Path

# Capture before/after content
before = path.read_text()
# ... make modifications ...
after = path.read_text()

audit_logger.log_file_modified(
    agent_name="formatter",
    file_path=path,
    before_content=before,
    after_content=after,
    message="Formatted test.py with black",
    success=True,
    duration_ms=150,
)
```

The logger automatically:
- Generates unified diffs between before/after
- Calculates file sizes and line counts
- Computes SHA256 hashes for integrity verification
- Truncates large diffs (over 100 lines) to prevent log bloat

#### Log a fix applied

```python
audit_logger.log_fix_applied(
    agent_name="type-checker",
    file_path=path,
    before_content=before,
    after_content=after,
    fix_type="missing-return-type",
    severity="high",
    success=True,
    duration_ms=200,
)
```

#### Log command execution

```python
audit_logger.log_command_execution(
    agent_name="test-runner",
    command="pytest tests/ -v",
    exit_code=0,
    success=True,
    duration_ms=5000,
    message="All tests passed",
)
```

#### Log findings

```python
audit_logger.log_finding_reported(
    agent_name="linter",
    finding_type="line-too-long",
    severity="warning",
    message="Line 42 exceeds max length of 88 characters",
    file_path=path,
    line_number=42,
    fixable=True,
)
```

#### Query audit log

```python
# Get recent entries
entries = audit_logger.query_recent(limit=20)

# Get entries for specific agent
entries = audit_logger.query_by_agent("formatter", limit=20)

# Get specific action types
entries = audit_logger.query_by_action_type(ActionType.FIX_APPLIED)

# Get failed actions
entries = audit_logger.query_failed_actions(limit=20)

# Get fixes applied
entries = audit_logger.query_fixes_applied(agent_name="formatter")

# Get modifications to specific file
entries = audit_logger.query_file_modifications(Path("src/main.py"))
```

### Command Line Interface

#### View recent audit entries

```bash
devloop audit recent
devloop audit recent --limit 50
devloop audit recent --json
```

#### View entries for specific agent

```bash
devloop audit by-agent formatter
devloop audit by-agent linter --limit 10
```

#### View failed actions and errors

```bash
devloop audit errors
devloop audit errors --limit 20
devloop audit errors --json
```

#### View fixes applied

```bash
devloop audit fixes
devloop audit fixes --agent formatter
devloop audit fixes --limit 10
```

#### View file modification history

```bash
devloop audit file src/main.py
devloop audit file src/main.py --diff
devloop audit file src/main.py --limit 20
```

#### View summary statistics

```bash
devloop audit summary
devloop audit summary --json
```

## Log Entry Structure

### Minimal Entry (Action)

```json
{
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "agent_name": "formatter",
  "action_type": "file_modified",
  "message": "Formatted file with black",
  "success": true,
  "duration_ms": 150,
  "file_modifications": null,
  "command": null,
  "exit_code": null,
  "error": null,
  "findings_count": null,
  "context": null
}
```

### Complete Entry (File Modification)

```json
{
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "agent_name": "formatter",
  "action_type": "file_modified",
  "message": "Formatted test.py with black",
  "success": true,
  "duration_ms": 150,
  "file_modifications": [
    {
      "path": "/home/user/project/test.py",
      "action": "modified",
      "size_bytes_before": 1024,
      "size_bytes_after": 1030,
      "line_count_before": 42,
      "line_count_after": 42,
      "diff_lines": [
        "--- test.py",
        "+++ test.py",
        "@@ -5,7 +5,7 @@",
        " def hello():",
        "-    x=1",
        "+    x = 1",
        " "
      ],
      "hash_before": "abc123def456...",
      "hash_after": "fed456abc123..."
    }
  ],
  "command": null,
  "exit_code": null,
  "error": null,
  "findings_count": null,
  "context": {
    "formatter": "black"
  }
}
```

## Security Considerations

### Immutability

The audit log is append-only and stored in a standard file format. To ensure integrity:

1. **Never modify existing entries** - Always append new entries
2. **Use version control** - Commit `.devloop/agent-audit.log` to git for full history
3. **Verify hashes** - Use SHA256 hashes for file change verification
4. **Restrict access** - Limit access to audit logs on production systems

### Privacy

The audit log includes:
- File paths (absolute paths for easy tracing)
- File diffs (actual code changes)
- Command names (first argument only, not full arguments)
- Timestamps

Consider:
- **Not committing sensitive file diffs** to public repositories
- **Archiving old logs** separately from code repositories
- **Rotating logs** to prevent unbounded growth

### Data Retention

Configure log rotation in your DevLoop configuration:

```json
{
  "global": {
    "audit": {
      "rotation": {
        "enabled": true,
        "maxSize": "100MB",
        "maxBackups": 10,
        "maxAgeDays": 30,
        "compress": true
      }
    }
  }
}
```

## Integration with Agents

### Formatter Agent Example

The formatter agent is already integrated:

```python
from devloop.core.agent_audit_logger import get_agent_audit_logger

class FormatterAgent(Agent):
    async def _run_formatter(self, formatter: str, path: Path):
        audit_logger = get_agent_audit_logger()
        
        # Capture before content
        before = path.read_text()
        
        # Run formatter
        success, error = await self._format(formatter, path)
        
        # Log the modification
        if success:
            after = path.read_text()
            audit_logger.log_file_modified(
                agent_name=self.name,
                file_path=path,
                before_content=before,
                after_content=after,
                message=f"Formatted {path.name} with {formatter}",
            )
```

### Adding to Other Agents

To add audit logging to any agent:

1. **Import the logger**:
   ```python
   from devloop.core.agent_audit_logger import get_agent_audit_logger
   ```

2. **Log actions in appropriate places**:
   ```python
   audit_logger = get_agent_audit_logger()
   
   # Log file modifications
   audit_logger.log_file_modified(...)
   
   # Log fixes applied
   audit_logger.log_fix_applied(...)
   
   # Log command execution
   audit_logger.log_command_execution(...)
   
   # Log errors
   audit_logger.log_error(...)
   ```

## Use Cases

### Incident Investigation

When a deployment fails or code issue is discovered:

```bash
# Find all modifications to the failing file
devloop audit file src/failing_service.py

# Check what fixes were attempted
devloop audit fixes --agent type-checker

# Review all errors from the agent
devloop audit errors --agent linter
```

### Compliance Auditing

For regulatory requirements:

```bash
# Export all audit logs to compliance system
devloop audit recent --limit 1000000 --json | \
  jq '[.[] | select(.action_type == "fix_applied")]' > compliance_fixes.json

# Review by agent for access control
devloop audit by-agent formatter --json
```

### Performance Analysis

Understand which agents spend the most time:

```bash
# Get summary with duration breakdown
devloop audit summary

# Analyze specific agent
devloop audit by-agent formatter
```

### Code Review Preparation

Track exactly what changed:

```bash
# See all modifications before commit
devloop audit file src/main.py --diff

# Verify fixes were appropriate
devloop audit fixes --limit 20
```

## File Diff Handling

### Small Changes (< 100 diff lines)

Full diff is stored:

```json
{
  "diff_lines": [
    "--- test.py",
    "+++ test.py",
    "@@ -1,3 +1,3 @@",
    " def hello():",
    "-    print('world')",
    "+    print('hello')"
  ]
}
```

### Large Changes (>= 100 diff lines)

Diff is truncated to first/last 25 lines with indicator:

```json
{
  "diff_lines": [
    "--- large_file.py",
    "+++ large_file.py",
    "@@ -1,10 +1,10 @@",
    "... first 25 lines ...",
    "... (truncated) ...",
    "... last 25 lines ..."
  ]
}
```

This prevents audit log bloat while preserving context for investigation.

## Performance Considerations

- **JSONL format**: Single-pass reading, no full deserialization needed
- **Append-only**: No locking required for writing
- **Lazy queries**: Read only what's needed from tail of file
- **Diff truncation**: Large changes automatically truncated
- **Hash computation**: SHA256 calculated only on demand
- **No external dependencies**: Pure Python with stdlib only

## Testing

The audit logging system includes comprehensive tests:

```bash
pytest tests/unit/core/test_agent_audit_logger.py -v
```

Key test coverage:
- Entry creation and serialization
- File modification tracking
- Diff generation (small and large files)
- Hash calculation
- Query operations (by agent, action type, failures)
- Error handling (invalid JSON, missing files)
- Singleton pattern

## Future Enhancements

Planned improvements:

1. **Audit log rotation** - Automatic archival of old logs
2. **Compression** - Gzip compression for archived logs
3. **Encryption** - Optional encryption for sensitive logs
4. **Remote export** - Send audit logs to external systems
5. **Real-time streaming** - Stream audit events to monitoring systems
6. **Analytics dashboard** - Visual audit log analysis
7. **Alerting** - Alerts on suspicious patterns
8. **OpenTelemetry** - Integration with observability platforms

## Related Documentation

- [AGENTS.md](../AGENTS.md) - Agent architecture overview
- [CODING_RULES.md](../CODING_RULES.md) - Development standards
- [Security Guide](./SECURITY.md) - Security best practices
