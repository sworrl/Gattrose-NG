# Gattrose-NG API Testing Guide

## Overview

Gattrose-NG now includes a comprehensive REST API for programmatic control of the GUI. This allows for automation, testing, and external control of all major features.

## Changes Made

### 1. Fixed Map Flashing

**Problem:** The map was reloading the entire HTML page every 5 seconds, causing visible flickering.

**Solution:**
- Changed map initialization to load HTML only once
- Implemented JavaScript functions for incremental marker updates
- Used `QWebEngineView.page().runJavaScript()` to update markers without page reload
- Added three update functions:
  - `updateMarkers()` - Updates AP markers dynamically
  - `updateTrackPoints()` - Updates GPS track trail
  - `updateCurrentGPS()` - Shows current GPS location with accuracy circle

**Files Modified:**
- `/home/eurrl/Documents/Code & Scripts/gattrose-ng/src/gui/mapping_tab.py`

**Key Changes:**
- Added `map_initialized` flag to track map state
- Split `refresh_map()` into `load_initial_map()` and `update_markers()`
- Implemented `_update_markers_js()` to send data via JavaScript
- Map now loads once and updates smoothly every 5 seconds

### 2. Fixed Missing Data on Map

**Problem:** No GPS data or network markers were displaying on the map.

**Solution:**
- Added `_get_current_gps_location()` to read from `/tmp/gattrose-status.json`
- GPS location (39.005509, -90.741686) is now displayed with accuracy circle
- Current GPS marker shows:
  - Live position with icon (📍 for GPS, 📱 for phone)
  - Accuracy circle showing precision
  - Popup with source, fix quality, and coordinates
- Network observations from database are queried and displayed
- User track trail shows wardriving path

**Files Modified:**
- `/home/eurrl/Documents/Code & Scripts/gattrose-ng/src/gui/mapping_tab.py`

### 3. Added Comprehensive GUI API Control

**New API Endpoints:**

#### GUI Control Endpoints

```bash
# Switch to specific tab
POST /api/gui/tab
Body: {"tab": "mapping"}

# Start scanning
POST /api/gui/scan/start

# Stop scanning
POST /api/gui/scan/stop

# Get scan status
GET /api/gui/scan/status

# Get networks from GUI
GET /api/gui/networks

# Get clients from GUI
GET /api/gui/clients

# Get GPS status
GET /api/gui/gps/status

# Update GPS location on map
POST /api/gui/gps/location
Body: {"latitude": 39.005509, "longitude": -90.741686}

# Apply filters
POST /api/gui/filter
Body: {"type": "ssid", "value": "MyNetwork"}

# Get all statistics
GET /api/gui/stats

# Change theme
POST /api/gui/theme
Body: {"theme": "sonic"}

# Get complete GUI state
GET /api/gui/state
```

**Valid Tab Names:**
- `dashboard` - Main dashboard
- `scanner` - Network scanner
- `wps` - WPS networks
- `clients` - Unassociated clients
- `auto_attack` - Auto attack
- `manual_attack` - Manual attack
- `bluetooth` - Bluetooth
- `flipper` - Flipper Zero
- `wigle` - WiGLE import
- `mapping` - Map view

**Files Modified:**
- `/home/eurrl/Documents/Code & Scripts/gattrose-ng/src/services/local_api.py` - Added API endpoints
- `/home/eurrl/Documents/Code & Scripts/gattrose-ng/src/gui/main_window.py` - Added API control methods

**Key Features:**
- Thread-safe GUI updates using Qt signals/slots
- All GUI operations use `QMetaObject.invokeMethod()` with `QueuedConnection`
- MainWindow is accessible to API via reference stored in LocalAPIServer
- Comprehensive error handling and logging

## Testing the API

### 1. Start Gattrose-NG

```bash
cd /home/eurrl/Documents/Code\ \&\ Scripts/gattrose-ng
sudo python3 -m src.main
```

The API server will start automatically on `http://localhost:5555`

### 2. View API Documentation

```bash
curl http://localhost:5555/api/docs | jq
```

### 3. Test GPS Status

```bash
# Get current GPS status
curl http://localhost:5555/api/gui/gps/status | jq

# Expected output:
{
  "success": true,
  "data": {
    "has_fix": true,
    "latitude": 39.005509,
    "longitude": -90.741686,
    "altitude": null,
    "accuracy": 10.204082,
    "source": "phone-usb",
    "fix_quality": "3D Fix"
  }
}
```

### 4. Switch to Mapping Tab

```bash
curl -X POST http://localhost:5555/api/gui/tab \
  -H "Content-Type: application/json" \
  -d '{"tab": "mapping"}' | jq

# Expected output:
{
  "success": true,
  "message": "Switched to mapping tab"
}
```

### 5. Get GUI State

