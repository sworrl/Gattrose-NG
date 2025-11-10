#!/usr/bin/env python3
"""
Unified Gattrose-NG Orchestrator Tray
Single tray icon with status badge overlay and hierarchical menu system
"""

import sys
import os
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QTextEdit, QGroupBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PyQt6.QtCore import QTimer, Qt, pyqtSignal

# Add project root to path
PROJECT_ROOT = Path('/opt/gattrose-ng')
sys.path.insert(0, str(PROJECT_ROOT))


class PhoneStatsWindow(QWidget):
    """Dedicated window for phone statistics and IMSI detection"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Phone & IMSI Catcher Detection")
        self.setMinimumSize(800, 600)
        self.init_ui()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(2000)  # Update every 2 seconds

    def init_ui(self):
        layout = QVBoxLayout()

        # Header
        header = QLabel("📱 Phone Statistics & Security Monitoring")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        # Phone status group
        phone_group = QGroupBox("Phone Status")
        phone_layout = QGridLayout()

        self.phone_connected_label = QLabel("❌ No Phone Connected")
        self.phone_model_label = QLabel("Model: Unknown")
        self.phone_battery_label = QLabel("Battery: --")
        self.gps_status_label = QLabel("GPS: No Fix")
        self.gps_accuracy_label = QLabel("Accuracy: --")
        self.gps_coords_label = QLabel("Coordinates: --")

        phone_layout.addWidget(self.phone_connected_label, 0, 0, 1, 2)
        phone_layout.addWidget(self.phone_model_label, 1, 0)
        phone_layout.addWidget(self.phone_battery_label, 1, 1)
        phone_layout.addWidget(self.gps_status_label, 2, 0)
        phone_layout.addWidget(self.gps_accuracy_label, 2, 1)
        phone_layout.addWidget(self.gps_coords_label, 3, 0, 1, 2)

        phone_group.setLayout(phone_layout)
        layout.addWidget(phone_group)

        # Cellular security group
        cellular_group = QGroupBox("Cellular Network Security")
        cellular_layout = QGridLayout()

        self.cell_tower_label = QLabel("Cell Tower ID: --")
        self.cell_mcc_mnc_label = QLabel("MCC/MNC: --")
        self.cell_network_label = QLabel("Network Type: --")
        self.cell_signal_label = QLabel("Signal: --")
        self.tower_changes_label = QLabel("Tower Changes: 0")

        cellular_layout.addWidget(self.cell_tower_label, 0, 0)
        cellular_layout.addWidget(self.cell_mcc_mnc_label, 0, 1)
        cellular_layout.addWidget(self.cell_network_label, 1, 0)
        cellular_layout.addWidget(self.cell_signal_label, 1, 1)
        cellular_layout.addWidget(self.tower_changes_label, 2, 0, 1, 2)

        cellular_group.setLayout(cellular_layout)
        layout.addWidget(cellular_group)

        # IMSI Catcher Alerts
        alerts_group = QGroupBox("🚨 IMSI Catcher Detection Alerts")
        alerts_layout = QVBoxLayout()

        self.alerts_table = QTableWidget(0, 4)
        self.alerts_table.setHorizontalHeaderLabels(["Time", "Severity", "Type", "Message"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alerts_table.setMaximumHeight(200)

        alerts_layout.addWidget(self.alerts_table)
        alerts_group.setLayout(alerts_layout)
        layout.addWidget(alerts_group)

        # Phone hardware stats
        hardware_group = QGroupBox("Hardware Statistics")
        hardware_layout = QGridLayout()

        self.cpu_freq_label = QLabel("CPU: --")
        self.cpu_temp_label = QLabel("Temp: --")
        self.ram_label = QLabel("RAM: --")
        self.storage_label = QLabel("Storage: --")

        hardware_layout.addWidget(self.cpu_freq_label, 0, 0)
        hardware_layout.addWidget(self.cpu_temp_label, 0, 1)
        hardware_layout.addWidget(self.ram_label, 1, 0)
        hardware_layout.addWidget(self.storage_label, 1, 1)

        hardware_group.setLayout(hardware_layout)
        layout.addWidget(hardware_group)

        # Actions
        actions_layout = QHBoxLayout()

        self.blacklist_btn = QPushButton("🚫 Blacklist Phone WiFi")
        self.blacklist_btn.clicked.connect(self.blacklist_phone_wifi)

        self.clear_alerts_btn = QPushButton("🗑️ Clear Alerts")
        self.clear_alerts_btn.clicked.connect(self.clear_alerts)

        actions_layout.addWidget(self.blacklist_btn)
        actions_layout.addWidget(self.clear_alerts_btn)
        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        self.setLayout(layout)

    def update_stats(self):
        """Update phone statistics from status files"""
        try:
            # Read phone tray status if available
            # For now, show placeholder data
            pass
        except Exception as e:
            pass

    def blacklist_phone_wifi(self):
        """Blacklist the phone's current WiFi network"""
        # Implementation would call the API
        pass

    def clear_alerts(self):
        """Clear IMSI catcher alerts"""
        self.alerts_table.setRowCount(0)


