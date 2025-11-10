# Changelog - November 1, 2024

## Major Update: Attack Scoring, Device Fingerprinting & Directory Reorganization

This update represents a significant overhaul of Gattrose-NG with new features, improved organization, and enhanced functionality.

---

## 🎯 New Features

### 1. Attack Scoring System
**File:** `src/tools/attack_scoring.py`

- **Intelligent vulnerability scoring** (0-100 scale)
- Considers multiple factors:
  - Encryption type (WEP=95, WPA=70, WPA2=40, WPA3=15, Open=100)
  - Authentication method (PSK, SAE, MGT)
  - WPS status (+40 points if enabled - CRITICAL vulnerability)
  - Signal strength (stronger = easier to attack, +0 to +20 points)
  - Active clients (+5 points - helps with handshake capture)
  - Hidden SSID (-3 points - slightly harder)
- **Risk levels**: CRITICAL (80-100), HIGH (60-79), MEDIUM (35-59), LOW (0-34)
- **24-bit RGB color gradients**: Smooth color transitions from green (secure) to red (vulnerable)
- **Automatic color calculation** based on score

### 2. WPS Detection
**Modified:** `src/tools/wifi_scanner.py`

- Parallel WPS scanning using `wash` tool
- Detects locked/unlocked WPS status
- Real-time updates when WPS is detected
- Automatic attack score recalculation when WPS found
- Background thread for non-blocking operation

### 3. Device Fingerprinting
**File:** `src/utils/mac_vendor.py`

- **MAC vendor lookup** with 200+ OUI database entries
  - Apple, Google, Samsung, Intel, Raspberry Pi
  - Ubiquiti, TP-Link, Netgear, Amazon, Sonos, Ring
  - And many more...
- **Device type identification** with confidence scoring
  - Smartphones (iPhone, Android, Galaxy)
  - Laptops and desktops
  - IoT devices (Echo, Nest, cameras, thermostats)
  - Network equipment (routers, APs, UniFi)
  - Gaming consoles (Xbox, PlayStation, Nintendo)
  - Smart TVs and streaming devices
  - Printers, speakers, and more
- **Confidence percentages** (0-100%)
- **Unicode device icons**:
  - 🌐 Routers/APs
  - 📱 Phones/Tablets
  - 💻 Laptops
  - 🖥️ Desktops
  - ⌚ Smartwatches
  - 🔊 Speakers
  - 📺 Smart TVs
  - 📷 Cameras
  - 🖨️ Printers
  - 🌡️ Thermostats
  - 🎮 Gaming Consoles
  - 🥧 Raspberry Pi
  - 💡 Smart/IoT Devices

### 4. Enhanced GUI Display
**Modified:** `src/gui/main_window.py`

#### New Column Layout:
```
Icon | BSSID/MAC | SSID/Info | Vendor | Device Type | Channel | Encryption |
Power | Attack Score | WPS | Beacons/Pkts | Clients | First Seen | Last Seen
```

#### Features:
- **Device icons** in first column
- **Vendor identification** for all devices
- **Device type** with confidence percentage
- **Attack score** with risk level (e.g., "85 - CRITICAL")
- **WPS status** (LOCKED/UNLOCKED)
- **Color-coded rows** based on attack scores
- **Adjustable text size** (6-20pt slider)
- **Historical data loading** from previous scans

### 5. GUI Sudo Elevation
**Files:** `config/com.gattrose.pkexec.policy`, `gattrose-ng.desktop`

- **PolicyKit integration** for GUI password prompts
- **No more terminal launching** required
- **Double-click to launch** with GUI password dialog
- Secure privilege elevation through pkexec

### 6. Database Schema Updates
**Modified:** `src/database/models.py`

#### Network Table Additions:
- `manufacturer` - Device vendor
- `device_type` - Specific device identification
- `device_confidence` - Confidence score (0-100)
- `current_attack_score` - Current vulnerability score
- `highest_attack_score` - Highest score ever recorded
- `lowest_attack_score` - Lowest score ever recorded
- `risk_level` - CRITICAL, HIGH, MEDIUM, LOW
- `wps_enabled` - Boolean
- `wps_locked` - Boolean
- `wps_version` - WPS version string

#### Client Table Additions:
- `manufacturer` - Device vendor
- `device_type` - Specific device identification
- `device_confidence` - Confidence score (0-100)
- `max_signal`, `min_signal`, `current_signal` - Signal strength tracking

---

## 📁 Directory Reorganization

### New Structure:
```
gattrose-ng/
├── gattrose-ng.py          # Main launcher (ROOT)
├── gattrose-ng.desktop     # Desktop launcher (ROOT)
├── README.md               # Project docs (ROOT)
├── LICENSE                 # GPL-3.0 (ROOT)
├── requirements.txt        # Dependencies (ROOT)
├── assets/                 # Images and icons
│   ├── gattrose-ng.png
│   └── gattrose-ng.svg
├── bin/                    # Scripts and utilities
│   ├── gattrose-daemon.py
│   ├── install.py
│   ├── launch-gattrose.sh
│   └── start-gattrose.sh
├── config/                 # Configuration files
│   ├── com.gattrose.pkexec.policy
│   └── gattrose-ng.service
├── docs/                   # All documentation
│   ├── INSTALLATION.md
│   ├── QUICKSTART.md
│   ├── NEW_FEATURES.md
│   ├── RECENT_UPDATES.md
│   └── ...
├── src/                    # Source code
├── data/                   # Data storage
└── logs/                   # Application logs
```

### Changes:
- ✅ Only essential files in root (launcher, desktop file, README, LICENSE)
- ✅ All documentation moved to `docs/`
- ✅ All images moved to `assets/`
- ✅ All scripts moved to `bin/`
- ✅ Service files moved to `config/`
- ✅ Clean, professional structure

