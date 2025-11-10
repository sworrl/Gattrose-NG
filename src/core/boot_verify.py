#!/usr/bin/env python3
"""
Boot-Time Verification and Auto-Repair System

Verifies and fixes:
- System services installation
- Database integrity
- PolicyKit policies
- Directory structure
- File permissions
- Dependencies

File Index: 0000102
File Serial: (to be generated)
File Version: 1.0.0
Last Modified: 2025-11-01
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, List


class BootVerifier:
    """Boot-time system verification and auto-repair"""

    def __init__(self, project_root: Path = None):
        if project_root is None:
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = Path(project_root)

        self.issues_found = []
        self.fixes_applied = []
        self.errors = []

        # OS detection info
        self.os_info = {}
        self.is_kali = False
        self.is_ubuntu = False
        self.is_debian = False

    def log_issue(self, issue: str):
        """Log an issue found"""
        self.issues_found.append(issue)
        print(f"[!] {issue}")

    def log_fix(self, fix: str):
        """Log a fix applied"""
        self.fixes_applied.append(fix)
        print(f"[✓] {fix}")

    def log_error(self, error: str):
        """Log an error"""
        self.errors.append(error)
        print(f"[✗] {error}")

    def detect_operating_system(self) -> bool:
        """Detect operating system and version"""
        print("\n[*] Detecting operating system...")

        try:
            # Read /etc/os-release for distribution info
            os_release_file = Path("/etc/os-release")

            if os_release_file.exists():
                with open(os_release_file) as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            # Remove quotes
                            value = value.strip('"').strip("'")
                            self.os_info[key] = value

                # Extract key information
                distro_id = self.os_info.get('ID', 'unknown').lower()
                distro_name = self.os_info.get('NAME', 'Unknown')
                distro_version = self.os_info.get('VERSION_ID', 'unknown')
                distro_codename = self.os_info.get('VERSION_CODENAME', 'unknown')
                pretty_name = self.os_info.get('PRETTY_NAME', 'Unknown OS')

                # Detect specific distributions
                if 'kali' in distro_id or 'kali' in distro_name.lower():
                    self.is_kali = True
                elif 'ubuntu' in distro_id or 'ubuntu' in distro_name.lower():
                    self.is_ubuntu = True
                elif 'debian' in distro_id:
                    self.is_debian = True

                # Also check ID_LIKE for derivatives
                id_like = self.os_info.get('ID_LIKE', '').lower()
                if 'debian' in id_like and not self.is_debian and not self.is_ubuntu:
                    self.is_debian = True

                # Read kernel version
                try:
                    kernel_version = subprocess.run(
                        ['uname', '-r'],
                        capture_output=True,
                        text=True
                    ).stdout.strip()
                except:
                    kernel_version = 'unknown'

                # Display OS information
                print("\n" + "="*60)
                print("  OPERATING SYSTEM INFORMATION")
                print("="*60)
                print(f"Distribution:  {pretty_name}")
                print(f"ID:            {distro_id}")
                print(f"Version:       {distro_version}")
                print(f"Codename:      {distro_codename}")
                print(f"Kernel:        {kernel_version}")

                # Display detected type
                if self.is_kali:
                    print(f"Detected:      Kali Linux (Debian-based pentesting distribution)")
                elif self.is_ubuntu:
                    print(f"Detected:      Ubuntu/Kubuntu (Debian-based)")
                elif self.is_debian:
                    print(f"Detected:      Debian-based distribution")
                else:
                    print(f"Detected:      Unknown/Other Linux distribution")

                # Check architecture
                try:
                    arch = subprocess.run(
                        ['uname', '-m'],
                        capture_output=True,
                        text=True
                    ).stdout.strip()
                    print(f"Architecture:  {arch}")
                except:
                    pass

                print("="*60)

                # Store for later use
                self.os_info['kernel'] = kernel_version
                self.os_info['distribution_type'] = (
                    'kali' if self.is_kali else
                    'ubuntu' if self.is_ubuntu else
                    'debian' if self.is_debian else
                    'other'
                )

                # Save to config file for reference
                self._save_os_info()

                print("[✓] Operating system detected successfully")
                return True

            else:
                self.log_error("Cannot detect OS: /etc/os-release not found")
                return False

        except Exception as e:
            self.log_error(f"OS detection error: {e}")
            return False

    def _save_os_info(self):
        """Save OS info to config for later reference"""
        try:
            import json
            config_dir = self.project_root / "data" / "config"
            config_dir.mkdir(parents=True, exist_ok=True)

            os_info_file = config_dir / "os_info.json"

            with open(os_info_file, 'w') as f:
                json.dump(self.os_info, f, indent=2)

        except Exception as e:
            # Non-critical, don't fail if we can't save
            pass

    def get_package_manager(self) -> str:
        """Get appropriate package manager for the detected OS"""
        if self.is_kali or self.is_ubuntu or self.is_debian:
            return 'apt'
        else:
            # Try to detect
            for pm in ['apt', 'dnf', 'yum', 'pacman', 'zypper']:
                try:
                    result = subprocess.run(['which', pm], capture_output=True)
                    if result.returncode == 0:
                        return pm
                except:
                    pass
            return 'apt'  # Default

    def verify_directory_structure(self) -> bool:
        """Verify and create required directories"""
        print("\n[*] Verifying directory structure...")

        required_dirs = [
            "data",
            "data/database",
            "data/captures",
            "data/captures/handshakes",
            "data/captures/service",
            "data/logs",
            "data/config",
            "bin",
            "services",
            "src",
            "src/core",
            "src/database",
            "src/gui",
            "src/tools",
            "src/utils",
            "src/services",
            "docs"
        ]

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                self.log_issue(f"Missing directory: {dir_name}")
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.log_fix(f"Created directory: {dir_name}")
                except Exception as e:
                    self.log_error(f"Failed to create {dir_name}: {e}")
                    return False

        print("[✓] Directory structure verified")
        return True

    def verify_database(self) -> bool:
        """Verify and initialize database"""
        print("\n[*] Verifying database...")

        try:
            from src.database.models import init_db, get_engine
            from sqlalchemy import text

            # Initialize database
            engine = init_db()

            # Test connection
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            self.log_fix("Database initialized and verified")
            return True

        except Exception as e:
            self.log_error(f"Database verification failed: {e}")
            return False

    def verify_policykit(self) -> bool:
        """Verify and install PolicyKit policy"""
        print("\n[*] Verifying PolicyKit policy...")

        policy_source = self.project_root / "bin" / "com.gattrose.pkexec.policy"
        policy_dest = Path("/usr/share/polkit-1/actions/com.gattrose.pkexec.policy")

        if not policy_source.exists():
            self.log_error("PolicyKit policy source file missing")
            return False

        # Check if installed
        if not policy_dest.exists():
            self.log_issue("PolicyKit policy not installed")

            # Try to install
            try:
                result = subprocess.run(
                    ["sudo", "cp", str(policy_source), str(policy_dest)],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    self.log_fix("PolicyKit policy installed")
                    return True
                else:
                    self.log_error(f"Failed to install policy: {result.stderr}")
                    return False

            except Exception as e:
                self.log_error(f"PolicyKit installation error: {e}")
                return False

        # Policy exists, verify it's current
        try:
            with open(policy_source, 'r') as f:
                source_content = f.read()
            with open(policy_dest, 'r') as f:
                dest_content = f.read()

            if source_content != dest_content:
                self.log_issue("PolicyKit policy outdated")

                subprocess.run(
                    ["sudo", "cp", str(policy_source), str(policy_dest)],
                    check=True
                )
                self.log_fix("PolicyKit policy updated")

        except Exception as e:
            self.log_error(f"PolicyKit verification error: {e}")

        print("[✓] PolicyKit policy verified")
        return True

    def verify_systemd_services(self) -> bool:
        """Verify and install systemd services"""
        print("\n[*] Verifying systemd services...")

        services = [
            "gattrose-scanner.service",
            "gattrose-attacker.service",
            "gattrose-maintenance.service",
            "gattrose-maintenance.timer"
        ]

        all_ok = True

        for service_name in services:
            source = self.project_root / "services" / service_name
            dest = Path("/etc/systemd/system") / service_name

            if not source.exists():
                self.log_error(f"Service file missing: {service_name}")
                all_ok = False
                continue

            # Check if installed
            if not dest.exists():
                self.log_issue(f"Service not installed: {service_name}")

                # Try to install
                try:
                    result = subprocess.run(
                        ["sudo", "cp", str(source), str(dest)],
                        capture_output=True,
                        text=True
                    )

                    if result.returncode == 0:
                        self.log_fix(f"Installed service: {service_name}")

                        # Reload systemd
                        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                    else:
                        self.log_error(f"Failed to install {service_name}: {result.stderr}")
                        all_ok = False

                except Exception as e:
                    self.log_error(f"Service installation error: {e}")
                    all_ok = False
                    continue

            # Verify service file is current
            try:
                with open(source, 'r') as f:
                    source_content = f.read()
                with open(dest, 'r') as f:
                    dest_content = f.read()

                if source_content != dest_content:
                    self.log_issue(f"Service file outdated: {service_name}")

                    subprocess.run(
                        ["sudo", "cp", str(source), str(dest)],
                        check=True
                    )
                    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                    self.log_fix(f"Updated service: {service_name}")

            except Exception as e:
                self.log_error(f"Service verification error: {e}")

        if all_ok:
            print("[✓] Systemd services verified")

        return all_ok

    def verify_file_permissions(self) -> bool:
        """Verify and fix file permissions"""
        print("\n[*] Verifying file permissions...")

        executable_files = [
            "gattrose-ng.py",
            "bin/gattrose-gui.sh",
            "bin/gattrose-launcher.sh",
            "src/services/scanner_service.py",
            "src/services/attacker_service.py",
            "src/services/maintenance_service.py",
            "src/utils/file_manifest.py",
            "src/utils/migrate_manifest.py"
        ]

        for file_path in executable_files:
            full_path = self.project_root / file_path

            if not full_path.exists():
                continue

            # Check if executable
            if not os.access(full_path, os.X_OK):
                self.log_issue(f"File not executable: {file_path}")

                try:
                    full_path.chmod(0o755)
                    self.log_fix(f"Made executable: {file_path}")
                except Exception as e:
                    self.log_error(f"Failed to make executable: {e}")

        print("[✓] File permissions verified")
        return True

    def verify_dependencies(self) -> bool:
        """Verify Python dependencies"""
        print("\n[*] Verifying Python dependencies...")

        requirements_file = self.project_root / "docs" / "requirements.txt"

        if not requirements_file.exists():
            self.log_error("docs/requirements.txt not found")
            return False

        # Check if venv exists
        venv_path = self.project_root / ".venv"
        if not venv_path.exists():
            self.log_issue("Virtual environment missing")

            try:
                subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_path)],
                    check=True
                )
                self.log_fix("Created virtual environment")
            except Exception as e:
                self.log_error(f"Failed to create venv: {e}")
                return False

        # Install/update dependencies
        python_exe = venv_path / "bin" / "python"

        if python_exe.exists():
            try:
                # Check if PyYAML is installed (needed for manifest)
                result = subprocess.run(
                    [str(python_exe), "-c", "import yaml"],
                    capture_output=True
                )

                if result.returncode != 0:
                    self.log_issue("PyYAML not installed")

                    subprocess.run(
                        [str(python_exe), "-m", "pip", "install", "pyyaml"],
                        check=True,
                        capture_output=True
                    )
                    self.log_fix("Installed PyYAML")

            except Exception as e:
                self.log_error(f"Dependency check error: {e}")

        print("[✓] Dependencies verified")
        return True

    def verify_desktop_file(self) -> bool:
        """Verify desktop launcher is installed"""
        print("\n[*] Verifying desktop launcher...")

        desktop_source = self.project_root / "assets" / "gattrose-ng.desktop"
        desktop_dest = Path.home() / ".local" / "share" / "applications" / "gattrose-ng.desktop"

        if not desktop_source.exists():
            self.log_error("Desktop file missing")
            return False

        # Ensure destination directory exists
        desktop_dest.parent.mkdir(parents=True, exist_ok=True)

        # Check if installed
        if not desktop_dest.exists():
            self.log_issue("Desktop launcher not installed")

            try:
                shutil.copy(desktop_source, desktop_dest)
                self.log_fix("Desktop launcher installed")

                # Update desktop database
                subprocess.run(
                    ["update-desktop-database", str(desktop_dest.parent)],
                    capture_output=True
                )

            except Exception as e:
                self.log_error(f"Desktop installation error: {e}")
                return False

        print("[✓] Desktop launcher verified")
        return True

    def run_full_verification(self) -> Tuple[bool, List[str], List[str], List[str]]:
        """
        Run complete boot verification

        Returns:
            (success, issues_found, fixes_applied, errors)
        """
        print("="*60)
        print("  GATTROSE-NG BOOT VERIFICATION")
        print("="*60)

        all_passed = True

        # Run all verifications (OS detection first!)
        all_passed &= self.detect_operating_system()
        all_passed &= self.verify_directory_structure()
        all_passed &= self.verify_database()
        all_passed &= self.verify_file_permissions()
        all_passed &= self.verify_dependencies()
        all_passed &= self.verify_policykit()
        all_passed &= self.verify_systemd_services()
        all_passed &= self.verify_desktop_file()

        # Summary
        print("\n" + "="*60)
        print("  VERIFICATION SUMMARY")
        print("="*60)
        print(f"Issues Found:  {len(self.issues_found)}")
        print(f"Fixes Applied: {len(self.fixes_applied)}")
        print(f"Errors:        {len(self.errors)}")

        if all_passed and len(self.errors) == 0:
            print("\n[✓] All systems verified and operational")
        elif len(self.errors) > 0:
            print("\n[!] Some systems have errors - manual intervention required")
        else:
            print("\n[!] Some issues were fixed - restart may be required")

        print("="*60)
        print()

        return all_passed, self.issues_found, self.fixes_applied, self.errors


def verify_at_boot():
    """Run boot verification (called from main.py)"""
    verifier = BootVerifier()
    success, issues, fixes, errors = verifier.run_full_verification()

    # Return True if no critical errors
    return len(errors) == 0


def main():
    """CLI entry point"""
    verifier = BootVerifier()
    success, issues, fixes, errors = verifier.run_full_verification()

    if errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
