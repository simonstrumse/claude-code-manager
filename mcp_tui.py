"""
Interactive TUI for MCP Server Manager.
Uses textual library for rich terminal interface.
Comprehensive scanning for MCP Servers, Skills, Rules, and CLAUDE.md files.
"""

import os
from typing import List, Optional, Union

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer, Center, Grid
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Label,
    Static,
    TabbedContent,
    TabPane,
)
from rich.text import Text


class NonFocusableScroll(ScrollableContainer):
    """ScrollableContainer that can't receive focus (skipped in tab order).

    The detail panels inside ARE focusable for keyboard navigation.
    Mouse wheel scrolling still works on this container.
    """
    can_focus = False


class JumpToProject(Message):
    """Message to request jumping to a project in the Projects tab."""
    def __init__(self, project: 'EnhancedProjectInfo') -> None:
        self.project = project
        super().__init__()


class JumpToServer(Message):
    """Message to request jumping to a server in the Servers tab."""
    def __init__(self, server_name: str) -> None:
        self.server_name = server_name
        super().__init__()

from mcp_data import (
    ProjectInfo, ServerDetail, ServerUsage, compute_server_usages,
    EnhancedProjectInfo, SkillInfo, CommandInfo, RuleInfo, ClaudeMdInfo,
    compute_skill_usages, compute_rule_usages, SkillUsage, RuleUsage
)
from mcp_scanner import EnhancedScanner, ComprehensiveScanner, discover_claude_projects
from mcp_config import UserConfig, load_config, save_config
from mcp_operations import consolidate_projects, move_project, MoveResult


# Main header (constant) - Compact 2-line ASCII art using half-blocks
# Fits "CLAUDE CODE MANAGER" in ~70 chars width
MAIN_HEADER = """[bold cyan]
  █▀▀ █   ▄▀█ █ █ █▀▄ █▀▀   █▀▀ █▀█ █▀▄ █▀▀   █▀▄▀█ ▄▀█ █▄ █ ▄▀█ █▀▀ █▀▀ █▀█
  █▄▄ █▄▄ █▀█ █▄█ █▄▀ ██▄   █▄▄ █▄█ █▄▀ ██▄   █ ▀ █ █▀█ █ ▀█ █▀█ █▄█ ██▄ █▀▄[/]"""

KEYBOARD_HELP = """
[bold white]Navigation:[/]  [cyan]1-6[/] Switch tabs   [cyan]↑↓[/] Select   [cyan]Tab[/] Focus detail   [cyan]Enter[/] Preview   [cyan]o[/] Open   [cyan]p[/] Private   [cyan]d[/] Discover   [cyan]r[/] Refresh   [cyan]q[/] Quit
"""


class HeaderWidget(Static):
    """Static header with ASCII art title and keyboard help."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._private_mode = False

    def on_mount(self) -> None:
        """Set content when mounted."""
        self._refresh_content()

    def set_private_mode(self, enabled: bool) -> None:
        """Update private mode indicator."""
        self._private_mode = enabled
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Refresh the header content."""
        if self._private_mode:
            indicator = "\n[bold red on black] 🔒 PRIVATE MODE - Names redacted for screenshots [/]"
            content = MAIN_HEADER + indicator + "\n" + KEYBOARD_HELP
        else:
            content = MAIN_HEADER + "\n" + KEYBOARD_HELP
        self.update(Text.from_markup(content))


