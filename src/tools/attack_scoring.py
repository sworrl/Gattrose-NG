"""
Attack Scoring System for WiFi Networks
Evaluates the ease of attack based on multiple factors
"""

from typing import Dict, Tuple


class AttackScorer:
    """
    Calculates attack difficulty scores for WiFi networks
    Higher score = Easier to attack (0-100 scale)
    """

    # Encryption scoring (higher = easier to attack)
    ENCRYPTION_SCORES = {
        'OPN': 100,      # Open networks - trivial
        'WEP': 95,       # WEP - easily crackable
        'WPA': 70,       # WPA - vulnerable
        'WPA2': 40,      # WPA2 - harder but possible
        'WPA3': 15,      # WPA3 - very difficult
        'WPA3 WPA2': 25, # Mixed mode - slightly easier than pure WPA3
        'WPA2 WPA': 50,  # Mixed mode - easier than pure WPA2
    }

    # Authentication scoring
    AUTH_SCORES = {
        'PSK': 0,        # Pre-shared key (standard)
        'SAE': -15,      # WPA3 SAE - more secure
        'MGT': -20,      # Enterprise (very secure)
        'SAE PSK': -5,   # Mixed SAE/PSK
    }

    # WPS bonus (if enabled, HUGE vulnerability)
    WPS_BONUS = 40

    # Signal strength multiplier (stronger = easier to attack)
    # Power values typically range from -30 (very strong) to -90 (very weak)
    @staticmethod
    def calculate_signal_bonus(power: str) -> float:
        """
        Calculate bonus based on signal strength using granular formula
        Returns a fractional score for maximum uniqueness
        """
        try:
            power_val = int(power.strip())
            # Use exponential formula for very granular scoring
            # Range: -30 (best) gets 20.0, -90 (worst) gets 0.0
            # Formula creates unique fractional values for each dBm
            if power_val >= -30:
                # Perfect signal: 20.0
                base = 20.0
            else:
                # Exponential decay from -30 to -90
                # This gives unique scores like 19.87, 15.42, 8.91, etc.
                normalized = (power_val + 90) / 60.0  # 0.0 to 1.0
                base = 20.0 * (normalized ** 1.5)  # Exponential curve

            # Add fractional component based on exact dBm value
            # This ensures almost every different signal has a unique score
            fractional = (abs(power_val) % 10) / 100.0
            return round(base + fractional, 3)
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def calculate_score(encryption: str, authentication: str = '',
                       power: str = '', wps_enabled: bool = False,
                       has_clients: bool = False, hidden: bool = False,
                       beacons: int = 0, channel: str = '', cipher: str = '') -> Tuple[float, str]:
        """
        Calculate attack score for a network with maximum granularity

        Returns:
            Tuple of (score, risk_level)
            score: 0.0-100.0 (higher = easier to attack, fractional for uniqueness)
            risk_level: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
        """
        score = 0.0

        # Base encryption score
        enc_key = encryption.strip().upper()
        for key, value in AttackScorer.ENCRYPTION_SCORES.items():
            if key in enc_key:
                score = float(value)
                break

        # If not found, try partial matches
        if score == 0.0:
            if 'WPA3' in enc_key:
                score = 15.0
            elif 'WPA2' in enc_key:
                score = 40.0
            elif 'WPA' in enc_key:
                score = 70.0
            elif 'WEP' in enc_key:
                score = 95.0
            else:
                score = 50.0  # Unknown encryption

        # Authentication modifier
        auth_key = authentication.strip().upper()
        for key, value in AttackScorer.AUTH_SCORES.items():
            if key in auth_key:
                score += value
                break

        # Cipher granularity (adds fractional component)
        cipher_key = cipher.strip().upper()
        cipher_bonus = 0.0
        if 'TKIP' in cipher_key:
            cipher_bonus = 0.5  # TKIP is weaker
        elif 'CCMP' in cipher_key:
            cipher_bonus = 0.0  # CCMP is standard
        score += cipher_bonus

        # WPS vulnerability (MASSIVE bonus)
        if wps_enabled:
            score += AttackScorer.WPS_BONUS
            score = min(100.0, score)  # Cap at 100

        # Signal strength bonus (granular fractional)
        signal_bonus = AttackScorer.calculate_signal_bonus(power)
        score += signal_bonus

        # Active clients bonus (indicates active use, good for handshake capture)
        # Networks with clients are MUCH more valuable targets
        if has_clients:
            score += 15.0

        # Hidden SSID penalty (slightly harder to attack)
        if hidden:
            score -= 3.0

        # Beacons count (more beacons = more observable = slightly easier)
        # Adds tiny fractional component for uniqueness
        if beacons > 0:
            beacon_bonus = min(2.0, beacons / 10.0)  # Max 2.0 bonus
            # Add fractional based on exact beacon count for uniqueness
            beacon_fraction = (beacons % 100) / 1000.0
            score += beacon_bonus + beacon_fraction

        # Channel factor (congested channels slightly easier - more traffic to analyze)
        # Channels 1, 6, 11 are most common (2.4GHz)
        try:
            ch = int(channel.strip()) if channel else 0
            if ch in [1, 6, 11]:
                score += 0.3  # Congested channel bonus
            elif ch > 0:
                # Add tiny fractional for uniqueness
                score += (ch % 10) / 100.0
        except (ValueError, AttributeError):
            pass

        # Clamp score to 0-100
        score = max(0.0, min(100.0, score))

        # Determine risk level
        if score >= 80:
            risk_level = 'CRITICAL'
        elif score >= 60:
            risk_level = 'HIGH'
        elif score >= 35:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        # Round to 2 decimal places for display while maintaining uniqueness
        return round(score, 2), risk_level

    @staticmethod
    def get_score_color(score: int) -> Tuple[int, int, int]:
        """
        Get RGB color based on attack score
        Uses full 24-bit color gradient from dark purple (secure) to gold (vulnerable)

        Gradient: Dark Purple (0) -> Blue (20) -> Cyan (35) -> Green (50) ->
                  Yellow-Green (65) -> Yellow (80) -> Gold (90) -> Bright Gold (100)

        Returns:
            Tuple of (R, G, B) values (0-255)
        """
        # Normalize score to 0-1 range
        normalized = score / 100.0

        if score >= 90:
            # 90-100: Bright Gold with warm tones (CRITICAL - perfect target)
            # Gold = RGB(255, 215, 0) to Bright Gold RGB(255, 223, 0)
            r = 255
            g = int(215 + (score - 90) * 0.8)  # 215 -> 223
            b = int(10 - (score - 90))  # 10 -> 0 (slight sparkle effect)
        elif score >= 80:
            # 80-89: Yellow to Gold (CRITICAL)
            # Yellow RGB(255, 255, 0) to Gold RGB(255, 215, 0)
            r = 255
            g = int(255 - ((score - 80) * 4))  # 255 -> 215
            b = int((score - 80) * 1)  # 0 -> 10
        elif score >= 65:
            # 65-79: Yellow-Green to Yellow (HIGH)
            # RGB(200, 255, 0) to RGB(255, 255, 0)
            r = int(200 + ((score - 65) * 3.67))  # 200 -> 255
            g = 255
            b = 0
        elif score >= 50:
            # 50-64: Green to Yellow-Green (HIGH)
            # RGB(50, 255, 50) to RGB(200, 255, 0)
            r = int(50 + ((score - 50) * 10.71))  # 50 -> 200
            g = 255
            b = int(50 - ((score - 50) * 3.57))  # 50 -> 0
        elif score >= 35:
            # 35-49: Cyan to Green (MEDIUM)
            # RGB(0, 255, 200) to RGB(50, 255, 50)
            r = int((score - 35) * 3.57)  # 0 -> 50
            g = 255
            b = int(200 - ((score - 35) * 10))  # 200 -> 50
        elif score >= 20:
            # 20-34: Blue to Cyan (LOW)
            # RGB(50, 100, 255) to RGB(0, 255, 200)
            r = int(50 - ((score - 20) * 3.57))  # 50 -> 0
            g = int(100 + ((score - 20) * 10.36))  # 100 -> 255
            b = int(255 - ((score - 20) * 3.93))  # 255 -> 200
        else:
            # 0-19: Dark Purple to Blue (LOW - very secure)
            # RGB(75, 0, 130) to RGB(50, 100, 255)
            r = int(75 - (score * 1.25))  # 75 -> 50
            g = int(score * 5)  # 0 -> 100
            b = int(130 + (score * 6.25))  # 130 -> 255

        # Ensure values are in valid range
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))

        return (r, g, b)

    @staticmethod
    def get_risk_description(score: int, risk_level: str, wps_enabled: bool) -> str:
        """Get human-readable risk description"""
        descriptions = {
            'CRITICAL': 'Extremely vulnerable - Easy target',
            'HIGH': 'High vulnerability - Attackable',
            'MEDIUM': 'Moderate security - Possible target',
            'LOW': 'Strong security - Difficult target'
        }

        desc = descriptions.get(risk_level, 'Unknown')

        if wps_enabled:
            desc += ' [WPS ENABLED!]'

        return desc

    @staticmethod
    def get_star_rating(score: float) -> Tuple[int, str]:
        """
        Get star rating and colored star icons based on attack score

        Returns:
            Tuple of (star_count, star_string)
            star_count: 0-5 stars
            star_string: Colored star emoji string
        """
        # Map score to 0-5 stars (higher score = more stars = easier to attack)
        if score >= 90:
            stars = 5  # ⭐⭐⭐⭐⭐ CRITICAL - perfect target
        elif score >= 75:
            stars = 4  # ⭐⭐⭐⭐ HIGH
        elif score >= 55:
            stars = 3  # ⭐⭐⭐ MEDIUM-HIGH
        elif score >= 35:
            stars = 2  # ⭐⭐ MEDIUM
        elif score >= 15:
            stars = 1  # ⭐ LOW-MEDIUM
        else:
            stars = 0  # No stars - very secure

        # Create colored star string
        # Use different Unicode star symbols with colors
        if score >= 90:
            # Gold/Yellow stars for CRITICAL (🌟 glowing star)
            star_str = "🌟" * stars
        elif score >= 75:
            # Orange stars for HIGH (⭐ medium star)
            star_str = "⭐" * stars
        elif score >= 55:
            # Yellow stars for MEDIUM-HIGH
            star_str = "⭐" * stars
        elif score >= 35:
            # White/Light stars for MEDIUM (✨ sparkle)
            star_str = "✨" * stars
        elif score >= 15:
            # Small stars for LOW
            star_str = "⭐" * stars
        else:
            # No stars or security shield for very secure
            star_str = "🛡️"  # Shield for very secure networks

        return stars, star_str
