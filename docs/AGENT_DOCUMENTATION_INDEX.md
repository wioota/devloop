# Agent Documentation Index

Quick index for all agent-related documentation. Start here to find what you need.

## Getting Started

**New to agent development?** Start here:

1. [Agent Development Guide](./AGENT_DEVELOPMENT.md) - Concepts, lifecycle, and your first agent
   - Learn what agents are and how they work
   - Build your first agent (Echo example)
   - Understand event patterns and configuration
   - Best practices and common patterns

2. [Agent Examples](./AGENT_EXAMPLES.md) - Real-world code examples
   - Simple examples (Echo, File Watcher)
   - Medium examples (Pattern Matcher, Command Runner)
   - Advanced examples (Caching, Batching, Integration)
   - Testing patterns

## Reference

**Need API details?** Look here:

- [Agent API Reference](./AGENT_API_REFERENCE.md) - Complete class and method documentation
  - `Agent` base class
  - `Event` and `EventBus`
  - `AgentResult` structure
  - Built-in agents (LinterAgent, FormatterAgent, etc.)

## Marketplace

**Want to share your agent?** See:

1. [Marketplace Guide](./MARKETPLACE_GUIDE.md) - Publishing and discovery
   - How to search for agents
   - How to install agents
   - How to publish your own agent
   - Agent metadata and requirements

## Troubleshooting

**Something not working?** Check:

- [Agent Troubleshooting](./AGENT_TROUBLESHOOTING.md) - Common issues and solutions
  - Agent not running
  - Agent crashing
  - Performance issues
  - Event handling problems
  - Testing issues
  - Configuration problems

## Quick Links by Task

### I want to...

