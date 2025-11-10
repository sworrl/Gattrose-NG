#!/usr/bin/env python3
"""
Migration: Add cracking-related columns to networks table
Adds: wps_pin, is_cracked, cracked_at, password, crack_method
"""

import sqlite3
import sys
from pathlib import Path

def migrate(db_path: str):
    """Add cracking columns to networks table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Migrating database: {db_path}")

    # List of columns to add
    columns_to_add = [
        ("wps_pin", "VARCHAR(8)"),
        ("is_cracked", "BOOLEAN DEFAULT 0"),
        ("cracked_at", "DATETIME"),
        ("password", "VARCHAR(63)"),
        ("crack_method", "VARCHAR(50)")
    ]

    # Get existing columns
    cursor.execute("PRAGMA table_info(networks)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add missing columns
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"  Adding column: {col_name} {col_type}")
            cursor.execute(f"ALTER TABLE networks ADD COLUMN {col_name} {col_type}")
        else:
            print(f"  Skipping {col_name} (already exists)")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")


if __name__ == "__main__":
    # Migrate both databases
    databases = [
        "/opt/gattrose-ng/data/database/gattrose.db",
        "/home/eurrl/Documents/Code & Scripts/gattrose-ng/data/database/gattrose.db"
    ]

    for db_path in databases:
        if Path(db_path).exists():
            migrate(db_path)
        else:
            print(f"Skipping {db_path} (does not exist)")
