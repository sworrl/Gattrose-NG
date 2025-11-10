#!/usr/bin/env python3
"""
Comprehensive Gattrose-NG Functionality Test
Tests all major components and reports their status
"""

import sys
import os
import subprocess
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(test_name, passed, details=""):
    """Print test result"""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status:8} | {test_name:40} | {details}")

def test_orchestrator():
    """Test orchestrator service"""
    print_header("Orchestrator Service")

    # Check if orchestrator is running
    try:
        result = subprocess.run(['pgrep', '-f', 'orchestrator.py'],
                               capture_output=True, text=True)
        running = bool(result.stdout.strip())
        print_result("Orchestrator Process", running,
                    f"PID: {result.stdout.strip()}" if running else "Not running")
    except Exception as e:
        print_result("Orchestrator Process", False, str(e))
        return False

    # Check status file
    try:
        with open('/tmp/gattrose-status.json', 'r') as f:
            status = json.load(f)

        print_result("Status File", True, "Valid JSON")
        print_result("Orchestrator Running",
                    status.get('orchestrator', {}).get('running', False))

        # Check services
        services = status.get('services', {})
        for svc_name, svc_data in services.items():
            svc_status = svc_data.get('status', 'unknown')
            svc_running = svc_data.get('running', False)
            print_result(f"Service: {svc_data.get('name', svc_name)}",
                        svc_running, svc_status)

        return True
    except FileNotFoundError:
        print_result("Status File", False, "File not found")
        return False
    except Exception as e:
        print_result("Status File", False, str(e))
        return False

def test_database():
    """Test database connectivity and data"""
    print_header("Database")

    try:
        from src.database.models import get_session, Network, Client
        from src.database.models import CurrentScanNetwork, CurrentScanClient

        print_result("Database Import", True)

        session = get_session()

        # Count networks
        network_count = session.query(Network).count()
        print_result("Historical Networks", True, f"{network_count} networks")

        # Count clients
        client_count = session.query(Client).count()
        print_result("Historical Clients", True, f"{client_count} clients")

        # Count current scan data
        current_networks = session.query(CurrentScanNetwork).count()
        print_result("Live Scan Networks", current_networks > 0,
                    f"{current_networks} networks")

        current_clients = session.query(CurrentScanClient).count()
        print_result("Live Scan Clients", current_clients > 0,
                    f"{current_clients} clients")

        session.close()
        return True

    except Exception as e:
        print_result("Database Connection", False, str(e))
        return False

def test_gps():
    """Test GPS service"""
    print_header("GPS Service")

    try:
        from src.services.gps_service import get_gps_service

        gps = get_gps_service()
        print_result("GPS Service Import", True)

        lat, lon, alt, acc, source = gps.get_location()

        has_fix = lat is not None
        print_result("GPS Fix", has_fix,
                    f"{lat:.6f}, {lon:.6f} ({source})" if has_fix else "No fix")

        if has_fix:
            print_result("GPS Accuracy", True, f"{acc:.2f}m")

        return True

    except Exception as e:
        print_result("GPS Service", False, str(e))
        return False

def test_scanner():
    """Test WiFi scanner"""
    print_header("WiFi Scanner")

    # Check monitor interface
    try:
        result = subprocess.run(['iw', 'dev'], capture_output=True, text=True)
        has_monitor = 'type monitor' in result.stdout

        if has_monitor:
            # Extract monitor interface name
            lines = result.stdout.split('\n')
            monitor_iface = None
            for i, line in enumerate(lines):
                if 'type monitor' in line:
                    # Interface name is a few lines above
                    for j in range(i-1, max(0, i-5), -1):
                        if 'Interface' in lines[j]:
                            monitor_iface = lines[j].split()[-1]
                            break

            print_result("Monitor Mode Interface", True, monitor_iface or "Found")
        else:
            print_result("Monitor Mode Interface", False, "No monitor interface")

    except Exception as e:
        print_result("Monitor Mode Check", False, str(e))

    # Check airodump-ng process
    try:
        result = subprocess.run(['pgrep', '-f', 'airodump-ng'],
                               capture_output=True, text=True)
        airodump_running = bool(result.stdout.strip())
        print_result("airodump-ng Process", airodump_running,
                    f"PID: {result.stdout.strip()}" if airodump_running else "Not running")
    except Exception as e:
        print_result("airodump-ng Check", False, str(e))

    # Check CSV output
    csv_files = list(Path('/tmp/gattrose-captures').glob('*.csv'))
    if csv_files:
        latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)

        with open(latest_csv, 'r') as f:
            lines = f.readlines()

        # Check if CSV has more than just headers (headers are first 5 lines usually)
        has_data = len(lines) > 5
        print_result("Scanner CSV Output", True,
                    f"{len(lines)} lines, {'HAS DATA' if has_data else 'HEADERS ONLY'}")

        if not has_data:
            print()
            print("  ⚠️  WARNING: Scanner is running but not capturing networks!")
            print("  This usually means the WiFi card doesn't fully support monitor mode.")
            print("  Intel WiFi cards (iwlwifi driver) often have this limitation.")
            print("  Solution: Use external USB WiFi adapter (Alfa AWUS036ACH, etc.)")
    else:
        print_result("Scanner CSV Output", False, "No CSV files found")

def test_api():
    """Test local API"""
    print_header("Local API")

    try:
        import requests

        # Check if API is running
        try:
            response = requests.get('http://127.0.0.1:5555/api/status', timeout=2)
            api_running = response.status_code == 200
            print_result("API Server", api_running,
                        f"Status: {response.status_code}")

            if api_running:
                data = response.json()
                print_result("API Response", True, "Valid JSON")

        except requests.exceptions.ConnectionError:
            print_result("API Server", False, "Not responding on port 5555")
        except Exception as e:
            print_result("API Server", False, str(e))

    except ImportError:
        print_result("API Test", False, "requests module not installed")

def test_gui():
    """Test GUI process"""
    print_header("GUI Application")

    try:
        result = subprocess.run(['pgrep', '-f', 'src/main.py'],
                               capture_output=True, text=True)
        gui_running = bool(result.stdout.strip())
        print_result("GUI Process", gui_running,
                    f"PID: {result.stdout.strip()}" if gui_running else "Not running")
    except Exception as e:
        print_result("GUI Check", False, str(e))

def main():
    """Run all tests"""
    print_header("GATTROSE-NG COMPREHENSIVE FUNCTIONALITY TEST")
    print(f"Test Time: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}")

    # Run all tests
    test_orchestrator()
    test_database()
    test_gps()
    test_scanner()
    test_api()
    test_gui()

    print_header("TEST COMPLETE")
    print()

if __name__ == "__main__":
    main()
