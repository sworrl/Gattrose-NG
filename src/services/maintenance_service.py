#!/usr/bin/env python3
"""
Gattrose-NG Maintenance Service

Periodic database maintenance tasks
- Vacuum and optimize database
- Archive old scans
- Update OUI database
- Clean up orphaned records
- Generate statistics
- Purge old temporary files
"""

import os
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import get_session, get_engine, ScanSession, Network, Client, Handshake, OUIUpdate
from src.utils.oui_downloader import OUIDownloader
from src.version import VERSION


class MaintenanceService:
    """Database and system maintenance service"""

    def __init__(self):
        self.start_time = time.time()
        print(f"[*] Gattrose-NG Maintenance Service v{VERSION}")
        print(f"[*] Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()

    def vacuum_database(self):
        """Vacuum and optimize SQLite database"""
        print("[*] Task: Vacuum Database")
        try:
            engine = get_engine()
            with engine.connect() as conn:
                # Get database size before
                db_path = str(PROJECT_ROOT / "data" / "database" / "gattrose.db")
                if Path(db_path).exists():
                    size_before = Path(db_path).stat().st_size / (1024 * 1024)  # MB
                    print(f"    Database size before: {size_before:.2f} MB")

                    # Vacuum
                    conn.execute("VACUUM")

                    # Get size after
                    size_after = Path(db_path).stat().st_size / (1024 * 1024)
                    savings = size_before - size_after

                    print(f"    Database size after: {size_after:.2f} MB")
                    if savings > 0:
                        print(f"    Space saved: {savings:.2f} MB")
                    print(f"[✓] Database vacuumed")
                else:
                    print(f"[!] Database file not found")

        except Exception as e:
            print(f"[!] Error vacuuming database: {e}")

    def archive_old_scans(self, days_old: int = 7):
        """Archive scan sessions older than specified days"""
        print(f"\n[*] Task: Archive Old Scans (>{days_old} days)")
        try:
            session = get_session()

            # Find old live/failed scans
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            old_scans = session.query(ScanSession).filter(
                ScanSession.status.in_(['live', 'failed']),
                ScanSession.start_time < cutoff_date
            ).all()

            if not old_scans:
                print(f"    No old scans to archive")
                return

            print(f"    Found {len(old_scans)} old scan(s)")

            for scan in old_scans:
                scan.status = 'archived'
                if not scan.end_time:
                    scan.end_time = datetime.utcnow()
                print(f"    Archived scan: {scan.serial} ({scan.start_time})")

            session.commit()
            print(f"[✓] Archived {len(old_scans)} scan(s)")

        except Exception as e:
            print(f"[!] Error archiving scans: {e}")
            session.rollback()
        finally:
            session.close()

    def update_oui_database(self, force: bool = False):
        """Update OUI database if needed"""
        print(f"\n[*] Task: Update OUI Database")
        try:
            downloader = OUIDownloader()

            # Check last update
            last_update = downloader.get_last_update_time()

            if last_update:
                age_days = (datetime.utcnow() - last_update).days
                print(f"    Last update: {last_update} ({age_days} days ago)")

                if age_days < 30 and not force:
                    print(f"    Database is recent (< 30 days), skipping update")
                    return
            else:
                print(f"    No previous update found")

            # Perform update
            print(f"    Downloading OUI data...")
            stats = downloader.update_database(source='all')

            if stats['success']:
                print(f"[✓] OUI database updated")
                print(f"    Records added: {stats['records_added']}")
                print(f"    Records updated: {stats['records_updated']}")
                print(f"    Total records: {stats['records_total']}")
            else:
                print(f"[!] OUI database update failed")

        except Exception as e:
            print(f"[!] Error updating OUI database: {e}")

    def cleanup_orphaned_records(self):
        """Clean up orphaned database records"""
        print(f"\n[*] Task: Cleanup Orphaned Records")
        try:
            session = get_session()

            # Find handshakes without networks
            orphaned_hs = session.query(Handshake).filter(
                ~Handshake.network_id.in_(
                    session.query(Network.id)
                )
            ).all()

            if orphaned_hs:
                print(f"    Found {len(orphaned_hs)} orphaned handshake(s)")
                for hs in orphaned_hs:
                    session.delete(hs)
                session.commit()
                print(f"    Deleted {len(orphaned_hs)} orphaned handshake(s)")

            # Find clients without networks (if we had foreign key)
            # This depends on database schema

            print(f"[✓] Cleanup complete")

        except Exception as e:
            print(f"[!] Error cleaning up orphans: {e}")
            session.rollback()
        finally:
            session.close()

    def purge_old_temp_files(self, days_old: int = 30):
        """Delete old temporary and capture files"""
        print(f"\n[*] Task: Purge Old Temp Files (>{days_old} days)")
        try:
            captures_dir = PROJECT_ROOT / "data" / "captures"
            if not captures_dir.exists():
                print(f"    No captures directory found")
                return

            cutoff_time = time.time() - (days_old * 86400)
            deleted_count = 0
            deleted_size = 0

            # Walk through captures directory
            for file_path in captures_dir.rglob("*"):
                if file_path.is_file():
                    # Check file age
                    if file_path.stat().st_mtime < cutoff_time:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        deleted_size += size

            if deleted_count > 0:
                deleted_mb = deleted_size / (1024 * 1024)
                print(f"[✓] Deleted {deleted_count} old file(s) ({deleted_mb:.2f} MB)")
            else:
                print(f"    No old files to delete")

        except Exception as e:
            print(f"[!] Error purging temp files: {e}")

    def generate_statistics(self):
        """Generate and display database statistics"""
        print(f"\n[*] Task: Generate Statistics")
        try:
            session = get_session()

            # Count records
            total_networks = session.query(Network).count()
            total_clients = session.query(Client).count()
            total_handshakes = session.query(Handshake).count()
            cracked_handshakes = session.query(Handshake).filter_by(is_cracked=True).count()

            # Count scans
            live_scans = session.query(ScanSession).filter_by(status='live').count()
            archived_scans = session.query(ScanSession).filter_by(status='archived').count()

            # Recent activity
            recent_networks = session.query(Network).filter(
                Network.last_seen > datetime.utcnow() - timedelta(days=7)
            ).count()

            print(f"\n    Database Statistics:")
            print(f"    ───────────────────────────────")
            print(f"    Networks:           {total_networks:,}")
            print(f"    Clients:            {total_clients:,}")
            print(f"    Handshakes:         {total_handshakes:,}")
            print(f"    Cracked PSKs:       {cracked_handshakes:,}")
            print(f"    Live Scans:         {live_scans}")
            print(f"    Archived Scans:     {archived_scans}")
            print(f"    Active (7d):        {recent_networks:,}")
            print(f"    ───────────────────────────────")

            print(f"[✓] Statistics generated")

        except Exception as e:
            print(f"[!] Error generating statistics: {e}")
        finally:
            session.close()

    def run(self):
        """Run all maintenance tasks"""
        print("="*60)
        print("  GATTROSE-NG MAINTENANCE SERVICE")
        print("="*60)
        print()

        try:
            # Database optimization
            self.vacuum_database()

            # Archive old scans
            self.archive_old_scans(days_old=7)

            # Update OUI database
            self.update_oui_database(force=False)

            # Cleanup orphaned records
            self.cleanup_orphaned_records()

            # Purge old temp files
            self.purge_old_temp_files(days_old=30)

            # Generate statistics
            self.generate_statistics()

            # Summary
            duration = time.time() - self.start_time
            print()
            print("="*60)
            print(f"[✓] Maintenance Complete")
            print(f"    Duration: {duration:.2f} seconds")
            print(f"    Finished: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print("="*60)

            return 0

        except Exception as e:
            print(f"\n[!] Maintenance failed: {e}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    """Entry point"""
    service = MaintenanceService()
    sys.exit(service.run())


if __name__ == "__main__":
    main()
