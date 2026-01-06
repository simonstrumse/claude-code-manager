#!/usr/bin/env python3
"""
Claude Code MCP Detector
Finds all MCP servers available in the current Claude Code instance
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class ClaudeMCPDetector:
    def __init__(self):
        self.project_path = os.getcwd()
        self.home = Path.home()
        
    def find_all_mcp_sources(self) -> Dict[str, Any]:
        """Find all possible MCP server sources for current project"""
        sources = {}
        
        # 1. Check global user config (~/.claude.json)
        global_config = self.home / '.claude.json'
        if global_config.exists():
            try:
                with open(global_config) as f:
                    data = json.load(f)
                    
                    # Check for global mcpServers
                    if 'mcpServers' in data:
                        sources['global'] = {
                            'path': str(global_config),
                            'servers': data['mcpServers']
                        }
                    
                    # Check for project-specific config
                    if 'projects' in data:
                        for proj_path, proj_config in data['projects'].items():
                            if self.project_path.startswith(proj_path):
                                if 'mcpServers' in proj_config:
                                    sources['project_in_global'] = {
                                        'path': f"{global_config} (project: {proj_path})",
                                        'servers': proj_config['mcpServers']
                                    }
            except Exception as e:
                print(f"Error reading {global_config}: {e}")
        
        # 2. Check project-level .mcp.json
        project_mcp = Path(self.project_path) / '.mcp.json'
        if project_mcp.exists():
            try:
                with open(project_mcp) as f:
                    data = json.load(f)
                    if 'mcpServers' in data:
                        sources['project_mcp'] = {
                            'path': str(project_mcp),
                            'servers': data['mcpServers']
                        }
            except Exception as e:
                print(f"Error reading {project_mcp}: {e}")
        
        # 3. Check .claude/settings.json in project
        project_claude_settings = Path(self.project_path) / '.claude' / 'settings.json'
        if project_claude_settings.exists():
            try:
                with open(project_claude_settings) as f:
                    data = json.load(f)
                    if 'mcpServers' in data:
                        sources['project_claude'] = {
                            'path': str(project_claude_settings),
                            'servers': data['mcpServers']
                        }
            except Exception as e:
                print(f"Error reading {project_claude_settings}: {e}")
        
        # 4. Check .claude/settings.local.json in project
        project_claude_local = Path(self.project_path) / '.claude' / 'settings.local.json'
        if project_claude_local.exists():
            try:
                with open(project_claude_local) as f:
                    data = json.load(f)
                    if 'mcpServers' in data:
                        sources['project_local'] = {
                            'path': str(project_claude_local),
                            'servers': data['mcpServers']
                        }
            except Exception as e:
                print(f"Error reading {project_claude_local}: {e}")
        
        # 5. Check user-level ~/.claude/settings.json
        user_claude_settings = self.home / '.claude' / 'settings.json'
        if user_claude_settings.exists():
            try:
                with open(user_claude_settings) as f:
                    data = json.load(f)
                    if 'mcpServers' in data:
                        sources['user_settings'] = {
                            'path': str(user_claude_settings),
                            'servers': data['mcpServers']
                        }
            except Exception as e:
                print(f"Error reading {user_claude_settings}: {e}")
        
        return sources
    
    def get_active_mcp_list(self) -> List[str]:
        """Try to get the actual MCP list from claude CLI"""
        try:
            result = subprocess.run(
                ['claude', 'mcp', 'list'],
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            
            if result.returncode == 0:
                output = result.stdout
                # Parse the output to extract server names
                servers = []
                for line in output.split('\n'):
                    if '•' in line or '-' in line:
                        # Extract server name from lines like "• server-name: connected"
                        parts = line.split(':')
                        if parts:
                            server_name = parts[0].strip().replace('•', '').replace('-', '').strip()
                            if server_name:
                                servers.append(server_name)
                return servers
            else:
                return []
        except Exception:
            return []
    
    def display_findings(self):
        """Display all MCP server sources found"""
        from mcp_manager import Colors  # Import colors from main script
        
        sources = self.find_all_mcp_sources()
        active_servers = self.get_active_mcp_list()
        
        print(f"\n{Colors.BOLD}MCP Server Detection for: {self.project_path}{Colors.RESET}")
        print("=" * 80)
        
        if not sources:
            print(f"{Colors.YELLOW}No MCP server configurations found{Colors.RESET}")
            return
        
        # Display each source
        all_servers = {}
        for source_name, source_data in sources.items():
            path = source_data['path']
            servers = source_data['servers']
            
            # Make path relative to home for readability
            display_path = path.replace(str(self.home), '~')
            
            print(f"\n{Colors.CYAN}{Colors.BOLD}Source: {source_name}{Colors.RESET}")
            print(f"{Colors.DIM}Path: {display_path}{Colors.RESET}")
            
            for server_name, server_config in servers.items():
                all_servers[server_name] = source_name
                
                # Check if this server is active
                is_active = server_name in active_servers
                status_color = Colors.GREEN if is_active else Colors.YELLOW
                status = "✓ ACTIVE" if is_active else "○ CONFIGURED"
                
                print(f"  {status_color}{status}{Colors.RESET} {Colors.BOLD}{server_name}{Colors.RESET}")
                
                if 'command' in server_config:
                    print(f"    {Colors.DIM}Command: {server_config['command']}{Colors.RESET}")
        
        # Summary
        print("\n" + "-" * 80)
        print(f"{Colors.BOLD}Summary:{Colors.RESET}")
        print(f"  Total configured servers: {len(all_servers)}")
        print(f"  Active in Claude Code: {len(active_servers)}")
        print(f"  Configuration sources: {len(sources)}")
        
        # Show priority order
        print(f"\n{Colors.YELLOW}Priority (highest to lowest):{Colors.RESET}")
        print(f"  1. Project .claude/settings.local.json")
        print(f"  2. Project .claude/settings.json")
        print(f"  3. Project .mcp.json")
        print(f"  4. Project-specific in ~/.claude.json")
        print(f"  5. User ~/.claude/settings.json")
        print(f"  6. Global ~/.claude.json")
        
        # Try to show actual Claude Code status
        print(f"\n{Colors.BOLD}Claude Code Status:{Colors.RESET}")
        try:
            result = subprocess.run(
                ['claude', 'mcp', 'list'],
                capture_output=True,
                text=True,
                cwd=self.project_path
            )
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(f"{Colors.DIM}Could not get Claude Code MCP status{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.DIM}Claude Code not running or not accessible: {e}{Colors.RESET}")

if __name__ == '__main__':
    detector = ClaudeMCPDetector()
    detector.display_findings()