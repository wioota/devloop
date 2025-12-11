"""Amp thread mapping for self-improvement agent.

Maps CLI actions to Amp thread context, enabling pattern detection
across multiple threads. Tracks which user actions followed agent actions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentAction:
    """Record of an agent action within a thread.

    Attributes:
        action: Type of action (e.g., "linter", "formatter", "test_runner")
        command: Command that was executed
        output: Output or findings from the action
        timestamp: When the action occurred
        success: Whether the action succeeded
    """

    action: str
    command: str
    output: Optional[str] = None
    timestamp: Optional[str] = None
    success: bool = True


@dataclass
class UserManualAction:
    """Record of a user performing an action after an agent action.

    Attributes:
        action: Type of manual action (e.g., "manual_fix", "rerun_command")
        description: Human-readable description
        time_after_agent_action: Seconds elapsed since the agent action
        timestamp: When the user action occurred
        related_agent_actions: List of agent action indices that may have triggered this
    """

    action: str
    description: str
    time_after_agent_action: int = 0
    timestamp: Optional[str] = None
    related_agent_actions: list[int] = field(default_factory=list)


@dataclass
class ThreadInsight:
    """Insight detected about a thread's patterns.

    Attributes:
        pattern: Name of the detected pattern
        severity: Severity level (info, warning, error)
        message: Human-readable message about the pattern
        evidence: Data supporting the insight
    """

    pattern: str
    severity: str  # "info", "warning", "error"
    message: str
    evidence: Optional[dict[str, Any]] = None


@dataclass
class AmpThreadEntry:
    """Complete record of a thread's agent and user actions.

    Attributes:
        timestamp: When this entry was created
        thread_id: Amp thread ID (format: T-{uuid})
        thread_url: Full Amp thread URL
        user_prompt: Initial prompt/request from the user
        agent_actions: List of actions taken by agents
        user_manual_actions: List of manual user actions
        insights: Detected patterns and insights
    """

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    thread_id: str = ""
    thread_url: str = ""
    user_prompt: str = ""
    agent_actions: list[AgentAction] = field(default_factory=list)
    user_manual_actions: list[UserManualAction] = field(default_factory=list)
    insights: list[ThreadInsight] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Recursively convert dataclass instances to dicts
        data["agent_actions"] = [asdict(action) for action in self.agent_actions]
        data["user_manual_actions"] = [
            asdict(action) for action in self.user_manual_actions
        ]
        data["insights"] = [asdict(insight) for insight in self.insights]
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class AmpThreadMapper:
    """Maps CLI actions to Amp thread context for pattern detection."""

    def __init__(self, log_file: Path):
        """Initialize Amp thread mapper.

        Args:
            log_file: Path to .devloop/amp-thread-log.jsonl file
        """
        self.log_file = log_file
        self._ensure_dir()
        self._thread_cache: dict[str, AmpThreadEntry] = {}

    def _ensure_dir(self) -> None:
        """Ensure log directory exists."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_entry(self, entry: AmpThreadEntry) -> None:
        """Log a thread entry to JSONL file.

        Args:
            entry: AmpThreadEntry to log
        """
        try:
            with open(self.log_file, "a") as f:
                f.write(entry.to_json() + "\n")
            # Update cache
            self._thread_cache[entry.thread_id] = entry
        except Exception as e:
            logger.error(f"Failed to log Amp thread entry: {e}")

    def create_entry(
        self,
        thread_id: str,
        thread_url: str,
        user_prompt: str = "",
    ) -> AmpThreadEntry:
        """Create a new thread entry.

        Args:
            thread_id: Amp thread ID
            thread_url: Amp thread URL
            user_prompt: Initial user prompt/request

        Returns:
            New AmpThreadEntry
        """
        return AmpThreadEntry(
            thread_id=thread_id,
            thread_url=thread_url,
            user_prompt=user_prompt,
        )

    def record_agent_action(
        self,
        thread_id: str,
        agent_name: str,
        command: str,
        output: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """Record an agent action for a thread.

        This method finds or creates the thread entry and adds the agent action.

        Args:
            thread_id: Thread ID
            agent_name: Name of the agent (e.g., "linter", "formatter")
            command: Command executed
            output: Output or findings
            success: Whether action succeeded
        """
        entry = self._get_or_create_entry(thread_id)

        action = AgentAction(
            action=agent_name,
            command=command,
            output=output,
            timestamp=datetime.now(UTC).isoformat(),
            success=success,
        )

        entry.agent_actions.append(action)
        self.log_entry(entry)

    def record_user_action(
        self,
        thread_id: str,
        action_type: str,
        description: str,
        time_after_last_agent_action: int = 0,
    ) -> None:
        """Record a manual user action following agent actions.

        Args:
            thread_id: Thread ID
            action_type: Type of user action
            description: Description of what user did
            time_after_last_agent_action: Seconds since last agent action
        """
        entry = self._get_or_create_entry(thread_id)

        user_action = UserManualAction(
            action=action_type,
            description=description,
            time_after_agent_action=time_after_last_agent_action,
            timestamp=datetime.now(UTC).isoformat(),
            related_agent_actions=self._identify_related_agent_actions(entry),
        )

        entry.user_manual_actions.append(user_action)
        self.log_entry(entry)

    def record_insight(
        self,
        thread_id: str,
        pattern: str,
        severity: str,
        message: str,
        evidence: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record a detected pattern/insight for a thread.

        Args:
            thread_id: Thread ID
            pattern: Pattern name
            severity: Severity level
            message: Human-readable message
            evidence: Supporting data
        """
        entry = self._get_or_create_entry(thread_id)

        insight = ThreadInsight(
            pattern=pattern,
            severity=severity,
            message=message,
            evidence=evidence,
        )

        entry.insights.append(insight)
        self.log_entry(entry)

    def detect_patterns(self, entry: AmpThreadEntry) -> list[ThreadInsight]:
        """Detect patterns in a thread's actions.

        Analyzes the sequence of agent and user actions to identify patterns:
        - User manual fix after agent suggestion
        - Command repetition (retry pattern)
        - Silent completions (agent output ignored)

        Args:
            entry: Thread entry to analyze

        Returns:
            List of detected insights
        """
        insights = []

        # Pattern: User manually fixed what agent suggested
        if self._detect_manual_fix_pattern(entry):
            insights.append(
                ThreadInsight(
                    pattern="user_manual_fix_after_agent",
                    severity="medium",
                    message="User manually applied fix instead of auto-fix",
                    evidence={
                        "agent_actions_count": len(entry.agent_actions),
                        "user_actions_count": len(entry.user_manual_actions),
                    },
                )
            )

        # Pattern: Command rerun (retry pattern)
        if self._detect_rerun_pattern(entry):
            insights.append(
                ThreadInsight(
                    pattern="command_rerun",
                    severity="info",
                    message="Command was re-run multiple times",
                    evidence={
                        "reruns": self._count_reruns(entry),
                    },
                )
            )

        # Pattern: Silent completion (agent action not acted on)
        if self._detect_silent_completion_pattern(entry):
            insights.append(
                ThreadInsight(
                    pattern="silent_completion",
                    severity="warning",
                    message="Agent action produced no visible user response",
                    evidence={
                        "agent_actions_without_response": self._count_unresponded_actions(
                            entry
                        ),
                    },
                )
            )

        return insights

    def _get_or_create_entry(self, thread_id: str) -> AmpThreadEntry:
        """Get existing entry or create new one.

        Args:
            thread_id: Thread ID

        Returns:
            AmpThreadEntry
        """
        if thread_id in self._thread_cache:
            return self._thread_cache[thread_id]

        # Try to load from file
        entry = self._load_entry_from_file(thread_id)
        if entry:
            self._thread_cache[thread_id] = entry
            return entry

        # Create new entry
        entry = AmpThreadEntry(thread_id=thread_id)
        self._thread_cache[thread_id] = entry
        return entry

    def _load_entry_from_file(self, thread_id: str) -> Optional[AmpThreadEntry]:
        """Load a thread entry from the log file.

        Args:
            thread_id: Thread ID to find

        Returns:
            AmpThreadEntry if found, None otherwise
        """
        if not self.log_file.exists():
            return None

        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("thread_id") == thread_id:
                                # Reconstruct dataclass instances
                                return self._dict_to_entry(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed JSON line: {line}")
        except Exception as e:
            logger.error(f"Failed to load entry for thread {thread_id}: {e}")

        return None

    def _dict_to_entry(self, data: dict[str, Any]) -> AmpThreadEntry:
        """Reconstruct AmpThreadEntry from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            AmpThreadEntry instance
        """
        # Convert nested dicts back to dataclass instances
        agent_actions = [
            AgentAction(**action) for action in data.get("agent_actions", [])
        ]
        user_manual_actions = [
            UserManualAction(**action) for action in data.get("user_manual_actions", [])
        ]
        insights = [ThreadInsight(**insight) for insight in data.get("insights", [])]

        return AmpThreadEntry(
            timestamp=data.get("timestamp", datetime.now(UTC).isoformat()),
            thread_id=data.get("thread_id", ""),
            thread_url=data.get("thread_url", ""),
            user_prompt=data.get("user_prompt", ""),
            agent_actions=agent_actions,
            user_manual_actions=user_manual_actions,
            insights=insights,
        )

    def _identify_related_agent_actions(self, entry: AmpThreadEntry) -> list[int]:
        """Identify which agent actions may have triggered a user action.

        Returns indices of agent actions that occurred before the user action.

        Args:
            entry: Thread entry

        Returns:
            List of agent action indices
        """
        return list(range(len(entry.agent_actions)))

    def _detect_manual_fix_pattern(self, entry: AmpThreadEntry) -> bool:
        """Detect if user manually fixed what an agent suggested.

        Args:
            entry: Thread entry

        Returns:
            True if pattern detected
        """
        # Pattern exists if there are agent actions and user actions following them
        if not entry.agent_actions or not entry.user_manual_actions:
            return False

        # Check if user actions mention "manual" or "fix"
        for user_action in entry.user_manual_actions:
            if (
                "manual" in user_action.action.lower()
                or "fix" in user_action.description.lower()
            ):
                return True

        return False

    def _detect_rerun_pattern(self, entry: AmpThreadEntry) -> bool:
        """Detect if commands were re-run multiple times.

        Args:
            entry: Thread entry

        Returns:
            True if pattern detected
        """
        # Look for repeated commands or rerun user actions
        rerun_count = sum(
            1
            for action in entry.user_manual_actions
            if "rerun" in action.action.lower() or "retry" in action.action.lower()
        )

        # Also check for duplicate commands in agent actions
        commands = [action.command for action in entry.agent_actions]
        command_counts: dict[str, int] = {}
        for cmd in commands:
            command_counts[cmd] = command_counts.get(cmd, 0) + 1

        duplicate_commands = sum(1 for count in command_counts.values() if count > 1)

        return rerun_count > 0 or duplicate_commands > 0

    def _detect_silent_completion_pattern(self, entry: AmpThreadEntry) -> bool:
        """Detect if agent actions produced no visible user response.

        Args:
            entry: Thread entry

        Returns:
            True if pattern detected
        """
        # Pattern exists if there are agent actions but few/no user actions
        if not entry.agent_actions:
            return False

        # If agent actions far outnumber user actions, likely silent completion
        return len(entry.agent_actions) > 0 and len(entry.user_manual_actions) == 0

    def _count_reruns(self, entry: AmpThreadEntry) -> int:
        """Count rerun actions in a thread.

        Args:
            entry: Thread entry

        Returns:
            Number of rerun actions
        """
        return sum(
            1
            for action in entry.user_manual_actions
            if "rerun" in action.action.lower() or "retry" in action.action.lower()
        )

    def _count_unresponded_actions(self, entry: AmpThreadEntry) -> int:
        """Count agent actions that had no corresponding user action.

        Args:
            entry: Thread entry

        Returns:
            Number of unresponded actions
        """
        if not entry.agent_actions or not entry.user_manual_actions:
            return len(entry.agent_actions)

        # Simple heuristic: if more agent actions than user actions,
        # excess are likely unresponded
        excess = len(entry.agent_actions) - len(entry.user_manual_actions)
        return max(0, excess)

    def read_recent(self, limit: int = 50) -> list[AmpThreadEntry]:
        """Read recent thread entries from log file.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of AmpThreadEntry objects (most recent first)
        """
        if not self.log_file.exists():
            return []

        entries = []
        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()
                # Process in reverse to get most recent first
                for line in reversed(lines):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            entries.append(self._dict_to_entry(data))
                            if len(entries) >= limit:
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed JSON line: {line}")
        except Exception as e:
            logger.error(f"Failed to read thread entries: {e}")

        return entries

    def read_by_pattern(self, pattern: str) -> list[AmpThreadEntry]:
        """Find all entries that detected a specific pattern.

        Args:
            pattern: Pattern name to search for

        Returns:
            List of matching AmpThreadEntry objects
        """
        if not self.log_file.exists():
            return []

        entries = []
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            entry = self._dict_to_entry(data)
                            # Check if any insight matches the pattern
                            if any(
                                insight.pattern == pattern for insight in entry.insights
                            ):
                                entries.append(entry)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed JSON line: {line}")
        except Exception as e:
            logger.error(f"Failed to read entries by pattern: {e}")

        return entries


# Global instance (initialized on first use)
_thread_mapper: Optional[AmpThreadMapper] = None


def get_amp_thread_mapper(devloop_dir: Optional[Path] = None) -> AmpThreadMapper:
    """Get or create the global Amp thread mapper instance.

    Args:
        devloop_dir: Path to .devloop directory (defaults to ~/.devloop)

    Returns:
        AmpThreadMapper instance
    """
    global _thread_mapper

    if _thread_mapper is None:
        if devloop_dir is None:
            devloop_dir = Path.home() / ".devloop"

        log_file = devloop_dir / "amp-thread-log.jsonl"
        _thread_mapper = AmpThreadMapper(log_file)

    return _thread_mapper
