# Gattrose-NG API Testing Plan

## Prerequisites

1. **Start Gattrose:**
   ```bash
   sudo ./gattrose-ng.py
   ```

2. **Verify API is running:**
   ```bash
   curl http://127.0.0.1:5555/api/status
   ```

3. **Ensure Flipper Zero is connected via USB**

---

## Test Suite Overview

### Quick Automated Test
```bash
./test_api.sh
```
Runs all tests automatically (takes ~30 seconds)

### Interactive Test
```bash
./test_individual.sh
```
Runs tests one-by-one with pauses (you can see each result)

---

## Individual Test Commands

### 1. API Documentation
**Purpose:** Verify API is responding and get endpoint list

**Command:**
```bash
curl http://127.0.0.1:5555/api/docs | python3 -m json.tool
```

**Expected Output:**
```json
{
  "success": true,
  "message": "Gattrose-NG Local API",
  "version": "1.0.0",
  "endpoints": {
    "Status & Info": {...},
    "Scanner Control": {...},
    "Flipper Zero": {...}
  }
}
```

**Pass Criteria:** ✅ Returns JSON with success=true and endpoint list

---

### 2. Status Check
**Purpose:** Get current Gattrose state

**Command:**
```bash
curl http://127.0.0.1:5555/api/status | python3 -m json.tool
```

**Expected Output:**
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

**Pass Criteria:** ✅ Returns status with running=true

---

### 3. Connect to Flipper Zero
**Purpose:** Establish connection with Flipper device

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/connect | python3 -m json.tool
```

**Expected Output:**
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

**Pass Criteria:** ✅ Returns success=true with device info
**Physical Check:** Flipper screen should show connection activity

---

### 4. Get Flipper Device Info
**Purpose:** Retrieve detailed hardware/firmware information

**Command:**
```bash
curl http://127.0.0.1:5555/api/flipper/info | python3 -m json.tool
```

**Expected Output:**
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

**Pass Criteria:** ✅ Returns detailed device information

---

### 5. Blink LED (Blue)
**Purpose:** Test LED control

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/led \
  -H "Content-Type: application/json" \
  -d '{"color": "blue", "duration": 2}' | python3 -m json.tool
```

**Expected Output:**
```json
{
  "success": true,
  "message": "LED blinked blue for 2s"
}
```

**Pass Criteria:** ✅ Returns success=true
**Physical Check:** 💡 Flipper LED blinks BLUE for 2 seconds

---

### 6. Blink LED (Red)
**Purpose:** Test different LED color

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/led \
  -H "Content-Type: application/json" \
  -d '{"color": "red", "duration": 1}' | python3 -m json.tool
```

**Pass Criteria:** ✅ Returns success=true
**Physical Check:** 💡 Flipper LED blinks RED for 1 second

---

### 7. Blink LED (Green)
**Purpose:** Test another LED color

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/led \
  -H "Content-Type: application/json" \
  -d '{"color": "green", "duration": 1}' | python3 -m json.tool
```

**Pass Criteria:** ✅ Returns success=true
**Physical Check:** 💡 Flipper LED blinks GREEN for 1 second

---

### 8. Vibrate Flipper
**Purpose:** Test vibration motor control

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/vibrate \
  -H "Content-Type: application/json" \
  -d '{"duration": 1}' | python3 -m json.tool
```

**Expected Output:**
```json
{
  "success": true,
  "message": "Vibrated for 1s"
}
```

**Pass Criteria:** ✅ Returns success=true
**Physical Check:** 📳 Flipper vibrates for 1 second

---

### 9. Send Custom Command (device_info)
**Purpose:** Test raw command sending

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/command \
  -H "Content-Type: application/json" \
  -d '{"command": "device_info"}' | python3 -m json.tool
```

**Expected Output:**
```json
{
  "success": true,
  "command": "device_info",
  "response": "device_info\ndevice_info_major: 2\n..."
}
```

**Pass Criteria:** ✅ Returns command response with device info

---

### 10. LED Control via Raw Command (Green On)
**Purpose:** Test raw LED command

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/command \
  -H "Content-Type: application/json" \
  -d '{"command": "led 0 255 0"}' | python3 -m json.tool
```

**Pass Criteria:** ✅ Returns success=true
**Physical Check:** 💡 Flipper LED turns GREEN and stays on

---

### 11. LED Control via Raw Command (Off)
**Purpose:** Turn LED off with raw command

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/command \
  -H "Content-Type: application/json" \
  -d '{"command": "led 0 0 0"}' | python3 -m json.tool
```

**Pass Criteria:** ✅ Returns success=true
**Physical Check:** 💡 Flipper LED turns OFF

---

