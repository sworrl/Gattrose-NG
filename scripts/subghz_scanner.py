#!/usr/bin/env python3
"""
SubGHz Signal Scanner via Gattrose-NG Local API
Scans common SubGHz frequencies for signals
"""

import requests
import json
import time
import sys
from datetime import datetime

API_BASE = "http://127.0.0.1:5555/api"

# Common SubGHz frequencies (in Hz)
FREQUENCIES = {
    "315 MHz (US keyfobs, garage doors)": 315000000,
    "433.92 MHz (ISM band, most common)": 433920000,
    "868 MHz (EU ISM band)": 868000000,
    "915 MHz (US ISM band)": 915000000,
}

def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}")

def print_status(text):
    """Print status message"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

def check_api_status():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_BASE}/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_status("✓ API is running")
                status = data.get('data', {})
                print_status(f"  Scanner: {'Active' if status.get('scanner_active') else 'Inactive'}")
                print_status(f"  Flipper: {'Connected' if status.get('flipper_connected') else 'Disconnected'}")
                print_status(f"  Networks: {status.get('ap_count', 0)}")
                print_status(f"  Clients: {status.get('client_count', 0)}")
                return True
    except Exception as e:
        print_status(f"✗ API not accessible: {e}")
        return False
    return False

def connect_flipper():
    """Connect to Flipper Zero"""
    print_status("Connecting to Flipper Zero...")
    try:
        response = requests.post(f"{API_BASE}/flipper/connect",
                                json={},
                                timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                device = data.get('device', {})
                print_status("✓ Connected to Flipper Zero")
                print_status(f"  Name: {device.get('name')}")
                print_status(f"  Model: {device.get('model')}")
                print_status(f"  UID: {device.get('uid')}")
                print_status(f"  Firmware: {device.get('firmware')}")
                print_status(f"  Port: {device.get('port')}")
                return True
            else:
                print_status(f"✗ Failed to connect: {data.get('error')}")
        else:
            print_status(f"✗ API error: {response.status_code}")
    except Exception as e:
        print_status(f"✗ Connection error: {e}")
    return False

def scan_frequency(frequency, freq_name, duration=15):
    """Scan a specific frequency for signals"""
    print_status(f"Scanning {freq_name}...")
    print_status(f"  Frequency: {frequency} Hz")
    print_status(f"  Duration: {duration} seconds")

    # Start reception
    try:
        # Send raw command to start SubGHz reception
        cmd = f"subghz rx {frequency} 0"
        response = requests.post(f"{API_BASE}/flipper/command",
                                json={"command": cmd},
                                timeout=5)

        if response.status_code != 200:
            print_status(f"✗ Failed to start RX: {response.status_code}")
            return None

        data = response.json()
        if not data.get('success'):
            print_status(f"✗ RX command failed: {data.get('error')}")
            return None

        print_status(f"  Listening...")

        # Listen for specified duration
        for i in range(duration):
            time.sleep(1)
            remaining = duration - i - 1
            if remaining > 0 and remaining % 5 == 0:
                print_status(f"  {remaining} seconds remaining...")

        # Stop reception by sending empty command
        requests.post(f"{API_BASE}/flipper/command",
                     json={"command": ""},
                     timeout=5)

        print_status(f"  ✓ Scan complete")

        # Get device info to see if anything was captured
        response = requests.get(f"{API_BASE}/flipper/info", timeout=5)
        if response.status_code == 200:
            return response.json()

    except Exception as e:
        print_status(f"✗ Error during scan: {e}")
        # Try to stop reception
        try:
            requests.post(f"{API_BASE}/flipper/command",
                         json={"command": ""},
                         timeout=2)
        except:
            pass

    return None

def scan_all_frequencies():
    """Scan all common SubGHz frequencies"""
    print_header("SUBGHZ FREQUENCY SCAN")

    results = {}

    for freq_name, frequency in FREQUENCIES.items():
        result = scan_frequency(frequency, freq_name, duration=15)
        results[freq_name] = result

        # Brief pause between frequencies
        time.sleep(2)

    return results

def generate_report(results):
    """Generate scan report"""
    print_header("SCAN RESULTS REPORT")

    print_status(f"Scan completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_status(f"Total frequencies scanned: {len(FREQUENCIES)}")

    print("\n" + "="*80)
    print("FREQUENCY BREAKDOWN:")
    print("="*80)

    for freq_name in FREQUENCIES.keys():
        print(f"\n{freq_name}")
        result = results.get(freq_name)
        if result and result.get('success'):
            print("  Status: ✓ Scan completed successfully")
            # Note: Actual signal detection would require parsing Flipper's response
            # The current API returns device info, not capture data
            print("  Note: Signal capture data requires additional parsing")
        else:
            print("  Status: ✗ Scan failed or no data")

    print("\n" + "="*80)
    print("NOTES:")
    print("="*80)
    print("• Flipper Zero SubGHz reception captures signals in real-time")
    print("• Detected signals are typically saved to SD card")
    print("• To analyze captures, check /ext/subghz/ directory on Flipper")
    print("• Common signals: garage doors, car keys, weather stations, sensors")
    print("• For better results, scan near active devices (e.g., press garage remote)")
    print("="*80)

def main():
    """Main execution"""
    print_header("GATTROSE-NG SUBGHZ SIGNAL SCANNER")
    print_status("Starting SubGHz signal scanning via Local API")

    # Check API
    if not check_api_status():
        print_status("✗ Local API is not running")
        print_status("  Start Gattrose-NG first, then run this script")
        sys.exit(1)

    # Connect to Flipper
    if not connect_flipper():
        print_status("✗ Could not connect to Flipper Zero")
        print_status("  Make sure Flipper is plugged in via USB")
        sys.exit(1)

    # LED indicator - set to blue for scanning
    print_status("Setting LED to blue (scanning mode)...")
    try:
        requests.post(f"{API_BASE}/flipper/led",
                     json={"color": "blue"},
                     timeout=5)
    except:
        pass

    # Perform scan
    results = scan_all_frequencies()

    # LED indicator - set to green when done
    print_status("Setting LED to green (scan complete)...")
    try:
        requests.post(f"{API_BASE}/flipper/led",
                     json={"color": "green"},
                     timeout=5)
        time.sleep(2)
        requests.post(f"{API_BASE}/flipper/led",
                     json={"color": "off"},
                     timeout=5)
    except:
        pass

    # Generate report
    generate_report(results)

    print_status("\n✓ SubGHz scanning complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_status("\n\n✗ Scan interrupted by user")
        # Turn off LED
        try:
            requests.post(f"{API_BASE}/flipper/led",
                         json={"color": "off"},
                         timeout=2)
        except:
            pass
        sys.exit(1)
