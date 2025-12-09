# Claude Code Hooks Implementation Checklist

## Phase 1: Core Automation (Must Have) ⏱️ ~2 hours

### Hook Scripts

- [ ] Create `.agents/hooks/claude-session-start` script
  - [ ] Pre-load findings on session startup
  - [ ] Non-blocking failure handling
  - [ ] Test with `claude --resume`

- [ ] Create `.agents/hooks/claude-stop` script
  - [ ] Collect findings on Claude completion
  - [ ] Check `stop_hook_active` flag to prevent loops
  - [ ] Non-blocking JSON handling
  - [ ] Test with basic Claude response

- [ ] Create `.agents/hooks/claude-file-protection` script
  - [ ] Block writes to `.beads/`
  - [ ] Block writes to `.devloop/`
  - [ ] Block writes to `.git/`
  - [ ] Block writes to `.agents/`
  - [ ] Block writes to AGENTS.md, CODING_RULES.md
  - [ ] Test blocking behavior

### Integration

- [ ] Update `src/devloop/cli/main.py` init command
  - [ ] Create hook scripts during `devloop init`
  - [ ] Make scripts executable (chmod 0o755)
  - [ ] Offer to install hooks to ~/.claude/settings.json

- [ ] Create `.agents/hooks/install-claude-hooks` script
  - [ ] Merge hooks into ~/.claude/settings.json
  - [ ] Handle missing settings file
  - [ ] Provide fallback manual instructions
  - [ ] Test JSON merging logic

### Testing

- [ ] Unit test session-start hook
  - [ ] Verify `devloop amp_context` is called
  - [ ] Verify exit code 0 on success
  - [ ] Verify graceful failure if devloop missing

- [ ] Unit test stop hook
  - [ ] Verify `devloop amp_findings` is called
  - [ ] Verify loop prevention with `stop_hook_active`
  - [ ] Verify exit code 0 on success

- [ ] Unit test file-protection hook
  - [ ] Verify blocks `.beads/` writes
  - [ ] Verify blocks `.devloop/` writes
  - [ ] Verify allows other file writes
  - [ ] Verify helpful error message in stderr
  - [ ] Verify exit code 2 on block

### Documentation

- [ ] Update `AMP_ONBOARDING.md`
  - [ ] Add "Claude Code Hooks" section
  - [ ] Explain SessionStart, Stop, PreToolUse hooks
  - [ ] Document how hooks integrate with workflow
  - [ ] Add troubleshooting for hook failures

- [ ] Create `.agents/hooks/README.md`
  - [ ] List all hook scripts
  - [ ] Explain what each does
  - [ ] Show how to test hooks manually
  - [ ] Link to main documentation

- [ ] Update main README.md
  - [ ] Mention Claude Code hook support
  - [ ] Link to AMP_ONBOARDING.md for setup

---

## Phase 2: File Protection (Should Have) ⏱️ ~1 hour

### Hook Refinement

- [ ] Test file-protection with real Write tool calls
  - [ ] Verify it blocks without being too aggressive
  - [ ] Verify error message is clear
  - [ ] Test edge cases (symlinks, relative paths)

- [ ] Add whitelist mechanism if needed
  - [ ] Allow overrides for legitimate edits
  - [ ] Document override process
  - [ ] Test with actual use cases

### Integration

- [ ] Ensure file-protection hook included in init
- [ ] Test that init registers all three hooks

### Documentation

- [ ] Document what files are protected and why
- [ ] Provide alternatives when protection blocks edits
  - [ ] Manual terminal edit
  - [ ] Get user explicit permission
  - [ ] Ask to bypass protection

---

## Phase 3: Advanced Features (Nice to Have) ⏱️ Future

### Optional Hooks

- [ ] Create `claude-user-prompt-submit` script
  - [ ] Inject findings when relevant
  - [ ] Detect when user asking about code quality
  - [ ] Add context to prompt

### Subagent Integration

- [ ] Create `claude-subagent-stop` script
  - [ ] Extract findings on task completion
  - [ ] Create Beads issues automatically
  - [ ] Link to task/parent issue

---

## Testing & Validation

### Manual Testing

- [ ] Install DevLoop with `devloop init` in test project
- [ ] Verify hooks installed to ~/.claude/settings.json
  - [ ] Check `/hooks` menu in Claude Code
  - [ ] Verify all hooks registered

