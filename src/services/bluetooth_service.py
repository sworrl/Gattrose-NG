"""
Bluetooth Low Energy (BLE) Service for Gattrose-NG
Provides device discovery, GATT interrogation, and characteristic read/write operations
Uses bleak library for cross-platform async BLE communication
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict

try:
    from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False

# Standard GATT UUIDs for human-readable names
GATT_SERVICE_NAMES = {
    "00001800-0000-1000-8000-00805f9b34fb": "Generic Access",
    "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute",
    "0000180a-0000-1000-8000-00805f9b34fb": "Device Information",
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery Service",
    "00001810-0000-1000-8000-00805f9b34fb": "Blood Pressure",
    "00001816-0000-1000-8000-00805f9b34fb": "Cycling Speed and Cadence",
    "00001818-0000-1000-8000-00805f9b34fb": "Cycling Power",
    "0000181a-0000-1000-8000-00805f9b34fb": "Environmental Sensing",
    "0000181c-0000-1000-8000-00805f9b34fb": "User Data",
    "0000181d-0000-1000-8000-00805f9b34fb": "Weight Scale",
    "00001812-0000-1000-8000-00805f9b34fb": "Human Interface Device",
    "00001808-0000-1000-8000-00805f9b34fb": "Glucose",
    "00001809-0000-1000-8000-00805f9b34fb": "Health Thermometer",
    "0000180d-0000-1000-8000-00805f9b34fb": "Heart Rate",
    "00001802-0000-1000-8000-00805f9b34fb": "Immediate Alert",
    "00001803-0000-1000-8000-00805f9b34fb": "Link Loss",
    "00001804-0000-1000-8000-00805f9b34fb": "Tx Power",
    "00001805-0000-1000-8000-00805f9b34fb": "Current Time",
    "00001806-0000-1000-8000-00805f9b34fb": "Reference Time Update",
    "00001807-0000-1000-8000-00805f9b34fb": "Next DST Change",
    "0000ffe0-0000-1000-8000-00805f9b34fb": "HM-10 Serial",
    "0000fff0-0000-1000-8000-00805f9b34fb": "Vendor Specific",
}

GATT_CHARACTERISTIC_NAMES = {
    "00002a00-0000-1000-8000-00805f9b34fb": "Device Name",
    "00002a01-0000-1000-8000-00805f9b34fb": "Appearance",
    "00002a04-0000-1000-8000-00805f9b34fb": "Peripheral Preferred Connection Parameters",
    "00002a05-0000-1000-8000-00805f9b34fb": "Service Changed",
    "00002a19-0000-1000-8000-00805f9b34fb": "Battery Level",
    "00002a23-0000-1000-8000-00805f9b34fb": "System ID",
    "00002a24-0000-1000-8000-00805f9b34fb": "Model Number String",
    "00002a25-0000-1000-8000-00805f9b34fb": "Serial Number String",
    "00002a26-0000-1000-8000-00805f9b34fb": "Firmware Revision String",
    "00002a27-0000-1000-8000-00805f9b34fb": "Hardware Revision String",
    "00002a28-0000-1000-8000-00805f9b34fb": "Software Revision String",
    "00002a29-0000-1000-8000-00805f9b34fb": "Manufacturer Name String",
    "00002a2a-0000-1000-8000-00805f9b34fb": "IEEE 11073-20601 Regulatory Certification Data List",
    "00002a50-0000-1000-8000-00805f9b34fb": "PnP ID",
    "00002a37-0000-1000-8000-00805f9b34fb": "Heart Rate Measurement",
    "00002a38-0000-1000-8000-00805f9b34fb": "Body Sensor Location",
    "00002a39-0000-1000-8000-00805f9b34fb": "Heart Rate Control Point",
    "0000ffe1-0000-1000-8000-00805f9b34fb": "HM-10 Serial TX/RX",
}

GATT_DESCRIPTOR_NAMES = {
    "00002900-0000-1000-8000-00805f9b34fb": "Characteristic Extended Properties",
    "00002901-0000-1000-8000-00805f9b34fb": "Characteristic User Description",
    "00002902-0000-1000-8000-00805f9b34fb": "Client Characteristic Configuration",
    "00002903-0000-1000-8000-00805f9b34fb": "Server Characteristic Configuration",
    "00002904-0000-1000-8000-00805f9b34fb": "Characteristic Presentation Format",
    "00002905-0000-1000-8000-00805f9b34fb": "Characteristic Aggregate Format",
    "00002906-0000-1000-8000-00805f9b34fb": "Valid Range",
    "00002907-0000-1000-8000-00805f9b34fb": "External Report Reference",
    "00002908-0000-1000-8000-00805f9b34fb": "Report Reference",
}

# BLE Appearance codes
APPEARANCE_CODES = {
    0: "Unknown",
    64: "Phone",
    128: "Computer",
    192: "Watch",
    256: "Clock",
    320: "Display",
    384: "Remote Control",
    448: "Eye-glasses",
    512: "Tag",
    576: "Keyring",
    640: "Media Player",
    704: "Barcode Scanner",
    768: "Thermometer",
    832: "Heart Rate Sensor",
    896: "Blood Pressure",
    960: "Human Interface Device",
    961: "Keyboard",
    962: "Mouse",
    963: "Joystick",
    964: "Gamepad",
    965: "Digitizer Tablet",
    966: "Card Reader",
    967: "Digital Pen",
    968: "Barcode Scanner",
    1024: "Glucose Meter",
    1088: "Running Walking Sensor",
    1152: "Cycling",
    1216: "Control Device",
    1280: "Network Device",
    1344: "Sensor",
    1408: "Light Fixtures",
    1472: "Fan",
    1536: "HVAC",
    1600: "Air Conditioning",
    1664: "Humidifier",
    1728: "Heating",
    1792: "Access Control",
    1856: "Motorized Device",
    1920: "Power Device",
    1984: "Light Source",
    2048: "Window Covering",
    2112: "Audio Sink",
    2176: "Audio Source",
    2240: "Motorized Vehicle",
    2304: "Domestic Appliance",
    2368: "Wearable Audio Device",
    2432: "Aircraft",
    2496: "AV Equipment",
    2560: "Display Equipment",
    2624: "Hearing aid",
    2688: "Gaming",
    2752: "Signage",
    3136: "Pulse Oximeter",
    3200: "Weight Scale",
    3264: "Personal Mobility Device",
    3328: "Continuous Glucose Monitor",
    3392: "Insulin Pump",
    3456: "Medication Delivery",
    5184: "Outdoor Sports Activity",
}


@dataclass
class DescriptorData:
    """Data class for a GATT descriptor"""
    uuid: str
    uuid_short: str
    name: str
    handle: int
    value: Optional[bytes] = None
    value_hex: Optional[str] = None
    value_decoded: Optional[str] = None


@dataclass
class CharacteristicData:
    """Data class for a GATT characteristic"""
    uuid: str
    uuid_short: str
    name: str
    handle: int
    properties: List[str] = field(default_factory=list)
    can_read: bool = False
    can_write: bool = False
    can_write_no_response: bool = False
    can_notify: bool = False
    can_indicate: bool = False
    value: Optional[bytes] = None
    value_hex: Optional[str] = None
    value_decoded: Optional[str] = None
    descriptors: List[DescriptorData] = field(default_factory=list)


@dataclass
class ServiceData:
    """Data class for a GATT service"""
    uuid: str
    uuid_short: str
    name: str
    handle_start: int = 0
    handle_end: int = 0
    characteristics: List[CharacteristicData] = field(default_factory=list)


@dataclass
class DeviceData:
    """Data class for a discovered BLE device"""
    mac_address: str
    name: Optional[str] = None
    local_name: Optional[str] = None
    rssi: Optional[int] = None
    tx_power: Optional[int] = None
    appearance: Optional[int] = None
    appearance_name: Optional[str] = None
    manufacturer_id: Optional[int] = None
    manufacturer_data: Optional[Dict[int, bytes]] = None
    service_uuids: List[str] = field(default_factory=list)
    service_data: Optional[Dict[str, bytes]] = None
    is_connectable: bool = True
    services: List[ServiceData] = field(default_factory=list)


class BluetoothService:
    """
    Bluetooth Low Energy service for device discovery and GATT interrogation
    """

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.logger = logging.getLogger("gattrose.bluetooth")
        self.log_callback = log_callback
        self.discovered_devices: Dict[str, DeviceData] = {}
        self.scanning = False
        self._scanner = None
        self._scan_task = None
        # Persistent connection support
        self._persistent_client: Optional['BleakClient'] = None
        self._persistent_mac: Optional[str] = None
        self._persistent_lock = asyncio.Lock() if BLEAK_AVAILABLE else None

        if not BLEAK_AVAILABLE:
            self.log("[!] Bleak library not available. Install with: pip install bleak")

    def log(self, message: str):
        """Log a message"""
        self.logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def get_service_name(self, uuid: str) -> str:
        """Get human-readable service name from UUID"""
        uuid_lower = uuid.lower()
        if uuid_lower in GATT_SERVICE_NAMES:
            return GATT_SERVICE_NAMES[uuid_lower]
        # Check for short UUID pattern
        if len(uuid) == 4:
            full_uuid = f"0000{uuid}-0000-1000-8000-00805f9b34fb".lower()
            if full_uuid in GATT_SERVICE_NAMES:
                return GATT_SERVICE_NAMES[full_uuid]
        return "Unknown Service"

    def get_characteristic_name(self, uuid: str) -> str:
        """Get human-readable characteristic name from UUID"""
        uuid_lower = uuid.lower()
        if uuid_lower in GATT_CHARACTERISTIC_NAMES:
            return GATT_CHARACTERISTIC_NAMES[uuid_lower]
        return "Unknown Characteristic"

    def get_descriptor_name(self, uuid: str) -> str:
        """Get human-readable descriptor name from UUID"""
        uuid_lower = uuid.lower()
        if uuid_lower in GATT_DESCRIPTOR_NAMES:
            return GATT_DESCRIPTOR_NAMES[uuid_lower]
        return "Unknown Descriptor"

    def get_appearance_name(self, appearance: int) -> str:
        """Get appearance category name"""
        if appearance in APPEARANCE_CODES:
            return APPEARANCE_CODES[appearance]
        # Try to find the category (upper bits)
        category = (appearance >> 6) << 6
        if category in APPEARANCE_CODES:
            return f"{APPEARANCE_CODES[category]} (sub: {appearance & 0x3F})"
        return f"Unknown ({appearance})"

    def get_short_uuid(self, uuid: str) -> str:
        """Extract short UUID from full UUID if standard"""
        uuid_lower = uuid.lower()
        if uuid_lower.endswith("-0000-1000-8000-00805f9b34fb"):
            short = uuid_lower[:8].lstrip("0")
            if len(short) <= 4:
                return f"0x{short.upper().zfill(4)}"
        return uuid[:8]

    def decode_value(self, value: bytes) -> str:
        """Attempt to decode a characteristic value to human-readable form"""
        if not value:
            return ""

        # Try UTF-8 string
        try:
            decoded = value.decode('utf-8').strip('\x00')
            if decoded.isprintable() and len(decoded) > 0:
                return f"String: {decoded}"
        except:
            pass

        # Try as integers
        if len(value) == 1:
            return f"UInt8: {value[0]}"
        elif len(value) == 2:
            le = int.from_bytes(value, 'little')
            be = int.from_bytes(value, 'big')
            return f"UInt16: {le} (LE) / {be} (BE)"
        elif len(value) == 4:
            le = int.from_bytes(value, 'little')
            be = int.from_bytes(value, 'big')
            return f"UInt32: {le} (LE) / {be} (BE)"

        # Return hex if nothing else works
        return f"Bytes[{len(value)}]: {value.hex()}"

    async def scan_devices(
        self,
        duration: float = 10.0,
        callback: Optional[Callable[[DeviceData], None]] = None
    ) -> Dict[str, DeviceData]:
        """
        Scan for BLE devices

        Args:
            duration: Scan duration in seconds
            callback: Optional callback for each discovered device

        Returns:
            Dictionary of discovered devices keyed by MAC address
        """
        if not BLEAK_AVAILABLE:
            self.log("[!] Bleak not available")
            return {}

        self.scanning = True
        self.discovered_devices.clear()

        def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
            if not self.scanning:
                return

            mac = device.address.upper()

            # Parse manufacturer data
            mfr_data = None
            mfr_id = None
            if advertisement_data.manufacturer_data:
                mfr_id = list(advertisement_data.manufacturer_data.keys())[0]
                mfr_data = {k: v.hex() for k, v in advertisement_data.manufacturer_data.items()}

            # Parse appearance
            appearance = None
            appearance_name = None
            # Appearance might be in local_name or we detect from manufacturer
            # For now, leave as None - would need to connect to get this

            device_data = DeviceData(
                mac_address=mac,
                name=device.name or advertisement_data.local_name,
                local_name=advertisement_data.local_name,
                rssi=advertisement_data.rssi,
                tx_power=advertisement_data.tx_power,
                manufacturer_id=mfr_id,
                manufacturer_data=mfr_data,
                service_uuids=list(advertisement_data.service_uuids) if advertisement_data.service_uuids else [],
                service_data={k: v.hex() for k, v in advertisement_data.service_data.items()} if advertisement_data.service_data else None,
                is_connectable=True  # Assume connectable, verify on connect
            )

            self.discovered_devices[mac] = device_data

            if callback:
                callback(device_data)

            self.log(f"[+] Found: {device_data.name or 'Unknown'} [{mac}] RSSI: {device_data.rssi}")

        self.log(f"[*] Starting BLE scan for {duration}s...")

        try:
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(duration)
            await scanner.stop()
        except Exception as e:
            self.log(f"[!] Scan error: {e}")

        self.scanning = False
        self.log(f"[+] Scan complete. Found {len(self.discovered_devices)} devices.")

        return self.discovered_devices

    async def connect_and_interrogate(
        self,
        mac_address: str,
        read_values: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[DeviceData]:
        """
        Connect to a device and enumerate all GATT services, characteristics, and descriptors

        Args:
            mac_address: Device MAC address
            read_values: Whether to read characteristic values
            progress_callback: Optional callback for progress updates

        Returns:
            DeviceData with full GATT structure, or None on failure
        """
        if not BLEAK_AVAILABLE:
            self.log("[!] Bleak not available")
            return None

        def progress(msg: str):
            self.log(msg)
            if progress_callback:
                progress_callback(msg)

        progress(f"[*] Connecting to {mac_address}...")

        device_data = self.discovered_devices.get(mac_address.upper(), DeviceData(mac_address=mac_address.upper()))
        device_data.services = []

        try:
            async with BleakClient(mac_address, timeout=20.0) as client:
                if not client.is_connected:
                    progress(f"[!] Failed to connect to {mac_address}")
                    return None

                progress(f"[+] Connected to {mac_address}")

                # Get all services (convert to list for len() support)
                services = list(client.services)
                progress(f"[*] Discovering services... Found {len(services)} services")

                for service in services:
                    svc_uuid = str(service.uuid).lower()
                    svc_name = self.get_service_name(svc_uuid)
                    svc_short = self.get_short_uuid(svc_uuid)

                    service_data = ServiceData(
                        uuid=svc_uuid,
                        uuid_short=svc_short,
                        name=svc_name,
                        handle_start=service.handle,
                        handle_end=service.handle,  # Would need end handle from raw data
                        characteristics=[]
                    )

                    progress(f"  [Service] {svc_name} ({svc_short})")

                    # Get characteristics
                    for char in service.characteristics:
                        char_uuid = str(char.uuid).lower()
                        char_name = self.get_characteristic_name(char_uuid)
                        char_short = self.get_short_uuid(char_uuid)

                        # Parse properties
                        props = char.properties
                        can_read = "read" in props
                        can_write = "write" in props
                        can_write_nr = "write-without-response" in props
                        can_notify = "notify" in props
                        can_indicate = "indicate" in props

                        char_data = CharacteristicData(
                            uuid=char_uuid,
                            uuid_short=char_short,
                            name=char_name,
                            handle=char.handle,
                            properties=list(props),
                            can_read=can_read,
                            can_write=can_write,
                            can_write_no_response=can_write_nr,
                            can_notify=can_notify,
                            can_indicate=can_indicate,
                            descriptors=[]
                        )

                        # Try to read value if allowed
                        if read_values and can_read:
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                char_data.value = value
                                char_data.value_hex = value.hex() if value else None
                                char_data.value_decoded = self.decode_value(value)
                                progress(f"    [Char] {char_name} ({char_short}) = {char_data.value_decoded}")
                            except Exception as e:
                                char_data.value_decoded = f"Read error: {e}"
                                progress(f"    [Char] {char_name} ({char_short}) - Read failed: {e}")
                        else:
                            progress(f"    [Char] {char_name} ({char_short}) [{', '.join(props)}]")

                        # Get descriptors
                        for desc in char.descriptors:
                            desc_uuid = str(desc.uuid).lower()
                            desc_name = self.get_descriptor_name(desc_uuid)
                            desc_short = self.get_short_uuid(desc_uuid)

                            desc_data = DescriptorData(
                                uuid=desc_uuid,
                                uuid_short=desc_short,
                                name=desc_name,
                                handle=desc.handle
                            )

                            # Try to read descriptor
                            if read_values:
                                try:
                                    value = await client.read_gatt_descriptor(desc.handle)
                                    desc_data.value = value
                                    desc_data.value_hex = value.hex() if value else None
                                    desc_data.value_decoded = self.decode_value(value)
                                except Exception as e:
                                    desc_data.value_decoded = f"Read error: {e}"

                            char_data.descriptors.append(desc_data)
                            progress(f"      [Desc] {desc_name} ({desc_short})")

                        service_data.characteristics.append(char_data)

                    device_data.services.append(service_data)

                progress(f"[+] Interrogation complete: {len(device_data.services)} services, "
                        f"{sum(len(s.characteristics) for s in device_data.services)} characteristics")

        except Exception as e:
            progress(f"[!] Connection/interrogation error: {e}")
            return None

        return device_data

    async def read_characteristic(self, mac_address: str, char_uuid: str) -> Optional[bytes]:
        """Read a specific characteristic value"""
        if not BLEAK_AVAILABLE:
            return None

        try:
            async with BleakClient(mac_address, timeout=10.0) as client:
                if client.is_connected:
                    value = await client.read_gatt_char(char_uuid)
                    self.log(f"[+] Read {char_uuid}: {value.hex() if value else 'empty'}")
                    return value
        except Exception as e:
            self.log(f"[!] Read error: {e}")
        return None

    async def write_characteristic(
        self,
        mac_address: str,
        char_uuid: str,
        value: bytes,
        with_response: bool = True
    ) -> bool:
        """Write to a specific characteristic"""
        if not BLEAK_AVAILABLE:
            return False

        try:
            async with BleakClient(mac_address, timeout=10.0) as client:
                if client.is_connected:
                    await client.write_gatt_char(char_uuid, value, response=with_response)
                    self.log(f"[+] Wrote to {char_uuid}: {value.hex()}")
                    return True
        except Exception as e:
            self.log(f"[!] Write error: {e}")
        return False

    async def subscribe_notifications(
        self,
        mac_address: str,
        char_uuid: str,
        callback: Callable[[str, bytes], None],
        duration: float = 30.0
    ):
        """Subscribe to notifications from a characteristic"""
        if not BLEAK_AVAILABLE:
            return

        def notification_handler(sender: BleakGATTCharacteristic, data: bytes):
            callback(str(sender.uuid), data)
            self.log(f"[Notify] {sender.uuid}: {data.hex()}")

        try:
            async with BleakClient(mac_address, timeout=10.0) as client:
                if client.is_connected:
                    await client.start_notify(char_uuid, notification_handler)
                    self.log(f"[+] Subscribed to {char_uuid}")
                    await asyncio.sleep(duration)
                    await client.stop_notify(char_uuid)
                    self.log(f"[*] Unsubscribed from {char_uuid}")
        except Exception as e:
            self.log(f"[!] Notification error: {e}")

    # ========== Persistent Connection Methods ==========
    # These allow maintaining a single connection for multiple operations

    async def connect_persistent(self, mac_address: str) -> bool:
        """
        Establish a persistent connection to a device.
        This connection stays open for multiple read/write/notify operations.
        """
        if not BLEAK_AVAILABLE:
            return False

        async with self._persistent_lock:
            # Disconnect existing connection if different device
            if self._persistent_client and self._persistent_mac != mac_address:
                await self.disconnect_persistent()

            # Already connected to this device
            if self._persistent_client and self._persistent_client.is_connected:
                return True

            try:
                self._persistent_client = BleakClient(mac_address, timeout=15.0)
                await self._persistent_client.connect()
                if self._persistent_client.is_connected:
                    self._persistent_mac = mac_address
                    self.log(f"[+] Persistent connection established to {mac_address}")
                    return True
                else:
                    self._persistent_client = None
                    return False
            except Exception as e:
                self.log(f"[!] Persistent connection error: {e}")
                self._persistent_client = None
                return False

    async def disconnect_persistent(self):
        """Disconnect the persistent connection"""
        if self._persistent_client:
            try:
                if self._persistent_client.is_connected:
                    await self._persistent_client.disconnect()
                    self.log(f"[*] Disconnected from {self._persistent_mac}")
            except Exception as e:
                self.log(f"[!] Disconnect error: {e}")
            finally:
                self._persistent_client = None
                self._persistent_mac = None

    def is_connected_persistent(self, mac_address: str = None) -> bool:
        """Check if persistently connected to a device"""
        if not self._persistent_client:
            return False
        if mac_address and self._persistent_mac != mac_address:
            return False
        return self._persistent_client.is_connected

    async def write_persistent(self, char_uuid: str, value: bytes, with_response: bool = False) -> bool:
        """Write to characteristic using persistent connection"""
        if not self._persistent_client or not self._persistent_client.is_connected:
            self.log("[!] No persistent connection")
            return False

        try:
            await self._persistent_client.write_gatt_char(char_uuid, value, response=with_response)
            self.log(f"[+] Wrote to {char_uuid}: {value.hex()}")
            return True
        except Exception as e:
            self.log(f"[!] Write error: {e}")
            return False

    async def read_persistent(self, char_uuid: str) -> Optional[bytes]:
        """Read characteristic using persistent connection"""
        if not self._persistent_client or not self._persistent_client.is_connected:
            self.log("[!] No persistent connection")
            return None

        try:
            value = await self._persistent_client.read_gatt_char(char_uuid)
            self.log(f"[+] Read {char_uuid}: {value.hex() if value else 'empty'}")
            return value
        except Exception as e:
            self.log(f"[!] Read error: {e}")
            return None

    async def subscribe_persistent(
        self,
        char_uuid: str,
        callback: Callable[[str, bytes], None]
    ) -> bool:
        """Subscribe to notifications using persistent connection"""
        if not self._persistent_client or not self._persistent_client.is_connected:
            self.log("[!] No persistent connection")
            return False

        def notification_handler(sender: BleakGATTCharacteristic, data: bytes):
            callback(str(sender.uuid), data)

        try:
            await self._persistent_client.start_notify(char_uuid, notification_handler)
            self.log(f"[+] Subscribed to {char_uuid}")
            return True
        except Exception as e:
            self.log(f"[!] Subscribe error: {e}")
            return False

    async def unsubscribe_persistent(self, char_uuid: str) -> bool:
        """Unsubscribe from notifications"""
        if not self._persistent_client or not self._persistent_client.is_connected:
            return False

        try:
            await self._persistent_client.stop_notify(char_uuid)
            self.log(f"[*] Unsubscribed from {char_uuid}")
            return True
        except Exception as e:
            self.log(f"[!] Unsubscribe error: {e}")
            return False

    def export_device_json(self, device_data: DeviceData) -> str:
        """Export device data as JSON for use in other tools/Claude"""
        def convert(obj):
            if isinstance(obj, bytes):
                return obj.hex()
            elif hasattr(obj, '__dict__'):
                return {k: convert(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(i) for i in obj]
            return obj

        data = convert(device_data)
        return json.dumps(data, indent=2)

    def generate_controller_template(self, device_data: DeviceData) -> str:
        """
        Generate a Python controller template for the interrogated device

        This creates a ready-to-use Python class that can control the device
        """
        template = f'''"""