class StatsBar(Static):
    """Statistics bar showing comprehensive scan summary."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._projects: List[EnhancedProjectInfo] = []
        self._user_skill_count: int = 0
        self._user_command_count: int = 0
        self._user_rule_count: int = 0

    def update_stats(
        self,
        projects: List[EnhancedProjectInfo],
        user_skills: int = 0,
        user_commands: int = 0,
        user_rules: int = 0
    ) -> None:
        """Update statistics with new project data."""
        self._projects = projects
        self._user_skill_count = user_skills
        self._user_command_count = user_commands
        self._user_rule_count = user_rules
        self.refresh()

    def render(self) -> Text:
        total = len(self._projects)

        # Count unique servers across all projects
        seen_servers = set()
        for p in self._projects:
            for s in p.mcp_servers:
                seen_servers.add(s.name)
        total_servers = len(seen_servers)

        # Count project-level skills/commands/rules (user-level counted separately)
        project_skills = sum(p.skill_count for p in self._projects)
        project_commands = sum(p.command_count for p in self._projects)
        project_rules = sum(p.rule_count for p in self._projects)

        # Total = user + project (no duplication now)
        total_skills = self._user_skill_count + project_skills
        total_commands = self._user_command_count + project_commands
        total_rules = self._user_rule_count + project_rules

        # CLAUDE.md - count unique paths
        seen_claude_mds = set()
        for p in self._projects:
            for cm in p.claude_mds:
                seen_claude_mds.add(cm.path)
        total_claude_mds = len(seen_claude_mds)

        return Text.from_markup(
            f"[bold]Projects:[/] {total}  "
            f"[bold]MCP:[/] [green]{total_servers}[/]  "
            f"[bold]Skills:[/] [magenta]{total_skills}[/]  "
            f"[bold]Cmds:[/] [cyan]{total_commands}[/]  "
            f"[bold]Rules:[/] [blue]{total_rules}[/]  "
            f"[bold]CLAUDE.md:[/] [yellow]{total_claude_mds}[/]"
        )


# =============================================================================
# DETAIL PANELS
# =============================================================================

class ProjectDetailPanel(Static):
    """Detail panel showing selected project's full configuration.

    Focusable with Tab key. When focused, use ↑↓ to select items, Enter to preview/jump.
    Supports navigation through: MCP Servers, Skills, Rules, CLAUDE.md files.
    """

    can_focus = True  # Make this panel focusable

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project: Optional[EnhancedProjectInfo] = None
        self._selected_idx: int = 0  # Track which item is selected (flat index)
        self._items: List[tuple] = []  # List of (type, item) tuples for navigation

    def set_project(self, project: Optional[EnhancedProjectInfo]) -> None:
        self.project = project
        self._selected_idx = 0  # Reset selection
        self._build_items_list()
        # Force a complete refresh and layout recalculation
        self.refresh(layout=True)

    def _build_items_list(self) -> None:
        """Build flat list of navigable items."""
        self._items = []
        if not self.project:
            return
        p = self.project
        # Add servers
        servers_list = getattr(p, 'mcp_servers', None) or getattr(p, 'servers', [])
        for server in servers_list:
            self._items.append(('server', server))
        # Add skills
        for skill in getattr(p, 'skills', []):
            self._items.append(('skill', skill))
        # Add rules
        for rule in getattr(p, 'rules', []):
            self._items.append(('rule', rule))
        # Add CLAUDE.md files
        for claude_md in getattr(p, 'claude_mds', []):
            self._items.append(('claude_md', claude_md))

    def on_focus(self) -> None:
        """When panel receives focus, refresh to show selection highlight."""
        self.refresh()

    def on_blur(self) -> None:
        """When panel loses focus, refresh to hide selection highlight."""
        self.refresh()

    def on_key(self, event) -> None:
        """Handle keyboard navigation within the detail panel."""
        if not self._items:
            return

        max_idx = len(self._items) - 1

        if event.key == "up":
            self._selected_idx = max(0, self._selected_idx - 1)
            self.refresh()
            event.stop()
        elif event.key == "down":
            self._selected_idx = min(max_idx, self._selected_idx + 1)
            self.refresh()
            event.stop()
        elif event.key == "enter":
            if 0 <= self._selected_idx < len(self._items):
                item_type, item = self._items[self._selected_idx]
                if item_type == 'server':
                    self.post_message(JumpToServer(item.name))
                elif item_type == 'skill':
                    self.app.push_screen(FilePreviewModal(
                        title=f"Skill: {item.name}",
                        file_path=item.path
                    ))
                elif item_type == 'rule':
                    self.app.push_screen(FilePreviewModal(
                        title=f"Rule: {item.name}",
                        file_path=item.path
                    ))
                elif item_type == 'claude_md':
                    self.app.push_screen(FilePreviewModal(
                        title=f"CLAUDE.md: {item.filename}",
                        file_path=item.path
                    ))
            event.stop()

    def _is_selected(self, item_type: str, item) -> bool:
        """Check if an item is currently selected."""
        if not self.has_focus or self._selected_idx >= len(self._items):
            return False
        sel_type, sel_item = self._items[self._selected_idx]
        return sel_type == item_type and sel_item is item

    def render(self) -> Text:
        if not self.project:
            return Text.from_markup("[dim]← Select a project to see details[/]")

        lines = []
        p = self.project
        is_focused = self.has_focus

        # Header
        git_badge = "[green]● git[/]" if p.has_git else "[dim]○ no git[/]"
        mcp_badge = "[green]● mcp[/]" if p.has_mcp_config else "[yellow]○ global[/]"
        lines.append(f"[bold cyan]{self.app._redact(p.name)}[/]  {git_badge}  {mcp_badge}")
        lines.append(f"[dim]{self.app._redact_path(p.path)}[/]")
        if is_focused:
            lines.append("[cyan]↑↓ navigate • Enter preview/jump[/]")
        lines.append("")

        # MCP Servers
        servers_list = getattr(p, 'mcp_servers', None) or getattr(p, 'servers', [])
        if servers_list:
            lines.append(f"[bold]MCP Servers ({len(servers_list)}):[/]")
            for server in servers_list:
                level = getattr(server, 'level', 'project')
                level_color = {"enterprise": "red", "user": "yellow", "project": "green", "local": "cyan"}.get(level, "white")
                name = self.app._redact(server.name)

                if self._is_selected('server', server):
                    lines.append(f"  [reverse] [bold yellow]{name}[/] {server.server_type} [{level_color}]{level}[/] [/reverse]")
                else:
                    lines.append(f"  [bold yellow]{name}[/] [dim]{server.server_type}[/] [{level_color}]{level}[/]")
            lines.append("")

        # Skills
        skills_list = getattr(p, 'skills', [])
        if skills_list:
            lines.append(f"[bold]Skills ({len(skills_list)}):[/]")
            for skill in skills_list:
                level_color = {"project": "green", "personal": "yellow"}.get(skill.level, "white")
                if self._is_selected('skill', skill):
                    lines.append(f"  [reverse] [magenta]{skill.name}[/] [{level_color}]{skill.level}[/] [/reverse]")
                else:
                    lines.append(f"  [magenta]{skill.name}[/] [{level_color}]{skill.level}[/]")
            lines.append("")

        # Rules
        rules_list = getattr(p, 'rules', [])
        if rules_list:
            lines.append(f"[bold]Rules ({len(rules_list)}):[/]")
            for rule in rules_list:
                level_color = {"user": "yellow", "project": "green"}.get(rule.level, "white")
                if self._is_selected('rule', rule):
                    lines.append(f"  [reverse] [blue]{rule.name}[/] [{level_color}]{rule.level}[/] [/reverse]")
                else:
                    lines.append(f"  [blue]{rule.name}[/] [{level_color}]{rule.level}[/]")
            lines.append("")

        # CLAUDE.md files
        claude_mds_list = getattr(p, 'claude_mds', [])
        if claude_mds_list:
            lines.append(f"[bold]CLAUDE.md ({len(claude_mds_list)}):[/]")
            for claude_md in claude_mds_list:
                imports_badge = "[green]@[/]" if claude_md.has_imports else " "
                level_color = {
                    "enterprise": "red",
                    "user": "yellow",
                    "project": "green",
                    "local": "cyan",
                    "subdirectory": "dim"
                }.get(claude_md.level, "white")
                # Show filename or relative path
                filename = os.path.basename(claude_md.path)
                if claude_md.level == "subdirectory" and hasattr(claude_md, 'relative_dir'):
                    filename = f"{claude_md.relative_dir}/CLAUDE.md"
                if self._is_selected('claude_md', claude_md):
                    lines.append(f"  [reverse] {imports_badge} [{level_color}]{claude_md.level}[/] {filename} [/reverse]")
                else:
                    lines.append(f"  {imports_badge} [{level_color}]{claude_md.level}[/] [dim]{filename}[/]")
            lines.append("")

        # Pre-commit hooks
        pre_commit = getattr(p, 'pre_commit', None)
        if pre_commit:
            lines.append(f"[bold]Pre-commit ({pre_commit.hook_count} hooks):[/]")
            # Group by repo
            by_repo = {}
            for hook in pre_commit.hooks:
                repo_name = hook.repo_url.split('/')[-1] if '/' in hook.repo_url else hook.repo_url
                if repo_name not in by_repo:
                    by_repo[repo_name] = []
                by_repo[repo_name].append(hook.id)
            for repo_name, hooks in by_repo.items():
                lines.append(f"  [dim]{repo_name}:[/] {', '.join(hooks)}")
            lines.append("")

        if not any([servers_list, skills_list, rules_list, claude_mds_list, pre_commit]):
            lines.append("[dim]No Claude Code configuration found[/]")

        return Text.from_markup("\n".join(lines))


class ServerDetailPanel(Static):
    """Detail panel showing selected server's usage across projects.

    Focusable with Tab key. When focused, use ↑↓ to select projects, Enter to jump.
    """

    can_focus = True  # Make this panel focusable

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_usage: Optional[ServerUsage] = None
        self._selected_project_idx: int = 0  # Track which project is selected

    def set_server(self, server_usage: Optional[ServerUsage]) -> None:
        self.server_usage = server_usage
        self._selected_project_idx = 0  # Reset selection
        self.refresh()

    def on_focus(self) -> None:
        """When panel receives focus, refresh to show selection highlight."""
        self.refresh()

    def on_blur(self) -> None:
        """When panel loses focus, refresh to hide selection highlight."""
        self.refresh()

    def on_key(self, event) -> None:
        """Handle keyboard navigation within the detail panel."""
        if not self.server_usage or not self.server_usage.projects:
            return

        max_idx = min(len(self.server_usage.projects), 12) - 1

        if event.key == "up":
            self._selected_project_idx = max(0, self._selected_project_idx - 1)
            self.refresh()
            event.stop()
        elif event.key == "down":
            self._selected_project_idx = min(max_idx, self._selected_project_idx + 1)
            self.refresh()
            event.stop()
        elif event.key == "enter":
            # Jump to the selected project
            if 0 <= self._selected_project_idx < len(self.server_usage.projects):
                project = self.server_usage.projects[self._selected_project_idx]
                self.post_message(JumpToProject(project))
            event.stop()

    def render(self) -> Text:
        if not self.server_usage:
            return Text.from_markup("[dim]← Select a server to see details[/]")

        lines = []
        s = self.server_usage

        lines.append(f"[bold cyan]{self.app._redact(s.name)}[/]  [dim]({s.server_type})[/]")
        lines.append(f"[bold]Used by {s.usage_count} projects[/]")
        lines.append("")

        # Show server config from first project that has it
        for project in s.projects:
            # ProjectInfo uses 'servers', EnhancedProjectInfo uses 'mcp_servers'
            servers_list = getattr(project, 'mcp_servers', None) or getattr(project, 'servers', [])
            for srv in servers_list:
                if srv.name == s.name:
                    cmd = getattr(srv, 'command', None)
                    if cmd:
                        lines.append(f"[bold]Config:[/]")
                        lines.append(f"  [dim]command:[/] {cmd}")
                        args = getattr(srv, 'args', [])
                        if args:
                            args_str = " ".join(args[:5])
                            if len(args) > 5:
                                args_str += " ..."
                            lines.append(f"  [dim]args:[/] {args_str}")
                        url = getattr(srv, 'url', None)
                        if url:
                            lines.append(f"  [dim]url:[/] {url}")
                        api_key = getattr(srv, 'api_key_preview', None)
                        if api_key:
                            lines.append(f"  [dim]key:[/] {api_key}")
                        lines.append("")
                    break
            else:
                continue
            break

        # Show hint based on focus state
        is_focused = self.has_focus
        if is_focused:
            lines.append("[bold]Projects:[/] [cyan]↑↓ select, Enter to jump[/]")
        else:
            lines.append("[bold]Projects:[/] [dim](Tab to navigate, 'g' to jump)[/]")

        for idx, project in enumerate(s.projects[:12]):
            git_badge = "[green]●[/]" if project.has_git else "[dim]○[/]"
            # Find the server's level in this project
            level = "user"
            servers_list = getattr(project, 'mcp_servers', None) or getattr(project, 'servers', [])
            for srv in servers_list:
                if srv.name == s.name:
                    level = getattr(srv, 'level', 'project')
                    break
            level_color = {"enterprise": "red", "user": "yellow", "project": "green", "local": "cyan"}.get(level, "white")

            # Highlight selected project when focused
            proj_name = self.app._redact(project.name)
            if is_focused and idx == self._selected_project_idx:
                lines.append(f"  [reverse] {git_badge} {proj_name} [{level_color}]{level}[/] [/reverse]")
            else:
                lines.append(f"  {git_badge} {proj_name} [{level_color}]{level}[/]")

        if len(s.projects) > 12:
            lines.append(f"  [dim]... +{len(s.projects) - 12} more[/]")

        return Text.from_markup("\n".join(lines))


class SkillDetailPanel(Static):
    """Detail panel showing selected skill's details.

    Focusable - press Enter to preview full SKILL.md content.
    """

    can_focus = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.skill: Optional[SkillInfo] = None

    def set_skill(self, skill: Optional[SkillInfo]) -> None:
        self.skill = skill
        self.refresh()

    def on_key(self, event) -> None:
        """Handle Enter to preview skill content."""
        if event.key == "enter" and self.skill:
            self.app.push_screen(FilePreviewModal(
                title=f"Skill: {self.skill.name}",
                file_path=self.skill.path
            ))
            event.stop()

    def render(self) -> Text:
        if not self.skill:
            return Text.from_markup("[dim]← Select a skill to see details[/]\n\n[dim]Tab to focus, Enter to preview full content[/]")

        lines = []
        s = self.skill

        level_color = {"personal": "yellow", "project": "green", "enterprise": "red", "plugin": "cyan"}.get(s.level, "white")
        lines.append(f"[bold magenta]{s.name}[/]  [{level_color}]{s.level}[/]")
        lines.append("")

        if s.description:
            lines.append("[bold]Description:[/]")
            lines.append(f"  {s.description}")
            lines.append("")

        if s.allowed_tools:
            lines.append("[bold]Allowed Tools:[/]")
            lines.append(f"  {', '.join(s.allowed_tools)}")
            lines.append("")

        if s.model:
            lines.append(f"[bold]Model:[/] {s.model}")
            lines.append("")

        lines.append(f"[dim]Path: {s.short_path}[/]")
        lines.append("")
        lines.append("[cyan]Press Enter to view full content[/]")

        return Text.from_markup("\n".join(lines))


class CommandDetailPanel(Static):
    """Detail panel showing selected command's details.

    Focusable - press Enter to preview full command content.
    """

    can_focus = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.command: Optional['CommandInfo'] = None

    def set_command(self, command: Optional['CommandInfo']) -> None:
        self.command = command
        self.refresh()

    def on_key(self, event) -> None:
        """Handle Enter to preview command content."""
        if event.key == "enter" and self.command:
            self.app.push_screen(FilePreviewModal(
                title=f"Command: /{self.command.name}",
                file_path=self.command.path
            ))
            event.stop()

    def render(self) -> Text:
        if not self.command:
            return Text.from_markup("[dim]← Select a command to see details[/]\n\n[dim]Tab to focus, Enter to preview full content[/]")

        lines = []
        c = self.command

        level_color = {"user": "yellow", "project": "green", "plugin": "cyan"}.get(c.level, "white")
        lines.append(f"[bold yellow]/{c.name}[/]  [{level_color}]{c.level}[/]")
        lines.append("")

        if c.description:
            lines.append("[bold]Description:[/]")
            lines.append(f"  {c.description}")
            lines.append("")

        if c.args:
            lines.append(f"[bold]Arguments:[/] {c.args}")
            lines.append("")

        if c.allowed_tools:
            lines.append("[bold]Allowed Tools:[/]")
            lines.append(f"  {', '.join(c.allowed_tools)}")
            lines.append("")

        lines.append(f"[dim]Path: {c.short_path}[/]")
        lines.append("")
        lines.append("[cyan]Press Enter to view full content[/]")

        return Text.from_markup("\n".join(lines))


class RuleDetailPanel(Static):
    """Detail panel showing selected rule's details.

    Focusable - press Enter to preview full rule content.
    """

    can_focus = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rule: Optional[RuleInfo] = None

    def set_rule(self, rule: Optional[RuleInfo]) -> None:
        self.rule = rule
        self.refresh()

    def on_key(self, event) -> None:
        """Handle Enter to preview rule content."""
        if event.key == "enter" and self.rule:
            self.app.push_screen(FilePreviewModal(
                title=f"Rule: {self.rule.name}",
                file_path=self.rule.path
            ))
            event.stop()

    def render(self) -> Text:
        if not self.rule:
            return Text.from_markup("[dim]← Select a rule to see details[/]\n\n[dim]Tab to focus, Enter to preview full content[/]")

        lines = []
        r = self.rule

        level_color = {"user": "yellow", "project": "green"}.get(r.level, "white")
        lines.append(f"[bold blue]{r.name}[/]  [{level_color}]{r.level}[/]")

        if r.project_name:
            lines.append(f"[dim]Project: {self.app._redact(r.project_name)}[/]")
        lines.append("")

        if r.paths_glob:
            lines.append(f"[bold]Applies to:[/] {r.paths_glob}")
            lines.append("")

        if r.content_preview:
            lines.append("[bold]Preview:[/]")
            lines.append(f"  {r.content_preview[:150]}...")
            lines.append("")

        lines.append(f"[dim]Path: {r.short_path}[/]")
        lines.append("")
        lines.append("[cyan]Press Enter to view full content[/]")

        return Text.from_markup("\n".join(lines))


class ClaudeMdDetailPanel(Static):
    """Detail panel showing selected CLAUDE.md file's details.

    Focusable - press Enter to preview full CLAUDE.md content.
    """

    can_focus = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.claude_md: Optional[ClaudeMdInfo] = None

    def set_claude_md(self, claude_md: Optional[ClaudeMdInfo]) -> None:
        self.claude_md = claude_md
        self.refresh()

    def on_key(self, event) -> None:
        """Handle Enter to preview CLAUDE.md content."""
        if event.key == "enter" and self.claude_md:
            self.app.push_screen(FilePreviewModal(
                title=f"CLAUDE.md: {self.claude_md.filename}",
                file_path=self.claude_md.path
            ))
            event.stop()

    def render(self) -> Text:
        if not self.claude_md:
            return Text.from_markup("[dim]← Select a file to see details[/]\n\n[dim]Tab to focus, Enter to preview full content[/]")

        lines = []
        c = self.claude_md

        level_color = {"enterprise": "red", "user": "yellow", "project": "green", "local": "cyan", "subdirectory": "magenta"}.get(c.level, "white")
        lines.append(f"[bold yellow]{c.filename}[/]  [{level_color}]{c.level}[/]")

        if c.project_name:
            lines.append(f"[dim]Project: {self.app._redact(c.project_name)}[/]")
        lines.append("")

        if c.has_imports:
            lines.append("[green]● Has @imports[/]")
        else:
            lines.append("[dim]○ No @imports[/]")
        lines.append("")

        if c.paths_glob:
            lines.append(f"[bold]Applies to:[/] {c.paths_glob}")
            lines.append("")

        if c.relative_dir:
            lines.append(f"[bold]Subdirectory:[/] {c.relative_dir}")
            lines.append("")

        if c.content_preview:
            lines.append("[bold]Preview:[/]")
            lines.append(f"  {c.content_preview[:150]}...")
            lines.append("")

        lines.append(f"[dim]Path: {c.short_path}[/]")
        lines.append("")
        lines.append("[cyan]Press Enter to view full content[/]")

        return Text.from_markup("\n".join(lines))


# =============================================================================
# DISCOVERY MODAL
# =============================================================================

class DiscoveryModal(ModalScreen):
    """Modal screen for discovering and moving projects."""

    CSS = """
    DiscoveryModal {
        align: center middle;
    }

    #discovery-container {
        width: 90%;
        height: 85%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #discovery-title {
        text-align: center;
        text-style: bold;
        padding: 1;
        background: $primary-darken-2;
        margin-bottom: 1;
    }

    #discovery-table {
        height: 1fr;
        margin-bottom: 1;
    }

    #discovery-status {
        height: 1;
        padding: 0 1;
        text-align: center;
        margin-bottom: 1;
    }

    #discovery-buttons {
        height: 3;
        align: center middle;
    }

    #discovery-buttons Button {
        margin: 0 1;
        min-width: 16;
    }

    #btn-move {
        background: $success;
    }

    #btn-finder {
        background: $warning;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("a", "select_all", "Select All"),
        Binding("n", "select_none", "Select None"),
        Binding("enter", "confirm_move", "Confirm Move"),
        Binding("o", "open_finder", "Open in Finder"),
        Binding("space", "toggle_selection", "Toggle", show=False),
    ]

    def __init__(
        self,
        discovered_projects: List[str],
        target_dir: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.discovered_projects = discovered_projects
        self.target_dir = target_dir
        self.selected: set = set(range(len(discovered_projects)))  # All selected by default

    def compose(self) -> ComposeResult:
        with Vertical(id="discovery-container"):
            yield Label(
                f"[bold cyan]Found {len(self.discovered_projects)} Projects Outside Current Folder[/]",
                id="discovery-title"
            )

            yield DataTable(id="discovery-table")

            yield Label(
                f"[dim]Target:[/] {self.target_dir}",
                id="discovery-status"
            )

            with Horizontal(id="discovery-buttons"):
                yield Button("✓ Move Selected", id="btn-move", variant="success")
                yield Button("⌘ Open in Finder", id="btn-finder", variant="warning")
                yield Button("Select All [a]", id="btn-all", variant="default")
                yield Button("Select None [n]", id="btn-none", variant="default")
                yield Button("Cancel [Esc]", id="btn-cancel", variant="error")

    def on_mount(self) -> None:
        """Populate the table with project data."""
        table = self.query_one("#discovery-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        table.add_column("✓", key="selected", width=3)
        table.add_column("Project", key="name", width=25)
        table.add_column("Location", key="location", width=35)
        table.add_column("Has Git", key="git", width=8)

        for idx, project in enumerate(self.discovered_projects):
            name = os.path.basename(project)
            short_path = project.replace(os.path.expanduser("~"), "~")
            parent = os.path.dirname(short_path)
            has_git = os.path.isdir(os.path.join(project, ".git"))

            table.add_row(
                Text("●", style="green bold"),
                Text(name, style="cyan bold"),
                Text(parent, style="dim"),
                Text("●", style="green") if has_git else Text("○", style="dim"),
                key=str(idx)
            )

        self._update_status()

    def _update_status(self) -> None:
        """Update the status label with selection count."""
        status = self.query_one("#discovery-status", Label)
        count = len(self.selected)
        total = len(self.discovered_projects)
        status.update(
            f"[bold]{count}[/] of [bold]{total}[/] selected  •  "
            f"[dim]Target:[/] {self.target_dir}"
        )

    def _update_row_selection(self, idx: int) -> None:
        """Update visual selection for a row."""
        table = self.query_one("#discovery-table", DataTable)
        is_selected = idx in self.selected
        # Update the checkmark column
        table.update_cell(
            str(idx),
            "selected",
            Text("●", style="green bold") if is_selected else Text("○", style="dim")
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle selection when row is clicked/selected."""
        if event.row_key:
            idx = int(event.row_key.value)
            if idx in self.selected:
                self.selected.discard(idx)
            else:
                self.selected.add(idx)
            self._update_row_selection(idx)
            self._update_status()

    def action_toggle_selection(self) -> None:
        """Toggle selection for current row with space."""
        table = self.query_one("#discovery-table", DataTable)
        if table.cursor_row is not None:
            idx = table.cursor_row
            if idx in self.selected:
                self.selected.discard(idx)
            else:
                self.selected.add(idx)
            self._update_row_selection(idx)
            self._update_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-all":
            self.action_select_all()
        elif event.button.id == "btn-none":
            self.action_select_none()
        elif event.button.id == "btn-move":
            self.action_confirm_move()
        elif event.button.id == "btn-finder":
            self.action_open_finder()

    def action_cancel(self) -> None:
        """Cancel and close modal."""
        self.dismiss(None)

    def action_select_all(self) -> None:
        """Select all projects."""
        self.selected = set(range(len(self.discovered_projects)))
        for idx in range(len(self.discovered_projects)):
            self._update_row_selection(idx)
        self._update_status()
        self.app.notify(f"Selected all {len(self.discovered_projects)} projects")

    def action_select_none(self) -> None:
        """Deselect all projects."""
        self.selected = set()
        for idx in range(len(self.discovered_projects)):
            self._update_row_selection(idx)
        self._update_status()
        self.app.notify("Cleared selection")

    def action_open_finder(self) -> None:
        """Open selected project in Finder."""
        table = self.query_one("#discovery-table", DataTable)
        if table.cursor_row is not None:
            idx = table.cursor_row
            project_path = self.discovered_projects[idx]
            import subprocess
            subprocess.run(["open", project_path])
            self.app.notify(f"Opened {os.path.basename(project_path)} in Finder")

    def action_confirm_move(self) -> None:
        """Show confirmation before moving."""
        if not self.selected:
            self.app.notify("No projects selected", title="Nothing to move", severity="warning")
            return

        count = len(self.selected)
        names = [os.path.basename(self.discovered_projects[i]) for i in sorted(self.selected)]

        # Show confirmation dialog
        if count <= 3:
            project_list = ", ".join(names)
        else:
            project_list = f"{names[0]}, {names[1]}, and {count - 2} more"

        # Push confirmation screen
        self.app.push_screen(
            ConfirmMoveModal(
                count=count,
                project_names=names,
                target_dir=self.target_dir
            ),
            self._handle_confirmation
        )

    def _handle_confirmation(self, confirmed: bool) -> None:
        """Handle confirmation result."""
        if confirmed:
            to_move = [self.discovered_projects[idx] for idx in sorted(self.selected)]
            self.dismiss(to_move)


class ConfirmMoveModal(ModalScreen):
    """Confirmation dialog before moving projects."""

    CSS = """
    ConfirmMoveModal {
        align: center middle;
    }

    #confirm-container {
        width: 60;
        height: auto;
        border: thick $warning;
        background: $surface;
        padding: 2;
    }

    #confirm-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #confirm-details {
        margin-bottom: 1;
        padding: 1;
        background: $surface-darken-1;
    }

    #confirm-buttons {
        height: 3;
        align: center middle;
    }

    #confirm-buttons Button {
        margin: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
    ]

    def __init__(self, count: int, project_names: List[str], target_dir: str, **kwargs):
        super().__init__(**kwargs)
        self.count = count
        self.project_names = project_names
        self.target_dir = target_dir

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Label(
                f"[bold yellow]⚠ Confirm Move[/]",
                id="confirm-title"
            )

            # Build project list
            if self.count <= 5:
                project_list = "\n".join(f"  • {name}" for name in self.project_names)
            else:
                shown = self.project_names[:4]
                project_list = "\n".join(f"  • {name}" for name in shown)
                project_list += f"\n  [dim]... and {self.count - 4} more[/]"

            yield Label(
                f"Move [bold]{self.count}[/] project(s):\n\n"
                f"{project_list}\n\n"
                f"To: [cyan]{self.target_dir}[/]",
                id="confirm-details"
            )

            with Horizontal(id="confirm-buttons"):
                yield Button("Yes, Move [y]", id="btn-yes", variant="success")
                yield Button("No, Cancel [n]", id="btn-no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class FilePreviewModal(ModalScreen):
    """Modal screen for previewing file content (skills, commands, rules, CLAUDE.md)."""

    CSS = """
    FilePreviewModal {
        align: center middle;
    }

    #preview-container {
        width: 90%;
        height: 90%;
        border: thick $primary;
        background: $surface;
    }

    #preview-header {
        height: 3;
        padding: 1 2;
        background: $primary-darken-2;
    }

    #preview-title {
        text-style: bold;
    }

    #preview-scroll {
        height: 1fr;
        padding: 1 2;
    }

    #preview-content {
        width: 100%;
    }

    #preview-footer {
        height: 2;
        padding: 0 2;
        background: $surface-darken-1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
    ]

    def __init__(self, title: str, file_path: str, **kwargs):
        super().__init__(**kwargs)
        self.title_text = title
        self.file_path = file_path

    def compose(self) -> ComposeResult:
        # Read file content
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            content = f"[red]Error reading file:[/]\n{e}"

        with Vertical(id="preview-container"):
            with Horizontal(id="preview-header"):
                yield Label(f"[bold cyan]{self.title_text}[/]", id="preview-title")
            with ScrollableContainer(id="preview-scroll"):
                yield Static(content, id="preview-content")
            yield Label("[dim]↑↓ Scroll  •  Esc/q Close[/]", id="preview-footer")

    def action_close(self) -> None:
        self.dismiss()


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class MCPManagerApp(App):
    """MCP Server Manager TUI Application - Comprehensive Edition."""

    CSS = """
    HeaderWidget {
        height: auto;
        text-align: center;
        padding: 0 1;
    }

    #stats-bar {
        height: 1;
        padding: 0 2;
        background: $surface;
        margin-bottom: 1;
    }

    #main-content {
        height: 1fr;
    }

    .tab-container {
        width: 100%;
        height: 1fr;
    }

    .list-container {
        width: 55%;
        height: 1fr;
    }

    .detail-container {
        width: 45%;
        height: 1fr;
        border-left: solid $primary;
        padding: 1 2;
        overflow-y: auto;
    }

    /* Visual feedback when detail panel is focused */
    ProjectDetailPanel:focus,
    ServerDetailPanel:focus {
        background: $surface-darken-1;
        border: solid $accent;
    }

    DataTable {
        height: 1fr;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        height: 1fr;
        padding: 0;
    }

    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "discover", "Discover projects"),
        Binding("o", "open_project", "Open in Finder"),
        Binding("question_mark", "show_help", "Help"),
        Binding("tab", "focus_next", "Next", show=False),
        Binding("shift+tab", "focus_previous", "Prev", show=False),
        # Number keys for quick tab switching
        Binding("1", "switch_tab('tab-projects')", "Projects", show=False),
        Binding("2", "switch_tab('tab-servers')", "MCP", show=False),
        Binding("3", "switch_tab('tab-skills')", "Skills", show=False),
        Binding("4", "switch_tab('tab-commands')", "Commands", show=False),
        Binding("5", "switch_tab('tab-rules')", "Rules", show=False),
        Binding("6", "switch_tab('tab-claudemd')", "CLAUDE.md", show=False),
        Binding("p", "toggle_private", "Private mode", show=False),
    ]

    def __init__(self, directory: str, **kwargs):
        super().__init__(**kwargs)
        self.directory = directory
        self.config = load_config()
        self.scanner = ComprehensiveScanner()

        # Privacy mode (redacts project names for screenshots)
        self._private_mode = False

        # Data
        self.projects: List[EnhancedProjectInfo] = []
        self.server_usages: List[ServerUsage] = []
        self.skill_usages: List[SkillUsage] = []
        self.rule_usages: List[RuleUsage] = []
        self.all_claude_mds: List[ClaudeMdInfo] = []

        # User-level items (global, not duplicated per project)
        self.user_skills: List[SkillInfo] = []
        self.user_commands: List[CommandInfo] = []
        self.user_rules: List[RuleInfo] = []

        # Scan data BEFORE compose
        self._initial_scan()

    def _initial_scan(self) -> None:
        """Perform comprehensive scan."""
        settings = self.config.get_directory_settings(self.directory)
        self.projects = self.scanner.scan_directory(
            self.directory,
            max_depth=settings.depth,
            mode=settings.mode
        )

        # Get user-level items (not duplicated per project)
        self.user_skills = self.scanner.get_user_skills()
        self.user_commands = self.scanner.get_user_commands()
        self.user_rules = self.scanner.get_user_rules()

        # Compute aggregated statistics
        # Server usages (need to convert to old format for compatibility)
        old_projects = []
        for p in self.projects:
            old_p = ProjectInfo(
                name=p.name,
                path=p.path,
                has_git=p.has_git,
                has_mcp_config=p.has_mcp_config,
                config_source=p.config_source,
                servers=p.servers
            )
            old_projects.append(old_p)
        self.server_usages = compute_server_usages(old_projects)

        # Skill and rule usages
        self.skill_usages = compute_skill_usages(self.projects)
        self.rule_usages = compute_rule_usages(self.projects)

        # Collect all unique CLAUDE.md files
        seen_paths = set()
        self.all_claude_mds = []
        for p in self.projects:
            for claude_md in p.claude_mds:
                if claude_md.path not in seen_paths:
                    seen_paths.add(claude_md.path)
                    self.all_claude_mds.append(claude_md)

    def _redact(self, text: str) -> str:
        """Redact text for privacy mode. Keeps first 2 and last 1 chars, replaces middle with ***."""
        if not self._private_mode or not text:
            return text
        if len(text) <= 4:
            return text[0] + "**" + text[-1] if len(text) > 1 else text
        return text[:2] + "***" + text[-1]

    def _redact_path(self, path: str) -> str:
        """Redact a file path, keeping directory structure but redacting folder/file names."""
        if not self._private_mode or not path:
            return path
        parts = path.split(os.sep)
        # Keep home dir indicator, redact rest
        redacted_parts = []
        for i, part in enumerate(parts):
            if part in ('', '~', 'Users', 'home') or part.startswith('.'):
                redacted_parts.append(part)
            elif i < 3:  # Keep first few path segments
                redacted_parts.append(part)
            else:
                redacted_parts.append(self._redact(part))
        return os.sep.join(redacted_parts)

    def compose(self) -> ComposeResult:
        yield HeaderWidget(id="header")
        yield StatsBar(id="stats-bar")

        with TabbedContent(id="main-content"):
            # Projects Tab
            with TabPane("Projects", id="tab-projects"):
                with Horizontal(classes="tab-container"):
                    with Vertical(classes="list-container"):
                        yield DataTable(id="projects-table")
                    with NonFocusableScroll(classes="detail-container"):
                        yield ProjectDetailPanel(id="project-detail")

            # MCP Servers Tab
            with TabPane("MCP", id="tab-servers"):
                with Horizontal(classes="tab-container"):
                    with Vertical(classes="list-container"):
                        yield DataTable(id="servers-table")
                    with NonFocusableScroll(classes="detail-container"):
                        yield ServerDetailPanel(id="server-detail")

            # Skills Tab
            with TabPane("Skills", id="tab-skills"):
                with Horizontal(classes="tab-container"):
                    with Vertical(classes="list-container"):
                        yield DataTable(id="skills-table")
                    with NonFocusableScroll(classes="detail-container"):
                        yield SkillDetailPanel(id="skill-detail")

            # Commands Tab
            with TabPane("Commands", id="tab-commands"):
                with Horizontal(classes="tab-container"):
                    with Vertical(classes="list-container"):
                        yield DataTable(id="commands-table")
                    with NonFocusableScroll(classes="detail-container"):
                        yield CommandDetailPanel(id="command-detail")

            # Rules Tab
            with TabPane("Rules", id="tab-rules"):
                with Horizontal(classes="tab-container"):
                    with Vertical(classes="list-container"):
                        yield DataTable(id="rules-table")
                    with NonFocusableScroll(classes="detail-container"):
                        yield RuleDetailPanel(id="rule-detail")

            # CLAUDE.md Tab
            with TabPane("CLAUDE.md", id="tab-claudemd"):
                with Horizontal(classes="tab-container"):
                    with Vertical(classes="list-container"):
                        yield DataTable(id="claudemd-table")
                    with NonFocusableScroll(classes="detail-container"):
                        yield ClaudeMdDetailPanel(id="claudemd-detail")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app after mounting."""
        self._populate_all_tables()

        # Update stats bar with user-level counts
        stats_bar = self.query_one("#stats-bar", StatsBar)
        stats_bar.update_stats(
            self.projects,
            user_skills=len(self.user_skills),
            user_commands=len(self.user_commands),
            user_rules=len(self.user_rules)
        )

    def _populate_all_tables(self) -> None:
        """Populate all data tables."""
        self._populate_projects_table()
        self._populate_servers_table()
        self._populate_skills_table()
        self._populate_commands_table()
        self._populate_rules_table()
        self._populate_claudemd_table()

    def _populate_projects_table(self) -> None:
        """Populate the projects table."""
        table = self.query_one("#projects-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        if not table.columns:
            table.add_column("Project", key="name")
            table.add_column("Git", key="git")
            table.add_column("MCP", key="mcp")
            table.add_column("Skills", key="skills")
            table.add_column("Rules", key="rules")
            table.add_column("Docs", key="docs")
            table.add_column("Hooks", key="hooks")
        else:
            table.clear()

        for project in self.projects:
            git_icon = Text("●", style="green") if project.has_git else Text("○", style="dim")
            mcp_text = Text(str(project.mcp_count), style="green") if project.mcp_count > 0 else Text("-", style="dim")
            skills_text = Text(str(project.skill_count), style="magenta") if project.skill_count > 0 else Text("-", style="dim")
            rules_text = Text(str(project.rule_count), style="blue") if project.rule_count > 0 else Text("-", style="dim")
            docs_text = Text(str(project.claude_md_count), style="yellow") if project.claude_md_count > 0 else Text("-", style="dim")
            # Pre-commit hooks count
            hook_count = project.pre_commit.hook_count if project.pre_commit else 0
            hooks_text = Text(str(hook_count), style="cyan") if hook_count > 0 else Text("-", style="dim")

            table.add_row(
                self._redact(project.name),
                git_icon,
                mcp_text,
                skills_text,
                rules_text,
                docs_text,
                hooks_text,
                key=project.path,
            )

    def _populate_servers_table(self) -> None:
        """Populate the servers table."""
        table = self.query_one("#servers-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        if not table.columns:
            table.add_column("Server", key="name")
            table.add_column("Type", key="type")
            table.add_column("Usage", key="usage")
            table.add_column("Bar", key="bar")
            table.add_column("Projects", key="projects")
        else:
            table.clear()

        if not self.server_usages:
            return

        max_usage = max(s.usage_count for s in self.server_usages)

        for server in self.server_usages:
            bar_width = 12
            filled = int((server.usage_count / max_usage) * bar_width) if max_usage > 0 else 0
            bar = Text("█" * filled, style="green") + Text("░" * (bar_width - filled), style="dim")

            projects_preview = ", ".join(self._redact(p.name) for p in server.projects[:2])
            if len(server.projects) > 2:
                projects_preview += f" +{len(server.projects) - 2}"

            table.add_row(
                self._redact(server.name),
                server.server_type,
                str(server.usage_count),
                bar,
                Text(projects_preview, style="dim"),
                key=server.name,
            )

    def _populate_skills_table(self) -> None:
        """Populate the skills table with user-level and project-level skills."""
        table = self.query_one("#skills-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        if not table.columns:
            table.add_column("Skill", key="name")
            table.add_column("Level", key="level")
            table.add_column("Description", key="desc")
        else:
            table.clear()

        # Collect all unique skills (user-level + project-level)
        seen = set()
        all_skills = []

        # First add user skills (personal level)
        for skill in self.user_skills:
            key = f"{skill.level}:{skill.name}"
            if key not in seen:
                seen.add(key)
                all_skills.append(skill)

        # Then add project-level skills
        for p in self.projects:
            for skill in p.skills:
                key = f"{skill.level}:{skill.name}"
                if key not in seen:
                    seen.add(key)
                    all_skills.append(skill)

        for skill in all_skills:
            level_color = {"personal": "yellow", "project": "green", "enterprise": "red", "plugin": "cyan"}.get(skill.level, "white")
            desc_preview = skill.description[:35] + "..." if len(skill.description) > 35 else skill.description

            table.add_row(
                Text(skill.name, style="magenta"),
                Text(skill.level, style=level_color),
                Text(desc_preview, style="dim"),
                key=f"{skill.level}:{skill.name}",
            )

    def _populate_commands_table(self) -> None:
        """Populate the commands table with user-level and project-level commands."""
        table = self.query_one("#commands-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        if not table.columns:
            table.add_column("Command", key="name")
            table.add_column("Level", key="level")
            table.add_column("Description", key="desc")
        else:
            table.clear()

        # Collect all unique commands (user-level + project-level)
        seen = set()
        all_commands = []

        # First add user commands
        for cmd in self.user_commands:
            key = f"{cmd.level}:{cmd.name}"
            if key not in seen:
                seen.add(key)
                all_commands.append(cmd)

        # Then add project-level commands
        for p in self.projects:
            for cmd in p.commands:
                key = f"{cmd.level}:{cmd.name}"
                if key not in seen:
                    seen.add(key)
                    all_commands.append(cmd)

        for cmd in all_commands:
            level_color = {"user": "yellow", "project": "green", "plugin": "cyan"}.get(cmd.level, "white")
            desc_preview = cmd.description[:35] + "..." if len(cmd.description) > 35 else cmd.description

            table.add_row(
                Text(f"/{cmd.name}", style="yellow"),
                Text(cmd.level, style=level_color),
                Text(desc_preview, style="dim"),
                key=f"{cmd.level}:{cmd.name}",
            )

    def _populate_rules_table(self) -> None:
        """Populate the rules table with user-level and project-level rules."""
        table = self.query_one("#rules-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        if not table.columns:
            table.add_column("Rule", key="name")
            table.add_column("Project", key="project")
            table.add_column("Level", key="level")
            table.add_column("Scope", key="scope")
        else:
            table.clear()

        # Collect all unique rules (user-level + project-level)
        seen = set()
        all_rules = []

        # First add user rules
        for rule in self.user_rules:
            key = f"{rule.level}:{rule.name}"
            if key not in seen:
                seen.add(key)
                all_rules.append(rule)

        # Then add project-level rules
        for p in self.projects:
            for rule in p.rules:
                key = f"{rule.level}:{rule.name}"
                if key not in seen:
                    seen.add(key)
                    all_rules.append(rule)

        for rule in all_rules:
            level_color = {"user": "yellow", "project": "green"}.get(rule.level, "white")
            scope = rule.paths_glob if rule.paths_glob else "all"
            project_name = self._redact(rule.project_name) if rule.project_name else "~"
            if rule.level != "project":
                project_name = "~"

            table.add_row(
                Text(rule.name, style="blue"),
                Text(project_name, style="dim"),
                Text(rule.level, style=level_color),
                Text(scope, style="cyan"),
                key=f"{rule.level}:{rule.name}",
            )

    def _populate_claudemd_table(self) -> None:
        """Populate the CLAUDE.md table."""
        table = self.query_one("#claudemd-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        if not table.columns:
            table.add_column("File", key="file")
            table.add_column("Project", key="project")
            table.add_column("Level", key="level")
            table.add_column("@", key="imports")
        else:
            table.clear()

        for claude_md in self.all_claude_mds:
            level_color = {"enterprise": "red", "user": "yellow", "project": "green", "local": "cyan", "subdirectory": "magenta"}.get(claude_md.level, "white")
            imports_icon = Text("●", style="green") if claude_md.has_imports else Text("○", style="dim")
            project_name = self._redact(claude_md.project_name) if claude_md.project_name else "~"

            table.add_row(
                Text(claude_md.filename, style="yellow"),
                Text(project_name, style="dim"),
                Text(claude_md.level, style=level_color),
                imports_icon,
                key=claude_md.path,
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight (cursor movement) in any table - shows details as you navigate."""
        if not event.row_key:
            return

        table_id = event.data_table.id
        key = event.row_key.value

        if table_id == "projects-table":
            for project in self.projects:
                if project.path == key:
                    detail = self.query_one("#project-detail", ProjectDetailPanel)
                    detail.set_project(project)
                    break

        elif table_id == "servers-table":
            for server in self.server_usages:
                if server.name == key:
                    detail = self.query_one("#server-detail", ServerDetailPanel)
                    detail.set_server(server)
                    break

        elif table_id == "skills-table":
            # key format: "level:name"
            for p in self.projects:
                for skill in p.skills:
                    if f"{skill.level}:{skill.name}" == key:
                        detail = self.query_one("#skill-detail", SkillDetailPanel)
                        detail.set_skill(skill)
                        return
            # Check user skills too
            for skill in self.user_skills:
                if f"{skill.level}:{skill.name}" == key:
                    detail = self.query_one("#skill-detail", SkillDetailPanel)
                    detail.set_skill(skill)
                    return

        elif table_id == "commands-table":
            # key format: "level:name"
            for p in self.projects:
                for cmd in p.commands:
                    if f"{cmd.level}:{cmd.name}" == key:
                        detail = self.query_one("#command-detail", CommandDetailPanel)
                        detail.set_command(cmd)
                        return
            # Check user commands too
            for cmd in self.user_commands:
                if f"{cmd.level}:{cmd.name}" == key:
                    detail = self.query_one("#command-detail", CommandDetailPanel)
                    detail.set_command(cmd)
                    return

        elif table_id == "rules-table":
            for p in self.projects:
                for rule in p.rules:
                    if f"{rule.level}:{rule.name}" == key:
                        detail = self.query_one("#rule-detail", RuleDetailPanel)
                        detail.set_rule(rule)
                        return

        elif table_id == "claudemd-table":
            for claude_md in self.all_claude_mds:
                if claude_md.path == key:
                    detail = self.query_one("#claudemd-detail", ClaudeMdDetailPanel)
                    detail.set_claude_md(claude_md)
                    return

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key press on tables - opens file preview for previewable content."""
        if not event.row_key:
            return

        table_id = event.data_table.id
        key = event.row_key.value

        if table_id == "skills-table":
            # key format: "level:name"
            for p in self.projects:
                for skill in p.skills:
                    if f"{skill.level}:{skill.name}" == key:
                        self.push_screen(FilePreviewModal(
                            title=f"Skill: {skill.name}",
                            file_path=skill.path
                        ))
                        return
            # Check user skills too
            for skill in self.user_skills:
                if f"{skill.level}:{skill.name}" == key:
                    self.push_screen(FilePreviewModal(
                        title=f"Skill: {skill.name}",
                        file_path=skill.path
                    ))
                    return

        elif table_id == "commands-table":
            # key format: "level:name"
            for p in self.projects:
                for cmd in p.commands:
                    if f"{cmd.level}:{cmd.name}" == key:
                        self.push_screen(FilePreviewModal(
                            title=f"Command: /{cmd.name}",
                            file_path=cmd.path
                        ))
                        return
            # Check user commands too
            for cmd in self.user_commands:
                if f"{cmd.level}:{cmd.name}" == key:
                    self.push_screen(FilePreviewModal(
                        title=f"Command: /{cmd.name}",
                        file_path=cmd.path
                    ))
                    return

        elif table_id == "rules-table":
            for p in self.projects:
                for rule in p.rules:
                    if f"{rule.level}:{rule.name}" == key:
                        self.push_screen(FilePreviewModal(
                            title=f"Rule: {rule.name}",
                            file_path=rule.path
                        ))
                        return
            # Check user rules too
            for rule in self.user_rules:
                if f"{rule.level}:{rule.name}" == key:
                    self.push_screen(FilePreviewModal(
                        title=f"Rule: {rule.name}",
                        file_path=rule.path
                    ))
                    return

        elif table_id == "claudemd-table":
            for claude_md in self.all_claude_mds:
                if claude_md.path == key:
                    filename = os.path.basename(claude_md.path)
                    self.push_screen(FilePreviewModal(
                        title=f"CLAUDE.md: {filename}",
                        file_path=claude_md.path
                    ))
                    return

    def action_refresh(self) -> None:
        """Refresh the scan."""
        self._initial_scan()
        self._populate_all_tables()

        stats_bar = self.query_one("#stats-bar", StatsBar)
        stats_bar.update_stats(
            self.projects,
            user_skills=len(self.user_skills),
            user_commands=len(self.user_commands),
            user_rules=len(self.user_rules)
        )

        self.notify(f"Scanned {len(self.projects)} projects", title="Refresh Complete")

    def action_toggle_private(self) -> None:
        """Toggle private mode (redacts project names for screenshots)."""
        self._private_mode = not self._private_mode
        # Refresh all tables to show redacted/unredacted names
        self._populate_all_tables()
        # Update header to show mode indicator
        header = self.query_one("#header", HeaderWidget)
        header.set_private_mode(self._private_mode)
        mode = "ON 🔒" if self._private_mode else "OFF"
        self.notify(f"Private mode: {mode}", title="Privacy")

    def _navigate_to_project(self, project) -> None:
        """Navigate to a specific project in the Projects tab.

        Args:
            project: Can be ProjectInfo or EnhancedProjectInfo - we look up
                     the full EnhancedProjectInfo from self.projects by path.
        """
        tabbed = self.query_one("#main-content", TabbedContent)
        tabbed.active = "tab-projects"

        # Find and highlight the project in the table
        projects_table = self.query_one("#projects-table", DataTable)

        # Find row index by iterating through our data
        for idx, p in enumerate(self.projects):
            if p.path == project.path:
                projects_table.move_cursor(row=idx)
                # Update detail panel with full EnhancedProjectInfo (not the passed ProjectInfo)
                detail = self.query_one("#project-detail", ProjectDetailPanel)
                detail.set_project(p)  # Use 'p' from self.projects, not 'project' param
                projects_table.focus()
                self.notify(f"Jumped to {p.name}")
                break

    def _navigate_to_server(self, server_name: str) -> None:
        """Navigate to a specific server in the Servers tab."""
        tabbed = self.query_one("#main-content", TabbedContent)
        tabbed.active = "tab-servers"

        # Find and highlight the server in the table
        servers_table = self.query_one("#servers-table", DataTable)

        # Find row index by iterating through our data
        for idx, server in enumerate(self.server_usages):
            if server.name == server_name:
                servers_table.move_cursor(row=idx)
                # Update detail panel
                detail = self.query_one("#server-detail", ServerDetailPanel)
                detail.set_server(server)
                servers_table.focus()
                self.notify(f"Jumped to {server_name}")
                break

    def on_jump_to_project(self, message: JumpToProject) -> None:
        """Handle request to jump to a project (from detail panel)."""
        self._navigate_to_project(message.project)

    def on_jump_to_server(self, message: JumpToServer) -> None:
        """Handle request to jump to a server (from detail panel)."""
        self._navigate_to_server(message.server_name)

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to a specific tab by ID."""
        tabbed = self.query_one("#main-content", TabbedContent)
        tabbed.active = tab_id

    def action_open_project(self) -> None:
        """Open the selected item in Finder (macOS).

        For projects: opens the project folder
        For files (skills, commands, rules, CLAUDE.md): reveals the file in Finder
        """
        import subprocess
        tabbed = self.query_one("#main-content", TabbedContent)
        current_tab = tabbed.active

        # Get path and whether it's a file (to reveal) or directory (to open)
        path = None
        reveal_file = False  # If True, use 'open -R' to reveal file in Finder

        if current_tab == "tab-projects":
            table = self.query_one("#projects-table", DataTable)
            cursor_row = table.cursor_row
            if cursor_row is not None and 0 <= cursor_row < len(self.projects):
                path = self.projects[cursor_row].path
        elif current_tab == "tab-servers":
            # For servers, open the project of the first usage
            detail = self.query_one("#server-detail", ServerDetailPanel)
            if detail.server_usage and detail.server_usage.projects:
                path = detail.server_usage.projects[0].path
        elif current_tab == "tab-skills":
            detail = self.query_one("#skill-detail", SkillDetailPanel)
            if detail.skill:
                path = detail.skill.path
                reveal_file = True
        elif current_tab == "tab-commands":
            detail = self.query_one("#command-detail", CommandDetailPanel)
            if detail.command:
                path = detail.command.path
                reveal_file = True
        elif current_tab == "tab-rules":
            detail = self.query_one("#rule-detail", RuleDetailPanel)
            if detail.rule:
                path = detail.rule.path
                reveal_file = True
        elif current_tab == "tab-claudemd":
            detail = self.query_one("#claudemd-detail", ClaudeMdDetailPanel)
            if detail.claude_md:
                path = detail.claude_md.path
                reveal_file = True

        if path and os.path.exists(path):
            if reveal_file:
                # Reveal file in Finder (selects it)
                subprocess.run(["open", "-R", path])
                self.notify(f"Revealed: {os.path.basename(path)}")
            else:
                # Open directory
                subprocess.run(["open", path])
                self.notify(f"Opened: {os.path.basename(path)}")
        else:
            self.notify("No item selected", severity="warning")

    def action_discover(self) -> None:
        """Discover Claude Code projects across the system."""
        self.notify("Scanning for Claude Code projects...", title="Discovery")

        # Run discovery
        discovered = discover_claude_projects(max_depth=3)

        # Filter out projects already in the current directory
        current_projects = {p.path for p in self.projects}
        new_projects = [p for p in discovered if p not in current_projects]

        # Check which projects are outside the current scanning directory
        abs_directory = os.path.abspath(self.directory)
        outside_current = [
            p for p in new_projects
            if not p.startswith(abs_directory)
        ]

        # Save discovered projects to config for future reference
        self.config.discovered_projects = discovered
        from datetime import datetime
        self.config.last_discovery_time = datetime.now().isoformat()
        save_config(self.config)

        if outside_current:
            # Show modal with projects that can be moved
            def handle_move_result(to_move: Optional[List[str]]) -> None:
                if to_move is None:
                    self.notify("Discovery cancelled", title="Cancelled")
                    return

                if not to_move:
                    self.notify("No projects selected", title="Nothing to move")
                    return

                # Move the selected projects
                moved = 0
                failed = 0
                for project_path in to_move:
                    result = move_project(project_path, abs_directory)
                    if result.success:
                        moved += 1
                    else:
                        failed += 1
                        self.notify(
                            f"Failed to move {os.path.basename(project_path)}: {result.error}",
                            title="Move Error",
                            severity="error"
                        )

                if moved > 0:
                    self.notify(
                        f"Moved {moved} project(s) to {self.directory}",
                        title="Move Complete"
                    )
                    # Refresh to show new projects
                    self.action_refresh()

            self.push_screen(
                DiscoveryModal(outside_current, abs_directory),
                handle_move_result
            )
        else:
            self.notify(
                f"All {len(discovered)} Claude projects are within current folder",
                title="Discovery Complete"
            )

    def action_show_help(self) -> None:
        """Show help information about Claude Code configuration concepts."""
        help_text = """[bold cyan]Claude Code Configuration Guide[/]

[bold white]MCP Servers[/] — External tools/services Claude can use
  • Located: .mcp.json (project), ~/.claude.json (user)
  • Examples: Supabase, GitHub, filesystem access
  • Hierarchy: Enterprise > Local > Project > User

[bold white]Skills[/] — Specialized knowledge for Claude
  • Structure: skills/skill-name/SKILL.md (folder-based)
  • [yellow]Cannot nest[/] — must be directly in skills/
  • Triggered automatically by description matching

[bold white]Commands[/] — Slash commands you invoke manually
  • Structure: commands/*.md (flat files)
  • [yellow]Cannot nest[/] — must be directly in commands/
  • Invoked with /command-name

[bold white]Rules[/] — Always-on instructions for Claude
  • Structure: rules/**/*.md
  • [green]Can nest[/] in subdirectories
  • Applied based on paths: glob in frontmatter

[bold white]CLAUDE.md[/] — Project instructions and context
  • Locations: ./CLAUDE.md, .claude/CLAUDE.md, CLAUDE.local.md
  • [green]Can nest[/] — subdirectory CLAUDE.md loaded contextually
  • Supports @imports for including other files

[dim]Press any key to close[/]"""

        self.notify(help_text, title="Help", timeout=30)


