# Optional Agents Implementation Plan

## Overview
Make Phase 2 agents (code_rabbit, snyk, ci_monitor) optional during installation through interactive prompts and configuration choices.

## Current Installation Flow

### 1. Package Installation (`pip install devloop`)
- Downloads fixed package from PyPI
- All code included regardless of use
- Single `pyproject.toml` configuration

### 2. Project Initialization (`devloop init`)
- Creates `.devloop/` directory
- Writes default `agents.json` with standard 8 agents enabled
- User manually edits if they want to customize

### 3. Runtime (`devloop watch`)
- Loads config from `agents.json`
- Instantiates only enabled agents
- Agents with missing CLI tools fail gracefully

---

## Proposed Implementation Strategy

### Option A: Configuration-Only (Simplest)
✅ **Easiest to implement**
- Keep all agents in package
- Add interactive prompts during `devloop init`
- User selects which optional agents to enable
- Saves selection to `agents.json`

**Pros**: No packaging complexity, gradual feature adoption
**Cons**: Unused code still downloaded

### Option B: Optional Dependencies (Medium)
✅ **Better UX, requires poetry changes**
- Define optional dependency groups in `pyproject.toml`
- Users install: `pip install devloop[snyk,code-rabbit]`
- Only selected agents included in wheel

**Pros**: Smaller installation, intentional opt-in
**Cons**: Requires education about extra dependencies

### Option C: Plugin Architecture (Most Flexible)
✅ **Best long-term, requires refactoring**
- Move optional agents to separate packages
- `devloop-plugin-snyk`, `devloop-plugin-code-rabbit`
- Users `pip install devloop devloop-plugin-snyk`
- Plugin auto-discovery on init

**Pros**: Minimal core package, community plugins possible
**Cons**: Most complex, requires plugin system

### Option D: Custom Interactive Installer (Most UX-Friendly)
✅ **Best user experience, requires script changes**
- Enhance `install.sh` script with interactive menu
- Enhanced `devloop init` with multi-choice prompts
- Supports all three approaches above
- Clear documentation of selected features

**Pros**: Single consistent experience, guides users
**Cons**: More code, more edge cases to handle

---

## Recommended Approach: Option A + Option D

**Rationale**: Quick implementation (Phase 2 focus) with excellent UX

### Phase 2A: Interactive Configuration (Short-term)
```bash
$ devloop init
? Select which optional agents to enable: (space to select)
  ❌ code-rabbit (requires: code-rabbit CLI)
  ❌ snyk (requires: snyk CLI)  
  ❌ ci-monitor (monitors CI/CD pipelines)
  
Selected: snyk
Created: .devloop/agents.json with snyk enabled
```

### Phase 2B: Optional Dependencies (Medium-term)
```bash
$ pip install devloop[snyk,code-rabbit]
# Only installs code for selected agents
```

### Phase 3: Plugin Architecture (Long-term)
```bash
$ pip install devloop
$ pip install devloop-plugin-snyk devloop-plugin-code-rabbit
$ devloop init  # Auto-discovers plugins
```

---

## Implementation Details for Phase 2A

### 1. Update `pyproject.toml`

```toml
[tool.poetry.extras]
# Optional dependency groups
snyk = []
code-rabbit = []
ci-monitor = []
all-optional = ["snyk", "code-rabbit", "ci-monitor"]

[tool.poetry.group.snyk.dependencies]
# Empty for now - these agents don't need special deps
# Could add snyk CLI detection later

# Users can then install with:
# pip install devloop[snyk,code-rabbit]
```

### 2. Enhance `devloop init` Command

Add interactive prompts using `typer`:

