"""
Process Manager
Manages Gattrose-NG processes, prevents duplicates, handles cleanup
"""

import os
import sys
import psutil
import signal
import time
from pathlib import Path
from typing import List, Tuple


class ProcessManager:
    """Manages application processes and prevents duplicates"""

    def __init__(self):
        self.current_pid = os.getpid()
        self.project_root = Path(__file__).parent.parent.parent
        self.main_script = self.project_root / "src" / "main.py"
        self.parent_pids = self._get_parent_chain()

    def _get_parent_chain(self) -> List[int]:
        """
        Get chain of parent PIDs from current process to root

        Returns:
            List of parent PIDs
        """
        parents = []
        try:
            current = psutil.Process(self.current_pid)
            while current:
                try:
                    parent = current.parent()
                    if parent:
                        parents.append(parent.pid)
                        current = parent
                    else:
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        except Exception:
            pass

        return parents

    def _is_parent_or_child(self, pid: int) -> bool:
        """
        Check if a PID is a parent or child of current process

        Args:
            pid: Process ID to check

        Returns:
            True if it's a parent or child, False otherwise
        """
        # Check if it's in our parent chain
        if pid in self.parent_pids:
            return True

        # Check if it's a child of current process
        try:
            current = psutil.Process(self.current_pid)
            children = current.children(recursive=True)
            for child in children:
                if child.pid == pid:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return False

    def find_gattrose_processes(self, exclude_current: bool = True) -> List[Tuple[int, str]]:
        """
        Find all running Gattrose-NG processes

        Returns:
            List of (pid, cmdline) tuples
        """
        processes = []

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Check if this is a Python process
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = proc.info['cmdline']

                        if cmdline and len(cmdline) > 0:
                            # Check if running our main.py
                            cmdline_str = ' '.join(cmdline)

                            if 'gattrose' in cmdline_str.lower() or 'main.py' in cmdline_str:
                                pid = proc.info['pid']

                                # Exclude current process if requested
                                if exclude_current and pid == self.current_pid:
                                    continue

                                # IMPORTANT: Exclude parent processes (like wrapper scripts)
                                # and child processes to avoid killing ourselves
                                if self._is_parent_or_child(pid):
                                    print(f"[DEBUG] Skipping PID {pid} (parent/child of current process)")
                                    continue

                                processes.append((pid, cmdline_str))

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

        except Exception as e:
            print(f"[WARNING] Error finding processes: {e}")

        return processes

    def kill_duplicate_processes(self, force: bool = False) -> int:
        """
        Kill duplicate Gattrose-NG processes

        Args:
            force: If True, use SIGKILL. If False, use SIGTERM

        Returns:
            Number of processes killed
        """
        processes = self.find_gattrose_processes(exclude_current=True)

        if not processes:
            return 0

        print(f"[*] Found {len(processes)} duplicate Gattrose-NG process(es)")

        killed_count = 0

        for pid, cmdline in processes:
            try:
                print(f"[*] Killing process {pid}: {cmdline[:80]}...")

                # Try graceful shutdown first
                os.kill(pid, signal.SIGTERM if not force else signal.SIGKILL)

                # Wait a moment for process to die
                time.sleep(0.5)

                # Check if still alive
                if psutil.pid_exists(pid):
                    print(f"[*] Process {pid} still alive, forcing kill...")
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.2)

                killed_count += 1
                print(f"[✓] Killed process {pid}")

            except ProcessLookupError:
                # Process already dead
                killed_count += 1
                print(f"[✓] Process {pid} already terminated")

            except PermissionError:
                print(f"[!] Permission denied to kill process {pid}")

            except Exception as e:
                print(f"[!] Error killing process {pid}: {e}")

        return killed_count

    def cleanup_orphaned_processes(self) -> int:
        """
        Clean up orphaned background processes (airodump, airmon, etc.)

        Returns:
            Number of processes killed
        """
        orphaned_processes = [
            'airodump-ng',
            'aireplay-ng',
            'aircrack-ng',
            'reaver',
            'wash'
        ]

        killed_count = 0

        print("[*] Checking for orphaned wireless tool processes...")

        for proc_name in orphaned_processes:
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'] == proc_name:
                            pid = proc.info['pid']
                            print(f"[*] Killing orphaned {proc_name} process (PID: {pid})")

                            os.kill(pid, signal.SIGTERM)
                            time.sleep(0.2)

                            if psutil.pid_exists(pid):
                                os.kill(pid, signal.SIGKILL)

                            killed_count += 1

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            except Exception as e:
                print(f"[WARNING] Error cleaning up {proc_name}: {e}")

        return killed_count

    def is_another_instance_running(self) -> bool:
        """
        Check if another instance of Gattrose-NG is already running

        Returns:
            True if another instance is running, False otherwise
        """
        processes = self.find_gattrose_processes(exclude_current=True)
        return len(processes) > 0

    def ensure_single_instance(self, force_kill: bool = True) -> bool:
        """
        Ensure only one instance is running

        Args:
            force_kill: If True, kill other instances. If False, just check.

        Returns:
            True if we are the only instance, False if others exist and weren't killed
        """
        if not self.is_another_instance_running():
            return True

        if force_kill:
            print("[*] Detected duplicate instances, cleaning up...")
            killed = self.kill_duplicate_processes(force=False)

            # Wait a moment and check again
            time.sleep(1)

            if self.is_another_instance_running():
                print("[*] Some processes survived SIGTERM, force killing...")
                killed += self.kill_duplicate_processes(force=True)

            print(f"[✓] Cleaned up {killed} duplicate instance(s)")
            return True
        else:
            return False

    def cleanup_on_exit(self):
        """
        Cleanup processes on application exit
        """
        print("[*] Cleaning up on exit...")

        # Kill orphaned wireless tool processes
        orphaned = self.cleanup_orphaned_processes()
        if orphaned > 0:
            print(f"[✓] Cleaned up {orphaned} orphaned process(es)")

        # Restore all WiFi interfaces to managed mode
        try:
            from ..tools.wifi_monitor import WiFiMonitorManager

            interfaces = WiFiMonitorManager.get_wireless_interfaces()
            for iface in interfaces:
                if WiFiMonitorManager.is_monitor_mode(iface):
                    print(f"[*] Restoring {iface} to managed mode...")
                    success, message = WiFiMonitorManager.disable_monitor_mode(iface)
                    if success:
                        print(f"[✓] {message}")
                    else:
                        print(f"[!] {message}")
        except Exception as e:
            print(f"[!] Error restoring WiFi interfaces: {e}")

        print("[✓] Cleanup complete")

    def register_exit_handler(self):
        """Register cleanup handler for application exit"""
        import atexit
        atexit.register(self.cleanup_on_exit)

        # Also handle signals
        def signal_handler(signum, frame):
            print(f"\n[*] Received signal {signum}, cleaning up...")
            self.cleanup_on_exit()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


