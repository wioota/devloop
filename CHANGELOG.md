# Changelog

All notable changes to devloop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.4.0] - 2025-12-09

### Major Features

#### Structured Event Logging & Performance Tracking
- **Event store with SQLite backend** for persistent event history
- **Agent execution metrics** - timing, success rates, error tracking
- **Performance benchmarking framework** for agent efficiency analysis
- **Audit logging** with 30-day retention policy
- **File-level locking and versioning** for race condition prevention

#### Observability & Analysis
- **Agent audit CLI commands** - query recent findings and agent activity
- **Agent health monitoring** - track agent performance and reliability
- **README value validation** - documented features with data tracking
- **CLI telemetry integration** - foundation for usage analytics

### Improvements

#### Memory Management
- **Aggressive context store trimming** - per-tier memory limits (500 → 250 findings)
- **Increased cleanup frequency** - 1 hour → 15 minutes for faster cleanup
- **Timestamp-based prioritization** - keeps most recent findings in memory
- **Comprehensive memory tests** - validates memory constraints

#### CLI & UX
- **Pre-flight checklist updates** - documentation in AGENTS.md
- **Typer/Click compatibility fix** - proper audit command integration
- **CI status verification** - pre-push hook validates GitHub Actions status
- **Interactive agent setup** - optional agents during `devloop init`

#### Code Quality
- **25+ unit tests for context store** including memory management
- **Comprehensive audit logging tests**
- **Performance benchmarking tests**
- **All code formatted with Black and type-checked with mypy**

### Security
- **Audit log retention policies** prevent unbounded disk usage
- **File locking** prevents race conditions in concurrent access
- **Event versioning** for audit trail integrity

### Documentation
- **Agent architecture guide** in AGENTS.md
- **Task management with Beads** - synced issue tracking
- **Development discipline framework** with git hooks

---

## [0.3.1] - 2025-12-06

### Fixed
- Black formatting in main.py
- Flaky sandbox benchmark test thresholds

---

## [0.3.0] - 2025-12-06

### Major Features

#### Claude Code Integration
- **Auto-install Claude Code slash commands** during `devloop init`
  - Slash commands: `/agent-summary`, `/agent-status`
  - Automatic setup in `.claude/commands/` directory
  - Zero-configuration integration for Claude Code users

#### Sandbox Security System (Phases 1-3)
- **Phase 1: Bubblewrap sandbox foundation**
  - Secure agent execution in isolated environments
  - Filesystem restrictions and process isolation
  - Resource limits (CPU, memory, execution time)

- **Phase 2: cgroups & Performance**
  - Memory and CPU limits via cgroups v2
  - Performance benchmarking framework
  - Comprehensive audit logging for all sandbox operations

- **Phase 3: Pyodide WASM sandbox**
  - Browser-grade sandboxing for Python code execution
  - Automatic Pyodide installation during `devloop init`
  - Network allowlist and policy engine design

- **Security testing**: Malicious config detection, path traversal prevention

#### DevLoop Visibility Enhancement
- **Extract findings to Beads** via pre-push hook
  - Automatic conversion of DevLoop findings to Beads issues
  - Link discovered issues with `discovered-from` dependencies
  - Git-synced issue tracking for long-term memory

- **Operational health analytics** in agent summary
  - Health status, performance metrics, activity timeline
  - Agent success/failure tracking
  - Resource usage monitoring

### Improvements

#### Task Management & Workflow
- **Beads-only policy** for all task tracking (no markdown TODOs)
  - AGENTS.md auto-injection during `devloop init`
  - Claude Code symlink (`CLAUDE.md -> AGENTS.md`)
  - Template system for Beads integration

- **Developer discipline framework**
  - Pre-commit and pre-push git hooks
  - CI status verification before pushes
  - Verification scripts for task completion

#### Installation & Setup
- **Interactive optional agent selection** during `devloop init`
  - Snyk, Code Rabbit, CI Monitor, Pyodide sandbox
  - Poetry extras for dependency management
  - Non-interactive mode support

- **Comprehensive installation testing guide**
  - Multi-environment testing procedures
  - Installation verification checklist

#### Code Quality
- **Process improvements** to prevent CI failures
  - Auto-format with Black before commits
  - Ruff linting enforcement
  - Type checking with mypy

### Changed

- **Hybrid sandbox architecture** for secure agent execution
  - Default: Bubblewrap for native speed
  - Optional: Pyodide WASM for maximum security
  - Configurable sandbox policies

- **Improved `devloop summary` command**
  - Better devloop directory detection
  - Context directory inference
  - Operational health section

### Documentation

- **AGENTS.md enhancements**: Beads integration, sandbox security, publishing guidelines
- **Risk assessment updates**: Sandbox security, resource limits, audit logging
- **Installation automation guide**: `devloop init` deep dive

### Fixed

- Poetry.lock sync with pyproject.toml extras
- Ruff linting errors in extract-findings-to-beads hook
- Type annotations for CI compliance
- Interactive prompts in non-interactive test environments

---

## [0.2.2] - 2025-12-01

