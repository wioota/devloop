---
description: Run code quality verification and extract findings (like Amp post-task)
---

Run verification checks and extract findings by executing:
```bash
devloop verify-work
```

Or directly via the adapter:
```bash
poetry run python -m devloop.core.claude_adapter verify-and-extract --format text
```

This command:
1. Runs unified code quality verification (Black, Ruff, mypy, pytest)
2. Extracts DevLoop findings and creates Beads issues
3. Shows blocking issues and warnings
4. Lists created Beads issues for tracking

**Similar to:** Amp's post-task hook for equivalent enforcement

**Output shows:**
- ✅ Checks passed or ❌ blocking issues found
- List of warnings (non-blocking)
- Created Beads issue IDs
- Summary of quality status

After running, use `bd ready` to see newly created issues.
