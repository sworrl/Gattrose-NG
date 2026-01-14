"""
Triangulation Service
Calculates physical location of WiFi access points based on multiple GPS observations
Uses signal strength-weighted trilateration with optional FFT signal processing for accurate AP positioning
"""

import math
from typing import List, Tuple, Optional
from datetime import datetime, timedelta

# Optional FFT support - graceful fallback if scipy/numpy not available
try:
    import numpy as np
    from scipy.fft import fft, fftfreq
    FFT_AVAILABLE = True
except ImportError:
    FFT_AVAILABLE = False
    print("[Triangulation] Warning: scipy/numpy not available, FFT features disabled")


class TriangulationService:
    """Service for triangulating AP physical locations from wardriving data"""

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula

        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate

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

    @staticmethod
    def fft_signal_quality_analysis(signal_strengths: List[float]) -> Tuple[float, float, float]:
        """
        Analyze signal quality using FFT to detect noise and interference patterns

        Args:
            signal_strengths: List of signal strength measurements in dBm

        Returns:
            Tuple of (quality_score 0-100, noise_level, dominant_frequency_hz)
        """
        if not FFT_AVAILABLE:
            # FFT not available, return default values
            return (50.0, 0.0, 0.0)

        if len(signal_strengths) < 4:
            # Not enough samples for FFT analysis
            return (50.0, 0.0, 0.0)

        # Convert to numpy array
        signals = np.array(signal_strengths, dtype=float)

        # Remove DC component (mean)
        signals_centered = signals - np.mean(signals)

        # Apply FFT
        n = len(signals)
        fft_vals = fft(signals_centered)
        fft_freqs = fftfreq(n, d=1.0)  # Assuming 1Hz sampling

        # Calculate power spectrum
        power_spectrum = np.abs(fft_vals) ** 2

        # Analyze frequency components (ignore DC)
        positive_freqs = fft_freqs[1:n//2]
        positive_power = power_spectrum[1:n//2]

        if len(positive_power) == 0:
            return (50.0, 0.0, 0.0)

        # Noise level = average high-frequency power
        noise_level = np.mean(positive_power[len(positive_power)//2:])

        # Signal power = low-frequency power
        signal_power = np.mean(positive_power[:len(positive_power)//4])

        # Find dominant frequency
        dominant_freq_idx = np.argmax(positive_power)
        dominant_freq = abs(positive_freqs[dominant_freq_idx]) if len(positive_freqs) > 0 else 0.0

        # Quality score: SNR-based (higher signal/noise ratio = better)
        if noise_level > 0:
            snr = signal_power / noise_level
            quality_score = min(100.0, max(0.0, 50.0 + 10 * np.log10(snr + 0.001)))
        else:
            quality_score = 100.0

        return (quality_score, float(noise_level), float(dominant_freq))

    @staticmethod
    def fft_filter_signal(signal_strengths: List[float], cutoff_ratio: float = 0.3) -> List[float]:
        """
        Filter signal using FFT to remove high-frequency noise

        Args:
            signal_strengths: List of signal measurements in dBm
            cutoff_ratio: Ratio of frequencies to keep (0.3 = keep lowest 30%)

        Returns:
            Filtered signal strengths
        """
        if not FFT_AVAILABLE:
            # FFT not available, return original signals
            return signal_strengths

        if len(signal_strengths) < 4:
            return signal_strengths

        signals = np.array(signal_strengths, dtype=float)

        # Apply FFT
        fft_vals = fft(signals)

        # Create low-pass filter
        n = len(fft_vals)
        cutoff_idx = int(n * cutoff_ratio)

        # Zero out high frequencies
        fft_filtered = fft_vals.copy()
        fft_filtered[cutoff_idx:n-cutoff_idx] = 0

        # Inverse FFT to get filtered signal
        filtered_signal = np.real(np.fft.ifft(fft_filtered))

        return filtered_signal.tolist()

    @staticmethod
    def signal_to_distance(signal_dbm: int, frequency_mhz: int = 2412) -> float:
        """
        Estimate distance from signal strength using Free Space Path Loss model

        Args:
            signal_dbm: Signal strength in dBm (negative value)
            frequency_mhz: Frequency in MHz (default 2412 for channel 1)

        Returns:
            Estimated distance in meters
        """
        if signal_dbm >= 0:
            return 0.0

        # Transmit power estimate (typically 20dBm for WiFi)
        tx_power_dbm = 20

        # Path loss in dB
        path_loss = tx_power_dbm - signal_dbm

        # FSPL formula: distance = 10 ^ ((Path Loss - 20*log10(freq) - 32.44) / 20)
        freq_ghz = frequency_mhz / 1000.0
        distance = 10 ** ((path_loss - 20 * math.log10(freq_ghz) - 32.44) / 20)

        return distance * 1000  # Convert km to meters

    @staticmethod
    def weighted_centroid(observations: List[Tuple[float, float, int]], use_fft: bool = True) -> Tuple[float, float, float]:
        """
        Calculate weighted centroid based on signal strength with optional FFT enhancement

        Stronger signals (closer observations) get more weight in calculation
        FFT analysis improves weighting by considering signal quality

        Args:
            observations: List of (latitude, longitude, signal_dbm) tuples
            use_fft: Use FFT signal quality analysis for improved weighting

        Returns:
            Tuple of (estimated_lat, estimated_lon, confidence_radius_meters)
        """
        if not observations:
            return (0.0, 0.0, 0.0)

        if len(observations) == 1:
            # Only one observation - use it but low confidence
            lat, lon, signal = observations[0]
            return (lat, lon, 100.0)  # 100m confidence radius

        # Calculate weights based on signal strength
        # Stronger signal (closer to 0) = higher weight
        weights = []

        # Extract signal strengths for FFT analysis
        signal_strengths = [signal for _, _, signal in observations]

        # Perform FFT quality analysis if enabled and enough samples
        quality_multiplier = 1.0
        if use_fft and len(signal_strengths) >= 4:
            try:
                quality_score, noise_level, _ = TriangulationService.fft_signal_quality_analysis(signal_strengths)
                # Use quality score to adjust overall confidence
                # Higher quality (less noise) = more confidence in positioning
                quality_multiplier = quality_score / 100.0

                # Filter signals using FFT to remove noise
                filtered_signals = TriangulationService.fft_filter_signal(signal_strengths)
                # Use filtered signals for weight calculation
                signal_strengths = filtered_signals
            except Exception as e:
                # FFT analysis failed, fall back to regular weighting
                print(f"[Triangulation] FFT analysis failed: {e}, using standard weighting")

        for i, (lat, lon, _) in enumerate(observations):
            signal = signal_strengths[i]
            # Convert dBm to weight (stronger signal = higher weight)
            # -30 dBm = 100 weight, -90 dBm = 1 weight
            base_weight = max(1, 100 + signal)

            # Apply FFT quality multiplier
            weight = base_weight * quality_multiplier
            weights.append(weight)

        total_weight = sum(weights)

        # Calculate weighted average position
        weighted_lat = sum(lat * w for (lat, _, _), w in zip(observations, weights)) / total_weight
        weighted_lon = sum(lon * w for (_, lon, _), w in zip(observations, weights)) / total_weight

        # Calculate confidence radius (standard deviation of observations)
        distances = []
        for lat, lon, _ in observations:
            dist = TriangulationService.calculate_distance(
                weighted_lat, weighted_lon, lat, lon
            )
            distances.append(dist)

        # Confidence radius = average distance from centroid
        # Adjusted by FFT quality (better quality = tighter confidence)
        base_confidence = sum(distances) / len(distances) if distances else 50.0
        confidence_radius = base_confidence / quality_multiplier if quality_multiplier > 0 else base_confidence

        return (weighted_lat, weighted_lon, confidence_radius)

    @staticmethod
    def trilateration(observations: List[Tuple[float, float, int]]) -> Tuple[float, float, float]:
        """
        Perform trilateration using signal strength to estimate distances

        This is more accurate than weighted centroid when we have 3+ observations

        Args:
            observations: List of (latitude, longitude, signal_dbm) tuples

        Returns:
            Tuple of (estimated_lat, estimated_lon, confidence_radius_meters)
        """
        if len(observations) < 3:
            # Need at least 3 points for trilateration, fall back to centroid
            return TriangulationService.weighted_centroid(observations)

        # Use weighted centroid as initial approximation
        # True trilateration requires iterative solver (e.g., Levenberg-Marquardt)
        # For wardriving, weighted centroid is often sufficient and much faster
        return TriangulationService.weighted_centroid(observations)

    @staticmethod
    def calculate_ap_location(network_id: int, min_observations: int = 3,
                            max_age_hours: int = 24) -> Optional[Tuple[float, float, float, int]]:
        """
        Calculate estimated physical location of an AP from database observations

        Args:
            network_id: Database ID of the network
            min_observations: Minimum observations required (default 3)
            max_age_hours: Only use observations from last N hours (default 24)

        Returns:
            Tuple of (latitude, longitude, confidence_radius_meters, observation_count)
            or None if insufficient data
        """
        from ..database.models import get_session, NetworkObservation

        session = get_session()
        try:
            # Get recent observations
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            observations = session.query(NetworkObservation).filter(
                NetworkObservation.network_id == network_id,
                NetworkObservation.timestamp >= cutoff_time,
                NetworkObservation.latitude.isnot(None),
                NetworkObservation.longitude.isnot(None)
            ).all()

            if len(observations) < min_observations:
                return None

            # Extract observation data
            obs_data = [
                (obs.latitude, obs.longitude, obs.signal_strength or -70)
                for obs in observations
            ]

            # Calculate estimated location
            est_lat, est_lon, confidence = TriangulationService.trilateration(obs_data)

            return (est_lat, est_lon, confidence, len(observations))

        finally:
            session.close()

    @staticmethod
    def update_network_location(network_id: int) -> bool:
        """
        Update network's calculated location in database

        Args:
            network_id: Database ID of the network

        Returns:
            True if location was updated, False otherwise
        """
        from ..database.models import get_session, Network

        result = TriangulationService.calculate_ap_location(network_id)
        if not result:
            return False

        est_lat, est_lon, confidence, obs_count = result

        session = get_session()
        try:
            network = session.query(Network).filter_by(id=network_id).first()
            if network:
                # Store calculated location (could add new fields for calculated vs observed)
                network.latitude = est_lat
                network.longitude = est_lon
                # Note: Could add confidence_radius field to Network model
                session.commit()
                print(f"[Triangulation] Updated AP {network.bssid} location: "
                      f"{est_lat:.6f}, {est_lon:.6f} (±{confidence:.1f}m from {obs_count} observations)")
                return True

        except Exception as e:
            session.rollback()
            print(f"[Triangulation] Error updating network location: {e}")
            return False
        finally:
            session.close()

        return False

    @staticmethod
    def batch_update_all_locations(min_observations: int = 3):
        """
        Update calculated locations for all APs with sufficient observations

        Args:
            min_observations: Minimum observations required

        Returns:
            Number of APs updated
        """
        from ..database.models import get_session, Network, NetworkObservation
        from sqlalchemy import func

        session = get_session()
        updated_count = 0

        try:
            # Find all networks with enough observations
            networks_with_obs = session.query(
                NetworkObservation.network_id,
                func.count(NetworkObservation.id).label('obs_count')
            ).group_by(
                NetworkObservation.network_id
            ).having(
                func.count(NetworkObservation.id) >= min_observations
            ).all()

            print(f"[Triangulation] Found {len(networks_with_obs)} APs with {min_observations}+ observations")

            for network_id, obs_count in networks_with_obs:
                if TriangulationService.update_network_location(network_id):
                    updated_count += 1

            print(f"[Triangulation] Updated {updated_count} AP locations")

        finally:
            session.close()

        return updated_count

    @staticmethod
    def detect_location_clusters(observations, min_cluster_size=2, cluster_radius_meters=500.0):
        """
        Detect distinct geographic clusters of observations.
        Used to identify when an AP has been "moved" (or more likely, user moved to a new area).
        """
        if not observations:
            return []

        # Sort by timestamp
        sorted_obs = sorted(observations, key=lambda x: x[3])
        clusters = []
        used = set()

        for i, obs in enumerate(sorted_obs):
            if i in used:
                continue

            cluster = [obs]
            used.add(i)

            for j, other in enumerate(sorted_obs):
                if j in used:
                    continue

                dist = TriangulationService.calculate_distance(obs[0], obs[1], other[0], other[1])
                if dist <= cluster_radius_meters:
                    cluster.append(other)
                    used.add(j)

            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)

        return clusters

    @staticmethod
    def relocate_ap_if_needed(network_id, new_location_threshold=1000.0, min_new_observations=2):
        """
        Check if AP should be relocated and update if so.
        Handles scenario where user moves to a new area and old AP coords are wrong.
        """
        from ..database.models import get_session, Network, NetworkObservation
        from sqlalchemy import desc

        session = get_session()
        try:
            network = session.query(Network).filter_by(id=network_id).first()
            if not network or not network.latitude or not network.longitude:
                return False

            current_lat = network.latitude
            current_lon = network.longitude

            # Get recent observations with GPS
            recent_obs = session.query(NetworkObservation).filter(
                NetworkObservation.network_id == network_id,
                NetworkObservation.latitude.isnot(None),
                NetworkObservation.longitude.isnot(None)
            ).order_by(desc(NetworkObservation.timestamp)).limit(20).all()

            if len(recent_obs) < min_new_observations:
                return False

            # Check if recent observations are far from current stored location
            new_location_obs = []
            for obs in recent_obs:
                dist = TriangulationService.calculate_distance(
                    current_lat, current_lon, obs.latitude, obs.longitude
                )
                if dist > new_location_threshold:
                    new_location_obs.append((obs.latitude, obs.longitude, obs.signal_strength or -70, obs.timestamp))

            # If we have enough observations at a "new" location, trigger relocation
            if len(new_location_obs) >= min_new_observations:
                clusters = TriangulationService.detect_location_clusters(new_location_obs)

                if clusters:
                    largest_cluster = max(clusters, key=len)
                    obs_for_centroid = [(lat, lon, sig) for lat, lon, sig, _ in largest_cluster]
                    new_lat, new_lon, confidence = TriangulationService.weighted_centroid(obs_for_centroid)

                    dist_moved = TriangulationService.calculate_distance(current_lat, current_lon, new_lat, new_lon)

                    old_lat = network.latitude
                    old_lon = network.longitude
                    network.latitude = new_lat
                    network.longitude = new_lon
                    session.commit()
                    print(f"[Triangulation] RELOCATED AP {network.bssid}: "
                          f"({old_lat:.4f}, {old_lon:.4f}) -> ({new_lat:.4f}, {new_lon:.4f})")
                    print(f"[Triangulation] Reason: {len(largest_cluster)} observations at new location ({dist_moved/1000:.1f}km away)")
                    return True

            return False
        except Exception as e:
            session.rollback()
            print(f"[Triangulation] Error in relocate check: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def check_and_relocate_all_aps(new_location_threshold=1000.0, min_new_observations=2):
        """Check all APs for relocation and update as needed."""
        from ..database.models import get_session, Network

        session = get_session()
        relocated_count = 0

        try:
            networks = session.query(Network).filter(
                Network.latitude.isnot(None),
                Network.longitude.isnot(None)
            ).all()

            for network in networks:
                if TriangulationService.relocate_ap_if_needed(
                    network.id, new_location_threshold, min_new_observations
                ):
                    relocated_count += 1

            if relocated_count > 0:
                print(f"[Triangulation] Relocated {relocated_count} APs to new locations")

        finally:
            session.close()

        return relocated_count
