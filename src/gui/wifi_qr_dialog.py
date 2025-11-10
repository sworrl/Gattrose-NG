"""
WiFi QR Code Dialog
Android-style QR code display for sharing WiFi credentials
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
import qrcode
from io import BytesIO


class WiFiQRDialog(QDialog):
    """Dialog to display WiFi credentials as QR code (Android style)"""

    def __init__(self, ssid: str, password: str, encryption: str = "WPA", parent=None):
        super().__init__(parent)
        self.ssid = ssid
        self.password = password
        self.encryption = encryption
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle(f"WiFi QR Code - {self.ssid}")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)

        layout = QVBoxLayout()

        # Header
        header = QLabel(f"📱 Scan to Connect")
        header.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Generate and display QR code
        qr_label = self.generate_qr_code()
        layout.addWidget(qr_label)

        # Network information
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(8)

        ssid_label = QLabel(f"<b>Network:</b> {self.ssid}")
        ssid_label.setStyleSheet("font-size: 16px; padding: 5px;")
        info_layout.addWidget(ssid_label)

        password_label = QLabel(f"<b>Password:</b> {self.password}")
        password_label.setStyleSheet("font-size: 16px; padding: 5px;")
        password_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info_layout.addWidget(password_label)

        encryption_label = QLabel(f"<b>Security:</b> {self.encryption}")
        encryption_label.setStyleSheet("font-size: 14px; padding: 5px; color: #666;")
        info_layout.addWidget(encryption_label)

        layout.addWidget(info_widget)

        # Instructions
        instructions = QLabel(
            "Open your phone's camera app and point it at the QR code.\n"
            "Tap the notification to connect to the network."
        )
        instructions.setStyleSheet("font-size: 12px; color: #888; padding: 10px;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Buttons
        button_layout = QHBoxLayout()

        copy_password_btn = QPushButton("📋 Copy Password")
        copy_password_btn.clicked.connect(self.copy_password)
        button_layout.addWidget(copy_password_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def generate_qr_code(self) -> QLabel:
        """Generate QR code for WiFi credentials"""
        # WiFi QR code format: WIFI:T:WPA;S:SSID;P:password;;
        # T = Type (WPA, WEP, or nopass)
        # S = SSID
        # P = Password
        # H = Hidden (true/false)

        # Map encryption types
        enc_type = "WPA"
        if "WEP" in self.encryption.upper():
            enc_type = "WEP"
        elif "WPA3" in self.encryption.upper():
            enc_type = "WPA"  # WPA3 uses WPA in QR code
        elif not self.password:
            enc_type = "nopass"

        # Escape special characters
        ssid_escaped = self.ssid.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")
        password_escaped = self.password.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")

        # Generate QR code data
        if enc_type == "nopass":
            qr_data = f"WIFI:T:nopass;S:{ssid_escaped};;"
        else:
            qr_data = f"WIFI:T:{enc_type};S:{ssid_escaped};P:{password_escaped};;"

        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        # Convert to image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert PIL image to QPixmap
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        qimage = QImage()
        qimage.loadFromData(buffer.read())
        pixmap = QPixmap.fromImage(qimage)

        # Create label with QR code
        qr_label = QLabel()
        qr_label.setPixmap(pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio))
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        return qr_label

    def copy_password(self):
        """Copy password to clipboard"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.password)

        # Show brief confirmation
        self.sender().setText("✓ Copied!")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self.sender().setText("📋 Copy Password"))
