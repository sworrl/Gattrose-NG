"""
Database manager for Gattrose
Handles database creation, connections, and operations
"""

import os
import csv
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

from .models import (
    Base, Network, NetworkObservation, Client, Handshake,
    ScanSession, WiGLEImport
)


class DatabaseManager:
    """Manages database operations for Gattrose"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Use default location
            data_dir = self._get_data_dir()
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "gattrose-ng.db")

        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.Session = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

    def _get_data_dir(self) -> Path:
        """Get the data directory for the database"""
        project_root = Path(os.environ.get('GATTROSE_NG_ROOT', Path.cwd()))
        is_portable = os.environ.get('GATTROSE_NG_PORTABLE', '1') == '1'

        if is_portable:
            # Portable mode: data in project directory
            return project_root / "data"
        else:
            # Installed mode: data in user's home directory
            return Path.home() / ".local" / "share" / "gattrose-ng" / "data"

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.Session()

    # ==================== Network Operations ====================

    def add_network(self, session: Session, **kwargs) -> Network:
        """Add a new network to the database"""
        network = Network(**kwargs)
        session.add(network)
        session.commit()
        return network

    def get_network_by_bssid(self, session: Session, bssid: str) -> Optional[Network]:
        """Get a network by its BSSID"""
        return session.query(Network).filter(Network.bssid == bssid).first()

    def get_or_create_network(self, session: Session, bssid: str, **kwargs) -> Network:
        """Get existing network or create new one"""
        network = self.get_network_by_bssid(session, bssid)

        if network is None:
            network = Network(bssid=bssid, **kwargs)
            session.add(network)
            session.commit()
        else:
            # Update last_seen
            network.last_seen = datetime.utcnow()
            session.commit()

        return network

    def search_networks(
        self,
        session: Session,
        ssid: Optional[str] = None,
        encryption: Optional[str] = None,
        manufacturer: Optional[str] = None,
        limit: int = 100
    ) -> List[Network]:
        """Search for networks with filters"""
        query = session.query(Network)

        if ssid:
            query = query.filter(Network.ssid.like(f"%{ssid}%"))
        if encryption:
            query = query.filter(Network.encryption == encryption)
        if manufacturer:
            query = query.filter(Network.manufacturer.like(f"%{manufacturer}%"))

        return query.limit(limit).all()

    def get_networks_by_location(
        self,
        session: Session,
        lat: float,
        lon: float,
        radius_km: float = 1.0
    ) -> List[Network]:
        """Get networks within a radius of a location"""
        # Simple bounding box search (more efficient than true distance calculation)
        # 1 degree latitude ≈ 111 km
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * abs(float(lat)))  # Adjust for longitude

        return session.query(Network).filter(
            Network.latitude.between(lat - lat_delta, lat + lat_delta),
            Network.longitude.between(lon - lon_delta, lon + lon_delta)
        ).all()

    # ==================== Observation Operations ====================

    def add_observation(self, session: Session, network_id: int, **kwargs) -> NetworkObservation:
        """Add a network observation"""
        obs = NetworkObservation(network_id=network_id, **kwargs)
        session.add(obs)
        session.commit()
        return obs

    # ==================== WiGLE Import Operations ====================

    def import_wigle_csv(self, session: Session, csv_path: str) -> WiGLEImport:
        """
        Import networks from WiGLE CSV export

        WiGLE CSV format:
        MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,CurrentLatitude,CurrentLongitude,...
        """
        csv_path = Path(csv_path)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Calculate file hash
        file_hash = self._calculate_file_hash(csv_path)

        # Check if already imported
        existing = session.query(WiGLEImport).filter(
            WiGLEImport.file_hash == file_hash
        ).first()

        if existing:
            print(f"[!] File already imported at {existing.import_time}")
            return existing

        # Create import record
        wigle_import = WiGLEImport(
            file_path=str(csv_path),
            file_hash=file_hash
        )

        imported = 0
        updated = 0
        skipped = 0

        # Read and import CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip header comment lines
            for line in f:
                if not line.startswith('#'):
                    f.seek(f.tell() - len(line) - 1)
                    break

            reader = csv.DictReader(f)

            for row in reader:
                try:
                    bssid = row.get('MAC', '').strip().upper()
                    ssid = row.get('SSID', '').strip()

                    if not bssid:
                        skipped += 1
                        continue

                    # Parse encryption
                    auth_mode = row.get('AuthMode', '')
                    encryption = self._parse_encryption(auth_mode)

                    # Parse location
                    try:
                        lat = float(row.get('CurrentLatitude', 0))
                        lon = float(row.get('CurrentLongitude', 0))
                    except (ValueError, TypeError):
                        lat = lon = None

                    # Parse first seen timestamp
                    first_seen_str = row.get('FirstSeen', '')
                    try:
                        first_seen = datetime.strptime(first_seen_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        first_seen = datetime.utcnow()

                    # Parse channel
                    try:
                        channel = int(row.get('Channel', 0))
                    except (ValueError, TypeError):
                        channel = None

                    # Parse signal
                    try:
                        signal = int(row.get('RSSI', 0))
                    except (ValueError, TypeError):
                        signal = None

                    # Get or create network
                    network = self.get_network_by_bssid(session, bssid)

                    if network is None:
                        # Create new network
                        network = Network(
                            bssid=bssid,
                            ssid=ssid if ssid else None,
                            encryption=encryption,
                            channel=channel,
                            latitude=lat,
                            longitude=lon,
                            first_seen=first_seen,
                            last_seen=first_seen
                        )

                        if signal:
                            network.max_signal = signal
                            network.min_signal = signal
                            network.avg_signal = signal

                        session.add(network)
                        imported += 1
                    else:
                        # Update existing network
                        if not network.ssid and ssid:
                            network.ssid = ssid

                        if not network.encryption and encryption:
                            network.encryption = encryption

                        if not network.latitude and lat:
                            network.latitude = lat
                            network.longitude = lon

                        if first_seen < network.first_seen:
                            network.first_seen = first_seen

                        network.last_seen = max(network.last_seen, first_seen)

                        updated += 1

                    # Add observation
                    if lat and lon:
                        obs = NetworkObservation(
                            network=network,
                            latitude=lat,
                            longitude=lon,
                            signal_strength=signal,
                            timestamp=first_seen,
                            source='wigle'
                        )
                        session.add(obs)

                    # Commit periodically
                    if (imported + updated) % 100 == 0:
                        session.commit()

                except Exception as e:
                    print(f"[!] Error importing row: {e}")
                    skipped += 1
                    continue

        # Final commit
        session.commit()

        # Update import record
        wigle_import.networks_imported = imported
        wigle_import.networks_updated = updated
        wigle_import.networks_skipped = skipped
        session.add(wigle_import)
        session.commit()

        print(f"[+] WiGLE import complete:")
        print(f"    Imported: {imported}")
        print(f"    Updated: {updated}")
        print(f"    Skipped: {skipped}")

        return wigle_import

    def _parse_encryption(self, auth_mode: str) -> str:
        """Parse encryption type from WiGLE auth mode"""
        auth_mode = auth_mode.upper()

        if 'WPA3' in auth_mode:
            return 'WPA3'
        elif 'WPA2' in auth_mode:
            return 'WPA2'
        elif 'WPA' in auth_mode:
            return 'WPA'
        elif 'WEP' in auth_mode:
            return 'WEP'
        elif auth_mode in ['OPEN', 'NONE', '']:
            return 'Open'
        else:
            return auth_mode

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    # ==================== Statistics ====================

    def get_statistics(self, session: Session) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            'total_networks': session.query(Network).count(),
            'total_observations': session.query(NetworkObservation).count(),
            'total_clients': session.query(Client).count(),
            'total_handshakes': session.query(Handshake).count(),
            'cracked_handshakes': session.query(Handshake).filter(Handshake.is_cracked == True).count(),
            'scan_sessions': session.query(ScanSession).count(),
            'wigle_imports': session.query(WiGLEImport).count(),
            'encryption_breakdown': self._get_encryption_breakdown(session),
        }

    def _get_encryption_breakdown(self, session: Session) -> Dict[str, int]:
        """Get count of networks by encryption type"""
        results = session.query(
            Network.encryption,
            func.count(Network.id)
        ).group_by(Network.encryption).all()

        return {enc or 'Unknown': count for enc, count in results}

    # ==================== Maintenance ====================

    def vacuum_database(self):
        """Optimize database (SQLite VACUUM)"""
        with self.engine.connect() as conn:
            conn.execute("VACUUM")

    def backup_database(self, backup_path: str):
        """Create a backup of the database"""
        import shutil
        shutil.copy2(self.db_path, backup_path)
        print(f"[+] Database backed up to: {backup_path}")
