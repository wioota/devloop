# Background Agent Integration
**Amp integration instructions for devloop**

This project includes background agents that enhance Amp's development workflow through automated code quality checks and intelligent context provision.

## Installation

**Single Command Installation:**
```bash
curl -fsSL https://raw.githubusercontent.com/wioota/devloop/main/install.sh | bash
```

This will:
- Install Claude Agents to `~/.devloop`
- Set up Python virtual environment
- Add `devloop` and `ca` to your PATH
- Configure shell integration

**Quick Start:**
```bash
cd your-project
ca start    # Start background agents
ca status   # Check agent status
ca stop     # Stop agents
```

**Amp Integration Setup:**
```bash
ca amp-setup  # Setup Amp integration
```

**Coding Rules Validation:**
```bash
validate-rules --all  # Check all Python files
validate-rules file.py  # Check specific file
```

## Background Agent System

- **Linter Agent**: Automatically runs code linting on file changes (ruff, eslint, etc.)
- **Formatter Agent**: Applies consistent code formatting (black, prettier, etc.)
- **Test Runner Agent**: Executes relevant tests when code changes (pytest, jest, etc.)
- **Security Scanner**: Checks for security vulnerabilities

## Amp Integration Instructions

When working with Amp, leverage background agents using subagent patterns for optimal integration:

### Proactive Subagent Usage

1. **Session Start**: "Spawn a subagent to check current background agent status"
2. **During Development**: "Use a subagent to monitor background agent activity"
3. **Before Commits**: "Have a subagent summarize recent agent findings"
4. **When Debugging**: "Ask a subagent to analyze background agent diagnostics"

### Example Amp Commands

- "Spawn a subagent to check if background linter found any issues in my recent changes"
- "Use a subagent to monitor background agent activity during this refactoring"
- "Have a subagent summarize the current test status from background agents"
- "Ask a subagent to analyze security scan results for my recent changes"
- "Check background agent results for the files I just modified"
- "Automatically apply safe background agent fixes"
- "Apply auto-fixable lint issues"

### Context Location

Background agents write structured findings to: `.claude/context/`

**Key files for Amp integration:**
- `index.json` - **Read this first** - Summary of all findings with urgency levels
- `immediate.json` - Blocking issues that need immediate attention
- `relevant.json` - Issues worth mentioning during development
- `background.json` - Non-urgent items for awareness
- `auto_fixed.json` - Log of automatic fixes applied

Subagents can read these files to provide contextual insights during development.

### Available Agent Results

Subagents can access:
- **Lint results** and auto-fix suggestions
- **Test execution status** and failure details
- **Security scan findings** and recommendations
- **Code formatting status** and changes applied
- **Recent activity logs** and performance metrics

### Advanced Amp Integration

- **Oracle Integration**: Use Amp's Oracle to analyze complex background agent findings
- **Librarian Queries**: Use Librarian to search related code when agents detect issues
- **Custom Subagents**: Create project-specific subagents that incorporate background agent results
- **Thread Context**: Background agent results persist across Amp thread sessions

### Auto-Fix Capabilities

Amp subagents can automatically apply safe fixes when instructed:

- **Safety Levels**: Configure auto-fix safety (safe_only, medium_risk, all)
- **Backup System**: All fixes are backed up and can be rolled back
- **Change Tracking**: Amp is aware of all changes made and can suggest rollbacks
- **User Control**: You control what gets auto-fixed and when
- **Transparent**: You'll be notified of all auto-applied fixes

**Example**: "Automatically apply safe background agent fixes"
This will apply lint fixes, formatting fixes, and other safe improvements.

### Rollback Capabilities

If issues arise from automatic fixes, Amp knows how to rollback changes:

- **Simple Commands**: "Rollback the last background agent changes"
- **Selective Rollback**: "Rollback specific change by ID"
- **Full Session Rollback**: "Rollback all changes from this session"
- **Safe Process**: All rollbacks use timestamped backups

**Rollback Commands for Amp:**
- "Rollback the last background agent fix"
- "Undo the changes from background agents"
- "Revert the automatic fixes that were just applied"
- "Show me what changes can be rolled back"

