#!/usr/bin/env python3
"""
Gattrose System Tray Application
Standalone tray icon that monitors orchestrator and provides controls

Features:
- Real-time service status monitoring
- Color-coded icon based on health
- Detailed status on mouseover
- Start/stop orchestrator
- Show/hide GUI
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtDBus import QDBusConnection, QDBusMessage

# Add project root to path
# Use /opt/gattrose-ng for installed system, not dev directory
PROJECT_ROOT = Path('/opt/gattrose-ng')
sys.path.insert(0, str(PROJECT_ROOT))


class GattroseTrayApp:
    """Standalone system tray application for Gattrose-NG"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # Keep running when GUI closes

        # Prevent multiple instances
        self._check_single_instance()

        self.gui_process = None
        self.gui_log_file = None  # Keep log file handle alive
        self.orchestrator_process = None
        self.tray_icon = None
        self.menu = None

        # Status tracking
        self.status_file = Path("/tmp/gattrose-status.json")
        self.last_status = None
        self.overall_health = "unknown"  # good, warning, error, unknown

        # Event tracking
        self.events_file = Path("/tmp/gattrose-events.json")
        self.last_event_count = 0  # Track number of events we've seen

        # Comprehensive state tracking
        self.system_state = {
            'gui_running': False,
            'orchestrator_running': False,
            'web_server_running': False,
            'scanner_running': False,
            'auto_attack_enabled': False,
            'attack_queue_size': 0,
            'networks_found': 0,
            'clients_found': 0
        }

        self._init_tray_icon()
        self._init_menu()
        self._start_status_monitoring()
        self._start_event_polling()
        self._start_comprehensive_monitoring()

    def _check_single_instance(self):
        """Ensure only one instance of tray app is running"""
        import fcntl
        self.lock_file = open('/tmp/gattrose-tray.lock', 'w')
        try:
            fcntl.lockf(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            print("[!] Another instance of Gattrose tray is already running")
            sys.exit(0)

    def _init_tray_icon(self):
        """Initialize system tray icon"""
        # Start with default icon
        icon = self._create_colored_icon("gray")
        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip("Gattrose-NG - Initializing...")
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _create_colored_icon(self, color: str) -> QIcon:
        """Create a colored icon using actual Gattrose-NG logo with color overlay"""
        # Load the actual Gattrose-NG icon
        icon_path = PROJECT_ROOT / "assets" / "gattrose-ng.png"

        if not icon_path.exists():
            # Fallback to simple colored circle if icon not found
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            colors = {
                "green": QColor(0, 255, 0),
                "yellow": QColor(255, 255, 0),
                "red": QColor(255, 0, 0),
                "gray": QColor(128, 128, 128)
            }
            painter.setBrush(colors.get(color, colors["gray"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(8, 8, 48, 48)
            painter.end()
            return QIcon(pixmap)

        # Load and scale the icon
        original = QPixmap(str(icon_path))
        pixmap = original.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)

        # Create colored overlay
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)

        # Color mapping with transparency for overlay
        colors = {
            "green": QColor(0, 255, 0, 100),      # All services running - green tint
            "yellow": QColor(255, 255, 0, 100),   # Some warnings - yellow tint
            "red": QColor(255, 0, 0, 120),        # Errors/failures - red tint
            "gray": QColor(128, 128, 128, 120)    # Unknown/starting - gray tint
        }

        painter.fillRect(pixmap.rect(), colors.get(color, colors["gray"]))
        painter.end()

        return QIcon(pixmap)

    def _init_menu(self):
        """Initialize context menu"""
        self.menu = QMenu()

        # Status header
        self.status_header = QAction("Gattrose-NG", self.menu)
        self.status_header.setEnabled(False)
        font = self.status_header.font()
        font.setBold(True)
        self.status_header.setFont(font)
        self.menu.addAction(self.status_header)

        self.menu.addSeparator()

        # System state indicators (non-clickable)
        self.gui_status_action = QAction("○ GUI: Stopped", self.menu)
        self.gui_status_action.setEnabled(False)
        self.menu.addAction(self.gui_status_action)

        self.web_status_action = QAction("○ Web UI: Not Running", self.menu)
        self.web_status_action.setEnabled(False)
        self.menu.addAction(self.web_status_action)

        self.scanner_status_action = QAction("○ Scanner: Idle", self.menu)
        self.scanner_status_action.setEnabled(False)
        self.menu.addAction(self.scanner_status_action)

        self.stats_action = QAction("📊 Networks: 0 | Clients: 0", self.menu)
        self.stats_action.setEnabled(False)
        self.menu.addAction(self.stats_action)

        self.gps_status_action = QAction("📍 GPS: Searching...", self.menu)
        self.gps_status_action.setEnabled(False)
        self.menu.addAction(self.gps_status_action)

        self.menu.addSeparator()

        # GUI controls (dynamic based on state)
        self.show_gui_action = QAction("▶ Start GUI", self.menu)
        self.show_gui_action.triggered.connect(self._show_gui)
        self.menu.addAction(self.show_gui_action)

        self.hide_gui_action = QAction("⏹ Stop GUI", self.menu)
        self.hide_gui_action.triggered.connect(self._hide_gui)
        self.hide_gui_action.setVisible(False)  # Hidden by default
        self.menu.addAction(self.hide_gui_action)

        self.menu.addSeparator()

        # Web UI
        self.web_ui_action = QAction("🌐 Open Web UI", self.menu)
        self.web_ui_action.triggered.connect(self._open_web_ui)
        self.menu.addAction(self.web_ui_action)

        self.menu.addSeparator()

        # Orchestrator controls (dynamic based on state)
        self.start_orch_action = QAction("▶ Start Orchestrator", self.menu)
        self.start_orch_action.triggered.connect(self._start_orchestrator)
        self.menu.addAction(self.start_orch_action)

        self.restart_orch_action = QAction("🔄 Restart Orchestrator", self.menu)
        self.restart_orch_action.triggered.connect(self._restart_orchestrator)
        self.restart_orch_action.setVisible(False)  # Hidden until orchestrator is running
        self.menu.addAction(self.restart_orch_action)

        self.stop_orch_action = QAction("⏹ Stop Orchestrator", self.menu)
        self.stop_orch_action.triggered.connect(self._stop_orchestrator)
        self.stop_orch_action.setVisible(False)  # Hidden until orchestrator is running
        self.menu.addAction(self.stop_orch_action)

        self.menu.addSeparator()

        # Service status actions (will be updated dynamically)
        self.service_actions = {}
        service_names = [
            'orchestrator', 'database', 'gps', 'scanner',
            'attack_queue', 'wps_cracking', 'wpa_crack', 'wep_crack'
        ]
        for name in service_names:
            action = QAction(f"{name.replace('_', ' ').title()}: Checking...", self.menu)
            action.setEnabled(False)
            self.menu.addAction(action)
            self.service_actions[name] = action

        self.menu.addSeparator()

        # Quit
        quit_action = QAction("❌ Quit Tray", self.menu)
        quit_action.triggered.connect(self._quit)
        self.menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.menu)

    def _start_status_monitoring(self):
        """Start monitoring orchestrator status file"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(2000)  # Check every 2 seconds

        # Initial check
        self._update_status()

    def _start_event_polling(self):
        """Start polling for events to display as notifications"""
        self.event_timer = QTimer()
        self.event_timer.timeout.connect(self._poll_events)
        self.event_timer.start(1000)  # Check every 1 second

    def _poll_events(self):
        """Poll events file and display new events as notifications"""
        try:
            if not self.events_file.exists():
                return

            # Read events file
            with open(self.events_file, 'r') as f:
                data = json.load(f)

            events = data.get('events', [])
            total_events = len(events)

            # Check if there are new events
            if total_events > self.last_event_count:
                # Get only new events
                new_events = events[self.last_event_count:]

                # Display each new event
                for event in new_events:
                    event_type = event.get('type', 'unknown')
                    title = event.get('title', 'Event')
                    message = event.get('message', '')
                    urgency = event.get('urgency', 'normal')

                    self._show_notification(title, message, urgency)

                # Update counter
                self.last_event_count = total_events

        except json.JSONDecodeError:
            pass  # Ignore malformed JSON
        except Exception as e:
            print(f"[!] Error polling events: {e}")

    def _update_status(self):
        """Read status from orchestrator and update display"""
        try:
            if not self.status_file.exists():
                self._set_status_unknown()
                return

            # Read status file
            with open(self.status_file, 'r') as f:
                status = json.load(f)

            self.last_status = status

            # Update tooltip with detailed status
            tooltip = self._build_tooltip(status)
            self.tray_icon.setToolTip(tooltip)

            # Update menu items
            self._update_menu_items(status)

            # Determine overall health and update icon
            health = self._calculate_health(status)
            if health != self.overall_health:
                self.overall_health = health
                self._update_icon(health)

        except json.JSONDecodeError:
            self._set_status_error("Invalid status file")
        except Exception as e:
            self._set_status_error(f"Error reading status: {e}")

    def _build_tooltip(self, status: dict) -> str:
        """Build detailed tooltip from status"""
        lines = ["Gattrose-NG Status"]
        lines.append("=" * 30)

        if 'orchestrator' in status:
            orch_running = status['orchestrator'].get('running', False)
            lines.append(f"Orchestrator: {'✓ Running' if orch_running else '✗ Stopped'}")

        if 'services' in status:
            lines.append("")
            lines.append("Services:")

            for svc_name, svc_data in status['services'].items():
                name = svc_data.get('name', svc_name.title())
                running = svc_data.get('running', False)
                svc_status = svc_data.get('status', 'unknown')

                if running:
                    icon = "✓"
                elif svc_status == 'error':
                    icon = "✗"
                else:
                    icon = "○"

                lines.append(f"  {icon} {name}: {svc_status}")

                # Add metadata if available
                metadata = svc_data.get('metadata', {})
                if metadata:
                    for key, value in metadata.items():
                        if value is not None:
                            lines.append(f"     {key}: {value}")

        return "\n".join(lines)

    def _update_menu_items(self, status: dict):
        """Update menu items with current status"""
        if 'services' not in status:
            return

        services = status['services']

        # Update orchestrator status in header
        orch_running = status.get('orchestrator', {}).get('running', False)
        if orch_running:
            self.status_header.setText("Gattrose-NG: ✓ Running")
        else:
            self.status_header.setText("Gattrose-NG: ○ Stopped")

        # Update individual service statuses
        for svc_name, action in self.service_actions.items():
            if svc_name == 'orchestrator':
                # Handled in header
                if orch_running:
                    action.setText("Orchestrator: ✓ Running")
                else:
                    action.setText("Orchestrator: ○ Stopped")
                continue

            if svc_name in services:
                svc_data = services[svc_name]
                name = svc_data.get('name', svc_name.title())
                running = svc_data.get('running', False)
                svc_status = svc_data.get('status', 'unknown')

                if running:
                    icon = "✓"
                    text = f"{name}: Running"
                elif svc_status == 'error':
                    icon = "✗"
                    text = f"{name}: Error"
                else:
                    icon = "○"
                    text = f"{name}: {svc_status.title()}"

                action.setText(f"{icon} {text}")

                # Add metadata to tooltip if available
                metadata = svc_data.get('metadata', {})
                if metadata:
                    tooltip_parts = [text]
                    for key, value in metadata.items():
                        if value is not None:
                            tooltip_parts.append(f"{key}: {value}")
                    action.setToolTip("\n".join(tooltip_parts))
            else:
                action.setText(f"{svc_name.title()}: Unknown")

        # Update GPS/Phone status
        gps_svc = services.get('gps', {})
        gps_running = gps_svc.get('running', False)
        gps_meta = gps_svc.get('metadata', {})
        has_location = gps_meta.get('has_location', False)
        gps_source = gps_meta.get('source', 'none')

        if has_location:
            # We have a GPS fix
            source_icon = {
                'gpsd': '🛰️',
                'phone-usb': '📱',
                'phone-bt': '📱',
                'iphone': '📱',
                'android': '📱',
                'manual': '📌',
                'geoip': '🌍'
            }.get(gps_source, '📍')

            accuracy = gps_meta.get('accuracy', 0)
            if accuracy < 100:
                acc_str = f"±{accuracy:.0f}m"
            else:
                acc_str = f"±{accuracy/1000:.1f}km"

            self.gps_status_action.setText(f"{source_icon} GPS: {gps_source} ({acc_str})")
            tooltip = (f"Location Source: {gps_source}\n"
                       f"Accuracy: {acc_str}\n"
                       f"Fix: {gps_meta.get('fix_quality', 'Unknown')}")
            self.gps_status_action.setToolTip(tooltip)
        elif gps_running:
            self.gps_status_action.setText("📍 GPS: Searching...")
            self.gps_status_action.setToolTip("GPS service running, waiting for fix")
        else:
            self.gps_status_action.setText("📍 GPS: Not Available")
            self.gps_status_action.setToolTip("No GPS source connected")

    def _calculate_health(self, status: dict) -> str:
        """Calculate overall system health"""
        if 'orchestrator' not in status or not status['orchestrator'].get('running', False):
            return "gray"

        if 'services' not in status:
            return "gray"

        services = status['services']
        running_count = 0
        error_count = 0
        total_count = len(services)

        for svc_data in services.values():
            if svc_data.get('running', False):
                running_count += 1
            elif svc_data.get('status') == 'error':
                error_count += 1

        # Health logic
        if error_count > 0:
            return "red"  # Any errors = red
        elif running_count == total_count:
            return "green"  # All services running = green
        elif running_count > 0:
            return "yellow"  # Some services running = yellow
        else:
            return "gray"  # Nothing running = gray

    def _update_icon(self, health: str):
        """Update tray icon color based on health"""
        icon = self._create_colored_icon(health)
        self.tray_icon.setIcon(icon)

    def _set_status_unknown(self):
        """Set status to unknown (orchestrator not running)"""
        self.overall_health = "gray"
        self._update_icon("gray")
        self.tray_icon.setToolTip("Gattrose-NG - Orchestrator Not Running")
        self.status_header.setText("Gattrose-NG: ○ Not Running")

        # Update all service actions
        for name, action in self.service_actions.items():
            action.setText(f"{name.title()}: Unknown")

    def _set_status_error(self, error: str):
        """Set status to error"""
        self.overall_health = "red"
        self._update_icon("red")
        self.tray_icon.setToolTip(f"Gattrose-NG - Error\n{error}")
        self.status_header.setText("Gattrose-NG: ✗ Error")

    def _start_orchestrator(self):
        """Start the orchestrator"""
        if self.orchestrator_process and self.orchestrator_process.poll() is None:
            self._show_notification("Orchestrator Running", "Orchestrator is already running")
            return

        try:
            # Start orchestrator in background
            python = PROJECT_ROOT / '.venv' / 'bin' / 'python'
            script = PROJECT_ROOT / 'src' / 'services' / 'orchestrator.py'

            self.orchestrator_process = subprocess.Popen(
                [str(python), str(script)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self._show_notification(
                "Orchestrator Started",
                "Gattrose-NG orchestrator is starting..."
            )

        except Exception as e:
            self._show_notification(
                "Start Failed",
                f"Failed to start orchestrator: {e}",
                urgency="critical"
            )

    def _stop_orchestrator(self):
        """Stop the orchestrator"""
        if not self.orchestrator_process or self.orchestrator_process.poll() is not None:
            # Try to stop via signal file
            try:
                # Send SIGTERM via orchestrator if running
                subprocess.run(['pkill', '-TERM', '-f', 'orchestrator.py'], timeout=2)
                self._show_notification("Orchestrator Stopped", "Orchestrator is stopping...")
            except:
                self._show_notification("Not Running", "Orchestrator is not running")
            return

        try:
            self.orchestrator_process.terminate()
            self.orchestrator_process.wait(timeout=5)
            self.orchestrator_process = None

            self._show_notification(
                "Orchestrator Stopped",
                "Gattrose-NG orchestrator has been stopped"
            )

        except subprocess.TimeoutExpired:
            self.orchestrator_process.kill()
            self.orchestrator_process = None
            self._show_notification(
                "Orchestrator Killed",
                "Orchestrator was forcefully stopped"
            )

    def _restart_orchestrator(self):
        """Restart the orchestrator"""
        self._stop_orchestrator()
        time.sleep(1)
        self._start_orchestrator()

    def _show_gui(self):
        """Launch or show the GUI"""
        if self.gui_process is None or self.gui_process.poll() is not None:
            # GUI not running, start it
            try:
                python = PROJECT_ROOT / '.venv' / 'bin' / 'python'
                script = PROJECT_ROOT / 'src' / 'main.py'

                # Copy current environment and add GUI-specific settings
                env = os.environ.copy()
                # DISPLAY, QT_QPA_PLATFORM, etc. should already be in environment from systemd
                # Just ensure PYTHONPATH is set
                env['PYTHONPATH'] = str(PROJECT_ROOT)
                env['PYTHONUNBUFFERED'] = '1'

                # Redirect output to log file instead of PIPE to prevent buffer filling
                # Keep the file handle alive to prevent it being closed by garbage collector
                self.gui_log_file = open('/tmp/gattrose-gui-from-tray.log', 'a')

                self.gui_process = subprocess.Popen(
                    [str(python), str(script), '--viewer-only'],  # Viewer mode: no privileged ops
                    cwd=str(PROJECT_ROOT),
                    env=env,
                    stdout=self.gui_log_file,
                    stderr=self.gui_log_file,
                    start_new_session=True  # Detach from parent process group
                )
                self.show_gui_action.setEnabled(False)
                self.hide_gui_action.setEnabled(True)

                # Monitor GUI process
                self.gui_timer = QTimer()
                self.gui_timer.timeout.connect(self._check_gui_running)
                self.gui_timer.start(2000)

                self._show_notification(
                    "GUI Launched",
                    "Gattrose-NG GUI is starting..."
                )

            except Exception as e:
                print(f"[!] GUI launch error: {e}")
                self._show_notification(
                    "GUI Launch Failed",
                    f"Failed to launch GUI: {e}",
                    urgency="critical"
                )
        else:
            # GUI already running
            self._show_notification(
                "GUI Running",
                "GUI is already running"
            )

    def _hide_gui(self):
        """Hide/close the GUI"""
        if self.gui_process and self.gui_process.poll() is None:
            self.gui_process.terminate()
            try:
                self.gui_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.gui_process.kill()

            self.gui_process = None
            self.show_gui_action.setEnabled(True)
            self.hide_gui_action.setEnabled(False)

    def _open_web_ui(self):
        """Open Web UI in default browser"""
        import webbrowser
        web_url = "http://localhost:5555"

        # Check if web server is running
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5555))
        sock.close()

        if result == 0:
            # Web server is running, open browser
            print(f"[*] Opening Web UI at {web_url}")
            webbrowser.open(web_url)
            self._show_notification("Web UI", f"Opening {web_url}", "normal")
        else:
            # Web server not running
            msg = "Web UI server is not running.\nStart the orchestrator first."
            print(f"[!] {msg}")
            self._show_notification("Web UI Error", msg, "critical")

    def _check_gui_running(self):
        """Check if GUI is still running"""
        if self.gui_process and self.gui_process.poll() is not None:
            # GUI exited
            self.gui_process = None
            self.show_gui_action.setEnabled(True)
            self.hide_gui_action.setEnabled(False)
            if hasattr(self, 'gui_timer'):
                self.gui_timer.stop()

    def _on_tray_activated(self, reason):
        """Handle tray icon activation - disabled GUI launch"""
        # GUI is controlled separately, not from tray
        pass

    def _start_comprehensive_monitoring(self):
        """Start comprehensive system state monitoring"""
        self.state_timer = QTimer()
        self.state_timer.timeout.connect(self._check_all_states)
        self.state_timer.start(1000)  # Check every 1 second for responsiveness

        # Initial check
        self._check_all_states()

    def _check_all_states(self):
        """Check all system states and update menu"""
        # 1. Check GUI state
        gui_running = self._is_gui_running()
        self.system_state['gui_running'] = gui_running

        # 2. Check orchestrator state (from status file)
        orch_running = self._is_orchestrator_running()
        self.system_state['orchestrator_running'] = orch_running

        # 3. Check web server state
        web_running = self._is_web_server_running()
        self.system_state['web_server_running'] = web_running

        # 4. Check scanner state (from status file)
        scanner_running = self._is_scanner_running()
        self.system_state['scanner_running'] = scanner_running

        # 5. Get database stats
        self._update_database_stats()

        # Update menu based on states
        self._update_menu_from_state()

    def _is_gui_running(self):
        """Check if GUI is running"""
        # Method 1: Check if we have a tracked process
        if self.gui_process and self.gui_process.poll() is None:
            return True

        # Method 2: Check for running process by name
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'gattrose-ng.*main.py'],
                capture_output=True,
                text=True,
                timeout=1
            )
            return result.returncode == 0 and result.stdout.strip()
        except:
            return False

    def _is_orchestrator_running(self):
        """Check if orchestrator is running"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    status = json.load(f)
                    return status.get('orchestrator', {}).get('running', False)
        except:
            pass

        # Fallback: Check process
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'orchestrator'],
                capture_output=True,
                text=True,
                timeout=1
            )
            return result.returncode == 0
        except:
            return False

    def _is_web_server_running(self):
        """Check if web server is running on port 5555"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('127.0.0.1', 5555))
            sock.close()
            return result == 0
        except:
            return False

    def _is_scanner_running(self):
        """Check if scanner is running"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    status = json.load(f)
                    services = status.get('services', {})
                    scanner = services.get('scanner', {})
                    return scanner.get('running', False)
        except:
            pass
        return False

    def _update_database_stats(self):
        """Get quick stats from database"""
        try:
            # Quick check via sqlite3 (faster than SQLAlchemy for just counts)
            import sqlite3
            db_path = PROJECT_ROOT / 'data' / 'database' / 'gattrose.db'
            if db_path.exists():
                conn = sqlite3.connect(str(db_path), timeout=1)
                cursor = conn.cursor()

                # Get current scan counts
                cursor.execute("SELECT COUNT(*) FROM current_scan_networks")
                networks = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM current_scan_clients")
                clients = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM attack_queue WHERE status = 'pending'")
                queue_size = cursor.fetchone()[0]

                conn.close()

                self.system_state['networks_found'] = networks
                self.system_state['clients_found'] = clients
                self.system_state['attack_queue_size'] = queue_size
            else:
                self.system_state['networks_found'] = 0
                self.system_state['clients_found'] = 0
                self.system_state['attack_queue_size'] = 0
        except Exception as e:
            print(f"[!] Error getting database stats: {e}")

    def _update_menu_from_state(self):
        """Update all menu items based on current system state"""
        state = self.system_state

        # Update status indicators
        if state['gui_running']:
            self.gui_status_action.setText("✓ GUI: Running")
        else:
            self.gui_status_action.setText("○ GUI: Stopped")

        if state['web_server_running']:
            self.web_status_action.setText("✓ Web UI: Running (port 5555)")
        else:
            self.web_status_action.setText("○ Web UI: Not Running")

        if state['scanner_running']:
            self.scanner_status_action.setText("✓ Scanner: Active")
        else:
            self.scanner_status_action.setText("○ Scanner: Idle")

        # Update stats
        networks = state['networks_found']
        clients = state['clients_found']
        queue = state['attack_queue_size']
        self.stats_action.setText(f"📊 Networks: {networks} | Clients: {clients} | Queue: {queue}")

        # Update GUI controls visibility and state
        if state['gui_running']:
            self.show_gui_action.setVisible(False)
            self.hide_gui_action.setVisible(True)
            self.hide_gui_action.setEnabled(True)
        else:
            self.show_gui_action.setVisible(True)
            self.show_gui_action.setEnabled(True)
            self.hide_gui_action.setVisible(False)

        # Update orchestrator controls
        if state['orchestrator_running']:
            self.start_orch_action.setVisible(False)
            self.restart_orch_action.setVisible(True)
            self.restart_orch_action.setEnabled(True)
            self.stop_orch_action.setVisible(True)
            self.stop_orch_action.setEnabled(True)
            self.status_header.setText("Gattrose-NG: ✓ Running")
        else:
            self.start_orch_action.setVisible(True)
            self.start_orch_action.setEnabled(True)
            self.restart_orch_action.setVisible(False)
            self.stop_orch_action.setVisible(False)
            self.status_header.setText("Gattrose-NG: ○ Stopped")

        # Update web UI action tooltip
        if state['web_server_running']:
            self.web_ui_action.setToolTip("Open Web UI at http://localhost:5555")
        else:
            self.web_ui_action.setToolTip("Web server not running. Start orchestrator first.")

    def _show_notification(self, title, message, urgency="normal"):
        """Show desktop notification"""
        try:
            # Use D-Bus for KDE Plasma
            bus = QDBusConnection.sessionBus()
            if bus.isConnected():
                msg = QDBusMessage.createMethodCall(
                    "org.freedesktop.Notifications",
                    "/org/freedesktop/Notifications",
                    "org.freedesktop.Notifications",
                    "Notify"
                )

                urgency_level = {"low": 0, "normal": 1, "critical": 2}.get(urgency, 1)

                args = [
                    "Gattrose-NG",
                    0,
                    "network-wireless",
                    title,
                    message,
                    [],
                    {"urgency": urgency_level},
                    5000
                ]

                msg.setArguments(args)
                bus.call(msg)
                return
        except Exception as e:
            print(f"[!] D-Bus notification failed: {e}")

        # Fallback to Qt
        icon = QSystemTrayIcon.MessageIcon.Information
        if urgency == "critical":
            icon = QSystemTrayIcon.MessageIcon.Critical
        elif urgency == "warning":
            icon = QSystemTrayIcon.MessageIcon.Warning

        self.tray_icon.showMessage(title, message, icon, 5000)

    def _quit(self):
        """Quit the tray application only - orchestrator keeps running"""
        self.app.quit()

    def run(self):
        """Run the tray application"""
        self.tray_icon.show()

        # Show welcome notification
        self._show_notification(
            "Gattrose-NG Tray Started",
            "System tray is monitoring services",
            urgency="low"
        )

        # Try to auto-start orchestrator
        self._start_orchestrator()

        return self.app.exec()


def main():
    """Entry point for tray application"""
    print("[*] Starting Gattrose-NG System Tray...")

    # Import time for restart delay
    import time

    # IMPORTANT: Set this BEFORE creating QApplication
    # Required for QtWebEngineWidgets compatibility
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    app = GattroseTrayApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
