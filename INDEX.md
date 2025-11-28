# Claude Agents - Documentation Index

**Complete guide to all documentation in this project**

## 🚀 Getting Started (Start Here!)

New to Claude Agents? Start with these:

1. **[PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)** ⭐
   - Complete overview of what was built
   - Architecture and features
   - Quick stats and status

2. **[GETTING_STARTED.md](./GETTING_STARTED.md)** ⭐
   - Installation instructions
   - Quick start guide
   - Troubleshooting
   - Real examples

3. **[README_v2.md](./README_v2.md)** ⭐
   - User-friendly introduction
   - Feature overview
   - Usage examples
   - Configuration guide

## 📖 User Documentation

For using Claude Agents:

- **[COMMANDS.md](./COMMANDS.md)** - Complete CLI command reference
- **[QUICKSTART.md](./QUICKSTART.md)** - Quick start without Poetry
- **[README.md](./README.md)** - Original prototype README

## 📋 Planning & Specifications

Comprehensive system design:

- **[CLAUDE.md](./CLAUDE.md)** - Main system specification
  - Overview and principles
  - 20+ planned agents across 7 categories
  - System architecture
  - Implementation phases
  - Configuration examples

- **[agent-types.md](./agent-types.md)** - Detailed agent specifications
  - Complete specs for all planned agents
  - Configuration schemas per agent
  - Behavior descriptions
  - Lifecycle hooks

- **[event-system.md](./event-system.md)** - Event architecture
  - Event types catalog (filesystem, git, process, etc.)
  - Event collectors
  - Event dispatcher
  - Performance patterns
  - Error handling

- **[configuration-schema.md](./configuration-schema.md)** - Configuration reference
  - Complete JSON schema
  - Agent-specific configs
  - Global configuration
  - Environment variables
  - Example configurations

- **[INTERACTION_MODEL.md](./INTERACTION_MODEL.md)** - Interaction patterns
  - Developer ↔ Agent interactions
  - Coding Agent (Claude Code/Amp) ↔ Background Agent
  - Agent ↔ Agent communication
  - Usage scenarios and examples

- **[TECH_STACK.md](./TECH_STACK.md)** - Technology decisions
  - Framework analysis (8 options)
  - Final decision: Python + Pydantic
  - Dependency justification
  - Implementation recommendations

## 🏗️ Implementation Guides

For developers building or extending the system:

- **[IMPLEMENTATION.md](./IMPLEMENTATION.md)** - Implementation roadmap
  - Complete project structure
  - 12-week implementation plan
  - Code samples for core components
  - Phase-by-phase breakdown

- **[PROTOTYPE_STATUS.md](./PROTOTYPE_STATUS.md)** - Prototype status
  - What works in the prototype
  - Architecture validation
  - Next steps from prototype

- **[PHASE2_COMPLETE.md](./PHASE2_COMPLETE.md)** - Phase 2 summary
  - Three production agents built
  - Features and capabilities
  - Configuration system
  - Usage examples
  - What's next

## 📊 Status & Progress

Current state of the project:

- **[STATUS.md](./STATUS.md)** - Overall project status
  - What's implemented
  - Statistics
  - Quick start instructions
  - Next phase options

- **[PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)** - Complete summary
  - Full accomplishments
  - Architecture diagrams
  - Metrics and statistics
  - Future vision

## 📁 Files by Category

### Core Documentation (What to Read)

| File | Purpose | Audience |
|------|---------|----------|
| PROJECT_SUMMARY.md | Complete overview | Everyone |
| GETTING_STARTED.md | Installation & setup | Users |
| README_v2.md | Feature guide | Users |
| COMMANDS.md | CLI reference | Users |
| PHASE2_COMPLETE.md | Phase 2 status | Developers |

### Specification Documents (Reference)

| File | Purpose | Audience |
|------|---------|----------|
| CLAUDE.md | System spec | Architects |
| agent-types.md | Agent specs | Developers |
| event-system.md | Event architecture | Developers |
| configuration-schema.md | Config reference | Users/Devs |
| INTERACTION_MODEL.md | Interaction patterns | Architects |
| TECH_STACK.md | Technology decisions | Architects |
| IMPLEMENTATION.md | Implementation guide | Developers |

### Status Documents (Progress Tracking)

| File | Purpose | Audience |
|------|---------|----------|
| STATUS.md | Current status | Everyone |
| PROTOTYPE_STATUS.md | Prototype status | Developers |
| INDEX.md | This file | Everyone |

## 🗂️ Navigation Guide

### I want to...

**...understand what Claude Agents is:**
→ Read [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)

**...install and use it:**
→ Follow [GETTING_STARTED.md](./GETTING_STARTED.md)

**...see what features exist:**
→ Check [README_v2.md](./README_v2.md)