### ⚠️ ALPHA SOFTWARE NOTICE
This is research-quality software. Not recommended for production use. See [Risk Assessment](./history/RISK_ASSESSMENT.md) for details on known limitations and risks.

### Fixed
- **Unbounded Disk Growth**: Implement automatic log rotation and context cleanup
  - RotatingFileHandler: 10MB per file, keep 3 backups (40MB max logs)
  - Automatic context cleanup: Remove findings older than 7 days
  - Automatic event cleanup: Remove events older than 30 days
  - Background cleanup task runs hourly
  - Prevents silent disk exhaustion from log file growth

### Added
- Comprehensive Risk Assessment document (`history/RISK_ASSESSMENT.md`)
  - 7 major risk categories, 17 identified risks
  - CRITICAL risks: subprocess sandboxing, auto-fix safety
  - HIGH risks: resource limits, audit logging, race conditions
  - 20 tracked mitigation tasks in beads
- Risk Fix Progress tracking (`history/RISK_FIX_PROGRESS.md`)
  - Complete task list with priorities
  - Implementation roadmap

### Changed
- **README**: Updated with clear alpha software warnings
  - Badge changed from "production ready" to "alpha"
  - Added prominent ⚠️ warning section
  - Listed known limitations and risks
  - Clarified use cases (suitable for research/side projects only)
  - Set `autonomousFixes.enabled` default to `false`
  - Added auto-fix safety warnings
  - Improved troubleshooting with recovery steps

### Documentation
- Added pre-start disclaimer in Quick Start
- Added recovery procedures for unexpected file modifications
- Added issue reporting guidance
- Clarified that some agents may fail silently

---

## [0.2.1] - 2025-12-01

### Fixed
- **Log Rotation**: Configure log rotation in agents.json to prevent unbounded disk usage
  - Logs now rotate at 100MB with compression
  - Old logs (>7 days) automatically cleaned up
  - Added LOG_ROTATION.md documentation with configuration examples

### Added
- Publishing & Security Considerations guide in AGENTS.md
  - Secrets management best practices
  - Version consistency requirements
  - Breaking changes documentation
  - Dependency security guidelines
  - Pre-release checklist

### Improved
- Installation instructions: Added PyPI installation option to README
- Agent documentation: Enhanced with public software considerations

---

## [0.2.0] - 2025-11-29

### Changed - Project Rename: dev-agents → DevLoop
**BREAKING CHANGE:** Complete project rename from "dev-agents"/"Dev Agents" to "devloop"/"DevLoop"

#### Package & Installation
- Python package: `dev_agents` → `devloop`
- PyPI package name: `dev-agents` → `devloop`
- CLI command: `dev-agents` → `devloop`
- Version: 0.1.0 → 0.2.0

#### Configuration & Directories
- Config directory: `.dev-agents/` → `.devloop/`
- All path references updated throughout codebase

#### Migration Required
- Users must reinstall: `pip uninstall dev-agents && pip install devloop`
- Update all imports: `from dev_agents` → `from devloop`
- Update CLI commands: `dev-agents` → `devloop`
- Rename config directory: `mv .dev-agents .devloop`

#### Files Modified
- 616 occurrences across 75 files
- All Python imports updated
- All documentation updated (25+ markdown files)
- All configuration files updated (pyproject.toml, setup.py)
- All string references in code updated
- All test mocks updated

#### Testing
- All 167 tests passing after rename
- Full regression testing completed

---

## [0.1.0] - 2025-11-28

### Added - Context Store Implementation

**Date:** November 28, 2025

#### Core Features
- Three-tier progressive disclosure system (immediate/relevant/background/auto_fixed)
- Finding-based API with structured metadata
- Relevance scoring based on file scope, severity, and freshness
- LLM-driven surfacing at natural trigger points
- Local-first architecture (all data stays on machine)

#### Files Created
- `src/devloop/core/context_store.py` (530 lines) - Complete context store implementation
- `tests/unit/core/test_context_store.py` (500+ lines) - Comprehensive test suite
- `.devloop/context/` directory structure for storing findings

#### Integration
- All agents (linter, formatter, test-runner, security-scanner) integrated with context store
- Claude Code integration via `.devloop/AGENT_STATUS.md` proactive checking
- Context reader module for querying findings

#### Testing
- 22 unit tests covering finding validation, operations, relevance scoring, and tier assignment
- All tests passing

---

## [0.0.3] - 2025-10

### Added - Learning & Optimization

**Focus:** Transformed system from reactive automation to intelligent learning assistant

#### Feedback System
- Thumbs up/down, 1-5 star ratings, comments, dismiss actions
- Persistent JSONL-based storage with efficient querying
- Real-time agent performance and feedback analysis
- Feedback API for collecting and analyzing developer responses

#### Performance Optimization
- Resource monitoring (CPU, memory, disk I/O, network)
- Performance metrics (execution time, success rates, resource consumption)
- Optimization engine with debouncing, concurrency limits, and caching
- Health monitoring and trend analysis
- Historical performance data and forecasting

#### Custom Agent Framework
- Template system for common agent patterns
- Dynamic loading of agents from Python files
- Agent factory with dependency injection
- Agent marketplace for sharing and discovery
- Built-in templates for file watching, command running, data processing

