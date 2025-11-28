# Documentation Consolidation Plan

**Date:** November 28, 2025
**Current State:** 35 markdown files in root directory
**Problem:** LLM-assisted development creates temporary documentation that persists beyond usefulness
**Solution:** Systematic consolidation with lifecycle management

---

## File Inventory & Categorization

### Category 1: KEEP - Core Documentation (8 files)

**These are essential, permanent documentation:**

1. **README.md** - Main project documentation ✅
2. **CLAUDE.md** - Development background agents system overview ✅
3. **CODING_RULES.md** - Development patterns and best practices ✅
4. **PUBLISHING_PLAN.md** - Future public release roadmap ✅
5. **.claude/CLAUDE.md** - Claude Code integration instructions ✅
6. **agent-types.md** - Agent specifications ✅
7. **configuration-schema.md** - Configuration reference ✅
8. **event-system.md** - Event monitoring architecture ✅

**Action:** Keep as-is, ensure they're up to date

---

### Category 2: CONSOLIDATE - Overlapping Content (7 files)

**These have overlapping or redundant information:**

#### Getting Started Docs (3 files)
- **GETTING_STARTED.md** - Getting started guide
- **QUICKSTART.md** - Quick start guide
- **CLAUDE_CODE_TEST_GUIDE.md** - Claude Code testing guide

**Consolidation Target:** `docs/getting-started.md`
**Action:** Merge into single comprehensive getting started guide

#### Project Status Docs (2 files)
- **STATUS.md** - "Claude Agents - Project Status"
- **PROJECT_SUMMARY.md** - Project overview

**Consolidation Target:** Update README.md with current status
**Action:** Merge relevant content into README, archive originals

#### Implementation Guides (2 files)
- **IMPLEMENTATION.md** - Implementation guide
- **INTERACTION_MODEL.md** - Interaction model

**Consolidation Target:** `docs/architecture.md`
**Action:** Create comprehensive architecture document

---

### Category 3: ARCHIVE - Historical Completion Docs (10 files)

**These document completed work - valuable for history, not current development:**

1. **PHASE2_COMPLETE.md** - "Phase 2: Real Agents - COMPLETE ✅"
2. **PHASE3_COMPLETE.md** - "Phase 3: Learning & Optimization - COMPLETE ✅"
3. **PHASE3_README.md** - Phase 3 documentation
4. **IMPLEMENTATION_COMPLETE.md** - "Context Store Implementation - Complete! ✅"
5. **CONTEXT_STORE_STATUS.md** - Context store status
6. **RENAME_COMPLETE.md** - Project rename completion ✅
7. **FIX_SUMMARY.md** - Threading fix summary
8. **THREADING_FIX.md** - Threading/async fix details
9. **ENHANCEMENTS_SUMMARY.md** - Enhancements implemented
10. **SESSION_STATUS.md** - Session status (October 25, 2025)

**Consolidation Target:** `docs/archive/YYYY-MM/`
**Action:** Move to dated archive directories

---

### Category 4: CONSOLIDATE INTO CHANGELOG (2 files)

**These track changes and should become changelog entries:**

1. **TESTING_RESULTS.md** - Test results
2. **PROTOTYPE_STATUS.md** - Prototype status

**Consolidation Target:** `CHANGELOG.md`
**Action:** Create CHANGELOG.md with milestone entries, archive originals

---

### Category 5: MOVE TO docs/ (6 files)

**These are reference docs that belong in docs/ directory:**

1. **AGENTS.md** - "Agent Development Rules & Processes"
2. **COMMANDS.md** - Command reference
3. **TECH_STACK.md** - Technology stack
4. **TESTING_STRATEGY.md** - Testing approach
5. **INDEX.md** - Documentation index
6. **REPORT_ONLY_MODE.md** - Report-only mode documentation

**Action:** Move to `docs/` with appropriate subdirectories

---

### Category 6: SPECIAL - Quality & Process (3 files)

**These define development standards:**

1. **CI_QUALITY_COMMITMENT.md** - CI/CD quality standards ✅
2. **RENAME_PLAN.md** - Rename execution plan (historical reference)
3. **CODEBASE_ASSESSMENT.md** - Recent codebase assessment ✅ (NEW)