Auto-generated BLE Controller for {device_data.name or device_data.mac_address}
Generated by Gattrose-NG on {datetime.now().isoformat()}

Device: {device_data.name or 'Unknown'}
MAC: {device_data.mac_address}
Services: {len(device_data.services)}
"""

import asyncio
from bleak import BleakClient

class BLEDeviceController:
    """Controller for {device_data.name or device_data.mac_address}"""

    MAC_ADDRESS = "{device_data.mac_address}"

    # Service UUIDs
'''
        # Add service constants
        for svc in device_data.services:
            svc_const = svc.name.upper().replace(" ", "_").replace("-", "_")
            template += f'    SERVICE_{svc_const} = "{svc.uuid}"\n'

        template += "\n    # Characteristic UUIDs\n"

        # Add characteristic constants
        for svc in device_data.services:
            for char in svc.characteristics:
                char_const = char.name.upper().replace(" ", "_").replace("-", "_")
                props_str = ", ".join(char.properties)
                template += f'    CHAR_{char_const} = "{char.uuid}"  # [{props_str}]\n'

        template += '''
    def __init__(self, mac_address: str = None):
        self.mac_address = mac_address or self.MAC_ADDRESS
        self.client = None

    async def connect(self) -> bool:
        """Connect to the device"""
        self.client = BleakClient(self.mac_address, timeout=10.0)
        await self.client.connect()
        return self.client.is_connected

    async def disconnect(self):
        """Disconnect from the device"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()

