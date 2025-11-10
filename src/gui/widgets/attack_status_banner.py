"""
Attack Status Banner for Gattrose-NG
Prominent banner displayed during active attacks
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime


class AttackStatusBanner(QFrame):
    """Large, prominent status banner for attack progress"""

    clicked = pyqtSignal()  # Emitted when banner is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.attack_start_time = None
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_index = 0
        self.init_ui()

        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate)
        self.animation_timer.start(100)  # 100ms per frame

        # Auto-hide by default
        self.setVisible(False)

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E74C3C, stop:1 #C0392B);
                border: 3px solid #A93226;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        self.setMinimumHeight(100)
        self.setMaximumHeight(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mousePressEvent = lambda e: self.clicked.emit()

        main_layout = QHBoxLayout()

        # Animated spinner
        self.spinner_label = QLabel(self.spinner_chars[0])
        self.spinner_label.setStyleSheet("font-size: 48pt; color: white;")
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner_label.setFixedWidth(80)
        main_layout.addWidget(self.spinner_label)

        # Status text
        text_layout = QVBoxLayout()

        self.title_label = QLabel("🔓 WPS ATTACK IN PROGRESS")
        self.title_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: white;")
        text_layout.addWidget(self.title_label)

        self.details_label = QLabel("Target: --\nElapsed: --")
        self.details_label.setStyleSheet("font-size: 14pt; color: #ECF0F1;")
        text_layout.addWidget(self.details_label)

        main_layout.addLayout(text_layout)

        # Progress info
        progress_layout = QVBoxLayout()
        progress_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.progress_label = QLabel("0%")
        self.progress_label.setStyleSheet("font-size: 36pt; font-weight: bold; color: white;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_label)

        self.eta_label = QLabel("ETA: --")
        self.eta_label.setStyleSheet("font-size: 12pt; color: #ECF0F1;")
        self.eta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.eta_label)

        main_layout.addLayout(progress_layout)

        self.setLayout(main_layout)

    def show_wps_attack(self, target_ssid: str, target_bssid: str, attack_type: str = "WPS"):
        """Show banner for WPS attack"""
        self.attack_start_time = datetime.now()

        if attack_type == "wps_pixie":
            self.title_label.setText("⚡ WPS PIXIE DUST ATTACK")
            self.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #9B59B6, stop:1 #8E44AD);
                    border: 3px solid #7D3C98;
                    border-radius: 10px;
                    padding: 15px;
                }
            """)
        elif attack_type == "wps_pin":
            self.title_label.setText("🔐 WPS PIN BRUTEFORCE")
            self.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #E74C3C, stop:1 #C0392B);
                    border: 3px solid #A93226;
                    border-radius: 10px;
                    padding: 15px;
                }
            """)
        else:
            self.title_label.setText("🔓 WPS ATTACK")

        self.details_label.setText(
            f"Target: {target_ssid} ({target_bssid})\n"
            f"Started: {self.attack_start_time.strftime('%H:%M:%S')}"
        )
        self.progress_label.setText("0%")
        self.eta_label.setText("ETA: Calculating...")
        self.setVisible(True)

    def show_handshake_capture(self, target_ssid: str, target_bssid: str):
        """Show banner for handshake capture"""
        self.attack_start_time = datetime.now()
        self.title_label.setText("🤝 HANDSHAKE CAPTURE")
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498DB, stop:1 #2980B9);
                border: 3px solid #21618C;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        self.details_label.setText(
            f"Target: {target_ssid} ({target_bssid})\n"
            f"Waiting for client reconnection..."
        )
        self.progress_label.setText("--")
        self.eta_label.setText("ETA: 1-5 min")
        self.setVisible(True)

    def show_deauth_attack(self, target_ssid: str, target_bssid: str, client_mac: str = None):
        """Show banner for deauth attack"""
        self.attack_start_time = datetime.now()
        self.title_label.setText("💥 DEAUTH ATTACK")
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E67E22, stop:1 #D68910);
                border: 3px solid #BA4A00;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        if client_mac:
            details = f"Target: {target_ssid} ({target_bssid})\nClient: {client_mac}"
        else:
            details = f"Target: {target_ssid} ({target_bssid})\nAll clients"

        self.details_label.setText(details)
        self.progress_label.setText("--")
        self.eta_label.setText("ETA: < 1 min")
        self.setVisible(True)

    def show_hashcat_crack(self, target_ssid: str, wordlist_size: int):
        """Show banner for hashcat cracking"""
        self.attack_start_time = datetime.now()
        self.title_label.setText("💻 HASHCAT GPU CRACKING")
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #16A085, stop:1 #117A65);
                border: 3px solid #0E6655;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        self.details_label.setText(
            f"Target: {target_ssid}\n"
            f"Wordlist: {wordlist_size:,} passwords"
        )
        self.progress_label.setText("0%")
        self.eta_label.setText("ETA: Calculating...")
        self.setVisible(True)

    def update_progress(self, progress: int, eta_seconds: int = None):
        """Update progress and ETA"""
        self.progress_label.setText(f"{progress}%")

        if eta_seconds is not None:
            eta_str = self.format_time(eta_seconds)
            self.eta_label.setText(f"ETA: {eta_str}")

        # Update elapsed time in details
        if self.attack_start_time:
            elapsed = (datetime.now() - self.attack_start_time).total_seconds()
            elapsed_str = self.format_time(int(elapsed))

            # Update details label (keep first line, update elapsed)
            current_text = self.details_label.text()
            lines = current_text.split('\n')
            if len(lines) >= 2:
                lines[-1] = f"Elapsed: {elapsed_str}"
                self.details_label.setText('\n'.join(lines))

    def format_time(self, seconds: int) -> str:
        """Format seconds into human readable time"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def hide_banner(self):
        """Hide the banner"""
        self.setVisible(False)
        self.attack_start_time = None

    def animate(self):
        """Animate the spinner"""
        if self.isVisible():
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            self.spinner_label.setText(self.spinner_chars[self.spinner_index])

            # Update elapsed time every second
            if self.attack_start_time and self.spinner_index % 10 == 0:
                elapsed = (datetime.now() - self.attack_start_time).total_seconds()
                elapsed_str = self.format_time(int(elapsed))

                current_text = self.details_label.text()
                lines = current_text.split('\n')
                if len(lines) >= 2:
                    # Update the elapsed/status line
                    if lines[-1].startswith("Elapsed:"):
                        lines[-1] = f"Elapsed: {elapsed_str}"
                        self.details_label.setText('\n'.join(lines))
