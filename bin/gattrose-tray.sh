#!/bin/bash
#
# Gattrose-NG System Tray Launcher
# Starts the standalone system tray application
#

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Launch tray app
cd "$PROJECT_ROOT" || exit 1
exec "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/src/tray_app.py"
