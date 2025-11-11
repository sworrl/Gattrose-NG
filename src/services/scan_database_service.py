"""
Scan Database Service
Manages current scan data in database and periodic upsert to historical tables
"""

import threading
import time
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

from ..database.models import (
    get_session, init_db,
    CurrentScanNetwork, CurrentScanClient,
    Network, Client, NetworkObservation
)
from .event_manager import get_event_manager
from .gps_track_manager import GPSTrackManager


class ScanDatabaseService:
    """Service to manage current scan data in database

    This service:
    1. Updates current_scan tables as CSV data is parsed
    2. Periodically upserts current_scan data to historical tables
    3. Provides thread-safe access to current scan data
    """

    def __init__(self, upsert_interval: float = 10.0, triangulation_interval: float = 60.0):
        """
        Initialize scan database service

        Args:
            upsert_interval: Seconds between upserts to historical tables (default 10s)
            triangulation_interval: Seconds between triangulation updates (default 60s)
        """
        self._lock = threading.RLock()
        self.upsert_interval = upsert_interval
        self.triangulation_interval = triangulation_interval
        self.running = False
        self._upsert_thread: Optional[threading.Thread] = None
        self._last_triangulation = 0  # Track when we last ran triangulation

        # Track data state to detect changes
        self._last_data_hash = None
        self._consecutive_no_change = 0

        # Initialize GPS track manager for smart observation deduplication
        self.gps_track_manager = GPSTrackManager()

        # Initialize database
        init_db()

    def start_new_scan(self):
        """Start a new scan - clears current_scan tables"""
        with self._lock:
            session = get_session()
            try:
                # Clear current scan tables
                session.query(CurrentScanNetwork).delete()
                session.query(CurrentScanClient).delete()
                session.commit()
                print("[*] Current scan tables cleared - new scan started")
            except Exception as e:
                session.rollback()
                print(f"[!] Error clearing current scan tables: {e}")
            finally:
                session.close()

    def load_historical_data(self, max_age_days: int = 7, gps_radius_km: Optional[float] = None):
        """
        Load historical networks and clients into current_scan tables

        Args:
            max_age_days: Only load data seen within this many days (default 7)
            gps_radius_km: If provided with GPS location, only load nearby data
        """
        with self._lock:
            session = get_session()
            try:
                from datetime import timedelta

                # Clear current scan tables first
                session.query(CurrentScanNetwork).delete()
                session.query(CurrentScanClient).delete()

                # Calculate cutoff date
                cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

                # Load networks
                networks_query = session.query(Network).filter(
                    Network.last_seen >= cutoff_date
                )

                # Optional: Filter by GPS proximity
                if gps_radius_km is not None:
                    try:
                        from ..services.gps_service import get_gps_service
                        gps = get_gps_service()
                        lat, lon, _, _, _ = gps.get_location()

                        if lat and lon:
                            # Simple bounding box filter (rough approximation)
                            # 1 degree latitude ≈ 111 km
                            # 1 degree longitude ≈ 111 km * cos(latitude)
                            import math
                            lat_delta = gps_radius_km / 111.0
                            lon_delta = gps_radius_km / (111.0 * math.cos(math.radians(lat)))

                            networks_query = networks_query.filter(
                                Network.latitude.between(lat - lat_delta, lat + lat_delta),
                                Network.longitude.between(lon - lon_delta, lon + lon_delta)
                            )
                            print(f"[*] Filtering historical data within {gps_radius_km}km of {lat:.6f}, {lon:.6f}")
                    except Exception as e:
                        print(f"[!] GPS filtering failed: {e}")

                networks = networks_query.all()

                # Load clients
                clients = session.query(Client).filter(
                    Client.last_seen >= cutoff_date
                ).all()

                # Copy to current scan tables
                networks_loaded = 0
                for network in networks:
                    current_network = CurrentScanNetwork(
                        bssid=network.bssid,
                        ssid=network.ssid,
                        channel=network.channel,
                        encryption=network.encryption,
                        cipher=network.cipher,
                        authentication=network.authentication,
                        power=network.current_signal or network.max_signal,
                        beacon_count=network.beacon_count,
                        iv_count=network.iv_count,
                        lan_ip=network.lan_ip,
                        speed=network.speed,
                        vendor=network.manufacturer,
                        wps_enabled=network.wps_enabled,
                        wps_locked=network.wps_locked,
                        wps_version=network.wps_version,
                        attack_score=float(network.current_attack_score) if network.current_attack_score else None,
                        latitude=network.latitude,
                        longitude=network.longitude,
                        altitude=network.altitude,
                        first_seen=network.first_seen,
                        last_seen=network.last_seen
                    )
                    session.add(current_network)
                    networks_loaded += 1

                clients_loaded = 0
                for client in clients:
                    # Parse associated networks JSON if exists
                    bssid = None
                    if client.associated_networks:
                        try:
                            import json
                            networks_list = json.loads(client.associated_networks)
                            if networks_list:
                                bssid = networks_list[0]  # Use first associated network
                        except:
                            pass

                    current_client = CurrentScanClient(
                        mac_address=client.mac_address,
                        bssid=bssid,
                        power=client.current_signal or client.max_signal,
                        vendor=client.manufacturer,
                        device_type=client.device_type,
                        first_seen=client.first_seen,
                        last_seen=client.last_seen
                    )
                    session.add(current_client)
                    clients_loaded += 1

                session.commit()
                print(f"[+] Loaded historical data: {networks_loaded} networks, {clients_loaded} clients (max age: {max_age_days} days)")

            except Exception as e:
                session.rollback()
                print(f"[!] Error loading historical data: {e}")
                import traceback
                traceback.print_exc()
            finally:
                session.close()

    def start_upsert_worker(self):
        """Start background worker to upsert to historical tables"""
        if self.running:
            return

        self.running = True
        self._upsert_thread = threading.Thread(target=self._upsert_loop, daemon=True)
        self._upsert_thread.start()
        print(f"[+] Database upsert worker started (interval: {self.upsert_interval}s)")

    def stop_upsert_worker(self):
        """Stop background upsert worker"""
        self.running = False
        if self._upsert_thread:
            self._upsert_thread.join(timeout=5)
        print("[+] Database upsert worker stopped")

    def _get_current_data_hash(self):
        """Compute hash of current scan data to detect changes"""
        session = get_session()
        try:
            # Get current data sorted by BSSID/MAC for consistent hashing
            networks = session.query(CurrentScanNetwork).order_by(CurrentScanNetwork.bssid).all()
            clients = session.query(CurrentScanClient).order_by(CurrentScanClient.mac_address).all()

            # Create hash from network BSSIDs, signals, and last_seen times
            # This captures new networks, signal changes, and time updates
            import hashlib
            hash_data = []
            for net in networks:
                hash_data.append(f"{net.bssid}:{net.power}:{net.last_seen}")
            for client in clients:
                hash_data.append(f"{client.mac_address}:{client.power}:{client.last_seen}")

            data_str = "|".join(hash_data)
            return hashlib.md5(data_str.encode()).hexdigest()
        finally:
            session.close()

    def _upsert_loop(self):
        """Background loop to periodically upsert to historical tables"""
        cache_cleanup_counter = 0
        while self.running:
            try:
                time.sleep(self.upsert_interval)
                if self.running:
                    # Check if data has changed before upserting
                    current_hash = self._get_current_data_hash()

                    if current_hash != self._last_data_hash:
                        # Data has changed - perform upsert
                        self.upsert_to_historical()
                        self._last_data_hash = current_hash
                        self._consecutive_no_change = 0
                    else:
                        # No changes detected - skip upsert
                        self._consecutive_no_change += 1
                        if self._consecutive_no_change == 1:  # Log first skip
                            print(f"[DB] No changes detected, skipping upsert")
                        elif self._consecutive_no_change % 30 == 0:  # Log every 5 minutes
                            print(f"[DB] No changes for {self._consecutive_no_change * self.upsert_interval / 60:.1f} minutes")

                    # Run triangulation less frequently (e.g., every 60 seconds)
                    # This calculates physical AP locations from multiple GPS observations
                    if time.time() - self._last_triangulation >= self.triangulation_interval:
                        from .triangulation_service import TriangulationService
                        TriangulationService.batch_update_all_locations(min_observations=3)
                        self._last_triangulation = time.time()

                    # Cleanup GPS track manager cache every 10 minutes (60 iterations at 10s interval)
                    cache_cleanup_counter += 1
                    if cache_cleanup_counter >= 60:
                        self.gps_track_manager.cleanup_cache()
                        cache_cleanup_counter = 0
            except Exception as e:
                print(f"[!] Error in upsert loop: {e}")
                import traceback
                traceback.print_exc()

    def update_network(self, network_data: Dict):
        """Update or insert network in current_scan_networks table

        Args:
            network_data: Dictionary with network data from CSV/scanner
        """
        with self._lock:
            session = get_session()
            try:
                bssid = network_data.get('bssid')
                if not bssid:
                    return

                # Check if exists
                network = session.query(CurrentScanNetwork).filter_by(bssid=bssid).first()

                is_new = False
                if network:
                    # Update existing
                    for key, value in network_data.items():
                        if hasattr(network, key) and key != 'id':
                            setattr(network, key, value)
                    network.updated_at = datetime.utcnow()
                else:
                    # Create new
                    network = CurrentScanNetwork(**network_data)
                    session.add(network)
                    is_new = True

                session.commit()
                session.refresh(network)  # Get fresh data with ID

                # Convert to dict for signal emission
                network_dict = {
                    'id': network.id,
                    'bssid': network.bssid,
                    'ssid': network.ssid,
                    'channel': network.channel,
                    'encryption': network.encryption,
                    'power': network.power,
                    'beacon_count': network.beacon_count,
                    'wps_enabled': network.wps_enabled,
                    'attack_score': network.attack_score,
                    'first_seen': network.first_seen,
                    'last_seen': network.last_seen,
                    'updated_at': network.updated_at
                }

                # Emit Qt signal for instant GUI update
                event_manager = get_event_manager()
                if is_new:
                    # Emit file-based event for tray
                    try:
                        event_manager.emit_network_discovered(
                            bssid=bssid,
                            ssid=network_data.get('ssid', ''),
                            encryption=network_data.get('encryption', 'Unknown'),
                            power=network_data.get('power', 0)
                        )
                    except Exception as e:
                        print(f"[!] Error emitting network event: {e}")

                    # Emit Qt signal for GUI
                    if hasattr(event_manager, 'network_added'):
                        event_manager.network_added.emit(network_dict)
                else:
                    # Emit Qt signal for updated network
                    if hasattr(event_manager, 'network_updated'):
                        event_manager.network_updated.emit(network_dict)
            except Exception as e:
                session.rollback()
                print(f"[!] Error updating network in database: {e}")
                import traceback
                traceback.print_exc()
                # Emit error event
                try:
                    get_event_manager().emit_error(
                        title="Database Error",
                        message=f"Failed to update network: {str(e)[:100]}",
                        error_type="database"
                    )
                except:
                    pass
            finally:
                session.close()

    def update_client(self, client_data: Dict):
        """Update or insert client in current_scan_clients table

        Args:
            client_data: Dictionary with client data from CSV/scanner
        """
        with self._lock:
            session = get_session()
            try:
                mac = client_data.get('mac_address')
                if not mac:
                    return

                # Check if exists
                client = session.query(CurrentScanClient).filter_by(mac_address=mac).first()

                is_new = False
                if client:
                    # Update existing
                    for key, value in client_data.items():
                        if hasattr(client, key) and key != 'id':
                            setattr(client, key, value)
                    client.updated_at = datetime.utcnow()
                else:
                    # Create new
                    client = CurrentScanClient(**client_data)
                    session.add(client)
                    is_new = True

                session.commit()
                session.refresh(client)

                # Build client dict for Qt signal
                client_dict = {
                    'id': client.id,
                    'mac_address': client.mac_address,
                    'bssid': client.bssid,
                    'power': client.power,
                    'packets': client.packets,
                    'vendor': client.vendor,
                    'probes': client.probed_essids,
                    'first_seen': client.first_seen,
                    'last_seen': client.last_seen,
                    'updated_at': client.updated_at
                }

                # Emit Qt signal for instant GUI update
                event_manager = get_event_manager()
                if is_new:
                    # Emit file-based event for tray
                    try:
                        event_manager.emit_client_discovered(
                            mac=mac,
                            bssid=client_data.get('bssid', 'Unknown'),
                            power=client_data.get('power', 0)
                        )
                    except Exception as e:
                        print(f"[!] Error emitting client event: {e}")

                    # Emit Qt signal for GUI
                    if hasattr(event_manager, 'client_added'):
                        event_manager.client_added.emit(client_dict)
                else:
                    # Emit Qt signal for updated client
                    if hasattr(event_manager, 'client_updated'):
                        event_manager.client_updated.emit(client_dict)
            except Exception as e:
                session.rollback()
                print(f"[!] Error updating client in database: {e}")
                import traceback
                traceback.print_exc()
                # Emit error event
                try:
                    get_event_manager().emit_error(
                        title="Database Error",
                        message=f"Failed to update client: {str(e)[:100]}",
                        error_type="database"
                    )
                except:
                    pass
            finally:
                session.close()

    def batch_update_networks(self, networks: List[Dict]):
        """Batch update networks for better performance

        Args:
            networks: List of network dictionaries
        """
        with self._lock:
            session = get_session()
            new_networks = []  # Track new networks for event emission
            try:
                for network_data in networks:
                    bssid = network_data.get('bssid')
                    if not bssid:
                        continue

                    # Check if exists
                    network = session.query(CurrentScanNetwork).filter_by(bssid=bssid).first()

                    if network:
                        # Update existing
                        for key, value in network_data.items():
                            if hasattr(network, key) and key != 'id':
                                setattr(network, key, value)
                        network.updated_at = datetime.utcnow()
                    else:
                        # Create new
                        network = CurrentScanNetwork(**network_data)
                        session.add(network)
                        new_networks.append(network_data)

                session.commit()

                # Emit events for new networks
                for network_data in new_networks:
                    try:
                        get_event_manager().emit_network_discovered(
                            bssid=network_data.get('bssid'),
                            ssid=network_data.get('ssid', ''),
                            encryption=network_data.get('encryption', 'Unknown'),
                            power=network_data.get('power', 0)
                        )
                    except Exception as e:
                        print(f"[!] Error emitting network event: {e}")
            except Exception as e:
                session.rollback()
                print(f"[!] Error batch updating networks: {e}")
                import traceback
                traceback.print_exc()
            finally:
                session.close()

    def batch_update_clients(self, clients: List[Dict]):
        """Batch update clients for better performance

        Args:
            clients: List of client dictionaries
        """
        with self._lock:
            session = get_session()
            new_clients = []  # Track new clients for event emission
            try:
                for client_data in clients:
                    mac = client_data.get('mac_address')
                    if not mac:
                        continue

                    # Check if exists
                    client = session.query(CurrentScanClient).filter_by(mac_address=mac).first()

                    if client:
                        # Update existing
                        for key, value in client_data.items():
                            if hasattr(client, key) and key != 'id':
                                setattr(client, key, value)
                        client.updated_at = datetime.utcnow()
                    else:
                        # Create new
                        client = CurrentScanClient(**client_data)
                        session.add(client)
                        new_clients.append(client_data)

                session.commit()

                # Emit events for new clients
                for client_data in new_clients:
                    try:
                        get_event_manager().emit_client_discovered(
                            mac=client_data.get('mac_address'),
                            bssid=client_data.get('bssid', 'Unknown'),
                            power=client_data.get('power', 0)
                        )
                    except Exception as e:
                        print(f"[!] Error emitting client event: {e}")
            except Exception as e:
                session.rollback()
                print(f"[!] Error batch updating clients: {e}")
                import traceback
                traceback.print_exc()
            finally:
                session.close()

    def upsert_to_historical(self):
        """Upsert current scan data to historical tables"""
        with self._lock:
            session = get_session()
            try:
                # Upsert networks
                current_networks = session.query(CurrentScanNetwork).all()
                networks_upserted = 0

                for current_net in current_networks:
                    # Check if exists in historical
                    hist_net = session.query(Network).filter_by(bssid=current_net.bssid).first()

                    if hist_net:
                        # Update existing historical record
                        hist_net.last_seen = current_net.last_seen or datetime.utcnow()

                        # Update signal if stronger
                        if current_net.power:
                            if hist_net.max_signal is None or current_net.power > hist_net.max_signal:
                                hist_net.max_signal = current_net.power
                            if hist_net.min_signal is None or current_net.power < hist_net.min_signal:
                                hist_net.min_signal = current_net.power
                            hist_net.current_signal = current_net.power

                        # Update beacon/IV counts (take max)
                        if current_net.beacon_count:
                            hist_net.beacon_count = max(hist_net.beacon_count or 0, current_net.beacon_count)
                        if current_net.iv_count:
                            hist_net.iv_count = max(hist_net.iv_count or 0, current_net.iv_count)

                        # Update SSID if it was hidden before
                        if current_net.ssid and not hist_net.ssid:
                            hist_net.ssid = current_net.ssid

                        # Update attack score
                        if current_net.attack_score:
                            hist_net.current_attack_score = int(current_net.attack_score)
                            if hist_net.highest_attack_score is None or current_net.attack_score > hist_net.highest_attack_score:
                                hist_net.highest_attack_score = int(current_net.attack_score)
                            if hist_net.lowest_attack_score is None or current_net.attack_score < hist_net.lowest_attack_score:
                                hist_net.lowest_attack_score = int(current_net.attack_score)

                        # Update WPS info
                        if current_net.wps_enabled is not None:
                            hist_net.wps_enabled = current_net.wps_enabled
                        if current_net.wps_locked is not None:
                            hist_net.wps_locked = current_net.wps_locked
                        if current_net.wps_version:
                            hist_net.wps_version = current_net.wps_version

                        # Update GPS location (use most recent)
                        if current_net.latitude and current_net.longitude:
                            hist_net.latitude = current_net.latitude
                            hist_net.longitude = current_net.longitude
                            if current_net.altitude:
                                hist_net.altitude = current_net.altitude

                    else:
                        # Create new historical record
                        hist_net = Network(
                            bssid=current_net.bssid,
                            ssid=current_net.ssid,
                            channel=current_net.channel,
                            encryption=current_net.encryption,
                            cipher=current_net.cipher,
                            authentication=current_net.authentication,
                            max_signal=current_net.power,
                            min_signal=current_net.power,
                            current_signal=current_net.power,
                            beacon_count=current_net.beacon_count or 0,
                            iv_count=current_net.iv_count or 0,
                            lan_ip=current_net.lan_ip,
                            speed=current_net.speed,
                            manufacturer=current_net.vendor,
                            device_type=current_net.device_type,
                            current_attack_score=int(current_net.attack_score) if current_net.attack_score else None,
                            highest_attack_score=int(current_net.attack_score) if current_net.attack_score else None,
                            lowest_attack_score=int(current_net.attack_score) if current_net.attack_score else None,
                            wps_enabled=current_net.wps_enabled or False,
                            wps_locked=current_net.wps_locked or False,
                            wps_version=current_net.wps_version,
                            latitude=current_net.latitude,
                            longitude=current_net.longitude,
                            altitude=current_net.altitude,
                            first_seen=current_net.first_seen or datetime.utcnow(),
                            last_seen=current_net.last_seen or datetime.utcnow()
                        )
                        session.add(hist_net)
                        session.flush()  # Get ID for observation

                    # Create NetworkObservation for GPS tracking/triangulation
                    # This allows us to determine AP physical location from multiple observations
                    # Use smart deduplication to prevent database bloat when stationary
                    if current_net.latitude and current_net.longitude:
                        # Update movement tracking
                        movement_info = self.gps_track_manager.update_location(
                            current_net.latitude, current_net.longitude
                        )

                        # Check if we should create observation for this network
                        should_create, reason = self.gps_track_manager.should_create_observation(
                            hist_net.id, current_net.latitude, current_net.longitude
                        )

                        if should_create:
                            observation = NetworkObservation(
                                network_id=hist_net.id,
                                latitude=current_net.latitude,
                                longitude=current_net.longitude,
                                altitude=current_net.altitude,
                                accuracy=current_net.gps_accuracy,
                                gps_source=current_net.gps_source,
                                signal_strength=current_net.power,
                                timestamp=datetime.utcnow(),
                                source='scan'
                            )
                            session.add(observation)
                        # Don't spam logs - only log first few skips
                        elif networks_upserted < 3:
                            print(f"[GPS-TRACK] Skipping observation for {hist_net.bssid}: {reason}")

                    networks_upserted += 1

                # Upsert clients (filter out probe requests and randomized MACs)
                current_clients = session.query(CurrentScanClient).all()
                clients_upserted = 0
                clients_skipped = 0

                def is_locally_administered_mac(mac: str) -> bool:
                    """Check if MAC address is locally administered (randomized)

                    Locally administered addresses have bit 1 of the first octet set to 1.
                    Examples: x2, x3, x6, x7, xA, xB, xE, xF (where x is any hex digit)
                    """
                    if not mac or len(mac) < 2:
                        return False
                    try:
                        first_octet = int(mac[0:2], 16)
                        return (first_octet & 0x02) != 0
                    except:
                        return False

                for current_cli in current_clients:
                    # Skip probe requests (not actually connected to any network)
                    if not current_cli.bssid or current_cli.bssid == "(not associated)":
                        clients_skipped += 1
                        continue

                    # Skip locally administered (randomized) MAC addresses
                    # These are privacy features from mobile devices and don't represent real clients
                    if is_locally_administered_mac(current_cli.mac_address):
                        clients_skipped += 1
                        continue

                    # Update associated_networks JSON for this client
                    import json
                    associated_networks = [current_cli.bssid]

                    # Check if exists in historical
                    hist_cli = session.query(Client).filter_by(mac_address=current_cli.mac_address).first()

                    if hist_cli:
                        # Update existing
                        hist_cli.last_seen = current_cli.last_seen or datetime.utcnow()

                        # Update signal
                        if current_cli.power:
                            if hist_cli.max_signal is None or current_cli.power > hist_cli.max_signal:
                                hist_cli.max_signal = current_cli.power
                            if hist_cli.min_signal is None or current_cli.power < hist_cli.min_signal:
                                hist_cli.min_signal = current_cli.power
                            hist_cli.current_signal = current_cli.power

                        # Update associated networks (merge with existing)
                        try:
                            existing_networks = json.loads(hist_cli.associated_networks) if hist_cli.associated_networks else []
                            if current_cli.bssid not in existing_networks:
                                existing_networks.append(current_cli.bssid)
                            hist_cli.associated_networks = json.dumps(existing_networks)
                        except:
                            hist_cli.associated_networks = json.dumps(associated_networks)

                    else:
                        # Create new
                        hist_cli = Client(
                            mac_address=current_cli.mac_address,
                            associated_networks=json.dumps(associated_networks),
                            manufacturer=current_cli.vendor,
                            device_type=current_cli.device_type,
                            max_signal=current_cli.power,
                            min_signal=current_cli.power,
                            current_signal=current_cli.power,
                            first_seen=current_cli.first_seen or datetime.utcnow(),
                            last_seen=current_cli.last_seen or datetime.utcnow()
                        )
                        session.add(hist_cli)

                    clients_upserted += 1

                session.commit()

                if networks_upserted > 0 or clients_upserted > 0 or clients_skipped > 0:
                    print(f"[DB] Upserted {networks_upserted} networks, {clients_upserted} clients to historical tables (skipped {clients_skipped} probe requests/randomized MACs)")

            except Exception as e:
                session.rollback()
                print(f"[!] Error upserting to historical tables: {e}")
                import traceback
                traceback.print_exc()
            finally:
                session.close()

    def get_all_networks(self) -> List[CurrentScanNetwork]:
        """Get all current scan networks"""
        session = get_session()
        try:
            return session.query(CurrentScanNetwork).all()
        finally:
            session.close()

    def get_all_clients(self) -> List[CurrentScanClient]:
        """Get all current scan clients"""
        session = get_session()
        try:
            return session.query(CurrentScanClient).all()
        finally:
            session.close()


# Singleton instance
_service_instance: Optional[ScanDatabaseService] = None

def get_scan_db_service() -> ScanDatabaseService:
    """Get singleton scan database service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ScanDatabaseService()
    return _service_instance
