# Agent Examples

Real-world examples of DevLoop agents, from simple to advanced.

## Table of Contents

1. [Simple Examples](#simple-examples)
2. [Medium Examples](#medium-examples)
3. [Advanced Examples](#advanced-examples)
4. [Specialized Examples](#specialized-examples)

## Simple Examples

### 1. Echo Agent (Minimal Example)

The simplest possible agent - just logs events:

```python
"""Echo agent - logs all received events."""

from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class EchoAgent(Agent):
    """Simple agent that echoes events."""

    async def handle(self, event: Event) -> AgentResult:
        """Log the event."""
        message = f"Received {event.type} event"
        
        # Add details if available
        if "path" in event.payload:
            message += f": {event.payload['path']}"
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message=message,
            data=event.payload,
        )
```

**Key Concepts:**
- Minimal implementation
- Direct event payload echoing
- No error handling needed

**Testing:**
```python
import pytest
from devloop.core.event import Event


@pytest.mark.asyncio
async def test_echo_agent(mock_event_bus):
    agent = EchoAgent(
        name="echo",
        triggers=["file:save"],
        event_bus=mock_event_bus,
    )
    
    event = Event(
        type="file:save",
        source="fs",
        payload={"path": "test.py"}
    )
    
    result = await agent.handle(event)
    
    assert result.success
    assert "test.py" in result.message
```

---

### 2. File Watcher Agent

Count files and lines in modified files:

```python
"""File watcher - counts files and lines."""

from pathlib import Path
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class FileWatcherAgent(Agent):
    """Watch for file changes and report statistics."""

    async def handle(self, event: Event) -> AgentResult:
        """Check the modified file."""
        
        # Get file path
        file_path = event.payload.get("path", "")
        if not file_path:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="No file path",
            )
        
        # Check if file exists
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message=f"Not a file: {file_path}",
            )
        
        try:
            # Count lines
            content = path.read_text()
            lines = len(content.splitlines())
            size = path.stat().st_size
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.01,
                message=f"{file_path}: {lines} lines, {size} bytes",
                data={
                    "file": file_path,
                    "lines": lines,
                    "bytes": size,
                }
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                error=f"Failed to read file: {e}",
            )
```

**Key Concepts:**
- File path handling
- Safe file reading
- Error recovery

---

## Medium Examples

### 3. Pattern Matcher Agent

Check files for specific patterns:

```python
"""Pattern matcher - finds matching lines."""

import re
from pathlib import Path
from typing import List
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class PatternMatcherAgent(Agent):
    """Find lines matching a pattern."""
    
    def __init__(self, name: str, triggers: List[str], pattern: str, **kwargs):
        super().__init__(name, triggers, **kwargs)
        self.pattern = re.compile(pattern)
    
    async def handle(self, event: Event) -> AgentResult:
        """Find pattern matches in file."""
        
        file_path = event.payload.get("path")
        if not file_path:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="No file",
                data={"matches": []},
            )
        
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="Not a file",
                data={"matches": []},
            )
        
        try:
            content = path.read_text()
        except Exception:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="Skipped (binary)",
                data={"matches": []},
            )
        
        # Find matches
        matches = []
        for i, line in enumerate(content.splitlines(), 1):
            if self.pattern.search(line):
                matches.append({
                    "line": i,
                    "content": line.strip(),
                })
        
        success = len(matches) == 0  # Success if no matches found
        message = f"Found {len(matches)} matches" if matches else "No matches"
        
        return AgentResult(
            agent_name=self.name,
            success=success,
            duration=0.02,
            message=message,
            data={
                "file": file_path,
                "pattern": self.pattern.pattern,
                "matches": matches,
            }
        )
```

**Configuration:**
```json
{
  "agents": {
    "pattern-matcher": {
      "enabled": true,
      "module": "examples.pattern_matcher",
      "class": "PatternMatcherAgent",
      "triggers": ["file:save"],
      "config": {
        "pattern": "TODO|FIXME|XXX"
      }
    }
  }
}
```

**Key Concepts:**
- Configuration via constructor
- Regex pattern matching
- Line number tracking
- Custom result structure

---

### 4. Command Runner Agent

Execute commands on file changes:

```python
"""Command runner - executes shell commands on events."""

import asyncio
import subprocess
from pathlib import Path
from typing import List
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class CommandRunnerAgent(Agent):
    """Run shell commands on file changes."""
    
    def __init__(self, name: str, triggers: List[str], command: str, **kwargs):
        super().__init__(name, triggers, **kwargs)
        self.command = command
    
    async def handle(self, event: Event) -> AgentResult:
        """Run the configured command."""
        
        file_path = event.payload.get("path", "")
        
        # Prepare command (replace {{file}} placeholder)
        cmd = self.command.replace("{{file}}", file_path)
        
        try:
            # Run command with timeout
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0,
            )
            
            success = process.returncode == 0
            output = stdout.decode('utf-8', errors='replace')
            
            message = f"Exit code: {process.returncode}"
            if not success and stderr:
                message += f" - {stderr.decode('utf-8', errors='replace')[:100]}"
            
            return AgentResult(
                agent_name=self.name,
                success=success,
                duration=0.1,
                message=message,
                data={
                    "command": cmd,
                    "exit_code": process.returncode,
                    "output": output[:1000],  # Limit output size
                }
            )
        
        except asyncio.TimeoutError:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=30.0,
                error="Command timeout after 30s",
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                error=str(e),
            )
```

**Configuration:**
```json
{
  "agents": {
    "command-runner": {
      "enabled": true,
      "triggers": ["file:save"],
      "config": {
        "command": "python -m py_compile {{file}}"
      }
    }
  }
}
```

**Key Concepts:**
- Async subprocess execution
- Timeout handling
- Output capture
- Command parameterization

---

## Advanced Examples

### 5. Caching Agent

Cache results and only reprocess when needed:

```python
"""Caching agent - caches results based on file hashes."""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class CacheEntry:
    """Cached result entry."""
    
    def __init__(self, result: AgentResult, file_hash: str):
        self.result = result
        self.file_hash = file_hash
        self.timestamp = time.time()
    
    def is_valid(self, file_hash: str, max_age: float = 3600) -> bool:
        """Check if cache is still valid."""
        age = time.time() - self.timestamp
        return (self.file_hash == file_hash and age < max_age)


class CachingAgent(Agent):
    """Agent with result caching."""
    
    def __init__(self, name: str, triggers: list, **kwargs):
        super().__init__(name, triggers, **kwargs)
        self.cache: Dict[str, CacheEntry] = {}
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file content."""
        try:
            content = Path(file_path).read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
    
    async def handle(self, event: Event) -> AgentResult:
        """Handle with caching."""
        
        file_path = event.payload.get("path", "")
        if not file_path:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="No file path",
            )
        
        # Get file hash
        file_hash = self._get_file_hash(file_path)
        
        # Check cache
        if file_path in self.cache:
            cached = self.cache[file_path]
            if cached.is_valid(file_hash):
                self.logger.debug(f"Cache hit: {file_path}")
                return cached.result
        
        # Process file (implementation would go here)
        result = await self._process(file_path)
        
        # Store in cache
        self.cache[file_path] = CacheEntry(result, file_hash)
        
        return result
    
    async def _process(self, file_path: str) -> AgentResult:
        """Actual processing logic."""
        # Implement your processing here
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.1,
            message="Processed",
        )
```

**Key Concepts:**
- Content-based caching
- Cache invalidation
- Hash-based change detection
- Timestamp-based TTL

---

### 6. Batching Agent

Process multiple events in batches:

```python
"""Batching agent - collects and processes events in batches."""

import asyncio
from typing import List, Dict
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class BatchingAgent(Agent):
    """Process events in batches."""
    
    def __init__(
        self,
        name: str,
        triggers: List[str],
        batch_size: int = 10,
        batch_timeout: float = 2.0,
        **kwargs
    ):
        super().__init__(name, triggers, **kwargs)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batch: List[Event] = []
        self.batch_timer_task: asyncio.Task = None
    
    async def handle(self, event: Event) -> AgentResult:
        """Add event to batch."""
        
        self.batch.append(event)
        
        # Start timer if batch just started
        if len(self.batch) == 1:
            self.batch_timer_task = asyncio.create_task(
                self._batch_timeout()
            )
        
        # Process if batch is full
        if len(self.batch) >= self.batch_size:
            return await self._process_batch()
        
        # Otherwise, acknowledge receipt
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0,
            message=f"Batched ({len(self.batch)}/{self.batch_size})",
        )
    
    async def _batch_timeout(self) -> None:
        """Process batch after timeout."""
        await asyncio.sleep(self.batch_timeout)
        
        if self.batch:
            await self._process_batch()
    
    async def _process_batch(self) -> AgentResult:
        """Process accumulated batch."""
        
        if not self.batch:
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0,
                message="Empty batch",
            )
        
        # Cancel timer if running
        if self.batch_timer_task:
            self.batch_timer_task.cancel()
        
        batch_copy = self.batch.copy()
        self.batch.clear()
        
        # Process batch
        files = [e.payload.get("path") for e in batch_copy]
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.1,
            message=f"Processed batch of {len(files)} files",
            data={"files": files, "count": len(files)},
        )
```

**Key Concepts:**
- Event accumulation
- Timer-based flushing
- Size-based triggering
- Batch efficiency

---

## Specialized Examples

### 7. Integration Agent (GitHub)

Integrate with external services:

```python
"""GitHub integration agent - posts results to GitHub."""

import aiohttp
from typing import Optional, List
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class GitHubIntegrationAgent(Agent):
    """Post agent results to GitHub checks."""
    
    def __init__(
        self,
        name: str,
        triggers: List[str],
        github_token: str,
        repo: str,
        **kwargs
    ):
        super().__init__(name, triggers, **kwargs)
        self.github_token = github_token
        self.repo = repo
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def start(self) -> None:
        """Start agent and create HTTP session."""
        self.session = aiohttp.ClientSession()
        await super().start()
    
    async def stop(self) -> None:
        """Stop agent and close HTTP session."""
        await super().stop()
        if self.session:
            await self.session.close()
    
    async def handle(self, event: Event) -> AgentResult:
        """Post to GitHub."""
        
        # Extract info
        repo = self.repo
        message = event.payload.get("message", "")
        
        # Post to GitHub
        try:
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            
            data = {
                "state": "success",
                "context": self.name,
                "description": message,
            }
            
            url = f"https://api.github.com/repos/{repo}/statuses/HEAD"
            
            async with self.session.post(url, json=data, headers=headers) as resp:
                success = resp.status == 201
                
                return AgentResult(
                    agent_name=self.name,
                    success=success,
                    duration=0.5,
                    message=f"Posted to GitHub ({resp.status})",
                    data={"status_code": resp.status}
                )
        
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                error=f"GitHub API failed: {e}",
            )
```

**Configuration:**
```json
{
  "agents": {
    "github-integration": {
      "enabled": true,
      "triggers": ["agent:*:completed"],
      "config": {
        "github_token": "${GITHUB_TOKEN}",
        "repo": "myuser/myrepo"
      }
    }
  }
}
```

**Key Concepts:**
- HTTP client management
- External API integration
- Authentication handling
- Result forwarding

---

### 8. Data Pipeline Agent

Transform and filter events:

```python
"""Data pipeline agent - transforms and aggregates event data."""

from typing import List, Dict, Any, Callable
from devloop.core.agent import Agent, AgentResult
from devloop.core.event import Event


class DataTransformer:
    """Transforms event data."""
    
    def __init__(self, transformers: List[Callable]):
        self.transformers = transformers
    
    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformations."""
        for transformer in self.transformers:
            data = transformer(data)
        return data


class DataPipelineAgent(Agent):
    """Transform and aggregate event data."""
    
    def __init__(
        self,
        name: str,
        triggers: List[str],
        transformer: DataTransformer,
        **kwargs
    ):
        super().__init__(name, triggers, **kwargs)
        self.transformer = transformer
    
    async def handle(self, event: Event) -> AgentResult:
        """Transform event data."""
        
        try:
            # Transform payload
            transformed = self.transformer.transform(event.payload.copy())
            
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.01,
                message="Transformed",
                data=transformed,
            )
        
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0,
                error=f"Transformation failed: {e}",
            )


# Example transformers
def lowercase_transformer(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert strings to lowercase."""
    return {k: v.lower() if isinstance(v, str) else v for k, v in data.items()}


def filter_transformer(data: Dict[str, Any]) -> Dict[str, Any]:
    """Filter out None values."""
    return {k: v for k, v in data.items() if v is not None}


# Usage
transformer = DataTransformer([
    lowercase_transformer,
    filter_transformer,
])

agent = DataPipelineAgent(
    name="pipeline",
    triggers=["file:save"],
    event_bus=event_bus,
    transformer=transformer,
)
```

**Key Concepts:**
- Functional composition
- Chainable transformations
- Data filtering
- Immutable data handling

---

## Testing Examples

### Testing Pattern Matcher

```python
import pytest
from pathlib import Path
import tempfile
from examples.pattern_matcher import PatternMatcherAgent


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file with test content."""
    file_path = tmp_path / "test.py"
    file_path.write_text("def hello():\n    print('hello')\n    # TODO: fix this\n")
    return file_path


@pytest.mark.asyncio
async def test_finds_todo_comments(mock_event_bus, temp_file):
    """Test that agent finds TODO comments."""
    agent = PatternMatcherAgent(
        name="pattern-matcher",
        triggers=["file:save"],
        event_bus=mock_event_bus,
        pattern="TODO|FIXME",
    )
    
    event = Event(
        type="file:save",
        source="fs",
        payload={"path": str(temp_file)},
    )
    
    result = await agent.handle(event)
    
    assert result.success is False  # Found matches
    assert len(result.data["matches"]) == 1
    assert result.data["matches"][0]["line"] == 3


@pytest.mark.asyncio
async def test_handles_missing_file(mock_event_bus):
    """Test that agent handles missing files."""
    agent = PatternMatcherAgent(
        name="pattern-matcher",
        triggers=["file:save"],
        event_bus=mock_event_bus,
        pattern="TODO",
    )
    
    event = Event(
        type="file:save",
        source="fs",
        payload={"path": "/nonexistent/file.py"},
    )
    
    result = await agent.handle(event)
    
    assert result.success is True  # No file = no matches
    assert len(result.data["matches"]) == 0
```

---

## Running Examples

Clone the examples repository:

```bash
git clone https://github.com/wioota/devloop-agent-examples.git
cd devloop-agent-examples

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest examples/

# Run specific example
devloop install ./examples/pattern-matcher
```

---

## Next Steps

- [Agent Development Guide](./AGENT_DEVELOPMENT.md) - Full development guide
- [Agent API Reference](./AGENT_API_REFERENCE.md) - Complete API
- [Marketplace Guide](./MARKETPLACE_GUIDE.md) - Publishing agents
- Create your own agent!
