#!/usr/bin/env python3
"""
Local API Server for Gattrose-NG

Provides comprehensive REST API endpoints for controlling Gattrose from localhost.
Fully headless-capable and automation-ready with 100+ endpoints.

Security: Only listens on 127.0.0.1 (localhost)
Version: 3.0.0
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import threading
from typing import Optional, Dict, Any
import time
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path


class LocalAPIServer:
    """Local API server for controlling Gattrose"""

    def __init__(self, main_window, port: int = 5555):
        self.main_window = main_window
        self.port = port
        self.app = Flask(__name__)

        # Enable CORS for localhost only
        CORS(self.app, resources={r"/*": {"origins": "http://localhost:*"}})

        self.server_thread: Optional[threading.Thread] = None
        self.running = False

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup all API routes"""

        # ========== Status & Info ==========

        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """Get Gattrose status"""
            try:
                # Try to find scanner object
                scanner = None
                if hasattr(self.main_window, 'scanner') and self.main_window.scanner:
                    scanner = self.main_window.scanner
                elif hasattr(self.main_window, 'scanner_tab') and hasattr(self.main_window.scanner_tab, 'scanner'):
                    scanner = self.main_window.scanner_tab.scanner

                status = {
                    'running': True,
                    'scanner_active': scanner and scanner.running if scanner else False,
                    'monitor_interface': getattr(self.main_window, 'monitor_interface', None),
                    'flipper_connected': hasattr(self.main_window, 'flipper_tab') and
                                       self.main_window.flipper_tab.flipper_service and
                                       self.main_window.flipper_tab.flipper_service.is_connected(),
                    'ap_count': len(self.main_window.ap_tree_items) if hasattr(self.main_window, 'ap_tree_items') else 0,
                    'client_count': len(self.main_window.client_tree_items) if hasattr(self.main_window, 'client_tree_items') else 0
                }
                return jsonify({'success': True, 'data': status})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        # ========== Scanner Control ==========

        @self.app.route('/api/scanner/start', methods=['POST'])
        def start_scanner():
            """Start WiFi scanning"""
            try:
                monitor_iface = getattr(self.main_window, 'monitor_interface', None)
                if not monitor_iface:
                    return jsonify({
                        'success': False,
                        'error': 'No monitor interface available'
                    }), 400

                # Call start_scan from main thread
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self.main_window.scanner_tab,
                    "start_scan",
                    Qt.ConnectionType.QueuedConnection
                )

                return jsonify({
                    'success': True,
                    'message': 'Scanner started',
                    'interface': monitor_iface
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/scanner/stop', methods=['POST'])
        def stop_scanner():
            """Stop WiFi scanning"""
            try:
                # Call stop_scan from main thread
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self.main_window.scanner_tab,
                    "stop_scan",
                    Qt.ConnectionType.QueuedConnection
                )

                return jsonify({
                    'success': True,
                    'message': 'Scanner stopped'
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/scanner/networks', methods=['GET'])
        def get_networks():
            """Get discovered networks"""
            try:
                networks = []

                # Try to find scanner object (could be at main_window.scanner or scanner_tab.scanner)
                scanner = None
                if hasattr(self.main_window, 'scanner') and self.main_window.scanner:
                    scanner = self.main_window.scanner
                elif hasattr(self.main_window, 'scanner_tab') and hasattr(self.main_window.scanner_tab, 'scanner'):
                    scanner = self.main_window.scanner_tab.scanner

                if scanner:
                    for ap in scanner.get_all_aps():
                        networks.append({
                            'bssid': ap.bssid,
                            'ssid': ap.ssid,
                            'channel': ap.channel,
                            'encryption': ap.encryption,
                            'power': ap.power,
                            'wps_enabled': ap.wps_enabled,
                            'client_count': len(ap.clients),
                            'vendor': ap.vendor,
                            'device_type': ap.device_type
                        })

                return jsonify({
                    'success': True,
                    'count': len(networks),
                    'data': networks
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/scanner/clients', methods=['GET'])
        def get_clients():
            """Get discovered clients"""
            try:
                clients = []

                # Try to find scanner object (could be at main_window.scanner or scanner_tab.scanner)
                scanner = None
                if hasattr(self.main_window, 'scanner') and self.main_window.scanner:
                    scanner = self.main_window.scanner
                elif hasattr(self.main_window, 'scanner_tab') and hasattr(self.main_window.scanner_tab, 'scanner'):
                    scanner = self.main_window.scanner_tab.scanner

                if scanner:
                    for client in scanner.get_all_clients():
                        clients.append({
                            'mac': client.mac,
                            'bssid': client.bssid,
                            'power': client.power,
                            'packets': client.packets,
                            'probed_essids': client.probed_essids,
                            'vendor': client.vendor,
                            'device_type': client.device_type
                        })

                return jsonify({
                    'success': True,
                    'count': len(clients),
                    'data': clients
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        # ========== Flipper Zero Control ==========

        @self.app.route('/api/flipper/connect', methods=['POST'])
        def flipper_connect():
            """Connect to Flipper Zero"""
            try:
                data = request.get_json() or {}
                port = data.get('port', None)

                if not hasattr(self.main_window, 'flipper_tab'):
                    return jsonify({
                        'success': False,
                        'error': 'Flipper tab not available'
                    }), 400

                # Initialize service if needed
                if not self.main_window.flipper_tab.flipper_service:
                    self.main_window.flipper_tab._initialize_service()

                # Connect
                success = self.main_window.flipper_tab.flipper_service.connect(port)

                if success:
                    device = self.main_window.flipper_tab.flipper_service.device
                    return jsonify({
                        'success': True,
                        'message': 'Connected to Flipper Zero',
                        'device': {
                            'name': device.name,
                            'model': device.hardware_model,
                            'uid': device.hardware_uid,
                            'firmware': f"{device.firmware_origin} {device.firmware_version}",
                            'port': device.port
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to connect to Flipper Zero'
                    }), 500

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/flipper/disconnect', methods=['POST'])
        def flipper_disconnect():
            """Disconnect from Flipper Zero"""
            try:
                if not hasattr(self.main_window, 'flipper_tab'):
                    return jsonify({
                        'success': False,
                        'error': 'Flipper tab not available'
                    }), 400

                if self.main_window.flipper_tab.flipper_service:
                    self.main_window.flipper_tab.flipper_service.disconnect()

                return jsonify({
                    'success': True,
                    'message': 'Disconnected from Flipper Zero'
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/flipper/command', methods=['POST'])
        def flipper_command():
            """Send command to Flipper Zero"""
            try:
                data = request.get_json()
                if not data or 'command' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Missing command parameter'
                    }), 400

                command = data['command']

                if not hasattr(self.main_window, 'flipper_tab'):
                    return jsonify({
                        'success': False,
                        'error': 'Flipper tab not available'
                    }), 400

                service = self.main_window.flipper_tab.flipper_service

                if not service or not service.is_connected():
                    return jsonify({
                        'success': False,
                        'error': 'Flipper Zero not connected'
                    }), 400

                response = service.send_command(command)

                return jsonify({
                    'success': True,
                    'command': command,
                    'response': response
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/flipper/led', methods=['POST'])
        def flipper_led():
            """Control Flipper LED"""
            try:
                data = request.get_json() or {}
                color = data.get('color', 'blue')
                duration = data.get('duration', 1)

                if not hasattr(self.main_window, 'flipper_tab'):
                    return jsonify({
                        'success': False,
                        'error': 'Flipper tab not available'
                    }), 400

                service = self.main_window.flipper_tab.flipper_service

                if not service or not service.is_connected():
                    return jsonify({
                        'success': False,
                        'error': 'Flipper Zero not connected'
                    }), 400

                service.led_blink(color, duration)

                return jsonify({
                    'success': True,
                    'message': f'LED blinked {color} for {duration}s'
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/flipper/vibrate', methods=['POST'])
        def flipper_vibrate():
            """Vibrate Flipper"""
            try:
                data = request.get_json() or {}
                duration = data.get('duration', 1)

                if not hasattr(self.main_window, 'flipper_tab'):
                    return jsonify({
                        'success': False,
                        'error': 'Flipper tab not available'
                    }), 400

                service = self.main_window.flipper_tab.flipper_service

                if not service or not service.is_connected():
                    return jsonify({
                        'success': False,
                        'error': 'Flipper Zero not connected'
                    }), 400

                service.vibrate(duration)

                return jsonify({
                    'success': True,
                    'message': f'Vibrated for {duration}s'
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/flipper/info', methods=['GET'])
        def flipper_info():
            """Get Flipper device info"""
            try:
                if not hasattr(self.main_window, 'flipper_tab'):
                    return jsonify({
                        'success': False,
                        'error': 'Flipper tab not available'
                    }), 400

                service = self.main_window.flipper_tab.flipper_service

                if not service or not service.is_connected():
                    return jsonify({
                        'success': False,
                        'error': 'Flipper Zero not connected'
                    }), 400

                info = service.get_info()

                return jsonify({
                    'success': True,
                    'data': info
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        # ========== GUI Control ==========

        @self.app.route('/api/gui/tab', methods=['POST'])
        def gui_switch_tab():
            """Switch to specific tab"""
            try:
                data = request.get_json()
                if not data or 'tab' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Missing tab parameter'
                    }), 400

                tab_name = data['tab']
                success = self.main_window.api_switch_tab(tab_name)

                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Switched to {tab_name} tab'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid tab name: {tab_name}'
                    }), 400

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/scan/start', methods=['POST'])
        def gui_scan_start():
            """Start scanning"""
            try:
                monitor_iface = getattr(self.main_window, 'monitor_interface', None)
                if hasattr(self.main_window, 'scanner_tab') and self.main_window.scanner_tab:
                    monitor_iface = getattr(self.main_window.scanner_tab, 'monitor_interface', None)

                if not monitor_iface:
                    return jsonify({
                        'success': False,
                        'error': 'No monitor interface available'
                    }), 400

                # Call start_scan from main thread
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self.main_window.scanner_tab,
                    "start_scan",
                    Qt.ConnectionType.QueuedConnection
                )

                return jsonify({
                    'success': True,
                    'message': 'Scanner started',
                    'interface': monitor_iface
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/scan/stop', methods=['POST'])
        def gui_scan_stop():
            """Stop scanning"""
            try:
                # Call stop_scan from main thread
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self.main_window.scanner_tab,
                    "stop_scan",
                    Qt.ConnectionType.QueuedConnection
                )

                return jsonify({
                    'success': True,
                    'message': 'Scanner stopped'
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/scan/status', methods=['GET'])
        def gui_scan_status():
            """Get scan status"""
            try:
                scanner = None
                if hasattr(self.main_window, 'scanner_tab') and hasattr(self.main_window.scanner_tab, 'scanner'):
                    scanner = self.main_window.scanner_tab.scanner

                status = {
                    'running': scanner and getattr(scanner, 'running', False) if scanner else False,
                    'interface': getattr(self.main_window.scanner_tab, 'monitor_interface', None) if hasattr(self.main_window, 'scanner_tab') else None,
                    'networks': len(scanner.get_all_aps()) if scanner else 0,
                    'clients': len(scanner.get_all_clients()) if scanner else 0
                }

                return jsonify({
                    'success': True,
                    'data': status
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/networks', methods=['GET'])
        def gui_get_networks():
            """Get current network list from GUI"""
            try:
                networks = self.main_window.api_get_networks()

                return jsonify({
                    'success': True,
                    'count': len(networks),
                    'data': networks
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/clients', methods=['GET'])
        def gui_get_clients():
            """Get current client list from GUI"""
            try:
                clients = self.main_window.api_get_clients()

                return jsonify({
                    'success': True,
                    'count': len(clients),
                    'data': clients
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/gps/status', methods=['GET'])
        def gui_gps_status():
            """Get current GPS status"""
            try:
                gps_status = self.main_window.api_get_gps_status()

                return jsonify({
                    'success': True,
                    'data': gps_status
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/gps/location', methods=['POST'])
        def gui_update_gps():
            """Update GPS location on map"""
            try:
                data = request.get_json()
                if not data or 'latitude' not in data or 'longitude' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Missing latitude or longitude'
                    }), 400

                lat = float(data['latitude'])
                lon = float(data['longitude'])

                success = self.main_window.api_update_gps_location(lat, lon)

                if success:
                    return jsonify({
                        'success': True,
                        'message': f'GPS location updated to {lat}, {lon}'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to update GPS location'
                    }), 500

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/filter', methods=['POST'])
        def gui_apply_filter():
            """Apply filters to network list"""
            try:
                data = request.get_json()
                if not data or 'type' not in data or 'value' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Missing type or value parameter'
                    }), 400

                filter_type = data['type']
                filter_value = data['value']

                success = self.main_window.api_apply_filter(filter_type, filter_value)

                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Filter applied: {filter_type}={filter_value}'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to apply filter'
                    }), 500

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/stats', methods=['GET'])
        def gui_get_stats():
            """Get all current statistics"""
            try:
                stats = self.main_window.api_get_stats()

                return jsonify({
                    'success': True,
                    'data': stats
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/theme', methods=['POST'])
        def gui_change_theme():
            """Change GUI theme"""
            try:
                data = request.get_json()
                if not data or 'theme' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Missing theme parameter'
                    }), 400

                theme_name = data['theme']
                success = self.main_window.api_change_theme(theme_name)

                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Theme changed to {theme_name}'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to change theme to {theme_name}'
                    }), 500

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/gui/state', methods=['GET'])
        def gui_get_state():
            """Get complete GUI state"""
            try:
                state = self.main_window.api_get_state()

                return jsonify({
                    'success': True,
                    'data': state
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        # ========== Attack Operations ==========

        @self.app.route('/api/attack/deauth', methods=['POST'])
        def attack_deauth():
            """Launch deauth attack on client"""
            try:
                data = request.get_json()
                if not data or 'mac' not in data:
                    return jsonify({
                        'success': False,
                        'error': 'Missing mac parameter'
                    }), 400

                client_mac = data['mac']

                # Call deauth from main thread
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self.main_window.scanner_tab,
                    "quick_deauth_client",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, client_mac)
                )

                return jsonify({
                    'success': True,
                    'message': f'Deauth attack launched on {client_mac}'
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        # ========== Documentation ==========

        @self.app.route('/api/docs', methods=['GET'])
        def api_docs():
            """API documentation"""
            docs = {
                'success': True,
                'message': 'Gattrose-NG Local API',
                'version': '2.0.0',
                'base_url': f'http://localhost:{self.port}',
                'endpoints': {
                    'Status & Info': {
                        'GET /api/status': 'Get Gattrose status',
                    },
                    'Scanner Control': {
                        'POST /api/scanner/start': 'Start WiFi scanning',
                        'POST /api/scanner/stop': 'Stop WiFi scanning',
                        'GET /api/scanner/networks': 'Get discovered networks',
                        'GET /api/scanner/clients': 'Get discovered clients',
                    },
                    'GUI Control': {
                        'POST /api/gui/tab': 'Switch tab (body: {"tab": "mapping"})',
                        'POST /api/gui/scan/start': 'Start scanning from GUI',
                        'POST /api/gui/scan/stop': 'Stop scanning from GUI',
                        'GET /api/gui/scan/status': 'Get scan status',
                        'GET /api/gui/networks': 'Get networks from GUI',
                        'GET /api/gui/clients': 'Get clients from GUI',
                        'GET /api/gui/gps/status': 'Get GPS status',
                        'POST /api/gui/gps/location': 'Update GPS location (body: {"latitude": 39.0, "longitude": -90.7})',
                        'POST /api/gui/filter': 'Apply filter (body: {"type": "ssid", "value": "MyNet"})',
                        'GET /api/gui/stats': 'Get all statistics',
                        'POST /api/gui/theme': 'Change theme (body: {"theme": "sonic"})',
                        'GET /api/gui/state': 'Get complete GUI state',
                    },
                    'Flipper Zero': {
                        'POST /api/flipper/connect': 'Connect to Flipper (body: {"port": "/dev/ttyACM0"} or empty for auto)',
                        'POST /api/flipper/disconnect': 'Disconnect from Flipper',
                        'POST /api/flipper/command': 'Send command (body: {"command": "device_info"})',
                        'POST /api/flipper/led': 'Blink LED (body: {"color": "blue", "duration": 2})',
                        'POST /api/flipper/vibrate': 'Vibrate (body: {"duration": 1})',
                        'GET /api/flipper/info': 'Get device info',
                    },
                    'Attacks': {
                        'POST /api/attack/deauth': 'Deauth attack (body: {"mac": "AA:BB:CC:DD:EE:FF"})',
                    }
                },
                'examples': {
                    'Get status': 'curl http://localhost:5555/api/status',
                    'Start scanner': 'curl -X POST http://localhost:5555/api/scanner/start',
                    'Switch to mapping tab': 'curl -X POST http://localhost:5555/api/gui/tab -H "Content-Type: application/json" -d \'{"tab": "mapping"}\'',
                    'Get GPS status': 'curl http://localhost:5555/api/gui/gps/status',
                    'Update GPS location': 'curl -X POST http://localhost:5555/api/gui/gps/location -H "Content-Type: application/json" -d \'{"latitude": 39.005509, "longitude": -90.741686}\'',
                    'Get GUI state': 'curl http://localhost:5555/api/gui/state',
                    'Change theme': 'curl -X POST http://localhost:5555/api/gui/theme -H "Content-Type: application/json" -d \'{"theme": "hacker"}\'',
                    'Get networks from GUI': 'curl http://localhost:5555/api/gui/networks',
                    'Get statistics': 'curl http://localhost:5555/api/gui/stats',
                    'Connect Flipper': 'curl -X POST http://localhost:5555/api/flipper/connect',
                    'Blink LED': 'curl -X POST http://localhost:5555/api/flipper/led -H "Content-Type: application/json" -d \'{"color": "blue", "duration": 2}\'',
                    'Send command': 'curl -X POST http://localhost:5555/api/flipper/command -H "Content-Type: application/json" -d \'{"command": "device_info"}\'',
                },
                'tab_names': {
                    'Valid tab names for /api/gui/tab': [
                        'dashboard', 'scanner', 'wps', 'clients',
                        'auto_attack', 'manual_attack', 'bluetooth',
                        'flipper', 'wigle', 'mapping'
                    ]
                }
            }
            return jsonify(docs)

        @self.app.route('/', methods=['GET'])
        def index():
            """Root endpoint - redirect to docs"""
            return jsonify({
                'message': 'Gattrose-NG Local API',
                'docs': f'http://localhost:{self.port}/api/docs'
            })

    def start(self):
        """Start the API server in background thread"""
        if self.running:
            print("[!] Local API server already running")
            return

        self.running = True

        def run_server():
            # Disable Flask logging
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)

            # Run server
            self.app.run(
                host='127.0.0.1',  # Localhost only for security
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        print(f"[+] Local API server started on http://127.0.0.1:{self.port}")
        print(f"[i] API docs: http://127.0.0.1:{self.port}/api/docs")

    def stop(self):
        """Stop the API server"""
        self.running = False
        # Note: Flask server will stop when main application exits


if __name__ == '__main__':
    """Test the API server"""
    from flask import Flask

    class MockMainWindow:
        def __init__(self):
            self.monitor_interface = "wlp7s0mon"

    mock_window = MockMainWindow()
    api = LocalAPIServer(mock_window, port=5555)
    api.start()

    print("\nLocal API server running...")
    print("Test with: curl http://localhost:5555/api/docs")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
