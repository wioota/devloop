"""Automatic fix application based on agent findings."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from devloop.core.backup_manager import BackupManager, get_backup_manager
from devloop.core.config import AutonomousFixesConfig, config
from devloop.core.context_store import Finding, context_store

logger = logging.getLogger(__name__)


class AutoFix:
    """Automatically applies safe fixes based on agent findings.

    Features:
    - Pre-modification backups for all changes
    - Atomic operations with rollback support
    - Safety level enforcement
    - Opt-in configuration
    - Comprehensive audit trail
    """

    def __init__(self, project_root: Optional[Path] = None):
        self._fix_history: set[str] = set()  # Track applied fixes to avoid duplicates
        self._backup_manager = get_backup_manager(project_root or Path.cwd())
        self._applied_fixes: List[Dict] = []  # Track all applied fixes in session

    async def apply_safe_fixes(self, require_confirmation: bool = True) -> Dict[str, int]:
        """Apply all safe fixes from agent findings.

        Args:
            require_confirmation: If True, user must explicitly confirm before applying

        Returns:
            Dict mapping agent types to number of fixes applied
        """
        # Check if autonomous fixes are enabled
        global_config = config.get_global_config()
        if (
            not global_config.autonomous_fixes
            or not global_config.autonomous_fixes.enabled
        ):
            logger.info("Autonomous fixes are disabled in configuration")
            return {}

        # Check for explicit opt-in (CRITICAL SECURITY REQUIREMENT)
        if not global_config.autonomous_fixes.opt_in:
            logger.warning(
                "Autonomous fixes require explicit opt-in. "
                "Set 'autonomousFixes.opt_in: true' in .devloop/agents.json"
            )
            return {}

        findings = await context_store.get_findings()
        actionable_findings = [f for f in findings if f.auto_fixable]

        if not actionable_findings:
            logger.info("No auto-fixable findings to apply")
            return {}

        # User confirmation if required
        if require_confirmation:
            logger.info(
                f"Found {len(actionable_findings)} auto-fixable findings. "
                "User confirmation required before applying."
            )
            # In a real implementation, this would prompt the user
            # For now, we return empty to be safe
            return {}

        applied_fixes: Dict[str, int] = {}

        for finding in actionable_findings:
            agent_type = finding.agent
            if await self._apply_single_fix(
                agent_type, finding, global_config.autonomous_fixes
            ):
                applied_fixes[agent_type] = applied_fixes.get(agent_type, 0) + 1
                await context_store.clear_findings(file_filter=finding.file)

        return applied_fixes

    async def _apply_single_fix(
        self,
        agent_type: str,
        finding: Finding,
        autonomous_fixes_config: AutonomousFixesConfig,
    ) -> bool:
        """Apply a single fix if it's safe to do so.

        This method:
        1. Creates a backup before modification
        2. Applies the fix
        3. Tracks the change for audit/rollback
        """
        if finding.id in self._fix_history:
            return False  # Already applied

        # Check if fix is safe based on safety level
        if not self._is_safe_for_config(
            agent_type, finding, autonomous_fixes_config.safety_level
        ):
            logger.info(
                f"Skipping {agent_type} fix (not safe for current safety level): {finding.message}"
            )
            return False

        # CRITICAL: Create backup before any modification
        file_path = finding.file
        if file_path:
            backup_id = self._backup_manager.create_backup(
                file_path=Path(file_path),
                fix_type=agent_type,
                description=finding.message,
                metadata={
                    "finding_id": finding.id,
                    "severity": finding.severity,
                    "safety_level": autonomous_fixes_config.safety_level,
                    "context": finding.context
                }
            )

            if not backup_id:
                logger.error(f"Failed to create backup for {file_path}, aborting fix")
                return False

            logger.info(f"Created backup {backup_id} before applying fix")

        # Apply the fix
        success = await self._execute_fix(agent_type, finding)
        if success:
            self._fix_history.add(finding.id)
            self._applied_fixes.append({
                "finding_id": finding.id,
                "agent_type": agent_type,
                "file": file_path,
                "backup_id": backup_id if file_path else None,
                "message": finding.message
            })
            logger.info(f"Applied {agent_type} fix: {finding.message}")

        return success

    def _is_safe_for_config(
        self, agent_type: str, finding: Finding, safety_level: str
    ) -> bool:
        """Check if a finding is safe to apply based on the configured safety level."""
        message = finding.message.lower()

        # Always reject errors/failures
        if any(
            keyword in message for keyword in ["error", "failed", "timeout", "conflict"]
        ):
            return False

        if safety_level == "safe_only":
            return self._is_safe_only_fix(agent_type, finding)
        elif safety_level == "medium_risk":
            return self._is_medium_risk_fix(agent_type, finding)
        elif safety_level == "all":
            return True  # Apply all fixes
        else:
            return False  # Unknown safety level, be safe

    def _is_safe_only_fix(self, agent_type: str, finding: Finding) -> bool:
        """Check if a finding is safe-only level."""
        message = finding.message.lower()

        if agent_type == "formatter":
            # Only basic formatting issues
            return "would format" in message or "needs formatting" in message

        elif agent_type == "linter":
            # Only very safe linting fixes
            safe_patterns = [
                "whitespace",
                "indentation",
                "trailing whitespace",
                "blank line",
            ]
            return any(pattern in message for pattern in safe_patterns)

        return False

    def _is_medium_risk_fix(self, agent_type: str, finding: Finding) -> bool:
        """Check if a finding is medium-risk level."""
        message = finding.message.lower()

        if agent_type == "formatter":
            # All formatting fixes
            return "would format" in message or "needs formatting" in message

        elif agent_type == "linter":
            # More linting fixes including imports
            safe_patterns = [
                "unused import",
                "import sort",
                "whitespace",
                "indentation",
                "trailing whitespace",
                "blank line",
            ]
            return any(pattern in message for pattern in safe_patterns)

        return False

    async def _execute_fix(self, agent_type: str, finding: Finding) -> bool:
        """Execute the actual fix."""
        try:
            if agent_type == "formatter":
                return await self._execute_formatter_fix(finding)
            elif agent_type == "linter":
                return await self._execute_linter_fix(finding)
            else:
                return False
        except Exception as e:
            logger.error(f"Error applying {agent_type} fix: {e}")
            return False

    async def _execute_formatter_fix(self, finding: Finding) -> bool:
        """Execute a formatter fix."""
        file_path = finding.file
        if not file_path:
            return False

        path = Path(file_path)
        formatter = finding.context.get("formatter", "black")

        # Import the formatter agent logic
        from devloop.agents.formatter import FormatterAgent

        # Create a temporary formatter instance to run the fix
        agent = FormatterAgent(
            name="auto-formatter",
            triggers=[],
            event_bus=None,
            config={
                "formatOnSave": True,
                "reportOnly": False,
                "filePatterns": ["**/*"],
                "formatters": {path.suffix.lstrip("."): formatter},
            },
        )

        # Run the formatter directly
        success, error = await agent._run_formatter(formatter, path)
        return success

    async def _execute_linter_fix(self, finding: Finding) -> bool:
        """Execute a linter fix."""
        # For now, we'll implement basic auto-fixes
        # In a full implementation, this would use ruff --fix or similar
        file_path = finding.file
        if not file_path:
            return False

        message = finding.message.lower()

        # Handle specific fix types
        if "unused import" in message:
            return await self._fix_unused_import(file_path, finding.context)
        elif "import sort" in message:
            return await self._fix_import_sort(file_path)
        elif "whitespace" in message or "indentation" in message:
            return await self._fix_whitespace(file_path, finding.context)

        return False

    async def _fix_unused_import(self, file_path: str, context: Dict) -> bool:
        """Fix unused import."""
        # This would need more sophisticated parsing
        # For now, return False to be safe
        return False

    async def _fix_import_sort(self, file_path: str) -> bool:
        """Fix import sorting."""
        # Could use isort or similar
        return False

    async def _fix_whitespace(self, file_path: str, context: Dict) -> bool:
        """Fix whitespace issues."""
        # Could use autopep8 or similar
        return False


    def rollback_last(self) -> bool:
        """Rollback the last applied fix.

        Returns:
            True if rollback successful
        """
        if not self._applied_fixes:
            logger.warning("No fixes to rollback in current session")
            return False

        last_fix = self._applied_fixes[-1]
        backup_id = last_fix.get("backup_id")

        if not backup_id:
            logger.error("No backup ID found for last fix")
            return False

        success = self._backup_manager.rollback(backup_id)
        if success:
            self._applied_fixes.pop()
            logger.info(f"Rolled back fix: {last_fix['message']}")

        return success

    def rollback_all_session(self) -> int:
        """Rollback all fixes from current session.

        Returns:
            Number of fixes successfully rolled back
        """
        rolled_back = 0

        for fix in reversed(self._applied_fixes):
            backup_id = fix.get("backup_id")
            if backup_id and self._backup_manager.rollback(backup_id):
                rolled_back += 1

        if rolled_back > 0:
            self._applied_fixes.clear()
            logger.info(f"Rolled back {rolled_back} fixes from current session")

        return rolled_back

    def get_applied_fixes(self) -> List[Dict]:
        """Get list of fixes applied in current session."""
        return self._applied_fixes.copy()

    def get_change_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get change history from backup manager."""
        return self._backup_manager.get_change_history(limit=limit)


# Global instance
auto_fix = AutoFix()


async def apply_safe_fixes(require_confirmation: bool = True):
    """Convenience function to apply safe fixes."""
    results = await auto_fix.apply_safe_fixes(require_confirmation=require_confirmation)
    return results


def rollback_last() -> bool:
    """Convenience function to rollback last fix."""
    return auto_fix.rollback_last()


def rollback_all_session() -> int:
    """Convenience function to rollback all session fixes."""
    return auto_fix.rollback_all_session()


def get_change_history(limit: Optional[int] = None) -> List[Dict]:
    """Convenience function to get change history."""
    return auto_fix.get_change_history(limit=limit)
