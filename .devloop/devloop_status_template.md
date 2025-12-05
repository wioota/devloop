## DevLoop Agent Status Verification (REQUIRED)

**CRITICAL:** Before starting any coding work, verify that `devloop watch` is running.

```bash
# Quick status check
./.agents/check-devloop-status
```

**Why this matters:**
- Real-time code quality feedback from linters, formatters, tests
- Missing issues won't be caught until commit time (slower feedback loop)
- Tests run in background automatically for faster iteration
- Security scans happen on file changes, not just at commit

**If not running:**
```bash
# Start in background with nohup (recommended)
nohup devloop watch . > .devloop/devloop.log 2>&1 &

# Or run directly
devloop watch .
```

**If it stops:**
Check the log: `tail -50 .devloop/devloop.log`

Common causes:
- Database lock: `rm -f .beads/daemon.lock`
- Permissions issue in `.devloop/` directory
- Virtual environment not activated

**Beads daemon safety:** Always use `bd daemon stop` for graceful shutdown. Hard-killing beads (with `pkill`) risks data loss in the issue database.
