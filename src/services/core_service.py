#!/usr/bin/env python3
"""
Gattrose Core Service
Central service that manages all Gattrose operations independently of GUI
"""

import os
import sys
import json
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import signal

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.wifi_scanner import WiFiAccessPoint, WiFiClient
from src.tools.wifi_scanner_headless import WiFiScannerHeadless
from src.services.wireless_card_manager import WirelessCardManager, CardRole, CardState, WirelessCard


class GattroseState:
    """Thread-safe state manager for Gattrose"""

    def __init__(self):
        self._lock = threading.RLock()
        self._state = {
            'running': True,
            'scanner_active': False,
            'monitor_interface': None,
            'physical_interface': None,
            'flipper_connected': False,
            'flipper_port': None,
            'aps': {},  # BSSID -> WiFiAccessPoint
            'clients': {},  # MAC -> WiFiClient
            'attacks_running': [],
            'capture_files': []
        }

    def get(self, key: str, default=None):
        """Thread-safe get"""
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value):
        """Thread-safe set"""
        with self._lock:
            self._state[key] = value

    def get_all(self) -> dict:
        """Get full state snapshot"""
        with self._lock:
            return self._state.copy()

    def update_ap(self, bssid: str, ap: WiFiAccessPoint):
        """Update AP in state"""
        with self._lock:
            self._state['aps'][bssid] = ap

    def update_client(self, mac: str, client: WiFiClient):
        """Update client in state"""
        with self._lock:
            self._state['clients'][mac] = client

    def get_aps(self) -> Dict[str, WiFiAccessPoint]:
        """Get all APs"""
        with self._lock:
            return self._state['aps'].copy()

    def get_clients(self) -> Dict[str, WiFiClient]:
        """Get all clients"""
        with self._lock:
            return self._state['clients'].copy()


