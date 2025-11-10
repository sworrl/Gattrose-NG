"""
MAC Address Vendor Lookup and Device Fingerprinting
Uses IEEE OUI database and heuristics to identify devices
"""

import re
from typing import Dict, Tuple, Optional
from pathlib import Path


class MACVendorLookup:
    """Lookup MAC address vendors using OUI database"""

    # Common vendor OUI prefixes (first 3 octets)
    # This is a subset - for full database, use external OUI file
    VENDOR_DATABASE = {
        # Apple devices
        '00:03:93': 'Apple',
        '00:0A:27': 'Apple',
        '00:0A:95': 'Apple',
        '00:0D:93': 'Apple',
        '00:10:FA': 'Apple',
        '00:11:24': 'Apple',
        '00:14:51': 'Apple',
        '00:16:CB': 'Apple',
        '00:17:F2': 'Apple',
        '00:19:E3': 'Apple',
        '00:1B:63': 'Apple',
        '00:1C:B3': 'Apple',
        '00:1D:4F': 'Apple',
        '00:1E:52': 'Apple',
        '00:1F:5B': 'Apple',
        '00:1F:F3': 'Apple',
        '00:21:E9': 'Apple',
        '00:22:41': 'Apple',
        '00:23:12': 'Apple',
        '00:23:32': 'Apple',
        '00:23:6C': 'Apple',
        '00:23:DF': 'Apple',
        '00:24:36': 'Apple',
        '00:25:00': 'Apple',
        '00:25:4B': 'Apple',
        '00:25:BC': 'Apple',
        '00:26:08': 'Apple',
        '00:26:4A': 'Apple',
        '00:26:B0': 'Apple',
        '00:26:BB': 'Apple',
        '00:3E:E1': 'Apple',
        '00:50:E4': 'Apple',
        '00:61:71': 'Apple',
        '00:88:65': 'Apple',
        '00:C6:10': 'Apple',
        '00:CD:FE': 'Apple',
        '00:F4:B9': 'Apple',
        '04:0C:CE': 'Apple',
        '04:15:52': 'Apple',
        '04:26:65': 'Apple',
        '04:48:9A': 'Apple',
        '04:4B:ED': 'Apple',
        '04:54:53': 'Apple',
        '04:69:F8': 'Apple',
        '04:D3:CF': 'Apple',
        '04:DB:56': 'Apple',
        '04:E5:36': 'Apple',
        '04:F1:3E': 'Apple',
        '04:F7:E4': 'Apple',
        '08:66:98': 'Apple',
        '08:6D:41': 'Apple',
        '08:70:45': 'Apple',
        '08:74:02': 'Apple',

        # Google/Nest devices
        '00:1A:11': 'Google',
        '18:B4:30': 'Google (Nest)',
        '64:16:66': 'Google (Nest)',
        '64:9E:F3': 'Google (Nest)',
        'AC:63:BE': 'Google',
        'F4:F5:D8': 'Google',

        # Amazon devices
        '00:71:47': 'Amazon (Echo)',
        '00:FC:8B': 'Amazon',
        '18:74:2E': 'Amazon',
        '34:D2:70': 'Amazon (Echo)',
        '44:65:0D': 'Amazon',
        '50:DC:E7': 'Amazon',
        '74:75:48': 'Amazon (Echo)',
        '84:D6:D0': 'Amazon',
        'A0:02:DC': 'Amazon (Fire)',
        'AC:63:BE': 'Amazon',
        'B4:7C:9C': 'Amazon (Echo)',
        'FC:65:DE': 'Amazon',

        # Samsung
        '00:07:AB': 'Samsung',
        '00:12:47': 'Samsung',
        '00:12:FB': 'Samsung',
        '00:13:77': 'Samsung',
        '00:15:99': 'Samsung',
        '00:16:32': 'Samsung',
        '00:16:6B': 'Samsung',
        '00:16:6C': 'Samsung',
        '00:17:C9': 'Samsung',
        '00:17:D5': 'Samsung',
        '00:18:AF': 'Samsung',
        '00:1A:8A': 'Samsung',
        '00:1B:98': 'Samsung',
        '00:1C:43': 'Samsung',
        '00:1D:25': 'Samsung',
        '00:1E:7D': 'Samsung',
        '00:1F:CD': 'Samsung',
        '00:21:19': 'Samsung',
        '00:21:4C': 'Samsung',
        '00:23:39': 'Samsung',
        '00:23:D6': 'Samsung',
        '00:23:D7': 'Samsung',
        '00:24:54': 'Samsung',
        '00:24:90': 'Samsung',
        '00:24:91': 'Samsung',
        '00:25:38': 'Samsung',
        '00:26:37': 'Samsung',
        '00:26:5D': 'Samsung',
        '00:26:5F': 'Samsung',

        # Intel
        '00:02:B3': 'Intel',
        '00:03:47': 'Intel',
        '00:04:23': 'Intel',
        '00:0E:0C': 'Intel',
        '00:0E:35': 'Intel',
        '00:11:11': 'Intel',
        '00:12:F0': 'Intel',
        '00:13:02': 'Intel',
        '00:13:20': 'Intel',
        '00:13:CE': 'Intel',
        '00:13:E8': 'Intel',
        '00:15:00': 'Intel',
        '00:16:6F': 'Intel',
        '00:16:76': 'Intel',
        '00:16:EA': 'Intel',
        '00:16:EB': 'Intel',
        '00:19:D1': 'Intel',
        '00:19:D2': 'Intel',
        '00:1B:21': 'Intel',
        '00:1B:77': 'Intel',
        '00:1C:BF': 'Intel',
        '00:1D:E0': 'Intel',
        '00:1D:E1': 'Intel',
        '00:1E:64': 'Intel',
        '00:1E:65': 'Intel',
        '00:1E:67': 'Intel',
        '00:1F:3A': 'Intel',
        '00:1F:3B': 'Intel',
        '00:1F:3C': 'Intel',
        '00:21:5C': 'Intel',
        '00:21:5D': 'Intel',
        '00:21:6A': 'Intel',
        '00:21:6B': 'Intel',
        '00:22:FA': 'Intel',
        '00:22:FB': 'Intel',
        '00:23:14': 'Intel',
        '00:23:15': 'Intel',
        '00:24:D6': 'Intel',
        '00:24:D7': 'Intel',
        '00:26:C6': 'Intel',
        '00:26:C7': 'Intel',

        # Raspberry Pi
        'B8:27:EB': 'Raspberry Pi Foundation',
        'DC:A6:32': 'Raspberry Pi Foundation',
        'E4:5F:01': 'Raspberry Pi Foundation',

        # TP-Link
        '00:27:19': 'TP-Link',
        '14:CF:92': 'TP-Link',
        '50:C7:BF': 'TP-Link',
        '64:66:B3': 'TP-Link',
        '74:DA:88': 'TP-Link',
        '90:F6:52': 'TP-Link',
        'A0:F3:C1': 'TP-Link',
        'C0:4A:00': 'TP-Link',
        'EC:08:6B': 'TP-Link',

        # Ubiquiti
        '00:15:6D': 'Ubiquiti',
        '04:18:D6': 'Ubiquiti',
        '24:A4:3C': 'Ubiquiti',
        '68:72:51': 'Ubiquiti',
        '68:D7:9A': 'Ubiquiti',
        '74:83:C2': 'Ubiquiti',
        '78:8A:20': 'Ubiquiti',
        '80:2A:A8': 'Ubiquiti',
        'B4:FB:E4': 'Ubiquiti',
        'DC:9F:DB': 'Ubiquiti',
        'F0:9F:C2': 'Ubiquiti',
        'FC:EC:DA': 'Ubiquiti',

        # Netgear
        '00:09:5B': 'Netgear',
        '00:0F:B5': 'Netgear',
        '00:14:6C': 'Netgear',
        '00:18:4D': 'Netgear',
        '00:1B:2F': 'Netgear',
        '00:1E:2A': 'Netgear',
        '00:1F:33': 'Netgear',
        '00:22:3F': 'Netgear',
        '00:24:B2': 'Netgear',
        '00:26:F2': 'Netgear',
        '20:0C:C8': 'Netgear',
        '28:C6:8E': 'Netgear',
        '2C:B0:5D': 'Netgear',
        '30:46:9A': 'Netgear',
        '4C:60:DE': 'Netgear',
        'A0:21:B7': 'Netgear',
        'C0:3F:0E': 'Netgear',
        'E0:46:9A': 'Netgear',

        # Sonos
        '00:0E:58': 'Sonos',
        '5C:AA:FD': 'Sonos',
        '94:9F:3E': 'Sonos',
        'B8:E9:37': 'Sonos',

        # Ring
        '74:4C:A1': 'Ring',
        '88:71:E5': 'Ring',
    }

    @staticmethod
    def lookup_vendor(mac: str) -> str:
        """
        Look up vendor from MAC address using OUI database

        Args:
            mac: MAC address (format: XX:XX:XX:XX:XX:XX)

        Returns:
            Vendor name or 'Unknown'
        """
        if not mac:
            return 'Unknown'

        # Extract OUI (first 3 octets)
        parts = mac.upper().split(':')
        if len(parts) < 3:
            return 'Unknown'

        oui = ':'.join(parts[:3])

        # First try the OUI database (38K+ entries)
        try:
            from ..database.models import get_session, OUIDatabase
            session = get_session()
            try:
                oui_record = session.query(OUIDatabase).filter_by(mac_prefix=oui).first()
                if oui_record:
                    # Return short name if available, otherwise full name
                    vendor = oui_record.vendor_name_short or oui_record.vendor_name
                    # Clean up vendor name (remove extra text after first line)
                    if '\n' in vendor:
                        vendor = vendor.split('\n')[0]
                    return vendor.strip()
            finally:
                session.close()
        except Exception as e:
            # Database lookup failed, fall back to hardcoded
            pass

        # Fallback to hardcoded dictionary
        return MACVendorLookup.VENDOR_DATABASE.get(oui, 'Unknown')


