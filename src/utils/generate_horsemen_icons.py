#!/usr/bin/env python3
"""
Generate custom PNG icons for the Four Horsemen tabs
Creates distinctive 64x64 icons for War, Pestilence, Famine, and Death
"""

from PIL import Image, ImageDraw
import os


def create_war_icon(size=32):
    """Create WAR icon - Crossed swords in red (optimized for tabs)"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Red gradient background circle
    for i in range(size//2, 0, -1):
        alpha = int(255 * (1 - i/(size/2)) * 0.3)
        draw.ellipse([size//2-i, size//2-i, size//2+i, size//2+i],
                     fill=(180, 0, 0, alpha))

    # Crossed swords (simplified as X with pointed ends)
    sword_color = (255, 50, 50, 255)
    blade_width = 6

    # Sword 1 (top-left to bottom-right)
    draw.line([10, 10, size-10, size-10], fill=sword_color, width=blade_width)
    # Sword tip
    draw.polygon([size-10, size-10, size-15, size-5, size-5, size-15], fill=sword_color)
    # Sword handle
    draw.ellipse([5, 5, 15, 15], fill=(100, 0, 0, 255))

    # Sword 2 (top-right to bottom-left)
    draw.line([size-10, 10, 10, size-10], fill=sword_color, width=blade_width)
    # Sword tip
    draw.polygon([10, size-10, 15, size-5, 5, size-15], fill=sword_color)
    # Sword handle
    draw.ellipse([size-15, 5, size-5, 15], fill=(100, 0, 0, 255))

    return img


def create_pestilence_icon(size=64):
    """Create PESTILENCE icon - Biohazard symbol in green"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Green toxic glow background
    for i in range(size//2, 0, -1):
        alpha = int(255 * (1 - i/(size/2)) * 0.25)
        draw.ellipse([size//2-i, size//2-i, size//2+i, size//2+i],
                     fill=(0, 150, 0, alpha))

    # Simplified biohazard symbol
    center_x, center_y = size // 2, size // 2
    radius = size // 4

    # Center circle
    draw.ellipse([center_x - 6, center_y - 6, center_x + 6, center_y + 6],
                 fill=(0, 255, 0, 255))

    # Three biohazard circles (120 degrees apart)
    import math
    for angle in [0, 120, 240]:
        rad = math.radians(angle)
        x = center_x + int(radius * math.cos(rad))
        y = center_y + int(radius * math.sin(rad))

        # Outer circle
        draw.ellipse([x - 10, y - 10, x + 10, y + 10],
                     fill=(50, 200, 50, 255), outline=(0, 255, 0, 255), width=2)

        # Connecting arc (simplified as line)
        draw.line([center_x, center_y, x, y], fill=(0, 255, 0, 255), width=4)

    return img


def create_famine_icon(size=64):
    """Create FAMINE icon - Empty/cracked bowl in purple"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Purple draining aura
    for i in range(size//2, 0, -1):
        alpha = int(255 * (1 - i/(size/2)) * 0.2)
        draw.ellipse([size//2-i, size//2-i, size//2+i, size//2+i],
                     fill=(100, 0, 100, alpha))

    # Empty bowl
    bowl_color = (150, 100, 200, 255)
    crack_color = (80, 40, 120, 255)

    # Bowl outline (arc)
    draw.arc([10, 20, size-10, size-5], 0, 180, fill=bowl_color, width=6)

    # Bowl sides
    draw.line([10, 40, 10, 50], fill=bowl_color, width=6)
    draw.line([size-10, 40, size-10, 50], fill=bowl_color, width=6)

    # Crack in bowl
    draw.line([size//2-5, 30, size//2, 50], fill=crack_color, width=3)
    draw.line([size//2, 50, size//2+5, 35], fill=crack_color, width=3)

    # Empty indicator (X inside bowl)
    draw.line([15, 35, size-15, 45], fill=(100, 50, 150, 200), width=2)
    draw.line([size-15, 35, 15, 45], fill=(100, 50, 150, 200), width=2)

    return img


def create_death_icon(size=64):
    """Create DEATH icon - Skull in black/grey"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark aura
    for i in range(size//2, 0, -1):
        alpha = int(255 * (1 - i/(size/2)) * 0.3)
        draw.ellipse([size//2-i, size//2-i, size//2+i, size//2+i],
                     fill=(20, 20, 20, alpha))

    # Skull
    skull_color = (200, 200, 200, 255)
    shadow_color = (80, 80, 80, 255)

    # Skull outline (rounded rectangle for head)
    draw.ellipse([15, 10, size-15, 45], fill=skull_color, outline=shadow_color, width=2)

    # Eye sockets (dark)
    draw.ellipse([22, 20, 32, 32], fill=(0, 0, 0, 255))
    draw.ellipse([size-32, 20, size-22, 32], fill=(0, 0, 0, 255))

    # Nose cavity (triangle)
    nose_x = size // 2
    draw.polygon([nose_x, 30, nose_x-5, 38, nose_x+5, 38], fill=(0, 0, 0, 255))

    # Jaw/teeth (simplified)
    draw.rectangle([20, 42, size-20, 52], fill=skull_color, outline=shadow_color, width=2)

    # Teeth lines
    for x in range(25, size-20, 6):
        draw.line([x, 42, x, 52], fill=shadow_color, width=1)

    # Crossbones behind skull (faint)
    bone_color = (150, 150, 150, 180)
    draw.line([10, size-10, size-10, size-10], fill=bone_color, width=8)
    draw.ellipse([5, size-15, 15, size-5], fill=bone_color)
    draw.ellipse([size-15, size-15, size-5, size-5], fill=bone_color)

    return img


def main():
    """Generate all Four Horsemen icons"""
    # Create icons directory if it doesn't exist
    icons_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'icons')
    os.makedirs(icons_dir, exist_ok=True)

    print("[*] Generating Four Horsemen icons...")

    # Generate each icon
    icons = {
        'war': create_war_icon(),
        'pestilence': create_pestilence_icon(),
        'famine': create_famine_icon(),
        'death': create_death_icon()
    }

    # Save icons
    for name, img in icons.items():
        filepath = os.path.join(icons_dir, f'{name}.png')
        img.save(filepath, 'PNG')
        print(f"[✓] Created {filepath}")

    print("[✓] All Four Horsemen icons generated successfully")


if __name__ == '__main__':
    main()
