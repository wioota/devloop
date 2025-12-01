#!/usr/bin/env python3
"""
Generate test context data for Amp integration testing.
"""

import json
from pathlib import Path
from datetime import datetime

def generate_test_context():
    """Generate realistic test context data."""

    project_root = Path(__file__).parent
    context_dir = project_root / ".claude" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)

    # Generate realistic test results
    context_data = {
        "format": "claude-agents-v1",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "project": "claude-agents",
        "agents": {
            "linter": {
                "status": "completed",
                "last_run": datetime.now().isoformat(),
                "duration_ms": 1250,
                "results": {
                    "issues_found": 5,
                    "auto_fixable": 3,
                    "files_checked": ["src/claude_agents/core/agent.py", "src/claude_agents/core/config.py"],
                    "languages": ["python"],
                    "tools_used": ["ruff"],
                    "summary": "Found 5 style issues, 3 can be auto-fixed"
                },
                "details": [
                    {
                        "file": "src/claude_agents/core/agent.py",
                        "line": 42,
                        "severity": "warning",
                        "message": "Line too long (92 > 88 characters)",
                        "auto_fixable": True
                    },
                    {
                        "file": "src/claude_agents/core/config.py",
                        "line": 67,
                        "severity": "warning",
                        "message": "Unused import",
                        "auto_fixable": True
                    }
                ]
            },
            "formatter": {
                "status": "completed",
                "last_run": datetime.now().isoformat(),
                "duration_ms": 890,
                "results": {
                    "files_formatted": 2,
                    "files_checked": 3,
                    "changes_made": True,
                    "tools_used": ["black"],
                    "summary": "Formatted 2 Python files"
                },
                "formatted_files": [
                    "src/claude_agents/core/agent.py",
                    "src/claude_agents/core/config.py"
                ]
            },
            "test-runner": {
                "status": "completed",
                "last_run": datetime.now().isoformat(),
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
                },
                "failed_tests": [
                    {
                        "file": "tests/test_agent.py",
                        "test": "test_agent_initialization",
                        "error": "AssertionError: expected True, got False"
                    }
                ]
            },
            "security-scanner": {
                "status": "completed",
                "last_run": datetime.now().isoformat(),
                "duration_ms": 1560,
                "results": {
                    "vulnerabilities_found": 0,
                    "warnings": 1,
                    "files_scanned": 12,
                    "tools_used": ["bandit"],
                    "summary": "No security vulnerabilities found"
                },
                "warnings": [
                    {
                        "file": "src/claude_agents/core/agent.py",
                        "line": 89,
                        "severity": "low",
                        "message": "Consider using 'with' statement for file operations"
                    }
                ]
            }
        },
        "overall_status": "completed",
        "total_duration_ms": 5040,
        "relevant_to_current_work": [
            "5 lint issues found (3 auto-fixable) in core modules",
            "8 tests passed but 1 failed - check test_agent.py",
            "2 files were automatically formatted",
            "No security vulnerabilities detected"
        ],
        "recommendations": [
            "Fix the failing test in test_agent.py",
            "Consider auto-fixing the 3 lint issues that can be resolved automatically",
            "Test coverage at 85.2% could be improved"
        ],
        "tool_agnostic": True,
        "readable_by": ["claude-code", "amp"]
    }

    # Write context file
    context_file = context_dir / "agent-results.json"
    with open(context_file, 'w') as f:
        json.dump(context_data, f, indent=2)

    print(f"✅ Generated test context file: {context_file}")
    print("\n📊 Test Results Summary:")
    print("  • Linter: 5 issues (3 auto-fixable)")
    print("  • Tests: 8 passed, 1 failed")
    print("  • Formatter: 2 files formatted")
    print("  • Security: No vulnerabilities")

    return context_data


if __name__ == "__main__":
    generate_test_context()