'''
        # Add read methods for readable characteristics
        for svc in device_data.services:
            for char in svc.characteristics:
                if char.can_read:
                    method_name = char.name.lower().replace(" ", "_").replace("-", "_")
                    template += f'''    async def read_{method_name}(self) -> bytes:
        """Read {char.name}"""
        return await self.client.read_gatt_char(self.CHAR_{char.name.upper().replace(" ", "_").replace("-", "_")})

'''

        # Add write methods for writable characteristics
        for svc in device_data.services:
            for char in svc.characteristics:
                if char.can_write or char.can_write_no_response:
                    method_name = char.name.lower().replace(" ", "_").replace("-", "_")
                    response = "True" if char.can_write else "False"
                    template += f'''    async def write_{method_name}(self, value: bytes):
        """Write to {char.name}"""
        await self.client.write_gatt_char(
            self.CHAR_{char.name.upper().replace(" ", "_").replace("-", "_")},
            value,
            response={response}
        )

'''

        # Add notify methods
        for svc in device_data.services:
            for char in svc.characteristics:
                if char.can_notify or char.can_indicate:
                    method_name = char.name.lower().replace(" ", "_").replace("-", "_")
                    template += f'''    async def subscribe_{method_name}(self, callback):
        """Subscribe to {char.name} notifications"""
        await self.client.start_notify(
            self.CHAR_{char.name.upper().replace(" ", "_").replace("-", "_")},
            callback
        )

    async def unsubscribe_{method_name}(self):
        """Unsubscribe from {char.name} notifications"""
        await self.client.stop_notify(
            self.CHAR_{char.name.upper().replace(" ", "_").replace("-", "_")}
        )

'''

        # Add example usage
        template += '''
# Example usage:
async def main():
    async with BLEDeviceController() as device:
        # Read device info
'''
        # Add example reads
        for svc in device_data.services:
            for char in svc.characteristics:
                if char.can_read and "name" in char.name.lower():
                    method_name = char.name.lower().replace(" ", "_").replace("-", "_")
                    template += f'        name = await device.read_{method_name}()\n'
                    template += f'        print(f"Device: {{name.decode()}}")\n'
                    break

        template += '''
if __name__ == "__main__":
    asyncio.run(main())
'''
        return template