### Best Practices

- Use subagents proactively to check background agent status before major changes
- Keep subagent context separate from main thread for clarity
- Leverage Amp's advanced reasoning capabilities for complex agent result analysis
- Integrate background agent findings into your development decision-making
- Use background agent data to inform Amp's suggestions and next steps

### Communication Style
**IMPORTANT**: Be much less verbose in work summaries. Keep responses concise and to the point. Focus on what was accomplished and next steps only.

### Coding Rules Integration
**MANDATORY**: When using devloop, automatically follow the coding rules in `CODING_RULES.md`. Learn from every failure pattern and update your coding approach:

- **Pattern Recognition**: Identify recurring issues (tool availability, configuration errors, path handling, async patterns)
- **Rule Application**: Apply the 10 core patterns from CODING_RULES.md to all code you generate
- **Failure Learning**: When encountering issues, reference CODING_RULES.md patterns and update your approach
- **Prevention**: Use the documented patterns to prevent known failure modes
- **Evolution**: Suggest improvements to CODING_RULES.md when discovering new patterns

**Key Rules to Always Follow:**
1. Check tool availability before execution with helpful error messages
2. Use dataclass configuration with `__post_init__` validation
3. Implement comprehensive async error handling
4. Use Path objects with security validation
5. Standardize results with AgentResult format
6. Apply safe imports for optional dependencies
7. Implement proper resource lifecycle management
8. Use structured logging consistently

**Test Setup Requirements**
**MANDATORY**: When initializing projects with devloop, ensure proper test framework setup:

- **Auto-detect test frameworks** in the project (pytest, unittest, jest, etc.)
- **Create basic test structure** if none exists (tests/ directory, basic test files)
- **Configure test runners** appropriately for detected frameworks
- **Add test dependencies** to project configuration
- **Create example tests** to demonstrate functionality
- **Setup CI/CD integration** for automated testing

### Git/GitHub Update Process
At the end of each fixing cycle:
1. **Validate coding rules**: `validate-rules --all` to ensure code follows established patterns
2. **Review changes**: `git status` and `git diff` to see what was modified
3. **Stage improvements**: `git add .` or selectively add changed files
4. **Commit changes**: `git commit -m "Brief description of improvements"`
5. **Push to GitHub**: `git push origin main` (or your branch)
6. **Update documentation**: Ensure README and docs reflect new capabilities
7. **Update coding rules**: If new patterns discovered, update CODING_RULES.md

### Amp Hooks Integration

For enhanced integration, consider adding these Amp hooks to your `.vscode/settings.json`:

```json
"amp.hooks": [
  {
    "id": "check-background-findings",
    "on": {
      "event": "tool:pre-execute",
      "tool": ["edit_file"]
    },
    "action": {
      "type": "send-user-message",
      "message": "Before editing files, check .claude/context/index.json for any background agent findings that might be relevant to your current task."
    }
  },
  {
    "id": "redact-dev-agent-commands",
    "on": {
      "event": "tool:post-execute",
      "tool": ["Bash"]
    },
    "action": {
      "type": "redact-tool-input",
      "redactedInput": {
        "cmd": "[Command redacted - background agent management]"
      }
    }
  }
]
```

### Development Workflow

Background agents run automatically on file changes and provide results that Amp subagents can analyze and present in contextually appropriate ways. This creates an intelligent, collaborative development environment where background agents handle routine checks while Amp focuses on complex reasoning and user interaction.

**Current Integration Status:**
- ✅ Context store provides structured findings with urgency tiers
- ✅ Amp can read findings proactively through subagents
- ✅ Background agents run automatically without blocking Amp
- ✅ Findings include severity levels, auto-fix suggestions, and context
- ✅ Integration works with Amp's thread-based workflow

### Future Integration Options

For even deeper integration, devloop could provide:

**MCP Servers**: Expose agents as callable tools (e.g., "run linter on this code")
**Toolboxes**: Simple scripts for specific operations (e.g., format this file)

These would allow Amp to call agents directly rather than reading results asynchronously. The current context store approach is more appropriate for background monitoring, but direct tool integration could enable more interactive workflows.
