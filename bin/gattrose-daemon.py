import sys
import time
import signal
import os
from pathlib import Path

# Import Gattrose modules
from src.utils.config_db import DBConfig
from src.database.manager import DatabaseManager
from src.tools.wifi_monitor import WiFiMonitorManager
from src.utils.logger import main_logger


class GattroseDaemon:
    """Background daemon for continuous scanning"""

    def __init__(self):
        self.running = False
        self.config = DBConfig()
        self.db = DatabaseManager()
        self.scanners = {}

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        main_logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)

    def start(self):
        """Start daemon"""
        main_logger.info("Starting Gattrose-NG daemon...")

        self.running = True

        # Start WiFi scanning if enabled
        if self.config.get('wifi.enabled', True):
            self.start_wifi_scanning()

        # Start Bluetooth scanning if enabled
        if self.config.get('bluetooth.enabled', True):
            self.start_bluetooth_scanning()

        # Start SDR scanning if enabled
        if self.config.get('sdr.enabled', True):
            self.start_sdr_scanning()

        main_logger.info("Daemon started successfully")
        main_logger.info("Press Ctrl+C to stop")

        # Main loop
        try:
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            main_logger.info("Interrupted, shutting down...")

        self.stop()

    def stop(self):
        """Stop daemon"""
        main_logger.info("Stopping Gattrose-NG daemon...")

        self.running = False

        # Stop all scanners
        for scanner_type, scanner in self.scanners.items():
            main_logger.info(f"Stopping {scanner_type} scanner...")
            try:
                if hasattr(scanner, 'stop'):
                    scanner.stop()
                if hasattr(scanner, 'join'):
                    scanner.join(timeout=5)
            except Exception as e:
                main_logger.exception(f"Error stopping {scanner_type} scanner: {e}")

        main_logger.info("Daemon stopped")

    def start_wifi_scanning(self):
        """Start WiFi scanning in background"""
        main_logger.info("Starting WiFi scanning...")

        try:
            # Check for monitor interface
            monitor_iface = WiFiMonitorManager.get_monitor_interface()

            if not monitor_iface:
                # Try to enable monitor mode
                interfaces = WiFiMonitorManager.get_wireless_interfaces()
                managed = [iface for iface in interfaces if 'mon' not in iface.lower()]

                if managed:
                    main_logger.info(f"Enabling monitor mode on {managed[0]}...")
                    success, monitor_iface, message = WiFiMonitorManager.enable_monitor_mode(managed[0])

                    if not success:
                        main_logger.error(f"Failed to enable monitor mode: {message}")
                        return

            main_logger.info(f"Using monitor interface: {monitor_iface}")

            # Start WiFi scanner
            from src.tools.wifi_scanner import WiFiScanner

            scanner = WiFiScanner(monitor_iface)

            # Connect signals to database logging
            scanner.ap_discovered.connect(self.on_ap_discovered)
            scanner.ap_updated.connect(self.on_ap_updated)
            scanner.client_discovered.connect(self.on_client_discovered)
            scanner.client_updated.connect(self.on_client_updated)

            scanner.start()

            self.scanners['wifi'] = scanner

            main_logger.info("WiFi scanning started")

        except Exception as e:
            main_logger.exception(f"Error starting WiFi scanner: {e}")

    def start_bluetooth_scanning(self):
        """Start Bluetooth scanning in background"""
        main_logger.info("Bluetooth scanning not yet implemented")
        # TODO: Implement Bluetooth scanner

    def start_sdr_scanning(self):
        """Start SDR scanning in background"""
        main_logger.info("SDR scanning not yet implemented")
        # TODO: Implement SDR scanner

    def on_ap_discovered(self, ap):
        """Handle new AP discovery - save to database"""
        try:
            with self.db.get_session() as session:
                from src.database.models import Network
                from datetime import datetime

                # Check if network already exists
                existing = session.query(Network).filter(Network.bssid == ap.bssid).first()

                if not existing:
                    # Create new network record
                    network = Network(
                        bssid=ap.bssid,
                        ssid=ap.ssid,
                        channel=int(ap.channel) if ap.channel and ap.channel.isdigit() else None,
                        encryption=ap.encryption,
                        cipher=ap.cipher,
                        authentication=ap.authentication,
                        current_signal=int(ap.power) if ap.power and ap.power.lstrip('-').isdigit() else None,
                        first_seen=datetime.utcnow(),
                        last_seen=datetime.utcnow()
                    )
                    session.add(network)
                    session.commit()

                    main_logger.info(f"Saved new AP: {ap.ssid or '(Hidden)'} [{ap.bssid}]")

        except Exception as e:
            main_logger.exception(f"Error saving AP to database: {e}")

    def on_ap_updated(self, ap):
        """Handle AP update - update database"""
        try:
            with self.db.get_session() as session:
                from src.database.models import Network
                from datetime import datetime

                network = session.query(Network).filter(Network.bssid == ap.bssid).first()

                if network:
                    # Update fields
                    network.last_seen = datetime.utcnow()
                    network.current_signal = int(ap.power) if ap.power and ap.power.lstrip('-').isdigit() else None

                    if ap.ssid:
                        network.ssid = ap.ssid
                    if ap.encryption:
                        network.encryption = ap.encryption
                    if ap.channel and ap.channel.isdigit():
                        network.channel = int(ap.channel)

                    session.commit()

        except Exception as e:
            main_logger.exception(f"Error updating AP in database: {e}")

    def on_client_discovered(self, client, bssid):
        """Handle new client discovery - save to database"""
        # TODO: Implement client database storage
        pass

    def on_client_updated(self, client):
        """Handle client update - update database"""
        # TODO: Implement client database update
        pass


def main():
    """Main entry point"""
    main_logger.info("="*70)
    main_logger.info("GATTROSE-NG BACKGROUND DAEMON")
    main_logger.info("="*70)
    main_logger.info("")

    # Check if running as root
    if os.geteuid() != 0:
        main_logger.error("This daemon must be run as root (use sudo)")
        main_logger.error("Reason: Monitor mode requires root privileges")
        sys.exit(1)

    # Create and start daemon
    daemon = GattroseDaemon()
    daemon.start()


if __name__ == '__main__':
    main()
