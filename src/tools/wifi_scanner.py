import subprocess
import os
import time
import csv
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
import threading
from src.utils.logger import main_logger

# Import database service
try:
    from ..services.scan_database_service import get_scan_db_service
    DATABASE_ENABLED = True
except ImportError:
    DATABASE_ENABLED = False
    main_logger.warning("Database service not available - running without database")

# Import GPS service
try:
    from ..services.gps_service import get_gps_service
    GPS_ENABLED = True
except ImportError:
    GPS_ENABLED = False
    main_logger.warning("GPS service not available - running without GPS tracking")


class WiFiAccessPoint:
    """Represents a WiFi Access Point with all captured data"""

    def __init__(self, bssid: str):
        self.bssid = bssid
        self.ssid = ""
        self.channel = ""
        self.speed = ""
        self.encryption = ""
        self.cipher = ""
        self.authentication = ""
        self.power = ""
        self.beacons = 0
        self.iv = 0
        self.lan_ip = ""
        self.id_length = 0
        self.essid = ""
        self.key = ""
        self.first_seen = None
        self.last_seen = None
        self.clients = {}  # MAC -> WiFiClient
        self.wps_enabled = False
        self.wps_locked = False
        self.wps_version = ""
        self.attack_score = 0
        self.risk_level = "UNKNOWN"
        self.vendor = "Unknown"
        self.device_type = "Unknown Device"
        self.device_confidence = 0
        self.icon = "🌐"
        self._fingerprinted = False  # Track if already fingerprinted
        self._lock = threading.Lock()  # Thread safety for updates

    def update_from_csv_row(self, row: List[str]):
        """Update AP data from airodump-ng CSV row"""
        try:
            with self._lock:
                if len(row) >= 14:
                    self.bssid = row[0].strip()
                    self.first_seen = row[1].strip() if row[1].strip() else self.first_seen
                    self.last_seen = row[2].strip() if row[2].strip() else self.last_seen
                    self.channel = row[3].strip()
                    self.speed = row[4].strip()
                    self.encryption = row[5].strip()
                    self.cipher = row[6].strip()
                    self.authentication = row[7].strip()
                    self.power = row[8].strip()

                    if row[9].strip().isdigit():
                        self.beacons = int(row[9].strip())
                    if row[10].strip().isdigit():
                        self.iv = int(row[10].strip())

                    self.lan_ip = row[11].strip()

                    if row[12].strip().isdigit():
                        self.id_length = int(row[12].strip())

                    # ESSID/SSID is the last field
                    self.essid = row[13].strip() if len(row) > 13 else ""
                    self.ssid = self.essid

                # NOTE: Device fingerprinting moved to background thread
                # Scanner will call calculate_attack_score_async() separately
        except Exception as e:
            main_logger.error(f"Error parsing AP row: {e}")

    def calculate_attack_score(self):
        """Calculate attack difficulty score and identify device (thread-safe)"""
        if self._fingerprinted:
            return  # Already fingerprinted

        try:
            from src.tools.attack_scoring import AttackScorer
            from src.utils.mac_vendor import MACVendorLookup, DeviceFingerprinter

            with self._lock:
                hidden = not bool(self.ssid)
                has_clients = len(self.clients) > 0

                # Parse beacons to int
                try:
                    beacons_int = int(self.beacons) if self.beacons else 0
                except (ValueError, TypeError):
                    beacons_int = 0

                self.attack_score, self.risk_level = AttackScorer.calculate_score(
                    encryption=self.encryption,
                    authentication=self.authentication,
                    power=self.power,
                    wps_enabled=self.wps_enabled,
                    has_clients=has_clients,
                    hidden=hidden,
                    beacons=beacons_int,
                    channel=self.channel,
                    cipher=self.cipher
                )

                # Identify vendor and device
                self.vendor = MACVendorLookup.lookup_vendor(self.bssid)
                self.device_type, self.device_confidence = DeviceFingerprinter.identify_device(
                    mac=self.bssid,
                    vendor=self.vendor,
                    probed_ssids=[],
                    signal_strength=self.power,
                    is_ap=True
                )
                self.icon = DeviceFingerprinter.get_device_icon(self.device_type, is_ap=True)

                self._fingerprinted = True  # Mark as fingerprinted

            main_logger.debug(f"AP {self.bssid}: Vendor={self.vendor}, Device={self.device_type}, WPS={self.wps_enabled}, Score={self.attack_score}")
        except Exception as e:
            main_logger.exception(f"calculate_attack_score failed for {self.bssid}: {e}")

    def to_dict(self) -> Dict:
        """Convert to dictionary for display/storage"""
        return {
            'bssid': self.bssid,
            'ssid': self.ssid,
            'channel': self.channel,
            'speed': self.speed,
            'encryption': self.encryption,
            'cipher': self.cipher,
            'authentication': self.authentication,
            'power': self.power,
            'beacons': self.beacons,
            'iv': self.iv,
            'lan_ip': self.lan_ip,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen,
            'client_count': len(self.clients)
        }


