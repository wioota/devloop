#!/usr/bin/env python3
"""Demo script for Phase 3: Learning & Optimization features."""

import asyncio
import tempfile
from pathlib import Path

from dev_agents.agents.linter import LinterAgent
from dev_agents.collectors.filesystem import FileSystemCollector
from dev_agents.core.manager import AgentManager
from dev_agents.core.event import EventBus, Event
from dev_agents.core.feedback import FeedbackType


async def demo_feedback_system():
    """Demonstrate the feedback system."""
    print("🔄 Phase 3 Demo: Learning & Optimization")
    print("=" * 50)

    # Create a temporary directory for the demo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Initialize systems
        event_bus = EventBus()
        manager = AgentManager(event_bus, project_dir=temp_path)

        # Create and register a linter agent
        linter_agent = manager.create_agent(
            LinterAgent,
            name="demo-linter",
            triggers=["file:modified"],
            config={"filePatterns": ["**/*.py"]}
        )

        print("✅ Created agent with feedback and performance monitoring")

        # Start the agent
        await manager.start_all()

        # Create a test file
        test_file = temp_path / "test.py"
        test_file.write_text("""
def hello():
    print("Hello World")

hello()
""")

        # Simulate file modification event
        await event_bus.emit(Event(
            type="file:modified",
            payload={"path": str(test_file)}
        ))

        # Wait for agent to process
        await asyncio.sleep(2)

        # Submit some feedback
        print("\\n📝 Submitting feedback...")

        feedback_id1 = await manager.submit_feedback(
            agent_name="demo-linter",
            feedback_type=FeedbackType.THUMBS_UP,
            value=True,
            event_type="file:modified",
            comment="Agent worked perfectly on this Python file"
        )
        print(f"✅ Submitted thumbs up feedback: {feedback_id1}")

        feedback_id2 = await manager.submit_feedback(
            agent_name="demo-linter",
            feedback_type=FeedbackType.RATING,
            value=5,
            event_type="file:modified",
            comment="Excellent performance and accuracy"
        )
        print(f"✅ Submitted 5-star rating: {feedback_id2}")

        # Get agent insights
        print("\\n📊 Agent Insights:")
        insights = await manager.get_agent_insights("demo-linter")
        if insights:
            perf = insights["performance"]
            print(f"  Total executions: {perf['total_executions']}")
            print(f"  Success rate: {perf['success_rate']}%")
            print(f"  Average duration: {perf['average_duration']}s")
            print(f"  Feedback count: {perf['feedback_count']}")
            print(f"  Thumbs up rate: {perf['thumbs_up_rate']}%")
            print(f"  Average rating: {perf['average_rating']}/5")

        # Get system health
        print("\\n💻 System Health:")
        health = await manager.get_system_health()
        if health:
            proc = health["process"]
            sys = health["system"]
            print(f"  Process CPU: {proc['cpu_percent']}%")
            print(f"  Process Memory: {proc['memory_mb']:.1f} MB")
            print(f"  System CPU: {sys['cpu_percent']}%")
            print(f"  System Memory: {sys['memory_used_gb']:.1f}/{sys['memory_total_gb']:.1f} GB")

        await manager.stop_all()


async def demo_custom_agent_creation():
    """Demonstrate custom agent creation from templates."""
    print("\\n🔧 Custom Agent Creation Demo")
    print("=" * 30)

    from dev_agents.core.agent_template import AgentTemplateRegistry, AgentFactory

    # Initialize template system
    registry = AgentTemplateRegistry()
    factory = AgentFactory(registry)

    # List available templates
    print("📋 Available Templates:")
    templates = registry.list_templates()
    for template in templates:
        print(f"  • {template.name}: {template.description}")

    # Get template details
    file_watcher = registry.get_template("file-watcher")
    if file_watcher:
        print(f"\\n📄 Template: {file_watcher.name}")
        print(f"   Category: {file_watcher.category}")
        print(f"   Triggers: {', '.join(file_watcher.triggers)}")
        print("   Config Schema:")
        for key, value in file_watcher.config_schema.get("properties", {}).items():
            default = value.get("default", "none")
            print(f"     {key}: {default}")

    print("\\n✅ Custom agent framework ready for use!")


async def main():
    """Run all Phase 3 demos."""
    try:
        await demo_feedback_system()
        await demo_custom_agent_creation()

        print("\\n🎉 Phase 3 Demo Complete!")
        print("\\nKey Features Implemented:")
        print("  ✅ Agent behavior learning from developer feedback")
        print("  ✅ Performance monitoring with resource usage analytics")
        print("  ✅ Custom agent creation framework")
        print("  ✅ Feedback collection (thumbs up/down, ratings, comments)")
        print("  ✅ Resource usage tracking (CPU, memory, execution time)")
        print("  ✅ Performance optimization system")
        print("  ✅ Agent template system for easy custom agent creation")
        print("  ✅ Dynamic agent loading from user-defined Python files")
        print("  ✅ Agent marketplace/registry for sharing custom agents")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
