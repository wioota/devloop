# DevLoop VSCode Extension

Real-time agent feedback and inline quick fixes for DevLoop directly in your editor.

## Features

- **Real-time Diagnostics**: See agent findings as inline squiggles with severity-based colors
- **Quick Fixes**: Apply auto-fixes directly from the lightbulb menu
- **Status Bar**: Monitor agent activity at a glance
- **Integrated Experience**: Seamless integration with existing DevLoop workflow

## Requirements

- VSCode 1.80.0 or higher
- Python 3.11 or higher
- DevLoop installed (`pip install devloop`)

## Installation

### From Source (Development)

1. Clone the DevLoop repository:
   ```bash
   git clone https://github.com/wioota/devloop.git
   cd devloop/vscode-extension
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Compile the extension:
   ```bash
   npm run compile
   ```

4. Open in VSCode and press F5 to launch Extension Development Host

### From VSIX (Coming Soon)

1. Download the `.vsix` file from releases
2. In VSCode, go to Extensions view (Ctrl+Shift+X)
3. Click "..." menu → "Install from VSIX..."
4. Select the downloaded file

## Configuration

Open VSCode settings (Ctrl+,) and search for "DevLoop":

```jsonc
{
  // Enable/disable DevLoop
  "devloop.enabled": true,

  // Auto-fix settings
  "devloop.autoFix.enabled": true,
  "devloop.autoFix.safetyLevel": "safe_only", // or "medium_risk", "all"

  // Diagnostic display
  "devloop.diagnostics.showBackgroundFindings": false,

  // Status bar
  "devloop.statusBar.enabled": true,

  // LSP server settings
  "devloop.lsp.pythonPath": "python", // Path to Python interpreter
  "devloop.lsp.debug": false // Enable debug logging
}
```

## Usage

### Viewing Diagnostics

Agent findings appear as:
- **Red squiggles**: Errors (blocking issues)
- **Yellow squiggles**: Warnings (non-blocking issues)
- **Blue squiggles**: Info (suggestions)
- **Gray squiggles**: Style (formatting hints)

Hover over a squiggle to see the full message and suggestion.

### Applying Quick Fixes

1. Place cursor on a diagnostic
2. Click the lightbulb icon or press `Ctrl+.`
3. Select "Fix: ..." to apply the fix
4. Or select "Dismiss this finding" to hide it

### Commands

Open the Command Palette (Ctrl+Shift+P) and search for:

- **DevLoop: Open Agent Dashboard** - View agent status and findings
- **DevLoop: Apply All Safe Fixes** - Apply all safe auto-fixes at once
- **DevLoop: Refresh Diagnostics** - Manually refresh findings
- **DevLoop: Open Agent Configuration** - Edit `.devloop/agents.json`

### Status Bar

Click the DevLoop status bar item to open the Agent Dashboard (coming soon).

## Troubleshooting

### LSP Server Not Starting

If you see "DevLoop LSP server failed to start":

1. Check Python path is correct: `devloop.lsp.pythonPath`
2. Verify DevLoop is installed: `python -m devloop --version`
3. Enable debug logging: `devloop.lsp.debug: true`
4. Check Output panel: View → Output → DevLoop LSP

### No Diagnostics Showing

1. Ensure DevLoop is enabled: `devloop.enabled: true`
2. Check agents are running: `devloop watch` in terminal
3. Verify findings exist: Check `.devloop/context/` directory
4. Refresh diagnostics: Command Palette → "DevLoop: Refresh Diagnostics"

### Python Path Issues

If you're using a virtual environment:

```json
{
  "devloop.lsp.pythonPath": "/path/to/venv/bin/python"
}
```

Or use the Python extension's interpreter:

```json
{
  "devloop.lsp.pythonPath": "${command:python.interpreterPath}"
}
```

## Known Limitations

- **Agent Dashboard**: Webview UI not yet implemented (v0.2.0)
- **Multi-file Fixes**: Not yet supported (v0.2.0)
- **Feedback Submission**: UI not yet implemented (v0.3.0)
- **Performance Metrics**: Not yet displayed (v0.3.0)

## Roadmap

### v0.2.0 (Planned)
- Agent Dashboard webview
- Multi-file fix support
- Configuration UI

### v0.3.0 (Planned)
- Feedback submission UI
- Performance metrics display
- Code lens integration

### v0.4.0 (Planned)
- Inline annotations
- Test coverage overlay
- Collaborative findings

## Development

### Building

```bash
npm run compile
```

### Watching

```bash
npm run watch
```

### Testing

```bash
npm run test
```

### Packaging

```bash
npm run vscode:prepublish
vsce package
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](../LICENSE) for details.

## Links

- [DevLoop Documentation](https://github.com/wioota/devloop)
- [Report Issues](https://github.com/wioota/devloop/issues)
- [VSCode Extension Design](../docs/VSCODE_EXTENSION_DESIGN.md)
