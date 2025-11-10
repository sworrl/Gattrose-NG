#!/usr/bin/env python3
"""
Gattrose Cracking Tasks Tray Icon
Monitors active WPA/WPS cracking tasks and displays progress
"""

import sys
import json
import requests
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import QTimer, Qt

PROJECT_ROOT = Path('/opt/gattrose-ng')
sys.path.insert(0, str(PROJECT_ROOT))


class CrackingTrayApp:
    """Cracking tasks monitor system tray application"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Prevent multiple instances
        self._check_single_instance()

        self.tray_icon = None
        self.menu = None

        # Attack status
        self.active_attacks = []
        self.total_cracked = 0
        self.running_count = 0

        self._init_tray_icon()
        self._init_menu()
        self._start_status_monitoring()

    def _check_single_instance(self):
        """Ensure only one instance is running"""
        import fcntl
        self.lock_file = open('/tmp/gattrose-cracking-tray.lock', 'w')
        try:
            fcntl.lockf(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            print("[!] Cracking tray is already running")
            sys.exit(0)

    def _init_tray_icon(self):
        """Initialize system tray icon"""
        icon = self._create_crack_icon("gray", 0)
        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip("Cracking Tasks - Idle")
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _create_crack_icon(self, status: str, count: int = 0) -> QIcon:
        """Create a cracking icon with status color and count

        Args:
            status: "green" (cracking active), "yellow" (completed),
                   "red" (failed), "gray" (idle)
            count: Number of active tasks
        """
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Color based on status
        colors = {
            "green": QColor(0, 255, 0),
            "yellow": QColor(255, 200, 0),
            "red": QColor(255, 0, 0),
            "gray": QColor(128, 128, 128)
        }
        color = colors.get(status, colors["gray"])

        # Draw key/lock shape
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)

        # Lock body
        painter.drawRoundedRect(22, 28, 20, 24, 3, 3)

        # Lock shackle
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(color)
        painter.setPen(Qt.PenStyle.SolidLine)
        pen = painter.pen()
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawArc(24, 16, 16, 20, 0, 180 * 16)

        # Draw count if > 0
        if count > 0:
            painter.setBrush(QColor(255, 50, 50))
            painter.drawEllipse(42, 8, 18, 18)

            painter.setPen(QColor(255, 255, 255))
            font = QFont()
            font.setPixelSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(42, 8, 18, 18, Qt.AlignmentFlag.AlignCenter, str(count))

        painter.end()
        return QIcon(pixmap)

    def _init_menu(self):
        """Initialize context menu"""
        self.menu = QMenu()

        # Status section
        self.status_action = QAction("Cracking Tasks")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.menu.addSeparator()

        # Attack summary
        self.running_action = QAction("Active: 0")
        self.running_action.setEnabled(False)
        self.menu.addAction(self.running_action)

        self.cracked_action = QAction("Cracked: 0")
        self.cracked_action.setEnabled(False)
        self.menu.addAction(self.cracked_action)

        self.menu.addSeparator()

        # Recent attacks section
        self.recent_label = QAction("Recent Attacks:")
        self.recent_label.setEnabled(False)
        self.menu.addAction(self.recent_label)

        # Placeholder for attack items (will be dynamically added)
        self.attack_actions = []

        self.menu.addSeparator()

        # Actions
        refresh_action = QAction("Refresh Status")
        refresh_action.triggered.connect(self._refresh_status)
        self.menu.addAction(refresh_action)

        self.menu.addSeparator()

        # Quit
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.menu)

    def _start_status_monitoring(self):
        """Start periodic status checks"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(3000)  # Check every 3 seconds

        # Initial update
        self._update_status()

    def _update_status(self):
        """Update cracking status from API"""
        try:
            # Query orchestrator API for attack status
            response = requests.get(
                'http://localhost:5555/api/v3/attacks/status',
                timeout=2
            )

            if response.status_code == 200:
                data = response.json()

                # Parse attack data
                if data.get('success'):
                    attack_data = data.get('data', {})
                    self.active_attacks = attack_data.get('attacks', [])
                    self.running_count = len([a for a in self.active_attacks if a.get('status') == 'running'])
                    self.total_cracked = attack_data.get('total_cracked', 0)
            else:
                # API not available or no data
                self.active_attacks = []
                self.running_count = 0

        except requests.exceptions.ConnectionError:
            # Orchestrator not running
            self.active_attacks = []
            self.running_count = 0
        except Exception as e:
            # Other error
            pass

        # Update UI
        self._update_ui()

    def _build_detailed_tooltip(self):
        """Build detailed tooltip with attack information"""
        lines = ["Cracking Tasks Monitor"]
        lines.append("=" * 30)

        # Summary
        lines.append(f"Active Attacks: {self.running_count}")
        lines.append(f"Total Cracked: {self.total_cracked}")
        lines.append("")

        # Active attacks detail
        if self.running_count > 0:
            lines.append("Running Attacks:")
            running_attacks = [a for a in self.active_attacks if a.get('status') == 'running']

            for attack in running_attacks[:5]:  # Show top 5
                target = attack.get('bssid', 'Unknown')[:17]
                attack_type = attack.get('type', 'unknown').upper()
                progress = attack.get('progress', 0)
                elapsed = attack.get('elapsed_seconds', 0)

                # Format elapsed time
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

                lines.append(f"  • {target}")
                lines.append(f"    Type: {attack_type} | {progress}% | {time_str}")
        elif self.active_attacks:
            # Show completed/failed attacks
            lines.append("Recent Results:")
            for attack in self.active_attacks[:3]:
                target = attack.get('bssid', 'Unknown')[:17]
                attack_type = attack.get('type', 'unknown').upper()
                status_text = attack.get('status', 'unknown')

                if status_text == 'completed':
                    icon = "✓"
                elif status_text == 'failed':
                    icon = "✗"
                else:
                    icon = "?"

                lines.append(f"  {icon} {target} ({attack_type})")
        else:
            lines.append("No active or recent attacks")

        return "\n".join(lines)

    def _update_ui(self):
        """Update tray icon and menu based on status"""
        # Determine icon status
        if self.running_count > 0:
            status = "green"
        elif self.total_cracked > 0:
            status = "yellow"
        else:
            status = "gray"

        # Build detailed tooltip
        tooltip = self._build_detailed_tooltip()

        # Update icon
        self.tray_icon.setIcon(self._create_crack_icon(status, self.running_count))
        self.tray_icon.setToolTip(tooltip)

        # Update menu
        self.running_action.setText(f"Active: {self.running_count}")
        self.cracked_action.setText(f"Cracked: {self.total_cracked}")

        # Clear old attack actions
        for action in self.attack_actions:
            self.menu.removeAction(action)
        self.attack_actions.clear()

        # Add current attacks to menu
        if self.active_attacks:
            # Get most recent 5 attacks
            recent = self.active_attacks[:5]

            for attack in recent:
                target = attack.get('bssid', 'Unknown')
                attack_type = attack.get('type', 'unknown')
                status_text = attack.get('status', 'unknown')
                progress = attack.get('progress', 0)

                # Create menu item
                if status_text == 'running':
                    text = f"• {target[:17]} - {attack_type} ({progress}%)"
                elif status_text == 'completed':
                    text = f"✓ {target[:17]} - Success!"
                elif status_text == 'failed':
                    text = f"✗ {target[:17]} - Failed"
                else:
                    text = f"? {target[:17]} - {status_text}"

                action = QAction(text)
                action.setEnabled(False)
                self.menu.insertAction(self.recent_label.menu(), action)
                self.attack_actions.append(action)
        else:
            # No attacks
            action = QAction("  (none)")
            action.setEnabled(False)
            self.menu.insertAction(self.recent_label.menu(), action)
            self.attack_actions.append(action)

    def _on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._refresh_status()

    def _refresh_status(self):
        """Force status refresh"""
        print("[*] Refreshing cracking status...")
        self._update_status()
        self.tray_icon.showMessage(
            "Status Refresh",
            f"{self.running_count} active, {self.total_cracked} cracked",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def quit(self):
        """Quit the application"""
        print("[*] Quitting cracking tray...")
        self.app.quit()

    def run(self):
        """Run the application"""
        self.tray_icon.show()
        print("[*] Cracking tasks tray started")
        return self.app.exec()


def main():
    print("[*] Starting Cracking Tasks Tray...")
    app = CrackingTrayApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
