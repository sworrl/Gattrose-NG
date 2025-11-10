# Gattrose-NG API v3.0 Documentation

## Overview

The Gattrose-NG API v3.0 provides comprehensive REST API access to all system functionality, making Gattrose fully headless-capable and automation-ready. With over **120 endpoints** across 8 major categories, you can control every aspect of Gattrose programmatically.

**API Version:** 3.0.0
**Base URL:** `http://localhost:5555`
**WebSocket URL:** `ws://localhost:5555/ws/events`
**Authentication:** API Key (optional, configurable)

---

## Features

✅ **Service Control** (25+ endpoints) - Start/stop/configure all services
✅ **Attack Operations** (30+ endpoints) - Deauth, WPS, Evil Twin, Handshake capture
✅ **Network Management** (20+ endpoints) - Query, filter, blacklist networks
✅ **System Operations** (15+ endpoints) - Monitor mode, interfaces, MAC spoofing
✅ **Configuration** (10+ endpoints) - Get/set all configuration values
✅ **File Operations** (15+ endpoints) - Export, download, manage capture files
✅ **Analytics** (10+ endpoints) - Statistics, summaries, reporting
✅ **Real-time WebSocket** - Live updates for scans and attacks
✅ **Rate Limiting** - 100 requests/minute protection
✅ **OpenAPI Documentation** - Auto-generated docs at `/api/v3/docs`

---

## Quick Start

### 1. Start the API Server

**Headless Mode (No GUI):**
```bash
python3 src/services/local_api_v3.py
```

**With GUI:**
```python
from src.services.local_api_v3 import APIv3Server

# In your main window initialization
self.api_server = APIv3Server(main_window=self, port=5555)
self.api_server.start()
```

### 2. Test the API

```bash
# Check API status
curl http://localhost:5555/api/v3/status

# Get documentation
curl http://localhost:5555/api/v3/docs

# Run test suite
python3 tests/test_api_v3.py
```

---

## Authentication

Authentication is **optional** and disabled by default for localhost access.

### Enable Authentication

Set in database config:
```python
config.set('api.auth_required', True)
```

### Using API Keys

**Option 1: Header (Recommended)**
```bash
curl -H "X-API-Key: gattrose_your_api_key_here" http://localhost:5555/api/v3/networks
```

**Option 2: Query Parameter**
```bash
curl http://localhost:5555/api/v3/networks?api_key=gattrose_your_api_key_here
```

### Generate API Key

```bash
# Default key is printed on server startup, or:
export GATTROSE_API_KEY="gattrose_custom_key_here"
python3 src/services/local_api_v3.py
```

---

## Endpoint Categories

### 1. Core System (4 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v3` | API root information |
| GET | `/api/v3/status` | Complete system status |
| GET | `/api/v3/health` | Health check |
| GET | `/api/v3/docs` | API documentation |

**Example:**
```bash
curl http://localhost:5555/api/v3/status | jq
```

**Response:**
```json
{
  "success": true,
  "data": {
    "system": {
      "running": true,
      "api_version": "3.0.0",
      "uptime_seconds": 3600
    },
    "services": {
      "scanner": {"running": true, "status": "running"},
      "gps": {"running": true, "status": "running"},
      "database": {"running": true, "status": "running"}
    }
  },
  "timestamp": "2025-11-03T12:00:00Z"
}
```

---

### 2. Service Control (25+ endpoints)

#### All Services
```bash
GET    /api/v3/services              # Get all service statuses
POST   /api/v3/services/start        # Start all services
POST   /api/v3/services/stop         # Stop all services
POST   /api/v3/services/restart      # Restart all services
```

#### Scanner Service
```bash
GET    /api/v3/services/scanner/status       # Get scanner status
POST   /api/v3/services/scanner/start        # Start scanner
POST   /api/v3/services/scanner/stop         # Stop scanner
POST   /api/v3/services/scanner/channel      # Set channel
POST   /api/v3/services/scanner/hop          # Toggle channel hopping
```

**Start Scanner Example:**
```bash
curl -X POST http://localhost:5555/api/v3/services/scanner/start \
  -H "Content-Type: application/json" \
  -d '{"interface": "wlan0mon", "channel": 6}'
```

#### GPS Service
```bash
GET    /api/v3/services/gps/status           # Get GPS status
GET    /api/v3/services/gps/location         # Get current location
POST   /api/v3/services/gps/source           # Change GPS source
```

**GPS Source Options:** `gpsd`, `phone-usb`, `phone-bt`, `geoip`

**Example:**
```bash
# Get GPS location
curl http://localhost:5555/api/v3/services/gps/location

# Change GPS source
curl -X POST http://localhost:5555/api/v3/services/gps/source \
  -H "Content-Type: application/json" \
  -d '{"source": "phone-usb"}'
```

