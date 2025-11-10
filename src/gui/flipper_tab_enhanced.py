"""
Enhanced Flipper Zero Integration Tab

Comprehensive UI for controlling all Flipper Zero capabilities:
- SubGHz radio TX/RX
- IR transmit/receive
- GPIO control
- RFID/NFC operations
- LED & vibration control
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTextEdit, QComboBox, QLineEdit, QMessageBox,
    QTabWidget, QSpinBox, QSlider, QCheckBox, QListWidget
)
from PyQt6.QtCore import pyqtSlot, Qt
from PyQt6.QtGui import QFont
from pathlib import Path


class FlipperTab(QWidget):
    """Enhanced Flipper Zero integration tab"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.flipper_service = None
        self.init_ui()

    def init_ui(self):
        """Initialize the enhanced Flipper Zero tab UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # ========== Connection Section (Always Visible) ==========
        connection_group = QGroupBox("🔌 Connection")
        connection_layout = QHBoxLayout()

        # Status
        self.status_label = QLabel("❌ Disconnected")
        self.status_label.setStyleSheet("color: #ff4444; font-weight: bold; padding: 5px;")
        connection_layout.addWidget(self.status_label)

        # Port selection
        connection_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.addItem("Auto-detect")
        self.port_combo.setMaximumWidth(150)
        connection_layout.addWidget(self.port_combo)

        self.refresh_ports_btn = QPushButton("🔄")
        self.refresh_ports_btn.clicked.connect(self.on_refresh_ports)
        self.refresh_ports_btn.setMaximumWidth(40)
        connection_layout.addWidget(self.refresh_ports_btn)

        # Connect/Disconnect buttons
        self.connect_btn = QPushButton("🔗 Connect")
        self.connect_btn.clicked.connect(self.on_connect)
        self.connect_btn.setStyleSheet("QPushButton { background-color: #2a5a2a; color: white; padding: 6px; font-weight: bold; }")
        connection_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("🔌 Disconnect")
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("QPushButton { background-color: #5a2a2a; color: white; padding: 6px; font-weight: bold; }")
        connection_layout.addWidget(self.disconnect_btn)

        connection_layout.addStretch()
        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)

        # ========== Tabbed Interface for Features ==========
        self.feature_tabs = QTabWidget()

        # Tab 1: SubGHz Radio
        self.feature_tabs.addTab(self._create_subghz_tab(), "📡 SubGHz")

        # Tab 2: IR Control
        self.feature_tabs.addTab(self._create_ir_tab(), "🔴 IR")

        # Tab 3: GPIO
        self.feature_tabs.addTab(self._create_gpio_tab(), "🔌 GPIO")

        # Tab 4: RFID/NFC
        self.feature_tabs.addTab(self._create_rfid_tab(), "💳 RFID/NFC")

        # Tab 5: LED & Effects
        self.feature_tabs.addTab(self._create_led_tab(), "💡 LED")

        # Tab 6: Console & Files
        self.feature_tabs.addTab(self._create_console_tab(), "💻 Console")

        main_layout.addWidget(self.feature_tabs)

        # ========== Status Bar ==========
        self.status_bar = QLabel("Ready to connect to Flipper Zero")
        self.status_bar.setStyleSheet("padding: 8px; background-color: #2a2a2a; border-radius: 4px;")
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)

    # ==================== Tab Creation Methods ====================

    def _create_subghz_tab(self):
        """Create SubGHz radio control tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # TX Section
        tx_group = QGroupBox("📤 Transmit")
        tx_layout = QVBoxLayout()

        # Frequency input
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Frequency (Hz):"))
        self.subghz_freq = QLineEdit("433920000")
        self.subghz_freq.setPlaceholderText("e.g., 433920000 for 433.92 MHz")
        freq_layout.addWidget(self.subghz_freq)

        # Quick presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Presets:"))
        for freq, label in [
            ("315000000", "315 MHz"),
            ("433920000", "433.92 MHz"),
            ("868000000", "868 MHz"),
            ("915000000", "915 MHz")
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, f=freq: self.subghz_freq.setText(f))
            btn.setMaximumWidth(100)
            preset_layout.addWidget(btn)
        preset_layout.addStretch()

        # Key and settings
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Key (hex):"))
        self.subghz_key = QLineEdit("AABBCC")
        self.subghz_key.setPlaceholderText("3-byte hex key")
        self.subghz_key.setMaximumWidth(100)
        key_layout.addWidget(self.subghz_key)

        key_layout.addWidget(QLabel("TE (μs):"))
        self.subghz_te = QSpinBox()
        self.subghz_te.setRange(100, 1000)
        self.subghz_te.setValue(400)
        self.subghz_te.setMaximumWidth(80)
        key_layout.addWidget(self.subghz_te)

        key_layout.addWidget(QLabel("Repeat:"))
        self.subghz_repeat = QSpinBox()
        self.subghz_repeat.setRange(1, 100)
        self.subghz_repeat.setValue(10)
        self.subghz_repeat.setMaximumWidth(60)
        key_layout.addWidget(self.subghz_repeat)
        key_layout.addStretch()

        # TX button
        self.subghz_tx_btn = QPushButton("📤 Transmit Signal")
        self.subghz_tx_btn.clicked.connect(self.on_subghz_tx)
        self.subghz_tx_btn.setEnabled(False)
        self.subghz_tx_btn.setStyleSheet("QPushButton { background-color: #3a4a5a; padding: 8px; font-weight: bold; }")

        tx_layout.addLayout(freq_layout)
        tx_layout.addLayout(preset_layout)
        tx_layout.addLayout(key_layout)
        tx_layout.addWidget(self.subghz_tx_btn)
        tx_group.setLayout(tx_layout)
        layout.addWidget(tx_group)

        # RX Section
        rx_group = QGroupBox("📥 Receive")
        rx_layout = QHBoxLayout()

        rx_layout.addWidget(QLabel("Duration (sec):"))
        self.subghz_rx_duration = QSpinBox()
        self.subghz_rx_duration.setRange(1, 60)
        self.subghz_rx_duration.setValue(10)
        self.subghz_rx_duration.setMaximumWidth(60)
        rx_layout.addWidget(self.subghz_rx_duration)

        self.subghz_rx_btn = QPushButton("📥 Start Receiving")
        self.subghz_rx_btn.clicked.connect(self.on_subghz_rx)
        self.subghz_rx_btn.setEnabled(False)
        self.subghz_rx_btn.setStyleSheet("QPushButton { background-color: #4a3a5a; padding: 8px; font-weight: bold; }")
        rx_layout.addWidget(self.subghz_rx_btn)
        rx_layout.addStretch()

        rx_group.setLayout(rx_layout)
        layout.addWidget(rx_group)

        # Output
        self.subghz_output = QTextEdit()
        self.subghz_output.setReadOnly(True)
        self.subghz_output.setPlaceholderText("SubGHz output will appear here...")
        self.subghz_output.setMaximumHeight(200)
        layout.addWidget(self.subghz_output)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_ir_tab(self):
        """Create IR control tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Universal Remote Section
        universal_group = QGroupBox("📺 Universal Remotes")
        universal_layout = QVBoxLayout()

        remote_layout = QHBoxLayout()
        remote_layout.addWidget(QLabel("Remote Type:"))
        self.ir_remote_type = QComboBox()
        self.ir_remote_type.addItems([
            "tv", "audio", "ac", "projectors", "monitor",
            "fans", "leds", "bluray_dvd", "digital_sign"
        ])
        remote_layout.addWidget(self.ir_remote_type)
        remote_layout.addStretch()

        # Quick buttons
        buttons_layout = QHBoxLayout()
        for signal in ["power", "vol_up", "vol_down", "ch_up", "ch_down", "mute"]:
            btn = QPushButton(signal.replace("_", " ").upper())
            btn.clicked.connect(lambda checked, s=signal: self.on_ir_universal(s))
            btn.setEnabled(False)
            setattr(self, f"ir_{signal}_btn", btn)
            buttons_layout.addWidget(btn)

        universal_layout.addLayout(remote_layout)
        universal_layout.addLayout(buttons_layout)
        universal_group.setLayout(universal_layout)
        layout.addWidget(universal_group)

        # Custom IR TX Section
        tx_group = QGroupBox("📤 Custom IR Transmit")
        tx_layout = QVBoxLayout()

        protocol_layout = QHBoxLayout()
        protocol_layout.addWidget(QLabel("Protocol:"))
        self.ir_protocol = QComboBox()
        self.ir_protocol.addItems([
            "NEC", "NECext", "Samsung32", "RC6", "RC5", "SIRC", "SIRC15", "SIRC20"
        ])
        protocol_layout.addWidget(self.ir_protocol)

        protocol_layout.addWidget(QLabel("Address:"))
        self.ir_address = QLineEdit("00")
        self.ir_address.setPlaceholderText("Hex")
        self.ir_address.setMaximumWidth(80)
        protocol_layout.addWidget(self.ir_address)

        protocol_layout.addWidget(QLabel("Command:"))
        self.ir_command = QLineEdit("00")
        self.ir_command.setPlaceholderText("Hex")
        self.ir_command.setMaximumWidth(80)
        protocol_layout.addWidget(self.ir_command)

        self.ir_tx_btn = QPushButton("📤 Transmit")
        self.ir_tx_btn.clicked.connect(self.on_ir_tx)
        self.ir_tx_btn.setEnabled(False)
        protocol_layout.addWidget(self.ir_tx_btn)
        protocol_layout.addStretch()

        tx_layout.addLayout(protocol_layout)
        tx_group.setLayout(tx_layout)
        layout.addWidget(tx_group)

        # IR RX Section
        rx_group = QGroupBox("📥 IR Receive")
        rx_layout = QHBoxLayout()

        rx_layout.addWidget(QLabel("Duration (sec):"))
        self.ir_rx_duration = QSpinBox()
        self.ir_rx_duration.setRange(1, 60)
        self.ir_rx_duration.setValue(10)
        self.ir_rx_duration.setMaximumWidth(60)
        rx_layout.addWidget(self.ir_rx_duration)

        self.ir_raw_mode = QCheckBox("Raw Mode")
        rx_layout.addWidget(self.ir_raw_mode)

        self.ir_rx_btn = QPushButton("📥 Start Receiving")
        self.ir_rx_btn.clicked.connect(self.on_ir_rx)
        self.ir_rx_btn.setEnabled(False)
        rx_layout.addWidget(self.ir_rx_btn)
        rx_layout.addStretch()

        rx_group.setLayout(rx_layout)
        layout.addWidget(rx_group)

        # Output
        self.ir_output = QTextEdit()
        self.ir_output.setReadOnly(True)
        self.ir_output.setPlaceholderText("IR output will appear here...")
        self.ir_output.setMaximumHeight(200)
        layout.addWidget(self.ir_output)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_gpio_tab(self):
        """Create GPIO control tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # GPIO Control
        gpio_group = QGroupBox("🔌 GPIO Pin Control")
        gpio_layout = QVBoxLayout()

        pin_layout = QHBoxLayout()
        pin_layout.addWidget(QLabel("Pin:"))
        self.gpio_pin = QComboBox()
        self.gpio_pin.addItems([
            "PC0", "PC1", "PC3", "PB2", "PB3", "PA4", "PA6", "PA7"
        ])
        pin_layout.addWidget(self.gpio_pin)

        pin_layout.addWidget(QLabel("Mode:"))
        self.gpio_mode = QComboBox()
        self.gpio_mode.addItems(["Input", "Output"])
        self.gpio_mode.currentTextChanged.connect(self.on_gpio_mode_changed)
        pin_layout.addWidget(self.gpio_mode)

        self.gpio_set_mode_btn = QPushButton("Set Mode")
        self.gpio_set_mode_btn.clicked.connect(self.on_gpio_set_mode)
        self.gpio_set_mode_btn.setEnabled(False)
        pin_layout.addWidget(self.gpio_set_mode_btn)
        pin_layout.addStretch()

        value_layout = QHBoxLayout()
        self.gpio_write_low_btn = QPushButton("Write LOW (0)")
        self.gpio_write_low_btn.clicked.connect(lambda: self.on_gpio_write(0))
        self.gpio_write_low_btn.setEnabled(False)
        value_layout.addWidget(self.gpio_write_low_btn)

        self.gpio_write_high_btn = QPushButton("Write HIGH (1)")
        self.gpio_write_high_btn.clicked.connect(lambda: self.on_gpio_write(1))
        self.gpio_write_high_btn.setEnabled(False)
        value_layout.addWidget(self.gpio_write_high_btn)

        self.gpio_read_btn = QPushButton("Read Value")
        self.gpio_read_btn.clicked.connect(self.on_gpio_read)
        self.gpio_read_btn.setEnabled(False)
        value_layout.addWidget(self.gpio_read_btn)
        value_layout.addStretch()

        gpio_layout.addLayout(pin_layout)
        gpio_layout.addLayout(value_layout)
        gpio_group.setLayout(gpio_layout)
        layout.addWidget(gpio_group)

        # GPIO Output
        self.gpio_output = QTextEdit()
        self.gpio_output.setReadOnly(True)
        self.gpio_output.setPlaceholderText("GPIO operations will appear here...")
        layout.addWidget(self.gpio_output)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_rfid_tab(self):
        """Create RFID/NFC tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # RFID Section
        rfid_group = QGroupBox("💳 RFID Operations")
        rfid_layout = QVBoxLayout()

        rfid_read_layout = QHBoxLayout()
        rfid_read_layout.addWidget(QLabel("Mode:"))
        self.rfid_mode = QComboBox()
        self.rfid_mode.addItems(["normal", "indala"])
        rfid_read_layout.addWidget(self.rfid_mode)

        self.rfid_read_btn = QPushButton("📖 Read RFID")
        self.rfid_read_btn.clicked.connect(self.on_rfid_read)
        self.rfid_read_btn.setEnabled(False)
        rfid_read_layout.addWidget(self.rfid_read_btn)
        rfid_read_layout.addStretch()

        rfid_layout.addLayout(rfid_read_layout)
        rfid_group.setLayout(rfid_layout)
        layout.addWidget(rfid_group)

        # NFC Section
        nfc_group = QGroupBox("📱 NFC Operations")
        nfc_layout = QVBoxLayout()

        apdu_layout = QHBoxLayout()
        apdu_layout.addWidget(QLabel("APDU:"))
        self.nfc_apdu = QLineEdit()
        self.nfc_apdu.setPlaceholderText("e.g., 00A4040007A000000004106001")
        apdu_layout.addWidget(self.nfc_apdu)

        self.nfc_send_btn = QPushButton("📤 Send APDU")
        self.nfc_send_btn.clicked.connect(self.on_nfc_send)
        self.nfc_send_btn.setEnabled(False)
        apdu_layout.addWidget(self.nfc_send_btn)

        nfc_layout.addLayout(apdu_layout)
        nfc_group.setLayout(nfc_layout)
        layout.addWidget(nfc_group)

        # Output
        self.rfid_nfc_output = QTextEdit()
        self.rfid_nfc_output.setReadOnly(True)
        self.rfid_nfc_output.setPlaceholderText("RFID/NFC operations will appear here...")
        layout.addWidget(self.rfid_nfc_output)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_led_tab(self):
        """Create LED control tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # LED Color Control
        led_group = QGroupBox("💡 LED Color Control")
        led_layout = QVBoxLayout()

        # RGB Sliders
        for channel, color in [("r", "Red"), ("g", "Green"), ("b", "Blue"), ("bl", "Backlight")]:
            channel_layout = QHBoxLayout()
            channel_layout.addWidget(QLabel(f"{color}:"))

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 255)
            slider.setValue(0)
            slider.valueChanged.connect(lambda val, ch=channel: self.on_led_slider_changed(ch, val))
            setattr(self, f"led_{channel}_slider", slider)
            channel_layout.addWidget(slider)

            value_label = QLabel("0")
            value_label.setMinimumWidth(30)
            setattr(self, f"led_{channel}_value", value_label)
            channel_layout.addWidget(value_label)

            led_layout.addLayout(channel_layout)

        # LED Buttons
        led_btn_layout = QHBoxLayout()

        self.led_apply_btn = QPushButton("✓ Apply Colors")
        self.led_apply_btn.clicked.connect(self.on_led_apply)
        self.led_apply_btn.setEnabled(False)
        led_btn_layout.addWidget(self.led_apply_btn)

        self.led_off_btn = QPushButton("⚫ LED Off")
        self.led_off_btn.clicked.connect(self.on_led_off)
        self.led_off_btn.setEnabled(False)
        led_btn_layout.addWidget(self.led_off_btn)

        led_layout.addLayout(led_btn_layout)

        # Quick Presets
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Presets:"))
        for color, rgb in [
            ("Red", (255, 0, 0, 0)),
            ("Green", (0, 255, 0, 0)),
            ("Blue", (0, 0, 255, 0)),
            ("Yellow", (255, 255, 0, 0)),
            ("Cyan", (0, 255, 255, 0)),
            ("Magenta", (255, 0, 255, 0)),
            ("White", (255, 255, 255, 0))
        ]:
            btn = QPushButton(color)
            btn.clicked.connect(lambda checked, r=rgb: self.on_led_preset(r))
            btn.setMaximumWidth(80)
            preset_layout.addWidget(btn)
        preset_layout.addStretch()

        led_layout.addLayout(preset_layout)
        led_group.setLayout(led_layout)
        layout.addWidget(led_group)

        # Vibration Control
        vib_group = QGroupBox("📳 Vibration")
        vib_layout = QHBoxLayout()

        vib_layout.addWidget(QLabel("Duration (sec):"))
        self.vib_duration = QSpinBox()
        self.vib_duration.setRange(1, 3)
        self.vib_duration.setValue(1)
        self.vib_duration.setMaximumWidth(60)
        vib_layout.addWidget(self.vib_duration)

        self.vib_btn = QPushButton("📳 Vibrate")
        self.vib_btn.clicked.connect(self.on_vibrate)
        self.vib_btn.setEnabled(False)
        vib_layout.addWidget(self.vib_btn)
        vib_layout.addStretch()

        vib_group.setLayout(vib_layout)
        layout.addWidget(vib_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_console_tab(self):
        """Create console and file browser tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Device Info
        info_group = QGroupBox("📱 Device Information")
        info_layout = QVBoxLayout()
        self.device_info_text = QTextEdit()
        self.device_info_text.setReadOnly(True)
        self.device_info_text.setMaximumHeight(120)
        self.device_info_text.setPlainText("No device connected")
        info_layout.addWidget(self.device_info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Command Console
        console_group = QGroupBox("💻 Command Console")
        console_layout = QVBoxLayout()

        command_layout = QHBoxLayout()
        command_layout.addWidget(QLabel("Command:"))
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter Flipper command (e.g., device_info, storage list /ext)")
        self.command_input.returnPressed.connect(self.on_send_command)
        command_layout.addWidget(self.command_input)

        self.send_btn = QPushButton("📤 Send")
        self.send_btn.clicked.connect(self.on_send_command)
        self.send_btn.setEnabled(False)
        command_layout.addWidget(self.send_btn)

        console_layout.addLayout(command_layout)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Monospace", 9))
        self.console_output.setPlaceholderText("Command history will appear here...")
        console_layout.addWidget(self.console_output)

        console_group.setLayout(console_layout)
        layout.addWidget(console_group)

        widget.setLayout(layout)
        return widget

    # ==================== Event Handlers ====================

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

    def on_connect(self):
        """Handle connect button"""
        if not self.flipper_service:
            self._initialize_service()

        port_text = self.port_combo.currentText()
        port = None if port_text == "Auto-detect" else port_text

        self.status_bar.setText("Connecting...")
        success = self.flipper_service.connect(port)

        if success:
            self.status_bar.setText(f"Connected to {self.flipper_service.device.name}")
        else:
            self.status_bar.setText("Connection failed")

    def on_disconnect(self):
        """Handle disconnect"""
        if self.flipper_service:
            self.flipper_service.disconnect()
            self.status_bar.setText("Disconnected")

    def on_send_command(self):
        """Send command"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        command = self.command_input.text().strip()
        if not command:
            return

        self.console_output.append(f"→ {command}")
        response = self.flipper_service.send_command(command)

        if response:
            self.console_output.append(f"← {response}")

        self.command_input.clear()

    # SubGHz Handlers
    def on_subghz_tx(self):
        """Transmit SubGHz signal"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        freq = int(self.subghz_freq.text())
        key = self.subghz_key.text()
        te = self.subghz_te.value()
        repeat = self.subghz_repeat.value()

        self.subghz_output.append(f"📤 Transmitting: {freq} Hz, Key: {key}, TE: {te}μs, Repeat: {repeat}")
        success = self.flipper_service.subghz_tx(freq, key, te, repeat)

        if success:
            self.subghz_output.append("✓ Transmission complete")
        else:
            self.subghz_output.append("✗ Transmission failed")

    def on_subghz_rx(self):
        """Receive SubGHz signals"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        freq = int(self.subghz_freq.text())
        duration = self.subghz_rx_duration.value()

        self.subghz_output.append(f"📥 Receiving on {freq} Hz for {duration} seconds...")
        self.flipper_service.subghz_rx(freq, 0, duration)
        self.subghz_output.append("✓ Reception complete")

    # IR Handlers
    def on_ir_universal(self, signal):
        """Send universal remote signal"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        remote = self.ir_remote_type.currentText()
        self.ir_output.append(f"📤 Sending: {remote} -> {signal}")
        success = self.flipper_service.ir_universal(remote, signal)

        if success:
            self.ir_output.append("✓ Signal sent")
        else:
            self.ir_output.append("✗ Failed to send signal")

    def on_ir_tx(self):
        """Transmit custom IR"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        protocol = self.ir_protocol.currentText()
        address = self.ir_address.text()
        command = self.ir_command.text()

        self.ir_output.append(f"📤 TX: {protocol} {address} {command}")
        success = self.flipper_service.ir_tx(protocol, address, command)

        if success:
            self.ir_output.append("✓ Transmitted")
        else:
            self.ir_output.append("✗ Failed")

    def on_ir_rx(self):
        """Receive IR signals"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        duration = self.ir_rx_duration.value()
        raw = self.ir_raw_mode.isChecked()

        self.ir_output.append(f"📥 Receiving IR for {duration}s...")
        self.flipper_service.ir_rx(duration, raw)
        self.ir_output.append("✓ Reception complete")

    # GPIO Handlers
    def on_gpio_mode_changed(self):
        """Handle GPIO mode change"""
        is_output = self.gpio_mode.currentText() == "Output"
        if hasattr(self, 'gpio_write_low_btn'):
            self.gpio_write_low_btn.setEnabled(is_output and self.flipper_service and self.flipper_service.is_connected())
            self.gpio_write_high_btn.setEnabled(is_output and self.flipper_service and self.flipper_service.is_connected())

    def on_gpio_set_mode(self):
        """Set GPIO pin mode"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        pin = self.gpio_pin.currentText()
        mode = 0 if self.gpio_mode.currentText() == "Input" else 1

        self.gpio_output.append(f"Setting {pin} to {'Output' if mode else 'Input'} mode...")
        success = self.flipper_service.gpio_set_mode(pin, mode)

        if success:
            self.gpio_output.append("✓ Mode set")
            self.on_gpio_mode_changed()
        else:
            self.gpio_output.append("✗ Failed")

    def on_gpio_write(self, value):
        """Write GPIO value"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        pin = self.gpio_pin.currentText()
        self.gpio_output.append(f"Writing {value} to {pin}...")
        success = self.flipper_service.gpio_write(pin, value)

        if success:
            self.gpio_output.append("✓ Written")
        else:
            self.gpio_output.append("✗ Failed")

    def on_gpio_read(self):
        """Read GPIO value"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        pin = self.gpio_pin.currentText()
        value = self.flipper_service.gpio_read(pin)

        if value is not None:
            self.gpio_output.append(f"{pin} = {value}")
        else:
            self.gpio_output.append("✗ Read failed")

    # RFID/NFC Handlers
    def on_rfid_read(self):
        """Read RFID tag"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        mode = self.rfid_mode.currentText()
        self.rfid_nfc_output.append(f"📖 Reading RFID ({mode} mode)...")
        data = self.flipper_service.rfid_read(mode)

        if data:
            self.rfid_nfc_output.append(f"✓ Data: {data.get('raw_response', 'No data')}")
        else:
            self.rfid_nfc_output.append("✗ Read failed")

    def on_nfc_send(self):
        """Send NFC APDU"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        apdu = self.nfc_apdu.text().strip()
        if not apdu:
            return

        self.rfid_nfc_output.append(f"📤 Sending APDU: {apdu}")
        response = self.flipper_service.nfc_send_apdu(apdu)

        if response:
            self.rfid_nfc_output.append(f"← {response}")
        else:
            self.rfid_nfc_output.append("✗ No response")

    # LED Handlers
    def on_led_slider_changed(self, channel, value):
        """Update LED value label"""
        label = getattr(self, f"led_{channel}_value")
        label.setText(str(value))

    def on_led_preset(self, rgb):
        """Apply LED preset"""
        r, g, b, bl = rgb
        self.led_r_slider.setValue(r)
        self.led_g_slider.setValue(g)
        self.led_b_slider.setValue(b)
        self.led_bl_slider.setValue(bl)
        self.on_led_apply()

    def on_led_apply(self):
        """Apply LED colors"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        r = self.led_r_slider.value()
        g = self.led_g_slider.value()
        b = self.led_b_slider.value()
        bl = self.led_bl_slider.value()

        self.flipper_service.led_set(r, g, b, bl)
        self.status_bar.setText(f"LED set: R={r} G={g} B={b} BL={bl}")

    def on_led_off(self):
        """Turn LED off"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        self.flipper_service.led_off()
        self.led_r_slider.setValue(0)
        self.led_g_slider.setValue(0)
        self.led_b_slider.setValue(0)
        self.led_bl_slider.setValue(0)
        self.status_bar.setText("LED turned off")

    def on_vibrate(self):
        """Vibrate"""
        if not self.flipper_service or not self.flipper_service.is_connected():
            return

        duration = self.vib_duration.value()
        self.flipper_service.vibrate(duration)
        self.status_bar.setText(f"Vibrating for {duration}s")

    # Signal Handlers
    @pyqtSlot(object)
    def on_flipper_connected(self, device):
        """Handle connection"""
        self.status_label.setText(f"✅ {device.name}")
        self.status_label.setStyleSheet("color: #44ff44; font-weight: bold; padding: 5px;")

        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.send_btn.setEnabled(True)

        # Enable all feature buttons
        for btn_name in dir(self):
            if btn_name.endswith('_btn') and btn_name not in ['connect_btn', 'disconnect_btn', 'refresh_ports_btn', 'send_btn']:
                btn = getattr(self, btn_name)
                if isinstance(btn, QPushButton):
                    btn.setEnabled(True)

        self.device_info_text.setPlainText(f"Name: {device.name}\nModel: {device.hardware_model}\nUID: {device.hardware_uid}\nFirmware: {device.firmware_origin} {device.firmware_version}\nPort: {device.port}")

    @pyqtSlot()
    def on_flipper_disconnected(self):
        """Handle disconnection"""
        self.status_label.setText("❌ Disconnected")
        self.status_label.setStyleSheet("color: #ff4444; font-weight: bold; padding: 5px;")

        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.send_btn.setEnabled(False)

        # Disable all feature buttons
        for btn_name in dir(self):
            if btn_name.endswith('_btn') and btn_name not in ['connect_btn', 'disconnect_btn', 'refresh_ports_btn', 'send_btn']:
                btn = getattr(self, btn_name)
                if isinstance(btn, QPushButton):
                    btn.setEnabled(False)

        self.device_info_text.setPlainText("No device connected")

    @pyqtSlot(str)
    def on_flipper_status_message(self, message):
        """Handle status message"""
        self.console_output.append(f"[INFO] {message}")

    @pyqtSlot(str)
    def on_flipper_error(self, error):
        """Handle error"""
        self.console_output.append(f"[ERROR] {error}")
        self.status_bar.setText(f"Error: {error}")

    def _initialize_service(self):
        """Initialize Flipper service"""
        from ..services.flipper_service import FlipperZeroService

        self.flipper_service = FlipperZeroService()
        self.flipper_service.connected.connect(self.on_flipper_connected)
        self.flipper_service.disconnected.connect(self.on_flipper_disconnected)
        self.flipper_service.status_message.connect(self.on_flipper_status_message)
        self.flipper_service.error_occurred.connect(self.on_flipper_error)
