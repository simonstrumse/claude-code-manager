"""
Enhanced scanner for MCP Server Manager.
Scans directories for projects, git status, and MCP configurations.
Includes comprehensive scanning for Skills, Rules, CLAUDE.md, and Hooks.
"""

import json
import os
import re
import glob as glob_module
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

from mcp_data import (
    ProjectInfo, ServerDetail,
    MCPServerConfig, SkillInfo, CommandInfo, RuleInfo, ClaudeMdInfo, HookInfo, SettingsInfo,
    EnhancedProjectInfo, PreCommitConfig, PreCommitHook
)


# Project markers for smart detection mode
PROJECT_MARKERS = {
    ".git",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "mix.exs",
    "CMakeLists.txt",
    "Makefile",
    ".mcp.json",
    ".claude",
}

# Directories to always skip
SKIP_DIRS = {
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "target",
    "build",
    "dist",
    ".next",
    ".nuxt",
    "vendor",
    "Pods",
    ".gradle",
    ".idea",
    ".vscode",
}


class EnhancedScanner:
    """Scan directories for projects with MCP configurations and git status."""

    def __init__(self):
        self._global_config: Optional[Dict] = None
        self._global_config_loaded = False

    def scan_directory(
        self,
        directory: str,
        max_depth: int = 2,
        mode: Literal["all", "smart"] = "all"
    ) -> List[ProjectInfo]:
        """
        Scan directory for projects.

        Args:
            directory: Directory to scan
            max_depth: Maximum depth to scan (1 = immediate children only)
            mode: "all" = every subfolder is a project
                  "smart" = only folders with project markers

        Returns:
            List of ProjectInfo objects
        """
        directory = os.path.expanduser(directory)
        directory = os.path.abspath(directory)

        if not os.path.isdir(directory):
            return []

        projects: List[ProjectInfo] = []

        # Get immediate subdirectories
        try:
            entries = os.listdir(directory)
        except PermissionError:
            return []

        for entry in sorted(entries):
            entry_path = os.path.join(directory, entry)

            # Skip non-directories
            if not os.path.isdir(entry_path):
                continue

            # Skip hidden directories (except .git which we check for)
            if entry.startswith(".") and entry not in PROJECT_MARKERS:
                continue

            # Skip known non-project directories
            if entry in SKIP_DIRS:
                continue

            # Check if this should be treated as a project
            if mode == "smart" and not self._is_project_folder(entry_path):
                # In smart mode, recurse into non-project folders
                if max_depth > 1:
                    nested = self.scan_directory(entry_path, max_depth - 1, mode)
                    projects.extend(nested)
                continue

            # Analyze this project
            project = self._analyze_project(entry_path)
            projects.append(project)

        return projects

    def _is_project_folder(self, path: str) -> bool:
        """Check if a folder looks like a project (has project markers)."""
        try:
            entries = set(os.listdir(path))
        except PermissionError:
            return False

        return bool(entries & PROJECT_MARKERS)

    def _analyze_project(self, path: str) -> ProjectInfo:
        """Analyze a single project directory."""
        name = os.path.basename(path)
        has_git = os.path.isdir(os.path.join(path, ".git"))

        # Check for local MCP config
        local_config = self._load_local_mcp_config(path)

        if local_config and local_config.get("mcpServers"):
            config_source = "project"
            servers = self._extract_servers(local_config)
            has_mcp_config = True
        else:
            # Project doesn't have local MCP config
            config_source = "none"
            servers = []
            has_mcp_config = False

        return ProjectInfo(
            name=name,
            path=path,
            has_git=has_git,
            has_mcp_config=has_mcp_config,
            config_source=config_source,
            servers=servers
        )

    def _load_local_mcp_config(self, path: str) -> Optional[Dict]:
        """Load MCP config from a project directory."""
        # Check possible config locations
        config_files = [
            os.path.join(path, ".mcp.json"),
            os.path.join(path, ".claude", "settings.json"),
            os.path.join(path, ".claude", "settings.local.json"),
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    continue

        return None

    def _load_global_config(self) -> Dict:
        """Load global MCP config (cached)."""
        if self._global_config_loaded:
            return self._global_config or {}

        self._global_config_loaded = True
        home = Path.home()

        # Check possible global config locations
        global_files = [
            home / ".mcp.json",
            home / ".claude.json",
            home / ".claude" / "settings.json",
        ]

        for config_file in global_files:
            if config_file.exists():
                try:
                    with open(config_file, "r") as f:
                        self._global_config = json.load(f)
                        return self._global_config
                except (json.JSONDecodeError, IOError):
                    continue

        self._global_config = {}
        return {}

    def _extract_servers(self, config: Dict) -> List[ServerDetail]:
        """Extract ServerDetail objects from config."""
        servers = []
        mcp_servers = config.get("mcpServers", {})

        for name, server_config in mcp_servers.items():
            if isinstance(server_config, dict):
                server = ServerDetail.from_config(name, server_config)
                servers.append(server)

        return servers

    def get_global_servers(self) -> List[ServerDetail]:
        """Get servers from global config."""
        global_config = self._load_global_config()
        return self._extract_servers(global_config)


def scan_for_overview(
    directory: str,
    mode: Literal["all", "smart"] = "all",
    max_depth: int = 2
) -> List[ProjectInfo]:
    """
    Convenience function to scan a directory and return project overview.

    Args:
        directory: Directory to scan
        mode: Scan mode ("all" or "smart")
        max_depth: Maximum scan depth

    Returns:
        List of ProjectInfo sorted by name
    """
    scanner = EnhancedScanner()
    projects = scanner.scan_directory(directory, max_depth, mode)
    return sorted(projects, key=lambda p: p.name.lower())


# =============================================================================
# COMPREHENSIVE SCANNER
# =============================================================================

# Configuration file locations
ENTERPRISE_PATHS = {
    'darwin': '/Library/Application Support/ClaudeCode',  # macOS
    'linux': '/etc/claude-code',
}

USER_PATHS = {
    'claude_json': Path.home() / '.claude.json',
    'claude_dir': Path.home() / '.claude',
    'skills': Path.home() / '.claude' / 'skills',
    'plugins': Path.home() / '.claude' / 'plugins' / 'marketplaces',
    'commands': Path.home() / '.claude' / 'commands',
    'rules': Path.home() / '.claude' / 'rules',
    'settings': Path.home() / '.claude' / 'settings.json',
    'claude_md': Path.home() / '.claude' / 'CLAUDE.md',
}


class ComprehensiveScanner:
    """
    Comprehensive scanner for ALL Claude Code configuration.
    Scans for MCP servers, Skills, Rules, CLAUDE.md files, and Hooks
    at all levels (Enterprise, User, Project, Local).
    """

    def __init__(self):
        # Cached user-level data (loaded once)
        self._user_mcp_servers: Dict[str, MCPServerConfig] = {}
        self._user_mcp_by_project: Dict[str, Dict[str, MCPServerConfig]] = {}
        self._user_skills: List[SkillInfo] = []
        self._user_commands: List[CommandInfo] = []
        self._user_rules: List[RuleInfo] = []
        self._user_claude_md: Optional[ClaudeMdInfo] = None
        self._user_hooks: List[HookInfo] = []
        self._user_settings: Optional[SettingsInfo] = None

        # Cached enterprise data
        self._enterprise_mcp: Dict[str, MCPServerConfig] = {}
        self._enterprise_claude_md: Optional[ClaudeMdInfo] = None

        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load user and enterprise level data (once)."""
        if self._loaded:
            return

        self._loaded = True
        self._load_user_level()
        self._load_enterprise_level()

    def _load_user_level(self) -> None:
        """Load all user-level configuration."""
        # Load ~/.claude.json for MCP servers
        if USER_PATHS['claude_json'].exists():
            try:
                with open(USER_PATHS['claude_json'], 'r') as f:
                    data = json.load(f)

                # Global MCP servers
                for name, config in data.get('mcpServers', {}).items():
                    self._user_mcp_servers[name] = MCPServerConfig.from_config(
                        name, config, level='user',
                        source_file=str(USER_PATHS['claude_json'])
                    )

                # Per-project local MCP servers
                for project_path, project_data in data.get('projects', {}).items():
                    self._user_mcp_by_project[project_path] = {}
                    for name, config in project_data.get('mcpServers', {}).items():
                        self._user_mcp_by_project[project_path][name] = MCPServerConfig.from_config(
                            name, config, level='local',
                            source_file=str(USER_PATHS['claude_json'])
                        )
            except (json.JSONDecodeError, IOError):
                pass

        # Load user skills
        if USER_PATHS['skills'].is_dir():
            self._user_skills = self._scan_skills_directory(
                USER_PATHS['skills'], level='personal'
            )

        # Load plugin skills from ~/.claude/plugins/marketplaces/
        if USER_PATHS['plugins'].is_dir():
            plugin_skills = self._scan_plugin_skills(USER_PATHS['plugins'])
            self._user_skills.extend(plugin_skills)

        # Load user commands
        if USER_PATHS['commands'].is_dir():
            self._user_commands = self._scan_commands_directory(
                USER_PATHS['commands'], level='user'
            )

        # Load user rules
        if USER_PATHS['rules'].is_dir():
            self._user_rules = self._scan_rules_directory(
                USER_PATHS['rules'], level='user'
            )

        # Load user CLAUDE.md
        if USER_PATHS['claude_md'].exists():
            self._user_claude_md = self._parse_claude_md(
                USER_PATHS['claude_md'], level='user'
            )

        # Load user settings (for hooks)
        if USER_PATHS['settings'].exists():
            self._user_settings, self._user_hooks = self._parse_settings_file(
                USER_PATHS['settings'], level='user'
            )

    def _load_enterprise_level(self) -> None:
        """Load enterprise-level configuration."""
        import sys
        platform = sys.platform

        enterprise_dir = ENTERPRISE_PATHS.get(platform)
        if not enterprise_dir:
            return

        enterprise_path = Path(enterprise_dir)
        if not enterprise_path.exists():
            return

        # Enterprise MCP
        mcp_file = enterprise_path / 'managed-mcp.json'
        if mcp_file.exists():
            try:
                with open(mcp_file, 'r') as f:
                    data = json.load(f)
                for name, config in data.get('mcpServers', {}).items():
                    self._enterprise_mcp[name] = MCPServerConfig.from_config(
                        name, config, level='enterprise',
                        source_file=str(mcp_file)
                    )
            except (json.JSONDecodeError, IOError):
                pass

        # Enterprise CLAUDE.md
        claude_md_file = enterprise_path / 'CLAUDE.md'
        if claude_md_file.exists():
            self._enterprise_claude_md = self._parse_claude_md(
                claude_md_file, level='enterprise'
            )

    def scan_directory(
        self,
        directory: str,
        max_depth: int = 2,
        mode: Literal["all", "smart"] = "all"
    ) -> List[EnhancedProjectInfo]:
        """
        Scan directory for projects with comprehensive configuration.

        Returns:
            List of EnhancedProjectInfo with all config data
        """
        self._ensure_loaded()

        directory = os.path.expanduser(directory)
        directory = os.path.abspath(directory)

        if not os.path.isdir(directory):
            return []

        projects: List[EnhancedProjectInfo] = []

        try:
            entries = os.listdir(directory)
        except PermissionError:
            return []

        for entry in sorted(entries):
            entry_path = os.path.join(directory, entry)

            if not os.path.isdir(entry_path):
                continue

            if entry.startswith(".") and entry not in PROJECT_MARKERS:
                continue

            if entry in SKIP_DIRS:
                continue

            if mode == "smart" and not self._is_project_folder(entry_path):
                if max_depth > 1:
                    nested = self.scan_directory(entry_path, max_depth - 1, mode)
                    projects.extend(nested)
                continue

            project = self._analyze_project_comprehensive(entry_path)
            projects.append(project)

        return projects

    def scan_project(self, path: str) -> EnhancedProjectInfo:
        """
        Scan a single project for comprehensive configuration.

        Args:
            path: Absolute path to the project directory

        Returns:
            EnhancedProjectInfo with all config data
        """
        self._ensure_loaded()
        path = os.path.expanduser(path)
        path = os.path.abspath(path)
        return self._analyze_project_comprehensive(path)

    def _is_project_folder(self, path: str) -> bool:
        """Check if a folder looks like a project."""
        try:
            entries = set(os.listdir(path))
        except PermissionError:
            return False
        return bool(entries & PROJECT_MARKERS)

    def _analyze_project_comprehensive(self, path: str) -> EnhancedProjectInfo:
        """Analyze a project for ALL Claude Code configuration."""
        name = os.path.basename(path)
        has_git = os.path.isdir(os.path.join(path, ".git"))

        project = EnhancedProjectInfo(
            name=name,
            path=path,
            has_git=has_git
        )

        # --- MCP SERVERS ---
        # 1. Enterprise (highest priority)
        for server in self._enterprise_mcp.values():
            project.mcp_servers.append(server)

        # 2. Local (from ~/.claude.json projects[path])
        if path in self._user_mcp_by_project:
            for server in self._user_mcp_by_project[path].values():
                project.mcp_servers.append(server)

        # 3. Project (.mcp.json)
        project_mcp = self._load_project_mcp(path)
        project.mcp_servers.extend(project_mcp)

        # 4. User global (if not overridden)
        existing_names = {s.name for s in project.mcp_servers}
        for name, server in self._user_mcp_servers.items():
            if name not in existing_names:
                project.mcp_servers.append(server)

        # --- SKILLS ---
        # Project skills only (user skills tracked separately, not duplicated per project)
        project_skills_dir = Path(path) / '.claude' / 'skills'
        if project_skills_dir.is_dir():
            project.skills = self._scan_skills_directory(
                project_skills_dir, level='project'
            )
        # NOTE: User skills available via get_user_skills(), not added to every project

        # --- COMMANDS ---
        # Project commands only
        project_commands_dir = Path(path) / '.claude' / 'commands'
        if project_commands_dir.is_dir():
            project.commands = self._scan_commands_directory(
                project_commands_dir, level='project'
            )
        # NOTE: User commands available via get_user_commands(), not added to every project

        # --- RULES ---
        # Project rules only (user rules tracked separately, not duplicated per project)
        project_rules_dir = Path(path) / '.claude' / 'rules'
        if project_rules_dir.is_dir():
            project.rules = self._scan_rules_directory(
                project_rules_dir, level='project', project_name=name
            )
        # NOTE: User rules available via get_user_rules(), not added to every project

        # --- CLAUDE.MD ---
        # Project root CLAUDE.md
        for claude_md_name in ['CLAUDE.md', '.claude/CLAUDE.md']:
            claude_md_path = Path(path) / claude_md_name
            if claude_md_path.exists():
                project.claude_mds.append(
                    self._parse_claude_md(claude_md_path, level='project', project_name=name)
                )

        # CLAUDE.local.md
        local_claude_md = Path(path) / 'CLAUDE.local.md'
        if local_claude_md.exists():
            project.claude_mds.append(
                self._parse_claude_md(local_claude_md, level='local', project_name=name)
            )

        # Subdirectory CLAUDE.md files (scan common subdirs)
        for subdir_claude_md in Path(path).glob('**/CLAUDE.md'):
            if subdir_claude_md.parent != Path(path) and '.claude' not in str(subdir_claude_md):
                rel_dir = str(subdir_claude_md.parent.relative_to(path))
                if not any(skip in rel_dir for skip in SKIP_DIRS):
                    info = self._parse_claude_md(subdir_claude_md, level='subdirectory', project_name=name)
                    info.relative_dir = rel_dir
                    project.claude_mds.append(info)

        # Add user CLAUDE.md
        if self._user_claude_md:
            project.claude_mds.append(self._user_claude_md)

        # Add enterprise CLAUDE.md
        if self._enterprise_claude_md:
            project.claude_mds.append(self._enterprise_claude_md)

        # --- HOOKS & SETTINGS ---
        # Project settings
        for settings_name, level in [
            ('.claude/settings.json', 'project'),
            ('.claude/settings.local.json', 'local'),
        ]:
            settings_path = Path(path) / settings_name
            if settings_path.exists():
                settings_info, hooks = self._parse_settings_file(settings_path, level)
                if settings_info:
                    project.settings.append(settings_info)
                project.hooks.extend(hooks)

        # Add user hooks
        project.hooks.extend(self._user_hooks)

        # Add user settings
        if self._user_settings:
            project.settings.append(self._user_settings)

        # --- PRE-COMMIT ---
        pre_commit_path = Path(path) / '.pre-commit-config.yaml'
        if pre_commit_path.exists():
            project.pre_commit = self._parse_pre_commit_config(pre_commit_path)

        return project

    def _load_project_mcp(self, path: str) -> List[MCPServerConfig]:
        """Load MCP servers from project .mcp.json."""
        servers = []
        mcp_file = Path(path) / '.mcp.json'

        if mcp_file.exists():
            try:
                with open(mcp_file, 'r') as f:
                    data = json.load(f)
                for name, config in data.get('mcpServers', {}).items():
                    servers.append(MCPServerConfig.from_config(
                        name, config, level='project',
                        source_file=str(mcp_file)
                    ))
            except (json.JSONDecodeError, IOError):
                pass

        return servers

    def _scan_skills_directory(
        self,
        skills_dir: Path,
        level: Literal["enterprise", "personal", "project", "plugin"]
    ) -> List[SkillInfo]:
        """Scan a skills directory for SKILL.md files."""
        skills = []

        if not skills_dir.is_dir():
            return skills

        for skill_folder in skills_dir.iterdir():
            if not skill_folder.is_dir():
                continue

            skill_md = skill_folder / 'SKILL.md'
            if not skill_md.exists():
                continue

            skill = self._parse_skill_md(skill_md, level)
            if skill:
                skills.append(skill)

        return skills

    def _scan_plugin_skills(self, marketplaces_dir: Path) -> List[SkillInfo]:
        """Scan plugin marketplaces for skills.

        Structure: marketplaces/{marketplace}/plugins/{plugin}/skills/{skill}/SKILL.md
        """
        skills = []

        if not marketplaces_dir.is_dir():
            return skills

        # Iterate through marketplaces
        for marketplace in marketplaces_dir.iterdir():
            if not marketplace.is_dir() or marketplace.name.startswith('.'):
                continue

            plugins_dir = marketplace / 'plugins'
            if not plugins_dir.is_dir():
                continue

            # Iterate through plugins
            for plugin in plugins_dir.iterdir():
                if not plugin.is_dir():
                    continue

                skills_dir = plugin / 'skills'
                if skills_dir.is_dir():
                    plugin_skills = self._scan_skills_directory(skills_dir, level='plugin')
                    skills.extend(plugin_skills)

        return skills

    def _parse_skill_md(
        self,
        path: Path,
        level: Literal["enterprise", "personal", "project", "plugin"]
    ) -> Optional[SkillInfo]:
        """Parse a SKILL.md file."""
        try:
            content = path.read_text(encoding='utf-8')
        except IOError:
            return None

        # Parse YAML frontmatter
        frontmatter, body = self._parse_frontmatter(content)

        name = frontmatter.get('name', path.parent.name)
        description = frontmatter.get('description', '')
        allowed_tools_str = frontmatter.get('allowed-tools', '')
        allowed_tools = [t.strip() for t in allowed_tools_str.split(',') if t.strip()]
        model = frontmatter.get('model')

        return SkillInfo(
            name=name,
            description=description[:200] if description else '',
            level=level,
            path=str(path),
            allowed_tools=allowed_tools,
            model=model
        )

    def _scan_commands_directory(
        self,
        commands_dir: Path,
        level: Literal["user", "project", "plugin"]
    ) -> List[CommandInfo]:
        """Scan a commands directory for .md files (slash commands)."""
        commands = []

        if not commands_dir.is_dir():
            return commands

        # Commands are .md files directly in the commands directory
        for md_file in commands_dir.glob('*.md'):
            command = self._parse_command_md(md_file, level)
            if command:
                commands.append(command)

        return commands

    def _parse_command_md(
        self,
        path: Path,
        level: Literal["user", "project", "plugin"]
    ) -> Optional[CommandInfo]:
        """Parse a command .md file (slash command definition)."""
        try:
            content = path.read_text(encoding='utf-8')
        except IOError:
            return None

        frontmatter, body = self._parse_frontmatter(content)

        # Command name is filename without extension (e.g., commit.md -> /commit)
        name = path.stem
        description = frontmatter.get('description', '')

        # If no description in frontmatter, use first line of body
        if not description and body:
            first_line = body.strip().split('\n')[0]
            # Remove markdown headers
            description = first_line.lstrip('#').strip()[:100]

        allowed_tools_str = frontmatter.get('allowed-tools', '')
        allowed_tools = [t.strip() for t in allowed_tools_str.split(',') if t.strip()]
        args = frontmatter.get('args')

        return CommandInfo(
            name=name,
            description=description[:200] if description else f'/{name} command',
            level=level,
            path=str(path),
            allowed_tools=allowed_tools,
            args=args
        )

    def _scan_rules_directory(
        self,
        rules_dir: Path,
        level: Literal["user", "project"],
        project_name: Optional[str] = None
    ) -> List[RuleInfo]:
        """Scan a rules directory for .md files."""
        rules = []

        if not rules_dir.is_dir():
            return rules

        # Recursively find all .md files
        for md_file in rules_dir.rglob('*.md'):
            rule = self._parse_rule_md(md_file, level, project_name)
            if rule:
                rules.append(rule)

        return rules

    def _parse_rule_md(
        self,
        path: Path,
        level: Literal["user", "project"],
        project_name: Optional[str] = None
    ) -> Optional[RuleInfo]:
        """Parse a rule .md file."""
        try:
            content = path.read_text(encoding='utf-8')
        except IOError:
            return None

        frontmatter, body = self._parse_frontmatter(content)

        name = path.stem  # Filename without extension
        paths_glob = frontmatter.get('paths')

        # Get content preview (first 200 chars of body)
        content_preview = body.strip()[:200] if body else ''

        return RuleInfo(
            name=name,
            level=level,
            path=str(path),
            paths_glob=paths_glob,
            content_preview=content_preview,
            project_name=project_name
        )

    def _parse_claude_md(
        self,
        path: Path,
        level: Literal["enterprise", "project", "local", "subdirectory", "user"],
        project_name: Optional[str] = None
    ) -> ClaudeMdInfo:
        """Parse a CLAUDE.md file."""
        content = ''
        try:
            content = path.read_text(encoding='utf-8')
        except IOError:
            pass

        frontmatter, body = self._parse_frontmatter(content)

        # Check for @imports
        has_imports = bool(re.search(r'@[~/\w]', body)) if body else False

        paths_glob = frontmatter.get('paths')
        content_preview = body.strip()[:200] if body else ''

        return ClaudeMdInfo(
            level=level,
            path=str(path),
            has_imports=has_imports,
            paths_glob=paths_glob,
            content_preview=content_preview,
            project_name=project_name
        )

    def _parse_settings_file(
        self,
        path: Path,
        level: Literal["enterprise", "user", "project", "local"]
    ) -> Tuple[Optional[SettingsInfo], List[HookInfo]]:
        """Parse a settings.json file for settings and hooks."""
        hooks = []
        settings_info = None

        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None, []

        # Parse permissions
        permissions = data.get('permissions', {})
        allow = permissions.get('allow', [])
        deny = permissions.get('deny', [])

        # Parse MCP server lists
        enabled_mcp = data.get('enabledMcpjsonServers', [])
        disabled_mcp = data.get('disabledMcpjsonServers', [])

        # Parse hooks
        hooks_data = data.get('hooks', {})
        hooks_count = 0

        for event, event_hooks in hooks_data.items():
            if isinstance(event_hooks, list):
                for hook_entry in event_hooks:
                    matcher = hook_entry.get('matcher')
                    for hook in hook_entry.get('hooks', []):
                        hook_type = hook.get('type', 'command')
                        hooks.append(HookInfo(
                            event=event,
                            hook_type=hook_type,
                            source_file=str(path),
                            matcher=matcher,
                            command=hook.get('command'),
                            prompt=hook.get('prompt'),
                            timeout=hook.get('timeout')
                        ))
                        hooks_count += 1

        settings_info = SettingsInfo(
            level=level,
            path=str(path),
            permissions_allow=allow if isinstance(allow, list) else [],
            permissions_deny=deny if isinstance(deny, list) else [],
            enabled_mcp_servers=enabled_mcp if isinstance(enabled_mcp, list) else [],
            disabled_mcp_servers=disabled_mcp if isinstance(disabled_mcp, list) else [],
            hooks_count=hooks_count,
            custom_model=data.get('model')
        )

        return settings_info, hooks

    def _parse_pre_commit_config(self, path: Path) -> Optional[PreCommitConfig]:
        """Parse a .pre-commit-config.yaml file."""
        try:
            import yaml
        except ImportError:
            # PyYAML not installed, skip pre-commit parsing
            return None

        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
        except Exception:
            return None

        if not data or 'repos' not in data:
            return None

        hooks = []
        for repo in data.get('repos', []):
            repo_url = repo.get('repo', '')
            repo_rev = repo.get('rev', '')

            for hook in repo.get('hooks', []):
                hook_id = hook.get('id', '')
                if hook_id:
                    hooks.append(PreCommitHook(
                        id=hook_id,
                        repo_url=repo_url,
                        repo_rev=repo_rev
                    ))

        return PreCommitConfig(
            path=str(path),
            hooks=hooks
        )

    def _parse_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """Parse YAML frontmatter from content."""
        if not content.startswith('---'):
            return {}, content

        # Find closing ---
        end_match = re.search(r'\n---\s*\n', content[3:])
        if not end_match:
            return {}, content

        frontmatter_text = content[3:end_match.start() + 3]
        body = content[end_match.end() + 3:]

        # Simple YAML parsing (key: value)
        frontmatter = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, _, value = line.partition(':')
                frontmatter[key.strip()] = value.strip()

        return frontmatter, body

    # Convenience methods
    def get_user_skills(self) -> List[SkillInfo]:
        """Get all user-level skills."""
        self._ensure_loaded()
        return self._user_skills

    def get_user_commands(self) -> List[CommandInfo]:
        """Get all user-level commands (slash commands)."""
        self._ensure_loaded()
        return self._user_commands

    def get_user_rules(self) -> List[RuleInfo]:
        """Get all user-level rules."""
        self._ensure_loaded()
        return self._user_rules

    def get_user_mcp_servers(self) -> List[MCPServerConfig]:
        """Get all user-level MCP servers."""
        self._ensure_loaded()
        return list(self._user_mcp_servers.values())


def scan_comprehensive(
    directory: str,
    mode: Literal["all", "smart"] = "all",
    max_depth: int = 2
) -> List[EnhancedProjectInfo]:
    """
    Convenience function to scan with comprehensive configuration.

    Returns:
        List of EnhancedProjectInfo sorted by name
    """
    scanner = ComprehensiveScanner()
    projects = scanner.scan_directory(directory, max_depth, mode)
    return sorted(projects, key=lambda p: p.name.lower())


# =============================================================================
# PROJECT DISCOVERY
# =============================================================================

# Smart locations to scan for projects (user-relative)
DISCOVERY_LOCATIONS = [
    "~",              # Home folder root (scans immediate children)
    "~/Documents",
    "~/Developer",
    "~/Projects",
    "~/Code",
    "~/Repos",
    "~/repos",
    "~/dev",
    "~/code",
    "~/Desktop",      # Some people keep projects here
    "~/Claude Code Projects",
    "~/GitHub",
    "~/Workspace",
    "~/workspace",
]

# Claude Code specific markers (more reliable than generic project markers)
CLAUDE_PROJECT_MARKERS = {
    ".mcp.json",          # MCP server config
    ".claude",             # Claude config directory
    "CLAUDE.md",           # Project instructions
    "CLAUDE.local.md",     # Local instructions
}

# Paths to exclude from discovery (not real projects)
DISCOVERY_EXCLUDE = {
    ".claude",            # User's Claude config folder
    "Downloads",          # Downloads folder
    "Library",            # System library
    "Applications",       # Applications folder
    ".Trash",             # Trash
    ".config",            # Config folder
    "node_modules",       # Dependencies
    ".npm",               # NPM cache
    ".cache",             # Cache folders
}


class ProjectDiscovery:
    """
    Fast, efficient discovery of Claude Code projects across the system.
    Scans smart locations for projects that have Claude Code configuration.
    """

    def __init__(self):
        self._discovered: List[str] = []
        self._scanned_dirs: set = set()

    def discover_projects(
        self,
        additional_paths: List[str] = None,
        max_depth: int = 3,
        claude_only: bool = True
    ) -> List[str]:
        """
        Discover Claude Code projects across the system.

        Args:
            additional_paths: Extra paths to scan beyond defaults
            max_depth: Maximum depth to scan (3 = grandchildren of search roots)
            claude_only: If True, only return projects with Claude Code config
                         If False, return all projects with any project marker

        Returns:
            List of absolute paths to discovered projects
        """
        self._discovered = []
        self._scanned_dirs = set()

        # Collect all paths to scan
        paths_to_scan = []
        for loc in DISCOVERY_LOCATIONS:
            expanded = os.path.expanduser(loc)
            if os.path.isdir(expanded):
                paths_to_scan.append(expanded)

        if additional_paths:
            for path in additional_paths:
                expanded = os.path.expanduser(path)
                expanded = os.path.abspath(expanded)
                if os.path.isdir(expanded):
                    paths_to_scan.append(expanded)

        # Deduplicate and scan
        paths_to_scan = list(set(paths_to_scan))
        for path in paths_to_scan:
            self._scan_for_projects(path, max_depth, claude_only)

        return sorted(set(self._discovered))

    def _scan_for_projects(
        self,
        directory: str,
        depth: int,
        claude_only: bool
    ) -> None:
        """Recursively scan a directory for projects."""
        if depth <= 0:
            return

        # Prevent re-scanning
        real_path = os.path.realpath(directory)
        if real_path in self._scanned_dirs:
            return
        self._scanned_dirs.add(real_path)

        try:
            entries = os.listdir(directory)
        except (PermissionError, OSError):
            return

        for entry in entries:
            # Skip hidden (except .claude) and known non-project dirs
            if entry.startswith('.') and entry not in ['.claude', '.mcp.json']:
                continue
            if entry in SKIP_DIRS:
                continue
            # Skip excluded discovery paths
            if entry in DISCOVERY_EXCLUDE:
                continue

            entry_path = os.path.join(directory, entry)
            if not os.path.isdir(entry_path):
                continue

            # Check if this is a project
            if claude_only:
                is_project = self._has_claude_config(entry_path)
            else:
                is_project = self._is_project_folder(entry_path)

            if is_project:
                # Double-check it's not an excluded path by full name
                basename = os.path.basename(entry_path)
                if basename not in DISCOVERY_EXCLUDE:
                    self._discovered.append(entry_path)
            elif depth > 1:
                # Recurse into non-project directories
                self._scan_for_projects(entry_path, depth - 1, claude_only)

    def _has_claude_config(self, path: str) -> bool:
        """Check if a directory has Claude Code configuration."""
        try:
            entries = set(os.listdir(path))
        except (PermissionError, OSError):
            return False

        # Check for Claude-specific markers
        if entries & CLAUDE_PROJECT_MARKERS:
            return True

        # Check for .claude directory with content
        claude_dir = os.path.join(path, '.claude')
        if os.path.isdir(claude_dir):
            try:
                if os.listdir(claude_dir):  # Has any content
                    return True
            except (PermissionError, OSError):
                pass

        return False

    def _is_project_folder(self, path: str) -> bool:
        """Check if a folder is any kind of project."""
        try:
            entries = set(os.listdir(path))
        except (PermissionError, OSError):
            return False
        return bool(entries & PROJECT_MARKERS)


def discover_claude_projects(
    additional_paths: List[str] = None,
    max_depth: int = 3
) -> List[str]:
    """
    Convenience function to discover Claude Code projects.

    Args:
        additional_paths: Extra paths to scan
        max_depth: Maximum scan depth

    Returns:
        Sorted list of project paths
    """
    discovery = ProjectDiscovery()
    return discovery.discover_projects(additional_paths, max_depth, claude_only=True)


def discover_all_projects(
    additional_paths: List[str] = None,
    max_depth: int = 3
) -> List[str]:
    """
    Discover all projects (not just Claude Code projects).

    Returns:
        Sorted list of project paths
    """
    discovery = ProjectDiscovery()
    return discovery.discover_projects(additional_paths, max_depth, claude_only=False)
