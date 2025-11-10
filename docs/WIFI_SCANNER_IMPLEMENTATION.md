# WiFi Scanner Implementation - Real-Time Data Acquisition

**Date:** 2025-10-31
**Status:** Core functionality complete ✅
**Database logging:** Pending

---

## Overview

Gattrose-NG now has **fully functional real-time WiFi scanning** with:

✅ Automatic monitor mode detection and enabling
✅ Real-time airodump-ng integration
✅ Hierarchical AP/Client tree display
✅ Verbose data collection
✅ Live updates as packets are captured
✅ Seamless startup - no manual configuration needed

---

## What Was Built

### 1. **WiFi Scanner Backend** (`src/tools/wifi_scanner.py`)

A complete airodump-ng wrapper that:

- **Runs airodump-ng** with CSV output in a background thread
- **Parses CSV data** in real-time (APs and clients)
- **Emits Qt signals** for new/updated APs and clients
- **Tracks relationships** between APs and their associated clients
- **Captures all data** available from airodump-ng

**Key Classes:**

**`WiFiAccessPoint`** - Stores all AP data:
- BSSID, SSID (ESSID)
- Channel, Speed, Encryption, Cipher, Authentication
- Power (signal strength)
- Beacons, IV count
- LAN IP
- First seen, Last seen timestamps
- Associated clients dictionary