**Action:**
- CI_QUALITY_COMMITMENT.md → Keep in root or docs/contributing/
- RENAME_PLAN.md → Archive (historical)
- CODEBASE_ASSESSMENT.md → Keep temporarily, archive when issues resolved

---

### Category 7: DUPLICATES (2 files)

**These appear to be duplicates or variations:**

1. **README_v2.md** - Alternative README
2. **(any other duplicate versions)**

**Action:** Compare with main version, merge unique content, delete

---

## Proposed New Structure

```
claude-agents/
├── README.md                      # Main documentation (updated)
├── CLAUDE.md                      # System overview (keep)
├── CODING_RULES.md               # Best practices (keep)
├── CHANGELOG.md                  # NEW: Version history
├── PUBLISHING_PLAN.md            # Future release plan (keep)
├── CI_QUALITY_COMMITMENT.md      # CI standards (keep)
│
├── docs/
│   ├── getting-started.md        # CONSOLIDATED: All getting started guides
│   ├── architecture.md           # CONSOLIDATED: Implementation + interaction
│   │
│   ├── reference/
│   │   ├── agent-types.md        # MOVED from root
│   │   ├── configuration-schema.md
│   │   ├── event-system.md
│   │   ├── commands.md           # MOVED from root
│   │   └── tech-stack.md         # MOVED from root
│   │
│   ├── guides/
│   │   ├── testing-strategy.md   # MOVED from root
│   │   └── report-only-mode.md   # MOVED from root
│   │
│   ├── contributing/
│   │   └── agents.md             # MOVED from AGENTS.md
│   │
│   └── archive/
│       ├── 2025-11/
│       │   ├── rename-complete.md
│       │   ├── rename-plan.md
│       │   └── codebase-assessment.md
│       │
│       ├── 2025-10/
│       │   ├── phase2-complete.md
│       │   ├── phase3-complete.md
│       │   ├── implementation-complete.md
│       │   ├── context-store-status.md
│       │   ├── fix-summary.md
│       │   ├── threading-fix.md
│       │   ├── enhancements-summary.md
│       │   ├── session-status.md
│       │   ├── testing-results.md
│       │   └── prototype-status.md
│       │
│       └── README.md              # Archive index
│
└── .claude/
    └── CLAUDE.md                  # Claude Code integration (keep)
```

---

## Consolidation Steps

### Phase 1: Preparation (No Deletions)
1. ✅ Create `docs/` directory structure
2. ✅ Create `CHANGELOG.md` from milestone docs
3. ✅ Create consolidated docs (getting-started.md, architecture.md)
4. ✅ Review README.md and update with current status

