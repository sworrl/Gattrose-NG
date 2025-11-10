#!/bin/bash
#
# Gattrose-NG Smart Launcher
# Intelligently chooses between system install and development version
#

# Color output for terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory of this script (dev installation)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_ROOT="$(dirname "$SCRIPT_DIR")"

# System installation paths
SYSTEM_ROOT="/opt/gattrose-ng"
SYSTEM_BIN="/usr/local/bin/gattrose-ng"

# Version comparison
get_version() {
    local version_file="$1/VERSION"
    if [ -f "$version_file" ]; then
        cat "$version_file"
    else
        echo "unknown"
    fi
}

# Check if system installation exists and is functional
check_system_install() {
    [ -d "$SYSTEM_ROOT" ] && [ -f "$SYSTEM_ROOT/src/main.py" ]
}

# Check if first run (no database exists)
is_first_run() {
    [ ! -f "/opt/gattrose-ng/data/database/gattrose.db" ] && \
    [ ! -f "$DEV_ROOT/data/database/gattrose.db" ]
}

# Main launcher logic
launch_gattrose() {
    local use_system=false
    local project_root="$DEV_ROOT"

    # Check for system installation
    if check_system_install; then
        local sys_version=$(get_version "$SYSTEM_ROOT")
        local dev_version=$(get_version "$DEV_ROOT")

        echo -e "${BLUE}[i] System install found: v${sys_version}${NC}"
        echo -e "${BLUE}[i] Dev version: v${dev_version}${NC}"

        # Prefer system install if it exists
        if [ "$sys_version" != "unknown" ]; then
            use_system=true
            project_root="$SYSTEM_ROOT"
            echo -e "${GREEN}[+] Using system installation${NC}"
        else
            echo -e "${YELLOW}[!] System install invalid, using dev version${NC}"
        fi
    else
        echo -e "${YELLOW}[i] No system installation found${NC}"
        echo -e "${BLUE}[i] Running from development directory${NC}"
    fi

    # Check for first run
    if is_first_run; then
        echo -e "${YELLOW}[*] First run detected - database will be initialized${NC}"
    fi

    # Set up environment
    export DISPLAY="${DISPLAY:-:1}"
    export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
    export QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --single-process"
    export QTWEBENGINE_DISABLE_SANDBOX=1

    # Handle pkexec/sudo execution
    if [ -n "$PKEXEC_UID" ]; then
        REAL_USER=$(id -nu "$PKEXEC_UID")
        REAL_HOME=$(eval echo ~"$REAL_USER")
    else
        REAL_USER="${SUDO_USER:-$USER}"
        REAL_HOME="${HOME}"
    fi

    # Set up X11 authentication
    if [ "$XDG_SESSION_TYPE" = "x11" ] || [ -z "$XDG_SESSION_TYPE" ]; then
        if [ -n "$XAUTHORITY" ] && [ -f "$XAUTHORITY" ]; then
            :
        elif [ -f "$REAL_HOME/.Xauthority" ]; then
            export XAUTHORITY="$REAL_HOME/.Xauthority"
        else
            export XAUTHORITY="/run/user/$(id -u "$REAL_USER")/gdm/Xauthority"
        fi
    fi

    # Set XDG runtime directory
    if [ -z "$XDG_RUNTIME_DIR" ] || [ ! -d "$XDG_RUNTIME_DIR" ]; then
        export XDG_RUNTIME_DIR="/run/user/$(id -u "$REAL_USER")"
    fi

    # Change to project directory and launch
    cd "$project_root" || {
        echo -e "${RED}[!] Failed to change to $project_root${NC}"
        exit 1
    }

    # Check for virtual environment
    if [ ! -f "$project_root/.venv/bin/python" ]; then
        echo -e "${RED}[!] Virtual environment not found!${NC}"
        echo -e "${YELLOW}[i] Please run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt${NC}"
        exit 1
    fi

    echo -e "${GREEN}[*] Launching Gattrose-NG GUI from: $project_root${NC}"
    exec "$project_root/.venv/bin/python" "$project_root/src/main.py"
}

# Run the launcher
launch_gattrose
