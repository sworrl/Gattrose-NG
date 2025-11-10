# Gattrose-NG Serialization System

## Overview

Every record and event in Gattrose-NG's database is assigned a **unique serial number (SN)**. This provides robust tracking, auditing, and identification of all entities throughout their lifecycle.

## Serial Number Format

Serial numbers follow this format:
```
[PREFIX][TIMESTAMP_BASE36][RANDOM]
```

- **Prefix**: 2-4 character entity type identifier (e.g., "AP", "OBS", "CSN")
- **Timestamp**: 8-character base36-encoded Unix timestamp (embedded time information)
- **Random**: Cryptographically random characters from charset

### Character Set
```
ABCDEFGHJKLMNPQRSTUVWXYZ23456789
```
Note: Excludes ambiguous characters (O, 0, I, 1) for readability

## Entity Prefixes

| Entity Type | Prefix | Length | Example |
|-------------|--------|--------|---------|
| Access Point (Network) | AP | 18 | `AP01LGF5A2VR43G6AR` |
| Client | CL | 18 | `CL01LGF5A2SNFDCAMZ` |
| Handshake | HS | 18 | `HS01LGF5A2XMDP8KQR` |
| Scan Session | SESS | 20 | `SESS01LGF5A2VKRM3PBX` |
| Network Observation | OBS | 20 | `OBS01LGF5A2VVZLDKK4J` |
| WiGLE Import | WI | 18 | `WI01LGF5A2HMRV9XTN` |
| OUI Update | OU | 18 | `OU01LGF5A2KPQR7SMT` |
| Attack Queue | AQ | 18 | `AQ01LGF5A2NXVM8KRP` |
| Current Scan Network | CSN | 20 | `CSN01LGF5A2B96S52GUM` |
| Current Scan Client | CSC | 20 | `CSC01LGF5A2KUB9JYE6D` |

## Database Models with Serials

### ✅ Permanent/Historical Tables
- **Network** (`networks`) - All discovered access points
- **Client** (`clients`) - All discovered client devices
- **Handshake** (`handshakes`) - Captured WPA handshakes
- **ScanSession** (`scan_sessions`) - Scanning session metadata
- **NetworkObservation** (`network_observations`) - Individual AP sightings with GPS
- **WiGLEImport** (`wigle_imports`) - WiGLE data import tracking
- **OUIUpdate** (`oui_updates`) - MAC vendor database updates
- **AttackQueue** (`attack_queue`) - Pending attack jobs

### ✅ Ephemeral/Current Scan Tables
- **CurrentScanNetwork** (`current_scan_networks`) - Live scan data
- **CurrentScanClient** (`current_scan_clients`) - Live client data

### ❌ Tables Without Serials (By Design)
- **Setting** - Key-value configuration (keyed by setting name)
- **OUIDatabase** - MAC vendor lookup table (keyed by MAC prefix)

## Serial Generation

### Automatic Generation
Serials are automatically generated when records are created:

```python
from src.database.models import Network, get_session

session = get_session()
network = Network(
    bssid="AA:BB:CC:DD:EE:FF",
    ssid="MyNetwork"
    # serial is auto-generated via default lambda
)
session.add(network)
session.commit()

print(network.serial)  # e.g., "AP01LGF5A2VR43G6AR"
```

### Manual Generation
You can also generate serials manually:

```python
from src.utils.serial import generate_serial

# Generate by entity type
ap_serial = generate_serial("ap")
obs_serial = generate_serial("obs")

# Or use specific methods
from src.utils.serial import SerialGenerator
ap_serial = SerialGenerator.generate_ap_serial()
```

## Benefits of Serialization

1. **Unique Identification**: Every record has a globally unique identifier
2. **Timestamp Embedded**: Serial contains creation time (parseable)
3. **Human Readable**: Avoids ambiguous characters
4. **Audit Trail**: Track records across systems and exports
5. **WiGLE Integration**: Can be used for data synchronization
6. **Debugging**: Easy to reference specific records in logs

## Timestamp Extraction

You can extract the creation timestamp from any serial:

```python
from src.utils.serial import SerialGenerator
from datetime import datetime

serial = "AP01LGF5A2VR43G6AR"
timestamp = SerialGenerator.parse_serial_timestamp(serial)
print(timestamp)  # datetime object
```

## Migration

### For Existing Databases

Run the migration script to add serials to existing records:

```bash
python3 migrate_gps_fields.py
# Choose option 1 or 3
```

This will:
1. Add `serial` column to tables missing it
2. Generate unique serials for all existing records
3. Create indexes for performance

### For New Installations

Serials are created automatically for all new records.

## Verification

Verify all records have proper serials:

```bash
python3 verify_serials.py
```

This checks:
- All records have serials
- All serials are unique
- No duplicate serials exist
- Shows sample serials from each table

## Save Pipeline

The serialization is integrated into the save pipeline:

1. **WiFi Scanner** → Creates `CurrentScanNetwork` and `CurrentScanClient` (auto-serial)
2. **Scan Database Service** → Upserts to `Network` and `Client` (auto-serial)
3. **Triangulation Service** → Creates `NetworkObservation` (auto-serial)

All records are guaranteed to have unique serials at creation time.

## Best Practices

1. **Never modify serials** - They are immutable identifiers
2. **Use serials for logging** - More readable than integer IDs
3. **Index serial columns** - Already indexed in models
4. **Export with serials** - Include in CSV/JSON exports for tracking
5. **Use in API responses** - Better than exposing internal IDs

## Example Usage

### Logging
```python
print(f"[AP] Discovered: {network.serial} ({network.ssid})")
# [AP] Discovered: AP01LGF5A2VR43G6AR (MyNetwork)
```

### API Export
```python
{
    "serial": "OBS01LGF5A2VVZLDKK4J",
    "network_serial": "AP01LGF5A2VR43G6AR",
    "timestamp": "2025-01-15T12:34:56Z",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "signal_strength": -65
}
```

### Database Query
```python
# Find observation by serial
obs = session.query(NetworkObservation).filter_by(
    serial="OBS01LGF5A2VVZLDKK4J"
).first()
```

## Summary

✅ **All records have unique serial numbers**
✅ **Automatic generation on creation**
✅ **Timestamp embedded in serial**
✅ **Human-readable format**
✅ **Robust save pipeline integration**

The serialization system ensures every event and record in Gattrose-NG can be uniquely identified, tracked, and audited throughout its lifecycle.
