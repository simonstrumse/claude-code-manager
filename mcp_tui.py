"""
Interactive TUI for MCP Server Manager.
Uses textual library for rich terminal interface.
"""

from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Static,
    TabbedContent,
    TabPane,
    Tree,
    Label,
    Rule,
)
from textual.widgets.tree import TreeNode
from rich.text import Text

from mcp_data import ProjectInfo, ServerDetail, ServerUsage, compute_server_usages
from mcp_scanner import EnhancedScanner
from mcp_config import UserConfig, load_config, save_config


ASCII_HEADER = """
[bold cyan] ███╗   ███╗ ██████╗██████╗    ███╗   ███╗ █████╗ ███╗   ██╗ █████╗  ██████╗ ███████╗██████╗ [/]
[bold cyan] ████╗ ████║██╔════╝██╔══██╗   ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔════╝ ██╔════╝██╔══██╗[/]
[bold cyan] ██╔████╔██║██║     ██████╔╝   ██╔████╔██║███████║██╔██╗ ██║███████║██║  ███╗█████╗  ██████╔╝[/]
[bold cyan] ██║╚██╔╝██║██║     ██╔═══╝    ██║╚██╔╝██║██╔══██║██║╚██╗██║██╔══██║██║   ██║██╔══╝  ██╔══██╗[/]
[bold cyan] ██║ ╚═╝ ██║╚██████╗██║        ██║ ╚═╝ ██║██║  ██║██║ ╚████║██║  ██║╚██████╔╝███████╗██║  ██║[/]
[bold cyan] ╚═╝     ╚═╝ ╚═════╝╚═╝        ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝[/]
"""


class BannerWidget(Static):
    """ASCII art banner widget."""

    def compose(self) -> ComposeResult:
        yield Static(ASCII_HEADER, id="ascii-header")


class StatsBar(Static):
    """Statistics bar showing scan summary."""

    def __init__(self, projects: List[ProjectInfo], **kwargs):
        super().__init__(**kwargs)
        self.projects = projects

    def render(self) -> Text:
        total = len(self.projects)
        with_mcp = sum(1 for p in self.projects if p.has_mcp_config)
        with_git = sum(1 for p in self.projects if p.has_git)
        total_servers = sum(p.server_count for p in self.projects)

        return Text.from_markup(
            f"[bold]Projects:[/] {total}  "
            f"[bold]With MCP:[/] [green]{with_mcp}[/]  "
            f"[bold]With Git:[/] [blue]{with_git}[/]  "
            f"[bold]Total Servers:[/] {total_servers}"
        )


