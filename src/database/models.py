"""
Database models for Gattrose-NG
Stores wireless network data, scan results, and WiGLE imports
All entities have unique serial numbers and timestamps
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    Boolean, Text, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


def generate_serial_number(prefix: str = "", length: int = 16) -> str:
    """Generate serial number for database record"""
    from ..utils.serial import generate_serial
    return generate_serial(prefix)


class Network(Base):
    """Wireless network/access point"""
    __tablename__ = 'networks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("ap"))
    bssid = Column(String(17), unique=True, nullable=False, index=True)  # MAC address
    ssid = Column(String(32), nullable=True, index=True)  # Network name

    # Location data
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)

    # Network properties
    channel = Column(Integer, nullable=True)
    frequency = Column(Integer, nullable=True)
    speed = Column(String(10), nullable=True)  # "54", "150", etc.
    encryption = Column(String(50), nullable=True)  # WEP, WPA, WPA2, WPA3, Open
    cipher = Column(String(50), nullable=True)  # TKIP, CCMP, etc.
    authentication = Column(String(50), nullable=True)  # PSK, MGT, etc.

    # Signal strength
    max_signal = Column(Integer, nullable=True)  # dBm
    min_signal = Column(Integer, nullable=True)
    avg_signal = Column(Integer, nullable=True)
    current_signal = Column(Integer, nullable=True)  # Most recent signal

    # Statistics
    beacon_count = Column(Integer, default=0)
    iv_count = Column(Integer, default=0)
    lan_ip = Column(String(15), nullable=True)

    # Vendor info
    manufacturer = Column(String(100), nullable=True)
    device_type = Column(String(100), nullable=True)
    device_confidence = Column(Integer, nullable=True)  # 0-100

    # Attack scoring
    current_attack_score = Column(Integer, nullable=True)  # 0-100 (current)
    highest_attack_score = Column(Integer, nullable=True)  # Highest score ever observed
    lowest_attack_score = Column(Integer, nullable=True)   # Lowest score ever observed
    risk_level = Column(String(20), nullable=True)  # CRITICAL, HIGH, MEDIUM, LOW

    # WPS status
    wps_enabled = Column(Boolean, default=False)
    wps_locked = Column(Boolean, default=False)
    wps_version = Column(String(20), nullable=True)
    wps_pin = Column(String(8), nullable=True)  # WPS PIN if cracked

    # Cracking status
    is_cracked = Column(Boolean, default=False)
    cracked_at = Column(DateTime, nullable=True)
    password = Column(String(63), nullable=True)  # WPA/WPA2 password if cracked
    crack_method = Column(String(50), nullable=True)  # WPS, WPA, WEP, Handshake, etc.

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # WiGLE integration
    wigle_id = Column(String(50), nullable=True, unique=True, index=True)

    # Blacklist status
    blacklisted = Column(Boolean, default=False, nullable=False, index=True)
    blacklist_reason = Column(Text, nullable=True)  # Why it was blacklisted

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    observations = relationship("NetworkObservation", back_populates="network", cascade="all, delete-orphan")
    handshakes = relationship("Handshake", back_populates="network", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Network(bssid='{self.bssid}', ssid='{self.ssid}', encryption='{self.encryption}')>"


class NetworkObservation(Base):
    """Individual observation/sighting of a network"""
    __tablename__ = 'network_observations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("obs"))
    network_id = Column(Integer, ForeignKey('networks.id'), nullable=False, index=True)

    # Location at time of observation
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)  # GPS accuracy in meters
    gps_source = Column(String(20), nullable=True)  # 'gpsd', 'phone-bt', 'phone-usb', 'geoip'

    # Signal at time of observation
    signal_strength = Column(Integer, nullable=True)  # dBm

    # Time of observation
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Source of observation
    source = Column(String(50), nullable=True)  # 'scan', 'wigle', 'manual', etc.

    # Relationship
    network = relationship("Network", back_populates="observations")

    def __repr__(self):
        return f"<NetworkObservation(serial='{self.serial}', network_id={self.network_id}, timestamp='{self.timestamp}')>"


class Client(Base):
    """Wireless client device"""
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("cl"))
    mac_address = Column(String(17), unique=True, nullable=False, index=True)

    # Associated networks (can be inferred from probes/associations)
    associated_networks = Column(Text, nullable=True)  # JSON array of BSSIDs

    # Device info
    manufacturer = Column(String(100), nullable=True)
    device_type = Column(String(100), nullable=True)
    device_confidence = Column(Integer, nullable=True)  # 0-100

    # Signal strength
    max_signal = Column(Integer, nullable=True)  # dBm
    min_signal = Column(Integer, nullable=True)
    current_signal = Column(Integer, nullable=True)

    # Timestamps
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Client(mac='{self.mac_address}', manufacturer='{self.manufacturer}')>"


class Handshake(Base):
    """Captured WPA/WPA2 handshakes"""
    __tablename__ = 'handshakes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("hs"))
    network_id = Column(Integer, ForeignKey('networks.id'), nullable=False, index=True)

    # Handshake file info
    file_path = Column(String(500), nullable=False)  # Path to .cap/.pcap file
    file_hash = Column(String(64), nullable=True)  # SHA256 of file

    # Handshake type and quality
    handshake_type = Column(String(20), nullable=True)  # 'WPA', 'WPA2', 'WPA3'
    is_complete = Column(Boolean, default=False)
    quality = Column(Integer, nullable=True)  # Quality score 0-100

    # Capture info
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    client_mac = Column(String(17), nullable=True)

    # Cracking status
    is_cracked = Column(Boolean, default=False)
    cracked_at = Column(DateTime, nullable=True)
    password = Column(String(63), nullable=True)  # Max WPA password length

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationship
    network = relationship("Network", back_populates="handshakes")

    def __repr__(self):
        return f"<Handshake(network_id={self.network_id}, complete={self.is_complete}, cracked={self.is_cracked})>"


class ScanSession(Base):
    """Scanning session metadata

    Supports both live and archived scans. Only one scan can be "live" at a time.
    When a new scan starts, the previous live scan is archived.
    """
    __tablename__ = 'scan_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("scan"))

    # Session info
    name = Column(String(100), nullable=True)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, nullable=True)

    # Status: 'live', 'archived', 'failed'
    status = Column(String(20), nullable=False, default='live', index=True)

    # Scan parameters
    interface = Column(String(20), nullable=True)
    channels = Column(String(100), nullable=True)  # Comma-separated
    scan_type = Column(String(50), nullable=True)  # 'passive', 'active', 'monitor'

    # Results summary
    networks_found = Column(Integer, default=0)
    clients_found = Column(Integer, default=0)
    handshakes_captured = Column(Integer, default=0)

    # Location info (for stationary or start of mobile scan)
    start_latitude = Column(Float, nullable=True)
    start_longitude = Column(Float, nullable=True)
    start_altitude = Column(Float, nullable=True)

    # End location (for mobile scans)
    end_latitude = Column(Float, nullable=True)
    end_longitude = Column(Float, nullable=True)
    end_altitude = Column(Float, nullable=True)

    # CSV file path (for reference)
    csv_path = Column(String(500), nullable=True)

    # Metadata
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ScanSession(id={self.id}, status='{self.status}', start='{self.start_time}', networks={self.networks_found})>"


class WiGLEImport(Base):
    """Track WiGLE data imports"""
    __tablename__ = 'wigle_imports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("wi"))

    # Import info
    import_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    file_path = Column(String(500), nullable=True)
    file_hash = Column(String(64), nullable=True)

    # Import results
    networks_imported = Column(Integer, default=0)
    networks_updated = Column(Integer, default=0)
    networks_skipped = Column(Integer, default=0)

    # Metadata
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<WiGLEImport(id={self.id}, time='{self.import_time}', imported={self.networks_imported})>"


class Setting(Base):
    """Application settings stored in database

    Replaces YAML config files with database storage.
    All settings are key-value pairs with type information.
    """
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)  # Setting key (e.g., 'app.theme')
    value = Column(Text, nullable=True)  # Setting value (stored as string, converted by type)
    value_type = Column(String(20), nullable=False, default='string')  # 'string', 'int', 'float', 'bool', 'json'
    category = Column(String(50), nullable=True, index=True)  # 'app', 'wifi', 'bluetooth', 'sdr', 'database', etc.
    description = Column(Text, nullable=True)  # Human-readable description
    default_value = Column(Text, nullable=True)  # Default value if not set

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value}', type='{self.value_type}')>"

    def get_value(self):
        """Get typed value"""
        if self.value is None:
            return self.default_value

        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        else:  # string
            return self.value

    def set_value(self, value):
        """Set typed value"""
        if value is None:
            self.value = None
        elif self.value_type == 'json':
            import json
            self.value = json.dumps(value)
        else:
            self.value = str(value)

        self.updated_at = datetime.utcnow()


class OUIDatabase(Base):
    """OUI (Organizationally Unique Identifier) Database

    Stores MAC address vendor lookups from IEEE and Wireshark.
    Downloaded periodically and stored locally for fast lookups.
    """
    __tablename__ = 'oui_database'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # MAC prefix (first 3 or 6 bytes)
    mac_prefix = Column(String(17), unique=True, nullable=False, index=True)  # e.g., "00:11:22" or "00:11:22:33:44:55"
    prefix_length = Column(Integer, nullable=False)  # 24 or 48 bits

    # Vendor information
    vendor_name = Column(String(200), nullable=False, index=True)
    vendor_name_short = Column(String(100), nullable=True)  # Short/abbreviated name

    # Address information
    address = Column(Text, nullable=True)
    country = Column(String(100), nullable=True, index=True)

    # Source of data
    source = Column(String(50), nullable=False)  # 'ieee', 'wireshark', 'manual'
    source_url = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<OUIDatabase(prefix='{self.mac_prefix}', vendor='{self.vendor_name}')>"


class OUIUpdate(Base):
    """Track OUI database update history"""
    __tablename__ = 'oui_updates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("ou"))

    # Update info
    update_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    source = Column(String(50), nullable=False)  # 'ieee', 'wireshark'

    # Results
    records_added = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_total = Column(Integer, default=0)

    # Source file info
    source_url = Column(String(500), nullable=True)
    source_file_hash = Column(String(64), nullable=True)
    source_file_size = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), nullable=False, default='success')  # 'success', 'failed', 'partial'
    error_message = Column(Text, nullable=True)

    # Metadata
    duration_seconds = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<OUIUpdate(source='{self.source}', time='{self.update_time}', total={self.records_total})>"


class AttackQueue(Base):
    """Attack queue for pending attacks

    Stores targets that need to be attacked.
    The attacker service processes items from this queue.
    """
    __tablename__ = 'attack_queue'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("aq"))

    # Target network
    network_id = Column(Integer, ForeignKey('networks.id'), nullable=False, index=True)

    # Attack details
    attack_type = Column(String(50), nullable=False, index=True)  # 'handshake', 'wps', 'pmkid', 'auto'
    priority = Column(Integer, default=50, nullable=False, index=True)  # 0-100, higher = more urgent

    # Status
    status = Column(String(20), nullable=False, default='pending', index=True)  # 'pending', 'in_progress', 'completed', 'failed'

    # Timing
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Results
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    result_data = Column(Text, nullable=True)  # JSON with results

    # Retry info
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationship
    network = relationship("Network")

    def __repr__(self):
        return f"<AttackQueue(id={self.id}, type='{self.attack_type}', status='{self.status}', priority={self.priority})>"


# Create indexes for performance
Index('idx_network_location', Network.latitude, Network.longitude)
Index('idx_network_encryption', Network.encryption)
Index('idx_network_last_seen', Network.last_seen)
Index('idx_observation_timestamp', NetworkObservation.timestamp)
Index('idx_handshake_captured', Handshake.captured_at)
Index('idx_scan_session_status', ScanSession.status)
Index('idx_scan_session_location', ScanSession.start_latitude, ScanSession.start_longitude)
Index('idx_oui_prefix', OUIDatabase.mac_prefix)
Index('idx_oui_vendor', OUIDatabase.vendor_name)
Index('idx_attack_queue_status', AttackQueue.status)
Index('idx_attack_queue_priority', AttackQueue.priority)
Index('idx_attack_queue_type', AttackQueue.attack_type)

class CurrentScanNetwork(Base):
    """Current scan networks - ephemeral table for active scan data

    This table is cleared when a new scan starts and populated in real-time
    as airodump-ng CSV is parsed. GUI reads from this table instead of CSV files.
    Data is periodically upserted to the networks table for historical tracking.
    """
    __tablename__ = 'current_scan_networks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("csn"))
    bssid = Column(String(17), unique=True, nullable=False, index=True)  # MAC address
    ssid = Column(String(32), nullable=True)  # Network name

    # Network properties (from airodump CSV)
    channel = Column(Integer, nullable=True)
    encryption = Column(String(50), nullable=True)  # Privacy column
    cipher = Column(String(50), nullable=True)
    authentication = Column(String(50), nullable=True)
    power = Column(Integer, nullable=True)  # Current signal dBm
    beacon_count = Column(Integer, default=0)
    iv_count = Column(Integer, default=0)
    lan_ip = Column(String(15), nullable=True)
    speed = Column(String(10), nullable=True)

    # Enhanced data (from fingerprinting/enrichment)
    vendor = Column(String(100), nullable=True)
    device_type = Column(String(100), nullable=True)
    wps_enabled = Column(Boolean, default=False)
    wps_locked = Column(Boolean, default=False)
    wps_version = Column(String(20), nullable=True)
    attack_score = Column(Float, nullable=True)

    # GPS/Location data (CRITICAL for wardriving/mapping)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    gps_accuracy = Column(Float, nullable=True)  # GPS accuracy in meters
    gps_source = Column(String(20), nullable=True)  # 'gpsd', 'phone-bt', 'phone-usb', 'geoip'

    # Timestamps (from CSV)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)

    # Internal tracking
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CurrentScanNetwork(bssid='{self.bssid}', ssid='{self.ssid}', power={self.power})>"


class CurrentScanClient(Base):
    """Current scan clients - ephemeral table for active scan data

    This table is cleared when a new scan starts and populated in real-time
    as airodump-ng CSV is parsed. GUI reads from this table instead of CSV files.
    Data is periodically upserted to the clients table for historical tracking.
    """
    __tablename__ = 'current_scan_clients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("csc"))
    mac_address = Column(String(17), unique=True, nullable=False, index=True)
    bssid = Column(String(17), nullable=True, index=True)  # Associated AP (or "(not associated)")

    # Client properties (from airodump CSV)
    power = Column(Integer, nullable=True)  # Current signal dBm
    packets = Column(Integer, default=0)
    probed_essids = Column(Text, nullable=True)  # Comma-separated list

    # Enhanced data
    vendor = Column(String(100), nullable=True)
    device_type = Column(String(100), nullable=True)

    # GPS/Location data (CRITICAL for wardriving/mapping)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    gps_accuracy = Column(Float, nullable=True)  # GPS accuracy in meters
    gps_source = Column(String(20), nullable=True)  # 'gpsd', 'phone-bt', 'phone-usb', 'geoip'

    # Timestamps (from CSV)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)

    # Internal tracking
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CurrentScanClient(mac='{self.mac_address}', bssid='{self.bssid}')>"


# ============================================================================
# BLUETOOTH MODELS
# ============================================================================

class BluetoothDevice(Base):
    """Discovered Bluetooth device"""
    __tablename__ = 'bluetooth_devices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("bt"))
    mac_address = Column(String(17), unique=True, nullable=False, index=True)

    # Device identification
    name = Column(String(100), nullable=True, index=True)
    local_name = Column(String(100), nullable=True)  # Advertised local name

    # Device classification
    device_type = Column(String(50), nullable=True)  # phone, headphones, computer, iot, etc.
    appearance = Column(Integer, nullable=True)  # BLE appearance value
    manufacturer_id = Column(Integer, nullable=True)  # Company identifier
    manufacturer_name = Column(String(100), nullable=True)

    # Connection info
    is_connectable = Column(Boolean, default=True)
    is_paired = Column(Boolean, default=False)
    is_bonded = Column(Boolean, default=False)
    address_type = Column(String(20), nullable=True)  # public, random, public-identity, random-static

    # Signal strength
    rssi = Column(Integer, nullable=True)  # Last seen RSSI
    max_rssi = Column(Integer, nullable=True)
    min_rssi = Column(Integer, nullable=True)
    tx_power = Column(Integer, nullable=True)  # Advertised TX power

    # Advertising data
    manufacturer_data = Column(Text, nullable=True)  # JSON hex data
    service_uuids = Column(Text, nullable=True)  # JSON array of advertised UUIDs
    service_data = Column(Text, nullable=True)  # JSON service data

    # GATT interrogation status
    is_interrogated = Column(Boolean, default=False)
    interrogation_time = Column(DateTime, nullable=True)
    services_count = Column(Integer, nullable=True)
    characteristics_count = Column(Integer, nullable=True)

    # Location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Timestamps
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    services = relationship("BluetoothService", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BluetoothDevice(mac='{self.mac_address}', name='{self.name}')>"


class BluetoothService(Base):
    """GATT Service discovered on a Bluetooth device"""
    __tablename__ = 'bluetooth_services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("bs"))
    device_id = Column(Integer, ForeignKey('bluetooth_devices.id'), nullable=False, index=True)

    # Service identification
    uuid = Column(String(36), nullable=False, index=True)  # Full UUID
    uuid_short = Column(String(8), nullable=True)  # Short form (0x1800)
    name = Column(String(100), nullable=True)  # Human-readable name

    # Service properties
    is_primary = Column(Boolean, default=True)
    handle_start = Column(Integer, nullable=True)
    handle_end = Column(Integer, nullable=True)

    # Timestamps
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    device = relationship("BluetoothDevice", back_populates="services")
    characteristics = relationship("BluetoothCharacteristic", back_populates="service", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BluetoothService(uuid='{self.uuid}', name='{self.name}')>"


class BluetoothCharacteristic(Base):
    """GATT Characteristic within a Bluetooth service"""
    __tablename__ = 'bluetooth_characteristics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("bc"))
    service_id = Column(Integer, ForeignKey('bluetooth_services.id'), nullable=False, index=True)

    # Characteristic identification
    uuid = Column(String(36), nullable=False, index=True)
    uuid_short = Column(String(8), nullable=True)
    name = Column(String(100), nullable=True)
    handle = Column(Integer, nullable=True)

    # Properties (bitmap as string for readability)
    properties = Column(String(100), nullable=True)  # "read,write,notify" etc.
    properties_raw = Column(Integer, nullable=True)  # Raw bitmap

    # Permissions
    can_read = Column(Boolean, default=False)
    can_write = Column(Boolean, default=False)
    can_write_no_response = Column(Boolean, default=False)
    can_notify = Column(Boolean, default=False)
    can_indicate = Column(Boolean, default=False)

    # Value storage
    last_value = Column(Text, nullable=True)  # Hex-encoded value
    last_value_decoded = Column(Text, nullable=True)  # Attempted decode (UTF-8, int, etc.)
    last_read_at = Column(DateTime, nullable=True)

    # Timestamps
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    service = relationship("BluetoothService", back_populates="characteristics")
    descriptors = relationship("BluetoothDescriptor", back_populates="characteristic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BluetoothCharacteristic(uuid='{self.uuid}', name='{self.name}', props='{self.properties}')>"


class BluetoothDescriptor(Base):
    """GATT Descriptor within a Bluetooth characteristic"""
    __tablename__ = 'bluetooth_descriptors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("bd"))
    characteristic_id = Column(Integer, ForeignKey('bluetooth_characteristics.id'), nullable=False, index=True)

    # Descriptor identification
    uuid = Column(String(36), nullable=False, index=True)
    uuid_short = Column(String(8), nullable=True)
    name = Column(String(100), nullable=True)
    handle = Column(Integer, nullable=True)

    # Value
    value = Column(Text, nullable=True)  # Hex-encoded
    value_decoded = Column(Text, nullable=True)
    last_read_at = Column(DateTime, nullable=True)

    # Timestamps
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    characteristic = relationship("BluetoothCharacteristic", back_populates="descriptors")

    def __repr__(self):
        return f"<BluetoothDescriptor(uuid='{self.uuid}', name='{self.name}')>"


class BluetoothInterrogation(Base):
    """Log of Bluetooth device interrogation sessions"""
    __tablename__ = 'bluetooth_interrogations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("bi"))
    device_id = Column(Integer, ForeignKey('bluetooth_devices.id'), nullable=False, index=True)

    # Session info
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default='in_progress')  # in_progress, completed, failed

    # Results
    services_found = Column(Integer, default=0)
    characteristics_found = Column(Integer, default=0)
    descriptors_found = Column(Integer, default=0)
    values_read = Column(Integer, default=0)

    # Full interrogation data as JSON for export
    full_data = Column(Text, nullable=True)  # Complete JSON dump

    # Error tracking
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<BluetoothInterrogation(device_id={self.device_id}, status='{self.status}')>"


# Bluetooth indexes
Index('idx_bt_device_mac', BluetoothDevice.mac_address)
Index('idx_bt_device_name', BluetoothDevice.name)
Index('idx_bt_device_last_seen', BluetoothDevice.last_seen)
Index('idx_bt_service_uuid', BluetoothService.uuid)
Index('idx_bt_char_uuid', BluetoothCharacteristic.uuid)


class TriangulationNode(Base):
    """Triangulation Node - Remote scanner for distributed triangulation

    Represents a remote Raspberry Pi or other device that scans WiFi networks
    and reports observations to the central orchestrator for triangulation.
    """
    __tablename__ = 'triangulation_nodes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("tn"))

    # Node identification
    node_id = Column(String(50), unique=True, nullable=False, index=True)  # Unique node identifier
    name = Column(String(100), nullable=True)  # Friendly name
    description = Column(Text, nullable=True)

    # Node location (static for fixed nodes)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    location_description = Column(String(200), nullable=True)  # e.g., "Roof of Building A"

    # Node status
    status = Column(String(20), nullable=False, default='offline')  # online, offline, error
    last_seen = Column(DateTime, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)

    # Node configuration
    is_mobile = Column(Boolean, default=False)  # Mobile node (has GPS) vs fixed node
    scan_interval = Column(Integer, default=60)  # Seconds between scans
    channel_hop_interval = Column(Float, default=0.5)  # Channel hopping speed
    enabled = Column(Boolean, default=True)  # Is node enabled for scanning

    # Hardware info
    hardware_info = Column(Text, nullable=True)  # JSON: CPU, RAM, WiFi adapter, etc.
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    api_key = Column(String(64), nullable=True)  # Authentication key for node

    # Statistics
    total_scans = Column(Integer, default=0)
    total_networks_observed = Column(Integer, default=0)
    total_observations = Column(Integer, default=0)  # Total signal observations reported
    uptime_seconds = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<TriangulationNode(node_id='{self.node_id}', name='{self.name}', status='{self.status}')>"


class NodeObservation(Base):
    """WiFi network observation from a triangulation node

    Stores individual signal strength observations from remote nodes for triangulation.
    """
    __tablename__ = 'node_observations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial = Column(String(20), unique=True, nullable=False, index=True, default=lambda: generate_serial_number("obs"))

    # Node and network
    node_id = Column(String(50), ForeignKey('triangulation_nodes.node_id'), nullable=False, index=True)
    bssid = Column(String(17), nullable=False, index=True)  # Network MAC address

    # Observation data
    signal_strength = Column(Integer, nullable=False)  # dBm
    channel = Column(Integer, nullable=True)

    # Location (from node's GPS at time of observation)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    gps_accuracy = Column(Float, nullable=True)

    # Timestamp
    observed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<NodeObservation(node_id='{self.node_id}', bssid='{self.bssid}', signal={self.signal_strength}dBm)>"


# Database setup
_engine = None
_Session = None


def init_db(db_path: str = None):
    """Initialize database connection"""
    global _engine, _Session

    if db_path is None:
        from pathlib import Path
        import os

        # Always use system database at /opt/gattrose-ng if it exists
        system_db = Path("/opt/gattrose-ng/data/database/gattrose.db")
        if system_db.parent.exists():
            db_path = system_db
        else:
            # Fallback to local database for development
            db_dir = Path.cwd() / "data" / "database"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "gattrose.db"

    _engine = create_engine(f'sqlite:///{db_path}', echo=False)
    _Session = sessionmaker(bind=_engine)

    # Create all tables
    Base.metadata.create_all(_engine)

    return _engine


def get_session():
    """Get database session"""
    global _Session

    if _Session is None:
        init_db()

    return _Session()


def get_engine():
    """Get database engine"""
    global _engine

    if _engine is None:
        init_db()

    return _engine
