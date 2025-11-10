#!/usr/bin/env python3
"""
Gattrose-NG Tray Icon Watchdog
Monitors all services and ensures tray icons are always running
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path('/opt/gattrose-ng')
sys.path.insert(0, str(PROJECT_ROOT))


class TrayWatchdog:
    """Watchdog to monitor services and ensure tray icons are running"""

    def __init__(self):
        self.check_interval = 30  # Check every 30 seconds
        self.orchestrator_tray_restarts = 0
        self.phone_tray_restarts = 0
        self.running = True

        # X11/Wayland display settings
        self.display_user = 'eurrl'
        self.display_env = self._detect_display_env()

        print("[*] Gattrose-NG Tray Watchdog started")
        print(f"[*] Display environment: {self.display_env}")
        print(f"[*] Check interval: {self.check_interval}s")

    def _detect_display_env(self) -> dict:
        """Detect the current display environment for the user"""
        try:
            # Find a GUI process owned by the user to get the display environment
            # Try common GUI processes
            gui_processes = ['plasmashell', 'gnome-shell', 'kwin', 'konsole', 'dolphin']

            env_vars = {}
            for proc_name in gui_processes:
                try:
                    # Find PID of the process
                    result = subprocess.run(
                        ['pgrep', '-u', self.display_user, proc_name],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        pid = result.stdout.strip().split()[0]

                        # Read environment from /proc/PID/environ
                        environ_file = Path(f'/proc/{pid}/environ')
                        if environ_file.exists():
                            environ_data = environ_file.read_bytes()

                            # Parse null-separated environment variables
                            for line in environ_data.split(b'\0'):
                                if b'=' in line:
                                    line_str = line.decode('utf-8', errors='ignore')
                                    key, value = line_str.split('=', 1)
                                    if key in ['DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR',
                                             'DBUS_SESSION_BUS_ADDRESS', 'XAUTHORITY']:
                                        if value:  # Only add if not empty
                                            env_vars[key] = value

                            # If we found display variables, we're done
                            if 'DISPLAY' in env_vars or 'WAYLAND_DISPLAY' in env_vars:
                                break

                except Exception:
                    continue

            # Fallback values if we couldn't detect
            if 'XDG_RUNTIME_DIR' not in env_vars:
                env_vars['XDG_RUNTIME_DIR'] = '/run/user/1000'
            if 'DBUS_SESSION_BUS_ADDRESS' not in env_vars:
                env_vars['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=/run/user/1000/bus'
            if 'DISPLAY' not in env_vars and 'WAYLAND_DISPLAY' not in env_vars:
                # Try to guess - most systems use :0 or :1 for X11
                env_vars['DISPLAY'] = ':1'

            return env_vars

        except Exception as e:
            print(f"[!] Failed to detect display environment: {e}")
            return {
                'DISPLAY': ':1',
                'XDG_RUNTIME_DIR': '/run/user/1000',
                'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus'
            }

    def _is_tray_running(self, process_name: str) -> bool:
        """Check if a tray process is running"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', process_name],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[!] Error checking if {process_name} is running: {e}")
            return False

    def _start_tray(self, script_path: str, name: str) -> bool:
        """Start a tray icon as the display user"""
        try:
            print(f"[*] Starting {name}...")

            # Build command with proper environment using env utility
            cmd = ['sudo', '-u', self.display_user, 'env']

            # Add environment variables as KEY=VALUE pairs
            for key, value in self.display_env.items():
                cmd.append(f'{key}={value}')

            # Add the Python command
            cmd.extend([
                f'{PROJECT_ROOT}/.venv/bin/python',
                script_path
            ])

            # Start the process in background
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            # Wait a moment and verify it started
            time.sleep(3)

            if self._is_tray_running(script_path):
                print(f"[+] {name} started successfully")
                return True
            else:
                print(f"[!] {name} failed to start")
                return False

        except Exception as e:
            print(f"[!] Error starting {name}: {e}")
            return False

    def _check_orchestrator_tray(self):
        """Check and restart orchestrator tray if needed"""
        if not self._is_tray_running('unified_orchestrator_tray.py'):
            print(f"[WATCHDOG] Orchestrator tray is not running!")

            if self._start_tray(
                f'{PROJECT_ROOT}/src/unified_orchestrator_tray.py',
                'Orchestrator Tray'
            ):
                self.orchestrator_tray_restarts += 1
                print(f"[WATCHDOG] ✓ Orchestrator tray restarted (restart #{self.orchestrator_tray_restarts})")
            else:
                print(f"[WATCHDOG] ✗ Failed to restart orchestrator tray")

    def _check_phone_tray(self):
        """Check phone tray - now part of unified orchestrator tray"""
        # Phone tray is now integrated into unified_orchestrator_tray.py
        # This method is kept for compatibility but does nothing
        pass

    def _check_services(self):
        """Check status of gattrose services"""
        services = [
            'gattrose-orchestrator.service',
            'gattrose-scanner.service',
            'gattrose-attacker.service'
        ]

        for service in services:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                status = result.stdout.strip()
                if status != 'active':
                    print(f"[WATCHDOG] ⚠️  Service {service} is {status}")

            except Exception as e:
                print(f"[WATCHDOG] Error checking {service}: {e}")

    def run(self):
        """Main watchdog loop"""
        print("[+] Watchdog running - monitoring services and tray icons")
        print("[i] Press Ctrl+C to stop")

        # Initial startup - ensure orchestrator tray is running
        # (Phone tray is integrated into orchestrator tray)
        self._check_orchestrator_tray()

        while self.running:
            try:
                time.sleep(self.check_interval)

                # Check tray icons
                self._check_orchestrator_tray()
                self._check_phone_tray()

                # Check services
                self._check_services()

            except KeyboardInterrupt:
                print("\n[*] Shutting down watchdog...")
                self.running = False
                break
            except Exception as e:
                print(f"[!] Watchdog error: {e}")
                time.sleep(5)

        print("[+] Watchdog stopped")


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("\n[*] Received shutdown signal")
    sys.exit(0)


if __name__ == '__main__':
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start watchdog
    watchdog = TrayWatchdog()
    watchdog.run()
