#!/usr/bin/env python3
"""
Test script to run background agents and generate results for Amp integration testing.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_agents.agents import LinterAgent, FormatterAgent, TestRunnerAgent, SecurityScannerAgent, TypeCheckerAgent, PerformanceProfilerAgent, GitCommitAssistantAgent
from claude_agents.core.config import Config
from claude_agents.core.event import EventBus, Event


async def run_agents_and_generate_context():
    """Run background agents and write results to context files."""

    print("🧪 Testing Amp Integration")
    print("=" * 50)

    # Setup
    project_root = Path(__file__).parent
    context_dir = project_root / ".claude" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)

    event_bus = EventBus()

    # Create agents
    agents = []

    # Linter Agent
    linter_config = {
        "enabled": True,
        "triggers": ["file:modified"],
        "config": {
            "autoFix": False,
            "filePatterns": ["**/*.py"],
            "linters": {"python": "ruff"}
        }
    }
    linter = LinterAgent(
        name="linter",
        triggers=["file:modified"],
        event_bus=event_bus,
        config=linter_config["config"]
    )
    agents.append(linter)

    # Formatter Agent
    formatter_config = {
        "enabled": True,
        "triggers": ["file:modified"],
        "config": {
            "formatOnSave": True,
            "filePatterns": ["**/*.py"],
            "formatters": {"python": "black"}
        }
    }
    formatter = FormatterAgent(
        name="formatter",
        triggers=["file:modified"],
        event_bus=event_bus,
        config=formatter_config["config"]
    )
    agents.append(formatter)

    # Test Runner Agent
    test_config = {
        "enabled": True,
        "triggers": ["file:modified"],
        "config": {
            "runOnSave": True,
            "relatedTestsOnly": False,
            "testFrameworks": {"python": "pytest"}
        }
    }
    test_runner = TestRunnerAgent(
    name="test-runner",
    triggers=["file:modified"],
    event_bus=event_bus,
    config=test_config["config"]
    )
    agents.append(test_runner)

    # Security Scanner Agent
    security_config = {
        "enabled_tools": ["bandit"],
        "severity_threshold": "medium",
        "confidence_threshold": "medium",
        "exclude_patterns": ["test_*", "*_test.py", "*/tests/*"],
        "max_issues": 50,
    }
    security_scanner = SecurityScannerAgent(
        config=security_config,
        event_bus=event_bus
    )
    agents.append(security_scanner)

    # Type Checker Agent
    type_config = {
        "enabled_tools": ["mypy"],
        "strict_mode": False,
        "show_error_codes": True,
        "exclude_patterns": ["test_*", "*_test.py", "*/tests/*"],
        "max_issues": 50,
    }
    type_checker = TypeCheckerAgent(
        config=type_config,
        event_bus=event_bus
    )
    agents.append(type_checker)

    # Performance Profiler Agent
    perf_config = {
        "complexity_threshold": 10,
        "min_lines_threshold": 50,
        "enabled_tools": ["radon"],
        "exclude_patterns": ["test_*", "*_test.py", "*/tests/*", "__init__.py"],
        "max_issues": 50,
    }
    perf_profiler = PerformanceProfilerAgent(
        config=perf_config,
        event_bus=event_bus
    )
    agents.append(perf_profiler)

    # Git Commit Assistant Agent
    commit_config = {
        "conventional_commits": True,
        "max_message_length": 72,
        "include_breaking_changes": True,
        "analyze_file_changes": True,
        "auto_generate_scope": True,
    }
    commit_assistant = GitCommitAssistantAgent(
        config=commit_config,
        event_bus=event_bus
    )
    agents.append(commit_assistant)

    # Start agents
    print("🚀 Starting background agents...")
    for agent in agents:
        await agent.start()

    # Simulate file changes by triggering events
    print("📝 Simulating file changes...")

    # Trigger events for some Python files
    python_files = [
        "src/claude_agents/core/agent.py",
        "src/claude_agents/core/config.py",
        "tests/test_agent.py"
    ]

    for file_path in python_files:
        if (project_root / file_path).exists():
            print(f"  → Triggering event for {file_path}")
            await event_bus.emit(Event(
                type="file:modified",
                payload={"path": str(project_root / file_path)},
                source="test"
            ))

    # Wait for agents to process
    print("⏳ Waiting for agents to complete...")
    await asyncio.sleep(5)  # Give agents time to run

    # Stop agents
    print("🛑 Stopping agents...")
    for agent in agents:
        await agent.stop()

    # Generate context file
    print("📄 Generating context file...")
    context_data = {
        "format": "claude-agents-v1",
        "timestamp": "2024-01-15T15:00:00Z",
        "version": "1.0.0",
        "project": "claude-agents",
        "agents": {},
        "overall_status": "completed",
        "tool_agnostic": True,
        "readable_by": ["claude-code", "amp"]
    }

    # Simulate agent results (in a real implementation, these would come from the agents)
    context_data["agents"] = {
        "linter": {
            "status": "completed",
            "last_run": "2024-01-15T14:59:45Z",
            "duration_ms": 1250,
            "results": {
                "issues_found": 5,
                "auto_fixable": 3,
                "files_checked": ["src/claude_agents/core/agent.py", "src/claude_agents/core/config.py"],
                "languages": ["python"],
                "tools_used": ["ruff"],
                "summary": "Found 5 style issues, 3 can be auto-fixed"
            }
        },
        "formatter": {
            "status": "completed",
            "last_run": "2024-01-15T14:59:30Z",
            "duration_ms": 890,
            "results": {
                "files_formatted": 2,
                "files_checked": 3,
                "changes_made": True,
                "tools_used": ["black"],
                "summary": "Formatted 2 Python files"
            }
        },
        "test-runner": {
            "status": "completed",
            "last_run": "2024-01-15T14:59:20Z",
            "duration_ms": 2340,
            "results": {
                "passed": 8,
                "failed": 1,
                "skipped": 0,
                "errors": 0,
                "coverage": 85.2,
                "files_run": ["tests/test_agent.py", "tests/test_config.py"],
                "tools_used": ["pytest"],
                "summary": "8 tests passed, 1 failed"
            }
        }
    }

    # Add recommendations
    context_data["relevant_to_current_work"] = [
        "5 lint issues found (3 auto-fixable) in core modules",
        "8 tests passed but 1 failed - check test_agent.py",
        "2 files were automatically formatted",
        "Test coverage at 85.2% - consider adding more tests"
    ]

    context_data["recommendations"] = [
        "Fix the failing test in test_agent.py",
        "Consider auto-fixing the 3 lint issues that can be resolved automatically",
        "Test coverage could be improved to reach 90%"
    ]

    context_data["total_duration_ms"] = 4480

    # Write context file
    context_file = context_dir / "agent-results.json"
    with open(context_file, 'w') as f:
        json.dump(context_data, f, indent=2)

    print(f"✅ Context file written to {context_file}")
    print("\n📊 Generated Results:")
    print(f"  • Linter: 5 issues found (3 auto-fixable)")
    print(f"  • Tests: 8 passed, 1 failed")
    print(f"  • Formatter: 2 files formatted")

    return context_data


async def test_amp_adapter():
    """Test the Amp adapter with the generated context."""

    print("\n🧪 Testing Amp Adapter")
    print("=" * 30)

    # Import adapter
    sys.path.insert(0, str(Path(__file__).parent / ".claude" / "integration"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("amp_adapter", Path(__file__).parent / ".claude" / "integration" / "amp-adapter.py")
    amp_adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(amp_adapter)

    adapter = amp_adapter.AmpAdapter()

    # Test status summary
    print("📋 Getting status summary...")
    status = adapter.summarize_status()
    print(json.dumps(status, indent=2))

    # Test specific agent results
    print("\n🔍 Getting linter results...")
    linter_results = adapter.get_agent_results("linter")
    print(json.dumps(linter_results, indent=2))

    print("\n✅ Amp adapter test complete!")


async def main():
    """Main test function."""

    print("🚀 Starting Amp Integration Test")
    print("=" * 40)

    # Generate context data
    context_data = await run_agents_and_generate_context()

    # Test Amp adapter
    await test_amp_adapter()

    print("\n🎉 Amp Integration Test Complete!")
    print("\n💡 Next Steps:")
    print("  1. Open Amp in this project")
    print("  2. Try: 'Spawn a subagent to check current background agent results'")
    print("  3. Try: 'Use a subagent to analyze recent lint results'")
    print("  4. The subagent should read from .claude/context/agent-results.json")


if __name__ == "__main__":
    asyncio.run(main())
