# Gattrose-NG Headless Mode Guide

## Overview

Gattrose-NG is now **fully headless-capable** with API v3.0! Run it on servers, Raspberry Pis, or any system without a GUI. Perfect for:

- 🚗 **Wardriving** - Automated WiFi scanning while driving
- 🏢 **Penetration Testing** - Automated security assessments
- 📊 **Network Monitoring** - Continuous WiFi surveillance
- 🤖 **Automation** - Script-driven reconnaissance
- ☁️ **Remote Operations** - Deploy on remote systems

---

## Quick Start

### 1. Install Dependencies

```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3 python3-pip aircrack-ng reaver

# Install Python dependencies
pip3 install flask flask-cors flask-limiter flask-sock sqlalchemy requests
```

### 2. Start Headless API Server

```bash
cd /home/eurrl/Documents/Code\ \&\ Scripts/gattrose-ng
python3 src/services/local_api_v3.py
```

**Output:**
```
======================================================================
Gattrose-NG API v3.0 - Headless Mode
======================================================================

[API v3] Initialized with 120 endpoints
[API v3] Default API key: gattrose_xxxxxxxxxxxx
[API v3] Server started on http://127.0.0.1:5555
[API v3] Documentation: http://127.0.0.1:5555/api/v3/docs
[API v3] WebSocket: ws://127.0.0.1:5555/ws/events
[API v3] Endpoints: 120

[*] API server running in headless mode
[*] Press Ctrl+C to stop
```

### 3. Test the API

```bash
# Check status
curl http://localhost:5555/api/v3/status

# Get documentation
curl http://localhost:5555/api/v3/docs | jq

# Run test suite
python3 tests/test_api_v3.py
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Gattrose-NG Headless                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐     ┌─────────────────────────────┐   │
│  │  API v3.0     │────▶│  Orchestrator Service       │   │
│  │  (REST/WS)    │     │  - Scanner Control          │   │
│  │  120+ endpoints│     │  - GPS Management           │   │
│  └───────────────┘     │  - Attack Coordination      │   │
│         │              │  - Database Management      │   │
│         │              └─────────────────────────────┘   │
│         │                                                 │
│         ▼                                                 │
│  ┌───────────────────────────────────────────────────┐   │
│  │           Core Services                            │   │
│  ├───────────────────────────────────────────────────┤   │
│  │ • WiFi Scanner  • GPS Service  • Triangulation   │   │
│  │ • Attack Engine • Database     • Event Manager   │   │
│  └───────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────────────────────────────────────────┐   │
│  │           Database (SQLite)                       │   │
│  │  Networks • Clients • Handshakes • Analytics      │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Features

### ✅ Complete API Control (120+ Endpoints)

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **Service Control** | 25+ | Start/stop services, configure components |
| **Attack Operations** | 30+ | Deauth, WPS, Evil Twin, Handshakes |
| **Network Management** | 20+ | Query, filter, blacklist networks |
| **System Operations** | 15+ | Monitor mode, interfaces, system info |
| **Configuration** | 10+ | Get/set all configuration values |
| **File Operations** | 15+ | Export, download, manage files |
| **Analytics** | 10+ | Statistics, summaries, reporting |
| **Real-time Events** | WebSocket | Live updates for scans and attacks |

### ✅ Authentication & Security

- **API Key Authentication** - Optional token-based auth
- **Rate Limiting** - 100 requests/minute (configurable)
- **Localhost Only** - Only accessible from 127.0.0.1 by default
- **Request Logging** - All API calls logged for audit

### ✅ Real-time WebSocket Events

Connect to `ws://localhost:5555/ws/events` for live updates:
- Network discovered
- Handshake captured
- Attack status changes
- GPS location updates
- Service status changes

---

## Usage Examples

### Example 1: Basic Wardriving

```bash
#!/bin/bash
# Simple wardriving automation

# Start services
curl -X POST http://localhost:5555/api/v3/services/start

# Start scanner on wlan0mon
curl -X POST http://localhost:5555/api/v3/services/scanner/start \
  -H "Content-Type: application/json" \
  -d '{"interface": "wlan0mon"}'

# Wait 10 minutes
sleep 600

# Export results to CSV
curl -X POST http://localhost:5555/api/v3/files/export/csv \
  -o wardrive_$(date +%Y%m%d_%H%M%S).csv

# Stop scanner
curl -X POST http://localhost:5555/api/v3/services/scanner/stop

echo "Wardriving complete! Results saved."
```

