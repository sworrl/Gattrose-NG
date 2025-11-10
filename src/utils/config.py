"""
Configuration management for Gattrose
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Configuration manager"""

    DEFAULT_CONFIG = {
        'app': {
            'theme': 'sonic',  # Default: Sonic the Hedgehog theme
            'time_format': '24h',  # Always 24-hour, never change
            'auto_update_check': True,
        },
        'database': {
            'auto_backup': True,
            'backup_interval_days': 7,
        },
        'scanning': {
            'default_timeout': 300,
            'auto_change_channel': True,
            'channel_hop_interval': 2,
        },
        'tools': {
            'wordlist_path': '/usr/share/wordlists/rockyou.txt',
            'capture_path': None,  # Auto-determined
        },
        'wigle': {
            'auto_import': False,
            'import_path': None,
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration

        Args:
            config_path: Path to config file. If None, uses default location.
        """
        if config_path is None:
            config_path = self._get_default_config_path()

        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}

        self._load_config()

    def _get_default_config_path(self) -> Path:
        """Get default configuration file path"""
        project_root = Path(os.environ.get('GATTROSE_NG_ROOT', Path.cwd()))
        is_portable = os.environ.get('GATTROSE_NG_PORTABLE', '1') == '1'

        if is_portable:
            # Portable mode: config in project directory
            config_dir = project_root / "config"
        else:
            # Installed mode: config in user's home directory
            config_dir = Path.home() / ".config" / "gattrose-ng"

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.yaml"

    def _load_config(self):
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[!] Error loading config: {e}")
                self.config = {}
        else:
            # Use defaults
            self.config = {}

        # Merge with defaults
        self.config = self._merge_with_defaults(self.config, self.DEFAULT_CONFIG)

        # Ensure 24-hour time format
        self.config['app']['time_format'] = '24h'

    def _merge_with_defaults(self, config: Dict, defaults: Dict) -> Dict:
        """Recursively merge config with defaults"""
        result = defaults.copy()

        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_with_defaults(value, result[key])
            else:
                result[key] = value

        return result

    def save(self):
        """Save configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)

            print(f"[+] Configuration saved to {self.config_path}")
            return True

        except Exception as e:
            print(f"[!] Error saving config: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key_path: Configuration key path (e.g., 'app.theme')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation

        Args:
            key_path: Configuration key path (e.g., 'app.theme')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self.config

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value
        config[keys[-1]] = value
