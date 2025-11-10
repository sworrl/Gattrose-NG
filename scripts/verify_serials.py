#!/usr/bin/env python3
"""
Serial Number Verification Script
Verifies that all database records have unique serial numbers
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.models import (
    init_db, get_session,
    Network, Client, Handshake, ScanSession,
    NetworkObservation, WiGLEImport, OUIUpdate, AttackQueue,
    CurrentScanNetwork, CurrentScanClient
)
from sqlalchemy import func


def verify_table_serials(session, model, model_name):
    """Verify serials for a specific table"""
    print(f"\n[*] Checking {model_name}...")

    # Count total records
    total = session.query(func.count(model.id)).scalar()
    print(f"    Total records: {total}")

    # Count records with serials
    with_serial = session.query(func.count(model.id)).filter(model.serial.isnot(None)).scalar()
    print(f"    With serial: {with_serial}")

    # Count records without serials
    without_serial = total - with_serial
    if without_serial > 0:
        print(f"    ⚠️  Missing serial: {without_serial}")
        return False
    else:
        print(f"    ✓ All records have serials")

    # Check for duplicate serials
    duplicates = session.query(model.serial, func.count(model.serial))\
        .group_by(model.serial)\
        .having(func.count(model.serial) > 1)\
        .all()

    if duplicates:
        print(f"    ⚠️  Duplicate serials found: {len(duplicates)}")
        for serial, count in duplicates:
            print(f"        {serial}: {count} occurrences")
        return False
    else:
        print(f"    ✓ All serials are unique")

    # Show sample serials
    samples = session.query(model.serial).limit(3).all()
    if samples:
        print(f"    Sample serials:")
        for (serial,) in samples:
            print(f"        {serial}")

    return True


def verify_all_serials():
    """Verify serial numbers across all tables"""
    print("=" * 70)
    print("Serial Number Verification")
    print("=" * 70)

    # Initialize database
    init_db()
    session = get_session()

    try:
        all_good = True

        # Check all tables with serials
        tables = [
            (Network, "Networks (APs)"),
            (Client, "Clients"),
            (Handshake, "Handshakes"),
            (ScanSession, "Scan Sessions"),
            (NetworkObservation, "Network Observations"),
            (WiGLEImport, "WiGLE Imports"),
            (OUIUpdate, "OUI Updates"),
            (AttackQueue, "Attack Queue"),
            (CurrentScanNetwork, "Current Scan Networks"),
            (CurrentScanClient, "Current Scan Clients"),
        ]

        for model, name in tables:
            if not verify_table_serials(session, model, name):
                all_good = False

        print("\n" + "=" * 70)
        if all_good:
            print("✓ All tables have proper serial numbers!")
        else:
            print("⚠️  Some tables have issues - run migration script")
        print("=" * 70)

    except Exception as e:
        print(f"\n[!] Error during verification: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


def test_serial_generation():
    """Test serial generation for all entity types"""
    print("\n" + "=" * 70)
    print("Testing Serial Generation")
    print("=" * 70)

    from src.utils.serial import generate_serial

    entities = [
        ("ap", "Access Point"),
        ("cl", "Client"),
        ("hs", "Handshake"),
        ("scan", "Scan Session"),
        ("obs", "Network Observation"),
        ("wi", "WiGLE Import"),
        ("ou", "OUI Update"),
        ("aq", "Attack Queue"),
        ("csn", "Current Scan Network"),
        ("csc", "Current Scan Client"),
    ]

    print("\nGenerating sample serials:")
    for entity_type, name in entities:
        serial = generate_serial(entity_type)
        print(f"  {name:25s} -> {serial}")

    print("\n✓ All serial generators working correctly")


if __name__ == "__main__":
    verify_all_serials()
    test_serial_generation()
