# Gattrose-NG API v3.0 Quick Reference

**Base URL:** `http://localhost:5555`
**Version:** 3.0.0
**Total Endpoints:** 120+
**Port:** 5555 (localhost only)

## 🚀 Quick Start

```bash
# Start API server (headless mode)
python3 src/services/local_api_v3.py

# View full API documentation
curl http://localhost:5555/api/v3/docs | jq

# Get current status
curl http://localhost:5555/api/v3/status | jq

# Run test suite
python3 tests/test_api_v3.py
```

## GUI Control Endpoints

### Tab Management

```bash
# Switch to mapping tab
curl -X POST http://localhost:5555/api/gui/tab \
  -H "Content-Type: application/json" \
  -d '{"tab": "mapping"}'

# Valid tabs: dashboard, scanner, wps, clients, auto_attack,
#             manual_attack, bluetooth, flipper, wigle, mapping
```

### Scanner Control

```bash
# Start scanning
curl -X POST http://localhost:5555/api/gui/scan/start

# Stop scanning
curl -X POST http://localhost:5555/api/gui/scan/stop

# Get scan status
curl http://localhost:5555/api/gui/scan/status
```

### Data Retrieval

```bash
# Get networks
curl http://localhost:5555/api/gui/networks

# Get clients
curl http://localhost:5555/api/gui/clients

# Get statistics
curl http://localhost:5555/api/gui/stats

# Get complete GUI state
curl http://localhost:5555/api/gui/state
```

### GPS Control

```bash
# Get GPS status
curl http://localhost:5555/api/gui/gps/status

# Update GPS location on map
curl -X POST http://localhost:5555/api/gui/gps/location \
  -H "Content-Type: application/json" \
  -d '{"latitude": 39.005509, "longitude": -90.741686}'
```

### Theme Management

```bash
# Change theme
curl -X POST http://localhost:5555/api/gui/theme \
  -H "Content-Type: application/json" \
  -d '{"theme": "hacker"}'

# Available themes: sonic, hacker, midnight, ocean, forest, sunset, neon, stealth
```

### Filters

```bash
# Apply filter
curl -X POST http://localhost:5555/api/gui/filter \
  -H "Content-Type: application/json" \
  -d '{"type": "ssid", "value": "MyNetwork"}'
```

## Legacy Endpoints (Still Available)

### Status

```bash
curl http://localhost:5555/api/status
```

### Scanner (Legacy)

```bash
# Start
curl -X POST http://localhost:5555/api/scanner/start

# Stop
curl -X POST http://localhost:5555/api/scanner/stop

# Get networks
curl http://localhost:5555/api/scanner/networks

# Get clients
curl http://localhost:5555/api/scanner/clients
```

### Flipper Zero

```bash
# Connect
curl -X POST http://localhost:5555/api/flipper/connect

# Disconnect
curl -X POST http://localhost:5555/api/flipper/disconnect

# Send command
curl -X POST http://localhost:5555/api/flipper/command \
  -H "Content-Type: application/json" \
  -d '{"command": "device_info"}'

# Blink LED
curl -X POST http://localhost:5555/api/flipper/led \
  -H "Content-Type: application/json" \
  -d '{"color": "blue", "duration": 2}'

# Vibrate
curl -X POST http://localhost:5555/api/flipper/vibrate \
  -H "Content-Type: application/json" \
  -d '{"duration": 1}'

# Get info
curl http://localhost:5555/api/flipper/info
```

### Attacks

```bash
# Deauth attack
curl -X POST http://localhost:5555/api/attack/deauth \
  -H "Content-Type: application/json" \
  -d '{"mac": "AA:BB:CC:DD:EE:FF"}'
```

## Response Format

All endpoints return JSON:

```json
{
  "success": true,
  "message": "Optional message",
  "data": {}
}
```

Error format:
```json
{
  "success": false,
  "error": "Error message"
}
```

## Common Use Cases

### Automation Script Example

