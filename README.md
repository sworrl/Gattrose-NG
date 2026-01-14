# Gattrose-NG

**Advanced Wireless Penetration Testing Suite**

![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Platform](https://img.shields.io/badge/platform-linux-lightgrey.svg)

Gattrose-NG is a comprehensive wireless security auditing and penetration testing framework designed for authorized security assessments. It provides real-time WiFi network scanning, attack scoring, device fingerprinting, and vulnerability analysis with an intuitive Qt6-based GUI.

### About the Name

**"Gattrose"** is a nickname for my daughter, who was as hungry as a baby gator when she was an infant. This project is dedicated to her fierce spirit.

*Developed by REAvER from Falcon Technix*

## ⚠️ Legal Disclaimer

**IMPORTANT**: This tool is intended for authorized security testing, penetration testing, and educational purposes ONLY.

- ✅ Use on networks you own or have explicit written permission to test
- ✅ Use for authorized penetration testing engagements
- ✅ Use for security research and education
- ❌ **DO NOT** use on networks without authorization
- ❌ **DO NOT** use for malicious purposes
- ❌ **DO NOT** violate computer fraud and abuse laws

Unauthorized access to computer networks is illegal in most jurisdictions and may result in criminal prosecution. The developers assume no liability for misuse of this software.

## 🚀 Features

### 🎯 Intelligent Attack Scoring System
- **Advanced vulnerability assessment** (0-100 scale) evaluating:
  - **Encryption strength**: WEP (95), WPA (75), WPA2 (40), WPA3 (15), Open (100)
  - **Authentication method**: PSK, SAE, MGT, Enterprise (-15 for enterprise)
  - **WPS vulnerability**: CRITICAL +40 if enabled, +50 if unlocked
  - **Signal strength**: Stronger signals = higher scores (easier attacks)
  - **Active clients**: Networks with clients = better handshake capture
  - **Hidden SSIDs**: Slight penalty (slightly harder to attack)
  - **Live vs Historical**: Real-time networks prioritized
- **5-tier risk classification**: CRITICAL, HIGH, MEDIUM, LOW with star ratings (⭐-⭐⭐⭐⭐⭐)
- **Cyberpunk color scheme**: 24-bit RGB gradients from red (vulnerable) to green (secure)
- **Visual signal bars**: Animated color-shifting signal strength indicators with progressive pips (▂▃▅▆█)

### 📡 Advanced WiFi Scanning
- **Real-time network discovery** using aircrack-ng suite
- **Multi-channel scanning** with configurable channel hopping
- **Dual-mode operation**:
  - **Live scanning**: Active monitoring of wireless traffic
  - **Historical data**: Load and analyze previous scan sessions
- **Network categorization**:
  - 🎯 **Networks with Active Clients** (high-priority targets)
  - 📡 **Networks without Clients** (lower-priority targets)
- **SSID grouping**: Multiple BSSIDs per SSID automatically grouped
- **Channel distribution analysis**: Visual bar charts showing channel congestion
- **Extended statistics**: Real-time metrics on encryption types, WPS networks, vendors

### 🔐 WPS Vulnerability Detection
- **Automatic WPS scanning** using `wash` tool integration
- **Lock status detection**: Identifies locked vs unlocked WPS networks
- **Dedicated WPS Networks tab** for focused assessment
- **Attack readiness scoring**: WPS-enabled networks automatically flagged
- **Manufacturer identification**: Correlates WPS with device vendor data

### 🎭 Advanced Device Fingerprinting
- **MAC address vendor lookup** with extensive OUI database (200+ manufacturers)
- **AI-powered device type classification** with confidence scoring:
  - 📱 Smartphones (iPhone, Samsung, Google Pixel, etc.)
  - 💻 Laptops and desktops (MacBook, ThinkPad, Surface, etc.)
  - 🌐 Network equipment (routers, APs, switches, extenders)
  - 📺 Smart TVs and streaming devices (Roku, FireTV, AppleTV)
  - 🎮 Gaming consoles (PlayStation, Xbox, Nintendo Switch)
  - 📷 Security cameras and IoT devices
  - 🔊 Smart speakers and home automation
  - And 30+ more device categories
- **Multi-factor detection**:
  - OUI-based vendor matching
  - Device name pattern analysis
  - MAC address pattern recognition
  - Statistical confidence scoring (0-100%)
- **Visual indicators**: Unicode icons for instant device recognition

### 🎨 Modern Qt6-Based GUI
#### Main Tabs:
1. **📊 Dashboard**: Real-time statistics and attack surface overview
   - Network count by encryption type
   - WPS-enabled network tracking
   - Top manufacturers and vendors
   - Signal strength distribution
   - Channel usage heatmap with color-coded congestion bars
   - Quick-access cracked passwords

2. **📡 Scanner**: Real-time WiFi network monitoring
   - **Subtabs**: Networks with/without clients
   - Hierarchical tree view with SSID grouping
   - Live/historical network markers
   - Animated signal strength bars
   - Context menu for quick actions (deauth, capture, blacklist)
   - Multi-column sorting and filtering
   - Adjustable text size (6-20pt)

3. **🎯 Auto Attack**: Automated attack queue management
   - Handshake capture automation
   - Auto-cracking with wordlist support
   - WPS PIN attacks (Reaver & Bully)
   - Progress tracking and results logging
   - Configurable timeouts and retry logic

4. **🗄️ Database**: Historical network and client storage
   - SQLAlchemy-powered persistence
   - Network attack score tracking
   - Captured handshake management
   - Cracked password vault
   - Device manufacturer history
   - Time-series signal strength data

5. **🗺️ WiGLE Integration**: Global network database
   - BSSID/SSID geolocation lookup
   - Network submission and sharing
   - CSV export for WiGLE upload
   - Historical network data correlation

6. **🔵 Bluetooth Scanner**: Bluetooth device discovery
   - Bluetoothctl/hcitool integration
   - Device name and MAC extraction
   - RSSI signal strength monitoring
   - Service profile detection
   - Device type classification

7. **👻 Unassociated Clients**: Probe request monitoring
   - Devices not connected to any AP
   - Probe request SSID collection
   - Karma attack target identification
   - Device manufacturer tracking

### ⚔️ Attack Capabilities
- **Deauthentication attacks**:
  - Single-burst deauth from context menu
  - Continuous deauth for handshake capture
  - Targeted client disconnection
  - Broadcast deauth to all clients

- **Handshake capture**:
  - Automated 4-way handshake detection
  - Intelligent deauth packet injection
  - Capture file management (.cap format)
  - Verification using aircrack-ng

- **WPS attacks**:
  - Reaver-based PIN brute-force
  - Bully alternative attack method
  - Automatic PSK recovery
  - Database integration for cracked credentials

- **Password cracking** (Auto Attack tab):
  - CPU-based: aircrack-ng wordlist attacks
  - GPU-based: Hashcat integration (planned)
  - Auto-detection of common wordlists (rockyou.txt)
  - Progress monitoring and ETA calculation

### 🗃️ Data Persistence & Management
- **SQLite database** with comprehensive schema:
  - Networks table (BSSID, SSID, encryption, WPS, scores)
  - Clients table (MAC, vendor, device type, associations)
  - Handshakes table (capture files, crack status)
  - Sessions table (scan session tracking)
  - Cracked passwords vault (secured storage)

- **Attack queue system**:
  - Priority-based target selection
  - Background worker threads
  - Status tracking (pending, in_progress, completed, failed)
  - Result logging and notification

- **Blacklist management**:
  - BSSID blacklist for noise reduction
  - Toggle visibility of blacklisted networks
  - Persistent blacklist storage

### 📊 Real-Time Analytics
- **Live statistics dashboard**:
  - Network count by encryption type
  - WPS vulnerability distribution
  - Top device manufacturers
  - Channel utilization with congestion visualization
  - Signal strength distribution
  - Active client count

- **Extended network details**:
  - Beacon frame analysis
  - Data packet counts
  - Signal strength trending
  - Client association history
  - GPS coordinates (if available)

### 🎨 Visual Design
- **Cyberpunk aesthetic**: Dark theme with neon accents
- **Color-coded threat levels**: Instant visual risk assessment
- **Animated elements**:
  - Pulsing signal strength bars
  - Scanning activity spinner
  - Progress bars for attacks
- **Adaptive UI**: Responsive layout for different screen sizes
- **Accessibility**: Adjustable font sizes and high-contrast colors

### 🔧 System Integration
- **Automatic monitor mode management**: Detects and enables monitor mode
- **Interface detection**: Auto-discovery of wireless adapters
- **Virtual environment management**: Isolated Python dependencies
- **Service integration**: SystemD service support for background scanning
- **PolicyKit integration**: GUI authentication for privileged operations
- **Desktop launcher**: Double-click .desktop file support

### 📝 Comprehensive Logging
- **Multi-level logging**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Scan activity logs**: Every discovered network and client
- **Attack operation logs**: Deauth, capture, crack attempts
- **Error diagnostics**: Detailed traceback for troubleshooting
- **Log rotation**: Automatic cleanup of old log files

## 📋 Requirements

### System Requirements
- **OS**: Linux (tested on Ubuntu/Debian-based distributions)
- **Python**: 3.8 or higher
- **Root privileges**: Required for wireless operations
- **Wireless adapter**: Must support monitor mode

### Required System Packages
```bash
# Core wireless tools
sudo apt-get install -y \
    aircrack-ng \
    wireless-tools \
    net-tools \
    iw \
    python3 \
    python3-pip \
    python3-venv

# WPS detection (optional but recommended)
sudo apt-get install -y reaver

# Additional tools (optional)
sudo apt-get install -y \
    macchanger \
    tshark \
    hashcat
```

### Python Dependencies
Automatically installed on first run:
- PyQt6
- PyQt6-sip
- psutil
- netifaces
- sqlalchemy

## 🔧 Installation

### 🚀 Quick Install/Update (One-Liners)

**Using curl:**
```bash
curl -fsSL https://raw.githubusercontent.com/sworrl/Gattrose-NG/main/bin/install.py | sudo python3 -
```

**Using wget:**
```bash
wget -qO- https://raw.githubusercontent.com/sworrl/Gattrose-NG/main/bin/install.py | sudo python3 -
```

**Using git (clone and install):**
```bash
git clone https://github.com/sworrl/Gattrose-NG.git && cd Gattrose-NG && sudo python3 bin/install.py
```

**Update existing installation:**
```bash
cd /path/to/gattrose-ng && git pull && sudo python3 scripts/update_install.py
```

These commands will:
- Install system dependencies (aircrack-ng, reaver, python3, etc.)
- Download/clone the latest version from GitHub
- Set up Python virtual environment
- Install to `/opt/gattrose-ng`
- Configure desktop launcher
- Set up system integration

### Manual Installation

```bash
# 1. Clone the repository
git clone https://github.com/sworrl/Gattrose-NG.git
cd Gattrose-NG

# 2. Run the installer
sudo python3 bin/install.py

# 3. Or run directly (auto-installs dependencies)
sudo ./gattrose-ng.py
```

### GUI Launcher Setup (Optional)

For double-click launching with GUI password prompt:

```bash
# 1. Install PolicyKit policy
sudo cp config/com.gattrose.pkexec.policy /usr/share/polkit-1/actions/
sudo chmod 644 /usr/share/polkit-1/actions/com.gattrose.pkexec.policy

# 2. Make desktop file executable
chmod +x assets/gattrose-ng.desktop

# 3. Double-click assets/gattrose-ng.desktop to launch
```

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for detailed setup instructions.

## 📖 Usage

### Starting a Scan

```bash
# Method 1: Run from terminal
sudo ./gattrose-ng.py

# Method 2: Double-click desktop file (after PolicyKit setup)
```

1. The application will automatically detect your wireless interface
2. Monitor mode will be enabled automatically (or you'll be prompted)
3. Click **"Start Scanning"** or wait for auto-start
4. Networks and clients appear in the tree view with:
   - Color coding (red = vulnerable, green = secure)
   - Attack scores and risk levels
   - Device manufacturers and types
   - WPS status
   - Signal strength
   - And much more...

### Interpreting Results

#### Color Coding
- **🔴 Red (Score 80-100)**: CRITICAL - Extremely vulnerable, easy target
- **🟠 Orange (Score 60-79)**: HIGH - Highly vulnerable, attackable
- **🟡 Yellow (Score 35-59)**: MEDIUM - Moderate security
- **🟢 Green (Score 0-34)**: LOW - Strong security, difficult target

#### Attack Scores
```
Score 100: Open network (no encryption)
Score 95:  WEP encryption
Score 85:  WPA2 with WPS unlocked
Score 40:  WPA2 with good signal
Score 25:  WPA3 with weak signal
Score 15:  WPA3 with enterprise auth
```

#### Device Icons
- 🌐 Routers/Access Points
- 📱 Smartphones
- 💻 Laptops
- 🖥️ Desktops
- 📺 Smart TVs
- 📷 Cameras
- 🔊 Speakers
- 🎮 Gaming Consoles
- 💡 IoT Devices

### Example Output

```
Icon | BSSID             | SSID      | Vendor    | Device Type         | Attack Score | WPS
🌐   | AA:BB:CC:DD:EE:FF | HomeWiFi  | Ubiquiti  | UniFi AP (90%)     | 25 - LOW     |
📡   | 11:22:33:44:55:66 | GuestNet  | TP-Link   | TP-Link Router(85%)| 85 - CRITICAL| UNLOCKED
📱   | 12:34:56:78:90:AB | CLIENT    | Apple     | iPhone (85%)       |              |
```

## 🔧 Advanced Usage

### Attack Queue Automation

```python
# Adding targets to auto-attack queue from Scanner tab:
1. Right-click on a network
2. Select "Add to Attack Queue"
3. Switch to Auto Attack tab
4. Configure attack parameters:
   - Timeout (default: 5 minutes)
   - Enable auto-cracking
   - Select wordlist
5. Click "Start Queue Processing"
```

### WPS PIN Attacks

```bash
# WPS attacks automatically try both Reaver and Bully:
1. Navigate to WPS Networks tab
2. Select an unlocked WPS network
3. Right-click → "Launch WPS Attack"
4. Monitor progress in Auto Attack tab
5. Cracked PIN/PSK saved to database automatically
```

### Handshake Capture Workflow

```bash
# Manual handshake capture:
1. Scanner tab → Right-click AP → "Capture Handshake"
2. Deauth packets sent automatically
3. Monitor capture progress
4. Verify handshake with aircrack-ng
5. Auto-crack if enabled

# Batch handshake capture:
1. Select multiple networks (Ctrl+Click)
2. Add all to attack queue
3. Auto Attack tab processes sequentially
```

### Database Queries

```python
# Access captured data via Database tab:
- Filter by encryption type
- Search by SSID/BSSID
- View cracked passwords
- Export to CSV
- Analyze attack score trends
```

### Bluetooth Enumeration

```bash
# Bluetooth device discovery:
1. Bluetooth tab → "Start Scan"
2. View device name, MAC, RSSI
3. Identify device types
4. Context menu for pairing/info
```

## ❓ FAQ

### Q: Why do I need root/sudo privileges?
**A:** Wireless operations (monitor mode, packet injection, interface management) require raw socket access and system-level control, which necessitates elevated privileges.

### Q: My wireless adapter doesn't support monitor mode. What do I do?
**A:** You need a compatible adapter. Recommended chipsets:
- Atheros AR9271 (Alfa AWUS036NHA)
- Ralink RT3070 (Alfa AWUS036NH)
- Realtek RTL8812AU (Alfa AWUS036ACH)
- Intel adapters (some models)

Check compatibility: `sudo airmon-ng`

### Q: Scanning shows no networks. How do I fix this?
**A:**
1. Verify monitor mode: `iwconfig` should show interface in Monitor mode
2. Check channel hopping: `airodump-ng wlan0mon` should show networks
3. Ensure antenna is connected
4. Try different channels: Some networks may be on 5GHz (channels 36+)

### Q: WPS scanning doesn't work.
**A:** Install the `reaver` package:
```bash
sudo apt-get install reaver
# Verify: wash -h
```

### Q: How do I interpret attack scores?
**A:**
- **90-100**: CRITICAL - Open/WEP networks, immediate compromise
- **70-89**: HIGH - WPA with WPS enabled, highly vulnerable
- **50-69**: MEDIUM - WPA2 with good signal, handshake capturable
- **30-49**: LOW - WPA2/WPA3, requires significant effort
- **0-29**: VERY LOW - WPA3 enterprise, very difficult

### Q: Can I run this on Kali Linux?
**A:** Yes! Gattrose-NG is designed for and tested on Kali. All dependencies (aircrack-ng, reaver, etc.) are pre-installed on Kali.

### Q: Does this work on Windows/macOS?
**A:** No. Linux-only due to:
- aircrack-ng suite requirements
- Monitor mode implementation
- Packet injection support
- Interface management (airmon-ng)

### Q: How do I update the OUI database for device fingerprinting?
**A:** The OUI database is embedded in the code. Future versions will support automatic updates from IEEE.

### Q: Are there any legal concerns?
**A:** **YES.** Only use on networks you own or have explicit written authorization to test. Unauthorized access is illegal in most countries. See Legal Disclaimer above.

### Q: How can I contribute?
**A:** Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test thoroughly
4. Submit a pull request with detailed description
5. Ensure ethical use guidelines are met

## 🐛 Troubleshooting

### Issue: "No monitor interface detected"
**Solution:**
```bash
# Check available interfaces
sudo airmon-ng

# Enable monitor mode manually
sudo airmon-ng start wlan0

# Verify
iwconfig  # Should show wlan0mon or similar
```

### Issue: "Permission denied" errors
**Solution:**
```bash
# Run with sudo
sudo ./gattrose-ng.py

# Or setup PolicyKit (see Installation)
```

### Issue: "Module 'PyQt6' not found"
**Solution:**
```bash
# Reinstall dependencies
cd /path/to/gattrose-ng
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: GUI doesn't launch
**Solution:**
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check Qt installation
python3 -c "from PyQt6.QtWidgets import QApplication"

# Check logs
tail -f logs/gattrose-ng.log
```

### Issue: Scan finds no networks
**Solution:**
```bash
# Test aircrack-ng directly
sudo airodump-ng wlan0mon

# Check for interface conflicts
sudo airmon-ng check kill

# Restart wireless services
sudo systemctl restart NetworkManager
```

### Issue: WPS attacks fail immediately
**Solution:**
```bash
# Verify reaver installation
which reaver
reaver -h

# Check WPS lock status
# Locked WPS networks may have rate limiting
# Try bully instead: Auto Attack tab → WPS Attack
```

### Issue: Database errors
**Solution:**
```bash
# Reset database
cd /path/to/gattrose-ng
rm -f data/gattrose.db
# Restart application - database will be recreated
```

### Issue: High CPU usage during scan
**Solution:**
- Reduce channel hopping frequency
- Close other resource-intensive applications
- Disable auto-cracking until needed
- Use fixed channel scanning for specific targets

### Issue: Bluetooth scan finds no devices
**Solution:**
```bash
# Check Bluetooth service
sudo systemctl start bluetooth
sudo systemctl status bluetooth

# Verify adapter
hciconfig
sudo hciconfig hci0 up

# Test manually
bluetoothctl
[bluetooth]# power on
[bluetooth]# scan on
```

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [Quick Start Guide](docs/QUICKSTART.md) - Get started quickly
- [New Features](docs/NEW_FEATURES.md) - Attack scoring and device fingerprinting
- [Recent Updates](docs/RECENT_UPDATES.md) - Latest changes
- [WiFi Scanner Implementation](docs/WIFI_SCANNER_IMPLEMENTATION.md) - Technical details
- [Incomplete Features](INCOMPLETE_FEATURES.md) - Roadmap and TODOs

## 🏗️ Project Structure

```
gattrose-ng/
├── LICENSE                 # GPL-3.0 license
├── README.md               # This file
├── VERSION                 # Version file
├── assets/                 # Images, icons, and desktop files
│   ├── gattrose-ng.png
│   ├── gattrose-ng.svg
│   ├── gattrose-ng.desktop     # Desktop launcher
│   └── gattrose-tray.desktop   # Tray desktop launcher
├── bin/                    # Scripts and utilities
│   ├── gattrose-daemon.py
│   ├── install.py          # GitHub installation script
│   ├── launch-gattrose.sh
│   └── start-gattrose.sh
├── config/                 # Configuration files
│   ├── com.gattrose.pkexec.policy
│   └── gattrose-ng.service
├── docs/                   # Documentation
│   ├── INSTALLATION.md
│   ├── QUICKSTART.md
│   ├── NEW_FEATURES.md
│   ├── TODO.md             # Project TODOs
│   ├── UPDATE.md           # Update notes
│   └── ...
├── scripts/                # Development and maintenance scripts
│   └── update_install.py   # Dev-to-prod sync script
├── src/                    # Source code
│   ├── main.py            # Application entry point
│   ├── gui/               # GUI components
│   ├── tools/             # Scanner and analysis tools
│   ├── utils/             # Utilities
│   ├── core/              # Core functionality
│   └── database/          # Database models
├── data/                   # Data storage
│   └── captures/          # Scan capture files
└── logs/                   # Application logs
```

## 🛠️ Development

### Built With
- **Python 3** - Core language
- **PyQt6** - GUI framework
- **SQLAlchemy** - Database ORM
- **aircrack-ng suite** - Wireless tools
- **wash/reaver** - WPS detection

### Contributing
Contributions are welcome! Please ensure:
- Code follows existing style
- All features are ethically sound
- Documentation is updated
- Changes are tested

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

```
Gattrose-NG - Wireless Penetration Testing Suite
Copyright (C) 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

See [LICENSE](LICENSE) for full license text.

---

## BW16 Firmware + Flipper Zero App (v4.0)

Gattrose-NG also includes a portable WiFi audit module using the **BW16 (RTL8720DN)** with **Flipper Zero** control.

### BW16 Features
- **Deauthentication** - Targeted/broadcast deauth with client detection
- **Evil Twin AP** - 7 captive portal templates (Google, Facebook, Amazon, Apple, Netflix, Microsoft)
- **PMKID Capture** - Capture from EAPOL Message 1 (hashcat format)
- **Handshake Capture** - 4-way handshake during deauth
- **Karma Attack** - Auto-respond to probe requests
- **Probe Logger** - Log SSIDs devices search for
- **WiFi Jammer** - Continuous deauth all channels
- **Rogue AP Detector** - Alert on new/changed APs
- **BLE Spam** - FastPair (Android), SwiftPair (Windows), AirTag payloads
- **BLE Scanner** - Track devices with RSSI history

### Wiring (Flipper to BW16)

| Flipper | BW16 |
|---------|------|
| TX (13) | PA14 |
| RX (14) | PA13 |
| GND | GND |
| 3.3V | 3V3 |

### Building

**Firmware:**
```bash
cd bw16_firmware/gattrose_ng
arduino-cli compile --fqbn realtek:AmebaD:Ai-Thinker_BW16 .
arduino-cli upload --fqbn realtek:AmebaD:Ai-Thinker_BW16 -p /dev/ttyUSB0 .
```

**Flipper App:**
```bash
cd flipper_bw16_deauther
ufbt
# Copy dist/gattrose_ng.fap to Flipper's apps/GPIO/
```

### Directory Structure
```
bw16_firmware/
└── gattrose_ng/           # Main firmware source
    ├── gattrose_ng.ino
    ├── wifi_cust_tx.cpp/h
    ├── dns.cpp/h
    └── portals/           # 7 portal templates

flipper_bw16_deauther/
├── gattrose_ng.c          # Flipper app
├── application.fam
└── gattrose_10x10.png
```

---

## 🙏 Acknowledgments

- **aircrack-ng** team for the excellent wireless tools
- **PyQt** team for the powerful GUI framework
- **IEEE** for the OUI database
- All contributors and security researchers

## ⚖️ Ethical Use

This tool is designed for:
- ✅ Authorized penetration testing
- ✅ Security auditing of your own networks
- ✅ Educational purposes in controlled environments
- ✅ Red team exercises with proper authorization

**Remember**: With great power comes great responsibility. Use this tool ethically and legally.

## 📞 Support

For questions, issues, or feature requests:
- Check the [documentation](docs/)
- Review existing issues
- Submit new issues with detailed information

---

**Made for security professionals, by security professionals. Use responsibly.**
