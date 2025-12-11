"""Pattern analysis engine for self-improvement agent.

Analyzes CLI actions and thread data to detect patterns that indicate
UX gaps, feature requests, messaging issues, or quality problems.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable, Optional

from .action_logger import CLIAction
from .amp_thread_mapper import AmpThreadEntry

if TYPE_CHECKING:
    from .action_logger import ActionLogger
    from .amp_thread_mapper import AmpThreadMapper

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Definition of a detectable pattern."""

    name: str
    description: str
    severity: str  # "info", "warning", "error"
    detector_func: Optional[Callable[[PatternContext], Optional[PatternMatch]]] = field(
        default=None, init=False, repr=False
    )


@dataclass
class PatternMatch:
    """A detected pattern instance."""

    pattern_name: str
    severity: str
    message: str
    evidence: dict[str, Any]
    confidence: float  # 0.0 to 1.0
    recommendation: Optional[str] = None
    affected_threads: list[str] = field(default_factory=list)


@dataclass
class PatternContext:
    """Context provided to pattern detectors."""

    cli_actions: list[CLIAction]
    thread_entries: list[AmpThreadEntry]
    time_window_hours: int = 24
    min_occurrences: int = 2


class PatternDefinitions:
    """Built-in pattern definitions."""

    @staticmethod
    def frequency_analysis_pattern() -> Pattern:
        """Detect command repetition within a time window."""
        pattern = Pattern(
            name="command_repetition",
            description="Same command executed multiple times",
            severity="info",
        )
        pattern.detector_func = PatternDefinitions._detect_command_repetition
        return pattern

    @staticmethod
    def cross_thread_pattern() -> Pattern:
        """Detect patterns repeated across multiple threads."""
        pattern = Pattern(
            name="cross_thread_pattern",
            description="Same question or action across multiple threads",
            severity="warning",
        )
        pattern.detector_func = PatternDefinitions._detect_cross_thread_pattern
        return pattern

    @staticmethod
    def manual_fix_pattern() -> Pattern:
        """Detect user manually fixing what agent suggested."""
        pattern = Pattern(
            name="user_manual_fix",
            description="User manually applied fix instead of auto-fix",
            severity="medium",
        )
        pattern.detector_func = PatternDefinitions._detect_manual_fix_pattern
        return pattern

    @staticmethod
    def silent_completion_pattern() -> Pattern:
        """Detect agent actions that produced no user response."""
        pattern = Pattern(
            name="silent_completion",
            description="Agent action produced no visible user response",
            severity="warning",
        )
        pattern.detector_func = PatternDefinitions._detect_silent_completion_pattern
        return pattern

    @staticmethod
    def command_rerun_pattern() -> Pattern:
        """Detect commands being re-run multiple times."""
        pattern = Pattern(
            name="command_rerun",
            description="Commands re-run or retried multiple times",
            severity="info",
        )
        pattern.detector_func = PatternDefinitions._detect_command_rerun
        return pattern

    @staticmethod
    def _detect_command_repetition(
        context: PatternContext,
    ) -> Optional[PatternMatch]:
        """Detect same command run multiple times."""
        if not context.cli_actions:
            return None

        # Count command occurrences in time window
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=context.time_window_hours)

        command_counts: dict[str, list[CLIAction]] = {}
        for action in context.cli_actions:
            try:
                action_time = datetime.fromisoformat(action.timestamp)
                if action_time >= cutoff:
                    command_counts.setdefault(action.command, []).append(action)
            except (ValueError, TypeError):
                continue

        # Find commands executed multiple times
        repeated_commands = {
            cmd: actions
            for cmd, actions in command_counts.items()
            if len(actions) >= context.min_occurrences
        }

        if not repeated_commands:
            return None

        # Get the most repeated command
        most_repeated = max(repeated_commands.items(), key=lambda x: len(x[1]))
        command, actions = most_repeated

        return PatternMatch(
            pattern_name="command_repetition",
            severity="info",
            message=f"Command '{command}' executed {len(actions)} times in {context.time_window_hours}h",
            evidence={
                "command": command,
                "occurrences": len(actions),
                "time_window_hours": context.time_window_hours,
            },
            confidence=min(1.0, len(actions) / (context.min_occurrences * 2)),
            recommendation="Consider automating this command or adding it to a watch script",
        )

    @staticmethod
    def _detect_cross_thread_pattern(
        context: PatternContext,
    ) -> Optional[PatternMatch]:
        """Detect same pattern across multiple threads."""
        if (
            not context.thread_entries
            or len(context.thread_entries) < context.min_occurrences
        ):
            return None

        # Count pattern occurrences across threads
        pattern_counts: dict[str, list[str]] = {}
        for entry in context.thread_entries:
            for insight in entry.insights:
                pattern_counts.setdefault(insight.pattern, []).append(entry.thread_id)

        # Find patterns occurring multiple times
        repeated_patterns = {
            pattern: threads
            for pattern, threads in pattern_counts.items()
            if len(threads) >= context.min_occurrences
        }

        if not repeated_patterns:
            return None

        # Get the most repeated pattern
        most_repeated = max(repeated_patterns.items(), key=lambda x: len(x[1]))
        pattern_name, thread_ids = most_repeated

        return PatternMatch(
            pattern_name="cross_thread_pattern",
            severity="warning",
            message=f"Pattern '{pattern_name}' detected in {len(thread_ids)} threads",
            evidence={
                "pattern": pattern_name,
                "thread_count": len(thread_ids),
                "examples": thread_ids[:3],  # First 3 as examples
            },
            confidence=min(
                1.0, len(thread_ids) / 5.0
            ),  # Higher confidence with more occurrences
            recommendation=f"Investigate why '{pattern_name}' is recurring across threads",
            affected_threads=thread_ids,
        )

    @staticmethod
    def _detect_manual_fix_pattern(
        context: PatternContext,
    ) -> Optional[PatternMatch]:
        """Detect user manually fixing what agent suggested."""
        if not context.thread_entries:
            return None

        # Find threads with manual fix pattern
        manual_fix_threads = []
        for entry in context.thread_entries:
            for insight in entry.insights:
                if insight.pattern == "user_manual_fix_after_agent":
                    manual_fix_threads.append(entry.thread_id)
                    break

        if len(manual_fix_threads) < context.min_occurrences:
            return None

        return PatternMatch(
            pattern_name="user_manual_fix",
            severity="medium",
            message=f"Users manually applied fixes instead of auto-fix in {len(manual_fix_threads)} threads",
            evidence={
                "affected_threads": len(manual_fix_threads),
                "examples": manual_fix_threads[:3],
            },
            confidence=min(1.0, len(manual_fix_threads) / 3.0),
            recommendation="Review agent auto-fix messaging or completeness",
            affected_threads=manual_fix_threads,
        )

    @staticmethod
    def _detect_silent_completion_pattern(
        context: PatternContext,
    ) -> Optional[PatternMatch]:
        """Detect agent actions with no user response."""
        if not context.thread_entries:
            return None

        # Find threads with silent completion pattern
        silent_threads = []
        for entry in context.thread_entries:
            for insight in entry.insights:
                if insight.pattern == "silent_completion":
                    silent_threads.append(entry.thread_id)
                    break

        if len(silent_threads) < context.min_occurrences:
            return None

        return PatternMatch(
            pattern_name="silent_completion",
            severity="warning",
            message=f"Agent actions produced no visible response in {len(silent_threads)} threads",
            evidence={
                "affected_threads": len(silent_threads),
                "examples": silent_threads[:3],
            },
            confidence=min(1.0, len(silent_threads) / 4.0),
            recommendation="Review agent output visibility or add feedback prompts",
            affected_threads=silent_threads,
        )

    @staticmethod
    def _detect_command_rerun(
        context: PatternContext,
    ) -> Optional[PatternMatch]:
        """Detect commands being re-run or retried."""
        if not context.thread_entries:
            return None

        # Find threads with rerun pattern
        rerun_threads = []
        for entry in context.thread_entries:
            for insight in entry.insights:
                if insight.pattern == "command_rerun":
                    rerun_threads.append(entry.thread_id)
                    break

        if len(rerun_threads) < context.min_occurrences:
            return None

        return PatternMatch(
            pattern_name="command_rerun",
            severity="info",
            message=f"Commands re-run or retried in {len(rerun_threads)} threads",
            evidence={
                "affected_threads": len(rerun_threads),
                "examples": rerun_threads[:3],
            },
            confidence=min(1.0, len(rerun_threads) / 3.0),
            recommendation="Investigate why users need to retry - consider better error messages",
            affected_threads=rerun_threads,
        )


