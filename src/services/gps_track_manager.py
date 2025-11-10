"""
GPS Track Manager
Manages GPS observations with smart duplicate detection and movement state tracking
Prevents database bloat from stationary wardriving
"""

import math
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta


class GPSTrackManager:
    """
    Intelligent GPS track point management
    - Detects when user is stationary, walking, or driving
    - Prevents duplicate observations at same location
    - Optimizes database storage while preserving triangulation accuracy
    """

    # Movement thresholds
    STATIONARY_THRESHOLD_MPS = 0.5  # < 0.5 m/s = stationary
    WALKING_THRESHOLD_MPS = 2.0     # < 2.0 m/s = walking
    DRIVING_THRESHOLD_MPS = 5.0     # > 5.0 m/s = driving

    # Duplicate detection distances (meters)
    MIN_DISTANCE_STATIONARY = 3.0    # 3m minimum movement when stationary
    MIN_DISTANCE_WALKING = 10.0      # 10m minimum movement when walking
    MIN_DISTANCE_DRIVING = 30.0      # 30m minimum movement when driving

    # Time thresholds for same network (seconds)
    MIN_TIME_STATIONARY = 60        # 1 minute between observations when stationary
    MIN_TIME_WALKING = 30           # 30 seconds when walking
    MIN_TIME_DRIVING = 10           # 10 seconds when driving

    def __init__(self):
        """Initialize track manager"""
        self._last_location: Optional[Tuple[float, float]] = None
        self._last_location_time: Optional[datetime] = None
        self._movement_state: str = 'unknown'  # 'stationary', 'walking', 'driving', 'unknown'
        self._speed_mps: float = 0.0
        self._last_observation_cache: Dict[int, Tuple[float, float, datetime]] = {}  # network_id -> (lat, lon, time)

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula

        Returns:
            Distance in meters
        """
        R = 6371000  # Earth radius in meters

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = math.sin(delta_lat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def update_location(self, latitude: float, longitude: float) -> Dict:
        """
        Update current GPS location and calculate movement state

        Args:
            latitude: Current latitude
            longitude: Current longitude

        Returns:
            Dict with movement analysis: {
                'moved': bool,
                'distance_m': float,
                'speed_mps': float,
                'movement_state': str,
                'time_delta_s': float
            }
        """
        now = datetime.utcnow()
        result = {
            'moved': False,
            'distance_m': 0.0,
            'speed_mps': 0.0,
            'movement_state': 'unknown',
            'time_delta_s': 0.0
        }

        if self._last_location is None:
            # First location
            self._last_location = (latitude, longitude)
            self._last_location_time = now
            self._movement_state = 'unknown'
            result['movement_state'] = 'unknown'
            return result

        # Calculate movement
        last_lat, last_lon = self._last_location
        distance_m = self.calculate_distance(last_lat, last_lon, latitude, longitude)

        # Calculate speed
        time_delta = (now - self._last_location_time).total_seconds()
        if time_delta > 0:
            speed_mps = distance_m / time_delta
        else:
            speed_mps = 0.0

        # Determine movement state
        if speed_mps < self.STATIONARY_THRESHOLD_MPS:
            movement_state = 'stationary'
        elif speed_mps < self.WALKING_THRESHOLD_MPS:
            movement_state = 'walking'
        elif speed_mps < self.DRIVING_THRESHOLD_MPS:
            movement_state = 'driving-slow'
        else:
            movement_state = 'driving-fast'

        # Determine if moved significantly based on state
        min_distance = self.MIN_DISTANCE_STATIONARY
        if movement_state == 'walking':
            min_distance = self.MIN_DISTANCE_WALKING
        elif 'driving' in movement_state:
            min_distance = self.MIN_DISTANCE_DRIVING

        moved = distance_m >= min_distance

        # Update state
        if moved:
            self._last_location = (latitude, longitude)
            self._last_location_time = now

        self._movement_state = movement_state
        self._speed_mps = speed_mps

        result.update({
            'moved': moved,
            'distance_m': distance_m,
            'speed_mps': speed_mps,
            'movement_state': movement_state,
            'time_delta_s': time_delta
        })

        return result

    def should_create_observation(self, network_id: int, latitude: float, longitude: float) -> Tuple[bool, str]:
        """
        Determine if a new observation should be created for a network

        Args:
            network_id: Database ID of the network
            latitude: Current GPS latitude
            longitude: Current GPS longitude

        Returns:
            Tuple of (should_create: bool, reason: str)
        """
        now = datetime.utcnow()

        # Check if we have a recent observation for this network
        if network_id in self._last_observation_cache:
            last_lat, last_lon, last_time = self._last_observation_cache[network_id]

            # Calculate distance from last observation
            distance_m = self.calculate_distance(last_lat, last_lon, latitude, longitude)
            time_delta_s = (now - last_time).total_seconds()

            # Get thresholds based on movement state
            if self._movement_state == 'stationary':
                min_distance = self.MIN_DISTANCE_STATIONARY
                min_time = self.MIN_TIME_STATIONARY
            elif self._movement_state == 'walking':
                min_distance = self.MIN_DISTANCE_WALKING
                min_time = self.MIN_TIME_WALKING
            elif 'driving' in self._movement_state:
                min_distance = self.MIN_DISTANCE_DRIVING
                min_time = self.MIN_TIME_DRIVING
            else:
                # Unknown state - be conservative
                min_distance = self.MIN_DISTANCE_WALKING
                min_time = self.MIN_TIME_WALKING

            # Check if we've moved enough or enough time has passed
            if distance_m < min_distance and time_delta_s < min_time:
                return (False, f"duplicate ({self._movement_state}, {distance_m:.1f}m, {time_delta_s:.0f}s)")

        # Create observation and cache it
        self._last_observation_cache[network_id] = (latitude, longitude, now)
        return (True, "new location")

    def get_movement_state(self) -> Dict:
        """
        Get current movement state

        Returns:
            Dict with: {
                'state': str,
                'speed_mps': float,
                'speed_kmh': float,
                'speed_mph': float
            }
        """
        return {
            'state': self._movement_state,
            'speed_mps': self._speed_mps,
            'speed_kmh': self._speed_mps * 3.6,
            'speed_mph': self._speed_mps * 2.237
        }

    def cleanup_cache(self, max_age_seconds: int = 3600):
        """
        Clean up old entries from observation cache

        Args:
            max_age_seconds: Maximum age of cache entries (default 1 hour)
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=max_age_seconds)

        # Remove old entries
        old_keys = [
            network_id for network_id, (_, _, timestamp) in self._last_observation_cache.items()
            if timestamp < cutoff
        ]

        for key in old_keys:
            del self._last_observation_cache[key]

        if old_keys:
            print(f"[GPS-TRACK] Cleaned {len(old_keys)} old observation cache entries")
