#!/bin/bash
#
# Gattrose-NG Direct Launcher
# Ultra-simple sudo launcher
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT" || exit 1
sudo "$PROJECT_ROOT/gattrose-ng.py"
