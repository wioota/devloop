# Tool Dependency Resolution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a user installs a marketplace agent, check its declared external tool dependencies (e.g. `bandit`, `shellcheck`) and warn with remediation commands if any are missing — without blocking installation or auto-installing anything.

**Architecture:** Add `ToolDependency` to the metadata schema, implement a `ToolDependencyChecker` in a new file, and call it from `AgentInstaller.install()` after successful agent install. Check-only, never install.

**Tech Stack:** Python stdlib only — `shutil.which`, `importlib.metadata`, `subprocess` for version checks.

---

### Task 1: Add `ToolDependency` to metadata schema

**Files:**
- Modify: `src/devloop/marketplace/metadata.py`
- Test: `tests/integration/test_marketplace_metadata.py`

**Step 1: Write failing test**

Add to `tests/integration/test_marketplace_metadata.py`:

```python
def test_tool_dependency_from_dict():
    from devloop.marketplace.metadata import ToolDependency
    dep = ToolDependency.from_dict({
        "type": "python",
        "minVersion": "1.7.0",
        "package": "bandit",
        "install": "pip install bandit",
    })
    assert dep.type == "python"
    assert dep.min_version == "1.7.0"
    assert dep.package == "bandit"
    assert dep.install_hint == "pip install bandit"


def test_agent_metadata_tool_dependencies_roundtrip():
    from devloop.marketplace.metadata import AgentMetadata, ToolDependency
    agent = AgentMetadata(
        name="test-agent",
        version="1.0.0",
        description="Test",
        author="Author",
        license="MIT",
        homepage="https://example.com",
        tool_dependencies={
            "bandit": ToolDependency(type="python", package="bandit", min_version="1.7.0"),
            "shellcheck": ToolDependency(type="binary", install_hint="apt-get install shellcheck"),
        },
    )
    data = agent.to_dict()
    assert "toolDependencies" in data
    assert "bandit" in data["toolDependencies"]
    roundtripped = AgentMetadata.from_dict(data)
    assert "bandit" in roundtripped.tool_dependencies
    assert roundtripped.tool_dependencies["bandit"].type == "python"
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/integration/test_marketplace_metadata.py::test_tool_dependency_from_dict tests/integration/test_marketplace_metadata.py::test_agent_metadata_tool_dependencies_roundtrip -v
```
Expected: FAIL — `ToolDependency` not importable, `tool_dependencies` not a field.

**Step 3: Implement**

In `src/devloop/marketplace/metadata.py`, add after the `Dependency` dataclass:

```python
@dataclass
class ToolDependency:
    """External tool dependency (CLI binary, Python package, etc.)."""

    type: str  # "python" | "binary" | "npm-global" | "venv" | "docker"
    package: Optional[str] = None      # pip package name (python type)
    min_version: Optional[str] = None  # e.g. "1.7.0"
    install_hint: Optional[str] = None # e.g. "apt-get install shellcheck"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolDependency":
        return cls(
            type=data["type"],
            package=data.get("package"),
            min_version=data.get("minVersion"),
            install_hint=data.get("install"),
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"type": self.type}
        if self.package:
            d["package"] = self.package
        if self.min_version:
            d["minVersion"] = self.min_version
        if self.install_hint:
            d["install"] = self.install_hint
        return d
```

Add `tool_dependencies` field to `AgentMetadata`:

```python
tool_dependencies: Dict[str, ToolDependency] = field(default_factory=dict)
```

Update `AgentMetadata.from_dict()` — add before `return cls(...)`:

```python
tool_deps = {}
for tool_name, tool_data in data.get("toolDependencies", {}).items():
    tool_deps[tool_name] = ToolDependency.from_dict(tool_data)
```

Pass `tool_dependencies=tool_deps` to `cls(...)`.

Update `AgentMetadata.to_dict()` — add before `return data`:

```python
if self.tool_dependencies:
    data["toolDependencies"] = {
        name: dep.to_dict() for name, dep in self.tool_dependencies.items()
    }
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/integration/test_marketplace_metadata.py::test_tool_dependency_from_dict tests/integration/test_marketplace_metadata.py::test_agent_metadata_tool_dependencies_roundtrip -v
```
Expected: PASS

