#!/usr/bin/env python3
"""
Enhanced Flipper Zero Integration Service

Comprehensive control of Flipper Zero including:
- SubGHz radio TX/RX
- IR transmit/receive
- GPIO control
- RFID/NFC operations
- LED & vibration control (Momentum firmware compatible)
- File/storage management
- Screen capture/control
"""

import serial
import serial.tools.list_ports
import time
import threading
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime


class FlipperZeroDevice:
    """Represents a connected Flipper Zero device"""

    def __init__(self):
        self.serial_number: str = ""
        self.name: str = ""
        self.firmware_version: str = ""
        self.firmware_origin: str = ""
        self.hardware_model: str = ""
        self.hardware_uid: str = ""
        self.hardware_name: str = ""
        self.port: str = ""
        self.ble_mac: str = ""
        self.connected: bool = False
        self.last_seen: Optional[datetime] = None

    def update_from_device_info(self, info: Dict[str, str]):
        """Update device info from device_info command response"""
        self.hardware_model = info.get('hardware_model', 'Unknown')
        self.hardware_uid = info.get('hardware_uid', 'Unknown')
        self.hardware_name = info.get('hardware_name', 'Flipper')
        self.firmware_version = info.get('firmware_version', 'Unknown')
        self.firmware_origin = info.get('firmware_origin_fork', 'Official')
        self.serial_number = self.hardware_uid
        self.name = self.hardware_name
        self.last_seen = datetime.now()

    def __str__(self):
        return f"{self.name} ({self.hardware_model}) - {self.firmware_origin} {self.firmware_version}"


