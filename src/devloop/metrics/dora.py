"""DORA metrics analysis from git and CI/CD history.

DORA (DevOps Research and Assessment) metrics:
1. Deployment Frequency - How often deployments to production occur
2. Lead Time for Changes - Time from code commit to production deployment
3. Change Failure Rate - Percentage of deployments causing incidents
4. Time to Restore Service - Time to recover from production failures
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, UTC, timedelta
from pathlib import Path
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class GitCommit:
    """Represents a git commit."""

    hash: str
    message: str
    author: str
    timestamp: datetime
    files_changed: int
    insertions: int
    deletions: int


@dataclass
class GitTag:
    """Represents a git tag/release."""

    tag: str
    hash: str
    timestamp: datetime
    is_release: bool = False


@dataclass
class DeploymentMetrics:
    """Deployment frequency metrics."""

    period_days: int
    deployments_count: int
    deployment_frequency: float  # deployments per day
    date_range: tuple[datetime, datetime]


@dataclass
class LeadTimeMetrics:
    """Lead time for changes metrics."""

    avg_lead_time_hours: float
    min_lead_time_hours: float
    max_lead_time_hours: float
    median_lead_time_hours: float
    commits_analyzed: int


@dataclass
class ChangeFailureRateMetrics:
    """Change failure rate metrics."""

    total_deployments: int
    failed_deployments: int
    failure_rate_percent: float


@dataclass
class DORAMetrics:
    """Complete DORA metrics report."""

    period: str
    date_range: tuple[datetime, datetime]
    deployment_frequency: DeploymentMetrics
    lead_time: Optional[LeadTimeMetrics] = None
    change_failure_rate: Optional[ChangeFailureRateMetrics] = None
    time_to_restore: Optional[float] = None  # hours


class GitAnalyzer:
    """Analyzes git history for DORA metrics."""

    def __init__(self, repo_path: Path = Path(".")):
        """Initialize git analyzer.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = repo_path
        self._validate_repo()

    def _validate_repo(self) -> None:
        """Validate that path is a git repository."""
        try:
            self._run_git(["rev-parse", "--git-dir"])
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Not a git repository: {self.repo_path}") from e

    def _run_git(self, args: list[str]) -> str:
        """Run git command and return output."""
        result = subprocess.run(
            ["git"] + args,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def get_commits_in_range(
        self,
        start: datetime,
        end: datetime,
        branch: str = "main",
    ) -> list[GitCommit]:
        """Get commits in a date range.

        Args:
            start: Start date
            end: End date
            branch: Git branch to analyze

        Returns:
            List of commits
        """
        start_str = start.isoformat()
        end_str = end.isoformat()

        try:
            # Get commit hashes and timestamps (without numstat to simplify parsing)
            # Use --all to get commits from all branches/tags
            output = self._run_git(
                [
                    "log",
                    f"--after={start_str}",
                    f"--before={end_str}",
                    "--all",
                    "--format=%H%x00%ai%x00%an%x00%s%x00",
                ]
            )
        except subprocess.CalledProcessError:
            # Error in git log, return empty
            return []

        commits = []

        # Split by null terminators for each commit
        commit_strings = output.split("\x00\x00")

        for commit_str in commit_strings:
            if not commit_str.strip():
                continue

            parts = commit_str.split("\x00")
            if len(parts) < 4:
                continue

            commit_hash = parts[0].strip()
            timestamp_str = parts[1].strip()
            author = parts[2].strip()
            message = parts[3].strip()

            if not commit_hash or not timestamp_str:
                continue

            # Parse timestamp
            try:
                # Git format: "2025-12-13 18:39:01 +1300"
                # Convert to ISO format for parsing
                # Replace the last space with '+' for timezone
                parts = timestamp_str.rsplit(" ", 1)
                if len(parts) == 2:
                    datetime_part = parts[0]
                    tz_part = parts[1]
                    # Construct ISO string: YYYY-MM-DDTHH:MM:SS±HHMM
                    iso_str = datetime_part.replace(" ", "T") + tz_part
                    timestamp = datetime.fromisoformat(iso_str)
                else:
                    timestamp = datetime.fromisoformat(timestamp_str)
            except (ValueError, IndexError):
                continue

            # Get file stats separately to avoid parsing complexity
            try:
                stats = self._run_git(["show", "--numstat", "--format=", commit_hash])
                lines = stats.strip().split("\n")
                files_changed = len([line for line in lines if line.strip()])
                insertions = 0
                deletions = 0

                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            insertions += int(parts[0]) if parts[0].isdigit() else 0
                            deletions += int(parts[1]) if parts[1].isdigit() else 0
                        except ValueError:
                            pass
            except subprocess.CalledProcessError:
                files_changed = 0
                insertions = 0
                deletions = 0

            commits.append(
                GitCommit(
                    hash=commit_hash,
                    message=message,
                    author=author,
                    timestamp=timestamp,
                    files_changed=files_changed,
                    insertions=insertions,
                    deletions=deletions,
                )
            )

        return commits

    def get_tags_in_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[GitTag]:
        """Get git tags (releases) in a date range.

        Args:
            start: Start date
            end: End date

        Returns:
            List of tags
        """
        try:
            output = self._run_git(
                [
                    "tag",
                    "-l",
                    "--format=%(refname:short)|%(objectname:short)|%(creatordate:iso8601)",
                    "--sort=-creatordate",
                ]
            )
        except subprocess.CalledProcessError:
            return []

        tags = []

        for line in output.split("\n"):
            if not line.strip():
                continue

            parts = line.split("|")
            if len(parts) < 3:
                continue

            tag, hash_short, timestamp_str = parts[0], parts[1], parts[2]

            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                continue

            if start <= timestamp <= end:
                # Determine if this is likely a release tag (v1.0.0, release-*, etc.)
                is_release = (
                    tag.startswith("v")
                    or tag.startswith("release")
                    or tag.startswith("v-")
                )

                tags.append(
                    GitTag(
                        tag=tag,
                        hash=hash_short,
                        timestamp=timestamp,
                        is_release=is_release,
                    )
                )

        return tags

    def get_deployment_frequency(
        self,
        start: datetime,
        end: datetime,
    ) -> DeploymentMetrics:
        """Calculate deployment frequency from git tags.

        Args:
            start: Start date
            end: End date

        Returns:
            Deployment frequency metrics
        """
        tags = self.get_tags_in_range(start, end)

        # Filter to release tags only
        releases = [t for t in tags if t.is_release]

        period_days = (end - start).days
        if period_days == 0:
            period_days = 1

        frequency = len(releases) / period_days

        return DeploymentMetrics(
            period_days=period_days,
            deployments_count=len(releases),
            deployment_frequency=frequency,
            date_range=(start, end),
        )

    def get_lead_time_for_changes(
        self,
        start: datetime,
        end: datetime,
        branch: str = "main",
    ) -> Optional[LeadTimeMetrics]:
        """Calculate lead time for changes.

        This approximates lead time by analyzing commit timestamps.
        A more accurate calculation would require deployment tracking.

        Args:
            start: Start date
            end: End date
            branch: Git branch to analyze

        Returns:
            Lead time metrics
        """
        commits = self.get_commits_in_range(start, end, branch)

        if len(commits) < 2:
            return None

        # Calculate time between commits (as a proxy for lead time)
        lead_times = []

        for i in range(1, len(commits)):
            time_diff = (
                commits[i - 1].timestamp - commits[i].timestamp
            ).total_seconds()
            if time_diff > 0:
                lead_times.append(time_diff / 3600)  # Convert to hours

        if not lead_times:
            return None

        lead_times.sort()
        median = lead_times[len(lead_times) // 2]

        return LeadTimeMetrics(
            avg_lead_time_hours=sum(lead_times) / len(lead_times),
            min_lead_time_hours=min(lead_times),
            max_lead_time_hours=max(lead_times),
            median_lead_time_hours=median,
            commits_analyzed=len(commits),
        )


class DORAMetricsAnalyzer:
    """Analyzes DORA metrics from git and CI/CD history."""

    def __init__(
        self, repo_path: Path = Path("."), telemetry_logger: Optional[Any] = None
    ):
        """Initialize DORA metrics analyzer.

        Args:
            repo_path: Path to git repository
            telemetry_logger: Optional telemetry logger for CI metrics
        """
        self.git_analyzer = GitAnalyzer(repo_path)
        self.telemetry_logger = telemetry_logger
        self.repo_path = repo_path

    def analyze(
        self,
        period_days: int = 30,
        branch: str = "main",
    ) -> DORAMetrics:
        """Analyze DORA metrics for a time period.

        Args:
            period_days: Number of days to analyze
            branch: Git branch to analyze

        Returns:
            Complete DORA metrics report
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=period_days)

        # Calculate deployment frequency
        deployment_freq = self.git_analyzer.get_deployment_frequency(start, end)

        # Calculate lead time for changes
        lead_time = self.git_analyzer.get_lead_time_for_changes(start, end, branch)

        # Calculate change failure rate from telemetry if available
        change_failure_rate = None
        if self.telemetry_logger:
            change_failure_rate = self._calculate_change_failure_rate()

        return DORAMetrics(
            period=f"{period_days} days",
            date_range=(start, end),
            deployment_frequency=deployment_freq,
            lead_time=lead_time,
            change_failure_rate=change_failure_rate,
        )

    def _calculate_change_failure_rate(self) -> Optional[ChangeFailureRateMetrics]:
        """Calculate change failure rate from telemetry.

        Returns:
            Change failure rate metrics
        """
        if not self.telemetry_logger:
            return None

        try:
            stats = self.telemetry_logger.get_stats()

            # Count pre-push checks as deployments
            pre_push_events = stats.get("events_by_type", {}).get("pre_push_check", 0)

            if pre_push_events == 0:
                return None

            # Get events to count failures
            events = self.telemetry_logger._get_events_streaming()
            failed_pushes = sum(
                1
                for e in events
                if e.get("event_type") == "pre_push_check"
                and not e.get("success", True)
            )

            failure_rate = (
                (failed_pushes / pre_push_events * 100) if pre_push_events > 0 else 0
            )

            return ChangeFailureRateMetrics(
                total_deployments=pre_push_events,
                failed_deployments=failed_pushes,
                failure_rate_percent=failure_rate,
            )
        except Exception as e:
            logger.warning(f"Failed to calculate change failure rate: {e}")
            return None

    def compare_periods(
        self,
        before_start: datetime,
        before_end: datetime,
        after_start: datetime,
        after_end: datetime,
        branch: str = "main",
    ) -> tuple[DORAMetrics, DORAMetrics]:
        """Compare DORA metrics between two periods.

        Args:
            before_start: Start of before period
            before_end: End of before period
            after_start: Start of after period
            after_end: End of after period
            branch: Git branch to analyze

        Returns:
            Tuple of (before_metrics, after_metrics)
        """
        # Calculate metrics for both periods
        before_deployment_freq = self.git_analyzer.get_deployment_frequency(
            before_start, before_end
        )
        before_lead_time = self.git_analyzer.get_lead_time_for_changes(
            before_start, before_end, branch
        )

        after_deployment_freq = self.git_analyzer.get_deployment_frequency(
            after_start, after_end
        )
        after_lead_time = self.git_analyzer.get_lead_time_for_changes(
            after_start, after_end, branch
        )

        before_metrics = DORAMetrics(
            period=f"{(before_end - before_start).days} days",
            date_range=(before_start, before_end),
            deployment_frequency=before_deployment_freq,
            lead_time=before_lead_time,
        )

        after_metrics = DORAMetrics(
            period=f"{(after_end - after_start).days} days",
            date_range=(after_start, after_end),
            deployment_frequency=after_deployment_freq,
            lead_time=after_lead_time,
        )

        return before_metrics, after_metrics