def check_and_cleanup_processes() -> bool:
    """
    Convenience function to check and cleanup processes at startup

    Returns:
        True if cleanup was successful or not needed, False on error
    """
    try:
        manager = ProcessManager()

        # Kill any duplicate instances
        if manager.is_another_instance_running():
            print("\n" + "=" * 60)
            print("  WARNING: Another Gattrose-NG instance detected")
            print("=" * 60)

            manager.ensure_single_instance(force_kill=True)

            # Also cleanup orphaned processes
            manager.cleanup_orphaned_processes()

            print("=" * 60 + "\n")

        # Register cleanup handler for exit
        manager.register_exit_handler()

        return True

    except Exception as e:
        print(f"[ERROR] Process cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def force_cleanup_all():
    """
    Force cleanup of ALL Gattrose-NG related processes
    Use this for emergency cleanup
    """
    print("\n[*] Force cleaning up ALL Gattrose-NG processes...")

    manager = ProcessManager()

    # Kill all Gattrose instances (including current)
    processes = manager.find_gattrose_processes(exclude_current=False)

    for pid, cmdline in processes:
        if pid == manager.current_pid:
            continue

        try:
            print(f"[*] Force killing {pid}...")
            os.kill(pid, signal.SIGKILL)
        except Exception as e:
            print(f"[!] Failed to kill {pid}: {e}")

    # Cleanup orphaned processes
    manager.cleanup_orphaned_processes()

    print("[✓] Force cleanup complete")


if __name__ == "__main__":
    # Allow running as standalone script for cleanup
    if len(sys.argv) > 1 and sys.argv[1] == "--force-cleanup":
        force_cleanup_all()
    else:
        manager = ProcessManager()
        processes = manager.find_gattrose_processes(exclude_current=True)

        if processes:
            print(f"Found {len(processes)} Gattrose-NG process(es):")
            for pid, cmdline in processes:
                print(f"  PID {pid}: {cmdline[:80]}")

            response = input("\nKill these processes? [y/N]: ")
            if response.lower() == 'y':
                killed = manager.kill_duplicate_processes()
                print(f"\nKilled {killed} process(es)")
        else:
            print("No duplicate Gattrose-NG processes found")
