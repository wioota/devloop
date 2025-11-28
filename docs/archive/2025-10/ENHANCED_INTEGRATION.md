# Enhanced Claude Agents Integration

## Overview

The enhanced Claude Agents system provides seamless integration between background agents and Amp, featuring single-command installation, automatic fix application, and comprehensive rollback capabilities.

## Key Enhancements

### 1. Single-Command Installation

**One-liner installation:**
```bash
curl -fsSL https://raw.githubusercontent.com/wioota/dev-agents/main/install.sh | bash
```

**Features:**
- Automatic dependency management
- Virtual environment setup
- PATH configuration
- Shell integration (`ca` alias)
- Cross-platform support

### 2. Enhanced Amp Integration

**Automatic Fix Application:**
- Amp can automatically apply safe fixes with: `"Automatically apply safe background agent fixes"`
- Change tracking ensures Amp knows what was modified
- Intelligent summaries of applied changes
- Safety-first approach with configurable risk levels

**Change Awareness:**
- Amp maintains full awareness of background agent changes
- Detailed change logs for transparency
- Context preservation across sessions

### 3. Comprehensive Rollback System

**Easy Rollback Commands:**
```bash
# Check rollback status
rollback.sh status

# Rollback last change
rollback.sh last

# Rollback all changes
rollback.sh all

# List changes for selective rollback
rollback.sh list
```

**Amp Integration:**
- "Rollback the last background agent changes"
- "Show me what changes can be rolled back"
- "Undo the changes from background agents"

## Architecture

### Components

1. **Enhanced Amp Adapter** (`.claude/integration/amp-enhanced-adapter.py`)
   - Autofix mode with change tracking
   - Rollback orchestration
   - Amp context provision

2. **Rollback Utility** (`rollback.sh`)
   - User-friendly rollback interface
   - Status checking and change listing
   - Safe rollback operations

3. **Installation Script** (`install.sh`)
   - Automated setup process
   - Environment configuration
   - Integration setup

### Data Flow

```
User Request → Amp Subagent → Enhanced Adapter → Apply Fixes → Track Changes → Provide Summary
                                      ↓
                              Backup Creation ← Change Logging ← Rollback Ready
```

## Usage Examples

### For Amp Users

**Automatic Fixes:**
```
User: "Automatically apply safe background agent fixes"
Amp: [Spawns subagent to apply fixes]
Result: "Applied 3 fixes: formatting, linting, and import sorting. All changes backed up."
```

**Rollback:**
```
User: "Rollback the last background agent changes"
Amp: [Uses rollback system to undo changes]
Result: "Successfully rolled back 3 changes to their previous state."
```

### For Direct Users

**Installation:**
```bash
curl -fsSL https://raw.githubusercontent.com/wioota/dev-agents/main/install.sh | bash
cd my-project
ca start
```

**Status Checking:**
```bash
ca status                    # Agent status
rollback.sh status          # Rollback status
rollback.sh list           # List changes
```

## Safety Features

### Fix Safety Levels

- **safe_only**: Only high-confidence, low-risk fixes
- **medium_risk**: Includes medium-confidence fixes
- **all**: Applies all available fixes (advanced users)

### Backup System

- Automatic backups before any file modification
- Timestamped backup files with unique IDs
- Easy restoration via rollback commands
- Backup integrity verification

### Change Tracking

- Detailed logs of all applied changes
- Amp-aware summaries for transparency
- Selective rollback capabilities
- Session-based change grouping

## Integration Points

### Amp Commands

The system responds to these natural language commands:

- "Automatically apply safe background agent fixes"
- "Check background agent results for issues"
- "Rollback the last background agent changes"
- "Show me what changes can be rolled back"
- "What did the background agents just change?"

### Context Awareness

Amp maintains awareness through:
- `.claude/context/agent-results.json` - Agent outputs
- `.claude/context/change-log.json` - Applied changes
- `.claude/backups/` - File backups
- Real-time adapter queries

## Error Handling

### Automatic Recovery

- Failed fixes are logged but don't stop the process
- Partial application with detailed reporting
- Backup integrity checks before rollback

### User Guidance

- Clear error messages with suggested actions
- Fallback to manual operations when needed
- Comprehensive help documentation

## Future Enhancements

### Phase 2 (Current Focus)
- [ ] Context engine with project understanding
- [ ] Multi-agent coordination framework
- [ ] Advanced notification system
- [ ] Additional agent types (security, performance, etc.)

### Phase 3 (Learning & Optimization)
- [ ] Developer behavior learning
- [ ] Performance analytics
- [ ] Custom agent creation
- [ ] Team collaboration features

## Testing

The enhanced system includes comprehensive testing:

```bash
# Test autofix workflow
python simulate_auto_fix_workflow.py

# Test Amp integration
python test_amp_integration.py

# Test rollback functionality
./rollback.sh status
```

## Support

For issues or questions:
1. Check the change log: `.claude/context/change-log.json`
2. Use rollback tools: `./rollback.sh help`
3. Review agent results: `.claude/context/agent-results.json`
4. Check installation logs: `~/.dev-agents/install.log`

The enhanced system provides a seamless, safe, and powerful development workflow enhancement that Amp can fully leverage.
