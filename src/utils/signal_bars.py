"""
Signal strength visualization with 24-bit color gradients
Theme-aware signal bars that adapt colors per active theme
"""

from typing import Tuple


class SignalBars:
    """Generate colorful signal strength bars with theme-aware colors"""

    # Theme-specific color gradients (weak -> strong signal)
    # Format: (R, G, B) tuples for [weakest, weak, medium, strong, strongest]
    THEME_GRADIENTS = {
        'sonic': [
            (30, 30, 80),      # Dark blue (weak)
            (50, 100, 200),    # Blue
            (100, 150, 255),   # Bright blue
            (150, 200, 255),   # Light blue
            (200, 230, 255)    # Ice blue (strong)
        ],
        'mario': [
            (100, 0, 0),       # Dark red (weak)
            (180, 20, 20),     # Red
            (255, 100, 50),    # Orange-red
            (255, 180, 50),    # Orange
            (255, 220, 100)    # Yellow-orange (strong)
        ],
        'metroid': [
            (80, 0, 80),       # Dark purple (weak)
            (120, 40, 120),    # Purple
            (180, 80, 180),    # Light purple
            (220, 120, 220),   # Pink-purple
            (255, 160, 255)    # Bright pink (strong)
        ],
        'zelda': [
            (0, 60, 0),        # Dark green (weak)
            (40, 120, 40),     # Green
            (80, 180, 80),     # Light green
            (120, 220, 120),   # Bright green
            (180, 255, 180)    # Very bright green (strong)
        ],
        'dynamicNight': [
            (20, 20, 40),      # Dark blue-grey (weak)
            (60, 60, 100),     # Blue-grey
            (100, 100, 150),   # Medium blue-grey
            (140, 140, 200),   # Light blue-grey
            (180, 180, 240)    # Bright blue-grey (strong)
        ],
        'dynamicDay': [
            (80, 80, 40),      # Dark gold (weak)
            (140, 140, 60),    # Gold
            (200, 200, 80),    # Bright gold
            (240, 240, 120),   # Very bright gold
            (255, 255, 180)    # Pale gold (strong)
        ],
        'hacker': [
            (0, 40, 0),        # Dark green (weak)
            (0, 80, 0),        # Matrix green
            (0, 140, 0),       # Bright green
            (0, 200, 0),       # Very bright green
            (100, 255, 100)    # Neon green (strong)
        ],
        'default': [
            (60, 0, 0),        # Dark red (weak)
            (150, 50, 0),      # Orange-red
            (200, 150, 0),     # Yellow-orange
            (150, 200, 50),    # Yellow-green
            (50, 200, 50)      # Green (strong)
        ]
    }

    # Signal bar characters (from empty to full)
    BAR_CHARS = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']

    @staticmethod
    def get_signal_level(power_dbm: int) -> int:
        """
        Convert dBm to signal level (0-4)

        Args:
            power_dbm: Signal strength in dBm (e.g., -30 to -90)

        Returns:
            Signal level 0-4 (0=weakest, 4=strongest)
        """
        # Typical WiFi range: -30 dBm (excellent) to -90 dBm (barely usable)
        if power_dbm >= -30:
            return 4  # Excellent
        elif power_dbm >= -50:
            return 3  # Good
        elif power_dbm >= -67:
            return 2  # Fair
        elif power_dbm >= -80:
            return 1  # Weak
        else:
            return 0  # Very weak

    @staticmethod
    def interpolate_color(color1: Tuple[int, int, int],
                         color2: Tuple[int, int, int],
                         factor: float) -> Tuple[int, int, int]:
        """
        Interpolate between two RGB colors

        Args:
            color1: Start color (R, G, B)
            color2: End color (R, G, B)
            factor: Interpolation factor (0.0 to 1.0)

        Returns:
            Interpolated color (R, G, B)
        """
        r = int(color1[0] + (color2[0] - color1[0]) * factor)
        g = int(color1[1] + (color2[1] - color1[1]) * factor)
        b = int(color1[2] + (color2[2] - color1[2]) * factor)
        return (r, g, b)

    @staticmethod
    def get_signal_color(power_dbm: int, theme: str = 'default') -> Tuple[int, int, int]:
        """
        Get 24-bit RGB color for signal strength based on theme

        Args:
            power_dbm: Signal strength in dBm
            theme: Theme name

        Returns:
            RGB tuple (R, G, B) for signal strength
        """
        # Get theme gradient or default
        gradient = SignalBars.THEME_GRADIENTS.get(theme, SignalBars.THEME_GRADIENTS['default'])

        # Normalize power to 0.0-1.0 range (-90 to -30 dBm)
        normalized = max(0.0, min(1.0, (power_dbm + 90) / 60.0))

        # Map to gradient position (0-4)
        gradient_pos = normalized * (len(gradient) - 1)

        # Get surrounding colors
        lower_idx = int(gradient_pos)
        upper_idx = min(lower_idx + 1, len(gradient) - 1)

        # Interpolate between colors
        factor = gradient_pos - lower_idx
        return SignalBars.interpolate_color(gradient[lower_idx], gradient[upper_idx], factor)

    @staticmethod
    def generate_signal_bars(power_dbm: int, theme: str = 'default',
                           num_bars: int = 5, use_unicode: bool = True) -> str:
        """
        Generate colored signal bars for display

        Args:
            power_dbm: Signal strength in dBm
            theme: Theme name for color scheme
            num_bars: Number of bars to display (default: 5)
            use_unicode: Use unicode block characters (True) or ASCII (False)

        Returns:
            Colored signal bars string (HTML format for Qt)
        """
        level = SignalBars.get_signal_level(power_dbm)
        r, g, b = SignalBars.get_signal_color(power_dbm, theme)

        if use_unicode:
            # Use filled/empty unicode blocks
            filled = min(level + 1, num_bars)
            bars = '█' * filled + '░' * (num_bars - filled)
        else:
            # ASCII fallback
            filled = min(level + 1, num_bars)
            bars = '|' * filled + '.' * (num_bars - filled)

        # Return HTML-styled text for Qt labels
        return f'<span style="color: rgb({r}, {g}, {b});">{bars}</span>'

    @staticmethod
    def generate_signal_indicator(power_dbm: int, theme: str = 'default') -> str:
        """
        Generate a single-character signal indicator with gradient colors

        Args:
            power_dbm: Signal strength in dBm
            theme: Theme name

        Returns:
            Colored single-character indicator (HTML format)
        """
        level = SignalBars.get_signal_level(power_dbm)
        r, g, b = SignalBars.get_signal_color(power_dbm, theme)

        # Pick appropriate bar character based on level
        char_idx = min(level * 2, len(SignalBars.BAR_CHARS) - 1)
        char = SignalBars.BAR_CHARS[char_idx]

        return f'<span style="color: rgb({r}, {g}, {b}); font-size: 16px;">{char}</span>'

    @staticmethod
    def get_signal_quality_text(power_dbm: int) -> str:
        """
        Get human-readable signal quality text

        Args:
            power_dbm: Signal strength in dBm

        Returns:
            Quality text (e.g., "Excellent", "Good", "Fair", "Weak", "Poor")
        """
        level = SignalBars.get_signal_level(power_dbm)

        if level == 4:
            return "Excellent"
        elif level == 3:
            return "Good"
        elif level == 2:
            return "Fair"
        elif level == 1:
            return "Weak"
        else:
            return "Poor"
