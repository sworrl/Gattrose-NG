"""
Auto Attack Tab
Automated wireless network attack management
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QCheckBox, QProgressBar, QTreeWidget,
    QTreeWidgetItem, QSpinBox, QTextEdit, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from pathlib import Path


class AutoAttackMode:
    """Auto attack mode definitions"""
    PASSIVE = "passive"  # Collect handshakes/PCAPs only
    FULL_AUTO = "full_auto"  # Attack all networks by score
    WPS_ONLY = "wps_only"  # Target WPS-enabled only
    WPS_FIRST = "wps_first"  # WPS then others
    SKIP_WPS = "skip_wps"  # Avoid WPS, attack rest
    AUTO_PWN_247 = "auto_pwn_247"  # Continuously attack all uncracked networks 24/7
    CUSTOM = "custom"  # User-defined rules


class AutoAttackTab(QWidget):
    """Automated attack management interface"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None  # Reference to main window for accessing scanner
        self.attack_engine = None
        self.auto_pwn_timer = None
        self.auto_pwn_active = False
        self.attack_processor_timer = None
        self.init_ui()

    def set_main_window(self, main_window):
        """Set reference to main window for accessing scanner tab"""
        self.main_window = main_window

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()

        # ========== HEADER ==========
        header = QLabel("Auto Attack System")
        header.setProperty("heading", True)
        layout.addWidget(header)

        info = QLabel("Automated wireless network attack and key recovery system")
        layout.addWidget(info)

        # ========== CONTROL PANEL ==========
        control_group = QGroupBox("Attack Control")
        control_layout = QVBoxLayout()

        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Attack Mode:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("🔒 Passive - Collect Handshakes Only", AutoAttackMode.PASSIVE)
        self.mode_combo.addItem("⚡ Full Auto - Attack by Vulnerability Score", AutoAttackMode.FULL_AUTO)
        self.mode_combo.addItem("🔓 WPS Only - Target WPS Networks", AutoAttackMode.WPS_ONLY)
        self.mode_combo.addItem("🎯 WPS First - WPS then Others", AutoAttackMode.WPS_FIRST)
        self.mode_combo.addItem("🚫 Skip WPS - Avoid WPS Networks", AutoAttackMode.SKIP_WPS)
        self.mode_combo.addItem("💀 Auto Pwn 24/7 - Continuously Attack All Uncracked", AutoAttackMode.AUTO_PWN_247)
        self.mode_combo.addItem("⚙️ Custom - User-Defined Rules", AutoAttackMode.CUSTOM)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)

        mode_layout.addStretch()
        control_layout.addLayout(mode_layout)

        # Attack parameters
        params_layout = QHBoxLayout()

        # Min attack score
        params_layout.addWidget(QLabel("Min Attack Score:"))
        self.min_score_spin = QSpinBox()
        self.min_score_spin.setRange(0, 100)
        self.min_score_spin.setValue(60)
        self.min_score_spin.setSuffix(" / 100")
        params_layout.addWidget(self.min_score_spin)

        # Max concurrent attacks
        params_layout.addWidget(QLabel("Max Concurrent:"))
        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 10)
        self.max_concurrent_spin.setValue(3)
        params_layout.addWidget(self.max_concurrent_spin)

        # Timeout per attack
        params_layout.addWidget(QLabel("Timeout (min):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 1440)
        self.timeout_spin.setValue(30)
        params_layout.addWidget(self.timeout_spin)

        params_layout.addStretch()
        control_layout.addLayout(params_layout)

        # Attack options
        options_layout = QHBoxLayout()

        self.handshake_only_check = QCheckBox("Capture Handshakes Only")
        self.handshake_only_check.setChecked(False)
        options_layout.addWidget(self.handshake_only_check)

        self.auto_crack_check = QCheckBox("Auto-Crack Captured Handshakes")
        self.auto_crack_check.setChecked(True)
        options_layout.addWidget(self.auto_crack_check)

        self.use_gpu_check = QCheckBox("Use GPU Acceleration")
        self.use_gpu_check.setChecked(False)
        options_layout.addWidget(self.use_gpu_check)

        options_layout.addStretch()
        control_layout.addLayout(options_layout)

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶️ Start Auto Attack")
        self.start_btn.clicked.connect(self.start_auto_attack)
        self.start_btn.setMinimumHeight(40)
        button_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.clicked.connect(self.pause_auto_attack)
        self.pause_btn.setEnabled(False)
        button_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self.stop_auto_attack)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        button_layout.addStretch()
        control_layout.addLayout(button_layout)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # ========== STATUS & PROGRESS ==========
        status_group = QGroupBox("Attack Status")
        status_layout = QVBoxLayout()

        # Overall progress
        self.overall_progress = QProgressBar()
        self.overall_progress.setFormat("Overall: %p% (%v/%m)")
        status_layout.addWidget(self.overall_progress)

        # Current attack progress
        self.current_progress = QProgressBar()
        self.current_progress.setFormat("Current: %p%")
        status_layout.addWidget(self.current_progress)

        # Stats
        stats_layout = QHBoxLayout()

        self.queued_label = QLabel("Queued: 0")
        stats_layout.addWidget(self.queued_label)

        self.attacking_label = QLabel("Attacking: 0")
        stats_layout.addWidget(self.attacking_label)

        self.completed_label = QLabel("Completed: 0")
        stats_layout.addWidget(self.completed_label)

        self.successful_label = QLabel("Successful: 0")
        stats_layout.addWidget(self.successful_label)

        self.failed_label = QLabel("Failed: 0")
        stats_layout.addWidget(self.failed_label)

        stats_layout.addStretch()
        status_layout.addLayout(stats_layout)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # ========== TARGET QUEUE ==========
        queue_group = QGroupBox("Target Queue")
        queue_layout = QVBoxLayout()

        # Queue tree (with enhanced object-oriented display like scanner)
        self.queue_tree = QTreeWidget()
        self.queue_tree.setHeaderLabels([
            "SSID", "BSSID/MAC (Vendor)", "Device", "Score", "Encryption", "Status", "Progress", "Result"
        ])
        self.queue_tree.setColumnWidth(0, 150)   # SSID
        self.queue_tree.setColumnWidth(1, 280)   # BSSID/MAC (Vendor)
        self.queue_tree.setColumnWidth(2, 150)   # Device Type
        self.queue_tree.setColumnWidth(3, 60)    # Score
        self.queue_tree.setColumnWidth(4, 100)   # Encryption
        self.queue_tree.setColumnWidth(5, 100)   # Status
        self.queue_tree.setColumnWidth(6, 80)    # Progress
        self.queue_tree.setColumnWidth(7, 120)   # Result
        self.queue_tree.setMinimumHeight(200)
        self.queue_tree.setAlternatingRowColors(True)
        queue_layout.addWidget(self.queue_tree)

        # Queue controls
        queue_controls = QHBoxLayout()

        add_target_btn = QPushButton("Add Selected Targets")
        add_target_btn.clicked.connect(self.add_targets_from_scanner)
        queue_controls.addWidget(add_target_btn)

        clear_queue_btn = QPushButton("Clear Queue")
        clear_queue_btn.clicked.connect(self.clear_queue)
        queue_controls.addWidget(clear_queue_btn)

        remove_selected_btn = QPushButton("Remove Selected")
        remove_selected_btn.clicked.connect(self.remove_selected_targets)
        queue_controls.addWidget(remove_selected_btn)

        queue_controls.addStretch()
        queue_layout.addLayout(queue_controls)

        queue_group.setLayout(queue_layout)
        layout.addWidget(queue_group)

        # ========== ATTACK LOG ==========
        log_group = QGroupBox("Attack Log")
        log_layout = QVBoxLayout()

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        self.log_area.setFontFamily("monospace")
        log_layout.addWidget(self.log_area)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.setLayout(layout)

    def on_mode_changed(self, index):
        """Handle attack mode change"""
        mode = self.mode_combo.itemData(index)

        # Update UI based on mode
        if mode == AutoAttackMode.PASSIVE:
            self.handshake_only_check.setChecked(True)
            self.handshake_only_check.setEnabled(False)
            self.auto_crack_check.setChecked(False)
            self.auto_crack_check.setEnabled(False)
            self.log("Mode: Passive - Will only capture handshakes")

        elif mode == AutoAttackMode.WPS_ONLY:
            self.min_score_spin.setEnabled(False)
            self.log("Mode: WPS Only - Will target WPS-enabled networks only")

        elif mode == AutoAttackMode.WPS_FIRST:
            self.log("Mode: WPS First - Will attack WPS networks first, then others")

        elif mode == AutoAttackMode.SKIP_WPS:
            self.log("Mode: Skip WPS - Will avoid WPS networks entirely")

        elif mode == AutoAttackMode.FULL_AUTO:
            self.handshake_only_check.setEnabled(True)
            self.auto_crack_check.setEnabled(True)
            self.min_score_spin.setEnabled(True)
            self.log("Mode: Full Auto - Will attack networks by vulnerability score")

        elif mode == AutoAttackMode.CUSTOM:
            self.log("Mode: Custom - Configure attack rules manually")

    def start_auto_attack(self):
        """Start automated attack"""
        mode = self.mode_combo.currentData()
        self.log(f"🚀 Starting auto attack in {mode} mode...")
        self.log(f"⚙️ Min Score: {self.min_score_spin.value()}, Max Concurrent: {self.max_concurrent_spin.value()}")

        # Stop scanner if it's running (attacks require exclusive use of the wireless interface)
        if self.main_window and hasattr(self.main_window, 'scanner_tab'):
            scanner_tab = self.main_window.scanner_tab
            if hasattr(scanner_tab, 'scanner') and scanner_tab.scanner and scanner_tab.scanner.isRunning():
                self.log("⏹️ Stopping active scan - attacks require exclusive interface access")
                scanner_tab.stop_scan()
                self.log("✓ Scanner stopped")

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

        # Special handling for Auto Pwn 24/7 mode
        if mode == AutoAttackMode.AUTO_PWN_247:
            self.start_auto_pwn_247()
        else:
            # Start attack processing for other modes
            self.start_attack_processing()

    def start_attack_processing(self):
        """Start processing the attack queue"""
        self.log("⚙️ Starting attack queue processing...")

        # Create attack processor thread
        from PyQt6.QtCore import QTimer
        self.attack_processor_timer = QTimer()
        self.attack_processor_timer.timeout.connect(self.process_attack_queue)
        self.attack_processor_timer.start(2000)  # Check queue every 2 seconds

        # Process first batch immediately
        self.process_attack_queue()

    def process_attack_queue(self):
        """Process queued attacks"""
        max_concurrent = self.max_concurrent_spin.value()

        # Count currently running attacks
        running_count = 0
        for i in range(self.queue_tree.topLevelItemCount()):
            item = self.queue_tree.topLevelItem(i)
            status = item.text(5)  # Status is now column 5
            if "Attacking" in status or "In Progress" in status or "⚔️" in status:
                running_count += 1

        # Start new attacks if under limit
        if running_count < max_concurrent:
            for i in range(self.queue_tree.topLevelItemCount()):
                if running_count >= max_concurrent:
                    break

                item = self.queue_tree.topLevelItem(i)
                status = item.text(5)  # Status is now column 5
                if "Queued" in status or "⏳" in status:
                    # Launch attack on this target
                    self.launch_attack_on_target(item)
                    running_count += 1

    def launch_attack_on_target(self, item: QTreeWidgetItem):
        """Launch attack on a queued target"""
        # Extract BSSID from column 1 (which now contains icon and vendor)
        bssid_text = item.text(1)  # e.g., "📱 AA:BB:CC:DD:EE:FF (Vendor)"
        # Extract MAC address (format XX:XX:XX:XX:XX:XX)
        import re
        mac_match = re.search(r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})', bssid_text)
        bssid = mac_match.group(1) if mac_match else bssid_text.split()[1] if len(bssid_text.split()) > 1 else bssid_text

        ssid = item.text(0)
        encryption = item.text(4)  # Encryption is now column 4

        item.setText(5, "⚔️ Attacking")  # Status is now column 5
        item.setText(6, "0%")  # Progress is now column 6
        self.update_queue_stats()

        self.log(f"🎯 Launching attack on {bssid} ({ssid})")

        # Detect monitor interface
        import subprocess
        try:
            result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=2)
            monitor_iface = None
            for line in result.stdout.split('\n'):
                if 'Mode:Monitor' in line or 'mon' in line.lower():
                    monitor_iface = line.split()[0]
                    break

            if not monitor_iface:
                item.setText(5, "❌ Failed")  # Status is column 5
                item.setText(7, "No monitor interface")  # Result is column 7
                self.log(f"❌ No monitor interface found for {bssid}")
                self.update_queue_stats()
                return

            # Get channel from database or scanner
            channel = "1"  # Default, should query from database

            # Launch appropriate attack based on encryption
            if "WPS" in encryption.upper():
                self.launch_wps_attack_thread(item, monitor_iface, bssid, ssid, channel)
            else:
                self.launch_handshake_attack_thread(item, monitor_iface, bssid, ssid, channel)

        except Exception as e:
            item.setText(5, "❌ Failed")  # Status is column 5
            item.setText(7, str(e))  # Result is column 7
            self.log(f"❌ Error launching attack on {bssid}: {e}")
            self.update_queue_stats()

    def launch_handshake_attack_thread(self, item, interface, bssid, ssid, channel):
        """Launch handshake capture attack in thread"""
        from ..core.attack_engine import HandshakeCapturer

        capturer = HandshakeCapturer(interface, bssid, channel, ssid, timeout=self.timeout_spin.value() * 60)

        # Connect signals
        capturer.progress_updated.connect(lambda pct, msg: self.on_attack_progress(item, pct, msg))
        capturer.handshake_captured.connect(lambda s, b, f: self.on_handshake_captured(item, s, b, f))
        capturer.finished.connect(lambda success, msg: self.on_attack_finished(item, success, msg))

        # Start capture
        capturer.start()

    def launch_wps_attack_thread(self, item, interface, bssid, ssid, channel):
        """Launch WPS attack in thread"""
        try:
            from ..core.attack_engine import WPSAttacker

            self.log(f"🔓 Launching WPS attack on {ssid} [{bssid}]...")
            item.setText(5, "🔓 Attacking")  # Status is column 5

            # Create WPS attacker
            attacker = WPSAttacker(interface, bssid, ssid, timeout=self.timeout_spin.value() * 60)

            # Connect signals
            attacker.progress_updated.connect(lambda pct, msg: self.on_attack_progress(item, pct, msg))
            attacker.pin_found.connect(lambda s, b, pin, psk: self.on_wps_pin_found(item, s, b, pin, psk))
            attacker.finished.connect(lambda success, msg: self.on_attack_finished(item, success, msg))

            # Start attack
            attacker.start()
        except Exception as e:
            self.log(f"❌ Error launching WPS attack: {e}")
            item.setText(5, "❌ Failed")
            item.setText(7, f"Launch error: {str(e)}")
            self.update_queue_stats()

    def on_wps_pin_found(self, item, ssid, bssid, pin, psk):
        """Handle WPS PIN/PSK found"""
        self.log(f"✅ WPS Cracked: {ssid} [{bssid}]")
        self.log(f"   PIN: {pin}")
        self.log(f"   PSK: {psk}")

        # Update result column
        item.setText(7, f"PIN: {pin} | PSK: {psk}")

        # Save to database
        try:
            from src.database.models import get_session, Network
            from datetime import datetime

            session = get_session()
            network = session.query(Network).filter_by(bssid=bssid).first()

            if network:
                network.password = psk
                network.wps_pin = pin
                network.cracked_at = datetime.now()
                session.commit()
                self.log(f"💾 Saved credentials to database")

            session.close()
        except Exception as e:
            self.log(f"⚠️ Database save error: {e}")

    def on_attack_progress(self, item, percentage, message):
        """Handle attack progress update"""
        item.setText(6, f"{percentage}%")  # Progress is column 6

    def on_handshake_captured(self, item, ssid, bssid, capture_file):
        """Handle handshake capture"""
        self.log(f"✅ Handshake captured for {bssid}!")
        item.setText(7, f"Handshake: {Path(capture_file).name}")  # Result is column 7

        # Auto-crack if enabled
        if self.auto_crack_check.isChecked():
            self.log(f"🔓 Auto-cracking {bssid}...")
            self.launch_cracking_thread(item, ssid, bssid, capture_file)

    def launch_cracking_thread(self, item, ssid, bssid, capture_file):
        """Launch password cracking thread"""
        from src.core.attack_engine import PSKCracker
        from pathlib import Path

        self.log(f"🔓 Starting password crack for {ssid} [{bssid}]...")
        item.setText(5, "🔓 Cracking")  # Status is column 5

        # Get wordlist (check settings or use default)
        wordlist = None
        if hasattr(self, 'wordlist_path') and self.wordlist_path:
            wordlist = self.wordlist_path
        else:
            # Try common wordlist locations
            possible_wordlists = [
                '/usr/share/wordlists/rockyou.txt',
                '/usr/share/dict/words',
                str(Path.cwd() / 'data' / 'wordlists' / 'common-passwords.txt')
            ]
            for wl in possible_wordlists:
                if Path(wl).exists():
                    wordlist = wl
                    break

        if not wordlist:
            self.log("⚠️ No wordlist found! Please configure a wordlist.")
            item.setText(5, "❌ Failed")
            item.setText(7, "No wordlist available")
            return

        # Create cracker
        use_gpu = False  # TODO: Add GPU settings
        cracker = PSKCracker(capture_file, ssid, bssid, wordlist, use_gpu)

        # Connect signals
        cracker.progress_updated.connect(lambda pct, msg: self.on_crack_progress(item, pct, msg))
        cracker.key_recovered.connect(lambda s, b, key: self.on_key_recovered(item, s, b, key))
        cracker.finished.connect(lambda success, msg: self.on_crack_finished(item, success, msg))

        # Start cracking
        cracker.start()

    def on_crack_progress(self, item, percentage, message):
        """Handle cracking progress"""
        item.setText(6, f"{percentage}%")  # Progress is column 6
        item.setText(7, f"Cracking: {message}")  # Result is column 7

    def on_key_recovered(self, item, ssid, bssid, key):
        """Handle key recovery"""
        self.log(f"✅ Password Cracked: {ssid} [{bssid}]")
        self.log(f"   Key: {key}")

        # Update result column
        item.setText(7, f"Password: {key}")

        # Save to database
        try:
            from src.database.models import get_session, Network
            from datetime import datetime

            session = get_session()
            network = session.query(Network).filter_by(bssid=bssid).first()

            if network:
                network.password = key
                network.cracked_at = datetime.now()
                session.commit()
                self.log(f"💾 Saved password to database")

            session.close()
        except Exception as e:
            self.log(f"⚠️ Database save error: {e}")

    def on_crack_finished(self, item, success, message):
        """Handle cracking completion"""
        if success:
            item.setText(5, "✅ Cracked")  # Status is column 5
        else:
            item.setText(5, "❌ Not Found")  # Status is column 5
            item.setText(7, message)  # Result is column 7

    def on_attack_finished(self, item, success, message):
        """Handle attack completion"""
        if success:
            item.setText(5, "✅ Completed")  # Status is column 5
            self.log(f"✅ Attack completed: {message}")
        else:
            item.setText(5, "❌ Failed")  # Status is column 5
            item.setText(7, message)  # Result is column 7
            self.log(f"❌ Attack failed: {message}")

        self.update_queue_stats()

    def start_auto_pwn_247(self):
        """Start Auto Pwn 24/7 mode - continuously attack all uncracked networks"""
        self.auto_pwn_active = True
        self.log("💀 Auto Pwn 24/7 mode activated")
        self.log("📡 Will continuously scan database for uncracked networks...")

        # Create timer to periodically check for uncracked networks
        from PyQt6.QtCore import QTimer
        self.auto_pwn_timer = QTimer()
        self.auto_pwn_timer.timeout.connect(self.auto_pwn_cycle)
        self.auto_pwn_timer.start(30000)  # Check every 30 seconds

        # Run first cycle immediately
        self.auto_pwn_cycle()

    def auto_pwn_cycle(self):
        """Auto Pwn 24/7 cycle - query database and queue uncracked networks"""
        if not self.auto_pwn_active:
            return

        try:
            from ..database.models import get_session, Network

            session = get_session()
            try:
                # Query for uncracked networks (no password)
                # Order by attack score descending (highest priority first)
                min_score = self.min_score_spin.value()

                uncracked = session.query(Network).filter(
                    (Network.password == None) | (Network.password == ""),
                    Network.attack_score >= min_score
                ).order_by(Network.attack_score.desc()).limit(50).all()

                added_count = 0
                for network in uncracked:
                    # Check if already in queue
                    already_queued = False
                    for i in range(self.queue_tree.topLevelItemCount()):
                        item = self.queue_tree.topLevelItem(i)
                        if item.text(1) == network.bssid:
                            already_queued = True
                            break

                    if not already_queued:
                        # Add to queue
                        self.queue_target(
                            bssid=network.bssid,
                            ssid=network.ssid or "",
                            channel=str(network.channel) if network.channel else "",
                            encryption=network.encryption or ""
                        )
                        added_count += 1

                if added_count > 0:
                    self.log(f"💀 Auto Pwn: Added {added_count} new targets (score >= {min_score})")
                else:
                    self.log(f"💀 Auto Pwn: No new targets found (score >= {min_score})")

            finally:
                session.close()

        except Exception as e:
            self.log(f"⚠️ Auto Pwn cycle error: {e}")

    def pause_auto_attack(self):
        """Pause automated attack"""
        self.log("⏸️ Pausing auto attack...")

        # Pause Auto Pwn 24/7 if active
        if self.auto_pwn_timer and self.auto_pwn_timer.isActive():
            self.auto_pwn_timer.stop()
            self.log("💀 Auto Pwn 24/7 paused")

        # Pause attack processor
        if self.attack_processor_timer and self.attack_processor_timer.isActive():
            self.attack_processor_timer.stop()
            self.log("⏸️ Attack processor paused")

    def stop_auto_attack(self):
        """Stop automated attack"""
        self.log("⏹️ Stopping auto attack...")

        # Stop Auto Pwn 24/7 if active
        self.auto_pwn_active = False
        if self.auto_pwn_timer:
            self.auto_pwn_timer.stop()
            self.auto_pwn_timer = None
            self.log("💀 Auto Pwn 24/7 stopped")

        # Stop attack processor
        if self.attack_processor_timer:
            self.attack_processor_timer.stop()
            self.attack_processor_timer = None
            self.log("⏹️ Attack processor stopped")

        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

    def queue_target(self, bssid: str, ssid: str = "", channel: str = "", encryption: str = ""):
        """Add a single target to the attack queue with enhanced object display

        Args:
            bssid: Target BSSID/MAC address
            ssid: Target SSID (optional)
            channel: Target channel (optional)
            encryption: Encryption type (optional)
        """
        # Check if target already in queue
        for i in range(self.queue_tree.topLevelItemCount()):
            item = self.queue_tree.topLevelItem(i)
            # Check if BSSID already exists (with or without icon prefix)
            bssid_text = item.text(1)
            if bssid in bssid_text:
                self.log(f"⚠️ Target {bssid} already in queue")
                return

        # Fetch detailed info from database for rich display
        vendor = ""
        device_type = "Unknown"
        device_icon = "📱"  # Default icon
        attack_score = "??"
        network = None

        try:
            from src.database.models import get_session, Network, AttackQueue
            session = get_session()
            network = session.query(Network).filter_by(bssid=bssid).first()

            if network:
                vendor = network.manufacturer or ""
                attack_score = str(network.attack_score) if network.attack_score else "??"
                # Get device type from network if available
                if hasattr(network, 'device_type'):
                    device_type = network.device_type or "WiFi AP"

                # Determine icon based on vendor or device type
                vendor_lower = vendor.lower() if vendor else ""
                if "apple" in vendor_lower or "iphone" in vendor_lower:
                    device_icon = "📱"
                elif "samsung" in vendor_lower or "android" in vendor_lower:
                    device_icon = "📱"
                elif "router" in device_type.lower() or "gateway" in device_type.lower():
                    device_icon = "🌐"
                elif "cisco" in vendor_lower or "netgear" in vendor_lower or "tp-link" in vendor_lower:
                    device_icon = "📡"
                else:
                    device_icon = "📶"  # Generic WiFi icon

                # ===== SAVE TO DATABASE ATTACK QUEUE =====
                # Check if already queued in database
                existing_queue = session.query(AttackQueue).filter_by(
                    network_id=network.id,
                    status='pending'
                ).first()

                if not existing_queue:
                    # Determine attack type based on encryption
                    if encryption and "WPS" in encryption.upper():
                        attack_type = "wps"
                    else:
                        attack_type = "handshake"

                    # Use attack score as priority (higher = more priority)
                    priority = network.attack_score if network.attack_score else 50

                    # Create new queue entry
                    queue_item = AttackQueue(
                        network_id=network.id,
                        attack_type=attack_type,
                        priority=priority,
                        status='pending'
                    )
                    session.add(queue_item)
                    session.commit()
                    print(f"[DEBUG] Added {bssid} to AttackQueue database table")
                else:
                    print(f"[DEBUG] {bssid} already in AttackQueue database table")

            session.close()
        except Exception as e:
            print(f"[WARN] Could not fetch network details: {e}")

        # Create enhanced queue item with object-oriented display
        item = QTreeWidgetItem()
        item.setText(0, ssid or "(Hidden)")  # SSID

        # BSSID with vendor (like scanner tab)
        vendor_display = f" ({vendor})" if vendor else ""
        item.setText(1, f"{device_icon} {bssid}{vendor_display}")  # BSSID/MAC (Vendor)

        item.setText(2, device_type)  # Device Type
        item.setText(3, attack_score)  # Score
        item.setText(4, encryption or "Unknown")  # Encryption
        item.setText(5, "⏳ Queued")  # Status with emoji
        item.setText(6, "0%")  # Progress
        item.setText(7, "Pending")  # Result

        # Color code by status (queued = dark blue-gray)
        from PyQt6.QtGui import QBrush, QColor
        queued_color = QColor(70, 70, 90)
        for i in range(8):
            item.setBackground(i, QBrush(queued_color))
            item.setForeground(i, QBrush(QColor(200, 200, 200)))

        self.queue_tree.addTopLevelItem(item)
        self.log(f"✅ Added {bssid} ({ssid or 'Hidden'}) to queue")

        # Update stats
        self.update_queue_stats()

    def add_targets_from_scanner(self):
        """Add selected targets from scanner tab"""
        self.log("📝 Adding targets from scanner...")

        if not self.main_window:
            self.log("⚠️ Main window reference not set")
            return

        # Get scanner tab reference
        scanner_tab = getattr(self.main_window, 'scanner_tab', None)
        if not scanner_tab:
            self.log("⚠️ Scanner tab not found")
            return

        # Get the network tree from scanner tab
        network_tree = getattr(scanner_tab, 'network_tree', None)
        if not network_tree:
            self.log("⚠️ Network tree not found in scanner")
            return

        # Get selected items from scanner
        selected_items = network_tree.selectedItems()

        if not selected_items:
            self.log("⚠️ No networks selected in scanner - please select networks first")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "No Selection",
                "Please select one or more networks in the Scanner tab first,\n"
                "then click 'Add Selected Targets' to add them to the attack queue."
            )
            return

        added_count = 0
        for item in selected_items:
            # Skip if this is a child item (client) not a network
            parent = item.parent()

            # Handle both top-level networks and SSID-grouped networks
            if parent is None:
                # Top-level item - could be a network or SSID group
                network_item = item
            else:
                # Child of a group - this is the actual network
                network_item = item

            # Extract network data from tree columns
            # Column layout: SSID, BSSID/MAC, Device, Score, Enc, WPS, Clients, Pwr, Chan, Last Seen
            try:
                ssid = network_item.text(0) or ""
                bssid_col = network_item.text(1)  # Contains icon + MAC + vendor
                encryption = network_item.text(4) or ""
                channel = network_item.text(8) or ""

                # Extract MAC address from BSSID column
                import re
                mac_match = re.search(r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})', bssid_col)
                if mac_match:
                    bssid = mac_match.group(1).upper()
                else:
                    # Skip if no valid BSSID found (might be a group header)
                    continue

                # Add to queue
                self.queue_target(
                    bssid=bssid,
                    ssid=ssid,
                    channel=channel,
                    encryption=encryption
                )
                added_count += 1

            except Exception as e:
                self.log(f"⚠️ Error adding target: {e}")
                continue

        if added_count > 0:
            self.log(f"✅ Added {added_count} target(s) to attack queue")
        else:
            self.log("⚠️ No valid networks found in selection")

    def clear_queue(self):
        """Clear target queue"""
        self.queue_tree.clear()
        self.log("🗑️ Queue cleared")
        self.update_queue_stats()

    def remove_selected_targets(self):
        """Remove selected targets from queue"""
        selected = self.queue_tree.selectedItems()
        for item in selected:
            index = self.queue_tree.indexOfTopLevelItem(item)
            self.queue_tree.takeTopLevelItem(index)
        self.log(f"🗑️ Removed {len(selected)} target(s)")
        self.update_queue_stats()

    def update_queue_stats(self):
        """Update queue statistics labels"""
        total = self.queue_tree.topLevelItemCount()
        queued = 0
        attacking = 0
        completed = 0
        successful = 0
        failed = 0

        for i in range(total):
            item = self.queue_tree.topLevelItem(i)
            status = item.text(5)  # Column 5 is Status

            if "Queued" in status or "⏳" in status:
                queued += 1
            elif "Attacking" in status or "In Progress" in status or "⚔️" in status:
                attacking += 1
            elif "Completed" in status or "Success" in status or "✅" in status:
                completed += 1
                successful += 1
            elif "Failed" in status or "❌" in status:
                completed += 1
                failed += 1

        self.queued_label.setText(f"Queued: {queued}")
        self.attacking_label.setText(f"Attacking: {attacking}")
        self.completed_label.setText(f"Completed: {completed}")
        self.successful_label.setText(f"Successful: {successful}")
        self.failed_label.setText(f"Failed: {failed}")

        # Update overall progress
        if total > 0:
            self.overall_progress.setMaximum(total)
            self.overall_progress.setValue(completed)

    def log(self, message: str):
        """Add message to attack log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")