def run_tui(directory: str) -> None:
    """Run the TUI application."""
    app = MCPManagerApp(directory)
    app.run()


def main() -> None:
    """Entry point for CLI command (ccmanager).

    Usage:
        ccmanager ~/Projects     # Scan a projects folder
        ccmanager               # Scan current directory
        ccmanager --debug       # Show what paths are being scanned
    """
    import sys
    from pathlib import Path

    args = sys.argv[1:]

    # Handle --debug flag
    if '--debug' in args:
        args.remove('--debug')
        directory = args[0] if args else "."

        print("=== Claude Code Manager Debug ===\n")
        print("Checking paths:\n")

        # User paths
        home = Path.home()
        paths_to_check = [
            (home / '.claude.json', 'User MCP servers'),
            (home / '.claude' / 'skills', 'User skills'),
            (home / '.claude' / 'plugins' / 'marketplaces', 'Plugin skills'),
            (home / '.claude' / 'commands', 'User commands'),
            (home / '.claude' / 'rules', 'User rules'),
            (home / '.claude' / 'CLAUDE.md', 'User CLAUDE.md'),
        ]

        for path, desc in paths_to_check:
            exists = "✓" if path.exists() else "✗"
            print(f"  {exists} {path} ({desc})")

        print(f"\nScanning directory: {os.path.abspath(directory)}\n")

        # Check if ~/.claude.json has mcpServers
        claude_json = home / '.claude.json'
        if claude_json.exists():
            import json
            try:
                with open(claude_json) as f:
                    data = json.load(f)
                servers = data.get('mcpServers', {})
                print(f"Found {len(servers)} MCP servers in ~/.claude.json:")
                for name in servers:
                    print(f"    - {name}")
            except Exception as e:
                print(f"Error reading ~/.claude.json: {e}")

        print("\nStarting TUI...\n")
        run_tui(directory)
    else:
        directory = args[0] if args else "."
        run_tui(directory)


if __name__ == "__main__":
    main()
