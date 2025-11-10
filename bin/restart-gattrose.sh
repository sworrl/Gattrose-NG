#!/bin/bash

# Gattrose-NG Clean Restart Script
# Kills any running instances, cleans cache, and restarts

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Gattrose-NG Clean Restart Script            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Kill any running instances
echo -e "${YELLOW}[*] Checking for running instances...${NC}"
if pgrep -f "gattrose-ng.py" > /dev/null; then
    echo -e "${YELLOW}[!] Killing existing Gattrose-NG processes...${NC}"
    sudo pkill -f "gattrose-ng.py" 2>/dev/null
    sleep 2
fi

# Clean Python cache
echo -e "${YELLOW}[*] Cleaning Python cache...${NC}"
find "$PROJECT_ROOT/src" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$PROJECT_ROOT/src" -type f -name "*.pyc" -delete 2>/dev/null
echo -e "${GREEN}[✓] Cache cleaned${NC}"

# Restart application
echo -e "${GREEN}[*] Starting Gattrose-NG...${NC}"
echo ""

cd "$PROJECT_ROOT"
sudo python3 gattrose-ng.py

