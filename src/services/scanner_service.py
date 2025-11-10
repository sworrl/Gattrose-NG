#!/usr/bin/env python3
"""
Gattrose-NG Scanner Service Daemon

24/7 headless WiFi scanning service
- Continuously scans for networks and clients
- Stores data in live_scans database table
- Archives previous scans when starting new
- Tracks location if available
- Auto-restarts on failure
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import get_session, ScanSession, Network, Client
from src.services.database_service import get_database_service
from src.tools.wifi_monitor import WiFiMonitorManager, find_command
from src.utils.location import GPSManager, GeoIPManager
from src.version import VERSION


class ScannerServiceDaemon:
    """24/7 WiFi scanner daemon"""

    def __init__(self):
        self.running = False
        self.scan_session = None
        self.monitor_interface = None
        self.airodump_process = None
        self.wps_process = None
        self.csv_path = None
        self.gps_manager = None
        self.current_location = None
        self.db_service = get_database_service()  # Get database service instance
        self.wps_data = {}  # BSSID -> {version, locked}
        self.setup_signal_handlers()

        print(f"[*] Gattrose-NG Scanner Service v{VERSION}")
        print(f"[*] PID: {os.getpid()}")
        print(f"[+] Database service initialized")

    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n[*] Received signal {signum}, shutting down gracefully...")
        self.shutdown()
        sys.exit(0)

    def archive_previous_live_scans(self):
        """Archive any existing live scans"""
        session = get_session()
        try:
            # Find all live scans
            live_scans = session.query(ScanSession).filter_by(status='live').all()

            for scan in live_scans:
                print(f"[*] Archiving previous live scan: {scan.serial}")
                scan.status = 'archived'
                scan.end_time = datetime.utcnow()

                # Set end location if we have current location
                if self.current_location:
                    scan.end_latitude = self.current_location.get('lat')
                    scan.end_longitude = self.current_location.get('lon')
                    scan.end_altitude = self.current_location.get('alt')

            session.commit()
            print(f"[✓] Archived {len(live_scans)} previous scan(s)")

        except Exception as e:
            print(f"[!] Error archiving scans: {e}")
            session.rollback()
        finally:
            session.close()

    def create_scan_session(self) -> Optional[ScanSession]:
        """Create new live scan session"""
        session = get_session()
        try:
            # Archive previous scans
            self.archive_previous_live_scans()

            # Create new scan session
            scan = ScanSession(
                name=f"Live Scan {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
                status='live',
                interface=self.monitor_interface,
                scan_type='monitor'
            )

            # Set start location
            if self.current_location:
                scan.start_latitude = self.current_location.get('lat')
                scan.start_longitude = self.current_location.get('lon')
                scan.start_altitude = self.current_location.get('alt')

            session.add(scan)
            session.commit()
            session.refresh(scan)

            print(f"[✓] Created scan session: {scan.serial}")
            return scan

        except Exception as e:
            print(f"[!] Error creating scan session: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def setup_monitor_mode(self) -> bool:
        """Setup wireless interface in monitor mode"""
        print("[*] Setting up monitor mode...")

        manager = WiFiMonitorManager()

        # Detect wireless interfaces
        interfaces = manager.get_wireless_interfaces()
        if not interfaces:
            print("[!] No wireless interfaces found")
            return False

        print(f"[*] Found wireless interfaces: {', '.join(interfaces)}")

        # Use first interface
        interface = interfaces[0]

        # Enable monitor mode
        success, monitor_iface, message = manager.enable_monitor_mode(interface)

        if success:
            self.monitor_interface = monitor_iface
            print(f"[✓] Monitor mode enabled: {monitor_iface}")
            return True
        else:
            print(f"[!] Failed to enable monitor mode: {message}")
            return False

    def start_location_tracking(self):
        """Start GPS location tracking if available"""
        try:
            # Try GPS first
            self.gps_manager = GPSManager()
            self.gps_manager.location_updated.connect(self.on_location_updated)
            self.gps_manager.start()
            print("[✓] GPS tracking started")
            return True

        except Exception as e:
            print(f"[!] GPS not available: {e}")

            # Fallback to GeoIP
            try:
                geoip = GeoIPManager()
                location = geoip.get_location()

                if location:
                    self.current_location = location
                    print(f"[✓] GeoIP location: {location['lat']}, {location['lon']}")
                    return True

            except Exception as e:
                print(f"[!] GeoIP also failed: {e}")

        return False

    def on_location_updated(self, lat: float, lon: float, alt: float, accuracy: float):
        """Handle GPS location update"""
        self.current_location = {
            'lat': lat,
            'lon': lon,
            'alt': alt,
            'accuracy': accuracy,
            'source': 'gps'
        }

    def start_airodump(self) -> bool:
        """Start airodump-ng process with PolicyKit authentication"""
        if not self.monitor_interface:
            print("[!] No monitor interface available")
            return False

        # Create captures directory
        captures_dir = PROJECT_ROOT / "data" / "captures" / "service"
        captures_dir.mkdir(parents=True, exist_ok=True)

        # Generate CSV filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        csv_base = captures_dir / f"scanner_service_{timestamp}"
        self.csv_path = f"{csv_base}-01.csv"

        # Find airodump-ng path
        airodump_path = find_command("airodump-ng")
        if not airodump_path:
            print("[!] airodump-ng not found in PATH")
            return False

        # Build airodump command with sudo (requires sudoers entry)
        cmd = [
            "sudo",
            airodump_path,
            "--output-format", "csv",
            "--write", str(csv_base),
            "--write-interval", "3",  # Write every 3 seconds
            self.monitor_interface
        ]

        print(f"[*] Starting airodump-ng on {self.monitor_interface}")
        print(f"[*] Output: {self.csv_path}")
        print(f"[*] Using sudo with NOPASSWD sudoers entry")

        try:
            self.airodump_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait a moment and check if process started successfully
            time.sleep(1)
            if self.airodump_process.poll() is not None:
                print(f"[!] Airodump-ng failed to start (exit code: {self.airodump_process.returncode})")
                return False

            print(f"[✓] Airodump-ng started (PID: {self.airodump_process.pid})")
            return True

        except Exception as e:
            print(f"[!] Failed to start airodump-ng: {e}")
            return False

    def start_wps_scan(self):
        """Start wash WPS scanning in parallel"""
        try:
            import threading
            import re

            # Check if wash is available
            wash_check = subprocess.run(['which', 'wash'], capture_output=True)
            if wash_check.returncode != 0:
                print("[!] 'wash' tool not found - WPS detection disabled")
                print("[!] Install: sudo apt-get install reaver")
                return

            print("[*] Starting WPS detection with wash...")

            # Start wash in a separate thread
            wps_thread = threading.Thread(target=self._wps_scan_thread, daemon=True)
            wps_thread.start()

        except Exception as e:
            print(f"[!] WPS scan error: {e}")

    def _wps_scan_thread(self):
        """Background thread for WPS scanning"""
        import re

        try:
            # Run wash to detect WPS
            cmd = ['sudo', 'wash', '-i', self.monitor_interface, '--ignore-fcs']

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

                    # Store WPS info
                    self.wps_data[bssid.upper()] = {
                        'version': wps_version,
                        'locked': wps_locked
                    }

                    print(f"[+] WPS detected: {bssid} [{'LOCKED' if wps_locked else 'UNLOCKED'}]")

                time.sleep(0.1)

        except Exception as e:
            if self.running:
                print(f"[!] WPS scan thread error: {e}")

    def process_csv_data(self):
        """Process CSV data and update database"""
        if not self.csv_path or not Path(self.csv_path).exists():
            return

        try:
            with open(self.csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Split into AP and Client sections
            if '\n\n' in content:
                sections = content.split('\n\n')
            elif '\r\n\r\n' in content:
                sections = content.split('\r\n\r\n')
            else:
                return

            # Process APs
            if len(sections) >= 1:
                self.process_ap_section(sections[0])

            # Process Clients
            if len(sections) >= 2:
                self.process_client_section(sections[1])

        except Exception as e:
            print(f"[!] Error processing CSV: {e}")

    def process_ap_section(self, section: str):
        """Process Access Point section from CSV"""
        import csv
        import re

        try:
            if '\r\n' in section:
                lines = section.strip().split('\r\n')
            else:
                lines = section.strip().split('\n')

            if len(lines) < 2:
                return

            # Parse APs (skip first 2 header lines)
            session = get_session()
            count = 0

            for line in lines[2:]:
                if not line.strip():
                    continue

                row = list(csv.reader([line]))[0] if line else []
                if len(row) < 14:
                    continue

                bssid = row[0].strip()
                if not bssid or not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', bssid):
                    continue

                # Upsert network
                network = session.query(Network).filter_by(bssid=bssid).first()

                if not network:
                    # Create new
                    from src.utils.serial import generate_serial
                    network = Network(
                        serial=generate_serial("ap"),
                        bssid=bssid
                    )
                    session.add(network)

                # Update from CSV data
                network.ssid = row[13].strip() if len(row) > 13 and row[13].strip() else network.ssid
                network.channel = int(row[3].strip()) if row[3].strip().isdigit() else network.channel
                network.encryption = row[5].strip() if len(row) > 5 else network.encryption
                network.current_signal = int(row[8].strip()) if row[8].strip().lstrip('-').isdigit() else network.current_signal
                network.beacon_count = int(row[9].strip()) if row[9].strip().isdigit() else network.beacon_count
                network.last_seen = datetime.utcnow()

                # Update location if available
                if self.current_location:
                    network.latitude = self.current_location.get('lat')
                    network.longitude = self.current_location.get('lon')
                    network.altitude = self.current_location.get('alt')

                # Update WPS info if available
                bssid_upper = bssid.upper()
                if bssid_upper in self.wps_data:
                    network.wps_enabled = True
                    network.wps_version = self.wps_data[bssid_upper]['version']
                    network.wps_locked = self.wps_data[bssid_upper]['locked']

                count += 1

            session.commit()

            # Update scan session counts
            if self.scan_session:
                scan = session.query(ScanSession).filter_by(id=self.scan_session.id).first()
                if scan:
                    scan.networks_found = count
                    session.commit()

            session.close()

        except Exception as e:
            print(f"[!] Error processing APs: {e}")

    def process_client_section(self, section: str):
        """Process Client section from CSV"""
        import csv
        import re

        try:
            if '\r\n' in section:
                lines = section.strip().split('\r\n')
            else:
                lines = section.strip().split('\n')

            if len(lines) < 2:
                return

            # Parse clients (skip first 2 header lines)
            session = get_session()
            count = 0

            for line in lines[2:]:
                if not line.strip():
                    continue

                row = list(csv.reader([line]))[0] if line else []
                if len(row) < 6:
                    continue

                mac = row[0].strip()
                if not mac or not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', mac):
                    continue

                # Upsert client
                client = session.query(Client).filter_by(mac_address=mac).first()

                if not client:
                    # Create new
                    from src.utils.serial import generate_serial
                    client = Client(
                        serial=generate_serial("cl"),
                        mac_address=mac
                    )
                    session.add(client)

                # Update from CSV data
                client.current_signal = int(row[3].strip()) if row[3].strip().lstrip('-').isdigit() else client.current_signal
                client.last_seen = datetime.utcnow()

                # Track associated network BSSID
                if len(row) > 5 and row[5].strip():
                    import json
                    bssid = row[5].strip()
                    try:
                        associated = json.loads(client.associated_networks) if client.associated_networks else []
                    except:
                        associated = []
                    if bssid not in associated:
                        associated.append(bssid)
                        client.associated_networks = json.dumps(associated)

                count += 1

            session.commit()

            # Update scan session counts
            if self.scan_session:
                scan = session.query(ScanSession).filter_by(id=self.scan_session.id).first()
                if scan:
                    scan.clients_found = count
                    session.commit()

            session.close()

        except Exception as e:
            print(f"[!] Error processing clients: {e}")

    def run(self):
        """Main service loop"""
        print("[*] Starting Scanner Service...")

        # Setup monitor mode
        if not self.setup_monitor_mode():
            print("[!] Failed to setup monitor mode")
            return 1

        # Start location tracking
        self.start_location_tracking()

        # Create scan session
        self.scan_session = self.create_scan_session()
        if not self.scan_session:
            print("[!] Failed to create scan session")
            return 1

        # Start airodump
        if not self.start_airodump():
            print("[!] Failed to start airodump")
            return 1

        # Start WPS detection
        self.start_wps_scan()

        # Main loop
        self.running = True
        print("[✓] Scanner service running")
        print("[*] Processing CSV data every 5 seconds...")

        try:
            while self.running:
                # Process CSV data
                self.process_csv_data()

                # Sleep
                time.sleep(5)

        except KeyboardInterrupt:
            print("\n[*] Interrupted by user")
        except Exception as e:
            print(f"\n[!] Error in main loop: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.shutdown()

        return 0

    def shutdown(self):
        """Cleanup and shutdown"""
        print("[*] Shutting down scanner service...")

        self.running = False

        # Stop airodump
        if self.airodump_process:
            try:
                print("[*] Stopping airodump-ng...")
                self.airodump_process.terminate()
                self.airodump_process.wait(timeout=5)
                print("[✓] Airodump-ng stopped")
            except Exception as e:
                print(f"[!] Error stopping airodump: {e}")
                try:
                    self.airodump_process.kill()
                except:
                    pass

        # Stop WPS scanning
        if self.wps_process:
            try:
                print("[*] Stopping wash...")
                self.wps_process.terminate()
                self.wps_process.wait(timeout=5)
                print("[✓] Wash stopped")
            except Exception as e:
                print(f"[!] Error stopping wash: {e}")
                try:
                    self.wps_process.kill()
                except:
                    pass

        # Stop GPS
        if self.gps_manager:
            try:
                self.gps_manager.stop()
                print("[✓] GPS tracking stopped")
            except:
                pass

        # Archive scan session
        if self.scan_session:
            try:
                session = get_session()
                scan = session.query(ScanSession).filter_by(id=self.scan_session.id).first()
                if scan:
                    scan.status = 'archived'
                    scan.end_time = datetime.utcnow()
                    scan.csv_path = str(self.csv_path) if self.csv_path else None

                    # Set end location
                    if self.current_location:
                        scan.end_latitude = self.current_location.get('lat')
                        scan.end_longitude = self.current_location.get('lon')
                        scan.end_altitude = self.current_location.get('alt')

                    session.commit()
                    print(f"[✓] Scan session archived: {scan.serial}")
                session.close()
            except Exception as e:
                print(f"[!] Error archiving scan: {e}")

        # Disable monitor mode
        if self.monitor_interface:
            try:
                print("[*] Disabling monitor mode...")
                manager = WiFiMonitorManager()
                manager.disable_monitor_mode(self.monitor_interface)
                print("[✓] Monitor mode disabled")
            except Exception as e:
                print(f"[!] Error disabling monitor mode: {e}")

        print("[✓] Scanner service shutdown complete")


def main():
    """Entry point"""
    daemon = ScannerServiceDaemon()
    sys.exit(daemon.run())


if __name__ == "__main__":
    main()
