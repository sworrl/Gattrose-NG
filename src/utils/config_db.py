"""
Database-based configuration management for Gattrose-NG
Replaces YAML config files with database storage
"""

from typing import Any, Optional
from ..database.manager import DatabaseManager
from ..database.models import Setting


class DBConfig:
    """Database-backed configuration manager

    All settings are stored in the database instead of flat files.
    Settings are key-value pairs with type information.
    """

    # Default configuration values
    DEFAULT_SETTINGS = {
        # Application settings
        'app.theme': ('sonic', 'string', 'app', 'UI theme name'),
        'app.time_format': ('24h', 'string', 'app', '24-hour time format (always 24h)'),
        'app.auto_update_check': ('true', 'bool', 'app', 'Check for updates automatically'),
        'app.window_width': ('1200', 'int', 'app', 'Main window width'),
        'app.window_height': ('800', 'int', 'app', 'Main window height'),

        # Database settings
        'database.auto_backup': ('true', 'bool', 'database', 'Automatically backup database'),
        'database.backup_interval_days': ('7', 'int', 'database', 'Days between automatic backups'),
        'database.backup_path': ('data/backups', 'string', 'database', 'Backup directory path'),

        # WiFi scanning settings
        'wifi.default_timeout': ('300', 'int', 'wifi', 'Default scan timeout (seconds)'),
        'wifi.auto_change_channel': ('true', 'bool', 'wifi', 'Auto channel hopping'),
        'wifi.channel_hop_interval': ('2', 'int', 'wifi', 'Channel hop interval (seconds)'),
        'wifi.auto_start_scan': ('true', 'bool', 'wifi', 'Auto-start scanning on launch'),
        'wifi.save_captures': ('true', 'bool', 'wifi', 'Save capture files to disk'),
        'wifi.capture_path': ('data/captures', 'string', 'wifi', 'Capture file directory'),

        # Bluetooth scanning settings
        'bluetooth.enabled': ('true', 'bool', 'bluetooth', 'Enable Bluetooth scanning'),
        'bluetooth.scan_interval': ('10', 'int', 'bluetooth', 'Scan interval (seconds)'),
        'bluetooth.save_devices': ('true', 'bool', 'bluetooth', 'Save discovered devices'),

        # SDR settings
        'sdr.enabled': ('true', 'bool', 'sdr', 'Enable SDR scanning'),
        'sdr.default_frequency': ('100000000', 'int', 'sdr', 'Default frequency (Hz)'),
        'sdr.sample_rate': ('2048000', 'int', 'sdr', 'Sample rate (Hz)'),

        # Service settings
        'service.enabled': ('false', 'bool', 'service', 'Run as background service'),
        'service.auto_start': ('false', 'bool', 'service', 'Start service at boot'),
        'service.scan_24_7': ('false', 'bool', 'service', 'Continuous 24/7 scanning'),

        # Tools settings
        'tools.wordlist_path': ('/usr/share/wordlists/rockyou.txt', 'string', 'tools', 'Default wordlist path'),

        # WiGLE integration
        'wigle.auto_import': ('false', 'bool', 'wigle', 'Auto-import WiGLE data'),
        'wigle.import_path': ('', 'string', 'wigle', 'WiGLE import directory'),
        'wigle.api_key': ('', 'string', 'wigle', 'WiGLE API key'),
    }

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize database configuration

        Args:
            db_manager: DatabaseManager instance. If None, creates new one.
        """
        if db_manager is None:
            self.db = DatabaseManager()
        else:
            self.db = db_manager

        # Initialize default settings if not exist
        self._init_defaults()

    def _init_defaults(self):
        """Initialize default settings in database if they don't exist"""
        with self.db.get_session() as session:
            for key, (default_value, value_type, category, description) in self.DEFAULT_SETTINGS.items():
                # Check if setting exists
                existing = session.query(Setting).filter(Setting.key == key).first()

                if not existing:
                    # Create new setting with default value
                    setting = Setting(
                        key=key,
                        value=default_value,
                        value_type=value_type,
                        category=category,
                        description=description,
                        default_value=default_value
                    )
                    session.add(setting)

            session.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value

        Args:
            key: Setting key (e.g., 'app.theme')
            default: Default value if setting doesn't exist

        Returns:
            Setting value with proper type
        """
        with self.db.get_session() as session:
            setting = session.query(Setting).filter(Setting.key == key).first()

            if setting:
                return setting.get_value()
            else:
                # Check if it's in defaults
                if key in self.DEFAULT_SETTINGS:
                    return self.DEFAULT_SETTINGS[key][0]
                return default

    def set(self, key: str, value: Any, value_type: str = 'string', category: str = 'app', description: str = ''):
        """
        Set setting value

        Args:
            key: Setting key (e.g., 'app.theme')
            value: Value to set
            value_type: Type of value ('string', 'int', 'float', 'bool', 'json')
            category: Setting category
            description: Human-readable description
        """
        with self.db.get_session() as session:
            setting = session.query(Setting).filter(Setting.key == key).first()

            if setting:
                # Update existing setting
                setting.set_value(value)
            else:
                # Create new setting
                setting = Setting(
                    key=key,
                    value_type=value_type,
                    category=category,
                    description=description
                )
                setting.set_value(value)
                session.add(setting)

            session.commit()

    def delete(self, key: str):
        """Delete a setting"""
        with self.db.get_session() as session:
            setting = session.query(Setting).filter(Setting.key == key).first()
            if setting:
                session.delete(setting)
                session.commit()

    def get_category(self, category: str) -> dict:
        """
        Get all settings in a category

        Args:
            category: Category name (e.g., 'app', 'wifi', 'bluetooth')

        Returns:
            Dictionary of {key: value} for all settings in category
        """
        with self.db.get_session() as session:
            settings = session.query(Setting).filter(Setting.category == category).all()

            result = {}
            for setting in settings:
                # Remove category prefix from key
                short_key = setting.key.replace(f"{category}.", "", 1)
                result[short_key] = setting.get_value()

            return result

    def get_all(self) -> dict:
        """Get all settings as a nested dictionary"""
        with self.db.get_session() as session:
            settings = session.query(Setting).all()

            result = {}
            for setting in settings:
                # Split key by dots to create nested structure
                parts = setting.key.split('.')

                current = result
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                current[parts[-1]] = setting.get_value()

            return result

    def reset_to_defaults(self):
        """Reset all settings to default values"""
        with self.db.get_session() as session:
            for key, (default_value, value_type, category, description) in self.DEFAULT_SETTINGS.items():
                setting = session.query(Setting).filter(Setting.key == key).first()

                if setting:
                    setting.value = default_value
                else:
                    # Create if missing
                    setting = Setting(
                        key=key,
                        value=default_value,
                        value_type=value_type,
                        category=category,
                        description=description,
                        default_value=default_value
                    )
                    session.add(setting)

            session.commit()

    def export_to_dict(self) -> dict:
        """Export all settings as a flat dictionary (for backup/export)"""
        with self.db.get_session() as session:
            settings = session.query(Setting).all()

            return {
                setting.key: {
                    'value': setting.get_value(),
                    'type': setting.value_type,
                    'category': setting.category,
                    'description': setting.description
                }
                for setting in settings
            }

    def import_from_dict(self, data: dict):
        """Import settings from dictionary (for restore/import)"""
        with self.db.get_session() as session:
            for key, info in data.items():
                setting = session.query(Setting).filter(Setting.key == key).first()

                if setting:
                    setting.set_value(info['value'])
                    if 'type' in info:
                        setting.value_type = info['type']
                    if 'category' in info:
                        setting.category = info['category']
                    if 'description' in info:
                        setting.description = info['description']
                else:
                    setting = Setting(
                        key=key,
                        value_type=info.get('type', 'string'),
                        category=info.get('category', 'app'),
                        description=info.get('description', '')
                    )
                    setting.set_value(info['value'])
                    session.add(setting)

            session.commit()


# For backward compatibility with old Config class
class Config(DBConfig):
    """Backward compatible configuration class

    Migrates from YAML to database automatically.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize and migrate from YAML if needed"""
        super().__init__()

        # If YAML config exists, migrate it
        if config_path:
            import os
            from pathlib import Path
            yaml_path = Path(config_path)

            if yaml_path.exists():
                self._migrate_from_yaml(yaml_path)

    def _migrate_from_yaml(self, yaml_path):
        """Migrate settings from YAML file to database"""
        try:
            import yaml

            with open(yaml_path, 'r') as f:
                yaml_config = yaml.safe_load(f) or {}

            # Flatten YAML structure and import
            def flatten_dict(d, parent_key='', sep='.'):
                items = []
                for k, v in d.items():
                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, new_key, sep=sep).items())
                    else:
                        items.append((new_key, v))
                return dict(items)

            flat_config = flatten_dict(yaml_config)

            # Determine type for each value
            for key, value in flat_config.items():
                if isinstance(value, bool):
                    value_type = 'bool'
                elif isinstance(value, int):
                    value_type = 'int'
                elif isinstance(value, float):
                    value_type = 'float'
                else:
                    value_type = 'string'

                category = key.split('.')[0] if '.' in key else 'app'

                self.set(key, value, value_type=value_type, category=category)

            print(f"[+] Migrated {len(flat_config)} settings from YAML to database")

            # Optionally backup old YAML file
            import shutil
            backup_path = str(yaml_path) + ".bak"
            shutil.copy(yaml_path, backup_path)
            print(f"[+] Backed up YAML config to: {backup_path}")

        except Exception as e:
            print(f"[!] Error migrating YAML config: {e}")

    def save(self):
        """No-op for compatibility (database auto-saves)"""
        pass
