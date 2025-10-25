# Agent Type Specifications

This document details the specific implementation requirements for each background agent type.

## Code Quality Agents

### Linter Agent

**Purpose**: Automatically run linters on code changes to catch issues early.

**Triggers**:
- `file:save` - On file save
- `git:pre-commit` - Before commit
- `file:created` - When new file created

**Behavior**:
- Debounce file changes (500ms default)
- Run appropriate linter based on file type
- Cache results to avoid redundant runs
- Report only new issues introduced by changes
- Auto-fix when safe and configured

**Configuration**:
```json
{
  "debounce": 500,
  "filePatterns": ["**/*.{js,ts,jsx,tsx,py,go,rs}"],
  "autoFix": true,
  "autoFixOnSave": true,
  "incrementalOnly": true,
  "linters": {
    "javascript": "eslint",
    "python": "ruff",
    "go": "golangci-lint"
  }
}
```

**Outputs**:
- Inline annotations (via LSP)
- Summary notification on completion
- Exit code for git hooks

---

### Formatter Agent

**Purpose**: Ensure consistent code formatting across the project.

**Triggers**:
- `file:save` - On file save
- `git:pre-commit` - Before commit
- `command:format` - Manual trigger

**Behavior**:
- Format according to project configuration
- Preserve cursor position when possible
- Skip files in .gitignore
- Respect .editorconfig settings

**Configuration**:
```json
{
  "formatOnSave": true,
  "formatOnCommit": false,
  "filePatterns": ["**/*.{js,ts,jsx,tsx,json,md}"],
  "formatters": {
    "javascript": "prettier",
    "python": "black",
    "go": "gofmt",
    "rust": "rustfmt"
  }
}
```

---

### Type Checker Agent

**Purpose**: Continuously monitor for type errors without blocking workflow.

**Triggers**:
- `file:save` - On file save
- `project:load` - On project open
- `interval:60s` - Periodic checks

**Behavior**:
- Run type checker in background (daemon mode)
- Update error locations as code changes
- Show type errors in problem panel
- Provide quick fixes when available

**Configuration**:
```json
{
  "mode": "daemon",
  "checkInterval": 60000,
  "watchMode": true,
  "strictness": "project-default",
  "languages": ["typescript", "python", "go"]
}
```

---

### Security Scanner Agent

**Purpose**: Detect potential security vulnerabilities in code and dependencies.

**Triggers**:
- `file:save` - For code patterns
- `file:package-changed` - When dependencies change
- `git:pre-push` - Before pushing
- `schedule:daily` - Daily full scan

**Behavior**:
- Scan for common vulnerabilities (SQL injection, XSS, etc.)
- Check dependencies against vulnerability databases
- Flag hardcoded secrets
- Validate security headers and configurations

**Configuration**:
```json
{
  "scanDependencies": true,
  "scanCode": true,
  "scanSecrets": true,
  "secretPatterns": ["api_key", "password", "secret", "token"],
  "excludePatterns": ["**/test/**", "**/*.test.*"],
  "severity": ["high", "critical"]
}
```

---

## Testing Agents

### Test Runner Agent

**Purpose**: Automatically run relevant tests when code changes.

**Triggers**:
- `file:save` - Run tests for changed files
- `git:pre-commit` - Run affected tests
- `git:pre-push` - Run full test suite

**Behavior**:
- Determine affected tests from changed files
- Run in watch mode with incremental execution
- Show results in test explorer
- Cancel previous runs when new changes detected

**Configuration**:
```json
{
  "watchMode": true,
  "relatedTestsOnly": true,
  "runOnSave": true,
  "parallelExecution": true,
  "maxParallel": 4,
  "coverage": false,
  "testFrameworks": {
    "javascript": "jest",
    "python": "pytest",
    "go": "go test"
  }
}
```

---

### Coverage Monitor Agent

**Purpose**: Track test coverage trends over time.

**Triggers**:
- `test:complete` - After test run
- `git:post-commit` - After commit
- `schedule:daily` - Daily summary

**Behavior**:
- Calculate coverage deltas
- Alert on coverage decreases
- Generate coverage reports
- Track coverage history

**Configuration**:
```json
{
  "trackHistory": true,
  "alertOnDecrease": true,
  "minimumCoverage": 80,
  "thresholds": {
    "statements": 80,
    "branches": 75,
    "functions": 80,
    "lines": 80
  }
}
```

