# Claude Agents Coding Rules & Patterns

## Overview

Documented patterns, rules, and lessons learned from claude-agents development to prevent recurring issues and ensure consistent code quality.

## Core Patterns

### 1. Tool Availability & Graceful Degradation

**Problem:** Agents fail when external tools aren't installed
**Pattern:**
```python
async def _run_tool(self, file_path: Path) -> Optional[ToolResult]:
    """Run external tool with availability checking."""
    try:
        # Check if tool is available
        result = subprocess.run(
            [sys.executable, "-c", "import tool_name"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return ToolResult("tool_name", [], ["Tool not installed - run: pip install tool_name"])

        # Proceed with tool execution
        # ... tool execution code ...

    except subprocess.TimeoutExpired:
        return ToolResult("tool_name", [], ["Tool check timeout"])
    except Exception as e:
        return ToolResult("tool_name", [], [f"Tool execution error: {str(e)}"])
```

**Rule:** Always check tool availability before execution and provide helpful installation messages.

### 2. Configuration Validation & Defaults

**Problem:** Invalid configurations cause runtime failures
**Pattern:**
```python
@dataclass
class AgentConfig:
    """Configuration with validation and defaults."""

    enabled_tools: List[str] = None
    severity_threshold: str = "medium"
    max_issues: int = 50

    def __post_init__(self):
        # Set defaults for None values
        if self.enabled_tools is None:
            self.enabled_tools = ["default_tool"]

        # Validate configuration
        if self.severity_threshold not in ["low", "medium", "high"]:
            raise ValueError(f"Invalid severity_threshold: {self.severity_threshold}")

        if not isinstance(self.max_issues, int) or self.max_issues < 1:
            raise ValueError("max_issues must be a positive integer")
```

**Rule:** Use dataclasses with `__post_init__` for configuration validation and default setting.

### 3. Async Error Handling

**Problem:** Unhandled exceptions in async code cause silent failures
**Pattern:**
```python
async def handle(self, event: Event) -> AgentResult:
    """Handle events with comprehensive error handling."""
    try:
        # Main logic here
        result = await self._process_event(event)
        return AgentResult(
            agent_name=self.name,
            success=True,
            data=result
        )
    except FileNotFoundError as e:
        return AgentResult(
            agent_name=self.name,
            success=False,
            message=f"File not found: {e.filename}"
        )
    except PermissionError as e:
        return AgentResult(
            agent_name=self.name,
            success=False,
            message=f"Permission denied: {e.filename}"
        )
    except Exception as e:
        # Log unexpected errors
        self.logger.error(f"Unexpected error in {self.name}: {e}", exc_info=True)
        return AgentResult(
            agent_name=self.name,
            success=False,
            message=f"Internal error: {str(e)}"
        )
```

**Rule:** Wrap all async operations in try-catch blocks with specific exception handling.

### 4. Path Handling & Cross-Platform Compatibility

**Problem:** Path operations fail on different platforms
**Pattern:**
```python
from pathlib import Path

def resolve_project_path(self, file_path: str) -> Path:
    """Resolve file path relative to project root."""
    path = Path(file_path)

    # Convert to absolute path if relative
    if not path.is_absolute():
        path = self.project_root / path

    # Resolve any symlinks and normalize
    resolved = path.resolve()

    # Ensure path is within project root for security
    try:
        resolved.relative_to(self.project_root)
    except ValueError:
        raise ValueError(f"Path outside project root: {resolved}")

    return resolved

def safe_read_file(self, file_path: Path) -> Optional[str]:
    """Safely read file with error handling."""
    try:
        # Check file exists and is a regular file
        if not file_path.exists():
            return None
        if not file_path.is_file():
            return None

        # Read with explicit encoding
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    except UnicodeDecodeError:
        # Try alternative encodings
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except UnicodeDecodeError:
            return None
    except (OSError, IOError) as e:
        self.logger.warning(f"Failed to read file {file_path}: {e}")
        return None
```

**Rule:** Always use Path objects, resolve paths, validate they're within project bounds, and handle encoding issues.

### 5. Event-Driven Architecture Patterns

