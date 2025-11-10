#!/usr/bin/env python3
"""
Event Manager for Gattrose-NG
Handles event logging and notification system for toast popups
Supports both file-based events (for tray) and Qt signals (for GUI)
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque
import threading

# Optional Qt support for real-time GUI updates
try:
    from PyQt6.QtCore import QObject, pyqtSignal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object  # Fallback


class Event:
    """Represents a single event"""

    def __init__(self, event_type: str, title: str, message: str, urgency: str = "normal", metadata: Optional[Dict] = None):
        """
        Create an event

        Args:
            event_type: Type of event (network_new, client_new, handshake, error, etc.)
            title: Short title for notification
            message: Detailed message
            urgency: low, normal, critical
            metadata: Additional event data
        """
        self.event_type = event_type
        self.title = title
        self.message = message
        self.urgency = urgency
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.id = f"{event_type}_{int(time.time() * 1000000)}"  # Microsecond precision

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'type': self.event_type,
            'title': self.title,
            'message': self.message,
            'urgency': self.urgency,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class EventManager(QObject if QT_AVAILABLE else object):
    """
    Centralized event manager for Gattrose-NG

    Events are written to /tmp/gattrose-events.json for tray icon to consume
    Also emits Qt signals for real-time GUI updates (if Qt available)
    """

    # Qt Signals for real-time GUI updates (only defined if Qt available)
    if QT_AVAILABLE:
        # Data change signals (emit immediately when data changes)
        network_added = pyqtSignal(dict)  # {bssid, ssid, encryption, power, ...}
        network_updated = pyqtSignal(dict)  # {bssid, ssid, encryption, power, ...}
        client_added = pyqtSignal(dict)  # {mac, bssid, power, ...}
        client_updated = pyqtSignal(dict)  # {mac, bssid, power, ...}
        client_removed = pyqtSignal(str)  # mac_address

        # Attack/handshake signals
        handshake_captured = pyqtSignal(dict)  # {bssid, ssid, file_path}
        attack_started = pyqtSignal(str, str, str)  # attack_type, bssid, ssid
        attack_finished = pyqtSignal(str, str, str, bool)  # attack_type, bssid, ssid, success

        # Service status signals
        service_status_changed = pyqtSignal(str, str)  # service_name, status

        # Error signals
        error_occurred = pyqtSignal(str, str)  # title, message

    def __init__(self, max_events: int = 100):
        """
        Initialize event manager

        Args:
            max_events: Maximum events to keep in file (rolling buffer)
        """
        if QT_AVAILABLE:
            super().__init__()

        self.events_file = Path("/tmp/gattrose-events.json")
        self.max_events = max_events
        self._lock = threading.RLock()

        # Event tracking for deduplication
        self._seen_networks = set()  # Track BSSID
        self._seen_clients = set()   # Track MAC
        self._last_event_time = {}   # Track event type timestamps for rate limiting

        # Rate limiting (seconds between same event type)
        self.rate_limits = {
            'network_new': 0.0,      # No rate limit for Qt signals
            'client_new': 0.0,       # No rate limit for Qt signals
            'client_left': 0.0,      # No rate limit for Qt signals
            'handshake': 0.0,        # Immediate
            'error': 0.5,            # Max 2 per second
            'service_status': 2.0,   # Max 1 per 2 seconds
        }

        # Initialize events file
        self._init_events_file()

    def _init_events_file(self):
        """Initialize empty events file"""
        with self._lock:
            if not self.events_file.exists():
                self._write_events([])

    def _read_events(self) -> List[Dict]:
        """Read events from file"""
        try:
            with open(self.events_file, 'r') as f:
                data = json.load(f)
                return data.get('events', [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write_events(self, events: List[Dict]):
        """Write events to file"""
        import os
        import stat

        data = {
            'last_update': datetime.now().isoformat(),
            'event_count': len(events),
            'events': events
        }

        try:
            # Atomic write using temp file
            temp_file = self.events_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

            # Set world-writable permissions so both root and user can access
            os.chmod(temp_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)

            temp_file.replace(self.events_file)

            # Set permissions on final file too
            os.chmod(self.events_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
        except PermissionError as e:
            # Silently ignore permission errors (file owned by different user)
            pass
        except Exception as e:
            print(f"[!] Error writing events: {e}")

    def _should_emit(self, event_type: str) -> bool:
        """Check if event should be emitted based on rate limiting"""
        rate_limit = self.rate_limits.get(event_type, 1.0)
        last_time = self._last_event_time.get(event_type, 0)
        current_time = time.time()

        if current_time - last_time >= rate_limit:
            self._last_event_time[event_type] = current_time
            return True
        return False

    def emit_event(self, event: Event) -> bool:
        """
        Emit an event to the notification system

        Args:
            event: Event to emit

        Returns:
            True if event was emitted, False if rate limited
        """
        with self._lock:
            # Rate limiting
            if not self._should_emit(event.event_type):
                return False

            # Read existing events
            events = self._read_events()

            # Add new event
            events.append(event.to_dict())

            # Trim to max size (keep most recent)
            if len(events) > self.max_events:
                events = events[-self.max_events:]

            # Write back
            self._write_events(events)
            return True

    def emit_network_discovered(self, bssid: str, ssid: str, encryption: str, power: int):
        """Emit new network discovered event"""
        # Deduplication
        if bssid in self._seen_networks:
            return

        self._seen_networks.add(bssid)

        ssid_display = ssid if ssid else "(hidden)"
        event = Event(
            event_type='network_new',
            title=f"New Network: {ssid_display}",
            message=f"BSSID: {bssid}\nEncryption: {encryption}\nPower: {power} dBm",
            urgency='normal',
            metadata={'bssid': bssid, 'ssid': ssid, 'encryption': encryption, 'power': power}
        )
        self.emit_event(event)

    def emit_client_discovered(self, mac: str, bssid: str, power: int):
        """Emit new client discovered event"""
        # Deduplication
        if mac in self._seen_clients:
            return

        self._seen_clients.add(mac)

        event = Event(
            event_type='client_new',
            title=f"New Client: {mac[:17]}",
            message=f"Connected to: {bssid}\nPower: {power} dBm",
            urgency='normal',
            metadata={'mac': mac, 'bssid': bssid, 'power': power}
        )
        self.emit_event(event)

    def emit_client_left(self, mac: str, bssid: str):
        """Emit client left event (with deadzone time check)"""
        event = Event(
            event_type='client_left',
            title=f"Client Left: {mac[:17]}",
            message=f"Disconnected from: {bssid}",
            urgency='low',
            metadata={'mac': mac, 'bssid': bssid}
        )
        self.emit_event(event)

    def emit_handshake_captured(self, bssid: str, ssid: str):
        """Emit handshake captured event"""
        ssid_display = ssid if ssid else "(hidden)"
        event = Event(
            event_type='handshake',
            title=f"🤝 Handshake Captured!",
            message=f"Network: {ssid_display}\nBSSID: {bssid}",
            urgency='critical',
            metadata={'bssid': bssid, 'ssid': ssid}
        )
        self.emit_event(event)

    def emit_error(self, title: str, message: str, error_type: str = "general"):
        """Emit error event"""
        event = Event(
            event_type='error',
            title=f"Error: {title}",
            message=message,
            urgency='critical',
            metadata={'error_type': error_type}
        )
        self.emit_event(event)

    def emit_service_status(self, service: str, status: str, message: str):
        """Emit service status change event"""
        event = Event(
            event_type='service_status',
            title=f"{service}: {status}",
            message=message,
            urgency='normal' if status == 'running' else 'critical',
            metadata={'service': service, 'status': status}
        )
        self.emit_event(event)

    def emit_attack_started(self, attack_type: str, bssid: str, ssid: str):
        """Emit attack started event"""
        ssid_display = ssid if ssid else "(hidden)"
        event = Event(
            event_type='attack_started',
            title=f"Attack Started: {attack_type}",
            message=f"Target: {ssid_display}\nBSSID: {bssid}",
            urgency='normal',
            metadata={'attack_type': attack_type, 'bssid': bssid, 'ssid': ssid}
        )
        self.emit_event(event)

    def emit_attack_finished(self, attack_type: str, bssid: str, ssid: str, success: bool):
        """Emit attack finished event"""
        ssid_display = ssid if ssid else "(hidden)"
        status = "Success" if success else "Failed"
        event = Event(
            event_type='attack_finished',
            title=f"{attack_type} {status}",
            message=f"Target: {ssid_display}\nBSSID: {bssid}",
            urgency='normal',
            metadata={'attack_type': attack_type, 'bssid': bssid, 'ssid': ssid, 'success': success}
        )
        self.emit_event(event)

    def emit_password_cracked(self, bssid: str, ssid: str, password: str, crack_method: str):
        """Emit password cracked event"""
        ssid_display = ssid if ssid else "(hidden)"
        event = Event(
            event_type='password_cracked',
            title=f"Password Found: {ssid_display}",
            message=f"BSSID: {bssid}\nPassword: {password}\nMethod: {crack_method}",
            urgency='critical',
            metadata={'bssid': bssid, 'ssid': ssid, 'password': password, 'crack_method': crack_method}
        )
        self.emit_event(event)

    def clear_events(self):
        """Clear all events"""
        with self._lock:
            self._write_events([])

    def reset_seen_networks(self):
        """Reset seen networks (for new scan sessions)"""
        with self._lock:
            self._seen_networks.clear()

    def reset_seen_clients(self):
        """Reset seen clients (for new scan sessions)"""
        with self._lock:
            self._seen_clients.clear()


# Global event manager instance
_event_manager = None
_event_manager_lock = threading.Lock()


def get_event_manager() -> EventManager:
    """Get global event manager instance (singleton)"""
    global _event_manager

    with _event_manager_lock:
        if _event_manager is None:
            _event_manager = EventManager()
        return _event_manager
