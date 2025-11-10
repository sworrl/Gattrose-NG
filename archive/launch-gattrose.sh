#!/bin/bash
#
# Gattrose-NG Desktop Launcher
# This script launches Gattrose-NG with proper terminal and sudo
#

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to project directory
cd "$SCRIPT_DIR"

# Launch in terminal with sudo
x-terminal-emulator -e sudo ./gattrose-ng.py
