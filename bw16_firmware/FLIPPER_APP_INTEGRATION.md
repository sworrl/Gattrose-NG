# Gattrose-NG Flipper App Integration Guide

**Firmware Version: 2.1**
**For Claude/Developer updating the Flipper Zero app**

This document describes the BW16 firmware protocol so you can update the Flipper app to communicate with the Gattrose-NG firmware.

---

## Overview

Gattrose-NG is a merged firmware combining KinimodD + custom features. It uses **STX/ETX binary framing** (same as KinimodD/DelfyRTL) for Flipper compatibility.

### What's Compatible (No Changes Needed)
- Basic protocol framing (STX/ETX)
- Scan command (`s`)
- Get networks command (`g`)
- Basic deauth command (`d<index>`)
- Beacon commands (`b`)
- WiFi AP commands (`w`)

### What's NEW (App Needs Updates)
- Client detection commands (`m`, `c`) - **TESTED & WORKING**
- LED control command (`r`) - **TESTED & WORKING**
- BLE commands (`l`)
- Targeted deauth with MAC address (`k`)
- Client-only attack command
- More portal types (6 total + default)
- Extended info command
- PMF detection for networks

### Verified Working (v2.1)
- WiFi scanning (64+ networks)
- Client detection with accurate RSSI
- PMF (Protected Management Frames) detection
- LED control (static colors + effects)
- Morse code boot sequence
- Deauth attacks (on non-PMF networks)
- Network sorting (by clients, PMF status, signal)

---

## Protocol Specification

### Framing

```
TX to BW16:   [0x02] [cmd] [args...] [0x03]
RX from BW16: [0x02] [type] [data...] [0x03]
```

| Byte | Name | Value | Description |
|------|------|-------|-------------|
| STX | Start | `0x02` | Message start marker |
| ETX | End | `0x03` | Message end marker |
| SEP | Separator | `0x1D` | Field separator in data |

### Sending Commands (Flipper -> BW16)

```c
// Example: Send scan command
void send_command(char cmd, const char* args) {
    furi_hal_uart_tx(0x02);           // STX
    furi_hal_uart_tx(cmd);            // Command byte
    if (args) {
        furi_hal_uart_tx_str(args);   // Arguments
    }
    furi_hal_uart_tx(0x03);           // ETX
}

// Usage:
send_command('s', "5000");    // Scan for 5 seconds
send_command('g', NULL);      // Get network list
send_command('d', "3");       // Deauth network 3
```

### Receiving Responses (BW16 -> Flipper)

Parse between STX and ETX. First byte after STX is the response type.

```c
// Response types
typedef enum {
    RESP_READY = 'r',      // Boot/ready message OR LED response
    RESP_SCAN = 's',       // Scan status
    RESP_NETWORK = 'n',    // Network entry
    RESP_CLIENT = 'c',     // Client entry
    RESP_BLE = 'l',        // BLE device entry
    RESP_CREDS = 'C',      // Captured credentials
    RESP_INFO = 'i',       // Info/count
    RESP_ERROR = 'e',      // Error message
    RESP_DEAUTH = 'd',     // Deauth status
    RESP_WIFI = 'w',       // WiFi AP status
    RESP_BEACON = 'b',     // Beacon status
    RESP_MONITOR = 'm',    // Monitor mode status
    RESP_STOP = 'x',       // Stop all confirmation
    RESP_KICK = 'k',       // Client kick status
} ResponseType;
```

---

## Command Reference

### 1. WiFi Scanning

**Command:** `s[time_ms]`

| Command | Description |
|---------|-------------|
| `s` | Scan with default 5000ms |
| `s10000` | Scan for 10 seconds |

**Responses:**
```
[STX]sSCANNING[ETX]           // Scan started
[STX]sDONE:64[ETX]            // Scan complete, 64 networks found
```

**Console output during scan:**
```
Starting WiFi scan...
Found 64 networks
PMF protected: 17
Hidden: 13
```

### 2. Get Network List

**Command:** `g`

