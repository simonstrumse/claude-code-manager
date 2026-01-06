"""
Data models for MCP Server Manager TUI.
Provides dataclasses for representing projects, servers, and usage statistics.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
import re


@dataclass
class ServerDetail:
    """Detailed information about an MCP server configuration."""
    name: str
    server_type: Literal["stdio", "http", "sse"] = "stdio"
    command: Optional[str] = None
    url: Optional[str] = None

    # Extracted identifiers (redacted for display)
    supabase_project_ref: Optional[str] = None
    resend_sender: Optional[str] = None
    api_key_preview: Optional[str] = None

    # Other environment variables (values marked as [set])
    env_vars: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_config(cls, name: str, config: Dict) -> "ServerDetail":
        """Create ServerDetail from raw MCP server config."""
        server_type = config.get("type", "stdio")

        detail = cls(
            name=name,
            server_type=server_type,
            command=config.get("command"),
            url=config.get("url")
        )

        # Extract from args
        args = config.get("args", [])
        detail._extract_from_args(args)

        # Extract from env
        env = config.get("env", {})
        detail._extract_from_env(env)

        return detail

    def _extract_from_args(self, args: List) -> None:
        """Extract identifiable info from command arguments."""
        for i, arg in enumerate(args):
            if not isinstance(arg, str):
                continue

            # Supabase project-ref
            if "--project-ref=" in arg:
                ref = arg.split("=", 1)[1]
                self.supabase_project_ref = _redact_middle(ref)
            elif arg == "--project-ref" and i + 1 < len(args):
                self.supabase_project_ref = _redact_middle(str(args[i + 1]))

            # API keys in args (various patterns)
            if "api-key" in arg.lower() or "API_KEY" in arg:
                if "=" in arg:
                    _, value = arg.split("=", 1)
                    self.api_key_preview = _redact_key(value)
            elif arg in ("--api-key", "-k") and i + 1 < len(args):
                self.api_key_preview = _redact_key(str(args[i + 1]))

            # Access tokens in args
            if "--access-token=" in arg:
                _, value = arg.split("=", 1)
                self.api_key_preview = _redact_key(value)
            elif arg == "--access-token" and i + 1 < len(args):
                self.api_key_preview = _redact_key(str(args[i + 1]))

    def _extract_from_env(self, env: Dict[str, str]) -> None:
        """Extract identifiable info from environment variables."""
        for key, value in env.items():
            key_upper = key.upper()

            # Supabase token
            if "SUPABASE" in key_upper and "TOKEN" in key_upper:
                if not self.api_key_preview:
                    self.api_key_preview = _redact_key(value)
                self.env_vars[key] = "[set]"

            # Resend sender email (not a secret, show full)
            elif key == "SENDER_EMAIL_ADDRESS":
                self.resend_sender = value

            # Various API keys/tokens
            elif "API_KEY" in key_upper or "TOKEN" in key_upper or "SECRET" in key_upper:
                if not self.api_key_preview:
                    self.api_key_preview = _redact_key(value)
                self.env_vars[key] = "[set]"

            # Credential paths (show truncated path)
            elif "PATH" in key_upper or "CREDENTIALS" in key_upper:
                self.env_vars[key] = _truncate_path(value)

            # Other env vars
            else:
                self.env_vars[key] = "[set]"


@dataclass
class ProjectInfo:
    """Information about a project directory."""
    name: str
    path: str
    has_git: bool
    has_mcp_config: bool
    config_source: Literal["project", "global", "none"]
    servers: List[ServerDetail] = field(default_factory=list)

    @property
    def server_count(self) -> int:
        """Number of MCP servers configured."""
        return len(self.servers)

    @property
    def uses_global(self) -> bool:
        """Whether this project uses global MCP config."""
        return not self.has_mcp_config


@dataclass
class ServerUsage:
    """Usage statistics for an MCP server across projects."""
    name: str
    server_type: str
    usage_count: int
    projects: List[ProjectInfo] = field(default_factory=list)

    def get_server_in_project(self, project: ProjectInfo) -> Optional[ServerDetail]:
        """Get this server's detail from a specific project."""
        for server in project.servers:
            if server.name == self.name:
                return server
        return None


def _redact_key(value: str, visible_start: int = 3, visible_end: int = 6) -> str:
    """Redact API key showing first 3 and last 6 characters."""
    if not value:
        return "[empty]"
    if len(value) <= visible_start + visible_end + 3:
        return "***"
    return f"{value[:visible_start]}***{value[-visible_end:]}"


def _redact_middle(value: str, visible_chars: int = 6) -> str:
    """Redact middle of value, showing start and end."""
    if not value:
        return "[empty]"
    if len(value) <= visible_chars * 2:
        return value
    return f"{value[:visible_chars]}...{value[-4:]}"


def _truncate_path(path: str, max_len: int = 30) -> str:
    """Truncate file path for display."""
    if not path:
        return "[empty]"
    # Replace home dir
    import os
    home = os.path.expanduser("~")
    if path.startswith(home):
        path = "~" + path[len(home):]
    if len(path) <= max_len:
        return path
    return "..." + path[-(max_len - 3):]


def compute_server_usages(projects: List[ProjectInfo]) -> List[ServerUsage]:
    """Compute server usage statistics from a list of projects."""
    usage_map: Dict[str, ServerUsage] = {}

    for project in projects:
        for server in project.servers:
            if server.name not in usage_map:
                usage_map[server.name] = ServerUsage(
                    name=server.name,
                    server_type=server.server_type,
                    usage_count=0,
                    projects=[]
                )
            usage_map[server.name].usage_count += 1
            usage_map[server.name].projects.append(project)

    # Sort by usage count descending
    return sorted(usage_map.values(), key=lambda x: -x.usage_count)
