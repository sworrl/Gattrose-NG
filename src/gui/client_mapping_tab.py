"""
Client Mapping Tab
Displays WiFi client devices on a map with observed locations and AP associations
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox, QComboBox
)
from PyQt6.QtCore import QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
import json


class ClientMappingTab(QWidget):
    """Tab for displaying WiFi client devices on a map"""

    def __init__(self):
        super().__init__()
        self.map_initialized = False
        self.page_loaded = False
        self.init_ui()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_markers)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds

    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.setLayout(layout)

        # Controls at top (compact)
        controls_layout = QHBoxLayout()

        # Refresh button
        self.refresh_btn = QPushButton("Refresh Map")
        self.refresh_btn.clicked.connect(self.refresh_map)
        controls_layout.addWidget(self.refresh_btn)

        # Show connected only checkbox
        self.connected_only_check = QCheckBox("Show Connected Only")
        self.connected_only_check.setChecked(True)
        self.connected_only_check.toggled.connect(self.refresh_map)
        controls_layout.addWidget(self.connected_only_check)

        # Time range filter
        controls_layout.addWidget(QLabel("Time Range:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["Last Hour", "Last 6 Hours", "Last 24 Hours", "All Time"])
        self.time_range_combo.setCurrentIndex(1)  # Default: Last 6 Hours
        self.time_range_combo.currentIndexChanged.connect(self.refresh_map)
        controls_layout.addWidget(self.time_range_combo)

        # Stats label
        self.stats_label = QLabel("No clients displayed")
        controls_layout.addWidget(self.stats_label)
        controls_layout.addStretch()

        layout.addLayout(controls_layout, 0)

        # Web view for map
        self.web_view = QWebEngineView()
        self.web_view.setMinimumHeight(400)
        layout.addWidget(self.web_view, 1)

        # Load initial map
        self.load_initial_map()

    def load_initial_map(self):
        """Load map HTML once (no flickering)"""
        html = self._generate_map_html()
        self.web_view.loadFinished.connect(self._on_page_loaded)
        self.web_view.setHtml(html)
        self.map_initialized = True

    def _on_page_loaded(self, ok):
        """Called when page finishes loading"""
        if ok:
            self.page_loaded = True
            QTimer.singleShot(500, self.update_markers)

    def refresh_map(self):
        """Force full map refresh"""
        if not self.map_initialized:
            self.load_initial_map()
        else:
            self.update_markers()

    def update_markers(self):
        """Update client markers incrementally without reloading HTML"""
        if not self.map_initialized or not self.page_loaded:
            return

        from ..database.models import get_session, Client, Network
        from datetime import datetime, timedelta
        import json as json_lib

        session = get_session()
        try:
            # Get current GPS location
            current_gps = self._get_current_gps_location()

            # Get time range filter
            time_range_map = {
                0: 1,    # Last Hour
                1: 6,    # Last 6 Hours
                2: 24,   # Last 24 Hours
                3: None  # All Time
            }
            hours = time_range_map[self.time_range_combo.currentIndex()]

            if hours:
                time_cutoff = datetime.utcnow() - timedelta(hours=hours)
            else:
                time_cutoff = None

            # Get clients
            if self.connected_only_check.isChecked():
                # Only show clients that have associated networks
                clients_query = session.query(Client).filter(
                    Client.associated_networks.isnot(None)
                )
            else:
                # Show all clients
                clients_query = session.query(Client)

            if time_cutoff:
                clients_query = clients_query.filter(Client.last_seen >= time_cutoff)

            clients = clients_query.all()

            # Build markers data for clients
            # Since clients don't have GPS, we'll use the location of their associated networks
            markers = []
            for client in clients:
                # Parse associated networks
                associated_bssids = []
                if client.associated_networks:
                    try:
                        associated_bssids = json_lib.loads(client.associated_networks)
                    except:
                        pass

                if not associated_bssids:
                    continue

                # Get network location for first associated network
                for bssid in associated_bssids[:1]:  # Just use first network
                    network = session.query(Network).filter(Network.bssid == bssid).first()
                    if network and network.latitude and network.longitude:
                        marker = {
                            'lat': network.latitude,
                            'lon': network.longitude,
                            'mac': client.mac_address,
                            'vendor': client.manufacturer or 'Unknown',
                            'signal': client.current_signal or 0,
                            'ap_ssid': network.ssid or "(hidden)",
                            'ap_bssid': network.bssid,
                            'last_seen': client.last_seen.isoformat() if client.last_seen else None,
                            'obs_count': len(associated_bssids),
                            'track': []  # No track data available for clients
                        }
                        markers.append(marker)
                        break

            # Update stats
            self.stats_label.setText(f"Displaying {len(markers)} clients")

            # Update markers via JavaScript
            self._update_markers_js(markers, current_gps)

        finally:
            session.close()

    def _get_current_gps_location(self):
        """Get current GPS location from status file"""
        import os
        try:
            if not os.path.exists('/tmp/gattrose-status.json'):
                return None

            with open('/tmp/gattrose-status.json', 'r') as f:
                status = json.load(f)
                gps_data = status.get('services', {}).get('gps', {}).get('metadata', {})
                if gps_data.get('has_location'):
                    return {
                        'lat': gps_data.get('latitude'),
                        'lon': gps_data.get('longitude'),
                        'accuracy': gps_data.get('accuracy'),
                        'source': gps_data.get('source'),
                        'fix_quality': gps_data.get('fix_quality')
                    }
        except Exception as e:
            if os.path.exists('/tmp/gattrose-status.json'):
                print(f"[CLIENT-MAP] Error reading GPS location: {e}")
        return None

    def _update_markers_js(self, markers, current_gps):
        """Update markers using JavaScript without reloading page"""
        if not self.page_loaded:
            return

        markers_json = json.dumps(markers)
        gps_json = json.dumps(current_gps) if current_gps else 'null'

        js_code = f"""
        try {{
            if (typeof updateClientMarkers === 'function') {{
                updateClientMarkers({markers_json});
            }}
            if (typeof updateCurrentGPS === 'function') {{
                updateCurrentGPS({gps_json});
            }}
        }} catch(e) {{
            console.error('Error updating client markers:', e);
        }}
        """

        self.web_view.page().runJavaScript(js_code)

    def _generate_map_html(self):
        """Generate HTML for the client map"""
        avg_lat = 39.005509
        avg_lon = -90.741686

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ width: 100%; height: 100vh; }}
        .client-label {{
            font-size: 10px;
            font-weight: bold;
            color: #fff;
            background-color: rgba(0, 100, 200, 0.8);
            border-radius: 3px;
            padding: 2px 4px;
            white-space: nowrap;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([{avg_lat}, {avg_lon}], 13);

        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 19,
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        }}).addTo(map);

        var clientMarkersLayer = L.markerClusterGroup({{
            maxClusterRadius: 40,
            spiderfyOnMaxZoom: true
        }}).addTo(map);
        var clientTracksLayer = L.layerGroup().addTo(map);
        var currentGPSMarker = null;

        function updateClientMarkers(markers) {{
            clientMarkersLayer.clearLayers();
            clientTracksLayer.clearLayers();

            markers.forEach(function(marker) {{
                // Draw client track if available
                if (marker.track && marker.track.length > 1) {{
                    var trackCoords = marker.track.map(p => [p.lat, p.lon]);
                    var clientTrack = L.polyline(trackCoords, {{
                        color: '#0066cc',
                        weight: 2,
                        opacity: 0.5,
                        dashArray: '5, 5'
                    }});
                    clientTracksLayer.addLayer(clientTrack);
                }}

                // Create client marker
                var clientMarker = L.circleMarker([marker.lat, marker.lon], {{
                    radius: 6,
                    fillColor: '#0066cc',
                    color: '#003366',
                    weight: 2,
                    opacity: 0.9,
                    fillOpacity: 0.7
                }});

                // Determine device icon based on vendor
                var deviceIcon = '📱'; // Default phone
                var deviceColor = '#0066cc';
                if (marker.vendor.toLowerCase().includes('apple')) {{
                    deviceIcon = ''; // iPhone
                    deviceColor = '#555';
                }} else if (marker.vendor.toLowerCase().includes('samsung')) {{
                    deviceIcon = '📱'; // Android
                    deviceColor = '#1a73e8';
                }} else if (marker.vendor.toLowerCase().includes('intel') || marker.vendor.toLowerCase().includes('dell') || marker.vendor.toLowerCase().includes('lenovo') || marker.vendor.toLowerCase().includes('hp')) {{
                    deviceIcon = '💻'; // Laptop
                    deviceColor = '#5f6368';
                }} else if (marker.vendor.toLowerCase().includes('amazon') || marker.vendor.toLowerCase().includes('google')) {{
                    deviceIcon = '📺'; // Smart device
                    deviceColor = '#ea4335';
                }}

                // Device icon with vendor label
                var deviceIconHtml = `
                    <div style="text-align: center;">
                        <div style="font-size: 24px; filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.5));">
                            ${{deviceIcon}}
                        </div>
                        <div style="background: ${{deviceColor}}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; white-space: nowrap; margin-top: 2px;">
                            ${{marker.vendor.substring(0, 12)}}
                        </div>
                    </div>
                `;

                var label = L.marker([marker.lat, marker.lon], {{
                    icon: L.divIcon({{
                        className: 'client-device-icon',
                        html: deviceIconHtml,
                        iconSize: [80, 50],
                        iconAnchor: [40, 25]
                    }})
                }});

                var popup = `
                    <div style="min-width: 250px;">
                        <h3 style="margin: 0 0 8px 0;">📱 Client Device</h3>
                        <table style="width: 100%; font-size: 12px;">
                            <tr><td><b>MAC:</b></td><td>${{marker.mac}}</td></tr>
                            <tr><td><b>Vendor:</b></td><td>${{marker.vendor}}</td></tr>
                            <tr><td><b>Signal:</b></td><td>${{marker.signal}} dBm</td></tr>
                            <tr><td colspan="2"><hr style="margin: 4px 0;"></td></tr>
                            <tr><td><b>Connected AP:</b></td><td>${{marker.ap_ssid}}</td></tr>
                            <tr><td><b>AP BSSID:</b></td><td>${{marker.ap_bssid}}</td></tr>
                            <tr><td colspan="2"><hr style="margin: 4px 0;"></td></tr>
                            <tr><td><b>Last Seen:</b></td><td>${{marker.last_seen || 'Unknown'}}</td></tr>
                            <tr><td><b>Observations:</b></td><td>${{marker.obs_count}}</td></tr>
                            <tr><td><b>Location:</b></td><td>${{marker.lat.toFixed(6)}}, ${{marker.lon.toFixed(6)}}</td></tr>
                        </table>
                    </div>
                `;

                clientMarker.bindPopup(popup);
                label.bindPopup(popup);

                clientMarkersLayer.addLayer(clientMarker);
                clientMarkersLayer.addLayer(label);
            }});

            if (markers.length > 0) {{
                var bounds = markers.map(m => [m.lat, m.lon]);
                map.fitBounds(bounds, {{padding: [50, 50]}});
            }}
        }}

        function updateCurrentGPS(gpsData) {{
            if (currentGPSMarker) {{
                map.removeLayer(currentGPSMarker);
                currentGPSMarker = null;
            }}

            if (gpsData && gpsData.lat && gpsData.lon) {{
                var accuracyCircle = L.circle([gpsData.lat, gpsData.lon], {{
                    color: '#4ecdc4',
                    fillColor: '#4ecdc4',
                    fillOpacity: 0.1,
                    radius: gpsData.accuracy || 10,
                    weight: 2
                }});

                var gpsMarker = L.marker([gpsData.lat, gpsData.lon], {{
                    icon: L.divIcon({{
                        html: '📍',
                        iconSize: [30, 30]
                    }})
                }});

                currentGPSMarker = L.featureGroup([accuracyCircle, gpsMarker]).addTo(map);
            }}
        }}
    </script>
</body>
</html>
        """
        return html
