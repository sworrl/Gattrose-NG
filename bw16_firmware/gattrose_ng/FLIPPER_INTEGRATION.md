# Gattrose-NG Flipper Zero Integration

Communication protocol and command reference for Flipper Zero integration with Gattrose-NG BW16 firmware.

## Hardware Connection

```
Flipper Zero          BW16 Module
===========           ===========
Pin 1 (5V)    -------> 5V
Pin 8 (GND)   -------> GND
Pin 13 (TX)   -------> RX1 (PA13)
Pin 14 (RX)   <------- TX1 (PA14)
```

**Important Notes:**
- Use **Serial1** (TX1/RX1) on BW16, NOT Serial (TX0/RX0)
- Enable 5V on GPIO in Flipper settings: `Settings > System > GPIO 5V Control > Enable`
- Baud rate: **115200**
- Do NOT connect external power when Flipper 5V is connected

## Protocol Format

All communication uses binary-framed messages:

### Command Format (Flipper -> BW16)
```
[STX][CMD][SEP][ARGS][ETX]
```
- `STX` (0x02): Start of message
- `CMD`: Single character command
- `SEP` (0x1D): Field separator (optional)
- `ARGS`: Command arguments (variable)
- `ETX` (0x03): End of message

### Response Format (BW16 -> Flipper)
```
[STX][RESP_TYPE][SEP][DATA][ETX]
```
- `STX` (0x02): Start of response
- `RESP_TYPE`: Single character response type
- `SEP` (0x1D): Field separator
- `DATA`: Response data
- `ETX` (0x03): End of response

## Commands Reference

### Scan Commands

| Command | Description | Example |
|---------|-------------|---------|
| `s` | Scan all channels (default 5 sec) | `[STX]s[ETX]` |
| `s<ms>` | Scan with custom duration | `[STX]s10000[ETX]` (10 sec) |
| `g` | Get network list | `[STX]g[ETX]` |
| `c` | Get client list | `[STX]c[ETX]` |

### Deauthentication Commands

| Command | Description | Example |
|---------|-------------|---------|
| `d<idx>` | Deauth network by index | `[STX]d0[ETX]` |
| `d<idx>-<reason>` | Deauth with reason code | `[STX]d0-7[ETX]` |
| `ds` | Stop all deauth attacks | `[STX]ds[ETX]` |
| `k<mac>` | Deauth specific client | `[STX]kAA:BB:CC:DD:EE:FF[ETX]` |
| `k<mac>-<reason>` | Deauth client with reason | `[STX]kAA:BB:CC:DD:EE:FF-7[ETX]` |

**Reason Codes (802.11):**
- `1`: Unspecified
- `2`: Auth no longer valid (default)
- `3`: Station leaving
- `4`: Inactivity
- `5`: AP cannot handle
- `6`: Class 2 frame from non-auth
- `7`: Class 3 frame from non-assoc

### Beacon Flood Commands

| Command | Description | Example |
|---------|-------------|---------|
| `br` | Start random beacon flood | `[STX]br[ETX]` |
| `bk` | Start Rickroll beacon flood | `[STX]bk[ETX]` |
| `bc<ssid>` | Custom SSID beacon | `[STX]bcMyNetwork[ETX]` |
| `bs` | Stop beacon flood | `[STX]bs[ETX]` |

### Evil Twin / AP Commands

| Command | Description | Example |
|---------|-------------|---------|
| `w0` | Disable AP | `[STX]w0[ETX]` |
| `w1` | Enable AP (default portal) | `[STX]w1[ETX]` |
| `w2` | Enable AP (Google portal) | `[STX]w2[ETX]` |
| `w3` | Enable AP (Facebook portal) | `[STX]w3[ETX]` |
| `w4` | Enable AP (Amazon portal) | `[STX]w4[ETX]` |
| `w5` | Enable AP (Apple portal) | `[STX]w5[ETX]` |
| `w6` | Enable AP (Netflix portal) | `[STX]w6[ETX]` |
| `w7` | Enable AP (Microsoft portal) | `[STX]w7[ETX]` |
| `a<ssid>\|<pass>\|<ch>` | Set AP config | `[STX]aFreeWifi\|pass123\|6[ETX]` |

### BLE Commands (Currently Disabled)

| Command | Description | Example |
|---------|-------------|---------|
| `ls` | Start BLE scan | `[STX]ls[ETX]` |
| `lg` | Get BLE device list | `[STX]lg[ETX]` |
| `lp` | Start BLE spam | `[STX]lp[ETX]` |
| `lx` | Stop BLE operations | `[STX]lx[ETX]` |

### Monitor Mode Commands

| Command | Description | Example |
|---------|-------------|---------|
| `m1` | Enable promiscuous mode | `[STX]m1[ETX]` |
| `m0` | Disable promiscuous mode | `[STX]m0[ETX]` |

### LED Control Commands