**Problem:** Event handling inconsistencies and missing event types
**Pattern:**
```python
class Agent(ABC):
    """Base agent with consistent event handling."""

    def __init__(self, name: str, triggers: List[str], event_bus: EventBus):
        self.name = name
        self.triggers = triggers  # Explicitly declare supported events
        self.event_bus = event_bus
        self._running = False
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    async def handle(self, event: Event) -> AgentResult:
        """Handle a single event. Must be implemented by subclasses."""
        pass

    async def _handle_event_safe(self, event: Event) -> None:
        """Safe event handling with logging and error recovery."""
        if event.type not in self.triggers:
            return  # Silently ignore unsupported events

        try:
            start_time = time.time()
            result = await self.handle(event)
            duration = time.time() - start_time

            # Log result
            if result.success:
                self.logger.info(f"Processed {event.type} in {duration:.2f}s")
            else:
                self.logger.warning(f"Failed to process {event.type}: {result.message}")

        except Exception as e:
            self.logger.error(f"Critical error handling {event.type}: {e}", exc_info=True)
```

**Rule:** Define supported event types explicitly, handle events safely, and log all operations.

### 6. Result Consistency & Type Safety

**Problem:** Inconsistent result formats across agents
**Pattern:**
```python
@dataclass
class AgentResult:
    """Standardized agent result format."""

    agent_name: str
    success: bool
    duration: float = 0.0
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "success": self.success,
            "duration": self.duration,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "timestamp": datetime.now().isoformat()
        }

# Usage in agents
return AgentResult(
    agent_name=self.name,
    success=True,
    duration=processing_time,
    message="Analysis completed successfully",
    data={
        "issues_found": len(issues),
        "issues": issues,
        "tool_used": tool_name
    }
)
```

**Rule:** Use consistent result objects with standardized fields and serialization methods.

### 7. Configuration Import Safety

**Problem:** Import errors when optional dependencies are missing
**Pattern:**
```python
def safe_import(module_name: str, package_name: str = None) -> Optional[Any]:
    """Safely import optional modules."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        if package_name:
            print(f"Optional dependency '{package_name}' not installed. Run: pip install {package_name}")
        return None

# Usage
radon = safe_import("radon", "radon")
mypy = safe_import("mypy", "mypy")

class PerformanceProfilerAgent(Agent):
    def _check_tools(self):
        """Check which tools are available."""
        self.radon_available = radon is not None
        self.mypy_available = mypy is not None

        if not self.radon_available:
            self.logger.warning("Radon not available - complexity analysis disabled")
```

**Rule:** Use safe imports for optional dependencies and gracefully degrade functionality.

### 8. Logging Standards

**Problem:** Inconsistent logging across components
**Pattern:**
```python
import logging

class Agent(ABC):
    def __init__(self, name: str, triggers: List[str], event_bus: EventBus):
        self.logger = logging.getLogger(f"agent.{name}")
        # Configure logger level based on environment
        if os.getenv("DEBUG_AGENTS"):
            self.logger.setLevel(logging.DEBUG)

    def log_operation(self, operation: str, **context):
        """Standardized operation logging."""
        self.logger.info(f"{operation}", extra={
            "agent": self.name,
            "operation": operation,
            **context
        })

    def log_error(self, error: Exception, operation: str = "", **context):
        """Standardized error logging."""
        self.logger.error(
            f"{operation or 'Operation'} failed: {error}",
            exc_info=True,
            extra={
                "agent": self.name,
                "error_type": type(error).__name__,
                **context
            }
        )
```

**Rule:** Use structured logging with consistent formats and appropriate log levels.

### 9. Resource Management

**Problem:** Resource leaks in long-running agents
**Pattern:**
```python
class Agent(ABC):
    async def start(self) -> None:
        """Start agent with resource initialization."""
        if self._running:
            return

        try:
            # Initialize resources
            self._running = True
            self._event_queue = asyncio.Queue()
            self._background_tasks = set()

            # Start background processing
            task = asyncio.create_task(self._process_events())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

            self.logger.info(f"Agent {self.name} started")

        except Exception as e:
            self._running = False
            await self._cleanup_resources()
            raise

    async def stop(self) -> None:
        """Stop agent with proper cleanup."""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Cleanup resources
        await self._cleanup_resources()
        self.logger.info(f"Agent {self.name} stopped")

    async def _cleanup_resources(self) -> None:
        """Cleanup agent resources."""
        # Close connections, clear caches, etc.
        pass
```

**Rule:** Implement proper resource lifecycle management with cleanup in all exit paths.

### 11. Loop Prevention in File-Modifying Agents

