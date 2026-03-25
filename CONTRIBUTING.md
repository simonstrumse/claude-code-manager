# Contributing to Claude Code Manager

Thanks for your interest in contributing! PRs, bug reports, and feature requests are all welcome.

## Getting Started

### Prerequisites

- Python >= 3.8
- pip or uv

### Development Setup

```bash
git clone https://github.com/simonstrumse/claude-code-manager.git
cd claude-code-manager
pip install -e ".[dev]"
```

Or with uv:

```bash
uv pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Style

This project uses [Black](https://black.readthedocs.io/) for formatting:

```bash
black .
```

## Making Changes

1. **Fork the repo** and create a branch from `main`
2. **Make your changes** — keep commits focused
3. **Add tests** for new functionality
4. **Format your code** with Black
5. **Run tests** — `pytest`
6. **Open a pull request** against `main`

## Project Structure

```
ccmanager/
  mcp_tui.py           # Main TUI application (Textual)
  mcp_scanner.py        # File scanning and discovery
  mcp_data.py           # Data models
  mcp_config.py         # Configuration management
  mcp_operations.py     # File/project operations
  claude_mcp_detector.py # MCP server detection
  tests/                # Test suite
```

## What to Contribute

- **New tab views** — extend the TUI with additional Claude Code configuration views
- **Bug fixes** — especially cross-platform compatibility (macOS, Linux, Windows)
- **Scanner improvements** — better detection of MCP servers and configurations
- **Documentation** — usage examples, screenshots, tutorials
- **Tests** — improve coverage

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