class DeviceFingerprinter:
    """Identify specific device types based on multiple signals"""

    @staticmethod
    def identify_device(mac: str, vendor: str, probed_ssids: list = None,
                       signal_strength: str = '', is_ap: bool = False) -> Tuple[str, int]:
        """
        Identify specific device type and confidence level

        Args:
            mac: MAC address
            vendor: Vendor name from OUI lookup
            probed_ssids: List of SSIDs the device probed for
            signal_strength: Signal strength in dBm
            is_ap: Whether this is an access point

        Returns:
            Tuple of (device_type, confidence_percentage)
        """
        if probed_ssids is None:
            probed_ssids = []

        device_type = "Unknown Device"
        confidence = 0

        # Access Points
        if is_ap:
            device_type, confidence = DeviceFingerprinter._identify_ap(vendor, signal_strength)
        else:
            # Client devices
            device_type, confidence = DeviceFingerprinter._identify_client(
                vendor, probed_ssids, signal_strength
            )

        return device_type, confidence

    @staticmethod
    def _identify_ap(vendor: str, signal_strength: str) -> Tuple[str, int]:
        """Identify access point type"""

        if 'Apple' in vendor:
            return "Apple Airport/Router", 75
        elif 'Google' in vendor or 'Nest' in vendor:
            return "Google Nest WiFi/Router", 80
        elif 'Ubiquiti' in vendor:
            return "Ubiquiti UniFi AP", 90
        elif 'TP-Link' in vendor:
            return "TP-Link Router/AP", 85
        elif 'Netgear' in vendor:
            return "Netgear Router/AP", 85
        elif 'Linksys' in vendor:
            return "Linksys Router", 85
        elif 'Asus' in vendor:
            return "Asus Router", 85
        elif 'D-Link' in vendor:
            return "D-Link Router", 85
        elif vendor != 'Unknown':
            return f"{vendor} Router/AP", 70
        else:
            return "Wireless Router/AP", 50

    @staticmethod
    def _identify_client(vendor: str, probed_ssids: list, signal_strength: str) -> Tuple[str, int]:
        """Identify client device type"""

        probed_lower = [ssid.lower() for ssid in probed_ssids if ssid]

        # Apple devices
        if 'Apple' in vendor:
            # Check for specific device indicators
            for ssid in probed_lower:
                if 'iphone' in ssid:
                    return "Apple iPhone", 85
                elif 'ipad' in ssid:
                    return "Apple iPad", 85
                elif 'macbook' in ssid or 'mac' in ssid:
                    return "Apple MacBook/iMac", 80
                elif 'watch' in ssid:
                    return "Apple Watch", 75
            # Default Apple device
            return "Apple iOS/macOS Device", 70

        # Amazon devices
        elif 'Amazon' in vendor:
            if 'Echo' in vendor:
                return "Amazon Echo/Alexa", 90
            elif 'Fire' in vendor:
                return "Amazon Fire Tablet/TV", 85
            return "Amazon Smart Device", 75

        # Google devices
        elif 'Google' in vendor:
            if 'Nest' in vendor:
                return "Google Nest Device", 85
            for ssid in probed_lower:
                if 'android' in ssid or 'pixel' in ssid:
                    return "Google Pixel Phone", 80
            return "Google/Android Device", 70

        # Samsung devices
        elif 'Samsung' in vendor:
            for ssid in probed_lower:
                if 'galaxy' in ssid or 'samsung' in ssid:
                    return "Samsung Galaxy Phone/Tablet", 80
                elif 'tv' in ssid or 'smart' in ssid:
                    return "Samsung Smart TV", 75
            return "Samsung Device", 70

        # Sonos
        elif 'Sonos' in vendor:
            return "Sonos Speaker", 95

        # Ring
        elif 'Ring' in vendor:
            return "Ring Doorbell/Camera", 90

        # Raspberry Pi
        elif 'Raspberry Pi' in vendor:
            return "Raspberry Pi", 90

        # Intel (likely laptop WiFi card)
        elif 'Intel' in vendor:
            return "Laptop/PC (Intel WiFi)", 75

        # Check probed SSIDs for hints
        for ssid in probed_lower:
            if 'printer' in ssid or 'hp' in ssid or 'epson' in ssid or 'canon' in ssid:
                return "Network Printer", 70
            elif 'camera' in ssid or 'cam' in ssid:
                return "Security Camera", 65
            elif 'tv' in ssid or 'roku' in ssid or 'chromecast' in ssid:
                return "Smart TV/Streaming Device", 70
            elif 'thermostat' in ssid or 'nest' in ssid or 'ecobee' in ssid:
                return "Smart Thermostat", 70
            elif 'xbox' in ssid or 'playstation' in ssid or 'ps4' in ssid or 'ps5' in ssid:
                return "Gaming Console", 75
            elif 'nintendo' in ssid or 'switch' in ssid:
                return "Nintendo Switch", 80

        # Fallback based on vendor
        if vendor != 'Unknown':
            return f"{vendor} Device", 60

        return "Unknown WiFi Device", 30


    @staticmethod
    def get_device_icon(device_type: str, is_ap: bool) -> str:
        """
        Get Unicode icon for device type

        Args:
            device_type: Device type string
            is_ap: Whether this is an access point

        Returns:
            Unicode icon character
        """
        device_lower = device_type.lower()

        # Access Points
        if is_ap:
            if 'ubiquiti' in device_lower or 'unifi' in device_lower:
                return '📡'  # Professional AP
            else:
                return '🌐'  # Router/AP

        # Client devices
        if 'iphone' in device_lower:
            return '📱'
        elif 'ipad' in device_lower or 'tablet' in device_lower:
            return '📱'
        elif 'macbook' in device_lower or 'laptop' in device_lower or 'pc' in device_lower:
            return '💻'
        elif 'imac' in device_lower or 'desktop' in device_lower:
            return '🖥️'
        elif 'watch' in device_lower:
            return '⌚'
        elif 'echo' in device_lower or 'alexa' in device_lower or 'speaker' in device_lower:
            return '🔊'
        elif 'tv' in device_lower or 'roku' in device_lower or 'chromecast' in device_lower:
            return '📺'
        elif 'camera' in device_lower or 'ring' in device_lower:
            return '📷'
        elif 'printer' in device_lower:
            return '🖨️'
        elif 'thermostat' in device_lower:
            return '🌡️'
        elif 'console' in device_lower or 'xbox' in device_lower or 'playstation' in device_lower or 'nintendo' in device_lower:
            return '🎮'
        elif 'phone' in device_lower or 'galaxy' in device_lower or 'pixel' in device_lower:
            return '📱'
        elif 'raspberry pi' in device_lower:
            return '🥧'
        elif 'smart' in device_lower or 'iot' in device_lower:
            return '💡'
        else:
            return '📶'  # Generic wireless device