**Responses:**
```
[STX]i64[ETX]                 // Count: 64 networks

// Then 64 network entries:
[STX]n0|MyWiFi|AA:BB:CC:DD:EE:FF|6|-45|2|3|WPA2|0|0[ETX]
      ^  ^      ^               ^  ^   ^ ^  ^   ^ ^
      |  |      |               |  |   | |  |   | +-- Hidden (1=yes)
      |  |      |               |  |   | |  |   +-- PMF (1=yes, CAN'T DEAUTH!)
      |  |      |               |  |   | |  +-- Security
      |  |      |               |  |   | +-- Client count
      |  |      |               |  |   +-- Band (2=2.4GHz, 5=5GHz)
      |  |      |               |  +-- RSSI
      |  |      |               +-- Channel
      |  |      +-- BSSID
      |  +-- SSID (empty if hidden)
      +-- Index
```

**Networks are sorted by priority:**
1. Named networks (non-hidden) first
2. Networks with detected clients first
3. Attackable networks (no PMF) before PMF-protected
4. By signal strength (RSSI)

**Network data structure:**
```c
typedef struct {
    int index;
    char ssid[33];
    char bssid[18];      // "AA:BB:CC:DD:EE:FF"
    int channel;
    int rssi;
    bool is_5ghz;        // band == "5"
    int client_count;
    char security[16];   // "Open", "WEP", "WPA", "WPA2", "WPA3"
    bool has_pmf;        // PMF enabled - deauth won't work!
    bool hidden;         // Hidden SSID
} GattroseNetwork;
```

### PMF (Protected Management Frames) - IMPORTANT!

**Networks with PMF enabled are IMMUNE to deauthentication attacks.**

PMF is detected by checking for:
- WPA3 security (always has PMF)
- WPA2 with AES-CMAC (management frame protection)

**UI Recommendations:**
- Display PMF networks with a shield/lock icon
- Gray out or warn when selecting PMF network for deauth
- Show "Protected - Deauth won't work" message
- Still useful for reconnaissance

**Detection accuracy:** PMF detection uses RTL8720 SDK security flags:
- `WPA3_SECURITY (0x00800000)` = PMF required
- `AES_CMAC_ENABLED (0x0010)` = MFP enabled

### 3. Deauthentication

**Command:** `d<args>`

| Command | Description |
|---------|-------------|
| `ds` | Stop all deauth |
| `d3` | Deauth network index 3 (broadcast) |
| `d3-7` | Deauth index 3 with reason code 7 |
| `d3-7-AA:BB:CC:DD:EE:FF` | Targeted deauth to specific client |

**Reason codes (optional, default=2):**
```c
typedef enum {
    REASON_UNSPECIFIED = 1,
    REASON_PREV_AUTH_INVALID = 2,   // Default
    REASON_LEAVING = 3,
    REASON_INACTIVITY = 4,
    REASON_AP_OVERLOAD = 5,
    REASON_CLASS2_FROM_UNAUTH = 6,
    REASON_CLASS3_FROM_UNASSOC = 7,
} DeauthReason;
```

**Responses:**
```
[STX]dDEAUTH:3[ETX]           // Started deauth on index 3
[STX]dSTOPPED[ETX]            // All deauth stopped
[STX]eALREADY_DEAUTHING[ETX]  // Error: already attacking this network
[STX]eINVALID_INDEX[ETX]      // Error: index out of range
```

**WARNING:** Deauth will NOT work on PMF-protected networks. Check `has_pmf` flag before attacking!

### 3b. Client-Only Attack

**Command:** `k<mac>[-reason]`

Attack a specific client without knowing which AP they're on. The firmware looks up the client's associated AP automatically.

| Command | Description |
|---------|-------------|
| `kAA:BB:CC:DD:EE:FF` | Deauth client (default reason 2) |
| `kAA:BB:CC:DD:EE:FF-7` | Deauth client with reason code 7 |

**Responses:**
```
[STX]kCLIENT_DEAUTH:AA:BB:CC:DD:EE:FF[ETX]  // Attack started
[STX]eCLIENT_NOT_FOUND[ETX]                  // Client not in detected list
[STX]eINVALID_MAC[ETX]                       // MAC format invalid
```

