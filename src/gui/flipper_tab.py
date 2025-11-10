"""
Flipper Zero Integration Tab

Provides interface for connecting to and controlling Flipper Zero device
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTextEdit, QComboBox, QLineEdit, QMessageBox
)
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QFont
from pathlib import Path


class FlipperTab(QWidget):
    """Flipper Zero integration tab"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.flipper_service = None
        self.init_ui()

    def init_ui(self):
        """Initialize the Flipper Zero tab UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # ========== Connection Section ==========
        connection_group = QGroupBox("🔌 Connection")
        connection_layout = QVBoxLayout()

        # Status
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_label = QLabel("❌ Disconnected")
        self.status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        connection_layout.addLayout(status_layout)

        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.addItem("Auto-detect")
        self.port_combo.addItem("/dev/ttyACM0")
        self.port_combo.addItem("/dev/ttyACM1")
        self.port_combo.addItem("/dev/ttyUSB0")
        port_layout.addWidget(self.port_combo)

        self.refresh_ports_btn = QPushButton("🔄 Refresh")
        self.refresh_ports_btn.clicked.connect(self.on_refresh_ports)
        port_layout.addWidget(self.refresh_ports_btn)

        connection_layout.addLayout(port_layout)

        # Connect/Disconnect buttons
        button_layout = QHBoxLayout()
        self.connect_btn = QPushButton("🔗 Connect")
        self.connect_btn.clicked.connect(self.on_connect)
        self.connect_btn.setStyleSheet("QPushButton { background-color: #2a5a2a; color: white; padding: 8px; font-weight: bold; }")
        button_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("🔌 Disconnect")
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("QPushButton { background-color: #5a2a2a; color: white; padding: 8px; font-weight: bold; }")
        button_layout.addWidget(self.disconnect_btn)

        connection_layout.addLayout(button_layout)

        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)

        # ========== Device Info Section ==========
        device_info_group = QGroupBox("📱 Device Information")
        device_info_layout = QVBoxLayout()

        self.device_info_text = QTextEdit()
        self.device_info_text.setReadOnly(True)
        self.device_info_text.setMaximumHeight(150)
        self.device_info_text.setPlainText("No device connected")
        device_info_layout.addWidget(self.device_info_text)

        device_info_group.setLayout(device_info_layout)
        layout.addWidget(device_info_group)

        # ========== Command Console Section ==========
        console_group = QGroupBox("💻 Command Console")
        console_layout = QVBoxLayout()

        # Command input
        command_layout = QHBoxLayout()
        command_layout.addWidget(QLabel("Command:"))
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter Flipper command (e.g., device_info, led 0 0 255)")
        self.command_input.returnPressed.connect(self.on_send_command)
        command_layout.addWidget(self.command_input)

        self.send_btn = QPushButton("📤 Send")
        self.send_btn.clicked.connect(self.on_send_command)
        self.send_btn.setEnabled(False)
        command_layout.addWidget(self.send_btn)

        console_layout.addLayout(command_layout)

        # Command history/output
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Monospace", 9))
        self.console_output.setPlaceholderText("Command history will appear here...")
        console_layout.addWidget(self.console_output)

        console_group.setLayout(console_layout)
        layout.addWidget(console_group)

        # ========== Quick Actions Section ==========
        actions_group = QGroupBox("⚡ Quick Actions")
        actions_layout = QHBoxLayout()

        self.blink_btn = QPushButton("💡 Blink LED")
        self.blink_btn.clicked.connect(self.on_blink_led)
        self.blink_btn.setEnabled(False)
        actions_layout.addWidget(self.blink_btn)

        self.vibrate_btn = QPushButton("📳 Vibrate")
        self.vibrate_btn.clicked.connect(self.on_vibrate)
        self.vibrate_btn.setEnabled(False)
        actions_layout.addWidget(self.vibrate_btn)

        self.info_btn = QPushButton("ℹ️ Get Info")
        self.info_btn.clicked.connect(self.on_get_info)
        self.info_btn.setEnabled(False)
        actions_layout.addWidget(self.info_btn)

        actions_layout.addStretch()

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # ========== Status Bar ==========
        self.status_bar = QLabel("Ready to connect to Flipper Zero")
        self.status_bar.setStyleSheet("padding: 8px; background-color: #2a2a2a; border-radius: 4px;")
        layout.addWidget(self.status_bar)

        layout.addStretch()
        self.setLayout(layout)

    # ========== Event Handlers ==========

    def on_refresh_ports(self):
        """Refresh available serial ports"""
        if not self.flipper_service:
            self._initialize_service()

        ports = self.flipper_service.detect_flipper_devices()

        self.port_combo.clear()
        self.port_combo.addItem("Auto-detect")

        if ports:
            for port in ports:
                self.port_combo.addItem(port)
            self.log_to_console(f"Found {len(ports)} Flipper device(s)")
        else:
            self.log_to_console("No Flipper Zero devices found")

        # Add common ports
        self.port_combo.addItem("/dev/ttyACM0")
        self.port_combo.addItem("/dev/ttyACM1")
        self.port_combo.addItem("/dev/ttyUSB0")

    def on_connect(self):
        """Handle connect button click"""
        if not self.flipper_service:
            self._initialize_service()

        # Get selected port
        port_text = self.port_combo.currentText()
        port = None if port_text == "Auto-detect" else port_text

        self.log_to_console(f"Connecting to Flipper Zero{f' at {port}' if port else ''}...")
        self.status_bar.setText("Connecting...")

        # Attempt connection
        success = self.flipper_service.connect(port)

        if success:
            self.log_to_console("✓ Connected successfully!")
            self.status_bar.setText(f"Connected to {self.flipper_service.device.name}")
        else:
            self.log_to_console("✗ Connection failed")
            self.status_bar.setText("Connection failed")
            QMessageBox.critical(
                self,
                "Connection Failed",
                "Failed to connect to Flipper Zero.\n\n"
                "Make sure:\n"
                "• Flipper is powered on and connected via USB\n"
                "• You have permission to access serial ports\n"
                "• No other application is using the device"
            )

    def on_disconnect(self):
        """Handle disconnect button click"""
        if self.flipper_service:
            self.flipper_service.disconnect()
            self.log_to_console("Disconnected from Flipper Zero")
            self.status_bar.setText("Disconnected")

    def on_send_command(self):
        """Handle send command button"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to Flipper Zero first")
            return

        command = self.command_input.text().strip()
        if not command:
            return

        self.log_to_console(f"→ {command}")

        response = self.flipper_service.send_command(command)

        if response:
            self.log_to_console(f"← {response}")
        else:
            self.log_to_console("← (no response)")

        self.command_input.clear()

    def on_blink_led(self):
        """Blink Flipper LED"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        self.log_to_console("Blinking LED...")
        self.flipper_service.led_blink('blue', 2)

    def on_vibrate(self):
        """Vibrate Flipper"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        self.log_to_console("Vibrating...")
        self.flipper_service.vibrate(1)

    def on_get_info(self):
        """Get device info"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        self.log_to_console("Getting device info...")
        info = self.flipper_service.get_info()

        if info:
            self._update_device_info(info)
            self.log_to_console("✓ Device info retrieved")
        else:
            self.log_to_console("✗ Failed to get device info")

    # ========== Signal Handlers ==========

    @pyqtSlot(object)
    def on_flipper_connected(self, device):
        """Handle Flipper connected signal"""
        self.status_label.setText(f"✅ Connected: {device.name}")
        self.status_label.setStyleSheet("color: #44ff44; font-weight: bold;")

        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.blink_btn.setEnabled(True)
        self.vibrate_btn.setEnabled(True)
        self.info_btn.setEnabled(True)

        # Update device info
        info_text = f"""