#### Database Service
```bash
GET    /api/v3/services/database/status      # Database status
POST   /api/v3/services/database/vacuum      # Vacuum database
POST   /api/v3/services/database/backup      # Backup database
GET    /api/v3/services/database/stats       # Database statistics
```

#### Triangulation Service
```bash
GET    /api/v3/services/triangulation/status           # Status
POST   /api/v3/services/triangulation/calculate        # Calculate for AP
```

---

### 3. Attack Operations (30+ endpoints)

#### Deauth Attacks
```bash
POST   /api/v3/attacks/deauth/start          # Start deauth attack
POST   /api/v3/attacks/deauth/stop           # Stop deauth attack
GET    /api/v3/attacks/deauth/status         # Get status
```

**Example:**
```bash
# Deauth specific client from AP
curl -X POST http://localhost:5555/api/v3/attacks/deauth/start \
  -H "Content-Type: application/json" \
  -d '{
    "bssid": "AA:BB:CC:DD:EE:FF",
    "client": "11:22:33:44:55:66",
    "count": 10
  }'
```

#### Evil Twin Attacks
```bash
POST   /api/v3/attacks/eviltwin/start        # Start evil twin
POST   /api/v3/attacks/eviltwin/stop         # Stop evil twin
GET    /api/v3/attacks/eviltwin/status       # Get status
GET    /api/v3/attacks/eviltwin/captures     # Get captured credentials
```

#### WPS Attacks
```bash
POST   /api/v3/attacks/wps/pixie             # WPS Pixie Dust
POST   /api/v3/attacks/wps/bruteforce        # WPS PIN bruteforce
POST   /api/v3/attacks/wps/null              # WPS NULL PIN
POST   /api/v3/attacks/wps/stop              # Stop WPS attack
GET    /api/v3/attacks/wps/status            # Get status
```

**Example:**
```bash
# Start WPS Pixie Dust attack
curl -X POST http://localhost:5555/api/v3/attacks/wps/pixie \
  -H "Content-Type: application/json" \
  -d '{"bssid": "AA:BB:CC:DD:EE:FF"}'
```

#### Handshake Capture
```bash
POST   /api/v3/attacks/handshake/capture     # Capture handshake
GET    /api/v3/attacks/handshake/status      # Get status
POST   /api/v3/attacks/handshake/verify      # Verify handshake file
```

#### PMKID Attacks
```bash
POST   /api/v3/attacks/pmkid/capture         # Capture PMKID
GET    /api/v3/attacks/pmkid/status          # Get status
```

#### Auto-Attack Mode
```bash
POST   /api/v3/attacks/auto/start            # Start auto-attack
POST   /api/v3/attacks/auto/stop             # Stop auto-attack
GET    /api/v3/attacks/auto/status           # Get status
POST   /api/v3/attacks/auto/config           # Configure settings
```

#### Attack Queue
```bash
GET    /api/v3/attacks/queue                 # Get attack queue
POST   /api/v3/attacks/queue/add             # Add to queue
```

---

### 4. Network & Client Management (20+ endpoints)

#### Networks
```bash
GET    /api/v3/networks                      # Get all networks
GET    /api/v3/networks/{bssid}              # Get specific network
POST   /api/v3/networks/filter               # Apply filters
DELETE /api/v3/networks                      # Clear network list
```

**Query Parameters:**
- `limit` - Results per page (default: 100)
- `offset` - Pagination offset (default: 0)
- `sort_by` - Sort field (default: last_seen)
- `order` - Sort order: asc/desc (default: desc)

**Example:**
```bash
# Get first 20 networks sorted by signal strength
curl "http://localhost:5555/api/v3/networks?limit=20&sort_by=current_signal&order=desc"

# Filter networks by encryption type
curl -X POST http://localhost:5555/api/v3/networks/filter \
  -H "Content-Type: application/json" \
  -d '{
    "encryption": "WPA2",
    "min_signal": -70,
    "wps_enabled": true
  }'
```

**Filter Options:**
- `encryption` - Filter by encryption type
- `min_signal` - Minimum signal strength (dBm)
- `channel` - Specific channel
- `wps_enabled` - WPS enabled (true/false)
- `ssid_pattern` - SSID pattern match

#### Blacklist Management
```bash
POST   /api/v3/networks/blacklist/add        # Add to blacklist
POST   /api/v3/networks/blacklist/remove     # Remove from blacklist
GET    /api/v3/networks/blacklist            # Get blacklist
```

#### Clients
```bash
GET    /api/v3/clients                       # Get all clients
GET    /api/v3/clients/{mac}                 # Get specific client
POST   /api/v3/clients/filter                # Apply filters
```

