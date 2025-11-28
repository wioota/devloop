# Event System Architecture

## Overview

The event system is the backbone of the background agent architecture. It monitors various sources, normalizes events, and dispatches them to registered agents with proper prioritization, throttling, and error handling.

## Event Flow

```
Event Sources → Event Collectors → Event Normalizer → Event Dispatcher → Agents
                                          ↓
                                    Event Store
                                          ↓
                                    Event Replay
```

## Event Structure

### Base Event Schema

```typescript
interface Event {
  id: string;                    // Unique event identifier
  type: string;                  // Event type (e.g., "file:save")
  timestamp: number;             // Unix timestamp
  source: string;                // Event source identifier
  payload: Record<string, any>;  // Event-specific data
  metadata: EventMetadata;       // Additional metadata
}

interface EventMetadata {
  priority: 'low' | 'normal' | 'high' | 'critical';
  debounce?: number;             // Debounce time in ms
  throttle?: number;             // Throttle time in ms
  cancelPrevious?: boolean;      // Cancel previous events of same type
  requiresSync?: boolean;        // Must be processed synchronously
  correlationId?: string;        // For event correlation
  parentEventId?: string;        // For event chains
}
```

## Event Types

### Filesystem Events

**file:created**
```json
{
  "type": "file:created",
  "payload": {
    "path": "/path/to/file.js",
    "size": 1024,
    "extension": "js",
    "mimeType": "text/javascript"
  }
}
```

**file:modified**
```json
{
  "type": "file:modified",
  "payload": {
    "path": "/path/to/file.js",
    "changeType": "content",
    "diff": "...",
    "previousHash": "abc123",
    "currentHash": "def456"
  }
}
```

**file:deleted**
```json
{
  "type": "file:deleted",
  "payload": {
    "path": "/path/to/file.js",
    "wasTracked": true
  }
}
```

**file:renamed**
```json
{
  "type": "file:renamed",
  "payload": {
    "oldPath": "/path/to/old.js",
    "newPath": "/path/to/new.js"
  }
}
```

**file:save**
```json
{
  "type": "file:save",
  "payload": {
    "path": "/path/to/file.js",
    "size": 1024,
    "changesSinceLastSave": 42
  }
}
```

### Git Events

**git:pre-commit**
```json
{
  "type": "git:pre-commit",
  "payload": {
    "stagedFiles": ["/path/to/file1.js", "/path/to/file2.js"],
    "diff": "...",
    "branch": "feature/new-feature"
  },
  "metadata": {
    "requiresSync": true
  }
}
```

**git:post-commit**
```json
{
  "type": "git:post-commit",
  "payload": {
    "hash": "abc123def456",
    "message": "feat: add new feature",
    "author": "developer@example.com",
    "timestamp": 1234567890,
    "filesChanged": ["/path/to/file.js"]
  }
}
```

**git:pre-push**
```json
{
  "type": "git:pre-push",
  "payload": {
    "branch": "feature/new-feature",
    "commits": ["abc123", "def456"],
    "remote": "origin"
  },
  "metadata": {
    "requiresSync": true
  }
}
```

**git:checkout**
```json
{
  "type": "git:checkout",
  "payload": {
    "previousBranch": "main",
    "currentBranch": "feature/new-feature",
    "commitHash": "abc123"
  }
}
```

**git:merge**
```json
{
  "type": "git:merge",
  "payload": {
    "sourceBranch": "feature/branch",
    "targetBranch": "main",
    "conflicts": ["/path/to/conflicted.js"],
    "success": false
  }
}
```

**git:conflict-detected**
```json
{
  "type": "git:conflict-detected",
  "payload": {
    "files": ["/path/to/file.js"],
    "branch": "feature/branch"
  },
  "metadata": {
    "priority": "high"
  }
}
```

### Process Events

**process:started**
```json
{
  "type": "process:started",
  "payload": {
    "pid": 12345,
    "command": "npm run build",
    "cwd": "/path/to/project"
  }
}
```

**process:completed**
```json
{
  "type": "process:completed",
  "payload": {
    "pid": 12345,
    "command": "npm run build",
    "exitCode": 0,
    "duration": 5000,
    "stdout": "...",
    "stderr": ""
  }
}
```

**process:failed**
```json
{
  "type": "process:failed",
  "payload": {
    "pid": 12345,
    "command": "npm run build",
    "exitCode": 1,
    "error": "Build failed",
    "stderr": "..."
  },
  "metadata": {
    "priority": "high"
  }
}
```

**process:stdout**
```json
{
  "type": "process:stdout",
  "payload": {
    "pid": 12345,
    "data": "Build progress: 50%",
    "timestamp": 1234567890
  }
}
```

**process:stderr**
```json
{
  "type": "process:stderr",
  "payload": {
    "pid": 12345,
    "data": "Warning: deprecated API",
    "timestamp": 1234567890
  },
  "metadata": {
    "priority": "high"
  }
}
```

### Build Events

**build:started**
```json
{
  "type": "build:started",
  "payload": {
    "buildId": "build-123",
    "type": "production",
    "timestamp": 1234567890
  }
}
```

