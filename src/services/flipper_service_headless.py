#!/usr/bin/env python3
"""
Headless Flipper Zero Service (no PyQt dependency)
For use in system daemons and services
"""

import serial
import serial.tools.list_ports
import time
import threading
from pathlib import Path
from typing import Optional, Dict, List
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
        self.ble_mac = info.get('hardware_ble_mac', 'Unknown')
        self.serial_number = self.hardware_uid
        self.name = self.hardware_name
        self.last_seen = datetime.now()

    def __str__(self):
        return f"{self.name} ({self.hardware_model}) - {self.firmware_origin} {self.firmware_version}"


class FlipperZeroServiceHeadless:
    """Headless Flipper service without PyQt dependencies"""

    FLIPPER_VID = 0x0483
    FLIPPER_PID = 0x5740

    def __init__(self):
        self.device: Optional[FlipperZeroDevice] = None
        self.serial_conn: Optional[serial.Serial] = None
        self.port: Optional[str] = None
        self.running: bool = False
        self._lock = threading.Lock()
        self.rainbow_thread: Optional[threading.Thread] = None
        self.rainbow_running: bool = False

    def detect_flipper_devices(self) -> List[str]:
        """Detect all connected Flipper Zero devices"""
        flipper_ports = []
        for port in serial.tools.list_ports.comports():
            if port.vid == self.FLIPPER_VID and port.pid == self.FLIPPER_PID:
                flipper_ports.append(port.device)
        return flipper_ports

    def connect(self, port: Optional[str] = None, baud: int = 115200) -> bool:
        """Connect to Flipper Zero device"""
        try:
            if not port:
                ports = self.detect_flipper_devices()
                if not ports:
                    print("[!] No Flipper Zero devices found")
                    return False
                port = ports[0]

            print(f"[*] Connecting to Flipper Zero at {port}...")

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
                self.running = True
                return True
            else:
                self.disconnect()
                return False

        except Exception as e:
            print(f"[!] Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from Flipper Zero"""
        self.running = False
        self.led_rainbow_stop()

        with self._lock:
            if self.serial_conn and self.serial_conn.is_open:
                try:
                    self.serial_conn.close()
                except:
                    pass

        if self.device:
            self.device.connected = False
            self.device = None

    def is_connected(self) -> bool:
        """Check if connected"""
        return self.running and self.serial_conn and self.serial_conn.is_open

    def send_command(self, command: str, wait_response: bool = True, timeout: float = 2.0) -> Optional[str]:
        """Send command to Flipper"""
        if not self.is_connected():
            return None

        try:
            with self._lock:
                # Clear buffers
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()

                # Send command
                cmd = f"{command}\r\n"
                self.serial_conn.write(cmd.encode())
                self.serial_conn.flush()

                if not wait_response:
                    return ""

                # Read response
                start_time = time.time()
                response_lines = []

                while time.time() - start_time < timeout:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            response_lines.append(line)
                            if '>' in line:  # Prompt
                                break
                    time.sleep(0.01)

                return '\n'.join(response_lines)

        except Exception as e:
            print(f"[!] Command error: {e}")
            return None

    def _get_device_info(self) -> Optional[Dict[str, str]]:
        """Get device information"""
        response = self.send_command('device_info')
        if not response:
            return None

        info = {}
        for line in response.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()

        return info

    # ===== LED Control =====

    def led_set(self, red: int = 0, green: int = 0, blue: int = 0, backlight: int = 0):
        """Set LED color (Momentum firmware compatible)"""
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
            print(f"[!] LED set error: {e}")

    def led_off(self):
        """Turn off all LED channels"""
        self.led_set(0, 0, 0, 0)

    def led_rainbow_cycle(self, speed: float = 0.05, brightness: int = 128):
        """Start rainbow LED cycling"""
        if self.rainbow_running:
            return

        self.rainbow_running = True
        self.rainbow_thread = threading.Thread(
            target=self._rainbow_cycle_worker,
            args=(speed, brightness),
            daemon=True
        )
        self.rainbow_thread.start()

    def led_rainbow_stop(self):
        """Stop rainbow LED cycling"""
        self.rainbow_running = False
        if self.rainbow_thread:
            self.rainbow_thread.join(timeout=2.0)
        self.led_off()

    def _rainbow_cycle_worker(self, speed: float, brightness: int):
        """Background worker for rainbow cycling"""
        try:
            hue = 0.0
            while self.rainbow_running and self.is_connected():
                # HSV to RGB conversion
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

                self.led_set(r, g, b, 0)
                hue = (hue + 5) % 360
                time.sleep(speed)

        except Exception as e:
            print(f"[!] Rainbow cycle error: {e}")
        finally:
            self.rainbow_running = False

    def vibrate(self, duration: int = 1):
        """Vibrate Flipper"""
        try:
            self.send_command(f"vibro {duration}", wait_response=False)
        except Exception as e:
            print(f"[!] Vibrate error: {e}")
