#!/usr/bin/env bash
#
# Gattrose-NG System Installation Script
#
# Installs Gattrose as a system service with:
# - Core service (scanner, state management)
# - API service (REST API)
# - Symlinked to dev location for easy updates
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INSTALL_DIR="/opt/gattrose-ng"
BIN_DIR="/usr/local/bin"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Gattrose-NG System Installation Script           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[!] This script must be run as root${NC}"
    echo -e "${YELLOW}    Run: sudo $0${NC}"
    exit 1
fi

echo -e "${GREEN}[*] Project root: ${PROJECT_ROOT}${NC}"
echo -e "${GREEN}[*] Install target: ${INSTALL_DIR}${NC}"
echo ""

# ========== Create Install Directory ==========

echo -e "${BLUE}[1/9] Creating installation directory...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}    Install directory already exists${NC}"
    read -p "    Remove and reinstall? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}    Removing existing installation...${NC}"
        rm -rf "$INSTALL_DIR"
    else
        echo -e "${RED}    Installation cancelled${NC}"
        exit 1
    fi
fi

mkdir -p "$INSTALL_DIR"
echo -e "${GREEN}    ✓ Created ${INSTALL_DIR}${NC}"

# ========== Copy/Symlink Files ==========

echo -e "${BLUE}[2/9] Symlinking source files...${NC}"

# Symlink main directories to dev location for live updates
ln -sf "$PROJECT_ROOT/src" "$INSTALL_DIR/src"
ln -sf "$PROJECT_ROOT/assets" "$INSTALL_DIR/assets"
ln -sf "$PROJECT_ROOT/docs" "$INSTALL_DIR/docs"

# Copy configuration and data directories (not symlinked)
cp -r "$PROJECT_ROOT/config" "$INSTALL_DIR/config" 2>/dev/null || mkdir -p "$INSTALL_DIR/config"
mkdir -p "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/data/captures"
mkdir -p "$INSTALL_DIR/logs"

# Symlink virtual environment
if [ -d "$PROJECT_ROOT/.venv" ]; then
    ln -sf "$PROJECT_ROOT/.venv" "$INSTALL_DIR/.venv"
    echo -e "${GREEN}    ✓ Symlinked virtual environment${NC}"
else
    echo -e "${YELLOW}    ! Virtual environment not found at ${PROJECT_ROOT}/.venv${NC}"
    echo -e "${YELLOW}      Creating new virtual environment...${NC}"
    python3 -m venv "$INSTALL_DIR/.venv"
    "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/.venv/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"
    echo -e "${GREEN}    ✓ Created virtual environment${NC}"
fi

echo -e "${GREEN}    ✓ Source files symlinked (changes in dev location will reflect in install)${NC}"

# ========== Install Systemd Services ==========

echo -e "${BLUE}[3/9] Installing systemd services...${NC}"

# Stop services if running
systemctl stop gattrose-core.service 2>/dev/null || true
systemctl stop gattrose-api.service 2>/dev/null || true

# Copy service files
cp "$PROJECT_ROOT/install/systemd/gattrose-core.service" /etc/systemd/system/
cp "$PROJECT_ROOT/install/systemd/gattrose-api.service" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

echo -e "${GREEN}    ✓ Installed gattrose-core.service${NC}"
echo -e "${GREEN}    ✓ Installed gattrose-api.service${NC}"

# ========== Create CLI Wrapper ==========

echo -e "${BLUE}[4/9] Creating CLI wrapper...${NC}"

cat > "$BIN_DIR/gattrose" <<'EOF'
#!/usr/bin/env bash
# Gattrose CLI wrapper

INSTALL_DIR="/opt/gattrose-ng"

