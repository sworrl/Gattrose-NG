# Gattrose-NG Local API

**Automated testing and control API for Gattrose-NG**

The Local API server starts automatically when Gattrose launches, listening on `http://127.0.0.1:5555` (localhost only for security).

---

## Quick Start

### 1. Start Gattrose
```bash
sudo ./gattrose-ng.py
```

The Local API will automatically start and show:
```
[+] Local API server started on http://127.0.0.1:5555
[i] API docs: http://127.0.0.1:5555/api/docs
```

### 2. Test the API
```bash
# Get API documentation
curl http://127.0.0.1:5555/api/docs | python3 -m json.tool

# Or run the full test suite
./test_api.sh
```

---

## API Endpoints

### Status & Information

#### **GET** `/api/status`
Get current Gattrose status

**Response:**
```json
{
  "success": true,
  "data": {
    "running": true,
    "scanner_active": false,
    "monitor_interface": "wlp7s0mon",
    "flipper_connected": false,
    "ap_count": 0,
    "client_count": 0
  }
}
```

**Example:**
```bash
curl http://127.0.0.1:5555/api/status
```

---

### Scanner Control

#### **POST** `/api/scanner/start`
Start WiFi scanning

**Response:**
```json
{
  "success": true,
  "message": "Scanner started",
  "interface": "wlp7s0mon"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:5555/api/scanner/start
```

---

#### **POST** `/api/scanner/stop`
Stop WiFi scanning

**Response:**
```json
{
  "success": true,
  "message": "Scanner stopped"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:5555/api/scanner/stop
```

---

#### **GET** `/api/scanner/networks`
Get all discovered networks

**Response:**
```json
{
  "success": true,
  "count": 42,
  "data": [
    {
      "bssid": "AA:BB:CC:DD:EE:FF",
      "ssid": "MyNetwork",
      "channel": "6",
      "encryption": "WPA2",
      "power": "-45",
      "wps_enabled": false,
      "client_count": 3,
      "vendor": "TP-Link",
      "device_type": "Wireless Router/AP"
    }
  ]
}
```

**Example:**
```bash
curl http://127.0.0.1:5555/api/scanner/networks
```

---

#### **GET** `/api/scanner/clients`
Get all discovered clients

**Response:**
```json
{
  "success": true,
  "count": 15,
  "data": [
    {
      "mac": "11:22:33:44:55:66",
      "bssid": "AA:BB:CC:DD:EE:FF",
      "power": "-55",
      "packets": 234,
      "probed_essids": ["HomeWiFi"],
      "vendor": "Apple",
      "device_type": "iPhone/iPad"
    }
  ]
}
```

**Example:**
```bash
curl http://127.0.0.1:5555/api/scanner/clients
```

---

### Flipper Zero Control

#### **POST** `/api/flipper/connect`
Connect to Flipper Zero

**Request Body (optional):**
```json
{
  "port": "/dev/ttyACM0"
}
```

Leave empty for auto-detection.

**Response:**
```json
{
  "success": true,
  "message": "Connected to Flipper Zero",
  "device": {
    "name": "Ur3nak0",
    "model": "Flipper Zero",
    "uid": "9877E90027E18000",
    "firmware": "Momentum mntm-011",
    "port": "/dev/ttyACM0"
  }
}
```

**Examples:**
```bash
# Auto-detect
curl -X POST http://127.0.0.1:5555/api/flipper/connect

# Specific port
curl -X POST http://127.0.0.1:5555/api/flipper/connect \
  -H "Content-Type: application/json" \
  -d '{"port": "/dev/ttyACM0"}'
```

---

#### **POST** `/api/flipper/disconnect`
Disconnect from Flipper Zero

**Response:**
```json
{
  "success": true,
  "message": "Disconnected from Flipper Zero"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/disconnect
```

---

#### **POST** `/api/flipper/command`
Send raw command to Flipper

**Request Body:**
```json
{
  "command": "device_info"
}
```

**Response:**
```json
{
  "success": true,
  "command": "device_info",
  "response": "device_info\nhardware_model: Flipper Zero\n..."
}
```

**Examples:**
```bash
# Get device info
curl -X POST http://127.0.0.1:5555/api/flipper/command \
  -H "Content-Type: application/json" \
  -d '{"command": "device_info"}'

# Turn LED blue
curl -X POST http://127.0.0.1:5555/api/flipper/command \
  -H "Content-Type: application/json" \
  -d '{"command": "led 0 0 255"}'

# Turn LED off
curl -X POST http://127.0.0.1:5555/api/flipper/command \
  -H "Content-Type: application/json" \
  -d '{"command": "led 0 0 0"}'
```

---

#### **POST** `/api/flipper/led`
Blink Flipper LED

**Request Body:**
```json
{
  "color": "blue",
  "duration": 2
}
```

**Colors:** `red`, `green`, `blue`, `yellow`, `cyan`, `magenta`, `white`

**Response:**
```json
{
  "success": true,
  "message": "LED blinked blue for 2s"
}
```

