#!/usr/bin/env python3
"""
Database Migration Script - Add GPS Source Fields
Adds gps_source field to track GPS data quality (gpsd, phone-bt, phone-usb, geoip)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.models import init_db, get_session
from sqlalchemy import text


def migrate_add_serials():
    """Add serial columns to tables missing them"""
    print("[*] Starting serial number migration...")

    # Initialize database
    init_db()
    session = get_session()

    try:
        # Add serial to network_observations
        print("[*] Adding serial to network_observations...")
        try:
            session.execute(text(
                "ALTER TABLE network_observations ADD COLUMN serial VARCHAR(20) UNIQUE"
            ))
            session.commit()
            print("[+] Added serial to network_observations")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[!] serial already exists in network_observations")
                session.rollback()
            else:
                raise

        # Add serial to current_scan_networks
        print("[*] Adding serial to current_scan_networks...")
        try:
            session.execute(text(
                "ALTER TABLE current_scan_networks ADD COLUMN serial VARCHAR(20) UNIQUE"
            ))
            session.commit()
            print("[+] Added serial to current_scan_networks")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[!] serial already exists in current_scan_networks")
                session.rollback()
            else:
                raise

        # Add serial to current_scan_clients
        print("[*] Adding serial to current_scan_clients...")
        try:
            session.execute(text(
                "ALTER TABLE current_scan_clients ADD COLUMN serial VARCHAR(20) UNIQUE"
            ))
            session.commit()
            print("[+] Added serial to current_scan_clients")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[!] serial already exists in current_scan_clients")
                session.rollback()
            else:
                raise

        # Now populate serials for existing records
        print("[*] Populating serial numbers for existing records...")
        from src.utils.serial import generate_serial

        # NetworkObservations
        observations = session.execute(text("SELECT id FROM network_observations WHERE serial IS NULL")).fetchall()
        for obs in observations:
            serial = generate_serial("obs")
            session.execute(text(f"UPDATE network_observations SET serial = '{serial}' WHERE id = {obs[0]}"))
        if observations:
            session.commit()
            print(f"[+] Generated serials for {len(observations)} network observations")

        # CurrentScanNetworks
        networks = session.execute(text("SELECT id FROM current_scan_networks WHERE serial IS NULL")).fetchall()
        for net in networks:
            serial = generate_serial("csn")
            session.execute(text(f"UPDATE current_scan_networks SET serial = '{serial}' WHERE id = {net[0]}"))
        if networks:
            session.commit()
            print(f"[+] Generated serials for {len(networks)} current scan networks")

        # CurrentScanClients
        clients = session.execute(text("SELECT id FROM current_scan_clients WHERE serial IS NULL")).fetchall()
        for cli in clients:
            serial = generate_serial("csc")
            session.execute(text(f"UPDATE current_scan_clients SET serial = '{serial}' WHERE id = {cli[0]}"))
        if clients:
            session.commit()
            print(f"[+] Generated serials for {len(clients)} current scan clients")

        print("\n[+] Serial migration completed successfully!")

    except Exception as e:
        print(f"\n[!] Serial migration failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()

    return True


def migrate_add_gps_source():
    """Add gps_source column to tables"""
    print("[*] Starting GPS source field migration...")

    # Initialize database
    init_db()
    session = get_session()

    try:
        # Add gps_source to current_scan_networks
        print("[*] Adding gps_source to current_scan_networks...")
        try:
            session.execute(text(
                "ALTER TABLE current_scan_networks ADD COLUMN gps_source VARCHAR(20)"
            ))
            session.commit()
            print("[+] Added gps_source to current_scan_networks")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[!] gps_source already exists in current_scan_networks")
                session.rollback()
            else:
                raise

        # Add gps_source to current_scan_clients
        print("[*] Adding gps_source to current_scan_clients...")
        try:
            session.execute(text(
                "ALTER TABLE current_scan_clients ADD COLUMN gps_source VARCHAR(20)"
            ))
            session.commit()
            print("[+] Added gps_source to current_scan_clients")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[!] gps_source already exists in current_scan_clients")
                session.rollback()
            else:
                raise

        # Add gps_source to network_observations
        print("[*] Adding gps_source to network_observations...")
        try:
            session.execute(text(
                "ALTER TABLE network_observations ADD COLUMN gps_source VARCHAR(20)"
            ))
            session.commit()
            print("[+] Added gps_source to network_observations")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("[!] gps_source already exists in network_observations")
                session.rollback()
            else:
                raise

        print("\n[+] Migration completed successfully!")
        print("[i] GPS source values:")
        print("    - 'gpsd': Accurate GPS from GPS daemon")
        print("    - 'phone-bt': Accurate GPS from phone via Bluetooth")
        print("    - 'phone-usb': Accurate GPS from phone via USB")
        print("    - 'geoip': Approximate location from IP geolocation")

    except Exception as e:
        print(f"\n[!] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()

    return True


def recreate_database():
    """Completely recreate the database with new schema"""
    print("[!] WARNING: This will DELETE ALL DATA and recreate the database!")
    response = input("Type 'yes' to continue: ")

    if response.lower() != 'yes':
        print("[*] Aborted")
        return

    print("[*] Recreating database...")

    # Remove existing database
    db_path = Path.cwd() / "data" / "database" / "gattrose.db"
    if db_path.exists():
        print(f"[*] Removing existing database: {db_path}")
        db_path.unlink()

    # Initialize with new schema
    from src.database.models import Base, _engine
    init_db()

    print("[+] Creating all tables with new schema...")
    Base.metadata.create_all(_engine)

    print("[+] Database recreated successfully!")
    print("[i] New GPS tracking fields added:")
    print("    - latitude, longitude, altitude, gps_accuracy, gps_source")


if __name__ == "__main__":
    print("=" * 70)
    print("Gattrose-NG Database Migration Script")
    print("=" * 70)
    print()
    print("This script handles database schema migrations")
    print()
    print("Options:")
    print("  1. Add serial numbers to all tables (preserves data)")
    print("  2. Add GPS source field (preserves data)")
    print("  3. Run both migrations (recommended)")
    print("  4. Recreate database from scratch (DELETES ALL DATA)")
    print()

    choice = input("Enter choice (1-4): ").strip()

    if choice == "1":
        migrate_add_serials()
    elif choice == "2":
        migrate_add_gps_source()
    elif choice == "3":
        print("\n[*] Running both migrations...\n")
        if migrate_add_serials():
            print()
            migrate_add_gps_source()
    elif choice == "4":
        recreate_database()
    else:
        print("[!] Invalid choice")
        sys.exit(1)