---

### Test Generator Agent

**Purpose**: Suggest test cases for untested code.

**Triggers**:
- `file:save` - Analyze new/changed code
- `coverage:low` - When coverage drops
- `command:suggest-tests` - Manual trigger

**Behavior**:
- Analyze function signatures and logic
- Generate test scaffolds
- Suggest edge cases
- Identify untested code paths

**Configuration**:
```json
{
  "autoSuggest": true,
  "minComplexity": 3,
  "includeEdgeCases": true,
  "testStyle": "describe-it",
  "frameworks": ["jest", "pytest", "go-test"]
}
```

---

## Git & Version Control Agents

### Commit Message Assistant Agent

**Purpose**: Generate meaningful commit messages from staged changes.

**Triggers**:
- `git:pre-commit` - Before commit dialog
- `command:suggest-commit` - Manual trigger

**Behavior**:
- Analyze staged changes (diff)
- Identify type of change (feat, fix, refactor, etc.)
- Generate conventional commit message
- Consider recent commit patterns

**Configuration**:
```json
{
  "format": "conventional",
  "analyzeContext": true,
  "maxLength": 72,
  "includeScope": true,
  "includeBody": true,
  "templates": {
    "feat": "feat({scope}): {summary}",
    "fix": "fix({scope}): {summary}"
  }
}
```

---

### Merge Conflict Resolver Agent

**Purpose**: Provide context and suggestions for resolving merge conflicts.

**Triggers**:
- `git:conflict-detected` - When conflicts occur
- `file:conflict-markers` - When conflict markers found

**Behavior**:
- Analyze both sides of conflict
- Show history leading to conflict
- Suggest resolution strategies
- Provide "accept both" options when safe

**Configuration**:
```json
{
  "autoAnalyze": true,
  "showHistory": true,
  "suggestResolution": true,
  "contextLines": 5
}
```

---

### Branch Hygiene Agent

**Purpose**: Maintain clean branch structure and suggest cleanup.

**Triggers**:
- `schedule:weekly` - Weekly branch audit
- `git:post-merge` - After merging
- `command:audit-branches` - Manual trigger

**Behavior**:
- Identify merged branches
- Find stale branches (no activity > 30 days)
- Suggest branch deletions
- Warn about diverged branches

**Configuration**:
```json
{
  "staleDays": 30,
  "autoSuggestCleanup": true,
  "excludeBranches": ["main", "develop", "staging"],
  "checkRemote": true
}
```

---

### Code Review Preparer Agent

**Purpose**: Generate PR descriptions and review checklists.

**Triggers**:
- `command:create-pr` - When creating PR
- `git:pre-push` - Before pushing

**Behavior**:
- Analyze commit history on branch
- Generate PR summary from commits
- Create testing checklist
- Identify reviewers based on changed files

**Configuration**:
```json
{
  "includeCommitList": true,
  "generateTestPlan": true,
  "suggestReviewers": true,
  "template": "default",
  "includeScreenshots": false
}
```

---

## Documentation Agents

### Doc Sync Agent

**Purpose**: Ensure documentation stays in sync with code changes.

**Triggers**:
- `file:save` - When code files change
- `git:pre-commit` - Before commit
- `api:changed` - When API surface changes

**Behavior**:
- Detect API signature changes
- Flag outdated documentation
- Suggest documentation updates
- Verify code examples in docs

**Configuration**:
```json
{
  "watchPaths": ["src/**/*.{js,ts,py}", "docs/**/*.md"],
  "verifyExamples": true,
  "checkApiDocs": true,
  "autoUpdate": false
}
```

---

### Comment Updater Agent

**Purpose**: Flag and update outdated code comments.

**Triggers**:
- `file:save` - When code changes
- `refactor:complete` - After refactoring

**Behavior**:
- Compare comments to code
- Detect comment drift
- Suggest comment updates
- Remove obsolete comments

**Configuration**:
```json
{
  "checkFunctionComments": true,
  "checkTodos": true,
  "flagOutdated": true,
  "removeObsolete": false
}
```

---

## Dependency & Build Agents

### Dependency Updater Agent

**Purpose**: Monitor and suggest dependency updates.

