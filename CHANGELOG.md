# MCP Server Manager - Development Changelog

This changelog tracks implementation decisions, bug fixes, and feature additions across all development sessions.

---

## 2026-01-07 - README Enhancement & GitHub Optimization

### Features Added
- **README Overhaul** — Restructured following best practices from popular repos
  - Added navigation links at top for quick section jumping
  - Added screenshot preview (uses existing `screenshots/interactive-mode.png`)
  - Simplified Quick Start to 4 lines of copy-paste commands
  - Added `Built with Textual` badge
  - Moved Troubleshooting to collapsible `<details>` sections
  - Cleaned up section organization with horizontal rules
  - **Files**: `README.md`

- **Open in Finder Enhancement** — Now reveals files in their actual subdirectory
  - Uses `open -R <file>` to reveal and select files in Finder
  - Previously only opened project root folder
  - **Files**: `mcp_tui.py` `action_open_project()`

### Bug Fixes
- **Detail Panel Content Clipping** — Skills/servers were cut off without scrolling
  - Root cause: `Static` widget in `ScrollableContainer` needed `refresh(layout=True)` call
  - Added layout refresh when project changes via `set_project()`
  - **Files**: `mcp_tui.py` `ProjectDetailPanel.set_project()`

### Technical Insights
- Shields.io badges should link to relevant resources (LICENSE file, Python.org, etc.)
- GitHub README best practices: tagline, badges, screenshot, quick start, then details
- Collapsible `<details>` sections reduce visual clutter while preserving info
- `open -R` on macOS reveals and selects a file in Finder (vs `open` which opens folder)

---

## 2026-01-07 (Late Night) - ProjectDetailPanel Navigation & Direct Table Preview

### Features Added
- **ProjectDetailPanel Multi-Item Navigation** — Enhanced to navigate through all config items
  - Supports servers, skills, rules, and CLAUDE.md files in a flat list
  - Use ↑↓ to navigate when panel is focused
  - Enter on server → jumps to MCP tab
  - Enter on skill/rule/claude_md → opens FilePreviewModal
  - `_build_items_list()` aggregates all items into navigable list
  - `_is_selected()` helper for highlight state
  - **Files**: `mcp_tui.py` `ProjectDetailPanel` class

- **Direct Table Preview** — Press Enter directly in tables to open file preview
  - Skills table: Enter opens SKILL.md preview
  - Commands table: Enter opens command preview
  - Rules table: Enter opens rule preview
  - CLAUDE.md table: Enter opens CLAUDE.md preview
  - No longer need to Tab to detail panel first
  - **Implementation**: Added `on_data_table_row_selected()` handler
  - **Files**: `mcp_tui.py`

- **CLI Command** — Install with `pip install -e .` and run `ccmanager ~/Projects`
  - Added `main()` entry point function
  - Added `[project.scripts]` to `pyproject.toml`
  - Two commands: `ccmanager` and `claude-code-manager`
  - **Files**: `mcp_tui.py`, `pyproject.toml`, `README.md`

### Bug Fixes
- **Detail Panel Scrolling** — Content was being cut off without scrollbar
  - Changed `NonFocusableScroll` to extend `VerticalScroll` instead of `ScrollableContainer`
  - Added `height: auto` CSS to all detail panels
  - Added `overflow-y: auto` to `.detail-container`
  - **Root cause**: `Static` widgets need proper container for scrolling
  - **Files**: `mcp_tui.py` CSS and container class

- **CLAUDE.md Selection Highlight Missing** — Selection wasn't visible in ProjectDetailPanel
  - Added `_is_selected('claude_md', claude_md)` check with reverse highlighting
  - **Files**: `mcp_tui.py` `ProjectDetailPanel.render()`

### Technical Insights
- DataTable uses `RowHighlighted` event for cursor movement (updates detail panel)
- DataTable uses `RowSelected` event for Enter key press (now opens preview directly)
- This two-event model enables both passive browsing and active selection
- `VerticalScroll` provides better automatic scrolling than `ScrollableContainer` for text content
- `Static` widgets with `height: auto` grow to fit content, enabling proper scrolling

---

## 2026-01-07 (Night) - Compact Headers, Commands Tab & Type Mismatch Fixes

### Bug Fixes
- **ServerDetailPanel Crash** — `AttributeError: 'ProjectInfo' object has no attribute 'mcp_servers'`
  - **Root cause**: `ServerUsage.projects` contains `ProjectInfo` (has `servers`) not `EnhancedProjectInfo` (has `mcp_servers`)
  - **Fix**: Used `getattr()` pattern: `servers_list = getattr(project, 'mcp_servers', None) or getattr(project, 'servers', [])`
  - **Files**: `mcp_tui.py` `ServerDetailPanel.render()`

