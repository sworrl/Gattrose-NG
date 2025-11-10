"""
IMSI Catcher Detection Module
Uses Rayhunter-inspired heuristics to detect cellular network anomalies
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import json
from pathlib import Path


@dataclass
class CellTowerInfo:
    """Cell tower information"""
    cell_id: int
    pci: Optional[int]
    mcc: int
    mnc: int
    network_type: str  # '5G', 'LTE', '3G', 'EDGE', 'GPRS'
    signal_strength: int  # dBm (RSRP for LTE/5G)
    frequency: Optional[int]  # MHz
    timestamp: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class IMSICatcherAlert:
    """IMSI catcher detection alert"""
    alert_type: str  # 'rapid_tower_change', 'signal_anomaly', 'location_mismatch', etc.
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    confidence: float  # 0.0 to 1.0
    details: Dict
    recommended_action: str
    timestamp: datetime


class IMSICatcherDetector:
    """
    IMSI Catcher Detector using Rayhunter-inspired heuristics

    Detection methods:
    1. Rapid tower changes (multiple changes in short time)
    2. Signal strength anomalies (too strong for distance)
    3. Downlink frequency anomalies
    4. LAC (Location Area Code) changes without movement
    5. Network downgrade attacks (5G/LTE → 3G/2G)
    6. Multiple PCI conflicts
    7. Timing advance anomalies
    """

    def __init__(self):
        self.tower_history = []  # List of CellTowerInfo objects
        self.observation_window = timedelta(minutes=15)
        self.max_history = 100

        # Thresholds
        self.rapid_change_threshold = 5  # Tower changes in window
        self.rapid_change_window = timedelta(minutes=5)
        self.signal_too_strong_threshold = -40  # dBm (suspiciously strong)
        self.tower_distance_threshold_km = 0.5  # Minimum distance to be considered moved

    def record_tower_observation(self, tower: CellTowerInfo):
        """Record a cell tower observation"""
        self.tower_history.append(tower)

        # Trim old observations
        cutoff = datetime.now() - self.observation_window
        self.tower_history = [t for t in self.tower_history if t.timestamp > cutoff]

        # Limit history size
        if len(self.tower_history) > self.max_history:
            self.tower_history = self.tower_history[-self.max_history:]

    def analyze_tower_change(self, new_tower: CellTowerInfo, old_tower: CellTowerInfo) -> List[IMSICatcherAlert]:
        """
        Analyze a tower change for IMSI catcher indicators
        Returns list of alerts (can be empty if no threats detected)
        """
        alerts = []

        # 1. Check for rapid tower changes
        rapid_alert = self._check_rapid_tower_changes(new_tower)
        if rapid_alert:
            alerts.append(rapid_alert)

        # 2. Check signal strength anomalies
        signal_alert = self._check_signal_anomalies(new_tower, old_tower)
        if signal_alert:
            alerts.append(signal_alert)

        # 3. Check for suspicious network downgrade
        downgrade_alert = self._check_network_downgrade(new_tower, old_tower)
        if downgrade_alert:
            alerts.append(downgrade_alert)

        # 4. Check for location/tower mismatch
        location_alert = self._check_location_mismatch(new_tower, old_tower)
        if location_alert:
            alerts.append(location_alert)

        # 5. Check for PCI conflicts
        pci_alert = self._check_pci_conflicts(new_tower)
        if pci_alert:
            alerts.append(pci_alert)

        return alerts

    def _check_rapid_tower_changes(self, new_tower: CellTowerInfo) -> Optional[IMSICatcherAlert]:
        """Detect abnormally frequent tower changes"""
        recent_window = datetime.now() - self.rapid_change_window
        recent_towers = [t for t in self.tower_history if t.timestamp > recent_window]

        # Count unique cell IDs
        unique_cells = set(t.cell_id for t in recent_towers)

        if len(unique_cells) >= self.rapid_change_threshold:
            confidence = min(1.0, len(unique_cells) / 10.0)

            return IMSICatcherAlert(
                alert_type='rapid_tower_change',
                severity='high' if len(unique_cells) >= 7 else 'medium',
                message=f'Rapid tower changes detected: {len(unique_cells)} towers in {self.rapid_change_window.seconds // 60} minutes',
                confidence=confidence,
                details={
                    'unique_towers': len(unique_cells),
                    'window_minutes': self.rapid_change_window.seconds // 60,
                    'tower_ids': list(unique_cells)
                },
                recommended_action='Disable mobile data and enable airplane mode. Move to different location.',
                timestamp=datetime.now()
            )

        return None

    def _check_signal_anomalies(self, new_tower: CellTowerInfo, old_tower: CellTowerInfo) -> Optional[IMSICatcherAlert]:
        """Detect suspiciously strong signals (possible nearby IMSI catcher)"""
        if new_tower.signal_strength > self.signal_too_strong_threshold:
            # Signal is unusually strong
            confidence = min(1.0, abs(new_tower.signal_strength + 40) / 30.0)

            return IMSICatcherAlert(
                alert_type='signal_anomaly',
                severity='medium',
                message=f'Unusually strong cell signal detected: {new_tower.signal_strength} dBm',
                confidence=confidence,
                details={
                    'signal_strength': new_tower.signal_strength,
                    'threshold': self.signal_too_strong_threshold,
                    'cell_id': new_tower.cell_id
                },
                recommended_action='Monitor for other anomalies. Strong signal may indicate nearby cell tower or IMSI catcher.',
                timestamp=datetime.now()
            )

        # Check for sudden large signal change without movement
        if old_tower and abs(new_tower.signal_strength - old_tower.signal_strength) > 30:
            # Large signal change (>30 dBm) is suspicious if location didn't change much
            if new_tower.latitude and old_tower.latitude:
                distance_km = self._calculate_distance(
                    old_tower.latitude, old_tower.longitude,
                    new_tower.latitude, new_tower.longitude
                )

                if distance_km < self.tower_distance_threshold_km:
                    return IMSICatcherAlert(
                        alert_type='signal_jump',
                        severity='medium',
                        message=f'Large signal change ({abs(new_tower.signal_strength - old_tower.signal_strength)} dBm) without significant movement',
                        confidence=0.6,
                        details={
                            'old_signal': old_tower.signal_strength,
                            'new_signal': new_tower.signal_strength,
                            'distance_km': round(distance_km, 3)
                        },
                        recommended_action='Monitor network behavior. May indicate nearby IMSI catcher activation.',
                        timestamp=datetime.now()
                    )

        return None

    def _check_network_downgrade(self, new_tower: CellTowerInfo, old_tower: CellTowerInfo) -> Optional[IMSICatcherAlert]:
        """Detect forced network downgrades (downgrade attack)"""
        type_priority = {'5G': 5, 'LTE': 4, '3G': 3, 'EDGE': 2, 'GPRS': 1, 'Unknown': 0}
        old_priority = type_priority.get(old_tower.network_type, 0)
        new_priority = type_priority.get(new_tower.network_type, 0)

        # Downgrade from 5G/LTE to 3G or lower is suspicious
        if old_priority >= 4 and new_priority <= 3:
            severity = 'high' if new_priority <= 2 else 'medium'
            confidence = 0.5 + (old_priority - new_priority) * 0.1

            return IMSICatcherAlert(
                alert_type='network_downgrade',
                severity=severity,
                message=f'Suspicious network downgrade: {old_tower.network_type} → {new_tower.network_type}',
                confidence=min(1.0, confidence),
                details={
                    'old_network': old_tower.network_type,
                    'new_network': new_tower.network_type,
                    'downgrade_levels': old_priority - new_priority
                },
                recommended_action='IMSI catchers often force 2G/3G connections. Enable "LTE/5G only" mode if available.',
                timestamp=datetime.now()
            )

        return None

    def _check_location_mismatch(self, new_tower: CellTowerInfo, old_tower: CellTowerInfo) -> Optional[IMSICatcherAlert]:
        """Detect tower change without GPS movement (possible fake tower)"""
        if not (new_tower.latitude and old_tower.latitude):
            return None  # Need GPS data

        distance_km = self._calculate_distance(
            old_tower.latitude, old_tower.longitude,
            new_tower.latitude, new_tower.longitude
        )

        # Tower changed but device didn't move much
        if distance_km < self.tower_distance_threshold_km and new_tower.cell_id != old_tower.cell_id:
            return IMSICatcherAlert(
                alert_type='location_mismatch',
                severity='high',
                message=f'Cell tower changed without movement (distance: {distance_km:.3f} km)',
                confidence=0.7,
                details={
                    'distance_km': round(distance_km, 3),
                    'old_cell': old_tower.cell_id,
                    'new_cell': new_tower.cell_id,
                    'time_delta_seconds': (new_tower.timestamp - old_tower.timestamp).seconds
                },
                recommended_action='HIGH RISK: Tower change without movement strongly indicates IMSI catcher. Disable mobile data immediately.',
                timestamp=datetime.now()
            )

        return None

    def _check_pci_conflicts(self, new_tower: CellTowerInfo) -> Optional[IMSICatcherAlert]:
        """Detect Physical Cell ID conflicts (same PCI, different cell ID)"""
        if not new_tower.pci:
            return None

        # Look for same PCI with different cell ID in recent history
        recent_window = datetime.now() - timedelta(minutes=10)
        recent_towers = [t for t in self.tower_history if t.timestamp > recent_window and t.pci]

        conflicts = [t for t in recent_towers if t.pci == new_tower.pci and t.cell_id != new_tower.cell_id]

        if conflicts:
            return IMSICatcherAlert(
                alert_type='pci_conflict',
                severity='medium',
                message=f'PCI conflict detected: Same PCI ({new_tower.pci}) used by multiple cell IDs',
                confidence=0.6,
                details={
                    'pci': new_tower.pci,
                    'conflicting_cells': [t.cell_id for t in conflicts],
                    'current_cell': new_tower.cell_id
                },
                recommended_action='PCI reuse can indicate legitimate network or spoofed tower. Monitor other indicators.',
                timestamp=datetime.now()
            )

        return None

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in kilometers (Haversine formula)"""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371.0  # Earth radius in kilometers

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = sin(delta_lat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def get_statistics(self) -> Dict:
        """Get detector statistics"""
        return {
            'observations_count': len(self.tower_history),
            'unique_towers': len(set(t.cell_id for t in self.tower_history)),
            'network_types': list(set(t.network_type for t in self.tower_history)),
            'window_minutes': self.observation_window.seconds // 60
        }


# Global detector instance
_detector_instance = None


def get_detector() -> IMSICatcherDetector:
    """Get or create the global detector instance"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = IMSICatcherDetector()
    return _detector_instance