**Use case:** When you see clients in the sniff list but don't care which network they're on - just kick them off.

**Note:** Client must be detected first via monitor mode (`m1`). Client list is cleared on new scan.

### 4. Client Detection (Monitor Mode)

**Command:** `m<state>` and `c`

| Command | Description |
|---------|-------------|
| `m1` | Enable promiscuous mode (monitor) |
| `m0` | Disable promiscuous mode |
| `c` | Get detected client list |

**Responses:**
```
[STX]mMONITOR_ON[ETX]         // Monitor enabled
[STX]mMONITOR_OFF[ETX]        // Monitor disabled

// When new client detected (automatic, real-time):
[STX]c3|AA:BB:CC:DD:EE:FF|-52[ETX]
      ^  ^                 ^
      |  |                 +-- RSSI (accurate, from RTL8720 driver)
      |  +-- Client MAC
      +-- AP index this client is connected to

// Response to 'c' command:
[STX]i8[ETX]                  // 8 clients detected
[STX]c0|AA:BB:CC:DD:EE:FF|-45[ETX]
[STX]c0|11:22:33:44:55:66|-62[ETX]
... (more client entries)
```

**Client data structure:**
```c
typedef struct {
    int ap_index;           // Which network this client belongs to
    char mac[18];           // "AA:BB:CC:DD:EE:FF"
    int rssi;               // Signal strength (accurate in v2.1+)
} GattroseClient;
```

**Technical Notes (v2.1):**
- Client detection uses RTL8720 promiscuous mode
- RSSI extracted from `ieee80211_frame_info_t` userdata (not packet buffer)
- BSSID matching uses driver-provided BSSID for accuracy
- Clients are associated with scanned networks by BSSID match

### 5. Evil Twin / Captive Portal

**Command:** `w<portal_type>` and `p<portal_type>`

| Command | Portal |
|---------|--------|
| `w0` | Stop evil twin |
| `w1` | Default (generic WiFi login) |
| `w2` | Google |
| `w3` | Facebook |
| `w4` | Amazon |
| `w5` | Apple |
| `w6` | Netflix |
| `w7` | Microsoft |

**Change portal while running:** `p<num>` (e.g., `p3` for Facebook)

**Responses:**
```
[STX]wAP_ON:2[ETX]            // Evil twin started with Google portal
[STX]wAP_OFF[ETX]             // Evil twin stopped
[STX]pPORTAL:3[ETX]           // Portal changed to Facebook

// When credentials captured:
[STX]Cuser@email.com|password123[ETX]
      ^              ^
      |              +-- Password
      +-- Username/Email
```

**Credential data structure:**
```c
typedef struct {
    char username[128];
    char password[128];
} GattroseCreds;
```

### 6. AP Settings

**Command:** `a<ssid>|<password>|<channel>`

```
a<ssid>|<password>|<channel>
```

Example: `aFree_WiFi|password123|6`

**Response:**
```
[STX]aAP_CONFIG_SET[ETX]
```

### 7. Beacon Flooding

**Command:** `b<mode>[ssid]`

| Command | Description |
|---------|-------------|
| `bs` | Stop beacon flood |
| `br` | Random SSIDs (flood) |
| `bk` | Rickroll SSIDs |
| `bc<ssid>` | Custom SSID (e.g., `bcFreeWiFi`) |

**Responses:**
```
[STX]bBEACON_STOP[ETX]
[STX]bBEACON_RANDOM[ETX]
[STX]bBEACON_RICKROLL[ETX]
[STX]bBEACON_CUSTOM:FreeWiFi[ETX]
```

### 8. BLE Commands

**Command:** `l<action>`

| Command | Description |
|---------|-------------|
| `ls` | Start BLE scan (5 seconds) |
| `lg` | Get BLE device list |
| `lp` | Start BLE spam |
| `lx` | Stop all BLE operations |

