#!/bin/bash
#
# Install Gattrose-NG System Services
# Installs orchestrator as a systemd service
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Gattrose-NG Service Installation${NC}"
echo -e "${BLUE}================================${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[!] This script must be run as root${NC}"
    echo -e "${YELLOW}[*] Please run: sudo $0${NC}"
    exit 1
fi

# Install to /opt
INSTALL_DIR="/opt/gattrose-ng"

echo -e "${BLUE}[*] Install directory: ${INSTALL_DIR}${NC}"
echo

# Copy project to /opt if not already there
if [ "$PROJECT_ROOT" != "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}[*] Copying project to ${INSTALL_DIR}...${NC}"

    # Create directory
    mkdir -p "$INSTALL_DIR"

    # Copy files (preserve existing data directory if exists)
    rsync -av --exclude='data/' --exclude='.git/' --exclude='__pycache__' \
        "$PROJECT_ROOT/" "$INSTALL_DIR/"

    # Copy data directory if doesn't exist
    if [ ! -d "$INSTALL_DIR/data" ] && [ -d "$PROJECT_ROOT/data" ]; then
        echo -e "${YELLOW}[*] Copying data directory...${NC}"
        rsync -av "$PROJECT_ROOT/data/" "$INSTALL_DIR/data/"
    fi

    echo -e "${GREEN}[✓] Project copied${NC}"
else
    echo -e "${GREEN}[✓] Project already in ${INSTALL_DIR}${NC}"
fi

# Set up virtual environment if needed
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    echo -e "${YELLOW}[*] Creating virtual environment...${NC}"
    cd "$INSTALL_DIR"
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    echo -e "${GREEN}[✓] Virtual environment created${NC}"
fi

# Install systemd service
echo -e "${YELLOW}[*] Installing systemd service...${NC}"

if [ -f "$INSTALL_DIR/services/gattrose-orchestrator.service" ]; then
    cp "$INSTALL_DIR/services/gattrose-orchestrator.service" /etc/systemd/system/
    systemctl daemon-reload
    echo -e "${GREEN}[✓] Service installed${NC}"
else
    echo -e "${RED}[!] Service file not found: $INSTALL_DIR/services/gattrose-orchestrator.service${NC}"
    exit 1
fi

# Enable service
echo -e "${YELLOW}[*] Enabling service...${NC}"
systemctl enable gattrose-orchestrator.service
echo -e "${GREEN}[✓] Service enabled${NC}"

# Set permissions
echo -e "${YELLOW}[*] Setting permissions...${NC}"
chown -R root:root "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/bin/"*.sh
chmod +x "$INSTALL_DIR/bin/"*.py
echo -e "${GREEN}[✓] Permissions set${NC}"

echo
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo
echo -e "${BLUE}Service Commands:${NC}"
echo -e "  ${YELLOW}Start service:${NC}   sudo systemctl start gattrose-orchestrator"
echo -e "  ${YELLOW}Stop service:${NC}    sudo systemctl stop gattrose-orchestrator"
echo -e "  ${YELLOW}Service status:${NC}  sudo systemctl status gattrose-orchestrator"
echo -e "  ${YELLOW}View logs:${NC}       sudo journalctl -u gattrose-orchestrator -f"
echo
echo -e "${BLUE}GUI (run as normal user):${NC}"
echo -e "  ${YELLOW}Start GUI:${NC}       cd /opt/gattrose-ng && bin/gattrose-gui.sh"
echo
echo -e "${YELLOW}[*] Starting service...${NC}"
systemctl start gattrose-orchestrator
sleep 3
systemctl status gattrose-orchestrator --no-pager
echo
echo -e "${GREEN}[✓] Service started!${NC}"
