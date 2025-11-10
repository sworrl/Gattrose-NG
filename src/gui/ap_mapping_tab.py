"""
AP Mapping Tab
Displays WiFi Access Points on a map with triangulated locations and confidence visualization
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox, QCheckBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
import json


class APMappingTab(QWidget):
    """Tab for displaying WiFi Access Points on a map with confidence visualization"""

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

        # Minimum observations filter
        controls_layout.addWidget(QLabel("Min Observations:"))
        self.min_obs_spin = QSpinBox()
        self.min_obs_spin.setMinimum(1)
        self.min_obs_spin.setMaximum(100)
        self.min_obs_spin.setValue(3)
        self.min_obs_spin.valueChanged.connect(self.refresh_map)
        controls_layout.addWidget(self.min_obs_spin)

        # Show all networks checkbox
        self.show_all_check = QCheckBox("Show All APs")
        self.show_all_check.setChecked(False)
        self.show_all_check.toggled.connect(self.refresh_map)
        controls_layout.addWidget(self.show_all_check)

        # Stats label
        self.stats_label = QLabel("No APs displayed")
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
        """Update AP markers incrementally without reloading HTML"""
        if not self.map_initialized or not self.page_loaded:
            return

        from ..database.models import get_session, Network, NetworkObservation
        from ..services.triangulation_service import TriangulationService
        from sqlalchemy import func

        session = get_session()
        try:
            # Get current GPS location
            current_gps = self._get_current_gps_location()

            # Get user location track
            from datetime import datetime, timedelta
            two_hours_ago = datetime.utcnow() - timedelta(hours=2)

            # Recent observations (last 2 hours)
            recent_obs = session.query(NetworkObservation).filter(
                NetworkObservation.latitude.isnot(None),
                NetworkObservation.longitude.isnot(None),
                NetworkObservation.timestamp >= two_hours_ago
            ).order_by(NetworkObservation.timestamp.asc()).all()

            # Older observations (decimated)
            older_obs = session.query(NetworkObservation).filter(
                NetworkObservation.latitude.isnot(None),
                NetworkObservation.longitude.isnot(None),
                NetworkObservation.timestamp < two_hours_ago
            ).order_by(NetworkObservation.timestamp.asc()).all()

            decimated_older = older_obs[::10] if len(older_obs) > 100 else older_obs
            all_obs = decimated_older + recent_obs

            track_points = [
                {
                    'lat': obs.latitude,
                    'lon': obs.longitude,
                    'timestamp': obs.timestamp.isoformat() if obs.timestamp else None,
                    'gps_source': obs.gps_source or 'unknown'
                }
                for obs in all_obs
            ]

            # Get networks
            if self.show_all_check.isChecked():
                networks = session.query(Network).filter(
                    Network.latitude.isnot(None),
                    Network.longitude.isnot(None)
                ).all()
            else:
                min_obs = self.min_obs_spin.value()
                networks_with_obs = session.query(
                    NetworkObservation.network_id,
                    func.count(NetworkObservation.id).label('obs_count')
                ).group_by(
                    NetworkObservation.network_id
                ).having(
                    func.count(NetworkObservation.id) >= min_obs
                ).all()

                network_ids = [net_id for net_id, _ in networks_with_obs]
                networks = session.query(Network).filter(Network.id.in_(network_ids)).all()

            # Build markers data
            markers = []
            for network in networks:
                result = TriangulationService.calculate_ap_location(network.id, min_observations=1)

                if result:
                    est_lat, est_lon, confidence_radius, obs_count = result
                    confidence_pct = max(0, min(100, 100 - (confidence_radius / 10)))

                    marker = {
                        'lat': est_lat,
                        'lon': est_lon,
                        'bssid': network.bssid,
                        'ssid': network.ssid or '(hidden)',
                        'confidence_radius': confidence_radius,
                        'confidence_pct': round(confidence_pct, 1),
                        'obs_count': obs_count,
                        'signal': network.current_signal or 0,
                        'encryption': network.encryption or 'Unknown',
                        'channel': network.channel or '?',
                        'attack_score': network.current_attack_score or 0
                    }
                    markers.append(marker)
                elif network.latitude and network.longitude:
                    marker = {
                        'lat': network.latitude,
                        'lon': network.longitude,
                        'bssid': network.bssid,
                        'ssid': network.ssid or '(hidden)',
                        'confidence_radius': 100.0,
                        'confidence_pct': 20.0,
                        'obs_count': 1,
                        'signal': network.current_signal or 0,
                        'encryption': network.encryption or 'Unknown',
                        'channel': network.channel or '?',
                        'attack_score': network.current_attack_score or 0
                    }
                    markers.append(marker)

            # Update stats
            self.stats_label.setText(f"Displaying {len(markers)} APs | {len(track_points)} track points")

            # Update markers via JavaScript
            self._update_markers_js(markers, track_points, current_gps)

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
                print(f"[AP-MAP] Error reading GPS location: {e}")
        return None

    def _update_markers_js(self, markers, track_points, current_gps):
        """Update markers using JavaScript without reloading page"""
        if not self.page_loaded:
            return

        markers_json = json.dumps(markers)
        track_json = json.dumps(track_points)
        gps_json = json.dumps(current_gps) if current_gps else 'null'

        js_code = f"""
        try {{
            if (typeof updateMarkers === 'function') {{
                updateMarkers({markers_json});
            }}
            if (typeof updateTrackPoints === 'function') {{
                updateTrackPoints({track_json});
            }}
            if (typeof updateCurrentGPS === 'function') {{
                updateCurrentGPS({gps_json});
            }}
        }} catch(e) {{
            console.error('Error updating markers:', e);
        }}
        """

        self.web_view.page().runJavaScript(js_code)

    def _generate_map_html(self):
        """Generate HTML for the AP map"""
        avg_lat = 39.005509
        avg_lon = -90.741686

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ width: 100%; height: 100vh; }}
        .confidence-label {{
            font-size: 11px;
            font-weight: bold;
            color: #fff;
            background-color: rgba(0, 0, 0, 0.7);
            border-radius: 3px;
            padding: 2px 5px;
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

        var apMarkersLayer = L.markerClusterGroup({{
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true
        }}).addTo(map);
        var trackLayer = L.layerGroup().addTo(map);
        var heatmapLayer = null;
        var currentGPSMarker = null;

        function updateMarkers(markers) {{
            apMarkersLayer.clearLayers();

            markers.forEach(function(marker) {{
                var color = marker.confidence_pct >= 80 ? '#00ff00' :
                           marker.confidence_pct >= 50 ? '#ffff00' :
                           marker.confidence_pct >= 30 ? '#ff8800' : '#ff0000';

                var circle = L.circle([marker.lat, marker.lon], {{
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.15,
                    radius: marker.confidence_radius,
                    weight: 1
                }});

                // Create router icon with confidence badge
                var routerIconHtml = `
                    <div style="position: relative; width: 40px; height: 40px;">
                        <svg width="32" height="32" viewBox="0 0 24 24" style="filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.5));">
                            <path fill="${{color}}" d="M12 2c5.5 0 10 4.5 10 10s-4.5 10-10 10S2 17.5 2 12 6.5 2 12 2m0 2c-4.4 0-8 3.6-8 8s3.6 8 8 8 8-3.6 8-8-3.6-8-8-8m0 3c2.8 0 5 2.2 5 5s-2.2 5-5 5-5-2.2-5-5 2.2-5 5-5m0 2c-1.7 0-3 1.3-3 3s1.3 3 3 3 3-1.3 3-3-1.3-3-3-3z"/>
                        </svg>
                        <div style="position: absolute; bottom: -8px; right: -8px; background: ${{color}}; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; border: 2px solid white;">
                            ${{marker.confidence_pct}}%
                        </div>
                    </div>
                `;

                var markerIcon = L.marker([marker.lat, marker.lon], {{
                    icon: L.divIcon({{
                        className: 'ap-router-icon',
                        html: routerIconHtml,
                        iconSize: [40, 40],
                        iconAnchor: [20, 20]
                    }})
                }});

                var popup = `
                    <div style="min-width: 200px;">
                        <h3 style="margin: 0 0 8px 0;">${{marker.ssid}}</h3>
                        <table style="width: 100%; font-size: 12px;">
                            <tr><td><b>BSSID:</b></td><td>${{marker.bssid}}</td></tr>
                            <tr><td><b>Channel:</b></td><td>${{marker.channel}}</td></tr>
                            <tr><td><b>Signal:</b></td><td>${{marker.signal}} dBm</td></tr>
                            <tr><td><b>Encryption:</b></td><td>${{marker.encryption}}</td></tr>
                            <tr><td><b>Confidence:</b></td><td style="color: ${{color}};">${{marker.confidence_pct}}%</td></tr>
                            <tr><td><b>Radius:</b></td><td>±${{Math.round(marker.confidence_radius)}}m</td></tr>
                            <tr><td><b>Observations:</b></td><td>${{marker.obs_count}}</td></tr>
                        </table>
                    </div>
                `;

                circle.bindPopup(popup);
                markerIcon.bindPopup(popup);

                apMarkersLayer.addLayer(circle);
                apMarkersLayer.addLayer(markerIcon);
            }});

            if (markers.length > 0) {{
                var bounds = markers.map(m => [m.lat, m.lon]);
                map.fitBounds(bounds, {{padding: [50, 50]}});
            }}
        }}

        function updateTrackPoints(trackPoints) {{
            trackLayer.clearLayers();
            if (heatmapLayer) {{
                map.removeLayer(heatmapLayer);
                heatmapLayer = null;
            }}

            if (trackPoints.length > 0) {{
                var trackCoords = trackPoints.map(p => [p.lat, p.lon]);
                var trackPolyline = L.polyline(trackCoords, {{
                    color: '#0088ff',
                    weight: 3,
                    opacity: 0.7
                }});
                trackLayer.addLayer(trackPolyline);

                var heatData = trackPoints.map(p => [p.lat, p.lon, 1.0]);
                heatmapLayer = L.heatLayer(heatData, {{
                    radius: 25,
                    blur: 35,
                    maxZoom: 17
                }}).addTo(map);
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