**Responses:**
```
[STX]lBLE_SCANNING[ETX]
[STX]lSCAN_DONE:12[ETX]       // Found 12 BLE devices
[STX]lBLE_SPAM_ON[ETX]
[STX]lBLE_STOP[ETX]

// Response to 'lg' command:
[STX]i12[ETX]                 // 12 BLE devices
[STX]lAA:BB:CC:DD:EE:FF|iPhone|-52[ETX]
[STX]l11:22:33:44:55:66|Unknown|-78[ETX]
      ^                 ^       ^
      |                 |       +-- RSSI
      |                 +-- Device name
      +-- BLE address
```

**BLE device data structure:**
```c
typedef struct {
    char address[18];
    char name[64];
    int rssi;
} GattroseBLEDevice;
```

**Note:** BLE is initialized on-demand (not at boot) to avoid conflicts with WiFi scanning.

### 9. System Info

**Command:** `i`

**Response:**
```
[STX]iV:2.1|N:64|C:8|CH:6|D:2|B:1|W:0|BLE:0[ETX]
      ^     ^    ^   ^    ^   ^   ^   ^
      |     |    |   |    |   |   |   +-- BLE devices count
      |     |    |   |    |   |   +-- WiFi AP active (0/1)
      |     |    |   |    |   +-- Beacon active (0/1)
      |     |    |   |    +-- Deauth tasks running
      |     |    |   +-- Current channel
      |     |    +-- Clients detected
      |     +-- Networks found
      +-- Firmware version
```

### 10. Stop All

**Command:** `x`

Stops ALL operations: deauth, beacon, evil twin, BLE, monitor mode.

**Response:**
```
[STX]xALL_STOPPED[ETX]
```

### 11. LED Control

**Command:** `r<args>`

| Command | Description |
|---------|-------------|
| `r0` | LED off |
| `r1` | WiFi scan effect (cyan-blue-green pulse) |
| `r2` | BLE scan effect (purple-magenta pulse) |
| `r3` | Attack effect (red-orange fast pulse) |
| `r<R>,<G>,<B>` | Static color (e.g., `r255,0,128` for pink) |

**Responses:**
```
[STX]rLED_OFF[ETX]              // LED turned off
[STX]rLED_EFFECT:1[ETX]         // Effect mode 1 started
[STX]rLED:255,0,128[ETX]        // Static color set to R=255, G=0, B=128
[STX]eLED_NO_ARGS[ETX]          // Error: no arguments provided
```

**Examples:**
```
r0           -> Turn LED off
r1           -> Start WiFi scan effect
r2           -> Start BLE scan effect
r3           -> Start attack effect
r255,255,255 -> White (all on)
r0,255,0     -> Green (ready)
r255,0,0     -> Red (error/attack)
r0,255,255   -> Cyan
r255,0,255   -> Purple/Magenta
```

**Note:** BW16 LEDs are active-LOW. The firmware handles this internally.

---

## Flipper App UI Suggestions

### Main Menu
```
[Gattrose-NG v2.1]
> Scan Networks
> Saved Networks
> Client Sniff
> Evil Twin
> Beacon Flood
> BLE Tools
> LED Control      <- NEW
> Settings
```

### After Scan - Network Options
```
[MyWiFi] -45dB CH6 WPA2
  3 clients detected
  [NO PMF - Attackable]
> Deauth (Broadcast)
> Deauth (Select Client)
> Clone as Evil Twin
> View Clients
> Back

[SecureNet] -52dB CH11 WPA3
  [PMF PROTECTED]
> View Details (deauth blocked)
> Clone as Evil Twin
> Back
```

### Client Sniff View
```
[Client Sniff]
Monitor: ON
Found: 8 clients

AP: MyWiFi (idx 3)
  > AA:BB:CC:DD:EE:FF -45dB [Kick]
  > 11:22:33:44:55:66 -62dB [Kick]
AP: OtherNet (idx 7)
  > 22:33:44:55:66:77 -71dB [Kick]
```

### LED Control
```
[LED Control]
> Off
> WiFi Scan Effect (Cyan)
> BLE Scan Effect (Purple)
> Attack Effect (Red)
> Custom Color...
  [R: 255] [G: 128] [B: 0]
```

### BLE Tools
```
[BLE Tools]
> Scan Devices
> View Devices (12)
> BLE Spam
> Stop
```

