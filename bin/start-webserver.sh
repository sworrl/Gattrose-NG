#!/bin/bash

# Gattrose-NG Web Server Launcher
# Starts the Flask web API server

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Gattrose-NG Web Server Launcher          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] Warning: Not running as root. Some features may be limited.${NC}"
fi

# Activate virtual environment
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo -e "${GREEN}[+] Activating virtual environment...${NC}"
    source "$PROJECT_ROOT/.venv/bin/activate"
else
    echo -e "${RED}[!] Virtual environment not found. Please run installation first.${NC}"
    exit 1
fi

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}[!] Flask not installed. Installing dependencies...${NC}"
    pip install flask flask-cors
fi

# Set Flask environment variables
export FLASK_APP="$PROJECT_ROOT/src/services/web_api.py"
export FLASK_ENV="development"
export FLASK_DEBUG=1

# Get local IP address
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}[+] Starting Flask web server...${NC}"
echo -e "${BLUE}[i] Local access:     http://localhost:5000${NC}"
echo -e "${BLUE}[i] Network access:   http://$LOCAL_IP:5000${NC}"
echo -e "${BLUE}[i] API documentation available at /api/docs${NC}"
echo ""
echo -e "${YELLOW}[!] Press Ctrl+C to stop the server${NC}"
echo ""

# Start Flask server
cd "$PROJECT_ROOT"
python3 -m flask run --host=0.0.0.0 --port=5000
