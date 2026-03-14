"""Check external tool dependencies for marketplace agents."""

import importlib.metadata
import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional

from .metadata import ToolDependency

logger = logging.getLogger(__name__)


@dataclass
class ToolCheckResult:
    """Result of checking a single tool dependency."""

    name: str
    present: bool
    found_version: Optional[str] = None
    required_version: Optional[str] = None
    remediation: str = ""
    version_unverifiable: bool = False


class ToolDependencyChecker:
    """Check whether external tool dependencies are satisfied."""

    def check(self, deps: Dict[str, ToolDependency]) -> List[ToolCheckResult]:
        """Check all tool dependencies. Returns list of results."""
        return [self.check_one(name, dep) for name, dep in deps.items()]

    def check_one(self, name: str, dep: ToolDependency) -> ToolCheckResult:
        """Check a single tool dependency."""
        try:
            if dep.type == "python":
                return self._check_python(name, dep)
            elif dep.type in ("binary", "npm-global", "venv"):
                return self._check_binary(name, dep)
            elif dep.type == "docker":
                return self._check_docker(name, dep)
            else:
                logger.warning("Unknown tool dependency type: %s", dep.type)
                return ToolCheckResult(
                    name=name,
                    present=False,
                    remediation=f"Unknown type '{dep.type}' for {name}",
                )
        except Exception as e:
            logger.debug("Error checking %s: %s", name, e)
            return ToolCheckResult(
                name=name,
                present=False,
                remediation=dep.install_hint or f"Install {name}",
            )

    def _check_python(self, name: str, dep: ToolDependency) -> ToolCheckResult:
        """Check a Python package dependency."""
        package = dep.package or name
        try:
            version = importlib.metadata.version(package)
            return ToolCheckResult(
                name=name,
                present=True,
                found_version=version,
                required_version=dep.min_version,
            )
        except Exception:
            hint = dep.install_hint or f"pip install {package}"
            return ToolCheckResult(name=name, present=False, remediation=hint)

    def _check_binary(self, name: str, dep: ToolDependency) -> ToolCheckResult:
        """Check a binary/executable dependency."""
        # "venv" type checks if the executable is on PATH (basic check; full venv
        # isolation detection is a future improvement)
        path = shutil.which(name)
        if not path:
            if dep.type == "npm-global":
                hint = dep.install_hint or f"npm install -g {name}"
            else:
                hint = (
                    dep.install_hint
                    or f"Install {name} using your system package manager"
                )
            return ToolCheckResult(name=name, present=False, remediation=hint)

        found_version = None
        version_unverifiable = False
        if dep.min_version:
            try:
                result = subprocess.run(
                    [name, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                found_version = result.stdout.strip() or result.stderr.strip()
            except Exception:
                version_unverifiable = True

        return ToolCheckResult(
            name=name,
            present=True,
            found_version=found_version,
            required_version=dep.min_version,
            version_unverifiable=version_unverifiable,
        )

    def _check_docker(self, name: str, dep: ToolDependency) -> ToolCheckResult:
        """Check a Docker image dependency."""
        if not shutil.which("docker"):
            hint = (
                dep.install_hint
                or "Install Docker: https://docs.docker.com/get-docker/"
            )
            return ToolCheckResult(name=name, present=False, remediation=hint)

        try:
            result = subprocess.run(
                ["docker", "image", "inspect", name],
                capture_output=True,
                timeout=10,
            )
            present = result.returncode == 0
            hint = "" if present else (dep.install_hint or f"docker pull {name}")
            return ToolCheckResult(name=name, present=present, remediation=hint)
        except Exception:
            hint = dep.install_hint or f"docker pull {name}"
            return ToolCheckResult(name=name, present=False, remediation=hint)
