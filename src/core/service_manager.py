"""
Systemd Service Manager for Gattrose-NG
Manages all three background services: scanner, attacker, and maintenance
"""

import subprocess
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, List


class ServiceManager:
    """Manage Gattrose-NG systemd services"""

    # All three services
    SERVICES = {
        'scanner': 'gattrose-scanner.service',
        'attacker': 'gattrose-attacker.service',
        'maintenance': 'gattrose-maintenance.service'
    }

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    SERVICES_DIR = PROJECT_ROOT / "services"

    @staticmethod
    def is_installed(service_name: str = None) -> bool:
        """Check if service(s) are installed

        Args:
            service_name: Specific service to check (scanner/attacker/maintenance) or None for all

        Returns:
            True if specified service (or all services) are installed
        """
        if service_name:
            if service_name not in ServiceManager.SERVICES:
                return False
            service_file = ServiceManager.SERVICES[service_name]
            return (Path("/etc/systemd/system") / service_file).exists()
        else:
            # Check if all services are installed
            return all(
                (Path("/etc/systemd/system") / svc).exists()
                for svc in ServiceManager.SERVICES.values()
            )

    @staticmethod
    def install_all() -> Tuple[bool, str]:
        """Install all services to systemd

        Returns:
            (success: bool, message: str)
        """
        try:
            installed = []
            failed = []

            for service_key, service_file in ServiceManager.SERVICES.items():
                source_file = ServiceManager.SERVICES_DIR / service_file

                if not source_file.exists():
                    failed.append(f"{service_key}: file not found at {source_file}")
                    continue

                # Copy service file to systemd directory
                result = subprocess.run(
                    ['sudo', 'cp', str(source_file), '/etc/systemd/system/'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    failed.append(f"{service_key}: {result.stderr}")
                else:
                    installed.append(service_key)

            # Also install the timer for maintenance
            timer_source = ServiceManager.SERVICES_DIR / "gattrose-maintenance.timer"
            if timer_source.exists():
                subprocess.run(
                    ['sudo', 'cp', str(timer_source), '/etc/systemd/system/'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            # Reload systemd daemon
            result = subprocess.run(
                ['sudo', 'systemctl', 'daemon-reload'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return (False, f"Failed to reload systemd: {result.stderr}")

            if failed:
                return (False, f"Installed: {', '.join(installed)}. Failed: {'; '.join(failed)}")
            else:
                return (True, f"All services installed successfully: {', '.join(installed)}")

        except Exception as e:
            return (False, f"Error installing services: {e}")

    @staticmethod
    def start(service_name: str = None) -> Tuple[bool, str]:
        """Start service(s)

        Args:
            service_name: Specific service to start or None for all

        Returns:
            (success: bool, message: str)
        """
        try:
            services_to_start = []

            if service_name:
                if service_name not in ServiceManager.SERVICES:
                    return (False, f"Unknown service: {service_name}")
                services_to_start = [ServiceManager.SERVICES[service_name]]
            else:
                services_to_start = list(ServiceManager.SERVICES.values())

            started = []
            failed = []

            for svc in services_to_start:
                result = subprocess.run(
                    ['sudo', 'systemctl', 'start', svc],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    failed.append(f"{svc}: {result.stderr}")
                else:
                    started.append(svc)

            # Also start the maintenance timer if starting all or maintenance
            if not service_name or service_name == 'maintenance':
                subprocess.run(
                    ['sudo', 'systemctl', 'start', 'gattrose-maintenance.timer'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            if failed:
                return (False, f"Started: {', '.join(started)}. Failed: {'; '.join(failed)}")
            else:
                return (True, f"Started: {', '.join(started)}")

        except Exception as e:
            return (False, f"Error starting service(s): {e}")

    @staticmethod
    def stop(service_name: str = None) -> Tuple[bool, str]:
        """Stop service(s)

        Args:
            service_name: Specific service to stop or None for all

        Returns:
            (success: bool, message: str)
        """
        try:
            services_to_stop = []

            if service_name:
                if service_name not in ServiceManager.SERVICES:
                    return (False, f"Unknown service: {service_name}")
                services_to_stop = [ServiceManager.SERVICES[service_name]]
            else:
                services_to_stop = list(ServiceManager.SERVICES.values())

            stopped = []
            failed = []

            for svc in services_to_stop:
                result = subprocess.run(
                    ['sudo', 'systemctl', 'stop', svc],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0 and "not loaded" not in result.stderr:
                    failed.append(f"{svc}: {result.stderr}")
                else:
                    stopped.append(svc)

            # Also stop the maintenance timer if stopping all or maintenance
            if not service_name or service_name == 'maintenance':
                subprocess.run(
                    ['sudo', 'systemctl', 'stop', 'gattrose-maintenance.timer'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            if failed:
                return (False, f"Stopped: {', '.join(stopped)}. Failed: {'; '.join(failed)}")
            else:
                return (True, f"Stopped: {', '.join(stopped)}")

        except Exception as e:
            return (False, f"Error stopping service(s): {e}")

    @staticmethod
    def enable(service_name: str = None) -> Tuple[bool, str]:
        """Enable service(s) to start at boot

        Args:
            service_name: Specific service to enable or None for all

        Returns:
            (success: bool, message: str)
        """
        try:
            services_to_enable = []

            if service_name:
                if service_name not in ServiceManager.SERVICES:
                    return (False, f"Unknown service: {service_name}")
                services_to_enable = [ServiceManager.SERVICES[service_name]]
            else:
                services_to_enable = list(ServiceManager.SERVICES.values())

            enabled = []
            failed = []

            for svc in services_to_enable:
                result = subprocess.run(
                    ['sudo', 'systemctl', 'enable', svc],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    failed.append(f"{svc}: {result.stderr}")
                else:
                    enabled.append(svc)

            # Also enable the maintenance timer
            if not service_name or service_name == 'maintenance':
                subprocess.run(
                    ['sudo', 'systemctl', 'enable', 'gattrose-maintenance.timer'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            if failed:
                return (False, f"Enabled: {', '.join(enabled)}. Failed: {'; '.join(failed)}")
            else:
                return (True, f"Enabled: {', '.join(enabled)}")

        except Exception as e:
            return (False, f"Error enabling service(s): {e}")

    @staticmethod
    def get_all_status() -> Dict[str, dict]:
        """Get status for all services

        Returns:
            Dictionary mapping service names to their status info
        """
        all_status = {}

        for service_key, service_file in ServiceManager.SERVICES.items():
            status = {
                'name': service_key,
                'service_file': service_file,
                'installed': False,
                'enabled': False,
                'active': False,
                'running': False,
                'status_text': 'Not installed',
                'details': ''
            }

            try:
                # Check if installed
                service_path = Path("/etc/systemd/system") / service_file
                status['installed'] = service_path.exists()

                if not status['installed']:
                    all_status[service_key] = status
                    continue

                # Get systemctl status
                result = subprocess.run(
                    ['systemctl', 'status', service_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                output = result.stdout

                # Parse status
                if 'enabled' in output or 'static' in output:
                    status['enabled'] = True

                if 'active (running)' in output:
                    status['active'] = True
                    status['running'] = True
                    status['status_text'] = '✓ Running'
                elif 'inactive' in output or 'dead' in output:
                    status['status_text'] = '○ Stopped'
                elif 'failed' in output:
                    status['status_text'] = '✗ Failed'
                else:
                    status['status_text'] = '? Unknown'

                status['details'] = output

            except Exception as e:
                status['details'] = f"Error: {e}"
                status['status_text'] = '✗ Error'

            all_status[service_key] = status

        return all_status

    @staticmethod
    def get_status() -> dict:
        """Get aggregated status for all services (for backward compatibility)

        Returns:
            Dictionary with aggregated status
        """
        all_status = ServiceManager.get_all_status()

        # Count installed, running, enabled services
        total = len(ServiceManager.SERVICES)
        installed_count = sum(1 for s in all_status.values() if s['installed'])
        running_count = sum(1 for s in all_status.values() if s['running'])
        enabled_count = sum(1 for s in all_status.values() if s['enabled'])

        # Determine overall status
        if installed_count == 0:
            status_text = 'Not installed'
        elif running_count == total:
            status_text = f'✓ All services running ({total}/{total})'
        elif running_count > 0:
            status_text = f'⚠ Partially running ({running_count}/{total})'
        else:
            status_text = f'○ All services stopped'

        return {
            'installed': installed_count > 0,
            'running': running_count > 0,
            'enabled': enabled_count > 0,
            'status_text': status_text,
            'installed_count': installed_count,
            'running_count': running_count,
            'enabled_count': enabled_count,
            'total_count': total,
            'services': all_status
        }

    @staticmethod
    def get_logs(lines: int = 50) -> str:
        """Get aggregated logs from all services (for backward compatibility)

        Args:
            lines: Number of log lines per service

        Returns:
            Combined log output from all services
        """
        all_logs = []

        for service_name, service_file in ServiceManager.SERVICES.items():
            logs = ServiceManager.get_service_logs(service_name, lines)
            if logs and not logs.startswith("Unknown service"):
                all_logs.append(f"=== {service_name.upper()} SERVICE ===")
                all_logs.append(logs)
                all_logs.append("")

        return "\n".join(all_logs) if all_logs else "No logs available"

    @staticmethod
    def get_service_logs(service_name: str, lines: int = 50) -> str:
        """Get logs for a specific service

        Args:
            service_name: Service to get logs for (scanner/attacker/maintenance)
            lines: Number of log lines to retrieve

        Returns:
            Log output as string
        """
        if service_name not in ServiceManager.SERVICES:
            return f"Unknown service: {service_name}"

        service_file = ServiceManager.SERVICES[service_name]

        try:
            result = subprocess.run(
                ['journalctl', '-u', service_file, '-n', str(lines), '--no-pager'],
                capture_output=True,
                text=True,
                timeout=10
            )

            return result.stdout

        except Exception as e:
            return f"Error getting logs: {e}"

    @staticmethod
    def uninstall() -> Tuple[bool, str]:
        """Uninstall all services from systemd

        Returns:
            (success: bool, message: str)
        """
        try:
            stopped = []
            disabled = []
            removed = []
            failed = []

            for service_key, service_file in ServiceManager.SERVICES.items():
                # Stop the service
                stop_result = subprocess.run(
                    ['sudo', 'systemctl', 'stop', service_file],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if stop_result.returncode == 0:
                    stopped.append(service_key)

                # Disable the service
                disable_result = subprocess.run(
                    ['sudo', 'systemctl', 'disable', service_file],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if disable_result.returncode == 0:
                    disabled.append(service_key)

                # Remove service file from systemd directory
                systemd_file = Path(f"/etc/systemd/system/{service_file}")
                if systemd_file.exists():
                    remove_result = subprocess.run(
                        ['sudo', 'rm', str(systemd_file)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if remove_result.returncode == 0:
                        removed.append(service_key)
                    else:
                        failed.append(f"{service_key}: {remove_result.stderr}")

            # Also remove timer if it exists
            timer_file = Path("/etc/systemd/system/gattrose-maintenance.timer")
            if timer_file.exists():
                subprocess.run(
                    ['sudo', 'rm', str(timer_file)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            # Reload systemd daemon
            reload_result = subprocess.run(
                ['sudo', 'systemctl', 'daemon-reload'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if reload_result.returncode != 0:
                return (False, f"Failed to reload systemd: {reload_result.stderr}")

            if failed:
                return (False, f"Uninstalled: {', '.join(removed)}. Failed: {'; '.join(failed)}")
            else:
                return (True, f"All services uninstalled successfully: {', '.join(removed)}")

        except Exception as e:
            return (False, f"Error uninstalling services: {e}")
