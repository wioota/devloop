# Changelog

All notable changes to devloop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

## [0.0.3] - 2025-10 (Phase 3)

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
- CLI commands for all Phase 3 features
- Backward compatibility (existing agents work without modification)
- Automatic injection of feedback and performance systems

---

## [0.0.2] - 2025-10 (Phase 2)

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

## [0.0.1] - 2025-10 (Phase 1/Prototype)

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
- **Phase 3 Complete:** Learning & Optimization
- **Phase 2 Complete:** Production Agents
- **Phase 1 Complete:** Foundation & Prototype

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