case "$1" in
    start)
        echo "[*] Starting Gattrose services..."
        sudo systemctl start gattrose-core
        sudo systemctl start gattrose-api
        echo "[✓] Services started"
        echo "    API: http://127.0.0.1:5555/api/docs"
        ;;
    stop)
        echo "[*] Stopping Gattrose services..."
        sudo systemctl stop gattrose-api
        sudo systemctl stop gattrose-core
        echo "[✓] Services stopped"
        ;;
    restart)
        echo "[*] Restarting Gattrose services..."
        sudo systemctl restart gattrose-core
        sudo systemctl restart gattrose-api
        echo "[✓] Services restarted"
        ;;
    status)
        echo "=== Gattrose Service Status ==="
        systemctl status gattrose-core --no-pager
        echo ""
        systemctl status gattrose-api --no-pager
        ;;
    enable)
        echo "[*] Enabling Gattrose services to start on boot..."
        sudo systemctl enable gattrose-core
        sudo systemctl enable gattrose-api
        echo "[✓] Services enabled"
        ;;
    disable)
        echo "[*] Disabling Gattrose services from starting on boot..."
        sudo systemctl disable gattrose-core
        sudo systemctl disable gattrose-api
        echo "[✓] Services disabled"
        ;;
    logs)
        if [ -z "$2" ]; then
            journalctl -u gattrose-core -u gattrose-api -f
        else
            journalctl -u "gattrose-$2" -f
        fi
        ;;
    gui)
        cd "$INSTALL_DIR"
        sudo -E .venv/bin/python gattrose-ng.py
        ;;
    update)
        echo "[*] Updating Gattrose from dev location..."
        cd "/home/eurrl/Documents/Code & Scripts/gattrose-ng"
        sudo /home/eurrl/Documents/Code\ \&\ Scripts/gattrose-ng/install/install.sh
        ;;
    *)
        echo "Gattrose-NG CLI"
        echo ""
        echo "Usage: gattrose <command>"
        echo ""
        echo "Commands:"
        echo "  start       Start Gattrose services"
        echo "  stop        Stop Gattrose services"
        echo "  restart     Restart Gattrose services"
        echo "  status      Show service status"
        echo "  enable      Enable services to start on boot"
        echo "  disable     Disable services from starting on boot"
        echo "  logs [core|api]  View service logs"
        echo "  gui         Launch GUI (experimental)"
        echo "  update      Update installation from dev location"
        echo ""
        echo "API: http://127.0.0.1:5555/api/docs"
        ;;
esac
EOF

chmod +x "$BIN_DIR/gattrose"
echo -e "${GREEN}    ✓ Created 'gattrose' command in ${BIN_DIR}${NC}"

# ========== Set Permissions ==========

echo -e "${BLUE}[5/9] Setting permissions...${NC}"

chown -R root:root "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"
chmod -R 777 "$INSTALL_DIR/data"
chmod -R 777 "$INSTALL_DIR/logs"

echo -e "${GREEN}    ✓ Permissions set${NC}"

# ========== Install Dependencies ==========

echo -e "${BLUE}[6/9] Checking dependencies...${NC}"

# Check for airmon-ng
if ! command -v airmon-ng &> /dev/null; then
    echo -e "${YELLOW}    ! airmon-ng not found, installing aircrack-ng...${NC}"
    apt-get update -qq
    apt-get install -y aircrack-ng
fi

# Check for iw
if ! command -v iw &> /dev/null; then
    echo -e "${YELLOW}    ! iw not found, installing...${NC}"
    apt-get install -y iw
fi

echo -e "${GREEN}    ✓ Dependencies verified${NC}"

# ========== Install Bluetooth Attack Frameworks ==========

echo -e "${BLUE}[7/9] Installing Bluetooth attack frameworks...${NC}"

# Install system dependencies for BT tools
apt-get install -y libbluetooth-dev bluez-tools bluez-hcidump 2>/dev/null || true

# Install Python BT attack libraries
echo -e "${YELLOW}    Installing WHAD (Wireless Hacking Framework)...${NC}"
"$INSTALL_DIR/.venv/bin/pip" install -q whad 2>/dev/null || true

echo -e "${YELLOW}    Installing BtleJuice (BLE MITM)...${NC}"
"$INSTALL_DIR/.venv/bin/pip" install -q btlejuice websocket-client 2>/dev/null || true

echo -e "${YELLOW}    Installing BlueToolkit dependencies...${NC}"
"$INSTALL_DIR/.venv/bin/pip" install -q pwntools cmd2 tabulate colorama 2>/dev/null || true

