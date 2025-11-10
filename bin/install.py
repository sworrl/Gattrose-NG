#!/usr/bin/env python3
"""
Gattrose System Installation Script
Installs Gattrose to system with desktop integration
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def check_root():
    """Check if running with appropriate privileges"""
    if os.geteuid() != 0:
        print("[!] This script should be run with sudo for system-wide installation")
        print("[*] For user installation, it will request sudo for specific operations")


def get_install_paths(system_wide: bool = False):
    """Get installation paths"""
    if system_wide:
        return {
            'install_dir': Path('/opt/gattrose-ng'),
            'bin_dir': Path('/usr/local/bin'),
            'desktop_dir': Path('/usr/share/applications'),
            'data_dir': Path('/var/lib/gattrose-ng'),
            'config_dir': Path('/etc/gattrose-ng'),
        }
    else:
        home = Path.home()
        return {
            'install_dir': home / '.local' / 'share' / 'gattrose-ng',
            'bin_dir': home / '.local' / 'bin',
            'desktop_dir': home / '.local' / 'share' / 'applications',
            'data_dir': home / '.local' / 'share' / 'gattrose-ng' / 'data',
            'config_dir': home / '.config' / 'gattrose-ng',
        }


def install_gattrose(system_wide: bool = False):
    """Install Gattrose to system"""
    print("\n" + "="*60)
    print("  Gattrose Installation")
    print("  Mode:", "System-wide" if system_wide else "User")
    print("="*60 + "\n")

    project_root = Path(__file__).parent.resolve()
    paths = get_install_paths(system_wide)

    # Create directories
    print("[*] Creating directories...")
    for path_name, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        print(f"    {path_name}: {path}")

    # Copy application files
    print("\n[*] Copying application files...")

    # Copy source directory
    src_dest = paths['install_dir'] / 'src'
    if src_dest.exists():
        shutil.rmtree(src_dest)
    shutil.copytree(project_root / 'src', src_dest)
    print(f"    Source code -> {src_dest}")

    # Copy launcher
    shutil.copy2(project_root / 'gattrose-ng.py', paths['install_dir'] / 'gattrose-ng.py')
    print(f"    Launcher -> {paths['install_dir'] / 'gattrose-ng.py'}")

    # Copy requirements
    shutil.copy2(project_root / 'docs' / 'requirements.txt', paths['install_dir'] / 'docs' / 'requirements.txt')
    print(f"    Requirements -> {paths['install_dir'] / 'docs' / 'requirements.txt'}")

    # Copy README
    shutil.copy2(project_root / 'README.md', paths['install_dir'] / 'README.md')
    print(f"    README -> {paths['install_dir'] / 'README.md'}")

    # Copy icons
    if (project_root / 'gattrose-ng.png').exists():
        shutil.copy2(project_root / 'gattrose-ng.png', paths['install_dir'] / 'gattrose-ng.png')
        print(f"    Icon (PNG) -> {paths['install_dir'] / 'gattrose-ng.png'}")
    if (project_root / 'gattrose-ng.svg').exists():
        shutil.copy2(project_root / 'gattrose-ng.svg', paths['install_dir'] / 'gattrose-ng.svg')
        print(f"    Icon (SVG) -> {paths['install_dir'] / 'gattrose-ng.svg'}")

    # Create installed marker
    (paths['install_dir'] / '.installed').touch()
    print(f"    Created .installed marker")

    # Create launcher script
    print("\n[*] Creating launcher script...")
    launcher_script = paths['bin_dir'] / 'gattrose-ng'

    with open(launcher_script, 'w') as f:
        f.write(f"""#!/bin/bash
# Gattrose-NG launcher script

cd "{paths['install_dir']}"
python3 gattrose-ng.py "$@"
""")

    launcher_script.chmod(0o755)
    print(f"    Launcher script -> {launcher_script}")

    # Create desktop entry
    print("\n[*] Creating desktop entry...")
    desktop_file = paths['desktop_dir'] / 'gattrose-ng.desktop'
    icon_path = paths['install_dir'] / 'gattrose-ng.png'

    with open(desktop_file, 'w') as f:
        f.write(f"""[Desktop Entry]