### Evil Twin Portals
```
[Select Portal]
> Default (Generic)
> Google
> Facebook
> Amazon
> Apple
> Netflix
> Microsoft
```

---

## Migration Notes from KinimodD/DelfyRTL

### Commands That Work The Same
- `s` - scan
- `g` - get networks
- `d` - deauth (basic form)
- `b` - beacon
- `w` - wifi AP

### Commands With Extended Functionality
- `d` - now supports `-<reason>-<mac>` for targeted deauth
- `w` - now supports portals 1-7 (was 1-3)

### New Commands
- `m` - monitor mode (client detection)
- `c` - get client list
- `k` - client-only attack (kick by MAC)
- `l` - BLE operations
- `r` - LED control
- `a` - AP settings
- `i` - extended info
- `x` - stop all

### Response Changes
- Network response now includes PMF and hidden flags
- New response types: `m`, `l`, `k`, `C`
- `r` response used for both ready AND LED status

---

## Quick Reference Card

```
SCAN:     s[time]           -> sDONE:N
GET:      g                 -> i<count> then n<data>...
                               n: idx|ssid|bssid|ch|rssi|band|clients|sec|pmf|hidden
DEAUTH:   d<idx>[-R][-MAC]  -> dDEAUTH:N / dSTOPPED
          ds (stop)
KICKCLI:  k<mac>[-R]        -> kCLIENT_DEAUTH:MAC
MONITOR:  m1/m0             -> mMONITOR_ON/OFF
CLIENTS:  c                 -> i<count> then c<data>...
                               c: ap_idx|mac|rssi
EVILTWIN: w0-7              -> wAP_ON:N / wAP_OFF
PORTAL:   p0-7              -> pPORTAL:N
BEACON:   br/bk/bc<ssid>/bs -> bBEACON_*
BLE:      ls/lg/lp/lx       -> lBLE_* / lSCAN_DONE:N
APCONF:   a<ssid>|<pw>|<ch> -> aAP_CONFIG_SET
INFO:     i                 -> iV:...|N:...|C:...|...
STOPALL:  x                 -> xALL_STOPPED
LED:      r0/r1/r2/r3       -> rLED_OFF / rLED_EFFECT:N
          r<R>,<G>,<B>      -> rLED:R,G,B

AUTO:
CREDS:    (auto)            -> C<user>|<pass>
NEWCLIENT:(auto)            -> c<ap>|<mac>|<rssi>
READY:    (boot)            -> rGATTROSE-NG:2.1
```

---

## Error Handling

| Error Response | Meaning | Action |
|---------------|---------|--------|
| `eSCAN_IN_PROGRESS` | Scan already running | Wait or ignore |
| `eMAX_DEAUTH_TASKS` | Too many deauths (max 5) | Stop some first |
| `eALREADY_DEAUTHING` | Network already targeted | Ignore |
| `eINVALID_INDEX` | Network index doesn't exist | Refresh scan |
| `eCLIENT_NOT_FOUND` | Client MAC not in list | Run monitor first |
| `eINVALID_MAC` | Bad MAC format | Check format XX:XX:XX:XX:XX:XX |
| `eLED_NO_ARGS` | LED command missing args | Provide color or mode |

---

## Boot Sequence

On power-up, BW16 performs:

1. **Morse code LED sequence** - "GATTROSE NG 2.1"
   - Consonants: Purple (G, T, T, R, S, N, G)
   - Vowels: Cyan (A, O, E)
   - Numbers: Purple (2, 1)
   - Period: White (.-.-.-)

2. **Console output** (visible on USB serial):
   ```
   MORSE:
   G:--. A:.- T:- T:- R:.-. O:--- S:... E:. N:-. G:--. 2:..--- .:.-.-.- 1:.----
   ```

3. **LED turns solid green** (ready state)

4. **Sends ready message:**
   ```
   [STX]rGATTROSE-NG:2.1[ETX]
   ```

**No auto-scan** - scans must be initiated manually.

**Your app should:**
1. Wait for `r` response containing "GATTROSE-NG" to confirm connection
2. Send `s` to start a scan when ready
3. Wait for `sDONE:N` to know scan is complete
4. Send `g` to get network list