- **ProjectDetailPanel Crash** — Same type mismatch issue when navigating from MCP tab to project
  - **Root cause**: Panel could receive either `ProjectInfo` or `EnhancedProjectInfo`
  - **Fix**: Applied same `getattr()` pattern in `on_key()` and `render()` methods
  - **Also fixed**: `server.level` access (MCPServerConfig has it, ServerDetail doesn't)
  - **Files**: `mcp_tui.py` `ProjectDetailPanel.on_key()`, `ProjectDetailPanel.render()`

- **ProjectDetailPanel Crash (skills/rules/claude_mds)** — `AttributeError: 'ProjectInfo' object has no attribute 'skills'`
  - **Root cause**: `_navigate_to_project()` passed the `ProjectInfo` param directly instead of looking up the full `EnhancedProjectInfo`
  - **Fix 1**: `_navigate_to_project()` now uses `p` (from `self.projects`) instead of the `project` parameter
  - **Fix 2**: Also added `getattr()` fallbacks in `ProjectDetailPanel.render()` for defensive coding
  - **Files**: `mcp_tui.py` `_navigate_to_project()`, `ProjectDetailPanel.render()`

### Features Added
- **Compact 2-Line ASCII Art Header** — Ultra-compact half-block font
  - Full "CLAUDE CODE MANAGER" in ~70 chars width using ▀▄█ characters
  - Static header (same for all tabs) - simpler, no tab-specific subheaders
  - Reduced from 6-line height to 2-line height

- **Commands Tab** — New tab for slash commands (/commit, etc.)
  - `CommandDetailPanel` class for command details
  - Table shows command name, level, and description
  - Handler for row selection and detail display

- **Stats Bar Consistency** — Changed "Docs" to "CLAUDE.md" for clarity

- **Enhanced Discovery Modal** — Complete UI overhaul
  - Replaced checkbox layout with `DataTable` for better visibility
  - Selection indicators: `●` selected, `○` not selected
  - Columns: Selection, Project Name, Parent Directory, Git Status
  - Toggle selection with `Space` key or click

- **Confirmation Dialog** — New `ConfirmMoveModal` screen
  - Shows list of projects to be moved (smart abbreviation for large lists)
  - Displays destination directory
  - Requires explicit yes/no confirmation before moving

- **Open in Finder** — Press `o` to explore project in macOS Finder
  - Uses `subprocess.run(["open", path])` for native integration

- **Discovery Exclusions** — System folders automatically filtered
  - Added `DISCOVERY_EXCLUDE` set in `mcp_scanner.py`
  - Excludes: `.claude`, `Downloads`, `Library`, `Applications`, `.Trash`, `.config`, `node_modules`, `.npm`, `.cache`

### Files Modified
| File | Changes |
|------|---------|
| `mcp_tui.py` | `ServerDetailPanel.render()` fix, `DiscoveryModal` rewrite, `ConfirmMoveModal` added |
| `mcp_scanner.py` | Added `DISCOVERY_EXCLUDE` set, filtering logic in `ProjectDiscovery` |

### Technical Insights
- Textual `DataTable` provides better selection UX than raw checkboxes
- Type mismatch between `ServerUsage.projects: List[ProjectInfo]` annotation and actual `EnhancedProjectInfo` contents - `getattr()` pattern handles both
- `EnhancedProjectInfo.servers` property returns only project-level servers for backward compatibility

---

## 2026-01-06 (Late Evening) - Discovery Modal & Dynamic UI

### Features Added
- **Dynamic ASCII Art Header** — Header changes based on active tab
  - Projects → "CLAUDE CODE MANAGER"
  - MCP → "MCP MANAGER" (green)
  - Skills → "SKILL MANAGER" (magenta)
  - Rules → "RULES MANAGER" (blue)
  - CLAUDE.md → "DOCS MANAGER" (yellow)

- **Discovery Modal** — Interactive project selection dialog
  - Shows all projects found outside current folder
  - Checkbox selection (all selected by default)
  - Buttons: Move Selected, Select All, Select None, Cancel
  - Keyboard shortcuts: `a` all, `n` none, `m` move, `Esc` cancel
  - Automatic refresh after moving projects

- **Tab Rename** — "Servers" tab renamed to "MCP"

- **Project Discovery Action** — Press `d` to scan system for Claude projects (`mcp_tui.py`)
  - Scans DISCOVERY_LOCATIONS: ~/Documents, ~/Developer, ~/Projects, ~/Code, etc.
  - Shows projects found outside current folder
  - Saves discovery results to config for persistence

- **In-App Help** — Press `?` for configuration concepts guide
  - Explains MCP Servers, Skills, Commands, Rules, CLAUDE.md
  - Highlights nesting rules (Skills/Commands=NO, Rules/CLAUDE.md=YES)
  - 30-second timeout notification

- **Project Operations Module** — `mcp_operations.py`
  - `move_project()` — Safe project relocation with conflict detection
  - `consolidate_projects()` — Batch move with conflict resolution
  - `check_move_conflicts()` — Pre-flight validation
  - `get_project_size()` / `format_size()` — Size utilities

- **Session Changelog Rule** — `.claude/rules/session-changelog.md`
  - Turn-start protocol for capturing changes
  - Entry format with features, bugs, architecture sections

### Files Modified
| File | Changes |
|------|---------|
| `mcp_tui.py` | Added `d` and `?` bindings, `action_discover()`, `action_show_help()` |
| `mcp_scanner.py` | Added `ProjectDiscovery` class, discovery functions |
| `mcp_operations.py` | Created with move/consolidate functionality |
| `mcp_config.py` | Added `ProjectFolder`, multi-folder support |
| `.claude/rules/session-changelog.md` | Created changelog rule |
| `CHANGELOG.md` | Created with full project history |

### Technical Insights
- Textual notifications support Rich markup for styled help text
- Discovery uses `os.path.realpath()` to prevent symlink re-scanning
- Config persists to `~/.config/mcp-manager/settings.json`

---

## 2026-01-06 (Evening) - Multi-Directory & Discovery

### Features Added
- **Project Discovery Scanner** — Efficient system-wide project discovery (`mcp_scanner.py`)
  - Scans smart locations: `~/Documents`, `~/Developer`, `~/Projects`, `~/Code`, `~/GitHub`, etc.
  - Two modes: `claude_only` (only Claude Code projects) and `all_projects`
  - Prevents re-scanning with realpath deduplication
  - Configurable depth (default: 3 levels)

- **Multi-Folder Configuration** — Persistent project folder management (`mcp_config.py`)
  - `ProjectFolder` dataclass with path, name, and primary flag
  - Add/remove project folders with automatic primary fallback
  - Discovery cache with timestamp for efficient re-scans
  - Persisted to `~/.config/mcp-manager/settings.json`

- **Session Changelog Rule** — Self-documenting development tracking (`.claude/rules/session-changelog.md`)

### Files Modified
| File | Changes |
|------|---------|
| `mcp_scanner.py` | Added `ProjectDiscovery` class, `DISCOVERY_LOCATIONS`, `CLAUDE_PROJECT_MARKERS`, convenience functions |
| `mcp_config.py` | Added `ProjectFolder`, multi-folder support, discovery cache fields |
| `.claude/rules/session-changelog.md` | Created changelog tracking rule |
| `CHANGELOG.md` | Created with full project history |

---

## 2026-01-06 (Afternoon) - Skills/Commands Separation & Stats Fix

### Bug Fixes
- **Skills Miscount (800+ shown instead of ~11)** — Root cause: `project.skills.extend(self._user_skills)` duplicated user skills into EVERY project (8 skills × 108 projects = 864)
  - **Fix**: Track user-level items separately, don't add to project lists
  - **Files**: `mcp_scanner.py`, `mcp_tui.py`

- **TwoWayDict Navigation Crash** — `TypeError: 'TwoWayDict' object is not subscriptable` when pressing Enter in detail view
  - **Root cause**: Used `_row_locations[key]` which returns TwoWayDict, not row index
  - **Fix**: Changed to `move_cursor(row=idx)` with index-based iteration
  - **Files**: `mcp_tui.py` lines ~1100-1150

### Features Added
- **Commands Category** — Separated slash commands from skills (`mcp_data.py`, `mcp_scanner.py`)
  - New `CommandInfo` dataclass
  - `_scan_commands_directory()` and `_parse_command_md()` methods
  - Commands are flat (`commands/*.md`), Skills are folder-based (`skills/name/SKILL.md`)

- **User-Level Item Tracking** — Stats bar shows unique counts
  - `_user_skills`, `_user_commands`, `_user_rules` tracked separately
  - `get_user_*()` methods on `ComprehensiveScanner`
  - `StatsBar.update_stats()` accepts user-level counts

- **In-App Help Legend** — Educational text in keyboard help
  - Explains: MCP, Skills, Commands, Rules, CLAUDE.md in one line
  - Non-intrusive, productivity-focused

### Documentation Added
- **Quick Concepts Guide** — Added to `docs/claude-code-config.md`
  - What each component does (MCP, Skills, Commands, Rules, CLAUDE.md)
  - User vs Project scope explanation
  - Nesting rules: Skills/Commands=NO, Rules/CLAUDE.md=YES

- **Commands Section** — Full documentation with examples
  - Frontmatter format, file structure
  - Comparison table: Commands vs Skills

### Technical Insights
- Textual's `DataTable._row_locations` is a `TwoWayDict` mapping row_key↔index
- Cannot subscript directly; use `move_cursor(row=idx)` for navigation
- Skills count should NOT include duplicates per project

---

## 2026-01-06 (Morning) - TUI Crash Fixes & Navigation

### Bug Fixes
- **MissingStyle Exception** — Rich markup error when rendering server type
  - **Root cause**: `[stdio]` interpreted as Rich style markup
  - **Fix**: Escape brackets or use plain text rendering
  - **Files**: `mcp_tui.py` detail panel rendering

- **DataTable Empty Lists** — Table showed "0 projects" despite data existing
  - **Root cause**: `table.clear(columns=True)` caused state sync issues
  - **Fix**: Only add columns once, then `table.clear()` without clearing columns
  - **Files**: `mcp_tui.py` `_populate_projects_table()`, `_populate_servers_table()`

### Features Added
- **Tab Navigation** — Jump between tabs with keyboard shortcuts
  - `g` → Jump to project's server in Servers tab
  - `s` → Jump to server's projects in Projects tab
  - Tab key to focus detail panel

- **Detail Panel Focus** — Tab key moves focus to detail panel for scrolling

### Files Modified
| File | Changes |
|------|---------|
| `mcp_tui.py` | Navigation methods, crash fixes, column handling |

---

## 2026-01-06 (Early Morning) - Initial TUI Implementation

### Features Added
- **Textual TUI Application** — Full-featured terminal interface
  - 5 tabs: Projects, MCP Servers, Skills, Rules, CLAUDE.md
  - DataTable with row selection and highlighting
  - Detail panels for each tab
  - Stats bar with totals
  - Keyboard-driven navigation

- **Comprehensive Scanner** — `ComprehensiveScanner` class
  - Scans all Claude Code configuration levels
  - Enterprise → User → Project → Local precedence
  - Skills, Rules, CLAUDE.md, Hooks, Settings

- **Enhanced Data Models** — Rich dataclasses (`mcp_data.py`)
  - `MCPServerConfig`, `SkillInfo`, `RuleInfo`, `ClaudeMdInfo`, `HookInfo`
  - `EnhancedProjectInfo` with counts and aggregations

### Architecture Decisions
- **Textual Framework** — Chosen for async support and rich widgets
- **Separate Scanner Classes** — `EnhancedScanner` (basic) vs `ComprehensiveScanner` (full)
- **Cached User Data** — Load user-level config once, reuse for all projects

---

## 2026-01-06 (Pre-Dawn) - Project Genesis

### Initial Scope
- User asked about MCP server management tools
- Explored existing projects: MCP Hub, MCP Router, claude-code-tool-manager
- Decided to build custom TUI-first solution

### Research Findings
- **MCP Hub** (406 stars): Single unified endpoint concept
- **MCP Router** (1.5k stars): Project/workspace organization, tool toggling
- **claude-code-tool-manager** (32 stars): Most comprehensive, manages all config types

### Design Decisions
- Python + Textual (no Electron/Tauri)
- Multi-project scanning with unified view
- Usage analytics (which servers used most)
- Configuration conflict detection

---

## Project Structure

```
mcp-server-manager/
├── mcp_manager.py      # CLI entry point
├── mcp_tui.py          # Textual TUI application
├── mcp_scanner.py      # Project & config scanning
├── mcp_data.py         # Data models
├── mcp_config.py       # User configuration
├── docs/
│   └── claude-code-config.md  # Configuration reference
├── .claude/
│   └── rules/
│       └── session-changelog.md  # This changelog rule
└── CHANGELOG.md        # This file
```

---

## Known Issues & Future Work

### Open
- [ ] Project move/consolidate feature (relocate scattered projects)
- [ ] Help tab with pedagogical documentation
- [ ] Project discovery integration with TUI

### Resolved
- [x] DataTable empty on load (fixed: column handling)
- [x] Navigation crash (fixed: index-based cursor)
- [x] Skills miscount (fixed: separate user tracking)
- [x] Commands confused with skills (fixed: separate category)