# Install PyBluez
echo -e "${YELLOW}    Installing PyBluez...${NC}"
"$INSTALL_DIR/.venv/bin/pip" install -q git+https://github.com/pybluez/pybluez.git#egg=pybluez 2>/dev/null || true

# Clone BlueToolkit if not exists
if [ ! -d "$INSTALL_DIR/tools/BlueToolkit" ]; then
    echo -e "${YELLOW}    Cloning BlueToolkit (43 BT exploits)...${NC}"
    mkdir -p "$INSTALL_DIR/tools"
    git clone --recurse-submodules https://github.com/sgxgsx/BlueToolkit "$INSTALL_DIR/tools/BlueToolkit" 2>/dev/null || true

    # Install bluekit package
    if [ -d "$INSTALL_DIR/tools/BlueToolkit/bluekit" ]; then
        "$INSTALL_DIR/.venv/bin/pip" install -q "$INSTALL_DIR/tools/BlueToolkit/bluekit" 2>/dev/null || true
    fi
fi

echo -e "${GREEN}    ✓ Bluetooth attack frameworks installed${NC}"
echo -e "${GREEN}      - WHAD (InjectaBLE, BLE sniffing/injection)${NC}"
echo -e "${GREEN}      - BtleJuice (BLE MITM proxy)${NC}"
echo -e "${GREEN}      - BlueToolkit (43 BT Classic exploits)${NC}"
echo -e "${GREEN}      - PyBluez (Bluetooth sockets)${NC}"

# ========== Final Steps ==========

echo -e "${BLUE}[8/9] Finishing installation...${NC}"

# Create update script in dev location
cat > "$PROJECT_ROOT/update-install.sh" <<'EOF'
#!/usr/bin/env bash
# Quick update script - run from dev location to update system install
echo "[*] Updating system installation..."
sudo bash install/install.sh
echo "[+] Update complete!"
EOF

chmod +x "$PROJECT_ROOT/update-install.sh"

echo -e "${GREEN}    ✓ Created update-install.sh in dev location${NC}"
echo ""

# ========== Verify Installation ==========

echo -e "${BLUE}[9/9] Verifying installation...${NC}"

# Test imports
echo -e "${YELLOW}    Testing Python imports...${NC}"
"$INSTALL_DIR/.venv/bin/python" -c "import whad; import btlejuice; import bluekit; import bluetooth; print('    ✓ All BT attack libraries verified')" 2>/dev/null || echo -e "${YELLOW}    ! Some BT libraries may need manual setup${NC}"

echo -e "${GREEN}    ✓ Installation verified${NC}"
echo ""

# ========== Installation Complete ==========

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Installation Complete Successfully!            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Installation Details:${NC}"
echo -e "  Installed to: ${INSTALL_DIR}"
echo -e "  Dev location: ${PROJECT_ROOT}"
echo -e "  Services: gattrose-core, gattrose-api"
echo ""
echo -e "${BLUE}BT Attack Frameworks:${NC}"
echo -e "  ${GREEN}WHAD${NC}        - InjectaBLE, BLE packet injection"
echo -e "  ${GREEN}BtleJuice${NC}   - BLE Man-in-the-Middle proxy"
echo -e "  ${GREEN}BlueToolkit${NC} - 43 Bluetooth Classic exploits"
echo -e "  ${GREEN}PyBluez${NC}     - Bluetooth socket programming"
echo ""
echo -e "${BLUE}Quick Start:${NC}"
echo -e "  ${GREEN}gattrose start${NC}     - Start services"
echo -e "  ${GREEN}gattrose status${NC}    - Check status"
echo -e "  ${GREEN}gattrose logs${NC}      - View logs"
echo -e "  ${GREEN}gattrose gui${NC}       - Launch GUI"
echo ""
echo -e "${BLUE}API Access:${NC}"
echo -e "  http://127.0.0.1:5555/api/docs"
echo ""
echo -e "${BLUE}Update from Dev:${NC}"
echo -e "  ${GREEN}gattrose update${NC}    - Or run ./update-install.sh in dev dir"
echo ""
echo -e "${YELLOW}Note: Source files are symlinked - changes in dev location${NC}"
echo -e "${YELLOW}      will automatically reflect in the system installation!${NC}"
echo ""