---

## Hardware Notes

**UART Settings:**
- Baud: 115200
- Data: 8 bits
- Stop: 1 bit
- Parity: None
- Flow: None

**Pin Connections:**
```
BW16 TX1 (PA14) -> Flipper RX (GPIO 14)
BW16 RX1 (PA13) -> Flipper TX (GPIO 13)
BW16 GND        -> Flipper GND (GPIO 8)
BW16 5V         -> Flipper 5V  (GPIO 1)
```

**LED Pin Mapping (Ai-Thinker BW16):**
```
LED_R = Pin 12 (PA_12)
LED_G = Pin 10 (PA_14) - Note: No PWM support
LED_B = Pin 11 (PA_13)
```

**LED Status (on BW16):**
- **Green steady**: System ready/idle
- **Cyan-Blue-Green pulsing**: WiFi scanning in progress
- **Purple-Magenta-Pink pulsing**: BLE scanning in progress
- **Red-Orange fast pulse**: Attack (deauth) active
- **Red steady**: Error/failure
- **Morse code on boot**: Purple consonants, cyan vowels, white punctuation
- **Controllable via `r` command**: App can set any RGB color or effect

**USB Serial Testing:**
The firmware accepts commands from both Serial1 (Flipper GPIO) AND Serial (USB) for testing without a Flipper connected. Connect via USB at 115200 baud and send STX-framed commands.

---

## CLI Testing Tool

A Python CLI tool is included for testing without a Flipper:

**Location:** `gattrose_cli.py`

**Usage:**
```bash
# Interactive mode
./gattrose_cli.py

# Flash firmware first
./gattrose_cli.py --flash

# Specify port
./gattrose_cli.py --port /dev/ttyUSB1

# Compile only
./gattrose_cli.py --compile
```

**Interactive Commands:**
```
scan [ms]        - Scan for networks (default 5000ms)
list [filter]    - List networks (optional SSID filter)
find <ssid>      - Find network by name (partial match)
monitor [sec]    - Enable client sniffing (default 10s)
clients          - List detected clients
deauth <idx>     - Deauth network by index
attack <ssid>    - Find and attack network by name
stop             - Stop all attacks
led <r,g,b>      - Set static LED color
led <0-3>        - Set LED effect mode
info             - Show device info
flash            - Compile and flash firmware
compile          - Compile firmware only
raw <cmd> [args] - Send raw command
quit             - Exit
```

---

## Troubleshooting

### No response from board
1. Check serial connection (correct port, 115200 baud)
2. Press RESET on the BW16
3. Wait for morse code to complete (~5 seconds)
4. Check for "GATTROSE-NG:2.1" ready message

### Deauth not working
1. Check if target network has PMF enabled (pmf=1 in network list)
2. PMF-protected networks are IMMUNE to deauth by design
3. Try a different network without PMF
4. Ensure you're on the correct channel

### No clients detected
1. Start monitor mode first (`m1`)
2. Wait 10-20 seconds for clients to be captured
3. Clients must be actively transmitting data
4. Idle devices may not be detected

### LED not changing
1. BW16 LEDs are active-LOW (handled by firmware)
2. After morse code, LED should be solid green
3. Try `r255,0,0` for red or `r0,255,0` for green
4. If stuck white, reset the board

### Flash failing
1. Put board in burn mode: Hold BURN, press RESET, release BURN
2. Red LED should be on (burn mode indicator)
3. "All images are sent successfully!" = success
4. "Upload Image done" without success message = try again

---

## Version History

### v2.1 (Current)
- Fixed client detection RSSI (now accurate, was always -128)
- Fixed client-to-AP association (uses driver BSSID)
- Added LED control command (`r`)
- Added morse code boot sequence with console output
- Changed ready LED from red to green
- Added PMF detection using correct RTL8720 security flags
- Removed auto-scan at boot
- Added CLI testing tool

### v2.0
- Initial merged firmware
- Combined KinimodD + Gattrose features
- Client detection (buggy RSSI)
- BLE support
- Multiple portal types

---

## License

For authorized security testing, educational purposes, and CTF challenges only.
