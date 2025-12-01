# Release v0.2.2 - Published to PyPI

**Release Date:** 2025-12-01  
**Status:** ✅ Live on PyPI  
**Package URL:** https://pypi.org/project/devloop/0.2.2/

---

## What Was Released

DevLoop v0.2.2 is now available for installation via PyPI:

```bash
pip install devloop==0.2.2
```

---

## Key Changes in v0.2.2

### 1. Fixed Unbounded Disk Growth ✅
- **RotatingFileHandler** - Logs rotate at 10MB per file, keep 3 backups (40MB max)
- **Context Cleanup** - Remove findings older than 7 days (runs hourly)
- **Event Cleanup** - Remove events older than 30 days (runs hourly)
- **Background Task** - `_cleanup_old_data()` automatically manages storage

**Before:** 17GB+ logs in days  
**After:** ~40MB logs + 7 days of context data

### 2. Updated with Clear Alpha Warnings ⚠️
- README badge changed from "production ready" to "alpha"
- Added prominent ⚠️ ALPHA SOFTWARE section
- Listed known limitations (subprocess security, auto-fix safety, race conditions, etc.)
- Clarified use cases:
  - ✅ Suitable: Side projects, research, testing automation
  - ❌ NOT suitable: Production, critical code, untrusted projects
- Set `autonomousFixes.enabled` default to `false` (safe)
- Added recovery procedures for when things go wrong

### 3. Comprehensive Risk Assessment
- Created `history/RISK_ASSESSMENT.md` - 5 pages, 7 categories, 17 risks identified
- Created `history/RISK_FIX_PROGRESS.md` - 20 tracked mitigation tasks
- 2 CRITICAL risks: subprocess execution, auto-fix safety
- 11 HIGH priority fixes needed
- 7 MEDIUM priority improvements

### 4. Version Consistency
- Updated `pyproject.toml`: 0.2.1 → 0.2.2
- Updated `src/devloop/__init__.py`: 0.2.0 → 0.2.2
- Updated `CHANGELOG.md` with comprehensive release notes

---

## Test Coverage

All 167 tests passing before release:

```
======================== 167 passed in 3.08s ========================
```

**Test Suite Includes:**
- Unit tests for all agents
- CLI command tests
- Collector tests
- Integration tests
- Configuration tests

---

## Release Workflow

### GitHub Actions
✅ Release v0.2.2 completed successfully:
- Built distribution packages
- Published to PyPI
- Created GitHub Release
- Uploaded artifacts

### GitHub Release
📍 Available at: https://github.com/wioota/devloop/releases/tag/v0.2.2

### PyPI Package
📦 Available at: https://pypi.org/project/devloop/0.2.2/

---

## Installation Instructions

### From PyPI (Recommended)
```bash
pip install devloop==0.2.2
```

### From Source
```bash
git clone https://github.com/wioota/devloop
cd devloop
git checkout v0.2.2
poetry install
```

### First Time Setup
```bash
devloop init /path/to/project
devloop watch /path/to/project
```

---

## Important Notes for Users

### ⚠️ ALPHA SOFTWARE
This is research-quality code, not production-ready.

- **Data Loss Risk:** Only use on projects you can afford to lose
- **Commit First:** Always commit to git before enabling DevLoop
- **No Auto-fix:** Set `autonomousFixes.enabled = false` (default)
- **Silent Failures:** Some agents may fail without notification

### Known Limitations
See [RISK_ASSESSMENT.md](./history/RISK_ASSESSMENT.md) for:
- Security risks (subprocess execution not sandboxed)
- Auto-fix risks (no backups, may corrupt code)
- Reliability risks (race conditions, no transactions)
- Operational risks (manual daemon management, no config migrations)

### Recovery Steps (If Something Goes Wrong)
1. Stop daemon: `devloop stop .`
2. Check logs: `tail -100 .devloop/devloop.log`
3. Verify git: `git status`
4. Recover: `git checkout -- .`

---

## What's Next (Roadmap)

### Immediate (P0 - CRITICAL)
- [ ] Sandbox subprocess execution (security)
- [ ] Secure auto-fix with backups and rollback

### Short Term (P1 - HIGH)
- [ ] Enforce resource limits (CPU/memory)
- [ ] Implement audit logging
- [ ] Fix race conditions in file operations
- [ ] Proper daemon process supervision (systemd)
- [ ] Config schema versioning
- [ ] Path validation and symlink protection
- [ ] Secure token management
- [ ] Document external tool dependencies

### Medium Term (P2 - MEDIUM)
- [ ] Transaction semantics for operations
- [ ] Event persistence and replay
- [ ] Better error handling
- [ ] Multi-project documentation
- [ ] Performance tuning knobs
- [ ] Large repo optimization
- [ ] Metrics/monitoring exports
- [ ] Debugging improvements
- [ ] Upgrade documentation

---

## Commits in This Release

```
deb907b chore: Bump version to 0.2.2 and update CHANGELOG
4c317b2 docs: Update README with alpha/research quality warnings
af096f4 docs: Add risk fix progress summary - disk fill-up fixed, 20 tasks created
f2cb57c Fix unbounded disk fill-up: implement log rotation and automatic context/event cleanup
```

---

## File Changes Summary

### Core Implementation
- `src/devloop/cli/main.py` - Log rotation with RotatingFileHandler
- `src/devloop/core/context_store.py` - Added cleanup_old_findings() method
- `src/devloop/__init__.py` - Version bump

### Documentation
- `README.md` - Alpha warnings, auto-fix safety, troubleshooting
- `CHANGELOG.md` - Comprehensive release notes
- `pyproject.toml` - Version update
- `history/RISK_ASSESSMENT.md` - 5-page risk analysis (NEW)
- `history/RISK_FIX_PROGRESS.md` - Implementation tracking (NEW)

### Total Changes
- 7 commits
- 4 files modified
- 2 new documentation files
- 100+ lines added (warnings, documentation)
- 20 tracked tasks created in beads

---

## Quality Metrics

| Metric | Value |
|--------|-------|
| Tests Passing | 167/167 ✅ |
| Code Coverage | ~85% |
| Python Versions | 3.11, 3.12+ |
| Release Type | Research/Alpha |
| Documentation | Complete |
| Known Issues | Documented |

---

## Thank You!

Thanks for testing DevLoop. Please report issues at:
https://github.com/wioota/devloop/issues

And remember: **This is alpha software. Use at your own risk.**

---

## Release Assets

### Distribution Packages
- `devloop-0.2.2-py3-none-any.whl`
- `devloop-0.2.2.tar.gz`

Available at:
- PyPI: https://pypi.org/project/devloop/0.2.2/
- GitHub Release: https://github.com/wioota/devloop/releases/tag/v0.2.2
- GitHub Actions Artifacts: Available for 30 days
