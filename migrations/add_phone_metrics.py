#!/usr/bin/env python3
"""
Migration: Add phone metrics logging tables
Creates tables for logging GPS, battery, weather, and system metrics from connected phones
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def migrate(db_path):
    """Add phone metrics tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("[*] Creating phone_metrics_gps table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phone_metrics_gps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            altitude REAL,
            accuracy REAL,
            source TEXT,
            fix_mode INTEGER,
            satellites INTEGER
        )
    ''')

    # Index for time-based queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_gps_timestamp
        ON phone_metrics_gps(timestamp DESC)
    ''')

    print("[*] Creating phone_metrics_battery table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phone_metrics_battery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            level INTEGER NOT NULL,
            status TEXT,
            temperature REAL,
            voltage REAL,
            health TEXT
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_battery_timestamp
        ON phone_metrics_battery(timestamp DESC)
    ''')

    print("[*] Creating phone_metrics_weather table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phone_metrics_weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            temperature_f REAL,
            feels_like_f REAL,
            humidity INTEGER,
            condition TEXT,
            wind_speed_mph REAL,
            wind_direction INTEGER,
            precipitation REAL
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_weather_timestamp
        ON phone_metrics_weather(timestamp DESC)
    ''')

    print("[*] Creating phone_metrics_system table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phone_metrics_system (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            device_model TEXT,
            device_manufacturer TEXT,
            android_version TEXT,
            android_sdk TEXT,
            wifi_enabled BOOLEAN,
            wifi_ssid TEXT,
            wifi_bssid TEXT,
            wifi_rssi INTEGER,
            wifi_frequency INTEGER,
            bluetooth_enabled BOOLEAN,
            screen_on BOOLEAN,
            cpu_temp REAL,
            storage_used_gb REAL,
            storage_total_gb REAL,
            ram_used_mb INTEGER,
            ram_total_mb INTEGER
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_system_timestamp
        ON phone_metrics_system(timestamp DESC)
    ''')

    # Add GPS coordinates to network_observations if not present
    print("[*] Checking network_observations table for GPS columns...")
    cursor.execute("PRAGMA table_info(network_observations)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'latitude' not in columns:
        print("[*] Adding GPS columns to network_observations...")
        cursor.execute('ALTER TABLE network_observations ADD COLUMN latitude REAL')
        cursor.execute('ALTER TABLE network_observations ADD COLUMN longitude REAL')
        cursor.execute('ALTER TABLE network_observations ADD COLUMN altitude REAL')
        cursor.execute('ALTER TABLE network_observations ADD COLUMN gps_accuracy REAL')

        # Index for location-based queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_network_location
            ON network_observations(latitude, longitude)
        ''')

    conn.commit()
    conn.close()

    print("[+] Migration completed successfully!")


if __name__ == '__main__':
    # Database path
    db_path = PROJECT_ROOT / 'data' / 'database' / 'gattrose.db'

    if not db_path.exists():
        print(f"[!] Database not found at {db_path}")
        sys.exit(1)

    print(f"[*] Running migration on {db_path}")
    migrate(str(db_path))
