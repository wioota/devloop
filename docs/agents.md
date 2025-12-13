# Built-in Agents Reference

Complete documentation of all built-in agents.

## Agent Categories

### Code Quality Agents

#### Linter Agent
Runs linters on changed files to catch code issues.
- **Triggers**: `file:save`, `git:pre-commit`
- **Tools**: Ruff, custom linters
- **Output**: Linting errors and warnings

#### Formatter Agent
Auto-formats code with Black, isort, and other formatters.
- **Triggers**: `file:save`
- **Tools**: Black, isort
- **Output**: Applied formatting changes

#### Type Checker Agent
Background type checking with mypy.
- **Triggers**: `file:save`
- **Tools**: mypy
- **Output**: Type errors

### Testing Agents

#### Test Runner Agent
Automatically runs relevant tests on file changes.
- **Triggers**: `file:save`
- **Features**: Smart test selection (runs only affected tests)
- **Output**: Test results and coverage

### Security Agents

#### Security Scanner Agent
Detects code vulnerabilities with Bandit.
- **Triggers**: `file:save`, `git:pre-commit`
- **Tools**: Bandit
- **Output**: Security issues and severity

#### Snyk Agent
Scans dependencies for known vulnerabilities (optional).
- **Triggers**: `git:pre-push`
- **Tools**: Snyk CLI
- **Requires**: `pip install devloop[snyk]`
- **Output**: Vulnerability reports

### Performance Agents

#### Performance Profiler Agent
Tracks performance metrics and detects regressions.
- **Triggers**: `file:save`, `test:complete`
- **Output**: Performance metrics and warnings

### Workflow Agents

#### Git Commit Assistant
Suggests commit messages based on changes.
- **Triggers**: `git:pre-commit`
- **Output**: Suggested commit messages

#### CI Monitor Agent
Tracks GitHub Actions status and failures.
- **Triggers**: `git:post-push`
- **Output**: CI status and failure notifications

#### Doc Lifecycle Agent
Manages documentation organization and sync.
- **Triggers**: `file:save`
- **Output**: Documentation suggestions

### Special Agents

#### Code Rabbit Agent (Optional)
AI-powered code analysis and insights.
- **Requires**: `pip install devloop[code-rabbit]`
- **Triggers**: `file:save`
- **Output**: AI analysis and recommendations

## Configuring Agents

Each agent can be enabled/disabled and configured in `.devloop/agents.json`:

```json
{
  "agents": {
    "linter": {
      "enabled": true,
      "triggers": ["file:save", "git:pre-commit"],
      "config": {
        "debounce": 500,
        "filePatterns": ["**/*.py"]
      }
    }
  }
}
```

## Agent Lifecycle

1. **Initialization** - Agent loads configuration and registers triggers
2. **Monitoring** - Waits for configured events
3. **Execution** - Runs when triggered
4. **Result Reporting** - Logs findings to event store
5. **Notification** - Reports to user (if enabled)

## Custom Agents

Create your own agents without code:

```bash
devloop custom-create find_todos pattern_matcher \
  --description "Find TODO comments" \
  --triggers file:created,file:modified
```

See [docs/AGENT_DEVELOPMENT.md](./AGENT_DEVELOPMENT.md) for detailed guide.

## Agent Marketplace

Discover and install community agents:

```bash
# Search
devloop marketplace search "formatter"

# Install
devloop marketplace install awesome-formatter 1.0.0

# Publish your own
devloop agent publish ./my-agent
```

See [docs/MARKETPLACE_GUIDE.md](./MARKETPLACE_GUIDE.md) for details.

## Troubleshooting Agents

**Agent not running:**
1. Check `.devloop/agents.json` - `"enabled": true`
2. Check logs: `tail -f .devloop/devloop.log`
3. Check triggers - verify events are being generated

**Agent too slow:**
1. Reduce `maxConcurrentAgents` in config
2. Increase `debounce` time
3. Disable optional agents you don't use

**Agent modifying files incorrectly:**
1. Disable auto-fix: Set `"autoFix": false`
2. Review changes: `git diff`
3. Report issue with configuration

See [docs/troubleshooting.md](./troubleshooting.md) for more solutions.