```bash
curl http://localhost:5555/api/gui/state | jq

# Expected output:
{
  "success": true,
  "data": {
    "theme": "sonic",
    "gps": {
      "has_fix": true,
      "latitude": 39.005509,
      "longitude": -90.741686,
      "accuracy": 10.204082,
      "source": "phone-usb",
      "fix_quality": "3D Fix"
    },
    "stats": {
      "networks": 0,
      "clients": 0,
      "scanner_running": false,
      "monitor_interface": "wlp7s0mon",
      "current_tab": 9
    },
    "tabs": {
      "current": 9,
      "count": 10
    }
  }
}
```

### 6. Update GPS Location (Testing)

```bash
curl -X POST http://localhost:5555/api/gui/gps/location \
  -H "Content-Type: application/json" \
  -d '{"latitude": 39.005509, "longitude": -90.741686}' | jq
```

### 7. Get Network Statistics

```bash
curl http://localhost:5555/api/gui/stats | jq
```

### 8. Change Theme

```bash
# Available themes: sonic, hacker, midnight, ocean, forest, sunset, neon, stealth
curl -X POST http://localhost:5555/api/gui/theme \
  -H "Content-Type: application/json" \
  -d '{"theme": "hacker"}' | jq
```

### 9. Get Networks

```bash
curl http://localhost:5555/api/gui/networks | jq
```

### 10. Start/Stop Scanner

```bash
# Start scanning
curl -X POST http://localhost:5555/api/gui/scan/start | jq

# Check status
curl http://localhost:5555/api/gui/scan/status | jq

# Stop scanning
curl -X POST http://localhost:5555/api/gui/scan/stop | jq
```

## Complete Test Script

Save as `test_api.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:5555"

echo "=== Testing Gattrose-NG API ==="
echo

echo "1. Getting API documentation..."
curl -s $BASE_URL/api/docs | jq '.endpoints'
echo

echo "2. Getting GPS status..."
curl -s $BASE_URL/api/gui/gps/status | jq
echo

echo "3. Getting GUI state..."
curl -s $BASE_URL/api/gui/state | jq
echo

echo "4. Getting statistics..."
curl -s $BASE_URL/api/gui/stats | jq
echo

echo "5. Switching to mapping tab..."
curl -s -X POST $BASE_URL/api/gui/tab \
  -H "Content-Type: application/json" \
  -d '{"tab": "mapping"}' | jq
echo

echo "6. Switching to dashboard tab..."
curl -s -X POST $BASE_URL/api/gui/tab \
  -H "Content-Type: application/json" \
  -d '{"tab": "dashboard"}' | jq
echo

echo "7. Getting networks..."
curl -s $BASE_URL/api/gui/networks | jq '.count'
echo

echo "8. Getting clients..."
curl -s $BASE_URL/api/gui/clients | jq '.count'
echo

echo "=== All tests complete ==="
```

Make executable and run:
```bash
chmod +x test_api.sh
./test_api.sh
```

## Integration Examples

### Python Integration

```python
import requests
import json

BASE_URL = "http://localhost:5555"

# Get GPS status
response = requests.get(f"{BASE_URL}/api/gui/gps/status")
gps_data = response.json()
print(f"GPS: {gps_data['data']['latitude']}, {gps_data['data']['longitude']}")

# Switch to mapping tab
response = requests.post(
    f"{BASE_URL}/api/gui/tab",
    json={"tab": "mapping"}
)
print(response.json())

# Get all networks
response = requests.get(f"{BASE_URL}/api/gui/networks")
networks = response.json()
print(f"Found {networks['count']} networks")

# Change theme
response = requests.post(
    f"{BASE_URL}/api/gui/theme",
    json={"theme": "hacker"}
)
print(response.json())
```

### JavaScript Integration

```javascript
const BASE_URL = 'http://localhost:5555';

// Get GPS status
fetch(`${BASE_URL}/api/gui/gps/status`)
  .then(res => res.json())
  .then(data => console.log('GPS:', data.data));

// Switch tab
fetch(`${BASE_URL}/api/gui/tab`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ tab: 'mapping' })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

## Security Notes

- API server only listens on `127.0.0.1` (localhost) for security
- No authentication required (local only)
- CORS enabled for localhost origins only
- All GUI updates are thread-safe via Qt signals

## Troubleshooting

### API not responding
- Check if Gattrose-NG is running
- Verify port 5555 is not in use: `lsof -i :5555`

### GPS data not showing
- Check `/tmp/gattrose-status.json` exists
- Verify GPS service is running in status output
- Ensure phone is connected via ADB (if using phone GPS)

### Map not updating
- Switch to mapping tab first
- Allow 1 second for initial map load
- Check browser console for JavaScript errors

### Theme not changing
- Verify theme name is valid (see API docs)
- Check main_window logs for errors

## Summary

All requested features have been implemented:

1. **Map Flashing Fixed** - Smooth incremental updates without page reload
2. **Missing Data Fixed** - GPS location and network markers now display correctly
3. **API Control Added** - 12 new GUI control endpoints for complete programmatic control
4. **Thread Safety** - All API operations use Qt signals for safe GUI updates
5. **Documentation** - Complete API documentation with examples

The system is now ready for automated testing, external control, and integration with other tools.
