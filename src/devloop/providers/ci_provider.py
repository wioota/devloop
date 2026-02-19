"""Abstract base class for CI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RunStatus(str, Enum):
    """CI run status enumeration."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    QUEUED = "queued"


class RunConclusion(str, Enum):
    """CI run conclusion enumeration."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    NEUTRAL = "neutral"
    SKIPPED = "skipped"
    STALE = "stale"


@dataclass
class WorkflowRun:
    """Represents a single CI workflow run."""

    id: str
    name: str
    branch: str
    status: RunStatus
    conclusion: Optional[RunConclusion]
    created_at: datetime
    updated_at: datetime
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowDefinition:
    """Represents a CI workflow definition."""

    name: str
    path: str
    triggers: List[str]
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CIProvider(ABC):
    """Abstract base class for CI platform providers."""

    @abstractmethod
    def get_status(self, branch: str) -> Optional[WorkflowRun]:
        """Get the latest workflow run status for a branch.

        Args:
            branch: Branch name

        Returns:
            Latest WorkflowRun or None if no runs found
        """
        pass

    @abstractmethod
    def list_runs(
        self,
        branch: str,
        limit: int = 10,
        workflow_name: Optional[str] = None,
    ) -> List[WorkflowRun]:
        """List workflow runs for a branch.

        Args:
            branch: Branch name
            limit: Maximum number of runs to return
            workflow_name: Optional filter by workflow name

        Returns:
            List of WorkflowRun objects
        """
        pass

    @abstractmethod
    def get_logs(self, run_id: str) -> Optional[str]:
        """Get logs for a specific run.

        Args:
            run_id: Run ID

        Returns:
            Log content or None if unavailable
        """
        pass

    @abstractmethod
    def rerun(self, run_id: str) -> bool:
        """Rerun a specific workflow run.

        Args:
            run_id: Run ID

        Returns:
            True if rerun was triggered successfully
        """
        pass

    @abstractmethod
    def cancel(self, run_id: str) -> bool:
        """Cancel a running workflow.

        Args:
            run_id: Run ID

        Returns:
            True if cancellation was successful
        """
        pass

    @abstractmethod
    def get_workflows(self) -> List[WorkflowDefinition]:
        """Get all workflow definitions in the repository.

        Returns:
            List of WorkflowDefinition objects
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if CI system is available and properly configured.

        Returns:
            True if provider is available and authenticated
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get human-readable provider name.

        Returns:
            Provider name (e.g., "GitHub Actions", "GitLab CI")
        """
        pass
