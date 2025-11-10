"""
WPA/WPA2 Cracking Service for Gattrose-NG
GPU-accelerated password cracking using hashcat with managed dictionaries
"""

import subprocess
import re
import time
import threading
from pathlib import Path
from typing import Optional, Callable, Tuple
from .dictionary_manager import DictionaryManager


class WPACrackService:
    """Service for WPA/WPA2 password cracking with hashcat"""

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("/opt/gattrose-ng/data")
        self.dict_manager = DictionaryManager(data_dir)
        self.hashcat_process = None
        self.running = False
        self.progress_callback = None
        self.status_callback = None
        self._lock = threading.Lock()

    def crack_handshake(self, handshake_file: str, bssid: str, essid: str = "",
                       wordlist_size: int = 10000000,
                       progress_callback: Callable = None,
                       status_callback: Callable = None,
                       use_rules: bool = False) -> dict:
        """
        Crack WPA/WPA2 handshake using hashcat with GPU acceleration
        handshake_file: Path to .cap, .hccapx, or .22000 file
        wordlist_size: Number of passwords to try (default 10M)
        use_rules: Apply hashcat rules for password mutations
        Returns: {'success': bool, 'password': str, 'error': str, 'stats': dict}
        """
        with self._lock:
            if self.running:
                return {'success': False, 'error': 'Crack already in progress'}

            self.running = True
            self.progress_callback = progress_callback
            self.status_callback = status_callback

        print(f"[WPA-CRACK] Starting hashcat crack on {essid} ({bssid})")
        print(f"[WPA-CRACK] Wordlist size: {wordlist_size:,} passwords")

        try:
            # Convert handshake to hashcat format if needed
            hash_file = self._prepare_hash_file(handshake_file)
            if not hash_file:
                return {'success': False, 'error': 'Failed to convert handshake to hashcat format'}

            # Export optimized wordlist from dictionary manager
            wordlist_file = self.data_dir / "wordlists" / f"crack_{bssid.replace(':', '')}.txt"
            wordlist_file.parent.mkdir(exist_ok=True)

            if self.status_callback:
                self.status_callback("Preparing optimized wordlist...")

            exported = self.dict_manager.export_optimized_wordlist(
                wordlist_file,
                max_passwords=wordlist_size,
                min_length=8,
                max_length=63
            )

            if exported == 0:
                return {
                    'success': False,
                    'error': 'No passwords in dictionary. Run dictionary download first.'
                }

            print(f"[WPA-CRACK] Using {exported:,} passwords from optimized dictionary")

            # Build hashcat command
            # Mode 22000: WPA-PBKDF2-PMKID+EAPOL (newer format)
            # Mode 2500: WPA/WPA2 (legacy .hccapx format)
            mode = "22000" if hash_file.endswith('.22000') else "2500"

            cmd = [
                'hashcat',
                '-m', mode,  # WPA/WPA2 mode
                '-a', '0',   # Straight attack mode
                hash_file,
                str(wordlist_file),
                '--status',
                '--status-timer', '5',  # Status update every 5 seconds
                '--force',   # Ignore warnings
                '-O',        # Optimized kernels
                '-w', '3'    # Workload profile: high performance
            ]

            if use_rules:
                # Add best64.rule for common password mutations
                cmd.extend(['-r', '/usr/share/hashcat/rules/best64.rule'])

            # Output file for cracked passwords
            potfile = self.data_dir / "cracked" / f"{bssid.replace(':', '')}.pot"
            potfile.parent.mkdir(exist_ok=True)
            cmd.extend(['--potfile-path', str(potfile)])

            if self.status_callback:
                self.status_callback(f"Launching hashcat GPU cracking...")

            # Start hashcat process
            start_time = time.time()
            self.hashcat_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )

            # Monitor output
            password = None
            last_progress = 0
            total_candidates = exported
            candidates_tested = 0
            speed = 0  # H/s

            for line in iter(self.hashcat_process.stdout.readline, ''):
                if not self.running:
                    self.hashcat_process.terminate()
                    return {'success': False, 'error': 'Crack cancelled by user'}

                line = line.strip()
                if not line:
                    continue

                # Log important lines
                if any(keyword in line.lower() for keyword in ['cracked', 'exhausted', 'progress', 'speed']):
                    print(f"[WPA-CRACK] {line}")

                # Parse hashcat status output
                # Progress: [######...] 45% (4500000/10000000)
                progress_match = re.search(r'Progress.*?(\d+)%', line)
                if progress_match:
                    progress = int(progress_match.group(1))
                    if progress != last_progress:
                        last_progress = progress
                        if self.progress_callback:
                            self.progress_callback(progress)

                # Speed: 123.4 MH/s
                speed_match = re.search(r'Speed.*?:\s*([\d.]+)\s*([kMGT]?)H/s', line)
                if speed_match:
                    speed_val = float(speed_match.group(1))
                    speed_unit = speed_match.group(2)
                    multipliers = {'k': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12}
                    speed = speed_val * multipliers.get(speed_unit, 1)

                    # Calculate ETA
                    if speed > 0 and progress > 0:
                        remaining = total_candidates * (100 - progress) / 100
                        eta_seconds = int(remaining / speed)
                        if self.status_callback:
                            eta_str = self._format_time(eta_seconds)
                            self.status_callback(f"Speed: {speed_val:.1f} {speed_unit}H/s, ETA: {eta_str}")

                # Cracked password found
                # Format varies, but usually contains the BSSID and password
                if ':' in line and bssid.replace(':', '').lower() in line.lower():
                    # Try to extract password from line
                    # Format: <hash>:<password>
                    parts = line.split(':')
                    if len(parts) >= 2:
                        password = ':'.join(parts[1:]).strip()
                        print(f"[WPA-CRACK] ✓ PASSWORD FOUND: {password}")
                        if self.status_callback:
                            self.status_callback(f"✓ Password cracked: {password}")

                # Check for completion messages
                if "Cracked" in line or "exhausted" in line.lower():
                    if "0 cracked" in line.lower():
                        print(f"[WPA-CRACK] Password not found in wordlist")
                    break

            # Wait for process to complete
            self.hashcat_process.wait(timeout=3600)  # 1 hour max

            elapsed = time.time() - start_time

            if password:
                print(f"[WPA-CRACK] ✓ SUCCESS! Password: {password} (elapsed: {elapsed:.1f}s)")
                return {
                    'success': True,
                    'password': password,
                    'elapsed_seconds': elapsed,
                    'wordlist_size': exported,
                    'stats': {
                        'speed': speed,
                        'total_candidates': total_candidates
                    }
                }
            else:
                # Check potfile in case we missed the output
                password = self._check_potfile(potfile, bssid)
                if password:
                    print(f"[WPA-CRACK] ✓ Found in potfile: {password}")
                    return {
                        'success': True,
                        'password': password,
                        'elapsed_seconds': elapsed,
                        'wordlist_size': exported
                    }

                print(f"[WPA-CRACK] Failed to crack password")
                return {
                    'success': False,
                    'error': 'Password not found in wordlist',
                    'wordlist_size': exported,
                    'elapsed_seconds': elapsed
                }

        except subprocess.TimeoutExpired:
            if self.hashcat_process:
                self.hashcat_process.kill()
            return {
                'success': False,
                'error': 'Hashcat crack timed out (1 hour)',
                'wordlist_size': exported if 'exported' in locals() else 0
            }

        except Exception as e:
            print(f"[WPA-CRACK] Error during crack: {e}")
            return {
                'success': False,
                'error': str(e),
                'wordlist_size': exported if 'exported' in locals() else 0
            }

        finally:
            self.running = False
            self.hashcat_process = None

    def _prepare_hash_file(self, handshake_file: str) -> Optional[str]:
        """
        Convert handshake file to hashcat format if needed
        Returns: Path to hash file in hashcat format
        """
        handshake_path = Path(handshake_file)

        if not handshake_path.exists():
            print(f"[WPA-CRACK] Error: Handshake file not found: {handshake_file}")
            return None

        # Already in hashcat format
        if handshake_file.endswith('.22000') or handshake_file.endswith('.hccapx'):
            return handshake_file

        # Convert .cap to hashcat format
        if handshake_file.endswith('.cap'):
            # Try hcxpcapngtool first (newer, better)
            hash_file = handshake_file.replace('.cap', '.22000')
            try:
                result = subprocess.run(
                    ['hcxpcapngtool', '-o', hash_file, handshake_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0 and Path(hash_file).exists():
                    print(f"[WPA-CRACK] Converted to 22000 format: {hash_file}")
                    return hash_file
            except FileNotFoundError:
                print(f"[WPA-CRACK] hcxpcapngtool not found, trying cap2hccapx...")

            # Fall back to cap2hccapx (legacy)
            hash_file = handshake_file.replace('.cap', '.hccapx')
            try:
                result = subprocess.run(
                    ['cap2hccapx', handshake_file, hash_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0 and Path(hash_file).exists():
                    print(f"[WPA-CRACK] Converted to hccapx format: {hash_file}")
                    return hash_file
            except Exception as e:
                print(f"[WPA-CRACK] Conversion failed: {e}")

        print(f"[WPA-CRACK] Failed to convert {handshake_file} to hashcat format")
        return None

    def _check_potfile(self, potfile: Path, bssid: str) -> Optional[str]:
        """
        Check hashcat potfile for cracked password
        Returns: Password if found, None otherwise
        """
        if not potfile.exists():
            return None

        try:
            with open(potfile, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if bssid.replace(':', '').lower() in line.lower():
                        # Format: <hash>:<password>
                        parts = line.strip().split(':')
                        if len(parts) >= 2:
                            return ':'.join(parts[1:])
        except Exception as e:
            print(f"[WPA-CRACK] Error reading potfile: {e}")

        return None

    def _format_time(self, seconds: int) -> str:
        """Format seconds into human readable time"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"

    def stop_crack(self):
        """Stop current crack operation"""
        with self._lock:
            self.running = False
            if self.hashcat_process:
                try:
                    self.hashcat_process.terminate()
                    self.hashcat_process.wait(timeout=5)
                except:
                    self.hashcat_process.kill()
                print("[WPA-CRACK] Crack stopped")

    def is_running(self) -> bool:
        """Check if crack is currently running"""
        return self.running

    def check_hashcat_available(self) -> Tuple[bool, str]:
        """
        Check if hashcat is installed and GPU is available
        Returns: (available: bool, message: str)
        """
        try:
            result = subprocess.run(
                ['hashcat', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]

                # Check for OpenCL/CUDA devices
                result = subprocess.run(
                    ['hashcat', '-I'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                gpu_count = result.stdout.lower().count('gpu')
                if gpu_count > 0:
                    return (True, f"Hashcat {version} with {gpu_count} GPU(s)")
                else:
                    return (True, f"Hashcat {version} (CPU only)")
            else:
                return (False, "Hashcat installed but not working")

        except FileNotFoundError:
            return (False, "Hashcat not installed. Install with: sudo apt install hashcat")
        except Exception as e:
            return (False, f"Error checking hashcat: {e}")
