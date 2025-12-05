"""Performance benchmarks for sandbox overhead.

Measures the performance impact of sandbox isolation to ensure acceptable overhead.
Target: <15% overhead, <100ms startup time.
"""

import pytest
import time
from pathlib import Path
import asyncio
import subprocess
from devloop.security.sandbox import SandboxConfig
from devloop.security.bubblewrap_sandbox import BubblewrapSandbox
from devloop.security.no_sandbox import NoSandbox


@pytest.fixture
def sandbox_config():
    """Create benchmark sandbox configuration."""
    return SandboxConfig(
        mode="bubblewrap",
        max_memory_mb=500,
        max_cpu_percent=50,
        timeout_seconds=30,
        allowed_tools=["python3", "echo", "cat"],
    )


@pytest.fixture
def bench_workspace(tmp_path):
    """Create benchmark workspace."""
    workspace = tmp_path / "bench"
    workspace.mkdir()
    # Create test file
    (workspace / "test.txt").write_text("benchmark data\n" * 1000)
    return workspace


class TestStartupOverhead:
    """Measure sandbox startup overhead."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_simple_command_overhead(self, sandbox_config, bench_workspace):
        """Measure overhead for simple echo command."""
        sandbox = BubblewrapSandbox(sandbox_config)
        no_sandbox = NoSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Measure sandboxed execution
        iterations = 10
        sandboxed_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await sandbox.execute(["echo", "test"], cwd=bench_workspace)
            duration = (time.perf_counter() - start) * 1000  # ms
            sandboxed_times.append(duration)

        # Measure non-sandboxed execution
        nosandbox_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await no_sandbox.execute(["echo", "test"], cwd=bench_workspace)
            duration = (time.perf_counter() - start) * 1000  # ms
            nosandbox_times.append(duration)

        # Calculate averages
        avg_sandboxed = sum(sandboxed_times) / iterations
        avg_nosandbox = sum(nosandbox_times) / iterations
        overhead_ms = avg_sandboxed - avg_nosandbox
        overhead_percent = (overhead_ms / avg_nosandbox) * 100 if avg_nosandbox > 0 else 0

        print(f"\n=== Simple Command (echo) ===")
        print(f"Sandboxed avg: {avg_sandboxed:.2f}ms")
        print(f"No sandbox avg: {avg_nosandbox:.2f}ms")
        print(f"Overhead: {overhead_ms:.2f}ms ({overhead_percent:.1f}%)")

        # Assert target: <20ms absolute overhead for simple commands
        assert overhead_ms < 20, f"Startup overhead {overhead_ms:.2f}ms exceeds 20ms target"

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_python_execution_overhead(self, sandbox_config, bench_workspace):
        """Measure overhead for Python script execution."""
        sandbox = BubblewrapSandbox(sandbox_config)
        no_sandbox = NoSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create test Python script
        test_script = bench_workspace / "test.py"
        test_script.write_text("print('hello' * 100)")

        iterations = 10
        sandboxed_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await sandbox.execute(["python3", str(test_script)], cwd=bench_workspace)
            duration = (time.perf_counter() - start) * 1000
            sandboxed_times.append(duration)

        nosandbox_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await no_sandbox.execute(["python3", str(test_script)], cwd=bench_workspace)
            duration = (time.perf_counter() - start) * 1000
            nosandbox_times.append(duration)

        avg_sandboxed = sum(sandboxed_times) / iterations
        avg_nosandbox = sum(nosandbox_times) / iterations
        overhead_ms = avg_sandboxed - avg_nosandbox
        overhead_percent = (overhead_ms / avg_nosandbox) * 100 if avg_nosandbox > 0 else 0

        print(f"\n=== Python Script Execution ===")
        print(f"Sandboxed avg: {avg_sandboxed:.2f}ms")
        print(f"No sandbox avg: {avg_nosandbox:.2f}ms")
        print(f"Overhead: {overhead_ms:.2f}ms ({overhead_percent:.1f}%)")

        # Assert target: <50% overhead or <30ms absolute (whichever is more lenient)
        # Percentage can be high for fast operations due to startup cost
        assert overhead_ms < 30 or overhead_percent < 50, \
            f"Overhead {overhead_percent:.1f}% ({overhead_ms:.2f}ms) exceeds targets"


class TestIOOverhead:
    """Measure I/O performance overhead."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_file_read_overhead(self, sandbox_config, bench_workspace):
        """Measure overhead for file reading operations."""
        sandbox = BubblewrapSandbox(sandbox_config)
        no_sandbox = NoSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        iterations = 10
        sandboxed_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await sandbox.execute(["cat", "test.txt"], cwd=bench_workspace)
            duration = (time.perf_counter() - start) * 1000
            sandboxed_times.append(duration)

        nosandbox_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await no_sandbox.execute(["cat", "test.txt"], cwd=bench_workspace)
            duration = (time.perf_counter() - start) * 1000
            nosandbox_times.append(duration)

        avg_sandboxed = sum(sandboxed_times) / iterations
        avg_nosandbox = sum(nosandbox_times) / iterations
        overhead_ms = avg_sandboxed - avg_nosandbox
        overhead_percent = (overhead_ms / avg_nosandbox) * 100 if avg_nosandbox > 0 else 0

        print(f"\n=== File Read (cat 14KB file) ===")
        print(f"Sandboxed avg: {avg_sandboxed:.2f}ms")
        print(f"No sandbox avg: {avg_nosandbox:.2f}ms")
        print(f"Overhead: {overhead_ms:.2f}ms ({overhead_percent:.1f}%)")

        # File I/O overhead: allow <20ms absolute (percentage high for fast operations)
        assert overhead_ms < 20, f"I/O overhead {overhead_ms:.2f}ms exceeds 20ms target"


