#!/usr/bin/env python3
"""
Test script to detect and communicate with Flipper Zero
"""

import serial
import time

def probe_flipper(port='/dev/ttyACM0', baud=115200):
    """Probe Flipper Zero device"""
    try:
        # Open serial connection
        print(f"[*] Opening serial connection to {port}...")
        ser = serial.Serial(port, baud, timeout=2)
        time.sleep(0.5)  # Wait for connection to stabilize

        # Flush any existing data
        ser.flushInput()
        ser.flushOutput()

        print(f"[+] Connected to {port} at {baud} baud")
        print(f"[i] Serial settings: {ser}")
        print()

        # Send device_info command
        print("[*] Sending 'device_info' command...")
        ser.write(b"device_info\r\n")
        time.sleep(0.5)

        # Read response
        response = []
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                response.append(line)
                print(f"    {line}")

        if not response:
            print("[!] No response received")

            # Try sending help command
            print()
            print("[*] Trying 'help' command...")
            ser.write(b"help\r\n")
            time.sleep(0.5)

            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"    {line}")

        print()
        print("[*] Closing connection...")
        ser.close()
        print("[+] Test complete!")

        return True

    except serial.SerialException as e:
        print(f"[!] Serial error: {e}")
        return False
    except Exception as e:
        print(f"[!] Error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Flipper Zero Detection & Communication Test")
    print("=" * 60)
    print()

    probe_flipper()
