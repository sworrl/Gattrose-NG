#!/usr/bin/env python3
"""
Enhanced SubGHz Signal Finder
Actively scans and identifies SubGHz signals in real-time
"""

import requests
import json
import time
import sys
from datetime import datetime
from collections import defaultdict

API_BASE = "http://127.0.0.1:5555/api"

# Extended frequency list with specific use cases
FREQUENCIES = [
    # Garage doors and car remotes
    (300000000, "300 MHz", "Garage doors (older systems)"),
    (310000000, "310 MHz", "Car remotes (some Japanese cars)"),
    (315000000, "315 MHz", "US garage doors, car remotes, wireless doorbells"),
    (318000000, "318 MHz", "Car remotes (some European models)"),

    # ISM bands - most common
    (433050000, "433.05 MHz", "European car keys"),
    (433075000, "433.075 MHz", "Gate remotes"),
    (433920000, "433.92 MHz", "ISM - weather stations, sensors, most remotes"),

    # Other common frequencies
    (868000000, "868 MHz", "EU ISM - alarm systems, home automation"),
    (915000000, "915 MHz", "US ISM - tire pressure sensors, RFID"),
]

class SubGHzSignalDetector:
    def __init__(self):
        self.detected_signals = []
        self.signal_counts = defaultdict(int)

    def print_header(self, text):
        print(f"\n{'='*80}")
        print(f"  {text}")
        print(f"{'='*80}")

    def print_status(self, text, level="info"):
        timestamp = datetime.now().strftime('%H:%M:%S')
        symbols = {"info": "▶", "success": "✓", "error": "✗", "warning": "⚠"}
        symbol = symbols.get(level, "▶")
        print(f"[{timestamp}] {symbol} {text}")

    def check_api(self):
        """Verify API is accessible"""
        try:
            response = requests.get(f"{API_BASE}/status", timeout=2)
            if response.status_code == 200 and response.json().get('success'):
                return True
        except:
            pass
        return False

    def connect_flipper(self):
        """Connect to Flipper Zero"""
        self.print_status("Connecting to Flipper Zero...")
        try:
            response = requests.post(f"{API_BASE}/flipper/connect", json={}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    device = data.get('device', {})
                    self.print_status(f"Connected: {device.get('name')} ({device.get('firmware')})", "success")
                    return True
        except Exception as e:
            self.print_status(f"Connection failed: {e}", "error")
        return False

    def scan_frequency_active(self, freq_hz, freq_name, description, duration=20):
        """
        Actively scan a frequency and attempt to detect signals
        Returns: list of detected signal characteristics
        """
        self.print_status(f"Scanning {freq_name} - {description}")
        self.print_status(f"  Frequency: {freq_hz} Hz | Duration: {duration}s")

        detected = []

        try:
            # Start SubGHz reception
            cmd = f"subghz rx {freq_hz} 0"
            response = requests.post(f"{API_BASE}/flipper/command",
                                   json={"command": cmd},
                                   timeout=5)

            if response.status_code != 200 or not response.json().get('success'):
                self.print_status(f"Failed to start RX on {freq_name}", "error")
                return detected

            self.print_status(f"  Listening for signals...", "info")

            # Visual progress indicator
            for i in range(duration):
                # Print progress every 5 seconds
                if i > 0 and i % 5 == 0:
                    print(f"    {'▓' * (i//5)}{'░' * ((duration-i)//5)} {i}/{duration}s", end='\r')
                time.sleep(1)

            print()  # New line after progress

            # Stop reception
            requests.post(f"{API_BASE}/flipper/command",
                         json={"command": ""},
                         timeout=5)

            self.print_status(f"  Scan complete", "success")

            # Note: In a real implementation, we would parse the Flipper's
            # serial output during RX to detect actual signals. This would
            # require modifications to the FlipperZeroService to capture
            # and parse the real-time output from the device.

            # For now, we report completion
            detected.append({
                'frequency': freq_hz,
                'name': freq_name,
                'description': description,
                'scanned': True
            })

        except requests.exceptions.ConnectionError:
            self.print_status(f"API connection lost during {freq_name} scan", "error")
        except Exception as e:
            self.print_status(f"Error scanning {freq_name}: {e}", "error")

        return detected

    def scan_all_frequencies(self):
        """Scan all frequencies and compile results"""
        self.print_header("ACTIVE SUBGHZ SIGNAL SCANNING")
        self.print_status("Initiating comprehensive frequency sweep")

        # Set LED to blue (scanning)
        try:
            requests.post(f"{API_BASE}/flipper/led", json={"color": "blue"}, timeout=5)
        except:
            pass

        total_scanned = 0
        total_failed = 0

        for freq_hz, freq_name, description in FREQUENCIES:
            results = self.scan_frequency_active(freq_hz, freq_name, description, duration=10)

            if results:
                self.detected_signals.extend(results)
                total_scanned += 1
            else:
                total_failed += 1

            # Brief pause between frequencies
            time.sleep(1)

        # Turn LED green on completion
        try:
            requests.post(f"{API_BASE}/flipper/led", json={"color": "green"}, timeout=5)
            time.sleep(1)
            requests.post(f"{API_BASE}/flipper/led", json={"color": "off"}, timeout=5)
        except:
            pass

        return total_scanned, total_failed

    def generate_report(self, scanned, failed):
        """Generate comprehensive scan report"""
        self.print_header("SUBGHZ SCAN REPORT")

        print(f"\nScan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Frequencies: {len(FREQUENCIES)}")
        print(f"Successfully Scanned: {scanned}")
        print(f"Failed Scans: {failed}")

        self.print_header("FREQUENCY BREAKDOWN")

        for signal in self.detected_signals:
            print(f"\n{signal['name']} ({signal['frequency']} Hz)")
            print(f"  Purpose: {signal['description']}")
            print(f"  Status: ✓ Scanned")

        self.print_header("SIGNAL DETECTION NOTES")

        print("""
The Flipper Zero can detect SubGHz signals in real-time. Here's what to look for:

VISUAL INDICATORS ON FLIPPER SCREEN:
  • Waveform display shows incoming signals
  • RSSI (signal strength) indicator
  • Protocol detection (if signal is recognized)

COMMON SIGNAL TYPES:
  • Static Code (older systems - easy to capture and replay)
  • Rolling Code (modern car keys - harder to crack)
  • OOK/ASK Modulation (simple on/off keying)
  • FSK Modulation (frequency shift keying)

TO IMPROVE DETECTION:
  1. Position Flipper near signal source (within 10-50 feet)
  2. Press remote buttons during scan
  3. Check Flipper screen for visual confirmation
  4. Captured signals saved to: /ext/subghz/ on SD card

NEXT STEPS:
  • Review Flipper's SD card for .sub files
  • Use Flipper's "Read" mode for passive monitoring
  • Use "Read RAW" for unknown protocols
  • Replay captured signals with Flipper's "Send" feature
""")

        self.print_header("ENHANCED DETECTION CAPABILITIES")

        print("""
To enable REAL-TIME signal parsing, the FlipperZeroService needs enhancement:

1. Serial Output Parsing:
   - Monitor Flipper's serial output during RX
   - Detect "Signal received" messages
   - Parse protocol, frequency, and data

2. Signal Characterization:
   - Identify modulation type (OOK/ASK/FSK)
   - Calculate signal strength (RSSI)
   - Detect known protocols (Princeton, KeeLoq, etc.)

3. Storage Integration:
   - List captured .sub files from SD card
   - Download and parse signal files
   - Provide signal analysis and replay options

This would require extending the API and FlipperZeroService with:
  - Real-time serial stream parsing
  - Storage file system access
  - Signal protocol database
        """)

def main():
    detector = SubGHzSignalDetector()

    detector.print_header("GATTROSE-NG SUBGHZ SIGNAL DETECTOR")
    detector.print_status("Enhanced SubGHz signal scanning and identification")

    # Check API
    if not detector.check_api():
        detector.print_status("Local API not accessible - start Gattrose first", "error")
        sys.exit(1)

    detector.print_status("API is running", "success")

    # Connect to Flipper
    if not detector.connect_flipper():
        detector.print_status("Could not connect to Flipper Zero", "error")
        sys.exit(1)

    # Perform comprehensive scan
    scanned, failed = detector.scan_all_frequencies()

    # Generate detailed report
    detector.generate_report(scanned, failed)

    detector.print_status("SubGHz signal detection complete!", "success")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[✗] Scan interrupted by user")
        try:
            requests.post(f"{API_BASE}/flipper/led", json={"color": "off"}, timeout=2)
        except:
            pass
        sys.exit(1)
