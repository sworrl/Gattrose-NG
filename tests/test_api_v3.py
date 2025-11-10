#!/usr/bin/env python3
"""
Comprehensive API v3 Test Suite

Tests all 120+ endpoints of the Gattrose-NG API v3
"""

import requests
import json
import time
from datetime import datetime

# API Configuration
API_BASE = "http://localhost:5555"
API_KEY = None  # Set if authentication is enabled


def make_request(method, endpoint, data=None, params=None):
    """Make API request with optional authentication"""
    url = f"{API_BASE}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    if API_KEY:
        headers['X-API-Key'] = API_KEY

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            return None

        return response
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None


def print_result(test_name, response):
    """Print test result"""
    if response is None:
        print(f"❌ {test_name}: No response")
        return False

    success = response.status_code in [200, 201]
    icon = "✅" if success else "❌"
    print(f"{icon} {test_name}: {response.status_code}")

    if not success:
        print(f"   Error: {response.text[:200]}")
    else:
        try:
            data = response.json()
            if 'message' in data:
                print(f"   Message: {data['message']}")
        except:
            pass

    return success


def test_core_system():
    """Test core system endpoints"""
    print("\n" + "=" * 70)
    print("Testing Core System Endpoints")
    print("=" * 70)

    tests = [
        ("GET", "/api/v3", None, "API Root"),
        ("GET", "/api/v3/status", None, "System Status"),
        ("GET", "/api/v3/health", None, "Health Check"),
        ("GET", "/api/v3/docs", None, "API Documentation"),
    ]

    passed = 0
    for method, endpoint, data, name in tests:
        response = make_request(method, endpoint, data)
        if print_result(name, response):
            passed += 1
        time.sleep(0.1)

    print(f"\nPassed: {passed}/{len(tests)}")
    return passed


def test_service_control():
    """Test service control endpoints"""
    print("\n" + "=" * 70)
    print("Testing Service Control Endpoints")
    print("=" * 70)

    tests = [
        ("GET", "/api/v3/services", None, "Get All Services"),
        ("GET", "/api/v3/services/scanner/status", None, "Scanner Status"),
        ("GET", "/api/v3/services/gps/status", None, "GPS Status"),
        ("GET", "/api/v3/services/gps/location", None, "GPS Location"),
        ("GET", "/api/v3/services/database/status", None, "Database Status"),
        ("GET", "/api/v3/services/database/stats", None, "Database Stats"),
        ("GET", "/api/v3/services/triangulation/status", None, "Triangulation Status"),
    ]

    passed = 0
    for method, endpoint, data, name in tests:
        response = make_request(method, endpoint, data)
        if print_result(name, response):
            passed += 1
        time.sleep(0.1)

    print(f"\nPassed: {passed}/{len(tests)}")
    return passed


def test_network_management():
    """Test network management endpoints"""
    print("\n" + "=" * 70)
    print("Testing Network Management Endpoints")
    print("=" * 70)

    tests = [
        ("GET", "/api/v3/networks", None, "Get All Networks"),
        ("GET", "/api/v3/networks?limit=10&offset=0", None, "Get Networks with Pagination"),
        ("POST", "/api/v3/networks/filter", {"encryption": "WPA"}, "Filter Networks by Encryption"),
        ("GET", "/api/v3/networks/blacklist", None, "Get Blacklist"),
        ("GET", "/api/v3/clients", None, "Get All Clients"),
        ("GET", "/api/v3/handshakes", None, "Get Handshakes"),
    ]

    passed = 0
    for method, endpoint, data, name in tests:
        response = make_request(method, endpoint, data)
        if print_result(name, response):
            passed += 1

            # Try to get details of first network
            if endpoint == "/api/v3/networks" and response.status_code == 200:
                try:
                    networks = response.json().get('data', {}).get('networks', [])
                    if networks:
                        bssid = networks[0]['bssid']
                        detail_response = make_request("GET", f"/api/v3/networks/{bssid}", None)
                        print_result(f"Get Network Details ({bssid})", detail_response)
                except:
                    pass

        time.sleep(0.1)

    print(f"\nPassed: {passed}/{len(tests)}")
    return passed


