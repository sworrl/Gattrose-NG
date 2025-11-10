"""
Attack Queue Widget for Gattrose-NG
Draggable, interactive attack queue with progress tracking
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QProgressBar, QLabel, QPushButton, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont


class AttackQueueWidget(QWidget):
    """Interactive attack queue widget with drag-drop reordering"""

    job_reordered = pyqtSignal(list)  # Emit new order of job IDs
    job_cancelled = pyqtSignal(str)   # Emit job ID to cancel
    job_paused = pyqtSignal(str)      # Emit job ID to pause
    job_resumed = pyqtSignal(str)     # Emit job ID to resume
    job_priority_changed = pyqtSignal(str, int)  # Emit job ID and new priority
    view_job_details = pyqtSignal(str)  # Emit job ID to view details

    def __init__(self, parent=None):
        super().__init__(parent)
        self.jobs = {}  # job_id -> QTreeWidgetItem
        self.progress_bars = {}  # job_id -> QProgressBar
        self.init_ui()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.request_update)
        self.refresh_timer.start(1000)  # Update every second

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # Header with stats
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_frame.setStyleSheet("background-color: #2C3E50; padding: 10px; border-radius: 5px;")
        header_layout = QVBoxLayout()

        header_label = QLabel("🎯 Attack Queue")
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: white;")
        header_layout.addWidget(header_label)

        # Statistics row
        stats_layout = QHBoxLayout()
        self.stats_queued = QLabel("Queued: 0")
        self.stats_queued.setStyleSheet("color: #3498DB; font-weight: bold;")
        self.stats_running = QLabel("Running: 0")
        self.stats_running.setStyleSheet("color: #E74C3C; font-weight: bold;")
        self.stats_completed = QLabel("Completed: 0")
        self.stats_completed.setStyleSheet("color: #2ECC71; font-weight: bold;")
        self.stats_failed = QLabel("Failed: 0")
        self.stats_failed.setStyleSheet("color: #E67E22; font-weight: bold;")

        stats_layout.addWidget(self.stats_queued)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.stats_running)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.stats_completed)
        stats_layout.addWidget(QLabel("|"))
        stats_layout.addWidget(self.stats_failed)
        stats_layout.addStretch()

        header_layout.addLayout(stats_layout)
        header_frame.setLayout(header_layout)
        layout.addWidget(header_frame)

        # Queue tree with drag-drop
        self.queue_tree = QTreeWidget()
        self.queue_tree.setHeaderLabels([
            "Priority", "Attack", "Target", "SSID", "Status", "Progress", "ETA", "Attempts"
        ])
        self.queue_tree.setColumnWidth(0, 60)  # Priority
        self.queue_tree.setColumnWidth(1, 120)  # Attack
        self.queue_tree.setColumnWidth(2, 130)  # Target
        self.queue_tree.setColumnWidth(3, 150)  # SSID
        self.queue_tree.setColumnWidth(4, 80)  # Status
        self.queue_tree.setColumnWidth(5, 100)  # Progress
        self.queue_tree.setColumnWidth(6, 80)  # ETA
        self.queue_tree.setColumnWidth(7, 70)  # Attempts

        self.queue_tree.setDragEnabled(True)
        self.queue_tree.setAcceptDrops(True)
        self.queue_tree.setDropIndicatorShown(True)
        self.queue_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.queue_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.queue_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.queue_tree.setAlternatingRowColors(True)

        # Connect drag-drop signals
        self.queue_tree.model().rowsMoved.connect(self.on_rows_moved)

        layout.addWidget(self.queue_tree)

        # Control buttons
        button_layout = QHBoxLayout()

        self.pause_all_btn = QPushButton("⏸ Pause All")
        self.pause_all_btn.clicked.connect(self.pause_all)

        self.clear_completed_btn = QPushButton("🗑️ Clear Completed")
        self.clear_completed_btn.clicked.connect(self.clear_completed)

        button_layout.addWidget(self.pause_all_btn)
        button_layout.addWidget(self.clear_completed_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def add_job(self, job_dict: dict):
        """Add or update job in queue tree"""
        job_id = job_dict['id']

        # Check if job already exists
        if job_id in self.jobs:
            self.update_job(job_dict)
            return

        # Create new item
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, job_id)  # Store job ID

        # Set basic info
        item.setText(0, str(job_dict['priority']))
        item.setText(1, self.format_attack_type(job_dict['attack_type']))
        item.setText(2, job_dict['target_bssid'])
        item.setText(3, job_dict['target_ssid'][:20] if job_dict['target_ssid'] else "")
        item.setText(4, job_dict['status'].upper())
        item.setText(7, f"{job_dict['attempts']}/{job_dict['max_attempts']}")

        # Color code by status
        self.apply_status_color(item, job_dict['status'])

        # Create progress bar
        progress_bar = QProgressBar()
        progress_bar.setValue(job_dict['progress'])
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 3px;
                text-align: center;
                font-size: 9pt;
            }
            QProgressBar::chunk {
                background-color: #3498DB;
            }
        """)
        self.progress_bars[job_id] = progress_bar

        # Add to tree
        self.queue_tree.addTopLevelItem(item)
        self.queue_tree.setItemWidget(item, 5, progress_bar)
        self.jobs[job_id] = item

        # Calculate ETA
        self.update_eta(item, job_dict)

    def update_job(self, job_dict: dict):
        """Update existing job"""
        job_id = job_dict['id']
        if job_id not in self.jobs:
            return

        item = self.jobs[job_id]
        item.setText(0, str(job_dict['priority']))
        item.setText(4, job_dict['status'].upper())
        item.setText(7, f"{job_dict['attempts']}/{job_dict['max_attempts']}")

        # Update progress bar
        if job_id in self.progress_bars:
            self.progress_bars[job_id].setValue(job_dict['progress'])

        # Update colors
        self.apply_status_color(item, job_dict['status'])

        # Update ETA
        self.update_eta(item, job_dict)

    def remove_job(self, job_id: str):
        """Remove job from tree"""
        if job_id in self.jobs:
            item = self.jobs[job_id]
            index = self.queue_tree.indexOfTopLevelItem(item)
            self.queue_tree.takeTopLevelItem(index)
            del self.jobs[job_id]
            if job_id in self.progress_bars:
                del self.progress_bars[job_id]

    def apply_status_color(self, item: QTreeWidgetItem, status: str):
        """Apply color based on status"""
        if status == "running":
            color = QColor(231, 76, 60)  # Red
            font_weight = QFont.Weight.Bold
        elif status == "completed":
            color = QColor(46, 204, 113)  # Green
            font_weight = QFont.Weight.Normal
        elif status == "failed":
            color = QColor(230, 126, 34)  # Orange
            font_weight = QFont.Weight.Normal
        elif status == "paused":
            color = QColor(241, 196, 15)  # Yellow
            font_weight = QFont.Weight.Normal
        elif status == "cancelled":
            color = QColor(149, 165, 166)  # Gray
            font_weight = QFont.Weight.Normal
        else:  # queued
            color = QColor(52, 152, 219)  # Blue
            font_weight = QFont.Weight.Normal

        for i in range(8):
            item.setForeground(i, QBrush(color))
            font = item.font(i)
            font.setWeight(font_weight)
            item.setFont(i, font)

    def format_attack_type(self, attack_type: str) -> str:
        """Format attack type for display"""
        icons = {
            'wps_pixie': '⚡ WPS Pixie',
            'wps_pin': '🔐 WPS PIN',
            'deauth': '💥 Deauth',
            'handshake': '🤝 Handshake',
            'wep_crack': '🔓 WEP Crack',
            'hashcat_crack': '💻 Hashcat',
            'karma': '🎭 KARMA',
            'evil_twin': '👿 Evil Twin'
        }
        return icons.get(attack_type, attack_type.upper())

    def update_eta(self, item: QTreeWidgetItem, job_dict: dict):
        """Calculate and display ETA"""
        if job_dict['status'] == 'running':
            # Simple ETA based on estimated duration and progress
            progress = job_dict['progress']
            if progress > 0:
                estimated = job_dict.get('estimated_duration', 0)
                elapsed = 0  # Would calculate from start_time
                remaining = int((estimated * (100 - progress)) / progress)
                item.setText(6, self.format_time(remaining))
            else:
                item.setText(6, "Calculating...")
        elif job_dict['status'] == 'completed':
            item.setText(6, "Done")
        elif job_dict['status'] == 'failed':
            item.setText(6, "Failed")
        else:
            estimated = job_dict.get('estimated_duration', 0)
            item.setText(6, self.format_time(estimated))

    def format_time(self, seconds: int) -> str:
        """Format seconds into human readable time"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        else:
            return f"{seconds // 3600}h {(seconds % 3600) // 60}m"

    def show_context_menu(self, position):
        """Show right-click context menu"""
        item = self.queue_tree.itemAt(position)
        if not item:
            return

        job_id = item.data(0, Qt.ItemDataRole.UserRole)
        status = item.text(4).lower()

        menu = QMenu()

        # Priority controls
        priority_menu = menu.addMenu("⚡ Set Priority")
        for i in range(1, 11):
            action = priority_menu.addAction(f"Priority {i}")
            action.triggered.connect(lambda checked, p=i: self.job_priority_changed.emit(job_id, p))

        menu.addSeparator()

        # Move controls
        move_top = menu.addAction("⬆️ Move to Top")
        move_top.triggered.connect(lambda: self.move_to_top(item))

        move_bottom = menu.addAction("⬇️ Move to Bottom")
        move_bottom.triggered.connect(lambda: self.move_to_bottom(item))

        menu.addSeparator()

        # Pause/resume
        if status == "running":
            pause_action = menu.addAction("⏸ Pause")
            pause_action.triggered.connect(lambda: self.job_paused.emit(job_id))
        elif status == "paused":
            resume_action = menu.addAction("▶️ Resume")
            resume_action.triggered.connect(lambda: self.job_resumed.emit(job_id))

        # Cancel
        if status in ["queued", "running", "paused"]:
            cancel_action = menu.addAction("❌ Cancel")
            cancel_action.triggered.connect(lambda: self.job_cancelled.emit(job_id))

        menu.addSeparator()

        # View details
        details_action = menu.addAction("🔍 View Details")
        details_action.triggered.connect(lambda: self.view_job_details.emit(job_id))

        menu.exec(self.queue_tree.viewport().mapToGlobal(position))

    def move_to_top(self, item: QTreeWidgetItem):
        """Move item to top of queue"""
        index = self.queue_tree.indexOfTopLevelItem(item)
        self.queue_tree.takeTopLevelItem(index)
        self.queue_tree.insertTopLevelItem(0, item)
        self.emit_reorder()

    def move_to_bottom(self, item: QTreeWidgetItem):
        """Move item to bottom of queue"""
        index = self.queue_tree.indexOfTopLevelItem(item)
        self.queue_tree.takeTopLevelItem(index)
        self.queue_tree.addTopLevelItem(item)
        self.emit_reorder()

    def on_rows_moved(self, parent, start, end, destination, row):
        """Handle drag-drop reordering"""
        self.emit_reorder()

    def emit_reorder(self):
        """Emit new order of job IDs"""
        job_ids = []
        for i in range(self.queue_tree.topLevelItemCount()):
            item = self.queue_tree.topLevelItem(i)
            job_id = item.data(0, Qt.ItemDataRole.UserRole)
            job_ids.append(job_id)
        self.job_reordered.emit(job_ids)

    def pause_all(self):
        """Pause all running/queued jobs"""
        # TODO: Implement pause all
        pass

    def clear_completed(self):
        """Remove completed/failed jobs from view"""
        items_to_remove = []
        for job_id, item in self.jobs.items():
            status = item.text(4).lower()
            if status in ["completed", "failed", "cancelled"]:
                items_to_remove.append(job_id)

        for job_id in items_to_remove:
            self.remove_job(job_id)

    def update_statistics(self, stats: dict):
        """Update header statistics"""
        self.stats_queued.setText(f"Queued: {stats.get('queued', 0)}")
        self.stats_running.setText(f"Running: {stats.get('running', 0)}")
        self.stats_completed.setText(f"Completed: {stats.get('completed', 0)}")
        self.stats_failed.setText(f"Failed: {stats.get('failed', 0)}")

    def request_update(self):
        """Request queue status update from orchestrator"""
        # This would be connected to a signal that fetches current queue state
        pass

class CompactAttackQueueWidget(QWidget):
    """Compact attack queue for dashboard overview"""
    
    view_full_queue = pyqtSignal()  # Signal to switch to full queue tab
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.jobs_data = []
        self.init_ui()
        
        # Auto-refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.request_update)
        self.refresh_timer.start(2000)  # Update every 2 seconds
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with stats
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_frame.setStyleSheet("background-color: #2C3E50; padding: 8px; border-radius: 5px;")
        header_layout = QHBoxLayout()
        
        title = QLabel("🎯 Attack Queue")
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        
        # Quick stats
        self.stats_label = QLabel("Queued: 0 | Running: 0")
        self.stats_label.setStyleSheet("color: #ECF0F1; font-size: 10pt;")
        header_layout.addWidget(self.stats_label)
        header_layout.addStretch()
        
        # View full button
        view_btn = QPushButton("View Full →")
        view_btn.setStyleSheet("background-color: #3498DB; color: white; padding: 5px 10px; border-radius: 3px;")
        view_btn.clicked.connect(self.view_full_queue.emit)
        header_layout.addWidget(view_btn)
        
        header_frame.setLayout(header_layout)
        layout.addWidget(header_frame)
        
        # Compact list of top 5 jobs
        self.queue_list = QWidget()
        self.queue_list.setMaximumHeight(150)
        queue_list_layout = QVBoxLayout()
        queue_list_layout.setContentsMargins(5, 5, 5, 5)
        queue_list_layout.setSpacing(2)
        self.queue_list.setLayout(queue_list_layout)
        
        # Scroll area for jobs
        scroll = QScrollArea()
        scroll.setWidget(self.queue_list)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
    
    def update_queue(self, jobs: list, stats: dict):
        """Update with top jobs"""
        self.jobs_data = jobs
        
        # Clear existing items
        layout = self.queue_list.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Update stats
        queued = stats.get('queued', 0)
        running = stats.get('running', 0)
        completed = stats.get('completed', 0)
        self.stats_label.setText(f"Queued: {queued} | Running: {running} | Done: {completed}")
        
        # Show top 5 jobs
        for i, job in enumerate(jobs[:5]):
            job_widget = self._create_job_widget(job)
            layout.addWidget(job_widget)
        
        # Add "..." if more jobs
        if len(jobs) > 5:
            more_label = QLabel(f"... and {len(jobs) - 5} more jobs")
            more_label.setStyleSheet("color: #7F8C8D; font-style: italic; padding: 5px;")
            layout.addWidget(more_label)
        
        # Add stretch to push items to top
        layout.addStretch()
    
    def _create_job_widget(self, job: dict) -> QFrame:
        """Create a compact job display widget"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setMaximumHeight(35)
        
        # Color by status
        if job['status'] == 'running':
            bg_color = "#E74C3C"  # Red
            text_color = "white"
            status_icon = "▶️"
        elif job['status'] == 'completed':
            bg_color = "#2ECC71"  # Green
            text_color = "white"
            status_icon = "✅"
        elif job['status'] == 'failed':
            bg_color = "#E67E22"  # Orange
            text_color = "white"
            status_icon = "❌"
        elif job['status'] == 'paused':
            bg_color = "#F39C12"  # Yellow
            text_color = "black"
            status_icon = "⏸"
        else:  # queued
            bg_color = "#3498DB"  # Blue
            text_color = "white"
            status_icon = "⏳"
        
        frame.setStyleSheet(f"background-color: {bg_color}; border-radius: 3px; padding: 3px;")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Status icon + Attack type
        attack_type = self.format_attack_type(job['attack_type'])
        type_label = QLabel(f"{status_icon} {attack_type}")
        type_label.setStyleSheet(f"color: {text_color}; font-weight: bold; font-size: 10pt;")
        layout.addWidget(type_label)
        
        # Arrow
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet(f"color: {text_color};")
        layout.addWidget(arrow_label)
        
        # Target
        ssid = job.get('target_ssid', '')
        bssid = job.get('target_bssid', '')
        target = ssid[:15] if ssid else bssid[:17]
        target_label = QLabel(target)
        target_label.setStyleSheet(f"color: {text_color}; font-size: 10pt;")
        layout.addWidget(target_label)
        
        layout.addStretch()
        
        # Priority badge
        priority = job.get('priority', 0)
        priority_label = QLabel(f"P{priority}")
        priority_label.setStyleSheet(f"color: {text_color}; font-weight: bold; background-color: rgba(0,0,0,0.2); padding: 2px 5px; border-radius: 2px; font-size: 9pt;")
        layout.addWidget(priority_label)
        
        # Progress (if running)
        if job['status'] == 'running':
            progress = job.get('progress', 0)
            progress_label = QLabel(f"{progress}%")
            progress_label.setStyleSheet(f"color: {text_color}; font-size: 9pt;")
            layout.addWidget(progress_label)
        
        frame.setLayout(layout)
        return frame
    
    def format_attack_type(self, attack_type: str) -> str:
        """Short format for attack type"""
        short_names = {
            'wps_pixie': 'WPS-Pixie',
            'wps_pin': 'WPS-PIN',
            'deauth': 'Deauth',
            'handshake_capture': 'Handshake',
            'handshake': 'Handshake',
            'wep_crack': 'WEP',
            'wpa_crack': 'WPA',
            'wpa2_crack': 'WPA2',
            'hashcat_crack': 'Crack'
        }
        return short_names.get(attack_type, attack_type[:8].upper())
    
    def request_update(self):
        """Request queue update - can be overridden"""
        pass