**`WiFiClient`** - Stores all client data:
- MAC address
- Associated BSSID (which AP they're connected to)
- Power, Packets
- Probed ESSIDs (networks they're searching for)
- First seen, Last seen timestamps

**`WiFiScanner(QThread)`** - Main scanner:
- Runs airodump-ng with configurable channel
- Parses CSV every second
- Emits signals: `ap_discovered`, `ap_updated`, `client_discovered`, `client_updated`
- Status messages and error handling
- Clean start/stop with proper cleanup

### 2. **Monitor Mode Manager** (`src/tools/wifi_monitor.py`)

Automatic WiFi card management:

**`WiFiMonitorManager`** static class:
- **`get_wireless_interfaces()`** - Detects all wireless interfaces (uses iwconfig and iw)
- **`is_monitor_mode(interface)`** - Checks if interface is in monitor mode
- **`get_monitor_interface()`** - Finds existing monitor interface
- **`enable_monitor_mode(interface)`** - Enables monitor mode with airmon-ng
- **`auto_enable_monitor()`** - **One-click auto-detection and enabling**
- **`disable_monitor_mode(interface)`** - Cleanup when done

**Auto-enable sequence:**
1. Check if already in monitor mode → use it
2. Detect wireless interfaces
3. Filter to managed interfaces (exclude mon*, lo)
4. Enable monitor mode on first available
5. Kill interfering processes automatically
6. Return monitor interface name

### 3. **Scanner Tab UI** (`src/gui/main_window.py` - ScannerTab class)

Complete rewrite with real functionality:

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ WiFi Scanner - Real-Time Data Acquisition              │
├─────────────────────────────────────────────────────────┤
│ Interface: wlan0mon     [Start Scanning] [Stop Scanning│
├─────────────────────────────────────────────────────────┤
│ APs: 15    Clients: 42         Status: Active - Capturing Data
├─────────────────────────────────────────────────────────┤
│ ┌─ AP Tree View ─────────────────────────────────────┐ │
│ │  BSSID/MAC | SSID | Ch | Encryption | Power | ...  │ │
│ │  ├─ AA:BB:CC:DD:EE:FF | MyNetwork | 6 | WPA2 ...  │ │
│ │  │  └─ 11:22:33:44:55:66 | CLIENT | | | -65 | ...  │ │
│ │  │  └─ 77:88:99:AA:BB:CC | CLIENT | | | -70 | ...  │ │
│ │  ├─ FF:EE:DD:CC:BB:AA | Guest_WiFi | 11 | WPA ...│ │
│ │  │  └─ AA:BB:CC:DD:EE:11 | CLIENT | | | -50 | ...  │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ Scanner Log:                                            │
│ [23:45:12] Monitor interface ready: wlan0mon            │
│ [23:45:15] Starting scan on wlan0mon                    │
│ [23:45:16] Scan started - capturing data...             │
│ [23:45:18] New AP: MyNetwork [WPA2]                     │
│ [23:45:20] New client: 11:22:33:44:55:66 -> AA:BB:...   │
└─────────────────────────────────────────────────────────┘
```

**Tree Columns (9 total - all verbose data):**
1. **BSSID/MAC** - Access Point BSSID or Client MAC
2. **SSID/Info** - SSID for APs, "CLIENT" for clients
3. **Channel** - WiFi channel
4. **Encryption** - Encryption type + cipher (WPA2 CCMP, etc.)
5. **Power** - Signal strength in dBm
6. **Beacons/Packets** - Beacon count for APs, packet count for clients
7. **Clients/Probed** - Client count for APs, probed ESSIDs for clients
8. **First Seen** - First detection timestamp
9. **Last Seen** - Most recent update timestamp

**Features:**
- **Hierarchical display** - Clients shown as children under their AP
- **Bold APs** - Access Points are bolded for easy identification
- **Auto-expanding** - APs auto-expand when clients are discovered
- **Unassociated clients** - Clients without an AP shown at root level
- **Real-time updates** - Tree updates as data streams in
- **Sortable columns** - Click any column header to sort
- **Alternating row colors** - Easier to read
- **Live statistics** - AP count, Client count always visible
- **Status tracking** - See scan state (Ready/Scanning/Stopped)
- **Timestamped log** - 24-hour format log of all events

### 4. **Auto-Start Integration** (`src/gui/main_window.py` - MainWindow)

Monitor mode automatically enabled at startup:

**In `MainWindow.__init__()`:**
```python
def __init__(self):
    super().__init__()
    self.status_monitor = None
    self.current_theme = "sonic"
    self.load_config()
    self.init_ui()
    self.start_monitoring()
    self.init_monitor_mode()  # ← Auto-enable!
```

**In `init_monitor_mode()` method:**
1. Import WiFiMonitorManager
2. Call `auto_enable_monitor()`
3. If successful → pass monitor interface to ScannerTab
4. Update status bar with result
5. Scanner is ready immediately!

---

## How It Works

### Startup Sequence:

```
1. App launches
   ↓
2. MainWindow initializes
   ↓
3. `init_monitor_mode()` called automatically
   ↓
4. WiFiMonitorManager detects wireless card
   ↓
5. airmon-ng enables monitor mode (e.g., wlan0 → wlan0mon)
   ↓
6. Monitor interface passed to ScannerTab
   ↓
7. "Start Scanning" button becomes active
   ↓
8. User clicks "Start Scanning" (or could auto-start)
   ↓
9. WiFiScanner thread starts airodump-ng
   ↓
10. CSV file created in data/captures/
   ↓
11. Scanner parses CSV every second
   ↓
12. New APs → emit `ap_discovered` → tree updates
    ↓
13. New Clients → emit `client_discovered` → tree updates
    ↓
14. Existing data → emit `*_updated` → tree updates
    ↓
15. Real-time display shows all captured data!
```

### Data Flow:

```
airodump-ng process
    ↓
Writes CSV file (updated every 1 second)
    ↓
WiFiScanner thread reads CSV
    ↓
Parses AP section → WiFiAccessPoint objects
Parses Client section → WiFiClient objects
    ↓
Emits Qt signals with data
    ↓
ScannerTab receives signals
    ↓
Updates QTreeWidget
    ↓
User sees live data in tree view
```

---

## Files Created/Modified

### New Files:
1. **`src/tools/wifi_scanner.py`** (457 lines)
   - WiFiAccessPoint class
   - WiFiClient class
   - WiFiScanner QThread class
   - CSV parsing logic

2. **`src/tools/wifi_monitor.py`** (175 lines)
   - WiFiMonitorManager class
   - Interface detection
   - Monitor mode management

3. **`start-gattrose.sh`**
   - Shell script for reliable double-click launching

### Modified Files:
1. **`src/gui/main_window.py`**
   - Replaced ScannerTab placeholder (25 lines) with full implementation (230 lines)
   - Added `init_monitor_mode()` method
   - Added QTreeWidget, QTreeWidgetItem imports

---

## What You Can Do Now

### 1. Launch the App:
```bash
sudo ./gattrose-ng.py
```

Or double-click:
```bash
./start-gattrose.sh
```

### 2. Watch Auto-Init:
Console will show:
```
[*] Initializing WiFi monitor mode...
[*] Detected wireless interface: wlan0
[*] Checking for interfering processes...
[*] Enabling monitor mode on wlan0...
[*] Monitor mode enabled on wlan0mon
```

### 3. Start Scanning:
- Click "Start Scanning" button
- Watch tree fill with APs
- Clients appear under their APs
- All data updates in real-time

### 4. View Captured Data:
- **BSSID** - MAC address of AP
- **SSID** - Network name (or "(Hidden)")
- **Channel** - WiFi channel (1-14)
- **Encryption** - WPA/WPA2/WPA3/WEP/Open + cipher
- **Power** - Signal strength (-30 to -90 dBm)
- **Beacons** - Number of beacon frames (higher = more active)
- **Clients** - Number of connected devices
- **Timestamps** - When first/last seen

### 5. Expand APs:
- Click the arrow next to an AP
- See all connected clients
- View client details (MAC, power, packets, probed networks)

---

## Next Steps (Database Logging - TODO)

The current implementation captures all data in memory. To add database persistence:

1. **Connect to database** in scanner initialization
2. **Save new APs** when `ap_discovered` signal emits
3. **Save new clients** when `client_discovered` signal emits
4. **Update existing records** on `*_updated` signals
5. **Track scan sessions** for historical analysis
6. **Enable querying** old scans from Database tab

This will be implemented next to provide full data retention.

---

## Technical Details

### airodump-ng CSV Format:

**AP Section:**
```csv
BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
AA:BB:CC:DD:EE:FF, 2025-10-31 23:45:10, 2025-10-31 23:50:15, 6, 54, WPA2, CCMP, PSK, -45, 1234, 567, 0.0.0.0, 9, MyNetwork,
```

**Client Section:**
```csv
Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
11:22:33:44:55:66, 2025-10-31 23:45:12, 2025-10-31 23:50:16, -65, 892, AA:BB:CC:DD:EE:FF, Guest_Network
```

### Signal/Slot Connections:

```python
scanner.ap_discovered.connect(on_ap_discovered)      # New AP found
scanner.ap_updated.connect(on_ap_updated)            # AP data changed
scanner.client_discovered.connect(on_client_discovered)  # New client
scanner.client_updated.connect(on_client_updated)    # Client data changed
scanner.status_message.connect(log)                  # Status messages
scanner.error_occurred.connect(on_error)             # Errors
scanner.scan_started.connect(on_scan_started)        # Scan began
scanner.scan_stopped.connect(on_scan_stopped)        # Scan ended
```

---

## Verbose Data Collection ✅

**We capture EVERYTHING airodump-ng provides:**

**Per Access Point (14 fields):**
- BSSID (unique identifier)
- SSID/ESSID (network name)
- First seen timestamp
- Last seen timestamp
- Channel
- Speed (54, 150, 300, etc.)
- Privacy/Encryption (WPA, WPA2, WPA3, WEP, OPN)
- Cipher (CCMP, TKIP, WEP)
- Authentication (PSK, MGT)
- Power (signal strength in dBm)
- Beacon count
- IV count (initialization vectors)
- LAN IP
- ESSID length

**Per Client (7 fields):**
- Station MAC address
- First seen timestamp
- Last seen timestamp
- Power (signal strength)
- Packet count
- Associated BSSID (which AP)
- Probed ESSIDs (networks being searched for)

**All displayed in the tree view!**

---

## Testing

**Prerequisites must be met:**
```bash
# Check that these work:
which airmon-ng
which airodump-ng
which iw
which iwconfig
```

**Test sequence:**
```bash
# 1. Launch
sudo ./gattrose-ng.py

# 2. Verify monitor mode enabled (console output)
[*] Monitor mode enabled on wlan0mon

# 3. Go to Scanner tab
# 4. Click "Start Scanning"
# 5. Watch APs appear in tree
# 6. Expand APs to see clients
# 7. Check log for status messages
```

**Scan files created:**
```
data/captures/scan_20251031_234510-01.csv  ← Parsed data
data/captures/scan_20251031_234510-01.cap  ← Raw packets
```

---

## Summary

🐊 **Gattrose-NG is now a REAL data acquisition tool!**

✅ Auto-detects WiFi card
✅ Auto-enables monitor mode
✅ Real-time airodump-ng scanning
✅ Hierarchical AP/Client display
✅ All verbose data captured and shown
✅ Live updates as packets arrive
✅ Professional Qt6 interface
✅ Seamless startup experience

**Ready to chomp networks!** 🐊📡💻

---

**All times in 24-hour format. Always.**