class WiFiClient:
    """Represents a WiFi client station"""

    def __init__(self, mac: str):
        self.mac = mac
        self.bssid = ""  # Associated AP
        self.first_seen = None
        self.last_seen = None
        self.power = ""
        self.packets = 0
        self.probed_essids = []
        self.vendor = "Unknown"
        self.device_type = "Unknown Device"
        self.device_confidence = 0
        self.icon = "📶"
        self._fingerprinted = False  # Track if already fingerprinted
        self._lock = threading.Lock()  # Thread safety for updates

    def update_from_csv_row(self, row: List[str]):
        """Update client data from airodump-ng CSV row"""
        try:
            with self._lock:
                if len(row) >= 6:
                    self.mac = row[0].strip()
                    self.first_seen = row[1].strip() if row[1].strip() else self.first_seen
                    self.last_seen = row[2].strip() if row[2].strip() else self.last_seen
                    self.power = row[3].strip()

                    if row[4].strip().isdigit():
                        self.packets = int(row[4].strip())

                    self.bssid = row[5].strip()

                    # Probed ESSIDs (can be multiple)
                    if len(row) > 6:
                        probed = row[6].strip()
                        if probed and probed not in self.probed_essids:
                            self.probed_essids.append(probed)

                # NOTE: Device fingerprinting moved to background thread
                # Scanner will call identify_device() separately in thread pool
        except Exception as e:
            main_logger.error(f"Error parsing client row: {e}")

    def identify_device(self):
        """Identify client device based on MAC and probed SSIDs (thread-safe)"""
        if self._fingerprinted:
            return  # Already fingerprinted

        from src.utils.mac_vendor import MACVendorLookup, DeviceFingerprinter

        with self._lock:
            self.vendor = MACVendorLookup.lookup_vendor(self.mac)
            self.device_type, self.device_confidence = DeviceFingerprinter.identify_device(
                mac=self.mac,
                vendor=self.vendor,
                probed_ssids=self.probed_essids,
                signal_strength=self.power,
                is_ap=False
            )
            self.icon = DeviceFingerprinter.get_device_icon(self.device_type, is_ap=False)
            self._fingerprinted = True  # Mark as fingerprinted

    def to_dict(self) -> Dict:
        """Convert to dictionary for display/storage"""
        return {
            'mac': self.mac,
            'bssid': self.bssid,
            'power': self.power,
            'packets': self.packets,
            'probed_essids': ', '.join(self.probed_essids),
            'first_seen': self.first_seen,
            'last_seen': self.last_seen
        }


