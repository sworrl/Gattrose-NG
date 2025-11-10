"""
System Tray Integration and Notifications
Provides system tray icon and desktop notifications
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path
import subprocess


class NotificationManager(QObject):
    """Manages desktop notifications with customizable settings"""

    # Notification types
    NEW_AP_DISCOVERED = "new_ap"
    WPS_NETWORK_FOUND = "wps_found"
    HANDSHAKE_CAPTURED = "handshake"
    ATTACK_SUCCESS = "attack_success"
    ATTACK_FAILED = "attack_failed"
    KEY_RECOVERED = "key_recovered"
    CRITICAL_VULNERABILITY = "critical_vuln"
    SCAN_STARTED = "scan_started"
    SCAN_STOPPED = "scan_stopped"
    WIRELESS_CARD_ADDED = "card_added"
    WIRELESS_CARD_REMOVED = "card_removed"
    WIRELESS_CARD_ROLE_CHANGED = "card_role_changed"

    def __init__(self):
        super().__init__()
        self.enabled_notifications = {
            self.NEW_AP_DISCOVERED: True,
            self.WPS_NETWORK_FOUND: True,
            self.HANDSHAKE_CAPTURED: True,
            self.ATTACK_SUCCESS: True,
            self.ATTACK_FAILED: False,  # Disabled by default (too noisy)
            self.KEY_RECOVERED: True,
            self.CRITICAL_VULNERABILITY: True,
            self.SCAN_STARTED: True,
            self.SCAN_STOPPED: False,
            self.WIRELESS_CARD_ADDED: True,
            self.WIRELESS_CARD_REMOVED: True,
            self.WIRELESS_CARD_ROLE_CHANGED: True,
        }

        self.notification_sound = True
        self.tray_icon = None

    def set_tray_icon(self, tray_icon):
        """Set reference to system tray icon for showing messages"""
        self.tray_icon = tray_icon

    def is_enabled(self, notification_type: str) -> bool:
        """Check if a notification type is enabled"""
        return self.enabled_notifications.get(notification_type, False)

    def set_enabled(self, notification_type: str, enabled: bool):
        """Enable or disable a notification type"""
        self.enabled_notifications[notification_type] = enabled

    def notify(self, title: str, message: str, notification_type: str = None,
               urgency: str = "normal", timeout: int = 5000):
        """
        Show desktop notification

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification (for filtering)
            urgency: low, normal, or critical
            timeout: Milliseconds to show (0 = until dismissed)
        """
        # Check if this notification type is enabled
        if notification_type and not self.is_enabled(notification_type):
            return

        # Try system tray notification first
        if self.tray_icon:
            icon = QSystemTrayIcon.MessageIcon.Information
            if urgency == "critical":
                icon = QSystemTrayIcon.MessageIcon.Critical
            elif urgency == "warning":
                icon = QSystemTrayIcon.MessageIcon.Warning

            self.tray_icon.showMessage(title, message, icon, timeout)

        # Fallback to notify-send
        else:
            try:
                subprocess.run([
                    'notify-send',
                    f'--urgency={urgency}',
                    f'--expire-time={timeout}',
                    f'--app-name=Gattrose-NG',
                    title,
                    message
                ], check=False)
            except Exception as e:
                print(f"[!] Failed to send notification: {e}")

    def notify_new_ap(self, ssid: str, bssid: str, encryption: str, score: int):
        """Notify about new AP discovered"""
        if score >= 80:
            urgency = "critical"
            emoji = "🎯"
        elif score >= 60:
            urgency = "normal"
            emoji = "⚠️"
        else:
            urgency = "low"
            emoji = "📡"

        self.notify(
            f"{emoji} New Network Discovered",
            f"{ssid or '(Hidden)'}\n{bssid}\n{encryption} - Score: {score}",
            notification_type=self.NEW_AP_DISCOVERED,
            urgency=urgency
        )

    def notify_wps_found(self, ssid: str, bssid: str, locked: bool):
        """Notify about WPS network"""
        status = "LOCKED" if locked else "UNLOCKED"
        urgency = "critical" if not locked else "normal"

        self.notify(
            f"🔓 WPS Network Found!",
            f"{ssid or '(Hidden)'}\n{bssid}\nWPS: {status}",
            notification_type=self.WPS_NETWORK_FOUND,
            urgency=urgency
        )

    def notify_handshake(self, ssid: str, bssid: str):
        """Notify about captured handshake"""
        self.notify(
            "🤝 Handshake Captured!",
            f"{ssid or '(Hidden)'}\n{bssid}",
            notification_type=self.HANDSHAKE_CAPTURED,
            urgency="normal"
        )

    def notify_key_recovered(self, ssid: str, key: str):
        """Notify about recovered key"""
        self.notify(
            "🔑 Key Recovered!",
            f"{ssid}\nKey: {key}",
            notification_type=self.KEY_RECOVERED,
            urgency="critical",
            timeout=10000
        )

    def notify_attack_success(self, ssid: str, attack_type: str):
        """Notify about successful attack"""
        self.notify(
            "✅ Attack Successful",
            f"{ssid}\nAttack: {attack_type}",
            notification_type=self.ATTACK_SUCCESS,
            urgency="normal"
        )

    def notify_critical_vuln(self, ssid: str, vulnerability: str):
        """Notify about critical vulnerability"""
        self.notify(
            "⚠️ Critical Vulnerability",
            f"{ssid}\n{vulnerability}",
            notification_type=self.CRITICAL_VULNERABILITY,
            urgency="critical"
        )

    def notify_card_added(self, interface: str, driver: str, card_count: int):
        """Notify about wireless card added"""
        self.notify(
            "📶 Wireless Card Detected",
            f"New card: {interface} ({driver})\nTotal cards: {card_count}\nClick to configure card roles",
            notification_type=self.WIRELESS_CARD_ADDED,
            urgency="normal",
            timeout=8000
        )

    def notify_card_removed(self, interface: str):
        """Notify about wireless card removed"""
        self.notify(
            "📴 Wireless Card Removed",
            f"Card {interface} was removed",
            notification_type=self.WIRELESS_CARD_REMOVED,
            urgency="low"
        )

    def notify_card_role_changed(self, interface: str, role: str):
        """Notify about card role changed"""
        role_emoji = {
            "scanner": "📡",
            "attacker": "⚔️",
            "both": "🔄"
        }
        emoji = role_emoji.get(role.lower(), "📶")

        self.notify(
            f"{emoji} Card Role Changed",
            f"{interface} → {role.upper()}",
            notification_type=self.WIRELESS_CARD_ROLE_CHANGED,
            urgency="low"
        )


class SystemTrayIcon(QSystemTrayIcon):
    """System tray icon for Gattrose-NG"""

    # Signals
    show_window_requested = pyqtSignal()
    start_scan_requested = pyqtSignal()
    stop_scan_requested = pyqtSignal()
    configure_cards_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        # Find icon
        icon_path = Path(__file__).parent.parent.parent / "assets" / "gattrose-ng.png"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
        else:
            icon = QIcon.fromTheme("network-wireless")

        super().__init__(icon, parent)

        self.setToolTip("Gattrose-NG - Wireless Pentesting Suite")

        # Create menu
        self.menu = QMenu()

        # Show/Hide action
        self.show_action = QAction("Show Window", self)
        self.show_action.triggered.connect(self.show_window_requested.emit)
        self.menu.addAction(self.show_action)

        self.menu.addSeparator()

        # Scan actions
        self.start_scan_action = QAction("Start Scan", self)
        self.start_scan_action.triggered.connect(self.start_scan_requested.emit)
        self.menu.addAction(self.start_scan_action)

        self.stop_scan_action = QAction("Stop Scan", self)
        self.stop_scan_action.triggered.connect(self.stop_scan_requested.emit)
        self.stop_scan_action.setEnabled(False)
        self.menu.addAction(self.stop_scan_action)

        self.menu.addSeparator()

        # Card configuration
        self.configure_cards_action = QAction("Configure Wireless Cards", self)
        self.configure_cards_action.triggered.connect(self.configure_cards_requested.emit)
        self.menu.addAction(self.configure_cards_action)

        self.menu.addSeparator()

        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(quit_action)

        self.setContextMenu(self.menu)

        # Double-click shows window
        self.activated.connect(self.on_activated)

    def on_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()

    def set_scanning(self, scanning: bool):
        """Update menu based on scanning status"""
        self.start_scan_action.setEnabled(not scanning)
        self.stop_scan_action.setEnabled(scanning)

        if scanning:
            self.setToolTip("Gattrose-NG - Scanning...")
        else:
            self.setToolTip("Gattrose-NG - Idle")

    def update_stats(self, ap_count: int, client_count: int):
        """Update tooltip with current stats"""
        self.setToolTip(f"Gattrose-NG\nAPs: {ap_count} | Clients: {client_count}")
