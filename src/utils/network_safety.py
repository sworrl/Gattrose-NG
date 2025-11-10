"""
Network Safety Module
Ensures we never kill our own internet connection or NetworkManager
"""

import subprocess
import time
from typing import Optional, Dict, Set, Tuple
from pathlib import Path


class NetworkSafety:
    """Protects our own network connection from attacks"""

    def __init__(self):
        self.connected_bssid: Optional[str] = None
        self.connected_ssid: Optional[str] = None
        self.connected_interface: Optional[str] = None
        self.gateway_ip: Optional[str] = None
        self.blacklisted_bssids: Set[str] = set()
        self.nm_restart_count = 0
        self.last_nm_check = 0

        # Update connection info on init
        self.update_connection_info()

    def update_connection_info(self):
        """Update information about our current connection"""
        try:
            # Get connected BSSID and interface from NetworkManager
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'ACTIVE,SSID,BSSID,DEVICE', 'dev', 'wifi'],
                capture_output=True,
                text=True,
                timeout=5
            )

            for line in result.stdout.strip().split('\n'):
                if line.startswith('yes:'):
                    parts = line.split(':')
                    if len(parts) >= 4:
                        self.connected_ssid = parts[1] if parts[1] else None
                        self.connected_bssid = parts[2].upper() if parts[2] else None
                        self.connected_interface = parts[3] if parts[3] else None

                        if self.connected_bssid:
                            self.blacklisted_bssids.add(self.connected_bssid)
                            print(f"[SAFETY] Protected connection: {self.connected_ssid} ({self.connected_bssid}) on {self.connected_interface}")
                        break

            # Get gateway IP
            result = subprocess.run(
                ['ip', 'route'],
                capture_output=True,
                text=True,
                timeout=5
            )

            for line in result.stdout.strip().split('\n'):
                if 'default' in line:
                    parts = line.split()
                    if len(parts) >= 3 and parts[0] == 'default':
                        self.gateway_ip = parts[2]
                        print(f"[SAFETY] Gateway: {self.gateway_ip}")
                        break

            # Also get any bridge connections
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE', 'dev'],
                capture_output=True,
                text=True,
                timeout=5
            )

            for line in result.stdout.strip().split('\n'):
                if 'bridge' in line.lower() and 'connected' in line.lower():
                    parts = line.split(':')
                    if parts:
                        bridge_dev = parts[0]
                        print(f"[SAFETY] Protected bridge: {bridge_dev}")

        except Exception as e:
            print(f"[SAFETY] Warning: Could not get connection info: {e}")

    def is_safe_to_attack(self, bssid: str, ssid: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if it's safe to attack a network

        Returns:
            Tuple of (is_safe, reason)
        """
        bssid_upper = bssid.upper()

        # Never attack our own connection
        if self.connected_bssid and bssid_upper == self.connected_bssid:
            return False, f"This is our active connection ({self.connected_ssid})"

        # Never attack blacklisted BSSIDs
        if bssid_upper in self.blacklisted_bssids:
            return False, f"Network is blacklisted (protected connection)"

        # Check if this BSSID belongs to our gateway (same first 3 octets = same router)
        if self.connected_bssid:
            our_prefix = ':'.join(self.connected_bssid.split(':')[:3])
            target_prefix = ':'.join(bssid_upper.split(':')[:3])

            if our_prefix == target_prefix:
                # Likely same router/network, be cautious
                self.blacklisted_bssids.add(bssid_upper)
                return False, f"Network appears to be on same router as our connection"

        return True, "Safe to attack"

    def ensure_networkmanager_running(self) -> bool:
        """
        Ensure NetworkManager is running, restart if needed

        Returns:
            True if NetworkManager is running
        """
        current_time = time.time()

        # Only check every 30 seconds to avoid spam
        if current_time - self.last_nm_check < 30:
            return True

        self.last_nm_check = current_time

        try:
            # Check if NetworkManager is running
            result = subprocess.run(
                ['systemctl', 'is-active', 'NetworkManager'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0 or result.stdout.strip() != 'active':
                print("[SAFETY] WARNING: NetworkManager is not running!")
                print("[SAFETY] Attempting to restart NetworkManager...")

                restart_result = subprocess.run(
                    ['sudo', 'systemctl', 'restart', 'NetworkManager'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if restart_result.returncode == 0:
                    self.nm_restart_count += 1
                    print(f"[SAFETY] NetworkManager restarted (restart #{self.nm_restart_count})")

                    # Wait for it to come back up
                    time.sleep(3)

                    # Update connection info
                    self.update_connection_info()
                    return True
                else:
                    print(f"[SAFETY] ERROR: Failed to restart NetworkManager: {restart_result.stderr}")
                    return False

            return True

        except Exception as e:
            print(f"[SAFETY] Error checking NetworkManager: {e}")
            return False

    def verify_internet_connectivity(self) -> bool:
        """
        Verify we still have internet connectivity

        Returns:
            True if we can reach the gateway
        """
        if not self.gateway_ip:
            return False

        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', self.gateway_ip],
                capture_output=True,
                timeout=5
            )

            return result.returncode == 0

        except Exception as e:
            print(f"[SAFETY] Warning: Could not verify connectivity: {e}")
            return False

    def add_to_blacklist(self, bssid: str, reason: str = "Manual blacklist"):
        """Manually add a BSSID to the blacklist"""
        bssid_upper = bssid.upper()
        self.blacklisted_bssids.add(bssid_upper)
        print(f"[SAFETY] Blacklisted {bssid_upper}: {reason}")

    def get_blacklist(self) -> Set[str]:
        """Get the current blacklist"""
        return self.blacklisted_bssids.copy()

    def get_safety_status(self) -> Dict:
        """Get current safety status for monitoring"""
        return {
            'connected_bssid': self.connected_bssid,
            'connected_ssid': self.connected_ssid,
            'connected_interface': self.connected_interface,
            'gateway_ip': self.gateway_ip,
            'blacklisted_count': len(self.blacklisted_bssids),
            'nm_restart_count': self.nm_restart_count,
            'internet_ok': self.verify_internet_connectivity() if self.gateway_ip else None
        }


# Singleton instance
_network_safety_instance: Optional[NetworkSafety] = None


def get_network_safety() -> NetworkSafety:
    """Get the singleton NetworkSafety instance"""
    global _network_safety_instance

    if _network_safety_instance is None:
        _network_safety_instance = NetworkSafety()

    return _network_safety_instance
