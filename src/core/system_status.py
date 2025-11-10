"""
System component status checker
Verifies all required tools and dependencies
"""

import subprocess
import sys
import os
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ComponentStatus:
    """Status of a system component"""
    name: str
    required: bool
    installed: bool
    version: Optional[str]
    path: Optional[str]
    status_message: str


class SystemStatusChecker:
    """Check status of all required system components"""

    @staticmethod
    def check_command(command: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if a command is available

        Returns:
            (installed: bool, path: str, version: str)
        """
        # Check if command exists
        try:
            result = subprocess.run(
                ['which', command],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                path = result.stdout.strip()

                # Try to get version
                version = None
                try:
                    # Try common version flags
                    for flag in ['--version', '-v', '-V', 'version']:
                        try:
                            ver_result = subprocess.run(
                                [command, flag],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            if ver_result.returncode == 0:
                                # Get first line of version output
                                version = ver_result.stdout.split('\n')[0].strip()
                                if version:
                                    break
                        except:
                            continue
                except:
                    pass

                return (True, path, version)
            else:
                return (False, None, None)

        except Exception as e:
            return (False, None, None)

    @staticmethod
    def check_python_module(module_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a Python module is available

        Returns:
            (installed: bool, version: str)
        """
        try:
            mod = __import__(module_name)
            version = getattr(mod, '__version__', 'Unknown')
            return (True, version)
        except ImportError:
            return (False, None)

    @staticmethod
    def get_all_component_status() -> Dict[str, ComponentStatus]:
        """Get status of all system components"""
        components = {}

        # Core WiFi Tools (ALL REQUIRED)
        wifi_tools = [
            ('airmon-ng', True),
            ('airodump-ng', True),
            ('aircrack-ng', True),
            ('aireplay-ng', True),
            ('iw', True),
            ('iwconfig', False),  # Optional (iw is preferred)
            ('rfkill', True),
        ]

        for tool, required in wifi_tools:
            installed, path, version = SystemStatusChecker.check_command(tool)

            if installed:
                status_msg = f"✓ Installed at {path}"
            else:
                if required:
                    status_msg = "✗ MISSING - REQUIRED!"
                else:
                    status_msg = "✗ Not installed (optional)"

            components[tool] = ComponentStatus(
                name=tool,
                required=required,
                installed=installed,
                version=version,
                path=path,
                status_message=status_msg
            )

        # Bluetooth Tools
        bt_tools = [
            ('hcitool', True),
            ('bluetoothctl', True),
            ('hciconfig', True),
        ]

        for tool, required in bt_tools:
            installed, path, version = SystemStatusChecker.check_command(tool)

            if installed:
                status_msg = f"✓ Installed at {path}"
            else:
                if required:
                    status_msg = "✗ MISSING - REQUIRED!"
                else:
                    status_msg = "✗ Not installed (optional)"

            components[tool] = ComponentStatus(
                name=tool,
                required=required,
                installed=installed,
                version=version,
                path=path,
                status_message=status_msg
            )

        # SDR Tools
        sdr_tools = [
            ('rtl_test', True),
            ('rtl_sdr', True),
            ('hackrf_info', False),
        ]

        for tool, required in sdr_tools:
            installed, path, version = SystemStatusChecker.check_command(tool)

            if installed:
                status_msg = f"✓ Installed at {path}"
            else:
                if required:
                    status_msg = "✗ MISSING - REQUIRED!"
                else:
                    status_msg = "✗ Not installed (optional)"

            components[tool] = ComponentStatus(
                name=tool,
                required=required,
                installed=installed,
                version=version,
                path=path,
                status_message=status_msg
            )

        # Python environment
        components['python'] = ComponentStatus(
            name='python',
            required=True,
            installed=True,
            version=sys.version.split()[0],
            path=sys.executable,
            status_message=f"✓ Python {sys.version.split()[0]} at {sys.executable}"
        )

        # Python modules
        python_modules = [
            'PyQt6',
            'sqlalchemy',
            'scapy',
        ]

        for module in python_modules:
            installed, version = SystemStatusChecker.check_python_module(module)

            if installed:
                status_msg = f"✓ Installed (version {version})"
            else:
                status_msg = "✗ MISSING - REQUIRED!"

            components[f'python-{module}'] = ComponentStatus(
                name=f'python-{module}',
                required=True,
                installed=installed,
                version=version,
                path=None,
                status_message=status_msg
            )

        # Database
        from ..database.manager import DatabaseManager
        db_path = "/home/eurrl/Documents/Code & Scripts/gattrose-ng/data/gattrose-ng.db"
        db_exists = os.path.exists(db_path)

        components['database'] = ComponentStatus(
            name='database',
            required=True,
            installed=db_exists,
            version='SQLite',
            path=db_path,
            status_message=f"✓ Database at {db_path}" if db_exists else "✗ Database not initialized"
        )

        return components

    @staticmethod
    def get_summary() -> Dict[str, any]:
        """Get summary of system status"""
        components = SystemStatusChecker.get_all_component_status()

        total = len(components)
        installed = sum(1 for c in components.values() if c.installed)
        required = sum(1 for c in components.values() if c.required)
        required_installed = sum(1 for c in components.values() if c.required and c.installed)

        all_required_ok = required_installed == required

        return {
            'total_components': total,
            'installed': installed,
            'required': required,
            'required_installed': required_installed,
            'all_required_ok': all_required_ok,
            'components': components
        }

    @staticmethod
    def print_status():
        """Print component status to console"""
        summary = SystemStatusChecker.get_summary()

        print("\n" + "="*70)
        print("GATTROSE-NG SYSTEM STATUS")
        print("="*70)

        print(f"\nRequired Components: {summary['required_installed']}/{summary['required']}")
        print(f"Total Components: {summary['installed']}/{summary['total_components']}")
        print(f"System Ready: {'✓ YES' if summary['all_required_ok'] else '✗ NO'}")

        print("\n" + "-"*70)
        print("COMPONENT DETAILS")
        print("-"*70)

        # Group by category
        wifi_components = {k: v for k, v in summary['components'].items()
                          if k in ['airmon-ng', 'airodump-ng', 'aircrack-ng', 'aireplay-ng', 'iw', 'iwconfig', 'rfkill']}
        bt_components = {k: v for k, v in summary['components'].items()
                        if k in ['hcitool', 'bluetoothctl', 'hciconfig']}
        sdr_components = {k: v for k, v in summary['components'].items()
                         if k in ['rtl_test', 'rtl_sdr', 'hackrf_info']}
        python_components = {k: v for k, v in summary['components'].items()
                           if k.startswith('python')}
        other_components = {k: v for k, v in summary['components'].items()
                          if k not in list(wifi_components.keys()) + list(bt_components.keys()) +
                             list(sdr_components.keys()) + list(python_components.keys())}

        print("\nWiFi Tools:")
        for name, comp in wifi_components.items():
            req = "[REQUIRED]" if comp.required else "[OPTIONAL]"
            print(f"  {req:12} {comp.name:20} {comp.status_message}")
            if comp.version:
                print(f"               {'':20} Version: {comp.version}")

        print("\nBluetooth Tools:")
        for name, comp in bt_components.items():
            req = "[REQUIRED]" if comp.required else "[OPTIONAL]"
            print(f"  {req:12} {comp.name:20} {comp.status_message}")
            if comp.version:
                print(f"               {'':20} Version: {comp.version}")

        print("\nSDR Tools:")
        for name, comp in sdr_components.items():
            req = "[REQUIRED]" if comp.required else "[OPTIONAL]"
            print(f"  {req:12} {comp.name:20} {comp.status_message}")
            if comp.version:
                print(f"               {'':20} Version: {comp.version}")

        print("\nPython Environment:")
        for name, comp in python_components.items():
            req = "[REQUIRED]" if comp.required else "[OPTIONAL]"
            print(f"  {req:12} {comp.name:20} {comp.status_message}")

        print("\nOther Components:")
        for name, comp in other_components.items():
            req = "[REQUIRED]" if comp.required else "[OPTIONAL]"
            print(f"  {req:12} {comp.name:20} {comp.status_message}")
            if comp.version:
                print(f"               {'':20} Version: {comp.version}")

        print("\n" + "="*70)

        if not summary['all_required_ok']:
            print("\n⚠️  WARNING: Some required components are missing!")
            print("Please install missing components before running Gattrose-NG.\n")
        else:
            print("\n✓ All required components are installed!\n")
