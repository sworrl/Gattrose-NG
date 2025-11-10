#!/usr/bin/env python3
"""
Migration: Add serial column to scan_sessions table
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import generate_serial_number

DB_PATH = PROJECT_ROOT / "data" / "gattrose-ng.db"


def migrate():
    """Add serial column to scan_sessions table"""
    if not DB_PATH.exists():
        print(f"[!] Database not found: {DB_PATH}")
        return 1

    print(f"[*] Migrating database: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # Check if serial column already exists
        cursor.execute("PRAGMA table_info(scan_sessions)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'serial' in columns:
            print("[*] serial column already exists in scan_sessions table")
            return 0

        # Add serial column to scan_sessions table
        print("[*] Adding serial column to scan_sessions table...")
        cursor.execute("ALTER TABLE scan_sessions ADD COLUMN serial TEXT")

        # Generate serial numbers for existing scan sessions
        cursor.execute("SELECT id FROM scan_sessions WHERE serial IS NULL OR serial = ''")
        rows = cursor.fetchall()

        print(f"[*] Generating serial numbers for {len(rows)} existing scan sessions...")
        for row in rows:
            scan_id = row[0]
            serial = generate_serial_number("scan")
            cursor.execute("UPDATE scan_sessions SET serial = ? WHERE id = ?", (serial, scan_id))

        # Create unique index on serial column
        print("[*] Creating unique index on serial column...")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_scan_sessions_serial ON scan_sessions(serial)")

        conn.commit()
        print("[✓] Migration complete!")
        print(f"    - Added serial column to scan_sessions")
        print(f"    - Generated {len(rows)} serial numbers")
        print(f"    - Created unique index")

        return 0

    except Exception as e:
        print(f"[!] Migration failed: {e}")
        conn.rollback()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(migrate())
