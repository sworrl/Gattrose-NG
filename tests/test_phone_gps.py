#!/usr/bin/env python3
"""
Test Android Phone GPS via ADB
Quick utility to verify phone GPS is working
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.gps_service import get_gps_service


def check_adb():
    """Check if ADB can see the phone"""
    print("=" * 70)
    print("Android Phone GPS Test")
    print("=" * 70)
    print()

    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        print("[*] ADB Devices:")
        print(result.stdout)

        lines = result.stdout.strip().split('\n')[1:]
        devices = [line for line in lines if line.strip() and 'unauthorized' not in line.lower()]

        if not devices:
            print("[!] No authorized devices found")
            print()
            print("To enable USB debugging on your Android phone:")
            print("1. Go to Settings → About Phone")
            print("2. Tap 'Build Number' 7 times")
            print("3. Go to Settings → System → Developer Options")
            print("4. Enable 'USB Debugging'")
            print("5. Accept the authorization dialog on your phone")
            print()
            return False

        print(f"[+] Found {len(devices)} authorized device(s)")
        return True

    except Exception as e:
        print(f"[!] Error checking ADB: {e}")
        return False


def test_location():
    """Test reading location from phone"""
    print()
    print("[*] Testing location read via dumpsys...")

    try:
        result = subprocess.run(
            ['adb', 'shell', 'dumpsys', 'location'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"[!] Command failed with code {result.returncode}")
            return False

        output = result.stdout

        # Look for location data
        found_gps = False
        found_network = False

        for line in output.split('\n'):
            if 'gps:' in line.lower() or 'Location[gps' in line:
                found_gps = True
                print(f"[+] GPS Provider: {line.strip()}")
            elif 'network:' in line.lower() or 'Location[network' in line:
                found_network = True
                print(f"[+] Network Provider: {line.strip()}")

        if found_gps or found_network:
            print()
            print("[+] Phone has location data available!")
        else:
            print()
            print("[!] No location data found - make sure:")
            print("    - Location/GPS is enabled on the phone")
            print("    - Phone has a GPS fix (go outside if needed)")
            print("    - Location permissions are granted to system")

        return found_gps or found_network

    except Exception as e:
        print(f"[!] Error testing location: {e}")
        return False


def test_gps_service():
    """Test GPS service integration"""
    print()
    print("[*] Testing GPS Service integration...")

    try:
        gps = get_gps_service()
        gps.start()

        import time
        time.sleep(3)  # Give it time to update

        lat, lon, alt, acc, source = gps.get_location()

        if lat is not None and lon is not None:
            print(f"[+] GPS Service working!")
            print(f"    Latitude:  {lat:.8f}")
            print(f"    Longitude: {lon:.8f}")
            if alt:
                print(f"    Altitude:  {alt:.2f}m")
            if acc:
                print(f"    Accuracy:  ±{acc:.1f}m")
            print(f"    Source:    {source}")
        else:
            print("[!] GPS Service didn't get location yet")
            print(f"    Source: {source if source else 'None'}")

        gps.stop()

    except Exception as e:
        print(f"[!] Error testing GPS service: {e}")
        import traceback
        traceback.print_exc()


def main():
    if not check_adb():
        print()
        print("[i] Once USB debugging is enabled, run this script again")
        return 1

    if not test_location():
        print()
        print("[i] Fix location issues and try again")
        return 1

    test_gps_service()

    print()
    print("=" * 70)
    print("[+] All tests complete!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