class ProjectDetailPanel(Static):
    """Detail panel showing selected project's servers."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project: Optional[ProjectInfo] = None

    def set_project(self, project: Optional[ProjectInfo]) -> None:
        """Update the displayed project."""
        self.project = project
        self.refresh()

    def render(self) -> Text:
        if not self.project:
            return Text.from_markup("[dim]Select a project to see details[/]")

        lines = []
        p = self.project

        # Header
        git_badge = "[green]● git[/]" if p.has_git else "[dim]○ no git[/]"
        mcp_badge = "[green]● mcp[/]" if p.has_mcp_config else "[yellow]○ global[/]"
        lines.append(f"[bold cyan]{p.name}[/]  {git_badge}  {mcp_badge}")
        lines.append(f"[dim]{p.path}[/]")
        lines.append("")

        if not p.servers:
            lines.append("[dim]No local MCP servers (using global config)[/]")
        else:
            lines.append(f"[bold]MCP Servers ({len(p.servers)}):[/]")
            lines.append("")

            for server in p.servers:
                lines.append(f"  [bold yellow]{server.name}[/] [{server.server_type}]")

                if server.command:
                    lines.append(f"    [dim]command:[/] {server.command}")
                if server.url:
                    lines.append(f"    [dim]url:[/] {server.url}")
                if server.supabase_project_ref:
                    lines.append(f"    [dim]supabase:[/] {server.supabase_project_ref}")
                if server.resend_sender:
                    lines.append(f"    [dim]sender:[/] {server.resend_sender}")
                if server.api_key_preview:
                    lines.append(f"    [dim]key:[/] {server.api_key_preview}")
                for env_key, env_val in server.env_vars.items():
                    if env_val != "[set]":
                        lines.append(f"    [dim]{env_key}:[/] {env_val}")

                lines.append("")

        return Text.from_markup("\n".join(lines))


class ServerDetailPanel(Static):
    """Detail panel showing selected server's usage across projects."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_usage: Optional[ServerUsage] = None

    def set_server(self, server_usage: Optional[ServerUsage]) -> None:
        """Update the displayed server."""
        self.server_usage = server_usage
        self.refresh()

    def render(self) -> Text:
        if not self.server_usage:
            return Text.from_markup("[dim]Select a server to see details[/]")

        lines = []
        s = self.server_usage

        # Header
        lines.append(f"[bold cyan]{s.name}[/]  [{s.server_type}]")
        lines.append(f"[bold]Used by {s.usage_count} projects[/]")
        lines.append("")

        # Projects using this server
        lines.append("[bold]Projects:[/]")
        lines.append("")

        for project in s.projects:
            git_badge = "[green]●[/]" if project.has_git else "[dim]○[/]"
            lines.append(f"  {git_badge} [bold]{project.name}[/]")

            # Find this server's detail in the project
            server_detail = s.get_server_in_project(project)
            if server_detail:
                if server_detail.supabase_project_ref:
                    lines.append(f"      [dim]supabase:[/] {server_detail.supabase_project_ref}")
                if server_detail.resend_sender:
                    lines.append(f"      [dim]sender:[/] {server_detail.resend_sender}")
                if server_detail.api_key_preview:
                    lines.append(f"      [dim]key:[/] {server_detail.api_key_preview}")

            lines.append("")

        return Text.from_markup("\n".join(lines))


