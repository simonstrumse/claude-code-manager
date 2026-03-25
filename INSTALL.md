# Installation Guide

## Quick Install (Recommended)

```bash
pip install ccmanager
```

Or with uv:

```bash
uv pip install ccmanager
```

After installation, launch with:

```bash
ccmanager              # Primary command
claude-code-manager    # Alternative (longer) command
```

## Verify Installation

```bash
ccmanager --help
```

If you see the help output, you're ready to go. Launch the TUI with just `ccmanager`.

## Troubleshooting

### "Command not found" after pip install

Your Python scripts directory may not be in PATH. Common fixes:

**macOS/Linux:**
```bash
# Check where pip installed it
python3 -m site --user-base
# Typically: ~/.local/bin — add to PATH:
export PATH="$HOME/.local/bin:$PATH"
# Add the above line to ~/.zshrc or ~/.bashrc to persist
```

**Or use pipx** (auto-handles PATH):
```bash
pipx install ccmanager
```

### Different servers in Claude Code vs ccmanager

Claude Code merges MCP servers from multiple configuration sources in priority order:

1. **Project Local** (`.claude/settings.local.json`) — Highest priority
2. **Project Settings** (`.claude/settings.json`)
3. **Project MCP** (`.mcp.json`)
4. **User Settings** (`~/.claude/settings.json`)
5. **Global** (`~/.claude.json`) — Lowest priority

Higher priority configs override lower ones.

### Permission denied

```bash
# Install in user directory instead
pip install --user ccmanager
```

## Development Install

For contributing or local development:

```bash
git clone https://github.com/simonstrumse/claude-code-manager.git
cd claude-code-manager
pip install -e ".[dev]"
```
