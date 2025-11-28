#!/usr/bin/env python3
"""
Auto-fix engine for background agent integration.
Provides safe, configurable automatic application of fixes.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

class AutoFixEngine:
    """Engine for safely applying automatic fixes from background agents."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.context_dir = self.project_root / ".claude" / "context"
        self.backup_dir = self.project_root / ".claude" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def get_auto_fixable_issues(self, agent_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all auto-fixable issues from background agents."""

        results_file = self.context_dir / "agent-results.json"
        if not results_file.exists():
            return []

        with open(results_file, 'r') as f:
            data = json.load(f)

        auto_fixable = []

        for agent_name, agent_data in data.get("agents", {}).items():
            if agent_filter and agent_name != agent_filter:
                continue

            results = agent_data.get("results", {})

            # Check for auto-fixable issues based on agent type
            if agent_name == "linter":
                fixes = self._extract_linter_fixes(agent_data, agent_name)
                auto_fixable.extend(fixes)
            elif agent_name == "formatter":
                fixes = self._extract_formatter_fixes(agent_data, agent_name)
                auto_fixable.extend(fixes)

        return auto_fixable

    def apply_auto_fixes(self, fixes: List[Dict[str, Any]],
                        safety_level: str = "safe_only") -> Dict[str, Any]:
        """Apply a list of auto-fixes with safety controls."""

        applied = []
        skipped = []
        errors = []

        for fix in fixes:
            try:
                # Check if fix meets safety requirements
                if not self._is_safe_to_apply(fix, safety_level):
                    skipped.append({
                        "fix": fix,
                        "reason": f"Safety level '{safety_level}' prevents application"
                    })
                    continue

                # Create backup before applying
                backup_id = self._create_backup(fix["file"])

                # Apply the fix
                success = self._apply_single_fix(fix)

                if success:
                    applied.append({
                        "fix": fix,
                        "backup_id": backup_id,
                        "applied_at": datetime.now().isoformat()
                    })
                else:
                    # Restore backup if application failed
                    self._restore_backup(backup_id)
                    errors.append({
                        "fix": fix,
                        "error": "Fix application failed"
                    })

            except Exception as e:
                errors.append({
                    "fix": fix,
                    "error": str(e)
                })

        return {
            "applied": applied,
            "skipped": skipped,
            "errors": errors,
            "summary": {
                "total_fixes": len(fixes),
                "applied_count": len(applied),
                "skipped_count": len(skipped),
                "error_count": len(errors)
            }
        }

    def rollback_fixes(self, applied_fixes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Rollback applied auto-fixes."""

        rolled_back = []
        errors = []

        for applied in applied_fixes:
            try:
                backup_id = applied.get("backup_id")
                if backup_id and self._restore_backup(backup_id):
                    rolled_back.append(applied)
                else:
                    errors.append({
                        "applied": applied,
                        "error": "Backup not found or restore failed"
                    })
            except Exception as e:
                errors.append({
                    "applied": applied,
                    "error": str(e)
                })

        return {
            "rolled_back": rolled_back,
            "errors": errors,
            "summary": {
                "total_rolled_back": len(rolled_back),
                "error_count": len(errors)
            }
        }

    def _extract_linter_fixes(self, agent_data: Dict[str, Any], agent_name: str) -> List[Dict[str, Any]]:
        """Extract auto-fixable lint issues."""

        fixes = []
        results = agent_data.get("results", {})
        details = agent_data.get("details", [])

        auto_fixable_count = results.get("auto_fixable", 0)

        # For demo purposes, mark some issues as auto-fixable
        # In reality, this would be determined by the linter
        for i, detail in enumerate(details):
            if i < auto_fixable_count:  # First N issues are auto-fixable
                fixes.append({
                    "agent": agent_name,
                    "type": "lint_fix",
                    "file": detail["file"],
                    "line": detail["line"],
                    "description": detail["message"],
                    "safety_level": "safe",  # Lint fixes are generally safe
                    "confidence": "high",
                    "estimated_effort": "low"
                })

        return fixes

    def _extract_formatter_fixes(self, agent_data: Dict[str, Any], agent_name: str) -> List[Dict[str, Any]]:
        """Extract formatter fixes."""

        fixes = []
        results = agent_data.get("results", {})
        formatted_files = results.get("formatted_files", [])

        for file_path in formatted_files:
            fixes.append({
                "agent": agent_name,
                "type": "format_fix",
                "file": file_path,
                "description": f"Apply {results.get('tools_used', ['formatter'])} formatting",
                "safety_level": "safe",  # Formatting is generally safe
                "confidence": "high",
                "estimated_effort": "low"
            })

        return fixes

    def _is_safe_to_apply(self, fix: Dict[str, Any], safety_level: str) -> bool:
        """Check if a fix is safe to apply based on safety level."""

        fix_safety = fix.get("safety_level", "unknown")
        confidence = fix.get("confidence", "unknown")

        if safety_level == "safe_only":
            return fix_safety == "safe" and confidence == "high"
        elif safety_level == "medium_risk":
            return fix_safety in ["safe", "medium"] and confidence in ["high", "medium"]
        elif safety_level == "all":
            return True

        return False

    def _create_backup(self, file_path: str) -> str:
        """Create a backup of a file before modifying it."""

        source_path = self.project_root / file_path
        if not source_path.exists():
            raise FileNotFoundError(f"File to backup does not exist: {file_path}")

        # Create backup ID
        timestamp = datetime.now().isoformat()
        file_hash = hashlib.md5(str(source_path).encode()).hexdigest()[:8]
        backup_id = f"{file_hash}_{timestamp.replace(':', '').replace('-', '').replace('.', '_')}"

        # Create backup directory for this file
        backup_file_dir = self.backup_dir / backup_id
        backup_file_dir.mkdir(exist_ok=True)

        # Copy file
        backup_path = backup_file_dir / source_path.name
        shutil.copy2(source_path, backup_path)

        # Store metadata
        metadata = {
            "original_path": str(source_path),
            "backup_path": str(backup_path),
            "timestamp": timestamp,
            "file_hash": file_hash
        }

        with open(backup_file_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f)

        return backup_id

    def _restore_backup(self, backup_id: str) -> bool:
        """Restore a file from backup."""

        backup_file_dir = self.backup_dir / backup_id
        metadata_file = backup_file_dir / "metadata.json"

        if not metadata_file.exists():
            return False

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        original_path = Path(metadata["original_path"])
        backup_path = Path(metadata["backup_path"])

        if backup_path.exists():
            shutil.copy2(backup_path, original_path)
            return True

        return False

    def _apply_single_fix(self, fix: Dict[str, Any]) -> bool:
        """Apply a single fix (simplified implementation)."""

        fix_type = fix.get("type")

        if fix_type == "lint_fix":
            # In a real implementation, this would use the linter's fix functionality
            # For demo, we'll just mark as applied
            return True
        elif fix_type == "format_fix":
            # In a real implementation, this would run the formatter
            # For demo, we'll just mark as applied
            return True

        return False


def main():
    """Command-line interface for the auto-fix engine."""

    import argparse

    parser = argparse.ArgumentParser(description="Auto-fix engine for background agents")
    parser.add_argument("command", choices=["list", "apply", "rollback"])
    parser.add_argument("--agent", help="Filter by specific agent")
    parser.add_argument("--safety", choices=["safe_only", "medium_risk", "all"],
                       default="safe_only", help="Safety level for applying fixes")
    parser.add_argument("--backup-id", help="Backup ID for rollback")

    args = parser.parse_args()

    engine = AutoFixEngine()

    if args.command == "list":
        fixes = engine.get_auto_fixable_issues(args.agent)
        print(json.dumps(fixes, indent=2))

    elif args.command == "apply":
        fixes = engine.get_auto_fixable_issues(args.agent)
        if not fixes:
            print("No auto-fixable issues found")
            return

        result = engine.apply_auto_fixes(fixes, args.safety)
        print(json.dumps(result, indent=2))

    elif args.command == "rollback":
        # For demo, this would need applied fixes list
        print("Rollback functionality requires applied fixes list")
        print("Use: rollback --backup-id <id>")


if __name__ == "__main__":
    main()
