#!/usr/bin/env python3
"""
Gattrose-NG Update Script
Syncs changes from dev directory to /opt/gattrose-ng installation
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def print_status(msg, color=GREEN):
    print(f"{color}[*]{RESET} {msg}")

def print_error(msg):
    print(f"{RED}[!]{RESET} {msg}")

def print_success(msg):
    print(f"{GREEN}[✓]{RESET} {msg}")

def check_sudo():
    """Check if we have sudo access"""
    if os.geteuid() != 0:
        print_error("This script needs sudo to update /opt/gattrose-ng")
        print_status("Run: sudo python3 update_install.py", YELLOW)
        sys.exit(1)

def sync_directory(src, dst, desc):
    """Sync a directory from src to dst"""
    print_status(f"Syncing {desc}...")

    if not src.exists():
        print_error(f"Source directory not found: {src}")
        return False

    # Create destination if it doesn't exist
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Remove old destination if it's a symlink
    if dst.is_symlink():
        dst.unlink()

    # Copy directory
    if dst.exists() and not dst.is_symlink():
        shutil.rmtree(dst)

    shutil.copytree(src, dst, symlinks=False, dirs_exist_ok=True)
    print_success(f"{desc} synced")
    return True

def sync_file(src, dst, desc):
    """Sync a file from src to dst"""
    print_status(f"Syncing {desc}...")

    if not src.exists():
        print_error(f"Source file not found: {src}")
        return False

    # Create destination directory if needed
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Remove symlink if exists
    if dst.is_symlink():
        dst.unlink()

    # Copy file
    shutil.copy2(src, dst)
    print_success(f"{desc} synced")
    return True

def restart_services():
    """Restart systemd services"""
    print_status("Restarting services...")

    # Restart system orchestrator (as root)
    try:
        subprocess.run(['systemctl', 'restart', 'gattrose-orchestrator.service'],
                      check=False, capture_output=True)
        print_success("Orchestrator service restarted")
    except Exception as e:
        print_error(f"Failed to restart orchestrator: {e}")

    # Get the user who invoked sudo
    sudo_user = os.environ.get('SUDO_USER')
    if sudo_user:
        # Restart user tray service
        try:
            subprocess.run(['sudo', '-u', sudo_user, 'systemctl', '--user',
                          'restart', 'gattrose-tray.service'],
                          check=False, capture_output=True)
            print_success("Tray service restarted")
        except Exception as e:
            print_error(f"Failed to restart tray: {e}")

def main():
    print("\n" + "="*60)
    print("  Gattrose-NG Update/Install Script")
    print("  Syncing dev → /opt/gattrose-ng")
    print("="*60 + "\n")

    check_sudo()

    # Source and destination paths
    dev_root = Path("/home/eurrl/Documents/Code & Scripts/gattrose-ng")
    install_root = Path("/opt/gattrose-ng")

    if not dev_root.exists():
        print_error(f"Dev directory not found: {dev_root}")
        sys.exit(1)

    # Sync main directories
    sync_directory(dev_root / "src", install_root / "src", "Source code")
    sync_directory(dev_root / "security", install_root / "security", "Security modules")
    sync_directory(dev_root / "config", install_root / "config", "Configuration modules")
    sync_directory(dev_root / "bin", install_root / "bin", "Scripts")
    sync_directory(dev_root / "assets", install_root / "assets", "Assets")
    sync_directory(dev_root / "docs", install_root / "docs", "Documentation")

    # Sync desktop files to system applications directory
    print_status("Syncing desktop files...")
    if (dev_root / "assets" / "gattrose-ng.desktop").exists():
        sync_file(dev_root / "assets" / "gattrose-ng.desktop",
                 Path("/usr/share/applications/gattrose-ng.desktop"),
                 "Main desktop entry")
    if (dev_root / "assets" / "gattrose-tray.desktop").exists():
        sync_file(dev_root / "assets" / "gattrose-tray.desktop",
                 Path("/usr/share/applications/gattrose-tray.desktop"),
                 "Tray desktop entry")

    # Remove old user-specific desktop files (use system-wide ones instead)
    old_user_desktop = Path.home() / ".local/share/applications/gattrose-ng.desktop"
    if old_user_desktop.exists():
        old_user_desktop.unlink()
        print_success("Removed old user-specific desktop file")

    # Sync main launcher to /usr/local/bin
    if (dev_root / "bin" / "gattrose-ng").exists():
        sync_file(dev_root / "bin" / "gattrose-ng",
                 Path("/usr/local/bin/gattrose-ng"),
                 "Main launcher")
        os.chmod("/usr/local/bin/gattrose-ng", 0o755)

    # Set permissions
    print_status("Setting permissions...")
    os.chmod(install_root / "bin" / "gattrose-gui.sh", 0o755)
    print_success("Permissions set")

    # Restart services automatically
    print("\n" + "="*60)
    restart_services()

    print("\n" + "="*60)
    print_success("Update complete!")
    print_status("You can now run: gattrose-ng", YELLOW)
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
