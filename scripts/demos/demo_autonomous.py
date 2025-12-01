#!/usr/bin/env python3
"""Demonstration of autonomous coding agent operation."""

import asyncio
import tempfile
from pathlib import Path

from claude_agents.core.amp_integration import (
    apply_autonomous_fixes,
    check_agent_findings,
    show_agent_status,
)
from claude_agents.core.event import Event, EventBus
from claude_agents.agents.formatter import FormatterAgent


async def create_test_file():
    """Create a test file that needs formatting."""
    # Create a temporary Python file with formatting issues
    content = '''# Test file with formatting issues
x=1+2
def test():
    return 42
'''

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
    temp_file.write(content)
    temp_file.close()

    return Path(temp_file.name)


async def simulate_agent_workflow():
    """Simulate the full autonomous workflow."""
    print("🤖 Autonomous Coding Agent Demo")
    print("=" * 50)

    # Step 1: Create a test file with formatting issues
    print("\n1. Creating test file with formatting issues...")
    test_file = await create_test_file()
    print(f"   Created: {test_file}")

    try:
        # Step 2: Set up formatter agent
        print("\n2. Setting up formatter agent...")
        event_bus = EventBus()
        formatter = FormatterAgent(
            name="formatter",
            triggers=["file:modified"],
            event_bus=event_bus,
            config={
                "formatOnSave": False,  # Report-only mode initially
                "reportOnly": True,
                "filePatterns": ["**/*.py"],
                "formatters": {"python": "black"}
            }
        )

        # Step 3: Agent detects the file change
        print("\n3. Agent detects file change...")
        event = Event(
            type="file:modified",
            payload={"path": str(test_file)},
            timestamp=0
        )

        result = await formatter.handle(event)
        print(f"   Agent result: {result.message}")

        # Step 4: Check agent findings
        print("\n4. Checking agent findings...")
        findings = await check_agent_findings()
        print(f"   Total findings: {findings['summary']['total_findings']}")
        print(f"   Actionable findings: {findings['summary']['actionable_findings']}")

        if findings['actionable_findings']:
            print("   📋 Actionable findings:")
            for agent_type, agent_findings in findings['actionable_findings'].items():
                for finding in agent_findings:
                    print(f"     • {agent_type}: {finding['message']}")

        # Step 5: Autonomous fix application
        print("\n5. Applying autonomous fixes...")
        fix_results = await apply_autonomous_fixes()
        print(f"   Fix results: {fix_results}")

        # Step 6: Verify the fix was applied
        print("\n6. Verifying fix application...")
        with open(test_file, 'r') as f:
            final_content = f.read()

        print("   Final file content:")
        print("   " + "\n   ".join(final_content.split('\n')))

        # Step 7: Check that findings were cleared
        print("\n7. Checking that findings were cleared...")
        final_findings = await check_agent_findings()
        print(f"   Remaining findings: {final_findings['summary']['total_findings']}")

        print("\n✅ Autonomous workflow completed successfully!")

    finally:
        # Clean up
        test_file.unlink(missing_ok=True)


async def show_status_demo():
    """Show the agent status functionality."""
    print("\n📊 Agent Status Demo")
    print("=" * 30)

    status = await show_agent_status()
    print(f"Agent activity: {len(status['agent_activity'])} agents")
    print(f"Pending actions: {sum(status['pending_actions'].values())} total")

    if status['recent_findings']:
        print("\nRecent findings:")
        for agent_type, findings in status['recent_findings'].items():
            print(f"  {agent_type}:")
            for finding in findings[:3]:  # Show first 3
                actionable = " (actionable)" if finding['actionable'] else ""
                print(f"    • {finding['message']}{actionable}")


async def main():
    """Run the autonomous demo."""
    await simulate_agent_workflow()
    await show_status_demo()

    print("\n🎉 Demo complete!")
    print("\nIn real usage, you would:")
    print("• Let background agents run continuously")
    print("• Periodically check 'show_agent_status'")
    print("• Run 'apply_autonomous_fixes' when convenient")
    print("• Only intervene for complex decisions")


if __name__ == "__main__":
    asyncio.run(main())
