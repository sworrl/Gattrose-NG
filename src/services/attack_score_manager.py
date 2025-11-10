"""
Attack Score Manager with Intelligent Updates and Data Smoothing
Prevents GUI lag by throttling recalculations and smoothing signal data
"""

import time
import threading
from typing import Dict, Optional, Tuple
from collections import deque
from datetime import datetime

from ..database.models import get_session, Network, CurrentScanNetwork
from ..tools.attack_scoring import AttackScorer


class NetworkScoreTracker:
    """Tracks score-related data for a single network with smoothing"""

    def __init__(self, bssid: str, window_size: int = 5):
        self.bssid = bssid
        self.window_size = window_size

        # Moving average windows
        self.signal_history = deque(maxlen=window_size)  # Signal strength history
        self.client_count_history = deque(maxlen=window_size)  # Client count history

        # Last known values
        self.last_signal = None
        self.last_client_count = 0
        self.last_score = None
        self.last_update = 0

        # Cached network data
        self.encryption = None
        self.authentication = None
        self.cipher = None
        self.wps_enabled = False
        self.channel = None
        self.hidden = False
        self.beacon_count = 0

    def add_signal_sample(self, signal: int) -> int:
        """Add signal sample and return smoothed value"""
        if signal and signal != -1:
            self.signal_history.append(signal)
            self.last_signal = signal

        # Return moving average
        if self.signal_history:
            return int(sum(self.signal_history) / len(self.signal_history))
        return self.last_signal or -70

    def add_client_count(self, count: int) -> int:
        """Add client count and return smoothed value"""
        self.client_count_history.append(count)
        self.last_client_count = count

        # Return moving average (rounded)
        if self.client_count_history:
            return int(sum(self.client_count_history) / len(self.client_count_history))
        return 0

    def should_update(self, min_interval: float = 10.0) -> bool:
        """Check if enough time has passed since last update"""
        current_time = time.time()
        if current_time - self.last_update >= min_interval:
            self.last_update = current_time
            return True
        return False

    def has_significant_change(self, new_signal: int, new_client_count: int) -> bool:
        """Check if there's a significant change warranting immediate update"""
        # Significant signal change (>10 dBm)
        if self.last_signal and abs(new_signal - self.last_signal) > 10:
            return True

        # Client count changed
        if new_client_count != self.last_client_count:
            return True

        return False


