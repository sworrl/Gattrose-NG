"""
Client Attack Scoring System
Evaluates individual clients for targeted attacks (deauth, MITM, etc.)
"""

from typing import Dict, Tuple


class ClientScorer:
    """
    Calculates attack ease scores for individual WiFi clients
    Higher score = Easier to attack / more valuable target (0-100 scale)
    """

    # Device type scores (higher = more valuable/easier)
    DEVICE_TYPE_SCORES = {
        'phone': 85,        # Phones - high value, often vulnerable
        'smartphone': 85,
        'tablet': 80,       # Tablets - similar to phones
        'laptop': 75,       # Laptops - valuable but more security aware
        'computer': 70,     # Desktop computers
        'iot': 90,          # IoT devices - often very vulnerable
        'camera': 88,       # IP cameras - notoriously insecure
        'tv': 82,           # Smart TVs
        'printer': 85,      # Printers - often insecure
        'speaker': 87,      # Smart speakers
        'watch': 78,        # Smartwatches
        'gaming': 75,       # Gaming consoles
        'unknown': 50,      # Unknown devices
    }

    # Manufacturer vulnerability scores (based on known security track record)
    MANUFACTURER_SCORES = {
        # High vulnerability manufacturers
        'Tp-Link': 10,
        'D-Link': 12,
        'Netgear': 8,
        'Xiaomi': 15,
        'Huawei': 14,
        'Belkin': 10,

        # IoT/Camera manufacturers (often vulnerable)
        'HikVision': 20,
        'Dahua': 20,
        'Wyze': 15,
        'Ring': 12,

        # Medium vulnerability
        'Samsung': 5,
        'LG': 5,
        'Sony': 3,

        # Lower vulnerability (better security)
        'Apple': -5,
        'Google': -3,
        'Microsoft': -2,

        # Unknown
        'Unknown': 0,
    }

    @staticmethod
    def calculate_client_score(mac: str, signal: int = -70, packets: int = 0,
                               manufacturer: str = '', device_type: str = 'unknown',
                               probes: list = None, associated_bssid: str = None,
                               data_rate: int = 0) -> Tuple[float, str]:
        """
        Calculate attack score for a client

        Args:
            mac: Client MAC address
            signal: Signal strength (dBm)
            packets: Number of packets seen
            manufacturer: Device manufacturer (from MAC OUI)
            device_type: Type of device
            probes: List of SSIDs the client is probing for
            associated_bssid: BSSID client is connected to
            data_rate: Estimated data throughput (KB/s)

        Returns:
            Tuple of (score, priority_level)
            score: 0.0-100.0 (higher = easier/more valuable target)
            priority_level: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
        """
        score = 50.0  # Base score

        # Device type score (primary factor)
        device_type_lower = device_type.lower()
        for key, value in ClientScorer.DEVICE_TYPE_SCORES.items():
            if key in device_type_lower:
                score = float(value)
                break

        # Manufacturer vulnerability bonus
        manufacturer_bonus = 0
        for key, value in ClientScorer.MANUFACTURER_SCORES.items():
            if key.lower() in manufacturer.lower():
                manufacturer_bonus = value
                break
        score += manufacturer_bonus

        # Signal strength (stronger = easier to attack)
        # -30 dBm (very strong) = +20 bonus
        # -70 dBm (medium) = +10 bonus
        # -90 dBm (weak) = 0 bonus
        if signal >= -30:
            signal_bonus = 20.0
        elif signal >= -50:
            # Linear from 20 to 15
            signal_bonus = 20.0 - ((abs(signal) - 30) * 0.25)
        elif signal >= -70:
            # Linear from 15 to 10
            signal_bonus = 15.0 - ((abs(signal) - 50) * 0.25)
        elif signal >= -90:
            # Linear from 10 to 0
            signal_bonus = 10.0 - ((abs(signal) - 70) * 0.5)
        else:
            signal_bonus = 0.0

        score += signal_bonus

        # Packet activity (more packets = more active = more valuable)
        # Also helps with attack success (more traffic to capture)
        if packets > 1000:
            packet_bonus = 15.0
        elif packets > 500:
            packet_bonus = 10.0
        elif packets > 100:
            packet_bonus = 5.0
        elif packets > 10:
            packet_bonus = 2.0
        else:
            packet_bonus = 0.0

        # Add fractional component for uniqueness
        packet_bonus += (packets % 100) / 1000.0
        score += packet_bonus

        # Data throughput (higher = more valuable, indicates active use)
        if data_rate > 1000:  # > 1 MB/s
            data_bonus = 10.0
        elif data_rate > 500:  # > 500 KB/s
            data_bonus = 7.0
        elif data_rate > 100:  # > 100 KB/s
            data_bonus = 4.0
        elif data_rate > 10:   # > 10 KB/s
            data_bonus = 2.0
        else:
            data_bonus = 0.0

        # Add fractional for uniqueness
        data_bonus += (data_rate % 100) / 10000.0
        score += data_bonus

        # Probe requests (indicates client is searching for networks)
        # More probes = potentially easier to evil twin or redirect
        if probes and len(probes) > 0:
            probe_bonus = min(8.0, len(probes) * 1.5)  # Max 8 point bonus
            # Add fractional
            probe_bonus += (len(probes) % 10) / 100.0
            score += probe_bonus

        # Association status
        if associated_bssid:
            # Client is connected - can try deauth/MITM
            score += 5.0
        else:
            # Client is unassociated - potentially looking for network
            # Good target for evil twin
            score += 3.0

        # MAC address analysis (randomization detection)
        # Locally administered MACs (bit 1 of first octet set) = randomized
        try:
            first_octet = int(mac.split(':')[0], 16)
            if first_octet & 0x02:  # Check local bit
                # Randomized MAC - indicates privacy-aware device (potentially harder)
                score -= 5.0
            else:
                # Real MAC - potentially less security aware
                score += 2.0
        except:
            pass

        # Unique fractional component based on MAC address
        # Ensures virtually no two clients have exactly the same score
        try:
            mac_hash = sum(int(b, 16) for b in mac.split(':'))
            mac_fraction = (mac_hash % 1000) / 10000.0
            score += mac_fraction
        except:
            pass

        # Clamp to 0-100
        score = max(0.0, min(100.0, score))

        # Determine priority level
        if score >= 85:
            priority = 'CRITICAL'
        elif score >= 70:
            priority = 'HIGH'
        elif score >= 50:
            priority = 'MEDIUM'
        else:
            priority = 'LOW'

        return round(score, 2), priority

    @staticmethod
    def get_attack_recommendations(score: float, device_type: str,
                                   associated: bool) -> list:
        """
        Get recommended attack types for this client

        Returns:
            List of recommended attack strings
        """
        recommendations = []

        if score >= 85:
            if associated:
                recommendations.append("Deauth + Evil Twin")
                recommendations.append("MITM Attack")
                recommendations.append("Packet Capture")
            else:
                recommendations.append("Evil Twin")
                recommendations.append("Karma Attack")

            # IoT-specific attacks
            if 'iot' in device_type.lower() or 'camera' in device_type.lower():
                recommendations.append("Exploit Known CVEs")
                recommendations.append("Default Credentials")

        elif score >= 70:
            if associated:
                recommendations.append("Deauth Attack")
                recommendations.append("Handshake Capture")
            else:
                recommendations.append("Probe Response")

        elif score >= 50:
            if associated:
                recommendations.append("Passive Monitoring")
                recommendations.append("Handshake Capture")
            else:
                recommendations.append("Probe Monitoring")

        return recommendations

    @staticmethod
    def get_client_description(score: float, priority: str, device_type: str) -> str:
        """Get human-readable client description"""
        descriptions = {
            'CRITICAL': 'High-value target - Easy attack',
            'HIGH': 'Valuable target - Attackable',
            'MEDIUM': 'Moderate target - Possible',
            'LOW': 'Low-value target - Difficult'
        }

        desc = descriptions.get(priority, 'Unknown')

        if device_type and device_type != 'unknown':
            desc += f' [{device_type}]'

        return desc