#### Handshakes
```bash
GET    /api/v3/handshakes                    # Get all handshakes
GET    /api/v3/handshakes/{id}               # Get specific handshake
POST   /api/v3/handshakes/{id}/crack         # Start cracking
DELETE /api/v3/handshakes/{id}               # Delete handshake
```

**Example:**
```bash
# Start cracking handshake with custom wordlist
curl -X POST http://localhost:5555/api/v3/handshakes/123/crack \
  -H "Content-Type: application/json" \
  -d '{"wordlist": "/usr/share/wordlists/rockyou.txt"}'
```

---

### 5. System Operations (15+ endpoints)

#### Monitor Mode
```bash
GET    /api/v3/system/monitor/status         # Check monitor mode
POST   /api/v3/system/monitor/enable         # Enable monitor mode
POST   /api/v3/system/monitor/disable        # Disable monitor mode
GET    /api/v3/system/interfaces             # List interfaces
```

**Example:**
```bash
# Enable monitor mode on wlan0
curl -X POST http://localhost:5555/api/v3/system/monitor/enable \
  -H "Content-Type: application/json" \
  -d '{"interface": "wlan0"}'
```

---

### 6. Configuration Management (10+ endpoints)

```bash
GET    /api/v3/config                        # Get all configuration
GET    /api/v3/config/{key}                  # Get specific value
POST   /api/v3/config/{key}                  # Set value
POST   /api/v3/config/reset                  # Reset to defaults
```

**Configuration Keys:**
- `app.theme` - UI theme
- `wifi.interface` - WiFi interface
- `gps.source` - GPS source
- `attack.timeout` - Attack timeout
- `scanner.channel_hop` - Channel hopping
- `api.auth_required` - API authentication

**Example:**
```bash
# Set theme
curl -X POST http://localhost:5555/api/v3/config/app.theme \
  -H "Content-Type: application/json" \
  -d '{"value": "hacker"}'

# Get current theme
curl http://localhost:5555/api/v3/config/app.theme
```

---

### 7. File Operations (15+ endpoints)

```bash
GET    /api/v3/files/captures                # List capture files
GET    /api/v3/files/captures/{id}/download  # Download capture
DELETE /api/v3/files/captures/{id}           # Delete capture

GET    /api/v3/files/logs                    # List log files
GET    /api/v3/files/logs/{id}/download      # Download log
GET    /api/v3/files/logs/tail               # Tail current log

POST   /api/v3/files/export/csv              # Export to CSV
POST   /api/v3/files/export/wigle            # Export to WiGLE format
POST   /api/v3/files/export/kismet           # Export to Kismet format
POST   /api/v3/files/export/json             # Export to JSON

GET    /api/v3/files/sessions                # List scan sessions
GET    /api/v3/files/sessions/{id}           # Get session details
```

**Example:**
```bash
# Export networks to CSV
curl -X POST http://localhost:5555/api/v3/files/export/csv \
  -o networks_export.csv
```

---

### 8. Analytics (10+ endpoints)

```bash
GET    /api/v3/analytics/summary             # Analytics summary
GET    /api/v3/analytics/encryption          # Encryption statistics
GET    /api/v3/analytics/manufacturers       # Manufacturer distribution
GET    /api/v3/analytics/channels            # Channel distribution
GET    /api/v3/analytics/timeline            # Timeline data
```

**Example:**
```bash
curl http://localhost:5555/api/v3/analytics/summary | jq
```

**Response:**
```json
{
  "success": true,
  "data": {
    "networks": {
      "total": 1250,
      "wpa": 980,
      "open": 120,
      "wps_enabled": 450
    },
    "clients": {
      "total": 3500
    },
    "handshakes": {
      "total": 125,
      "cracked": 45
    }
  }
}
```

---

## WebSocket Events

Connect to `ws://localhost:5555/ws/events` for real-time updates.

**Event Types:**
- `network_discovered` - New network found
- `handshake_captured` - Handshake captured
- `attack_started` - Attack initiated
- `attack_completed` - Attack finished
- `gps_updated` - GPS location changed
- `service_status` - Service status changed

**Example (Python):**
```python
import websocket
import json

def on_message(ws, message):
    event = json.loads(message)
    print(f"Event: {event['type']}")
    print(f"Data: {event['data']}")

ws = websocket.WebSocketApp(
    "ws://localhost:5555/ws/events",
    on_message=on_message
)
ws.run_forever()
```

---

## Response Format

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2025-11-03T12:00:00Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2025-11-03T12:00:00Z"
}
```

**Common Error Codes:**
- `AUTH_REQUIRED` - Authentication required (401)
- `NOT_FOUND` - Resource not found (404)
- `MISSING_PARAM` - Missing required parameter (400)
- `INVALID_SOURCE` - Invalid parameter value (400)
- `*_ERROR` - General error (500)

---

## Rate Limiting

**Default:** 100 requests per minute per IP

**Headers:**
- `X-RateLimit-Limit` - Request limit
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Reset time (Unix timestamp)

**429 Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT",
  "retry_after": 60
}
```

