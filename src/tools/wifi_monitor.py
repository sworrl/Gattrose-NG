"""
Automatic WiFi monitor mode management
Detects wireless cards and enables monitor mode automatically
"""

import subprocess
import re
import os
import shutil
from typing import List, Tuple, Optional


def find_command(cmd: str) -> str:
    """
    Find command in standard locations
    Fixes PATH issues when running as service
    """
    # Try shutil.which first (checks PATH)
    result = shutil.which(cmd)
    if result:
        return result

    # Try standard locations for wireless tools
    standard_paths = ['/usr/sbin', '/usr/bin', '/sbin', '/bin', '/usr/local/sbin', '/usr/local/bin']
    for path in standard_paths:
        full_path = os.path.join(path, cmd)
        if os.path.exists(full_path) and os.access(full_path, os.X_OK):
            return full_path

    # Fallback to just the command name
    return cmd


class WiFiMonitorManager:
    """Manages WiFi interfaces and monitor mode"""

    @staticmethod
    def get_wireless_interfaces() -> List[str]:
        """Get list of wireless interfaces"""
        interfaces = []

        # Try 'iw dev' first (modern and widely available)
        try:
            result = subprocess.run(
                [find_command('iw'), 'dev'],
                capture_output=True,
                text=True,
                timeout=5
            )

            for line in result.stdout.split('\n'):
                if 'Interface' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        iface = parts[1]
                        if iface not in interfaces:
                            interfaces.append(iface)

        except Exception:
            pass

        # Fallback to iwconfig if iw didn't work or found nothing
        if not interfaces:
            try:
                # Use iwconfig to find wireless interfaces
                result = subprocess.run(
                    [find_command('iwconfig')],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                for line in result.stdout.split('\n'):
                    if 'IEEE 802.11' in line or 'ESSID' in line or 'Mode:' in line:
                        # Extract interface name (first word)
                        parts = line.split()
                        if parts:
                            iface = parts[0]
                            if iface and not iface.startswith(' '):
                                interfaces.append(iface)

            except Exception:
                # Silently fail if iwconfig is not available
                pass

        if not interfaces:
            print("[!] No wireless interface found for MAC spoofing")

        return list(set(interfaces))  # Remove duplicates

    @staticmethod
    def is_monitor_mode(interface: str) -> bool:
        """Check if interface is in monitor mode"""
        # Try iw first (more modern and widely available)
        try:
            result = subprocess.run(
                [find_command('iw'), 'dev', interface, 'info'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if 'type monitor' in result.stdout.lower():
                return True

        except Exception:
            pass

        # Fallback to iwconfig if available
        try:
            result = subprocess.run(
                [find_command('iwconfig'), interface],
                capture_output=True,
                text=True,
                timeout=5
            )

            if 'Mode:Monitor' in result.stdout:
                return True

        except Exception:
            pass

        # Last resort: check interface name
        # Most monitor interfaces have 'mon' in the name
        return 'mon' in interface.lower()


    @staticmethod
    def get_monitor_interface() -> Optional[str]:
        """Get existing monitor mode interface or None"""
        interfaces = WiFiMonitorManager.get_wireless_interfaces()

        for iface in interfaces:
            if WiFiMonitorManager.is_monitor_mode(iface):
                return iface

        return None

    @staticmethod
    def enable_monitor_mode(interface: str) -> Tuple[bool, Optional[str], str]:
        """
        Enable monitor mode on interface WITHOUT killing NetworkManager

        Returns:
            (success: bool, monitor_interface: str, message: str)
        """
        try:
            # Method 1: Try using iw directly (preserves NetworkManager)
            print(f"[*] Enabling monitor mode on {interface} using iw...")

            # First, unmanage the interface from NetworkManager without killing the service
            # (Skip if NetworkManager is not running)
            print(f"[*] Checking NetworkManager status...")
            nm_check = subprocess.run(
                ['systemctl', 'is-active', 'NetworkManager'],
                capture_output=True,
                text=True,
                timeout=2
            )

            if nm_check.returncode == 0 and 'active' in nm_check.stdout:
                print(f"[*] Unmanaging {interface} from NetworkManager...")
                subprocess.run(
                    ['sudo', 'nmcli', 'device', 'set', interface, 'managed', 'no'],
                    capture_output=True,
                    timeout=5
                )
            else:
                print(f"[*] NetworkManager not running - skipping unmanage step")

            # Bring interface down
            subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'down'],
                capture_output=True,
                timeout=5
            )

            # Set monitor mode using iw
            result = subprocess.run(
                ['sudo', find_command('iw'), 'dev', interface, 'set', 'type', 'monitor'],
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

            # Verify monitor mode was enabled
            if WiFiMonitorManager.is_monitor_mode(interface):
                print(f"[+] Successfully enabled monitor mode on {interface}")
                return True, interface, f"Monitor mode enabled on {interface} (NetworkManager preserved)"

            # Method 2: Fallback to airmon-ng if iw method failed
            print(f"[*] iw method failed, trying airmon-ng without killing NetworkManager...")

            # Just use airmon-ng start without 'check kill'
            result = subprocess.run(
                ['sudo', find_command('airmon-ng'), 'start', interface],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse output to find monitor interface name
            monitor_iface = None

            # Look for patterns like "wlan0mon" or "mon0"
            for line in result.stdout.split('\n'):
                # Pattern: (monitor mode enabled on wlan0mon)
                match = re.search(r'monitor mode (?:enabled|vif enabled)(?: on| for) (\w+)', line, re.IGNORECASE)
                if match:
                    monitor_iface = match.group(1)
                    break

            # If not found in output, try common patterns
            if not monitor_iface:
                if 'mon' not in interface:
                    # Try wlan0 -> wlan0mon
                    test_iface = f"{interface}mon"
                    if WiFiMonitorManager.is_monitor_mode(test_iface):
                        monitor_iface = test_iface

            if monitor_iface:
                # Unmanage the new monitor interface too
                subprocess.run(
                    ['sudo', 'nmcli', 'device', 'set', monitor_iface, 'managed', 'no'],
                    capture_output=True,
                    timeout=5
                )
                return True, monitor_iface, f"Monitor mode enabled on {monitor_iface} (NetworkManager preserved)"
            else:
                return False, None, "Failed to enable monitor mode (interface not found)"

        except subprocess.TimeoutExpired:
            return False, None, "Timeout enabling monitor mode"
        except Exception as e:
            return False, None, f"Error enabling monitor mode: {e}"

    @staticmethod
    def auto_enable_monitor() -> Tuple[bool, Optional[str], str]:
        """
        Automatically detect WiFi card and enable monitor mode

        Returns:
            (success: bool, monitor_interface: str, message: str)
        """
        # Check if already in monitor mode
        existing_monitor = WiFiMonitorManager.get_monitor_interface()
        if existing_monitor:
            return True, existing_monitor, f"Already in monitor mode: {existing_monitor}"

        # Get wireless interfaces
        interfaces = WiFiMonitorManager.get_wireless_interfaces()

        if not interfaces:
            return False, None, "No wireless interfaces detected"

        # Filter out monitor interfaces and loopback
        managed_interfaces = [
            iface for iface in interfaces
            if 'mon' not in iface.lower() and iface != 'lo'
        ]

        if not managed_interfaces:
            return False, None, "No managed wireless interfaces found"

        # Try to enable monitor mode on first managed interface
        primary_interface = managed_interfaces[0]

        print(f"[*] Detected wireless interface: {primary_interface}")
        success, monitor_iface, message = WiFiMonitorManager.enable_monitor_mode(primary_interface)

        return success, monitor_iface, message

    @staticmethod
    def disable_monitor_mode(interface: str) -> Tuple[bool, str]:
        """
        Disable monitor mode on interface and restore NetworkManager management

        Returns:
            (success: bool, message: str)
        """
        try:
            # Get the original interface name (remove 'mon' suffix if present)
            original_iface = interface.replace('mon', '') if interface.endswith('mon') else interface

            # Method 1: Try using iw to switch back to managed mode
            print(f"[*] Disabling monitor mode on {interface}...")

            # Bring interface down
            subprocess.run(
                ['sudo', 'ip', 'link', 'set', interface, 'down'],
                capture_output=True,
                timeout=5
            )

            # Set managed mode using iw
            result = subprocess.run(
                ['sudo', find_command('iw'), 'dev', interface, 'set', 'type', 'managed'],
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

            # Re-enable NetworkManager management
            print(f"[*] Restoring NetworkManager management of {interface}...")
            subprocess.run(
                ['sudo', 'nmcli', 'device', 'set', interface, 'managed', 'yes'],
                capture_output=True,
                timeout=5
            )

            # If original interface is different, also enable it
            if original_iface != interface:
                subprocess.run(
                    ['sudo', 'nmcli', 'device', 'set', original_iface, 'managed', 'yes'],
                    capture_output=True,
                    timeout=5
                )

            # Verify it's no longer in monitor mode
            if not WiFiMonitorManager.is_monitor_mode(interface):
                print(f"[+] Successfully disabled monitor mode on {interface}")
                return True, f"Monitor mode disabled on {interface} (NetworkManager restored)"

            # Method 2: Fallback to airmon-ng
            print(f"[*] iw method failed, trying airmon-ng...")
            result = subprocess.run(
                ['sudo', find_command('airmon-ng'), 'stop', interface],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Restore NetworkManager management for both interfaces
            subprocess.run(
                ['sudo', 'nmcli', 'device', 'set', interface, 'managed', 'yes'],
                capture_output=True,
                timeout=5
            )
            if original_iface != interface:
                subprocess.run(
                    ['sudo', 'nmcli', 'device', 'set', original_iface, 'managed', 'yes'],
                    capture_output=True,
                    timeout=5
                )

            # Verify interface is no longer in monitor mode (check both interfaces)
            import time
            time.sleep(0.5)  # Give system time to process changes

            still_monitor = False
            try:
                # Check if original interface or current interface is still in monitor mode
                for check_iface in [interface, original_iface]:
                    if WiFiMonitorManager.is_monitor_mode(check_iface):
                        still_monitor = True
                        break
            except:
                pass

            if not still_monitor:
                return True, f"Monitor mode disabled on {interface} (NetworkManager restored)"
            elif result.returncode == 0:
                return True, f"Monitor mode disabled on {interface} (NetworkManager restored)"
            else:
                return False, f"Failed to disable monitor mode: {result.stderr}"

        except Exception as e:
            return False, f"Error disabling monitor mode: {e}"
