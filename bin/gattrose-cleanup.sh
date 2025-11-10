#!/bin/bash
#
# Gattrose-NG Cleanup Script
# Force kills all Gattrose-NG processes and orphaned wireless tools
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  Gattrose-NG Force Cleanup"
echo "============================================"
echo ""

# Run Python cleanup script
cd "$PROJECT_ROOT"

if [ -f ".venv/bin/python" ]; then
    echo "[*] Running cleanup with virtual environment..."
    sudo .venv/bin/python -m src.utils.process_manager --force-cleanup
else
    echo "[*] Running cleanup with system Python..."
    sudo python3 -m src.utils.process_manager --force-cleanup
fi

echo ""
echo "[*] Killing any remaining Gattrose processes..."
sudo killall -9 python python3 2>/dev/null || true

echo ""
echo "[*] Killing orphaned wireless tool processes..."
sudo killall -9 airodump-ng aireplay-ng aircrack-ng reaver wash 2>/dev/null || true

echo ""
echo "[*] Restoring NetworkManager..."
sudo systemctl restart NetworkManager 2>/dev/null || true

echo ""
echo "============================================"
echo "[✓] Cleanup complete!"
echo "============================================"