class AttackQueueWindow(QWidget):
    """Dedicated window for viewing and managing the attack queue"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Attack Queue Manager")
        self.setMinimumSize(900, 600)
        self.init_ui()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_queue)
        self.update_timer.start(2000)  # Update every 2 seconds

    def init_ui(self):
        layout = QVBoxLayout()

        # Header
        header = QLabel("⚔️ Attack Queue Manager")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        # Controls
        controls_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_queue)
        controls_layout.addWidget(self.refresh_btn)

        self.add_btn = QPushButton("➕ Add Network to Queue")
        self.add_btn.clicked.connect(self.add_to_queue)
        controls_layout.addWidget(self.add_btn)

        self.cancel_btn = QPushButton("❌ Cancel Selected")
        self.cancel_btn.clicked.connect(self.cancel_attack)
        controls_layout.addWidget(self.cancel_btn)

        self.clear_completed_btn = QPushButton("🗑️ Clear Completed")
        self.clear_completed_btn.clicked.connect(self.clear_completed)
        controls_layout.addWidget(self.clear_completed_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Queue table
        queue_group = QGroupBox("Attack Queue")
        queue_layout = QVBoxLayout()
        queue_group.setLayout(queue_layout)

        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(8)
        self.queue_table.setHorizontalHeaderLabels([
            "Status", "SSID", "BSSID", "Type", "Priority",
            "Added", "Started", "Result"
        ])
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.queue_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        queue_layout.addWidget(self.queue_table)

        layout.addWidget(queue_group)

        # Status summary
        summary_group = QGroupBox("Queue Summary")
        summary_layout = QGridLayout()
        summary_group.setLayout(summary_layout)

        self.pending_label = QLabel("Pending: 0")
        self.in_progress_label = QLabel("In Progress: 0")
        self.completed_label = QLabel("Completed: 0")
        self.failed_label = QLabel("Failed: 0")

        summary_layout.addWidget(self.pending_label, 0, 0)
        summary_layout.addWidget(self.in_progress_label, 0, 1)
        summary_layout.addWidget(self.completed_label, 0, 2)
        summary_layout.addWidget(self.failed_label, 0, 3)

        layout.addWidget(summary_group)

        self.setLayout(layout)

        # Load initial data
        self.refresh_queue()

    def refresh_queue(self):
        """Refresh queue from database"""
        try:
            from src.database.models import get_session, AttackQueue, Network

            session = get_session()
            try:
                queue_items = session.query(AttackQueue).order_by(
                    AttackQueue.priority.desc(),
                    AttackQueue.added_at.desc()
                ).all()

                self.queue_table.setRowCount(len(queue_items))

                # Count by status
                pending = in_progress = completed = failed = 0

                for row, item in enumerate(queue_items):
                    network = session.query(Network).filter_by(id=item.network_id).first()

                    # Status
                    status_item = QTableWidgetItem(item.status.upper())
                    if item.status == 'pending':
                        status_item.setBackground(QColor(255, 255, 200))
                        pending += 1
                    elif item.status == 'in_progress':
                        status_item.setBackground(QColor(200, 200, 255))
                        in_progress += 1
                    elif item.status == 'completed':
                        status_item.setBackground(QColor(200, 255, 200))
                        completed += 1
                    elif item.status == 'failed':
                        status_item.setBackground(QColor(255, 200, 200))
                        failed += 1
                    self.queue_table.setItem(row, 0, status_item)

                    # Network info
                    ssid = network.ssid or "(hidden)" if network else "Unknown"
                    bssid = network.bssid if network else "Unknown"

                    self.queue_table.setItem(row, 1, QTableWidgetItem(ssid))
                    self.queue_table.setItem(row, 2, QTableWidgetItem(bssid))
                    self.queue_table.setItem(row, 3, QTableWidgetItem(item.attack_type))
                    self.queue_table.setItem(row, 4, QTableWidgetItem(str(item.priority)))

                    # Timing
                    added = item.added_at.strftime("%H:%M:%S") if item.added_at else ""
                    started = item.started_at.strftime("%H:%M:%S") if item.started_at else ""
                    self.queue_table.setItem(row, 5, QTableWidgetItem(added))
                    self.queue_table.setItem(row, 6, QTableWidgetItem(started))

                    # Result
                    result = ""
                    if item.status == 'completed':
                        result = "✓ Success" if item.success else "Failed"
                    elif item.status == 'failed':
                        result = item.error_message or "Failed"
                    self.queue_table.setItem(row, 7, QTableWidgetItem(result))

                # Update summary
                self.pending_label.setText(f"Pending: {pending}")
                self.in_progress_label.setText(f"In Progress: {in_progress}")
                self.completed_label.setText(f"Completed: {completed}")
                self.failed_label.setText(f"Failed: {failed}")

            finally:
                session.close()
        except Exception as e:
            print(f"[!] Error refreshing attack queue: {e}")

    def add_to_queue(self):
        """Add a network to the attack queue"""
        # This would open a dialog to select a network
        # For now, just refresh
        pass

    def cancel_attack(self):
        """Cancel the selected attack"""
        current_row = self.queue_table.currentRow()
        if current_row < 0:
            return

        # Get the network BSSID from the table
        bssid = self.queue_table.item(current_row, 2).text()

        try:
            from src.database.models import get_session, AttackQueue, Network

            session = get_session()
            try:
                # Find the queue item
                network = session.query(Network).filter_by(bssid=bssid).first()
                if network:
                    queue_item = session.query(AttackQueue).filter_by(
                        network_id=network.id
                    ).first()

                    if queue_item and queue_item.status in ['pending', 'in_progress']:
                        session.delete(queue_item)
                        session.commit()
                        self.refresh_queue()
            finally:
                session.close()
        except Exception as e:
            print(f"[!] Error canceling attack: {e}")

    def clear_completed(self):
        """Clear completed and failed attacks from queue"""
        try:
            from src.database.models import get_session, AttackQueue

            session = get_session()
            try:
                # Delete completed and failed items
                session.query(AttackQueue).filter(
                    AttackQueue.status.in_(['completed', 'failed'])
                ).delete(synchronize_session=False)
                session.commit()
                self.refresh_queue()
            finally:
                session.close()
        except Exception as e:
            print(f"[!] Error clearing completed attacks: {e}")


class UnifiedOrchestratorTray:
    """
    Unified orchestrator tray icon with:
    - Fixed Gattrose-NG icon
    - Status badge overlay (idle/busy/ready/error/failed)
    - Hierarchical tree-style context menu
    - Phone icon appears dynamically when phone detected
    """

    # Status colors for badge
    STATUS_COLORS = {
        'idle': QColor(128, 128, 128),      # Gray
        'busy': QColor(0, 123, 255),        # Blue
        'ready': QColor(40, 167, 69),       # Green
        'error': QColor(255, 193, 7),       # Yellow/Warning
        'failed': QColor(220, 53, 69),      # Red
        'unknown': QColor(108, 117, 125)    # Dark gray
    }

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Prevent multiple instances
        self._check_single_instance()

        # Status tracking
        self.status_file = Path("/tmp/gattrose-status.json")
        self.events_file = Path("/tmp/gattrose-events.json")
        self.last_status = None
        self.current_state = 'unknown'  # idle, busy, ready, error, failed

        # Service states
        self.services = {}
        self.networks_count = 0
        self.clients_count = 0
        self.attack_queue_size = 0
        self.active_attacks = 0

        # Phone detection
        self.phone_connected = False
        self.phone_type = None  # 'android' or 'iphone'
        self.phone_info_cache = {}  # Cache device info to avoid constant ADB calls
        self.phone_info_cache_time = 0  # Last time we queried detailed info
        self.phone_icon = None
        self.phone_stats_window = None

        # Windows
        self.gui_process = None
        self.attack_queue_window = None

        # Initialize UI
        self._init_orchestrator_tray()
        self._init_phone_tray()

        # Start monitoring
        self._start_monitoring()

    def _check_single_instance(self):
        """Ensure only one instance"""
        import fcntl
        import psutil

        lock_path = '/tmp/gattrose-unified-tray.lock'

        # Check if lock file exists and is held by a dead process
        if os.path.exists(lock_path):
            try:
                # Try to read PID from lock file if it exists
                with open(lock_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        try:
                            old_pid = int(content)
                            # Check if process is still running
                            if not psutil.pid_exists(old_pid):
                                print(f"[*] Cleaning up stale lock file from dead process {old_pid}")
                                os.remove(lock_path)
                        except (ValueError, psutil.Error):
                            pass
            except (IOError, OSError):
                pass

        # Open or create lock file and write our PID
        self.lock_file = open(lock_path, 'w')
        try:
            fcntl.lockf(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Write our PID to the lock file for future cleanup
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
        except IOError:
            print("[!] Unified tray already running")
            sys.exit(0)

    def _init_orchestrator_tray(self):
        """Initialize main orchestrator tray icon"""
        icon = self._create_orchestrator_icon('unknown')
        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip("Gattrose-NG Orchestrator")

        # Build menu
        self.menu = QMenu()
        self._build_menu()

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def _init_phone_tray(self):
        """Initialize phone tray icon (hidden by default) - OLD STYLE MENU"""
        icon = self._create_phone_icon('gray')
        self.phone_icon = QSystemTrayIcon(icon, self.app)
        self.phone_icon.setToolTip("Phone GPS - Checking...")

        # Phone menu (OLD STYLE from phone_tray.py)
        phone_menu = QMenu()

        # Status section
        self.phone_status_action = QAction("Phone GPS Status")
        self.phone_status_action.setEnabled(False)
        phone_menu.addAction(self.phone_status_action)

        phone_menu.addSeparator()

        # GPS info
        self.gps_fix_action = QAction("GPS: No Fix")
        self.gps_fix_action.setEnabled(False)
        phone_menu.addAction(self.gps_fix_action)

        self.gps_coords_action = QAction("Coordinates: --")
        self.gps_coords_action.setEnabled(False)
        phone_menu.addAction(self.gps_coords_action)

        self.gps_accuracy_action = QAction("Accuracy: --")
        self.gps_accuracy_action.setEnabled(False)
        phone_menu.addAction(self.gps_accuracy_action)

        phone_menu.addSeparator()

        # Phone connection info
        self.phone_device_action = QAction("Phone: Disconnected")
        self.phone_device_action.setEnabled(False)
        phone_menu.addAction(self.phone_device_action)

        phone_menu.addSeparator()

        # Actions
        refresh_action = QAction("Refresh GPS")
        refresh_action.triggered.connect(self._refresh_gps_phone)
        phone_menu.addAction(refresh_action)

        reconnect_action = QAction("Reconnect Phone")
        reconnect_action.triggered.connect(self._reconnect_phone)
        phone_menu.addAction(reconnect_action)

        phone_menu.addSeparator()

        # Phone Tools submenu
        phone_tools_menu = phone_menu.addMenu("📱 Phone Tools")

        open_gui_action = QAction("Open GUI in Phone Browser", phone_tools_menu)
        open_gui_action.triggered.connect(self._open_gui_in_phone_browser)
        phone_tools_menu.addAction(open_gui_action)

        mirror_action = QAction("Mirror Phone Screen (scrcpy)", phone_tools_menu)
        mirror_action.triggered.connect(self._mirror_phone_screen)
        phone_tools_menu.addAction(mirror_action)

        phone_tools_menu.addSeparator()

        screenshot_action = QAction("Take Screenshot", phone_tools_menu)
        screenshot_action.triggered.connect(self._take_screenshot)
        phone_tools_menu.addAction(screenshot_action)

        shell_action = QAction("Open ADB Shell", phone_tools_menu)
        shell_action.triggered.connect(self._open_adb_shell)
        phone_tools_menu.addAction(shell_action)

        device_info_action = QAction("View Device Info", phone_tools_menu)
        device_info_action.triggered.connect(self._view_device_info)
        phone_tools_menu.addAction(device_info_action)

        phone_tools_menu.addSeparator()

        wifi_action = QAction("Toggle WiFi", phone_tools_menu)
        wifi_action.triggered.connect(self._toggle_phone_wifi)
        phone_tools_menu.addAction(wifi_action)

        airplane_action = QAction("Toggle Airplane Mode", phone_tools_menu)
        airplane_action.triggered.connect(self._toggle_airplane_mode)
        phone_tools_menu.addAction(airplane_action)

        phone_tools_menu.addSeparator()

        restart_adb_action = QAction("Restart ADB Server", phone_tools_menu)
        restart_adb_action.triggered.connect(self._restart_adb_server)
        phone_tools_menu.addAction(restart_adb_action)

        phone_menu.addSeparator()

        # Security Settings submenu
        security_menu = phone_menu.addMenu("🛡️ Security Settings")

        auto_blacklist_action = QAction("☐ Auto-blacklist Phone WiFi", security_menu)
        auto_blacklist_action.setCheckable(True)
        auto_blacklist_action.toggled.connect(self._toggle_auto_blacklist)
        security_menu.addAction(auto_blacklist_action)

        imsi_detection_action = QAction("☐ IMSI Catcher Detection", security_menu)
        imsi_detection_action.setCheckable(True)
        imsi_detection_action.setChecked(True)  # Default on
        imsi_detection_action.toggled.connect(self._toggle_imsi_detection)
        security_menu.addAction(imsi_detection_action)

        security_menu.addSeparator()

        view_alerts_action = QAction("View Security Alerts", security_menu)
        view_alerts_action.triggered.connect(self.show_phone_stats)
        security_menu.addAction(view_alerts_action)

        clear_alerts_action = QAction("Clear Alerts", security_menu)
        clear_alerts_action.triggered.connect(self._clear_security_alerts)
        security_menu.addAction(clear_alerts_action)

        phone_menu.addSeparator()

        # Quit
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit_app)
        phone_menu.addAction(quit_action)

        self.phone_icon.setContextMenu(phone_menu)
        # Don't show until phone detected

    def _create_orchestrator_icon(self, state: str) -> QIcon:
        """
        Create orchestrator icon with status badge overlay
        Base icon stays the same, badge indicates state
        """
        # Load base Gattrose-NG logo
        icon_path = PROJECT_ROOT / "assets" / "gattrose-ng.png"

        if icon_path.exists():
            base_pixmap = QPixmap(str(icon_path)).scaled(
                64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        else:
            # Fallback: Create simple icon
            base_pixmap = QPixmap(64, 64)
            base_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(base_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(100, 100, 100))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(4, 4, 56, 56)
            painter.end()

        # Add status badge in bottom-right corner
        painter = QPainter(base_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Badge circle
        badge_color = self.STATUS_COLORS.get(state, self.STATUS_COLORS['unknown'])
        painter.setBrush(badge_color)
        painter.setPen(QColor(255, 255, 255))  # White border
        painter.drawEllipse(44, 44, 18, 18)

        # Badge icon/text based on state
        painter.setPen(QColor(255, 255, 255))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        state_symbols = {
            'idle': '○',
            'busy': '●',
            'ready': '✓',
            'error': '!',
            'failed': '✗',
            'unknown': '?'
        }

        symbol = state_symbols.get(state, '?')
        painter.drawText(47, 58, symbol)

        painter.end()

        return QIcon(base_pixmap)

    def _create_phone_icon(self, status: str) -> QIcon:
        """Create a phone icon with status color (old style with GPS waves)

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

    def _build_menu(self):
        """Build hierarchical tree-style context menu"""
        self.menu.clear()

        # ═══ Header ═══
        header = QAction("🔷 Gattrose-NG Orchestrator", self.menu)
        header.setEnabled(False)
        font = header.font()
        font.setBold(True)
        font.setPointSize(11)
        header.setFont(font)
        self.menu.addAction(header)

        # Status line
        status_text = self._get_status_summary()
        status_action = QAction(status_text, self.menu)
        status_action.setEnabled(False)
        self.menu.addAction(status_action)

        self.menu.addSeparator()

        # ═══ Quick Actions ═══
        quick_menu = QMenu("⚡ Quick Actions", self.menu)

        launch_gui = QAction("🖥️ Launch GUI", quick_menu)
        launch_gui.triggered.connect(self.launch_gui)
        quick_menu.addAction(launch_gui)

        show_queue = QAction("⚔️ Attack Queue Manager", quick_menu)
        show_queue.triggered.connect(self.show_attack_queue)
        quick_menu.addAction(show_queue)

        quick_menu.addSeparator()

        start_scan = QAction("📡 Start Scanning", quick_menu)
        start_scan.triggered.connect(self.start_scanning)
        quick_menu.addAction(start_scan)

        stop_scan = QAction("⏸️ Stop Scanning", quick_menu)
        stop_scan.triggered.connect(self.stop_scanning)
        quick_menu.addAction(stop_scan)

        self.menu.addMenu(quick_menu)

        # ═══ Services Tree ═══
        services_menu = QMenu("🔧 Services", self.menu)

        # Core services submenu
        core_menu = QMenu("Core Services", services_menu)
        self._add_service_action(core_menu, "database", "Database")
        self._add_service_action(core_menu, "gps", "GPS Service")
        self._add_service_action(core_menu, "scanner", "WiFi Scanner")
        self._add_service_action(core_menu, "upsert", "Database Upsert")
        self._add_service_action(core_menu, "triangulation", "Triangulation")
        services_menu.addMenu(core_menu)

        # Attack services submenu
        attack_menu = QMenu("Attack Services", services_menu)
        self._add_service_action(attack_menu, "attack_queue", "Attack Queue")
        self._add_service_action(attack_menu, "wps_cracking", "WPS Cracking")
        self._add_service_action(attack_menu, "wpa_crack", "WPA Cracking")
        self._add_service_action(attack_menu, "wep_crack", "WEP Cracking")
        self._add_service_action(attack_menu, "handshake", "Handshake Capture")
        self._add_service_action(attack_menu, "deauth", "Deauth Service")
        services_menu.addMenu(attack_menu)

        self.menu.addMenu(services_menu)

        # ═══ Statistics ═══
        stats_menu = QMenu("📊 Statistics", self.menu)

        networks_action = QAction(f"Networks: {self.networks_count}", stats_menu)
        networks_action.setEnabled(False)
        stats_menu.addAction(networks_action)

        clients_action = QAction(f"Clients: {self.clients_count}", stats_menu)
        clients_action.setEnabled(False)
        stats_menu.addAction(clients_action)

        queue_action = QAction(f"Attack Queue: {self.attack_queue_size}", stats_menu)
        queue_action.setEnabled(False)
        stats_menu.addAction(queue_action)

        active_action = QAction(f"Active Attacks: {self.active_attacks}", stats_menu)
        active_action.setEnabled(False)
        stats_menu.addAction(active_action)

        self.menu.addMenu(stats_menu)

        # ═══ Phone Settings (subset) ═══
        phone_menu = QMenu("📱 Phone Settings", self.menu)

        if self.phone_connected:
            show_phone_action = QAction("Show Phone Stats Window", phone_menu)
            show_phone_action.triggered.connect(self.show_phone_stats)
            phone_menu.addAction(show_phone_action)

            phone_menu.addSeparator()

            gps_action = QAction("GPS Enabled", phone_menu)
            gps_action.setCheckable(True)
            gps_action.setChecked(True)
            phone_menu.addAction(gps_action)

            imsi_action = QAction("IMSI Detection Enabled", phone_menu)
            imsi_action.setCheckable(True)
            imsi_action.setChecked(True)
            phone_menu.addAction(imsi_action)
        else:
            no_phone_action = QAction("No Phone Connected", phone_menu)
            no_phone_action.setEnabled(False)
            phone_menu.addAction(no_phone_action)

        self.menu.addMenu(phone_menu)

        self.menu.addSeparator()

        # ═══ System ═══
        restart_action = QAction("🔄 Restart Orchestrator", self.menu)
        restart_action.triggered.connect(self.restart_orchestrator)
        self.menu.addAction(restart_action)

        logs_action = QAction("📋 View Logs", self.menu)
        logs_action.triggered.connect(self.view_logs)
        self.menu.addAction(logs_action)

        self.menu.addSeparator()

        # ═══ Exit ═══
        quit_action = QAction("❌ Quit", self.menu)
        quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(quit_action)

    def _add_service_action(self, menu: QMenu, service_key: str, service_name: str):
        """Add a service control action to menu"""
        service = self.services.get(service_key, {})
        running = service.get('running', False)

        status_symbol = "✓" if running else "✗"
        action = QAction(f"{status_symbol} {service_name}", menu)

        # Submenu for service controls
        service_menu = QMenu(menu)

        start_action = QAction("▶️ Start", service_menu)
        start_action.triggered.connect(lambda: self.start_service(service_key))
        service_menu.addAction(start_action)

        stop_action = QAction("⏹️ Stop", service_menu)
        stop_action.triggered.connect(lambda: self.stop_service(service_key))
        service_menu.addAction(stop_action)

        restart_action = QAction("🔄 Restart", service_menu)
        restart_action.triggered.connect(lambda: self.restart_service(service_key))
        service_menu.addAction(restart_action)

        action.setMenu(service_menu)
        menu.addAction(action)

    def _get_status_summary(self) -> str:
        """Get one-line status summary"""
        return f"State: {self.current_state.upper()} | Networks: {self.networks_count} | Queue: {self.attack_queue_size}"

    def _start_monitoring(self):
        """Start all monitoring timers"""
        # Status file monitoring
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # 2 seconds

        # Phone detection
        self.phone_timer = QTimer()
        self.phone_timer.timeout.connect(self.check_phone_connection)
        self.phone_timer.start(5000)  # 5 seconds

        # Menu rebuild timer
        self.menu_timer = QTimer()
        self.menu_timer.timeout.connect(self._build_menu)
        self.menu_timer.start(10000)  # 10 seconds

    def update_status(self):
        """Update status from orchestrator"""
        try:
            if not self.status_file.exists():
                return

            with open(self.status_file, 'r') as f:
                status = json.load(f)

            self.services = status.get('services', {})

            # Extract key metrics
            upsert = self.services.get('upsert', {}).get('metadata', {})
            self.networks_count = upsert.get('networks_count', 0)
            self.clients_count = upsert.get('clients_count', 0)

            queue = self.services.get('attack_queue', {}).get('metadata', {})
            self.attack_queue_size = queue.get('queued', 0)
            self.active_attacks = queue.get('running', 0)

            # Fallback: Query database directly if status file doesn't have queue data
            if self.attack_queue_size == 0 and self.active_attacks == 0:
                try:
                    from src.database.models import get_session, AttackQueue
                    session = get_session()
                    try:
                        self.attack_queue_size = session.query(AttackQueue).filter_by(status='pending').count()
                        self.active_attacks = session.query(AttackQueue).filter_by(status='in_progress').count()
                    finally:
                        session.close()
                except:
                    pass

            # Determine state
            self.current_state = self._calculate_state()

            # Update icon
            icon = self._create_orchestrator_icon(self.current_state)
            self.tray_icon.setIcon(icon)

            # Update tooltip with verbose status
            tooltip = f"Gattrose-NG: {self.current_state.upper()}\n"
            tooltip += f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"

            # Scanner status
            scanner = self.services.get('scanner', {})
            if scanner.get('running'):
                interface = scanner.get('metadata', {}).get('interface', 'unknown')
                tooltip += f"📡 Scanner: ACTIVE ({interface})\n"
            else:
                tooltip += f"📡 Scanner: STOPPED\n"

            # Networks/Clients
            tooltip += f"   └─ Found: {self.networks_count} networks, {self.clients_count} clients\n"

            # Current attack status
            attack = status.get('attack', {})
            if attack.get('in_progress'):
                target_ssid = attack.get('target_ssid') or '(hidden)'
                target_bssid = attack.get('target_bssid', 'unknown')
                attack_type = attack.get('type', 'unknown')
                tooltip += f"\n⚔️ ACTIVE ATTACK:\n"
                tooltip += f"   Type: {attack_type.upper()}\n"
                tooltip += f"   Target: {target_ssid}\n"
                tooltip += f"   BSSID: {target_bssid}\n"

            # Attack queue status
            tooltip += f"\n📋 Attack Queue:\n"
            tooltip += f"   Queued: {self.attack_queue_size}\n"
            tooltip += f"   Running: {self.active_attacks}\n"
            queue_data = status.get('queue', {})
            tooltip += f"   Completed: {queue_data.get('completed', 0)}\n"
            tooltip += f"   Failed: {queue_data.get('failed', 0)}\n"

            # WPS Cracking status
            wps = self.services.get('wps_cracking', {})
            if wps.get('running'):
                wps_meta = wps.get('metadata', {})
                queue_size = wps_meta.get('queue_size', 0)
                cracked = wps_meta.get('total_cracked', 0)
                tooltip += f"\n🔓 WPS Cracking:\n"
                tooltip += f"   Queue: {queue_size}\n"
                tooltip += f"   Cracked: {cracked}\n"

            # GPS status
            gps = self.services.get('gps', {})
            if gps.get('running'):
                gps_meta = gps.get('metadata', {})
                if gps_meta.get('has_location'):
                    source = gps_meta.get('source', 'unknown')
                    accuracy = gps_meta.get('accuracy', 0)
                    tooltip += f"\n📍 GPS: {source.upper()} ({accuracy:.1f}m)\n"

            self.tray_icon.setToolTip(tooltip)

        except Exception as e:
            pass

    def _calculate_state(self) -> str:
        """Calculate overall state from services"""
        # Check for failures
        for service in self.services.values():
            if service.get('status') == 'error':
                return 'error'

        # Check if actively attacking
        if self.active_attacks > 0:
            return 'busy'

        # Check if scanner running and ready
        scanner = self.services.get('scanner', {})
        if scanner.get('running'):
            if self.attack_queue_size > 0:
                return 'ready'
            else:
                return 'idle'

        # Default
        return 'idle'

    def check_phone_connection(self):
        """Check if phone is connected and update phone icon accordingly"""
        try:
            # First check for iPhone (fast, doesn't spawn heavy processes)
            iphone_result = subprocess.run(['idevice_id', '-l'],
                                         capture_output=True, text=True, timeout=1)
            iphone_devices = [line.strip() for line in iphone_result.stdout.split('\n') if line.strip()]

            # Check for Android (only if no iPhone found to avoid unnecessary ADB polling)
            android_devices = []
            if not iphone_devices:
                try:
                    result = subprocess.run(['adb', 'devices'],
                                          capture_output=True, text=True, timeout=1)
                    android_devices = [line for line in result.stdout.split('\n')
                                     if '\tdevice' in line]
                except:
                    android_devices = []
            else:
                # iPhone detected, kill ADB server to save CPU
                try:
                    subprocess.run(['adb', 'kill-server'], capture_output=True, timeout=1)
                except:
                    pass

            phone_now_connected = len(iphone_devices) > 0 or len(android_devices) > 0
            phone_type = 'iphone' if iphone_devices else 'android' if android_devices else None

            if phone_now_connected and not self.phone_connected:
                # Phone just connected - show icon and cache info
                device_id = (iphone_devices[0] if iphone_devices else
                           android_devices[0].split('\t')[0] if android_devices else 'unknown')

                self.phone_icon.show()
                self.phone_connected = True
                self.phone_type = phone_type

                # Get and cache phone model (only once on connect)
                if phone_type == 'android':
                    try:
                        model_result = subprocess.run(['adb', 'shell', 'getprop ro.product.model'],
                                                     capture_output=True, text=True, timeout=1)
                        phone_model = model_result.stdout.strip() or 'Android Phone'
                    except:
                        phone_model = 'Android Phone'
                elif phone_type == 'iphone':
                    try:
                        info_result = subprocess.run(['ideviceinfo', '-k', 'DeviceName'],
                                                   capture_output=True, text=True, timeout=1)
                        phone_model = info_result.stdout.strip() or 'iPhone'
                    except:
                        phone_model = 'iPhone'
                else:
                    phone_model = 'Unknown'

                self.phone_info_cache = {
                    'device_id': device_id,
                    'model': phone_model,
                    'type': phone_type
                }

                # Simple tooltip - no intensive queries
                tooltip = f"📱 {phone_type.title()} Connected\n"
                tooltip += f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                tooltip += f"Model: {phone_model}\n"
                tooltip += f"Device ID: {device_id[:16]}...\n\n"
                tooltip += f"GPS: Check status window for details"
                self.phone_icon.setToolTip(tooltip)

                # Update icon to green
                icon = self._create_phone_icon('green')
                self.phone_icon.setIcon(icon)

                print(f"[+] {phone_type.title()} detected ({phone_model}) - showing icon")

            elif not phone_now_connected and self.phone_connected:
                # Phone disconnected - hide icon and clear cache
                self.phone_icon.hide()
                self.phone_connected = False
                self.phone_type = None
                self.phone_info_cache = {}

                # Kill ADB to save CPU if no Android device
                try:
                    subprocess.run(['adb', 'kill-server'], capture_output=True, timeout=1)
                except:
                    pass

                print("[-] Phone disconnected - hiding icon")

            elif phone_now_connected and self.phone_connected:
                # Phone still connected - use cached info for tooltip (NO INTENSIVE QUERIES)
                cached_info = self.phone_info_cache
                device_id = cached_info.get('device_id', 'unknown')
                model = cached_info.get('model', 'Unknown')
                ptype = cached_info.get('type', 'unknown')
                # Simple tooltip using cached info (NO ADB QUERIES!)
                tooltip = f"📱 {ptype.title()} Connected\n"
                tooltip += f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                tooltip += f"Model: {model}\n"
                tooltip += f"Device ID: {device_id[:16]}...\n\n"
                tooltip += f"💡 Right-click phone icon for actions\n"
                tooltip += f"📊 Open Phone Stats window for details"

                self.phone_icon.setToolTip(tooltip)

        except Exception as e:
            print(f"[!] Error checking phone connection: {e}")

    def _decimal_to_dms(self, lat: float, lon: float) -> str:
        """Convert decimal degrees to DMS (Degrees, Minutes, Seconds) format"""
        def dd_to_dms(dd: float, is_latitude: bool) -> str:
            direction = ('N' if dd >= 0 else 'S') if is_latitude else ('E' if dd >= 0 else 'W')
            dd = abs(dd)
            degrees = int(dd)
            minutes = int((dd - degrees) * 60)
            seconds = (dd - degrees - minutes/60) * 3600
            return f"{degrees}°{minutes}'{seconds:.2f}\"{direction}"

        return f"{dd_to_dms(lat, True)}, {dd_to_dms(lon, False)}"

    def show_phone_stats(self):
        """Show phone statistics window"""
        if self.phone_stats_window is None:
            self.phone_stats_window = PhoneStatsWindow()

        self.phone_stats_window.show()
        self.phone_stats_window.raise_()
        self.phone_stats_window.activateWindow()

    def show_attack_queue(self):
        """Show attack queue management window"""
        if self.attack_queue_window is None:
            self.attack_queue_window = AttackQueueWindow()

        self.attack_queue_window.show()
        self.attack_queue_window.raise_()
        self.attack_queue_window.activateWindow()

    # ═══ Action Handlers ═══

    def launch_gui(self):
        """Launch the main GUI"""
        try:
            # Get XAUTHORITY dynamically
            xauth_result = subprocess.run(['ls', '/run/user/1000/xauth_*'],
                                        capture_output=True, text=True, timeout=2)
            xauth = xauth_result.stdout.strip().split('\n')[0] if xauth_result.returncode == 0 else ''

            # Build command with env
            cmd = ['sudo', '-u', 'eurrl', 'env']
            cmd.append('XDG_RUNTIME_DIR=/run/user/1000')
            cmd.append('DISPLAY=:1')
            cmd.append('WAYLAND_DISPLAY=wayland-0')
            if xauth:
                cmd.append(f'XAUTHORITY={xauth}')
            cmd.append('DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus')
            cmd.append('/opt/gattrose-ng/bin/gattrose-gui.sh')

            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[+] GUI launched")
        except Exception as e:
            print(f"[!] Failed to launch GUI: {e}")

    def start_scanning(self):
        """Start WiFi scanning"""
        try:
            # Enable 24/7 scan mode in config
            from src.utils.config_db import DBConfig
            config = DBConfig()
            config.set('service.scan_24_7', True)

            # Restart orchestrator to apply config
            print("[*] Enabling 24/7 scan mode and restarting orchestrator...")
            subprocess.run(['sudo', 'systemctl', 'restart', 'gattrose-orchestrator.service'],
                         timeout=5)
            print("[+] Scan mode enabled - orchestrator restarting")
        except Exception as e:
            print(f"[!] Failed to start scanning: {e}")

    def stop_scanning(self):
        """Stop WiFi scanning"""
        try:
            # Disable 24/7 scan mode in config
            from src.utils.config_db import DBConfig
            config = DBConfig()
            config.set('service.scan_24_7', False)

            # Restart orchestrator to apply config
            print("[*] Disabling 24/7 scan mode and restarting orchestrator...")
            subprocess.run(['sudo', 'systemctl', 'restart', 'gattrose-orchestrator.service'],
                         timeout=5)
            print("[+] Scan mode disabled - orchestrator restarting")
        except Exception as e:
            print(f"[!] Failed to stop scanning: {e}")

    def start_service(self, service_key: str):
        """Start a specific service"""
        print(f"[*] Starting service: {service_key}")
        # Would call orchestrator API

    def stop_service(self, service_key: str):
        """Stop a specific service"""
        print(f"[*] Stopping service: {service_key}")
        # Would call orchestrator API

    def restart_service(self, service_key: str):
        """Restart a specific service"""
        print(f"[*] Restarting service: {service_key}")
        # Would call orchestrator API

    def restart_orchestrator(self):
        """Restart the orchestrator service"""
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', 'gattrose-orchestrator.service'])
        except Exception as e:
            print(f"[!] Failed to restart orchestrator: {e}")

    def view_logs(self):
        """View orchestrator logs"""
        try:
            subprocess.Popen(['konsole', '-e', 'sudo', 'journalctl', '-u',
                            'gattrose-orchestrator.service', '-f'])
        except Exception as e:
            print(f"[!] Failed to open logs: {e}")

    # ═══ Phone Action Handlers ═══

    def _refresh_gps_phone(self):
        """Refresh GPS data from phone"""
        try:
            print("[*] Refreshing GPS data from phone...")
            # Trigger GPS refresh via orchestrator API or direct call
            # For now, just force a check
            self.check_phone_connection()
        except Exception as e:
            print(f"[!] Failed to refresh GPS: {e}")

    def _reconnect_phone(self):
        """Reconnect to phone"""
        try:
            print("[*] Reconnecting phone...")
            # Restart ADB server
            subprocess.run(['adb', 'kill-server'], timeout=2)
            subprocess.run(['adb', 'start-server'], timeout=5)
            # Force phone detection check
            self.check_phone_connection()
        except Exception as e:
            print(f"[!] Failed to reconnect phone: {e}")

    def _open_gui_in_phone_browser(self):
        """Open GUI in phone's browser"""
        try:
            # Get the GUI URL (assuming it's running on localhost)
            gui_url = "http://192.168.1.1:5000"  # Adjust based on your setup
            subprocess.run(['adb', 'shell', 'am', 'start', '-a', 'android.intent.action.VIEW',
                          '-d', gui_url], timeout=5)
        except Exception as e:
            print(f"[!] Failed to open GUI in phone browser: {e}")

    def _mirror_phone_screen(self):
        """Mirror phone screen using scrcpy"""
        try:
            subprocess.Popen(['scrcpy'])
        except Exception as e:
            print(f"[!] Failed to mirror phone screen: {e}")

    def _take_screenshot(self):
        """Take screenshot from phone"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/tmp/phone_screenshot_{timestamp}.png"
            subprocess.run(['adb', 'exec-out', 'screencap', '-p'],
                         stdout=open(screenshot_path, 'wb'), timeout=10)
            print(f"[+] Screenshot saved to {screenshot_path}")
        except Exception as e:
            print(f"[!] Failed to take screenshot: {e}")

    def _open_adb_shell(self):
        """Open ADB shell in terminal"""
        try:
            subprocess.Popen(['konsole', '-e', 'adb', 'shell'])
        except Exception as e:
            print(f"[!] Failed to open ADB shell: {e}")

    def _view_device_info(self):
        """View phone device info"""
        try:
            subprocess.Popen(['konsole', '-e', 'bash', '-c',
                            'echo "=== Device Info ===" && '
                            'adb shell getprop | grep "ro.product" && '
                            'echo "" && echo "=== Battery Info ===" && '
                            'adb shell dumpsys battery && '
                            'read -p "Press Enter to close..."'])
        except Exception as e:
            print(f"[!] Failed to view device info: {e}")

    def _toggle_phone_wifi(self):
        """Toggle WiFi on phone"""
        try:
            # Check current state
            result = subprocess.run(['adb', 'shell', 'settings', 'get', 'global', 'wifi_on'],
                                  capture_output=True, text=True, timeout=5)
            current_state = result.stdout.strip()

            # Toggle
            new_state = '0' if current_state == '1' else '1'
            subprocess.run(['adb', 'shell', 'svc', 'wifi', 'enable' if new_state == '1' else 'disable'],
                         timeout=5)
            print(f"[+] Phone WiFi {'enabled' if new_state == '1' else 'disabled'}")
        except Exception as e:
            print(f"[!] Failed to toggle WiFi: {e}")

    def _toggle_airplane_mode(self):
        """Toggle airplane mode on phone"""
        try:
            # Check current state
            result = subprocess.run(['adb', 'shell', 'settings', 'get', 'global', 'airplane_mode_on'],
                                  capture_output=True, text=True, timeout=5)
            current_state = result.stdout.strip()

            # Toggle
            new_state = '0' if current_state == '1' else '1'
            subprocess.run(['adb', 'shell', 'settings', 'put', 'global', 'airplane_mode_on', new_state],
                         timeout=5)
            # Broadcast the change
            subprocess.run(['adb', 'shell', 'am', 'broadcast', '-a', 'android.intent.action.AIRPLANE_MODE'],
                         timeout=5)
            print(f"[+] Airplane mode {'enabled' if new_state == '1' else 'disabled'}")
        except Exception as e:
            print(f"[!] Failed to toggle airplane mode: {e}")

    def _restart_adb_server(self):
        """Restart ADB server"""
        try:
            print("[*] Restarting ADB server...")
            subprocess.run(['adb', 'kill-server'], timeout=2)
            subprocess.run(['adb', 'start-server'], timeout=5)
            print("[+] ADB server restarted")
            self.check_phone_connection()
        except Exception as e:
            print(f"[!] Failed to restart ADB server: {e}")

    def _toggle_auto_blacklist(self, checked: bool):
        """Toggle auto-blacklist phone WiFi feature"""
        # This would set a flag in the database or config
        print(f"[*] Auto-blacklist phone WiFi: {'enabled' if checked else 'disabled'}")

    def _toggle_imsi_detection(self, checked: bool):
        """Toggle IMSI catcher detection"""
        # This would set a flag in the database or config
        print(f"[*] IMSI catcher detection: {'enabled' if checked else 'disabled'}")

    def _clear_security_alerts(self):
        """Clear security alerts"""
        print("[*] Clearing security alerts...")
        if self.phone_stats_window:
            self.phone_stats_window.clear_alerts()

    def quit_app(self):
        """Quit the tray application"""
        self.app.quit()

    def run(self):
        """Run the application"""
        print("[+] Unified Gattrose-NG Orchestrator Tray started")
        print("[i] Phone icon will appear when device is detected")
        sys.exit(self.app.exec())


def main():
    tray = UnifiedOrchestratorTray()
    tray.run()


if __name__ == "__main__":
    main()