**Triggers**:
- `schedule:daily` - Daily update check
- `file:package-changed` - When package file changes
- `command:check-updates` - Manual trigger

**Behavior**:
- Check for available updates
- Categorize by semver (major, minor, patch)
- Show changelogs
- Create update PRs

**Configuration**:
```json
{
  "checkFrequency": "daily",
  "autoUpdate": "patch",
  "groupUpdates": true,
  "excludePackages": [],
  "securityOnly": false
}
```

---

### Build Optimizer Agent

**Purpose**: Analyze and optimize build performance.

**Triggers**:
- `build:complete` - After each build
- `schedule:weekly` - Weekly analysis

**Behavior**:
- Track build times
- Identify slow build steps
- Suggest caching opportunities
- Recommend parallelization

**Configuration**:
```json
{
  "trackMetrics": true,
  "analyzeDuration": true,
  "suggestOptimizations": true,
  "thresholdMs": 10000
}
```

---

### Bundle Analyzer Agent

**Purpose**: Monitor bundle size and composition.

**Triggers**:
- `build:complete` - After production build
- `git:pre-push` - Before pushing
- `dependency:changed` - When deps change

**Behavior**:
- Generate bundle analysis
- Track size trends
- Identify large dependencies
- Suggest optimizations (tree-shaking, code splitting)

**Configuration**:
```json
{
  "maxSize": "500KB",
  "alertOnIncrease": true,
  "increaseThreshold": 10,
  "generateReport": true
}
```

---

## Performance & Monitoring Agents

### Performance Profiler Agent

**Purpose**: Detect performance regressions in code.

**Triggers**:
- `test:complete` - After running perf tests
- `git:pre-commit` - Before committing
- `benchmark:run` - After benchmarks

**Behavior**:
- Run performance benchmarks
- Compare against baseline
- Flag regressions
- Generate flame graphs

**Configuration**:
```json
{
  "regressionThreshold": 10,
  "baselineBranch": "main",
  "autoBenchmark": false,
  "trackMetrics": ["cpu", "memory", "duration"]
}
```

---

### Log Analyzer Agent

**Purpose**: Parse and analyze application logs for patterns.

**Triggers**:
- `log:written` - When logs are written
- `process:stderr` - On stderr output
- `schedule:hourly` - Periodic analysis

**Behavior**:
- Parse structured logs
- Detect error patterns
- Aggregate warnings
- Create alerts for anomalies

**Configuration**:
```json
{
  "logPaths": ["*.log", "logs/**/*.log"],
  "errorPatterns": ["ERROR", "FATAL", "Exception"],
  "aggregateWindow": 300,
  "alertThreshold": 10
}
```

---

## Productivity Agents

### Context Preloader Agent

**Purpose**: Intelligently preload files when switching context.

**Triggers**:
- `git:checkout` - When switching branches
- `ide:workspace-changed` - When workspace changes

**Behavior**:
- Identify recently modified files
- Preload related files
- Warm up language servers
- Cache frequently accessed files

**Configuration**:
```json
{
  "preloadRecent": true,
  "maxFiles": 20,
  "includeRelated": true,
  "warmupLSP": true
}
```

---

### Refactoring Suggester Agent

**Purpose**: Identify refactoring opportunities in codebase.

**Triggers**:
- `schedule:weekly` - Weekly analysis
- `complexity:high` - When complexity detected
- `command:suggest-refactor` - Manual trigger

**Behavior**:
- Detect code duplication
- Find overly complex functions
- Suggest design pattern applications
- Identify unused code

**Configuration**:
```json
{
  "detectDuplication": true,
  "complexityThreshold": 10,
  "suggestPatterns": true,
  "findUnused": true
}
```

---

## Custom Agent Template

For creating custom agents:

```json
{
  "name": "custom-agent",
  "description": "Description of agent purpose",
  "triggers": ["event:type"],
  "behavior": {
    "script": "./scripts/custom-agent.sh",
    "timeout": 30000,
    "parallel": true
  },
  "config": {
    "customOption": "value"
  }
}
```

## Agent Lifecycle Hooks

All agents support these lifecycle hooks:

- `onEnable()` - Called when agent is enabled
- `onDisable()` - Called when agent is disabled
- `onTrigger(event)` - Main execution handler
- `onError(error)` - Error handling
- `onComplete(result)` - Post-execution cleanup
