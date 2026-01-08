#!/bin/bash
#
# Setup script: Install git hooks for auto-publishing
#
# Run this after cloning the repo to enable auto-publish to PyPI
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Setting up git hooks..."

# Copy pre-push hook
cp "$SCRIPT_DIR/pre-push-hook.sh" "$REPO_ROOT/.git/hooks/pre-push"
chmod +x "$REPO_ROOT/.git/hooks/pre-push"

echo "Installed pre-push hook"

# Check for .pypi-token
if [ ! -f "$REPO_ROOT/.pypi-token" ]; then
    echo ""
    echo "IMPORTANT: Create .pypi-token file with your PyPI API token:"
    echo "  1. Go to https://pypi.org/manage/account/token/"
    echo "  2. Create a token scoped to 'ccmanager' project"
    echo "  3. Save it to: $REPO_ROOT/.pypi-token"
    echo ""
    echo "Without this, the hook will skip publishing."
fi

echo "Done! The pre-push hook will auto-publish when you bump the version."