---

## Complete Curl Examples

### Scan and Attack Workflow
```bash
# 1. Start all services
curl -X POST http://localhost:5555/api/v3/services/start

# 2. Start WiFi scanner
curl -X POST http://localhost:5555/api/v3/services/scanner/start \
  -H "Content-Type: application/json" \
  -d '{"interface": "wlan0mon"}'

# 3. Wait for networks to be discovered (5 seconds)
sleep 5

# 4. Get networks with WPS enabled
curl -X POST http://localhost:5555/api/v3/networks/filter \
  -H "Content-Type: application/json" \
  -d '{"wps_enabled": true, "min_signal": -70}' \
  | jq '.data.networks[0]'

# 5. Get network details
BSSID="AA:BB:CC:DD:EE:FF"
curl http://localhost:5555/api/v3/networks/$BSSID | jq

# 6. Start WPS Pixie Dust attack
curl -X POST http://localhost:5555/api/v3/attacks/wps/pixie \
  -H "Content-Type: application/json" \
  -d "{\"bssid\": \"$BSSID\"}"

# 7. Check attack status
curl http://localhost:5555/api/v3/attacks/wps/status

# 8. Get analytics
curl http://localhost:5555/api/v3/analytics/summary | jq
```

---

## Testing

Run the comprehensive test suite:
```bash
python3 tests/test_api_v3.py
```

Test output shows pass/fail for all endpoint categories.

---

## Python Client Library Example

```python
import requests

class GattroseAPI:
    def __init__(self, base_url="http://localhost:5555", api_key=None):
        self.base_url = base_url
        self.api_key = api_key

    def _headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    def get_status(self):
        """Get system status"""
        response = requests.get(
            f"{self.base_url}/api/v3/status",
            headers=self._headers()
        )
        return response.json()

    def get_networks(self, limit=100, **filters):
        """Get networks with optional filters"""
        if filters:
            response = requests.post(
                f"{self.base_url}/api/v3/networks/filter",
                headers=self._headers(),
                json=filters
            )
        else:
            response = requests.get(
                f"{self.base_url}/api/v3/networks",
                headers=self._headers(),
                params={'limit': limit}
            )
        return response.json()

    def start_scanner(self, interface="wlan0mon", channel=None):
        """Start WiFi scanner"""
        response = requests.post(
            f"{self.base_url}/api/v3/services/scanner/start",
            headers=self._headers(),
            json={'interface': interface, 'channel': channel}
        )
        return response.json()

# Usage
api = GattroseAPI()
status = api.get_status()
print(f"System running: {status['data']['system']['running']}")

networks = api.get_networks(limit=10, wps_enabled=True)
print(f"Found {len(networks['data']['networks'])} WPS networks")
```

---

## Security Considerations

1. **Localhost Only** - API only listens on 127.0.0.1 by default
2. **API Key Authentication** - Optional but recommended for production
3. **Rate Limiting** - Prevents abuse (100 req/min)
4. **No External Access** - Not exposed to network by default
5. **Log All Requests** - All API calls are logged

**To enable remote access (not recommended):**
```python
# In local_api_v3.py, change:
self.app.run(host='0.0.0.0', port=5555)
```

---

## Troubleshooting

### API Not Starting
```bash
# Check if port 5555 is available
sudo netstat -tlnp | grep 5555

# Check logs
tail -f data/logs/gattrose.log
```

### Authentication Errors
```bash
# Disable authentication
python3 -c "from src.utils.config_db import DBConfig; c = DBConfig(); c.set('api.auth_required', False)"

# Or set valid API key
export GATTROSE_API_KEY="your_key_here"
```

### Rate Limit Issues
```bash
# Increase rate limit in local_api_v3.py:
default_limits=["1000 per minute"]  # Increase from 100
```

---

## Support

- **Documentation:** `/docs/API_v3_Documentation.md`
- **Examples:** `/examples/api_automation.py`
- **Tests:** `/tests/test_api_v3.py`
- **Issues:** Report on GitHub

---

## Changelog

### v3.0.0 (2025-11-03)
- ✅ Complete rewrite with 120+ endpoints
- ✅ Added WebSocket support
- ✅ Added authentication & rate limiting
- ✅ Added comprehensive documentation
- ✅ Added test suite
- ✅ Made fully headless-capable

### v2.0.0 (Previous)
- Basic endpoints (12 GUI control endpoints)
- Flipper Zero integration
- Scanner control

---

**API v3.0 makes Gattrose-NG fully controllable via REST API - perfect for automation, scripts, and headless deployments!**
