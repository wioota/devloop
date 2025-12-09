---
description: Extract DevLoop findings and create Beads issues
---

Extract recent DevLoop findings and automatically create Beads issues:
```bash
devloop extract-findings
```

Or directly via the adapter:
```bash
poetry run python -m devloop.core.claude_adapter extract --format text
```

This command:
1. Reads DevLoop findings from `.devloop/context/`
2. Categorizes findings (formatter, linter, performance, security)
3. Creates Beads issues with appropriate priorities:
   - Formatter violations → P1 (can break CI)
   - Linter errors → P1 (need fixing)
   - Performance issues → P2 (nice to have)
   - Security findings → P1 or P0 (urgent)
4. Links issues to current work automatically

**What happens next:**
- Run `bd ready` to see unblocked issues
- Review categorized findings
- Work on highest priority issues

**Note:** Non-blocking operation - if no findings exist, it just reports that cleanly.
