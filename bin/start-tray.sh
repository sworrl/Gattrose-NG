#!/bin/bash
# Start Gattrose-NG System Tray Icon

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Use virtual environment Python
PYTHON="$PROJECT_ROOT/.venv/bin/python"

echo "[*] Starting Gattrose-NG System Tray..."
"$PYTHON" "$PROJECT_ROOT/src/tray_app.py" "$@"