#### New Modules
- `src/devloop/core/feedback.py` (200+ lines)
- `src/devloop/core/performance.py` (250+ lines)
- `src/devloop/core/agent_template.py` (300+ lines)
- `src/devloop/core/contextual_feedback.py` - Developer action tracking
- `src/devloop/core/proactive_feedback.py` - Proactive feedback engine
- `src/devloop/cli/phase3_commands.py` (150+ lines)

#### Enhanced Features
- Enhanced Agent Manager with feedback and performance integration
- CLI commands for learning and custom agent features
- Backward compatibility (existing agents work without modification)
- Automatic injection of feedback and performance systems

---

## [0.0.2] - 2025-10

### Added - Production Agents

**Focus:** Implemented production-ready agents with full configuration support

#### Agents Implemented

**1. LinterAgent** (`src/devloop/agents/linter.py`)
- Multi-language support (Python/ruff, JavaScript/TypeScript/eslint)
- Configurable file patterns
- Auto-fix capability
- JSON output parsing
- Error handling and tool detection

**2. FormatterAgent** (`src/devloop/agents/formatter.py`)
- Multi-language formatting (Python/black, JavaScript/prettier, Go/gofmt)
- Configurable formatting rules
- Auto-format on save option
- Integration with context store

**3. TestRunnerAgent** (`src/devloop/agents/test_runner.py`)
- Multi-framework support (pytest, jest, go test)
- Related tests detection
- Watch mode support
- Test result parsing and reporting

**4. SecurityScannerAgent** (`src/devloop/agents/security_scanner.py`)
- Bandit integration for Python security scanning
- Configurable severity and confidence thresholds
- Security finding categorization
- Integration with context store

**5. TypeCheckerAgent** (`src/devloop/agents/type_checker.py`)
- Static type checking (mypy, pyright, pyre)
- Configurable strict mode
- Error code display
- Exclude pattern support

**6. AgentHealthMonitorAgent** (`src/devloop/agents/agent_health_monitor.py`)
- Monitors agent execution health
- Failure pattern detection
- Resource usage tracking

**7. GitCommitAssistantAgent** (`src/devloop/agents/git_commit_assistant.py`)
- Analyzes staged changes
- Suggests commit messages based on conventions
- Template support for commit message formatting

**8. PerformanceProfilerAgent** (`src/devloop/agents/performance_profiler.py`)
- Profiles Python code execution
- Identifies performance bottlenecks
- Generates performance reports

#### Configuration System
- JSON-based configuration (`.devloop/agents.json`)
- Per-agent enable/disable
- Configurable triggers
- Agent-specific configuration options

---

## [0.0.1] - 2025-10 (Prototype)

### Added - Foundation & Prototype

**Focus:** Minimal working prototype with core architecture

#### Core Architecture
- Event-driven system with `EventBus`
- Base `Agent` class with async lifecycle
- `AgentManager` for agent coordination
- File system monitoring with watchdog
- Git hook integration
- Process monitoring

#### Core Modules
- `src/devloop/core/agent.py` - Base agent implementation
- `src/devloop/core/event.py` - Event system
- `src/devloop/core/manager.py` - Agent management
- `src/devloop/core/config.py` - Configuration management
- `src/devloop/collectors/filesystem.py` - File system monitoring
- `src/devloop/collectors/git.py` - Git event collection

#### CLI
- `devloop init` - Initialize project
- `devloop watch` - Start agent system
- `devloop status` - Show configuration

#### Demonstration
- EchoAgent prototype for testing
- Basic event routing
- Configuration loading
- Test suite foundation

#### Testing
- Unit test framework
- Core functionality tests
- Integration test setup

---

## Project Milestones

### November 28, 2025
- **Project Rename:** claude-agents → devloop
- **Repository:** https://github.com/wioota/devloop
- **Context Store:** Complete implementation with all agents integrated
- **Tests:** 96 tests passing (up from 22 originally)

### October 2025
- **Learning & Optimization Features** — Pattern recognition, performance tracking, custom agents
- **Production Agents** — Security scanner, performance profiler, doc lifecycle
- **Foundation & Prototype** — Core agents, event system, configuration

---

## Version History Summary

| Version | Date | Description | Tests | Lines of Code |
|---------|------|-------------|-------|---------------|
| 0.1.0 | 2025-11-28 | Context Store + Rename | 96 | ~3,400 |
| 0.0.3 | 2025-10 | Learning & Optimization | 67+ | ~3,000 |
| 0.0.2 | 2025-10 | Production Agents | 40+ | ~2,500 |
| 0.0.1 | 2025-10 | Foundation & Prototype | 22 | ~1,500 |

---

## Future Plans

See [PUBLISHING_PLAN.md](./PUBLISHING_PLAN.md) for:
- Public release roadmap
- PyPI publishing
- Documentation completion
- Community building

See [DOC_LIFECYCLE_AGENT_SPEC.md](./DOC_LIFECYCLE_AGENT_SPEC.md) for:
- Automated documentation management
- Archive organization
- Lifecycle automation
