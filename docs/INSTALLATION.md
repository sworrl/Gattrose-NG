# Gattrose-NG Installation Guide

## Quick Start

```bash
# 1. Clone or download the repository
cd "/home/eurrl/Documents/Code & Scripts/gattrose-ng"

# 2. Run the application (will auto-setup virtual environment)
sudo ./gattrose-ng.py
```

## GUI Desktop Launcher Setup

To enable double-click launching with GUI sudo prompt:

### 1. Install PolicyKit Policy (Required for GUI sudo)

```bash
# Copy the polkit policy file
sudo cp config/com.gattrose.pkexec.policy /usr/share/polkit-1/actions/

# Set correct permissions
sudo chmod 644 /usr/share/polkit-1/actions/com.gattrose.pkexec.policy
```

### 2. Make Desktop File Executable

```bash
chmod +x gattrose-ng.desktop

# Optional: Copy to applications directory for system-wide access
cp gattrose-ng.desktop ~/.local/share/applications/
```

### 3. Trust the Desktop File

When you first double-click `gattrose-ng.desktop`, you may need to:
- Right-click → "Allow Launching" or "Trust and Launch"
- Or: Mark as executable in file properties

After this, you can launch Gattrose-NG by double-clicking the desktop file, and a GUI password prompt will appear.

## Dependencies

### Required System Packages

```bash
# Core wireless tools
sudo apt-get update
sudo apt-get install -y \
    aircrack-ng \
    wireless-tools \
    net-tools \
    iw \
    python3 \
    python3-pip \
    python3-venv

# Optional but recommended: WPS detection
sudo apt-get install -y reaver

# Optional: Additional wireless tools
sudo apt-get install -y \
    macchanger \
    tshark \
    hashcat
```

### Python Dependencies

These are automatically installed when you first run the application:

- PyQt6
- PyQt6-sip
- psutil
- netifaces

## Wireless Interface Setup

### Enable Monitor Mode

```bash
# Find your wireless interface
iw dev

# Enable monitor mode (replace wlan0 with your interface)
sudo airmon-ng start wlan0

# This will create a monitor interface (usually wlan0mon)
```

### Disable Monitor Mode (when done)

```bash
sudo airmon-ng stop wlan0mon
```

## Running the Application

### Method 1: Terminal (Most Reliable)

```bash
sudo ./gattrose-ng.py
```

### Method 2: Desktop Launcher (After PolicyKit Setup)

Double-click `gattrose-ng.desktop` and enter your password when prompted.

### Method 3: Direct Python

```bash
cd "/home/eurrl/Documents/Code & Scripts/gattrose-ng"
sudo .venv/bin/python src/main.py
```

## Features

### Attack Scoring System
- Automatically scores WiFi networks based on vulnerability (0-100)
- Color-coded display (green = secure, red = vulnerable)
- Considers encryption, WPS, signal strength, and more

### WPS Detection
- Automatically scans for WPS-enabled networks
- Shows locked/unlocked status
- Adds +40 points to attack score for WPS networks

### Device Fingerprinting
- Identifies device manufacturers from MAC addresses
- Detects specific device types (iPhone, Samsung, etc.)
- Shows confidence percentage
- Unicode icons for different device types

### Text Size Adjustment
- Slider at bottom of Scanner tab
- Range: 6pt to 20pt
- Applies to entire tree view

## Troubleshooting

### "Permission Denied" Errors

The application requires root privileges to:
- Put wireless interfaces in monitor mode
- Run airodump-ng
- Run wash (WPS detection)

Always run with `sudo` or use the GUI launcher with PolicyKit.

### WPS Detection Not Working

If WPS detection isn't showing results:

```bash
# Install reaver (includes wash)
sudo apt-get install reaver

# Verify wash is installed
which wash
```

### Monitor Mode Not Working

```bash
# Kill conflicting processes
sudo airmon-ng check kill

# Try enabling monitor mode again
sudo airmon-ng start wlan0
```

### GUI Won't Launch

If the desktop launcher doesn't work:

1. Verify PolicyKit policy is installed:
   ```bash
   ls -l /usr/share/polkit-1/actions/com.gattrose.pkexec.policy
   ```

2. Check desktop file is executable:
   ```bash
   ls -l gattrose-ng.desktop
   ```

3. Try launching from terminal to see errors:
   ```bash
   sudo ./gattrose-ng.py
   ```

### No Networks Showing

1. Verify monitor mode is enabled:
   ```bash
   iwconfig
   # Look for "Mode:Monitor"
   ```

2. Check if interface is detecting packets:
   ```bash
   sudo airodump-ng wlan0mon
   ```

3. Try changing channels:
   ```bash
   sudo iwconfig wlan0mon channel 6
   ```

## File Structure

```
gattrose-ng/
├── gattrose-ng.py          # Main launcher script
├── gattrose-ng.desktop     # Desktop launcher file
├── README.md               # Project documentation
├── LICENSE                 # GPL-3.0 License
├── requirements.txt        # Python dependencies
├── assets/                 # Images and icons
│   ├── gattrose-ng.png    # Application icon (PNG)
│   └── gattrose-ng.svg    # Application icon (SVG)
├── bin/                    # Scripts and utilities
│   ├── gattrose-daemon.py # Daemon script
│   ├── install.py         # Installation script
│   ├── launch-gattrose.sh # Launcher script
│   └── start-gattrose.sh  # Start script
├── config/                 # Configuration files
│   ├── com.gattrose.pkexec.policy  # PolicyKit policy
│   └── gattrose-ng.service # Systemd service
├── docs/                   # Documentation
│   ├── INSTALLATION.md    # This file
│   ├── QUICKSTART.md      # Quick start guide
│   ├── NEW_FEATURES.md    # Feature documentation
│   └── ...                # Other docs
├── src/                    # Source code
│   ├── main.py            # Application entry point
│   ├── gui/               # GUI components
│   ├── tools/             # Scanner and tools
│   ├── utils/             # Utilities
│   ├── core/              # Core functionality
│   └── database/          # Database management
├── data/                   # Data storage
│   └── captures/          # Scan capture files
└── logs/                   # Application logs
```

## Uninstallation

```bash
# Remove PolicyKit policy
sudo rm /usr/share/polkit-1/actions/com.gattrose.pkexec.policy

# Remove desktop launcher
rm ~/.local/share/applications/gattrose-ng.desktop

# Remove application directory
rm -rf "/home/eurrl/Documents/Code & Scripts/gattrose-ng"
```

## Legal Notice

⚠️ **IMPORTANT**: This tool is for authorized security testing only.

- Only test networks you own or have written permission to test
- Unauthorized access to computer networks is illegal
- Use responsibly and ethically

## Support

For issues, feature requests, or questions:
- Check the README.md for usage instructions
- Review NEW_FEATURES.md for feature documentation
- Review INSTALLATION.md for setup help

## License

GNU General Public License v3.0 (GPL-3.0)
See LICENSE file for full details.
