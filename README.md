# Claude Code Manager

A terminal UI (TUI) for managing Claude Code configurations across all your projects. See MCP servers, skills, commands, rules, and CLAUDE.md files in one unified view.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-orange)](https://claude.ai/code)

```
  C L A U D E   C O D E   M A N A G E R
```

## Features

- **Multi-Project Scanning** - Scan a folder of projects and see all configurations at a glance
- **6 Configuration Tabs** - Projects, MCP Servers, Skills, Commands, Rules, CLAUDE.md
- **Content Preview** - Press Enter on any skill, command, rule, or CLAUDE.md to view full content
- **Cross-Navigation** - Jump between projects and their MCP servers with `g` and `s` keys
- **Project Discovery** - Find Claude Code projects scattered across your system
- **Usage Analytics** - See which MCP servers are used most across your projects

## Quick Start

### Prerequisites

- Python 3.8+
- [Textual](https://textual.textualize.io/) (installed automatically)

### Installation

```bash
# Clone the repository
git clone https://github.com/simonstrumse/claude-code-manager.git
cd claude-code-manager

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run!
python mcp_tui.py ~/path/to/your/projects
```

### One-Line Install (for Claude Code)

You can ask Claude Code to install this for you. Paste this into a Claude Code conversation:

```
Please help me install the Claude Code Manager TUI tool.

1. First, review the repository at https://github.com/simonstrumse/claude-code-manager
   to make sure it looks safe and legitimate
2. If it looks good, clone it to ~/tools/claude-code-manager
3. Set up a Python virtual environment and install dependencies
4. Create a shell alias so I can run it easily

Note: Always review code from the internet before running it on your machine!
```

## Usage

### Launch the TUI

```bash
# Scan a projects folder
python mcp_tui.py ~/Projects

# Or scan multiple specific projects
python mcp_tui.py ~/Project1 ~/Project2
```

### Keyboard Navigation

| Key | Action |
|-----|--------|
| `Tab` | Focus detail panel |
| `Enter` | Preview full content (skills, commands, rules, CLAUDE.md) |
| `g` | Jump to project (from MCP tab) |
| `s` | Jump to MCP server (from Projects tab) |
| `d` | Discover projects across system |
| `r` | Refresh scan |
| `o` | Open in Finder (macOS) |
| `q` | Quit |
| `Esc` | Close preview / cancel |

### Tabs Overview

1. **Projects** - All scanned projects with config counts
2. **MCP** - All MCP servers ranked by usage
3. **Skills** - User and project skills
4. **Commands** - Slash commands (/commit, etc.)
5. **Rules** - Always-on instruction files
6. **CLAUDE.md** - Project documentation files

## What It Scans

### Configuration Hierarchy

The tool understands Claude Code's configuration precedence:

| Level | Location | Priority |
|-------|----------|----------|
| Enterprise | `/Library/Application Support/ClaudeCode/` | Highest |
| Local | `~/.claude.json` -> `projects[path]` | 2nd |
| Project | `.mcp.json` | 3rd |
| User | `~/.claude.json` -> `mcpServers` | Lowest |

### Scanned Locations

- **MCP Servers**: Enterprise, User, Project, Local levels
- **Skills**: `~/.claude/skills/*/SKILL.md` and `.claude/skills/*/SKILL.md`
- **Commands**: `~/.claude/commands/*.md` and `.claude/commands/*.md`
- **Rules**: `~/.claude/rules/**/*.md` and `.claude/rules/**/*.md`
- **CLAUDE.md**: Root, `.claude/`, subdirectories, local variants

## Contributing

Contributions are welcome! This is my first maintained open source project, so please be patient and constructive.

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/claude-code-manager.git
cd claude-code-manager

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt

# Run the TUI
python mcp_tui.py ~/Projects
```

### Guidelines

1. **Be respectful** - This is a learning project
2. **Test your changes** - Make sure the TUI runs without crashing
3. **Follow existing patterns** - Look at how similar features are implemented
4. **Document changes** - Update CHANGELOG.md for significant changes
5. **Keep it simple** - Prefer readable code over clever code

### Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Test thoroughly: `python mcp_tui.py ~/Projects`
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request with a description of your changes

### Code Style

- Use Python type hints where helpful
- Follow existing naming conventions
- Keep functions focused and small
- Add comments for non-obvious logic

## Project Structure

```
claude-code-manager/
├── mcp_tui.py          # Main TUI application (Textual)
├── mcp_scanner.py      # Configuration scanning logic
├── mcp_data.py         # Data models and classes
├── mcp_config.py       # User settings management
├── mcp_operations.py   # Project move/consolidate operations
├── mcp_manager.py      # Legacy CLI tool
├── requirements.txt    # Python dependencies
├── CHANGELOG.md        # Development history
└── docs/
    └── claude-code-config.md  # Configuration reference
```

## Troubleshooting

### "No projects found"
- Make sure you're pointing to a directory that contains Claude Code projects
- Projects need `.git`, `.mcp.json`, or `.claude/` folder to be detected

### TUI looks broken
- Make sure your terminal supports Unicode
- Try a different terminal (iTerm2, Alacritty, Windows Terminal)
- Ensure terminal is at least 100 columns wide

### Preview not opening
- Tab to focus the detail panel first
- Then press Enter
- Press Escape or 'q' to close the preview

## License

MIT License - see [LICENSE](LICENSE) file.

## Acknowledgments

- Built with [Textual](https://textual.textualize.io/) - the amazing Python TUI framework
- Inspired by the need to understand Claude Code's configuration system
- Thanks to Anthropic for creating Claude Code

---

**Safe Computing Reminder**: Always review code from the internet before running it. This tool only reads your configuration files - it doesn't modify anything without your explicit action (like project moves).
