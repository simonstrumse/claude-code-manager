"""
Data models for MCP Server Manager TUI.
Provides dataclasses for representing projects, servers, and usage statistics.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
import re


# =============================================================================
# MCP SERVER MODELS
# =============================================================================

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


# =============================================================================
# ENHANCED MCP SERVER MODEL (with level tracking)
# =============================================================================

@dataclass
class MCPServerConfig:
    """MCP server configuration with level/source tracking."""
    name: str
    server_type: Literal["stdio", "http", "sse"] = "stdio"
    level: Literal["enterprise", "user", "project", "local"] = "project"
    source_file: str = ""  # Which file it came from

    # stdio-specific
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)

    # http/sse-specific
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)

    # Environment variables
    env_vars: Dict[str, str] = field(default_factory=dict)

    # Extracted identifiers (redacted for display)
    supabase_project_ref: Optional[str] = None
    resend_sender: Optional[str] = None
    api_key_preview: Optional[str] = None

    @classmethod
    def from_config(
        cls,
        name: str,
        config: Dict,
        level: Literal["enterprise", "user", "project", "local"] = "project",
        source_file: str = ""
    ) -> "MCPServerConfig":
        """Create MCPServerConfig from raw MCP server config dict."""
        server_type = config.get("type", "stdio")

        server = cls(
            name=name,
            server_type=server_type,
            level=level,
            source_file=source_file,
            command=config.get("command"),
            args=config.get("args", []),
            url=config.get("url"),
            headers=config.get("headers", {}),
        )

        # Extract identifiers from env
        env = config.get("env", {})
        server._extract_from_env(env)

        # Extract identifiers from args
        server._extract_from_args(server.args)

        return server

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

            # API keys in args
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


# =============================================================================
# SKILLS, RULES, CLAUDE.MD MODELS
# =============================================================================

@dataclass
class SkillInfo:
    """Information about a Claude Code skill."""
    name: str
    description: str
    level: Literal["enterprise", "personal", "project", "plugin"]
    path: str  # Full path to SKILL.md

    # Optional fields from SKILL.md frontmatter
    allowed_tools: List[str] = field(default_factory=list)
    model: Optional[str] = None

    @property
    def short_path(self) -> str:
        """Get shortened path for display."""
        return _truncate_path(self.path, 50)


@dataclass
class CommandInfo:
    """Information about a Claude Code slash command.

    Commands are markdown files that define custom slash commands like /commit.
    Located in ~/.claude/commands/*.md (user) or .claude/commands/*.md (project).
    """
    name: str  # Command name (e.g., "commit" for /commit)
    description: str  # From frontmatter or first line
    level: Literal["user", "project", "plugin"]
    path: str  # Full path to command.md

    # Optional fields from frontmatter
    allowed_tools: List[str] = field(default_factory=list)
    args: Optional[str] = None  # Argument pattern if command takes args

    @property
    def short_path(self) -> str:
        """Get shortened path for display."""
        return _truncate_path(self.path, 50)


@dataclass
class RuleInfo:
    """Information about a Claude Code rule file."""
    name: str  # Filename without extension
    level: Literal["user", "project"]
    path: str  # Full path to rule file

    # From frontmatter
    paths_glob: Optional[str] = None  # Applies to specific file patterns
    content_preview: str = ""  # First ~200 chars

    # Project context (for project-level rules)
    project_name: Optional[str] = None

    @property
    def short_path(self) -> str:
        """Get shortened path for display."""
        return _truncate_path(self.path, 50)


@dataclass
class ClaudeMdInfo:
    """Information about a CLAUDE.md file."""
    level: Literal["enterprise", "project", "local", "subdirectory", "user"]
    path: str  # Full path to CLAUDE.md

    # Content analysis
    has_imports: bool = False  # Contains @import statements
    paths_glob: Optional[str] = None  # From frontmatter
    content_preview: str = ""  # First ~200 chars

    # For subdirectory CLAUDE.md files
    relative_dir: Optional[str] = None  # e.g., "src/api"

    # Project context (for project-level files)
    project_name: Optional[str] = None

    @property
    def filename(self) -> str:
        """Get just the filename."""
        import os
        return os.path.basename(self.path)

    @property
    def short_path(self) -> str:
        """Get shortened path for display."""
        return _truncate_path(self.path, 50)


@dataclass
class HookInfo:
    """Information about a Claude Code hook configuration."""
    event: str  # PreToolUse, PostToolUse, SessionStart, etc.
    hook_type: Literal["command", "prompt"]
    source_file: str  # Which settings.json it came from

    # Optional fields
    matcher: Optional[str] = None  # Tool pattern matcher
    command: Optional[str] = None  # For command hooks
    prompt: Optional[str] = None  # For prompt hooks
    timeout: Optional[int] = None

    @property
    def short_source(self) -> str:
        """Get shortened source path for display."""
        return _truncate_path(self.source_file, 40)


@dataclass
class SettingsInfo:
    """Information about a Claude Code settings file."""
    level: Literal["enterprise", "user", "project", "local"]
    path: str

    # Parsed settings
    permissions_allow: List[str] = field(default_factory=list)
    permissions_deny: List[str] = field(default_factory=list)
    enabled_mcp_servers: List[str] = field(default_factory=list)
    disabled_mcp_servers: List[str] = field(default_factory=list)
    hooks_count: int = 0
    custom_model: Optional[str] = None


@dataclass
class PreCommitHook:
    """A single pre-commit hook."""
    id: str
    repo_url: str
    repo_rev: str


@dataclass
class PreCommitConfig:
    """Pre-commit configuration for a project."""
    path: str
    hooks: List[PreCommitHook] = field(default_factory=list)

    @property
    def hook_count(self) -> int:
        return len(self.hooks)

    @property
    def repo_count(self) -> int:
        repos = set(h.repo_url for h in self.hooks)
        return len(repos)


# =============================================================================
# ENHANCED PROJECT MODEL
# =============================================================================

@dataclass
class EnhancedProjectInfo:
    """Complete project information including all Claude Code configuration."""
    name: str
    path: str
    has_git: bool

    # MCP servers from all levels
    mcp_servers: List[MCPServerConfig] = field(default_factory=list)

    # Skills, Commands, Rules, CLAUDE.md
    skills: List[SkillInfo] = field(default_factory=list)
    commands: List['CommandInfo'] = field(default_factory=list)
    rules: List[RuleInfo] = field(default_factory=list)
    claude_mds: List[ClaudeMdInfo] = field(default_factory=list)

    # Hooks and Settings
    hooks: List[HookInfo] = field(default_factory=list)
    settings: List[SettingsInfo] = field(default_factory=list)

    # Pre-commit configuration
    pre_commit: Optional['PreCommitConfig'] = None

    @property
    def mcp_count(self) -> int:
        """Number of MCP servers (all levels)."""
        return len(self.mcp_servers)

    @property
    def project_mcp_count(self) -> int:
        """Number of project-level MCP servers."""
        return sum(1 for s in self.mcp_servers if s.level == "project")

    @property
    def skill_count(self) -> int:
        """Number of skills."""
        return len(self.skills)

    @property
    def command_count(self) -> int:
        """Number of commands."""
        return len(self.commands)

    @property
    def rule_count(self) -> int:
        """Number of rules."""
        return len(self.rules)

    @property
    def claude_md_count(self) -> int:
        """Number of CLAUDE.md files."""
        return len(self.claude_mds)

    @property
    def has_mcp_config(self) -> bool:
        """Whether project has any MCP configuration."""
        return any(s.level == "project" for s in self.mcp_servers)

    @property
    def config_source(self) -> Literal["project", "global", "none"]:
        """Primary config source for backward compatibility."""
        if any(s.level == "project" for s in self.mcp_servers):
            return "project"
        elif any(s.level in ("user", "local") for s in self.mcp_servers):
            return "global"
        return "none"

    # Backward compatibility properties
    @property
    def servers(self) -> List["ServerDetail"]:
        """Convert to ServerDetail list for backward compatibility."""
        result = []
        for mcp in self.mcp_servers:
            # Include all levels (user, project, local, enterprise)
            detail = ServerDetail(
                name=mcp.name,
                server_type=mcp.server_type,
                command=mcp.command,
                url=mcp.url,
                supabase_project_ref=mcp.supabase_project_ref,
                resend_sender=mcp.resend_sender,
                api_key_preview=mcp.api_key_preview,
                env_vars=mcp.env_vars
            )
            result.append(detail)
        return result

    @property
    def server_count(self) -> int:
        """Number of project-level servers for backward compatibility."""
        return self.project_mcp_count


# =============================================================================
# AGGREGATED USAGE STATISTICS
# =============================================================================

@dataclass
class SkillUsage:
    """Usage statistics for a skill across projects."""
    name: str
    level: str
    description: str
    usage_count: int
    projects: List[EnhancedProjectInfo] = field(default_factory=list)


@dataclass
class RuleUsage:
    """Usage statistics for a rule across projects."""
    name: str
    level: str
    paths_glob: Optional[str]
    usage_count: int
    projects: List[EnhancedProjectInfo] = field(default_factory=list)


def compute_skill_usages(projects: List[EnhancedProjectInfo]) -> List[SkillUsage]:
    """Compute skill usage statistics from projects."""
    usage_map: Dict[str, SkillUsage] = {}

    for project in projects:
        for skill in project.skills:
            key = f"{skill.level}:{skill.name}"
            if key not in usage_map:
                usage_map[key] = SkillUsage(
                    name=skill.name,
                    level=skill.level,
                    description=skill.description,
                    usage_count=0,
                    projects=[]
                )
            usage_map[key].usage_count += 1
            usage_map[key].projects.append(project)

    return sorted(usage_map.values(), key=lambda x: -x.usage_count)


def compute_rule_usages(projects: List[EnhancedProjectInfo]) -> List[RuleUsage]:
    """Compute rule usage statistics from projects."""
    usage_map: Dict[str, RuleUsage] = {}

    for project in projects:
        for rule in project.rules:
            key = f"{rule.level}:{rule.name}"
            if key not in usage_map:
                usage_map[key] = RuleUsage(
                    name=rule.name,
                    level=rule.level,
                    paths_glob=rule.paths_glob,
                    usage_count=0,
                    projects=[]
                )
            usage_map[key].usage_count += 1
            usage_map[key].projects.append(project)

    return sorted(usage_map.values(), key=lambda x: -x.usage_count)
