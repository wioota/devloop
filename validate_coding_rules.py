#!/usr/bin/env python3
"""
Coding Rules Validator for Claude Agents

Validates that code follows the established coding rules and patterns.
This script is automatically run during development to ensure consistency.
"""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import re


class CodingRulesValidator:
    """Validates code against established coding rules."""

    def __init__(self):
        self.violations: List[Dict[str, Any]] = []
        self.file_path: Optional[Path] = None

    def validate_file(self, file_path: Path) -> bool:
        """Validate a single file against coding rules."""
        if isinstance(file_path, str):
            file_path = Path(file_path)
        self.file_path = file_path
        self.violations = []

        if not file_path.exists():
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the AST for structural analysis
            tree = ast.parse(content, filename=str(file_path))

            # Run all validation checks
            self._check_imports(content, tree)
            self._check_async_error_handling(tree)
            self._check_dataclass_usage(tree)
            self._check_path_handling(content)
            self._check_logging_usage(tree)
            self._check_agent_result_usage(tree)

            return len(self.violations) == 0

        except SyntaxError as e:
            self._add_violation("syntax_error", f"Syntax error: {e}", line=e.lineno)
            return False
        except Exception as e:
            self._add_violation("parse_error", f"Failed to parse file: {e}")
            return False

    def _add_violation(self, rule: str, message: str, line: Optional[int] = None, severity: str = "warning"):
        """Add a coding rule violation."""
        self.violations.append({
            "rule": rule,
            "message": message,
            "file": str(self.file_path),
            "line": line,
            "severity": severity
        })

    def _check_imports(self, content: str, tree: ast.AST) -> None:
        """Check import patterns (Rule #6: Safe imports)."""
        # Check for unsafe imports of optional dependencies
        optional_tools = ["bandit", "mypy", "radon", "ruff", "black"]

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in optional_tools:
                        self._add_violation(
                            "unsafe_import",
                            f"Direct import of optional tool '{alias.name}' - use safe imports",
                            line=node.lineno,
                            severity="error"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module in optional_tools:
                    self._add_violation(
                        "unsafe_import",
                        f"Direct import from optional module '{node.module}' - use safe imports",
                        line=node.lineno,
                        severity="error"
                    )

    def _check_async_error_handling(self, tree: ast.AST) -> None:
        """Check async error handling (Rule #3: Async error handling)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                # Check if function has try-except block
                has_try_except = any(
                    isinstance(child, ast.Try)
                    for child in ast.walk(node)
                    if child != node  # Don't count nested functions
                )

                if not has_try_except:
                    self._add_violation(
                        "missing_error_handling",
                        f"Async function '{node.name}' missing try-except block",
                        line=node.lineno,
                        severity="warning"
                    )

    def _check_dataclass_usage(self, tree: ast.AST) -> None:
        """Check dataclass configuration usage (Rule #2: Configuration validation)."""
        # Look for configuration classes that should be dataclasses
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it's a config class
                if "config" in node.name.lower() and not any(
                    decorator.id == "dataclass" if isinstance(decorator, ast.Name) else False
                    for decorator in node.decorator_list
                ):
                    # Check if it has __post_init__
                    has_post_init = any(
                        isinstance(item, ast.FunctionDef) and item.name == "__post_init__"
                        for item in node.body
                    )

                    if not has_post_init:
                        self._add_violation(
                            "missing_dataclass",
                            f"Config class '{node.name}' should use @dataclass with __post_init__ validation",
                            line=node.lineno,
                            severity="warning"
                        )

    def _check_path_handling(self, content: str) -> None:
        """Check path handling patterns (Rule #4: Path handling)."""
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            # Check for string path operations that should use Path
            if re.search(r'[a-zA-Z_][a-zA-Z0-9_]*\s*[\+\\/]\s*[\'\"]', line):
                if 'Path(' not in line and '.resolve()' not in line:
                    self._add_violation(
                        "unsafe_path_operation",
                        "Path operation should use Path objects with resolve()",
                        line=i,
                        severity="warning"
                    )

    def _check_logging_usage(self, tree: ast.AST) -> None:
        """Check logging patterns (Rule #8: Logging standards)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if agent class has proper logging setup
                if "Agent" in node.name:
                    has_logger = any(
                        isinstance(item, ast.Assign) and
                        any(target.id == "logger" for target in item.targets if isinstance(target, ast.Name))
                        for item in node.body
                    )

                    if not has_logger:
                        self._add_violation(
                            "missing_logger",
                            f"Agent class '{node.name}' should have structured logging",
                            line=node.lineno,
                            severity="warning"
                        )

    def _check_agent_result_usage(self, tree: ast.AST) -> None:
        """Check AgentResult usage (Rule #5: Result consistency)."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                # Check if returning dict that should be AgentResult
                if isinstance(node.value, ast.Dict):
                    # Look for agent result patterns
                    keys = []
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant):
                            keys.append(key.value)

                    if "agent_name" in keys and "success" in keys:
                        # This looks like it should be an AgentResult
                        self._add_violation(
                            "use_agent_result",
                            "Return statement should use AgentResult object instead of dict",
                            line=node.lineno,
                            severity="info"
                        )

    def print_report(self) -> None:
        """Print validation report."""
        if not self.violations:
            print("✅ All coding rules validated successfully!")
            return

        print(f"❌ Found {len(self.violations)} coding rule violations:")
        print()

        for violation in self.violations:
            severity_icon = {
                "error": "🔴",
                "warning": "🟡",
                "info": "ℹ️"
            }.get(violation["severity"], "❓")

            line_info = f" (line {violation['line']})" if violation.get("line") else ""
            print(f"{severity_icon} {violation['rule']}: {violation['message']}{line_info}")

        print()
        print("📖 Refer to CODING_RULES.md for detailed guidelines")


def main():
    """Main validation script."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate coding rules")
    parser.add_argument("files", nargs="*", help="Files to validate")
    parser.add_argument("--all", action="store_true", help="Validate all Python files in project")

    args = parser.parse_args()

    if not args.files and not args.all:
        print("Usage: python validate_coding_rules.py [--all] [file1.py file2.py ...]")
        sys.exit(1)

    validator = CodingRulesValidator()
    total_violations = 0

    if args.all:
        # Find all Python files in the project
        project_root = Path.cwd()
        python_files = list(project_root.glob("**/*.py"))

        # Exclude some common directories
        exclude_patterns = ["__pycache__", ".venv", ".git", "node_modules"]
        files_to_check = [
            f for f in python_files
            if not any(pattern in str(f) for pattern in exclude_patterns)
        ]
    else:
        files_to_check = [Path(f) for f in args.files]

    for file_path in files_to_check:
        print(f"🔍 Validating {file_path}...")
        is_valid = validator.validate_file(file_path)
        if not is_valid:
            validator.print_report()
            total_violations += len(validator.violations)
            # Reset violations for next file
            validator.violations = []

    if total_violations == 0:
        print("✅ All files passed coding rules validation!")
        sys.exit(0)
    else:
        print(f"❌ Total violations: {total_violations}")
        sys.exit(1)


if __name__ == "__main__":
    main()