**Step 5: Run full metadata tests to check for regressions**

```bash
poetry run pytest tests/integration/test_marketplace_metadata.py -v
```
Expected: All PASS

**Step 6: Commit**

```bash
git add src/devloop/marketplace/metadata.py tests/integration/test_marketplace_metadata.py
git commit -m "feat: add ToolDependency to AgentMetadata schema (claude-agents-b0dc)"
```

---

### Task 2: Implement `ToolDependencyChecker`

**Files:**
- Create: `src/devloop/marketplace/tool_checker.py`
- Create: `tests/unit/marketplace/test_tool_checker.py` (create dir if needed)

**Step 1: Write failing tests**

Create `tests/unit/marketplace/__init__.py` (empty).

Create `tests/unit/marketplace/test_tool_checker.py`:

```python
"""Tests for ToolDependencyChecker."""
from unittest.mock import patch, MagicMock
import pytest
from devloop.marketplace.tool_checker import ToolDependencyChecker, ToolCheckResult
from devloop.marketplace.metadata import ToolDependency


@pytest.fixture
def checker():
    return ToolDependencyChecker()


def test_binary_present(checker):
    dep = ToolDependency(type="binary")
    with patch("shutil.which", return_value="/usr/bin/shellcheck"):
        result = checker.check_one("shellcheck", dep)
    assert result.present is True
    assert result.name == "shellcheck"


def test_binary_missing(checker):
    dep = ToolDependency(type="binary", install_hint="apt-get install shellcheck")
    with patch("shutil.which", return_value=None):
        result = checker.check_one("shellcheck", dep)
    assert result.present is False
    assert result.remediation == "apt-get install shellcheck"


def test_binary_missing_no_hint(checker):
    dep = ToolDependency(type="binary")
    with patch("shutil.which", return_value=None):
        result = checker.check_one("mytool", dep)
    assert result.present is False
    assert "mytool" in result.remediation


def test_python_package_present(checker):
    dep = ToolDependency(type="python", package="bandit", min_version="1.7.0")
    with patch("importlib.metadata.version", return_value="1.8.0"):
        result = checker.check_one("bandit", dep)
    assert result.present is True
    assert result.found_version == "1.8.0"


def test_python_package_missing(checker):
    dep = ToolDependency(type="python", package="bandit")
    with patch("importlib.metadata.version", side_effect=Exception("not found")):
        result = checker.check_one("bandit", dep)
    assert result.present is False
    assert "pip install bandit" in result.remediation


def test_npm_global_present(checker):
    dep = ToolDependency(type="npm-global")
    with patch("shutil.which", return_value="/usr/local/bin/prettier"):
        result = checker.check_one("prettier", dep)
    assert result.present is True


def test_npm_global_missing(checker):
    dep = ToolDependency(type="npm-global")
    with patch("shutil.which", return_value=None):
        result = checker.check_one("prettier", dep)
    assert result.present is False
    assert "npm install -g prettier" in result.remediation


def test_docker_image_present(checker):
    dep = ToolDependency(type="docker")
    with patch("shutil.which", return_value="/usr/bin/docker"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = checker.check_one("ubuntu:22.04", dep)
    assert result.present is True


def test_docker_missing_daemon(checker):
    dep = ToolDependency(type="docker")
    with patch("shutil.which", return_value=None):
        result = checker.check_one("ubuntu:22.04", dep)
    assert result.present is False
    assert "docker" in result.remediation.lower()


def test_check_multiple(checker):
    deps = {
        "bandit": ToolDependency(type="python", package="bandit"),
        "shellcheck": ToolDependency(type="binary"),
    }
    with patch("importlib.metadata.version", return_value="1.8.0"):
        with patch("shutil.which", return_value=None):
            results = checker.check(deps)
    assert len(results) == 2
    bandit = next(r for r in results if r.name == "bandit")
    shellcheck = next(r for r in results if r.name == "shellcheck")
    assert bandit.present is True
    assert shellcheck.present is False


def test_version_check_failure_treated_as_present(checker):
    """If we can't determine version, still mark as present."""
    dep = ToolDependency(type="binary", min_version="1.0.0")
    with patch("shutil.which", return_value="/usr/bin/mytool"):
        with patch("subprocess.run", side_effect=Exception("timeout")):
            result = checker.check_one("mytool", dep)
    assert result.present is True
    assert result.version_unverifiable is True
```

**Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/unit/marketplace/test_tool_checker.py -v
```
Expected: FAIL — module not found.

**Step 3: Implement `tool_checker.py`**

Create `src/devloop/marketplace/tool_checker.py`:

```python
"""Check external tool dependencies for marketplace agents."""

import importlib.metadata
import shutil
import subprocess
import logging
from dataclasses import dataclass, field
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
                logger.warning(f"Unknown tool dependency type: {dep.type}")
                return ToolCheckResult(name=name, present=False,
                                       remediation=f"Unknown type '{dep.type}' for {name}")
        except Exception as e:
            logger.debug(f"Error checking {name}: {e}")
            return ToolCheckResult(name=name, present=False,
                                   remediation=dep.install_hint or f"Install {name}")

    def _check_python(self, name: str, dep: ToolDependency) -> ToolCheckResult:
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
        path = shutil.which(name)
        if not path:
            if dep.type == "npm-global":
                hint = dep.install_hint or f"npm install -g {name}"
            else:
                hint = dep.install_hint or f"Install {name} using your system package manager"
            return ToolCheckResult(name=name, present=False, remediation=hint)

        # Try version check (best-effort)
        found_version = None
        version_unverifiable = False
        if dep.min_version:
            try:
                result = subprocess.run(
                    [name, "--version"], capture_output=True, text=True, timeout=5
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
        if not shutil.which("docker"):
            hint = dep.install_hint or "Install Docker: https://docs.docker.com/get-docker/"
            return ToolCheckResult(name=name, present=False, remediation=hint)

        try:
            result = subprocess.run(
                ["docker", "image", "inspect", name],
                capture_output=True, timeout=10
            )
            present = result.returncode == 0
            hint = "" if present else (dep.install_hint or f"docker pull {name}")
            return ToolCheckResult(name=name, present=present, remediation=hint)
        except Exception:
            return ToolCheckResult(name=name, present=True, version_unverifiable=True)
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest tests/unit/marketplace/test_tool_checker.py -v
```
Expected: All PASS

**Step 5: Commit**

```bash
git add src/devloop/marketplace/tool_checker.py tests/unit/marketplace/__init__.py tests/unit/marketplace/test_tool_checker.py
git commit -m "feat: implement ToolDependencyChecker for external tool deps (claude-agents-b0dc)"
```

---

### Task 3: Integrate checker into installer

**Files:**
- Modify: `src/devloop/marketplace/installer.py`
- Modify: `tests/integration/test_marketplace_installer.py`

**Step 1: Write failing test**

Add to `tests/integration/test_marketplace_installer.py`:

```python
def test_install_warns_on_missing_tool_deps(installer, registry):
    """Install succeeds but warns when tool deps are missing."""
    from devloop.marketplace.metadata import ToolDependency
    from unittest.mock import patch

    # Add agent with tool deps to registry
    agent_with_tools = AgentMetadata(
        name="agent-with-tools",
        version="1.0.0",
        description="Agent needing external tools",
        author="Author",
        license="MIT",
        homepage="https://example.com",
        tool_dependencies={
            "shellcheck": ToolDependency(
                type="binary",
                install_hint="apt-get install shellcheck",
            ),
        },
    )
    registry.register_agent(agent_with_tools)

    with patch("shutil.which", return_value=None):
        success, message = installer.install("agent-with-tools")

    assert success is True  # install always succeeds
    assert "shellcheck" in message
    assert "apt-get install shellcheck" in message


def test_install_no_warning_when_tool_deps_satisfied(installer, registry):
    """No warning when all tool deps are present."""
    from devloop.marketplace.metadata import ToolDependency
    from unittest.mock import patch

    agent_with_tools = AgentMetadata(
        name="agent-tools-ok",
        version="1.0.0",
        description="Agent with satisfied tools",
        author="Author",
        license="MIT",
        homepage="https://example.com",
        tool_dependencies={
            "black": ToolDependency(type="binary"),
        },
    )
    registry.register_agent(agent_with_tools)

    with patch("shutil.which", return_value="/usr/bin/black"):
        success, message = installer.install("agent-tools-ok")

    assert success is True
    assert "warning" not in message.lower()
    assert "missing" not in message.lower()
```

**Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/integration/test_marketplace_installer.py::TestAgentInstaller::test_install_warns_on_missing_tool_deps tests/integration/test_marketplace_installer.py::TestAgentInstaller::test_install_no_warning_when_tool_deps_satisfied -v
```
Expected: FAIL

**Step 3: Integrate into `installer.py`**

Add import at top of `src/devloop/marketplace/installer.py`:

```python
from .tool_checker import ToolDependencyChecker
```

Add `_check_tool_dependencies` method to `AgentInstaller`:

```python
def _check_tool_dependencies(self, agent: AgentMetadata) -> List[str]:
    """Check tool deps and return list of warning strings for missing ones."""
    if not agent.tool_dependencies:
        return []

    checker = ToolDependencyChecker()
    results = checker.check(agent.tool_dependencies)
    warnings = []
    for result in results:
        if not result.present:
            msg = f"  Missing tool '{result.name}'"
            if result.remediation:
                msg += f": {result.remediation}"
            warnings.append(msg)
        elif result.version_unverifiable and result.required_version:
            warnings.append(
                f"  Tool '{result.name}' found but version could not be verified "
                f"(requires >={result.required_version})"
            )
    return warnings
```

Update `install()` method — after the `self.registry_client.download_agent(agent_name)` line, add:

```python
# Check tool dependencies (warn only, never block)
tool_warnings = self._check_tool_dependencies(agent)
base_msg = f"Successfully installed {agent_name}@{agent.version} and dependencies"
if tool_warnings:
    warning_str = "\n".join(tool_warnings)
    return True, (
        f"{base_msg}\n\n"
        f"⚠ Missing tool dependencies — install manually:\n{warning_str}"
    )
return True, base_msg
```

Remove the old bare `return True, ...` at the end of the try block.

**Step 4: Run new tests**

```bash
poetry run pytest tests/integration/test_marketplace_installer.py::TestAgentInstaller::test_install_warns_on_missing_tool_deps tests/integration/test_marketplace_installer.py::TestAgentInstaller::test_install_no_warning_when_tool_deps_satisfied -v
```
Expected: PASS

**Step 5: Run full installer test suite**

```bash
poetry run pytest tests/integration/test_marketplace_installer.py -v
```
Expected: All PASS

**Step 6: Commit**

```bash
git add src/devloop/marketplace/installer.py tests/integration/test_marketplace_installer.py
git commit -m "feat: warn on missing tool deps after agent install (claude-agents-b0dc)"
```

---

### Task 4: Full verification and close

**Step 1: Run full test suite**

```bash
poetry run pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: All PASS (or pre-existing failures only)

**Step 2: Run linting**

```bash
poetry run black src/devloop/marketplace/tool_checker.py src/devloop/marketplace/metadata.py src/devloop/marketplace/installer.py tests/unit/marketplace/test_tool_checker.py tests/integration/test_marketplace_installer.py tests/integration/test_marketplace_metadata.py
poetry run ruff check src/devloop/marketplace/tool_checker.py src/devloop/marketplace/metadata.py src/devloop/marketplace/installer.py --fix
poetry run mypy src/devloop/marketplace/tool_checker.py src/devloop/marketplace/metadata.py src/devloop/marketplace/installer.py
```
Expected: No errors

**Step 3: Commit any formatting fixes**

```bash
git add -u
git commit -m "chore: format tool dependency files"
```
(skip if nothing changed)

**Step 4: Push and close issue**

```bash
git push origin main
bd close claude-agents-b0dc --reason "Implemented ToolDependencyChecker with schema, checker, and installer integration"
git add .beads/issues.jsonl
git commit -m "chore: close claude-agents-b0dc"
git push origin main
```
