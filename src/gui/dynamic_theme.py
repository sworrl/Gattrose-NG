"""
Dynamic 24/7 Theme System
Generates unique color schemes for each hour of a 7-day cycle
All themes are dark-based with shifting gradients and patterns
"""

import math
from datetime import datetime
from typing import Tuple, Dict
from PyQt6.QtGui import QLinearGradient, QColor, QBrush, QPalette
from PyQt6.QtCore import Qt, QTimer


class DynamicTheme:
    """
    24/7 Dynamic Theme Generator

    Creates 168 unique themes (7 days × 24 hours) using mathematical formulas
    Each hour has a unique color palette with gradients and textures
    """

    def __init__(self):
        self.current_palette = None
        self.timer = None

    @staticmethod
    def get_time_index() -> Tuple[int, int, float]:
        """
        Get current time index for theme calculation

        Returns:
            Tuple of (day_of_week, hour, minute_fraction)
            day_of_week: 0-6 (Monday=0)
            hour: 0-23
            minute_fraction: 0.0-1.0 (for smooth transitions)
        """
        now = datetime.now()
        day_of_week = now.weekday()  # 0-6
        hour = now.hour  # 0-23
        minute_fraction = now.minute / 60.0  # 0.0-1.0

        return day_of_week, hour, minute_fraction

    @staticmethod
    def get_unique_seed(day: int, hour: int) -> float:
        """
        Generate unique seed for each hour of the week

        Args:
            day: Day of week (0-6)
            hour: Hour of day (0-23)

        Returns:
            Unique seed value (0.0-1.0)
        """
        # Create unique index for 168 hours in a week
        total_hours = day * 24 + hour
        # Use multiple wave functions for uniqueness
        seed = (
            math.sin(total_hours * 0.1) * 0.3 +
            math.cos(total_hours * 0.05) * 0.3 +
            math.sin(total_hours * 0.15 + day) * 0.2 +
            math.cos(total_hours * 0.08 - day * 2) * 0.2
        )
        # Normalize to 0-1
        return (seed + 1.0) / 2.0

    @staticmethod
    def get_texture_pattern(day: int, hour: int) -> str:
        """
        Generate unique texture pattern for each hour
        Patterns shift with time to create dynamic visual changes

        Args:
            day: Day of week (0-6)
            hour: Hour of day (0-23)

        Returns:
            CSS pattern/texture string
        """
        total_hours = day * 24 + hour

        # Pattern type cycles through different styles
        pattern_type = total_hours % 7

        # Pattern intensity varies by hour of day
        intensity = (hour / 24.0) * 0.3 + 0.1  # 0.1 to 0.4

        # Pattern rotation/angle shifts continuously
        angle = (total_hours * 15) % 360

        if pattern_type == 0:
            # Diagonal stripes (subtle)
            return f"""
                repeating-linear-gradient(
                    {angle}deg,
                    transparent,
                    transparent 10px,
                    rgba(255, 255, 255, {intensity * 0.02}) 10px,
                    rgba(255, 255, 255, {intensity * 0.02}) 11px
                )
            """
        elif pattern_type == 1:
            # Dot pattern
            size = 3 + (total_hours % 3)
            spacing = 20 + (total_hours % 10)
            return f"""
                radial-gradient(
                    circle at {spacing}px {spacing}px,
                    rgba(255, 255, 255, {intensity * 0.03}) {size}px,
                    transparent {size}px
                )
            """
        elif pattern_type == 2:
            # Grid pattern
            return f"""
                repeating-linear-gradient(
                    0deg,
                    transparent,
                    transparent 19px,
                    rgba(255, 255, 255, {intensity * 0.015}) 19px,
                    rgba(255, 255, 255, {intensity * 0.015}) 20px
                ),
                repeating-linear-gradient(
                    90deg,
                    transparent,
                    transparent 19px,
                    rgba(255, 255, 255, {intensity * 0.015}) 19px,
                    rgba(255, 255, 255, {intensity * 0.015}) 20px
                )
            """
        elif pattern_type == 3:
            # Diagonal cross-hatch
            return f"""
                repeating-linear-gradient(
                    {angle}deg,
                    transparent,
                    transparent 15px,
                    rgba(255, 255, 255, {intensity * 0.02}) 15px,
                    rgba(255, 255, 255, {intensity * 0.02}) 16px
                ),
                repeating-linear-gradient(
                    {angle + 90}deg,
                    transparent,
                    transparent 15px,
                    rgba(255, 255, 255, {intensity * 0.02}) 15px,
                    rgba(255, 255, 255, {intensity * 0.02}) 16px
                )
            """
        elif pattern_type == 4:
            # Hexagon pattern (simulated with gradients)
            return f"""
                radial-gradient(
                    circle at 50% 50%,
                    rgba(255, 255, 255, {intensity * 0.01}) 0%,
                    transparent 1%
                )
            """
        elif pattern_type == 5:
            # Wave pattern
            wave_freq = 30 + (total_hours % 20)
            return f"""
                repeating-linear-gradient(
                    {angle}deg,
                    rgba(255, 255, 255, {intensity * 0.02}),
                    rgba(255, 255, 255, {intensity * 0.02}) 2px,
                    transparent 2px,
                    transparent {wave_freq}px
                )
            """
        else:
            # Organic noise pattern (subtle gradient spots)
            offset1 = (total_hours * 7) % 100
            offset2 = (total_hours * 13) % 100
            return f"""
                radial-gradient(
                    ellipse at {offset1}% {offset2}%,
                    rgba(255, 255, 255, {intensity * 0.015}) 0%,
                    transparent 50%
                )
            """

    @staticmethod
    def generate_dark_color(seed: float, offset: float = 0.0, saturation_mult: float = 1.0) -> QColor:
        """
        Generate a dark color based on seed

        Args:
            seed: Base seed value (0-1)
            offset: Hue offset for variation
            saturation_mult: Saturation multiplier

        Returns:
            QColor in dark range
        """
        # Hue: full spectrum but shifted by seed and offset
        hue = int((seed * 360 + offset) % 360)

        # Saturation: 60-100% for vibrant dark colors
        saturation = int(60 + (seed * 40) * saturation_mult)

        # Value/Brightness: 15-45% to keep it dark
        # Varies based on seed for uniqueness
        value = int(15 + (seed * 30))

        # SAFETY: Ensure value never exceeds 45 (keep it dark!)
        value = min(45, value)

        return QColor.fromHsv(hue, saturation, value)

    @staticmethod
    def generate_gradient_colors(day: int, hour: int, minute_frac: float = 0.0) -> Dict[str, any]:
        """
        Generate color palette and texture pattern for current time

        Args:
            day: Day of week (0-6)
            hour: Hour (0-23)
            minute_frac: Minute fraction for smooth transition

        Returns:
            Dictionary of colors and texture pattern for different UI elements
        """
        # Get base seed for this hour
        seed = DynamicTheme.get_unique_seed(day, hour)

        # Get next hour's seed for smooth transition
        next_hour = (hour + 1) % 24
        next_day = day if next_hour > 0 else (day + 1) % 7
        next_seed = DynamicTheme.get_unique_seed(next_day, next_hour)

        # Interpolate between current and next hour based on minutes
        interpolated_seed = seed * (1 - minute_frac) + next_seed * minute_frac

        # Generate multiple colors with different offsets for variety
        colors = {}

        # Add texture pattern for this hour
        colors['texture_pattern'] = DynamicTheme.get_texture_pattern(day, hour)

        # Primary background - deepest dark
        colors['bg_primary'] = DynamicTheme.generate_dark_color(interpolated_seed, 0, 0.8)

        # Secondary background - slightly lighter
        colors['bg_secondary'] = DynamicTheme.generate_dark_color(interpolated_seed, 30, 0.9)

        # Tertiary background
        colors['bg_tertiary'] = DynamicTheme.generate_dark_color(interpolated_seed, 60, 1.0)

        # Accent colors for highlights
        colors['accent_1'] = DynamicTheme.generate_dark_color(interpolated_seed, 120, 1.2)
        colors['accent_2'] = DynamicTheme.generate_dark_color(interpolated_seed, 180, 1.1)
        colors['accent_3'] = DynamicTheme.generate_dark_color(interpolated_seed, 240, 1.0)

        # Text colors - lighter but still in dark theme range
        # Increase value/brightness for text readability
        text_seed = (interpolated_seed + 0.5) % 1.0
        text_color = DynamicTheme.generate_dark_color(text_seed, 0, 0.6)
        text_color.setHsv(text_color.hue(), 20, 200)  # Desaturated, bright for readability
        colors['text_primary'] = text_color

        # Muted text
        muted_text = QColor(text_color)
        muted_text.setHsv(muted_text.hue(), 15, 140)
        colors['text_secondary'] = muted_text

        return colors

    @staticmethod
    def create_gradient(color1: QColor, color2: QColor, vertical: bool = True) -> str:
        """
        Create CSS gradient string

        Args:
            color1: Start color
            color2: End color
            vertical: If True, vertical gradient, else horizontal

        Returns:
            CSS gradient string
        """
        direction = "to bottom" if vertical else "to right"

        return f"""
        qlineargradient(
            x1:0, y1:0, x2:{0 if vertical else 1}, y2:{1 if vertical else 0},
            stop:0 {color1.name()},
            stop:1 {color2.name()}
        )
        """

    @staticmethod
    def create_multi_gradient(colors: list, vertical: bool = True) -> str:
        """
        Create multi-stop gradient

        Args:
            colors: List of QColor objects
            vertical: If True, vertical gradient

        Returns:
            CSS gradient string
        """
        direction = "to bottom" if vertical else "to right"
        stops = []

        for i, color in enumerate(colors):
            position = i / (len(colors) - 1) if len(colors) > 1 else 0
            stops.append(f"stop:{position:.2f} {color.name()}")

        return f"""
        qlineargradient(
            x1:0, y1:0, x2:{0 if vertical else 1}, y2:{1 if vertical else 0},
            {', '.join(stops)}
        )
        """

    @staticmethod
    def generate_stylesheet(colors: Dict[str, QColor]) -> str:
        """
        Generate complete stylesheet for application

        Args:
            colors: Color palette dictionary

        Returns:
            Complete CSS stylesheet string
        """
        # Create gradients
        bg_gradient = DynamicTheme.create_gradient(colors['bg_primary'], colors['bg_secondary'])
        accent_gradient = DynamicTheme.create_multi_gradient([
            colors['accent_1'], colors['accent_2'], colors['accent_3']
        ], vertical=False)

        # Get texture pattern
        texture = colors.get('texture_pattern', '')

        stylesheet = f"""
        /* Main Window with Dynamic Texture */
        QMainWindow {{
            background: {bg_gradient}, {texture};
            color: {colors['text_primary'].name()};
        }}

        /* Central Widget with Subtle Texture */
        QWidget {{
            background: {colors['bg_primary'].name()}, {texture};
            color: {colors['text_primary'].name()};
        }}

        /* Tab Widget */
        QTabWidget::pane {{
            border: 2px solid {colors['accent_2'].name()};
            background: {bg_gradient};
            border-radius: 5px;
        }}

        QTabWidget::tab-bar {{
            alignment: center;
        }}

        QTabBar::tab {{
            background: {DynamicTheme.create_gradient(colors['bg_secondary'], colors['bg_tertiary'])};
            color: {colors['text_secondary'].name()};
            padding: 8px 20px;
            margin: 2px;
            border: 1px solid {colors['accent_1'].name()};
            border-radius: 4px;
            min-width: 100px;
        }}

        QTabBar::tab:selected {{
            background: {accent_gradient};
            color: {colors['text_primary'].name()};
            font-weight: bold;
            border: 2px solid {colors['accent_3'].name()};
        }}

        QTabBar::tab:hover {{
            background: {DynamicTheme.create_gradient(colors['accent_1'], colors['accent_2'])};
            border: 1px solid {colors['accent_3'].name()};
        }}

        /* Group Box */
        QGroupBox {{
            background: {DynamicTheme.create_gradient(colors['bg_secondary'], colors['bg_primary'])};
            border: 2px solid {colors['accent_1'].name()};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 15px;
            font-weight: bold;
            color: {colors['text_primary'].name()};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 5px 10px;
            background: {accent_gradient};
            border-radius: 4px;
            color: {colors['text_primary'].name()};
        }}

        /* Buttons */
        QPushButton {{
            background: {DynamicTheme.create_gradient(colors['accent_1'], colors['accent_2'])};
            color: {colors['text_primary'].name()};
            border: 2px solid {colors['accent_3'].name()};
            border-radius: 5px;
            padding: 8px 15px;
            font-weight: bold;
            min-width: 80px;
        }}

        QPushButton:hover {{
            background: {DynamicTheme.create_gradient(colors['accent_2'], colors['accent_3'])};
            border: 2px solid {colors['text_primary'].name()};
        }}

        QPushButton:pressed {{
            background: {colors['accent_3'].name()};
            border: 2px solid {colors['accent_1'].name()};
        }}

        QPushButton:disabled {{
            background: {colors['bg_tertiary'].name()};
            color: {colors['text_secondary'].name()};
            border: 1px solid {colors['bg_secondary'].name()};
        }}

        /* Tree Widget */
        QTreeWidget {{
            background: {colors['bg_primary'].name()};
            alternate-background-color: {colors['bg_secondary'].name()};
            color: {colors['text_primary'].name()};
            border: 2px solid {colors['accent_1'].name()};
            border-radius: 5px;
            selection-background-color: {colors['accent_2'].name()};
        }}

        QTreeWidget::item {{
            padding: 5px;
            border-bottom: 1px solid {colors['bg_tertiary'].name()};
        }}

        QTreeWidget::item:hover {{
            background: {DynamicTheme.create_gradient(colors['bg_secondary'], colors['accent_1'], False)};
        }}

        QTreeWidget::item:selected {{
            background: {accent_gradient};
            color: {colors['text_primary'].name()};
        }}

        /* Header */
        QHeaderView::section {{
            background: {DynamicTheme.create_gradient(colors['accent_1'], colors['accent_2'], False)};
            color: {colors['text_primary'].name()};
            padding: 8px;
            border: 1px solid {colors['accent_3'].name()};
            font-weight: bold;
        }}

        /* Text Edit / Plain Text Edit */
        QTextEdit, QPlainTextEdit {{
            background: {colors['bg_primary'].name()};
            color: {colors['text_primary'].name()};
            border: 2px solid {colors['accent_1'].name()};
            border-radius: 5px;
            padding: 5px;
            selection-background-color: {colors['accent_2'].name()};
        }}

        /* Line Edit */
        QLineEdit {{
            background: {DynamicTheme.create_gradient(colors['bg_primary'], colors['bg_secondary'])};
            color: {colors['text_primary'].name()};
            border: 2px solid {colors['accent_1'].name()};
            border-radius: 5px;
            padding: 5px;
            selection-background-color: {colors['accent_2'].name()};
        }}

        QLineEdit:focus {{
            border: 2px solid {colors['accent_3'].name()};
        }}

        /* Labels */
        QLabel {{
            color: {colors['text_primary'].name()};
            background: transparent;
        }}

        /* Progress Bar */
        QProgressBar {{
            background: {colors['bg_secondary'].name()};
            border: 2px solid {colors['accent_1'].name()};
            border-radius: 5px;
            text-align: center;
            color: {colors['text_primary'].name()};
        }}

        QProgressBar::chunk {{
            background: {accent_gradient};
            border-radius: 3px;
        }}

        /* Scroll Bar */
        QScrollBar:vertical {{
            background: {colors['bg_secondary'].name()};
            width: 15px;
            border-radius: 7px;
        }}

        QScrollBar::handle:vertical {{
            background: {DynamicTheme.create_gradient(colors['accent_1'], colors['accent_2'])};
            border-radius: 7px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {colors['accent_3'].name()};
        }}

        QScrollBar:horizontal {{
            background: {colors['bg_secondary'].name()};
            height: 15px;
            border-radius: 7px;
        }}

        QScrollBar::handle:horizontal {{
            background: {DynamicTheme.create_gradient(colors['accent_1'], colors['accent_2'], False)};
            border-radius: 7px;
            min-width: 20px;
        }}

        /* Slider */
        QSlider::groove:horizontal {{
            background: {colors['bg_secondary'].name()};
            height: 8px;
            border-radius: 4px;
        }}

        QSlider::handle:horizontal {{
            background: {accent_gradient};
            width: 18px;
            margin: -5px 0;
            border-radius: 9px;
            border: 2px solid {colors['accent_3'].name()};
        }}

        /* Combo Box */
        QComboBox {{
            background: {DynamicTheme.create_gradient(colors['bg_secondary'], colors['accent_1'])};
            color: {colors['text_primary'].name()};
            border: 2px solid {colors['accent_2'].name()};
            border-radius: 5px;
            padding: 5px;
        }}

        QComboBox:hover {{
            border: 2px solid {colors['accent_3'].name()};
        }}

        QComboBox::drop-down {{
            border: none;
            background: {colors['accent_2'].name()};
            border-radius: 3px;
        }}

        /* Menu */
        QMenu {{
            background: {colors['bg_secondary'].name()};
            color: {colors['text_primary'].name()};
            border: 2px solid {colors['accent_1'].name()};
        }}

        QMenu::item:selected {{
            background: {accent_gradient};
        }}

        /* Status Bar */
        QStatusBar {{
            background: {DynamicTheme.create_gradient(colors['bg_secondary'], colors['bg_tertiary'], False)};
            color: {colors['text_primary'].name()};
            border-top: 2px solid {colors['accent_1'].name()};
        }}
        """

        return stylesheet

    def apply_theme(self, widget) -> None:
        """
        Apply current dynamic theme to widget

        Args:
            widget: QWidget to apply theme to
        """
        day, hour, minute_frac = self.get_time_index()
        colors = self.generate_gradient_colors(day, hour, minute_frac)
        stylesheet = self.generate_stylesheet(colors)
        widget.setStyleSheet(stylesheet)

        self.current_palette = colors

    def start_auto_update(self, widget, interval_ms: int = 60000) -> None:
        """
        Start automatic theme updates

        Args:
            widget: Widget to update
            interval_ms: Update interval in milliseconds (default: 1 minute)
        """
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.apply_theme(widget))
        self.timer.start(interval_ms)

        # Apply initial theme
        self.apply_theme(widget)

    def stop_auto_update(self) -> None:
        """Stop automatic theme updates"""
        if self.timer:
            self.timer.stop()


# Convenience function
def get_current_theme_colors() -> Dict[str, QColor]:
    """Get current theme colors based on time"""
    day, hour, minute_frac = DynamicTheme.get_time_index()
    return DynamicTheme.generate_gradient_colors(day, hour, minute_frac)
