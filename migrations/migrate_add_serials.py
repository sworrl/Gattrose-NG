#!/usr/bin/env python3
"""
Database Migration: Add serial columns to all tables
Adds serial number fields to clients, handshakes, wigle_imports, and oui_updates tables
"""

import sqlite3
import sys
from pathlib import Path
from src.utils.serial import generate_serial


def migrate_database(db_path: str):
    """Add serial columns to tables that are missing them"""

    print(f"[*] Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Add serial column to clients table (without UNIQUE - will add index later)
        print("[*] Adding serial column to clients table...")
        try:
            cursor.execute("ALTER TABLE clients ADD COLUMN serial VARCHAR(20)")
            conn.commit()
            print("  [✓] Column added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  [i] Column already exists")
            else:
                raise

        # Generate serials for existing clients
        cursor.execute("SELECT id FROM clients WHERE serial IS NULL")
        clients = cursor.fetchall()
        print(f"  [*] Generating serials for {len(clients)} existing clients...")
        for (client_id,) in clients:
            serial = generate_serial("cl")
            cursor.execute("UPDATE clients SET serial = ? WHERE id = ?", (serial, client_id))
        conn.commit()
        print(f"  [✓] Generated {len(clients)} client serials")

        # 2. Add serial column to handshakes table (without UNIQUE - will add index later)
        print("[*] Adding serial column to handshakes table...")
        try:
            cursor.execute("ALTER TABLE handshakes ADD COLUMN serial VARCHAR(20)")
            conn.commit()
            print("  [✓] Column added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  [i] Column already exists")
            else:
                raise

        # Generate serials for existing handshakes
        cursor.execute("SELECT id FROM handshakes WHERE serial IS NULL")
        handshakes = cursor.fetchall()
        print(f"  [*] Generating serials for {len(handshakes)} existing handshakes...")
        for (hs_id,) in handshakes:
            serial = generate_serial("hs")
            cursor.execute("UPDATE handshakes SET serial = ? WHERE id = ?", (serial, hs_id))
        conn.commit()
        print(f"  [✓] Generated {len(handshakes)} handshake serials")

        # 3. Add serial column to wigle_imports table (without UNIQUE - will add index later)
        print("[*] Adding serial column to wigle_imports table...")
        try:
            cursor.execute("ALTER TABLE wigle_imports ADD COLUMN serial VARCHAR(20)")
            conn.commit()
            print("  [✓] Column added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  [i] Column already exists")
            else:
                raise

        # Generate serials for existing wigle_imports
        cursor.execute("SELECT id FROM wigle_imports WHERE serial IS NULL")
        imports = cursor.fetchall()
        print(f"  [*] Generating serials for {len(imports)} existing WiGLE imports...")
        for (import_id,) in imports:
            serial = generate_serial("wi")
            cursor.execute("UPDATE wigle_imports SET serial = ? WHERE id = ?", (serial, import_id))
        conn.commit()
        print(f"  [✓] Generated {len(imports)} WiGLE import serials")

        # 4. Add serial column to oui_updates table (without UNIQUE - will add index later)
        print("[*] Adding serial column to oui_updates table...")
        try:
            cursor.execute("ALTER TABLE oui_updates ADD COLUMN serial VARCHAR(20)")
            conn.commit()
            print("  [✓] Column added")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  [i] Column already exists")
            else:
                raise

        # Generate serials for existing oui_updates
        cursor.execute("SELECT id FROM oui_updates WHERE serial IS NULL")
        updates = cursor.fetchall()
        print(f"  [*] Generating serials for {len(updates)} existing OUI updates...")
        for (update_id,) in updates:
            serial = generate_serial("ou")
            cursor.execute("UPDATE oui_updates SET serial = ? WHERE id = ?", (serial, update_id))
        conn.commit()
        print(f"  [✓] Generated {len(updates)} OUI update serials")

        # 5. Create indexes for serial columns
        print("[*] Creating indexes for serial columns...")
        indexes = [
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_serial ON clients(serial)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_handshakes_serial ON handshakes(serial)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_wigle_imports_serial ON wigle_imports(serial)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_oui_updates_serial ON oui_updates(serial)"
        ]
        for idx_sql in indexes:
            cursor.execute(idx_sql)
        conn.commit()
        print("  [✓] Indexes created")

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
    backup_path = db_path.with_suffix('.db.backup')
    print(f"[*] Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("[✓] Backup created")

    success = migrate_database(str(db_path))
    sys.exit(0 if success else 1)