**...learn what agents are**
→ Read [Agent Development Guide - Core Concepts](./AGENT_DEVELOPMENT.md#core-concepts)

**...create my first agent**
→ Follow [Agent Development Guide - Creating Your First Agent](./AGENT_DEVELOPMENT.md#creating-your-first-agent)

**...see code examples**
→ Check [Agent Examples](./AGENT_EXAMPLES.md)

**...understand the event system**
→ See [Agent Development Guide - Event System](./AGENT_DEVELOPMENT.md#event-system)

**...configure an agent**
→ Read [Agent Development Guide - Configuration](./AGENT_DEVELOPMENT.md#configuration)

**...test my agent**
→ Follow [Agent Development Guide - Testing](./AGENT_DEVELOPMENT.md#testing)

**...find an agent to use**
→ Try [Marketplace Guide - Discovering Agents](./MARKETPLACE_GUIDE.md#discovering-agents)

**...install an agent**
→ See [Marketplace Guide - Installing Agents](./MARKETPLACE_GUIDE.md#installing-agents)

**...publish my agent**
→ Follow [Marketplace Guide - Publishing Your Agent](./MARKETPLACE_GUIDE.md#publishing-your-agent)

**...look up an API**
→ Check [Agent API Reference](./AGENT_API_REFERENCE.md)

**...fix a problem**
→ See [Agent Troubleshooting](./AGENT_TROUBLESHOOTING.md)

**...read about Amp integration**
→ See [guides/AMP_ONBOARDING.md](./guides/AMP_ONBOARDING.md) and [guides/SUBAGENT_REFERENCE.md](./guides/SUBAGENT_REFERENCE.md)

**...understand telemetry**
→ Check [reference/TELEMETRY.md](./reference/TELEMETRY.md)

## Document Summaries

### AGENT_DEVELOPMENT.md
Comprehensive guide covering:
- Core concepts and agent architecture
- Agent lifecycle and state management
- Event system and triggers
- Step-by-step tutorials with code examples
- Configuration patterns
- Best practices and design patterns
- Testing strategies
- Publishing to marketplace

**Read if:** You're creating agents or want to understand how they work

**Length:** ~2,500 lines, ~30-40 minutes

### AGENT_API_REFERENCE.md
Complete API documentation covering:
- `Agent` base class
- `Event` and `EventBus` classes
- `AgentResult` dataclass
- Event types and patterns
- All built-in agents (Linter, Formatter, TypeChecker, etc.)
- Advanced features (monitoring, feedback, resource tracking)

**Read if:** You need API details or method signatures

**Length:** ~800 lines, ~15-20 minutes

### AGENT_EXAMPLES.md
Real-world working code examples:
- Simple examples (Echo, File Watcher)
- Medium examples (Pattern Matcher, Command Runner)
- Advanced examples (Caching, Batching, Integration)
- Testing examples with pytest patterns

**Read if:** You learn best by example

**Length:** ~800 lines, ~15-20 minutes

### MARKETPLACE_GUIDE.md
Guide to agent ecosystem:
- Discovering agents (search, filtering)
- Installing and configuring agents
- Publishing your own agent
- Agent metadata and requirements
- Marketplace policies and quality standards

**Read if:** You want to use or publish agents

**Length:** ~600 lines, ~15-20 minutes

### AGENT_TROUBLESHOOTING.md
Common problems and solutions:
- Agent not running (diagnosis and fixes)
- Agent crashing (error handling)
- Performance issues (optimization)
- Event handling problems
- Testing issues
- Configuration problems
- Installation problems
- Advanced debugging tools

**Read if:** Something's not working as expected

**Length:** ~700 lines, ~20-25 minutes

## Learning Paths

### For Agent Users (just installing agents)
1. [Marketplace Guide - Discovering Agents](./MARKETPLACE_GUIDE.md#discovering-agents)
2. [Marketplace Guide - Installing Agents](./MARKETPLACE_GUIDE.md#installing-agents)
3. [Agent Troubleshooting](./AGENT_TROUBLESHOOTING.md) (as needed)

**Time:** ~10 minutes

### For Agent Developers (creating agents)
1. [Agent Development Guide](./AGENT_DEVELOPMENT.md) - Read completely
2. [Agent Examples](./AGENT_EXAMPLES.md) - Study relevant examples
3. [Agent API Reference](./AGENT_API_REFERENCE.md) - Reference as needed
4. [Agent Troubleshooting](./AGENT_TROUBLESHOOTING.md) - Reference as needed

**Time:** ~2-3 hours

### For Publishing Your Agent
1. [Marketplace Guide - Publishing Your Agent](./MARKETPLACE_GUIDE.md#publishing-your-agent)
2. [Agent Development Guide - Best Practices](./AGENT_DEVELOPMENT.md#best-practices)
3. [Agent Examples](./AGENT_EXAMPLES.md) - See professional structure
4. [Marketplace Guide - Marketplace Policies](./MARKETPLACE_GUIDE.md#marketplace-policies)

**Time:** ~1-2 hours

## Documentation Organization

Docs are organized into categories:

- **Root level** - Agent development (AGENT_*.md, MARKETPLACE_GUIDE.md)
- **guides/** - Usage guides and integration docs
  - AMP_ONBOARDING.md - Amp integration guide
  - DEVELOPER_WORKFLOW.md - Development workflow
  - SUBAGENT_REFERENCE.md - Subagent reference
  - THREAD_HANDOFF.md - Thread handoff procedures
- **analysis/** - Design decisions and analysis documents
  - CLAUDE_CODE_HOOKS_*.md - Code hooks analysis
  - HOOK_OPTIMIZATION_ANALYSIS.md - Hook optimization study
  - SELF_IMPROVEMENT_AGENT_ANALYSIS.md - Agent improvement analysis
- **reference/** - Technical references
  - TELEMETRY.md - Telemetry documentation
- **architecture/** - Architecture and planning
  - ROADMAP.md - Project roadmap

## Related Documentation

Outside of agent development, see:
- [Main README](../README.md) - DevLoop overview
- [AGENTS.md](../AGENTS.md) - System architecture and principles
- [Getting Started Guide](./getting-started.md) - DevLoop installation
- [Configuration Guide](./configuration.md) - Full DevLoop config reference

## FAQ

**Q: What's the difference between an agent and a tool?**
A: See [Agent Development Guide - Core Concepts](./AGENT_DEVELOPMENT.md#core-concepts)

**Q: How do I know what events are available?**
A: See [Agent Development Guide - Event System](./AGENT_DEVELOPMENT.md#event-system)

**Q: Can I use external libraries in my agent?**
A: Yes! Add them to your `pyproject.toml` dependencies. See [Marketplace Guide - Package Configuration](./MARKETPLACE_GUIDE.md#package-configuration)

**Q: How do I test my agent?**
A: See [Agent Development Guide - Testing](./AGENT_DEVELOPMENT.md#testing)

**Q: Where can I get help?**
A: See [Agent Troubleshooting - Getting Help](./AGENT_TROUBLESHOOTING.md#getting-help)

## Version Information

This documentation is for **DevLoop 0.9.0+**

For previous versions, see [Agent Development Guide - Version Compatibility](./AGENT_DEVELOPMENT.md#version-compatibility) (if available)

## Contributing

Found an issue or want to improve the docs?
- Report issues: [GitHub Issues](https://github.com/wioota/devloop/issues)
- Suggest improvements: [Community Forum](https://forum.devloop.dev)
- Submit PRs: [GitHub Pull Requests](https://github.com/wioota/devloop/pulls)