```python
# src/devloop/cli/main.py

import typer
from enum import Enum

class OptionalAgent(str, Enum):
    """Available optional agents."""
    CODE_RABBIT = "code-rabbit"
    SNYK = "snyk"
    CI_MONITOR = "ci-monitor"

@app.command()
def init(
    path: Path = typer.Argument(Path.cwd(), help="Project directory"),
    skip_config: bool = typer.Option(False, "--skip-config", help="Skip creating configuration"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive mode"),
):
    """Initialize devloop in a project."""
    
    # Create .devloop directory
    claude_dir = path / ".devloop"
    claude_dir.mkdir(exist_ok=True)
    
    # Create config
    if not skip_config:
        config = Config.default_config()
        
        # Interactive optional agent selection
        if interactive:
            console.print("\n[bold]Optional Agents[/bold]")
            console.print("Select which optional agents to enable:\n")
            
            optional_agents = {
                "code-rabbit": {
                    "description": "Code Rabbit AI-powered code review",
                    "requires": "code-rabbit CLI",
                },
                "snyk": {
                    "description": "Snyk security scanning",
                    "requires": "snyk CLI",
                },
                "ci-monitor": {
                    "description": "CI/CD pipeline monitoring",
                    "requires": "None",
                },
            }
            
            selected = []
            for agent_name, info in optional_agents.items():
                enabled = typer.confirm(
                    f"Enable {agent_name}? ({info['description']}) [Requires: {info['requires']}]",
                    default=False
                )
                if enabled:
                    selected.append(agent_name)
                    config["agents"][agent_name] = {
                        "enabled": True,
                        "triggers": get_default_triggers(agent_name),
                        "config": get_default_config(agent_name),
                    }
        
        config_file = claude_dir / "agents.json"
        config.save(config_file)
        console.print(f"[green]✓[/green] Config saved to {config_file}")
        if selected:
            console.print(f"[green]✓[/green] Enabled optional agents: {', '.join(selected)}")
```

### 3. Update CLI Installer Script

Enhance `install.sh` with interactive menu:

```bash
#!/bin/bash

echo "🚀 DevLoop Installation"
echo "======================"

# ... existing checks ...

# Interactive optional agent selection
echo ""
echo "📦 Optional Agents"
echo "------------------"

ENABLE_CODE_RABBIT=false
ENABLE_SNYK=false
ENABLE_CI_MONITOR=false

read -p "Enable Code Rabbit agent? (y/n) " -n 1 -r REPLY
echo
[[ $REPLY =~ ^[Yy]$ ]] && ENABLE_CODE_RABBIT=true

read -p "Enable Snyk agent? (y/n) " -n 1 -r REPLY
echo
[[ $REPLY =~ ^[Yy]$ ]] && ENABLE_SNYK=true

read -p "Enable CI Monitor agent? (y/n) " -n 1 -r REPLY
echo
[[ $REPLY =~ ^[Yy]$ ]] && ENABLE_CI_MONITOR=true

# Pass selections to init command
python3 -m devloop init \
    --enable-code-rabbit=$ENABLE_CODE_RABBIT \
    --enable-snyk=$ENABLE_SNYK \
    --enable-ci-monitor=$ENABLE_CI_MONITOR
```

### 4. Create Configuration Helpers

Add utilities for agent configuration:

```python
# src/devloop/core/agent_config.py

from typing import Dict, Any

AGENT_DEFAULTS = {
    "code-rabbit": {
        "triggers": ["file:modified", "file:created"],
        "config": {
            "enabled_tools": ["code-rabbit"],
            "api_key": None,  # User must configure
            "file_patterns": ["**/*.py", "**/*.js", "**/*.ts"],
        }
    },
    "snyk": {
        "triggers": ["file:modified", "file:created"],
        "config": {
            "enabled_tools": ["snyk"],
            "severity_threshold": "medium",
            "file_patterns": ["**/*.py", "**/*.js", "package.json"],
        }
    },
    "ci-monitor": {
        "triggers": ["git:push"],
        "config": {
            "check_interval": 60,
            "providers": ["github", "gitlab"],
        }
    },
}

def get_optional_agent_defaults(agent_name: str) -> Dict[str, Any]:
    """Get default configuration for optional agent."""
    return AGENT_DEFAULTS.get(agent_name, {})
```

---

## Implementation Roadmap

