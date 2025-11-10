#!/usr/bin/env python3
"""
File Manifest Manager

Manages file serial numbers and versions for the entire codebase
Tracks every file's version independently from app version

File Serial: FILE-00053
File Version: 1.0.0
Last Modified: 2025-11-01
"""

import os
import sys
import yaml
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple


class FileManifestManager:
    """Manages file manifest with serial tracking"""

    def __init__(self, manifest_path: Optional[Path] = None):
        if manifest_path is None:
            self.manifest_path = Path(__file__).parent.parent.parent / "docs" / "FILE_MANIFEST.yaml"
        else:
            self.manifest_path = Path(manifest_path)

        self.manifest = self.load_manifest()

    def load_manifest(self) -> Dict:
        """Load manifest from YAML file"""
        if not self.manifest_path.exists():
            print(f"[!] Manifest not found: {self.manifest_path}")
            return {}

        with open(self.manifest_path, 'r') as f:
            return yaml.safe_load(f)

    def save_manifest(self):
        """Save manifest to YAML file"""
        with open(self.manifest_path, 'w') as f:
            yaml.dump(self.manifest, f, default_flow_style=False, sort_keys=False)

    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """Get file information from manifest"""
        return self.manifest.get('files', {}).get(file_path)

    def get_next_serial(self) -> str:
        """Get next available serial number"""
        next_serial = self.manifest.get('next_serial', 'FILE-00100')

        # Increment
        match = re.match(r'FILE-(\d+)', next_serial)
        if match:
            num = int(match.group(1)) + 1
            new_serial = f"FILE-{num:05d}"
            self.manifest['next_serial'] = new_serial
            return next_serial

        return next_serial

    def add_file(self, file_path: str, version: str = "1.0.0", description: str = ""):
        """Add new file to manifest"""
        if file_path in self.manifest.get('files', {}):
            print(f"[!] File already in manifest: {file_path}")
            return False

        serial = self.get_next_serial()

        if 'files' not in self.manifest:
            self.manifest['files'] = {}

        self.manifest['files'][file_path] = {
            'serial': serial,
            'version': version,
            'last_modified': datetime.utcnow().strftime('%Y-%m-%d'),
            'description': description
        }

        self.save_manifest()
        print(f"[✓] Added {file_path} with serial {serial}")
        return True

    def update_file_version(self, file_path: str, new_version: str):
        """Update file version in manifest"""
        if file_path not in self.manifest.get('files', {}):
            print(f"[!] File not in manifest: {file_path}")
            return False

        self.manifest['files'][file_path]['version'] = new_version
        self.manifest['files'][file_path]['last_modified'] = datetime.utcnow().strftime('%Y-%m-%d')

        self.save_manifest()
        print(f"[✓] Updated {file_path} to version {new_version}")
        return True

    def generate_file_header(self, file_path: str, file_type: str = "python") -> str:
        """
        Generate file header with serial and version

        Args:
            file_path: Path to file in manifest
            file_type: "python", "bash", or "markdown"

        Returns:
            Header string
        """
        info = self.get_file_info(file_path)
        if not info:
            return ""

        if file_type == "python":
            return f'''"""
{info.get('description', 'Gattrose-NG Component')}

File Serial: {info['serial']}
File Version: {info['version']}
Last Modified: {info['last_modified']}
"""
'''
        elif file_type == "bash":
            return f'''#!/bin/bash
#
# {info.get('description', 'Gattrose-NG Script')}
#
# File Serial: {info['serial']}
# File Version: {info['version']}
# Last Modified: {info['last_modified']}
#
'''
        elif file_type == "markdown":
            return f'''<!--
File Serial: {info['serial']}
File Version: {info['version']}
Last Modified: {info['last_modified']}
-->

# {info.get('description', 'Documentation')}
'''
        return ""

    def extract_file_header_info(self, file_path: Path) -> Optional[Tuple[str, str]]:
        """
        Extract serial and version from existing file header

        Returns:
            (serial, version) or None
        """
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r') as f:
                content = f.read(500)  # Read first 500 chars

            # Look for Serial
            serial_match = re.search(r'File Serial:\s*([A-Z]+-\d+)', content)
            version_match = re.search(r'File Version:\s*(\d+\.\d+\.\d+)', content)

            if serial_match and version_match:
                return serial_match.group(1), version_match.group(1)

        except:
            pass

        return None

    def scan_codebase(self, root_dir: Optional[Path] = None):
        """
        Scan codebase and suggest files to add to manifest

        Args:
            root_dir: Root directory to scan (defaults to project root)
        """
        if root_dir is None:
            root_dir = Path(__file__).parent.parent.parent

        print(f"[*] Scanning codebase: {root_dir}")
        print()

        # Patterns to include
        include_patterns = [
            "src/**/*.py",
            "bin/**/*.sh",
            "services/**/*.service",
            "services/**/*.timer",
            "docs/**/*.md",
            "*.py",
            "*.sh",
            "*.desktop"
        ]

        # Patterns to exclude
        exclude_patterns = [
            "__pycache__",
            ".venv",
            "*.pyc",
            ".git"
        ]

        found_files = set()

        for pattern in include_patterns:
            for file_path in root_dir.glob(pattern):
                # Check if should exclude
                should_exclude = False
                for exclude in exclude_patterns:
                    if exclude in str(file_path):
                        should_exclude = True
                        break

                if not should_exclude and file_path.is_file():
                    rel_path = str(file_path.relative_to(root_dir))
                    found_files.add(rel_path)

        # Check which files are missing from manifest
        manifest_files = set(self.manifest.get('files', {}).keys())
        missing_files = found_files - manifest_files

        if missing_files:
            print(f"[*] Found {len(missing_files)} file(s) not in manifest:")
            for file_path in sorted(missing_files):
                print(f"    - {file_path}")
            print()
            print("[*] Add these files with: python -m src.utils.file_manifest --add <file_path>")
        else:
            print(f"[✓] All {len(found_files)} files are tracked in manifest")

        # Check for orphaned manifest entries
        orphaned = manifest_files - found_files
        if orphaned:
            print(f"\n[!] Found {len(orphaned)} orphaned manifest entry/entries:")
            for file_path in sorted(orphaned):
                if (root_dir / file_path).exists():
                    continue  # File exists, just didn't match patterns
                print(f"    - {file_path} (file not found)")

    def generate_manifest_report(self) -> str:
        """Generate markdown report of all tracked files"""
        report = "# Gattrose-NG File Manifest Report\n\n"
        report += f"**App Version:** {self.manifest.get('app_version', 'Unknown')}\n"
        report += f"**Manifest Version:** {self.manifest.get('manifest_version', 'Unknown')}\n"
        report += f"**Last Updated:** {self.manifest.get('last_updated', 'Unknown')}\n"
        report += f"**Total Files:** {len(self.manifest.get('files', {}))}\n\n"

        # Group by category
        categories = {
            'Root Files': [],
            'Core Source': [],
            'Database': [],
            'GUI': [],
            'Tools': [],
            'Utils': [],
            'Services': [],
            'Scripts': [],
            'Systemd': [],
            'Documentation': []
        }

        for file_path, info in self.manifest.get('files', {}).items():
            if file_path.startswith('src/services/'):
                categories['Services'].append((file_path, info))
            elif file_path.startswith('src/database/'):
                categories['Database'].append((file_path, info))
            elif file_path.startswith('src/gui/'):
                categories['GUI'].append((file_path, info))
            elif file_path.startswith('src/tools/'):
                categories['Tools'].append((file_path, info))
            elif file_path.startswith('src/utils/'):
                categories['Utils'].append((file_path, info))
            elif file_path.startswith('src/'):
                categories['Core Source'].append((file_path, info))
            elif file_path.startswith('bin/'):
                categories['Scripts'].append((file_path, info))
            elif file_path.startswith('services/'):
                categories['Systemd'].append((file_path, info))
            elif file_path.startswith('docs/'):
                categories['Documentation'].append((file_path, info))
            else:
                categories['Root Files'].append((file_path, info))

        for category, files in categories.items():
            if not files:
                continue

            report += f"## {category}\n\n"
            report += "| File | Serial | Version | Last Modified | Description |\n"
            report += "|------|--------|---------|---------------|-------------|\n"

            for file_path, info in sorted(files):
                report += f"| `{file_path}` | {info['serial']} | {info['version']} | {info['last_modified']} | {info.get('description', '')} |\n"

            report += "\n"

        return report


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Gattrose-NG File Manifest Manager")
    parser.add_argument('--scan', action='store_true', help='Scan codebase for untracked files')
    parser.add_argument('--add', metavar='FILE', help='Add file to manifest')
    parser.add_argument('--update', metavar='FILE:VERSION', help='Update file version (format: path:version)')
    parser.add_argument('--report', action='store_true', help='Generate manifest report')
    parser.add_argument('--header', metavar='FILE:TYPE', help='Generate header for file (format: path:type)')

    args = parser.parse_args()

    manager = FileManifestManager()

    if args.scan:
        manager.scan_codebase()

    elif args.add:
        version = input("Version [1.0.0]: ").strip() or "1.0.0"
        description = input("Description: ").strip()
        manager.add_file(args.add, version=version, description=description)

    elif args.update:
        if ':' not in args.update:
            print("[!] Format: path:version")
            sys.exit(1)
        file_path, version = args.update.split(':', 1)
        manager.update_file_version(file_path, version)

    elif args.report:
        report = manager.generate_manifest_report()
        print(report)

        # Save to file
        report_path = Path(__file__).parent.parent.parent / "docs" / "FILE_MANIFEST_REPORT.md"
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"\n[✓] Report saved to: {report_path}")

    elif args.header:
        if ':' not in args.header:
            print("[!] Format: path:type (e.g., src/main.py:python)")
            sys.exit(1)
        file_path, file_type = args.header.split(':', 1)
        header = manager.generate_file_header(file_path, file_type)
        print(header)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
