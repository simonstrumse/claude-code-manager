"""
Configuration management for MCP Server Manager TUI.
Handles user preferences and per-directory scan settings.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Literal, Optional


CONFIG_DIR = Path.home() / ".config" / "mcp-manager"
CONFIG_FILE = CONFIG_DIR / "settings.json"


@dataclass
class DirectorySettings:
    """Settings for a specific directory."""
    mode: Literal["all", "smart"] = "all"
    depth: int = 2


@dataclass
class UserConfig:
    """User configuration for MCP Server Manager."""
    scan_directories: Dict[str, DirectorySettings] = field(default_factory=dict)
    default_scan_mode: Literal["all", "smart"] = "smart"
    default_depth: int = 2
    theme: str = "dark"
    last_directory: Optional[str] = None

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
            "scan_directories": {
                path: asdict(settings)
                for path, settings in self.scan_directories.items()
            },
            "default_scan_mode": self.default_scan_mode,
            "default_depth": self.default_depth,
            "theme": self.theme,
            "last_directory": self.last_directory,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "UserConfig":
        """Create from dictionary."""
        config = cls()

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
