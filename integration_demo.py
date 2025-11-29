#!/usr/bin/env python3
"""
Comprehensive integration demo showing all collectors working together.
This demonstrates the full Claude Agents system in action.
"""
import asyncio
import sys
import tempfile
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from devloop.core.event import Event, EventBus
from devloop.collectors import CollectorManager
from devloop.agents.echo import EchoAgent
from devloop.agents.linter import LinterAgent
from devloop.agents.formatter import FormatterAgent
from devloop.agents.test_runner import TestRunnerAgent


async def integration_demo():
    """Comprehensive demo of all collectors and agents working together."""
    print("🚀 Claude Agents - Full Integration Demo")
    print("=" * 70)
    print("This demo shows all collectors monitoring different event sources")
    print("and agents (Echo + Linter + Formatter + TestRunner) responding to events in real-time.\n")

    # Create event bus and collector manager
    event_bus = EventBus()
    collector_manager = CollectorManager(event_bus)

    # Create all available collectors
    print("📡 Setting up collectors...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Filesystem collector
        fs_config = {"watch_paths": [tmpdir]}
        collector_manager.create_collector("filesystem", fs_config)
        print("✓ Filesystem collector configured")

        # Process collector
        collector_manager.create_collector("process")
        print("✓ Process collector configured")

        # System collector
        system_config = {"check_interval": 10}  # Check every 10 seconds for demo
        collector_manager.create_collector("system", system_config)
        print("✓ System collector configured")

        # Git collector (if in git repo)
        if (Path(tmpdir).parent / ".git").exists():
            collector_manager.create_collector("git")
            print("✓ Git collector configured")
        else:
            print("⚠ Git collector skipped (not in git repository)")

        # Create demo agents
        print("\n🤖 Setting up agents...")

        agents = []

        # Echo agent for all events
        echo = EchoAgent("echo", ["file:*", "process:*", "git:*", "system:*"], event_bus)
        agents.append(echo)
        print("✓ Echo agent configured")

        # Linter agent for Python files
        linter = LinterAgent(
            "linter",
            ["file:created", "file:modified"],
            event_bus,
            config={
                "autoFix": False,
                "filePatterns": ["**/*.py"],
                "linters": {"python": "ruff"}
            }
        )
        agents.append(linter)
        print("✓ Linter agent configured")

        # Formatter agent for Python files
        formatter = FormatterAgent(
            "formatter",
            ["file:modified"],
            event_bus,
            config={
                "formatOnSave": True,
                "filePatterns": ["**/*.py"],
                "formatters": {"python": "black"}
            }
        )
        agents.append(formatter)
        print("✓ Formatter agent configured")

        # Test runner agent for Python files
        test_runner = TestRunnerAgent(
            "test_runner",
            ["file:modified"],
            event_bus,
            config={
                "runOnSave": True,
                "relatedTestsOnly": False,
                "testFrameworks": {"python": "pytest"}
            }
        )
        agents.append(test_runner)
        print("✓ Test runner agent configured")

        # Subscribe to agent results
        result_queue = asyncio.Queue()
        await event_bus.subscribe("agent:echo:completed", result_queue)
        await event_bus.subscribe("agent:linter:completed", result_queue)
        await event_bus.subscribe("agent:formatter:completed", result_queue)
        await event_bus.subscribe("agent:test_runner:completed", result_queue)

        # Start everything
        print("\n▶️  Starting all systems...")
        await collector_manager.start_all()

        for agent in agents:
            await agent.start()
            print(f"✓ {agent.name} agent started")

        print("\n📊 System Status:")
        status = collector_manager.get_status()
        for name, info in status.items():
            state = "Running" if info['running'] else "Stopped"
            print(f"  {name}: {state}")

        print(f"\n🎯 Monitoring directory: {tmpdir}")
        print("Watch the events flow in real-time!\n")

        # Demo 1: File operations
        print("📁 Demo 1: File Operations")
        print("-" * 30)

        test_files = []

        # Create files
        for i in range(1, 4):
            test_file = tmppath / f"test_file_{i}.py"
            # Add some actual Python code with potential issues for agents to catch
            content = f"""# Test file {i}
def hello_world():
    print('Hello from test file {i}!')
    return "success"

if __name__ == "__main__":
    result = hello_world()
    print(f"Result: {{result}}")
"""
            test_file.write_text(content)
            test_files.append(test_file)
            print(f"  📝 Created: {test_file.name} ({len(content)} chars)")
            # Give agents time to process each file creation
            await asyncio.sleep(2.0)

        # Create a test file for the test runner
        test_test_file = tmppath / "test_demo.py"
        test_content = """# Test file for demo
def add_numbers(a, b):
    return a + b

def test_add_numbers():
    assert add_numbers(2, 3) == 5
    assert add_numbers(0, 0) == 0

def test_add_negative():
    assert add_numbers(-1, 1) == 0
    assert add_numbers(-5, 5) == 0

if __name__ == "__main__":
    test_add_numbers()
    test_add_negative()
    print("All tests passed!")
"""
        test_test_file.write_text(test_content)
        test_files.append(test_test_file)
        print(f"  🧪 Created test file: {test_test_file.name}")
        await asyncio.sleep(2.0)

        # Modify a file to add some code issues that agents could catch
        print("\n  🔧 Modifying file to add linting issues...")
        await asyncio.sleep(0.5)
        modified_content = """# Test file 1 - Modified
def hello_world():
    print('Hello from modified test file 1!')
    unused_variable = "this should trigger a linting warning"
    return "success"

def another_function( x,y ):  # Missing spaces around parameters
    return x + y  # This might trigger style warnings

if __name__ == "__main__":
    result = hello_world()
    print(f"Result: {result}")
"""
        test_files[0].write_text(modified_content)
        print(f"  ✏️  Modified: {test_files[0].name} (added code issues)")

        # Give agents more time to process the modification
        print("  ⏳ Waiting for agents to process events...")
        await asyncio.sleep(3.0)

        # Demo 2: Process monitoring
        print("\n⚙️  Demo 2: Process Monitoring")
        print("-" * 30)

        # Run some processes that the collector should monitor
        processes_to_run = [
            ["python3", "-c", "print('Quick Python script')"],
            ["python3", "-c", "import time; time.sleep(0.5); print('Slower script done')"],
        ]

        if collector_manager.get_collector("process") and collector_manager.get_collector("process").is_running:
            print("  Running sample processes...")
            for cmd in processes_to_run:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        cwd=tmpdir
                    )
                    print(f"  ▶️  Ran: {' '.join(cmd)} (exit code: {result.returncode})")
                except subprocess.TimeoutExpired:
                    print(f"  ⏰ Process timed out: {' '.join(cmd)}")
                except FileNotFoundError:
                    print(f"  ⚠️  Command not found: {cmd[0]}")

                await asyncio.sleep(0.5)
        else:
            print("  ⚠️  Process collector not available (psutil not installed)")

        # Demo 3: Event summary
        print("\n📊 Demo 3: Event Processing Summary")
        print("-" * 30)

        # Collect all the results
        print("📊 Collecting agent results...")
        results = []
        try:
            while True:
                result = result_queue.get_nowait()
                results.append(result)
                agent_name = result.payload.get('agent_name', 'unknown')
                message = result.payload.get('message', 'no message')
                print(f"  🤖 {agent_name}: {message}")
        except asyncio.QueueEmpty:
            pass

        print(f"✅ Collected {len(results)} agent results")

        # Group results by agent
        agent_results = {}
        for result in results:
            agent_name = result.payload.get('agent_name', 'unknown')
            if agent_name not in agent_results:
                agent_results[agent_name] = []
            agent_results[agent_name].append(result)

        for agent_name, agent_res in agent_results.items():
            print(f"  🤖 {agent_name}: {len(agent_res)} events")

        # Show sample events
        if results:
            print("\n📋 Sample Events:")
            for i, result in enumerate(results[:5], 1):  # Show first 5
                agent = result.payload.get('agent_name', 'unknown')
                message = result.payload.get('message', 'No message')
                success = result.payload.get('success', False)
                duration = result.payload.get('duration', 0)
                status = "✅" if success else "❌"
                print(f"  {i}. {status} {agent}: {message[:60]}... ({duration:.2f}s)")

        # Final status
        print("\n🏁 Demo Complete!")
        print("=" * 70)

        final_status = collector_manager.get_status()
        running_collectors = sum(1 for info in final_status.values() if info['running'])
        print(f"✅ All {running_collectors} collectors remained stable")
        print(f"✅ Processed {len(results)} events successfully")
        print(f"✅ {len(agents)} agents handled events in real-time")

        # Cleanup
        print("\n🧹 Shutting down...")
        for agent in agents:
            await agent.stop()

        await collector_manager.stop_all()
        print("✓ All systems stopped cleanly")


async def main():
    """Run the integration demo."""
    try:
        await integration_demo()
        print("\n🎉 Integration demo completed successfully!")
        print("\nNext steps:")
        print("  • Try the quick demo: python quick_demo.py")
        print("  • Run full demo: python demo.py")
        print("  • Watch a directory: python -m devloop.cli.main watch /path/to/dir")
        return 0
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
