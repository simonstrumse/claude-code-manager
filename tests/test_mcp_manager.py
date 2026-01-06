"""
Test suite for MCP Server Manager
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
import sys

# Add the parent directory to the path to import mcp_manager
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mcp_manager import MCPServerManager
except ImportError:
    # If running as a package, try this import
    import mcp_manager
    MCPServerManager = mcp_manager.MCPServerManager


class TestMCPServerManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, '.claude.json')
        
        # Create a sample config
        self.sample_config = {
            "mcpServers": {
                "test-server-1": {
                    "command": "node",
                    "args": ["server1.js"]
                },
                "test-server-2": {
                    "command": "python",
                    "args": ["server2.py"],
                    "env": {"API_KEY": "test123"}
                }
            },
            "otherConfig": "preserved"
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(self.sample_config, f)
        
        self.manager = MCPServerManager(self.config_path)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_config(self):
        """Test loading configuration"""
        self.assertTrue(self.manager.load_config())
        self.assertIn('mcpServers', self.manager.config)
        self.assertEqual(len(self.manager.config['mcpServers']), 2)
    
    def test_get_all_servers(self):
        """Test getting all servers"""
        self.manager.load_config()
        servers = self.manager.get_all_servers()
        self.assertEqual(len(servers), 2)
        
        # Check server details
        server_names = [name for name, _, _ in servers]
        self.assertIn('test-server-1', server_names)
        self.assertIn('test-server-2', server_names)
    
    def test_disable_server(self):
        """Test disabling a server"""
        self.manager.load_config()
        
        # Disable a server
        result = self.manager.disable_server('test-server-1')
        self.assertTrue(result)
        
        # Check it's moved to disabled
        self.assertNotIn('test-server-1', self.manager.config['mcpServers'])
        self.assertIn('test-server-1', self.manager.disabled_servers)
        
        # Verify configuration is preserved
        disabled_config = self.manager.disabled_servers['test-server-1']
        self.assertEqual(disabled_config['command'], 'node')
        self.assertEqual(disabled_config['args'], ['server1.js'])
    
    def test_enable_server(self):
        """Test enabling a disabled server"""
        self.manager.load_config()
        
        # First disable a server
        self.manager.disable_server('test-server-1')
        
        # Then enable it
        result = self.manager.enable_server('test-server-1')
        self.assertTrue(result)
        
        # Check it's back in enabled
        self.assertIn('test-server-1', self.manager.config['mcpServers'])
        self.assertNotIn('test-server-1', self.manager.disabled_servers)
    
    def test_toggle_server(self):
        """Test toggling server state"""
        self.manager.load_config()
        
        # Toggle from enabled to disabled
        result = self.manager.toggle_server('test-server-1')
        self.assertFalse(result)  # Returns False when disabled
        self.assertNotIn('test-server-1', self.manager.config['mcpServers'])
        
        # Toggle back to enabled
        result = self.manager.toggle_server('test-server-1')
        self.assertTrue(result)  # Returns True when enabled
        self.assertIn('test-server-1', self.manager.config['mcpServers'])
    
    def test_save_config(self):
        """Test saving configuration"""
        self.manager.load_config()
        
        # Make a change
        self.manager.disable_server('test-server-1')
        
        # Save without backup
        result = self.manager.save_config(create_backup=False)
        self.assertTrue(result)
        
        # Load the saved config
        with open(self.config_path, 'r') as f:
            saved_config = json.load(f)
        
        # Verify changes were saved
        self.assertNotIn('test-server-1', saved_config.get('mcpServers', {}))
        self.assertIn('_disabled_mcpServers', saved_config)
        self.assertIn('test-server-1', saved_config['_disabled_mcpServers'])
        
        # Verify other config is preserved
        self.assertEqual(saved_config['otherConfig'], 'preserved')
    
    def test_save_config_with_backup(self):
        """Test saving configuration with backup"""
        self.manager.load_config()
        
        # Save with backup
        result = self.manager.save_config(create_backup=True)
        self.assertTrue(result)
        
        # Check backup was created
        backup_files = list(Path(self.temp_dir).glob('*.backup.*'))
        self.assertEqual(len(backup_files), 1)
    
    def test_nonexistent_server(self):
        """Test operations on non-existent servers"""
        self.manager.load_config()
        
        # Try to disable non-existent server
        result = self.manager.disable_server('non-existent')
        self.assertFalse(result)
        
        # Try to enable non-existent server
        result = self.manager.enable_server('non-existent')
        self.assertFalse(result)
        
        # Try to toggle non-existent server
        result = self.manager.toggle_server('non-existent')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()