---

## 📝 Documentation Updates

### Updated Files:
1. **README.md** - Complete rewrite with:
   - GPL-3.0 license information
   - Comprehensive feature list
   - Attack scoring system explanation
   - Device fingerprinting details
   - Professional formatting with badges
   - Clear usage examples
   - Ethical use guidelines

2. **LICENSE** - Full GPL-3.0 text (674 lines)

3. **docs/INSTALLATION.md** - Updated:
   - PolicyKit setup instructions
   - GUI launcher configuration
   - Updated file structure diagram
   - All paths corrected

4. **docs/NEW_FEATURES.md** - Comprehensive guide:
   - Attack scoring algorithm
   - Color gradient explanation
   - Device fingerprinting guide
   - WPS detection details
   - Usage examples

---

## 🔧 Technical Improvements

### Code Quality:
- All Python files pass syntax checks
- Proper import paths updated
- Clean module organization
- Comprehensive error handling
- Debug logging for troubleshooting

### Performance:
- Parallel WPS scanning (non-blocking)
- Efficient MAC vendor lookup
- Optimized color calculations
- Background device identification

### User Experience:
- Real-time visual feedback
- Color-coded vulnerability indicators
- Device type icons for quick recognition
- Confidence percentages for reliability
- Sortable columns for analysis
- Adjustable text size for accessibility

---

## 📊 Statistics

### Files Created:
- `src/tools/attack_scoring.py` (6KB)
- `src/utils/mac_vendor.py` (14KB)
- `config/com.gattrose.pkexec.policy` (825 bytes)
- `docs/INSTALLATION.md` (updated)
- `docs/NEW_FEATURES.md` (8.4KB)
- `docs/CHANGELOG_NOV_1_2024.md` (this file)

### Files Modified:
- `src/tools/wifi_scanner.py` - Added WPS detection, device ID
- `src/gui/main_window.py` - New columns, icons, colors
- `src/database/models.py` - New schema fields
- `gattrose-ng.desktop` - pkexec integration
- `README.md` - Complete rewrite
- `LICENSE` - GPL-3.0 full text

### Lines of Code Added:
- ~500 lines of new functionality
- ~200 lines of OUI database entries
- ~300 lines of documentation

---

## 🚀 Usage Examples

### Example 1: High-Value Target Detection
```
🌐 | AA:BB:CC:DD:EE:FF | GuestWiFi | TP-Link | TP-Link Router (85%) | Ch:6 |
WPA2 CCMP | -45dBm | 92 - CRITICAL | UNLOCKED | ...

→ This network scores 92 (CRITICAL) because:
  - WPA2 encryption (+40 base)
  - WPS UNLOCKED (+40 bonus) ← MAJOR VULNERABILITY
  - Strong signal (+15 bonus)
```

### Example 2: Device Identification
```
📱 | 12:34:56:78:90:AB | CLIENT | Apple | Apple iPhone (85%) | ...

→ Identified as iPhone with 85% confidence based on:
  - Apple OUI prefix
  - No specific identifying probes (generic iOS behavior)
```

### Example 3: Secure Network
```
🌐 | 11:22:33:44:55:66 | SecureNet | Ubiquiti | UniFi AP (90%) | Ch:11 |
WPA3 CCMP SAE | -65dBm | 18 - LOW | | ...

→ This network scores only 18 (LOW) because:
  - WPA3 encryption (15 base)
  - SAE authentication (-15 modifier)
  - Weak signal (+5 bonus)
  - Hidden SSID (-3 penalty)
```

---

## ⚙️ Installation & Setup

### First-Time Setup:
```bash
# 1. Install PolicyKit policy for GUI sudo
sudo cp config/com.gattrose.pkexec.policy /usr/share/polkit-1/actions/
sudo chmod 644 /usr/share/polkit-1/actions/com.gattrose.pkexec.policy

# 2. Make desktop file executable
chmod +x gattrose-ng.desktop

# 3. Install WPS detection (optional)
sudo apt-get install reaver

# 4. Launch application
# Method A: Double-click gattrose-ng.desktop (GUI password prompt)
# Method B: sudo ./gattrose-ng.py (terminal)
```

---

## 🐛 Bug Fixes

- Fixed `QGridLayout` import error
- Fixed column index mismatches in tree view updates
- Fixed historical data loading (now works on startup)
- Fixed text size slider not affecting new items
- Fixed color coding not updating on AP updates
- Fixed client device info not displaying

---

## ⚠️ Breaking Changes

### Database Schema:
- **Action Required**: Existing databases need migration or recreation
- New fields added to `networks` and `clients` tables
- Old databases will work but won't have new fields populated

### File Paths:
- **Action Required**: Update any custom scripts
- Images now in `assets/` not root
- Scripts now in `bin/` not root
- Documentation now in `docs/` not root

---

## 🔮 Future Enhancements

Planned for future releases:
- [ ] Export high-value targets to file
- [ ] Filter by attack score range
- [ ] Custom scoring weights
- [ ] Alert notifications for critical vulnerabilities
- [ ] Attack tool integration
- [ ] Detailed vulnerability reports
- [ ] Historical score trending
- [ ] Geolocation tracking
- [ ] Network relationship mapping

---

## 📜 License

This project is licensed under GNU General Public License v3.0 (GPL-3.0).

See [LICENSE](../LICENSE) for full text.

---

## 🙏 Credits

- **aircrack-ng** team - Wireless tools
- **reaver** team - WPS detection
- **PyQt** team - GUI framework
- **IEEE** - OUI database
- All security researchers and contributors

---

**Generated:** November 1, 2024
**Version:** 1.1.0
**Status:** Production Ready
