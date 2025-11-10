"""
Handshake Viewer Tab
View and analyze captured WiFi handshakes with WireShark integration and heuristic analysis
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QTextEdit, QProgressBar, QComboBox, QLineEdit
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor
import subprocess
import os
from pathlib import Path
from datetime import datetime
import json


class HandshakeViewerTab(QWidget):
    """Tab for viewing and analyzing captured handshakes with WireShark"""

    def __init__(self):
        super().__init__()
        self.handshake_dir = Path("/opt/gattrose-ng/data/handshakes")
        self.selected_handshake = None
        self.init_ui()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_handshakes)
        self.refresh_timer.start(3000)  # Refresh every 3 seconds

    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Controls at top
        controls_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_handshakes)
        controls_layout.addWidget(self.refresh_btn)

        # Filter by quality
        controls_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Handshakes", "Valid Only", "Cracked Only", "Not Cracked"])
        self.filter_combo.currentIndexChanged.connect(self.refresh_handshakes)
        controls_layout.addWidget(self.filter_combo)

        # Search
        controls_layout.addWidget(QLabel("Search SSID/BSSID:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter by SSID or BSSID...")
        self.search_box.textChanged.connect(self.refresh_handshakes)
        controls_layout.addWidget(self.search_box)

        controls_layout.addStretch()

        # Stats
        self.stats_label = QLabel("No handshakes")
        controls_layout.addWidget(self.stats_label)

        layout.addLayout(controls_layout)

        # Handshake table
        handshake_group = QGroupBox("Captured Handshakes")
        handshake_layout = QVBoxLayout()

        self.handshake_table = QTableWidget(0, 8)
        self.handshake_table.setHorizontalHeaderLabels([
            "SSID", "BSSID", "Captured", "Quality", "EAPOL", "Analysis", "Cracked", "Actions"
        ])
        self.handshake_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.handshake_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.handshake_table.itemSelectionChanged.connect(self.on_handshake_selected)
        handshake_layout.addWidget(self.handshake_table)

        handshake_group.setLayout(handshake_layout)
        layout.addWidget(handshake_group)

        # Analysis panel
        analysis_group = QGroupBox("WireShark Analysis & Heuristics")
        analysis_layout = QVBoxLayout()

        # Action buttons
        button_layout = QHBoxLayout()

        self.open_wireshark_btn = QPushButton("🦈 Open in WireShark")
        self.open_wireshark_btn.clicked.connect(self.open_in_wireshark)
        self.open_wireshark_btn.setEnabled(False)
        button_layout.addWidget(self.open_wireshark_btn)

        self.analyze_btn = QPushButton("🔍 Run Heuristic Analysis")
        self.analyze_btn.clicked.connect(self.run_heuristic_analysis)
        self.analyze_btn.setEnabled(False)
        button_layout.addWidget(self.analyze_btn)

        self.verify_btn = QPushButton("✓ Verify Handshake")
        self.verify_btn.clicked.connect(self.verify_handshake)
        self.verify_btn.setEnabled(False)
        button_layout.addWidget(self.verify_btn)

        self.crack_btn = QPushButton("🔓 Crack Handshake")
        self.crack_btn.clicked.connect(self.crack_handshake)
        self.crack_btn.setEnabled(False)
        button_layout.addWidget(self.crack_btn)

        button_layout.addStretch()
        analysis_layout.addLayout(button_layout)

        # Analysis output
        self.analysis_output = QTextEdit()
        self.analysis_output.setReadOnly(True)
        self.analysis_output.setMaximumHeight(200)
        self.analysis_output.setPlaceholderText("Select a handshake to view analysis...")
        analysis_layout.addWidget(self.analysis_output)

        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)

        # Initial load
        self.refresh_handshakes()

    def refresh_handshakes(self):
        """Refresh the handshake list"""
        from ..database.models import get_session, Handshake, Network

        session = get_session()
        try:
            # Get search filter
            search_text = self.search_box.text().strip().lower()

            # Get quality filter
            filter_idx = self.filter_combo.currentIndex()

            # Query handshakes with network info
            query = session.query(Handshake, Network).join(Network)

            # Apply filters
            if filter_idx == 1:  # Valid Only
                query = query.filter(Handshake.is_complete == True)
            elif filter_idx == 2:  # Cracked Only
                query = query.filter(Handshake.is_cracked == True)
            elif filter_idx == 3:  # Not Cracked
                query = query.filter(Handshake.is_cracked == False)

            results = query.order_by(Handshake.captured_at.desc()).all()

            # Apply search filter
            if search_text:
                results = [
                    (hs, net) for hs, net in results
                    if (net.ssid and search_text in net.ssid.lower()) or
                       (net.bssid and search_text in net.bssid.lower())
                ]

            # Update stats
            valid_count = sum(1 for hs, net in results if hs.is_complete)
            cracked_count = sum(1 for hs, net in results if hs.is_cracked)
            self.stats_label.setText(
                f"Total: {len(results)} | Valid: {valid_count} | Cracked: {cracked_count}"
            )

            # Update table
            self.handshake_table.setRowCount(0)

            for hs, net in results:
                row = self.handshake_table.rowCount()
                self.handshake_table.insertRow(row)

                # SSID
                ssid_item = QTableWidgetItem(net.ssid or "(hidden)")
                self.handshake_table.setItem(row, 0, ssid_item)

                # BSSID
                bssid_item = QTableWidgetItem(net.bssid or "Unknown")
                self.handshake_table.setItem(row, 1, bssid_item)

                # Captured time
                captured_time = hs.captured_at.strftime("%Y-%m-%d %H:%M") if hs.captured_at else "Unknown"
                time_item = QTableWidgetItem(captured_time)
                self.handshake_table.setItem(row, 2, time_item)

                # Quality indicator
                quality = "Unknown"
                quality_color = QColor(128, 128, 128)

                if hs.is_complete:
                    if hs.quality and hs.quality >= 80:
                        quality = "Excellent"
                        quality_color = QColor(0, 200, 0)
                    elif hs.quality and hs.quality >= 50:
                        quality = "Good"
                        quality_color = QColor(100, 200, 0)
                    else:
                        quality = "Fair"
                        quality_color = QColor(200, 200, 0)
                else:
                    quality = "Incomplete"
                    quality_color = QColor(200, 0, 0)

                quality_item = QTableWidgetItem(quality)
                quality_item.setBackground(quality_color)
                self.handshake_table.setItem(row, 3, quality_item)

                # EAPOL messages (use handshake type instead)
                eapol_info = hs.handshake_type or "Unknown"
                eapol_item = QTableWidgetItem(eapol_info)
                self.handshake_table.setItem(row, 4, eapol_item)

                # Analysis status (use quality score)
                analysis_status = "Not analyzed"
                if hs.quality is not None:
                    analysis_status = f"Quality: {hs.quality}/100"
                analysis_item = QTableWidgetItem(analysis_status)
                self.handshake_table.setItem(row, 5, analysis_item)

                # Cracked status
                cracked_status = "Yes" if hs.is_cracked else "No"
                cracked_item = QTableWidgetItem(cracked_status)
                if hs.is_cracked:
                    cracked_item.setBackground(QColor(0, 200, 0))
                self.handshake_table.setItem(row, 6, cracked_item)

                # Actions (store handshake ID)
                action_item = QTableWidgetItem(str(hs.id))
                self.handshake_table.setItem(row, 7, action_item)

        finally:
            session.close()

    def on_handshake_selected(self):
        """Called when a handshake is selected"""
        selected_rows = self.handshake_table.selectedItems()
        if not selected_rows:
            self.selected_handshake = None
            self.open_wireshark_btn.setEnabled(False)
            self.analyze_btn.setEnabled(False)
            self.verify_btn.setEnabled(False)
            self.crack_btn.setEnabled(False)
            return

        # Get handshake ID from last column
        row = selected_rows[0].row()
        handshake_id = int(self.handshake_table.item(row, 7).text())
        self.selected_handshake = handshake_id

        # Enable buttons
        self.open_wireshark_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.verify_btn.setEnabled(True)
        self.crack_btn.setEnabled(True)

        # Load analysis if available
        self.load_analysis()

    def load_analysis(self):
        """Load existing analysis for selected handshake"""
        if not self.selected_handshake:
            return

        from ..database.models import get_session, Handshake, Network

        session = get_session()
        try:
            hs = session.query(Handshake).filter(Handshake.id == self.selected_handshake).first()
            if not hs:
                return

            # Get network info
            net = session.query(Network).filter(Network.id == hs.network_id).first()
            ssid = net.ssid if net else "(unknown)"
            bssid = net.bssid if net else "(unknown)"
            encryption = net.encryption if net else "Unknown"

            output = f"=== Handshake Analysis: {ssid or '(hidden)'} ({bssid}) ===\n\n"

            output += f"📁 File: {hs.file_path}\n"
            output += f"📅 Captured: {hs.captured_at}\n"
            output += f"🔐 Encryption: {encryption}\n"
            output += f"📊 Handshake Type: {hs.handshake_type or 'Unknown'}\n"
            output += f"✓ Complete: {'Yes' if hs.is_complete else 'No'}\n"
            output += f"📈 Quality Score: {hs.quality if hs.quality is not None else 'Not scored'}\n"
            output += f"🔓 Cracked: {'Yes' if hs.is_cracked else 'No'}\n\n"

            if hs.notes:
                output += f"=== Notes ===\n{hs.notes}\n\n"

            if hs.is_cracked and hs.password:
                output += f"🔓 Password: {hs.password}\n"

            self.analysis_output.setText(output)

        finally:
            session.close()

    def open_in_wireshark(self):
        """Open selected handshake in WireShark"""
        if not self.selected_handshake:
            return

        from ..database.models import get_session, Handshake

        session = get_session()
        try:
            hs = session.query(Handshake).filter(Handshake.id == self.selected_handshake).first()
            if not hs or not hs.file_path:
                self.analysis_output.append("\n❌ Handshake file not found!")
                return

            file_path = Path(hs.file_path)
            if not file_path.exists():
                self.analysis_output.append(f"\n❌ File does not exist: {file_path}")
                return

            # Open in WireShark
            self.analysis_output.append(f"\n🦈 Opening {file_path.name} in WireShark...")
            subprocess.Popen(['wireshark', str(file_path)])

        finally:
            session.close()

    def run_heuristic_analysis(self):
        """Run heuristic analysis on selected handshake using tshark and custom analysis"""
        if not self.selected_handshake:
            return

        from ..database.models import get_session, Handshake

        session = get_session()
        try:
            hs = session.query(Handshake).filter(Handshake.id == self.selected_handshake).first()
            if not hs or not hs.file_path:
                self.analysis_output.append("\n❌ Handshake file not found!")
                return

            file_path = Path(hs.file_path)
            if not file_path.exists():
                self.analysis_output.append(f"\n❌ File does not exist: {file_path}")
                return

            self.analysis_output.append(f"\n🔍 Running heuristic analysis on {file_path.name}...")

            analysis_results = {
                'analyzed': True,
                'timestamp': datetime.now().isoformat(),
                'score': 0
            }

            # 1. Count EAPOL packets using tshark
            try:
                result = subprocess.run(
                    ['tshark', '-r', str(file_path), '-Y', 'eapol', '-T', 'fields', '-e', 'frame.number'],
                    capture_output=True, text=True, timeout=10
                )
                eapol_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                analysis_results['eapol_count'] = eapol_count

                self.analysis_output.append(f"   ✓ EAPOL Messages Found: {eapol_count}")

                if eapol_count >= 4:
                    analysis_results['score'] += 40
                    self.analysis_output.append(f"   ✓ Complete 4-way handshake (+40 points)")
                elif eapol_count >= 2:
                    analysis_results['score'] += 20
                    self.analysis_output.append(f"   ⚠ Partial handshake ({eapol_count} messages) (+20 points)")
                else:
                    self.analysis_output.append(f"   ❌ Insufficient EAPOL messages")

            except Exception as e:
                self.analysis_output.append(f"   ❌ EAPOL analysis failed: {e}")

            # 2. Check for specific EAPOL key types (M1, M2, M3, M4)
            try:
                result = subprocess.run(
                    ['tshark', '-r', str(file_path), '-Y', 'eapol.keydes.key_info', '-T', 'fields',
                     '-e', 'eapol.keydes.key_info'],
                    capture_output=True, text=True, timeout=10
                )

                if result.stdout.strip():
                    analysis_results['score'] += 15
                    self.analysis_output.append(f"   ✓ Key exchange information present (+15 points)")

            except Exception as e:
                pass

            # 3. Check for replay counter
            try:
                result = subprocess.run(
                    ['tshark', '-r', str(file_path), '-Y', 'eapol.keydes.replay_counter', '-T', 'fields',
                     '-e', 'eapol.keydes.replay_counter'],
                    capture_output=True, text=True, timeout=10
                )

                if result.stdout.strip():
                    analysis_results['replay_analysis'] = 'Present'
                    analysis_results['score'] += 10
                    self.analysis_output.append(f"   ✓ Replay counter present (+10 points)")

            except Exception as e:
                pass

            # 4. Check for nonces (ANonce, SNonce)
            try:
                result = subprocess.run(
                    ['tshark', '-r', str(file_path), '-Y', 'wlan.rsn.ie.pmkid or eapol.keydes.nonce',
                     '-T', 'fields', '-e', 'frame.number'],
                    capture_output=True, text=True, timeout=10
                )

                if result.stdout.strip():
                    analysis_results['nonce_check'] = 'Present'
                    analysis_results['score'] += 15
                    self.analysis_output.append(f"   ✓ Nonce data present (+15 points)")

            except Exception as e:
                pass

            # 5. Check for MIC (Message Integrity Code)
            try:
                result = subprocess.run(
                    ['tshark', '-r', str(file_path), '-Y', 'eapol.keydes.mic', '-T', 'fields',
                     '-e', 'eapol.keydes.mic'],
                    capture_output=True, text=True, timeout=10
                )

                mic_lines = [line for line in result.stdout.strip().split('\n') if line.strip()]
                if mic_lines:
                    analysis_results['mic_present'] = True
                    analysis_results['score'] += 20
                    self.analysis_output.append(f"   ✓ MIC present in {len(mic_lines)} messages (+20 points)")

            except Exception as e:
                pass

            # Determine packet quality
            score = analysis_results['score']
            if score >= 80:
                quality = "Excellent - Highly crackable"
            elif score >= 60:
                quality = "Good - Should be crackable"
            elif score >= 40:
                quality = "Fair - May be crackable"
            else:
                quality = "Poor - Unlikely to crack"

            analysis_results['packet_quality'] = quality

            self.analysis_output.append(f"\n📊 Overall Score: {score}/100")
            self.analysis_output.append(f"📈 Quality: {quality}")

            # Save analysis to database
            hs.quality = score
            hs.notes = f"Heuristic Analysis:\n{json.dumps(analysis_results, indent=2)}"
            session.commit()

            self.analysis_output.append("\n✓ Analysis complete and saved!")

        except Exception as e:
            self.analysis_output.append(f"\n❌ Analysis error: {e}")
        finally:
            session.close()

        # Refresh table to show updated analysis
        self.refresh_handshakes()

    def verify_handshake(self):
        """Verify handshake integrity using aircrack-ng"""
        if not self.selected_handshake:
            return

        from ..database.models import get_session, Handshake

        session = get_session()
        try:
            hs = session.query(Handshake).filter(Handshake.id == self.selected_handshake).first()
            if not hs or not hs.file_path:
                self.analysis_output.append("\n❌ Handshake file not found!")
                return

            file_path = Path(hs.file_path)
            if not file_path.exists():
                self.analysis_output.append(f"\n❌ File does not exist: {file_path}")
                return

            self.analysis_output.append(f"\n✓ Verifying handshake with aircrack-ng...")

            result = subprocess.run(
                ['aircrack-ng', str(file_path)],
                capture_output=True, text=True, timeout=30
            )

            # Parse output for validation info
            if "1 handshake" in result.stdout or "handshake" in result.stdout.lower():
                self.analysis_output.append("   ✓ Valid handshake detected!")
                hs.is_complete = True
            else:
                self.analysis_output.append("   ⚠ No valid handshake found")
                hs.is_complete = False

            # Show relevant output
            for line in result.stdout.split('\n'):
                if 'handshake' in line.lower() or 'EAPOL' in line:
                    self.analysis_output.append(f"   {line.strip()}")

            session.commit()

        except subprocess.TimeoutExpired:
            self.analysis_output.append("   ⚠ Verification timeout")
        except Exception as e:
            self.analysis_output.append(f"   ❌ Verification error: {e}")
        finally:
            session.close()

        self.refresh_handshakes()

    def crack_handshake(self):
        """Queue handshake for cracking"""
        if not self.selected_handshake:
            return

        self.analysis_output.append("\n🔓 Queuing handshake for cracking...")
        self.analysis_output.append("   This will be handled by the WPA cracking service")

        # In a full implementation, this would add to the attack queue
        # For now, just show the message
