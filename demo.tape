# VHS Demo Tape for Claude Code Manager
# Run: vhs demo.tape

Output screenshots/demo.gif

Set Shell bash
Set FontSize 13
Set Width 1400
Set Height 850
Set Padding 16
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms
Set PlaybackSpeed 0.5
Set WindowBar Colorful
Set BorderRadius 8

# Launch ccmanager via wrapper that sets up PATH
Type "bash scripts/demo-run.sh"
Enter
Sleep 4s

# Show Projects tab (default) — browse projects
Down
Sleep 300ms
Down
Sleep 300ms
Down
Sleep 300ms
Down
Sleep 300ms
Down
Sleep 1s

# Switch to MCP Servers tab
Type "2"
Sleep 2s

# Navigate servers
Down
Sleep 300ms
Down
Sleep 300ms
Down
Sleep 1s

# Switch to Skills tab
Type "3"
Sleep 2s

Down
Sleep 300ms
Down
Sleep 1s

# Switch to Commands tab
Type "4"
Sleep 2s

# Switch to CLAUDE.md tab
Type "6"
Sleep 2s

# Back to Projects
Type "1"
Sleep 1.5s

# Quit
Type "q"
Sleep 1s
