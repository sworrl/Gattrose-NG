"""
REST API for Gattrose-NG Web Interface
Provides full control via HTTPS endpoints
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from functools import wraps
import sqlite3
from pathlib import Path
import os


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Paths (dynamic, works on all systems)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "gattrose.db"
WEB_ROOT = PROJECT_ROOT / "web"


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def require_auth(f):
    """Decorator for routes requiring authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For now, no authentication - this is for local/trusted network use
        # In production, implement token-based auth
        return f(*args, **kwargs)
    return decorated_function


# ========== DASHBOARD / STATS ENDPOINTS ==========

@app.route('/api/dashboard/stats', methods=['GET'])
@require_auth
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total networks
        cursor.execute("SELECT COUNT(*) FROM networks")
        total_networks = cursor.fetchone()[0]

        # Total clients
        cursor.execute("SELECT COUNT(*) FROM clients")
        total_clients = cursor.fetchone()[0]

        # Total handshakes
        cursor.execute("SELECT COUNT(*) FROM handshakes")
        total_handshakes = cursor.fetchone()[0]

        # Cracked handshakes
        cursor.execute("SELECT COUNT(*) FROM handshakes WHERE is_cracked = 1")
        cracked_handshakes = cursor.fetchone()[0]

        # WPS enabled networks
        cursor.execute("SELECT COUNT(*) FROM networks WHERE wps_enabled = 1")
        wps_networks = cursor.fetchone()[0]

        # Encryption breakdown
        cursor.execute("""
            SELECT encryption, COUNT(*) as count
            FROM networks
            GROUP BY encryption
        """)
        encryption_breakdown = {row['encryption']: row['count'] for row in cursor.fetchall()}

        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'total_networks': total_networks,
                'total_clients': total_clients,
                'total_handshakes': total_handshakes,
                'cracked_handshakes': cracked_handshakes,
                'wps_networks': wps_networks,
                'encryption_breakdown': encryption_breakdown
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/networks', methods=['GET'])
@require_auth
def get_networks():
    """Get all networks with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM networks")
        total = cursor.fetchone()[0]

        # Get networks
        cursor.execute("""
            SELECT *
            FROM networks
            ORDER BY last_seen DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))

        networks = []
        for row in cursor.fetchall():
            networks.append(dict(row))

        conn.close()

        return jsonify({
            'success': True,
            'data': networks,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/networks/<bssid>', methods=['GET'])
@require_auth
def get_network(bssid):
    """Get specific network details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM networks WHERE bssid = ?", (bssid,))
        network = cursor.fetchone()

        if network:
            return jsonify({
                'success': True,
                'data': dict(network)
            })
        else:
            return jsonify({'success': False, 'error': 'Network not found'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/clients', methods=['GET'])
@require_auth
def get_clients():
    """Get all clients"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM clients ORDER BY last_seen DESC LIMIT 100")
        clients = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return jsonify({
            'success': True,
            'data': clients
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/handshakes', methods=['GET'])
@require_auth
def get_handshakes():
    """Get all handshakes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT h.*, n.ssid, n.bssid
            FROM handshakes h
            JOIN networks n ON h.network_id = n.id
            ORDER BY h.captured_at DESC
        """)

        handshakes = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            'success': True,
            'data': handshakes
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== ATTACK QUEUE ENDPOINTS ==========

@app.route('/api/attacks/queue', methods=['GET'])
@require_auth
def get_attack_queue():
    """Get attack queue"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT aq.*, n.ssid, n.bssid
            FROM attack_queue aq
            JOIN networks n ON aq.network_id = n.id
            ORDER BY aq.priority DESC, aq.added_at ASC
        """)

        queue = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({
            'success': True,
            'data': queue
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/attacks/queue', methods=['POST'])
@require_auth
def add_to_attack_queue():
    """Add target to attack queue"""
    try:
        data = request.json
        bssid = data.get('bssid')
        attack_type = data.get('attack_type', 'auto')
        priority = data.get('priority', 50)

        if not bssid:
            return jsonify({'success': False, 'error': 'BSSID required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get network ID
        cursor.execute("SELECT id FROM networks WHERE bssid = ?", (bssid,))
        network = cursor.fetchone()

        if not network:
            return jsonify({'success': False, 'error': 'Network not found'}), 404

        network_id = network['id']

        # Add to queue
        cursor.execute("""
            INSERT INTO attack_queue (network_id, attack_type, priority, status)
            VALUES (?, ?, ?, 'pending')
        """, (network_id, attack_type, priority))

        conn.commit()
        queue_id = cursor.lastrowid
        conn.close()

        return jsonify({
            'success': True,
            'data': {'id': queue_id}
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/attacks/queue/<int:queue_id>', methods=['DELETE'])
@require_auth
def remove_from_attack_queue(queue_id):
    """Remove target from attack queue"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM attack_queue WHERE id = ?", (queue_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== SYSTEM STATUS ENDPOINTS ==========

@app.route('/api/system/status', methods=['GET'])
@require_auth
def get_system_status():
    """Get system status"""
    try:
        import subprocess

        # Check if monitor mode is enabled
        result = subprocess.run(['iwconfig'], capture_output=True, text=True)
        monitor_enabled = 'Mode:Monitor' in result.stdout

        # Check interface
        interfaces = []
        for line in result.stdout.split('\n'):
            if 'IEEE 802.11' in line:
                iface = line.split()[0]
                interfaces.append(iface)

        return jsonify({
            'success': True,
            'data': {
                'monitor_enabled': monitor_enabled,
                'interfaces': interfaces,
                'scanning': False  # TODO: Check actual scanning status
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system/scan/start', methods=['POST'])
@require_auth
def start_scan():
    """Start scanning"""
    # TODO: Integrate with scanner service
    return jsonify({
        'success': False,
        'error': 'Not implemented - use GUI to start scan'
    }), 501


@app.route('/api/system/scan/stop', methods=['POST'])
@require_auth
def stop_scan():
    """Stop scanning"""
    # TODO: Integrate with scanner service
    return jsonify({
        'success': False,
        'error': 'Not implemented - use GUI to stop scan'
    }), 501


# ========== SEARCH ENDPOINTS ==========

@app.route('/api/search', methods=['GET'])
@require_auth
def search():
    """Search networks and clients"""
    try:
        query = request.args.get('q', '')
        search_type = request.args.get('type', 'all')  # 'all', 'networks', 'clients'

        if not query:
            return jsonify({'success': False, 'error': 'Query required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        results = {
            'networks': [],
            'clients': []
        }

        # Search networks
        if search_type in ['all', 'networks']:
            cursor.execute("""
                SELECT * FROM networks
                WHERE ssid LIKE ? OR bssid LIKE ? OR manufacturer LIKE ?
                LIMIT 50
            """, (f'%{query}%', f'%{query}%', f'%{query}%'))
            results['networks'] = [dict(row) for row in cursor.fetchall()]

        # Search clients
        if search_type in ['all', 'clients']:
            cursor.execute("""
                SELECT * FROM clients
                WHERE mac_address LIKE ? OR manufacturer LIKE ?
                LIMIT 50
            """, (f'%{query}%', f'%{query}%'))
            results['clients'] = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return jsonify({
            'success': True,
            'data': results
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== EXPORT ENDPOINTS ==========

@app.route('/api/export/csv', methods=['GET'])
@require_auth
def export_csv():
    """Export data as CSV"""
    try:
        export_type = request.args.get('type', 'networks')

        conn = get_db_connection()
        cursor = conn.cursor()

        if export_type == 'networks':
            cursor.execute("SELECT * FROM networks")
        elif export_type == 'clients':
            cursor.execute("SELECT * FROM clients")
        elif export_type == 'handshakes':
            cursor.execute("SELECT * FROM handshakes")
        else:
            return jsonify({'success': False, 'error': 'Invalid export type'}), 400

        rows = cursor.fetchall()
        conn.close()

        # Convert to CSV format
        import csv
        import io

        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        csv_data = output.getvalue()

        return csv_data, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=gattrose_{export_type}.csv'
        }

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== WEB INTERFACE ROUTES ==========

@app.route('/')
def index():
    """Serve the main web interface"""
    return send_from_directory(WEB_ROOT, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files (CSS, JS, images)"""
    return send_from_directory(WEB_ROOT, path)


@app.route('/api/docs')
def api_docs():
    """API documentation"""
    return jsonify({
        'success': True,
        'message': 'Gattrose-NG Web API',
        'version': '1.0.0',
        'endpoints': {
            '/': 'Web interface',
            '/api/dashboard/stats': 'Dashboard statistics',
            '/api/networks': 'List all networks',
            '/api/networks/<bssid>': 'Get specific network',
            '/api/clients': 'List all clients',
            '/api/clients/<mac>': 'Get specific client',
            '/api/handshakes': 'List all handshakes',
            '/api/attacks/queue': 'Get attack queue status',
            '/api/scan/status': 'Get scan status',
            '/api/system/status': 'System status',
            '/api/export/networks': 'Export networks to CSV',
            '/api/export/clients': 'Export clients to CSV',
            '/api/docs': 'This documentation'
        }
    })


def run_api_server(port=5000):
    """Run the API server"""
    print(f"[*] Starting Gattrose-NG Web API on http://0.0.0.0:{port}")
    print(f"[*] Web interface: http://localhost:{port}")
    print(f"[*] API docs: http://localhost:{port}/api/docs")
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    run_api_server()
