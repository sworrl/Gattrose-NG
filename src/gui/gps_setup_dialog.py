"""
GPS Setup Dialog
Automated wizard for setting up GPS sources (Android phone, etc.)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QGroupBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import subprocess


class GPSSetupDialog(QDialog):
    """Automated GPS setup wizard"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GPS Setup Wizard")
        self.setMinimumSize(700, 600)
        self.setup_complete = False

        # Gattrose dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 5px;
                margin-top: 15px;
                padding: 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #4ecdc4;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #2a2a2a;
                color: #00ff00;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border: 1px solid #6a6a6a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
            QProgressBar {
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                background-color: #2a2a2a;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #4ecdc4;
            }
        """)

        self.init_ui()
        self.check_initial_status()

    def init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()

        # Title
        title = QLabel("🛰️ Android Phone GPS Setup")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #4ecdc4; margin: 10px;")
        layout.addWidget(title)

        # Status group
        status_group = QGroupBox("📱 Connection Status")
        status_layout = QVBoxLayout()

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        self.status_text.setPlainText("Checking for Android phone...")
        status_layout.addWidget(self.status_text)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Phone info group (shows device details when connected)
        phone_info_group = QGroupBox("📊 Phone Details")
        phone_info_layout = QVBoxLayout()

        self.phone_info_text = QTextEdit()
        self.phone_info_text.setReadOnly(True)
        self.phone_info_text.setMaximumHeight(120)
        self.phone_info_text.setPlainText("No phone detected yet...")
        phone_info_layout.addWidget(self.phone_info_text)

        phone_info_group.setLayout(phone_info_layout)
        layout.addWidget(phone_info_group)

        # Instructions group
        instructions_group = QGroupBox("📋 Setup Instructions")
        instructions_layout = QVBoxLayout()

        self.instructions_text = QTextEdit()
        self.instructions_text.setReadOnly(True)
        self.instructions_text.setMaximumHeight(250)
        instructions_layout.addWidget(self.instructions_text)

        instructions_group.setLayout(instructions_layout)
        layout.addWidget(instructions_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()

        self.check_btn = QPushButton("🔍 Check Connection")
        self.check_btn.clicked.connect(self.check_connection)

        self.help_btn = QPushButton("❓ Help")
        self.help_btn.clicked.connect(self.show_help)

        self.skip_btn = QPushButton("⏭️ Skip")
        self.skip_btn.clicked.connect(self.skip_setup)

        self.done_btn = QPushButton("✅ Done")
        self.done_btn.clicked.connect(self.accept)
        self.done_btn.setEnabled(False)

        button_layout.addWidget(self.check_btn)
        button_layout.addWidget(self.help_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.done_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def check_initial_status(self):
        """Check initial connection status"""
        self.progress_bar.setValue(10)
        QTimer.singleShot(500, self.check_connection)

    def check_connection(self):
        """Check if Android phone is connected and authorized"""
        self.status_text.clear()
        self.progress_bar.setValue(20)

        status_lines = []
        status_lines.append("=" * 60)
        status_lines.append("ANDROID PHONE GPS SETUP")
        status_lines.append("=" * 60)
        status_lines.append("")

        # Step 1: Check if phone is connected via USB
        status_lines.append("[1/4] Checking USB connection...")
        try:
            result = subprocess.run(
                ['lsusb'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if any(x in result.stdout.lower() for x in ['google', 'android', '18d1']):
                status_lines.append("      ✅ Android phone detected via USB")
                self.progress_bar.setValue(40)
            else:
                status_lines.append("      ❌ No Android phone detected")
                status_lines.append("")
                status_lines.append("      → Please connect your Android phone via USB cable")
                self.status_text.setPlainText("\n".join(status_lines))
                self.show_usb_instructions()
                self.progress_bar.setValue(0)
                return
        except Exception as e:
            status_lines.append(f"      ❌ Error checking USB: {e}")
            self.status_text.setPlainText("\n".join(status_lines))
            self.progress_bar.setValue(0)
            return

        # Step 2: Check ADB
        status_lines.append("")
        status_lines.append("[2/4] Checking ADB...")
        try:
            result = subprocess.run(['which', 'adb'], capture_output=True, timeout=2)
            if result.returncode == 0:
                status_lines.append("      ✅ ADB is installed")
                self.progress_bar.setValue(60)
            else:
                status_lines.append("      ❌ ADB not found")
                self.status_text.setPlainText("\n".join(status_lines))
                self.progress_bar.setValue(40)
                return
        except:
            status_lines.append("      ❌ ADB check failed")
            self.status_text.setPlainText("\n".join(status_lines))
            return

        # Step 3: Check ADB authorization
        status_lines.append("")
        status_lines.append("[3/4] Checking ADB authorization...")
        try:
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                timeout=5
            )

            lines = result.stdout.strip().split('\n')[1:]
            authorized = [l for l in lines if l.strip() and 'device' in l and 'unauthorized' not in l.lower()]
            unauthorized = [l for l in lines if 'unauthorized' in l.lower()]

            if authorized:
                status_lines.append("      ✅ Phone is authorized!")
                self.progress_bar.setValue(80)

                # Get detailed phone info
                self._update_phone_info()
            elif unauthorized:
                status_lines.append("      ⚠️  Phone detected but NOT authorized")
                status_lines.append("")
                status_lines.append("      → Check your phone screen for authorization dialog")
                status_lines.append("      → Tap 'Allow' and check 'Always allow'")
                self.status_text.setPlainText("\n".join(status_lines))
                self.show_auth_instructions()
                self.progress_bar.setValue(60)
                return
            else:
                status_lines.append("      ⚠️  Phone not detected by ADB")
                status_lines.append("")
                status_lines.append("      → USB debugging may not be enabled")
                self.status_text.setPlainText("\n".join(status_lines))
                self.show_usb_debug_instructions()
                self.progress_bar.setValue(40)
                return

        except Exception as e:
            status_lines.append(f"      ❌ ADB check failed: {e}")
            self.status_text.setPlainText("\n".join(status_lines))
            return

        # Step 4: Test GPS data
        status_lines.append("")
        status_lines.append("[4/4] Testing GPS data...")
        try:
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'location'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if 'gps:' in result.stdout.lower() or 'location' in result.stdout.lower():
                status_lines.append("      ✅ GPS data accessible!")
                status_lines.append("")
                status_lines.append("=" * 60)
                status_lines.append("🎉 SETUP COMPLETE!")
                status_lines.append("=" * 60)
                status_lines.append("")
                status_lines.append("Your Android phone GPS is now ready to use.")
                status_lines.append("")
                status_lines.append("The GPS service will automatically use phone GPS data")
                status_lines.append("with accuracy of ±10-20 meters.")

                self.progress_bar.setValue(100)
                self.setup_complete = True
                self.done_btn.setEnabled(True)
                self.check_btn.setEnabled(False)
            else:
                status_lines.append("      ⚠️  Could not read GPS data")
                status_lines.append("")
                status_lines.append("      → Make sure Location is enabled on phone")
                self.progress_bar.setValue(80)

        except Exception as e:
            status_lines.append(f"      ⚠️  GPS test failed: {e}")
            self.progress_bar.setValue(80)

        self.status_text.setPlainText("\n".join(status_lines))

    def show_usb_instructions(self):
        """Show USB connection instructions"""
        instructions = []
        instructions.append("STEP 1: Connect Your Phone")
        instructions.append("")
        instructions.append("1. Connect your Android phone to the computer via USB cable")
        instructions.append("")
        instructions.append("2. On your phone, you may see:")
        instructions.append("   • 'USB for...' notification")
        instructions.append("   • Select 'File Transfer' or 'MTP' mode")
        instructions.append("")
        instructions.append("3. Click 'Check Connection' button when connected")

        self.instructions_text.setPlainText("\n".join(instructions))

    def show_usb_debug_instructions(self):
        """Show USB debugging enable instructions"""
        instructions = []
        instructions.append("STEP 2: Enable USB Debugging")
        instructions.append("")
        instructions.append("On Your Android Phone:")
        instructions.append("")
        instructions.append("1. Open Settings")
        instructions.append("")
        instructions.append("2. Go to 'About Phone' (or 'About Device')")
        instructions.append("")
        instructions.append("3. Tap 'Build Number' 7 times")
        instructions.append("   → You'll see 'You are now a developer!'")
        instructions.append("")
        instructions.append("4. Go back to Settings")
        instructions.append("")
        instructions.append("5. Open 'System' → 'Developer Options'")
        instructions.append("   (or 'Developer Options' directly)")
        instructions.append("")
        instructions.append("6. Enable 'USB Debugging'")
        instructions.append("")
        instructions.append("7. Click 'Check Connection' when done")

        self.instructions_text.setPlainText("\n".join(instructions))

    def show_auth_instructions(self):
        """Show authorization instructions"""
        instructions = []
        instructions.append("STEP 3: Authorize This Computer")
        instructions.append("")
        instructions.append("Check Your Phone Screen Now:")
        instructions.append("")
        instructions.append("You should see a dialog that says:")
        instructions.append("  'Allow USB debugging?'")
        instructions.append("")
        instructions.append("1. ✅ Check the box 'Always allow from this computer'")
        instructions.append("")
        instructions.append("2. Tap 'Allow' or 'OK'")
        instructions.append("")
        instructions.append("3. Click 'Check Connection' button below")
        instructions.append("")
        instructions.append("If you don't see the dialog:")
        instructions.append("• Unplug and replug the USB cable")
        instructions.append("• Try a different USB port")

        self.instructions_text.setPlainText("\n".join(instructions))

    def show_help(self):
        """Show help information"""
        from PyQt6.QtWidgets import QMessageBox

        help_text = """
