# BW16 Dual-Band WiFi Deauther

Flipper Zero application for controlling the BW16 (RTL8720DN) module for WiFi security testing on both 2.4GHz and 5GHz networks.

## Features

- **Dual-band scanning** - Scan 2.4GHz, 5GHz, or both bands simultaneously
- **Deauthentication attacks** - Disconnect clients from selected networks
- **EAPOL sniffing** - Capture WPA/WPA2 handshakes for security auditing
- **Channel hopping** - Automatically hop through all WiFi channels
- **Target selection** - Attack specific networks or broadcast deauth to all

## Hardware Requirements

### BW16 Module
- **BW16 (RTL8720DN)** development board
- Running **Evil-BW16** firmware: https://github.com/7h30th3r0n3/Evil-BW16

### Wiring

```
Flipper Zero          BW16 Module
═══════════           ═══════════
Pin 1 (5V)    ───────► 5V
Pin 8 (GND)   ───────► GND
Pin 13 (TX)   ───────► RX1 (Pin 13)
Pin 14 (RX)   ◄─────── TX1 (Pin 14)
```

**IMPORTANT:**
- Connect to **RX1/TX1** on the BW16, NOT RX0/TX0
- Enable **5V on GPIO** in Flipper settings before use!
- Do NOT connect BW16 to separate power while connected to Flipper 5V

## Building for Momentum Firmware

### Prerequisites

1. Install **uFBT** (micro Flipper Build Tool):
   ```bash
   pip install ufbt
   ```

2. Set up for Momentum firmware:
   ```bash
   ufbt update --index-url=https://up.unleashedflip.com/directory.json --channel=mntm-dev
   ```

### Build Commands

```bash
# Navigate to app directory
cd flipper_bw16_deauther

# Build the FAP
ufbt

# Build and install to connected Flipper
ufbt launch

# Just build without installing
ufbt fap_bw16_deauther
```

### Build Output

The compiled `.fap` file will be in:
```
.ufbt/build/bw16_deauther.fap
```

## Installation

### Option 1: Build and Launch
```bash
ufbt launch
```

### Option 2: Manual Copy
1. Build the app: `ufbt`
2. Copy `.ufbt/build/bw16_deauther.fap` to your Flipper's SD card:
   ```
   /ext/apps/GPIO/bw16_deauther.fap
   ```

## Usage

### First-Time Setup

1. Flash BW16 with Evil-BW16 firmware
2. Wire BW16 to Flipper Zero (see wiring diagram above)
3. Enable 5V on GPIO: `Settings > System > GPIO 5V Control > Enable`
4. Launch BW16 Deauther from `Apps > GPIO > BW16 WiFi`

### Menu Options

| Option | Description |
|--------|-------------|
| **Connect to BW16** | Initialize UART connection to module |
| **Scan 2.4 GHz** | Scan only 2.4GHz networks |
| **Scan 5 GHz** | Scan only 5GHz networks |
| **Scan All Bands** | Scan both 2.4GHz and 5GHz |
| **View Networks** | Display discovered networks |
| **Start Deauth Attack** | Begin deauthentication on targets |
| **Sniff EAPOL** | Capture WPA handshake frames |
| **View Log** | View activity log |
| **About** | App information |

### Typical Workflow

1. Connect to BW16
2. Scan for networks (choose band or scan all)
3. View networks to verify targets
4. Start Deauth Attack (with optional EAPOL sniff)
5. Stop when done

## Evil-BW16 Commands

The app uses these serial commands to control the BW16:

| Command | Description |
|---------|-------------|
| `scan` | Start network scan |
| `results` | Get scan results |
| `start deauther` | Start deauth attack |
| `stop deauther` | Stop deauth attack |
| `set target <n>` | Set target indices |
| `set ch <n>` | Set channel |
| `set start_channel 1` | Scan 2.4GHz |
| `set start_channel 36` | Scan 5GHz |
| `hop on/off` | Enable/disable channel hopping |
| `sniff eapol` | Start EAPOL capture |
| `stop sniff` | Stop sniffing |
| `info` | Get device info |

## Troubleshooting

### BW16 Not Responding
- Check wiring connections
- Verify 5V GPIO is enabled on Flipper
- Ensure BW16 has Evil-BW16 firmware flashed
- Try disconnecting and reconnecting

### No Networks Found
- Make sure BW16 antenna is connected
- Try scanning in different location
- Check if 5GHz is supported by your BW16 variant

### Build Errors
- Update uFBT: `pip install --upgrade ufbt`
- Clean and rebuild: `ufbt -c && ufbt`
- Check Momentum firmware compatibility

## File Structure

```
flipper_bw16_deauther/
├── application.fam      # FAP manifest
├── bw16_deauther.c      # Main application source
├── images/
│   └── bw16_10x10.png   # App icon (10x10 grayscale+alpha)
└── README.md            # This file
```

## Data Storage

App data is stored on the SD card:
```
/ext/apps_data/bw16_deauther/
├── bw16.log             # Activity log
└── handshakes/          # Captured EAPOL data (future)
```

## Legal Notice

This tool is intended for **authorized security testing only**.

- Only use on networks you own or have explicit permission to test
- Deauthentication attacks may be illegal in your jurisdiction
- Know and follow your local laws regarding wireless testing
- The authors are not responsible for misuse

## Credits

- **Evil-BW16 Firmware**: https://github.com/7h30th3r0n3/Evil-BW16
- **RTL8720DN Deauther**: https://github.com/tesa-klebeband/RTL8720dn-Deauther
- **Flipper Zero Tutorials**: https://github.com/jamisonderek/flipper-zero-tutorials
- **Gattrose-NG Project**: Part of the Gattrose-NG security toolkit

## License

GPL-3.0 - See LICENSE file for details.
