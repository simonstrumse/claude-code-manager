#!/bin/bash
#
# Pre-push hook: Auto-publish to PyPI when version changes
#
# This hook compares the local version in pyproject.toml with the
# published version on PyPI. If local is newer, it builds and uploads.
#

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[pre-push]${NC} Checking PyPI publish status..."

# Get local version from pyproject.toml
LOCAL_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

if [ -z "$LOCAL_VERSION" ]; then
    echo -e "${RED}[pre-push]${NC} Could not read version from pyproject.toml"
    exit 0  # Don't block push
fi

echo -e "${YELLOW}[pre-push]${NC} Local version: $LOCAL_VERSION"

# Get PyPI version (returns empty if package doesn't exist or network error)
PYPI_VERSION=$(curl -s "https://pypi.org/pypi/ccmanager/json" 2>/dev/null | grep -o '"version":"[^"]*"' | head -1 | sed 's/"version":"\(.*\)"/\1/' || echo "")

if [ -z "$PYPI_VERSION" ]; then
    echo -e "${YELLOW}[pre-push]${NC} Could not fetch PyPI version (network issue or new package)"
    PYPI_VERSION="0.0.0"
fi

echo -e "${YELLOW}[pre-push]${NC} PyPI version: $PYPI_VERSION"

# Compare versions (simple string comparison works for semver)
if [ "$LOCAL_VERSION" = "$PYPI_VERSION" ]; then
    echo -e "${YELLOW}[pre-push]${NC} Versions match - skipping PyPI publish"
    echo -e "${YELLOW}[pre-push]${NC} To publish, bump version in pyproject.toml first"
    exit 0
fi

# Check if local is newer using version sorting
NEWER=$(printf '%s\n%s' "$LOCAL_VERSION" "$PYPI_VERSION" | sort -V | tail -1)

if [ "$NEWER" != "$LOCAL_VERSION" ]; then
    echo -e "${YELLOW}[pre-push]${NC} Local version ($LOCAL_VERSION) is older than PyPI ($PYPI_VERSION)"
    echo -e "${YELLOW}[pre-push]${NC} Skipping publish - update your version first"
    exit 0
fi

echo -e "${GREEN}[pre-push]${NC} Local version is newer - publishing to PyPI..."

# Check for PyPI token
TOKEN_FILE="$REPO_ROOT/.pypi-token"
if [ ! -f "$TOKEN_FILE" ]; then
    echo -e "${RED}[pre-push]${NC} No .pypi-token file found"
    echo -e "${RED}[pre-push]${NC} Create $TOKEN_FILE with your PyPI API token"
    exit 0  # Don't block push, just skip publish
fi

PYPI_TOKEN=$(cat "$TOKEN_FILE" | tr -d '\n')

# Check for build tools
if ! command -v pyproject-build &> /dev/null; then
    echo -e "${YELLOW}[pre-push]${NC} Installing build tools..."
    uv tool install build 2>/dev/null || pip install build --quiet
fi

if ! command -v twine &> /dev/null; then
    echo -e "${YELLOW}[pre-push]${NC} Installing twine..."
    uv tool install twine 2>/dev/null || pip install twine --quiet
fi

# Clean and build
echo -e "${GREEN}[pre-push]${NC} Building package..."
rm -rf dist/ build/ *.egg-info
pyproject-build --quiet 2>/dev/null || pyproject-build

# Upload to PyPI
echo -e "${GREEN}[pre-push]${NC} Uploading to PyPI..."
if twine upload dist/* -u __token__ -p "$PYPI_TOKEN" 2>&1 | grep -q "View at"; then
    echo -e "${GREEN}[pre-push]${NC} Successfully published ccmanager $LOCAL_VERSION to PyPI!"
else
    echo -e "${RED}[pre-push]${NC} PyPI upload may have failed - check https://pypi.org/project/ccmanager/"
fi

exit 0
