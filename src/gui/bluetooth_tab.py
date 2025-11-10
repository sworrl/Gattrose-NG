"""
Bluetooth Scanning and Attack Tab
Provides Bluetooth device discovery and security testing
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QGroupBox, QLineEdit
)
from PyQt6.QtCore import Qt


class BluetoothTab(QWidget):
    """Bluetooth scanning and attack interface"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()

        # Title
        title = QLabel("🔵 Bluetooth Scanner & Attack Suite")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Control panel
        control_group = QGroupBox("Controls")
        control_layout = QHBoxLayout()

        self.start_scan_btn = QPushButton("🔍 Start Bluetooth Scan")
        self.start_scan_btn.clicked.connect(self.start_bluetooth_scan)
        self.stop_scan_btn = QPushButton("⏹️ Stop Scan")
        self.stop_scan_btn.clicked.connect(self.stop_bluetooth_scan)
        self.stop_scan_btn.setEnabled(False)

        control_layout.addWidget(self.start_scan_btn)
        control_layout.addWidget(self.stop_scan_btn)
        control_layout.addStretch()

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Bluetooth devices tree
        devices_group = QGroupBox("Discovered Bluetooth Devices")
        devices_layout = QVBoxLayout()

        self.devices_tree = QTreeWidget()
        self.devices_tree.setHeaderLabels([
            "Device Name", "MAC Address", "Type", "RSSI", "Services"
        ])
        self.devices_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.devices_tree.customContextMenuRequested.connect(self.show_context_menu)

        devices_layout.addWidget(self.devices_tree)
        devices_group.setLayout(devices_layout)
        layout.addWidget(devices_group)

        # Attack panel
        attack_group = QGroupBox("Bluetooth Attacks")
        attack_layout = QVBoxLayout()

        attack_row1 = QHBoxLayout()
        self.bluejack_btn = QPushButton("📨 Bluejacking")
        self.bluejack_btn.setToolTip("Send anonymous messages to Bluetooth devices")
        self.bluejack_btn.clicked.connect(lambda: self.log("Bluejacking attack not yet implemented"))

        self.bluesnarfing_btn = QPushButton("🔓 Bluesnarfing")
        self.bluesnarfing_btn.setToolTip("Attempt to steal information from device")
        self.bluesnarfing_btn.clicked.connect(lambda: self.log("Bluesnarfing attack not yet implemented"))

        self.l2ping_btn = QPushButton("📡 L2Ping DoS")
        self.l2ping_btn.setToolTip("L2CAP ping flood attack")
        self.l2ping_btn.clicked.connect(lambda: self.log("L2Ping attack not yet implemented"))

        attack_row1.addWidget(self.bluejack_btn)
        attack_row1.addWidget(self.bluesnarfing_btn)
        attack_row1.addWidget(self.l2ping_btn)

        attack_layout.addLayout(attack_row1)
        attack_group.setLayout(attack_layout)
        layout.addWidget(attack_group)

        # Log area
        log_group = QGroupBox("Bluetooth Activity Log")
        log_layout = QVBoxLayout()

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)

        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.setLayout(layout)

        # Initial log
        self.log("Bluetooth tab initialized. Click 'Start Bluetooth Scan' to begin.")
        self.log("⚠️ Note: Bluetooth functionality requires appropriate hardware and permissions.")

    def log(self, message: str):
        """Add message to log area"""
        self.log_area.append(message)

    def start_bluetooth_scan(self):
        """Start Bluetooth device discovery"""
        self.log("[*] Starting Bluetooth scan...")

        self.start_scan_btn.setEnabled(False)
        self.stop_scan_btn.setEnabled(True)

        # Clear existing devices
        self.devices_tree.clear()

        # Start scanning thread
        import threading
        self.scanning = True
        self.scan_thread = threading.Thread(target=self.bluetooth_scan_worker, daemon=True)
        self.scan_thread.start()

    def bluetooth_scan_worker(self):
        """Worker thread for Bluetooth scanning"""
        import subprocess
        import re

        self.log("[*] Initializing Bluetooth adapter...")

        # Try different scanning methods
        scan_methods = [
            self.scan_with_bluetoothctl,
            self.scan_with_hcitool,
            self.scan_with_btmgmt
        ]

        for scan_method in scan_methods:
            if not self.scanning:
                break
            try:
                devices = scan_method()
                if devices:
                    self.log(f"[+] Found {len(devices)} devices")
                    for device in devices:
                        self.add_device_to_tree(device)
                    return
            except Exception as e:
                self.log(f"[!] {scan_method.__name__} failed: {e}")
                continue

        self.log("[!] No Bluetooth tools available. Install bluez or bluez-utils.")
        self.log("    Ubuntu/Debian: sudo apt-get install bluez bluez-utils")
        self.log("    Kali: Should be pre-installed")

    def scan_with_bluetoothctl(self):
        """Scan using bluetoothctl"""
        import subprocess
        import re
        from PyQt6.QtCore import QMetaObject, Qt

        self.log("[*] Scanning with bluetoothctl...")

        devices = []

        try:
            # Start bluetooth service
            subprocess.run(['sudo', 'systemctl', 'start', 'bluetooth'], capture_output=True, timeout=5)

            # Power on the adapter
            power_cmd = subprocess.Popen(
                ['bluetoothctl'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            power_cmd.communicate(input='power on\nscan on\nquit\n', timeout=2)

            # Wait a bit for scan to start
            import time
            time.sleep(3)

            # Get discovered devices
            result = subprocess.run(
                ['bluetoothctl', 'devices'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Parse output: "Device AA:BB:CC:DD:EE:FF DeviceName"
            for line in result.stdout.splitlines():
                match = re.match(r'Device\s+([0-9A-Fa-f:]{17})\s+(.*)', line)
                if match:
                    mac = match.group(1)
                    name = match.group(2).strip()

                    # Get additional info
                    info_result = subprocess.run(
                        ['bluetoothctl', 'info', mac],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )

                    # Parse device info
                    device_type = "Unknown"
                    rssi = "N/A"
                    services = []

                    for info_line in info_result.stdout.splitlines():
                        if 'Icon:' in info_line:
                            icon = info_line.split('Icon:')[1].strip()
                            if 'phone' in icon:
                                device_type = "Phone"
                            elif 'audio' in icon or 'headset' in icon:
                                device_type = "Headphones"
                            elif 'computer' in icon:
                                device_type = "Computer"
                            elif 'input' in icon:
                                device_type = "Input Device"
                        elif 'RSSI:' in info_line:
                            rssi = info_line.split('RSSI:')[1].strip() + " dBm"
                        elif 'UUID:' in info_line:
                            uuid_part = info_line.split('UUID:')[1].strip()
                            if '(' in uuid_part:
                                service = uuid_part.split('(')[1].rstrip(')')
                                services.append(service)

                    services_str = ', '.join(services[:3]) if services else "Unknown"

                    devices.append({
                        'name': name or "Unknown Device",
                        'mac': mac,
                        'type': device_type,
                        'rssi': rssi,
                        'services': services_str
                    })

            # Stop scanning
            stop_cmd = subprocess.Popen(
                ['bluetoothctl'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stop_cmd.communicate(input='scan off\nquit\n', timeout=2)

        except Exception as e:
            self.log(f"[!] bluetoothctl error: {e}")

        return devices

    def scan_with_hcitool(self):
        """Scan using hcitool"""
        import subprocess
        import re

        self.log("[*] Scanning with hcitool...")

        devices = []

        try:
            # Run hcitool scan
            result = subprocess.run(
                ['sudo', 'hcitool', 'scan'],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse output
            for line in result.stdout.splitlines():
                # Format: "AA:BB:CC:DD:EE:FF  Device Name"
                match = re.match(r'\s*([0-9A-Fa-f:]{17})\s+(.*)', line)
                if match:
                    mac = match.group(1)
                    name = match.group(2).strip()

                    devices.append({
                        'name': name or "Unknown Device",
                        'mac': mac,
                        'type': "Unknown",
                        'rssi': "N/A",
                        'services': "Unknown"
                    })

        except Exception as e:
            self.log(f"[!] hcitool error: {e}")

        return devices

    def scan_with_btmgmt(self):
        """Scan using btmgmt"""
        import subprocess
        import re

        self.log("[*] Scanning with btmgmt...")

        devices = []

        try:
            # Start scanning
            subprocess.run(['sudo', 'btmgmt', 'find'], capture_output=True, timeout=15)

            # Wait for scan
            import time
            time.sleep(10)

            # Get devices (this is a simplified approach)
            # btmgmt doesn't easily list devices, so we fallback to bluetoothctl
            return self.scan_with_bluetoothctl()

        except Exception as e:
            self.log(f"[!] btmgmt error: {e}")

        return devices

    def add_device_to_tree(self, device):
        """Add device to tree widget"""
        from PyQt6.QtCore import QMetaObject, Qt

        # Use QMetaObject.invokeMethod to safely update GUI from thread
        QMetaObject.invokeMethod(
            self,
            "_add_device_to_tree_impl",
            Qt.ConnectionType.QueuedConnection,
            device
        )

    def _add_device_to_tree_impl(self, device):
        """Implementation of add_device_to_tree (runs in GUI thread)"""
        item = QTreeWidgetItem([
            device['name'],
            device['mac'],
            device['type'],
            device['rssi'],
            device['services']
        ])
        self.devices_tree.addTopLevelItem(item)

    def stop_bluetooth_scan(self):
        """Stop Bluetooth device discovery"""
        self.log("[*] Stopping Bluetooth scan...")

        self.scanning = False

        self.start_scan_btn.setEnabled(True)
        self.stop_scan_btn.setEnabled(False)

    def add_example_devices(self):
        """Add example Bluetooth devices (placeholder)"""
        example_devices = [
            ("iPhone 13", "AA:BB:CC:DD:EE:FF", "Phone", "-45 dBm", "A2DP, AVRCP, HFP"),
            ("Galaxy Buds", "11:22:33:44:55:66", "Headphones", "-52 dBm", "A2DP, AVRCP"),
            ("MacBook Pro", "77:88:99:AA:BB:CC", "Computer", "-38 dBm", "PAN, A2DP"),
        ]

        for device in example_devices:
            item = QTreeWidgetItem(device)
            self.devices_tree.addTopLevelItem(item)

        self.log(f"[+] Found {len(example_devices)} Bluetooth devices (example data)")

    def show_context_menu(self, position):
        """Show context menu for selected device"""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction

        item = self.devices_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        pair_action = QAction("🔗 Pair Device", self)
        pair_action.triggered.connect(lambda: self.log(f"Pairing with {item.text(0)}..."))
        menu.addAction(pair_action)

        info_action = QAction("ℹ️ Device Info", self)
        info_action.triggered.connect(lambda: self.show_device_info(item))
        menu.addAction(info_action)

        menu.addSeparator()

        copy_mac_action = QAction("📋 Copy MAC", self)
        from PyQt6.QtWidgets import QApplication
        copy_mac_action.triggered.connect(lambda: QApplication.clipboard().setText(item.text(1)))
        menu.addAction(copy_mac_action)

        menu.exec(self.devices_tree.viewport().mapToGlobal(position))

    def show_device_info(self, item: QTreeWidgetItem):
        """Show detailed device information"""
        from PyQt6.QtWidgets import QMessageBox

        info = f"""
**Device Information**

Name: {item.text(0)}
MAC: {item.text(1)}
Type: {item.text(2)}
RSSI: {item.text(3)}
Services: {item.text(4)}

---
⚠️ Detailed device probing not yet implemented
        """

        QMessageBox.information(self, "Bluetooth Device Info", info)
