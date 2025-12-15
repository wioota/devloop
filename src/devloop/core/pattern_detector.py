"""Pattern detector with persistence for self-improvement agent.

Detects patterns, stores results, and provides query interface for insights.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from .pattern_analyzer import PatternAnalyzer, PatternMatch

logger = logging.getLogger(__name__)


@dataclass
class DetectedPattern:
    """Stored record of a detected pattern."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    pattern_name: str = ""
    severity: str = ""
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    recommendation: Optional[str] = None
    affected_threads: list[str] = field(default_factory=list)
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class PatternDetector:
    """Detects and persists patterns from logs and thread data."""

    def __init__(self, devloop_dir: Optional[Path] = None):
        """Initialize pattern detector.

        Args:
            devloop_dir: Path to .devloop directory (defaults to ~/.devloop)
        """
        if devloop_dir is None:
            devloop_dir = Path.home() / ".devloop"

        self.devloop_dir = devloop_dir
        self.log_file = devloop_dir / "patterns.jsonl"
        self.devloop_dir.mkdir(parents=True, exist_ok=True)
        # Ensure proper permissions (rwxr-xr-x)
        self.devloop_dir.chmod(0o755)

        # Initialize components
        from .action_logger import get_action_logger
        from .amp_thread_mapper import get_amp_thread_mapper

        self.action_logger = get_action_logger(devloop_dir)
        self.thread_mapper = get_amp_thread_mapper(devloop_dir)
        self.analyzer = PatternAnalyzer(self.action_logger, self.thread_mapper)

    def detect_patterns(
        self,
        time_window_hours: int = 24,
        min_occurrences: int = 2,
        save_results: bool = True,
    ) -> list[DetectedPattern]:
        """Detect patterns in current logs.

        Args:
            time_window_hours: Look back this many hours
            min_occurrences: Minimum occurrences to trigger pattern
            save_results: Whether to save results to log file

        Returns:
            List of detected patterns
        """
        # Run analysis
        matches = self.analyzer.analyze(
            time_window_hours=time_window_hours,
            min_occurrences=min_occurrences,
        )

        # Convert matches to stored format
        detected = [self._match_to_detected(match) for match in matches]

        # Save results
        if save_results:
            for pattern in detected:
                self._log_pattern(pattern)

        return detected

    def log_pattern(self, pattern: DetectedPattern) -> None:
        """Manually log a detected pattern.

        Args:
            pattern: Pattern to log
        """
        self._log_pattern(pattern)

    def acknowledge_pattern(
        self,
        pattern_name: str,
        notes: Optional[str] = None,
    ) -> None:
        """Mark a pattern as acknowledged.

        Args:
            pattern_name: Name of pattern to acknowledge
            notes: Optional notes about acknowledgment
        """
        # TODO: Implement pattern acknowledgment tracking
        # This would allow users to mark patterns as reviewed/addressed
        pass

    def get_recent_patterns(
        self,
        limit: int = 50,
        severity: Optional[str] = None,
    ) -> list[DetectedPattern]:
        """Get recent detected patterns.

        Args:
            limit: Maximum number to return
            severity: Filter by severity level (info, warning, error)

        Returns:
            List of patterns (most recent first)
        """
        if not self.log_file.exists():
            return []

        patterns = []
        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()
                # Process in reverse for most recent first
                for line in reversed(lines):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            pattern = DetectedPattern(**data)
                            if severity is None or pattern.severity == severity:
                                patterns.append(pattern)
                                if len(patterns) >= limit:
                                    break
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed JSON line: {line}")
        except Exception as e:
            logger.error(f"Failed to read patterns: {e}")

        return patterns

    def get_patterns_by_type(self, pattern_name: str) -> list[DetectedPattern]:
        """Get all instances of a specific pattern.

        Args:
            pattern_name: Pattern name to search for

        Returns:
            List of matching patterns
        """
        if not self.log_file.exists():
            return []

        patterns = []
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if data.get("pattern_name") == pattern_name:
                                patterns.append(DetectedPattern(**data))
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed JSON line: {line}")
        except Exception as e:
            logger.error(f"Failed to read patterns by type: {e}")

        return patterns

    def get_patterns_for_thread(self, thread_id: str) -> list[DetectedPattern]:
        """Get patterns affecting a specific thread.

        Args:
            thread_id: Amp thread ID

        Returns:
            List of patterns affecting the thread
        """
        if not self.log_file.exists():
            return []

        patterns = []
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            pattern = DetectedPattern(**data)
                            if thread_id in pattern.affected_threads:
                                patterns.append(pattern)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipped malformed JSON line: {line}")
        except Exception as e:
            logger.error(f"Failed to read patterns for thread: {e}")

        return patterns

    def get_high_confidence_patterns(
        self,
        confidence_threshold: float = 0.6,
        limit: int = 20,
    ) -> list[DetectedPattern]:
        """Get high-confidence patterns suitable for action.

        Args:
            confidence_threshold: Minimum confidence (0.0 to 1.0)
            limit: Maximum number to return

        Returns:
            List of high-confidence patterns
        """
        recent = self.get_recent_patterns(limit=200)
        return [p for p in recent if p.confidence >= confidence_threshold][:limit]

    def _match_to_detected(self, match: PatternMatch) -> DetectedPattern:
        """Convert PatternMatch to DetectedPattern.

        Args:
            match: PatternMatch from analyzer

        Returns:
            DetectedPattern for storage
        """
        return DetectedPattern(
            pattern_name=match.pattern_name,
            severity=match.severity,
            message=match.message,
            evidence=match.evidence,
            confidence=match.confidence,
            recommendation=match.recommendation,
            affected_threads=match.affected_threads,
        )

    def _log_pattern(self, pattern: DetectedPattern) -> None:
        """Log a pattern to JSONL file.

        Args:
            pattern: Pattern to log
        """
        try:
            with open(self.log_file, "a") as f:
                f.write(pattern.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to log pattern: {e}")


# Global instance (initialized on first use)
_pattern_detector: Optional[PatternDetector] = None


def get_pattern_detector(devloop_dir: Optional[Path] = None) -> PatternDetector:
    """Get or create the global pattern detector instance.

    Args:
        devloop_dir: Path to .devloop directory (defaults to ~/.devloop)

    Returns:
        PatternDetector instance
    """
    global _pattern_detector

    if _pattern_detector is None:
        _pattern_detector = PatternDetector(devloop_dir)

    return _pattern_detector
