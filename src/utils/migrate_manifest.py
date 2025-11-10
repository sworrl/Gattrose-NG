#!/usr/bin/env python3
"""
Migrate FILE_MANIFEST.yaml from v1 to v2

Changes:
- Rename 'serial' to 'index' (fixed, never changes)
- Add 'serial' as 32-char random alphanumeric (changes with version)
- Update index ranges for large project growth
"""

import yaml
import random
import string
from pathlib import Path


def generate_serial(length=32):
    """Generate random alphanumeric serial"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))


def migrate_manifest():
    """Migrate manifest from v1 to v2"""
    manifest_path = Path(__file__).parent.parent.parent / "docs" / "FILE_MANIFEST.yaml"

    with open(manifest_path, 'r') as f:
        manifest = yaml.safe_load(f)

    # Index mapping (old FILE-XXXXX to new XXXXXXX)
    index_mapping = {
        # Root files (0000000-0000099)
        "FILE-00001": "0000001",
        "FILE-00002": "0000002",
        "FILE-00003": "0000003",

        # Core source (0000100-0000999)
        "FILE-00010": "0000100",
        "FILE-00011": "0000101",

        # Database (0001000-0001999)
        "FILE-00020": "0001000",

        # GUI (0002000-0002999)
        "FILE-00030": "0002000",
        "FILE-00031": "0002001",

        # Tools (0003000-0003999)
        "FILE-00040": "0003000",
        "FILE-00041": "0003001",

        # Utils (0004000-0004999)
        "FILE-00050": "0004000",
        "FILE-00051": "0004001",
        "FILE-00052": "0004002",
        "FILE-00053": "0004003",
        "FILE-00054": "0004004",

        # Services (0005000-0005999)
        "FILE-00060": "0005000",
        "FILE-00061": "0005001",
        "FILE-00062": "0005002",

        # Scripts (0006000-0006999)
        "FILE-00070": "0006000",
        "FILE-00071": "0006001",
        "FILE-00072": "0006002",

        # Systemd (0007000-0007999)
        "FILE-00080": "0007000",
        "FILE-00081": "0007001",
        "FILE-00082": "0007002",
        "FILE-00083": "0007003",
        "FILE-00084": "0007004",

        # Documentation (0008000-0008999)
        "FILE-00090": "0008000",
        "FILE-00091": "0008001",
        "FILE-00092": "0008002",
        "FILE-00093": "0008003",
    }

    # Migrate files
    new_files = {}
    for file_path, info in manifest.get('files', {}).items():
        old_serial = info.get('serial', '')

        # Get new index
        new_index = index_mapping.get(old_serial, old_serial)

        # Generate random serial
        random_serial = generate_serial(32)

        new_files[file_path] = {
            'index': new_index,
            'serial': random_serial,
            'version': info.get('version', '1.0.0'),
            'last_modified': info.get('last_modified', '2025-11-01'),
            'description': info.get('description', '')
        }

    manifest['files'] = new_files

    # Update next indexes
    manifest['next_indexes'] = {
        'root': '0000004',
        'core': '0000102',
        'database': '0001001',
        'gui': '0002002',
        'tools': '0003002',
        'utils': '0004005',
        'services': '0005003',
        'scripts': '0006003',
        'systemd': '0007005',
        'documentation': '0008004',
        'tests': '0009000',
        'future': '0010000'
    }

    # Save migrated manifest
    with open(manifest_path, 'w') as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"[✓] Migrated manifest to v2.0.0")
    print(f"[✓] Converted {len(new_files)} files")
    print(f"[✓] Generated 32-char serials for all files")


if __name__ == "__main__":
    migrate_manifest()
