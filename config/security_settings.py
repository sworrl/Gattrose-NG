"""
Security Settings Configuration
Manages security-related settings for IMSI detection, auto-blacklist, etc.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class SecuritySettings:
    """Security settings manager with persistent storage"""

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize security settings

        Args:
            config_file: Path to config file (default: /opt/gattrose-ng/data/config/security_settings.json)
        """
        if config_file is None:
            config_file = Path('/opt/gattrose-ng/data/config/security_settings.json')

        self.config_file = config_file
        self.events_file = self.config_file.parent / 'cellular_security_events.json'

        # Default settings
        self.defaults = {
            'imsi_detection_enabled': True,
            'imsi_log_events': True,
            'imsi_alert_on_detection': True,
            'auto_blacklist_enabled': True,
            'auto_blacklist_phone_wifi': True,
            'alert_sound_enabled': False,
            'min_alert_severity': 'medium',  # 'low', 'medium', 'high', 'critical'
            'tower_change_alert_threshold': 5,  # Number of changes before alerting
            'signal_anomaly_threshold': -40,  # dBm
            'network_downgrade_alert': True,
            'location_mismatch_alert': True,
            'rapid_change_window_minutes': 5,
        }

        self._settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (in case new settings added)
                    return {**self.defaults, **loaded}
            except Exception as e:
                print(f"[!] Error loading security settings: {e}, using defaults")

        # Create config directory if needed
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        return self.defaults.copy()

    def _save_settings(self):
        """Save current settings to file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            print(f"[!] Error saving security settings: {e}")

    def get(self, key: str, default=None) -> Any:
        """Get a setting value"""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        """Set a setting value and save"""
        self._settings[key] = value
        self._save_settings()

    def update(self, updates: Dict[str, Any]):
        """Update multiple settings at once"""
        self._settings.update(updates)
        self._save_settings()

    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self._settings = self.defaults.copy()
        self._save_settings()

    def add_cellular_event(self, event: Dict):
        """Log a cellular security event"""
        try:
            # Load existing events
            events = []
            if self.events_file.exists():
                with open(self.events_file, 'r') as f:
                    events = json.load(f)

            # Add timestamp if not present
            if 'timestamp' not in event:
                event['timestamp'] = datetime.now().isoformat()

            # Add new event
            events.append(event)

            # Keep last 1000 events
            if len(events) > 1000:
                events = events[-1000:]

            # Save
            self.events_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.events_file, 'w') as f:
                json.dump(events, f, indent=2)

        except Exception as e:
            print(f"[!] Error logging cellular event: {e}")

    def get_cellular_events(self, limit: int = 100) -> list:
        """Get recent cellular security events"""
        try:
            if self.events_file.exists():
                with open(self.events_file, 'r') as f:
                    events = json.load(f)
                    return events[-limit:]
        except Exception as e:
            print(f"[!] Error reading cellular events: {e}")

        return []

    def clear_cellular_events(self):
        """Clear all cellular security events"""
        try:
            if self.events_file.exists():
                self.events_file.unlink()
        except Exception as e:
            print(f"[!] Error clearing cellular events: {e}")

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings"""
        return self._settings.copy()

    def __repr__(self):
        return f"SecuritySettings(file={self.config_file}, enabled={self.get('imsi_detection_enabled')})"


# Global settings instance
_settings_instance = None


def get_security_settings(config_file: Optional[Path] = None) -> SecuritySettings:
    """
    Get or create the global security settings instance

    Args:
        config_file: Optional custom config file path

    Returns:
        SecuritySettings instance
    """
    global _settings_instance

    if _settings_instance is None:
        _settings_instance = SecuritySettings(config_file)

    return _settings_instance


def reset_security_settings():
    """Reset the global settings instance (useful for testing)"""
    global _settings_instance
    _settings_instance = None
