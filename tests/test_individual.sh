#!/bin/bash
# Individual API tests - run these one at a time for detailed testing

API="http://127.0.0.1:5555"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Function to run a test
run_test() {
    local test_num=$1
    local test_name=$2
    local command=$3

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}TEST $test_num: $test_name${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    echo -e "${YELLOW}Command:${NC} $command"
    echo ""

    echo -e "${YELLOW}Response:${NC}"
    eval "$command"

    echo ""
    echo ""

    read -p "Press Enter to continue to next test..."
    echo ""
}

# Check if API is running
echo -e "${YELLOW}Checking if API server is running...${NC}"
if ! curl -s "$API/api/status" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: API server is not responding!${NC}"
    echo -e "${RED}Please start Gattrose first: sudo ./gattrose-ng.py${NC}"
    exit 1
fi
echo -e "${GREEN}✓ API server is running${NC}"
echo ""

# Test 1: API Documentation
run_test 1 "Get API Documentation" \
    "curl -s '$API/api/docs' | python3 -m json.tool | head -30"

# Test 2: Status Check
run_test 2 "Get Gattrose Status" \
    "curl -s '$API/api/status' | python3 -m json.tool"

# Test 3: Flipper - Auto Connect
run_test 3 "Connect to Flipper Zero (auto-detect)" \
    "curl -s -X POST '$API/api/flipper/connect' | python3 -m json.tool"

# Test 4: Flipper - Get Info
run_test 4 "Get Flipper Device Info" \
    "curl -s '$API/api/flipper/info' | python3 -m json.tool | head -20"

# Test 5: Flipper - LED Blue
run_test 5 "Blink LED Blue (2 seconds)" \
    "curl -s -X POST '$API/api/flipper/led' -H 'Content-Type: application/json' -d '{\"color\": \"blue\", \"duration\": 2}' | python3 -m json.tool"

# Test 6: Flipper - LED Red
run_test 6 "Blink LED Red (1 second)" \
    "curl -s -X POST '$API/api/flipper/led' -H 'Content-Type: application/json' -d '{\"color\": \"red\", \"duration\": 1}' | python3 -m json.tool"

# Test 7: Flipper - LED Green
run_test 7 "Blink LED Green (1 second)" \
    "curl -s -X POST '$API/api/flipper/led' -H 'Content-Type: application/json' -d '{\"color\": \"green\", \"duration\": 1}' | python3 -m json.tool"

# Test 8: Flipper - Vibrate
run_test 8 "Vibrate Flipper (1 second)" \
    "curl -s -X POST '$API/api/flipper/vibrate' -H 'Content-Type: application/json' -d '{\"duration\": 1}' | python3 -m json.tool"

# Test 9: Flipper - Custom Command (device_info)
run_test 9 "Send Custom Command (device_info)" \
    "curl -s -X POST '$API/api/flipper/command' -H 'Content-Type: application/json' -d '{\"command\": \"device_info\"}' | python3 -m json.tool | head -30"

# Test 10: Flipper - Custom Command (LED on)
run_test 10 "Send Custom Command (LED 0 255 0 - Green)" \
    "curl -s -X POST '$API/api/flipper/command' -H 'Content-Type: application/json' -d '{\"command\": \"led 0 255 0\"}' | python3 -m json.tool"

# Wait 2 seconds
echo -e "${YELLOW}LED should be green for 2 seconds...${NC}"
sleep 2

# Test 11: Flipper - Custom Command (LED off)
run_test 11 "Send Custom Command (LED 0 0 0 - Off)" \
    "curl -s -X POST '$API/api/flipper/command' -H 'Content-Type: application/json' -d '{\"command\": \"led 0 0 0\"}' | python3 -m json.tool"

# Test 12: Scanner - Start
run_test 12 "Start WiFi Scanner" \
    "curl -s -X POST '$API/api/scanner/start' | python3 -m json.tool"

# Wait for networks
echo -e "${YELLOW}Waiting 10 seconds for networks to be discovered...${NC}"
sleep 10

# Test 13: Status check (should show scanner active)
run_test 13 "Get Status (scanner should be active)" \
    "curl -s '$API/api/status' | python3 -m json.tool"

# Test 14: Get Networks
run_test 14 "Get Discovered Networks" \
    "curl -s '$API/api/scanner/networks' | python3 -m json.tool | head -80"

# Test 15: Get Clients
run_test 15 "Get Discovered Clients" \
    "curl -s '$API/api/scanner/clients' | python3 -m json.tool | head -80"

# Test 16: Scanner - Stop
run_test 16 "Stop WiFi Scanner" \
    "curl -s -X POST '$API/api/scanner/stop' | python3 -m json.tool"

# Test 17: Flipper - Disconnect
run_test 17 "Disconnect from Flipper Zero" \
    "curl -s -X POST '$API/api/flipper/disconnect' | python3 -m json.tool"

# Test 18: Final Status Check
run_test 18 "Final Status Check" \
    "curl -s '$API/api/status' | python3 -m json.tool"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ALL TESTS COMPLETED!${NC}"
echo -e "${GREEN}========================================${NC}"
