#!/usr/bin/env python3
"""
Gattrose Phone Manager Tray Icon
Monitors phone GPS connection and provides phone management controls
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import QTimer, Qt

PROJECT_ROOT = Path('/opt/gattrose-ng')
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

# Import IMSI catcher detection
from security.imsi_catcher_detection import get_detector, CellTowerInfo, IMSICatcherAlert


class PhoneTrayApp:
    """Phone/GPS manager system tray application"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Prevent multiple instances
        self._check_single_instance()

        self.tray_icon = None
        self.menu = None

        # GPS/Phone status
        self.gps_fix = False
        self.gps_accuracy = 0
        self.phone_connected = False
        self.phone_model = "Unknown"
        self.gps_lat = 0.0
        self.gps_lon = 0.0
        self.device_id = None  # Selected ADB device ID (Android) or UDID (iPhone)
        self.device_type = None  # 'android' or 'iphone'

        # Phone hardware stats
        self.cpu_freq = {}  # {core: freq_mhz}
        self.cpu_temp = 0.0
        self.ram_used_mb = 0
        self.ram_total_mb = 0
        self.storage_used_gb = 0.0
        self.storage_total_gb = 0.0
        self.cell_signal = 0  # dBm
        self.cell_type = "Unknown"
        self.wifi_ssid = None
        self.wifi_signal = 0  # dBm
        self.soc_model = "Unknown"
        self.board_name = "Unknown"

        # Additional metrics
        self.uptime_seconds = 0
        self.cpu_load_avg = []  # [1min, 5min, 15min]
        self.screen_on = False
        self.battery_temp = 0.0
        self.network_rx_mb = 0.0  # Total received (MB)
        self.network_tx_mb = 0.0  # Total transmitted (MB)

        # Cellular security monitoring
        self.cell_tower_id = None
        self.cell_pci = None  # Physical Cell ID
        self.cell_mcc = None  # Mobile Country Code
        self.cell_mnc = None  # Mobile Network Code
        self.cell_network_type = "Unknown"  # LTE, 3G, 2G, etc
        self.cell_signal_strength = 0
        self.last_cell_tower_id = None
        self.tower_change_count = 0
        self.last_tower_change_time = None
        self.imsi_alerts = []  # List of security alerts

        # Performance optimization
        self.update_cycle_count = 0  # Counter for rate-limiting expensive operations

        # Load security settings
        from config.security_settings import get_security_settings
        self.security_settings = get_security_settings()

        # Initialize IMSI catcher detector
        self.imsi_detector = get_detector()
        print("[+] IMSI catcher detector initialized with Rayhunter heuristics")

        self._init_tray_icon()
        self._init_menu()
        self._start_status_monitoring()

    def _check_single_instance(self):
        """Ensure only one instance is running"""
        import fcntl
        self.lock_file = open('/tmp/gattrose-phone-tray.lock', 'w')
        try:
            fcntl.lockf(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            print("[!] Phone tray is already running")
            sys.exit(0)

    def _init_tray_icon(self):
        """Initialize system tray icon"""
        icon = self._create_phone_icon("gray")
        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip("Phone GPS - Checking...")
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _create_phone_icon(self, status: str) -> QIcon:
        """Create a phone icon with status color

        Args:
            status: "green" (GPS fix), "yellow" (phone connected, no fix),
                   "red" (no phone), "gray" (unknown)
        """
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Color based on status
        colors = {
            "green": QColor(0, 220, 0),
            "yellow": QColor(255, 200, 0),
            "red": QColor(255, 60, 60),
            "gray": QColor(140, 140, 140)
        }
        color = colors.get(status, colors["gray"])

        # Draw phone body with outline
        painter.setBrush(color)
        painter.setPen(QColor(255, 255, 255, 180))  # White semi-transparent outline
        painter.drawRoundedRect(18, 8, 28, 48, 4, 4)

        # Screen (lighter for visibility)
        painter.setBrush(QColor(220, 220, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(21, 13, 22, 28)

        # Status indicator dot
        painter.setBrush(QColor(50, 50, 50))
        painter.drawEllipse(30, 46, 4, 4)

        # GPS signal waves (if connected)
        if status in ["green", "yellow"]:
            painter.setPen(QColor(255, 255, 255, 200))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for i in range(3):
                size = 10 + (i * 8)
                painter.drawArc(32 - size//2, 44 - size//2, size, size, 0, 180 * 16)

        painter.end()
        return QIcon(pixmap)

    def _init_menu(self):
        """Initialize context menu"""
        self.menu = QMenu()

        # Status section
        self.status_action = QAction("Phone GPS Status")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.menu.addSeparator()

        # GPS info
        self.gps_fix_action = QAction("GPS: No Fix")
        self.gps_fix_action.setEnabled(False)
        self.menu.addAction(self.gps_fix_action)

        self.gps_coords_action = QAction("Coordinates: --")
        self.gps_coords_action.setEnabled(False)
        self.menu.addAction(self.gps_coords_action)

        self.gps_accuracy_action = QAction("Accuracy: --")
        self.gps_accuracy_action.setEnabled(False)
        self.menu.addAction(self.gps_accuracy_action)

        self.menu.addSeparator()

        # Phone info
        self.phone_status_action = QAction("Phone: Disconnected")
        self.phone_status_action.setEnabled(False)
        self.menu.addAction(self.phone_status_action)

        self.menu.addSeparator()

        # Actions
        refresh_action = QAction("Refresh GPS")
        refresh_action.triggered.connect(self._refresh_gps)
        self.menu.addAction(refresh_action)

        reconnect_action = QAction("Reconnect Phone")
        reconnect_action.triggered.connect(self._reconnect_phone)
        self.menu.addAction(reconnect_action)

        self.menu.addSeparator()

        # Phone Tools submenu
        phone_tools_menu = self.menu.addMenu("📱 Phone Tools")

        # Store submenu as instance variable to prevent garbage collection
        self.phone_tools_menu = phone_tools_menu

        open_gui_action = QAction("Open GUI in Phone Browser", phone_tools_menu)
        open_gui_action.triggered.connect(self._open_phone_gui)
        phone_tools_menu.addAction(open_gui_action)

        mirror_action = QAction("Mirror Phone Screen (scrcpy)", phone_tools_menu)
        mirror_action.triggered.connect(self._mirror_phone_screen)
        phone_tools_menu.addAction(mirror_action)

        phone_tools_menu.addSeparator()

        screenshot_action = QAction("Take Screenshot", phone_tools_menu)
        screenshot_action.triggered.connect(self._take_screenshot)
        phone_tools_menu.addAction(screenshot_action)

        shell_action = QAction("Open ADB Shell", phone_tools_menu)
        shell_action.triggered.connect(self._open_shell)
        phone_tools_menu.addAction(shell_action)

        device_info_action = QAction("View Device Info", phone_tools_menu)
        device_info_action.triggered.connect(self._view_device_info)
        phone_tools_menu.addAction(device_info_action)

        phone_tools_menu.addSeparator()

        wifi_action = QAction("Toggle WiFi", phone_tools_menu)
        wifi_action.triggered.connect(self._toggle_wifi)
        phone_tools_menu.addAction(wifi_action)

        airplane_action = QAction("Toggle Airplane Mode", phone_tools_menu)
        airplane_action.triggered.connect(self._toggle_airplane_mode)
        phone_tools_menu.addAction(airplane_action)

        phone_tools_menu.addSeparator()

        restart_adb_action = QAction("Restart ADB Server", phone_tools_menu)
        restart_adb_action.triggered.connect(self._restart_adb)
        phone_tools_menu.addAction(restart_adb_action)

        self.menu.addSeparator()

        # Security Settings submenu
        security_menu = self.menu.addMenu("🛡️ Security Settings")

        # Store submenu as instance variable to prevent garbage collection
        self.security_menu = security_menu

        # Auto-blacklist toggle
        self.auto_blacklist_action = QAction("✓ Auto-blacklist Phone WiFi" if self.security_settings.get('auto_blacklist_enabled') else "☐ Auto-blacklist Phone WiFi", security_menu)
        self.auto_blacklist_action.triggered.connect(self._toggle_auto_blacklist)
        security_menu.addAction(self.auto_blacklist_action)

        # IMSI detection toggle
        self.imsi_detection_action = QAction("✓ IMSI Catcher Detection" if self.security_settings.get('imsi_detection_enabled') else "☐ IMSI Catcher Detection", security_menu)
        self.imsi_detection_action.triggered.connect(self._toggle_imsi_detection)
        security_menu.addAction(self.imsi_detection_action)

        security_menu.addSeparator()

        # View alerts
        view_alerts_action = QAction("View Security Alerts", security_menu)
        view_alerts_action.triggered.connect(self._view_security_alerts)
        security_menu.addAction(view_alerts_action)

        # Clear alerts
        clear_alerts_action = QAction("Clear Alerts", security_menu)
        clear_alerts_action.triggered.connect(self._clear_security_alerts)
        security_menu.addAction(clear_alerts_action)

        self.menu.addSeparator()

        # Quit
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.menu)

    def _start_status_monitoring(self):
        """Start periodic status checks"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(10000)  # Check every 10 seconds (reduced from 2s for performance)

        # Initial update (async to avoid blocking startup)
        QTimer.singleShot(500, self._update_status)

    def _update_status(self):
        """Update phone and GPS status"""
        self.update_cycle_count += 1

        # Always check phone connection (fast operation)
        self._check_phone_connection()

        # Check GPS fix (fast-ish operation)
        self._check_gps_status()

        # Collect hardware stats only every 3rd cycle (30 seconds instead of 10)
        # This is expensive with multiple adb calls
        if self.update_cycle_count % 3 == 0:
            self._collect_hardware_stats()

        # Check cellular security (IMSI catcher detection) - run every cycle for security
        self._check_cellular_security()

        # Check auto-blacklist for phone's WiFi - run every cycle
        self._check_auto_blacklist()

        # Update UI
        self._update_ui()

    def _check_phone_connection(self):
        """Check if phone is connected via ADB (Android) or libimobiledevice (iPhone)"""
        # Check for Android devices first
        android_connected = False
        try:
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                timeout=1  # Reduced from 2s to 1s for faster response
            )

            # Parse output for connected devices (exclude emulators and offline devices)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            devices = []
            for line in lines:
                if line.strip() and '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    if not device_id.startswith('emulator'):
                        devices.append(device_id)

            if len(devices) > 0:
                android_connected = True
                self.device_id = devices[0]
                self.device_type = 'android'
                self.phone_connected = True

                # Try to get phone model (only if not cached)
                if not hasattr(self, '_cached_phone_model') or not self._cached_phone_model:
                    try:
                        model_result = subprocess.run(
                            ['adb', '-s', self.device_id, 'shell', 'getprop', 'ro.product.model'],
                            capture_output=True,
                            text=True,
                            timeout=1  # Reduced from 2s
                        )
                        self.phone_model = model_result.stdout.strip() or "Unknown Android"
                        self._cached_phone_model = self.phone_model
                    except:
                        self.phone_model = self.device_id[:12]
                        self._cached_phone_model = self.phone_model
                else:
                    self.phone_model = self._cached_phone_model
        except Exception:
            pass

        # Check for iPhone if no Android found
        if not android_connected:
            try:
                result = subprocess.run(
                    ['idevice_id', '-l'],
                    capture_output=True,
                    text=True,
                    timeout=1  # Reduced from 2s
                )
                devices = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]

                if len(devices) > 0:
                    self.device_id = devices[0]
                    self.device_type = 'iphone'
                    self.phone_connected = True

                    # Try to get iPhone model
                    try:
                        model_result = subprocess.run(
                            ['ideviceinfo', '-u', self.device_id, '-k', 'ProductType'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        product_type = model_result.stdout.strip()

                        name_result = subprocess.run(
                            ['ideviceinfo', '-u', self.device_id, '-k', 'DeviceName'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        device_name = name_result.stdout.strip()

                        self.phone_model = f"{device_name} ({product_type})" if device_name and product_type else "Unknown iPhone"
                    except:
                        self.phone_model = "iPhone"
                else:
                    self.phone_connected = False
                    self.device_id = None
                    self.device_type = None
            except Exception:
                self.phone_connected = False
                self.device_id = None
                self.device_type = None

        # If no devices found at all
        if not self.phone_connected:
            self.phone_model = "Unknown"
            self.device_id = None
            self.device_type = None

    def _check_gps_status(self):
        """Check GPS fix status from phone (Android or iPhone)"""
        if not self.phone_connected or not self.device_id:
            self.gps_fix = False
            self.gps_accuracy = 0
            self.gps_lat = 0.0
            self.gps_lon = 0.0
            return

        try:
            if self.device_type == 'android':
                # Get GPS data from Android using adb shell dumpsys location
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'dumpsys', 'location'],
                    capture_output=True,
                    text=True,
                    timeout=2  # Reduced from 3s to 2s
                )

                output = result.stdout

                # Parse for GPS fix - format is "Location[gps LAT,LON hAcc=ACCURACY"
                if 'Location[gps' in output:
                    # Extract coordinates and accuracy
                    try:
                        import re
                        # Match pattern: Location[gps LAT,LON hAcc=ACC
                        gps_match = re.search(r'Location\[gps\s+([-\d.]+),([-\d.]+)\s+hAcc=([\d.]+)', output)

                        if gps_match:
                            self.gps_lat = float(gps_match.group(1))
                            self.gps_lon = float(gps_match.group(2))
                            self.gps_accuracy = float(gps_match.group(3))
                            self.gps_fix = True
                        else:
                            self.gps_fix = False
                    except Exception:
                        self.gps_fix = False
                else:
                    self.gps_fix = False

            elif self.device_type == 'iphone':
                # Get GPS data from iPhone using our script
                result = subprocess.run(
                    ['/opt/gattrose-ng/bin/iphone-gps-check.py'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                try:
                    import json
                    data = json.loads(result.stdout)

                    if data.get('connected') and data.get('location'):
                        loc = data['location']
                        self.gps_lat = loc['latitude']
                        self.gps_lon = loc['longitude']
                        self.gps_accuracy = loc.get('accuracy', 0) or 0
                        self.gps_fix = True
                    else:
                        self.gps_fix = False
                except Exception:
                    self.gps_fix = False
            else:
                self.gps_fix = False

        except Exception as e:
            self.gps_fix = False
            self.gps_accuracy = 0

    def _collect_hardware_stats(self):
        """Collect comprehensive hardware statistics from phone"""
        if not self.phone_connected or not self.device_id:
            return

        try:
            import re

            # Get CPU frequencies
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq 2>/dev/null'],
                    capture_output=True, text=True, timeout=2
                )
                freqs = result.stdout.strip().split('\n')
                self.cpu_freq = {i: int(freq) // 1000 for i, freq in enumerate(freqs) if freq.isdigit()}
            except:
                pass

            # Get CPU temperature (try multiple thermal zones)
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null'],
                    capture_output=True, text=True, timeout=2
                )
                temps = [int(t) / 1000 for t in result.stdout.strip().split('\n') if t.isdigit()]
                if temps:
                    self.cpu_temp = max(temps)  # Highest temp
            except:
                pass

            # Get RAM usage
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'cat /proc/meminfo'],
                    capture_output=True, text=True, timeout=2
                )
                for line in result.stdout.split('\n'):
                    if 'MemTotal:' in line:
                        self.ram_total_mb = int(line.split()[1]) // 1024
                    elif 'MemAvailable:' in line:
                        avail_mb = int(line.split()[1]) // 1024
                        self.ram_used_mb = self.ram_total_mb - avail_mb
            except:
                pass

            # Get storage usage
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'df /data'],
                    capture_output=True, text=True, timeout=2
                )
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 3:
                        self.storage_total_gb = int(parts[1]) / 1024 / 1024  # KB to GB
                        self.storage_used_gb = int(parts[2]) / 1024 / 1024
            except:
                pass

            # Get cell signal strength
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'dumpsys telephony.registry'],
                    capture_output=True, text=True, timeout=2
                )
                # Look for signal strength patterns
                signal_match = re.search(r'mSignalStrength.*?(-?\d+)\s*dBm', result.stdout)
                if signal_match:
                    self.cell_signal = int(signal_match.group(1))

                # Get network type (LTE, 5G, etc)
                type_match = re.search(r'mDataNetworkType=(\d+)', result.stdout)
                if type_match:
                    type_code = int(type_match.group(1))
                    type_map = {13: 'LTE', 20: '5G', 3: '3G', 2: 'EDGE', 1: 'GPRS'}
                    self.cell_type = type_map.get(type_code, f'Type {type_code}')
            except:
                pass

            # Get WiFi info
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'dumpsys wifi'],
                    capture_output=True, text=True, timeout=2
                )
                # Get SSID
                ssid_match = re.search(r'SSID:\s*"?([^",\n]+)"?', result.stdout)
                if ssid_match:
                    self.wifi_ssid = ssid_match.group(1).strip()

                # Get signal strength
                rssi_match = re.search(r'RSSI:\s*(-?\d+)', result.stdout)
                if rssi_match:
                    self.wifi_signal = int(rssi_match.group(1))
            except:
                pass

            # Get SOC/Board info (only need to get once)
            if self.soc_model == "Unknown":
                try:
                    result = subprocess.run(
                        ['adb', '-s', self.device_id, 'shell', 'getprop ro.board.platform'],
                        capture_output=True, text=True, timeout=2
                    )
                    self.soc_model = result.stdout.strip() or "Unknown"
                except:
                    pass

            if self.board_name == "Unknown":
                try:
                    result = subprocess.run(
                        ['adb', '-s', self.device_id, 'shell', 'getprop ro.product.board'],
                        capture_output=True, text=True, timeout=2
                    )
                    self.board_name = result.stdout.strip() or "Unknown"
                except:
                    pass

            # Get uptime
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'cat /proc/uptime'],
                    capture_output=True, text=True, timeout=2
                )
                self.uptime_seconds = float(result.stdout.split()[0])
            except:
                pass

            # Get CPU load average
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'cat /proc/loadavg'],
                    capture_output=True, text=True, timeout=2
                )
                self.cpu_load_avg = [float(x) for x in result.stdout.split()[:3]]
            except:
                pass

            # Get screen state
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'dumpsys power | grep "mHolding"'],
                    capture_output=True, text=True, timeout=2
                )
                self.screen_on = 'SCREEN_BRIGHT_WAKE_LOCK' in result.stdout
            except:
                pass

            # Get battery temperature
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'dumpsys battery'],
                    capture_output=True, text=True, timeout=2
                )
                temp_match = re.search(r'temperature:\s*(\d+)', result.stdout)
                if temp_match:
                    self.battery_temp = int(temp_match.group(1)) / 10.0
            except:
                pass

            # Get network statistics (wlan0 only for simplicity)
            try:
                result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'cat /proc/net/dev'],
                    capture_output=True, text=True, timeout=2
                )
                for line in result.stdout.split('\n'):
                    if 'wlan0:' in line or line.strip().startswith('wlan0'):
                        parts = line.split()
                        if len(parts) > 9:
                            self.network_rx_mb = int(parts[1]) / 1024 / 1024
                            self.network_tx_mb = int(parts[9]) / 1024 / 1024
                        break
            except:
                pass

        except Exception as e:
            pass  # Silently continue if hardware stats fail

    def _check_cellular_security(self):
        """Check for IMSI catcher indicators and auto-blacklist phone's WiFi"""
        if not self.phone_connected or not self.device_id:
            return

        # Only check if IMSI detection is enabled
        if not self.security_settings.get('imsi_detection_enabled'):
            return

        try:
            import re
            from datetime import datetime, timedelta

            # Get cellular network data
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'dumpsys telephony.registry'],
                capture_output=True, text=True, timeout=3
            )
            output = result.stdout

            # Parse cell tower information
            cell_id_match = re.search(r'mCi=(\d+)', output)
            pci_match = re.search(r'mPci=(\d+)', output)
            mcc_match = re.search(r'mMcc=(\d+)', output)
            mnc_match = re.search(r'mMnc=(\d+)', output)

            # Parse network type from data network type code
            type_match = re.search(r'mDataNetworkType=(\d+)', output)
            network_type = "Unknown"
            if type_match:
                type_code = int(type_match.group(1))
                type_map = {13: 'LTE', 20: '5G', 3: '3G', 2: 'EDGE', 1: 'GPRS', 0: 'Unknown'}
                network_type = type_map.get(type_code, f'Type {type_code}')

            # Parse signal strength (RSRP for LTE)
            rsrp_match = re.search(r'rsrp=(-?\d+)', output)
            signal_strength = int(rsrp_match.group(1)) if rsrp_match else 0

            # Update current values
            if cell_id_match:
                new_cell_id = int(cell_id_match.group(1))

                # Get MCC/MNC (parsed below)
                new_mcc = int(mcc_match.group(1)) if mcc_match else self.cell_mcc or 0
                new_mnc = int(mnc_match.group(1)) if mnc_match else self.cell_mnc or 0
                new_pci = int(pci_match.group(1)) if pci_match else None

                # Create tower info object for new tower
                new_tower = CellTowerInfo(
                    cell_id=new_cell_id,
                    pci=new_pci,
                    mcc=new_mcc,
                    mnc=new_mnc,
                    network_type=network_type,
                    signal_strength=signal_strength,
                    frequency=None,  # Not available from dumpsys
                    timestamp=datetime.now(),
                    latitude=self.gps_lat if self.gps_fix else None,
                    longitude=self.gps_lon if self.gps_fix else None
                )

                # Record observation
                self.imsi_detector.record_tower_observation(new_tower)

                # Detect tower change with Rayhunter heuristics
                if self.last_cell_tower_id and self.last_cell_tower_id != new_cell_id:
                    # Create old tower object
                    old_tower = CellTowerInfo(
                        cell_id=self.last_cell_tower_id,
                        pci=self.cell_pci,
                        mcc=self.cell_mcc or 0,
                        mnc=self.cell_mnc or 0,
                        network_type=self.cell_network_type,
                        signal_strength=self.cell_signal_strength,
                        frequency=None,
                        timestamp=self.last_tower_change_time or datetime.now()
                    )

                    # Run Rayhunter-based analysis
                    alerts = self.imsi_detector.analyze_tower_change(new_tower, old_tower)

                    # Process any alerts
                    for alert in alerts:
                        print(f"[!] IMSI Catcher Alert: {alert.severity.upper()} - {alert.message}")

                        # Convert to old format for compatibility
                        alert_dict = {
                            'type': alert.alert_type,
                            'severity': alert.severity,
                            'message': alert.message,
                            'confidence': alert.confidence,
                            'details': alert.details,
                            'timestamp': alert.timestamp.isoformat()
                        }
                        self.imsi_alerts.append(alert_dict)

                        # Log event
                        if self.security_settings.get('imsi_log_events'):
                            self.security_settings.add_cellular_event(alert_dict)

                        # Show alert if enabled and severity is high enough
                        if self.security_settings.get('imsi_alert_on_detection'):
                            if alert.severity in ['high', 'critical']:
                                icon = QSystemTrayIcon.MessageIcon.Critical if alert.severity == 'critical' else QSystemTrayIcon.MessageIcon.Warning
                                self.tray_icon.showMessage(
                                    f"🚨 IMSI Catcher Alert ({alert.severity.upper()})",
                                    f"{alert.message}\n\n{alert.recommended_action}",
                                    icon,
                                    10000 if alert.severity == 'critical' else 5000
                                )

                    self.last_tower_change_time = datetime.now()
                    self.tower_change_count += 1

                self.last_cell_tower_id = new_cell_id
                self.cell_tower_id = new_cell_id
                self.cell_network_type = network_type
                self.cell_signal_strength = signal_strength

            if pci_match:
                self.cell_pci = int(pci_match.group(1))

            if mcc_match and mnc_match:
                new_mcc = int(mcc_match.group(1))
                new_mnc = int(mnc_match.group(1))

                # Detect MCC/MNC change (possible IMSI catcher)
                if self.cell_mcc and self.cell_mnc:
                    if (self.cell_mcc != new_mcc or self.cell_mnc != new_mnc):
                        alert = {
                            'type': 'carrier_change',
                            'severity': 'critical',
                            'message': f'Carrier identifier changed! Old: {self.cell_mcc}/{self.cell_mnc}, New: {new_mcc}/{new_mnc}',
                            'old_mcc_mnc': f'{self.cell_mcc}/{self.cell_mnc}',
                            'new_mcc_mnc': f'{new_mcc}/{new_mnc}',
                            'timestamp': datetime.now().isoformat()
                        }
                        self.imsi_alerts.append(alert)

                        if self.security_settings.get('imsi_log_events'):
                            self.security_settings.add_cellular_event(alert)

                        if self.security_settings.get('imsi_alert_on_detection'):
                            self.tray_icon.showMessage(
                                "🚨 CRITICAL ALERT",
                                alert['message'],
                                QSystemTrayIcon.MessageIcon.Critical,
                                10000
                            )

                self.cell_mcc = new_mcc
                self.cell_mnc = new_mnc

            # Detect network type downgrade (LTE -> 3G/2G is suspicious)
            if self.cell_network_type and network_type != self.cell_network_type:
                old_type = self.cell_network_type
                # Check for downgrade
                type_priority = {'5G': 4, 'LTE': 3, '3G': 2, 'EDGE': 1, 'GPRS': 1, 'Unknown': 0}
                old_priority = type_priority.get(old_type, 0)
                new_priority = type_priority.get(network_type, 0)

                if new_priority < old_priority and old_priority >= 3:  # Downgrade from LTE/5G
                    alert = {
                        'type': 'network_downgrade',
                        'severity': 'medium',
                        'message': f'Network downgrade detected: {old_type} → {network_type}',
                        'old_type': old_type,
                        'new_type': network_type,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.imsi_alerts.append(alert)

                    if self.security_settings.get('imsi_log_events'):
                        self.security_settings.add_cellular_event(alert)

                    if self.security_settings.get('imsi_alert_on_detection'):
                        self.tray_icon.showMessage(
                            "⚠️ Security Alert",
                            alert['message'],
                            QSystemTrayIcon.MessageIcon.Warning,
                            5000
                        )

            self.cell_network_type = network_type
            self.cell_signal_strength = signal_strength

            # Keep only last 10 alerts in memory
            if len(self.imsi_alerts) > 10:
                self.imsi_alerts = self.imsi_alerts[-10:]

        except Exception as e:
            pass  # Silently continue on errors

    def _check_auto_blacklist(self):
        """Auto-blacklist the phone's WiFi network if enabled"""
        if not self.phone_connected or not self.device_id:
            return

        # Only check if auto-blacklist is enabled
        if not self.security_settings.get('auto_blacklist_enabled'):
            return

        # Check if we have WiFi info
        if not self.wifi_ssid:
            return

        try:
            # Get WiFi BSSID (MAC address of access point)
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'dumpsys wifi'],
                capture_output=True, text=True, timeout=2
            )

            import re
            bssid_match = re.search(r'BSSID:\s*([0-9a-fA-F:]{17})', result.stdout)

            if bssid_match:
                bssid = bssid_match.group(1).upper()

                # Check if already blacklisted
                if self.security_settings.is_auto_blacklisted(bssid):
                    return  # Already handled

                # Blacklist this network via API
                try:
                    import requests
                    response = requests.post(
                        'http://localhost:5555/api/networks/blacklist',
                        json={
                            'bssid': bssid,
                            'reason': self.security_settings.get('auto_blacklist_reason', 'Auto-blacklisted: Phone WiFi network')
                        },
                        timeout=2
                    )

                    if response.status_code == 200:
                        # Track this blacklist
                        self.security_settings.add_blacklisted_network(self.wifi_ssid, bssid)

                        # Notify user
                        self.tray_icon.showMessage(
                            "🛡️ Network Protected",
                            f"Auto-blacklisted: {self.wifi_ssid}",
                            QSystemTrayIcon.MessageIcon.Information,
                            3000
                        )
                        print(f"[*] Auto-blacklisted phone WiFi: {self.wifi_ssid} ({bssid})")
                except Exception as e:
                    print(f"[!] Failed to auto-blacklist network: {e}")

        except Exception as e:
            pass  # Silently continue

    def _build_detailed_tooltip(self):
        """Build detailed tooltip with GPS and battery info"""
        lines = ["Phone GPS Manager"]
        lines.append("=" * 30)

        # GPS Status
        if self.gps_fix:
            lat_str = f"{abs(self.gps_lat):.6f}°{'N' if self.gps_lat >= 0 else 'S'}"
            lon_str = f"{abs(self.gps_lon):.6f}°{'E' if self.gps_lon >= 0 else 'W'}"
            acc_str = f" (±{int(self.gps_accuracy)}m)" if self.gps_accuracy and self.gps_accuracy < 10000 else ""
            lines.append(f"📍 GPS: {lat_str}, {lon_str}{acc_str}")
        elif self.phone_connected:
            lines.append("📍 GPS: Searching for fix...")
        else:
            lines.append("📍 GPS: No Fix")

        # Phone Status
        if self.phone_connected:
            lines.append(f"📱 Phone: {self.phone_model}")

            # Uptime and load
            if self.uptime_seconds > 0:
                hours = int(self.uptime_seconds // 3600)
                minutes = int((self.uptime_seconds % 3600) // 60)
                days = hours // 24
                hours = hours % 24
                if days > 0:
                    lines.append(f"⏱️  Uptime: {days}d {hours}h {minutes}m")
                else:
                    lines.append(f"⏱️  Uptime: {hours}h {minutes}m")

            if self.cpu_load_avg:
                lines.append(f"📊 Load: {self.cpu_load_avg[0]:.2f}, {self.cpu_load_avg[1]:.2f}, {self.cpu_load_avg[2]:.2f}")

            # Screen state
            screen_icon = "🔆" if self.screen_on else "🌙"
            screen_state = "ON" if self.screen_on else "OFF"
            lines.append(f"{screen_icon} Screen: {screen_state}")

            # Try to get battery info from GPS service
            try:
                from src.services.gps_service import get_gps_service
                gps_service = get_gps_service()
                phone_status = gps_service.get_phone_status()

                if phone_status and phone_status.get('battery_level'):
                    lines.append("")
                    battery = phone_status['battery_level']
                    battery_status = phone_status.get('battery_status', 'Unknown')
                    battery_icon = "🔋" if battery > 20 else "🪫"

                    lines.append(f"{battery_icon} Battery: {battery}% ({battery_status})")

                    # Voltage and current
                    voltage = phone_status.get('battery_voltage')
                    current_now = phone_status.get('battery_current_now')

                    if voltage and current_now is not None:
                        wattage = (voltage * abs(current_now)) / 1000.0
                        current_amps = current_now / 1000.0

                        if current_now > 0:
                            lines.append(f"   ⚡ Charging: {voltage:.2f}V @ {abs(current_amps):.3f}A ({wattage:.2f}W)")
                        else:
                            lines.append(f"   🔌 Draw: {voltage:.2f}V @ {abs(current_amps):.3f}A ({wattage:.2f}W)")
                    elif voltage:
                        lines.append(f"   Voltage: {voltage:.2f}V")

                    # Time estimates
                    time_to_full_mins = phone_status.get('battery_time_to_full_minutes')
                    if time_to_full_mins and battery_status == 'Charging':
                        hours = time_to_full_mins // 60
                        minutes = time_to_full_mins % 60
                        if hours > 0:
                            lines.append(f"   ⏱️  Time to full: {hours}h {minutes}m")
                        else:
                            lines.append(f"   ⏱️  Time to full: {minutes}m")
                    elif current_now is not None and battery_status == 'Discharging':
                        capacity_mah = phone_status.get('battery_capacity_mah')
                        if capacity_mah and abs(current_now) > 50:
                            remaining_mah = (capacity_mah * battery) / 100.0
                            hours_to_empty = remaining_mah / abs(current_now)

                            if 0 < hours_to_empty < 48:
                                hours = int(hours_to_empty)
                                minutes = int((hours_to_empty - hours) * 60)
                                if hours > 0:
                                    lines.append(f"   ⏱️  Time to empty: {hours}h {minutes}m")
                                else:
                                    lines.append(f"   ⏱️  Time to empty: {minutes}m")

                    # Battery temperature
                    if self.battery_temp > 0:
                        temp_icon = "🌡️" if self.battery_temp < 40 else "🔥"
                        lines.append(f"   {temp_icon} Temp: {self.battery_temp:.1f}°C")
            except Exception as e:
                pass  # Silently ignore battery info errors

            # Hardware stats
            lines.append("")

            # CPU info
            if self.cpu_temp > 0:
                temp_icon = "🌡️" if self.cpu_temp < 70 else "🔥"
                lines.append(f"{temp_icon} CPU: {self.cpu_temp:.1f}°C")

            if self.cpu_freq:
                # Show min and max frequencies
                freqs = list(self.cpu_freq.values())
                min_freq = min(freqs)
                max_freq = max(freqs)
                if min_freq == max_freq:
                    lines.append(f"   Clock: {max_freq}MHz ({len(freqs)} cores)")
                else:
                    lines.append(f"   Clock: {min_freq}-{max_freq}MHz ({len(freqs)} cores)")

            # RAM
            if self.ram_total_mb > 0:
                ram_pct = (self.ram_used_mb / self.ram_total_mb * 100) if self.ram_total_mb > 0 else 0
                lines.append(f"💾 RAM: {self.ram_used_mb}MB / {self.ram_total_mb}MB ({ram_pct:.0f}%)")

            # Storage
            if self.storage_total_gb > 0:
                storage_pct = (self.storage_used_gb / self.storage_total_gb * 100) if self.storage_total_gb > 0 else 0
                lines.append(f"💿 Storage: {self.storage_used_gb:.1f}GB / {self.storage_total_gb:.1f}GB ({storage_pct:.0f}%)")

            # Network info
            lines.append("")

            # Cell signal
            if self.cell_signal != 0:
                if self.cell_signal > -90:
                    signal_icon = "📶"
                elif self.cell_signal > -100:
                    signal_icon = "📶"
                else:
                    signal_icon = "📶"
                lines.append(f"{signal_icon} Cell: {self.cell_signal}dBm ({self.cell_type})")

            # WiFi
            if self.wifi_ssid:
                if self.wifi_signal > -60:
                    wifi_icon = "📶"
                elif self.wifi_signal > -70:
                    wifi_icon = "📶"
                else:
                    wifi_icon = "📶"
                lines.append(f"{wifi_icon} WiFi: {self.wifi_ssid} ({self.wifi_signal}dBm)")

            # Network data usage
            if self.network_rx_mb > 0 or self.network_tx_mb > 0:
                total_mb = self.network_rx_mb + self.network_tx_mb
                if total_mb >= 1024:
                    total_gb = total_mb / 1024
                    rx_gb = self.network_rx_mb / 1024
                    tx_gb = self.network_tx_mb / 1024
                    lines.append(f"📡 Data: ↓{rx_gb:.2f}GB ↑{tx_gb:.2f}GB (Total: {total_gb:.2f}GB)")
                else:
                    lines.append(f"📡 Data: ↓{self.network_rx_mb:.0f}MB ↑{self.network_tx_mb:.0f}MB")

            # Hardware info
            if self.soc_model != "Unknown" or self.board_name != "Unknown":
                lines.append("")
                if self.soc_model != "Unknown":
                    lines.append(f"🔧 SOC: {self.soc_model}")
                if self.board_name != "Unknown":
                    lines.append(f"📋 Board: {self.board_name}")

            # Security monitoring status
            if self.security_settings.get('imsi_detection_enabled'):
                lines.append("")
                lines.append("🛡️ Security Monitoring: Active")

                # Show cell tower info
                if self.cell_tower_id:
                    lines.append(f"   📡 Cell Tower: {self.cell_tower_id}")
                    if self.cell_mcc and self.cell_mnc:
                        lines.append(f"   📍 Carrier: {self.cell_mcc}/{self.cell_mnc} ({self.cell_network_type})")

                # Show recent alerts
                if self.imsi_alerts:
                    recent_alert = self.imsi_alerts[-1]
                    severity_icons = {'critical': '🚨', 'high': '⚠️', 'medium': '⚠️', 'low': 'ℹ️'}
                    icon = severity_icons.get(recent_alert.get('severity', 'low'), 'ℹ️')
                    lines.append(f"   {icon} Alert: {recent_alert['type'].replace('_', ' ').title()}")

        else:
            lines.append("📱 Phone: Not Connected")

        return "\n".join(lines)

    def _update_ui(self):
        """Update tray icon and tooltip based on status"""
        # Determine icon color
        if not self.phone_connected:
            status = "red"
        elif self.gps_fix:
            status = "green"
        elif self.phone_connected:
            status = "yellow"
        else:
            status = "gray"

        # Build detailed tooltip
        tooltip = self._build_detailed_tooltip()

        # Update icon
        self.tray_icon.setIcon(self._create_phone_icon(status))
        self.tray_icon.setToolTip(tooltip)

        # Update menu items
        if self.phone_connected:
            self.phone_status_action.setText(f"Phone: {self.phone_model}")
        else:
            self.phone_status_action.setText("Phone: Disconnected")

        if self.gps_fix:
            self.gps_fix_action.setText(f"GPS: Fix OK")
            self.gps_coords_action.setText(f"Coords: {self.gps_lat:.6f}, {self.gps_lon:.6f}")
            self.gps_accuracy_action.setText(f"Accuracy: ±{self.gps_accuracy:.1f}m")
        else:
            self.gps_fix_action.setText("GPS: No Fix")
            self.gps_coords_action.setText("Coordinates: --")
            self.gps_accuracy_action.setText("Accuracy: --")

    def _on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._refresh_gps()

    def _refresh_gps(self):
        """Force GPS refresh"""
        print("[*] Refreshing GPS...")
        self._update_status()
        self.tray_icon.showMessage(
            "GPS Refresh",
            "GPS status updated",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _reconnect_phone(self):
        """Attempt to reconnect phone"""
        print("[*] Reconnecting phone...")
        try:
            # Kill and restart adb server
            subprocess.run(['adb', 'kill-server'], timeout=2)
            subprocess.run(['adb', 'start-server'], timeout=5)

            self.tray_icon.showMessage(
                "Phone Reconnect",
                "Attempting to reconnect phone...",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

            # Update status after a moment
            QTimer.singleShot(3000, self._update_status)
        except Exception as e:
            print(f"[!] Reconnect failed: {e}")

    def _open_phone_gui(self):
        """Open Gattrose-NG GUI in phone browser (accessing PC's GUI)"""
        if not self.phone_connected or not self.device_id:
            self.tray_icon.showMessage(
                "Phone GUI",
                "No phone connected!",
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )
            return

        print("[*] Opening Gattrose-NG GUI on phone...")
        try:
            # Check which port the GUI is running on (5555-5559)
            gui_port = None
            for port in range(5555, 5560):
                try:
                    import socket
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_sock.settimeout(0.5)
                    result = test_sock.connect_ex(('127.0.0.1', port))
                    test_sock.close()
                    if result == 0:
                        gui_port = port
                        print(f"[+] Found GUI on port {gui_port}")
                        break
                except:
                    pass

            if not gui_port:
                self.tray_icon.showMessage(
                    "Phone GUI - Error",
                    "GUI is not running!\nStart the GUI first.",
                    QSystemTrayIcon.MessageIcon.Critical,
                    5000
                )
                print("[!] GUI is not running on any port 5555-5559")
                return

            # Method 1: If Android, use adb reverse port forwarding (works even if not on same WiFi)
            if self.device_type == 'android':
                # Setup reverse port forwarding
                print(f"[*] Setting up ADB reverse port forwarding for port {gui_port}...")
                reverse_result = subprocess.run(
                    ['adb', '-s', self.device_id, 'reverse', f'tcp:{gui_port}', f'tcp:{gui_port}'],
                    capture_output=True, text=True, timeout=3
                )

                if reverse_result.returncode != 0:
                    error_msg = reverse_result.stderr.strip() or "Failed to setup port forwarding"
                    print(f"[!] Port forwarding failed: {error_msg}")
                    self.tray_icon.showMessage(
                        "Phone GUI - Error",
                        f"Port forwarding failed:\n{error_msg}",
                        QSystemTrayIcon.MessageIcon.Critical,
                        5000
                    )
                    return

                print(f"[+] Port forwarding setup successful")

                # Open browser to localhost (which forwards to PC)
                print(f"[*] Opening browser on phone to http://localhost:{gui_port}...")
                browser_result = subprocess.run(
                    ['adb', '-s', self.device_id, 'shell', 'am', 'start',
                     '-a', 'android.intent.action.VIEW',
                     '-d', f'http://localhost:{gui_port}'],
                    capture_output=True, text=True, timeout=3
                )

                if browser_result.returncode != 0:
                    error_msg = browser_result.stderr.strip() or "Failed to open browser"
                    print(f"[!] Browser open failed: {error_msg}")
                    self.tray_icon.showMessage(
                        "Phone GUI - Error",
                        f"Failed to open browser:\n{error_msg}",
                        QSystemTrayIcon.MessageIcon.Critical,
                        5000
                    )
                    return

                print(f"[+] Successfully opened GUI on phone browser")
                self.tray_icon.showMessage(
                    "Phone GUI",
                    f"✓ Opened Gattrose-NG GUI on phone\nPort: {gui_port}",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )

            elif self.device_type == 'iphone':
                # For iPhone, we need them on same network
                # Just open the URL directly
                subprocess.run(
                    ['open', gui_url],  # Opens on Mac, which can then be shared
                    timeout=2
                )
                self.tray_icon.showMessage(
                    "Phone GUI",
                    f"GUI URL: {gui_url}\nOpen this URL in your iPhone browser",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000
                )
                print(f"[*] For iPhone, manually open: {gui_url}")

            else:
                # Unknown device type
                self.tray_icon.showMessage(
                    "Phone GUI",
                    f"Open this URL on your phone:\n{gui_url}",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000
                )
                print(f"[*] GUI URL: {gui_url}")

        except Exception as e:
            print(f"[!] Failed to open GUI on phone: {e}")
            import traceback
            traceback.print_exc()
            self.tray_icon.showMessage(
                "Phone GUI",
                f"Failed to open GUI: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000
            )

    def _toggle_auto_blacklist(self):
        """Toggle auto-blacklist feature"""
        enabled = self.security_settings.toggle_auto_blacklist()
        self.auto_blacklist_action.setText("✓ Auto-blacklist Phone WiFi" if enabled else "☐ Auto-blacklist Phone WiFi")

        status = "enabled" if enabled else "disabled"
        self.tray_icon.showMessage(
            "Auto-blacklist",
            f"Auto-blacklist {status}",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        print(f"[*] Auto-blacklist {status}")

    def _toggle_imsi_detection(self):
        """Toggle IMSI catcher detection"""
        enabled = self.security_settings.toggle_imsi_detection()
        self.imsi_detection_action.setText("✓ IMSI Catcher Detection" if enabled else "☐ IMSI Catcher Detection")

        status = "enabled" if enabled else "disabled"
        self.tray_icon.showMessage(
            "IMSI Detection",
            f"IMSI catcher detection {status}",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        print(f"[*] IMSI detection {status}")

    def _view_security_alerts(self):
        """Show security alerts dialog"""
        if not self.imsi_alerts:
            self.tray_icon.showMessage(
                "Security Alerts",
                "No security alerts",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            return

        # Format alerts for display
        alert_msgs = []
        for alert in reversed(self.imsi_alerts[-5:]):  # Show last 5
            severity_icons = {'critical': '🚨', 'high': '⚠️', 'medium': '⚠️', 'low': 'ℹ️'}
            icon = severity_icons.get(alert.get('severity', 'low'), 'ℹ️')
            alert_msgs.append(f"{icon} {alert['message']}")

        message = "\n".join(alert_msgs)
        self.tray_icon.showMessage(
            f"Security Alerts ({len(self.imsi_alerts)} total)",
            message,
            QSystemTrayIcon.MessageIcon.Warning,
            10000
        )

    def _clear_security_alerts(self):
        """Clear security alerts"""
        self.imsi_alerts = []
        self.tray_icon.showMessage(
            "Security Alerts",
            "All alerts cleared",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        print("[*] Security alerts cleared")

    def _mirror_phone_screen(self):
        """Mirror phone screen using scrcpy"""
        if not self.phone_connected or not self.device_id:
            self.tray_icon.showMessage(
                "Screen Mirror",
                "No phone connected!",
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )
            return

        print("[*] Starting screen mirroring...")
        try:
            # Check if scrcpy is installed
            try:
                subprocess.run(['which', 'scrcpy'], check=True, capture_output=True)
            except:
                self.tray_icon.showMessage(
                    "Screen Mirror - Error",
                    "scrcpy is not installed!\nRun: sudo apt install scrcpy",
                    QSystemTrayIcon.MessageIcon.Critical,
                    5000
                )
                print("[!] scrcpy not installed")
                return

            # Launch scrcpy in background with optimized settings
            subprocess.Popen(
                ['scrcpy', '-s', self.device_id,
                 '--window-title', f'Phone Mirror - {self.phone_model}',
                 '--window-borderless',  # Borderless window
                 '--stay-awake',  # Keep phone awake
                 '--turn-screen-off',  # Turn off phone screen to save battery (optional)
                 '--power-off-on-close'  # Turn screen back on when closed
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.tray_icon.showMessage(
                "Screen Mirror",
                f"✓ Mirroring {self.phone_model}\nClose the window to stop",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            print(f"[+] Screen mirroring started for {self.device_id}")

        except Exception as e:
            self.tray_icon.showMessage(
                "Screen Mirror Failed",
                f"Error: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000
            )
            print(f"[!] Screen mirroring failed: {e}")

    def _take_screenshot(self):
        """Take a screenshot of the phone screen"""
        if not self.phone_connected or not self.device_id:
            self.tray_icon.showMessage(
                "Screenshot",
                "No phone connected!",
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )
            return

        print("[*] Taking screenshot...")
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = f"/tmp/phone_screenshot_{timestamp}.png"

            # Take screenshot using adb
            subprocess.run(
                ['adb', '-s', self.device_id, 'exec-out', 'screencap', '-p'],
                stdout=open(screenshot_path, 'wb'),
                stderr=subprocess.DEVNULL,
                timeout=10
            )

            # Open screenshot in default viewer
            subprocess.Popen(['xdg-open', screenshot_path])

            self.tray_icon.showMessage(
                "Screenshot",
                f"Screenshot saved to {screenshot_path}",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            print(f"[+] Screenshot saved: {screenshot_path}")

        except Exception as e:
            self.tray_icon.showMessage(
                "Screenshot Failed",
                f"Error: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000
            )
            print(f"[!] Screenshot failed: {e}")

    def _open_shell(self):
        """Open an ADB shell in a terminal"""
        if not self.phone_connected or not self.device_id:
            self.tray_icon.showMessage(
                "ADB Shell",
                "No phone connected!",
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )
            return

        print("[*] Opening ADB shell...")
        try:
            # Try to open in various terminal emulators
            terminals = [
                ['gnome-terminal', '--', 'adb', '-s', self.device_id, 'shell'],
                ['konsole', '-e', 'adb', '-s', self.device_id, 'shell'],
                ['xterm', '-e', 'adb', '-s', self.device_id, 'shell'],
                ['x-terminal-emulator', '-e', 'adb', '-s', self.device_id, 'shell'],
            ]

            for terminal_cmd in terminals:
                try:
                    subprocess.Popen(terminal_cmd)
                    print(f"[+] Opened shell in {terminal_cmd[0]}")
                    return
                except FileNotFoundError:
                    continue

            # Fallback: just show instructions
            self.tray_icon.showMessage(
                "ADB Shell",
                f"Run: adb -s {self.device_id} shell",
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )

        except Exception as e:
            self.tray_icon.showMessage(
                "Shell Failed",
                f"Error: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000
            )
            print(f"[!] Shell open failed: {e}")

    def _view_device_info(self):
        """Display phone device information"""
        if not self.phone_connected or not self.device_id:
            self.tray_icon.showMessage(
                "Device Info",
                "No phone connected!",
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )
            return

        print("[*] Getting device info...")
        try:
            # Get device properties
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'getprop'],
                capture_output=True, text=True, timeout=5
            )

            # Parse key properties
            props = {}
            for line in result.stdout.split('\n'):
                if 'ro.product.model' in line:
                    props['Model'] = line.split('[')[1].split(']')[0]
                elif 'ro.product.manufacturer' in line:
                    props['Manufacturer'] = line.split('[')[1].split(']')[0]
                elif 'ro.build.version.release' in line:
                    props['Android'] = line.split('[')[1].split(']')[0]
                elif 'ro.build.version.sdk' in line:
                    props['SDK'] = line.split('[')[1].split(']')[0]
                elif 'ro.serialno' in line:
                    props['Serial'] = line.split('[')[1].split(']')[0]

            # Get battery info
            battery_result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'dumpsys', 'battery'],
                capture_output=True, text=True, timeout=5
            )
            for line in battery_result.stdout.split('\n'):
                if 'level' in line:
                    props['Battery'] = line.split(':')[1].strip() + '%'
                    break

            # Format info message
            info_lines = [f"{k}: {v}" for k, v in props.items()]
            info_msg = '\n'.join(info_lines)

            self.tray_icon.showMessage(
                f"Device Info - {self.device_id}",
                info_msg,
                QSystemTrayIcon.MessageIcon.Information,
                10000
            )
            print(f"[+] Device info:\n{info_msg}")

        except Exception as e:
            self.tray_icon.showMessage(
                "Device Info Failed",
                f"Error: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000
            )
            print(f"[!] Device info failed: {e}")

    def _toggle_wifi(self):
        """Toggle WiFi on/off on the phone"""
        if not self.phone_connected or not self.device_id:
            self.tray_icon.showMessage(
                "WiFi Toggle",
                "No phone connected!",
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )
            return

        print("[*] Toggling WiFi...")
        try:
            # Get current WiFi state
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'settings', 'get', 'global', 'wifi_on'],
                capture_output=True, text=True, timeout=5
            )
            current_state = result.stdout.strip()

            # Toggle state
            new_state = '0' if current_state == '1' else '1'
            subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'svc', 'wifi', 'enable' if new_state == '1' else 'disable'],
                timeout=5
            )

            status = "enabled" if new_state == '1' else "disabled"
            self.tray_icon.showMessage(
                "WiFi",
                f"WiFi {status}",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            print(f"[+] WiFi {status}")

        except Exception as e:
            self.tray_icon.showMessage(
                "WiFi Toggle Failed",
                f"Error: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000
            )
            print(f"[!] WiFi toggle failed: {e}")

    def _toggle_airplane_mode(self):
        """Toggle airplane mode on/off on the phone"""
        if not self.phone_connected or not self.device_id:
            self.tray_icon.showMessage(
                "Airplane Mode",
                "No phone connected!",
                QSystemTrayIcon.MessageIcon.Warning,
                2000
            )
            return

        print("[*] Toggling airplane mode...")
        try:
            # Get current airplane mode state
            result = subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'settings', 'get', 'global', 'airplane_mode_on'],
                capture_output=True, text=True, timeout=5
            )
            current_state = result.stdout.strip()

            # Toggle state
            new_state = '0' if current_state == '1' else '1'
            subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'settings', 'put', 'global', 'airplane_mode_on', new_state],
                timeout=5
            )

            # Broadcast the change
            subprocess.run(
                ['adb', '-s', self.device_id, 'shell', 'am', 'broadcast',
                 '-a', 'android.intent.action.AIRPLANE_MODE', '--ez', 'state', 'true' if new_state == '1' else 'false'],
                timeout=5
            )

            status = "enabled" if new_state == '1' else "disabled"
            self.tray_icon.showMessage(
                "Airplane Mode",
                f"Airplane mode {status}",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            print(f"[+] Airplane mode {status}")

        except Exception as e:
            self.tray_icon.showMessage(
                "Airplane Mode Failed",
                f"Error: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000
            )
            print(f"[!] Airplane mode toggle failed: {e}")

    def _restart_adb(self):
        """Restart the ADB server"""
        print("[*] Restarting ADB server...")
        try:
            # Kill ADB server
            subprocess.run(['adb', 'kill-server'], timeout=5)
            time.sleep(1)

            # Start ADB server
            subprocess.run(['adb', 'start-server'], timeout=10)

            self.tray_icon.showMessage(
                "ADB Server",
                "ADB server restarted successfully",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            print("[+] ADB server restarted")

            # Trigger reconnection
            time.sleep(1)
            self._reconnect_phone()

        except Exception as e:
            self.tray_icon.showMessage(
                "ADB Restart Failed",
                f"Error: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical,
                3000
            )
            print(f"[!] ADB restart failed: {e}")

    def quit(self):
        """Quit the application"""
        print("[*] Quitting phone tray...")
        self.app.quit()

    def run(self):
        """Run the application"""
        self.tray_icon.show()
        print("[*] Phone GPS tray started")
        return self.app.exec()


def main():
    print("[*] Starting Phone GPS Tray...")
    app = PhoneTrayApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
