"""
Configuration management for MCP Server Manager TUI.
Handles user preferences and per-directory scan settings.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Literal, Optional


CONFIG_DIR = Path.home() / ".config" / "mcp-manager"
CONFIG_FILE = CONFIG_DIR / "settings.json"


@dataclass
class DirectorySettings:
    """Settings for a specific directory."""
    mode: Literal["all", "smart"] = "all"
    depth: int = 2


@dataclass
class ProjectFolder:
    """A configured project folder."""
    path: str
    name: str  # Display name
    is_primary: bool = False


@dataclass
class UserConfig:
    """User configuration for MCP Server Manager."""
    # Multi-folder support
    project_folders: List[ProjectFolder] = field(default_factory=list)

    # Legacy/per-directory settings
    scan_directories: Dict[str, DirectorySettings] = field(default_factory=dict)
    default_scan_mode: Literal["all", "smart"] = "smart"
    default_depth: int = 2
    theme: str = "dark"
    last_directory: Optional[str] = None

    # Discovery cache
    discovered_projects: List[str] = field(default_factory=list)
    last_discovery_time: Optional[str] = None

    def get_primary_folder(self) -> Optional[ProjectFolder]:
        """Get the primary project folder."""
        for folder in self.project_folders:
            if folder.is_primary:
                return folder
        return self.project_folders[0] if self.project_folders else None

    def add_project_folder(self, path: str, name: str = None, is_primary: bool = False) -> None:
        """Add a project folder."""
        path = os.path.expanduser(path)
        path = os.path.abspath(path)

        # Check if already exists
        for folder in self.project_folders:
            if folder.path == path:
                if is_primary:
                    self._set_primary(path)
                return

        if name is None:
            name = os.path.basename(path)

        # If this is first folder or marked primary, set as primary
        if is_primary or not self.project_folders:
            for folder in self.project_folders:
                folder.is_primary = False
            is_primary = True

        self.project_folders.append(ProjectFolder(path=path, name=name, is_primary=is_primary))

    def remove_project_folder(self, path: str) -> bool:
        """Remove a project folder."""
        path = os.path.expanduser(path)
        path = os.path.abspath(path)

        for i, folder in enumerate(self.project_folders):
            if folder.path == path:
                was_primary = folder.is_primary
                del self.project_folders[i]
                # If removed primary, make first remaining folder primary
                if was_primary and self.project_folders:
                    self.project_folders[0].is_primary = True
                return True
        return False

    def _set_primary(self, path: str) -> None:
        """Set a folder as primary."""
        for folder in self.project_folders:
            folder.is_primary = (folder.path == path)

    def get_directory_settings(self, directory: str) -> DirectorySettings:
        """Get settings for a directory, or create defaults."""
        directory = os.path.expanduser(directory)
        directory = os.path.abspath(directory)

        if directory in self.scan_directories:
            return self.scan_directories[directory]

        # Return defaults
        return DirectorySettings(
            mode=self.default_scan_mode,
            depth=self.default_depth
        )

    def set_directory_settings(
        self,
        directory: str,
        mode: Literal["all", "smart"],
        depth: int = 2
    ) -> None:
        """Set settings for a specific directory."""
        directory = os.path.expanduser(directory)
        directory = os.path.abspath(directory)

        self.scan_directories[directory] = DirectorySettings(
            mode=mode,
            depth=depth
        )

    def remove_directory_settings(self, directory: str) -> bool:
        """Remove custom settings for a directory."""
        directory = os.path.expanduser(directory)
        directory = os.path.abspath(directory)

        if directory in self.scan_directories:
            del self.scan_directories[directory]
            return True
        return False

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_folders": [
                {"path": f.path, "name": f.name, "is_primary": f.is_primary}
                for f in self.project_folders
            ],
            "scan_directories": {
                path: asdict(settings)
                for path, settings in self.scan_directories.items()
            },
            "default_scan_mode": self.default_scan_mode,
            "default_depth": self.default_depth,
            "theme": self.theme,
            "last_directory": self.last_directory,
            "discovered_projects": self.discovered_projects,
            "last_discovery_time": self.last_discovery_time,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "UserConfig":
        """Create from dictionary."""
        config = cls()

        # Load project folders
        for folder_data in data.get("project_folders", []):
            config.project_folders.append(ProjectFolder(
                path=folder_data.get("path", ""),
                name=folder_data.get("name", ""),
                is_primary=folder_data.get("is_primary", False)
            ))

        # Load scan directories
        for path, settings in data.get("scan_directories", {}).items():
            config.scan_directories[path] = DirectorySettings(
                mode=settings.get("mode", "smart"),
                depth=settings.get("depth", 2)
            )

        config.default_scan_mode = data.get("default_scan_mode", "smart")
        config.default_depth = data.get("default_depth", 2)
        config.theme = data.get("theme", "dark")
        config.last_directory = data.get("last_directory")
        config.discovered_projects = data.get("discovered_projects", [])
        config.last_discovery_time = data.get("last_discovery_time")

        return config


def load_config() -> UserConfig:
    """Load user configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return UserConfig.from_dict(data)
        except (json.JSONDecodeError, IOError):
            pass

    return UserConfig()


def save_config(config: UserConfig) -> bool:
    """Save user configuration to file."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        with open(CONFIG_FILE, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

        return True
    except IOError:
        return False


def get_configured_directories(config: UserConfig) -> Dict[str, DirectorySettings]:
    """Get all configured directories with their settings."""
    return config.scan_directories.copy()


def add_directory(
    config: UserConfig,
    directory: str,
    mode: Literal["all", "smart"] = "all",
    depth: int = 2
) -> None:
    """Add a directory with specific scan settings."""
    config.set_directory_settings(directory, mode, depth)
    save_config(config)