class WiFiScanner(QThread):
    """WiFi scanner that runs airodump-ng and emits real-time data"""

    # Signals
    ap_discovered = pyqtSignal(object)  # Emits WiFiAccessPoint
    ap_updated = pyqtSignal(object)  # Emits WiFiAccessPoint
    client_discovered = pyqtSignal(object, str)  # Emits WiFiClient, AP BSSID
    client_updated = pyqtSignal(object, str)  # Emits WiFiClient, AP BSSID
    status_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    scan_started = pyqtSignal()
    scan_stopped = pyqtSignal()

    def __init__(self, interface: str = "wlan0mon", channel: Optional[str] = None):
        super().__init__()
        self.interface = interface
        self.channel = channel
        self.running = False
        self.process = None
        self.wps_process = None
        self.output_prefix = None
        self.aps = {}  # BSSID -> WiFiAccessPoint
        self.clients = {}  # MAC -> WiFiClient
        self.wps_networks = {}  # BSSID -> WPS info
        # Thread pool for device fingerprinting (max 4 workers)
        self.fingerprint_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="fingerprint")
        self.fingerprint_queue = set()  # Track queued fingerprinting tasks

        # Database service for storing scan data
        self.scan_db = get_scan_db_service() if DATABASE_ENABLED else None

        # GPS service for location tracking (critical for wardriving/mapping)
        self.gps_service = get_gps_service() if GPS_ENABLED else None
        if self.gps_service:
            self.gps_service.start()  # Start background GPS updates
            main_logger.info(f"[GPS] {self.gps_service.get_status_string()}")

        # Scanning intelligence for saturation detection
        self.scan_start_time = None
        self.last_new_ap_time = None
        self.last_new_client_time = None
        self.ap_count_history = []  # Track AP count every 5 seconds
        self.client_count_history = []  # Track client count every 5 seconds
        self.saturation_threshold = 30  # seconds without new discoveries
        self.min_scan_time = 60  # minimum scan time before declaring saturation

    def run(self):
        """Main scanner thread"""
        try:
            self.running = True
            self.scan_start_time = time.time()  # Track scan start for saturation detection

            # Create output directory (use /tmp to avoid issues with spaces in project path)
            output_dir = Path("/tmp/gattrose-captures")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_prefix = str(output_dir / f"scan_{timestamp}")

            # Build airodump-ng command
            cmd = ['sudo', 'airodump-ng']

            if self.channel:
                cmd.extend(['-c', str(self.channel)])

            cmd.extend([
                '-w', self.output_prefix,
                '--output-format', 'csv',
                '--write-interval', '1',  # Write every 1 second
                self.interface
            ])

            self.status_message.emit(f"Starting scan on {self.interface}")
            self.status_message.emit(f"Command: {' '.join(cmd)}")
            main_logger.info(f"Starting airodump-ng with command: {' '.join(cmd)}")

            # Start airodump-ng
            # NOTE: stdout/stderr must NOT be piped - airodump doesn't work properly with pipes
            # Redirect to DEVNULL instead to avoid interfering with airodump's operation
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )

            self.scan_started.emit()
            self.status_message.emit("Scan started - capturing data...")
            main_logger.info("Scan started - capturing data...")

            # Initialize database for new scan
            if self.scan_db:
                self.scan_db.start_new_scan()
                self.scan_db.start_upsert_worker()
                self.status_message.emit("Database initialized for new scan")
                main_logger.info("Database initialized for new scan")

            # Start WPS scanning in parallel
            self.start_wps_scan()

            # Monitor CSV file for updates
            csv_file = f"{self.output_prefix}-01.csv"

            # Wait for CSV file to be created
            wait_count = 0
            while not os.path.exists(csv_file) and self.running and wait_count < 30:
                # Check if process died
                if self.process.poll() is not None:
                    # Process exited (stderr is DEVNULL so can't get error details)
                    error_msg = f"airodump-ng exited unexpectedly. Check that wlp7s0mon is in monitor mode."
                    self.error_occurred.emit(error_msg)
                    main_logger.error(error_msg)
                    self.running = False
                    return

                time.sleep(0.5)
                wait_count += 1

            if not os.path.exists(csv_file):
                # Check if process is still running
                if self.process.poll() is not None:
                    error_msg = f"airodump-ng failed to start. Check monitor mode and permissions."
                    self.error_occurred.emit(error_msg)
                    main_logger.error(error_msg)
                else:
                    error_msg = "CSV file not created - check airodump-ng. Process is running but not producing output. Try restarting monitor mode."
                    self.error_occurred.emit(error_msg)
                    main_logger.error(error_msg)
                self.running = False
                return

            # Parse CSV continuously
            last_size = 0
            save_counter = 0
            while self.running:
                try:
                    current_size = os.path.getsize(csv_file)

                    if current_size != last_size:
                        self.parse_csv(csv_file)
                        last_size = current_size

                    # Save extended CSV every 10 seconds
                    save_counter += 1
                    if save_counter >= 10:
                        self.save_extended_csv()
                        save_counter = 0

                except Exception as e:
                    self.error_occurred.emit(f"Error reading CSV: {e}")
                    main_logger.exception(f"Error reading CSV: {e}")

                time.sleep(1)  # Check every second

        except Exception as e:
            self.error_occurred.emit(f"Scanner error: {e}")
            main_logger.exception(f"Scanner error: {e}")
        finally:
            self.cleanup()

    def parse_csv(self, csv_file: str):
        """Parse airodump-ng CSV file"""
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Split into AP and Client sections
            # Note: Python's text mode converts \r\n to \n, so split on \n\n
            sections = content.split('\n\n')

            if len(sections) >= 1:
                self.parse_ap_section(sections[0])

            if len(sections) >= 2:
                self.parse_client_section(sections[1])

        except Exception as e:
            self.error_occurred.emit(f"CSV parse error: {e}")
            main_logger.exception(f"CSV parse error: {e}")

    def _fingerprint_ap_async(self, ap: WiFiAccessPoint):
        """Fingerprint AP in background thread"""
        try:
            ap.calculate_attack_score()
            # Emit update signal after fingerprinting completes
            self.ap_updated.emit(ap)
            # Update database with enriched data
            if self.scan_db:
                self._update_ap_in_db(ap)
        except Exception as e:
            main_logger.exception(f"Error fingerprinting AP {ap.bssid}: {e}")
        finally:
            # Remove from queue
            self.fingerprint_queue.discard(ap.bssid)

    def _fingerprint_client_async(self, client: WiFiClient):
        """Fingerprint client in background thread"""
        try:
            client.identify_device()
            # Emit update signal after fingerprinting completes
            self.client_updated.emit(client, client.bssid)
            # Update database with enriched data
            if self.scan_db:
                self._update_client_in_db(client, client.bssid)
        except Exception as e:
            main_logger.exception(f"Error fingerprinting client {client.mac}: {e}")
        finally:
            # Remove from queue
            self.fingerprint_queue.discard(client.mac)

    def parse_ap_section(self, section: str):
        """Parse Access Points section of CSV"""
        try:
            # Note: Python's text mode converts \r\n to \n
            lines = section.strip().split('\n')
            if len(lines) < 2:
                return

            # Skip header
            for line in lines[2:]:
                if not line.strip():
                    continue

                # Parse CSV row
                row = list(csv.reader([line]))[0] if line else []
                if len(row) < 14:
                    continue

                bssid = row[0].strip()
                if not bssid or not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', bssid):
                    continue

                # New AP or update existing
                if bssid not in self.aps:
                    ap = WiFiAccessPoint(bssid)
                    ap.update_from_csv_row(row)
                    self.aps[bssid] = ap
                    self.last_new_ap_time = time.time()  # Track discovery time for saturation
                    self.ap_discovered.emit(ap)
                    self.status_message.emit(f"New AP: {ap.ssid or bssid} [{ap.encryption}]")
                    main_logger.info(f"New AP discovered: {ap.ssid or bssid} [{ap.bssid}] [{ap.encryption}]")

                    # Queue fingerprinting in background
                    if bssid not in self.fingerprint_queue:
                        self.fingerprint_queue.add(bssid)
                        self.fingerprint_executor.submit(self._fingerprint_ap_async, ap)
                else:
                    ap = self.aps[bssid]
                    ap.update_from_csv_row(row)
                    self.ap_updated.emit(ap)

                # Update database
                if self.scan_db:
                    self._update_ap_in_db(ap)

        except Exception as e:
            self.error_occurred.emit(f"AP parse error: {e}")
            main_logger.exception(f"AP parse error: {e}")

    def parse_client_section(self, section: str):
        """Parse Clients section of CSV"""
        try:
            # Note: Python's text mode converts \r\n to \n
            lines = section.strip().split('\n')
            if len(lines) < 2:
                return

            # Skip header
            for line in lines[2:]:
                if not line.strip():
                    continue

                # Parse CSV row
                row = list(csv.reader([line]))[0] if line else []
                if len(row) < 6:
                    continue

                mac = row[0].strip()
                if not mac or not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', mac):
                    continue

                bssid = row[5].strip()

                # New client or update existing
                if mac not in self.clients:
                    client = WiFiClient(mac)
                    client.update_from_csv_row(row)
                    self.clients[mac] = client

                    # Add to AP's client list
                    if bssid and bssid in self.aps:
                        self.aps[bssid].clients[mac] = client

                    self.last_new_client_time = time.time()  # Track discovery time for saturation
                    self.client_discovered.emit(client, bssid)
                    self.status_message.emit(f"New client: {mac} -> {bssid}")
                    main_logger.info(f"New client discovered: {mac} -> {bssid}")

                    # Queue fingerprinting in background
                    if mac not in self.fingerprint_queue:
                        self.fingerprint_queue.add(mac)
                        self.fingerprint_executor.submit(self._fingerprint_client_async, client)
                else:
                    client = self.clients[mac]
                    old_bssid = client.bssid
                    client.update_from_csv_row(row)

                    # Handle client moving to different AP
                    if old_bssid != bssid:
                        if old_bssid and old_bssid in self.aps:
                            self.aps[old_bssid].clients.pop(mac, None)
                        if bssid and bssid in self.aps:
                            self.aps[bssid].clients[mac] = client

                    self.client_updated.emit(client, bssid)

                # Update database
                if self.scan_db:
                    self._update_client_in_db(client, bssid)

        except Exception as e:
            self.error_occurred.emit(f"Client parse error: {e}")
            main_logger.exception(f"Client parse error: {e}")

    def start_wps_scan(self):
        """Start WPS scanning using wash tool"""
        try:
            import threading

            # Check if wash is available
            wash_check = subprocess.run(['which', 'wash'], capture_output=True)
            if wash_check.returncode != 0:
                self.status_message.emit("Note: 'wash' tool not found - WPS detection disabled")
                self.status_message.emit("Install: sudo apt-get install reaver")
                main_logger.warning("'wash' tool not found - WPS detection disabled. Install: sudo apt-get install reaver")
                return

            self.status_message.emit("Starting WPS detection...")
            main_logger.info("Starting WPS detection...")

            # Start wash in a separate thread
            wps_thread = threading.Thread(target=self._wps_scan_thread, daemon=True)
            wps_thread.start()

        except Exception as e:
            self.status_message.emit(f"WPS scan error: {e}")
            main_logger.exception(f"WPS scan error: {e}")

    def _wps_scan_thread(self):
        """Background thread for WPS scanning"""
        try:
            # Run wash to detect WPS
            cmd = ['sudo', 'wash', '-i', self.interface, '--ignore-fcs']
            main_logger.info(f"Starting wash with command: {' '.join(cmd)}")

            self.wps_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )

            # Parse wash output
            for line in iter(self.wps_process.stdout.readline, ''):
                if not self.running:
                    break

                line = line.strip()
                if not line or line.startswith('BSSID') or line.startswith('---'):
                    continue

                # Parse wash output format:
                # BSSID              Ch  dBm  WPS  Lck  Vendor    ESSID
                parts = line.split()
                if len(parts) >= 5:
                    bssid = parts[0].strip()

                    # Validate BSSID format
                    if not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', bssid):
                        continue

                    wps_version = parts[3].strip() if len(parts) > 3 else ""
                    wps_locked = parts[4].strip().lower() == 'yes' if len(parts) > 4 else False

                    # Update AP with WPS info
                    if bssid in self.aps:
                        ap = self.aps[bssid]
                        ap.wps_enabled = True
                        ap.wps_locked = wps_locked
                        ap.wps_version = wps_version

                        # Recalculate attack score with WPS info
                        ap.calculate_attack_score()

                        # Emit update
                        self.ap_updated.emit(ap)
                        self.status_message.emit(f"WPS detected: {ap.ssid or bssid} [{'LOCKED' if wps_locked else 'UNLOCKED'}]")
                        main_logger.info(f"WPS detected for {ap.ssid or bssid}: {'LOCKED' if wps_locked else 'UNLOCKED'}")

                time.sleep(0.1)

        except Exception as e:
            if self.running:
                self.status_message.emit(f"WPS scan thread error: {e}")
                main_logger.exception(f"WPS scan thread error: {e}")

    def is_scan_saturated(self) -> Tuple[bool, str]:
        """
        Detect if scanning has stopped discovering new networks/clients
        Returns: (is_saturated: bool, reason: str)
        """
        if not self.scan_start_time:
            main_logger.debug("Scan not started, not saturated.")
            return (False, "Scan not started")

        current_time = time.time()
        scan_duration = current_time - self.scan_start_time

        # Don't declare saturation before minimum scan time
        if scan_duration < self.min_scan_time:
            main_logger.debug(f"Min scan time not reached ({scan_duration:.0f}s / {self.min_scan_time}s), not saturated.")
            return (False, f"Min scan time not reached ({scan_duration:.0f}s / {self.min_scan_time}s)")

        # Check if we've discovered anything at all
        if not self.last_new_ap_time and not self.last_new_client_time:
            # No discoveries yet - probably just started or environment is empty
            main_logger.debug("No discoveries yet, not saturated.")
            return (False, "No discoveries yet")

        # Check time since last AP discovery
        if self.last_new_ap_time:
            time_since_last_ap = current_time - self.last_new_ap_time
            if time_since_last_ap < self.saturation_threshold:
                main_logger.debug(f"Still discovering APs (last: {time_since_last_ap:.0f}s ago), not saturated.")
                return (False, f"Still discovering APs (last: {time_since_last_ap:.0f}s ago)")

        # Check time since last client discovery
        if self.last_new_client_time:
            time_since_last_client = current_time - self.last_new_client_time
            if time_since_last_client < self.saturation_threshold:
                main_logger.debug(f"Still discovering clients (last: {time_since_last_client:.0f}s ago), not saturated.")
                return (False, f"Still discovering clients (last: {time_since_last_client:.0f}s ago)")

        # Both APs and clients have not been discovered for threshold time
        time_since_last = max(
            current_time - (self.last_new_ap_time or 0),
            current_time - (self.last_new_client_time or 0)
        )
        main_logger.info(f"Scan saturated: No new discoveries in {time_since_last:.0f}s (threshold: {self.saturation_threshold}s).")
        return (True, f"No new discoveries in {time_since_last:.0f}s (threshold: {self.saturation_threshold}s)")

    def get_scan_statistics(self) -> dict:
        """Return detailed scan statistics for UI display"""
        current_time = time.time()
        total_clients = sum(len(ap.clients) for ap in self.aps.values())
        wps_networks = [ap for ap in self.aps.values() if ap.wps_enabled]
        wps_unlocked = [ap for ap in wps_networks if not ap.wps_locked]

        is_saturated, reason = self.is_scan_saturated()

        return {
            'total_aps': len(self.aps),
            'total_clients': total_clients,
            'wps_networks': len(wps_networks),
            'wps_unlocked': len(wps_unlocked),
            'scan_duration': current_time - self.scan_start_time if self.scan_start_time else 0,
            'last_ap_discovery': current_time - self.last_new_ap_time if self.last_new_ap_time else None,
            'last_client_discovery': current_time - self.last_new_client_time if self.last_new_client_time else None,
            'is_saturated': is_saturated,
            'saturation_reason': reason
        }

    def stop(self):
        """Stop scanning"""
        self.running = False
        main_logger.info("WiFi scanner stop requested.")

    def save_extended_csv(self):
        """Save extended CSV with WPS and device info"""
        try:
            if not self.output_prefix:
                main_logger.warning("No output prefix set, cannot save extended CSV.")
                return

            extended_csv = f"{self.output_prefix}-extended.csv"

            with open(extended_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write AP section header
                writer.writerow(['BSSID', 'First Seen', 'Last Seen', 'Channel', 'Speed', 'Privacy', 'Cipher', 'Authentication', 'Power', 'Beacons', 'IV', 'LAN IP', 'ID-length', 'ESSID', 'WPS', 'WPS Locked', 'WPS Version', 'Vendor', 'Device Type'])
                writer.writerow([])  # Blank line

                # Write APs
                for ap in self.aps.values():
                    writer.writerow([
                        ap.bssid,
                        ap.first_seen or '',
                        ap.last_seen or '',
                        ap.channel,
                        ap.speed,
                        ap.encryption,
                        ap.cipher,
                        ap.authentication,
                        ap.power,
                        ap.beacons,
                        ap.iv,
                        ap.lan_ip,
                        ap.id_length,
                        ap.ssid,
                        'Yes' if ap.wps_enabled else 'No',
                        'Yes' if ap.wps_locked else 'No',
                        ap.wps_version,
                        ap.vendor,
                        ap.device_type
                    ])

                # Write separator
                writer.writerow([])
                writer.writerow([])

                # Write clients section header
                writer.writerow(['Station MAC', 'First Seen', 'Last Seen', 'Power', 'Packets', 'BSSID', 'Probed ESSIDs', 'Vendor', 'Device Type'])
                writer.writerow([])

                # Write clients
                for client in self.clients.values():
                    writer.writerow([
                        client.mac,
                        client.first_seen or '',
                        client.last_seen or '',
                        client.power,
                        client.packets,
                        client.bssid,
                        ', '.join(client.probed_essids),
                        client.vendor,
                        client.device_type
                    ])

            self.status_message.emit(f"Saved extended CSV: {extended_csv}")
            main_logger.info(f"Saved extended CSV: {extended_csv}")

        except Exception as e:
            self.error_occurred.emit(f"Error saving extended CSV: {e}")
            main_logger.exception(f"Error saving extended CSV: {e}")

    def cleanup(self):
        """Clean up resources"""
        main_logger.info("Starting WiFi scanner cleanup...")
        # Save extended CSV before cleanup
        self.save_extended_csv()

        # Stop database upsert worker
        if self.scan_db:
            self.scan_db.stop_upsert_worker()
            main_logger.info("Database upsert worker stopped.")

        # Shutdown fingerprint thread pool
        if hasattr(self, 'fingerprint_executor'):
            self.status_message.emit("Waiting for fingerprinting to complete...")
            main_logger.info("Waiting for fingerprinting to complete...")
            self.fingerprint_executor.shutdown(wait=True, cancel_futures=False)
            main_logger.info("Fingerprinting thread pool shutdown complete.")

        if self.process:
            main_logger.info("Terminating airodump-ng process...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                main_logger.info("airodump-ng process terminated.")
            except subprocess.TimeoutExpired:
                main_logger.warning("airodump-ng process did not terminate gracefully, killing...")
                self.process.kill()
                main_logger.info("airodump-ng process killed.")
            except Exception as e:
                main_logger.exception(f"Error terminating airodump-ng process: {e}")

        if self.wps_process:
            main_logger.info("Terminating wash process...")
            try:
                self.wps_process.terminate()
                self.wps_process.wait(timeout=5)
                main_logger.info("wash process terminated.")
            except subprocess.TimeoutExpired:
                main_logger.warning("wash process did not terminate gracefully, killing...")
                self.wps_process.kill()
                main_logger.info("wash process killed.")
            except Exception as e:
                main_logger.exception(f"Error terminating wash process: {e}")

        self.scan_stopped.emit()
        self.status_message.emit("Scan stopped")
        main_logger.info("WiFi scanner cleanup complete. Scan stopped.")

    def get_all_aps(self) -> List[WiFiAccessPoint]:
        """Get all discovered APs"""
        return list(self.aps.values())

    def get_all_clients(self) -> List[WiFiClient]:
        """Get all discovered clients"""
        return list(self.clients.values())

    def is_process_alive(self) -> bool:
        """Check if the airodump-ng process is still running"""
        if self.process is None:
            return False
        # poll() returns None if process is still running, otherwise returns exit code
        return self.process.poll() is None

    def get_process_pid(self) -> Optional[int]:
        """Get the PID of the airodump-ng process"""
        if self.process is None:
            return None
        return self.process.pid if self.is_process_alive() else None

    def _update_ap_in_db(self, ap: WiFiAccessPoint):
        """Update AP in database"""
        try:
            # Parse timestamps
            first_seen = None
            last_seen = None
            if ap.first_seen:
                try:
                    first_seen = datetime.strptime(ap.first_seen, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    main_logger.warning(f"Could not parse first_seen timestamp for AP {ap.bssid}: {ap.first_seen}")
                    pass
            if ap.last_seen:
                try:
                    last_seen = datetime.strptime(ap.last_seen, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    main_logger.warning(f"Could not parse last_seen timestamp for AP {ap.bssid}: {ap.last_seen}")
                    pass

            # Convert power to int
            power = None
            if ap.power and ap.power.strip():
                try:
                    power = int(ap.power.strip())
                except ValueError:
                    main_logger.warning(f"Could not parse power for AP {ap.bssid}: {ap.power}")
                    pass

            # Get current GPS location
            latitude, longitude, altitude, gps_accuracy, gps_source = None, None, None, None, None
            if self.gps_service:
                latitude, longitude, altitude, gps_accuracy, gps_source = self.gps_service.get_location()

            # Prepare network data for database (with GPS for mapping)
            network_data = {
                'bssid': ap.bssid,
                'ssid': ap.ssid if ap.ssid else None,
                'channel': int(ap.channel) if ap.channel and ap.channel.strip().isdigit() else None,
                'encryption': ap.encryption if ap.encryption else None,
                'cipher': ap.cipher if ap.cipher else None,
                'authentication': ap.authentication if ap.authentication else None,
                'power': power,
                'beacon_count': ap.beacons if ap.beacons else 0,
                'iv_count': ap.iv if ap.iv else 0,
                'lan_ip': ap.lan_ip if ap.lan_ip else None,
                'speed': ap.speed if ap.speed else None,
                'vendor': ap.vendor if ap.vendor else None,
                'device_type': ap.device_type if ap.device_type else None,
                'wps_enabled': ap.wps_enabled,
                'wps_locked': ap.wps_locked,
                'wps_version': ap.wps_version if ap.wps_version else None,
                'attack_score': float(ap.attack_score) if ap.attack_score else None,
                'first_seen': first_seen,
                'last_seen': last_seen,
                # GPS/Location data (CRITICAL for wardriving/mapping)
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'gps_accuracy': gps_accuracy,
                'gps_source': gps_source
            }

            self.scan_db.update_network(network_data)

        except Exception as e:
            main_logger.exception(f"Error updating AP in database: {e}")

    def _update_client_in_db(self, client: WiFiClient, bssid: str):
        """Update client in database"""
        try:
            # Parse timestamps
            first_seen = None
            last_seen = None
            if client.first_seen:
                try:
                    first_seen = datetime.strptime(client.first_seen, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    main_logger.warning(f"Could not parse first_seen timestamp for client {client.mac}: {client.first_seen}")
                    pass
            if client.last_seen:
                try:
                    last_seen = datetime.strptime(client.last_seen, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    main_logger.warning(f"Could not parse last_seen timestamp for client {client.mac}: {client.last_seen}")
                    pass

            # Convert power to int
            power = None
            if client.power and client.power.strip():
                try:
                    power = int(client.power.strip())
                except ValueError:
                    main_logger.warning(f"Could not parse power for client {client.mac}: {client.power}")
                    pass

            # Get current GPS location
            latitude, longitude, altitude, gps_accuracy, gps_source = None, None, None, None, None
            if self.gps_service:
                latitude, longitude, altitude, gps_accuracy, gps_source = self.gps_service.get_location()

            # Prepare client data for database (with GPS for mapping)
            client_data = {
                'mac_address': client.mac,
                'bssid': bssid if bssid else None,
                'power': power,
                'packets': client.packets if client.packets else 0,
                'probed_essids': ','.join(client.probed_essids) if hasattr(client, 'probed_essids') and client.probed_essids else None,
                'vendor': client.vendor if hasattr(client, 'vendor') and client.vendor else None,
                'device_type': client.device_type if hasattr(client, 'device_type') and client.device_type else None,
                'first_seen': first_seen,
                'last_seen': last_seen,
                # GPS/Location data (CRITICAL for wardriving/mapping)
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'gps_accuracy': gps_accuracy,
                'gps_source': gps_source
            }

            self.scan_db.update_client(client_data)

        except Exception as e:
            main_logger.exception(f"Error updating client in database: {e}")