<h3>GPS Setup Help</h3>

<p><b>What is this?</b><br>
This wizard helps you set up your Android phone as a GPS source
for accurate wardriving coordinates.</p>

<p><b>Why use phone GPS?</b><br>
• Much more accurate than GeoIP (±10-20m vs ±1-100km)<br>
• Works anywhere your phone has GPS signal<br>
• No additional hardware needed</p>

<p><b>Common Issues:</b></p>

<p><b>Phone not detected:</b><br>
- Try a different USB cable<br>
- Try a different USB port<br>
- Make sure phone is unlocked</p>

<p><b>Can't find Developer Options:</b><br>
- Settings vary by phone manufacturer<br>
- Search for "Developer" in Settings<br>
- Some phones: Settings → System → Advanced</p>

<p><b>Authorization keeps asking:</b><br>
- Make sure to check "Always allow"<br>
- Revoke old authorizations: Developer Options → "Revoke USB debugging"</p>

<p><b>Need more help?</b><br>
Run: <code>./setup_phone_gps.sh</code> in terminal</p>
"""

        msg = QMessageBox(self)
        msg.setWindowTitle("GPS Setup Help")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def _update_phone_info(self):
        """Update phone information display"""
        try:
            phone_lines = []
            phone_lines.append("=" * 60)
            phone_lines.append("PHONE INFORMATION")
            phone_lines.append("=" * 60)
            phone_lines.append("")

            # Get device model
            result = subprocess.run(
                ['adb', 'shell', 'getprop', 'ro.product.model'],
                capture_output=True,
                text=True,
                timeout=3
            )
            device_model = result.stdout.strip() if result.returncode == 0 else "Unknown"

            # Get Android version
            result = subprocess.run(
                ['adb', 'shell', 'getprop', 'ro.build.version.release'],
                capture_output=True,
                text=True,
                timeout=3
            )
            android_version = result.stdout.strip() if result.returncode == 0 else "Unknown"

            phone_lines.append(f"📱 Device: {device_model}")
            phone_lines.append(f"🤖 Android: {android_version}")
            phone_lines.append("")

            # Get battery info
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'battery'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                battery_level = None
                battery_status = None

                for line in result.stdout.split('\n'):
                    if 'level:' in line.lower():
                        try:
                            battery_level = int(line.split(':')[1].strip())
                        except (ValueError, IndexError):
                            pass
                    elif 'status:' in line.lower():
                        status_code = line.split(':')[1].strip()
                        status_map = {
                            '2': 'Charging',
                            '3': 'Discharging',
                            '4': 'Not charging',
                            '5': 'Full'
                        }
                        battery_status = status_map.get(status_code, status_code)

                if battery_level is not None:
                    battery_icon = "🔋" if battery_level > 20 else "🪫"
                    phone_lines.append(f"{battery_icon} Battery: {battery_level}%")
                    if battery_status:
                        phone_lines.append(f"⚡ Status: {battery_status}")
                    phone_lines.append("")

            # Get GPS satellites (if available)
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'location'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'satellites' in line.lower() and 'used in fix' in line.lower():
                        try:
                            satellites = int(line.split(':')[-1].strip())
                            phone_lines.append(f"🛰️  GPS Satellites: {satellites}")
                            break
                        except (ValueError, IndexError):
                            pass

            phone_lines.append("")
            phone_lines.append("=" * 60)

            self.phone_info_text.setPlainText("\n".join(phone_lines))

        except Exception as e:
            self.phone_info_text.setPlainText(f"Could not read phone info: {e}")

    def skip_setup(self):
        """Skip setup for now"""
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Skip GPS Setup?",
            "Skip Android phone GPS setup?\n\n"
            "You can run this wizard later from:\n"
            "• Click the GPS status in the status bar\n"
            "• Or run: ./setup_phone_gps.sh\n\n"
            "The system will use GeoIP (less accurate) until configured.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.reject()


def show_gps_setup_wizard(parent=None):
    """Show GPS setup wizard and return True if completed"""
    dialog = GPSSetupDialog(parent)
    result = dialog.exec()
    return dialog.setup_complete if result == QDialog.DialogCode.Accepted else False