**Examples:**
```bash
# Blue LED for 2 seconds
curl -X POST http://127.0.0.1:5555/api/flipper/led \
  -H "Content-Type: application/json" \
  -d '{"color": "blue", "duration": 2}'

# Red LED for 5 seconds
curl -X POST http://127.0.0.1:5555/api/flipper/led \
  -H "Content-Type: application/json" \
  -d '{"color": "red", "duration": 5}'
```

---

#### **POST** `/api/flipper/vibrate`
Vibrate Flipper

**Request Body:**
```json
{
  "duration": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Vibrated for 1s"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/vibrate \
  -H "Content-Type: application/json" \
  -d '{"duration": 2}'
```

---

#### **GET** `/api/flipper/info`
Get detailed Flipper device information

**Response:**
```json
{
  "success": true,
  "data": {
    "hardware_model": "Flipper Zero",
    "hardware_uid": "9877E90027E18000",
    "hardware_name": "Ur3nak0",
    "firmware_version": "mntm-011",
    "firmware_origin_fork": "Momentum",
    "radio_alive": "true",
    "radio_ble_mac": "9877E926E180"
  }
}
```

**Example:**
```bash
curl http://127.0.0.1:5555/api/flipper/info
```

---

### Attack Operations

#### **POST** `/api/attack/deauth`
Launch deauth attack on client

**Request Body:**
```json
{
  "mac": "AA:BB:CC:DD:EE:FF"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Deauth attack launched on AA:BB:CC:DD:EE:FF"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:5555/api/attack/deauth \
  -H "Content-Type: application/json" \
  -d '{"mac": "AA:BB:CC:DD:EE:FF"}'
```

---

## Complete Testing Workflow

```bash
#!/bin/bash
# Complete API test workflow

API="http://127.0.0.1:5555"

# 1. Check status
echo "1. Checking status..."
curl -s "$API/api/status" | python3 -m json.tool

# 2. Connect to Flipper
echo "2. Connecting to Flipper Zero..."
curl -s -X POST "$API/api/flipper/connect" | python3 -m json.tool

# 3. Blink LED
echo "3. Blinking Flipper LED..."
curl -s -X POST "$API/api/flipper/led" \
  -H "Content-Type: application/json" \
  -d '{"color": "blue", "duration": 2}' | python3 -m json.tool

# 4. Start scanner
echo "4. Starting WiFi scanner..."
curl -s -X POST "$API/api/scanner/start" | python3 -m json.tool

# 5. Wait for networks
echo "5. Waiting 5 seconds for networks..."
sleep 5

# 6. Get networks
echo "6. Getting discovered networks..."
curl -s "$API/api/scanner/networks" | python3 -m json.tool

# 7. Stop scanner
echo "7. Stopping scanner..."
curl -s -X POST "$API/api/scanner/stop" | python3 -m json.tool

# 8. Disconnect Flipper
echo "8. Disconnecting Flipper..."
curl -s -X POST "$API/api/flipper/disconnect" | python3 -m json.tool

echo "Done!"
```

---

## Python Example

```python
import requests

API = "http://127.0.0.1:5555"

# Get status
response = requests.get(f"{API}/api/status")
print(response.json())

# Connect to Flipper
response = requests.post(f"{API}/api/flipper/connect")
print(response.json())

# Blink LED
response = requests.post(
    f"{API}/api/flipper/led",
    json={"color": "blue", "duration": 2}
)
print(response.json())

# Start scanner
response = requests.post(f"{API}/api/scanner/start")
print(response.json())

# Wait for networks
import time
time.sleep(5)

# Get networks
response = requests.get(f"{API}/api/scanner/networks")
networks = response.json()
print(f"Found {networks['count']} networks")

# Stop scanner
response = requests.post(f"{API}/api/scanner/stop")
print(response.json())

# Disconnect Flipper
response = requests.post(f"{API}/api/flipper/disconnect")
print(response.json())
```

---

## Security Notes

- **Localhost only:** API only listens on `127.0.0.1` (not accessible from network)
- **No authentication:** For local testing only
- **Auto-start:** Starts automatically with Gattrose
- **Thread-safe:** Can be called from multiple scripts simultaneously

---

## Troubleshooting

### API not responding
```bash
# Check if Gattrose is running
ps aux | grep gattrose

# Check if port 5555 is listening
netstat -tlnp | grep 5555
```

### Port already in use
Edit `src/gui/main_window.py` line 8841 to change the port:
```python
self.local_api = LocalAPIServer(self, port=5556)  # Changed port
```

### Connection errors
Make sure to use `127.0.0.1` not `localhost`:
```bash
# ✓ Correct
curl http://127.0.0.1:5555/api/status

# ✗ May not work
curl http://localhost:5555/api/status
```

---

## Test Suite

Run the automated test suite:
```bash
./test_api.sh
```

This will:
1. Get API documentation
2. Check Gattrose status
3. Connect to Flipper Zero
4. Get Flipper device info
5. Blink LED
6. Vibrate Flipper
7. Send custom commands
8. Start WiFi scanner
9. Get discovered networks and clients
10. Stop scanner
11. Disconnect Flipper

---

**Happy testing!** 🚀