### 12. Start WiFi Scanner
**Purpose:** Begin network discovery

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/scanner/start | python3 -m json.tool
```

**Expected Output:**
```json
{
  "success": true,
  "message": "Scanner started",
  "interface": "wlp7s0mon"
}
```

**Pass Criteria:** ✅ Returns success=true with interface name
**GUI Check:** Scanner tab in Gattrose should show "Scanning..."

---

### 13. Status During Scan
**Purpose:** Verify scanner state change

**Command:**
```bash
curl http://127.0.0.1:5555/api/status | python3 -m json.tool
```

**Expected Output:**
```json
{
  "success": true,
  "data": {
    "running": true,
    "scanner_active": true,  // ← Should be true now
    "monitor_interface": "wlp7s0mon",
    "flipper_connected": true,
    "ap_count": 42,  // ← Should be > 0
    "client_count": 15  // ← Should be > 0
  }
}
```

**Pass Criteria:** ✅ scanner_active=true, ap_count > 0

---

### 14. Get Discovered Networks
**Purpose:** Retrieve scanned WiFi networks

**Command:**
```bash
curl http://127.0.0.1:5555/api/scanner/networks | python3 -m json.tool
```

**Expected Output:**
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

**Pass Criteria:** ✅ Returns array of networks with count > 0

---

### 15. Get Discovered Clients
**Purpose:** Retrieve discovered client devices

**Command:**
```bash
curl http://127.0.0.1:5555/api/scanner/clients | python3 -m json.tool
```

**Expected Output:**
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

**Pass Criteria:** ✅ Returns array of clients

---

### 16. Stop WiFi Scanner
**Purpose:** Stop network scanning

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/scanner/stop | python3 -m json.tool
```

**Expected Output:**
```json
{
  "success": true,
  "message": "Scanner stopped"
}
```

**Pass Criteria:** ✅ Returns success=true
**GUI Check:** Scanner tab should show "Stopped"

---

### 17. Disconnect Flipper
**Purpose:** Close Flipper connection

**Command:**
```bash
curl -X POST http://127.0.0.1:5555/api/flipper/disconnect | python3 -m json.tool
```

**Expected Output:**
```json
{
  "success": true,
  "message": "Disconnected from Flipper Zero"
}
```

**Pass Criteria:** ✅ Returns success=true
**Physical Check:** Flipper screen shows disconnection

---

### 18. Final Status Check
**Purpose:** Verify clean state after tests

**Command:**
```bash
curl http://127.0.0.1:5555/api/status | python3 -m json.tool
```

**Expected Output:**
```json
{
  "success": true,
  "data": {
    "running": true,
    "scanner_active": false,  // ← Should be false
    "monitor_interface": "wlp7s0mon",
    "flipper_connected": false,  // ← Should be false
    "ap_count": 42,  // ← Retains count
    "client_count": 15
  }
}
```

**Pass Criteria:** ✅ scanner_active=false, flipper_connected=false

---

## Additional Tests

### Test 19: Deauth Attack (Optional)
**Purpose:** Test attack functionality

**⚠️ WARNING:** Only test on YOUR OWN devices!

**Command:**
```bash
# First, get a client MAC from scanner/clients
curl http://127.0.0.1:5555/api/scanner/clients | python3 -m json.tool

# Then deauth (replace with actual MAC)
curl -X POST http://127.0.0.1:5555/api/attack/deauth \
  -H "Content-Type: application/json" \
  -d '{"mac": "AA:BB:CC:DD:EE:FF"}' | python3 -m json.tool
```

**Pass Criteria:** ✅ Returns success=true
**Physical Check:** Target device disconnects from WiFi

---

## Test Results Summary

| Test # | Endpoint | Status | Physical Effect |
|--------|----------|--------|-----------------|
| 1 | GET /api/docs | ⏳ | None |
| 2 | GET /api/status | ⏳ | None |
| 3 | POST /api/flipper/connect | ⏳ | Flipper screen activity |
| 4 | GET /api/flipper/info | ⏳ | None |
| 5 | POST /api/flipper/led (blue) | ⏳ | 💡 Blue LED |
| 6 | POST /api/flipper/led (red) | ⏳ | 💡 Red LED |
| 7 | POST /api/flipper/led (green) | ⏳ | 💡 Green LED |
| 8 | POST /api/flipper/vibrate | ⏳ | 📳 Vibration |
| 9 | POST /api/flipper/command | ⏳ | Depends on command |
| 10 | Raw LED command (on) | ⏳ | 💡 Green LED stays on |
| 11 | Raw LED command (off) | ⏳ | 💡 LED turns off |
| 12 | POST /api/scanner/start | ⏳ | Scanner GUI updates |
| 13 | GET /api/status (active) | ⏳ | None |
| 14 | GET /api/scanner/networks | ⏳ | None |
| 15 | GET /api/scanner/clients | ⏳ | None |
| 16 | POST /api/scanner/stop | ⏳ | Scanner GUI stops |
| 17 | POST /api/flipper/disconnect | ⏳ | Flipper screen update |
| 18 | GET /api/status (final) | ⏳ | None |

**Legend:** ⏳ Pending | ✅ Pass | ❌ Fail

---

## Running the Tests

### Option 1: Automated (Fast)
```bash
sudo ./gattrose-ng.py  # In terminal 1
./test_api.sh          # In terminal 2
```

### Option 2: Interactive (Detailed)
```bash
sudo ./gattrose-ng.py     # In terminal 1
./test_individual.sh      # In terminal 2
```

### Option 3: Manual (One by one)
Copy commands from above and run individually

---

## Troubleshooting

### API not responding
```bash
# Check if Gattrose is running
ps aux | grep gattrose

# Check API port
netstat -tlnp | grep 5555
```

### Flipper not connecting
```bash
# Check USB connection
lsusb | grep -i "STM\|Flipper"

# Check serial port
ls -la /dev/ttyACM*
```

### Scanner not finding networks
```bash
# Check monitor interface
iw dev | grep monitor

# Check if scanning
ps aux | grep airodump
```

---

**Ready to test!** Start Gattrose and run `./test_api.sh` or `./test_individual.sh`
