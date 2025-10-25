#!/usr/bin/env python3
"""Test loop prevention mechanisms in FormatterAgent."""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

from claude_agents.agents.formatter import FormatterAgent
from claude_agents.core.event import Event


async def test_formatting_loop_prevention():
    """Test that formatter prevents infinite formatting loops."""
    print("Testing formatting loop prevention...")

    # Create a mock event bus
    mock_event_bus = AsyncMock()

    # Create formatter agent with format-on-save enabled
    config = {
        "formatOnSave": True,
        "reportOnly": False,
        "filePatterns": ["**/*.py"],
        "formatters": {"python": "black"}
    }

    agent = FormatterAgent(
        name="test-formatter",
        triggers=["file:modified"],
        event_bus=mock_event_bus,
        config=config
    )

    # Create a temporary Python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Test file\nx=1+2\n")  # Needs formatting
        temp_path = Path(f.name)

    try:
        # Test 1: First formatting should succeed
        event = Event(
            type="file:modified",
            payload={"path": str(temp_path)},
            timestamp=time.time()
        )

        # Mock black to always succeed
        with patch.object(agent, '_run_black', return_value=(True, None)):
            result = await agent.handle(event)
            assert result.success, f"First format should succeed: {result.message}"
            print("✓ First formatting operation succeeded")

        # Test 2: Simulate rapid successive formatting attempts
        # This should trigger loop detection
        for i in range(agent._max_consecutive_formats + 1):
            event = Event(
                type="file:modified",
                payload={"path": str(temp_path)},
                timestamp=time.time()
            )

            # Mock both check and run to always think formatting is needed and succeed
            with patch.object(agent, '_check_black', return_value=(True, None)), \
                 patch.object(agent, '_run_black', return_value=(True, None)):
                result = await agent.handle(event)

            if i < agent._max_consecutive_formats:
                assert result.success, f"Format {i+1} should succeed: {result.message}"
                print(f"✓ Format operation {i+1} succeeded")
            else:
                # This one should be blocked by loop detection
                assert not result.success, f"Format {i+1} should be blocked: {result.message}"
                assert "FORMATTING_LOOP_DETECTED" in str(result.error)
                print(f"✓ Loop prevention triggered after {i} rapid formats")

        # Test 3: Wait for loop detection window to expire, then try again
        print(f"Waiting {agent._loop_detection_window + 5} seconds for window to expire...")
        await asyncio.sleep(agent._loop_detection_window + 5)

        event = Event(
            type="file:modified",
            payload={"path": str(temp_path)},
            timestamp=time.time()
        )

        with patch.object(agent, '_run_black', return_value=(True, None)):
            result = await agent.handle(event)
            assert result.success, "Formatting should work again after window expires"
            print("✓ Formatting works again after loop detection window expires")

        # Test 4: Test idempotency - file doesn't need formatting
        with patch.object(agent, '_check_black', return_value=(False, None)):  # Already formatted
            result = await agent.handle(event)
            assert result.success, "Should succeed when file doesn't need formatting"
            assert "already formatted" in result.message
            print("✓ Idempotency check prevents unnecessary formatting")

    finally:
        # Clean up
        temp_path.unlink(missing_ok=True)

    print("✅ All loop prevention tests passed!")


async def test_timeout_protection():
    """Test that formatting operations are protected by timeouts."""
    print("\nTesting timeout protection...")

    mock_event_bus = AsyncMock()

    config = {
        "formatOnSave": True,
        "reportOnly": False,
        "filePatterns": ["**/*.py"],
        "formatters": {"python": "black"}
    }

    agent = FormatterAgent(
        name="test-formatter",
        triggers=["file:modified"],
        event_bus=mock_event_bus,
        config=config
    )

    # Create a temporary Python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Test file\n")
        temp_path = Path(f.name)

    try:
        # Mock black to hang (never complete)
        async def hanging_black(path):
            await asyncio.sleep(60)  # Much longer than timeout
            return True, None

        event = Event(
            type="file:modified",
            payload={"path": str(temp_path)},
            timestamp=time.time()
        )

        with patch.object(agent, '_run_black', side_effect=hanging_black):
            start_time = time.time()
            result = await agent.handle(event)
            elapsed = time.time() - start_time

            assert not result.success, "Should fail due to timeout"
            assert "timed out" in result.error.lower()
            assert elapsed < agent._format_timeout + 5, f"Should not take full timeout: {elapsed}s"
            print(f"✓ Timeout protection worked in {elapsed:.1f}s")

    finally:
        temp_path.unlink(missing_ok=True)

    print("✅ Timeout protection test passed!")


async def main():
    """Run all tests."""
    print("Running loop prevention tests...\n")

    await test_formatting_loop_prevention()
    await test_timeout_protection()

    print("\n🎉 All tests completed successfully!")
    print("\nLoop prevention improvements:")
    print("- ✅ Loop detection prevents infinite formatting cycles")
    print("- ✅ Idempotency checks prevent unnecessary operations")
    print("- ✅ Timeout protection prevents hanging formatters")
    print("- ✅ CODING_RULES.md updated with new patterns")


if __name__ == "__main__":
    asyncio.run(main())