### Example 2: Automated WPS Testing

```bash
#!/bin/bash
# Find and test WPS-enabled networks

# Start services
curl -X POST http://localhost:5555/api/v3/services/start
sleep 3
curl -X POST http://localhost:5555/api/v3/services/scanner/start \
  -H "Content-Type: application/json" \
  -d '{"interface": "wlan0mon"}'

# Scan for 60 seconds
echo "Scanning for WPS networks..."
sleep 60

# Get WPS-enabled networks with good signal
NETWORKS=$(curl -X POST http://localhost:5555/api/v3/networks/filter \
  -H "Content-Type: application/json" \
  -d '{"wps_enabled": true, "min_signal": -70}' | jq -r '.data.networks[].bssid')

# Attack each WPS network
for BSSID in $NETWORKS; do
  echo "Attacking $BSSID with WPS Pixie Dust..."
  curl -X POST http://localhost:5555/api/v3/attacks/wps/pixie \
    -H "Content-Type: application/json" \
    -d "{\"bssid\": \"$BSSID\"}"
  sleep 120  # Wait 2 minutes per attack
done

# Get results
curl http://localhost:5555/api/v3/analytics/summary | jq

# Stop
curl -X POST http://localhost:5555/api/v3/services/scanner/stop
```

### Example 3: Python Automation

```python
from examples.api_automation import GattroseAPI
import time

# Initialize API client
api = GattroseAPI()

# Start services
api.start_services()
time.sleep(2)

# Start scanner
api.start_scanner(interface="wlan0mon")

# Scan for 60 seconds
print("Scanning...")
time.sleep(60)

# Get networks with WPA2 encryption
networks = api.get_networks(encryption="WPA2", min_signal=-70)
print(f"Found {len(networks['data']['networks'])} WPA2 networks")

# Capture handshakes for top 5
for net in networks['data']['networks'][:5]:
    print(f"Capturing handshake: {net['ssid']} ({net['bssid']})")
    api.capture_handshake(net['bssid'], timeout=120)
    time.sleep(120)

# Get summary
handshakes = api.get_handshakes()
print(f"Captured {handshakes['data']['count']} handshakes")

# Export results
api.export_csv("results.csv")

# Stop
api.stop_scanner()
```

### Example 4: Continuous Monitoring

```python
#!/usr/bin/env python3
# Monitor WiFi networks 24/7 and send alerts

from examples.api_automation import GattroseAPI
import time
import smtplib
from email.mime.text import MIMEText

api = GattroseAPI()

def send_alert(message):
    """Send email alert (configure SMTP settings)"""
    msg = MIMEText(message)
    msg['Subject'] = 'Gattrose Alert'
    msg['From'] = 'gattrose@localhost'
    msg['To'] = 'admin@example.com'

    # Send email (configure your SMTP server)
    # s = smtplib.SMTP('localhost')
    # s.send_message(msg)
    # s.quit()
    print(f"ALERT: {message}")

# Start monitoring
api.start_services()
time.sleep(2)
api.start_scanner(interface="wlan0mon")

print("Continuous monitoring started...")

known_networks = set()

while True:
    # Check for new networks every 30 seconds
    networks = api.get_networks(limit=1000)

    if networks and networks.get('success'):
        current_networks = {net['bssid'] for net in networks['data']['networks']}

        # Detect new networks
        new_networks = current_networks - known_networks
        if new_networks:
            send_alert(f"Detected {len(new_networks)} new networks")
            known_networks.update(new_networks)

        # Check for open networks
        open_nets = [n for n in networks['data']['networks']
                     if n['encryption'] == 'Open']
        if open_nets:
            send_alert(f"Warning: {len(open_nets)} open networks detected")

    # Get analytics
    analytics = api.get_analytics()
    if analytics:
        data = analytics['data']
        print(f"Status: {data['networks']['total']} networks, "
              f"{data['clients']['total']} clients")

    time.sleep(30)
```

