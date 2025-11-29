"""Automatic fix application based on agent findings."""

import logging
from pathlib import Path
from typing import Dict

from devloop.core.config import AutonomousFixesConfig, config
from devloop.core.context_store import Finding, context_store

logger = logging.getLogger(__name__)


class AutoFix:
    """Automatically applies safe fixes based on agent findings."""

    def __init__(self):
        self._fix_history = set()  # Track applied fixes to avoid duplicates

    async def apply_safe_fixes(self) -> Dict[str, int]:
        """Apply all safe fixes from agent findings.

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

        findings = await context_store.get_findings()
        actionable_findings = [f for f in findings if f.auto_fixable]
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
        """Apply a single fix if it's safe to do so."""
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

        # Apply the fix
        success = await self._execute_fix(agent_type, finding)
        if success:
            self._fix_history.add(finding.id)
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


# Global instance
auto_fix = AutoFix()


async def apply_safe_fixes():
    """Convenience function to apply safe fixes."""
    results = await auto_fix.apply_safe_fixes()
    return results
