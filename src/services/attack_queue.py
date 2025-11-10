"""
Attack Queue System for Gattrose-NG
Manages queuing, prioritization, and execution of WiFi attacks
"""

import time
import uuid
import threading
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class AttackType(Enum):
    """Types of attacks that can be queued"""
    WPS_PIXIE = "wps_pixie"
    WPS_PIN = "wps_pin"
    DEAUTH = "deauth"
    HANDSHAKE_CAPTURE = "handshake"
    WEP_CRACK = "wep"
    WPA_CRACK = "wpa"
    WPA2_CRACK = "wpa2"  # WPA2 uses same method as WPA
    KARMA = "karma"
    EVIL_TWIN = "evil_twin"


class AttackStatus(Enum):
    """Attack execution status"""
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AttackJob:
    """Represents a single attack job in the queue"""

    def __init__(self, attack_type: AttackType, target_bssid: str, params: dict):
        self.id = str(uuid.uuid4())
        self.attack_type = attack_type
        self.target_bssid = target_bssid.upper()
        self.target_ssid = params.get('ssid', '')
        self.params = params
        self.status = AttackStatus.QUEUED
        self.progress = 0  # 0-100
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None
        self.priority = params.get('priority', 5)  # 1-10, higher = more urgent
        self.estimated_duration = params.get('estimated_duration', 0)  # seconds
        self.attempts = 0
        self.max_attempts = params.get('max_attempts', 1)

    def to_dict(self) -> dict:
        """Convert job to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'attack_type': self.attack_type.value,
            'target_bssid': self.target_bssid,
            'target_ssid': self.target_ssid,
            'status': self.status.value,
            'progress': self.progress,
            'priority': self.priority,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'estimated_duration': self.estimated_duration,
            'attempts': self.attempts,
            'max_attempts': self.max_attempts,
            'params': self.params,
            'result': self.result,
            'error': self.error
        }

    def start(self):
        """Mark job as started"""
        self.status = AttackStatus.RUNNING
        self.start_time = datetime.now()
        self.attempts += 1

    def complete(self, result: Any):
        """Mark job as completed"""
        self.status = AttackStatus.COMPLETED
        self.end_time = datetime.now()
        self.progress = 100
        self.result = result

    def fail(self, error: str):
        """Mark job as failed"""
        self.status = AttackStatus.FAILED
        self.end_time = datetime.now()
        self.error = error

    def pause(self):
        """Pause job execution"""
        self.status = AttackStatus.PAUSED

    def cancel(self):
        """Cancel job"""
        self.status = AttackStatus.CANCELLED
        self.end_time = datetime.now()


class AttackQueueManager:
    """Manages the attack queue with prioritization and ordering"""

    def __init__(self):
        self.queue: List[AttackJob] = []  # Jobs waiting to execute
        self.current_job: Optional[AttackJob] = None  # Currently executing job
        self.completed_jobs: List[AttackJob] = []  # Successfully completed
        self.failed_jobs: List[AttackJob] = []  # Failed attacks
        self.cancelled_jobs: List[AttackJob] = []  # Cancelled by user
        self._lock = threading.Lock()
        self._job_index = {}  # job_id -> AttackJob for quick lookups

    def add_job(self, job: AttackJob) -> str:
        """
        Add job to queue, auto-sort by priority
        Returns: job ID
        """
        with self._lock:
            self.queue.append(job)
            self._job_index[job.id] = job
            # Sort by priority (higher first), then by creation time
            self.queue.sort(key=lambda x: (-x.priority, x.id))
            print(f"[QUEUE] Added {job.attack_type.value} attack on {job.target_ssid} ({job.target_bssid}) [Priority: {job.priority}]")
            return job.id

    def get_next_job(self) -> Optional[AttackJob]:
        """Get highest priority job from queue"""
        with self._lock:
            if self.queue:
                job = self.queue.pop(0)
                return job
            return None

    def pause_current_job(self):
        """Pause current job and return it to queue"""
        with self._lock:
            if self.current_job:
                self.current_job.pause()
                self.queue.insert(0, self.current_job)  # Add to front
                print(f"[QUEUE] Paused {self.current_job.attack_type.value} attack on {self.current_job.target_ssid}")
                self.current_job = None

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific job by ID"""
        with self._lock:
            # Check if it's the current job
            if self.current_job and self.current_job.id == job_id:
                self.current_job.cancel()
                self.cancelled_jobs.append(self.current_job)
                self.current_job = None
                return True

            # Check if it's in the queue
            for i, job in enumerate(self.queue):
                if job.id == job_id:
                    job.cancel()
                    self.cancelled_jobs.append(job)
                    self.queue.pop(i)
                    return True

            return False

    def reorder_queue(self, job_ids: List[str]):
        """Reorder queue based on user drag-drop (maintains order of job_ids)"""
        with self._lock:
            ordered = []
            for job_id in job_ids:
                job = self._job_index.get(job_id)
                if job and job in self.queue:
                    ordered.append(job)

            # Add any jobs that weren't in the reorder list (shouldn't happen)
            for job in self.queue:
                if job not in ordered:
                    ordered.append(job)

            self.queue = ordered
            print(f"[QUEUE] Reordered queue: {len(ordered)} jobs")

    def get_job(self, job_id: str) -> Optional[AttackJob]:
        """Get job by ID"""
        return self._job_index.get(job_id)

    def get_queue_status(self) -> dict:
        """Get current queue status"""
        with self._lock:
            return {
                'queued': len(self.queue),
                'running': 1 if self.current_job else 0,
                'completed': len(self.completed_jobs),
                'failed': len(self.failed_jobs),
                'cancelled': len(self.cancelled_jobs),
                'current_job': self.current_job.to_dict() if self.current_job else None,
                'queue': [job.to_dict() for job in self.queue],
                'completed': [job.to_dict() for job in self.completed_jobs[-10:]],  # Last 10
                'failed': [job.to_dict() for job in self.failed_jobs[-10:]]  # Last 10
            }

    def clear_completed(self):
        """Clear completed and failed jobs from history"""
        with self._lock:
            self.completed_jobs.clear()
            self.failed_jobs.clear()
            self.cancelled_jobs.clear()
            print("[QUEUE] Cleared job history")

    def auto_queue_wps_attacks(self, wps_networks: List[dict], priority: int = 22):
        """
        Automatically queue WPS attacks for discovered networks
        wps_networks: List of dicts with 'bssid', 'ssid', 'channel', 'wps_locked'

        WPS attacks get HIGHEST priority (22) because they're the easiest/fastest to crack
        - Pixie Dust: 2-10 minutes
        - PIN bruteforce: 1-8 hours
        """
        queued_count = 0
        for network in wps_networks:
            if network.get('wps_locked', False):
                continue  # Skip locked WPS networks

            # Try Pixie Dust first (much faster, 2-10 minutes)
            job = AttackJob(
                AttackType.WPS_PIXIE,
                network['bssid'],
                {
                    'ssid': network.get('ssid', ''),
                    'channel': network.get('channel', ''),
                    'priority': priority + 2,  # Pixie has highest priority (22)
                    'estimated_duration': 600,  # 10 minutes
                    'max_attempts': 1
                }
            )
            self.add_job(job)
            queued_count += 1

            # Queue full PIN bruteforce as backup (4-10 hours)
            job = AttackJob(
                AttackType.WPS_PIN,
                network['bssid'],
                {
                    'ssid': network.get('ssid', ''),
                    'channel': network.get('channel', ''),
                    'priority': priority,  # Still high priority (20)
                    'estimated_duration': 28800,  # 8 hours
                    'max_attempts': 1
                }
            )
            self.add_job(job)
            queued_count += 1

        print(f"[QUEUE] Auto-queued {queued_count} WPS attacks for {len(wps_networks)} networks")
        return queued_count

    def auto_queue_wpa_attacks(self, wpa_networks: List[dict], priority: int = 6,
                               handshake_files: dict = None):
        """
        Automatically queue WPA/WPA2 cracking attacks
        wpa_networks: List of dicts with 'bssid', 'ssid', 'channel', 'encryption'
        handshake_files: Dict mapping bssid -> handshake file path
        """
        queued_count = 0

        for network in wpa_networks:
            bssid = network['bssid']
            encryption = network.get('encryption', 'WPA2')

            # Check if we have a handshake file
            handshake_file = None
            if handshake_files:
                handshake_file = handshake_files.get(bssid)

            if not handshake_file:
                # Need to capture handshake first
                job = AttackJob(
                    AttackType.HANDSHAKE_CAPTURE,
                    bssid,
                    {
                        'ssid': network.get('ssid', ''),
                        'channel': network.get('channel', ''),
                        'priority': priority + 1,  # Capture first
                        'estimated_duration': 300,  # 5 minutes
                        'max_attempts': 2
                    }
                )
                self.add_job(job)
                queued_count += 1

            # Queue WPA crack (will wait for handshake if needed)
            attack_type = AttackType.WPA2_CRACK if 'WPA2' in encryption else AttackType.WPA_CRACK
            job = AttackJob(
                attack_type,
                bssid,
                {
                    'ssid': network.get('ssid', ''),
                    'channel': network.get('channel', ''),
                    'encryption': encryption,
                    'handshake_file': handshake_file,
                    'priority': priority,
                    'estimated_duration': 3600,  # 1 hour (depends on wordlist size)
                    'max_attempts': 1,
                    'wordlist_size': 10000000  # 10M passwords
                }
            )
            self.add_job(job)
            queued_count += 1

        print(f"[QUEUE] Auto-queued {queued_count} WPA/WPA2 attacks for {len(wpa_networks)} networks")
        return queued_count

    def auto_queue_wep_attacks(self, wep_networks: List[dict], priority: int = 21):
        """
        Automatically queue WEP cracking attacks
        wep_networks: List of dicts with 'bssid', 'ssid', 'channel'

        WEP gets VERY HIGH priority (21) - second only to WPS
        - Attack time: 5-30 minutes (much faster than WPA!)
        - Success rate: 100% (always crackable)
        - Requirements: 20k-40k IVs via packet injection
        """
        queued_count = 0

        for network in wep_networks:
            job = AttackJob(
                AttackType.WEP_CRACK,
                network['bssid'],
                {
                    'ssid': network.get('ssid', ''),
                    'channel': network.get('channel', ''),
                    'priority': priority,
                    'estimated_duration': 1800,  # 30 minutes
                    'max_attempts': 2,
                    'use_arp_replay': True
                }
            )
            self.add_job(job)
            queued_count += 1

        print(f"[QUEUE] Auto-queued {queued_count} WEP attacks for {len(wep_networks)} networks")
        return queued_count

    def auto_queue_deauth_attacks(self, targets: List[dict], priority: int = 5):
        """
        Automatically queue deauth attacks
        targets: List of dicts with 'bssid', 'ssid', 'client_mac' (optional)
        """
        queued_count = 0

        for target in targets:
            job = AttackJob(
                AttackType.DEAUTH,
                target['bssid'],
                {
                    'ssid': target.get('ssid', ''),
                    'client_mac': target.get('client_mac'),
                    'priority': priority,
                    'estimated_duration': 60,  # 1 minute
                    'max_attempts': 1,
                    'count': 10  # Number of deauth packets
                }
            )
            self.add_job(job)
            queued_count += 1

        print(f"[QUEUE] Auto-queued {queued_count} deauth attacks")
        return queued_count