### Week 1: Configuration-Based Selection
- [ ] Add `Agent` enum for optional agents
- [ ] Enhance `init` command with interactive prompts
- [ ] Create agent configuration utilities
- [ ] Update install.sh script

**Code changes**: ~200 lines
**Package size impact**: None (agents already included)
**User impact**: Clear, interactive setup experience

### Week 2: Poetry Extras
- [ ] Add extras groups to `pyproject.toml`
- [ ] Update installation docs
- [ ] Create separate install instruction for each

**Code changes**: ~50 lines in pyproject.toml
**Package size impact**: Multiple wheels by extra
**User impact**: Better control over what's installed

### Week 3: Documentation & Testing
- [ ] Document optional agent selection
- [ ] Test interactive flows
- [ ] Update README with optional features
- [ ] Create troubleshooting guide

---

## User Experience Flows

### Flow 1: First-Time User (pip install)
```
$ pip install devloop
$ devloop init /my/project
? Enable Code Rabbit agent? (y/n): n
? Enable Snyk agent? (y/n): y
? Enable CI Monitor agent? (y/n): n
✓ Config saved to .devloop/agents.json
✓ Enabled optional agents: snyk
Next steps:
  1. Review .devloop/agents.json
  2. Configure snyk API key
  3. Run: devloop watch /my/project
```

### Flow 2: Advanced User (with extras)
```
$ pip install devloop[snyk,code-rabbit]
$ devloop init /my/project --no-interactive
✓ Config saved with snyk and code-rabbit enabled
```

### Flow 3: Existing User (no changes)
```
$ pip install devloop
$ devloop init /my/project --skip-optional
✓ Config saved with standard 8 agents
```

---

## Benefits

### For Users
- **Clear choices**: Know what's being enabled
- **Smaller installs**: Install only what they need
- **Easy customization**: Modify selection anytime via config
- **Better onboarding**: Guided through setup

### For Package
- **Reduced bloat**: Core install stays lean
- **Faster CI/CD**: Less code to test by default
- **Clearer features**: Optional features are explicit
- **Future-proof**: Foundation for plugin system

### For Community
- **Example patterns**: Shows how to extend DevLoop
- **Plugin foundation**: Easier to add third-party agents
- **Scalability**: Optional agents model scales well

---

## Considerations & Challenges

### Challenge 1: Importing Non-Installed Agents
**Problem**: If user doesn't install snyk agent, importing it fails
**Solution**: 
```python
# In src/devloop/agents/__init__.py
try:
    from .snyk import SnykAgent
except ImportError:
    SnykAgent = None  # Gracefully skip
```

### Challenge 2: Configuration Migration
**Problem**: Existing users with custom configs
**Solution**: 
```python
# Auto-migrate old config format
if "version" not in config:
    config["version"] = "1.0.0"
    migrate_legacy_config(config)
    save_config(config)
```

### Challenge 3: Help Text & Documentation
**Problem**: Too many options can confuse users
**Solution**:
- Clear descriptions in interactive prompts
- Link to agent documentation
- Provide sensible defaults

### Challenge 4: CLI Tool Detection
**Problem**: User selects snyk but doesn't have CLI installed
**Solution**:
```python
def check_agent_dependencies(agent_name: str) -> tuple[bool, str]:
    """Check if agent has required CLI tools."""
    deps = AGENT_DEPENDENCIES.get(agent_name, {})
    missing = []
    for tool in deps.get("cli", []):
        if not shutil.which(tool):
            missing.append(tool)
    
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, "OK"
```

---

## Success Metrics

- [ ] Interactive init completes in <30 seconds
- [ ] Users understand what each agent does
- [ ] Support tickets about "why is X installed" decreases
- [ ] Installation size matches expectations
- [ ] 80%+ users use at least one optional agent OR skip them

---

## Next Steps

1. Implement Phase 2A (interactive configuration)
2. Gather user feedback on selections
3. Implement Phase 2B (optional dependencies)
4. Plan Phase 3 (plugin architecture)
