# Per-Project Config Design

**Goal:** Allow projects to override devloop settings via a `devloop.yaml` file at project root, discovered automatically by walking up from cwd.

**Architecture:** Walk-up discovery of `devloop.yaml` layered on top of existing `agents.json`. Override-only — only specify what differs.

**Tech Stack:** Python, PyYAML, existing `Config` / `ConfigWrapper` classes.

---

## Config Resolution Order

Highest → lowest priority:

1. CLI `--config` flag (explicit path, existing behavior — unchanged)
2. `devloop.yaml` found by walking cwd → parent → git root
3. `.devloop/agents.json` (existing behavior)
4. Built-in defaults

## Discovery

On any command that loads config, walk from `cwd` up to git root (via `git rev-parse --show-toplevel`), picking the first `devloop.yaml` found. If none found, fall through to `agents.json` as today.

## Merge Semantics

Shallow merge at top level, deep merge for nested objects. Example:

```yaml
# devloop.yaml — only overrides registry, leaves rest of providers intact
registry:
  provider: npm
```

Merges into `agents.json` global.providers.registry without touching ci, release, etc.

## devloop.yaml Schema (override-only)

```yaml
registry:
  provider: none | pypi | npm   # registry to publish to
ci:
  provider: github | gitlab | none
release:
  branch: main
  tag_prefix: v
```

Only keys present in the file are applied. Unknown keys: warn and skip (never fail).

## devloop config show

New CLI command. Prints resolved config with source annotation per value:

```
registry.provider   npm        [devloop.yaml]
ci.provider         github     [agents.json]
release.branch      main       [default]
```

## Auto-Detection (advisory only)

If no `devloop.yaml` found and `package.json` exists in git root → print one-time warning:
> "Detected npm project. Consider adding `registry: {provider: npm}` to devloop.yaml"

No silent overrides — detection is advisory only.

## Error Handling

- Invalid YAML in `devloop.yaml`: warn and skip (fall through to `agents.json`)
- Unknown keys: warn and skip
- `devloop.yaml` with no recognized keys: warn once, proceed

## Acceptance Criteria

- `devloop release check` in nanoclaw reads npm registry from `devloop.yaml`, not `agents.json`
- Walk-up discovery works from any subdirectory of the project
- Existing devloop project behavior unchanged (no `devloop.yaml` = identical to today)
- `devloop config show` displays resolved config with source file per key
- Invalid `devloop.yaml` degrades gracefully (warn, continue)
