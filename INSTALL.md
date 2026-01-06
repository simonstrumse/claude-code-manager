# 🚀 Global Installation Guide for MCP Manager

## Quick Install (macOS/Linux)

```bash
# Clone or navigate to your MCP_Manager directory
cd ~/Projects/MCP_Manager

# Make the install script executable
chmod +x install.sh

# Run the installer
./install.sh
```

After installation, you can use these commands from **ANY directory**:
- `mcp list` - List all MCP servers
- `mcpm list` - Same (shorter alias)
- `mcp-manager list` - Same (full name)

## Manual Installation

### Option 1: Add to PATH (Recommended)

```bash
# Copy the script to a directory in your PATH
sudo cp mcp_manager.py /usr/local/bin/mcp-manager
sudo chmod +x /usr/local/bin/mcp-manager

# Create shorter aliases
sudo ln -s /usr/local/bin/mcp-manager /usr/local/bin/mcp
sudo ln -s /usr/local/bin/mcp-manager /usr/local/bin/mcpm
```

### Option 2: Create an Alias

Add this to your `~/.zshrc` or `~/.bashrc`:

```bash
alias mcp='python3 ~/Projects/MCP_Manager/mcp_manager.py'
alias mcpm='python3 ~/Projects/MCP_Manager/mcp_manager.py'
```

Then reload your shell:
```bash
source ~/.zshrc  # or ~/.bashrc
```

## 🔍 Finding MCP Servers in Any Project

Once installed globally, you can check MCP servers from any project:

```bash
# Navigate to any project
cd ~/Projects/YourProject

# See what MCP servers are available here
mcp list

# Use the detector to find WHERE servers come from
python3 ~/Projects/MCP_Manager/claude_mcp_detector.py
```

## 📊 Understanding MCP Server Sources

Claude Code loads MCP servers from multiple locations in **priority order**:

1. **Project Local** (`.claude/settings.local.json`) - Highest priority
2. **Project Settings** (`.claude/settings.json`) 
3. **Project MCP** (`.mcp.json`)
4. **Project in Global** (project-specific section in `~/.claude.json`)
5. **User Settings** (`~/.claude/settings.json`)
6. **Global** (`~/.claude.json`) - Lowest priority

## 🎯 Usage in Any Project

### Check Current Project's MCP Servers
```bash
cd /path/to/your/project
mcp list
```

### Find WHERE servers are configured
```bash
cd /path/to/your/project
python3 ~/Projects/MCP_Manager/claude_mcp_detector.py
```

### Interactive Management
```bash
cd /path/to/your/project
mcp interactive
```

### See What Claude Code Actually Sees
```bash
# Start Claude Code
claude

# Inside Claude Code, type:
/mcp

# Compare with what mcp-manager shows:
# In another terminal in same directory:
mcp list
```

## 🔧 Troubleshooting

### "Command not found"
- Make sure `/usr/local/bin` is in your PATH
- Or use the full path: `/usr/local/bin/mcp list`

### Different servers in Claude Code vs mcp-manager
- Claude Code merges servers from multiple sources
- Use `claude_mcp_detector.py` to see all sources
- Higher priority configs override lower ones

### Permission denied
```bash
# Use sudo for system directories
sudo cp mcp_manager.py /usr/local/bin/mcp-manager

# Or install in user directory
mkdir -p ~/.local/bin
cp mcp_manager.py ~/.local/bin/mcp-manager
# Add ~/.local/bin to your PATH
```

## 📝 Project-Specific MCP Servers

To add MCP servers for a specific project:

### Method 1: Using Claude Code CLI
```bash
cd /path/to/project
claude mcp add github --scope local
```

### Method 2: Create .mcp.json
```bash
cd /path/to/project
cat > .mcp.json << 'EOF'
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token"
      }
    }
  }
}
EOF
```

### Method 3: Edit with mcp-manager
```bash
cd /path/to/project
mcp interactive
```

## 🎨 Pro Tips

1. **Check active servers in Claude Code:**
   ```bash
   claude mcp list
   ```

2. **See all configuration sources:**
   ```bash
   python3 ~/Projects/MCP_Manager/claude_mcp_detector.py
   ```

3. **Compare Desktop vs Code servers:**
   ```bash
   mcp --app desktop list  # Claude Desktop servers
   mcp --app code list     # Claude Code servers
   ```

4. **Quick toggle servers:**
   ```bash
   mcp toggle github
   ```

Remember: After changing MCP configurations, restart Claude Code for changes to take effect!