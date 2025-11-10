#!/bin/bash
#
# Gattrose-NG Desktop Launcher
# Simple launcher with sudo elevation and error handling
#

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    # Already root, show error
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Gattrose-NG Launcher Error" --text="This launcher should NOT be run as root.\n\nPlease run it as a regular user - it will ask for your password when needed." --width=400
    elif command -v kdialog >/dev/null 2>&1; then
        kdialog --error "This launcher should NOT be run as root.\n\nPlease run it as a regular user - it will ask for your password when needed."
    else
        echo "ERROR: This launcher should NOT be run as root."
        echo "Please run it as a regular user - it will ask for your password when needed."
        sleep 5
    fi
    exit 1
fi

# Launch in a terminal with sudo
if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal -- bash -c "cd '$PROJECT_ROOT' && sudo '$PROJECT_ROOT/gattrose-ng.py'; exec bash"
elif command -v xterm >/dev/null 2>&1; then
    xterm -hold -e "cd '$PROJECT_ROOT' && sudo '$PROJECT_ROOT/gattrose-ng.py'"
elif command -v konsole >/dev/null 2>&1; then
    konsole --hold -e bash -c "cd '$PROJECT_ROOT' && sudo '$PROJECT_ROOT/gattrose-ng.py'"
else
    # Fallback: show error about no terminal
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="No Terminal Found" --text="Could not find a terminal emulator.\n\nPlease install one of:\n• gnome-terminal\n• xterm\n• konsole\n\nOr run from command line:\nsudo $PROJECT_ROOT/gattrose-ng.py" --width=400
    else
        echo "ERROR: No terminal emulator found."
        echo "Please install gnome-terminal, xterm, or konsole"
        echo "Or run from command line: sudo $PROJECT_ROOT/gattrose-ng.py"
        sleep 10
    fi
    exit 1
fi