Type=Application
Name=Gattrose-NG
GenericName=Wireless Penetration Testing Suite
Comment=Advanced wireless security auditing and penetration testing framework
Exec={launcher_script}
Icon={icon_path}
Path={paths['install_dir']}
Terminal=true
Categories=System;Security;Network;
Keywords=wireless;wifi;penetration;testing;security;aircrack;hacking;wpa;wep;handshake;
StartupNotify=true
StartupWMClass=Gattrose-NG
Actions=RunAsRoot;

[Desktop Action RunAsRoot]
Name=Run with sudo (elevated privileges)
Exec=sudo {launcher_script}
""")

    desktop_file.chmod(0o644)
    print(f"    Desktop file -> {desktop_file}")

    # Update desktop database (if available)
    if system_wide:
        try:
            subprocess.run(['update-desktop-database', str(paths['desktop_dir'])],
                         capture_output=True, timeout=10)
            print("    Desktop database updated")
        except Exception:
            pass

    # Set up virtual environment
    print("\n[*] Setting up virtual environment...")
    venv_path = paths['install_dir'] / '.venv'

    subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], check=True)

    pip_exe = venv_path / 'bin' / 'pip'
    subprocess.run([str(pip_exe), 'install', '--upgrade', 'pip'], check=True)
    subprocess.run([str(pip_exe), 'install', '-r',
                   str(paths['install_dir'] / 'docs' / 'requirements.txt')], check=True)

    print("    Virtual environment created and dependencies installed")

    # Installation complete
    print("\n" + "="*60)
    print("  Installation Complete!")
    print("="*60)
    print(f"\nGattrose-NG has been installed to: {paths['install_dir']}")
    print(f"\nYou can now run Gattrose-NG by:")
    print(f"  1. Typing 'gattrose-ng' in terminal")
    print(f"  2. Using the application menu launcher")
    print(f"  3. Running: {launcher_script}")

    if not system_wide:
        print(f"\nMake sure {paths['bin_dir']} is in your PATH:")
        print(f"  export PATH=\"{paths['bin_dir']}:$PATH\"")
        print(f"  (Add to ~/.bashrc or ~/.profile for persistence)")

    print("\n")


def uninstall_gattrose(system_wide: bool = False):
    """Uninstall Gattrose from system"""
    print("\n" + "="*60)
    print("  Gattrose Uninstallation")
    print("="*60 + "\n")

    paths = get_install_paths(system_wide)

    # Remove installation directory
    if paths['install_dir'].exists():
        print(f"[*] Removing {paths['install_dir']}...")
        shutil.rmtree(paths['install_dir'])

    # Remove launcher script
    launcher = paths['bin_dir'] / 'gattrose-ng'
    if launcher.exists():
        print(f"[*] Removing {launcher}...")
        launcher.unlink()

    # Remove desktop entry
    desktop = paths['desktop_dir'] / 'gattrose-ng.desktop'
    if desktop.exists():
        print(f"[*] Removing {desktop}...")
        desktop.unlink()

    # Note about data
    if paths['data_dir'].exists():
        print(f"\n[!] Note: User data preserved at {paths['data_dir']}")
        print(f"    To remove data: rm -rf {paths['data_dir']}")

    if paths['config_dir'].exists():
        print(f"[!] Note: Configuration preserved at {paths['config_dir']}")
        print(f"    To remove config: rm -rf {paths['config_dir']}")

    print("\n[+] Gattrose-NG has been uninstalled")
    print()


def main():
    """Main installation routine"""
    check_root()

    if len(sys.argv) > 1:
        if sys.argv[1] == 'uninstall':
            system_wide = '--system' in sys.argv
            uninstall_gattrose(system_wide)
            return 0
        elif sys.argv[1] == '--help':
            print("Gattrose Installation Script")
            print("\nUsage:")
            print("  sudo python3 install.py              # Install for current user")
            print("  sudo python3 install.py --system     # Install system-wide")
            print("  python3 install.py uninstall         # Uninstall user installation")
            print("  sudo python3 install.py uninstall --system  # Uninstall system installation")
            return 0

    system_wide = '--system' in sys.argv

    try:
        install_gattrose(system_wide)
        return 0
    except Exception as e:
        print(f"\n[!] Installation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
