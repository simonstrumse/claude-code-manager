#!/bin/bash

# MCP Manager Global Installation Script
# This script installs mcp-manager globally so you can use it from any project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}MCP Manager - Global Installation${NC}"
echo "========================================"

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE=Linux;;
    Darwin*)    OS_TYPE=Mac;;
    CYGWIN*)    OS_TYPE=Windows;;
    MINGW*)     OS_TYPE=Windows;;
    *)          OS_TYPE="UNKNOWN:${OS}"
esac

echo -e "${GREEN}Detected OS: ${OS_TYPE}${NC}"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Get Python version (compatible with macOS)
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
echo -e "${GREEN}Python version: ${PYTHON_VERSION}${NC}"

# Determine installation directory
if [[ "$OS_TYPE" == "Mac" ]] || [[ "$OS_TYPE" == "Linux" ]]; then
    # Check if user has write access to /usr/local/bin
    if [[ -w "/usr/local/bin" ]]; then
        INSTALL_DIR="/usr/local/bin"
    else
        # Fall back to user's local bin
        INSTALL_DIR="$HOME/.local/bin"
        mkdir -p "$INSTALL_DIR"
        
        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
            echo -e "${YELLOW}Adding $INSTALL_DIR to PATH...${NC}"
            
            # Detect shell and add to appropriate config file
            if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == *"zsh"* ]]; then
                echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> ~/.zshrc
                echo -e "${GREEN}Added to ~/.zshrc${NC}"
            elif [[ -n "$BASH_VERSION" ]] || [[ "$SHELL" == *"bash"* ]]; then
                echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> ~/.bashrc
                echo -e "${GREEN}Added to ~/.bashrc${NC}"
            fi
            
            echo -e "${YELLOW}Please restart your terminal or run: source ~/.zshrc (or ~/.bashrc)${NC}"
        fi
    fi
else
    echo -e "${RED}Windows installation not yet supported via this script${NC}"
    echo "Please copy mcp_manager.py to a directory in your PATH manually"
    exit 1
fi

echo -e "${GREEN}Installation directory: ${INSTALL_DIR}${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if mcp_manager.py exists
if [[ ! -f "$SCRIPT_DIR/mcp_manager.py" ]]; then
    echo -e "${RED}Error: mcp_manager.py not found in $SCRIPT_DIR${NC}"
    exit 1
fi

# Copy the Python script
echo -e "${BLUE}Installing mcp_manager.py...${NC}"
cp "$SCRIPT_DIR/mcp_manager.py" "$INSTALL_DIR/mcp-manager.py"
chmod +x "$INSTALL_DIR/mcp-manager.py"

# Create a wrapper script that ensures Python 3 is used
cat > "$INSTALL_DIR/mcp-manager" << 'EOF'
#!/bin/bash
# MCP Manager wrapper script
exec python3 "$(dirname "$0")/mcp-manager.py" "$@"
EOF

chmod +x "$INSTALL_DIR/mcp-manager"

# Also create shorter aliases
ln -sf "$INSTALL_DIR/mcp-manager" "$INSTALL_DIR/mcpm" 2>/dev/null || true
ln -sf "$INSTALL_DIR/mcp-manager" "$INSTALL_DIR/mcp" 2>/dev/null || true

echo -e "${GREEN}✓ Installation complete!${NC}"
echo ""
echo -e "${BLUE}You can now use any of these commands from any directory:${NC}"
echo "  mcp-manager list     # List all MCP servers"
echo "  mcpm list           # Short alias"
echo "  mcp list            # Even shorter alias"
echo ""
echo -e "${BLUE}Usage examples:${NC}"
echo "  mcp list            # List all MCP servers in current project"
echo "  mcp interactive     # Interactive mode"
echo "  mcp list -d         # Detailed view"
echo "  mcp --help          # Show all options"
echo ""
echo -e "${YELLOW}Tip: Run 'mcp list' in any project directory to see its MCP servers!${NC}"

# Test the installation
echo ""
echo -e "${BLUE}Testing installation...${NC}"
if "$INSTALL_DIR/mcp-manager" --help > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Installation verified successfully!${NC}"
else
    echo -e "${RED}✗ Installation test failed${NC}"
    exit 1
fi