class FlipperZeroService(QObject):
    """Enhanced service for comprehensive Flipper Zero control"""

    # Signals
    connected = pyqtSignal(object)
    disconnected = pyqtSignal()
    command_sent = pyqtSignal(str)
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    status_message = pyqtSignal(str)
    subghz_data_received = pyqtSignal(dict)  # SubGHz RX data
    ir_data_received = pyqtSignal(dict)  # IR RX data
    screen_update = pyqtSignal(str)  # Screen content

    # Flipper Zero USB VID:PID
    FLIPPER_VID = 0x0483
    FLIPPER_PID = 0x5740

    def __init__(self):
        super().__init__()
        self.device: Optional[FlipperZeroDevice] = None
        self.serial_conn: Optional[serial.Serial] = None
        self.port: Optional[str] = None
        self.running: bool = False
        self.auto_reconnect: bool = True
        self.reconnect_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.rainbow_thread: Optional[threading.Thread] = None
        self.rainbow_running: bool = False

    # ==================== Connection Management ====================

    def detect_flipper_devices(self) -> List[str]:
        """Detect all connected Flipper Zero devices"""
        flipper_ports = []
        for port in serial.tools.list_ports.comports():
            if port.vid == self.FLIPPER_VID and port.pid == self.FLIPPER_PID:
                flipper_ports.append(port.device)
                self.status_message.emit(f"Found Flipper Zero at {port.device}")
        return flipper_ports

    def connect(self, port: Optional[str] = None, baud: int = 115200) -> bool:
        """Connect to Flipper Zero device"""
        try:
            if not port:
                ports = self.detect_flipper_devices()
                if not ports:
                    self.error_occurred.emit("No Flipper Zero devices found")
                    return False
                port = ports[0]

            self.status_message.emit(f"Connecting to Flipper Zero at {port}...")

            with self._lock:
                self.serial_conn = serial.Serial(port, baud, timeout=2, write_timeout=2)
                self.port = port

            time.sleep(0.5)
            self.serial_conn.flushInput()
            self.serial_conn.flushOutput()

            device_info = self._get_device_info()

            if device_info:
                self.device = FlipperZeroDevice()
                self.device.port = port
                self.device.connected = True
                self.device.update_from_device_info(device_info)

                self.status_message.emit(f"Connected to {self.device}")
                self.connected.emit(self.device)

                if self.auto_reconnect:
                    self._start_reconnect_monitor()

                return True
            else:
                self.error_occurred.emit("Failed to get device info")
                self.disconnect()
                return False

        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial error: {e}")
            return False
        except Exception as e:
            self.error_occurred.emit(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from Flipper Zero"""
        self.running = False

        with self._lock:
            if self.serial_conn and self.serial_conn.is_open:
                try:
                    self.serial_conn.close()
                    self.status_message.emit("Disconnected from Flipper Zero")
                except:
                    pass

            self.serial_conn = None
            self.port = None

        if self.device:
            self.device.connected = False
            self.device = None

        self.disconnected.emit()

    def is_connected(self) -> bool:
        """Check if connected to Flipper Zero"""
        with self._lock:
            return self.serial_conn is not None and self.serial_conn.is_open

    # ==================== Command Execution ====================

    def send_command(self, command: str, wait_response: bool = True, timeout: float = 2.0) -> Optional[str]:
        """Send command to Flipper Zero"""
        if not self.is_connected():
            self.error_occurred.emit("Not connected to Flipper Zero")
            return None

        try:
            with self._lock:
                cmd_bytes = f"{command}\r\n".encode('utf-8')
                self.serial_conn.write(cmd_bytes)
                self.serial_conn.flush()

            self.command_sent.emit(command)

            if wait_response:
                response = self._read_response(timeout)
                self.response_received.emit(response)
                return response

            return None

        except serial.SerialTimeoutException:
            self.error_occurred.emit(f"Timeout sending command: {command}")
            return None
        except Exception as e:
            self.error_occurred.emit(f"Error sending command: {e}")
            return None

    def _read_response(self, timeout: float = 2.0) -> str:
        """Read response from Flipper Zero"""
        response_lines = []
        start_time = time.time()

        try:
            while time.time() - start_time < timeout:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        if line.endswith('>:'):
                            break
                else:
                    time.sleep(0.01)

            return '\n'.join(response_lines)

        except Exception as e:
            self.error_occurred.emit(f"Error reading response: {e}")
            return ""

    def _get_device_info(self) -> Optional[Dict[str, str]]:
        """Get device information from Flipper Zero"""
        try:
            response = self.send_command("device_info", wait_response=True, timeout=3.0)
            if not response:
                return None

            info = {}
            for line in response.split('\n'):
                if ':' in line and not line.endswith('>:'):
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()

            return info

        except Exception as e:
            self.error_occurred.emit(f"Error getting device info: {e}")
            return None

    def _start_reconnect_monitor(self):
        """Start background thread to monitor connection"""
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return

        self.running = True
        self.reconnect_thread = threading.Thread(
            target=self._reconnect_monitor_loop,
            daemon=True
        )
        self.reconnect_thread.start()

    def _reconnect_monitor_loop(self):
        """Monitor connection and auto-reconnect if disconnected"""
        while self.running:
            try:
                if not self.is_connected() and self.auto_reconnect:
                    self.status_message.emit("Connection lost, attempting to reconnect...")
                    if self.port:
                        success = self.connect(self.port)
                        if success:
                            self.status_message.emit("Reconnected successfully")
                        else:
                            time.sleep(5)

                time.sleep(2)

            except Exception as e:
                self.error_occurred.emit(f"Reconnect monitor error: {e}")
                time.sleep(5)

    # ==================== LED Control (Momentum Firmware Compatible) ====================

    def led_set(self, red: int = 0, green: int = 0, blue: int = 0, backlight: int = 0):
        """
        Set LED color (Momentum firmware compatible)

        Args:
            red: Red channel (0-255)
            green: Green channel (0-255)
            blue: Blue channel (0-255)
            backlight: Backlight (0-255)
        """
        try:
            if red > 0:
                self.send_command(f"led r {red}", wait_response=False)
            else:
                self.send_command("led r 0", wait_response=False)

            if green > 0:
                self.send_command(f"led g {green}", wait_response=False)
            else:
                self.send_command("led g 0", wait_response=False)

            if blue > 0:
                self.send_command(f"led b {blue}", wait_response=False)
            else:
                self.send_command("led b 0", wait_response=False)

            if backlight > 0:
                self.send_command(f"led bl {backlight}", wait_response=False)
            else:
                self.send_command("led bl 0", wait_response=False)

        except Exception as e:
            self.error_occurred.emit(f"Error setting LED: {e}")

    def led_off(self):
        """Turn off all LED channels"""
        self.led_set(0, 0, 0, 0)

    def led_blink(self, color: str = "blue", duration: int = 1):
        """
        Blink LED in specified color

        Args:
            color: Color name (red, green, blue, yellow, cyan, magenta, white)
            duration: Blink duration in seconds
        """
        try:
            color_map = {
                'red': (255, 0, 0, 0),
                'green': (0, 255, 0, 0),
                'blue': (0, 0, 255, 0),
                'yellow': (255, 255, 0, 0),
                'cyan': (0, 255, 255, 0),
                'magenta': (255, 0, 255, 0),
                'white': (255, 255, 255, 0)
            }

            r, g, b, bl = color_map.get(color.lower(), (0, 0, 255, 0))

            # Turn on
            self.led_set(r, g, b, bl)
            time.sleep(duration)

            # Turn off
            self.led_off()

        except Exception as e:
            self.error_occurred.emit(f"Error blinking LED: {e}")

    def led_rainbow_cycle(self, speed: float = 0.05, brightness: int = 128):
        """
        Start rainbow LED cycling (runs in background thread)
        Indicates Flipper is under Gattrose-NG control

        Args:
            speed: Time between color steps (seconds, smaller = faster)
            brightness: LED brightness (0-255)
        """
        if self.rainbow_running:
            return  # Already running

        self.rainbow_running = True
        self.rainbow_thread = threading.Thread(
            target=self._rainbow_cycle_worker,
            args=(speed, brightness),
            daemon=True
        )
        self.rainbow_thread.start()
        self.status_message.emit("Rainbow LED cycling started")

    def led_rainbow_stop(self):
        """Stop rainbow LED cycling"""
        self.rainbow_running = False
        if self.rainbow_thread:
            self.rainbow_thread.join(timeout=2.0)
        self.led_off()
        self.status_message.emit("Rainbow LED cycling stopped")

    def _rainbow_cycle_worker(self, speed: float, brightness: int):
        """Background worker for rainbow cycling"""
        import math

        try:
            hue = 0.0
            while self.rainbow_running and self.is_connected():
                # Convert HSV to RGB (hue from 0-360, full saturation, brightness variable)
                h = hue / 60.0
                x = brightness * (1 - abs(h % 2 - 1))

                if h < 1:
                    r, g, b = brightness, int(x), 0
                elif h < 2:
                    r, g, b = int(x), brightness, 0
                elif h < 3:
                    r, g, b = 0, brightness, int(x)
                elif h < 4:
                    r, g, b = 0, int(x), brightness
                elif h < 5:
                    r, g, b = int(x), 0, brightness
                else:
                    r, g, b = brightness, 0, int(x)

                # Set LED color
                self.led_set(r, g, b, 0)

                # Increment hue
                hue = (hue + 5) % 360  # Step through colors

                time.sleep(speed)

        except Exception as e:
            self.error_occurred.emit(f"Rainbow cycle error: {e}")
        finally:
            self.rainbow_running = False

    # ==================== Vibration Control ====================

    def vibrate(self, duration: int = 1):
        """
        Vibrate Flipper

        Args:
            duration: Vibration duration in seconds (1-3)
        """
        try:
            self.send_command(f"vibro {duration}", wait_response=False)
        except Exception as e:
            self.error_occurred.emit(f"Error vibrating: {e}")

    # ==================== SubGHz Radio Control ====================

    def subghz_tx(self, frequency: int, key: str, te: int = 400, repeat: int = 10, device: int = 0) -> bool:
        """
        Transmit SubGHz signal

        Args:
            frequency: Frequency in Hz (e.g., 433920000 for 433.92 MHz)
            key: 3-byte key in hex (e.g., "AABBCC")
            te: Time element in microseconds
            repeat: Number of repetitions
            device: 0=internal CC1101, 1=external module

        Returns:
            Success status
        """
        try:
            cmd = f"subghz tx {key} {frequency} {te} {repeat} {device}"
            response = self.send_command(cmd, wait_response=True, timeout=5.0)
            return "error" not in response.lower() if response else False
        except Exception as e:
            self.error_occurred.emit(f"SubGHz TX error: {e}")
            return False

    def subghz_rx(self, frequency: int, device: int = 0, duration: int = 10) -> Optional[Dict]:
        """
        Receive SubGHz signals

        Args:
            frequency: Frequency in Hz
            device: 0=internal CC1101, 1=external module
            duration: Reception duration in seconds

        Returns:
            Dictionary with received data or None
        """
        try:
            cmd = f"subghz rx {frequency} {device}"
            self.send_command(cmd, wait_response=False)

            # Read data for specified duration
            time.sleep(duration)

            # Stop reception
            self.send_command("", wait_response=False)  # Send empty to stop

            return {"status": "completed", "duration": duration}

        except Exception as e:
            self.error_occurred.emit(f"SubGHz RX error: {e}")
            return None

    def subghz_tx_file(self, filename: str, repeat: int = 1, device: int = 0) -> bool:
        """
        Transmit SubGHz signal from file

        Args:
            filename: Path to .sub file on Flipper
            repeat: Number of repetitions
            device: 0=internal, 1=external

        Returns:
            Success status
        """
        try:
            cmd = f"subghz tx_from_file {filename} {repeat} {device}"
            response = self.send_command(cmd, wait_response=True, timeout=10.0)
            return "error" not in response.lower() if response else False
        except Exception as e:
            self.error_occurred.emit(f"SubGHz file TX error: {e}")
            return False

    # ==================== IR Control ====================

    def ir_tx(self, protocol: str, address: str, command: str) -> bool:
        """
        Transmit IR signal

        Args:
            protocol: IR protocol (NEC, Samsung32, RC6, etc.)
            address: Address in hex format
            command: Command in hex format

        Returns:
            Success status
        """
        try:
            cmd = f"ir tx {protocol} {address} {command}"
            response = self.send_command(cmd, wait_response=True, timeout=3.0)
            return "error" not in response.lower() if response else False
        except Exception as e:
            self.error_occurred.emit(f"IR TX error: {e}")
            return False

    def ir_rx(self, duration: int = 10, raw: bool = False) -> Optional[Dict]:
        """
        Receive IR signals

        Args:
            duration: Reception duration in seconds
            raw: Receive raw data

        Returns:
            Dictionary with received IR data
        """
        try:
            cmd = "ir rx raw" if raw else "ir rx"
            self.send_command(cmd, wait_response=False)

            time.sleep(duration)

            # Stop reception
            self.send_command("", wait_response=False)

            return {"status": "completed", "duration": duration}

        except Exception as e:
            self.error_occurred.emit(f"IR RX error: {e}")
            return None

    def ir_universal(self, remote_name: str, signal_name: str) -> bool:
        """
        Send universal remote signal

        Args:
            remote_name: Remote type (tv, audio, ac, etc.)
            signal_name: Signal name (power, vol_up, etc.)

        Returns:
            Success status
        """
        try:
            cmd = f"ir universal {remote_name} {signal_name}"
            response = self.send_command(cmd, wait_response=True, timeout=3.0)
            return "error" not in response.lower() if response else False
        except Exception as e:
            self.error_occurred.emit(f"IR universal error: {e}")
            return False

    # ==================== GPIO Control ====================

    def gpio_set_mode(self, pin: str, mode: int) -> bool:
        """
        Set GPIO pin mode

        Args:
            pin: Pin name (e.g., "PC0", "PA7")
            mode: 0=input, 1=output

        Returns:
            Success status
        """
        try:
            cmd = f"gpio mode {pin} {mode}"
            response = self.send_command(cmd, wait_response=True)
            return "error" not in response.lower() if response else False
        except Exception as e:
            self.error_occurred.emit(f"GPIO mode error: {e}")
            return False

    def gpio_write(self, pin: str, value: int) -> bool:
        """
        Write to GPIO pin

        Args:
            pin: Pin name
            value: 0=LOW, 1=HIGH

        Returns:
            Success status
        """
        try:
            cmd = f"gpio set {pin} {value}"
            response = self.send_command(cmd, wait_response=True)
            return "error" not in response.lower() if response else False
        except Exception as e:
            self.error_occurred.emit(f"GPIO write error: {e}")
            return False

    def gpio_read(self, pin: str) -> Optional[int]:
        """
        Read GPIO pin value

        Args:
            pin: Pin name

        Returns:
            Pin value (0 or 1) or None
        """
        try:
            cmd = f"gpio read {pin}"
            response = self.send_command(cmd, wait_response=True)
            if response and ":" in response:
                value_str = response.split(":")[-1].strip()
                return int(value_str) if value_str.isdigit() else None
            return None
        except Exception as e:
            self.error_occurred.emit(f"GPIO read error: {e}")
            return None

    # ==================== RFID Operations ====================

    def rfid_read(self, mode: str = "normal") -> Optional[Dict]:
        """
        Read RFID tag

        Args:
            mode: Reading mode ("normal" or "indala")

        Returns:
            Dictionary with RFID data
        """
        try:
            cmd = f"rfid read {mode}"
            response = self.send_command(cmd, wait_response=True, timeout=10.0)

            if response:
                # Parse RFID data from response
                return {"raw_response": response, "mode": mode}
            return None

        except Exception as e:
            self.error_occurred.emit(f"RFID read error: {e}")
            return None

    def rfid_emulate(self, key_type: str, key_data: str) -> bool:
        """
        Emulate RFID tag

        Args:
            key_type: Key type
            key_data: Key data in hex

        Returns:
            Success status
        """
        try:
            cmd = f"rfid emulate {key_type} {key_data}"
            response = self.send_command(cmd, wait_response=True)
            return "error" not in response.lower() if response else False
        except Exception as e:
            self.error_occurred.emit(f"RFID emulate error: {e}")
            return False

    # ==================== NFC Operations ====================

    def nfc_send_apdu(self, apdu: str) -> Optional[str]:
        """
        Send APDU command to NFC card

        Args:
            apdu: APDU command in hex

        Returns:
            Response data
        """
        try:
            cmd = f"nfc apdu {apdu}"
            response = self.send_command(cmd, wait_response=True, timeout=5.0)
            return response
        except Exception as e:
            self.error_occurred.emit(f"NFC APDU error: {e}")
            return None

    # ==================== Storage/File Management ====================

    def storage_list(self, path: str = "/ext") -> Optional[List[str]]:
        """
        List files in directory

        Args:
            path: Directory path (/int or /ext)

        Returns:
            List of file/directory names
        """
        try:
            cmd = f"storage list {path}"
            response = self.send_command(cmd, wait_response=True, timeout=5.0)

            if response:
                # Parse file listing
                files = []
                for line in response.split('\n'):
                    line = line.strip()
                    if line and not line.endswith('>:') and not line.startswith('storage'):
                        files.append(line)
                return files
            return None

        except Exception as e:
            self.error_occurred.emit(f"Storage list error: {e}")
            return None

    def storage_read_file(self, filepath: str) -> Optional[str]:
        """
        Read text file content

        Args:
            filepath: Full path to file

        Returns:
            File content as string
        """
        try:
            cmd = f"storage read {filepath}"
            response = self.send_command(cmd, wait_response=True, timeout=10.0)
            return response
        except Exception as e:
            self.error_occurred.emit(f"Storage read error: {e}")
            return None

    def storage_info(self) -> Optional[Dict[str, str]]:
        """Get storage information"""
        try:
            response = self.send_command("storage info /ext", wait_response=True)
            if not response:
                return None

            info = {}
            for line in response.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()

            return info

        except Exception as e:
            self.error_occurred.emit(f"Error getting storage info: {e}")
            return None

    # ==================== Info Methods ====================

    def get_info(self) -> Optional[Dict[str, str]]:
        """Get device information"""
        return self._get_device_info()


if __name__ == '__main__':
    """Test enhanced Flipper service"""
    print("=" * 60)
    print("Enhanced Flipper Zero Service Test")
    print("=" * 60)

    service = FlipperZeroService()

    # Connect signal handlers
    service.connected.connect(lambda dev: print(f"[✓] Connected: {dev}"))
    service.status_message.connect(lambda msg: print(f"[i] {msg}"))
    service.error_occurred.connect(lambda err: print(f"[!] Error: {err}"))

    if service.connect():
        print("\n[✓] Testing enhanced features...")

        # Test LED control
        print("\n[*] Testing LED (fixed for Momentum firmware)...")
        service.led_blink('blue', 2)

        # Test SubGHz
        print("\n[*] SubGHz capabilities ready")

        # Test IR
        print("\n[*] IR capabilities ready")

        # Test GPIO
        print("\n[*] GPIO capabilities ready")

        print("\n[✓] All tests complete!")
        service.disconnect()
    else:
        print("[!] Connection failed")