**...learn the CLI commands:**
→ Reference [COMMANDS.md](./COMMANDS.md)

**...understand the architecture:**
→ Study [CLAUDE.md](./CLAUDE.md)

**...see all planned agents:**
→ Browse [agent-types.md](./agent-types.md)

**...understand events:**
→ Read [event-system.md](./event-system.md)

**...configure agents:**
→ Reference [configuration-schema.md](./configuration-schema.md)

**...integrate with Claude Code:**
→ See [INTERACTION_MODEL.md](./INTERACTION_MODEL.md)

**...understand tech choices:**
→ Review [TECH_STACK.md](./TECH_STACK.md)

**...implement new features:**
→ Follow [IMPLEMENTATION.md](./IMPLEMENTATION.md)

**...see what's done:**
→ Check [PHASE2_COMPLETE.md](./PHASE2_COMPLETE.md)

**...know current status:**
→ Read [STATUS.md](./STATUS.md)

## 📚 Reading Order

### For New Users

1. [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) - Get overview (5 min)
2. [README_v2.md](./README_v2.md) - See features (10 min)
3. [GETTING_STARTED.md](./GETTING_STARTED.md) - Install & use (15 min)
4. [COMMANDS.md](./COMMANDS.md) - Learn commands (10 min)

**Total**: ~40 minutes to get started

### For Developers

1. [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) - Overview (5 min)
2. [CLAUDE.md](./CLAUDE.md) - System architecture (20 min)
3. [IMPLEMENTATION.md](./IMPLEMENTATION.md) - Implementation guide (30 min)
4. [agent-types.md](./agent-types.md) - Agent details (30 min)
5. [event-system.md](./event-system.md) - Event system (20 min)
6. [PHASE2_COMPLETE.md](./PHASE2_COMPLETE.md) - Current state (10 min)

**Total**: ~2 hours to understand system

### For Architects

1. [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) - Overview (5 min)
2. [TECH_STACK.md](./TECH_STACK.md) - Tech decisions (20 min)
3. [CLAUDE.md](./CLAUDE.md) - System architecture (20 min)
4. [INTERACTION_MODEL.md](./INTERACTION_MODEL.md) - Interactions (30 min)
5. [event-system.md](./event-system.md) - Event architecture (20 min)

**Total**: ~1.5 hours to understand architecture

## 🔍 Quick Reference

### Installation

```bash
# See: GETTING_STARTED.md
python3 -m venv .venv
source .venv/bin/activate
pip install -e /home/wioot/dev/dev-agents
```

### Basic Usage

```bash
# See: COMMANDS.md
dev-agents init
dev-agents watch
```

### Configuration

```bash
# See: configuration-schema.md
# Edit: .claude/agents.json
```

## 📊 Documentation Statistics

| Category | Files | Lines | Words |
|----------|-------|-------|-------|
| User Guides | 5 | ~2,000 | ~15,000 |
| Specifications | 7 | ~4,000 | ~30,000 |
| Status Reports | 3 | ~500 | ~4,000 |
| **Total** | **15** | **~6,500** | **~49,000** |

## 🎯 Documentation Principles

All docs follow these principles:

1. **User-first** - Written for the reader, not the writer
2. **Examples-driven** - Show, don't just tell
3. **Complete** - Cover all scenarios
4. **Organized** - Easy to navigate
5. **Up-to-date** - Maintained as code changes

## 🔄 Keeping Docs Current

When code changes:

1. Update relevant specs (agent-types.md, event-system.md, etc.)
2. Update implementation guide (IMPLEMENTATION.md)
3. Update user docs (README_v2.md, GETTING_STARTED.md)
4. Update status (PHASE2_COMPLETE.md, STATUS.md)
5. Update this index if new docs added

## 📝 Contributing to Docs

To add new documentation:

1. Create the file in project root
2. Add to appropriate category in this index
3. Add to "I want to..." section
4. Add to reading order if applicable
5. Update statistics

## ⚡ Quick Links

### Most Important Docs
- [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) - Complete overview
- [GETTING_STARTED.md](./GETTING_STARTED.md) - Installation guide
- [PHASE2_COMPLETE.md](./PHASE2_COMPLETE.md) - What's built

### For Specific Tasks
- Configure agents → [configuration-schema.md](./configuration-schema.md)
- Learn commands → [COMMANDS.md](./COMMANDS.md)
- Troubleshoot → [GETTING_STARTED.md](./GETTING_STARTED.md#troubleshooting)
- Extend system → [IMPLEMENTATION.md](./IMPLEMENTATION.md)

---

**Last Updated**: October 25, 2024
**Total Docs**: 15 files
**Total Words**: ~49,000
**Total Lines**: ~6,500

---

**Need help finding something?** Check the "I want to..." section above!
