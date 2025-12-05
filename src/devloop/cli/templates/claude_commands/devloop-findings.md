---
description: Extract devloop findings and create Beads issues for tracking
---

Run the findings extraction hook to automatically create Beads issues from recent DevLoop findings:

```bash
./.agents/hooks/extract-findings-to-beads
```

This will:
1. Scan `.devloop/context/` for recent findings (last 24 hours)
2. Categorize findings by type (formatter, linter, performance, security)
3. Create Beads issues for high-priority items:
   - Formatter violations (priority 1) - can break CI
   - Linter errors (priority 1) - need fixing
   - Performance issues (priority 2) - nice to have
4. Link created issues to the current work

After running, show the created issues and suggest running `bd ready` to see what's actionable.
