"""Release workflow management using provider abstraction."""

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from devloop.providers.ci_provider import CIProvider, RunConclusion, RunStatus
from devloop.providers.registry_provider import PackageRegistry
from devloop.providers.provider_manager import get_provider_manager


@dataclass
class ReleaseConfig:
    """Configuration for release workflow."""

    version: str
    branch: str = "main"
    tag_prefix: str = "v"
    create_tag: bool = True
    publish: bool = True
    ci_provider: Optional[str] = None  # auto-detect if None
    registry_provider: Optional[str] = None  # auto-detect if None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PreReleaseCheck:
    """Result of a pre-release check."""

    check_name: str
    passed: bool
    message: str
    details: Optional[str] = None


@dataclass
class ReleaseResult:
    """Result of a release operation."""

    success: bool
    version: str
    checks: List[PreReleaseCheck] = field(default_factory=list)
    ci_provider_name: Optional[str] = None
    registry_provider_name: Optional[str] = None
    tag_created: bool = False
    published: bool = False
    url: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class ReleaseManager:
    """Manages release workflow using provider abstraction.

    Works with any CI system and package registry through the provider interface.
    Handles pre-release checks, tagging, and publishing in a platform-agnostic way.
    """

    def __init__(self, config: ReleaseConfig):
        """Initialize release manager.

        Args:
            config: Release configuration
        """
        self.config = config
        self.manager = get_provider_manager()
        self.ci_provider: Optional[CIProvider] = None
        self.registry_provider: Optional[PackageRegistry] = None
        self._checks_passed: List[PreReleaseCheck] = []

    def get_ci_provider(self) -> Optional[CIProvider]:
        """Get CI provider (auto-detect or use configured)."""
        if self.ci_provider is None:
            if self.config.ci_provider:
                self.ci_provider = self.manager.get_ci_provider(self.config.ci_provider)
            else:
                self.ci_provider = self.manager.auto_detect_ci_provider()
        return self.ci_provider

    def get_registry_provider(self) -> Optional[PackageRegistry]:
        """Get registry provider (auto-detect or use configured)."""
        if self.registry_provider is None:
            if self.config.registry_provider:
                self.registry_provider = self.manager.get_registry_provider(
                    self.config.registry_provider
                )
            else:
                self.registry_provider = self.manager.auto_detect_registry_provider()
        return self.registry_provider

    def run_pre_release_checks(self) -> ReleaseResult:
        """Run all pre-release checks.

        Checks include:
        - Git working directory is clean
        - Branch is correct
        - CI passes on current branch
        - Registry credentials are valid
        - Version format is valid

        Returns:
            ReleaseResult with check details
        """
        start_time = datetime.now()
        result = ReleaseResult(success=True, version=self.config.version)

        # Check 1: Git working directory is clean
        if not self._check_git_clean():
            result.checks.append(
                PreReleaseCheck(
                    check_name="git_clean",
                    passed=False,
                    message="Git working directory has uncommitted changes",
                )
            )
            result.success = False
        else:
            result.checks.append(
                PreReleaseCheck(
                    check_name="git_clean",
                    passed=True,
                    message="Git working directory is clean",
                )
            )

        # Check 2: On correct branch
        current_branch = self._get_current_branch()
        if current_branch != self.config.branch:
            result.checks.append(
                PreReleaseCheck(
                    check_name="correct_branch",
                    passed=False,
                    message=f"Not on {self.config.branch} branch (currently on {current_branch})",
                )
            )
            result.success = False
        else:
            result.checks.append(
                PreReleaseCheck(
                    check_name="correct_branch",
                    passed=True,
                    message=f"On correct branch: {self.config.branch}",
                )
            )

        # Check 3: CI passes
        ci_check = self._check_ci_passes()
        result.checks.append(ci_check)
        result.ci_provider_name = (
            self.get_ci_provider().get_provider_name()
            if self.get_ci_provider()
            else None
        )
        if not ci_check.passed:
            result.success = False

        # Check 4: Registry credentials
        registry = self.get_registry_provider()
        if registry:
            if not registry.check_credentials():
                result.checks.append(
                    PreReleaseCheck(
                        check_name="registry_credentials",
                        passed=False,
                        message=f"{registry.get_provider_name()} credentials invalid or unavailable",
                    )
                )
                result.success = False
            else:
                result.checks.append(
                    PreReleaseCheck(
                        check_name="registry_credentials",
                        passed=True,
                        message=f"{registry.get_provider_name()} credentials valid",
                    )
                )
                result.registry_provider_name = registry.get_provider_name()
        else:
            result.checks.append(
                PreReleaseCheck(
                    check_name="registry_credentials",
                    passed=False,
                    message="No package registry provider available",
                )
            )
            result.success = False

        # Check 5: Version format
        if self._validate_version_format():
            result.checks.append(
                PreReleaseCheck(
                    check_name="version_format",
                    passed=True,
                    message=f"Version format valid: {self.config.version}",
                )
            )
        else:
            result.checks.append(
                PreReleaseCheck(
                    check_name="version_format",
                    passed=False,
                    message=f"Invalid version format: {self.config.version}",
                )
            )
            result.success = False

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    def create_release_tag(self) -> ReleaseResult:
        """Create a git tag for the release.

        Returns:
            ReleaseResult with tagging details
        """
        start_time = datetime.now()
        result = ReleaseResult(success=True, version=self.config.version)

        tag_name = f"{self.config.tag_prefix}{self.config.version}"

        try:
            # Check if tag already exists
            result_check = subprocess.run(
                ["git", "tag", "-l", tag_name],
                capture_output=True,
                text=True,
                check=False,
            )

            if result_check.stdout.strip():
                result.success = False
                result.error = f"Tag {tag_name} already exists"
                result.duration_seconds = (datetime.now() - start_time).total_seconds()
                return result

            # Create annotated tag
            subprocess.run(
                [
                    "git",
                    "tag",
                    "-a",
                    tag_name,
                    "-m",
                    f"DevLoop Release {self.config.version}",
                ],
                check=True,
                capture_output=True,
            )

            result.tag_created = True
            result.url = f"refs/tags/{tag_name}"

        except subprocess.CalledProcessError as e:
            result.success = False
            result.error = f"Failed to create tag: {e}"

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    def publish_release(self) -> ReleaseResult:
        """Publish release to registry.

        Returns:
            ReleaseResult with publishing details
        """
        start_time = datetime.now()
        result = ReleaseResult(success=True, version=self.config.version)

        registry = self.get_registry_provider()
        if not registry:
            result.success = False
            result.error = "No package registry provider available"
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            return result

        try:
            # Publish package
            if not registry.publish(".", self.config.version):
                result.success = False
                result.error = f"Failed to publish to {registry.get_provider_name()}"
            else:
                result.published = True
                result.registry_provider_name = registry.get_provider_name()
                result.url = registry.get_package_url("devloop", self.config.version)

        except Exception as e:
            result.success = False
            result.error = f"Publishing failed: {e}"

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    def release(self) -> ReleaseResult:
        """Execute full release workflow.

        Steps:
        1. Run pre-release checks
        2. If checks pass and config.create_tag: create git tag
        3. If tag created and config.publish: publish to registry
        4. If publishing succeeds: push tag to remote

        Returns:
            ReleaseResult with overall status
        """
        start_time = datetime.now()

        # Run pre-release checks
        checks_result = self.run_pre_release_checks()
        if not checks_result.success:
            checks_result.duration_seconds = (
                datetime.now() - start_time
            ).total_seconds()
            return checks_result

        result = ReleaseResult(
            success=True,
            version=self.config.version,
            checks=checks_result.checks,
            ci_provider_name=checks_result.ci_provider_name,
            registry_provider_name=checks_result.registry_provider_name,
        )

        # Create tag if configured
        if self.config.create_tag:
            tag_result = self.create_release_tag()
            if not tag_result.success:
                result.success = False
                result.error = tag_result.error
                result.duration_seconds = (datetime.now() - start_time).total_seconds()
                return result
            result.tag_created = tag_result.tag_created
            result.url = tag_result.url

        # Publish if configured
        if self.config.publish and result.tag_created:
            pub_result = self.publish_release()
            if not pub_result.success:
                result.success = False
                result.error = pub_result.error
                result.duration_seconds = (datetime.now() - start_time).total_seconds()
                return result
            result.published = pub_result.published
            result.url = pub_result.url

        # Push tag to remote if everything succeeded
        if result.tag_created and result.success:
            self._push_tag_to_remote(f"{self.config.tag_prefix}{self.config.version}")

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    # Helper methods

    def _check_git_clean(self) -> bool:
        """Check if git working directory is clean."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            return not result.stdout.strip()
        except subprocess.CalledProcessError:
            return False

    def _get_current_branch(self) -> Optional[str]:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def _check_ci_passes(self) -> PreReleaseCheck:
        """Check if CI passes on current branch."""
        ci = self.get_ci_provider()
        if not ci:
            return PreReleaseCheck(
                check_name="ci_status",
                passed=False,
                message="No CI provider available",
            )

        if not ci.is_available():
            return PreReleaseCheck(
                check_name="ci_status",
                passed=False,
                message=f"CI provider '{ci.get_provider_name()}' not available/authenticated",
            )

        try:
            run = ci.get_status(self.config.branch)
            if not run:
                return PreReleaseCheck(
                    check_name="ci_status",
                    passed=False,
                    message=f"No CI runs found on branch '{self.config.branch}'",
                )

            if run.status != RunStatus.COMPLETED:
                return PreReleaseCheck(
                    check_name="ci_status",
                    passed=False,
                    message=f"CI still running on branch '{self.config.branch}'",
                    details=f"Run {run.id}: {run.status.value}",
                )

            if run.conclusion == RunConclusion.SUCCESS:
                return PreReleaseCheck(
                    check_name="ci_status",
                    passed=True,
                    message=f"CI passes on '{self.config.branch}' ({ci.get_provider_name()})",
                    details=f"Run {run.id}: {run.conclusion.value}",
                )
            else:
                return PreReleaseCheck(
                    check_name="ci_status",
                    passed=False,
                    message=f"CI failed on '{self.config.branch}'",
                    details=f"Run {run.id}: {run.conclusion.value}",
                )

        except Exception as e:
            return PreReleaseCheck(
                check_name="ci_status",
                passed=False,
                message=f"Failed to check CI status: {e}",
            )

    def _validate_version_format(self) -> bool:
        """Validate semantic version format."""
        import re

        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, self.config.version))

    def _push_tag_to_remote(self, tag_name: str) -> bool:
        """Push tag to remote repository."""
        try:
            subprocess.run(
                ["git", "push", "origin", tag_name],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