**build:complete**
```json
{
  "type": "build:complete",
  "payload": {
    "buildId": "build-123",
    "success": true,
    "duration": 15000,
    "artifacts": ["/dist/bundle.js"],
    "stats": {
      "size": 524288,
      "chunks": 5
    }
  }
}
```

**build:failed**
```json
{
  "type": "build:failed",
  "payload": {
    "buildId": "build-123",
    "error": "TypeScript error",
    "details": "..."
  },
  "metadata": {
    "priority": "high"
  }
}
```

### Test Events

**test:started**
```json
{
  "type": "test:started",
  "payload": {
    "testId": "test-run-123",
    "suite": "unit",
    "files": ["/path/to/test.spec.js"]
  }
}
```

**test:complete**
```json
{
  "type": "test:complete",
  "payload": {
    "testId": "test-run-123",
    "success": true,
    "duration": 3000,
    "results": {
      "passed": 42,
      "failed": 0,
      "skipped": 2
    },
    "coverage": {
      "statements": 85.5,
      "branches": 78.2,
      "functions": 90.1,
      "lines": 84.8
    }
  }
}
```

**test:failed**
```json
{
  "type": "test:failed",
  "payload": {
    "testId": "test-run-123",
    "failures": [
      {
        "test": "should handle error case",
        "file": "/path/to/test.spec.js",
        "error": "Expected true to be false"
      }
    ]
  },
  "metadata": {
    "priority": "high"
  }
}
```

### IDE/Editor Events

**ide:file-opened**
```json
{
  "type": "ide:file-opened",
  "payload": {
    "path": "/path/to/file.js",
    "language": "javascript"
  }
}
```

**ide:focus-changed**
```json
{
  "type": "ide:focus-changed",
  "payload": {
    "previousFile": "/path/to/old.js",
    "currentFile": "/path/to/new.js"
  }
}
```

**ide:workspace-changed**
```json
{
  "type": "ide:workspace-changed",
  "payload": {
    "previousWorkspace": "/old/path",
    "currentWorkspace": "/new/path"
  }
}
```

### Dependency Events

**dependency:updated**
```json
{
  "type": "dependency:updated",
  "payload": {
    "package": "react",
    "previousVersion": "17.0.2",
    "newVersion": "18.2.0",
    "type": "dependencies"
  }
}
```

**dependency:installed**
```json
{
  "type": "dependency:installed",
  "payload": {
    "package": "lodash",
    "version": "4.17.21",
    "type": "dependencies"
  }
}
```

**dependency:outdated**
```json
{
  "type": "dependency:outdated",
  "payload": {
    "packages": [
      {
        "name": "react",
        "current": "17.0.2",
        "latest": "18.2.0",
        "type": "major"
      }
    ]
  }
}
```

### System Events

**system:idle**
```json
{
  "type": "system:idle",
  "payload": {
    "idleDuration": 300000
  }
}
```

**system:active**
```json
{
  "type": "system:active",
  "payload": {
    "timestamp": 1234567890
  }
}
```

**system:low-memory**
```json
{
  "type": "system:low-memory",
  "payload": {
    "available": 524288,
    "threshold": 1048576
  },
  "metadata": {
    "priority": "critical"
  }
}
```

### Scheduled Events

**schedule:interval**
```json
{
  "type": "schedule:interval",
  "payload": {
    "interval": "hourly",
    "timestamp": 1234567890
  }
}
```

**schedule:cron**
```json
{
  "type": "schedule:cron",
  "payload": {
    "expression": "0 9 * * 1",
    "description": "Every Monday at 9am"
  }
}
```

### Custom Events

**custom:***
```json
{
  "type": "custom:deployment-complete",
  "payload": {
    "environment": "production",
    "version": "1.2.3"
  }
}
```

## Event Collectors

### Filesystem Collector

**Technology**: inotify (Linux), FSEvents (macOS), ReadDirectoryChangesW (Windows)

**Configuration**:
```json
{
  "watchPaths": ["src/**/*", "tests/**/*"],
  "ignorePaths": ["node_modules/**", "dist/**", ".git/**"],
  "events": ["create", "modify", "delete", "rename"],
  "debounce": 100
}
```

**Responsibilities**:
- Monitor filesystem changes
- Filter based on patterns
- Debounce rapid changes
- Handle large directory operations

### Git Hook Collector

**Technology**: Git hooks integration

**Configuration**:
```json
{
  "hooks": ["pre-commit", "post-commit", "pre-push", "post-merge"],
  "async": false,
  "timeout": 30000
}
```

**Responsibilities**:
- Install git hooks
- Execute agents synchronously for blocking hooks
- Provide cancellation mechanism
- Capture git context

### Process Monitor Collector

**Technology**: Process spawning, stream monitoring

**Configuration**:
```json
{
  "commands": ["npm run build", "npm test"],
  "captureOutput": true,
  "parseOutput": true
}
```

**Responsibilities**:
- Monitor spawned processes
- Capture stdout/stderr
- Track process lifecycle
- Parse structured output

### LSP Event Collector

**Technology**: Language Server Protocol integration

