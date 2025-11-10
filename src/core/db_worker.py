"""
Database Worker
Continuously ingests airodump-ng CSV data into database
"""

import csv
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from PyQt6.QtCore import QThread, pyqtSignal


class DatabaseWorker(QThread):
    """Background worker that ingests CSV data into database"""

    progress_updated = pyqtSignal(int, int)  # networks_processed, clients_processed
    error_occurred = pyqtSignal(str)

    def __init__(self, csv_path: str, gps_enabled: bool = False, geoip_enabled: bool = False):
        super().__init__()
        self.csv_path = csv_path
        self.gps_enabled = gps_enabled
        self.geoip_enabled = geoip_enabled
        self.running = False
        self.update_interval = 3.0  # seconds between updates
        self.last_processed_networks = 0
        self.last_processed_clients = 0

        # GPS/Location tracking
        self.current_lat = None
        self.current_lon = None
        self.current_alt = None

    def run(self):
        """Run the database worker"""
        self.running = True

        try:
            from ..database.models import get_session, Network, Client, NetworkObservation
            from ..tools.wifi_scanner import AccessPoint, WirelessClient

            print(f"[*] Database worker started: {self.csv_path}")

            while self.running:
                try:
                    # Get current GPS location if enabled
                    if self.gps_enabled:
                        self._update_gps_location()

                    # Process networks (APs)
                    networks_file = Path(self.csv_path + "-01.csv")
                    if networks_file.exists():
                        networks = self._process_networks_csv(networks_file)
                        self._upsert_networks(networks)

                    # Process clients
                    # Airodump writes clients to the same CSV file after the APs
                    # We need to parse it properly

                    self.progress_updated.emit(self.last_processed_networks, self.last_processed_clients)

                except Exception as e:
                    print(f"[ERROR] Database worker error: {e}")
                    import traceback
                    traceback.print_exc()
                    self.error_occurred.emit(str(e))

                # Sleep for update interval
                time.sleep(self.update_interval)

        except Exception as e:
            print(f"[FATAL] Database worker fatal error: {e}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(str(e))

    def _update_gps_location(self):
        """Update current GPS location"""
        try:
            import gpsd

            # Connect to gpsd
            gpsd.connect()
            packet = gpsd.get_current()

            if packet.mode >= 2:  # 2D fix or better
                self.current_lat = packet.lat
                self.current_lon = packet.lon
                if packet.mode >= 3:  # 3D fix
                    self.current_alt = packet.alt

        except Exception as e:
            # GPS not available or error
            pass

    def _get_geoip_location(self) -> Optional[Dict]:
        """Get location from GeoIP (fallback if GPS not available)"""
        if not self.geoip_enabled:
            return None

        try:
            import requests

            # Use ipapi.co for free GeoIP lookup
            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'lat': data.get('latitude'),
                    'lon': data.get('longitude'),
                    'city': data.get('city'),
                    'country': data.get('country_name')
                }
        except Exception as e:
            print(f"[WARNING] GeoIP lookup failed: {e}")

        return None

    def _process_networks_csv(self, csv_file: Path) -> List[Dict]:
        """Parse airodump CSV and extract network data"""
        networks = []

        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Airodump CSV has two sections: APs and Clients
            # They're separated by an empty line
            sections = content.split('\n\n')

            if len(sections) < 1:
                return networks

            # Parse AP section
            ap_lines = sections[0].strip().split('\n')

            if len(ap_lines) < 2:
                return networks

            # Skip header line
            reader = csv.DictReader(ap_lines)

            for row in reader:
                try:
                    # Clean up keys (remove leading/trailing spaces)
                    row = {k.strip(): v.strip() if v else '' for k, v in row.items()}

                    bssid = row.get('BSSID', '').strip()
                    if not bssid or bssid == '':
                        continue

                    # Extract network data
                    network_data = {
                        'bssid': bssid,
                        'ssid': row.get('ESSID', '') or row.get('SSID', ''),
                        'channel': self._parse_int(row.get('channel', '')),
                        'encryption': row.get('Privacy', '') or row.get('Encryption', ''),
                        'cipher': row.get('Cipher', ''),
                        'authentication': row.get('Authentication', ''),
                        'max_signal': self._parse_int(row.get('Power', '')),
                        'beacon_count': self._parse_int(row.get('# beacons', '') or row.get('Beacons', '')),
                        'iv_count': self._parse_int(row.get('# IV', '') or row.get('IV', '')),
                        'lan_ip': row.get('LAN IP', ''),
                        'speed': row.get('Speed', ''),
                        'first_seen': self._parse_datetime(row.get('First time seen', '')),
                        'last_seen': self._parse_datetime(row.get('Last time seen', ''))
                    }

                    # Add GPS location if available
                    if self.current_lat and self.current_lon:
                        network_data['latitude'] = self.current_lat
                        network_data['longitude'] = self.current_lon
                        network_data['altitude'] = self.current_alt
                    elif self.geoip_enabled:
                        # Fallback to GeoIP (less accurate)
                        geoip = self._get_geoip_location()
                        if geoip:
                            network_data['latitude'] = geoip['lat']
                            network_data['longitude'] = geoip['lon']

                    networks.append(network_data)

                except Exception as e:
                    print(f"[WARNING] Error parsing network row: {e}")
                    continue

            self.last_processed_networks = len(networks)

        except Exception as e:
            print(f"[ERROR] Error reading networks CSV: {e}")
            import traceback
            traceback.print_exc()

        return networks

    def _upsert_networks(self, networks: List[Dict]):
        """Upsert networks into database"""
        from ..database.models import get_session, Network, NetworkObservation

        session = get_session()

        try:
            for net_data in networks:
                bssid = net_data['bssid']

                # Check if network exists
                network = session.query(Network).filter_by(bssid=bssid).first()

                if network:
                    # Update existing network
                    network.last_seen = datetime.utcnow()

                    # Update signal if stronger
                    new_signal = net_data.get('max_signal')
                    if new_signal:
                        if network.max_signal is None or new_signal > network.max_signal:
                            network.max_signal = new_signal
                        if network.min_signal is None or new_signal < network.min_signal:
                            network.min_signal = new_signal
                        network.current_signal = new_signal

                    # Update beacon count
                    if net_data.get('beacon_count'):
                        network.beacon_count = max(network.beacon_count, net_data['beacon_count'])

                    # Update IV count
                    if net_data.get('iv_count'):
                        network.iv_count = max(network.iv_count, net_data['iv_count'])

                    # Update SSID if it was hidden before
                    if net_data.get('ssid') and not network.ssid:
                        network.ssid = net_data['ssid']

                    # Update location if we have GPS/GeoIP
                    if net_data.get('latitude') and net_data.get('longitude'):
                        network.latitude = net_data['latitude']
                        network.longitude = net_data['longitude']
                        if net_data.get('altitude'):
                            network.altitude = net_data['altitude']

                else:
                    # Create new network
                    network = Network(
                        bssid=bssid,
                        ssid=net_data.get('ssid'),
                        channel=net_data.get('channel'),
                        encryption=net_data.get('encryption'),
                        cipher=net_data.get('cipher'),
                        authentication=net_data.get('authentication'),
                        max_signal=net_data.get('max_signal'),
                        min_signal=net_data.get('max_signal'),
                        current_signal=net_data.get('max_signal'),
                        beacon_count=net_data.get('beacon_count', 0),
                        iv_count=net_data.get('iv_count', 0),
                        lan_ip=net_data.get('lan_ip'),
                        speed=net_data.get('speed'),
                        latitude=net_data.get('latitude'),
                        longitude=net_data.get('longitude'),
                        altitude=net_data.get('altitude'),
                        first_seen=net_data.get('first_seen') or datetime.utcnow(),
                        last_seen=net_data.get('last_seen') or datetime.utcnow()
                    )
                    session.add(network)
                    session.flush()  # Get the ID

                # Create observation record with location
                if net_data.get('latitude') and net_data.get('longitude'):
                    observation = NetworkObservation(
                        network_id=network.id,
                        latitude=net_data['latitude'],
                        longitude=net_data['longitude'],
                        altitude=net_data.get('altitude'),
                        signal_strength=net_data.get('max_signal'),
                        timestamp=datetime.utcnow(),
                        source='scan'
                    )
                    session.add(observation)

            session.commit()

        except Exception as e:
            session.rollback()
            print(f"[ERROR] Database upsert failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            session.close()

    def _parse_int(self, value: str) -> Optional[int]:
        """Parse integer from string"""
        try:
            if value and value.strip():
                # Handle negative numbers (signal strength)
                return int(value.strip())
        except (ValueError, AttributeError):
            pass
        return None

    def _parse_datetime(self, value: str) -> Optional[datetime]:
        """Parse datetime from airodump format"""
        try:
            if value and value.strip():
                # Airodump format: "2025-11-01 12:34:56"
                return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            pass
        return None

    def stop(self):
        """Stop the worker"""
        self.running = False

    def set_gps_enabled(self, enabled: bool):
        """Enable/disable GPS tracking"""
        self.gps_enabled = enabled

    def set_geoip_enabled(self, enabled: bool):
        """Enable/disable GeoIP fallback"""
        self.geoip_enabled = enabled

    def set_update_interval(self, seconds: float):
        """Set update interval in seconds"""
        self.update_interval = max(1.0, seconds)  # Minimum 1 second
