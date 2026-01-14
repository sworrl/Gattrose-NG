# Gattrose-NG BW16 Custom Firmware

Custom firmware for RTL8720DN (BW16) module with client detection, targeted deauth, and BLE support.

## Features

- **WiFi Scanning**: 2.4GHz, 5GHz, and dual-band scanning
- **Client Detection**: Promiscuous mode captures client MACs associated with APs
- **Targeted Deauth**: Deauthenticate specific clients or broadcast
- **Beacon Spam**: Create fake access points
- **BLE Scanning**: Scan for Bluetooth LE devices
- **BLE Spam**: Advertise fake BLE devices
- **Channel Hopping**: Automatic channel switching during monitoring

## Serial Protocol

Compatible with Gattrose-NG Flipper app. Commands (case-insensitive):

| Command | Description |
|---------|-------------|
| `SCAN` | Scan 2.4GHz networks |
| `SCAN5` | Scan 5GHz networks |
| `SCANDUAL` | Scan both bands |
| `LIST` | List found networks |
| `CLIENTS` | List detected clients |
| `DEAUTH <n>` | Broadcast deauth AP #n |
| `DEAUTH <n> <mac>` | Targeted deauth to specific client |
| `STOP` | Stop all attacks |
| `BEACON <ssid> [ch]` | Start beacon spam |
| `SNIFF` | Enable monitor mode |
| `CHANNEL <n>` | Set WiFi channel |
| `HOPON` / `HOPOFF` | Channel hopping |
| `BLESCAN` | BLE device scan |
| `BLESPAM` | BLE advertising spam |
| `INFO` | Device status |
| `HELP` | List commands |

## Response Format

Networks:
```
AP:|<id>|<ssid>|<bssid>|<channel>|<security>|<rssi>|<client_count>
```

Clients:
```
CLIENT:|<ap_index>|<mac>|<rssi>
```

New client discovery (real-time):
```
CLIENT:NEW:|<ap_index>|<mac>|<rssi>
```

## Hardware Setup

### Pin Connections (BW16 to Flipper Zero)

| BW16 Pin | Flipper Pin | Description |
|----------|-------------|-------------|
| TX1 (PA14) | Pin 14 (RX) | Serial TX |
| RX1 (PA13) | Pin 13 (TX) | Serial RX |
| GND | GND | Ground |
| 3.3V | 3.3V | Power |

## Building the Firmware

### Prerequisites

1. Install Arduino IDE 2.x
2. Add Realtek AmebaD board package:
   - Open Arduino IDE Preferences
   - Add to Additional Board Manager URLs:
     ```
     https://github.com/ambiot/ambd_arduino/raw/master/Arduino_package/package_realtek_amebad_index.json
     ```
3. Open Board Manager and install "Realtek AmebaD Boards"
4. Select board: **BW16(RTL8720DN)**

### Compile and Upload

1. Open `gattrose_bw16.ino` in Arduino IDE
2. Select correct board and port
3. Click Upload

### Upload via Download Mode

If normal upload fails:

1. Connect BW16 LOG_TX/LOG_RX for serial upload
2. Hold BOOT button while pressing RESET
3. Release both - BW16 enters download mode
4. Upload sketch

## Backing Up Original Firmware

Before flashing, backup your current firmware using rtltool.py:

```bash
# Install prerequisites
pip install pyserial

# Clone rtltool
git clone https://github.com/nicwest/rtltool.git
cd rtltool

# Put BW16 in download mode (hold BOOT + press RESET)

# Read full flash (2MB)
python rtltool.py -p /dev/ttyUSB0 -b 1500000 rf 0x08000000 0x200000 backup.bin

# Verify backup
md5sum backup.bin
```

### Restoring Original Firmware

```bash
python rtltool.py -p /dev/ttyUSB0 -b 1500000 wf 0x08000000 backup.bin
```

## Security Warning

This firmware is for authorized security testing only. Only use on networks you own or have explicit written permission to test.

## License

Part of the Gattrose-NG project. For educational and authorized security research only.