**Problem:** Agents that modify files can trigger infinite loops when filesystem events cause re-processing
**Pattern:**
```python
class FileModifyingAgent(Agent):
    def __init__(self, ...):
        super().__init__(...)
        # Loop prevention state
        self._recent_operations = {}  # file_path -> timestamps
        self._loop_detection_window = 10  # seconds
        self._max_consecutive_ops = 3  # per file per window
        self._operation_timeout = 30  # seconds

    def _detect_operation_loop(self, path: Path) -> bool:
        """Detect if we're in an operation loop for this file."""
        import time

        file_key = str(path.resolve())
        now = time.time()

        # Clean up old entries
        self._recent_operations = {
            k: v for k, v in self._recent_operations.items()
            if now - v < self._loop_detection_window
        }

        # Count recent operations for this file
        recent_ops = [
            ts for file_path, ts in self._recent_operations.items()
            if file_path == file_key and now - ts < self._loop_detection_window
        ]

        if len(recent_ops) >= self._max_consecutive_ops:
            self.logger.warning(f"Operation loop detected for {path.name}")
            return True
        return False

    def _record_operation(self, path: Path) -> None:
        """Record that we just operated on this file."""
        import time
        file_key = str(path.resolve())
        self._recent_operations[file_key] = time.time()

    async def _run_operation_with_timeout(self, operation_coro):
        """Run operation with timeout protection."""
        try:
            return await asyncio.wait_for(operation_coro, timeout=self._operation_timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation timed out after {self._operation_timeout}s")

    async def handle(self, event: Event) -> AgentResult:
        # Extract file path and validate
        path = Path(event.payload.get("path"))

        # Loop prevention check
        if self._detect_operation_loop(path):
            return AgentResult(
                agent_name=self.name,
                success=False,
                message=f"Prevented operation loop for {path.name}",
                error="OPERATION_LOOP_DETECTED"
            )

        # Idempotency check - verify operation is actually needed
        if not await self._needs_operation(path):
            return AgentResult(
                agent_name=self.name,
                success=True,
                message=f"{path.name} already processed"
            )

        # Run operation with timeout
        try:
            result = await self._run_operation_with_timeout(self._perform_operation(path))
            self._record_operation(path)  # Only record on success
            return result
        except TimeoutError as e:
            return AgentResult(agent_name=self.name, success=False, error=str(e))
```

**Rule:** File-modifying agents must implement loop detection, idempotency checks, and timeout protection to prevent infinite processing cycles.

### 12. Testing Patterns

**Problem:** Inconsistent and incomplete testing
**Pattern:**
```python
# tests/test_agents/test_security_scanner.py
import pytest
from unittest.mock import AsyncMock, patch
from claude_agents.agents.security_scanner import SecurityScannerAgent

@pytest.fixture
def security_agent():
    """Create security scanner agent for testing."""
    config = {
        "enabled_tools": ["bandit"],
        "severity_threshold": "medium",
        "confidence_threshold": "medium"
    }
    return SecurityScannerAgent(config, mock_event_bus())

@pytest.mark.asyncio
async def test_tool_availability_check(security_agent):
    """Test that agent checks tool availability."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=0)

        result = await security_agent._run_bandit(Path("test.py"))
        assert result is not None
        assert result.tool == "bandit"

@pytest.mark.asyncio
async def test_graceful_tool_missing(security_agent):
    """Test graceful handling when tool is not installed."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=1)

        result = await security_agent._run_bandit(Path("test.py"))
        assert result is not None
        assert "not installed" in result.errors[0]

@pytest.mark.asyncio
async def test_result_filtering(security_agent):
    """Test that results are filtered by severity/confidence."""
    mock_issues = [
        {"severity": "high", "confidence": "high", "code": "B101"},
        {"severity": "low", "confidence": "low", "code": "B102"},
    ]

    security_agent.config.severity_threshold = "medium"
    filtered = security_agent._filter_issues(mock_issues)

    assert len(filtered) == 1
    assert filtered[0]["severity"] == "high"
```

**Rule:** Write comprehensive tests covering success paths, error conditions, and edge cases. Use mocks for external dependencies.

## Implementation Checklist

When creating new agents, ensure:

- [ ] Tool availability checking with helpful error messages
- [ ] Comprehensive configuration validation
- [ ] Async error handling with specific exception types
- [ ] Cross-platform path handling
- [ ] Consistent result formatting
- [ ] Proper resource cleanup
- [ ] Structured logging
- [ ] **Loop prevention for file-modifying agents** (loop detection, idempotency checks, timeouts)
- [ ] Unit tests with >80% coverage
- [ ] Integration tests for workflows
- [ ] Documentation following existing patterns

## Code Review Checklist

Before committing code:

- [ ] All tool imports are wrapped in availability checks
- [ ] Configuration uses dataclasses with validation
- [ ] Async functions have comprehensive error handling
- [ ] Paths are resolved and validated
- [ ] Results follow AgentResult format
- [ ] Logging is consistent and informative
- [ ] Tests exist and pass
- [ ] Documentation is updated
- [ ] No hardcoded paths or assumptions about environment
