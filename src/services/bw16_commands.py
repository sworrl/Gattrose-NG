"""
BW16 (RTL8720DN) Command Definitions and Parsers

Defines Evil-BW16 firmware serial commands and response parsers.
Used by BW16Service for communication with the BW16 module through
Flipper Zero UART bridge.

Evil-BW16 Firmware: https://github.com/7h30th3r0n3/Evil-BW16
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Tuple


class BW16Band(Enum):
    """WiFi frequency band"""
    BAND_2_4GHZ = "2.4GHz"
    BAND_5GHZ = "5GHz"
    DUAL_BAND = "dual"


class BW16State(Enum):
    """BW16 operational state"""
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    SCANNING = "scanning"
    DEAUTHING = "deauthing"
    SNIFFING = "sniffing"
    BRIDGE_MODE = "bridge_mode"


class BW16SniffType(Enum):
    """Packet sniff types"""
    ALL = "all"
    BEACON = "beacon"
    PROBE = "probe"
    DEAUTH = "deauth"
    EAPOL = "eapol"
    PWNAGOTCHI = "pwnagotchi"


@dataclass
class BW16Network:
    """Represents a network discovered by BW16 scan"""
    index: int                      # Evil-BW16 target index (for set target command)
    bssid: str                      # MAC address
    ssid: str                       # Network name
    channel: int                    # WiFi channel
    rssi: int                       # Signal strength (dBm)
    encryption: str                 # WPA/WPA2/WPA3/Open
    band: BW16Band = field(default=BW16Band.BAND_2_4GHZ)
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    @property
    def is_5ghz(self) -> bool:
        """Check if network is on 5GHz band"""
        return self.channel >= 36

    @staticmethod
    def band_from_channel(channel: int) -> BW16Band:
        """Determine band from channel number"""
        if channel >= 36:
            return BW16Band.BAND_5GHZ
        return BW16Band.BAND_2_4GHZ

    def __post_init__(self):
        """Set band based on channel after initialization"""
        self.band = self.band_from_channel(self.channel)


@dataclass
class BW16EAPOLFrame:
    """Captured EAPOL frame from BW16 sniff"""
    timestamp: datetime
    bssid: str
    client_mac: str
    frame_type: str                 # M1, M2, M3, M4 (4-way handshake messages)
    raw_data: bytes
    channel: int

    @property
    def message_number(self) -> int:
        """Get handshake message number (1-4)"""
        if self.frame_type.upper() in ('M1', 'MSG1', '1'):
            return 1
        elif self.frame_type.upper() in ('M2', 'MSG2', '2'):
            return 2
        elif self.frame_type.upper() in ('M3', 'MSG3', '3'):
            return 3
        elif self.frame_type.upper() in ('M4', 'MSG4', '4'):
            return 4
        return 0


@dataclass
class BW16Config:
    """BW16 configuration state"""
    channel: Optional[int] = None
    start_channel: int = 1          # 1 for 2.4GHz, 36 for 5GHz
    hop_enabled: bool = True
    cycle_delay: int = 1000         # ms between attack cycles
    scan_time: int = 5000           # ms scan duration
    num_frames: int = 10            # deauth frames per target
    targets: List[int] = field(default_factory=list)
    led_enabled: bool = True
    scan_cycles: bool = True


# ============================================================================
# EVIL-BW16 COMMAND DEFINITIONS
# ============================================================================

class BW16Commands:
    """Evil-BW16 serial command definitions"""

    # Scanning
    SCAN = "scan"
    RESULTS = "results"

    # Deauthentication
    START_DEAUTH = "start deauther"
    STOP_DEAUTH = "stop deauther"
    RANDOM_ATTACK = "random_attack"
    ATTACK_TIME = "attack_time"      # attack_time <ms>
    DISASSOC = "disassoc"            # Continuous disassociation

    # Sniffing
    START_SNIFF = "start sniff"
    STOP_SNIFF = "stop sniff"
    SNIFF_BEACON = "sniff beacon"
    SNIFF_PROBE = "sniff probe"
    SNIFF_DEAUTH = "sniff deauth"
    SNIFF_EAPOL = "sniff eapol"
    SNIFF_PWNAGOTCHI = "sniff pwnagotchi"
    SNIFF_ALL = "sniff all"

    # Channel control
    SET_CHANNEL = "set ch"           # set ch <channel>
    SET_START_CHANNEL = "set start_channel"  # 1 for 2.4GHz, 36 for 5GHz
    HOP_ON = "hop on"
    HOP_OFF = "hop off"

    # Configuration
    SET_TARGET = "set target"        # set target <indices> (comma-separated)
    SET_CYCLE_DELAY = "set cycle_delay"
    SET_SCAN_TIME = "set scan_time"
    SET_NUM_FRAMES = "set num_frames"
    SET_SCAN_CYCLES = "set scan_cycles"  # on/off
    SET_LED = "set led"              # on/off

    # Info/Status
    INFO = "info"
    HELP = "help"


# ============================================================================
# RESPONSE PARSERS
# ============================================================================

class BW16ResponseParser:
    """Parse Evil-BW16 serial output responses"""

    # Regex patterns for parsing
    NETWORK_PATTERN = re.compile(
        r'(\d+)\s*[\|:]\s*'                    # Index
        r'([0-9A-Fa-f:]{17})\s*[\|:]\s*'       # BSSID
        r'(\d+)\s*[\|:]\s*'                    # Channel
        r'(-?\d+)\s*[\|:]\s*'                  # RSSI
        r'(\w+(?:/\w+)?)\s*[\|:]\s*'           # Encryption
        r'(.+?)(?:\s*$|\s*[\|:])',             # SSID
        re.IGNORECASE
    )

    # Alternative simpler pattern
    NETWORK_SIMPLE_PATTERN = re.compile(
        r'^\s*(\d+)\s+'                        # Index
        r'([0-9A-Fa-f:]{17})\s+'               # BSSID
        r'ch:?\s*(\d+)\s+'                     # Channel
        r'(-?\d+)\s*(?:dBm)?\s+'               # RSSI
        r'(\w+)\s+'                            # Encryption
        r'(.*)$',                              # SSID
        re.IGNORECASE | re.MULTILINE
    )

    EAPOL_PATTERN = re.compile(
        r'EAPOL\s*[\|:]\s*'
        r'([0-9A-Fa-f:]{17})\s*[\|:]\s*'       # BSSID
        r'([0-9A-Fa-f:]{17})\s*[\|:]\s*'       # Client MAC
        r'(M[1-4])\s*[\|:]\s*'                 # Message type
        r'([0-9A-Fa-f]+)',                     # Raw data (hex)
        re.IGNORECASE
    )

    INFO_PATTERN = re.compile(
        r'(\w+)\s*[:=]\s*(.+?)(?:\s*$|\s*[\|])',
        re.MULTILINE
    )

    @classmethod
    def parse_scan_results(cls, output: str) -> List[BW16Network]:
        """
        Parse scan results output from Evil-BW16

        Args:
            output: Raw serial output from 'results' command

        Returns:
            List of BW16Network objects
        """
        networks = []

        # Try primary pattern first
        for match in cls.NETWORK_PATTERN.finditer(output):
            try:
                network = BW16Network(
                    index=int(match.group(1)),
                    bssid=match.group(2).upper(),
                    channel=int(match.group(3)),
                    rssi=int(match.group(4)),
                    encryption=match.group(5).upper(),
                    ssid=match.group(6).strip()
                )
                networks.append(network)
            except (ValueError, IndexError):
                continue

        # If no matches, try simpler pattern
        if not networks:
            for match in cls.NETWORK_SIMPLE_PATTERN.finditer(output):
                try:
                    network = BW16Network(
                        index=int(match.group(1)),
                        bssid=match.group(2).upper(),
                        channel=int(match.group(3)),
                        rssi=int(match.group(4)),
                        encryption=match.group(5).upper(),
                        ssid=match.group(6).strip()
                    )
                    networks.append(network)
                except (ValueError, IndexError):
                    continue

        # Fallback: line-by-line parsing for various formats
        if not networks:
            networks = cls._parse_scan_results_fallback(output)

        return networks

    @classmethod
    def _parse_scan_results_fallback(cls, output: str) -> List[BW16Network]:
        """Fallback parser for non-standard output formats"""
        networks = []
        lines = output.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('--'):
                continue

            # Look for MAC address pattern
            mac_match = re.search(r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})', line)
            if not mac_match:
                continue

            bssid = mac_match.group(1).upper()

            # Try to extract other fields
            parts = re.split(r'\s+|\|', line)
            parts = [p.strip() for p in parts if p.strip()]

            # Find index (usually first number)
            index = 0
            for p in parts:
                if p.isdigit() and int(p) < 100:
                    index = int(p)
                    break

            # Find channel
            channel = 1
            ch_match = re.search(r'ch:?\s*(\d+)', line, re.IGNORECASE)
            if ch_match:
                channel = int(ch_match.group(1))
            else:
                for p in parts:
                    if p.isdigit() and 1 <= int(p) <= 165:
                        channel = int(p)
                        break

            # Find RSSI
            rssi = -50
            rssi_match = re.search(r'(-\d+)\s*(?:dBm)?', line)
            if rssi_match:
                rssi = int(rssi_match.group(1))

            # Find encryption
            encryption = "WPA2"
            for enc in ['WPA3', 'WPA2', 'WPA', 'WEP', 'OPN', 'OPEN']:
                if enc in line.upper():
                    encryption = enc
                    break

            # SSID is typically the last quoted string or last non-MAC word
            ssid = ""
            ssid_match = re.search(r'"([^"]*)"', line)
            if ssid_match:
                ssid = ssid_match.group(1)
            else:
                # Take last meaningful segment
                for p in reversed(parts):
                    if p and not re.match(r'^[0-9A-Fa-f:]+$', p) and not p.lstrip('-').isdigit():
                        ssid = p
                        break

            networks.append(BW16Network(
                index=index,
                bssid=bssid,
                channel=channel,
                rssi=rssi,
                encryption=encryption,
                ssid=ssid
            ))

        return networks

    @classmethod
    def parse_eapol_frame(cls, line: str, channel: int = 0) -> Optional[BW16EAPOLFrame]:
        """
        Parse EAPOL frame from sniff output

        Args:
            line: Single line from sniff output
            channel: Current channel (if known)

        Returns:
            BW16EAPOLFrame or None
        """
        match = cls.EAPOL_PATTERN.search(line)
        if match:
            try:
                raw_hex = match.group(4)
                return BW16EAPOLFrame(
                    timestamp=datetime.now(),
                    bssid=match.group(1).upper(),
                    client_mac=match.group(2).upper(),
                    frame_type=match.group(3).upper(),
                    raw_data=bytes.fromhex(raw_hex),
                    channel=channel
                )
            except (ValueError, IndexError):
                pass

        # Try alternative patterns
        # Pattern: "EAPOL M1 from AA:BB:CC:DD:EE:FF to 11:22:33:44:55:66"
        alt_match = re.search(
            r'EAPOL\s+(M[1-4])\s+(?:from\s+)?([0-9A-Fa-f:]{17})\s+(?:to\s+)?([0-9A-Fa-f:]{17})',
            line, re.IGNORECASE
        )
        if alt_match:
            return BW16EAPOLFrame(
                timestamp=datetime.now(),
                bssid=alt_match.group(2).upper(),
                client_mac=alt_match.group(3).upper(),
                frame_type=alt_match.group(1).upper(),
                raw_data=b'',  # No raw data in this format
                channel=channel
            )

        return None

    @classmethod
    def parse_info(cls, output: str) -> BW16Config:
        """
        Parse info command output

        Args:
            output: Raw serial output from 'info' command

        Returns:
            BW16Config object
        """
        config = BW16Config()

        for match in cls.INFO_PATTERN.finditer(output):
            key = match.group(1).lower().strip()
            value = match.group(2).strip()

            try:
                if key in ('channel', 'ch'):
                    config.channel = int(value) if value.isdigit() else None
                elif key in ('start_channel', 'start_ch'):
                    config.start_channel = int(value)
                elif key in ('hop', 'hopping'):
                    config.hop_enabled = value.lower() in ('on', 'true', '1', 'enabled')
                elif key in ('cycle_delay', 'delay'):
                    config.cycle_delay = int(value)
                elif key in ('scan_time', 'scantime'):
                    config.scan_time = int(value)
                elif key in ('num_frames', 'frames'):
                    config.num_frames = int(value)
                elif key in ('led',):
                    config.led_enabled = value.lower() in ('on', 'true', '1', 'enabled')
                elif key in ('scan_cycles',):
                    config.scan_cycles = value.lower() in ('on', 'true', '1', 'enabled')
                elif key in ('target', 'targets'):
                    # Parse comma-separated target indices
                    config.targets = [int(t.strip()) for t in value.split(',') if t.strip().isdigit()]
            except (ValueError, AttributeError):
                continue

        return config

    @classmethod
    def parse_sniff_line(cls, line: str) -> Tuple[str, Dict]:
        """
        Parse a sniff output line and determine its type

        Args:
            line: Single line from sniff output

        Returns:
            Tuple of (type, data_dict)
            type: 'beacon', 'probe', 'deauth', 'eapol', 'pwnagotchi', 'unknown'
        """
        line_upper = line.upper()

        # EAPOL frame
        if 'EAPOL' in line_upper:
            frame = cls.parse_eapol_frame(line)
            if frame:
                return ('eapol', {
                    'bssid': frame.bssid,
                    'client': frame.client_mac,
                    'type': frame.frame_type,
                    'raw': frame.raw_data.hex() if frame.raw_data else ''
                })

        # Beacon frame
        if 'BEACON' in line_upper:
            mac_match = re.search(r'([0-9A-Fa-f:]{17})', line)
            ssid_match = re.search(r'SSID[:\s]+([^\|]+)', line, re.IGNORECASE)
            return ('beacon', {
                'bssid': mac_match.group(1).upper() if mac_match else '',
                'ssid': ssid_match.group(1).strip() if ssid_match else ''
            })

        # Probe request/response
        if 'PROBE' in line_upper:
            mac_match = re.search(r'([0-9A-Fa-f:]{17})', line)
            ssid_match = re.search(r'SSID[:\s]+([^\|]+)', line, re.IGNORECASE)
            return ('probe', {
                'mac': mac_match.group(1).upper() if mac_match else '',
                'ssid': ssid_match.group(1).strip() if ssid_match else ''
            })

        # Deauth frame
        if 'DEAUTH' in line_upper or 'DISASSOC' in line_upper:
            macs = re.findall(r'([0-9A-Fa-f:]{17})', line)
            return ('deauth', {
                'bssid': macs[0].upper() if len(macs) > 0 else '',
                'client': macs[1].upper() if len(macs) > 1 else ''
            })

        # Pwnagotchi
        if 'PWNA' in line_upper or 'PWNAGOTCHI' in line_upper:
            name_match = re.search(r'name[:\s]+([^\|]+)', line, re.IGNORECASE)
            return ('pwnagotchi', {
                'name': name_match.group(1).strip() if name_match else 'Unknown'
            })

        return ('unknown', {'raw': line})

    @classmethod
    def is_command_success(cls, response: str) -> bool:
        """Check if command response indicates success"""
        if not response:
            return False

        response_lower = response.lower()

        # Check for error indicators
        error_indicators = ['error', 'failed', 'invalid', 'unknown command']
        for indicator in error_indicators:
            if indicator in response_lower:
                return False

        # Check for success indicators
        success_indicators = ['ok', 'success', 'done', 'started', 'stopped', 'set to']
        for indicator in success_indicators:
            if indicator in response_lower:
                return True

        # If no clear indicator, assume success if we got a response
        return len(response) > 0


# ============================================================================
# FLIPPER UART BRIDGE COMMANDS
# ============================================================================

class FlipperUARTCommands:
    """Flipper Zero UART bridge commands for BW16 communication"""

    # Enter UART passthrough mode
    UART_BRIDGE = "uart_bridge"      # uart_bridge <baud_rate>

    # GPIO UART (alternative method)
    GPIO_MODE = "gpio mode"          # gpio mode <pin> <mode>
    GPIO_SET = "gpio set"            # gpio set <pin> <value>

    # Exit commands
    EXIT_BRIDGE = b'\x03'            # Ctrl+C to exit bridge mode

    @staticmethod
    def uart_bridge_command(baud_rate: int = 115200) -> str:
        """Get command to enter UART bridge mode"""
        return f"uart_bridge {baud_rate}"

    @staticmethod
    def get_exit_sequence() -> bytes:
        """Get byte sequence to exit bridge mode"""
        return b'\x03'  # Ctrl+C


# ============================================================================
# HANDSHAKE TRACKING
# ============================================================================

@dataclass
class HandshakeTracker:
    """Track EAPOL frames for handshake completion detection"""

    bssid: str
    frames: Dict[int, BW16EAPOLFrame] = field(default_factory=dict)  # msg_num -> frame
    started_at: datetime = field(default_factory=datetime.now)
    client_mac: Optional[str] = None

    def add_frame(self, frame: BW16EAPOLFrame) -> bool:
        """
        Add EAPOL frame to tracker

        Returns:
            True if handshake is now complete
        """
        msg_num = frame.message_number
        if msg_num == 0:
            return False

        self.frames[msg_num] = frame

        # Track client MAC from M2 (supplicant)
        if msg_num == 2:
            self.client_mac = frame.client_mac

        return self.is_complete

    @property
    def is_complete(self) -> bool:
        """Check if we have a complete 4-way handshake"""
        # Minimum viable handshake: M1 + M2
        # Full handshake: M1 + M2 + M3 + M4
        return 1 in self.frames and 2 in self.frames

    @property
    def is_full(self) -> bool:
        """Check if we have all 4 messages"""
        return all(i in self.frames for i in [1, 2, 3, 4])

    @property
    def has_messages(self) -> Tuple[bool, bool, bool, bool]:
        """Return tuple of (has_m1, has_m2, has_m3, has_m4)"""
        return (
            1 in self.frames,
            2 in self.frames,
            3 in self.frames,
            4 in self.frames
        )

    @property
    def quality_score(self) -> int:
        """Calculate handshake quality score (0-100)"""
        has = self.has_messages
        score = 0

        if has[0]:  # M1
            score += 25
        if has[1]:  # M2 - most important
            score += 40
        if has[2]:  # M3
            score += 20
        if has[3]:  # M4
            score += 15

        return score

    def get_all_raw_data(self) -> bytes:
        """Get concatenated raw data from all frames"""
        data = b''
        for i in [1, 2, 3, 4]:
            if i in self.frames and self.frames[i].raw_data:
                data += self.frames[i].raw_data
        return data