| Command | Description | Example |
|---------|-------------|---------|
| `r0` | LED off | `[STX]r0[ETX]` |
| `r1` | WiFi scan effect (cyan) | `[STX]r1[ETX]` |
| `r2` | BLE scan effect (purple) | `[STX]r2[ETX]` |
| `r3` | Attack effect (red) | `[STX]r3[ETX]` |
| `r<R>,<G>,<B>` | Static RGB color | `[STX]r255,0,128[ETX]` |

### System Commands

| Command | Description | Example |
|---------|-------------|---------|
| `i` | Get device info | `[STX]i[ETX]` |
| `x` | Stop all operations | `[STX]x[ETX]` |

## Response Types

| Type | Description | Example Data |
|------|-------------|--------------|
| `r` | Ready/boot | `GATTROSE-NG:2.1` |
| `s` | Scan status | `SCANNING` or `SCAN_DONE:<count>` |
| `n` | Network entry | `<idx>\|<ssid>\|<bssid>\|<rssi>\|<ch>\|<sec>\|<pmf>\|<clients>` |
| `d` | Deauth status | `DEAUTH:<idx>` or `STOPPED` |
| `b` | Beacon status | `BEACON_RANDOM` / `BEACON_STOP` |
| `w` | AP status | `AP_ON:<portal>` / `AP_OFF` |
| `l` | BLE status | `BLE_SCANNING` / `BLE_SPAM_ON` |
| `m` | Monitor status | `MONITOR_ON` / `MONITOR_OFF` |
| `i` | Info response | `V:2.1\|N:<nets>\|C:<clients>\|CH:<ch>\|D:<deauth>\|B:<beacon>\|W:<ap>\|BLE:<ble>` |
| `e` | Error | `INVALID_INDEX` / `SCAN_BUSY` / etc. |
| `k` | Client deauth | `CLIENT_DEAUTH:<mac>` |
| `x` | Stop all | `ALL_STOPPED` |

## Network List Format

When requesting networks with `g`, response contains multiple `n` type messages:

```
[STX]n[SEP]0|NetworkName|AA:BB:CC:DD:EE:FF|-45|6|4|0|3[ETX]
```

Fields (pipe-separated):
1. Index
2. SSID
3. BSSID
4. RSSI (dBm)
5. Channel
6. Security (bitmask)
7. PMF (0=no, 1=yes - cannot deauth if PMF)
8. Client count

**Security Bitmask:**
- `0x01`: WEP
- `0x02`: TKIP
- `0x04`: AES/CCMP
- `0x08`: WPA
- `0x10`: WPA2
- `0x20`: WPA3

## Client List Format

When requesting clients with `c`, response contains multiple `c` type messages:

```
[STX]c[SEP]AA:BB:CC:DD:EE:FF|-55|2[ETX]
```

Fields:
1. Client MAC
2. RSSI
3. Associated AP index

## Typical Workflow

### Basic Scan and Deauth
```
1. Wait for boot:       <- [STX]r[SEP]GATTROSE-NG:2.1[ETX]
2. Start scan:          -> [STX]s5000[ETX]
3. Scan response:       <- [STX]s[SEP]SCANNING[ETX]
4. Wait for complete:   <- [STX]s[SEP]SCAN_DONE:25[ETX]
5. Get networks:        -> [STX]g[ETX]
6. Receive networks:    <- (multiple n responses)
7. Start deauth:        -> [STX]d0[ETX]
8. Deauth response:     <- [STX]d[SEP]DEAUTH:0[ETX]
9. Stop when done:      -> [STX]ds[ETX]
10. Stop response:      <- [STX]d[SEP]STOPPED[ETX]
```

### Client Detection
```
1. Scan networks:       -> [STX]s[ETX]
2. Enable monitor:      -> [STX]m1[ETX]
3. Wait for clients
4. Get clients:         -> [STX]c[ETX]
5. Target specific:     -> [STX]kAA:BB:CC:DD:EE:FF[ETX]
```

## LED Behavior

| State | LED Color | Pattern |
|-------|-----------|---------|
| Boot/Ready | Green | Solid |
| Scanning | Cyan | Rainbow cycle |
| Deauth active | Blue | Flashing |
| AP active | Green | Solid |
| Error | Red | Solid |

## Error Handling

Common error responses:
- `SCAN_BUSY`: Scan already in progress
- `INVALID_INDEX`: Network index out of range
- `INVALID_MAC`: Malformed MAC address
- `NO_NETWORKS`: No networks scanned yet

## Notes

- **PMF Networks**: Networks with Protected Management Frames (PMF=1) cannot be deauthenticated
- **5GHz Support**: Full 5GHz band scanning and attack support
- **Concurrent Operations**: Multiple deauth tasks can run simultaneously
- **Channel Hopping**: Deauth task automatically sets channel per target

## Testing via USB Serial

The same protocol works over USB Serial (Serial) for testing without Flipper:
```bash
# Connect at 115200 baud
# Send binary commands (use xxd or hex terminal)
echo -ne '\x02s\x03' > /dev/ttyUSB0
```
