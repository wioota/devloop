#!/usr/bin/env python3
"""Quick scan of the current codebase with all agents."""

import asyncio
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from devloop.agents import (
    LinterAgent,
    FormatterAgent,
    TypeCheckerAgent,
    SecurityScannerAgent,
    TestRunnerAgent,
    PerformanceProfilerAgent,
)
from devloop.core import EventBus, context_store

async def scan():
    """Run all agents on the codebase."""
    repo_root = Path(__file__).parent
    
    # Initialize context store
    context_store.context_dir = repo_root / ".claude" / "context"
    await context_store.initialize()
    
    # Create event bus
    event_bus = EventBus()
    
    agents_config = {
        "linter": LinterAgent("linter", ["file:scan"], event_bus, {"reportOnly": True}),
        "formatter": FormatterAgent("formatter", ["file:scan"], event_bus, {"reportOnly": True}),
        "type_checker": TypeCheckerAgent("type_checker", ["file:scan"], event_bus, {"reportOnly": True}),
        "security_scanner": SecurityScannerAgent("security_scanner", ["file:scan"], event_bus, {"reportOnly": True}),
        "test_runner": TestRunnerAgent("test_runner", ["file:scan"], event_bus, {}),
        "performance_profiler": PerformanceProfilerAgent("performance_profiler", ["file:scan"], event_bus, {}),
    }
    
    print("🔍 Scanning codebase for issues...\n")
    
    # Scan Python files
    python_files = list(repo_root.glob("**/*.py"))
    python_files = [f for f in python_files if ".venv" not in str(f) and "venv" not in str(f) and "__pycache__" not in str(f) and ".git" not in str(f)]
    
    print(f"Found {len(python_files)} Python files to scan")
    
    # Run linter on Python files
    print("\n📝 Running linter...")
    for py_file in python_files[:20]:  # Limit to 20 files for speed
        result = await agents_config["linter"].execute({"file": str(py_file), "event_type": "file:scan"})
        if result.findings:
            print(f"  Found {len(result.findings)} issues in {py_file.name}")
    
    # Run type checker
    print("\n🔍 Running type checker...")
    result = await agents_config["type_checker"].execute({"file": str(repo_root / "src"), "event_type": "file:scan"})
    if result.findings:
        print(f"  Found {len(result.findings)} type issues")
    
    # Run security scanner
    print("\n🔒 Running security scanner...")
    for py_file in python_files[:20]:
        result = await agents_config["security_scanner"].execute({"file": str(py_file), "event_type": "file:scan"})
        if result.findings:
            print(f"  Found {len(result.findings)} security issues in {py_file.name}")
    
    # Run tests
    print("\n✅ Running tests...")
    result = await agents_config["test_runner"].execute({"file": str(repo_root), "event_type": "file:scan"})
    if result.findings:
        print(f"  Found {len(result.findings)} test issues")
    else:
        print(f"  Tests passed!")
    
    # Load and display findings
    print("\n📊 Summary:")
    await context_store.load_from_disk()
    
    immediate = context_store.findings.get("immediate", {})
    relevant = context_store.findings.get("relevant", {})
    background = context_store.findings.get("background", {})
    
    print(f"  🚨 Immediate issues: {len(immediate.get('findings', []))}")
    print(f"  ⚠️  Relevant issues: {len(relevant.get('findings', []))}")
    print(f"  ℹ️  Background items: {len(background.get('findings', []))}")
    
    print("\n✓ Scan complete!")

if __name__ == "__main__":
    asyncio.run(scan())
