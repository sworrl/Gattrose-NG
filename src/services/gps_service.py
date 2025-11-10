"""
GPS Service
Provides GPS location data for wardriving and network mapping
Supports gpsd, Android phone via ADB, and fallback to GeoIP
"""

import threading
import time
import subprocess
import json
from typing import Optional, Dict, Tuple
from datetime import datetime


class GPSService:
    """GPS service for tracking location during scans"""

    def __init__(self, enable_gps: bool = True, enable_geoip_fallback: bool = True):
        """
        Initialize GPS service

        Args:
            enable_gps: Enable GPS via gpsd
            enable_geoip_fallback: Use GeoIP if GPS unavailable
        """
        self.enable_gps = enable_gps
        self.enable_geoip_fallback = enable_geoip_fallback

        # Current location
        self._lock = threading.RLock()
        self._latitude: Optional[float] = None
        self._longitude: Optional[float] = None
        self._altitude: Optional[float] = None
        self._accuracy: Optional[float] = None
        self._gps_source: Optional[str] = None  # 'gpsd', 'phone-bt', 'phone-usb', 'geoip'
        self._fix_mode: int = 0  # 0=no fix, 2=2D, 3=3D
        self._last_update: Optional[datetime] = None

        # GPS daemon connection
        self._gpsd_available = False
        self._adb_available = False
        self._geoip_location: Optional[Dict] = None

        # Android phone status (when using ADB)
        self._phone_status: Dict = {
            'connected': False,
            'authorized': False,
            'battery_level': None,
            'battery_status': None,
            'gps_satellites': None,
            'gps_used_in_fix': None,
            'device_model': None,
            'android_version': None,
            'serial': None
        }

        # Background update thread
        self._running = False
        self._update_thread: Optional[threading.Thread] = None

        # Try to detect GPS sources
        if self.enable_gps:
            self._check_gpsd()
            self._check_adb_phone()

    def _check_gpsd(self):
        """Check if gpsd is available"""
        try:
            import gpsd
            gpsd.connect()
            packet = gpsd.get_current()
            if packet.mode >= 2:
                self._gpsd_available = True
                print("[GPS] ✓ GPS daemon detected and has fix")
            else:
                print("[GPS] GPS daemon detected but no fix yet")
                self._gpsd_available = True
        except ImportError:
            print("[GPS] gpsd Python module not installed (pip install gpsd-py3)")
            self._gpsd_available = False
        except Exception as e:
            print(f"[GPS] GPS daemon not available: {e}")
            self._gpsd_available = False

            # Try GeoIP fallback
            if self.enable_geoip_fallback:
                self._update_geoip_location()

    def _check_adb_phone(self):
        """Check if Android phone with GPS is available via ADB"""
        try:
            # Check if ADB is installed
            result = subprocess.run(['which', 'adb'], capture_output=True, timeout=2)
            if result.returncode != 0:
                print("[GPS] ADB not installed - phone GPS unavailable")
                self._phone_status['connected'] = False
                self._phone_status['authorized'] = False
                return

            # Check for connected devices
            result = subprocess.run(['adb', 'devices', '-l'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header

            # Look for authorized devices (not 'unauthorized')
            authorized_devices = [line for line in lines if line.strip() and 'unauthorized' not in line.lower() and 'device' in line.lower()]
            unauthorized_devices = [line for line in lines if line.strip() and 'unauthorized' in line.lower()]

            if authorized_devices:
                self._adb_available = True
                self._phone_status['connected'] = True
                self._phone_status['authorized'] = True

                # Extract serial number from first device
                device_line = authorized_devices[0]
                serial = device_line.split()[0] if device_line.split() else None
                self._phone_status['serial'] = serial

                # Get detailed phone info
                self._update_phone_info()

                print(f"[GPS] ✓ Android phone detected via ADB ({len(authorized_devices)} device(s))")
            elif unauthorized_devices:
                self._phone_status['connected'] = True
                self._phone_status['authorized'] = False
                self._adb_available = False
                print("[GPS] Android phone detected but not authorized - please accept USB debugging on phone")
            else:
                self._phone_status['connected'] = False
                self._phone_status['authorized'] = False
                self._adb_available = False
                print("[GPS] No Android phone detected via ADB")

        except FileNotFoundError:
            print("[GPS] ADB not installed")
            self._adb_available = False
            self._phone_status['connected'] = False
            self._phone_status['authorized'] = False
        except Exception as e:
            print(f"[GPS] ADB check failed: {e}")
            self._adb_available = False
            self._phone_status['connected'] = False
            self._phone_status['authorized'] = False

    def _monitor_device_changes(self):
        """Monitor for Android phone disconnect/reconnect/swap events"""
        try:
            # Check if ADB is installed
            result = subprocess.run(['which', 'adb'], capture_output=True, timeout=2)
            if result.returncode != 0:
                return

            # Get previous state
            prev_connected = self._phone_status.get('connected', False)
            prev_authorized = self._phone_status.get('authorized', False)
            prev_serial = self._phone_status.get('serial', None)

            # Check for connected devices
            result = subprocess.run(['adb', 'devices', '-l'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')[1:]  # Skip header

            # Look for authorized devices
            authorized_devices = [line for line in lines if line.strip() and 'unauthorized' not in line.lower() and 'device' in line.lower()]
            unauthorized_devices = [line for line in lines if line.strip() and 'unauthorized' in line.lower()]

            # Determine current state
            if authorized_devices:
                # Device connected and authorized
                device_line = authorized_devices[0]
                serial = device_line.split()[0] if device_line.split() else None

                # Check for device swap (different serial number)
                if prev_authorized and prev_serial and serial != prev_serial:
                    print(f"[GPS] 🔄 Device SWAPPED: {prev_serial} → {serial}")
                    print(f"[GPS] Old device: {prev_serial}")
                    print(f"[GPS] New device: {serial}")
                    # Clear previous device data
                    self._phone_status.clear()
                    self._phone_status['connected'] = True
                    self._phone_status['authorized'] = True
                    self._phone_status['serial'] = serial
                    # Get new device info
                    self._update_phone_info()

                # Check for reconnect (was disconnected, now connected)
                elif not prev_connected or not prev_authorized:
                    print(f"[GPS] 🔌 Android phone CONNECTED: {serial}")
                    self._adb_available = True
                    self._phone_status['connected'] = True
                    self._phone_status['authorized'] = True
                    self._phone_status['serial'] = serial
                    # Get device info
                    self._update_phone_info()

                # Device still connected, just update status
                else:
                    self._adb_available = True
                    self._phone_status['connected'] = True
                    self._phone_status['authorized'] = True
                    self._phone_status['serial'] = serial

            elif unauthorized_devices:
                # Device connected but not authorized
                if prev_authorized:
                    print(f"[GPS] ⚠️  Android phone became UNAUTHORIZED - accept USB debugging")
                elif not prev_connected:
                    print(f"[GPS] ⚠️  Android phone connected but NOT AUTHORIZED - accept USB debugging")

                self._phone_status['connected'] = True
                self._phone_status['authorized'] = False
                self._adb_available = False

            else:
                # No devices connected
                if prev_connected:
                    print(f"[GPS] 🔌 Android phone DISCONNECTED: {prev_serial}")
                    # Clear GPS data since phone is gone
                    with self._lock:
                        if self._gps_source == 'phone-usb':
                            self._latitude = None
                            self._longitude = None
                            self._altitude = None
                            self._accuracy = None
                            self._gps_source = None
                            self._fix_mode = 0

                self._phone_status['connected'] = False
                self._phone_status['authorized'] = False
                self._phone_status['serial'] = None
                self._adb_available = False

        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[GPS] Error monitoring device changes: {e}")

    def _update_phone_info(self):
        """Update detailed phone information (battery, device model, network, sensors, etc.)"""
        if not self._adb_available:
            return

        try:
            # Get device model
            result = subprocess.run(
                ['adb', 'shell', 'getprop', 'ro.product.model'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                self._phone_status['device_model'] = result.stdout.strip()

            # Get device manufacturer
            result = subprocess.run(
                ['adb', 'shell', 'getprop', 'ro.product.manufacturer'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                self._phone_status['device_manufacturer'] = result.stdout.strip()

            # Get Android version
            result = subprocess.run(
                ['adb', 'shell', 'getprop', 'ro.build.version.release'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                self._phone_status['android_version'] = result.stdout.strip()

            # Get Android SDK version
            result = subprocess.run(
                ['adb', 'shell', 'getprop', 'ro.build.version.sdk'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                self._phone_status['android_sdk'] = result.stdout.strip()

            # Get battery level, status, and temperature from dumpsys battery
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'battery'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    line_stripped = line.strip()
                    line_lower = line_stripped.lower()

                    # Parse battery level
                    if line_lower.startswith('level:'):
                        try:
                            level = int(line_stripped.split(':')[1].strip())
                            self._phone_status['battery_level'] = level
                        except (ValueError, IndexError):
                            pass

                    # Parse battery status
                    elif line_lower.startswith('status:'):
                        try:
                            status = line_stripped.split(':')[1].strip()
                            # Convert status code to string (2=Charging, 3=Discharging, 4=Not charging, 5=Full)
                            status_map = {
                                '2': 'Charging',
                                '3': 'Discharging',
                                '4': 'Not charging',
                                '5': 'Full'
                            }
                            self._phone_status['battery_status'] = status_map.get(status, status)
                        except (ValueError, IndexError):
                            pass

                    # Parse battery temperature
                    elif line_lower.startswith('temperature:'):
                        try:
                            # Temperature is in tenths of degrees Celsius
                            temp = int(line_stripped.split(':')[1].strip())
                            self._phone_status['battery_temp'] = temp / 10.0
                        except (ValueError, IndexError):
                            pass

                    # Parse battery voltage
                    elif line_lower.startswith('voltage:'):
                        try:
                            voltage = int(line_stripped.split(':')[1].strip())
                            self._phone_status['battery_voltage'] = voltage / 1000.0  # Convert to volts
                        except (ValueError, IndexError):
                            pass

                    # Parse battery health
                    elif line_lower.startswith('health:'):
                        try:
                            health = line_stripped.split(':')[1].strip()
                            health_map = {
                                '1': 'Unknown',
                                '2': 'Good',
                                '3': 'Overheat',
                                '4': 'Dead',
                                '5': 'Over voltage',
                                '6': 'Unspecified failure',
                                '7': 'Cold'
                            }
                            self._phone_status['battery_health'] = health_map.get(health, health)
                        except (ValueError, IndexError):
                            pass

                    # Parse battery current (in microamps, negative = discharging, positive = charging)
                    elif line_lower.startswith('current now:') or line_lower.startswith('current avg:'):
                        try:
                            current_ua = int(line_stripped.split(':')[1].strip())
                            # Convert microamps to milliamps for easier reading
                            current_ma = current_ua / 1000.0
                            if line_lower.startswith('current now:'):
                                self._phone_status['battery_current_now'] = current_ma
                            else:
                                self._phone_status['battery_current_avg'] = current_ma
                        except (ValueError, IndexError):
                            pass

                    # Parse battery capacity (in microamp-hours)
                    elif line_lower.startswith('charge counter:'):
                        try:
                            charge_uah = int(line_stripped.split(':')[1].strip())
                            # Convert to mAh
                            self._phone_status['battery_charge_mah'] = charge_uah / 1000.0
                        except (ValueError, IndexError):
                            pass

                    # Parse battery max capacity
                    elif line_lower.startswith('max charging current:') or line_lower.startswith('max charging voltage:'):
                        try:
                            if line_lower.startswith('max charging current:'):
                                max_current = int(line_stripped.split(':')[1].strip())
                                self._phone_status['battery_max_current'] = max_current / 1000.0  # to mA
                            else:
                                max_voltage = int(line_stripped.split(':')[1].strip())
                                self._phone_status['battery_max_voltage'] = max_voltage / 1000.0  # to V
                        except (ValueError, IndexError):
                            pass

                    # Parse AC/USB powered status for more accurate charging detection
                    elif line_lower.startswith('ac powered:') or line_lower.startswith('usb powered:') or line_lower.startswith('wireless powered:'):
                        if 'true' in line_lower:
                            # Override status if we detect actual power source
                            if self._phone_status.get('battery_status') == 'Not charging':
                                self._phone_status['battery_status'] = 'Charging'

            # Get current draw from sysfs (more reliable than dumpsys battery)
            try:
                result = subprocess.run(
                    ['adb', 'shell', 'cat', '/sys/class/power_supply/battery/current_now'],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if result.returncode == 0 and result.stdout.strip():
                    # Current in microamps (negative = discharging, positive = charging)
                    current_ua = int(result.stdout.strip())
                    self._phone_status['battery_current_now'] = current_ua / 1000.0  # Convert to mA
            except:
                pass

            # Get battery capacity from sysfs
            try:
                result = subprocess.run(
                    ['adb', 'shell', 'cat', '/sys/class/power_supply/battery/capacity'],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if result.returncode == 0 and result.stdout.strip():
                    self._phone_status['battery_capacity_mah'] = int(result.stdout.strip())
            except:
                pass

            # Get time remaining estimates from batterystats
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'batterystats'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    line_stripped = line.strip()

                    # Parse time to full when charging
                    if 'Charge time remaining:' in line_stripped or 'Estimated charge time remaining:' in line_stripped:
                        # Format: "Charge time remaining: +7h42m54s0ms" or "Estimated charge time remaining: +7h42m54s0ms"
                        try:
                            time_part = line_stripped.split(':', 1)[1].strip()
                            # Parse the time string (+7h42m54s0ms)
                            if time_part and time_part != 'N/A':
                                hours = 0
                                minutes = 0

                                if 'h' in time_part:
                                    hours = int(time_part.split('h')[0].replace('+', ''))
                                    time_part = time_part.split('h')[1]
                                if 'm' in time_part:
                                    minutes = int(time_part.split('m')[0])

                                total_minutes = hours * 60 + minutes
                                self._phone_status['battery_time_to_full_minutes'] = total_minutes
                        except:
                            pass

                    # Parse estimated battery capacity
                    elif line_stripped.startswith('Estimated battery capacity:'):
                        try:
                            capacity_str = line_stripped.split(':')[1].strip()
                            capacity_mah = int(capacity_str.split()[0])  # "5282 mAh" -> 5282
                            self._phone_status['battery_capacity_mah'] = capacity_mah
                        except:
                            pass

            # Get WiFi information
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'wifi'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                wifi_enabled = False
                wifi_ssid = None
                wifi_bssid = None
                wifi_rssi = None
                wifi_freq = None

                for line in result.stdout.split('\n'):
                    if 'Wi-Fi is enabled' in line or 'mWifiEnabled:true' in line:
                        wifi_enabled = True
                    elif 'SSID:' in line and 'mWifiInfo' in line:
                        try:
                            wifi_ssid = line.split('SSID:')[1].split(',')[0].strip().strip('"')
                        except (IndexError, AttributeError):
                            pass
                    elif 'BSSID:' in line:
                        try:
                            wifi_bssid = line.split('BSSID:')[1].split(',')[0].strip()
                        except (IndexError, AttributeError):
                            pass
                    elif 'RSSI:' in line:
                        try:
                            wifi_rssi = int(line.split('RSSI:')[1].split(',')[0].strip())
                        except (ValueError, IndexError):
                            pass
                    elif 'Frequency:' in line:
                        try:
                            wifi_freq = int(line.split('Frequency:')[1].split(',')[0].strip())
                        except (ValueError, IndexError):
                            pass

                self._phone_status['wifi_enabled'] = wifi_enabled
                if wifi_ssid:
                    self._phone_status['wifi_ssid'] = wifi_ssid
                if wifi_bssid:
                    self._phone_status['wifi_bssid'] = wifi_bssid
                if wifi_rssi:
                    self._phone_status['wifi_rssi'] = wifi_rssi
                if wifi_freq:
                    self._phone_status['wifi_frequency'] = wifi_freq

            # Get cellular network information
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'telephony.registry'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'mServiceState=' in line or 'ServiceState:' in line:
                        if 'mOperatorAlphaLong=' in line:
                            try:
                                operator = line.split('mOperatorAlphaLong=')[1].split()[0].strip()
                                self._phone_status['cellular_operator'] = operator
                            except (IndexError, AttributeError):
                                pass
                    elif 'mSignalStrength=' in line or 'SignalStrength:' in line:
                        # Parse signal strength
                        if 'rssi=' in line:
                            try:
                                rssi = line.split('rssi=')[1].split()[0].strip()
                                self._phone_status['cellular_rssi'] = int(rssi)
                            except (ValueError, IndexError):
                                pass

            # Get screen status
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'power'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Display Power: state=' in line:
                        if 'ON' in line:
                            self._phone_status['screen_on'] = True
                        elif 'OFF' in line:
                            self._phone_status['screen_on'] = False

            # Get memory info
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'meminfo'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Total RAM:' in line:
                        try:
                            # Extract total RAM in MB or GB
                            ram_str = line.split('Total RAM:')[1].strip().split()[0]
                            if ',' in ram_str:
                                ram_str = ram_str.replace(',', '')
                            self._phone_status['total_ram_mb'] = int(ram_str) // 1024  # Convert KB to MB
                        except (ValueError, IndexError):
                            pass
                    elif 'Free RAM:' in line:
                        try:
                            ram_str = line.split('Free RAM:')[1].strip().split()[0]
                            if ',' in ram_str:
                                ram_str = ram_str.replace(',', '')
                            self._phone_status['free_ram_mb'] = int(ram_str) // 1024  # Convert KB to MB
                        except (ValueError, IndexError):
                            pass

            # Get CPU temperature if available
            result = subprocess.run(
                ['adb', 'shell', 'cat', '/sys/class/thermal/thermal_zone0/temp'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                try:
                    # Usually in millidegrees Celsius
                    temp = int(result.stdout.strip())
                    self._phone_status['cpu_temp'] = temp / 1000.0
                except (ValueError, IndexError):
                    pass

            # Get storage info
            result = subprocess.run(
                ['adb', 'shell', 'df', '/data'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # Parse df output: Filesystem Size Used Avail Use% Mounted on
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        try:
                            # Convert to human readable format
                            used = parts[2]
                            available = parts[3]
                            self._phone_status['storage_used'] = used
                            self._phone_status['storage_available'] = available
                        except (ValueError, IndexError):
                            pass

            # Get Bluetooth status
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'bluetooth_manager'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                bluetooth_enabled = False
                for line in result.stdout.split('\n'):
                    if 'enabled: true' in line.lower() or 'state: on' in line.lower():
                        bluetooth_enabled = True
                        break
                self._phone_status['bluetooth_enabled'] = bluetooth_enabled

            # Get weather data using GPS coordinates (if available)
            with self._lock:
                lat = self._latitude
                lon = self._longitude

            if lat and lon:
                self._update_weather_from_coords(lat, lon)

        except Exception as e:
            print(f"[GPS] Error updating phone info: {e}")

    def _update_weather_from_coords(self, lat: float, lon: float):
        """Fetch weather data using GPS coordinates from Open-Meteo API (free, no key required)"""
        try:
            import requests

            # Open-Meteo API - free weather data, no API key required
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"

            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                current = data.get('current', {})

                # Weather code mapping (WMO Weather interpretation codes)
                weather_codes = {
                    0: 'Clear sky',
                    1: 'Mainly clear',
                    2: 'Partly cloudy',
                    3: 'Overcast',
                    45: 'Foggy',
                    48: 'Depositing rime fog',
                    51: 'Light drizzle',
                    53: 'Moderate drizzle',
                    55: 'Dense drizzle',
                    61: 'Slight rain',
                    63: 'Moderate rain',
                    65: 'Heavy rain',
                    71: 'Slight snow',
                    73: 'Moderate snow',
                    75: 'Heavy snow',
                    77: 'Snow grains',
                    80: 'Slight rain showers',
                    81: 'Moderate rain showers',
                    82: 'Violent rain showers',
                    85: 'Slight snow showers',
                    86: 'Heavy snow showers',
                    95: 'Thunderstorm',
                    96: 'Thunderstorm with slight hail',
                    99: 'Thunderstorm with heavy hail'
                }

                weather_code = current.get('weather_code', 0)
                weather_condition = weather_codes.get(weather_code, 'Unknown')

                self._phone_status['weather_temp_f'] = current.get('temperature_2m')
                self._phone_status['weather_feels_like_f'] = current.get('apparent_temperature')
                self._phone_status['weather_humidity'] = current.get('relative_humidity_2m')
                self._phone_status['weather_precipitation'] = current.get('precipitation')
                self._phone_status['weather_condition'] = weather_condition
                self._phone_status['weather_wind_speed_mph'] = current.get('wind_speed_10m')
                self._phone_status['weather_wind_direction'] = current.get('wind_direction_10m')
                self._phone_status['weather_last_update'] = current.get('time')

        except Exception as e:
            # Silently fail for weather - it's not critical
            pass

    def get_phone_status(self) -> Dict:
        """
        Get detailed Android phone status

        Returns:
            Dict with keys: connected, authorized, battery_level, battery_status,
            gps_satellites, gps_used_in_fix, device_model, android_version, serial
        """
        with self._lock:
            return self._phone_status.copy()

    def start(self):
        """Start background GPS update thread"""
        if self._running:
            return

        self._running = True
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        print("[GPS] Background update thread started")

    def stop(self):
        """Stop background GPS update thread"""
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=2)
        print("[GPS] Background update thread stopped")

    def _update_loop(self):
        """Background loop to update GPS position and monitor device connections"""
        device_check_counter = 0

        while self._running:
            try:
                # Check for device connection changes every ~6 seconds (3 iterations * 2s)
                # This detects Android phone detach/reattach and device swaps
                device_check_counter += 1
                if device_check_counter >= 3:
                    self._monitor_device_changes()
                    device_check_counter = 0

                # Try GPS sources in priority order: gpsd > ADB phone > GeoIP
                if self._gpsd_available:
                    self._update_from_gpsd()
                elif self._adb_available:
                    self._update_from_adb_phone()
                elif self.enable_geoip_fallback and not self._geoip_location:
                    self._update_geoip_location()

                # Update frequency based on source
                if self._gpsd_available or self._adb_available:
                    sleep_time = 2  # Fast updates for real GPS
                else:
                    sleep_time = 60  # Slow updates for GeoIP

                time.sleep(sleep_time)

            except Exception as e:
                print(f"[GPS] Error in update loop: {e}")
                time.sleep(5)

    def _update_from_gpsd(self):
        """Update location from gpsd"""
        try:
            import gpsd

            gpsd.connect()
            packet = gpsd.get_current()

            with self._lock:
                self._fix_mode = packet.mode

                if packet.mode >= 2:  # 2D fix or better
                    self._latitude = packet.lat
                    self._longitude = packet.lon
                    self._gps_source = 'gpsd'  # Accurate GPS from daemon
                    self._last_update = datetime.utcnow()

                    # Get accuracy from GPS (EPE = estimated position error)
                    if hasattr(packet, 'error') and hasattr(packet.error, 'c'):
                        self._accuracy = packet.error['c']  # Circular error
                    else:
                        self._accuracy = None

                    if packet.mode >= 3:  # 3D fix
                        self._altitude = packet.alt
                    else:
                        self._altitude = None

        except Exception as e:
            # GPS connection lost or no fix
            with self._lock:
                self._fix_mode = 0

    def _update_from_adb_phone(self):
        """Update location from Android phone via ADB"""
        try:
            # Get location from Android using dumpsys
            # This uses the phone's LocationManager to get last known location
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'location'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                # Device disconnected or unauthorized
                self._adb_available = False
                self._phone_status['connected'] = False
                self._phone_status['authorized'] = False
                return

            output = result.stdout

            # Parse GPS satellite information
            satellites_visible = None
            satellites_used = None
            for line in output.split('\n'):
                if 'satellites' in line.lower():
                    # Look for patterns like "satellites: 12" or "satellites used in fix: 8"
                    if 'used in fix' in line.lower():
                        try:
                            satellites_used = int(line.split(':')[-1].strip())
                        except (ValueError, IndexError):
                            pass
                    else:
                        try:
                            satellites_visible = int(line.split(':')[-1].strip())
                        except (ValueError, IndexError):
                            pass

            # Update satellite info
            with self._lock:
                self._phone_status['gps_satellites'] = satellites_visible
                self._phone_status['gps_used_in_fix'] = satellites_used

            # Parse location data from dumpsys output
            # Look for "Last Known Locations" section
            lat, lon, acc = None, None, None
            alt = None

            # Try to find GPS provider location first (most accurate)
            # Format: "Location[gps 39.005586,-90.741661 hAcc=13.77551 ... alt=128.0 ...]"
            for line in output.split('\n'):
                # Look for GPS provider location
                if 'Location[gps' in line:
                    try:
                        # Extract coordinates: "Location[gps LAT,LON ..."
                        start_idx = line.find('Location[gps') + len('Location[gps')
                        coords_part = line[start_idx:].split()[0].strip()  # Get "LAT,LON"

                        if ',' in coords_part:
                            lat_str, lon_str = coords_part.split(',')
                            lat = float(lat_str)
                            lon = float(lon_str)

                        # Extract accuracy: hAcc=VALUE
                        if 'hAcc=' in line:
                            for part in line.split():
                                if 'hAcc=' in part:
                                    acc = float(part.split('=')[1].rstrip(',]'))
                                    break

                        # Extract altitude: alt=VALUE
                        if 'alt=' in line:
                            for part in line.split():
                                if part.startswith('alt='):
                                    alt = float(part.split('=')[1].rstrip(',]'))
                                    break

                        # If we got coordinates, we're done
                        if lat is not None and lon is not None:
                            break

                    except (ValueError, IndexError) as e:
                        continue

            # If no GPS provider, try network provider
            if lat is None:
                for line in output.split('\n'):
                    if 'Location[network' in line:
                        try:
                            # Extract coordinates: "Location[network LAT,LON ..."
                            start_idx = line.find('Location[network') + len('Location[network')
                            coords_part = line[start_idx:].split()[0].strip()

                            if ',' in coords_part:
                                lat_str, lon_str = coords_part.split(',')
                                lat = float(lat_str)
                                lon = float(lon_str)

                            # Extract accuracy
                            if 'hAcc=' in line:
                                for part in line.split():
                                    if 'hAcc=' in part:
                                        acc = float(part.split('=')[1].rstrip(',]'))
                                        break

                            # Extract altitude
                            if 'alt=' in line:
                                for part in line.split():
                                    if part.startswith('alt='):
                                        alt = float(part.split('=')[1].rstrip(',]'))
                                        break

                            if lat is not None and lon is not None:
                                break

                        except (ValueError, IndexError):
                            continue

            # Update our location if we got valid data
            if lat is not None and lon is not None:
                with self._lock:
                    self._latitude = lat
                    self._longitude = lon
                    self._altitude = alt
                    self._accuracy = acc if acc else 10.0  # Default ~10m accuracy
                    self._gps_source = 'phone-usb'  # Phone GPS via USB
                    self._fix_mode = 3 if alt is not None else 2
                    self._last_update = datetime.utcnow()

            # Periodically update phone info (battery, etc.) - every 30 calls (~60 seconds)
            # Reduced frequency since batterystats is expensive
            if not hasattr(self, '_phone_info_counter'):
                self._phone_info_counter = 0
            self._phone_info_counter += 1
            if self._phone_info_counter >= 30:
                self._update_phone_info()
                self._phone_info_counter = 0

        except subprocess.TimeoutExpired:
            print("[GPS] ADB command timed out")
            self._adb_available = False
            self._phone_status['connected'] = False
        except FileNotFoundError:
            self._adb_available = False
            self._phone_status['connected'] = False
        except Exception as e:
            print(f"[GPS] Error reading phone GPS: {e}")

    def _update_geoip_location(self):
        """Get approximate location from GeoIP (fallback)"""
        try:
            import requests

            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                with self._lock:
                    self._geoip_location = {
                        'lat': data.get('latitude'),
                        'lon': data.get('longitude'),
                        'city': data.get('city'),
                        'country': data.get('country_name')
                    }
                    # Use GeoIP as fallback if no GPS
                    if not self._latitude:
                        self._latitude = data.get('latitude')
                        self._longitude = data.get('longitude')
                        self._gps_source = 'geoip'  # Approximate location from IP
                        self._accuracy = 5000.0  # GeoIP is very inaccurate (5km)
                        self._last_update = datetime.utcnow()
                        print(f"[GPS] Using GeoIP location: {self._geoip_location['city']}, {self._geoip_location['country']}")

        except Exception as e:
            print(f"[GPS] GeoIP lookup failed: {e}")

    def get_location(self) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[str]]:
        """
        Get current location

        Returns:
            Tuple of (latitude, longitude, altitude, accuracy, gps_source)
            All values are None if no location available
            gps_source: 'gpsd', 'phone-bt', 'phone-usb', 'geoip', or None
        """
        with self._lock:
            return (self._latitude, self._longitude, self._altitude, self._accuracy, self._gps_source)

    def has_fix(self) -> bool:
        """Check if we have a GPS fix"""
        with self._lock:
            return self._fix_mode >= 2

    def get_fix_quality(self) -> str:
        """Get fix quality as string"""
        with self._lock:
            if self._fix_mode == 0:
                return "No Fix"
            elif self._fix_mode == 2:
                return "2D Fix"
            elif self._fix_mode == 3:
                return "3D Fix"
            else:
                return "Unknown"

    def get_status_string(self) -> str:
        """Get human-readable status string"""
        lat, lon, alt, acc, gps_source = self.get_location()

        if lat is None:
            return "GPS: No location"

        fix_quality = self.get_fix_quality()
        source_str = f" ({gps_source})" if gps_source else ""
        if acc:
            return f"GPS: {lat:.6f}, {lon:.6f} (±{acc:.1f}m) - {fix_quality}{source_str}"
        else:
            return f"GPS: {lat:.6f}, {lon:.6f} - {fix_quality}{source_str}"


# Singleton instance
_gps_service_instance: Optional[GPSService] = None


def get_gps_service(enable_gps: bool = True, enable_geoip_fallback: bool = True) -> GPSService:
    """
    Get singleton GPS service instance

    Args:
        enable_gps: Enable GPS via gpsd
        enable_geoip_fallback: Use GeoIP if GPS unavailable

    Returns:
        GPSService instance
    """
    global _gps_service_instance

    if _gps_service_instance is None:
        _gps_service_instance = GPSService(enable_gps, enable_geoip_fallback)

    return _gps_service_instance
