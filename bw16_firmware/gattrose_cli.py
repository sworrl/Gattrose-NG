#!/usr/bin/env python3
"""
Gattrose-NG Interactive CLI Tool
For testing and flashing BW16 firmware

Usage:
    ./gattrose_cli.py                    # Interactive mode
    ./gattrose_cli.py --flash            # Flash firmware then interactive
    ./gattrose_cli.py --port /dev/ttyUSB1  # Specify port
"""

import serial
import serial.tools.list_ports
import time
import argparse
import subprocess
import sys
import os
import re
from typing import Optional, List, Tuple

# Protocol constants
STX = 0x02
ETX = 0x03
SEP = 0x1D

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def color(text, c):
    return f"{c}{text}{Colors.ENDC}"

class GattroseCLI:
    def __init__(self, port: str = '/dev/ttyUSB0', baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser: Optional[serial.Serial] = None
        self.networks: List[dict] = []
        self.clients: List[dict] = []
        self.firmware_dir = os.path.dirname(os.path.abspath(__file__))

    def connect(self) -> bool:
        """Connect to the BW16 board"""
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            print(color(f"Connected to {self.port}", Colors.GREEN))
            return True
        except Exception as e:
            print(color(f"Failed to connect: {e}", Colors.RED))
            return False

    def disconnect(self):
        """Disconnect from the board"""
        if self.ser:
            self.ser.close()
            self.ser = None

    def send_cmd(self, cmd: str, args: str = "") -> None:
        """Send a command to the BW16"""
        if not self.ser:
            print(color("Not connected!", Colors.RED))
            return
        packet = bytes([STX]) + cmd.encode() + args.encode() + bytes([ETX])
        self.ser.write(packet)
        self.ser.flush()

    def read_response(self, timeout: float = 2.0) -> str:
        """Read response from BW16"""
        if not self.ser:
            return ""
        data = b""
        start = time.time()
        while time.time() - start < timeout:
            chunk = self.ser.read(1024)
            if chunk:
                data += chunk
            elif data:
                break
        return data.decode('utf-8', errors='replace')

    def read_until(self, marker: str, timeout: float = 10.0) -> str:
        """Read until a specific marker is found"""
        if not self.ser:
            return ""
        data = b""
        start = time.time()
        while time.time() - start < timeout:
            chunk = self.ser.read(256)
            if chunk:
                data += chunk
                if marker.encode() in data:
                    break
        return data.decode('utf-8', errors='replace')

    def parse_networks(self, data: str) -> List[dict]:
        """Parse network list from response"""
        networks = []
        # Find all network entries: [STX]n<data>[ETX]
        pattern = r'\x02n([^\x03]+)\x03'
        matches = re.findall(pattern, data)
        for match in matches:
            parts = match.split('\x1d')
            if len(parts) >= 10:
                networks.append({
                    'index': int(parts[0]) if parts[0].isdigit() else 0,
                    'ssid': parts[1],
                    'bssid': parts[2],
                    'channel': int(parts[3]) if parts[3].isdigit() else 0,
                    'rssi': int(parts[4]) if parts[4].lstrip('-').isdigit() else 0,
                    'band': parts[5],
                    'clients': int(parts[6]) if parts[6].isdigit() else 0,
                    'security': parts[7],
                    'pmf': parts[8] == '1',
                    'hidden': parts[9] == '1'
                })
        return networks

    def parse_clients(self, data: str) -> List[dict]:
        """Parse client list from response"""
        clients = []
        # Find all client entries: [STX]c<data>[ETX]
        pattern = r'\x02c([^\x03]+)\x03'
        matches = re.findall(pattern, data)
        for match in matches:
            parts = match.split('\x1d')
            if len(parts) >= 3:
                clients.append({
                    'ap_index': int(parts[0]) if parts[0].isdigit() else -1,
                    'mac': parts[1],
                    'rssi': int(parts[2]) if parts[2].lstrip('-').isdigit() else 0
                })
        return clients

    def flash_firmware(self) -> bool:
        """Flash firmware using arduino-cli"""
        print(color("\n=== FLASHING FIRMWARE ===", Colors.HEADER))
        print(color("Put board in BURN MODE (hold BURN, press RESET, release BURN)", Colors.YELLOW))
        input("Press Enter when ready...")

        # Close serial if open
        if self.ser:
            self.ser.close()
            self.ser = None

        sketch_dir = os.path.join(self.firmware_dir, 'gattrose_ng')
        cmd = [
            'arduino-cli', 'upload',
            '-p', self.port,
            '--fqbn', 'realtek:AmebaD:Ai-Thinker_BW16',
            sketch_dir
        ]

        print(color(f"Running: {' '.join(cmd)}", Colors.CYAN))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr
            print(output)

            if "All images are sent successfully" in output:
                print(color("Flash SUCCESSFUL!", Colors.GREEN))
                time.sleep(1)
                return True
            elif "Upload Image done" in output:
                print(color("Flash likely successful (check board)", Colors.YELLOW))
                time.sleep(1)
                return True
            else:
                print(color("Flash may have FAILED", Colors.RED))
                return False
        except subprocess.TimeoutExpired:
            print(color("Flash timed out!", Colors.RED))
            return False
        except Exception as e:
            print(color(f"Flash error: {e}", Colors.RED))
            return False

    def compile_firmware(self) -> bool:
        """Compile firmware using arduino-cli"""
        print(color("\n=== COMPILING FIRMWARE ===", Colors.HEADER))

        sketch_dir = os.path.join(self.firmware_dir, 'gattrose_ng')
        cmd = [
            'arduino-cli', 'compile',
            '--fqbn', 'realtek:AmebaD:Ai-Thinker_BW16',
            sketch_dir
        ]

        print(color(f"Running: {' '.join(cmd)}", Colors.CYAN))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            output = result.stdout + result.stderr

            if result.returncode == 0:
                # Extract size info
                match = re.search(r'Sketch uses (\d+) bytes \((\d+)%\)', output)
                if match:
                    print(color(f"Compiled: {match.group(1)} bytes ({match.group(2)}%)", Colors.GREEN))
                else:
                    print(color("Compiled successfully!", Colors.GREEN))
                return True
            else:
                print(output)
                print(color("Compilation FAILED!", Colors.RED))
                return False
        except Exception as e:
            print(color(f"Compile error: {e}", Colors.RED))
            return False

    def cmd_scan(self, duration: int = 5000):
        """Scan for networks"""
        print(color(f"\nScanning for {duration}ms...", Colors.CYAN))
        self.send_cmd('s', str(duration))

        # Wait for scan to complete
        data = self.read_until('DONE:', timeout=duration/1000 + 5)

        # Parse result
        match = re.search(r'DONE:(\d+)', data)
        if match:
            count = int(match.group(1))
            print(color(f"Found {count} networks", Colors.GREEN))

            # Get network list
            self.send_cmd('g')
            time.sleep(1)
            data = self.read_response(timeout=5)
            self.networks = self.parse_networks(data)

            if not self.networks:
                # Try reading more
                data += self.read_response(timeout=3)
                self.networks = self.parse_networks(data)

    def cmd_list_networks(self, filter_str: str = ""):
        """List discovered networks"""
        if not self.networks:
            print(color("No networks. Run 'scan' first.", Colors.YELLOW))
            return

        print(color(f"\n{'Idx':<4} {'SSID':<30} {'BSSID':<18} {'CH':<4} {'RSSI':<6} {'Sec':<8} {'PMF':<4} {'Cli':<4}", Colors.HEADER))
        print("-" * 100)

        for net in self.networks:
            if filter_str and filter_str.lower() not in net['ssid'].lower():
                continue

            ssid = net['ssid'] if net['ssid'] else "<hidden>"
            pmf = color("YES", Colors.RED) if net['pmf'] else "no"
            cli = color(str(net['clients']), Colors.GREEN) if net['clients'] > 0 else "0"
            rssi_color = Colors.GREEN if net['rssi'] > -60 else Colors.YELLOW if net['rssi'] > -75 else Colors.RED

            print(f"{net['index']:<4} {ssid:<30} {net['bssid']:<18} {net['channel']:<4} {color(str(net['rssi']), rssi_color):<15} {net['security']:<8} {pmf:<13} {cli}")

    def cmd_monitor(self, enable: bool = True, duration: int = 10):
        """Enable/disable monitor mode for client detection"""
        if enable:
            print(color(f"\nMonitor mode ON - sniffing clients for {duration}s...", Colors.CYAN))
            self.send_cmd('m', '1')
            time.sleep(duration)

            # Get clients
            self.send_cmd('c')
            time.sleep(1)
            data = self.read_response(timeout=3)
            self.clients = self.parse_clients(data)

            print(color(f"Detected {len(self.clients)} clients", Colors.GREEN))
        else:
            print(color("\nMonitor mode OFF", Colors.CYAN))
            self.send_cmd('m', '0')
            self.read_response(timeout=1)

    def cmd_list_clients(self):
        """List detected clients"""
        if not self.clients:
            print(color("No clients. Run 'monitor' first.", Colors.YELLOW))
            return

        print(color(f"\n{'AP Idx':<8} {'Client MAC':<20} {'RSSI':<8} {'Network':<30}", Colors.HEADER))
        print("-" * 70)

        for cli in self.clients:
            ap_name = "<unknown>"
            for net in self.networks:
                if net['index'] == cli['ap_index']:
                    ap_name = net['ssid'] if net['ssid'] else "<hidden>"
                    break

            rssi_color = Colors.GREEN if cli['rssi'] > -60 else Colors.YELLOW if cli['rssi'] > -75 else Colors.RED
            print(f"{cli['ap_index']:<8} {cli['mac']:<20} {color(str(cli['rssi']), rssi_color):<17} {ap_name}")

    def cmd_deauth(self, target: str, reason: int = 2):
        """Start deauth attack"""
        if target.lower() == 'stop':
            print(color("\nStopping all deauth attacks...", Colors.YELLOW))
            self.send_cmd('d', 's')
        elif ':' in target:
            # MAC address - client attack
            print(color(f"\nDeauthing client {target}...", Colors.RED))
            self.send_cmd('k', f"{target}-{reason}")
        else:
            # Network index
            try:
                idx = int(target)
                net = next((n for n in self.networks if n['index'] == idx), None)
                if net and net['pmf']:
                    print(color(f"WARNING: Network has PMF enabled - deauth may not work!", Colors.YELLOW))
                print(color(f"\nDeauthing network {idx}...", Colors.RED))
                self.send_cmd('d', f"{idx}-{reason}")
            except ValueError:
                print(color(f"Invalid target: {target}", Colors.RED))
                return

        time.sleep(0.5)
        print(self.read_response(timeout=1))

    def cmd_led(self, args: str):
        """Control LED"""
        print(color(f"\nSetting LED: {args}", Colors.CYAN))
        self.send_cmd('r', args)
        time.sleep(0.3)
        print(self.read_response(timeout=1))

    def cmd_info(self):
        """Get device info"""
        self.send_cmd('i')
        time.sleep(0.5)
        data = self.read_response(timeout=2)

        # Parse info
        match = re.search(r'V:([^|]+)\|N:(\d+)\|C:(\d+)\|CH:(\d+)\|D:(\d+)', data)
        if match:
            print(color("\n=== Device Info ===", Colors.HEADER))
            print(f"  Version:  {color(match.group(1), Colors.GREEN)}")
            print(f"  Networks: {match.group(2)}")
            print(f"  Clients:  {match.group(3)}")
            print(f"  Channel:  {match.group(4)}")
            print(f"  Deauths:  {match.group(5)}")
        else:
            print(data)

    def cmd_find_network(self, name: str) -> Optional[dict]:
        """Find a network by name (partial match)"""
        for net in self.networks:
            if name.lower() in net['ssid'].lower():
                return net
        return None

    def interactive(self):
        """Interactive command loop"""
        print(color("\n=== Gattrose-NG Interactive CLI ===", Colors.HEADER))
        print("Type 'help' for commands\n")

        while True:
            try:
                cmd_line = input(color("gattrose> ", Colors.CYAN)).strip()
                if not cmd_line:
                    continue

                parts = cmd_line.split()
                cmd = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []

                if cmd in ['quit', 'exit', 'q']:
                    break
                elif cmd == 'help':
                    self.print_help()
                elif cmd == 'scan':
                    duration = int(args[0]) if args else 5000
                    self.cmd_scan(duration)
                elif cmd in ['list', 'networks', 'ls']:
                    filter_str = args[0] if args else ""
                    self.cmd_list_networks(filter_str)
                elif cmd == 'monitor':
                    duration = int(args[0]) if args else 10
                    self.cmd_monitor(True, duration)
                elif cmd in ['clients', 'cli']:
                    self.cmd_list_clients()
                elif cmd == 'deauth':
                    if not args:
                        print(color("Usage: deauth <index|mac|stop> [reason]", Colors.YELLOW))
                    else:
                        reason = int(args[1]) if len(args) > 1 else 2
                        self.cmd_deauth(args[0], reason)
                elif cmd == 'stop':
                    self.cmd_deauth('stop')
                elif cmd == 'led':
                    if not args:
                        print(color("Usage: led <r,g,b> or led <0-3>", Colors.YELLOW))
                    else:
                        self.cmd_led(args[0])
                elif cmd == 'info':
                    self.cmd_info()
                elif cmd == 'find':
                    if not args:
                        print(color("Usage: find <ssid>", Colors.YELLOW))
                    else:
                        net = self.cmd_find_network(' '.join(args))
                        if net:
                            print(color(f"\nFound: {net['ssid']} (index {net['index']})", Colors.GREEN))
                            print(f"  BSSID: {net['bssid']}")
                            print(f"  Channel: {net['channel']}, RSSI: {net['rssi']}")
                            print(f"  Security: {net['security']}, PMF: {net['pmf']}")
                            print(f"  Clients: {net['clients']}")
                        else:
                            print(color(f"Network '{args[0]}' not found", Colors.RED))
                elif cmd == 'attack':
                    if not args:
                        print(color("Usage: attack <ssid>", Colors.YELLOW))
                    else:
                        net = self.cmd_find_network(' '.join(args))
                        if net:
                            if net['pmf']:
                                print(color(f"WARNING: {net['ssid']} has PMF - attack may fail!", Colors.YELLOW))
                            confirm = input(f"Attack {net['ssid']} (index {net['index']})? [y/N] ")
                            if confirm.lower() == 'y':
                                self.cmd_deauth(str(net['index']))
                        else:
                            print(color(f"Network '{args[0]}' not found", Colors.RED))
                elif cmd == 'flash':
                    self.disconnect()
                    if self.compile_firmware():
                        if self.flash_firmware():
                            print(color("\nPress RESET on board, then press Enter...", Colors.YELLOW))
                            input()
                            self.connect()
                elif cmd == 'compile':
                    self.compile_firmware()
                elif cmd == 'raw':
                    if args:
                        self.send_cmd(args[0], ''.join(args[1:]) if len(args) > 1 else '')
                        time.sleep(0.5)
                        print(self.read_response(timeout=2))
                else:
                    print(color(f"Unknown command: {cmd}", Colors.RED))

            except KeyboardInterrupt:
                print("\n")
                continue
            except EOFError:
                break
            except Exception as e:
                print(color(f"Error: {e}", Colors.RED))

        print(color("\nGoodbye!", Colors.GREEN))

    def print_help(self):
        """Print help message"""
        print(color("\n=== Commands ===", Colors.HEADER))
        print(f"  {color('scan [ms]', Colors.CYAN):<25} Scan for networks (default 5000ms)")
        print(f"  {color('list [filter]', Colors.CYAN):<25} List networks (optional filter)")
        print(f"  {color('find <ssid>', Colors.CYAN):<25} Find network by name")
        print(f"  {color('monitor [sec]', Colors.CYAN):<25} Sniff clients (default 10s)")
        print(f"  {color('clients', Colors.CYAN):<25} List detected clients")
        print(f"  {color('deauth <idx|mac|stop>', Colors.CYAN):<25} Deauth network/client or stop")
        print(f"  {color('attack <ssid>', Colors.CYAN):<25} Find and attack network by name")
        print(f"  {color('stop', Colors.CYAN):<25} Stop all attacks")
        print(f"  {color('led <r,g,b|0-3>', Colors.CYAN):<25} Set LED color or effect")
        print(f"  {color('info', Colors.CYAN):<25} Device info")
        print(f"  {color('flash', Colors.CYAN):<25} Compile and flash firmware")
        print(f"  {color('compile', Colors.CYAN):<25} Compile firmware only")
        print(f"  {color('raw <cmd> [args]', Colors.CYAN):<25} Send raw command")
        print(f"  {color('quit', Colors.CYAN):<25} Exit")


def find_port() -> str:
    """Auto-detect BW16 port"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'USB' in port.device or 'ttyUSB' in port.device or 'ttyACM' in port.device:
            return port.device
    return '/dev/ttyUSB0'


def main():
    parser = argparse.ArgumentParser(description='Gattrose-NG CLI Tool')
    parser.add_argument('--port', '-p', default=None, help='Serial port (auto-detect if not specified)')
    parser.add_argument('--baud', '-b', type=int, default=115200, help='Baud rate')
    parser.add_argument('--flash', '-f', action='store_true', help='Flash firmware before starting')
    parser.add_argument('--compile', '-c', action='store_true', help='Compile firmware only')
    args = parser.parse_args()

    port = args.port or find_port()
    print(color(f"Using port: {port}", Colors.CYAN))

    cli = GattroseCLI(port=port, baud=args.baud)

    if args.compile:
        cli.compile_firmware()
        return

    if args.flash:
        if not cli.compile_firmware():
            return
        if not cli.flash_firmware():
            return
        print(color("\nPress RESET on board, then press Enter...", Colors.YELLOW))
        input()

    if cli.connect():
        # Wait for boot if just flashed
        if args.flash:
            print(color("Waiting for boot sequence...", Colors.CYAN))
            time.sleep(8)
            print(cli.read_response(timeout=2))

        try:
            cli.interactive()
        finally:
            cli.disconnect()


if __name__ == '__main__':
    main()
