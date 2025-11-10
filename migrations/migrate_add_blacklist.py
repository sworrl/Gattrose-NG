#!/usr/bin/env python3
"""
Database Migration: Add blacklist columns to networks table
Adds blacklisted and blacklist_reason fields
"""

import sqlite3
import sys
from pathlib import Path


def migrate_database(db_path: str):
    """Add blacklist columns to networks table"""

    print(f"[*] Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Add blacklisted column
        print("[*] Adding blacklisted column to networks table...")
        try:
            cursor.execute("ALTER TABLE networks ADD COLUMN blacklisted BOOLEAN DEFAULT 0 NOT NULL")
            conn.commit()
            print("  [✓] Column added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  [i] Column already exists")
            else:
                raise

        # 2. Add blacklist_reason column
        print("[*] Adding blacklist_reason column to networks table...")
        try:
            cursor.execute("ALTER TABLE networks ADD COLUMN blacklist_reason TEXT")
            conn.commit()
            print("  [✓] Column added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  [i] Column already exists")
            else:
                raise

        # 3. Create index for blacklisted column
        print("[*] Creating index for blacklisted column...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_networks_blacklisted ON networks(blacklisted)")
        conn.commit()
        print("  [✓] Index created")

        print("[✓] Migration completed successfully!")
        return True

    except Exception as e:
        print(f"[✗] Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = Path.cwd() / "data" / "database" / "gattrose.db"

    if not db_path.exists():
        print(f"[✗] Database not found: {db_path}")
        sys.exit(1)

    # Backup first
    import shutil
    backup_path = db_path.with_suffix('.db.blacklist_backup')
    print(f"[*] Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("[✓] Backup created")

    success = migrate_database(str(db_path))
    sys.exit(0 if success else 1)