```bash
#!/bin/bash
BASE="http://localhost:5555"

# Switch to scanner tab and start scan
curl -X POST $BASE/api/gui/tab -H "Content-Type: application/json" -d '{"tab": "scanner"}'
sleep 1
curl -X POST $BASE/api/gui/scan/start

# Wait 30 seconds
sleep 30

# Stop scan and get results
curl -X POST $BASE/api/gui/scan/stop
curl $BASE/api/gui/networks | jq '.count'

# Switch to mapping tab
curl -X POST $BASE/api/gui/tab -H "Content-Type: application/json" -d '{"tab": "mapping"}'
```

### Monitor GPS Location

```bash
# Continuous GPS monitoring
while true; do
  curl -s http://localhost:5555/api/gui/gps/status | \
    jq -r '.data | "\(.latitude), \(.longitude) - \(.source) - ±\(.accuracy)m"'
  sleep 2
done
```

### Network Count Monitor

```bash
# Monitor network count
watch -n 5 'curl -s http://localhost:5555/api/gui/networks | jq ".count"'
```

### Theme Cycler

```bash
# Cycle through themes
for theme in sonic hacker midnight ocean forest sunset neon stealth; do
  echo "Setting theme: $theme"
  curl -X POST http://localhost:5555/api/gui/theme \
    -H "Content-Type: application/json" \
    -d "{\"theme\": \"$theme\"}"
  sleep 5
done
```

## Python Integration

```python
import requests
import time

BASE = "http://localhost:5555"

class GattroseAPI:
    def __init__(self, base_url="http://localhost:5555"):
        self.base = base_url

    def get_gps(self):
        r = requests.get(f"{self.base}/api/gui/gps/status")
        return r.json()['data']

    def switch_tab(self, tab):
        r = requests.post(
            f"{self.base}/api/gui/tab",
            json={"tab": tab}
        )
        return r.json()['success']

    def get_networks(self):
        r = requests.get(f"{self.base}/api/gui/networks")
        return r.json()['data']

    def start_scan(self):
        r = requests.post(f"{self.base}/api/gui/scan/start")
        return r.json()['success']

    def stop_scan(self):
        r = requests.post(f"{self.base}/api/gui/scan/stop")
        return r.json()['success']

    def get_state(self):
        r = requests.get(f"{self.base}/api/gui/state")
        return r.json()['data']

# Usage
api = GattroseAPI()

# Get GPS
gps = api.get_gps()
print(f"GPS: {gps['latitude']}, {gps['longitude']}")

# Switch to mapping
api.switch_tab("mapping")

# Get state
state = api.get_state()
print(f"Theme: {state['theme']}")
print(f"Networks: {state['stats']['networks']}")
```

## Testing

Run the test suite:
```bash
cd /home/eurrl/Documents/Code\ \&\ Scripts/gattrose-ng
./test_api.sh
```

## Troubleshooting

### Connection Refused
```bash
# Check if Gattrose is running
curl http://localhost:5555/api/docs

# If not, start it:
cd /home/eurrl/Documents/Code\ \&\ Scripts/gattrose-ng
sudo python3 -m src.main
```

### Port In Use
```bash
# Check what's using port 5555
sudo lsof -i :5555

# Kill process if needed
sudo kill -9 <PID>
```

### Invalid Tab Name
Valid tabs:
- dashboard
- scanner
- wps
- clients
- auto_attack
- manual_attack
- bluetooth
- flipper
- wigle
- mapping

## Security

- API only accessible from localhost (127.0.0.1)
- No external network access
- CORS enabled for localhost only
- No authentication required (local access only)

## Rate Limiting

No rate limiting currently implemented. All endpoints can be called as frequently as needed.

## Notes

- All GUI operations are thread-safe via Qt signals
- Map updates automatically every 5 seconds
- GPS data refreshes from `/tmp/gattrose-status.json`
- Theme changes persist across sessions
- Scanner state preserved when switching tabs
