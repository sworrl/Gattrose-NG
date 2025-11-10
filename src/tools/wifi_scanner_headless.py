#!/usr/bin/env python3
"""
Headless WiFi scanner using airodump-ng (no PyQt dependencies)
For use in system services and daemons
"""

import subprocess
import os
import time
import csv
import re
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor


# Import the AP and Client classes from the PyQt scanner (they're just data classes)
from src.tools.wifi_scanner import WiFiAccessPoint, WiFiClient


class WiFiScannerHeadless:
    """Headless WiFi scanner that runs airodump-ng with callbacks instead of signals"""

    def __init__(self, interface: str = "wlan0mon", channel: Optional[str] = None, data_dir: str = None):
        self.interface = interface
        self.channel = channel
        self.data_dir = data_dir or os.path.join(os.getcwd(), "data")
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

        # Main scanner thread
        self.scanner_thread: Optional[threading.Thread] = None

        # Callbacks (set these to get notified of events)
        self.on_ap_discovered: Optional[Callable[[WiFiAccessPoint], None]] = None
        self.on_ap_updated: Optional[Callable[[WiFiAccessPoint], None]] = None
        self.on_client_discovered: Optional[Callable[[WiFiClient, str], None]] = None
        self.on_client_updated: Optional[Callable[[WiFiClient, str], None]] = None
        self.on_status_message: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_scan_started: Optional[Callable[[], None]] = None
        self.on_scan_stopped: Optional[Callable[[], None]] = None

    def start(self):
        """Start the scanner in a background thread"""
        if self.running:
            print("[!] Scanner already running")
            return False

        self.running = True
        self.scanner_thread = threading.Thread(target=self._run, daemon=False)
        self.scanner_thread.start()
        return True

    def stop(self):
        """Stop scanning"""
        self.running = False

    def wait(self):
        """Wait for scanner thread to finish"""
        if self.scanner_thread and self.scanner_thread.is_alive():
            self.scanner_thread.join(timeout=10)

    def _run(self):
        """Main scanner thread"""
        try:
            # Create output directory
            output_dir = Path(self.data_dir) / "captures"
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

            self._status(f"Starting scan on {self.interface}")
            self._status(f"Command: {' '.join(cmd)}")

            # Start airodump-ng
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )

            if self.on_scan_started:
                self.on_scan_started()
            self._status("Scan started - capturing data...")

            # Start WPS scanning in parallel
            self.start_wps_scan()

            # Monitor CSV file for updates
            csv_file = f"{self.output_prefix}-01.csv"

            # Wait for CSV file to be created
            wait_count = 0
            while not os.path.exists(csv_file) and self.running and wait_count < 30:
                time.sleep(0.5)
                wait_count += 1

            if not os.path.exists(csv_file):
                self._error("CSV file not created - check airodump-ng")
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
                    self._error(f"Error reading CSV: {e}")

                time.sleep(1)  # Check every second

        except Exception as e:
            self._error(f"Scanner error: {e}")
        finally:
            self.cleanup()

    def parse_csv(self, csv_file: str):
        """Parse airodump-ng CSV file"""
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Split into AP and Client sections
            sections = content.split('\n\n')

            if len(sections) >= 1:
                self.parse_ap_section(sections[0])

            if len(sections) >= 2:
                self.parse_client_section(sections[1])

        except Exception as e:
            self._error(f"CSV parse error: {e}")

    def _fingerprint_ap_async(self, ap: WiFiAccessPoint):
        """Fingerprint AP in background thread"""
        try:
            ap.calculate_attack_score()
            # Call update callback after fingerprinting completes
            if self.on_ap_updated:
                self.on_ap_updated(ap)
        except Exception as e:
            print(f"[!] Error fingerprinting AP {ap.bssid}: {e}")
        finally:
            # Remove from queue
            self.fingerprint_queue.discard(ap.bssid)

    def _fingerprint_client_async(self, client: WiFiClient):
        """Fingerprint client in background thread"""
        try:
            client.identify_device()
            # Call update callback after fingerprinting completes
            if self.on_client_updated:
                self.on_client_updated(client, client.bssid)
        except Exception as e:
            print(f"[!] Error fingerprinting client {client.mac}: {e}")
        finally:
            # Remove from queue
            self.fingerprint_queue.discard(client.mac)

    def parse_ap_section(self, section: str):
        """Parse Access Points section of CSV"""
        try:
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

                    if self.on_ap_discovered:
                        self.on_ap_discovered(ap)
                    self._status(f"New AP: {ap.ssid or bssid} [{ap.encryption}]")

                    # Queue fingerprinting in background
                    if bssid not in self.fingerprint_queue:
                        self.fingerprint_queue.add(bssid)
                        self.fingerprint_executor.submit(self._fingerprint_ap_async, ap)
                else:
                    ap = self.aps[bssid]
                    ap.update_from_csv_row(row)
                    if self.on_ap_updated:
                        self.on_ap_updated(ap)

        except Exception as e:
            self._error(f"AP parse error: {e}")

    def parse_client_section(self, section: str):
        """Parse Clients section of CSV"""
        try:
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

                    if self.on_client_discovered:
                        self.on_client_discovered(client, bssid)
                    self._status(f"New client: {mac} -> {bssid}")

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

                    if self.on_client_updated:
                        self.on_client_updated(client, bssid)

        except Exception as e:
            self._error(f"Client parse error: {e}")

    def start_wps_scan(self):
        """Start WPS scanning using wash tool"""
        try:
            # Check if wash is available
            wash_check = subprocess.run(['which', 'wash'], capture_output=True)
            if wash_check.returncode != 0:
                self._status("Note: 'wash' tool not found - WPS detection disabled")
                self._status("Install: sudo apt-get install reaver")
                return

            self._status("Starting WPS detection...")

            # Start wash in a separate thread
            wps_thread = threading.Thread(target=self._wps_scan_thread, daemon=True)
            wps_thread.start()

        except Exception as e:
            self._status(f"WPS scan error: {e}")

    def _wps_scan_thread(self):
        """Background thread for WPS scanning"""
        try:
            # Run wash to detect WPS
            cmd = ['sudo', 'wash', '-i', self.interface, '--ignore-fcs']

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

                        # Call update callback
                        if self.on_ap_updated:
                            self.on_ap_updated(ap)
                        self._status(f"WPS detected: {ap.ssid or bssid} [{'LOCKED' if wps_locked else 'UNLOCKED'}]")

                time.sleep(0.1)

        except Exception as e:
            if self.running:
                self._status(f"WPS scan thread error: {e}")

    def save_extended_csv(self):
        """Save extended CSV with WPS and device info"""
        try:
            if not self.output_prefix:
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

            self._status(f"Saved extended CSV: {extended_csv}")

        except Exception as e:
            self._error(f"Error saving extended CSV: {e}")

    def cleanup(self):
        """Clean up resources"""
        # Save extended CSV before cleanup
        self.save_extended_csv()

        # Shutdown fingerprint thread pool
        if hasattr(self, 'fingerprint_executor'):
            self._status("Waiting for fingerprinting to complete...")
            self.fingerprint_executor.shutdown(wait=True, cancel_futures=False)

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass

        if self.wps_process:
            try:
                self.wps_process.terminate()
                self.wps_process.wait(timeout=5)
            except:
                try:
                    self.wps_process.kill()
                except:
                    pass

        if self.on_scan_stopped:
            self.on_scan_stopped()
        self._status("Scan stopped")

    def get_all_aps(self) -> List[WiFiAccessPoint]:
        """Get all discovered APs"""
        return list(self.aps.values())

    def get_all_clients(self) -> List[WiFiClient]:
        """Get all discovered clients"""
        return list(self.clients.values())

    # Helper methods for callbacks
    def _status(self, msg: str):
        """Send status message"""
        if self.on_status_message:
            self.on_status_message(msg)

    def _error(self, msg: str):
        """Send error message"""
        if self.on_error:
            self.on_error(msg)