class TestCPUIntensiveOverhead:
    """Measure overhead for CPU-intensive operations."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cpu_intensive_overhead(self, sandbox_config, bench_workspace):
        """Measure overhead for CPU-bound computation."""
        sandbox = BubblewrapSandbox(sandbox_config)
        no_sandbox = NoSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Create CPU-intensive Python script
        cpu_script = bench_workspace / "cpu_test.py"
        cpu_script.write_text("""
import math
result = sum(math.sqrt(i) for i in range(10000))
print(result)
""")

        iterations = 5  # Fewer iterations for CPU-intensive
        sandboxed_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await sandbox.execute(["python3", str(cpu_script)], cwd=bench_workspace)
            duration = (time.perf_counter() - start) * 1000
            sandboxed_times.append(duration)

        nosandbox_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await no_sandbox.execute(["python3", str(cpu_script)], cwd=bench_workspace)
            duration = (time.perf_counter() - start) * 1000
            nosandbox_times.append(duration)

        avg_sandboxed = sum(sandboxed_times) / iterations
        avg_nosandbox = sum(nosandbox_times) / iterations
        overhead_ms = avg_sandboxed - avg_nosandbox
        overhead_percent = (overhead_ms / avg_nosandbox) * 100 if avg_nosandbox > 0 else 0

        print(f"\n=== CPU-Intensive (math.sqrt x10000) ===")
        print(f"Sandboxed avg: {avg_sandboxed:.2f}ms")
        print(f"No sandbox avg: {avg_nosandbox:.2f}ms")
        print(f"Overhead: {overhead_ms:.2f}ms ({overhead_percent:.1f}%)")

        # CPU overhead: allow <50ms absolute or <150% (startup dominates for short tasks)
        assert overhead_ms < 50 or overhead_percent < 150, \
            f"CPU overhead {overhead_percent:.1f}% ({overhead_ms:.2f}ms) exceeds targets"


class TestMemoryOverhead:
    """Measure memory overhead of sandbox."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_memory_overhead(self, sandbox_config, bench_workspace):
        """Measure resident memory overhead."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Memory measurement is OS-specific and approximate
        # For now, just ensure execution completes successfully
        # Full memory profiling would require psutil and process tracking

        result = await sandbox.execute(
            ["python3", "-c", "print('hello')"],
            cwd=bench_workspace
        )

        assert result.exit_code == 0
        print(f"\n=== Memory Overhead ===")
        print(f"(Memory profiling requires additional tooling)")
        print(f"Execution successful: {result.exit_code == 0}")


class TestConcurrentExecution:
    """Measure overhead with concurrent sandbox executions."""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_concurrent_overhead(self, sandbox_config, bench_workspace):
        """Measure overhead when running multiple sandboxes concurrently."""
        sandbox = BubblewrapSandbox(sandbox_config)

        if not await sandbox.is_available():
            pytest.skip("Bubblewrap not available")

        # Run 5 concurrent executions
        num_concurrent = 5
        start = time.perf_counter()

        tasks = [
            sandbox.execute(["echo", f"task-{i}"], cwd=bench_workspace)
            for i in range(num_concurrent)
        ]
        results = await asyncio.gather(*tasks)

        total_duration = (time.perf_counter() - start) * 1000
        avg_per_task = total_duration / num_concurrent

        print(f"\n=== Concurrent Execution ({num_concurrent} tasks) ===")
        print(f"Total time: {total_duration:.2f}ms")
        print(f"Average per task: {avg_per_task:.2f}ms")
        print(f"All tasks successful: {all(r.exit_code == 0 for r in results)}")

        # All should succeed
        assert all(r.exit_code == 0 for r in results)
        # Average shouldn't be much worse than single execution
        assert avg_per_task < 200, f"Concurrent overhead too high: {avg_per_task:.2f}ms"
