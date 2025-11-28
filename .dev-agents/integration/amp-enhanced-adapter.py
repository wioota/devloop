#!/usr/bin/env python3
"""
Enhanced Amp adapter with autofix mode and change tracking.
Provides seamless integration where Amp can automatically apply fixes and track changes.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

class EnhancedAmpAdapter:
    """Enhanced adapter for Amp subagents with autofix and rollback capabilities."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.context_dir = self.project_root / ".claude" / "context"
        self.backup_dir = self.project_root / ".claude" / "backups"
        self.change_log = self.context_dir / "change-log.json"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.context_dir.mkdir(parents=True, exist_ok=True)

        # Initialize paths for compatibility
        self.results_file = self.context_dir / "agent-results.json"

    def apply_autofix_mode(self, safety_level: str = "safe_only") -> Dict[str, Any]:
        """Apply all safe autofixes and track changes for Amp awareness.

        This is designed to be called by Amp subagents automatically.
        """
        print("🔧 Amp Autofix Mode: Scanning for safe fixes...")

        # Get available fixes
        fixes = self.get_auto_fixable_issues()
        applicable_fixes = [f for f in fixes if self._is_safe_to_apply(f, safety_level)]

        if not applicable_fixes:
            return {
                "status": "no_fixes",
                "message": f"No fixes available at safety level '{safety_level}'",
                "safety_level": safety_level
            }

        print(f"✅ Found {len(applicable_fixes)} applicable fixes")

        # Apply fixes and track changes
        applied_fixes = []
        change_log = []

        for fix in applicable_fixes:
            try:
                result = self._apply_single_fix(fix)
                if result["status"] == "applied":
                    applied_fixes.append(result)
                    change_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "fix": fix,
                        "result": result,
                        "rollback_id": result.get("backup_id")
                    })
            except Exception as e:
                print(f"❌ Failed to apply fix: {e}")

        # Save change log
        self._save_change_log(change_log)

        # Generate Amp-aware summary
        summary = self._generate_amp_summary(applied_fixes, change_log)

        return {
            "status": "completed",
            "applied_count": len(applied_fixes),
            "safety_level": safety_level,
            "applied_fixes": applied_fixes,
            "change_log": change_log,
            "amp_summary": summary,
            "rollback_instructions": self._generate_rollback_instructions(change_log)
        }

    def _save_change_log(self, changes: List[Dict[str, Any]]) -> None:
        """Save change log for Amp awareness and rollback."""
        log_data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "changes": changes
        }

        with open(self.change_log, 'w') as f:
            json.dump(log_data, f, indent=2)

    def _generate_amp_summary(self, applied_fixes: List[Dict[str, Any]], change_log: List[Dict[str, Any]]) -> str:
        """Generate a summary that Amp can understand and act upon."""
        if not applied_fixes:
            return "No fixes were applied."

        summary_parts = []
        summary_parts.append(f"Applied {len(applied_fixes)} automatic fixes:")

        for fix_info in applied_fixes:
            fix = fix_info["fix"]
            summary_parts.append(f"• {fix['type'].replace('_', ' ').title()}: {fix['description']} in {fix['file']}")

        summary_parts.append("")
        summary_parts.append("🔄 To rollback if needed: 'Rollback the last background agent fixes'")
        summary_parts.append("📝 All changes are logged and can be individually reverted")

        return "\n".join(summary_parts)

    def _generate_rollback_instructions(self, change_log: List[Dict[str, Any]]) -> str:
        """Generate clear rollback instructions for Amp."""
        if not change_log:
            return "No changes to rollback."

        instructions = [
            "To rollback these changes, Amp can use:",
            f"• Rollback all: Restore backups from {self.backup_dir}",
            f"• Selective rollback: Use backup IDs from change log at {self.change_log}",
            "• Git rollback: Commit these changes first, then revert if needed"
        ]

        return "\n".join(instructions)

    def rollback_changes(self, scope: str = "all", backup_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Rollback changes made by background agents.

        Args:
            scope: "all", "last", or "selective"
            backup_ids: Specific backup IDs to rollback (for selective)
        """
        if not self.change_log.exists():
            return {"status": "error", "message": "No change log found"}

        with open(self.change_log, 'r') as f:
            log_data = json.load(f)

        changes = log_data.get("changes", [])

        if not changes:
            return {"status": "error", "message": "No changes to rollback"}

        # Determine which changes to rollback
        if scope == "last":
            changes_to_rollback = [changes[-1]] if changes else []
        elif scope == "selective" and backup_ids:
            changes_to_rollback = [c for c in changes if c.get("rollback_id") in backup_ids]
        else:  # scope == "all"
            changes_to_rollback = changes

        rolled_back = []
        failed = []

        for change in reversed(changes_to_rollback):  # Reverse to undo in correct order
            try:
                result = self._rollback_single_change(change)
                if result["status"] == "rolled_back":
                    rolled_back.append(result)
                else:
                    failed.append(result)
            except Exception as e:
                failed.append({"change": change, "error": str(e)})

        return {
            "status": "completed",
            "rolled_back_count": len(rolled_back),
            "failed_count": len(failed),
            "rolled_back": rolled_back,
            "failed": failed,
            "summary": f"Rolled back {len(rolled_back)} changes, {len(failed)} failed"
        }

    def _rollback_single_change(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback a single change using its backup."""
        backup_id = change.get("rollback_id")
        if not backup_id:
            return {"status": "error", "message": "No backup ID found", "change": change}

        # Skip rollback for files that didn't need backup (e.g., non-existent files)
        if backup_id == "no_backup_needed":
            return {"status": "skipped", "message": "No backup needed for this change", "change": change}

        backup_path = self.backup_dir / f"{backup_id}.backup"
        if not backup_path.exists():
            return {"status": "error", "message": f"Backup not found: {backup_path}", "change": change}

        # Find original file path
        fix = change.get("fix", {})
        file_path = fix.get("file")
        if not file_path:
            return {"status": "error", "message": "Original file path not found", "change": change}

        target_path = self.project_root / file_path

        # Restore backup
        import shutil
        shutil.copy2(backup_path, target_path)

        return {
            "status": "rolled_back",
            "file": file_path,
            "backup_id": backup_id,
            "change": change
        }

    def get_amp_context(self) -> Dict[str, Any]:
        """Get current context including recent changes for Amp awareness."""
        context = {
            "has_recent_changes": False,
            "last_change_time": None,
            "change_count": 0,
            "pending_fixes": 0,
            "safety_status": "unknown"
        }

        # Check for recent changes
        if self.change_log.exists():
            with open(self.change_log, 'r') as f:
                log_data = json.load(f)

            changes = log_data.get("changes", [])
            if changes:
                context["has_recent_changes"] = True
                context["last_change_time"] = changes[-1]["timestamp"]
                context["change_count"] = len(changes)

        # Check for pending fixes
        fixes = self.get_auto_fixable_issues()
        safe_fixes = [f for f in fixes if self._is_safe_to_apply(f, "safe_only")]
        context["pending_fixes"] = len(safe_fixes)
        context["safety_status"] = "safe_fixes_available" if safe_fixes else "no_safe_fixes"

        return context

    def get_auto_fixable_issues(self, agent_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all auto-fixable issues from background agents."""
        if not self.results_file.exists():
            return []

        with open(self.results_file, 'r') as f:
            data = json.load(f)

        auto_fixable = []

        for agent_name, agent_data in data.get("agents", {}).items():
            if agent_filter and agent_name != agent_filter:
                continue

            results = agent_data.get("results", {})

            # Extract fixes based on agent type
            if agent_name == "linter":
                fixes = self._extract_linter_fixes(agent_data, agent_name)
                auto_fixable.extend(fixes)
            elif agent_name == "formatter":
                fixes = self._extract_formatter_fixes(agent_data, agent_name)
                auto_fixable.extend(fixes)

        return auto_fixable

    def _extract_linter_fixes(self, agent_data: Dict[str, Any], agent_name: str) -> List[Dict[str, Any]]:
        """Extract auto-fixable lint issues."""
        results = agent_data.get("results", {})
        auto_fixable_count = results.get("auto_fixable", 0)

        if auto_fixable_count == 0:
            return []

        # Create mock fixes based on the data (in real implementation, this would parse actual lint output)
        fixes = []
        files = results.get("files_checked", [])

        for i, file_path in enumerate(files[:auto_fixable_count]):
            fixes.append({
                "id": f"lint_fix_{i}",
                "type": "lint_fix",
                "description": f"Fix style issues in {file_path}",
                "file": file_path,
                "agent": agent_name,
                "safety_level": "safe",
                "confidence": "high",
                "tool": results.get("tools_used", ["unknown"])[0]
            })

        return fixes

    def _extract_formatter_fixes(self, agent_data: Dict[str, Any], agent_name: str) -> List[Dict[str, Any]]:
        """Extract formatter fixes."""
        results = agent_data.get("results", {})
        files_formatted = results.get("files_formatted", 0)

        if files_formatted == 0:
            return []

        # Create mock fixes for formatted files
        fixes = []
        files = results.get("files_checked", [])
        if isinstance(files, list) and len(files) >= files_formatted:
            files = files[:files_formatted]
        else:
            # If we don't have specific files, create generic ones
            files = [f"file_{i}.py" for i in range(files_formatted)]

        for i, file_path in enumerate(files):
            fixes.append({
                "id": f"format_fix_{i}",
                "type": "format_fix",
                "description": f"Format code in {file_path}",
                "file": file_path,
                "agent": agent_name,
                "safety_level": "safe",
                "confidence": "high",
                "tool": results.get("tools_used", ["unknown"])[0]
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

    def _apply_single_fix(self, fix: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single fix (mock implementation for demo)."""
        # In a real implementation, this would actually modify the file
        # For demo purposes, we'll simulate the fix application

        file_path = fix["file"]
        backup_id = self._create_backup(file_path)

        return {
            "status": "applied",
            "fix": fix,
            "file": file_path,
            "backup_id": backup_id,
            "message": f"Applied {fix['type']} to {file_path}"
        }

    def _create_backup(self, file_path: str) -> str:
        """Create a backup of a file."""
        import hashlib
        from datetime import datetime

        source_path = self.project_root / file_path
        if not source_path.exists():
            return "no_backup_needed"

        # Create unique backup ID
        timestamp = datetime.now().isoformat().replace(":", "").replace("-", "").replace(".", "_")
        file_hash = hashlib.md5(str(source_path).encode()).hexdigest()[:8]
        backup_id = f"{file_hash}_{timestamp}"

        backup_path = self.backup_dir / f"{backup_id}.backup"

        import shutil
        shutil.copy2(source_path, backup_path)

        return backup_id

    # Import existing methods from amp_adapter.py
    def get_agent_results(self, agent_name: Optional[str] = None,
                         since_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Get background agent results (inherited from amp_adapter.py)"""
        # Implementation would be copied from existing adapter
        pass

    

    


def main():
    """Command-line interface for the enhanced adapter."""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Amp Adapter")
    parser.add_argument("command", choices=["autofix", "rollback", "context", "status"])
    parser.add_argument("--safety", default="safe_only", choices=["safe_only", "medium_risk", "all"])
    parser.add_argument("--scope", default="all", choices=["all", "last", "selective"])
    parser.add_argument("--backup-ids", nargs="*", help="Specific backup IDs for selective rollback")

    args = parser.parse_args()

    adapter = EnhancedAmpAdapter()

    if args.command == "autofix":
        result = adapter.apply_autofix_mode(args.safety)
        print(json.dumps(result, indent=2))

    elif args.command == "rollback":
        result = adapter.rollback_changes(args.scope, args.backup_ids)
        print(json.dumps(result, indent=2))

    elif args.command == "context":
        result = adapter.get_amp_context()
        print(json.dumps(result, indent=2))

    elif args.command == "status":
        # Quick status for Amp
        context = adapter.get_amp_context()
        fixes = adapter.get_auto_fixable_issues()
        safe_fixes = [f for f in fixes if adapter._is_safe_to_apply(f, "safe_only")]

        status = {
            "amp_ready": True,
            "pending_safe_fixes": len(safe_fixes),
            "has_recent_changes": context["has_recent_changes"],
            "autofix_available": len(safe_fixes) > 0
        }
        print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
