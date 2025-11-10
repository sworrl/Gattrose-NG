# Gattrose-NG Changelog

All notable changes to this project will be documented in this file.

## [2.2.5] - 2025-11-01

### Added
- **Scanner Subtabs**: Networks now separated into two tabs:
  - 🎯 Networks with Clients (high-priority targets)
  - 📡 Networks without Clients (lower-priority targets)
  - Networks automatically move between tabs based on client associations

- **Animated Signal Strength Bars**:
  - Color-shifting/pulsing animation using sine wave
  - Smooth breathing effect (70-100% brightness)
  - Progressive bar heights: ▂▃▅▆█ (5 levels)
  - Updates every 150ms
  - Attached to SSID column for APs and MAC column for clients

- **Channel Frequency Display**:
  - Shows actual frequency alongside channel number
  - Format: "6 (2437 MHz)"
  - Supports all bands:
    - 2.4 GHz (channels 1-14)
    - 5 GHz (channels 36-165)
    - 6 GHz (channels >233)
  - Applied to Scanner and WPS Networks tabs

- **Channel Distribution Visualization**:
  - Relative bar charts showing channel congestion
  - Color-coded by usage:
    - Red: Very congested (8+ networks)
    - Orange: Congested (5-7 networks)
    - Yellow: Moderate (3-4 networks)
    - Green: Clear (1-2 networks)
  - Real-time updates in Dashboard

- **OUI Database Management**:
  - Complete MAC vendor database management in Settings tab
  - Statistics display:
    - Total vendor count (up to 38,000+ entries)
    - IEEE records count
    - Wireshark records count
    - Last update timestamp and age
  - Update button to download latest vendor data from:
    - IEEE OUI database
    - Wireshark manufacturer database
  - Threaded background updates with progress bar
  - Auto-loads statistics on Settings tab open

- **WPS Attack Features**:
  - Reaver integration for WPS PIN brute-force
  - Bully integration as alternative attack method
  - Auto-save discovered PINs and PSKs to database
  - Progress tracking and status updates

- **Auto-Cracking Feature**:
  - Automatic password cracking for captured handshakes
  - CPU-based attacks using aircrack-ng
  - Auto-detection of common wordlists (rockyou.txt)
  - Progress monitoring with ETA calculation
  - Auto-save cracked passwords to database

- **WiGLE Upload**:
  - Export networks to WiGLE CSV format (WigleWifi-1.4)
  - Proper encryption type mapping for WiGLE
  - Auto-switch to WiGLE tab for upload
  - CSV export to data/exports/

- **Bluetooth Scanner**:
  - Full Bluetooth device discovery
  - Multiple scanning methods:
    - bluetoothctl (primary)
    - hcitool (fallback)
    - btmgmt (alternative)
  - Device information extraction:
    - Name and MAC address
    - RSSI signal strength
    - Service profiles
    - Device type classification
  - Thread-safe GUI updates

- **Web Server**:
  - Flask-based REST API
  - Web interface serving at root /
  - API endpoints for:
    - Dashboard statistics
    - Network listing
    - Client listing
    - Handshake management
    - Attack queue status
    - System status
  - Auto-documentation at /api/docs
  - Launcher script: bin/start-webserver.sh

### Improved
- **README.md**: Comprehensive documentation with:
  - Detailed feature descriptions
  - Advanced usage examples
  - FAQ section (10+ questions)
  - Troubleshooting guide (8+ common issues)
  - API documentation
  - Installation instructions

- **Signal Bar Display**:
  - Changed from filled/empty blocks to progressive pips
  - Better visual representation of signal strength
  - Color-coded for instant recognition

- **Database Integration**:
  - WPS PIN/PSK auto-save
  - Cracked password vault
  - Handshake capture tracking

### Fixed
- Missing import in `update_signal_colors()` method (QBrush, QColor)
- Python cache issues causing old code to run
- Signal bar color shifting implementation

### Performance
- Optimized tree widget updates for scanner subtabs
- Improved database query performance for OUI lookups
- Reduced context usage with better file organization

### Documentation
- Updated README.md with all new features
- Created comprehensive CHANGELOG.md
- Updated INCOMPLETE_FEATURES.md
- Added tribute to Gattrose (developer's daughter) in About section

## [2.2.4] - 2025-10-31

### Previous Features
- Attack scoring system
- Device fingerprinting
- WPS detection
- Database persistence
- Multiple themes (30 retro themes)
- Real-time WiFi scanning
- Attack queue management

---

**Note**: This changelog follows [Keep a Changelog](https://keepachangelog.com/) format.
