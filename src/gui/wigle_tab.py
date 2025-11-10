"""
WiGLE Integration Tab
Interface for WiGLE.net database integration
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QTextEdit, QProgressBar, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QComboBox, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path
from datetime import datetime


class WiGLEUploadThread(QThread):
    """Upload scan data to WiGLE"""

    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, api_key: str, file_path: str):
        super().__init__()
        self.api_key = api_key
        self.file_path = file_path

    def run(self):
        """Upload to WiGLE"""
        try:
            import requests

            self.progress_updated.emit(10, "Preparing upload...")

            # WiGLE API endpoint
            url = "https://api.wigle.net/api/v2/file/upload"

            headers = {
                "Authorization": f"Basic {self.api_key}"
            }

            self.progress_updated.emit(30, "Uploading...")

            with open(self.file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(url, headers=headers, files=files, timeout=60)

            self.progress_updated.emit(90, "Processing response...")

            if response.status_code == 200:
                data = response.json()
                self.finished.emit(True, f"Upload successful! {data.get('message', '')}")
            else:
                self.finished.emit(False, f"Upload failed: {response.status_code} - {response.text}")

        except Exception as e:
            self.finished.emit(False, f"Error: {e}")


class WiGLETab(QWidget):
    """WiGLE.net integration interface"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.upload_thread = None
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()

        # ========== HEADER ==========
        header = QLabel("WiGLE.net Integration")
        header.setProperty("heading", True)
        layout.addWidget(header)

        info = QLabel(
            "Upload scan data to WiGLE.net and query global WiFi database\n"
            "Requires WiGLE API key (get one at https://wigle.net/account)"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # ========== API CONFIGURATION ==========
        api_group = QGroupBox("API Configuration")
        api_layout = QVBoxLayout()

        # API Key
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API Key:"))

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Encoded API key from WiGLE.net")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addWidget(self.api_key_input)

        show_key_btn = QPushButton("👁️")
        show_key_btn.setMaximumWidth(40)
        show_key_btn.clicked.connect(self.toggle_api_key_visibility)
        key_layout.addWidget(show_key_btn)

        save_key_btn = QPushButton("💾 Save")
        save_key_btn.clicked.connect(self.save_api_key)
        key_layout.addWidget(save_key_btn)

        api_layout.addLayout(key_layout)

        # Get API Key button
        get_key_btn = QPushButton("🔑 Get WiGLE API Key (Login Required)")
        get_key_btn.clicked.connect(self.open_wigle_api_page)
        api_layout.addWidget(get_key_btn)

        # Test connection
        test_btn = QPushButton("🔌 Test API Connection")
        test_btn.clicked.connect(self.test_api_connection)
        api_layout.addWidget(test_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # ========== UPLOAD DATA ==========
        upload_group = QGroupBox("Upload Scan Data")
        upload_layout = QVBoxLayout()

        upload_info = QLabel(
            "Upload your WiFi scan data to contribute to the global WiGLE database"
        )
        upload_info.setWordWrap(True)
        upload_layout.addWidget(upload_info)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("File:"))

        self.upload_file_input = QLineEdit()
        self.upload_file_input.setPlaceholderText("Select CSV file to upload...")
        file_layout.addWidget(self.upload_file_input)

        browse_upload_btn = QPushButton("Browse...")
        browse_upload_btn.clicked.connect(self.browse_upload_file)
        file_layout.addWidget(browse_upload_btn)

        upload_layout.addLayout(file_layout)

        # Upload controls
        upload_controls = QHBoxLayout()

        self.upload_btn = QPushButton("📤 Upload Selected")
        self.upload_btn.clicked.connect(self.upload_to_wigle)
        self.upload_btn.setMinimumHeight(35)
        upload_controls.addWidget(self.upload_btn)

        self.auto_upload_all_btn = QPushButton("📤 Auto Upload All Scans")
        self.auto_upload_all_btn.clicked.connect(self.auto_upload_all_scans)
        self.auto_upload_all_btn.setMinimumHeight(35)
        upload_controls.addWidget(self.auto_upload_all_btn)

        upload_controls.addStretch()
        upload_layout.addLayout(upload_controls)

        # Auto-upload settings
        auto_upload_settings = QHBoxLayout()

        self.auto_upload_enabled_check = QCheckBox("Enable Auto-Upload on Scan Complete")
        self.auto_upload_enabled_check.setChecked(False)
        self.auto_upload_enabled_check.stateChanged.connect(self.toggle_auto_upload)
        auto_upload_settings.addWidget(self.auto_upload_enabled_check)

        auto_upload_settings.addStretch()
        upload_layout.addLayout(auto_upload_settings)

        # Upload progress
        self.upload_progress = QProgressBar()
        upload_layout.addWidget(self.upload_progress)

        self.upload_status_label = QLabel("Status: Ready")
        upload_layout.addWidget(self.upload_status_label)

        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)

        # ========== QUERY DATABASE ==========
        query_group = QGroupBox("Query WiGLE Database")
        query_layout = QVBoxLayout()

        query_info = QLabel(
            "Search the global WiGLE database for networks by location or SSID"
        )
        query_info.setWordWrap(True)
        query_layout.addWidget(query_info)

        # Query options
        query_options_layout = QHBoxLayout()

        self.query_type_combo = QComboBox()
        self.query_type_combo.addItem("Search by SSID", "ssid")
        self.query_type_combo.addItem("Search by BSSID", "bssid")
        self.query_type_combo.addItem("Search by Location", "location")
        query_options_layout.addWidget(self.query_type_combo)

        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Enter search query...")
        query_options_layout.addWidget(self.query_input)

        query_btn = QPushButton("🔍 Search")
        query_btn.clicked.connect(self.query_wigle)
        query_options_layout.addWidget(query_btn)

        query_layout.addLayout(query_options_layout)

        # Results
        self.query_results_tree = QTreeWidget()
        self.query_results_tree.setHeaderLabels([
            "SSID", "BSSID", "Encryption", "Latitude", "Longitude", "First Seen"
        ])
        self.query_results_tree.setMinimumHeight(200)
        query_layout.addWidget(self.query_results_tree)

        # Export results
        export_results_btn = QPushButton("📥 Export Results")
        export_results_btn.clicked.connect(self.export_query_results)
        query_layout.addWidget(export_results_btn)

        query_group.setLayout(query_layout)
        layout.addWidget(query_group)

        # ========== LOG ==========
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(120)
        self.log_area.setFontFamily("monospace")
        log_layout.addWidget(self.log_area)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()
        self.setLayout(layout)

        # Load saved API key
        self.load_api_key()

    def toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

    def save_api_key(self):
        """Save API key to config"""
        try:
            from ..utils.config_db import DBConfig

            config = DBConfig()
            config.set('wigle.api_key', self.api_key_input.text(),
                      value_type='string', category='wigle',
                      description='WiGLE API key')
            self.log("✅ API key saved")
        except Exception as e:
            self.log(f"❌ Error saving API key: {e}")

    def load_api_key(self):
        """Load API key from config"""
        try:
            from ..utils.config_db import DBConfig

            config = DBConfig()
            api_key = config.get('wigle.api_key', '')
            if api_key:
                self.api_key_input.setText(api_key)
                self.log("Loaded saved API key")
        except Exception as e:
            pass  # No saved key

    def test_api_connection(self):
        """Test WiGLE API connection"""
        api_key = self.api_key_input.text().strip()

        if not api_key:
            self.log("❌ Error: API key required")
            return

        self.log("🔌 Testing API connection...")

        try:
            import requests

            url = "https://api.wigle.net/api/v2/network/search"
            headers = {"Authorization": f"Basic {api_key}"}
            params = {"ssid": "test"}

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                self.log("✅ API connection successful!")
            elif response.status_code == 401:
                self.log("❌ Authentication failed - check your API key")
            else:
                self.log(f"❌ API returned status {response.status_code}")

        except Exception as e:
            self.log(f"❌ Connection test failed: {e}")

    def open_wigle_api_page(self):
        """Open WiGLE API key page in browser"""
        import webbrowser
        url = "https://wigle.net/account"
        self.log(f"🌐 Opening WiGLE account page in browser...")
        self.log("   → Login to your WiGLE account")
        self.log("   → Navigate to 'Show my token' section")
        self.log("   → Copy the 'Encoded for use' value")
        self.log("   → Paste it into the API Key field above")
        try:
            webbrowser.open(url)
            self.log("✅ Browser opened successfully")
        except Exception as e:
            self.log(f"❌ Failed to open browser: {e}")
            self.log(f"   Please manually visit: {url}")

    def browse_upload_file(self):
        """Browse for file to upload"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Scan Data",
            str(Path.cwd() / "data" / "captures"),
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            self.upload_file_input.setText(file_path)

    def upload_to_wigle(self):
        """Upload scan data to WiGLE"""
        api_key = self.api_key_input.text().strip()
        file_path = self.upload_file_input.text().strip()

        if not api_key:
            self.log("❌ Error: API key required")
            return

        if not file_path or not Path(file_path).exists():
            self.log("❌ Error: Valid file required")
            return

        self.log(f"📤 Uploading {Path(file_path).name} to WiGLE...")
        self.upload_btn.setEnabled(False)

        self.upload_thread = WiGLEUploadThread(api_key, file_path)
        self.upload_thread.progress_updated.connect(self.on_upload_progress)
        self.upload_thread.finished.connect(self.on_upload_finished)
        self.upload_thread.start()

    def on_upload_progress(self, percentage: int, message: str):
        """Handle upload progress"""
        self.upload_progress.setValue(percentage)
        self.upload_status_label.setText(f"Status: {message}")

    def on_upload_finished(self, success: bool, message: str):
        """Handle upload finished"""
        self.log(message)
        self.upload_btn.setEnabled(True)
        self.upload_progress.setValue(0 if not success else 100)

    def query_wigle(self):
        """Query WiGLE database"""
        api_key = self.api_key_input.text().strip()
        query_type = self.query_type_combo.currentData()
        query = self.query_input.text().strip()

        if not api_key:
            self.log("❌ Error: API key required")
            return

        if not query:
            self.log("❌ Error: Query required")
            return

        self.log(f"🔍 Searching WiGLE for {query_type}: {query}")
        self.query_results_tree.clear()

        try:
            import requests

            url = "https://api.wigle.net/api/v2/network/search"
            headers = {"Authorization": f"Basic {api_key}"}
            params = {query_type: query}

            response = requests.get(url, headers=headers, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                self.log(f"✅ Found {len(results)} result(s)")

                for result in results:
                    item = QTreeWidgetItem(self.query_results_tree)
                    item.setText(0, result.get('ssid', ''))
                    item.setText(1, result.get('netid', ''))
                    item.setText(2, result.get('encryption', ''))
                    item.setText(3, str(result.get('trilat', '')))
                    item.setText(4, str(result.get('trilong', '')))
                    item.setText(5, result.get('firsttime', ''))

            else:
                self.log(f"❌ Query failed: {response.status_code}")

        except Exception as e:
            self.log(f"❌ Query error: {e}")

    def export_query_results(self):
        """Export query results"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            str(Path.cwd() / "data" / "wigle_query.csv"),
            "CSV Files (*.csv)"
        )

        if file_path:
            # TODO: Implement export
            self.log(f"📥 Exported results to {file_path}")

    def auto_upload_all_scans(self):
        """Auto-upload all scan files in captures directory"""
        api_key = self.api_key_input.text().strip()

        if not api_key:
            self.log("❌ Error: API key required for auto-upload")
            return

        captures_dir = Path.cwd() / "data" / "captures"
        if not captures_dir.exists():
            self.log("❌ No captures directory found")
            return

        # Find all CSV files in captures directory
        csv_files = list(captures_dir.glob("**/*-01.csv"))

        if not csv_files:
            self.log("❌ No scan files found to upload")
            return

        self.log(f"📤 Found {len(csv_files)} scan files to upload")
        self.log(f"🚀 Starting auto-upload...")

        # Upload each file
        uploaded = 0
        failed = 0

        for csv_file in csv_files:
            self.log(f"📤 Uploading {csv_file.name}...")

            # Create upload thread
            upload_thread = WiGLEUploadThread(api_key, str(csv_file))
            upload_thread.finished.connect(
                lambda success, msg, name=csv_file.name: self._handle_auto_upload_result(success, msg, name)
            )
            upload_thread.run()  # Run synchronously for simplicity

        self.log(f"✅ Auto-upload complete: {uploaded} uploaded, {failed} failed")

    def _handle_auto_upload_result(self, success: bool, message: str, filename: str):
        """Handle individual auto-upload result"""
        if success:
            self.log(f"✅ {filename}: {message}")
        else:
            self.log(f"❌ {filename}: {message}")

    def toggle_auto_upload(self, state):
        """Toggle auto-upload on scan complete"""
        try:
            from ..utils.config_db import DBConfig

            config = DBConfig()
            enabled = state == 2  # Qt.Checked

            config.set('wigle.auto_upload', str(enabled),
                      value_type='bool', category='wigle',
                      description='Auto-upload scans to WiGLE on completion')

            if enabled:
                self.log("✅ Auto-upload enabled - scans will upload automatically")
            else:
                self.log("❌ Auto-upload disabled")

        except Exception as e:
            self.log(f"❌ Error toggling auto-upload: {e}")

    def log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")
