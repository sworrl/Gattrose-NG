"""
OUI Database Downloader and Manager

Downloads MAC vendor databases from IEEE and Wireshark
Populates local database for fast offline lookups
"""

import requests
import re
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class OUIDownloader:
    """Download and parse OUI databases from multiple sources"""

    # Data sources
    IEEE_OUI_URL = "https://standards-oui.ieee.org/oui/oui.txt"
    IEEE_IAB_URL = "https://standards-oui.ieee.org/iab/iab.txt"
    WIRESHARK_OUI_URL = "https://gitlab.com/wireshark/wireshark/-/raw/HEAD/manuf"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Gattrose-NG OUI Updater/2.2'
        })

    def download_file(self, url: str, timeout: int = 30) -> Tuple[bool, Optional[bytes], str]:
        """
        Download file from URL

        Returns:
            (success, content, error_message)
        """
        try:
            print(f"[*] Downloading from {url}")
            response = self.session.get(url, timeout=timeout)

            if response.status_code == 200:
                print(f"[+] Downloaded {len(response.content)} bytes")
                return True, response.content, ""
            else:
                error = f"HTTP {response.status_code}"
                print(f"[!] Download failed: {error}")
                return False, None, error

        except Exception as e:
            error = str(e)
            print(f"[!] Download error: {error}")
            return False, None, error

    def compute_hash(self, data: bytes) -> str:
        """Compute SHA256 hash of data"""
        return hashlib.sha256(data).hexdigest()

    def parse_ieee_oui(self, content: bytes) -> List[Dict]:
        """
        Parse IEEE OUI format

        Example format:
        00-00-00   (hex)        XEROX CORPORATION
        000000     (base 16)    XEROX CORPORATION
                                M/S 105-50C
                                WEBSTER NY 14580
                                UNITED STATES
        """
        records = []
        text = content.decode('utf-8', errors='ignore')
        lines = text.split('\n')

        current_mac = None
        current_vendor = None
        current_address = []

        for line in lines:
            line = line.strip()

            # Match MAC prefix line (hex format)
            hex_match = re.match(r'^([0-9A-Fa-f]{2}-[0-9A-Fa-f]{2}-[0-9A-Fa-f]{2})\s+\(hex\)\s+(.+)$', line)
            if hex_match:
                # Save previous record
                if current_mac and current_vendor:
                    records.append({
                        'mac_prefix': current_mac,
                        'prefix_length': 24,
                        'vendor_name': current_vendor,
                        'vendor_name_short': current_vendor[:100] if len(current_vendor) > 100 else current_vendor,
                        'address': '\n'.join(current_address) if current_address else None,
                        'country': self._extract_country(current_address),
                        'source': 'ieee',
                        'source_url': self.IEEE_OUI_URL
                    })

                # Start new record
                current_mac = hex_match.group(1).replace('-', ':')
                current_vendor = hex_match.group(2).strip()
                current_address = []
                continue

            # Base 16 line (skip)
            if '(base 16)' in line:
                continue

            # Address lines (non-empty, not a new MAC)
            if line and current_mac and not hex_match:
                current_address.append(line)

        # Save last record
        if current_mac and current_vendor:
            records.append({
                'mac_prefix': current_mac,
                'prefix_length': 24,
                'vendor_name': current_vendor,
                'vendor_name_short': current_vendor[:100] if len(current_vendor) > 100 else current_vendor,
                'address': '\n'.join(current_address) if current_address else None,
                'country': self._extract_country(current_address),
                'source': 'ieee',
                'source_url': self.IEEE_OUI_URL
            })

        print(f"[+] Parsed {len(records)} IEEE OUI records")
        return records

    def parse_wireshark_manuf(self, content: bytes) -> List[Dict]:
        """
        Parse Wireshark manuf format

        Example format:
        00:00:00    Xerox       Xerox Corporation
        00:00:01    Xerox       Xerox Corporation
        """
        records = []
        text = content.decode('utf-8', errors='ignore')
        lines = text.split('\n')

        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Match MAC prefix and vendor
            # Format: MAC_PREFIX\tSHORT_NAME\tFULL_NAME
            # or:     MAC_PREFIX\tVENDOR_NAME
            parts = re.split(r'\s+', line, maxsplit=2)

            if len(parts) < 2:
                continue

            mac_prefix = parts[0].strip()

            # Normalize MAC format (handle /XX suffix for prefix length)
            prefix_match = re.match(r'^([0-9A-Fa-f:]{8,17})(/(\d+))?$', mac_prefix)
            if not prefix_match:
                continue

            mac = prefix_match.group(1).upper()
            prefix_bits = int(prefix_match.group(3)) if prefix_match.group(3) else 24

            # Determine prefix length in octets
            if ':' in mac:
                octets = mac.count(':') + 1
                prefix_length = octets * 8
            else:
                prefix_length = prefix_bits

            # Get vendor names
            vendor_short = parts[1].strip() if len(parts) > 1 else ""
            vendor_full = parts[2].strip() if len(parts) > 2 else vendor_short

            records.append({
                'mac_prefix': mac,
                'prefix_length': prefix_length,
                'vendor_name': vendor_full,
                'vendor_name_short': vendor_short,
                'address': None,
                'country': None,
                'source': 'wireshark',
                'source_url': self.WIRESHARK_OUI_URL
            })

        print(f"[+] Parsed {len(records)} Wireshark records")
        return records

    def _extract_country(self, address_lines: List[str]) -> Optional[str]:
        """Extract country from address lines (usually last non-empty line)"""
        if not address_lines:
            return None

        # Last non-empty line is usually the country
        for line in reversed(address_lines):
            if line.strip():
                # Remove postal codes
                line = re.sub(r'\b\d{5,6}\b', '', line)
                line = line.strip()
                if len(line) > 2:  # Valid country name
                    return line

        return None

    def update_database(self, source: str = 'all') -> Dict:
        """
        Update OUI database from sources

        Args:
            source: 'ieee', 'wireshark', or 'all'

        Returns:
            dict with update statistics
        """
        from ..database.models import get_session, OUIDatabase, OUIUpdate

        start_time = time.time()
        stats = {
            'success': False,
            'records_added': 0,
            'records_updated': 0,
            'records_total': 0,
            'sources': []
        }

        # Download and parse sources
        all_records = []

        if source in ['ieee', 'all']:
            print("\n[*] Downloading IEEE OUI database...")
            success, content, error = self.download_file(self.IEEE_OUI_URL)
            if success:
                records = self.parse_ieee_oui(content)
                all_records.extend(records)
                stats['sources'].append('ieee')
            else:
                print(f"[!] IEEE download failed: {error}")

        if source in ['wireshark', 'all']:
            print("\n[*] Downloading Wireshark OUI database...")
            success, content, error = self.download_file(self.WIRESHARK_OUI_URL)
            if success:
                records = self.parse_wireshark_manuf(content)
                all_records.extend(records)
                stats['sources'].append('wireshark')
            else:
                print(f"[!] Wireshark download failed: {error}")

        if not all_records:
            print("[!] No records downloaded")
            return stats

        print(f"\n[*] Updating database with {len(all_records)} records...")

        # Update database
        session = get_session()
        try:
            for record in all_records:
                # Check if exists
                existing = session.query(OUIDatabase).filter_by(
                    mac_prefix=record['mac_prefix']
                ).first()

                if existing:
                    # Update existing record
                    existing.vendor_name = record['vendor_name']
                    existing.vendor_name_short = record['vendor_name_short']
                    existing.address = record['address']
                    existing.country = record['country']
                    existing.source = record['source']
                    existing.updated_at = datetime.utcnow()
                    stats['records_updated'] += 1
                else:
                    # Create new record
                    new_oui = OUIDatabase(
                        mac_prefix=record['mac_prefix'],
                        prefix_length=record['prefix_length'],
                        vendor_name=record['vendor_name'],
                        vendor_name_short=record['vendor_name_short'],
                        address=record['address'],
                        country=record['country'],
                        source=record['source'],
                        source_url=record['source_url']
                    )
                    session.add(new_oui)
                    stats['records_added'] += 1

                # Commit in batches
                if (stats['records_added'] + stats['records_updated']) % 1000 == 0:
                    session.commit()
                    print(f"[*] Progress: {stats['records_added'] + stats['records_updated']}/{len(all_records)} records")

            # Final commit
            session.commit()

            # Get total count
            stats['records_total'] = session.query(OUIDatabase).count()

            # Record update in history
            duration = time.time() - start_time
            update_record = OUIUpdate(
                source=source,
                records_added=stats['records_added'],
                records_updated=stats['records_updated'],
                records_total=stats['records_total'],
                status='success',
                duration_seconds=duration
            )
            session.add(update_record)
            session.commit()

            stats['success'] = True
            print(f"\n[✓] Database updated successfully")
            print(f"    Added: {stats['records_added']}")
            print(f"    Updated: {stats['records_updated']}")
            print(f"    Total: {stats['records_total']}")
            print(f"    Duration: {duration:.2f}s")

        except Exception as e:
            session.rollback()
            print(f"[!] Database update failed: {e}")
            import traceback
            traceback.print_exc()

            # Record failure
            update_record = OUIUpdate(
                source=source,
                status='failed',
                error_message=str(e)
            )
            session.add(update_record)
            session.commit()

        finally:
            session.close()

        return stats

    def lookup_vendor(self, mac_address: str) -> Optional[str]:
        """
        Lookup vendor by MAC address

        Args:
            mac_address: MAC address (any format)

        Returns:
            Vendor name or None
        """
        from ..database.models import get_session, OUIDatabase

        # Normalize MAC address
        mac = mac_address.upper().replace('-', ':')

        # Extract prefix (first 3 octets for OUI)
        parts = mac.split(':')
        if len(parts) < 3:
            return None

        prefix = ':'.join(parts[:3])

        # Lookup in database
        session = get_session()
        try:
            oui = session.query(OUIDatabase).filter_by(mac_prefix=prefix).first()
            if oui:
                return oui.vendor_name
            return None
        finally:
            session.close()

    def get_last_update_time(self) -> Optional[datetime]:
        """Get time of last successful OUI update"""
        from ..database.models import get_session, OUIUpdate

        session = get_session()
        try:
            last_update = session.query(OUIUpdate).filter_by(
                status='success'
            ).order_by(OUIUpdate.update_time.desc()).first()

            if last_update:
                return last_update.update_time
            return None
        finally:
            session.close()

    def get_database_stats(self) -> Dict:
        """Get OUI database statistics"""
        from ..database.models import get_session, OUIDatabase, OUIUpdate

        session = get_session()
        try:
            total_records = session.query(OUIDatabase).count()
            ieee_records = session.query(OUIDatabase).filter_by(source='ieee').count()
            wireshark_records = session.query(OUIDatabase).filter_by(source='wireshark').count()

            last_update = self.get_last_update_time()

            return {
                'total_records': total_records,
                'ieee_records': ieee_records,
                'wireshark_records': wireshark_records,
                'last_update': last_update
            }
        finally:
            session.close()


def update_oui_database_cli():
    """CLI entry point for updating OUI database"""
    import sys

    print("="*60)
    print("  Gattrose-NG OUI Database Updater")
    print("="*60)
    print()

    downloader = OUIDownloader()

    # Check if update is needed
    last_update = downloader.get_last_update_time()
    if last_update:
        print(f"[*] Last update: {last_update}")
        age_days = (datetime.utcnow() - last_update).days
        print(f"[*] Database age: {age_days} days")

        if age_days < 30:
            response = input("\n[?] Database is less than 30 days old. Update anyway? [y/N]: ")
            if response.lower() != 'y':
                print("[*] Update cancelled")
                sys.exit(0)

    # Perform update
    source = sys.argv[1] if len(sys.argv) > 1 else 'all'
    stats = downloader.update_database(source=source)

    if stats['success']:
        print("\n[✓] OUI database update completed successfully")
        sys.exit(0)
    else:
        print("\n[!] OUI database update failed")
        sys.exit(1)


if __name__ == "__main__":
    update_oui_database_cli()
