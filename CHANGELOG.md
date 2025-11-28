# Changelog

All notable changes to dev-agents will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- Project renamed from `claude-agents` to `dev-agents` (November 28, 2025)
- GitHub repository renamed to `wioota/dev-agents`
- Package name changed to `dev-agents`
- CLI command changed to `dev-agents`

### Fixed
- Fixed IndentationError in `type_checker.py` preventing test execution (November 28, 2025)
- Type safety improvements across multiple agents (`any` → `Any`, added `Optional`)

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
- `src/dev_agents/core/context_store.py` (530 lines) - Complete context store implementation
- `tests/unit/core/test_context_store.py` (500+ lines) - Comprehensive test suite
- `.claude/context/` directory structure for storing findings

#### Integration
- All agents (linter, formatter, test-runner, security-scanner) integrated with context store
- Claude Code integration via `.claude/AGENT_STATUS.md` proactive checking
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
- `src/dev_agents/core/feedback.py` (200+ lines)
- `src/dev_agents/core/performance.py` (250+ lines)
- `src/dev_agents/core/agent_template.py` (300+ lines)
- `src/dev_agents/core/contextual_feedback.py` - Developer action tracking
- `src/dev_agents/core/proactive_feedback.py` - Proactive feedback engine
- `src/dev_agents/cli/phase3_commands.py` (150+ lines)

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

**1. LinterAgent** (`src/dev_agents/agents/linter.py`)
- Multi-language support (Python/ruff, JavaScript/TypeScript/eslint)
- Configurable file patterns
- Auto-fix capability
- JSON output parsing
- Error handling and tool detection

**2. FormatterAgent** (`src/dev_agents/agents/formatter.py`)
- Multi-language formatting (Python/black, JavaScript/prettier, Go/gofmt)
- Configurable formatting rules
- Auto-format on save option
- Integration with context store

**3. TestRunnerAgent** (`src/dev_agents/agents/test_runner.py`)
- Multi-framework support (pytest, jest, go test)
- Related tests detection
- Watch mode support
- Test result parsing and reporting

**4. SecurityScannerAgent** (`src/dev_agents/agents/security_scanner.py`)
- Bandit integration for Python security scanning
- Configurable severity and confidence thresholds
- Security finding categorization
- Integration with context store

**5. TypeCheckerAgent** (`src/dev_agents/agents/type_checker.py`)
- Static type checking (mypy, pyright, pyre)
- Configurable strict mode
- Error code display
- Exclude pattern support

**6. AgentHealthMonitorAgent** (`src/dev_agents/agents/agent_health_monitor.py`)
- Monitors agent execution health
- Failure pattern detection
- Resource usage tracking

**7. GitCommitAssistantAgent** (`src/dev_agents/agents/git_commit_assistant.py`)
- Analyzes staged changes
- Suggests commit messages based on conventions
- Template support for commit message formatting

**8. PerformanceProfilerAgent** (`src/dev_agents/agents/performance_profiler.py`)
- Profiles Python code execution
- Identifies performance bottlenecks
- Generates performance reports

#### Configuration System
- JSON-based configuration (`.claude/agents.json`)
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
- `src/dev_agents/core/agent.py` - Base agent implementation
- `src/dev_agents/core/event.py` - Event system
- `src/dev_agents/core/manager.py` - Agent management
- `src/dev_agents/core/config.py` - Configuration management
- `src/dev_agents/collectors/filesystem.py` - File system monitoring
- `src/dev_agents/collectors/git.py` - Git event collection

#### CLI
- `dev-agents init` - Initialize project
- `dev-agents watch` - Start agent system
- `dev-agents status` - Show configuration

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
- **Project Rename:** claude-agents → dev-agents
- **Repository:** https://github.com/wioota/dev-agents
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
