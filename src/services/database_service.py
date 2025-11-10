#!/usr/bin/env python3
"""
Gattrose-NG Database Service

Centralized database handling for all operations:
- Network insertions/updates
- Client handling
- Scan session management
- Data archiving
- Query operations
"""

import os
import sys
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from queue import Queue, Empty
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import (
    get_session, Network, Client, NetworkObservation,
    ScanSession, Handshake
)


class DatabaseService:
    """Centralized database service with async operations"""

    def __init__(self):
        self.queue = Queue()
        self.running = False
        self.worker_thread = None
        self.stats = {
            'networks_inserted': 0,
            'networks_updated': 0,
            'clients_inserted': 0,
            'clients_updated': 0,
            'observations_inserted': 0,
            'errors': 0
        }

    def start(self):
        """Start the database worker thread"""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        print("[+] Database service started")

    def stop(self):
        """Stop the database worker thread"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        print("[+] Database service stopped")

    def _worker(self):
        """Background worker thread for database operations"""
        while self.running:
            try:
                # Get task from queue with timeout
                try:
                    task = self.queue.get(timeout=1)
                except Empty:
                    continue

                # Execute task
                operation = task.get('operation')
                data = task.get('data')
                callback = task.get('callback')

                try:
                    result = self._execute_operation(operation, data)
                    if callback:
                        callback(result)
                except Exception as e:
                    self.stats['errors'] += 1
                    print(f"[!] Database error in {operation}: {e}")

                self.queue.task_done()

            except Exception as e:
                print(f"[!] Worker thread error: {e}")
                time.sleep(1)

    def _execute_operation(self, operation: str, data: dict):
        """Execute a database operation"""
        if operation == 'upsert_network':
            return self._upsert_network(data)
        elif operation == 'upsert_client':
            return self._upsert_client(data)
        elif operation == 'add_observation':
            return self._add_observation(data)
        elif operation == 'create_scan_session':
            return self._create_scan_session(data)
        elif operation == 'archive_scan':
            return self._archive_scan(data)
        elif operation == 'get_networks':
            return self._get_networks(data)
        elif operation == 'get_clients':
            return self._get_clients(data)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    # ========== Network Operations ==========

    def _upsert_network(self, data: dict) -> Network:
        """Insert or update a network"""
        session = get_session()
        try:
            bssid = data['bssid']

            # Try to find existing network
            network = session.query(Network).filter_by(bssid=bssid).first()

            if network:
                # Update existing
                network.essid = data.get('essid', network.essid)
                network.channel = data.get('channel', network.channel)
                network.encryption = data.get('encryption', network.encryption)
                network.power = data.get('power', network.power)
                network.beacons = data.get('beacons', network.beacons)
                network.data_packets = data.get('data_packets', network.data_packets)
                network.last_seen = datetime.utcnow()
                self.stats['networks_updated'] += 1
            else:
                # Insert new
                network = Network(
                    bssid=bssid,
                    essid=data.get('essid'),
                    channel=data.get('channel'),
                    encryption=data.get('encryption'),
                    power=data.get('power'),
                    beacons=data.get('beacons', 0),
                    data_packets=data.get('data_packets', 0),
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )
                session.add(network)
                self.stats['networks_inserted'] += 1

            session.commit()
            return network

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def _add_observation(self, data: dict) -> NetworkObservation:
        """Add a network observation with location"""
        session = get_session()
        try:
            obs = NetworkObservation(
                network_id=data['network_id'],
                scan_session_id=data.get('scan_session_id'),
                power=data.get('power'),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                altitude=data.get('altitude'),
                accuracy=data.get('accuracy'),
                gps_source=data.get('gps_source'),
                timestamp=datetime.utcnow()
            )
            session.add(obs)
            session.commit()
            self.stats['observations_inserted'] += 1
            return obs
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ========== Client Operations ==========

    def _upsert_client(self, data: dict) -> Client:
        """Insert or update a client"""
        session = get_session()
        try:
            mac = data['mac']

            # Try to find existing client
            client = session.query(Client).filter_by(mac=mac).first()

            if client:
                # Update existing
                client.bssid = data.get('bssid', client.bssid)
                client.probes = data.get('probes', client.probes)
                client.power = data.get('power', client.power)
                client.packets = data.get('packets', client.packets)
                client.last_seen = datetime.utcnow()
                self.stats['clients_updated'] += 1
            else:
                # Insert new
                client = Client(
                    mac=mac,
                    bssid=data.get('bssid'),
                    probes=data.get('probes'),
                    power=data.get('power'),
                    packets=data.get('packets', 0),
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )
                session.add(client)
                self.stats['clients_inserted'] += 1

            session.commit()
            return client

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ========== Scan Session Operations ==========

    def _create_scan_session(self, data: dict) -> ScanSession:
        """Create a new scan session"""
        session = get_session()
        try:
            scan = ScanSession(
                serial=data.get('serial'),
                status='live',
                start_time=datetime.utcnow(),
                interface=data.get('interface'),
                start_latitude=data.get('latitude'),
                start_longitude=data.get('longitude'),
                start_altitude=data.get('altitude')
            )
            session.add(scan)
            session.commit()
            return scan
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def _archive_scan(self, data: dict):
        """Archive a scan session"""
        session = get_session()
        try:
            scan_id = data['scan_id']
            scan = session.query(ScanSession).filter_by(id=scan_id).first()
            if scan:
                scan.status = 'archived'
                scan.end_time = datetime.utcnow()
                scan.end_latitude = data.get('latitude')
                scan.end_longitude = data.get('longitude')
                scan.end_altitude = data.get('altitude')
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ========== Query Operations ==========

    def _get_networks(self, data: dict) -> List[Network]:
        """Get networks with optional filtering"""
        session = get_session()
        try:
            query = session.query(Network)

            # Apply filters
            if data.get('encryption'):
                query = query.filter(Network.encryption.like(f"%{data['encryption']}%"))
            if data.get('min_power'):
                query = query.filter(Network.power >= data['min_power'])
            if data.get('has_clients'):
                query = query.filter(Network.clients.any())

            # Order by last seen
            query = query.order_by(Network.last_seen.desc())

            # Limit
            if data.get('limit'):
                query = query.limit(data['limit'])

            return query.all()
        finally:
            session.close()

    def _get_clients(self, data: dict) -> List[Client]:
        """Get clients with optional filtering"""
        session = get_session()
        try:
            query = session.query(Client)

            # Apply filters
            if data.get('bssid'):
                query = query.filter_by(bssid=data['bssid'])
            if data.get('unassociated'):
                query = query.filter(or_(Client.bssid == None, Client.bssid == '(not associated)'))

            # Order by last seen
            query = query.order_by(Client.last_seen.desc())

            # Limit
            if data.get('limit'):
                query = query.limit(data['limit'])

            return query.all()
        finally:
            session.close()

    # ========== Async API ==========

    def upsert_network_async(self, network_data: dict, callback=None):
        """Async network upsert"""
        self.queue.put({
            'operation': 'upsert_network',
            'data': network_data,
            'callback': callback
        })

    def upsert_client_async(self, client_data: dict, callback=None):
        """Async client upsert"""
        self.queue.put({
            'operation': 'upsert_client',
            'data': client_data,
            'callback': callback
        })

    def add_observation_async(self, obs_data: dict, callback=None):
        """Async observation insert"""
        self.queue.put({
            'operation': 'add_observation',
            'data': obs_data,
            'callback': callback
        })

    def get_stats(self) -> dict:
        """Get service statistics"""
        return {
            **self.stats,
            'queue_size': self.queue.qsize()
        }


# Global instance
_db_service = None

def get_database_service() -> DatabaseService:
    """Get or create the global database service instance"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
        _db_service.start()
    return _db_service