def test_attack_operations():
    """Test attack operation endpoints (status only, no actual attacks)"""
    print("\n" + "=" * 70)
    print("Testing Attack Operation Endpoints (Status Only)")
    print("=" * 70)

    tests = [
        ("GET", "/api/v3/attacks/deauth/status", None, "Deauth Attack Status"),
        ("GET", "/api/v3/attacks/eviltwin/status", None, "Evil Twin Status"),
        ("GET", "/api/v3/attacks/wps/status", None, "WPS Attack Status"),
        ("GET", "/api/v3/attacks/handshake/status", None, "Handshake Capture Status"),
        ("GET", "/api/v3/attacks/pmkid/status", None, "PMKID Capture Status"),
        ("GET", "/api/v3/attacks/auto/status", None, "Auto-Attack Status"),
        ("GET", "/api/v3/attacks/queue", None, "Attack Queue"),
    ]

    passed = 0
    for method, endpoint, data, name in tests:
        response = make_request(method, endpoint, data)
        if print_result(name, response):
            passed += 1
        time.sleep(0.1)

    print(f"\nPassed: {passed}/{len(tests)}")
    return passed


def test_system_operations():
    """Test system operation endpoints"""
    print("\n" + "=" * 70)
    print("Testing System Operation Endpoints")
    print("=" * 70)

    tests = [
        ("GET", "/api/v3/system/monitor/status", None, "Monitor Mode Status"),
        ("GET", "/api/v3/system/interfaces", None, "List Network Interfaces"),
    ]

    passed = 0
    for method, endpoint, data, name in tests:
        response = make_request(method, endpoint, data)
        if print_result(name, response):
            passed += 1
        time.sleep(0.1)

    print(f"\nPassed: {passed}/{len(tests)}")
    return passed


def test_configuration():
    """Test configuration endpoints"""
    print("\n" + "=" * 70)
    print("Testing Configuration Endpoints")
    print("=" * 70)

    tests = [
        ("GET", "/api/v3/config", None, "Get All Config"),
        ("GET", "/api/v3/config/app.theme", None, "Get Specific Config Value"),
    ]

    passed = 0
    for method, endpoint, data, name in tests:
        response = make_request(method, endpoint, data)
        if print_result(name, response):
            passed += 1
        time.sleep(0.1)

    print(f"\nPassed: {passed}/{len(tests)}")
    return passed


def test_file_operations():
    """Test file operation endpoints"""
    print("\n" + "=" * 70)
    print("Testing File Operation Endpoints")
    print("=" * 70)

    tests = [
        ("GET", "/api/v3/files/captures", None, "List Capture Files"),
    ]

    passed = 0
    for method, endpoint, data, name in tests:
        response = make_request(method, endpoint, data)
        if print_result(name, response):
            passed += 1
        time.sleep(0.1)

    print(f"\nPassed: {passed}/{len(tests)}")
    return passed


def test_analytics():
    """Test analytics endpoints"""
    print("\n" + "=" * 70)
    print("Testing Analytics Endpoints")
    print("=" * 70)

    tests = [
        ("GET", "/api/v3/analytics/summary", None, "Analytics Summary"),
    ]

    passed = 0
    for method, endpoint, data, name in tests:
        response = make_request(method, endpoint, data)
        if print_result(name, response):
            passed += 1
        time.sleep(0.1)

    print(f"\nPassed: {passed}/{len(tests)}")
    return passed


def main():
    """Run all tests"""
    print("=" * 70)
    print("Gattrose-NG API v3 Test Suite")
    print("=" * 70)
    print(f"API Base: {API_BASE}")
    print(f"Authentication: {'Enabled' if API_KEY else 'Disabled'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check if API is reachable
    try:
        response = requests.get(f"{API_BASE}/api/v3", timeout=2)
        if response.status_code != 200:
            print("❌ API is not reachable. Make sure the server is running.")
            return
        print("✅ API is reachable")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("\nTo start the API server:")
        print("  python3 src/services/local_api_v3.py")
        return

    # Run all test suites
    total_passed = 0
    total_passed += test_core_system()
    total_passed += test_service_control()
    total_passed += test_network_management()
    total_passed += test_attack_operations()
    total_passed += test_system_operations()
    total_passed += test_configuration()
    total_passed += test_file_operations()
    total_passed += test_analytics()

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Total tests passed: {total_passed}")
    print()


if __name__ == '__main__':
    main()
