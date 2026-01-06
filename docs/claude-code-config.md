# Claude Code Configuration Reference

Complete reference for all Claude Code configuration locations, formats, and precedence rules.
This document serves as the knowledge base for the MCP Server Manager scanner.

---

## MCP Server Configuration

### Hierarchy (Highest to Lowest Precedence)

| Level | Location | Shared | Use Case |
|-------|----------|--------|----------|
| **Enterprise** | System directories (see below) | Yes | IT-managed company policies |
| **Local** | `~/.claude.json` → `projects[path].mcpServers` | No | Per-project personal servers |
| **Project** | `.mcp.json` (repository root) | Yes (git) | Team-shared servers |
| **User** | `~/.claude.json` → `mcpServers` | No | Personal global servers |

### File Locations

#### Enterprise (System-Managed)
```
macOS:   /Library/Application Support/ClaudeCode/managed-mcp.json
Linux:   /etc/claude-code/managed-mcp.json
Windows: C:\Program Files\ClaudeCode\managed-mcp.json
```

#### User Global
```
~/.claude.json
```

Structure:
```json
{
  "mcpServers": {
    "server-name": { /* global server config */ }
  },
  "projects": {
    "/absolute/path/to/project": {
      "mcpServers": {
        "server-name": { /* local project server */ }
      }
    }
  }
}
```

#### Project Level
```
.mcp.json (repository root)
```

Structure:
```json
{
  "mcpServers": {
    "server-name": { /* server config */ }
  }
}
```

### Server Types

#### stdio (Local Process)
```json
{
  "server-name": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@package/server"],
    "env": {
      "API_KEY": "value",
      "VAR": "${ENV_VAR:-default}"
    }
  }
}
```

#### http (Remote HTTP Server)
```json
{
  "server-name": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${TOKEN}"
    }
  }
}
```

#### sse (Server-Sent Events) - DEPRECATED
```json
{
  "server-name": {
    "type": "sse",
    "url": "https://api.example.com/sse"
  }
}
```

### Environment Variable Expansion

Supported syntax:
- `${VAR}` - Value of VAR (fails if not set)
- `${VAR:-default}` - Value of VAR, or "default" if not set

Works in: `command`, `args`, `env`, `url`, `headers`

### Settings-Based MCP Control

In `~/.claude/settings.json` or `.claude/settings.json`:

```json
{
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["memory", "github"],
  "disabledMcpjsonServers": ["filesystem"]
}
```

---

## Skills

### Hierarchy

| Level | Location |
|-------|----------|
| **Enterprise** | Managed platform settings |
| **Personal** | `~/.claude/skills/*/SKILL.md` |
| **Project** | `.claude/skills/*/SKILL.md` |
| **Plugin** | `plugin-dir/skills/*/SKILL.md` |

### SKILL.md Format

```yaml
---
name: skill-name                    # Required: lowercase, hyphens/numbers only
description: When to use this...    # Required: triggers Claude's use
allowed-tools: Read, Grep, Glob     # Optional: auto-approved tools
model: claude-sonnet-4-20250514     # Optional: specific model
---

# Skill Title

## Instructions

Your skill instructions in markdown.

## Examples

[Usage examples]
```

### Directory Structure

```
skill-name/
├── SKILL.md              # Required
├── reference.md          # Optional: detailed docs (loaded on demand)
├── examples.md           # Optional: usage examples
└── scripts/
    └── helper.py         # Optional: utility scripts
```

---

## Rules

### Hierarchy

| Level | Location |
|-------|----------|
| **User** | `~/.claude/rules/*.md` |
| **Project** | `.claude/rules/**/*.md` |

### Rule File Format

```yaml
---
paths: src/api/**/*.ts    # Optional: applies only to matching files
---

# Rule Title

Your rule instructions in markdown.
```

### Glob Pattern Support

```
**/*.ts                   # All TypeScript files
src/**/*                  # All files under src/
*.md                      # Markdown files in root
{src,lib}/**/*.ts         # Multiple directories
```

---

## CLAUDE.md Files

### Hierarchy