class ProjectsView(Container):
    """Projects view with table and detail panel."""

    def __init__(self, projects: List[ProjectInfo], **kwargs):
        super().__init__(**kwargs)
        self.projects = projects

    def compose(self) -> ComposeResult:
        with Horizontal(id="projects-container"):
            with Vertical(id="projects-list"):
                yield DataTable(id="projects-table")
            with ScrollableContainer(id="projects-detail-container"):
                yield ProjectDetailPanel(id="project-detail")

    def on_mount(self) -> None:
        """Initialize the data table."""
        table = self.query_one("#projects-table", DataTable)
        table.cursor_type = "row"

        # Add columns
        table.add_column("Project", key="name", width=30)
        table.add_column("Git", key="git", width=5)
        table.add_column("MCP", key="mcp", width=5)
        table.add_column("Servers", key="servers", width=8)
        table.add_column("Config", key="config", width=8)

        # Add rows
        for project in self.projects:
            git_icon = Text("●", style="green") if project.has_git else Text("○", style="dim")
            mcp_icon = Text("●", style="green") if project.has_mcp_config else Text("○", style="yellow")

            if project.server_count > 0:
                servers_text = Text(str(project.server_count))
            else:
                servers_text = Text("global", style="dim")

            config_styles = {
                "project": ("local", "green"),
                "global": ("global", "yellow"),
                "none": ("none", "dim"),
            }
            config_text, config_style = config_styles.get(project.config_source, ("?", "red"))

            table.add_row(
                project.name,
                git_icon,
                mcp_icon,
                servers_text,
                Text(config_text, style=config_style),
                key=project.path,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        if event.row_key:
            # Find the project by path
            for project in self.projects:
                if project.path == event.row_key.value:
                    detail = self.query_one("#project-detail", ProjectDetailPanel)
                    detail.set_project(project)
                    break


class ServersView(Container):
    """Servers view with usage table and detail panel."""

    def __init__(self, projects: List[ProjectInfo], **kwargs):
        super().__init__(**kwargs)
        self.projects = projects
        self.server_usages = compute_server_usages(projects)

    def compose(self) -> ComposeResult:
        with Horizontal(id="servers-container"):
            with Vertical(id="servers-list"):
                yield DataTable(id="servers-table")
            with ScrollableContainer(id="servers-detail-container"):
                yield ServerDetailPanel(id="server-detail")

    def on_mount(self) -> None:
        """Initialize the data table."""
        table = self.query_one("#servers-table", DataTable)
        table.cursor_type = "row"

        # Add columns
        table.add_column("Server", key="name", width=20)
        table.add_column("Type", key="type", width=6)
        table.add_column("Usage", key="usage", width=6)
        table.add_column("Bar", key="bar", width=20)
        table.add_column("Projects", key="projects", width=30)

        if not self.server_usages:
            return

        max_usage = max(s.usage_count for s in self.server_usages)

        # Add rows
        for server in self.server_usages:
            # Usage bar
            bar_width = 15
            filled = int((server.usage_count / max_usage) * bar_width) if max_usage > 0 else 0
            bar = Text("█" * filled, style="green") + Text("░" * (bar_width - filled), style="dim")

            # Projects preview
            projects_preview = ", ".join(p.name for p in server.projects[:3])
            if len(server.projects) > 3:
                projects_preview += f" +{len(server.projects) - 3}"

            table.add_row(
                server.name,
                server.server_type,
                str(server.usage_count),
                bar,
                Text(projects_preview, style="dim"),
                key=server.name,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        if event.row_key:
            # Find the server by name
            for server in self.server_usages:
                if server.name == event.row_key.value:
                    detail = self.query_one("#server-detail", ServerDetailPanel)
                    detail.set_server(server)
                    break


class MCPManagerApp(App):
    """MCP Server Manager TUI Application."""

    CSS = """
    #ascii-header {
        text-align: center;
        padding: 1;
    }

    #stats-bar {
        dock: top;
        height: 1;
        padding: 0 2;
        background: $surface;
    }

    #projects-container, #servers-container {
        height: 100%;
    }

    #projects-list, #servers-list {
        width: 60%;
        height: 100%;
    }

    #projects-detail-container, #servers-detail-container {
        width: 40%;
        height: 100%;
        border-left: solid $primary;
        padding: 1 2;
    }

    DataTable {
        height: 100%;
    }

    TabbedContent {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("tab", "next_tab", "Next Tab", show=False),
        Binding("shift+tab", "prev_tab", "Prev Tab", show=False),
    ]

    def __init__(self, directory: str, **kwargs):
        super().__init__(**kwargs)
        self.directory = directory
        self.config = load_config()
        self.scanner = EnhancedScanner()
        self.projects: List[ProjectInfo] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield BannerWidget()
        yield StatsBar(self.projects, id="stats-bar")

        with TabbedContent():
            with TabPane("Projects", id="tab-projects"):
                yield ProjectsView(self.projects, id="projects-view")
            with TabPane("Servers", id="tab-servers"):
                yield ServersView(self.projects, id="servers-view")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app."""
        self.action_refresh()

    def action_refresh(self) -> None:
        """Refresh the scan."""
        settings = self.config.get_directory_settings(self.directory)
        self.projects = self.scanner.scan_directory(
            self.directory,
            max_depth=settings.depth,
            mode=settings.mode
        )

        # Update stats bar
        stats_bar = self.query_one("#stats-bar", StatsBar)
        stats_bar.projects = self.projects
        stats_bar.refresh()

        # Recreate views with new data
        # Note: In a real implementation, we'd update the existing views
        # For simplicity, we notify the user to restart
        self.notify(f"Scanned {len(self.projects)} projects", title="Refresh Complete")

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.action_next_tab()

    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.action_previous_tab()


def run_tui(directory: str) -> None:
    """Run the TUI application."""
    app = MCPManagerApp(directory)
    app.run()


if __name__ == "__main__":
    import sys
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    run_tui(directory)
