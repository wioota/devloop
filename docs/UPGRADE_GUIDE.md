# Upgrade Guide

## Upgrading DevLoop

### Latest Version

```bash
pip install --upgrade devloop
```

### Version Compatibility

- DevLoop 0.6.x requires Python 3.11+
- For breaking changes between versions, see [CHANGELOG.md](../CHANGELOG.md)

### After Upgrading

```bash
# Update project templates
devloop init --merge-templates /path/to/your/project

# Restart the daemon
devloop stop
devloop watch .
```

### Troubleshooting Upgrades

If you encounter issues after upgrading:

1. Check the [CHANGELOG.md](../CHANGELOG.md) for breaking changes
2. Verify Python version: `python --version` (should be 3.11+)
3. Clear cache: `rm -rf .devloop/cache`
4. Reinstall: `pip uninstall devloop && pip install devloop`

See [CLI_REFERENCE.md](../CLI_REFERENCE.md) for complete command documentation.
