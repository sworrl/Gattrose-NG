"""
Location Services
GPS and GeoIP location tracking
"""

import time
from typing import Optional, Dict, Tuple
from PyQt6.QtCore import QThread, pyqtSignal


class GPSManager(QThread):
    """GPS location manager"""

    location_updated = pyqtSignal(float, float, float, float)  # lat, lon, alt, accuracy
    status_changed = pyqtSignal(str)  # Status message
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self.update_interval = 2.0  # seconds
        self.current_location = None
        self.gps_available = False

    def run(self):
        """Run GPS monitoring"""
        self.running = True

        try:
            import gpsd

            # Connect to gpsd
            gpsd.connect()
            self.gps_available = True
            self.status_changed.emit("GPS connected")

            while self.running:
                try:
                    # Get current GPS fix
                    packet = gpsd.get_current()

                    if packet.mode >= 2:  # 2D fix or better
                        lat = packet.lat
                        lon = packet.lon
                        alt = packet.alt if packet.mode >= 3 else 0.0
                        accuracy = getattr(packet, 'error', {}).get('y', 0.0)

                        self.current_location = (lat, lon, alt, accuracy)
                        self.location_updated.emit(lat, lon, alt, accuracy)

                        fix_type = "3D" if packet.mode >= 3 else "2D"
                        self.status_changed.emit(f"GPS fix: {fix_type} ({packet.sats} sats)")
                    else:
                        self.status_changed.emit(f"GPS acquiring... ({packet.sats} sats)")

                except Exception as e:
                    self.error_occurred.emit(f"GPS read error: {e}")

                time.sleep(self.update_interval)

        except ImportError:
            self.error_occurred.emit("gpsd Python module not installed (pip install gpsd-py3)")
            self.gps_available = False
        except Exception as e:
            self.error_occurred.emit(f"GPS connection failed: {e}")
            self.gps_available = False

    def stop(self):
        """Stop GPS monitoring"""
        self.running = False

    def get_current_location(self) -> Optional[Tuple[float, float, float, float]]:
        """Get current location (lat, lon, alt, accuracy)"""
        return self.current_location

    def is_available(self) -> bool:
        """Check if GPS is available"""
        return self.gps_available


class GeoIPManager:
    """GeoIP location manager (fallback when GPS unavailable)"""

    def __init__(self):
        self.cached_location = None
        self.cache_time = 0
        self.cache_duration = 3600  # Cache for 1 hour

    def get_location(self, force_refresh: bool = False) -> Optional[Dict]:
        """
        Get location from GeoIP

        Returns dict with: lat, lon, city, region, country, accuracy
        """
        # Check cache
        current_time = time.time()
        if not force_refresh and self.cached_location and (current_time - self.cache_time) < self.cache_duration:
            return self.cached_location

        try:
            import requests

            # Try ipapi.co first (free, good accuracy)
            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()

                location = {
                    'lat': data.get('latitude'),
                    'lon': data.get('longitude'),
                    'city': data.get('city'),
                    'region': data.get('region'),
                    'country': data.get('country_name'),
                    'country_code': data.get('country_code'),
                    'accuracy': 50000.0,  # GeoIP is ~50km accuracy
                    'source': 'ipapi.co'
                }

                # Cache result
                self.cached_location = location
                self.cache_time = current_time

                return location

        except Exception as e:
            print(f"[WARNING] GeoIP lookup failed: {e}")

        # Try fallback service: ip-api.com
        try:
            import requests

            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()

                if data.get('status') == 'success':
                    location = {
                        'lat': data.get('lat'),
                        'lon': data.get('lon'),
                        'city': data.get('city'),
                        'region': data.get('regionName'),
                        'country': data.get('country'),
                        'country_code': data.get('countryCode'),
                        'accuracy': 50000.0,
                        'source': 'ip-api.com'
                    }

                    # Cache result
                    self.cached_location = location
                    self.cache_time = current_time

                    return location

        except Exception as e:
            print(f"[WARNING] GeoIP fallback failed: {e}")

        return None

    def is_available(self) -> bool:
        """Check if GeoIP is available"""
        try:
            import requests
            return True
        except ImportError:
            return False


class LocationManager:
    """
    Unified location manager
    Uses GPS if available, falls back to GeoIP
    """

    def __init__(self):
        self.gps_manager = None
        self.geoip_manager = GeoIPManager()
        self.gps_enabled = False
        self.geoip_enabled = False
        self.prefer_gps = True

    def enable_gps(self):
        """Enable GPS tracking"""
        if not self.gps_manager:
            self.gps_manager = GPSManager()

        if not self.gps_manager.isRunning():
            self.gps_manager.start()

        self.gps_enabled = True

    def disable_gps(self):
        """Disable GPS tracking"""
        if self.gps_manager and self.gps_manager.isRunning():
            self.gps_manager.stop()
            self.gps_manager.wait()

        self.gps_enabled = False

    def enable_geoip(self):
        """Enable GeoIP fallback"""
        self.geoip_enabled = True

    def disable_geoip(self):
        """Disable GeoIP fallback"""
        self.geoip_enabled = False

    def get_current_location(self) -> Optional[Dict]:
        """
        Get current location from best available source

        Returns dict with: lat, lon, alt, accuracy, source
        """
        # Try GPS first if enabled and available
        if self.gps_enabled and self.gps_manager:
            gps_loc = self.gps_manager.get_current_location()
            if gps_loc:
                lat, lon, alt, accuracy = gps_loc
                return {
                    'lat': lat,
                    'lon': lon,
                    'alt': alt,
                    'accuracy': accuracy,
                    'source': 'gps'
                }

        # Fallback to GeoIP if enabled
        if self.geoip_enabled:
            geoip_loc = self.geoip_manager.get_location()
            if geoip_loc:
                return {
                    'lat': geoip_loc['lat'],
                    'lon': geoip_loc['lon'],
                    'alt': 0.0,
                    'accuracy': geoip_loc['accuracy'],
                    'city': geoip_loc.get('city'),
                    'country': geoip_loc.get('country'),
                    'source': 'geoip'
                }

        return None

    def is_gps_available(self) -> bool:
        """Check if GPS is available"""
        return self.gps_manager and self.gps_manager.is_available()

    def is_geoip_available(self) -> bool:
        """Check if GeoIP is available"""
        return self.geoip_manager.is_available()

    def get_status(self) -> str:
        """Get current location service status"""
        if self.is_gps_available():
            return "GPS Active"
        elif self.geoip_enabled:
            return "GeoIP Active"
        else:
            return "Location Disabled"