---

## Configuration

### Environment Variables

```bash
# API Key (optional)
export GATTROSE_API_KEY="gattrose_your_custom_key"

# API Port (default: 5555)
export GATTROSE_API_PORT="5555"

# Database Path
export GATTROSE_DB_PATH="/path/to/gattrose.db"
```

### Config File

Configuration is stored in the database. Use the API to configure:

```bash
# Enable 24/7 scan mode
curl -X POST http://localhost:5555/api/v3/config/service.scan_24_7 \
  -H "Content-Type: application/json" \
  -d '{"value": true}'

# Set WiFi interface
curl -X POST http://localhost:5555/api/v3/config/wifi.interface \
  -H "Content-Type: application/json" \
  -d '{"value": "wlan0mon"}'

# Set GPS source
curl -X POST http://localhost:5555/api/v3/config/gps.source \
  -H "Content-Type: application/json" \
  -d '{"value": "phone-usb"}'
```

---

## Systemd Service (Run on Boot)

Create `/etc/systemd/system/gattrose.service`:

```ini
[Unit]
Description=Gattrose-NG Headless Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/eurrl/Documents/Code & Scripts/gattrose-ng
ExecStart=/usr/bin/python3 /home/eurrl/Documents/Code & Scripts/gattrose-ng/src/services/local_api_v3.py
Restart=always
RestartSec=10
Environment="GATTROSE_API_KEY=your_secure_key_here"

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable gattrose
sudo systemctl start gattrose
sudo systemctl status gattrose
```

**View logs:**
```bash
sudo journalctl -u gattrose -f
```

---

## Raspberry Pi Deployment

### Hardware Requirements
- Raspberry Pi 3/4/5 (recommended)
- WiFi adapter with monitor mode support
- USB GPS (optional, or use phone GPS via ADB)
- 16GB+ SD card

### Setup

1. **Install Raspberry Pi OS Lite** (headless)

2. **Install Gattrose:**
```bash
cd ~
git clone https://github.com/yourusername/gattrose-ng.git
cd gattrose-ng
sudo apt install -y python3-pip aircrack-ng
pip3 install -r requirements.txt
```

3. **Enable monitor mode on boot:**
```bash
# Add to /etc/rc.local (before exit 0)
ip link set wlan0 down
iw dev wlan0 set monitor control
ip link set wlan0 up
ip link set wlan0 name wlan0mon
```

4. **Start Gattrose API:**
```bash
python3 src/services/local_api_v3.py
```

5. **Access from laptop/phone:**
```bash
# If you enabled remote access
curl http://raspberrypi.local:5555/api/v3/status
```

---

## Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    aircrack-ng \
    wireless-tools \
    net-tools \
    iproute2 \
    reaver \
    && rm -rf /var/lib/apt/lists/*

# Copy application
WORKDIR /app
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose API port
EXPOSE 5555

# Run API server
CMD ["python3", "src/services/local_api_v3.py"]
```

**Build and run:**
```bash
# Build
docker build -t gattrose-ng .

# Run (requires host network and privileged mode for WiFi)
docker run -d \
  --name gattrose \
  --network host \
  --privileged \
  -v /dev:/dev \
  -v $(pwd)/data:/app/data \
  gattrose-ng
```

---

## API Client Libraries

### Python

Use the provided `GattroseAPI` class:
```python
from examples.api_automation import GattroseAPI
api = GattroseAPI()
networks = api.get_networks()
```

### Bash/Curl

```bash
# Helper function
api_get() {
  curl -s "http://localhost:5555$1" | jq
}

api_post() {
  curl -s -X POST "http://localhost:5555$1" \
    -H "Content-Type: application/json" \
    -d "$2" | jq
}

# Usage
api_get "/api/v3/networks"
api_post "/api/v3/services/scanner/start" '{"interface":"wlan0mon"}'
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

class GattroseAPI {
  constructor(baseURL = 'http://localhost:5555') {
    this.client = axios.create({ baseURL });
  }

  async getNetworks() {
    const response = await this.client.get('/api/v3/networks');
    return response.data;
  }

  async startScanner(interface = 'wlan0mon') {
    const response = await this.client.post('/api/v3/services/scanner/start', {
      interface
    });
    return response.data;
  }
}

// Usage
const api = new GattroseAPI();
api.getNetworks().then(data => console.log(data));
```

---

## Monitoring & Logging

### View API Logs
```bash
tail -f data/logs/gattrose.log
```

### Monitor via API
```bash
# Real-time status updates
watch -n 2 'curl -s http://localhost:5555/api/v3/analytics/summary | jq'
```

### WebSocket Monitoring
```python
import websocket
import json

def on_message(ws, message):
    event = json.loads(message)
    print(f"Event: {event['type']}")
    print(f"Data: {json.dumps(event['data'], indent=2)}")

ws = websocket.WebSocketApp(
    "ws://localhost:5555/ws/events",
    on_message=on_message
)
ws.run_forever()
```

---

## Troubleshooting

### API Not Starting

**Problem:** Port 5555 already in use
```bash
# Find and kill process
sudo lsof -i :5555
sudo kill -9 <PID>
```

**Problem:** Permission denied for monitor mode
```bash
# Run with sudo (not recommended)
sudo python3 src/services/local_api_v3.py

# Better: Add user to necessary groups
sudo usermod -a -G netdev $USER
```

### Scanner Not Working

**Problem:** No monitor interface
```bash
# Check interfaces
ip link show

# Enable monitor mode manually
sudo airmon-ng start wlan0
```

**Problem:** Scanner starts but no networks found
```bash
# Check channel
curl http://localhost:5555/api/v3/services/scanner/status

# Try channel hopping
curl -X POST http://localhost:5555/api/v3/services/scanner/hop \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Database Issues

**Problem:** Database locked
```bash
# Stop API server and vacuum
curl -X POST http://localhost:5555/api/v3/services/database/vacuum
```

**Problem:** Corrupted database
```bash
# Backup and restore
cp data/gattrose.db data/gattrose.db.backup
sqlite3 data/gattrose.db ".dump" | sqlite3 data/gattrose.db.new
mv data/gattrose.db.new data/gattrose.db
```

---

## Performance Tips

### 1. Optimize Database
```bash
# Vacuum regularly
curl -X POST http://localhost:5555/api/v3/services/database/vacuum

# Limit historical data
# Keep only last 30 days of observations
```

### 2. Reduce API Calls
- Use WebSocket for real-time updates instead of polling
- Batch requests when possible
- Increase scan intervals for long-term monitoring

### 3. Resource Limits
```bash
# Limit memory usage in systemd service
MemoryMax=512M
```

---

## Security Best Practices

1. **Enable Authentication** for production use
2. **Use HTTPS** if exposing API remotely (reverse proxy)
3. **Firewall Rules** - Only allow localhost access
4. **Regular Updates** - Keep dependencies updated
5. **Audit Logs** - Review API access logs regularly

---

## Example Use Cases

### 1. Pentesting Automation
```python
# Automated pentest workflow
api = GattroseAPI()
api.start_services()
api.start_scanner()

# Scan phase
time.sleep(300)

# Attack phase - prioritize by attack score
networks = api.get_networks(limit=100)
for net in sorted(networks['data']['networks'],
                  key=lambda x: x['attack_score'], reverse=True)[:10]:
    if net['wps_enabled']:
        api.start_wps_pixie(net['bssid'])
    else:
        api.capture_handshake(net['bssid'])

# Report phase
api.export_csv("pentest_results.csv")
```

### 2. Wardriving Fleet
Deploy on multiple vehicles/devices, aggregate data centrally.

### 3. Network Security Monitoring
Detect rogue APs, evil twins, and unauthorized networks.

### 4. WiFi Analytics Platform
Collect and analyze WiFi patterns for business intelligence.

---

## Resources

- **Full API Documentation:** `/docs/API_v3_Documentation.md`
- **Automation Examples:** `/examples/api_automation.py`
- **Test Suite:** `/tests/test_api_v3.py`
- **Source Code:** `/src/services/local_api_v3.py`

---

## Support

For issues, feature requests, or questions:
- Open an issue on GitHub
- Check the API documentation
- Review example scripts

---

**Gattrose-NG is now fully headless-capable! 🚀**