class GattroseCoreService:
    """
    Core Gattrose service that runs independently
    Manages scanner, attacks, flipper integration, etc.
    """

    def __init__(self, data_dir: str = None, auto_scan: bool = True):
        self.data_dir = data_dir or os.path.join(PROJECT_ROOT, 'data')
        self.db_path = os.path.join(self.data_dir, 'gattrose.db')
        self.auto_scan = auto_scan

        # State manager
        self.state = GattroseState()

        # Wireless card manager
        self.card_manager = WirelessCardManager()
        self.card_manager.on_card_added = self._on_card_added
        self.card_manager.on_card_removed = self._on_card_removed
        self.card_manager.on_card_role_changed = self._on_card_role_changed

        # Multiple scanners (one per scanner card)
        self.scanners: Dict[str, WiFiScannerHeadless] = {}  # interface -> scanner

        # Attack management
        self.attack_running = False
        self.attack_interface: Optional[str] = None

        # Flipper service
        self.flipper_service = None

        # Database connection
        self.db_conn: Optional[sqlite3.Connection] = None

        # System tray notification callbacks
        self.on_system_tray_notify: Optional[Callable[[str, str], None]] = None

        # Database
        self._init_database()

        # Signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        print("[*] Gattrose Core Service initialized")
        print(f"[*] Auto-scan on boot: {auto_scan}")
        print(f"[*] Database: {self.db_path}")

    def _init_database(self):
        """Initialize database"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, 'captures'), exist_ok=True)

        # Connect to database
        self.db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.db_conn.cursor()

        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_points (
                bssid TEXT PRIMARY KEY,
                ssid TEXT,
                channel INTEGER,
                encryption TEXT,
                power INTEGER,
                vendor TEXT,
                wps_enabled BOOLEAN,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                packets INTEGER,
                attack_score REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                mac TEXT PRIMARY KEY,
                bssid TEXT,
                vendor TEXT,
                device_type TEXT,
                power INTEGER,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                packets INTEGER,
                probed_essids TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                interface TEXT,
                aps_discovered INTEGER,
                clients_discovered INTEGER
            )
        ''')

        self.db_conn.commit()
        print("[+] Database initialized")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n[*] Received signal {signum}, shutting down gracefully...")
        self.shutdown()
        sys.exit(0)

    # ========== Wireless Card Management ==========

    def _on_card_added(self, card: WirelessCard):
        """Handle wireless card added event"""
        print(f"[+] Wireless card added: {card.interface} ({card.chipset})")

        # Send system tray notification
        if self.on_system_tray_notify:
            self.on_system_tray_notify(
                "Wireless Card Detected",
                f"New card detected: {card.interface}\nClick to configure card roles"
            )

        # Auto-assign roles
        self.card_manager.auto_assign_roles()

    def _on_card_removed(self, interface: str):
        """Handle wireless card removed event"""
        print(f"[-] Wireless card removed: {interface}")

        # Stop scanner if running on this card
        if interface in self.scanners:
            self.stop_scanner(interface)

        # Send system tray notification
        if self.on_system_tray_notify:
            self.on_system_tray_notify(
                "Wireless Card Removed",
                f"Card {interface} was removed"
            )

        # Re-assign roles
        self.card_manager.auto_assign_roles()

    def _on_card_role_changed(self, card: WirelessCard):
        """Handle card role changed event"""
        print(f"[*] Card role changed: {card.interface} -> {card.role.value}")

        # If card is now a scanner, start scanning
        if card.role in [CardRole.SCANNER, CardRole.BOTH]:
            # Enable monitor mode and start scanner
            success, monitor_iface = self.card_manager.enable_monitor_mode(card.interface)
            if success and monitor_iface:
                self.start_scanner_on_interface(monitor_iface, card.interface)

        # If card is now attacker only, stop scanning
        elif card.role == CardRole.ATTACKER:
            if card.interface in self.scanners:
                self.stop_scanner(card.interface)

    # ========== Scanner Management ==========

    def start_scanner_on_interface(self, interface: str, physical_interface: str = None) -> bool:
        """Start scanner on specific interface"""
        try:
            if interface in self.scanners and self.scanners[interface].running:
                print(f"[!] Scanner already running on {interface}")
                return False

            print(f"[*] Starting scanner on {interface}")

            # Create scanner
            scanner = WiFiScannerHeadless(interface=interface, channel=None, data_dir=self.data_dir)

            # Set callbacks
            scanner.on_ap_discovered = self._on_ap_discovered
            scanner.on_client_discovered = self._on_client_discovered
            scanner.on_ap_updated = self._on_ap_updated
            scanner.on_client_updated = self._on_client_updated

            # Start scanner
            scanner.start()

            self.scanners[interface] = scanner
            self.state.set('scanner_active', True)

            print(f"[+] Scanner started on {interface}")
            return True

        except Exception as e:
            print(f"[!] Failed to start scanner on {interface}: {e}")
            return False

    def stop_scanner(self, interface: str) -> bool:
        """Stop scanner on specific interface"""
        try:
            if interface not in self.scanners:
                print(f"[!] No scanner running on {interface}")
                return False

            scanner = self.scanners[interface]
            if not scanner.running:
                print(f"[!] Scanner not running on {interface}")
                return False

            print(f"[*] Stopping scanner on {interface}...")
            scanner.stop()
            scanner.wait()

            del self.scanners[interface]

            # Update state if no scanners running
            if len(self.scanners) == 0:
                self.state.set('scanner_active', False)

            print(f"[+] Scanner stopped on {interface}")
            return True

        except Exception as e:
            print(f"[!] Failed to stop scanner on {interface}: {e}")
            return False

    def stop_all_scanners(self) -> bool:
        """Stop all running scanners"""
        interfaces = list(self.scanners.keys())
        for interface in interfaces:
            self.stop_scanner(interface)
        return True

    def start_attack(self, interface: str = None) -> bool:
        """
        Start attack mode
        - If single card: stop scanning, use card for attack
        - If multi-card: use attacker card, keep scanning on scanner cards
        """
        try:
            # Get attacker cards
            attacker_cards = self.card_manager.get_attacker_cards()

            if not attacker_cards:
                print("[!] No attacker cards available")
                return False

            # If interface not specified, use first attacker card
            if not interface:
                card = attacker_cards[0]
                interface = card.monitor_interface or card.interface

            # Check if this is a BOTH role card (single card mode)
            card = self.card_manager.get_card(interface)
            if card and card.role == CardRole.BOTH:
                # Stop scanning on this card
                print(f"[*] Single card mode: Stopping scanner on {interface} for attack")
                self.stop_scanner(interface)

            self.attack_running = True
            self.attack_interface = interface

            print(f"[+] Attack mode started on {interface}")
            return True

        except Exception as e:
            print(f"[!] Failed to start attack: {e}")
            return False

    def stop_attack(self) -> bool:
        """
        Stop attack mode
        - If single card: restart scanning
        """
        try:
            if not self.attack_running:
                return False

            interface = self.attack_interface
            card = self.card_manager.get_card(interface) if interface else None

            # If BOTH role card, restart scanning
            if card and card.role == CardRole.BOTH:
                print(f"[*] Single card mode: Restarting scanner on {interface}")
                monitor_iface = card.monitor_interface or interface
                self.start_scanner_on_interface(monitor_iface, card.interface)

            self.attack_running = False
            self.attack_interface = None

            print("[+] Attack mode stopped")
            return True

        except Exception as e:
            print(f"[!] Failed to stop attack: {e}")
            return False

    # ========== Legacy Scanner Management (for compatibility) ==========

    def start_scanner(self, interface: str, channel: Optional[str] = None) -> bool:
        """Legacy start scanner method - redirects to new multi-card method"""
        return self.start_scanner_on_interface(interface, interface)

    def _on_ap_discovered(self, ap: WiFiAccessPoint):
        """Handle AP discovered"""
        self.state.update_ap(ap.bssid, ap)
        print(f"[+] AP discovered: {ap.ssid or '(Hidden)'} [{ap.bssid}]")
        # Log to database
        self._save_ap_to_db(ap)

    def _on_client_discovered(self, client: WiFiClient, bssid: str):
        """Handle client discovered"""
        self.state.update_client(client.mac, client)
        if bssid and bssid != "(not associated)":
            print(f"[+] Client discovered: {client.mac} -> {bssid}")
        else:
            print(f"[+] Unassociated client: {client.mac}")
        # Log to database
        self._save_client_to_db(client, bssid)

    def _on_ap_updated(self, ap: WiFiAccessPoint):
        """Handle AP updated"""
        self.state.update_ap(ap.bssid, ap)
        # Update database
        self._save_ap_to_db(ap)

    def _on_client_updated(self, client: WiFiClient):
        """Handle client updated"""
        self.state.update_client(client.mac, client)
        # Update database
        bssid = getattr(client, 'bssid', None) or "(not associated)"
        self._save_client_to_db(client, bssid)

    def _save_ap_to_db(self, ap: WiFiAccessPoint):
        """Save AP to database"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO access_points
                (bssid, ssid, channel, encryption, power, vendor, wps_enabled,
                 first_seen, last_seen, packets, attack_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ap.bssid,
                ap.ssid,
                ap.channel,
                ap.encryption,
                int(ap.power) if ap.power else None,
                ap.vendor,
                ap.wps_enabled,
                ap.first_seen,
                ap.last_seen,
                ap.beacons,  # Fixed: APs have beacons, not packets
                ap.attack_score
            ))
            self.db_conn.commit()
        except Exception as e:
            print(f"[!] Database error (AP): {e}")

    def _save_client_to_db(self, client: WiFiClient, bssid: str):
        """Save client to database"""
        try:
            cursor = self.db_conn.cursor()
            probed = ','.join(client.probed_essids) if client.probed_essids else ''
            cursor.execute('''
                INSERT OR REPLACE INTO clients
                (mac, bssid, vendor, device_type, power, first_seen, last_seen,
                 packets, probed_essids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                client.mac,
                bssid,
                client.vendor,
                client.device_type,
                int(client.power) if client.power else None,
                client.first_seen,
                client.last_seen,
                client.packets,
                probed
            ))
            self.db_conn.commit()
        except Exception as e:
            print(f"[!] Database error (Client): {e}")

    # ========== Flipper Integration ==========

    def connect_flipper(self, port: Optional[str] = None) -> bool:
        """Connect to Flipper Zero"""
        try:
            from src.services.flipper_service_headless import FlipperZeroServiceHeadless

            if not self.flipper_service:
                self.flipper_service = FlipperZeroServiceHeadless()

            success = self.flipper_service.connect(port)
            if success:
                self.state.set('flipper_connected', True)
                self.state.set('flipper_port', self.flipper_service.device.port if self.flipper_service.device else None)
                print(f"[+] Connected to Flipper Zero")

                # Start rainbow LED cycling to indicate Gattrose control
                self.flipper_service.led_rainbow_cycle(speed=0.05, brightness=128)
                print(f"[+] Rainbow LED indicator started")
            else:
                print("[!] Failed to connect to Flipper Zero")

            return success

        except Exception as e:
            print(f"[!] Flipper connection error: {e}")
            return False

    def disconnect_flipper(self) -> bool:
        """Disconnect from Flipper Zero"""
        try:
            if self.flipper_service:
                # Stop rainbow cycling
                self.flipper_service.led_rainbow_stop()
                # Disconnect
                self.flipper_service.disconnect()
                self.state.set('flipper_connected', False)
                self.state.set('flipper_port', None)
                print("[+] Disconnected from Flipper Zero")
                return True
            return False
        except Exception as e:
            print(f"[!] Flipper disconnection error: {e}")
            return False

    def get_flipper_info(self) -> Optional[dict]:
        """Get Flipper device info"""
        if self.flipper_service and self.flipper_service.device:
            device = self.flipper_service.device
            return {
                'name': device.name,
                'model': device.hardware_model,
                'uid': device.hardware_uid,
                'firmware': f"{device.firmware_origin} {device.firmware_version}",
                'port': device.port,
                'ble_mac': device.ble_mac
            }
        return None

    # ========== Monitor Mode ==========

    def enable_monitor_mode(self, interface: str) -> tuple[bool, Optional[str]]:
        """
        Enable monitor mode on interface
        Returns (success, monitor_interface_name)
        """
        try:
            import subprocess

            print(f"[*] Enabling monitor mode on {interface}")

            # Kill interfering processes (but preserve NetworkManager)
            # Only kill wpa_supplicant and dhclient which actually interfere
            try:
                subprocess.run(['sudo', 'pkill', '-9', 'wpa_supplicant'],
                              capture_output=True, timeout=5)
                subprocess.run(['sudo', 'pkill', '-9', 'dhclient'],
                              capture_output=True, timeout=5)
            except Exception:
                pass  # Not critical if these don't exist

            # Enable monitor mode
            result = subprocess.run(['sudo', 'airmon-ng', 'start', interface],
                                   capture_output=True, text=True, timeout=10)

            # Parse output to find monitor interface name
            monitor_iface = None
            for line in result.stdout.split('\n'):
                if 'monitor mode' in line.lower() and 'enabled' in line.lower():
                    # Extract interface name
                    parts = line.split()
                    for part in parts:
                        if 'mon' in part.lower() or interface in part:
                            monitor_iface = part
                            break

            if not monitor_iface:
                # Try default naming
                monitor_iface = f"{interface}mon"

            self.state.set('physical_interface', interface)
            self.state.set('monitor_interface', monitor_iface)

            print(f"[+] Monitor mode enabled: {monitor_iface}")
            return True, monitor_iface

        except Exception as e:
            print(f"[!] Failed to enable monitor mode: {e}")
            return False, None

    def disable_monitor_mode(self, interface: str) -> bool:
        """Disable monitor mode"""
        try:
            import subprocess

            print(f"[*] Disabling monitor mode on {interface}")

            subprocess.run(['sudo', 'airmon-ng', 'stop', interface],
                          capture_output=True, timeout=10)

            self.state.set('monitor_interface', None)

            print(f"[+] Monitor mode disabled")
            return True

        except Exception as e:
            print(f"[!] Failed to disable monitor mode: {e}")
            return False

    # ========== Data Export ==========

    def export_networks_json(self) -> dict:
        """Export networks as JSON"""
        aps = self.state.get_aps()
        return {
            'success': True,
            'count': len(aps),
            'data': [ap.to_dict() for ap in aps.values()]
        }

    def export_clients_json(self) -> dict:
        """Export clients as JSON"""
        clients = self.state.get_clients()
        return {
            'success': True,
            'count': len(clients),
            'data': [client.to_dict() for client in clients.values()]
        }

    # ========== Lifecycle ==========

    def run(self):
        """Run service (blocking)"""
        print("[*] Gattrose Core Service running...")
        print("[*] Press Ctrl+C to stop")

        # Detect wireless cards
        print("[*] Detecting wireless cards...")
        cards = self.card_manager.detect_cards()
        print(f"[+] Detected {len(cards)} wireless card(s)")

        for card in cards:
            print(f"    - {card.interface}: {card.driver} ({card.chipset})")

        # Auto-assign roles based on card count
        if len(cards) > 0:
            self.card_manager.auto_assign_roles()

        # Start hotplug monitoring
        print("[*] Starting card hotplug monitoring...")
        self.card_manager.start_monitoring_hotplug()

        # Auto-start scanning if enabled
        if self.auto_scan and len(cards) > 0:
            print("[*] Auto-scan enabled, starting scanners on all scanner cards...")

            # Get scanner cards
            scanner_cards = self.card_manager.get_scanner_cards()

            for card in scanner_cards:
                try:
                    # Enable monitor mode
                    success, monitor_iface = self.card_manager.enable_monitor_mode(card.interface)
                    if success and monitor_iface:
                        # Start scanning
                        self.start_scanner_on_interface(monitor_iface, card.interface)
                        print(f"[+] 24/7 scanning started on {monitor_iface}")
                    else:
                        print(f"[!] Failed to enable monitor mode on {card.interface}")
                except Exception as e:
                    print(f"[!] Failed to start scanner on {card.interface}: {e}")

        try:
            while self.state.get('running'):
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Keyboard interrupt received")
            self.shutdown()

    def shutdown(self):
        """Shutdown service"""
        print("[*] Shutting down Gattrose Core Service...")

        self.state.set('running', False)

        # Stop all scanners
        print("[*] Stopping all scanners...")
        self.stop_all_scanners()

        # Stop card hotplug monitoring
        print("[*] Stopping card hotplug monitoring...")
        self.card_manager.stop_monitoring_hotplug()

        # Disconnect Flipper
        if self.flipper_service:
            self.disconnect_flipper()

        # Close database
        if self.db_conn:
            self.db_conn.close()

        print("[+] Gattrose Core Service stopped")


# Singleton instance
_service_instance: Optional[GattroseCoreService] = None

def get_service() -> GattroseCoreService:
    """Get singleton service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = GattroseCoreService()
    return _service_instance


if __name__ == '__main__':
    # Run as standalone service
    service = GattroseCoreService()
    service.run()
