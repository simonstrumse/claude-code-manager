#!/usr/bin/env python3
"""
MCP Server Manager for Claude Desktop & Claude Code
A CLI tool to manage MCP servers across both Claude Desktop and Claude Code
Author: Kalin Yorgov
License: MIT
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import shutil
from datetime import datetime
from collections import defaultdict
import platform

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ORANGE = '\033[38;5;208m'
    PURPLE = '\033[38;5;141m'

class ConfigLevel:
    """Configuration levels for MCP servers"""
    DESKTOP = "Claude Desktop"  # Claude Desktop app config
    USER = "User/Global"  # ~/.claude.json for Claude Code
    PROJECT = "Project"   # ./.mcp.json or ./.claude/settings.json
    LOCAL = "Local"       # Project-specific in ~/.claude.json

class MCPServerManager:
    def __init__(self, project_path: str = None, app: str = "auto"):
        """Initialize the MCP Server Manager
        
        Args:
            project_path: Project directory path
            app: Which app to manage ('desktop', 'code', 'both', 'auto')
        """
        self.project_path = project_path or os.getcwd()
        self.app = app
        self.configs = {}
        self.disabled_servers = defaultdict(dict)
        
        # Detect which apps are available
        self.has_desktop = False
        self.has_code = False
        self._detect_apps()
        
        # Define configuration file paths
        self.config_paths = self._get_config_paths()
    
    def _detect_apps(self):
        """Detect which Claude apps are installed"""
        # Check for Claude Desktop
        desktop_paths = self._get_desktop_config_paths()
        for path in desktop_paths.values():
            if path and os.path.exists(path):
                self.has_desktop = True
                break
        
        # Check for Claude Code
        code_config = Path.home() / '.claude.json'
        if code_config.exists() or shutil.which('claude'):
            self.has_code = True
        
        # Auto-detect which app to use
        if self.app == "auto":
            if self.has_desktop and not self.has_code:
                self.app = "desktop"
            elif self.has_code and not self.has_desktop:
                self.app = "code"
            else:
                self.app = "both"
    
    def _get_desktop_config_paths(self) -> Dict[str, str]:
        """Get Claude Desktop config paths for different platforms"""
        paths = {}
        system = platform.system()
        home = Path.home()
        
        if system == "Darwin":  # macOS
            paths[ConfigLevel.DESKTOP] = str(home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json")
        elif system == "Windows":
            paths[ConfigLevel.DESKTOP] = str(home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json")
        elif system == "Linux":
            # Linux might use XDG config
            xdg_config = os.environ.get('XDG_CONFIG_HOME', str(home / '.config'))
            paths[ConfigLevel.DESKTOP] = str(Path(xdg_config) / "Claude" / "claude_desktop_config.json")
        
        return paths
    
    def _get_config_paths(self) -> Dict[str, str]:
        """Get all configuration file paths"""
        paths = {}
        
        # Claude Desktop config
        if self.app in ["desktop", "both"]:
            desktop_paths = self._get_desktop_config_paths()
            paths.update(desktop_paths)
        
        # Claude Code configs
        if self.app in ["code", "both"]:
            home = Path.home()
            
            # User/Global config for Claude Code
            primary = home / '.claude.json'
            alternative = home / '.claude' / 'settings.json'
            
            if primary.exists():
                paths[ConfigLevel.USER] = str(primary)
            elif alternative.exists():
                paths[ConfigLevel.USER] = str(alternative)
            else:
                paths[ConfigLevel.USER] = str(primary)
            
            # Project config
            project_dir = Path(self.project_path)
            possible_paths = [
                project_dir / '.mcp.json',
                project_dir / '.claude' / 'settings.json',
                project_dir / '.claude' / 'settings.local.json'
            ]
            
            for path in possible_paths:
                if path.exists():
                    paths[ConfigLevel.PROJECT] = str(path)
                    break
            else:
                paths[ConfigLevel.PROJECT] = str(project_dir / '.mcp.json')
            
            # Local config (project-specific in user config)
            paths[ConfigLevel.LOCAL] = paths.get(ConfigLevel.USER, str(primary))
        
        return paths
    
    def load_all_configs(self) -> bool:
        """Load configurations from all levels"""
        success = True
        
        for level, path in self.config_paths.items():
            if path and os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                        config = json.loads(content)
                        
                        if level == ConfigLevel.LOCAL and level != ConfigLevel.DESKTOP:
                            # Extract project-specific config from user config
                            if 'projects' in config:
                                for project_path, project_config in config['projects'].items():
                                    if self.project_path.startswith(project_path):
                                        self.configs[level] = project_config
                                        break
                        else:
                            self.configs[level] = config
                        
                        # Load disabled servers for this level
                        if level in self.configs:
                            disabled_key = '_disabled_mcpServers'
                            if disabled_key in self.configs[level]:
                                self.disabled_servers[level] = self.configs[level][disabled_key]
                        
                except Exception as e:
                    print(f"{Colors.YELLOW}Warning: Could not load {level} config from {path}: {e}{Colors.RESET}")
                    success = False
            else:
                # Initialize empty config for non-existent files
                if level in self.config_paths:
                    self.configs[level] = {}
        
        return success
    
    def get_all_servers(self) -> List[Tuple[str, bool, Dict, str]]:
        """Get all MCP servers from all levels
        Returns: List of tuples (name, is_enabled, config, level)
        """
        servers = {}
        
        # Process configs
        for level in self.configs:
            config = self.configs[level]
            
            # Add enabled servers
            if 'mcpServers' in config:
                for name, server_config in config['mcpServers'].items():
                    # For Claude Desktop, all servers are at the same level
                    display_level = level
                    servers[f"{level}:{name}"] = (name, True, server_config, display_level)
            
            # Add disabled servers
            if level in self.disabled_servers:
                for name, server_config in self.disabled_servers[level].items():
                    servers[f"{level}:{name}"] = (name, False, server_config, level)
        
        # Convert to list and sort by name
        result = list(servers.values())
        result.sort(key=lambda x: (x[3], x[0]))  # Sort by level, then name
        return result
    
    def toggle_server(self, server_name: str, level: str = None) -> Tuple[bool, str]:
        """Toggle a server between enabled and disabled state
        Returns: (new_state, level) where new_state is True if enabled, False if disabled
        """
        # Find which level contains this server
        target_level = level
        if not target_level:
            for srv_name, _, _, srv_level in self.get_all_servers():
                if srv_name == server_name:
                    target_level = srv_level
                    break
        
        if not target_level:
            print(f"{Colors.RED}Server '{server_name}' not found{Colors.RESET}")
            return None, None
        
        config = self.configs.get(target_level, {})
        
        # Check if server is currently enabled
        if 'mcpServers' in config and server_name in config['mcpServers']:
            # Disable it
            if target_level not in self.disabled_servers:
                self.disabled_servers[target_level] = {}
            self.disabled_servers[target_level][server_name] = config['mcpServers'][server_name]
            del config['mcpServers'][server_name]
            return False, target_level
        
        # Check if server is currently disabled
        elif target_level in self.disabled_servers and server_name in self.disabled_servers[target_level]:
            # Enable it
            if 'mcpServers' not in config:
                config['mcpServers'] = {}
            config['mcpServers'][server_name] = self.disabled_servers[target_level][server_name]
            del self.disabled_servers[target_level][server_name]
            return True, target_level
        
        else:
            print(f"{Colors.RED}Server '{server_name}' not found in {target_level} config{Colors.RESET}")
            return None, None
    
    def save_config(self, level: str, create_backup: bool = True) -> bool:
        """Save configuration for a specific level"""
        if level not in self.config_paths:
            print(f"{Colors.RED}Invalid level: {level}{Colors.RESET}")
            return False
        
        path = self.config_paths[level]
        
        # Handle special case for LOCAL level (stored in user config)
        if level == ConfigLevel.LOCAL and level != ConfigLevel.DESKTOP:
            # Load the full user config
            user_path = self.config_paths.get(ConfigLevel.USER)
            if user_path and os.path.exists(user_path):
                with open(user_path, 'r') as f:
                    full_config = json.load(f)
            else:
                full_config = {}
            
            # Update the projects section
            if 'projects' not in full_config:
                full_config['projects'] = {}
            
            # Update project-specific config
            project_config = self.configs.get(ConfigLevel.LOCAL, {})
            if ConfigLevel.LOCAL in self.disabled_servers:
                project_config['_disabled_mcpServers'] = self.disabled_servers[ConfigLevel.LOCAL]
            elif '_disabled_mcpServers' in project_config:
                del project_config['_disabled_mcpServers']
            
            full_config['projects'][self.project_path] = project_config
            config_to_save = full_config
            path = user_path
        else:
            # Regular config save
            config_to_save = self.configs.get(level, {})
            
            # Add disabled servers
            if level in self.disabled_servers and self.disabled_servers[level]:
                config_to_save['_disabled_mcpServers'] = self.disabled_servers[level]
            elif '_disabled_mcpServers' in config_to_save:
                del config_to_save['_disabled_mcpServers']
        
        try:
            # Create backup if requested and file exists
            if create_backup and os.path.exists(path):
                backup_path = f"{path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(path, backup_path)
                print(f"{Colors.DIM}Backup created: {backup_path}{Colors.RESET}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
            
            # Write the config
            with open(path, 'w') as f:
                json.dump(config_to_save, f, indent=2)
            
            return True
        except Exception as e:
            print(f"{Colors.RED}Error saving {level} config: {e}{Colors.RESET}")
            return False
    
    def display_servers(self, detailed: bool = False):
        """Display all servers from all levels with their status"""
        servers = self.get_all_servers()
        
        if not servers:
            print(f"{Colors.YELLOW}No MCP servers found in any configuration{Colors.RESET}")
            print(f"\n{Colors.DIM}Checked locations:{Colors.RESET}")
            for level, path in self.config_paths.items():
                if path:
                    exists = "✓" if os.path.exists(path) else "✗"
                    color = Colors.GREEN if exists == "✓" else Colors.RED
                    print(f"  {color}{exists}{Colors.RESET} {level}: {path}")
            
            # Provide helpful hints
            print(f"\n{Colors.CYAN}Hints:{Colors.RESET}")
            if self.has_desktop:
                print(f"  • Claude Desktop detected - Add servers via the app's settings")
            if self.has_code:
                print(f"  • Claude Code detected - Use: claude mcp add <server-name>")
            return
        
        # Determine which app we're showing
        app_name = ""
        if self.app == "desktop":
            app_name = " (Claude Desktop)"
        elif self.app == "code":
            app_name = " (Claude Code)"
        elif self.app == "both":
            app_name = " (Desktop & Code)"
        
        print(f"\n{Colors.BOLD}MCP Servers{app_name}:{Colors.RESET}")
        print("-" * 80)
        
        # Group servers by level
        by_level = defaultdict(list)
        for name, is_enabled, config, level in servers:
            by_level[level].append((name, is_enabled, config))
        
        # Display by level with appropriate colors
        level_colors = {
            ConfigLevel.DESKTOP: Colors.PURPLE,
            ConfigLevel.USER: Colors.BLUE,
            ConfigLevel.PROJECT: Colors.MAGENTA,
            ConfigLevel.LOCAL: Colors.CYAN
        }
        
        # Order to display
        display_order = []
        if ConfigLevel.DESKTOP in by_level:
            display_order.append(ConfigLevel.DESKTOP)
        if ConfigLevel.LOCAL in by_level:
            display_order.append(ConfigLevel.LOCAL)
        if ConfigLevel.PROJECT in by_level:
            display_order.append(ConfigLevel.PROJECT)
        if ConfigLevel.USER in by_level:
            display_order.append(ConfigLevel.USER)
        
        for level in display_order:
            if level in by_level:
                level_color = level_colors.get(level, Colors.WHITE)
                config_path = self.config_paths.get(level, 'N/A')
                
                # Shorten path for display
                if config_path != 'N/A':
                    display_path = config_path.replace(str(Path.home()), '~')
                else:
                    display_path = config_path
                
                print(f"\n{level_color}{Colors.BOLD}[{level}]{Colors.RESET} {Colors.DIM}{display_path}{Colors.RESET}")
                
                for name, is_enabled, config in by_level[level]:
                    status_color = Colors.GREEN if is_enabled else Colors.RED
                    status_text = "✓ ENABLED " if is_enabled else "✗ DISABLED"
                    
                    print(f"  {status_color}{status_text}{Colors.RESET} {Colors.BOLD}{name}{Colors.RESET}")
                    
                    if detailed:
                        if 'command' in config:
                            print(f"    {Colors.DIM}Command: {config['command']}{Colors.RESET}")
                        if 'args' in config and config['args']:
                            args_str = ' '.join(str(arg) for arg in config['args'])
                            if len(args_str) > 60:
                                args_str = args_str[:57] + "..."
                            print(f"    {Colors.DIM}Args: {args_str}{Colors.RESET}")
                        if 'env' in config:
                            env_keys = list(config['env'].keys())
                            print(f"    {Colors.DIM}Env vars: {', '.join(env_keys)}{Colors.RESET}")
        
        # Summary
        print("\n" + "-" * 80)
        total = len(servers)
        enabled = sum(1 for _, enabled, _, _ in servers if enabled)
        disabled = total - enabled
        
        print(f"Total: {total} servers ({Colors.GREEN}{enabled} enabled{Colors.RESET}, "
              f"{Colors.RED}{disabled} disabled{Colors.RESET})")
        
        # Count by level
        level_counts = defaultdict(lambda: {'enabled': 0, 'disabled': 0})
        for _, is_enabled, _, level in servers:
            if is_enabled:
                level_counts[level]['enabled'] += 1
            else:
                level_counts[level]['disabled'] += 1
        
        if len(level_counts) > 1:
            print(f"\n{Colors.DIM}By configuration:{Colors.RESET}")
            for level in display_order:
                if level in level_counts:
                    counts = level_counts[level]
                    level_color = level_colors.get(level, Colors.WHITE)
                    total_count = counts['enabled'] + counts['disabled']
                    print(f"  {level_color}{level}:{Colors.RESET} "
                          f"{total_count} servers "
                          f"({Colors.GREEN}{counts['enabled']}{Colors.RESET}/"
                          f"{Colors.RED}{counts['disabled']}{Colors.RESET})")
    
    @staticmethod
    def scan_directory(directory: str, detailed: bool = False, max_depth: int = 2) -> None:
        """Scan a directory for all projects with MCP configurations"""
        directory = os.path.expanduser(directory)
        directory = os.path.abspath(directory)

        if not os.path.isdir(directory):
            print(f"{Colors.RED}Error: '{directory}' is not a valid directory{Colors.RESET}")
            return

        print(f"\n{Colors.BOLD}Scanning for MCP configurations{Colors.RESET}")
        print(f"{Colors.DIM}Directory: {directory}{Colors.RESET}")
        print(f"{Colors.DIM}Max depth: {max_depth}{Colors.RESET}")
        print("-" * 80)

        # Find all .mcp.json and .claude/settings.json files
        projects = []

        for root, dirs, files in os.walk(directory):
            # Calculate depth
            depth = root[len(directory):].count(os.sep)
            if depth >= max_depth:
                dirs[:] = []  # Don't descend further
                continue

            # Skip hidden directories and common non-project dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__', '.git']]

            # Check for MCP config files
            mcp_file = os.path.join(root, '.mcp.json')
            claude_settings = os.path.join(root, '.claude', 'settings.json')

            config_file = None
            if os.path.exists(mcp_file):
                config_file = mcp_file
            elif os.path.exists(claude_settings):
                config_file = claude_settings

            if config_file:
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)

                    servers = config.get('mcpServers', {})
                    server_names = list(servers.keys())

                    projects.append({
                        'name': os.path.basename(root),
                        'path': root,
                        'config_file': config_file,
                        'servers': server_names,
                        'count': len(server_names)
                    })
                except Exception as e:
                    projects.append({
                        'name': os.path.basename(root),
                        'path': root,
                        'config_file': config_file,
                        'servers': [],
                        'count': 0,
                        'error': str(e)
                    })

        if not projects:
            print(f"\n{Colors.YELLOW}No projects with MCP configurations found{Colors.RESET}")
            return

        # Sort by project name
        projects.sort(key=lambda p: p['name'].lower())

        # Collect stats
        all_servers = defaultdict(int)
        total_projects = len(projects)
        total_servers = 0

        print(f"\n{Colors.BOLD}Found {total_projects} projects with MCP configs:{Colors.RESET}\n")

        for project in projects:
            name = project['name']
            count = project['count']
            total_servers += count

            # Count server usage
            for server in project['servers']:
                all_servers[server] += 1

            # Display project
            if 'error' in project:
                print(f"📁 {Colors.RED}{name}{Colors.RESET} ({Colors.RED}error: {project['error']}{Colors.RESET})")
            else:
                color = Colors.GREEN if count > 0 else Colors.DIM
                print(f"📁 {Colors.BOLD}{name}{Colors.RESET} ({color}{count} servers{Colors.RESET})")

                if detailed and project['servers']:
                    servers_str = ', '.join(project['servers'])
                    print(f"   {Colors.DIM}└─ {servers_str}{Colors.RESET}")

        # Summary
        print("\n" + "-" * 80)
        print(f"{Colors.BOLD}Summary:{Colors.RESET}")
        print(f"  Projects: {total_projects}")
        print(f"  Total server configs: {total_servers}")

        if all_servers:
            print(f"\n{Colors.BOLD}Most common servers:{Colors.RESET}")
            sorted_servers = sorted(all_servers.items(), key=lambda x: (-x[1], x[0]))
            for server, count in sorted_servers[:10]:
                bar_len = int((count / total_projects) * 20)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                pct = int((count / total_projects) * 100)
                print(f"  {Colors.CYAN}{server:20}{Colors.RESET} {bar} {count}/{total_projects} ({pct}%)")

    def interactive_mode(self):
        """Interactive mode for toggling servers"""
        servers = self.get_all_servers()
        
        if not servers:
            print(f"{Colors.YELLOW}No MCP servers found{Colors.RESET}")
            return
        
        print(f"\n{Colors.BOLD}Interactive MCP Server Manager{Colors.RESET}")
        print("Select servers to toggle (space-separated numbers, 'q' to quit, 'a' to apply changes):\n")
        
        # Display numbered list with level indicator
        level_colors = {
            ConfigLevel.DESKTOP: Colors.PURPLE,
            ConfigLevel.USER: Colors.BLUE,
            ConfigLevel.PROJECT: Colors.MAGENTA,
            ConfigLevel.LOCAL: Colors.CYAN
        }
        
        for i, (name, is_enabled, _, level) in enumerate(servers, 1):
            status_color = Colors.GREEN if is_enabled else Colors.RED
            status = "ON " if is_enabled else "OFF"
            level_color = level_colors.get(level, Colors.WHITE)
            
            # Short level indicator
            level_abbr = {
                ConfigLevel.DESKTOP: "D",
                ConfigLevel.USER: "U",
                ConfigLevel.PROJECT: "P",
                ConfigLevel.LOCAL: "L"
            }.get(level, level[0])
            
            print(f"  {i:2}. {status_color}[{status}]{Colors.RESET} "
                  f"{level_color}[{level_abbr}]{Colors.RESET} {name}")
        
        print(f"\n{Colors.DIM}Levels: [D]esktop, [L]ocal, [P]roject, [U]ser/Global{Colors.RESET}")
        
        changes_made = defaultdict(bool)
        
        while True:
            print(f"\n{Colors.CYAN}Enter selection (numbers/q/a): {Colors.RESET}", end='')
            choice = input().strip().lower()
            
            if choice == 'q':
                if any(changes_made.values()):
                    print(f"{Colors.YELLOW}Warning: You have unsaved changes!{Colors.RESET}")
                    confirm = input("Exit without saving? (y/n): ").strip().lower()
                    if confirm == 'y':
                        break
                else:
                    break
            
            elif choice == 'a':
                if any(changes_made.values()):
                    saved_levels = []
                    for level, changed in changes_made.items():
                        if changed and self.save_config(level):
                            saved_levels.append(level)
                    
                    if saved_levels:
                        print(f"{Colors.GREEN}✓ Changes saved for: {', '.join(saved_levels)}{Colors.RESET}")
                        if ConfigLevel.DESKTOP in saved_levels:
                            print(f"{Colors.YELLOW}Restart Claude Desktop for changes to take effect{Colors.RESET}")
                        if any(level in saved_levels for level in [ConfigLevel.USER, ConfigLevel.PROJECT, ConfigLevel.LOCAL]):
                            print(f"{Colors.YELLOW}Restart Claude Code for changes to take effect{Colors.RESET}")
                        break
                    else:
                        print(f"{Colors.RED}Failed to save some changes{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}No changes to save{Colors.RESET}")
            
            else:
                # Parse numbers
                try:
                    numbers = [int(n) for n in choice.split()]
                    for num in numbers:
                        if 1 <= num <= len(servers):
                            name, was_enabled, _, level = servers[num - 1]
                            new_state, affected_level = self.toggle_server(name, level)
                            if new_state is not None:
                                state_text = "enabled" if new_state else "disabled"
                                color = Colors.GREEN if new_state else Colors.RED
                                level_color = level_colors.get(affected_level, Colors.WHITE)
                                print(f"  {color}→ {name} {state_text}{Colors.RESET} "
                                      f"{level_color}[{affected_level}]{Colors.RESET}")
                                changes_made[affected_level] = True
                                # Update local list
                                servers = self.get_all_servers()
                        else:
                            print(f"{Colors.RED}Invalid number: {num}{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}Invalid input. Enter numbers separated by spaces{Colors.RESET}")

def main():
    parser = argparse.ArgumentParser(
        description='MCP Server Manager for Claude Desktop & Claude Code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported Applications:
  • Claude Desktop - macOS/Windows/Linux GUI app
  • Claude Code - Command-line interface tool

Configuration Locations:
  Claude Desktop:
    macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
    Windows: %%APPDATA%%\\Claude\\claude_desktop_config.json
    Linux:   ~/.config/Claude/claude_desktop_config.json
  
  Claude Code:
    User:    ~/.claude.json or ~/.claude/settings.json
    Project: ./.mcp.json or ./.claude/settings.json
    Local:   Project-specific in ~/.claude.json

Examples:
  %(prog)s list                    # List all MCP servers
  %(prog)s list -d                 # List with detailed info
  %(prog)s interactive             # Interactive selection mode
  %(prog)s --app desktop list      # List only Claude Desktop servers
  %(prog)s --app code list         # List only Claude Code servers

Current directory: {cwd}
        """.format(cwd=os.getcwd())
    )
    
    parser.add_argument('--app', choices=['desktop', 'code', 'both', 'auto'],
                       default='auto',
                       help='Which app to manage (default: auto-detect)')
    parser.add_argument('-p', '--project', help='Project directory path (for Claude Code)')
    parser.add_argument('-n', '--no-backup', action='store_true', 
                       help='Don\'t create backup when saving')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all MCP servers')
    list_parser.add_argument('-d', '--detailed', action='store_true',
                            help='Show detailed information')
    
    # Toggle command
    toggle_parser = subparsers.add_parser('toggle', help='Toggle server state')
    toggle_parser.add_argument('server', help='Server name to toggle')
    
    # Interactive mode
    subparsers.add_parser('interactive', help='Interactive selection mode')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan directory for all project MCP configs')
    scan_parser.add_argument('directory', nargs='?', default='.',
                            help='Directory to scan (default: current directory)')
    scan_parser.add_argument('-d', '--detailed', action='store_true',
                            help='Show server names for each project')
    scan_parser.add_argument('--depth', type=int, default=2,
                            help='Max depth to scan (default: 2)')

    # TUI command
    tui_parser = subparsers.add_parser('tui', help='Launch interactive TUI')
    tui_parser.add_argument('directory', nargs='?', default='.',
                           help='Directory to scan (default: current directory)')
    tui_parser.add_argument('--add-dir', nargs=2, metavar=('PATH', 'MODE'),
                           help='Add directory with scan mode (all/smart)')

    # Projects command (static view)
    projects_parser = subparsers.add_parser('projects', help='List all projects with MCP info')
    projects_parser.add_argument('directory', nargs='?', default='.',
                                help='Directory to scan')
    projects_parser.add_argument('--mode', choices=['all', 'smart'], default='all',
                                help='Scan mode: all=every folder, smart=project markers only')
    projects_parser.add_argument('--depth', type=int, default=2,
                                help='Max depth to scan')

    # Servers command (static view)
    servers_parser = subparsers.add_parser('servers', help='List MCP servers by usage')
    servers_parser.add_argument('directory', nargs='?', default='.',
                               help='Directory to scan')
    servers_parser.add_argument('--mode', choices=['all', 'smart'], default='all',
                               help='Scan mode: all=every folder, smart=project markers only')
    servers_parser.add_argument('--depth', type=int, default=2,
                               help='Max depth to scan')

    args = parser.parse_args()
    
    # Initialize manager
    manager = MCPServerManager(args.project if hasattr(args, 'project') else None, args.app)
    
    # Load all configurations
    if not manager.load_all_configs():
        print(f"{Colors.YELLOW}Note: Some configuration files don't exist yet{Colors.RESET}")
    
    # Default to list if no command
    if not args.command:
        args.command = 'list'
    
    # Execute command
    if args.command == 'list':
        manager.display_servers(detailed=args.detailed if hasattr(args, 'detailed') else False)
    
    elif args.command == 'toggle':
        new_state, affected_level = manager.toggle_server(args.server)
        if new_state is not None:
            if manager.save_config(affected_level, create_backup=not args.no_backup):
                state_text = "enabled" if new_state else "disabled"
                color = Colors.GREEN if new_state else Colors.RED
                print(f"{color}✓ Server '{args.server}' {state_text} in {affected_level}{Colors.RESET}")
                if affected_level == ConfigLevel.DESKTOP:
                    print(f"{Colors.YELLOW}Restart Claude Desktop for changes to take effect{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}Restart Claude Code for changes to take effect{Colors.RESET}")
            else:
                sys.exit(1)
    
    elif args.command == 'interactive':
        manager.interactive_mode()

    elif args.command == 'scan':
        MCPServerManager.scan_directory(
            args.directory,
            detailed=args.detailed,
            max_depth=args.depth
        )

    elif args.command == 'tui':
        try:
            from mcp_tui import run_tui
            from mcp_config import load_config, save_config, add_directory

            # Handle --add-dir option
            if args.add_dir:
                config = load_config()
                path, mode = args.add_dir
                if mode not in ('all', 'smart'):
                    print(f"{Colors.RED}Error: Mode must be 'all' or 'smart'{Colors.RESET}")
                    sys.exit(1)
                add_directory(config, path, mode)
                print(f"{Colors.GREEN}✓ Added directory: {path} (mode: {mode}){Colors.RESET}")

            run_tui(args.directory)
        except ImportError as e:
            print(f"{Colors.RED}Error: TUI requires 'textual' package{Colors.RESET}")
            print(f"{Colors.YELLOW}Install with: pip install textual{Colors.RESET}")
            sys.exit(1)

    elif args.command == 'projects':
        try:
            from mcp_scanner import scan_for_overview
            from mcp_data import compute_server_usages

            projects = scan_for_overview(args.directory, args.mode, args.depth)

            print(f"\n{Colors.BOLD}Projects Overview{Colors.RESET}")
            print(f"{Colors.DIM}Directory: {os.path.abspath(args.directory)}{Colors.RESET}")
            print(f"{Colors.DIM}Mode: {args.mode}, Depth: {args.depth}{Colors.RESET}")
            print("-" * 80)

            for p in projects:
                git_icon = f"{Colors.GREEN}●{Colors.RESET}" if p.has_git else f"{Colors.DIM}○{Colors.RESET}"
                mcp_icon = f"{Colors.GREEN}●{Colors.RESET}" if p.has_mcp_config else f"{Colors.YELLOW}○{Colors.RESET}"

                if p.server_count > 0:
                    servers = f"{p.server_count} servers"
                else:
                    servers = f"{Colors.DIM}global{Colors.RESET}"

                print(f"  {git_icon} {mcp_icon} {Colors.BOLD}{p.name}{Colors.RESET} ({servers})")

                if p.servers:
                    server_names = ", ".join(s.name for s in p.servers)
                    print(f"       {Colors.DIM}└─ {server_names}{Colors.RESET}")

            print("-" * 80)
            print(f"Total: {len(projects)} projects")

        except ImportError as e:
            print(f"{Colors.RED}Error importing modules: {e}{Colors.RESET}")
            sys.exit(1)

    elif args.command == 'servers':
        try:
            from mcp_scanner import scan_for_overview
            from mcp_data import compute_server_usages

            projects = scan_for_overview(args.directory, args.mode, args.depth)
            server_usages = compute_server_usages(projects)

            print(f"\n{Colors.BOLD}MCP Servers by Usage{Colors.RESET}")
            print(f"{Colors.DIM}Directory: {os.path.abspath(args.directory)}{Colors.RESET}")
            print("-" * 80)

            if not server_usages:
                print(f"{Colors.YELLOW}No MCP servers found in scanned projects{Colors.RESET}")
            else:
                max_usage = max(s.usage_count for s in server_usages)

                for s in server_usages:
                    bar_len = int((s.usage_count / max_usage) * 15) if max_usage > 0 else 0
                    bar = f"{Colors.GREEN}{'█' * bar_len}{Colors.RESET}{Colors.DIM}{'░' * (15 - bar_len)}{Colors.RESET}"

                    projects_preview = ", ".join(p.name for p in s.projects[:3])
                    if len(s.projects) > 3:
                        projects_preview += f" +{len(s.projects) - 3}"

                    print(f"  {Colors.CYAN}{s.name:20}{Colors.RESET} {bar} {s.usage_count:2}/{len(projects)}")
                    print(f"       {Colors.DIM}└─ {projects_preview}{Colors.RESET}")

            print("-" * 80)
            print(f"Total: {len(server_usages)} unique servers across {len(projects)} projects")

        except ImportError as e:
            print(f"{Colors.RED}Error importing modules: {e}{Colors.RESET}")
            sys.exit(1)

if __name__ == '__main__':
    main()