- [ ] Test SessionStart hook
  - [ ] Start Claude Code: `claude --resume` or `/clear`
  - [ ] Verify findings loaded (check verbose mode Ctrl+O)
  - [ ] Verify session doesn't break if findings missing

- [ ] Test Stop hook
  - [ ] Ask Claude to do something
  - [ ] After response completes, check verbose mode
  - [ ] Verify findings collected to `.devloop/context/`

- [ ] Test file-protection hook
  - [ ] Ask Claude to edit `.beads/issues.jsonl`
  - [ ] Verify Claude Code blocks the write
  - [ ] Verify helpful error message shown

- [ ] Test fallback CLI commands
  - [ ] Run `devloop verify-work`
  - [ ] Run `devloop extract_findings_cmd`
  - [ ] Verify they still work without hooks

### Integration Testing

- [ ] Test hooks with different project types
  - [ ] Python project
  - [ ] Node.js project
  - [ ] Multi-language project

- [ ] Test with DevLoop not installed
  - [ ] Hooks should fail gracefully
  - [ ] Claude Code should continue working

- [ ] Test with missing dependencies
  - [ ] Hooks should handle missing `bd`, `jq`
  - [ ] Should provide helpful error message

### Regression Testing

- [ ] Git pre-commit hook still works
- [ ] Amp post-task hook still works
- [ ] CLI commands still work
- [ ] No existing workflows broken

---

## Documentation Validation

- [ ] Setup instructions work on clean install
- [ ] Troubleshooting guide covers common issues
- [ ] Error messages match documentation
- [ ] Links to related docs work

---

## Release Preparation

### Code Quality

- [ ] All scripts pass shellcheck
- [ ] All Python code passes ruff, mypy
- [ ] All tests pass locally

### Commit & Documentation

- [ ] Update CHANGELOG.md with hook additions
- [ ] Document hooks in version release notes
- [ ] Provide migration guide (if any)

### Communication

- [ ] Update project README
- [ ] Add hooks section to setup guide
- [ ] Document in AGENTS.md architecture section

---

## Known Issues & Workarounds

### Potential Issues

| Issue | Impact | Workaround |
|-------|--------|-----------|
| Hooks timeout during verification | Medium | Set reasonable timeout (30s), non-blocking |
| Hook output interferes with Claude | Low | Minimize output, use stderr for messages |
| Hooks fail on different machines | Medium | Use `$CLAUDE_PROJECT_DIR` environment variable |
| PreToolUse too aggressive | Medium | Whitelist legitimate edit patterns |
| Web Claude Code can't use hooks | N/A | Document limitation, CLI still available |

---

## Success Criteria

### Phase 1 (Core)

✅ SessionStart hook loads findings automatically
✅ Stop hook collects findings automatically
✅ PreToolUse hook blocks protected files
✅ All hooks non-blocking (Claude Code still works if they fail)
✅ CLI commands still work as fallback
✅ Documentation clear and complete
✅ Tests pass (unit + integration)
✅ Clean install works without manual configuration

### Phase 2 (Protection)

✅ File protection doesn't over-block legitimate edits
✅ Error messages helpful and actionable
✅ Whitelist/override mechanism works if needed

### Phase 3 (Advanced)

✅ Optional hooks work but aren't required
✅ Subagent integration doesn't break tasks
✅ Extra context injection is helpful

---

## Sign-Off

- [ ] Code review complete
- [ ] All tests passing
- [ ] Documentation reviewed
- [ ] Ready for merge to main
- [ ] Release notes prepared

---

## Rollout Timeline

**Phase 1**: 1-2 weeks after implementation
- SessionStart + Stop hooks
- File protection hook
- Core documentation

**Phase 2**: 2-4 weeks after Phase 1
- Optional hooks
- Advanced integrations
- User feedback incorporation

**Phase 3**: Future minor releases
- Refinements based on usage
- Additional hook events
- Community contributions

---

## Notes

- Keep CLI commands as fallback indefinitely
- Prioritize non-blocking approach
- Provide clear error messages
- Document limitations (web Claude Code)
- Test on multiple OS (macOS, Linux, Windows)
- Gather user feedback on hook behavior