class PatternAnalyzer:
    """Analyzes logs and thread data for patterns."""

    def __init__(
        self,
        action_logger: ActionLogger,
        thread_mapper: AmpThreadMapper,
    ):
        """Initialize pattern analyzer.

        Args:
            action_logger: ActionLogger instance
            thread_mapper: AmpThreadMapper instance
        """
        self.action_logger = action_logger
        self.thread_mapper = thread_mapper
        self.patterns = [
            PatternDefinitions.frequency_analysis_pattern(),
            PatternDefinitions.cross_thread_pattern(),
            PatternDefinitions.manual_fix_pattern(),
            PatternDefinitions.silent_completion_pattern(),
            PatternDefinitions.command_rerun_pattern(),
        ]

    def analyze(
        self,
        time_window_hours: int = 24,
        min_occurrences: int = 2,
    ) -> list[PatternMatch]:
        """Analyze logs for patterns.

        Args:
            time_window_hours: Look back this many hours
            min_occurrences: Minimum occurrences to trigger pattern

        Returns:
            List of detected patterns
        """
        # Gather data
        cli_actions = self.action_logger.read_recent(limit=1000)
        thread_entries = self.thread_mapper.read_recent(limit=100)

        # Create context
        context = PatternContext(
            cli_actions=cli_actions,
            thread_entries=thread_entries,
            time_window_hours=time_window_hours,
            min_occurrences=min_occurrences,
        )

        # Run detectors
        matches = []
        for pattern in self.patterns:
            if pattern.detector_func:
                try:
                    match = pattern.detector_func(context)
                    if match:
                        matches.append(match)
                except Exception as e:
                    logger.error(f"Error detecting pattern '{pattern.name}': {e}")

        return matches

    def get_pattern_by_name(self, name: str) -> Optional[Pattern]:
        """Get a pattern definition by name.

        Args:
            name: Pattern name

        Returns:
            Pattern if found, None otherwise
        """
        for pattern in self.patterns:
            if pattern.name == name:
                return pattern
        return None

    def register_custom_pattern(
        self,
        name: str,
        description: str,
        severity: str,
        detector_func: Callable[[PatternContext], Optional[PatternMatch]],
    ) -> Pattern:
        """Register a custom pattern detector.

        Args:
            name: Pattern name
            description: Pattern description
            severity: Severity level
            detector_func: Detector function

        Returns:
            Registered Pattern
        """
        pattern = Pattern(
            name=name,
            description=description,
            severity=severity,
        )
        pattern.detector_func = detector_func
        self.patterns.append(pattern)
        return pattern