**Configuration**:
```json
{
  "events": ["textDocument/didOpen", "textDocument/didSave", "workspace/didChangeConfiguration"],
  "languages": ["javascript", "typescript", "python"]
}
```

**Responsibilities**:
- Connect to LSP servers
- Subscribe to LSP events
- Normalize LSP events to internal format

## Event Dispatcher

### Dispatcher Architecture

```typescript
class EventDispatcher {
  private agents: Map<string, Agent>;
  private subscriptions: Map<string, Set<string>>; // event type -> agent IDs
  private eventQueue: PriorityQueue<Event>;
  private processingPool: WorkerPool;

  async dispatch(event: Event): Promise<void> {
    // 1. Check if event should be debounced/throttled
    if (this.shouldSkip(event)) return;

    // 2. Add to priority queue
    this.eventQueue.enqueue(event);

    // 3. Process queue
    await this.processQueue();
  }

  private async processQueue(): Promise<void> {
    while (!this.eventQueue.isEmpty()) {
      const event = this.eventQueue.dequeue();
      const agents = this.getSubscribedAgents(event.type);

      // Execute agents in parallel (unless requiresSync)
      if (event.metadata.requiresSync) {
        await this.executeSync(event, agents);
      } else {
        await this.executeAsync(event, agents);
      }
    }
  }
}
```

### Event Filtering

```typescript
interface EventFilter {
  type?: string | RegExp;           // Event type pattern
  priority?: Priority[];            // Priority levels
  source?: string[];                // Event sources
  custom?: (event: Event) => boolean;  // Custom filter function
}
```

### Event Transformation

```typescript
interface EventTransformer {
  transform(event: Event): Event | Event[] | null;
}

// Example: Split batch file changes into individual events
class BatchFileTransformer implements EventTransformer {
  transform(event: Event): Event[] {
    if (event.type === 'file:batch-modified') {
      return event.payload.files.map(file => ({
        ...event,
        id: generateId(),
        type: 'file:modified',
        payload: { path: file }
      }));
    }
    return [event];
  }
}
```

## Event Store

### Purpose
- Audit trail of all events
- Event replay for debugging
- Historical analysis
- Agent replay after crashes

### Storage Schema

```sql
CREATE TABLE events (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  source TEXT NOT NULL,
  payload JSON NOT NULL,
  metadata JSON NOT NULL,
  processed BOOLEAN DEFAULT FALSE,
  processing_duration INTEGER
);

CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_processed ON events(processed);
```

### Configuration

```json
{
  "enabled": true,
  "storage": "sqlite",
  "path": ".claude/events.db",
  "retention": {
    "days": 30,
    "maxEvents": 100000
  },
  "replay": {
    "enabled": true,
    "onStartup": false
  }
}
```

## Event Patterns

### Event Aggregation

Combine multiple related events into one:

```typescript
// Multiple file saves -> single "batch save" event
const saves = events.filter(e => e.type === 'file:save');
if (saves.length > 10) {
  return {
    type: 'file:batch-save',
    payload: { files: saves.map(e => e.payload.path) }
  };
}
```

### Event Correlation

Link related events:

```typescript
{
  "type": "test:failed",
  "metadata": {
    "correlationId": "build-123",
    "parentEventId": "build:complete"
  }
}
```

### Event Chains

Create dependent event sequences:

```typescript
// file:save -> linter:run -> linter:complete -> commit:allowed
```

### Event Cancellation

Cancel pending events:

```typescript
{
  "type": "file:save",
  "metadata": {
    "cancelPrevious": true  // Cancel previous unsaved changes
  }
}
```

## Performance Considerations

### Debouncing

Prevent rapid-fire events:

```typescript
const debouncedEvent = debounce(event, 500);
```

### Throttling

Limit event rate:

```typescript
const throttledEvent = throttle(event, 1000);
```

### Batching

Group events for efficiency:

```typescript
const batchWindow = 1000; // 1 second
const batch = collectEvents(batchWindow);
```

### Priority Queue

Process high-priority events first:

```typescript
enum Priority {
  LOW = 0,
  NORMAL = 1,
  HIGH = 2,
  CRITICAL = 3
}
```

## Error Handling

### Event Processing Errors

```typescript
try {
  await agent.handle(event);
} catch (error) {
  await this.handleError(event, agent, error);
  // Retry logic
  if (shouldRetry(error)) {
    await this.retry(event, agent);
  }
}
```

### Dead Letter Queue

Events that fail repeatedly:

```typescript
{
  "enabled": true,
  "maxRetries": 3,
  "retryDelay": 1000,
  "storage": ".claude/failed-events.json"
}
```

## Monitoring & Observability

### Event Metrics

- Events processed per second
- Processing duration per event type
- Queue depth
- Agent execution times
- Error rates

### Event Logs

```json
{
  "timestamp": 1234567890,
  "level": "info",
  "message": "Event dispatched",
  "event": {
    "id": "evt-123",
    "type": "file:save",
    "agents": ["linter", "formatter"]
  }
}
```

### Debugging

```bash
# View event stream
dev-agents events stream

# Replay events
dev-agents events replay --from 2024-01-01 --to 2024-01-02

# Event statistics
dev-agents events stats --type file:save
```
