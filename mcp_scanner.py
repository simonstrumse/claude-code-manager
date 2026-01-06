"""
Enhanced scanner for MCP Server Manager.
Scans directories for projects, git status, and MCP configurations.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Literal, Optional

from mcp_data import ProjectInfo, ServerDetail


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