| Level | Location | Notes |
|-------|----------|-------|
| **Enterprise** | `/Library/Application Support/ClaudeCode/CLAUDE.md` | System-wide |
| **Project Root** | `./CLAUDE.md` OR `./.claude/CLAUDE.md` | Main project instructions |
| **Local** | `./CLAUDE.local.md` | Personal, NOT in git |
| **Subdirectories** | `*/CLAUDE.md` | Loaded when reading files in subtree |
| **User Global** | `~/.claude/CLAUDE.md` | Personal, all projects |

### CLAUDE.md Format

```yaml
---
paths: src/api/**/*.ts    # Optional: applies only to matching files
---

# Project Instructions

Your instructions in markdown.

Supports @imports using @path/to/file syntax.
```

### Import Syntax

- `@relative/path` - Import relative to current file
- `@~/absolute/path` - Import from home directory
- Max import depth: 5 hops
- Imports inside code blocks are ignored

---

## Hooks

### Configuration Location

Hooks are configured in settings.json files (NOT markdown):

| Level | Location |
|-------|----------|
| **Enterprise** | `/Library/Application Support/ClaudeCode/managed-settings.json` |
| **User** | `~/.claude/settings.json` |
| **Project** | `.claude/settings.json` |
| **Local** | `.claude/settings.local.json` |

### Hook Configuration

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/script.sh",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

### Hook Events

**Tool-Related (support matchers):**
- `PreToolUse` - Before tool executes
- `PostToolUse` - After tool completes
- `PermissionRequest` - When permission dialog shown

**Session/Lifecycle (no matchers):**
- `SessionStart` - Session startup/resume
- `SessionEnd` - Session termination
- `UserPromptSubmit` - User submits prompt
- `Stop` - Main agent finished
- `SubagentStop` - Subagent finished

**System Events:**
- `PreCompact` - Before context compaction
- `Notification` - When notifications sent

---

## Settings Files

### Hierarchy (Highest to Lowest)

| Level | Location |
|-------|----------|
| **Enterprise** | `/Library/Application Support/ClaudeCode/managed-settings.json` |
| **Local** | `.claude/settings.local.json` |
| **Project** | `.claude/settings.json` |
| **User** | `~/.claude/settings.json` |

### Common Settings

```json
{
  "permissions": {
    "allow": ["Bash(git:*)", "Read(~/.zshrc)"],
    "deny": ["Bash(curl:*)", "Read(./.env)"]
  },
  "hooks": { /* ... */ },
  "env": { "FOO": "bar" },
  "model": "claude-opus-4-5",
  "enableAllProjectMcpServers": true,
  "disabledMcpjsonServers": ["filesystem"]
}
```

---

## Plugins

### Structure

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json           # Required: manifest
├── commands/
│   └── *.md                  # Slash commands
├── agents/
│   └── */AGENT.md            # Subagents
├── skills/
│   └── */SKILL.md            # Skills
├── hooks/
│   └── hooks.json            # Hook configuration
└── .mcp.json                 # MCP servers (optional)
```

### plugin.json Format

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "description": "...",
  "commands": "commands/*.md",
  "agents": "agents/**/*.md",
  "skills": "skills/**/SKILL.md",
  "hooks": "hooks/hooks.json",
  "mcp": ".mcp.json"
}
```

---

## Summary Table

| Component | User Level | Project Level | Format |
|-----------|-----------|---------------|--------|
| **MCP Servers** | `~/.claude.json` | `.mcp.json` | JSON |
| **Skills** | `~/.claude/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md` | Markdown+YAML |
| **Rules** | `~/.claude/rules/*.md` | `.claude/rules/**/*.md` | Markdown+YAML |
| **CLAUDE.md** | `~/.claude/CLAUDE.md` | `./CLAUDE.md`, `.claude/CLAUDE.md` | Markdown+YAML |
| **Settings** | `~/.claude/settings.json` | `.claude/settings.json` | JSON |
| **Hooks** | In settings.json | In settings.json | JSON |

---

## CLI Commands Reference

```bash
# MCP Server Management
claude mcp list                           # List all servers
claude mcp list --scope user              # User scope only
claude mcp add myserver URL --transport http
claude mcp add myserver --transport stdio -- cmd args
claude mcp remove myserver

# Import from Claude Desktop
claude mcp add-from-claude-desktop
```
