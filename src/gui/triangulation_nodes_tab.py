"""
Triangulation Nodes Tab
Manage remote Raspberry Pi nodes for distributed WiFi triangulation
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QLineEdit, QTextEdit, QCheckBox, QSpinBox, QDoubleSpinBox,
    QMessageBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor
from datetime import datetime, timedelta
import json


class AddNodeDialog(QDialog):
    """Dialog for adding a new triangulation node"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Triangulation Node")
        self.setMinimumWidth(500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Form layout
        form_layout = QFormLayout()

        # Node ID (required)
        self.node_id_input = QLineEdit()
        self.node_id_input.setPlaceholderText("e.g., rpi-roof-01")
        form_layout.addRow("Node ID*:", self.node_id_input)

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Friendly name")
        form_layout.addRow("Name:", self.name_input)

        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(60)
        self.description_input.setPlaceholderText("Description of node location/purpose")
        form_layout.addRow("Description:", self.description_input)

        # Location
        location_group = QGroupBox("Location (Optional - for fixed nodes)")
        location_layout = QFormLayout()

        self.lat_input = QDoubleSpinBox()
        self.lat_input.setRange(-90, 90)
        self.lat_input.setDecimals(6)
        self.lat_input.setValue(0)
        location_layout.addRow("Latitude:", self.lat_input)

        self.lon_input = QDoubleSpinBox()
        self.lon_input.setRange(-180, 180)
        self.lon_input.setDecimals(6)
        self.lon_input.setValue(0)
        location_layout.addRow("Longitude:", self.lon_input)

        self.location_desc_input = QLineEdit()
        self.location_desc_input.setPlaceholderText("e.g., Roof of Building A")
        location_layout.addRow("Description:", self.location_desc_input)

        location_group.setLayout(location_layout)
        form_layout.addRow(location_group)

        # Configuration
        config_group = QGroupBox("Configuration")
        config_layout = QFormLayout()

        self.is_mobile_check = QCheckBox("Mobile node (has GPS)")
        config_layout.addRow("Type:", self.is_mobile_check)

        self.scan_interval_input = QSpinBox()
        self.scan_interval_input.setRange(10, 3600)
        self.scan_interval_input.setValue(60)
        self.scan_interval_input.setSuffix(" seconds")
        config_layout.addRow("Scan Interval:", self.scan_interval_input)

        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        config_layout.addRow("Status:", self.enabled_check)

        config_group.setLayout(config_layout)
        form_layout.addRow(config_group)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add Node")
        add_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(add_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def get_node_data(self):
        """Get the entered node data"""
        return {
            'node_id': self.node_id_input.text().strip(),
            'name': self.name_input.text().strip() or None,
            'description': self.description_input.toPlainText().strip() or None,
            'latitude': self.lat_input.value() if self.lat_input.value() != 0 else None,
            'longitude': self.lon_input.value() if self.lon_input.value() != 0 else None,
            'location_description': self.location_desc_input.text().strip() or None,
            'is_mobile': self.is_mobile_check.isChecked(),
            'scan_interval': self.scan_interval_input.value(),
            'enabled': self.enabled_check.isChecked()
        }


class TriangulationNodesTab(QWidget):
    """Tab for managing triangulation nodes"""

    def __init__(self):
        super().__init__()
        self.init_ui()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_nodes)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header with title and controls
        header_layout = QHBoxLayout()

        title_label = QLabel("<h3>📐 Triangulation Nodes</h3>")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_nodes)
        header_layout.addWidget(refresh_btn)

        # Add node button
        add_btn = QPushButton("➕ Add Node")
        add_btn.clicked.connect(self.add_node)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Stats bar
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Loading...")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Nodes table
        self.nodes_table = QTableWidget()
        self.nodes_table.setColumnCount(10)
        self.nodes_table.setHorizontalHeaderLabels([
            "Node ID", "Name", "Status", "Location", "Type", "Last Seen",
            "Observations", "Networks", "Uptime", "Actions"
        ])

        # Set column widths
        header = self.nodes_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)

        self.nodes_table.setAlternatingRowColors(True)
        self.nodes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.nodes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.nodes_table)

        # Info label
        info_label = QLabel(
            "ℹ️ Triangulation nodes are remote scanners (e.g., Raspberry Pis) that observe WiFi networks\n"
            "and report signal strength data for accurate AP location triangulation."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        layout.addWidget(info_label)

        # Initial load
        self.refresh_nodes()

    def refresh_nodes(self):
        """Refresh the nodes list from database"""
        try:
            from src.database.models import get_session, TriangulationNode

            session = get_session()
            nodes = session.query(TriangulationNode).order_by(TriangulationNode.created_at.desc()).all()

            # Update stats
            total_nodes = len(nodes)
            online_nodes = sum(1 for n in nodes if n.status == 'online')
            total_observations = sum(n.total_observations for n in nodes)
            self.stats_label.setText(
                f"Total Nodes: {total_nodes} | Online: {online_nodes} | "
                f"Total Observations: {total_observations:,}"
            )

            # Update table
            self.nodes_table.setRowCount(len(nodes))

            for row, node in enumerate(nodes):
                # Node ID
                self.nodes_table.setItem(row, 0, QTableWidgetItem(node.node_id))

                # Name
                self.nodes_table.setItem(row, 1, QTableWidgetItem(node.name or "-"))

                # Status
                status_item = QTableWidgetItem(node.status.upper())
                if node.status == 'online':
                    status_item.setForeground(QColor(0, 200, 0))
                elif node.status == 'error':
                    status_item.setForeground(QColor(255, 0, 0))
                else:
                    status_item.setForeground(QColor(128, 128, 128))
                self.nodes_table.setItem(row, 2, status_item)

                # Location
                if node.latitude and node.longitude:
                    loc_str = f"{node.latitude:.4f}, {node.longitude:.4f}"
                    if node.location_description:
                        loc_str += f" ({node.location_description})"
                else:
                    loc_str = node.location_description or "-"
                self.nodes_table.setItem(row, 3, QTableWidgetItem(loc_str))

                # Type
                node_type = "Mobile" if node.is_mobile else "Fixed"
                self.nodes_table.setItem(row, 4, QTableWidgetItem(node_type))

                # Last Seen
                if node.last_seen:
                    time_diff = datetime.utcnow() - node.last_seen
                    if time_diff < timedelta(minutes=5):
                        last_seen_str = "Just now"
                    elif time_diff < timedelta(hours=1):
                        last_seen_str = f"{int(time_diff.total_seconds() / 60)}m ago"
                    elif time_diff < timedelta(days=1):
                        last_seen_str = f"{int(time_diff.total_seconds() / 3600)}h ago"
                    else:
                        last_seen_str = f"{int(time_diff.days)}d ago"
                else:
                    last_seen_str = "Never"
                self.nodes_table.setItem(row, 5, QTableWidgetItem(last_seen_str))

                # Observations
                self.nodes_table.setItem(row, 6, QTableWidgetItem(f"{node.total_observations:,}"))

                # Networks
                self.nodes_table.setItem(row, 7, QTableWidgetItem(f"{node.total_networks_observed:,}"))

                # Uptime
                uptime_str = self._format_uptime(node.uptime_seconds)
                self.nodes_table.setItem(row, 8, QTableWidgetItem(uptime_str))

                # Actions
                actions_btn = QPushButton("⚙️")
                actions_btn.setMaximumWidth(40)
                actions_btn.clicked.connect(lambda checked, n=node: self.show_node_actions(n))
                self.nodes_table.setCellWidget(row, 9, actions_btn)

            session.close()

        except Exception as e:
            print(f"[TriangulationNodesTab] Error refreshing nodes: {e}")
            import traceback
            traceback.print_exc()

    def _format_uptime(self, seconds):
        """Format uptime in seconds to human-readable string"""
        if seconds == 0:
            return "-"

        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60

        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def add_node(self):
        """Show dialog to add a new node"""
        dialog = AddNodeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            node_data = dialog.get_node_data()

            if not node_data['node_id']:
                QMessageBox.warning(self, "Invalid Input", "Node ID is required.")
                return

            try:
                from src.database.models import get_session, TriangulationNode
                import secrets

                session = get_session()

                # Check if node_id already exists
                existing = session.query(TriangulationNode).filter_by(node_id=node_data['node_id']).first()
                if existing:
                    QMessageBox.warning(self, "Duplicate Node ID",
                                      f"A node with ID '{node_data['node_id']}' already exists.")
                    session.close()
                    return

                # Generate API key for node
                api_key = secrets.token_hex(32)

                # Create new node
                new_node = TriangulationNode(
                    node_id=node_data['node_id'],
                    name=node_data['name'],
                    description=node_data['description'],
                    latitude=node_data['latitude'],
                    longitude=node_data['longitude'],
                    location_description=node_data['location_description'],
                    is_mobile=node_data['is_mobile'],
                    scan_interval=node_data['scan_interval'],
                    enabled=node_data['enabled'],
                    api_key=api_key,
                    status='offline'
                )

                session.add(new_node)
                session.commit()

                # Show API key to user
                QMessageBox.information(
                    self,
                    "Node Added Successfully",
                    f"Node '{node_data['node_id']}' has been added.\n\n"
                    f"API Key (save this, it won't be shown again):\n{api_key}\n\n"
                    f"Configure your Raspberry Pi with this API key to authenticate."
                )

                session.close()
                self.refresh_nodes()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add node:\n{e}")
                print(f"[TriangulationNodesTab] Error adding node: {e}")
                import traceback
                traceback.print_exc()

    def show_node_actions(self, node):
        """Show actions menu for a node"""
        # TODO: Implement node actions (view details, edit, delete, view observations, etc.)
        QMessageBox.information(
            self,
            "Node Actions",
            f"Actions for node: {node.name or node.node_id}\n\n"
            f"Status: {node.status}\n"
            f"Last Seen: {node.last_seen}\n"
            f"Observations: {node.total_observations}\n\n"
            f"(Full node management coming soon)"
        )