Name: {device.name}
Model: {device.hardware_model}
UID: {device.hardware_uid}
Firmware: {device.firmware_origin} {device.firmware_version}
Port: {device.port}
"""
        self.device_info_text.setPlainText(info_text)

    @pyqtSlot()
    def on_flipper_disconnected(self):
        """Handle Flipper disconnected signal"""
        self.status_label.setText("❌ Disconnected")
        self.status_label.setStyleSheet("color: #ff4444; font-weight: bold;")

        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.blink_btn.setEnabled(False)
        self.vibrate_btn.setEnabled(False)
        self.info_btn.setEnabled(False)

        self.device_info_text.setPlainText("No device connected")

    @pyqtSlot(str)
    def on_flipper_status_message(self, message):
        """Handle status message from Flipper service"""
        self.log_to_console(f"[INFO] {message}")

    @pyqtSlot(str)
    def on_flipper_error(self, error):
        """Handle error from Flipper service"""
        self.log_to_console(f"[ERROR] {error}")
        self.status_bar.setText(f"Error: {error}")

    # ========== Helper Methods ==========

    def _initialize_service(self):
        """Initialize Flipper service"""
        from ..services.flipper_service import FlipperZeroService

        self.flipper_service = FlipperZeroService()

        # Connect signals
        self.flipper_service.connected.connect(self.on_flipper_connected)
        self.flipper_service.disconnected.connect(self.on_flipper_disconnected)
        self.flipper_service.status_message.connect(self.on_flipper_status_message)
        self.flipper_service.error_occurred.connect(self.on_flipper_error)

        self.log_to_console("Flipper service initialized")

    def log_to_console(self, message: str):
        """Add message to console output"""
        self.console_output.append(message)

    def _update_device_info(self, info: dict):
        """Update device info display"""
        info_lines = []
        for key, value in info.items():
            info_lines.append(f"{key}: {value}")

        self.device_info_text.setPlainText('\n'.join(info_lines))
