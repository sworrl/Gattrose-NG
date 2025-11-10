"""
Manual Attack Tab
Manual wireless network attack interface
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QComboBox, QProgressBar, QTextEdit,
    QFileDialog, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt
from pathlib import Path


class ManualAttackTab(QWidget):
    """Manual attack interface for one-off attacks"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_attack = None
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()

        # ========== HEADER ==========
        header = QLabel("Manual Attack Mode")
        header.setProperty("heading", True)
        layout.addWidget(header)

        info = QLabel("Manually configure and execute wireless network attacks")
        layout.addWidget(info)

        # ========== TARGET SELECTION ==========
        target_group = QGroupBox("Target Configuration")
        target_layout = QVBoxLayout()

        # BSSID
        bssid_layout = QHBoxLayout()
        bssid_layout.addWidget(QLabel("Target BSSID:"))
        self.bssid_input = QLineEdit()
        self.bssid_input.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        bssid_layout.addWidget(self.bssid_input)

        load_from_scanner_btn = QPushButton("📡 Load from Scanner")
        load_from_scanner_btn.clicked.connect(self.load_from_scanner)
        bssid_layout.addWidget(load_from_scanner_btn)

        target_layout.addLayout(bssid_layout)

        # SSID
        ssid_layout = QHBoxLayout()
        ssid_layout.addWidget(QLabel("SSID:"))
        self.ssid_input = QLineEdit()
        self.ssid_input.setPlaceholderText("Network Name")
        ssid_layout.addWidget(self.ssid_input)
        target_layout.addLayout(ssid_layout)

        # Channel
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Channel:"))
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("1-14")
        channel_layout.addWidget(self.channel_input)

        # Interface
        channel_layout.addWidget(QLabel("Interface:"))
        self.interface_input = QLineEdit()
        self.interface_input.setPlaceholderText("wlan0mon")
        channel_layout.addWidget(self.interface_input)

        target_layout.addLayout(channel_layout)

        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        # ========== ATTACK METHOD ==========
        method_group = QGroupBox("Attack Method")
        method_layout = QVBoxLayout()

        # Method selector
        method_select_layout = QHBoxLayout()
        method_select_layout.addWidget(QLabel("Method:"))

        self.method_combo = QComboBox()
        self.method_combo.addItem("🤝 Capture Handshake + Crack PSK", "handshake")
        self.method_combo.addItem("🔓 WPS PIN Attack (Reaver)", "wps_reaver")
        self.method_combo.addItem("⚡ WPS Pixie Dust", "wps_pixie")
        self.method_combo.addItem("📦 Crack Existing Handshake", "crack_only")
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        method_select_layout.addWidget(self.method_combo)

        method_select_layout.addStretch()
        method_layout.addLayout(method_select_layout)

        method_group.setLayout(method_layout)
        layout.addWidget(method_group)

        # ========== ATTACK OPTIONS ==========
        options_group = QGroupBox("Attack Options")
        options_layout = QVBoxLayout()

        # Handshake options
        self.handshake_options = QWidget()
        hs_layout = QVBoxLayout()

        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Capture Timeout (sec):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 3600)
        self.timeout_spin.setValue(300)
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        hs_layout.addLayout(timeout_layout)

        deauth_layout = QHBoxLayout()
        deauth_layout.addWidget(QLabel("Deauth Packets:"))
        self.deauth_spin = QSpinBox()
        self.deauth_spin.setRange(1, 100)
        self.deauth_spin.setValue(10)
        deauth_layout.addWidget(self.deauth_spin)
        deauth_layout.addStretch()
        hs_layout.addLayout(deauth_layout)

        self.handshake_options.setLayout(hs_layout)
        options_layout.addWidget(self.handshake_options)

        # Cracking options
        self.crack_options = QWidget()
        crack_layout = QVBoxLayout()

        wordlist_layout = QHBoxLayout()
        wordlist_layout.addWidget(QLabel("Wordlist:"))
        self.wordlist_input = QLineEdit()
        self.wordlist_input.setText("/usr/share/wordlists/rockyou.txt")
        wordlist_layout.addWidget(self.wordlist_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_wordlist)
        wordlist_layout.addWidget(browse_btn)
        crack_layout.addLayout(wordlist_layout)

        self.use_gpu_check = QCheckBox("Use GPU Acceleration (Hashcat)")
        crack_layout.addWidget(self.use_gpu_check)

        self.crack_options.setLayout(crack_layout)
        options_layout.addWidget(self.crack_options)

        # WPS options
        self.wps_options = QWidget()
        wps_layout = QVBoxLayout()

        wps_timeout_layout = QHBoxLayout()
        wps_timeout_layout.addWidget(QLabel("WPS Timeout (sec):"))
        self.wps_timeout_spin = QSpinBox()
        self.wps_timeout_spin.setRange(60, 7200)
        self.wps_timeout_spin.setValue(300)
        wps_timeout_layout.addWidget(self.wps_timeout_spin)
        wps_timeout_layout.addStretch()
        wps_layout.addLayout(wps_timeout_layout)

        self.wps_options.setLayout(wps_layout)
        options_layout.addWidget(self.wps_options)
        self.wps_options.setVisible(False)

        # Crack-only options
        self.crack_only_options = QWidget()
        crack_only_layout = QVBoxLayout()

        cap_file_layout = QHBoxLayout()
        cap_file_layout.addWidget(QLabel("Capture File:"))
        self.cap_file_input = QLineEdit()
        cap_file_layout.addWidget(self.cap_file_input)

        browse_cap_btn = QPushButton("Browse...")
        browse_cap_btn.clicked.connect(self.browse_capture)
        cap_file_layout.addWidget(browse_cap_btn)
        crack_only_layout.addLayout(cap_file_layout)

        self.crack_only_options.setLayout(crack_only_layout)
        options_layout.addWidget(self.crack_only_options)
        self.crack_only_options.setVisible(False)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # ========== ATTACK CONTROL ==========
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton("🚀 Start Attack")
        self.start_btn.clicked.connect(self.start_attack)
        self.start_btn.setMinimumHeight(40)
        control_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹️ Stop Attack")
        self.stop_btn.clicked.connect(self.stop_attack)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # ========== PROGRESS ==========
        progress_group = QGroupBox("Attack Progress")
        progress_layout = QVBoxLayout()

        self.status_label = QLabel("Status: Ready")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # ========== RESULTS ==========
        results_group = QGroupBox("Attack Results")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        self.results_text.setFontFamily("monospace")
        results_layout.addWidget(self.results_text)

        # Result actions
        result_actions = QHBoxLayout()

        save_results_btn = QPushButton("💾 Save Results")
        save_results_btn.clicked.connect(self.save_results)
        result_actions.addWidget(save_results_btn)

        clear_results_btn = QPushButton("🗑️ Clear")
        clear_results_btn.clicked.connect(self.results_text.clear)
        result_actions.addWidget(clear_results_btn)

        result_actions.addStretch()
        results_layout.addLayout(result_actions)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        layout.addStretch()
        self.setLayout(layout)

    def on_method_changed(self, index):
        """Handle attack method change"""
        method = self.method_combo.itemData(index)

        # Show/hide relevant options
        self.handshake_options.setVisible(method == "handshake")
        self.crack_options.setVisible(method == "handshake" or method == "crack_only")
        self.wps_options.setVisible(method in ["wps_reaver", "wps_pixie"])
        self.crack_only_options.setVisible(method == "crack_only")

    def load_from_scanner(self):
        """Load target from scanner tab"""
        self.log("Loading target from scanner...")
        # TODO: Get selected AP from scanner tab
        # For now, show placeholder
        self.log("Select an AP in the Scanner tab first")

    def load_target(self, bssid: str, ssid: str = "", channel: str = "", encryption: str = ""):
        """Load target data into the attack form

        Args:
            bssid: Target BSSID/MAC address
            ssid: Target SSID (optional)
            channel: Target channel (optional)
            encryption: Encryption type (optional)
        """
        self.bssid_input.setText(bssid)
        if ssid:
            self.ssid_input.setText(ssid)
        if channel:
            self.channel_input.setText(str(channel))

        # Set attack method based on encryption
        if encryption:
            if "WPS" in encryption.upper():
                # Set to WPS attack
                for i in range(self.method_combo.count()):
                    if "WPS" in self.method_combo.itemText(i):
                        self.method_combo.setCurrentIndex(i)
                        break
            elif "WPA" in encryption.upper():
                # Set to handshake capture
                self.method_combo.setCurrentIndex(0)  # Handshake + Crack

        # Try to auto-detect monitor interface using safe method
        try:
            import subprocess
            # Use 'iw dev' instead of 'iwconfig' (more reliable and doesn't require wireless-tools)
            result = subprocess.run(['iw', 'dev'], capture_output=True, text=True, timeout=2)
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines):
                if 'type monitor' in line.lower():
                    # Look backwards for the interface name
                    for j in range(i - 1, max(0, i - 5), -1):
                        if 'Interface' in lines[j]:
                            parts = lines[j].strip().split()
                            if len(parts) >= 2:
                                self.interface_input.setText(parts[1])
                                break
                    break
        except Exception as e:
            # Silently fail - user can manually enter interface if needed
            pass

        self.log(f"Loaded target: {bssid} ({ssid or 'Unknown'})")

    def browse_wordlist(self):
        """Browse for wordlist file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Wordlist",
            "/usr/share/wordlists",
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.wordlist_input.setText(file_path)

    def browse_capture(self):
        """Browse for capture file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Capture File",
            str(Path.cwd() / "data" / "captures"),
            "Capture Files (*.cap *.pcap);;All Files (*)"
        )
        if file_path:
            self.cap_file_input.setText(file_path)

    def start_attack(self):
        """Start manual attack"""
        method = self.method_combo.currentData()
        bssid = self.bssid_input.text().strip()
        ssid = self.ssid_input.text().strip()
        channel = self.channel_input.text().strip()
        interface = self.interface_input.text().strip()

        # Validate inputs
        if not bssid:
            self.log("❌ Error: BSSID required")
            return

        if method != "crack_only" and not interface:
            self.log("❌ Error: Interface required")
            return

        self.log(f"🚀 Starting {method} attack...")
        self.log(f"Target: {ssid} ({bssid})")

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)

        # Import attack engine
        from ..core.attack_engine import HandshakeCapturer, PSKCracker, WPSAttacker

        if method == "handshake":
            # Capture handshake then crack
            self.current_attack = HandshakeCapturer(
                interface=interface,
                bssid=bssid,
                channel=channel,
                ssid=ssid,
                timeout=self.timeout_spin.value()
            )
            self.current_attack.progress_updated.connect(self.on_progress)
            self.current_attack.handshake_captured.connect(self.on_handshake_captured)
            self.current_attack.finished.connect(self.on_attack_finished)
            self.current_attack.start()

        elif method in ["wps_reaver", "wps_pixie"]:
            # WPS attack
            self.current_attack = WPSAttacker(
                interface=interface,
                bssid=bssid,
                ssid=ssid,
                timeout=self.wps_timeout_spin.value()
            )
            self.current_attack.progress_updated.connect(self.on_progress)
            self.current_attack.pin_found.connect(self.on_wps_success)
            self.current_attack.finished.connect(self.on_attack_finished)
            self.current_attack.start()

        elif method == "crack_only":
            # Crack existing capture
            cap_file = self.cap_file_input.text().strip()
            if not cap_file or not Path(cap_file).exists():
                self.log("❌ Error: Valid capture file required")
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                return

            self.current_attack = PSKCracker(
                capture_file=cap_file,
                ssid=ssid or "Unknown",
                bssid=bssid,
                wordlist=self.wordlist_input.text() or None,
                use_gpu=self.use_gpu_check.isChecked()
            )
            self.current_attack.progress_updated.connect(self.on_progress)
            self.current_attack.key_recovered.connect(self.on_key_recovered)
            self.current_attack.finished.connect(self.on_attack_finished)
            self.current_attack.start()

    def stop_attack(self):
        """Stop current attack"""
        if self.current_attack:
            self.log("⏹️ Stopping attack...")
            self.current_attack.stop()
            self.current_attack.wait()
            self.current_attack = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def on_progress(self, percentage: int, message: str):
        """Update progress"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"Status: {message}")
        self.log(message)

    def on_handshake_captured(self, ssid: str, bssid: str, capture_file: str):
        """Handle handshake captured"""
        self.log(f"✅ Handshake captured for {ssid}!")
        self.log(f"📁 File: {capture_file}")

        # Auto-crack if enabled
        if self.crack_options.isVisible():
            self.log("Starting PSK crack...")
            from ..core.attack_engine import PSKCracker

            cracker = PSKCracker(
                capture_file=capture_file,
                ssid=ssid,
                bssid=bssid,
                wordlist=self.wordlist_input.text() or None,
                use_gpu=self.use_gpu_check.isChecked()
            )
            cracker.progress_updated.connect(self.on_progress)
            cracker.key_recovered.connect(self.on_key_recovered)
            cracker.finished.connect(self.on_attack_finished)
            cracker.start()

            self.current_attack = cracker

    def on_key_recovered(self, ssid: str, bssid: str, key: str):
        """Handle PSK recovered"""
        self.log(f"🔑 KEY RECOVERED!")
        self.log(f"SSID: {ssid}")
        self.log(f"BSSID: {bssid}")
        self.log(f"PSK: {key}")
        self.log("-" * 50)

    def on_wps_success(self, ssid: str, bssid: str, pin: str, psk: str):
        """Handle WPS attack success"""
        self.log(f"🔓 WPS CRACKED!")
        self.log(f"SSID: {ssid}")
        self.log(f"BSSID: {bssid}")
        self.log(f"WPS PIN: {pin}")
        self.log(f"PSK: {psk}")
        self.log("-" * 50)

    def on_attack_finished(self, success: bool, message: str):
        """Handle attack finished"""
        self.log(message)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.current_attack = None

    def save_results(self):
        """Save results to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Results",
            str(Path.cwd() / "data" / "results" / "attack_results.txt"),
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(self.results_text.toPlainText())
            self.log(f"💾 Results saved to {file_path}")

    def log(self, message: str):
        """Add message to results"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.results_text.append(f"[{timestamp}] {message}")
