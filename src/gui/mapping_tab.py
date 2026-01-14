"""
Mapping Tab
Displays WiFi access points on a map with triangulated locations and confidence visualization
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox, QCheckBox
)
from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from typing import Optional
import json


class MappingTab(QWidget):
    """Tab for displaying WiFi APs on a map with confidence visualization"""

    def __init__(self):
        super().__init__()
        self.map_initialized = False
        self.page_loaded = False
        self.init_ui()

        # Auto-refresh timer - faster updates
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_markers)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds for faster map updates

    def _log_click(self, action):
        """Log user click events for debugging"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [MAP-CLICK] {action}")
        return False  # Return False so it can be used in lambda with 'or'

    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for maximum space
        layout.setSpacing(2)  # Minimal spacing
        self.setLayout(layout)

        # Controls at top (compact)
        controls_layout = QHBoxLayout()

        # Refresh button
        self.refresh_btn = QPushButton("Refresh Map")
        self.refresh_btn.clicked.connect(lambda: self._log_click("Refresh Map") or self.refresh_map())
        controls_layout.addWidget(self.refresh_btn)

        # Minimum observations filter
        controls_layout.addWidget(QLabel("Min Observations:"))
        self.min_obs_spin = QSpinBox()
        self.min_obs_spin.setMinimum(1)
        self.min_obs_spin.setMaximum(100)
        self.min_obs_spin.setValue(3)
        self.min_obs_spin.valueChanged.connect(lambda: self._log_click(f"Min Obs: {self.min_obs_spin.value()}") or self.refresh_map())
        controls_layout.addWidget(self.min_obs_spin)

        # Show all networks checkbox
        self.show_all_check = QCheckBox("Show All Networks")
        self.show_all_check.setChecked(False)
        self.show_all_check.toggled.connect(lambda: self._log_click(f"Show All: {self.show_all_check.isChecked()}") or self.refresh_map())
        controls_layout.addWidget(self.show_all_check)

        # Snap to location buttons
        self.snap_data_btn = QPushButton("📍 Snap to Data")
        self.snap_data_btn.setToolTip("Zoom to fit all visible APs")
        self.snap_data_btn.clicked.connect(self._snap_to_data)
        controls_layout.addWidget(self.snap_data_btn)

        self.snap_gps_btn = QPushButton("🎯 Snap to GPS")
        self.snap_gps_btn.setToolTip("Center on current GPS location")
        self.snap_gps_btn.clicked.connect(self._snap_to_gps)
        controls_layout.addWidget(self.snap_gps_btn)

        # Stats label
        self.stats_label = QLabel("No APs displayed")
        controls_layout.addWidget(self.stats_label)
        controls_layout.addStretch()

        layout.addLayout(controls_layout, 0)  # Don't stretch controls

        # Web view for map - give it all available space
        self.web_view = QWebEngineView()
        self.web_view.setMinimumHeight(400)  # Ensure minimum size
        layout.addWidget(self.web_view, 1)  # Stretch factor 1 = fill remaining space

        # Load initial map (only once)
        self.load_initial_map()

    def load_initial_map(self):
        """Load map HTML once (no flickering)"""
        html = self._generate_map_html()
        # Connect to loadFinished signal
        self.web_view.loadFinished.connect(self._on_page_loaded)
        self.web_view.setHtml(html)
        self.map_initialized = True

    def _on_page_loaded(self, ok):
        """Called when page finishes loading"""
        if ok:
            self.page_loaded = True
            # Initial data load after page is ready
            QTimer.singleShot(500, self.update_markers)

    def refresh_map(self):
        """Force full map refresh (for button click)"""
        if not self.map_initialized:
            self.load_initial_map()
        else:
            self.update_markers()

    def _snap_to_data(self):
        """Zoom map to fit all visible data - user triggered only"""
        if not self.page_loaded:
            return
        js_code = """
        try {
            if (typeof apMarkersLayer !== 'undefined') {
                var bounds = apMarkersLayer.getBounds();
                if (bounds.isValid()) {
                    map.fitBounds(bounds, {padding: [50, 50], maxZoom: 16});
                }
            }
        } catch(e) { console.error('Snap to data error:', e); }
        """
        self.web_view.page().runJavaScript(js_code)

    def _snap_to_gps(self):
        """Center map on current GPS location - user triggered only"""
        if not self.page_loaded:
            return
        gps = self._get_current_gps_location()
        if gps and gps.get('lat') and gps.get('lon'):
            js_code = f"""
            try {{
                map.setView([{gps['lat']}, {gps['lon']}], 17);
            }} catch(e) {{ console.error('Snap to GPS error:', e); }}
            """
            self.web_view.page().runJavaScript(js_code)

    def update_markers(self):
        """Update markers incrementally without reloading HTML"""
        if not self.map_initialized or not self.page_loaded:
            return

        from ..database.models import get_session, Network, NetworkObservation
        from ..services.triangulation_service import TriangulationService
        from sqlalchemy import func

        session = get_session()
        try:
            # Get current GPS location from status file
            current_gps = self._get_current_gps_location()

            # Get user location track - optimized to prevent loading 30k+ points
            # Only load observations from last 2 hours or decimated older points
            from datetime import datetime, timedelta

            two_hours_ago = datetime.utcnow() - timedelta(hours=2)

            # Get recent observations with network info for colored display
            recent_obs = session.query(NetworkObservation, Network).join(
                Network, NetworkObservation.network_id == Network.id
            ).filter(
                NetworkObservation.latitude.isnot(None),
                NetworkObservation.longitude.isnot(None),
                NetworkObservation.timestamp >= two_hours_ago
            ).order_by(NetworkObservation.timestamp.asc()).all()

            # Get older observations - decimated
            older_obs = session.query(NetworkObservation, Network).join(
                Network, NetworkObservation.network_id == Network.id
            ).filter(
                NetworkObservation.latitude.isnot(None),
                NetworkObservation.longitude.isnot(None),
                NetworkObservation.timestamp < two_hours_ago
            ).order_by(NetworkObservation.timestamp.asc()).all()

            # Decimate older observations - keep every 10th point
            decimated_older = older_obs[::10] if len(older_obs) > 100 else older_obs

            # Combine: decimated old + full recent
            all_obs = decimated_older + recent_obs

            # Build color map for networks (consistent colors per network)
            network_colors = {}
            color_palette = [
                '#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00',
                '#ffff33', '#a65628', '#f781bf', '#999999', '#66c2a5',
                '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f'
            ]

            track_points = []
            for obs, network in all_obs:
                # Assign color to network if not already assigned
                if network.id not in network_colors:
                    network_colors[network.id] = color_palette[len(network_colors) % len(color_palette)]

                track_points.append({
                    'lat': obs.latitude,
                    'lon': obs.longitude,
                    'timestamp': obs.timestamp.isoformat() if obs.timestamp else None,
                    'gps_source': obs.gps_source or 'unknown',
                    'network_id': network.id,
                    'bssid': network.bssid,
                    'ssid': network.ssid or '(hidden)',
                    'color': network_colors[network.id]
                })
            # Get all networks with GPS data
            if self.show_all_check.isChecked():
                # Show all networks that have at least one location
                networks = session.query(Network).filter(
                    Network.latitude.isnot(None),
                    Network.longitude.isnot(None)
                ).all()
            else:
                # Only show networks with enough observations for triangulation
                from ..database.models import NetworkObservation

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
                # Calculate confidence if we have observations
                result = TriangulationService.calculate_ap_location(network.id, min_observations=1)

                if result:
                    est_lat, est_lon, confidence_radius, obs_count = result

                    # Calculate confidence percentage (inverse of radius, scaled)
                    # 0m radius = 100% confidence, 100m radius = 50%, 1000m+ = 0%
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
                    # Single observation, low confidence
                    marker = {
                        'lat': network.latitude,
                        'lon': network.longitude,
                        'bssid': network.bssid,
                        'ssid': network.ssid or '(hidden)',
                        'confidence_radius': 100.0,  # Default 100m
                        'confidence_pct': 20.0,  # Low confidence
                        'obs_count': 1,
                        'signal': network.current_signal or 0,
                        'encryption': network.encryption or 'Unknown',
                        'channel': network.channel or '?',
                        'attack_score': network.current_attack_score or 0
                    }
                    markers.append(marker)

            # Update stats
            self.stats_label.setText(f"Displaying {len(markers)} APs | {len(track_points)} track points")

            # Update markers via JavaScript (no page reload)
            self._update_markers_js(markers, track_points, current_gps)

        finally:
            session.close()

    def _get_current_gps_location(self):
        """Get current GPS location from status file"""
        import os
        try:
            if not os.path.exists('/tmp/gattrose-status.json'):
                # Don't spam errors if orchestrator isn't running yet
                return None

            import json
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
            # Only print error if file exists but couldn't be read
            if os.path.exists('/tmp/gattrose-status.json'):
                print(f"[MAP] Error reading GPS location: {e}")
        return None

    def _update_markers_js(self, markers, track_points, current_gps):
        """Update markers using JavaScript without reloading page"""
        if not self.page_loaded:
            return

        # Convert data to JSON
        markers_json = json.dumps(markers)
        track_json = json.dumps(track_points)
        gps_json = json.dumps(current_gps) if current_gps else 'null'

        # JavaScript to update markers wrapped in try-catch
        js_code = f"""
        try {{
            // Update AP markers
            if (typeof updateMarkers === 'function') {{
                updateMarkers({markers_json});
            }}

            // Update track points
            if (typeof updateTrackPoints === 'function') {{
                updateTrackPoints({track_json});
            }}

            // Update current GPS location
            if (typeof updateCurrentGPS === 'function') {{
                updateCurrentGPS({gps_json});
            }}
        }} catch(e) {{
            console.error('Error updating markers:', e);
        }}
        """

        # Execute JavaScript in web view
        self.web_view.page().runJavaScript(js_code)

    def _generate_map_html(self):
        """Generate HTML for the map (initial empty map)"""
        # Default center (will be updated by GPS)
        # Use provided GPS coordinates
        avg_lat = 39.005509
        avg_lon = -90.741686

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <!-- Leaflet Heatmap Plugin -->
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>

    <!-- Leaflet MarkerCluster Plugin -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
        #map {{
            width: 100%;
            height: 100vh;
        }}
        .confidence-label {{
            font-size: 11px;
            font-weight: bold;
            color: #fff;
            background-color: rgba(0, 0, 0, 0.7);
            border-radius: 3px;
            padding: 2px 5px;
            white-space: nowrap;
        }}
        .ap-marker {{
            cursor: pointer;
        }}
        .track-point {{
            cursor: pointer;
        }}
        /* Custom cluster styling */
        .marker-cluster-small {{
            background-color: rgba(181, 226, 140, 0.6);
        }}
        .marker-cluster-small div {{
            background-color: rgba(110, 204, 57, 0.6);
        }}
        .marker-cluster-medium {{
            background-color: rgba(241, 211, 87, 0.6);
        }}
        .marker-cluster-medium div {{
            background-color: rgba(240, 194, 12, 0.6);
        }}
        .marker-cluster-large {{
            background-color: rgba(253, 156, 115, 0.6);
        }}
        .marker-cluster-large div {{
            background-color: rgba(241, 128, 23, 0.6);
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        // Initialize map
        var map = L.map('map').setView([{avg_lat}, {avg_lon}], 13);

        // Add Satellite imagery tiles (Esri World Imagery)
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 19,
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        }}).addTo(map);

        // Layer groups for dynamic updates
        var apMarkersLayer = L.markerClusterGroup({{
            maxClusterRadius: 50,  // Cluster networks within 50 pixels
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: false,  // Disabled - no auto zoom
            animate: false,  // Disable animations that might cause issues
            iconCreateFunction: function(cluster) {{
                var childCount = cluster.getChildCount();
                var c = ' marker-cluster-';
                if (childCount < 5) {{
                    c += 'small';
                }} else if (childCount < 15) {{
                    c += 'medium';
                }} else {{
                    c += 'large';
                }}
                return new L.DivIcon({{
                    html: '<div><span>' + childCount + ' APs</span></div>',
                    className: 'marker-cluster' + c,
                    iconSize: new L.Point(40, 40)
                }});
            }}
        }}).addTo(map);
        var trackLayer = L.layerGroup().addTo(map);
        var heatmapLayer = null;
        var currentGPSMarker = null;

        // Helper function to calculate offset for overlapping markers
        function calculateOffset(index, total, radiusMeters) {{
            if (total === 1) return {{ lat: 0, lon: 0 }};

            // Use smaller radius for spacing (30% of confidence radius)
            var spacingRadius = radiusMeters * 0.3;

            // Arrange in a circle around the original point
            var angle = (2 * Math.PI * index) / total;

            // Convert meters to degrees (approximate at mid-latitudes)
            var metersPerDegreeLat = 111320;
            var metersPerDegreeLon = 111320; // Will adjust by latitude

            var offsetMetersLat = Math.sin(angle) * spacingRadius;
            var offsetMetersLon = Math.cos(angle) * spacingRadius;

            return {{
                lat: offsetMetersLat / metersPerDegreeLat,
                lon: offsetMetersLon / metersPerDegreeLon
            }};
        }}

        // Function to update AP markers (called from Qt)
        function updateMarkers(markers) {{
            // Clear existing markers
            apMarkersLayer.clearLayers();

            // Group markers by exact location (to detect overlaps)
            var locationGroups = {{}};
            markers.forEach(function(marker) {{
                var key = marker.lat.toFixed(6) + ',' + marker.lon.toFixed(6);
                if (!locationGroups[key]) {{
                    locationGroups[key] = [];
                }}
                locationGroups[key].push(marker);
            }});

            // Process each location group
            Object.keys(locationGroups).forEach(function(locationKey) {{
                var group = locationGroups[locationKey];
                var groupSize = group.length;

                // Apply spacing if multiple networks at same location
                group.forEach(function(marker, index) {{
                    var displayLat = marker.lat;
                    var displayLon = marker.lon;

                    // Apply offset for overlapping markers
                    if (groupSize > 1) {{
                        var offset = calculateOffset(index, groupSize, marker.confidence_radius);
                        displayLat += offset.lat;
                        displayLon += offset.lon;
                    }}

                    // Determine color based on confidence
                    var color = '#ff0000';  // Red = low confidence
                    if (marker.confidence_pct >= 80) {{
                        color = '#00ff00';  // Green = high confidence
                    }} else if (marker.confidence_pct >= 50) {{
                        color = '#ffff00';  // Yellow = medium confidence
                    }} else if (marker.confidence_pct >= 30) {{
                        color = '#ff8800';  // Orange = low-medium confidence
                    }}

                    // Create confidence circle (clickable) - at original location
                    var circle = L.circle([marker.lat, marker.lon], {{
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.15,
                        radius: marker.confidence_radius,
                        weight: 1,
                        className: 'ap-marker'
                    }});

                    // Create marker label - at offset location if needed
                    var labelText = marker.confidence_pct + '%';
                    if (groupSize > 1) {{
                        labelText = marker.confidence_pct + '% (' + (index + 1) + '/' + groupSize + ')';
                    }}

                    var markerIcon = L.marker([displayLat, displayLon], {{
                        icon: L.divIcon({{
                            className: 'confidence-label ap-marker',
                            html: labelText,
                            iconSize: [70, 20],
                            iconAnchor: [35, 10]
                        }}),
                        title: marker.ssid + ' - ' + marker.bssid
                    }});

                    // Enhanced popup with details
                    var popupContent = `
                        <div style="min-width: 200px;">
                            <h3 style="margin: 0 0 8px 0;">${{marker.ssid}}</h3>
                            <table style="width: 100%; font-size: 12px;">
                                <tr><td><b>BSSID:</b></td><td>${{marker.bssid}}</td></tr>
                                <tr><td><b>Channel:</b></td><td>${{marker.channel}}</td></tr>
                                <tr><td><b>Signal:</b></td><td>${{marker.signal}} dBm</td></tr>
                                <tr><td><b>Encryption:</b></td><td>${{marker.encryption}}</td></tr>
                                <tr><td colspan="2"><hr style="margin: 4px 0;"></td></tr>
                                <tr><td><b>Confidence:</b></td><td style="color: ${{color}}; font-weight: bold;">${{marker.confidence_pct}}%</td></tr>
                                <tr><td><b>Radius:</b></td><td>±${{Math.round(marker.confidence_radius)}}m</td></tr>
                                <tr><td><b>Observations:</b></td><td>${{marker.obs_count}}</td></tr>
                                <tr><td><b>Attack Score:</b></td><td>${{marker.attack_score}}</td></tr>
                                <tr><td colspan="2"><hr style="margin: 4px 0;"></td></tr>
                                <tr><td><b>Location:</b></td><td>${{marker.lat.toFixed(6)}}, ${{marker.lon.toFixed(6)}}</td></tr>
                            </table>
                        </div>
                    `;

                    circle.bindPopup(popupContent);
                    markerIcon.bindPopup(popupContent);

                    // Make clickable - auto open popup on click
                    circle.on('click', function() {{
                        this.openPopup();
                    }});
                    markerIcon.on('click', function() {{
                        this.openPopup();
                    }});

                    // Add to cluster group (cluster plugin handles the clustering)
                    apMarkersLayer.addLayer(circle);
                    apMarkersLayer.addLayer(markerIcon);
                }});
            }});

            // NO auto-zoom - map is fully freeform
            // User can click "Snap to Data" or "Snap to GPS" buttons to center
        }}

        // Function to update track points (called from Qt)
        function updateTrackPoints(trackPoints) {{
            // Clear existing track
            trackLayer.clearLayers();
            if (heatmapLayer) {{
                map.removeLayer(heatmapLayer);
                heatmapLayer = null;
            }}

            if (trackPoints.length > 0) {{
                // Group points by network for per-network heatmaps
                var networkGroups = {{}};
                trackPoints.forEach(function(point) {{
                    var netId = point.network_id || 'unknown';
                    if (!networkGroups[netId]) {{
                        networkGroups[netId] = {{
                            points: [],
                            color: point.color || '#0088ff',
                            ssid: point.ssid || 'Unknown',
                            bssid: point.bssid || ''
                        }};
                    }}
                    networkGroups[netId].points.push(point);
                }});

                // Create colored markers for each network's observations
                Object.keys(networkGroups).forEach(function(netId) {{
                    var group = networkGroups[netId];
                    group.points.forEach(function(point) {{
                        var trackMarker = L.circleMarker([point.lat, point.lon], {{
                            radius: 4,
                            fillColor: group.color,
                            color: '#fff',
                            weight: 1,
                            opacity: 0.9,
                            fillOpacity: 0.7
                        }});

                        trackMarker.bindPopup(`
                            <b>${{group.ssid}}</b><br>
                            BSSID: ${{group.bssid}}<br>
                            Time: ${{point.timestamp || 'Unknown'}}<br>
                            GPS: ${{point.gps_source}}<br>
                            Lat: ${{point.lat.toFixed(6)}}<br>
                            Lon: ${{point.lon.toFixed(6)}}
                        `);

                        trackLayer.addLayer(trackMarker);
                    }});
                }});

                // Optional: Add legend showing network colors (first 10)
                var legendHtml = '<div style="background:rgba(0,0,0,0.7);padding:5px;border-radius:3px;color:#fff;font-size:10px;">';
                legendHtml += '<b>Networks:</b><br>';
                var count = 0;
                Object.keys(networkGroups).forEach(function(netId) {{
                    if (count < 10) {{
                        var g = networkGroups[netId];
                        legendHtml += '<span style="color:' + g.color + '">●</span> ' + g.ssid + '<br>';
                        count++;
                    }}
                }});
                if (Object.keys(networkGroups).length > 10) {{
                    legendHtml += '... and ' + (Object.keys(networkGroups).length - 10) + ' more';
                }}
                legendHtml += '</div>';
            }}
        }}

        // Function to update current GPS location (called from Qt)
        function updateCurrentGPS(gpsData) {{
            // Remove existing GPS marker
            if (currentGPSMarker) {{
                map.removeLayer(currentGPSMarker);
                currentGPSMarker = null;
            }}

            if (gpsData && gpsData.lat && gpsData.lon) {{
                // Create GPS marker with accuracy circle
                var accuracyCircle = L.circle([gpsData.lat, gpsData.lon], {{
                    color: '#4ecdc4',
                    fillColor: '#4ecdc4',
                    fillOpacity: 0.1,
                    radius: gpsData.accuracy || 10,
                    weight: 2
                }});

                var gpsMarker = L.marker([gpsData.lat, gpsData.lon], {{
                    icon: L.divIcon({{
                        className: 'gps-marker',
                        html: '📍',
                        iconSize: [30, 30],
                        iconAnchor: [15, 15]
                    }}),
                    title: 'Current GPS Location'
                }});

                // Popup for GPS marker
                var sourceIcon = '📍';
                if (gpsData.source === 'phone-usb' || gpsData.source === 'phone-bt') {{
                    sourceIcon = '📱';
                }} else if (gpsData.source === 'geoip') {{
                    sourceIcon = '🌍';
                }}

                gpsMarker.bindPopup(`
                    <b>${{sourceIcon}} Current GPS Location</b><br>
                    Source: ${{gpsData.source}}<br>
                    Fix: ${{gpsData.fix_quality}}<br>
                    Accuracy: ±${{Math.round(gpsData.accuracy)}}m<br>
                    Lat: ${{gpsData.lat.toFixed(6)}}<br>
                    Lon: ${{gpsData.lon.toFixed(6)}}
                `);

                // Add to map as a feature group
                currentGPSMarker = L.featureGroup([accuracyCircle, gpsMarker]).addTo(map);
            }}
        }}
    </script>
</body>
</html>
        """
        return html
