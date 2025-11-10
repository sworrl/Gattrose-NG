"""
MAC Address Spoofing Utility
Uses macchanger to randomize MAC addresses for OPSEC
"""

import subprocess
import re
from typing import Tuple, Optional


class MACSpoofing:
    """Handle MAC address spoofing operations"""

    @staticmethod
    def get_interface_mac(interface: str) -> Optional[str]:
        """
        Get current MAC address of interface

        Args:
            interface: Network interface name

        Returns:
            MAC address string or None
        """
        try:
            result = subprocess.run(
                ['cat', f'/sys/class/net/{interface}/address'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip().upper()
        except Exception as e:
            print(f"[!] Error getting MAC for {interface}: {e}")
        return None

    @staticmethod
    def get_permanent_mac(interface: str) -> Optional[str]:
        """
        Get permanent (hardware) MAC address of interface

        Args:
            interface: Network interface name

        Returns:
            Permanent MAC address or None
        """
        try:
            # Try ethtool first
            result = subprocess.run(
                ['sudo', 'ethtool', '-P', interface],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', result.stdout)
                if match:
                    return match.group(0).upper()

            # Fallback: try macchanger -s
            result = subprocess.run(
                ['sudo', 'macchanger', '-s', interface],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                match = re.search(r'Permanent MAC:?\s*([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', result.stdout)
                if match:
                    return match.group(0).split()[-1].upper()

        except Exception as e:
            print(f"[!] Error getting permanent MAC for {interface}: {e}")
        return None

    @staticmethod
    def is_mac_spoofed(interface: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if MAC address is spoofed

        Args:
            interface: Network interface name

        Returns:
            Tuple of (is_spoofed, current_mac, permanent_mac)
        """
        current_mac = MACSpoofing.get_interface_mac(interface)
        permanent_mac = MACSpoofing.get_permanent_mac(interface)

        if not current_mac or not permanent_mac:
            return False, current_mac, permanent_mac

        # Normalize for comparison
        current_norm = current_mac.replace(':', '').replace('-', '').upper()
        perm_norm = permanent_mac.replace(':', '').replace('-', '').upper()

        is_spoofed = (current_norm != perm_norm)
        return is_spoofed, current_mac, permanent_mac

    @staticmethod
    def spoof_mac(interface: str, random: bool = True, specific_mac: Optional[str] = None) -> Tuple[bool, str]:
        """
        Spoof MAC address of interface

        Args:
            interface: Network interface name
            random: If True, use random MAC. If False, use specific_mac
            specific_mac: Specific MAC to set (if random=False)

        Returns:
            Tuple of (success, message)
        """
        try:
            print(f"[*] Spoofing MAC on {interface}...")

            # Step 1: Bring interface down
            print(f"[*] Bringing {interface} down...")
            result = subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'down'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, f"Failed to bring interface down: {result.stderr}"

            # Step 2: Change MAC
            if random:
                print(f"[*] Setting random MAC on {interface}...")
                cmd = ['sudo', 'macchanger', '-r', interface]
            else:
                if not specific_mac:
                    return False, "Specific MAC not provided"
                print(f"[*] Setting MAC to {specific_mac} on {interface}...")
                cmd = ['sudo', 'macchanger', '-m', specific_mac, interface]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )

            # Step 3: Bring interface back up
            print(f"[*] Bringing {interface} up...")
            up_result = subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'up'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse new MAC from output
                match = re.search(r'New\s+MAC:?\s*([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', result.stdout)
                new_mac = match.group(0).split()[-1] if match else "Unknown"

                return True, f"MAC spoofed successfully to {new_mac}"
            else:
                return False, f"macchanger failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "MAC spoofing timed out"
        except Exception as e:
            return False, f"Error spoofing MAC: {e}"

    @staticmethod
    def restore_permanent_mac(interface: str) -> Tuple[bool, str]:
        """
        Restore permanent (hardware) MAC address

        Args:
            interface: Network interface name

        Returns:
            Tuple of (success, message)
        """
        try:
            print(f"[*] Restoring permanent MAC on {interface}...")

            # Bring interface down
            subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'down'],
                capture_output=True,
                timeout=5
            )

            # Restore permanent MAC
            result = subprocess.run(
                ['sudo', 'macchanger', '-p', interface],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Bring interface back up
            subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'up'],
                capture_output=True,
                timeout=5
            )

            if result.returncode == 0:
                return True, "Permanent MAC restored"
            else:
                return False, f"Failed to restore MAC: {result.stderr}"

        except Exception as e:
            return False, f"Error restoring MAC: {e}"
