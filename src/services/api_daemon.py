#!/usr/bin/env python3
"""
Gattrose API Daemon
Standalone REST API server that interfaces with core service
"""

import os
import sys
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.core_service import get_service


class GattroseAPIDaemon:
    """Standalone API daemon"""

    def __init__(self, host: str = '127.0.0.1', port: int = 5555):
        self.host = host
        self.port = port
        self.app = Flask(__name__)

        # Enable CORS for localhost
        CORS(self.app, resources={r"/*": {"origins": "http://localhost:*"}})

        # Get core service
        self.service = get_service()

        # Setup routes
        self._setup_routes()

        print(f"[*] Gattrose API Daemon initialized on {host}:{port}")

    def _setup_routes(self):
        """Setup all API routes"""

        # ========== Documentation ==========

        @self.app.route('/api/docs', methods=['GET'])
        def get_docs():
            """Get API documentation"""
            docs = {
                'title': 'Gattrose-NG REST API',
                'version': '2.0',
                'description': 'RESTful API for Gattrose wireless security testing',
                'endpoints': {
                    'status': {
                        'GET /api/status': 'Get system status',
                    },
                    'scanner': {
                        'POST /api/scanner/start': 'Start WiFi scanner',
                        'POST /api/scanner/stop': 'Stop WiFi scanner',
                        'GET /api/scanner/networks': 'Get discovered networks',
                        'GET /api/scanner/clients': 'Get discovered clients'
                    },
                    'monitor': {
                        'POST /api/monitor/enable': 'Enable monitor mode',
                        'POST /api/monitor/disable': 'Disable monitor mode'
                    },
                    'flipper': {
                        'POST /api/flipper/connect': 'Connect to Flipper Zero',
                        'POST /api/flipper/disconnect': 'Disconnect Flipper Zero',
                        'GET /api/flipper/info': 'Get Flipper device info',
                        'POST /api/flipper/led': 'Control Flipper LED',
                        'POST /api/flipper/vibrate': 'Vibrate Flipper',
                        'POST /api/flipper/command': 'Send raw command to Flipper'
                    }
                }
            }
            return jsonify(docs)

        # ========== Status ==========

        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """Get Gattrose status"""
            try:
                state = self.service.state.get_all()
                return jsonify({
                    'success': True,
                    'data': {
                        'running': state['running'],
                        'scanner_active': state['scanner_active'],
                        'monitor_interface': state['monitor_interface'],
                        'physical_interface': state['physical_interface'],
                        'flipper_connected': state['flipper_connected'],
                        'flipper_port': state['flipper_port'],
                        'ap_count': len(state['aps']),
                        'client_count': len(state['clients']),
                        'attacks_running': len(state['attacks_running'])
                    }
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        # ========== Monitor Mode ==========

        @self.app.route('/api/monitor/enable', methods=['POST'])
        def enable_monitor():
            """Enable monitor mode"""
            try:
                data = request.get_json() or {}
                interface = data.get('interface', 'wlan0')

                success, monitor_iface = self.service.enable_monitor_mode(interface)

                if success:
                    return jsonify({
                        'success': True,
                        'message': 'Monitor mode enabled',
                        'monitor_interface': monitor_iface,
                        'physical_interface': interface
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to enable monitor mode'
                    }), 500

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/monitor/disable', methods=['POST'])
        def disable_monitor():
            """Disable monitor mode"""
            try:
                data = request.get_json() or {}
                interface = data.get('interface') or self.service.state.get('monitor_interface')

                if not interface:
                    return jsonify({
                        'success': False,
                        'error': 'No monitor interface specified'
                    }), 400

                success = self.service.disable_monitor_mode(interface)

                return jsonify({
                    'success': success,
                    'message': 'Monitor mode disabled' if success else 'Failed to disable monitor mode'
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        # ========== Scanner ==========

        @self.app.route('/api/scanner/start', methods=['POST'])
        def start_scanner():
            """Start WiFi scanner"""
            try:
                data = request.get_json() or {}
                interface = data.get('interface') or self.service.state.get('monitor_interface')
                channel = data.get('channel')

                if not interface:
                    return jsonify({
                        'success': False,
                        'error': 'No monitor interface available'
                    }), 400

                success = self.service.start_scanner(interface, channel)

                return jsonify({
                    'success': success,
                    'message': 'Scanner started' if success else 'Failed to start scanner',
                    'interface': interface
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/scanner/stop', methods=['POST'])
        def stop_scanner():
            """Stop WiFi scanner"""
            try:
                success = self.service.stop_scanner()
                return jsonify({
                    'success': success,
                    'message': 'Scanner stopped' if success else 'Scanner not running'
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/scanner/networks', methods=['GET'])
        def get_networks():
            """Get discovered networks"""
            try:
                return jsonify(self.service.export_networks_json())
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/scanner/clients', methods=['GET'])
        def get_clients():
            """Get discovered clients"""
            try:
                return jsonify(self.service.export_clients_json())
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        # ========== Flipper Zero ==========

        @self.app.route('/api/flipper/connect', methods=['POST'])
        def flipper_connect():
            """Connect to Flipper Zero"""
            try:
                data = request.get_json() or {}
                port = data.get('port')

                success = self.service.connect_flipper(port)

                if success:
                    info = self.service.get_flipper_info()
                    return jsonify({
                        'success': True,
                        'message': 'Connected to Flipper Zero',
                        'device': info
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
            """Disconnect Flipper Zero"""
            try:
                success = self.service.disconnect_flipper()
                return jsonify({
                    'success': success,
                    'message': 'Disconnected' if success else 'Not connected'
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/flipper/info', methods=['GET'])
        def flipper_info():
            """Get Flipper device info"""
            try:
                info = self.service.get_flipper_info()
                if info:
                    return jsonify({'success': True, 'device': info})
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Flipper not connected'
                    }), 400
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/flipper/led', methods=['POST'])
        def flipper_led():
            """Control Flipper LED"""
            try:
                if not self.service.flipper_service:
                    return jsonify({
                        'success': False,
                        'error': 'Flipper not connected'
                    }), 400

                data = request.get_json() or {}
                color = data.get('color', 'off').lower()

                if color == 'off':
                    self.service.flipper_service.led_off()
                elif color == 'red':
                    self.service.flipper_service.led_set(255, 0, 0)
                elif color == 'green':
                    self.service.flipper_service.led_set(0, 255, 0)
                elif color == 'blue':
                    self.service.flipper_service.led_set(0, 0, 255)
                elif color == 'custom':
                    r = data.get('red', 0)
                    g = data.get('green', 0)
                    b = data.get('blue', 0)
                    self.service.flipper_service.led_set(r, g, b)

                return jsonify({'success': True, 'message': f'LED set to {color}'})

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/flipper/vibrate', methods=['POST'])
        def flipper_vibrate():
            """Vibrate Flipper"""
            try:
                if not self.service.flipper_service:
                    return jsonify({
                        'success': False,
                        'error': 'Flipper not connected'
                    }), 400

                data = request.get_json() or {}
                enable = data.get('enable', True)

                self.service.flipper_service.vibrate(1 if enable else 0)

                return jsonify({
                    'success': True,
                    'message': 'Vibration ' + ('enabled' if enable else 'disabled')
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/flipper/command', methods=['POST'])
        def flipper_command():
            """Send raw command to Flipper"""
            try:
                if not self.service.flipper_service:
                    return jsonify({
                        'success': False,
                        'error': 'Flipper not connected'
                    }), 400

                data = request.get_json() or {}
                command = data.get('command', '')
                wait_response = data.get('wait_response', True)
                timeout = data.get('timeout', 5.0)

                response = self.service.flipper_service.send_command(
                    command,
                    wait_response=wait_response,
                    timeout=timeout
                )

                return jsonify({
                    'success': True,
                    'response': response
                })

            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

    def run(self):
        """Run API server"""
        print(f"[*] Starting Gattrose API server on {self.host}:{self.port}")
        print(f"[*] API documentation: http://{self.host}:{self.port}/api/docs")
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)


if __name__ == '__main__':
    daemon = GattroseAPIDaemon()
    daemon.run()
