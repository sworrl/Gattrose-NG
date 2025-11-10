#!/usr/bin/env python3
"""
Gattrose-NG - Wireless Penetration Testing Suite
Main launcher with automatic venv and dependency management

"Gattrose" is a nickname for REAvER's daughter, who was as hungry
as a baby gator when she was an infant. This project is dedicated
to her fierce spirit.

Developed by REAvER from Falcon Technix
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Project metadata
VERSION = "2.2.4"
APP_NAME = "Gattrose-NG"


def request_sudo_at_startup():
    """
    Request sudo authentication at startup (one time)
    Returns True if running with sudo, False otherwise
    """
    # Check if already running as root
    if os.geteuid() == 0:
        print("[+] Running with elevated privileges")
        return True

    print("\n" + "="*60)
    print(f"  {APP_NAME} requires elevated privileges")
    print("  for wireless network operations")
    print("="*60 + "\n")

    # Test sudo access
    print("[*] Requesting sudo authentication...")
    try:
        result = subprocess.run(
            ["sudo", "-v"],
            timeout=60
        )

        if result.returncode == 0:
            print("[+] Authentication successful")
            # Keep sudo alive in background
            subprocess.Popen(
                ["sudo", "-v"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        else:
            print("[!] Authentication failed")
            return False

    except subprocess.TimeoutExpired:
        print("[!] Authentication timeout")
        return False
    except Exception as e:
        print(f"[!] Authentication error: {e}")
        return False


class GattroseBootstrap:
    """Handles venv creation, dependency installation, and app launching"""

    def __init__(self):
        self.project_root = Path(__file__).parent.resolve()
        self.is_portable = self._detect_portable_mode()
        self.venv_path = self._get_venv_path()
        self.python_exe = self._get_python_exe()

    def _detect_portable_mode(self):
        """Detect if running in portable or installed mode"""
        # Check if installed to system paths
        install_marker = self.project_root / ".installed"
        return not install_marker.exists()

    def _get_venv_path(self):
        """Get appropriate venv path based on portable/installed mode"""
        if self.is_portable:
            # Portable mode: venv inside project directory
            return self.project_root / ".venv"
        else:
            # Installed mode: venv in user's home directory
            home = Path.home()
            return home / ".local" / "share" / "gattrose" / "venv"

    def _get_python_exe(self):
        """Get path to Python executable in venv"""
        if platform.system() == "Windows":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"

    def check_venv(self):
        """Check if venv exists and is valid"""
        return self.venv_path.exists() and self.python_exe.exists()

    def create_venv(self):
        """Create virtual environment"""
        print(f"[*] Creating virtual environment at {self.venv_path}")
        self.venv_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.check_call([
                sys.executable, "-m", "venv", str(self.venv_path)
            ])
            print("[+] Virtual environment created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[!] Failed to create venv: {e}")
            return False

    def install_dependencies(self):
        """Install required Python packages"""
        print("[*] Installing Python dependencies...")

        requirements = self.project_root / "docs" / "requirements.txt"
        if not requirements.exists():
            print("[!] docs/requirements.txt not found, skipping pip install")
            return True

        try:
            subprocess.check_call([
                str(self.python_exe), "-m", "pip", "install",
                "--upgrade", "pip"
            ])
            subprocess.check_call([
                str(self.python_exe), "-m", "pip", "install",
                "-r", str(requirements)
            ])
            print("[+] Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[!] Failed to install dependencies: {e}")
            return False

    def launch_app(self):
        """Launch the main Qt6 application"""
        main_app = self.project_root / "src" / "main.py"

        if not main_app.exists():
            print(f"[!] Main application not found at {main_app}")
            return False

        print(f"[*] Launching {APP_NAME}...")

        # Set environment variables
        env = os.environ.copy()
        env["GATTROSE_NG_ROOT"] = str(self.project_root)
        env["GATTROSE_NG_PORTABLE"] = "1" if self.is_portable else "0"
        env["GATTROSE_NG_VERSION"] = VERSION

        try:
            subprocess.check_call([
                str(self.python_exe), str(main_app)
            ], env=env)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[!] Application exited with error: {e}")
            return False
        except KeyboardInterrupt:
            print("\n[*] Shutting down...")
            return True

    def run(self):
        """Main bootstrap sequence"""
        print(f"\n{'='*60}")
        print(f"  {APP_NAME} v{VERSION}")
        print(f"  Wireless Penetration Testing Suite")
        print(f"{'='*60}\n")

        print(f"[*] Project root: {self.project_root}")
        print(f"[*] Mode: {'Portable' if self.is_portable else 'Installed'}")
        print(f"[*] Virtual environment: {self.venv_path}")
        print()

        # Check and create venv if needed
        if not self.check_venv():
            print("[!] Virtual environment not found")
            if not self.create_venv():
                print("[!] Failed to create virtual environment")
                return 1
            if not self.install_dependencies():
                print("[!] Failed to install dependencies")
                return 1
        else:
            print("[+] Virtual environment found")

        # Launch the application
        if not self.launch_app():
            return 1

        return 0


def main():
    """Entry point"""
    try:
        # Request sudo authentication at startup (one time)
        if not request_sudo_at_startup():
            print("\n[!] Sudo authentication required for wireless operations")
            print("[*] Exiting...")
            sys.exit(1)

        print()  # Blank line for spacing

        bootstrap = GattroseBootstrap()
        sys.exit(bootstrap.run())
    except KeyboardInterrupt:
        print("\n[*] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