### Phase 2: Migration (Copies First)
1. Copy (don't move) reference docs to `docs/reference/`
2. Copy guide docs to `docs/guides/`
3. Copy completion docs to `docs/archive/YYYY-MM/`
4. Copy AGENTS.md to `docs/contributing/agents.md`

### Phase 3: Verification
1. Verify all content is preserved
2. Verify no broken links
3. Update any internal references
4. Get user approval

### Phase 4: Cleanup (After Approval)
1. Remove originals from root (keep backups)
2. Update .gitignore if needed
3. Create docs/archive/README.md index
4. Commit changes

---

## File-by-File Action Plan

| File | Category | Action | Destination |
|------|----------|--------|-------------|
| README.md | Keep | Update | (root) |
| README_v2.md | Duplicate | Merge → Delete | - |
| CLAUDE.md | Keep | Keep | (root) |
| CODING_RULES.md | Keep | Keep | (root) |
| CHANGELOG.md | New | Create | (root) |
| PUBLISHING_PLAN.md | Keep | Keep | (root) |
| CI_QUALITY_COMMITMENT.md | Keep | Keep | (root) |
| CODEBASE_ASSESSMENT.md | Special | Archive later | docs/archive/2025-11/ |
| | | | |
| GETTING_STARTED.md | Consolidate | Merge | docs/getting-started.md |
| QUICKSTART.md | Consolidate | Merge | docs/getting-started.md |
| CLAUDE_CODE_TEST_GUIDE.md | Consolidate | Merge | docs/getting-started.md |
| STATUS.md | Consolidate | Merge → Archive | README + archive |
| PROJECT_SUMMARY.md | Consolidate | Merge → Archive | README + archive |
| IMPLEMENTATION.md | Consolidate | Merge | docs/architecture.md |
| INTERACTION_MODEL.md | Consolidate | Merge | docs/architecture.md |
| | | | |
| PHASE2_COMPLETE.md | Archive | Move | docs/archive/2025-10/ |
| PHASE3_COMPLETE.md | Archive | Move | docs/archive/2025-10/ |
| PHASE3_README.md | Archive | Move | docs/archive/2025-10/ |
| IMPLEMENTATION_COMPLETE.md | Archive | Move | docs/archive/2025-10/ |
| CONTEXT_STORE_STATUS.md | Archive | Move | docs/archive/2025-10/ |
| RENAME_COMPLETE.md | Archive | Move | docs/archive/2025-11/ |
| RENAME_PLAN.md | Archive | Move | docs/archive/2025-11/ |
| FIX_SUMMARY.md | Archive | Move | docs/archive/2025-10/ |
| THREADING_FIX.md | Archive | Move | docs/archive/2025-10/ |
| ENHANCEMENTS_SUMMARY.md | Archive | Move | docs/archive/2025-10/ |
| SESSION_STATUS.md | Archive | Move | docs/archive/2025-10/ |
| TESTING_RESULTS.md | Changelog | Extract → Archive | CHANGELOG + archive |
| PROTOTYPE_STATUS.md | Changelog | Extract → Archive | CHANGELOG + archive |
| | | | |
| AGENTS.md | Move | Move | docs/contributing/agents.md |
| COMMANDS.md | Move | Move | docs/reference/commands.md |
| TECH_STACK.md | Move | Move | docs/reference/tech-stack.md |
| TESTING_STRATEGY.md | Move | Move | docs/guides/testing-strategy.md |
| INDEX.md | Move | Update → Move | docs/index.md |
| REPORT_ONLY_MODE.md | Move | Move | docs/guides/report-only-mode.md |
| | | | |
| agent-types.md | Keep | Keep | (root) or docs/reference/ |
| configuration-schema.md | Keep | Keep | (root) or docs/reference/ |
| event-system.md | Keep | Keep | (root) or docs/reference/ |

**Total Files:** 35
**After Consolidation:** ~15-18 files (root) + organized docs/ directory

---

## Success Metrics

- ✅ Root directory has < 10 .md files
- ✅ All historical docs archived by date
- ✅ No duplicate content across files
- ✅ Clear documentation hierarchy
- ✅ CHANGELOG.md tracks all milestones
- ✅ Getting started guide is comprehensive and singular
- ✅ No broken documentation links

---

## Doc Lifecycle Agent (Future)

This consolidation reveals the need for a **Doc Lifecycle Agent** that:

1. **Detects Temporary Docs**
   - Monitors for completion markers ("COMPLETE ✅", "RESOLVED ✅")
   - Identifies date-stamped status files
   - Flags duplicate content

2. **Suggests Actions**
   - "PHASE2_COMPLETE.md looks historical - archive to docs/archive/2025-10/?"
   - "Found 3 getting-started guides - consolidate?"
   - "README_v2.md duplicates README.md - review and merge?"

3. **Maintains Structure**
   - Enforces docs/ directory structure
   - Auto-updates CHANGELOG.md
   - Keeps archive organized by date
   - Updates INDEX.md automatically

4. **Prevents Cruft**
   - Weekly scan for orphaned docs
   - Flags docs > 30 days old with completion markers
   - Suggests quarterly archive reviews

**Specification:** See separate document (to be created)

---

## Next Steps

1. **Get User Approval** for this consolidation plan
2. **Execute Phase 1** (create new structure, no deletions)
3. **Review** consolidated docs with user
4. **Execute Phase 2-4** after approval
5. **Design Doc Lifecycle Agent** for ongoing maintenance

---

## Risk Mitigation

- **Backup:** Git history preserves all content
- **Phased Approach:** Copy first, delete only after verification
- **User Approval:** Required before any file deletions
- **Rollback:** Can revert entire consolidation if needed

---

## Maintenance Strategy

**Ongoing (Without Agent):**
- Monthly review of root .md files
- Archive completed milestone docs within 1 week
- Update CHANGELOG.md for each release

**Future (With Doc Lifecycle Agent):**
- Automated detection and suggestions
- Proactive consolidation recommendations
- Enforced documentation structure