class AttackScoreManager:
    """
    Manages attack score updates with intelligent throttling and smoothing
    """

    def __init__(self, update_interval: float = 15.0, signal_window: int = 5):
        """
        Initialize score manager

        Args:
            update_interval: Minimum seconds between score updates (default 15s)
            signal_window: Number of samples for moving average (default 5)
        """
        self.update_interval = update_interval
        self.signal_window = signal_window

        # Track all networks
        self.trackers: Dict[str, NetworkScoreTracker] = {}

        # Update control
        self._lock = threading.RLock()
        self.running = False
        self._update_thread: Optional[threading.Thread] = None

        # Stats
        self.total_updates = 0
        self.throttled_updates = 0
        self.last_batch_update = 0

    def start(self):
        """Start the background update thread"""
        if self.running:
            return

        self.running = True
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        print(f"[SCORE-MGR] Started with {self.update_interval}s interval")

    def stop(self):
        """Stop the background update thread"""
        self.running = False
        if self._update_thread:
            self._update_thread.join(timeout=2)

    def _update_loop(self):
        """Background loop for periodic score updates"""
        while self.running:
            try:
                # Wait for update interval
                time.sleep(self.update_interval)

                # Batch update all networks
                self.update_all_scores(force=False)

            except Exception as e:
                print(f"[SCORE-MGR] Error in update loop: {e}")
                import traceback
                traceback.print_exc()

    def get_or_create_tracker(self, bssid: str) -> NetworkScoreTracker:
        """Get or create a tracker for a network"""
        with self._lock:
            if bssid not in self.trackers:
                self.trackers[bssid] = NetworkScoreTracker(bssid, self.signal_window)
            return self.trackers[bssid]

    def update_network_data(self, bssid: str, signal: Optional[int] = None,
                           client_count: int = 0, encryption: str = None,
                           **kwargs) -> Tuple[Optional[float], bool]:
        """
        Update network data with smoothing and return score if updated

        Returns:
            Tuple of (new_score, was_updated)
        """
        with self._lock:
            tracker = self.get_or_create_tracker(bssid)

            # Update tracker data
            if signal:
                smoothed_signal = tracker.add_signal_sample(signal)
            else:
                smoothed_signal = tracker.last_signal or -70

            smoothed_clients = tracker.add_client_count(client_count)

            # Update cached network attributes
            if encryption:
                tracker.encryption = encryption
            if 'authentication' in kwargs:
                tracker.authentication = kwargs['authentication']
            if 'cipher' in kwargs:
                tracker.cipher = kwargs['cipher']
            if 'wps_enabled' in kwargs:
                tracker.wps_enabled = kwargs['wps_enabled']
            if 'channel' in kwargs:
                tracker.channel = kwargs['channel']
            if 'hidden' in kwargs:
                tracker.hidden = kwargs['hidden']
            if 'beacon_count' in kwargs:
                tracker.beacon_count = kwargs['beacon_count']

            # Check if we should update score
            significant_change = tracker.has_significant_change(
                signal or smoothed_signal,
                client_count
            )

            should_update = tracker.should_update(self.update_interval) or significant_change

            if should_update:
                # Calculate new score
                new_score, risk = AttackScorer.calculate_score(
                    encryption=tracker.encryption or '',
                    authentication=tracker.authentication or '',
                    power=str(smoothed_signal),
                    wps_enabled=tracker.wps_enabled,
                    has_clients=(smoothed_clients > 0),
                    hidden=tracker.hidden,
                    beacons=tracker.beacon_count,
                    channel=str(tracker.channel) if tracker.channel else '',
                    cipher=tracker.cipher or ''
                )

                tracker.last_score = new_score
                self.total_updates += 1

                return new_score, True
            else:
                self.throttled_updates += 1
                return tracker.last_score, False

    def update_all_scores(self, force: bool = False) -> int:
        """
        Batch update all network scores from current_scan_networks

        Args:
            force: Force update even if not enough time passed

        Returns:
            Number of networks updated
        """
        updated_count = 0

        try:
            session = get_session()
            try:
                # Get all current scan networks
                current_networks = session.query(CurrentScanNetwork).all()

                # Count clients per network (from current_scan_clients if available)
                client_counts = {}
                try:
                    from ..database.models import CurrentScanClient
                    clients = session.query(CurrentScanClient).all()
                    for client in clients:
                        if client.bssid:
                            client_counts[client.bssid] = client_counts.get(client.bssid, 0) + 1
                except:
                    pass  # Table might not exist

                # Update scores for each network
                for net in current_networks:
                    client_count = client_counts.get(net.bssid, 0)

                    new_score, was_updated = self.update_network_data(
                        bssid=net.bssid,
                        signal=net.power,
                        client_count=client_count,
                        encryption=net.encryption,
                        authentication=net.authentication,
                        cipher=net.cipher,
                        wps_enabled=net.wps_enabled or False,
                        channel=net.channel,
                        hidden=(not net.ssid or net.ssid == ''),
                        beacon_count=net.beacon_count or 0
                    )

                    if was_updated and new_score is not None:
                        # Update the attack_score in current_scan_networks
                        net.attack_score = new_score
                        updated_count += 1

                        # Also update in historical networks table
                        hist_net = session.query(Network).filter_by(bssid=net.bssid).first()
                        if hist_net:
                            hist_net.current_attack_score = int(new_score)

                            # Track highest/lowest scores
                            if not hist_net.highest_attack_score or new_score > hist_net.highest_attack_score:
                                hist_net.highest_attack_score = int(new_score)
                            if not hist_net.lowest_attack_score or new_score < hist_net.lowest_attack_score:
                                hist_net.lowest_attack_score = int(new_score)

                            # Update risk level
                            if new_score >= 80:
                                hist_net.risk_level = 'CRITICAL'
                            elif new_score >= 60:
                                hist_net.risk_level = 'HIGH'
                            elif new_score >= 35:
                                hist_net.risk_level = 'MEDIUM'
                            else:
                                hist_net.risk_level = 'LOW'

                # Commit all updates at once (batch operation)
                session.commit()

                self.last_batch_update = time.time()

                if updated_count > 0:
                    print(f"[SCORE-MGR] Updated {updated_count}/{len(current_networks)} network scores")

            finally:
                session.close()

        except Exception as e:
            print(f"[SCORE-MGR] Error updating scores: {e}")
            import traceback
            traceback.print_exc()

        return updated_count

    def get_stats(self) -> Dict:
        """Get manager statistics"""
        return {
            'tracked_networks': len(self.trackers),
            'total_updates': self.total_updates,
            'throttled_updates': self.throttled_updates,
            'update_interval': self.update_interval,
            'last_batch_update': datetime.fromtimestamp(self.last_batch_update).isoformat() if self.last_batch_update else None,
            'throttle_ratio': f"{(self.throttled_updates / max(1, self.total_updates + self.throttled_updates) * 100):.1f}%"
        }


# Singleton instance
_attack_score_manager: Optional[AttackScoreManager] = None


def get_attack_score_manager(update_interval: float = 15.0) -> AttackScoreManager:
    """Get the singleton AttackScoreManager instance"""
    global _attack_score_manager

    if _attack_score_manager is None:
        _attack_score_manager = AttackScoreManager(update_interval=update_interval)

    return _attack_score_manager
