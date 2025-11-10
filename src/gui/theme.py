"""
Theme system for Gattrose Qt6 application
15 unique themes inspired by classic 90s video games
"""

from typing import Dict, NamedTuple


class ThemeColors(NamedTuple):
    """Color palette for a theme"""
    # Background colors
    bg_primary: str       # Main background
    bg_secondary: str     # Secondary panels
    bg_tertiary: str      # Tertiary elements
    bg_input: str         # Input fields
    bg_terminal: str      # Terminal/log output

    # Foreground colors
    fg_primary: str       # Main text
    fg_secondary: str     # Secondary text
    fg_terminal: str      # Terminal text

    # Accent colors
    accent_primary: str   # Main accent (buttons, highlights)
    accent_hover: str     # Hover state
    accent_pressed: str   # Pressed state
    accent_border: str    # Border highlights

    # Status colors
    status_ok: str        # Success/OK status
    status_warning: str   # Warning status
    status_error: str     # Error status

    # UI element colors
    border_primary: str   # Main borders
    border_secondary: str # Secondary borders
    heading_color: str    # Heading text

    # Theme metadata
    name: str
    description: str

    # Texture pattern (CSS gradient for subtle background texture)
    texture: str = "none"  # Default: no texture

    # YouTube channel link (optional, for YouTuber themes)
    youtube_channel: str = ""  # Default: no channel


# ==================== TEXTURE PATTERNS ====================

# Subtle, visible texture patterns using CSS gradients
# These create depth and visual interest without overwhelming the UI

TEXTURES = {
    "none": "",  # No texture

    # Subtle noise/grain patterns
    "fine_grain": "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.03) 2px, rgba(255,255,255,0.03) 4px)",
    "medium_grain": "repeating-linear-gradient(45deg, transparent, transparent 3px, rgba(255,255,255,0.04) 3px, rgba(255,255,255,0.04) 6px)",
    "coarse_grain": "repeating-linear-gradient(90deg, transparent, transparent 4px, rgba(255,255,255,0.05) 4px, rgba(255,255,255,0.05) 8px)",

    # Diagonal patterns
    "diagonal_lines": "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.03) 10px, rgba(255,255,255,0.03) 12px)",
    "diagonal_bold": "repeating-linear-gradient(-45deg, transparent, transparent 15px, rgba(255,255,255,0.04) 15px, rgba(255,255,255,0.04) 18px)",

    # Grid patterns
    "fine_grid": "repeating-linear-gradient(0deg, transparent, transparent 10px, rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 11px), repeating-linear-gradient(90deg, transparent, transparent 10px, rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 11px)",
    "medium_grid": "repeating-linear-gradient(0deg, transparent, transparent 20px, rgba(255,255,255,0.03) 20px, rgba(255,255,255,0.03) 21px), repeating-linear-gradient(90deg, transparent, transparent 20px, rgba(255,255,255,0.03) 20px, rgba(255,255,255,0.03) 21px)",

    # Dot patterns
    "dots": "radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px)",
    "dots_large": "radial-gradient(circle, rgba(255,255,255,0.05) 2px, transparent 2px)",

    # Fabric/weave patterns
    "fabric": "repeating-linear-gradient(45deg, transparent 0, transparent 2px, rgba(255,255,255,0.02) 2px, rgba(255,255,255,0.02) 4px), repeating-linear-gradient(-45deg, transparent 0, transparent 2px, rgba(0,0,0,0.02) 2px, rgba(0,0,0,0.02) 4px)",
    "weave": "repeating-linear-gradient(0deg, transparent 0, transparent 4px, rgba(255,255,255,0.03) 4px, rgba(255,255,255,0.03) 8px), repeating-linear-gradient(90deg, transparent 0, transparent 4px, rgba(0,0,0,0.03) 4px, rgba(0,0,0,0.03) 8px)",

    # Carbon fiber / Tech patterns
    "carbon": "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.15) 2px, rgba(0,0,0,0.15) 4px), repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(255,255,255,0.05) 2px, rgba(255,255,255,0.05) 4px)",
    "tech_mesh": "repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(255,255,255,0.02) 5px, rgba(255,255,255,0.02) 6px), repeating-linear-gradient(-45deg, transparent, transparent 5px, rgba(255,255,255,0.02) 5px, rgba(255,255,255,0.02) 6px)",

    # Subtle gradients with noise
    "radial_glow": "radial-gradient(circle at center, rgba(255,255,255,0.05) 0%, transparent 70%)",
    "corner_glow": "radial-gradient(circle at top left, rgba(255,255,255,0.06) 0%, transparent 50%), radial-gradient(circle at bottom right, rgba(255,255,255,0.04) 0%, transparent 50%)",

    # Crosshatch patterns
    "crosshatch": "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 11px), repeating-linear-gradient(-45deg, transparent, transparent 10px, rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 11px)",
    "crosshatch_heavy": "repeating-linear-gradient(45deg, transparent, transparent 8px, rgba(255,255,255,0.04) 8px, rgba(255,255,255,0.04) 10px), repeating-linear-gradient(-45deg, transparent, transparent 8px, rgba(255,255,255,0.04) 8px, rgba(255,255,255,0.04) 10px)",

    # Classic/Retro patterns
    # Houndstooth - Classic British textile pattern (dog tooth check)
    "houndstooth": """repeating-linear-gradient(45deg, transparent 0px, transparent 5px, rgba(255,255,255,0.06) 5px, rgba(255,255,255,0.06) 10px),
                      repeating-linear-gradient(-45deg, transparent 0px, transparent 5px, rgba(0,0,0,0.06) 5px, rgba(0,0,0,0.06) 10px),
                      repeating-linear-gradient(45deg, transparent 0px, transparent 2px, rgba(255,255,255,0.03) 2px, rgba(255,255,255,0.03) 4px)""",

    # Rootweave - Old-school woven root/basket pattern
    "rootweave": """repeating-linear-gradient(0deg, transparent 0, transparent 2px, rgba(255,255,255,0.04) 2px, rgba(255,255,255,0.04) 4px, transparent 4px, transparent 6px, rgba(0,0,0,0.04) 6px, rgba(0,0,0,0.04) 8px),
                    repeating-linear-gradient(90deg, transparent 0, transparent 2px, rgba(255,255,255,0.04) 2px, rgba(255,255,255,0.04) 4px, transparent 4px, transparent 6px, rgba(0,0,0,0.04) 6px, rgba(0,0,0,0.04) 8px)""",
}


# ==================== 90s VIDEO GAME THEMES ====================

THEMES: Dict[str, ThemeColors] = {
    # 1. SONIC THE HEDGEHOG - Green Hill Zone
    "sonic": ThemeColors(
        bg_primary="#1a4d2e",
        bg_secondary="#0f3820",
        bg_tertiary="#245a3b",
        bg_input="#0d2e1c",
        bg_terminal="#000000",
        fg_primary="#ffffff",
        fg_secondary="#c0e0c0",
        fg_terminal="#00ff00",
        accent_primary="#0066cc",  # Sonic blue
        accent_hover="#3399ff",
        accent_pressed="#004499",
        accent_border="#66ccff",
        status_ok="#ffd700",  # Ring gold
        status_warning="#ff8800",
        status_error="#ff0000",
        border_primary="#2d6b3f",
        border_secondary="#3d7b4f",
        heading_color="#0099ff",
        name="Sonic the Hedgehog",
        description="Green Hill Zone - Gotta go fast!",
        texture=TEXTURES["diagonal_lines"]
    ),

    # 2. SUPER MARIO WORLD - Bright and Colorful
    "mario": ThemeColors(
        bg_primary="#3a7bc8",
        bg_secondary="#2d6aa8",
        bg_tertiary="#4a8bd8",
        bg_input="#1e5088",
        bg_terminal="#000033",
        fg_primary="#ffffff",
        fg_secondary="#f0f0ff",
        fg_terminal="#ffff00",
        accent_primary="#e60012",  # Mario red
        accent_hover="#ff3344",
        accent_pressed="#cc0010",
        accent_border="#ff6677",
        status_ok="#00ff00",
        status_warning="#ffcc00",
        status_error="#ff0000",
        border_primary="#5a9bd8",
        border_secondary="#6aabe8",
        heading_color="#ffd700",
        name="Super Mario World",
        description="It's-a me, Mario!",
        texture=TEXTURES["fine_grain"]
    ),

    # 3. DOOM - Hell on Earth
    "doom": ThemeColors(
        bg_primary="#2b1810",
        bg_secondary="#1a0f08",
        bg_tertiary="#3b2820",
        bg_input="#0f0804",
        bg_terminal="#000000",
        fg_primary="#d0d0d0",
        fg_secondary="#a0a0a0",
        fg_terminal="#ff4444",
        accent_primary="#8b0000",  # Blood red
        accent_hover="#a52a2a",
        accent_pressed="#660000",
        accent_border="#cc3333",
        status_ok="#00aa00",
        status_warning="#ff8800",
        status_error="#ff0000",
        border_primary="#4a3228",
        border_secondary="#5a4238",
        heading_color="#ff6644",
        name="DOOM",
        description="Rip and tear!",
        texture=TEXTURES["coarse_grain"]
    ),

    # 4. MORTAL KOMBAT - Fatality!
    "mortalkombat": ThemeColors(
        bg_primary="#1a1a1a",
        bg_secondary="#0d0d0d",
        bg_tertiary="#2a2a2a",
        bg_input="#050505",
        bg_terminal="#000000",
        fg_primary="#ffff00",
        fg_secondary="#dddd00",
        fg_terminal="#ffff00",
        accent_primary="#cc0000",  # Blood red
        accent_hover="#ff3333",
        accent_pressed="#990000",
        accent_border="#ff6666",
        status_ok="#00ff00",
        status_warning="#ff8800",
        status_error="#cc0000",
        border_primary="#333333",
        border_secondary="#444444",
        heading_color="#ffff00",
        name="Mortal Kombat",
        description="Finish him!",
        texture=TEXTURES["dots"]
    ),

    # 5. STREET FIGHTER II - Hadouken!
    "streetfighter": ThemeColors(
        bg_primary="#1e2a4a",
        bg_secondary="#141e3a",
        bg_tertiary="#2e3a5a",
        bg_input="#0a1020",
        bg_terminal="#000020",
        fg_primary="#ffffff",
        fg_secondary="#d0d0ff",
        fg_terminal="#00ffff",
        accent_primary="#ffcc00",  # Energy yellow
        accent_hover="#ffdd33",
        accent_pressed="#cc9900",
        accent_border="#ffee66",
        status_ok="#00ff00",
        status_warning="#ff8800",
        status_error="#ff0000",
        border_primary="#3e4a6a",
        border_secondary="#4e5a7a",
        heading_color="#ff3366",
        name="Street Fighter II",
        description="You win! Perfect!"
    ),

    # 6. CHRONO TRIGGER - Time Gates
    "chronotrigger": ThemeColors(
        bg_primary="#1a1a3a",
        bg_secondary="#0d0d2a",
        bg_tertiary="#2a2a4a",
        bg_input="#05051a",
        bg_terminal="#000010",
        fg_primary="#e0e0ff",
        fg_secondary="#c0c0e0",
        fg_terminal="#aa88ff",
        accent_primary="#8844ff",  # Time purple
        accent_hover="#aa66ff",
        accent_pressed="#6622dd",
        accent_border="#cc99ff",
        status_ok="#00ff88",
        status_warning="#ffaa00",
        status_error="#ff3366",
        border_primary="#3a3a5a",
        border_secondary="#4a4a6a",
        heading_color="#aa66ff",
        name="Chrono Trigger",
        description="The time gate awaits...",
        texture=TEXTURES["medium_grid"]
    ),

    # 7. FINAL FANTASY VI - Crystal Magic
    "finalfantasy": ThemeColors(
        bg_primary="#1a1a2a",
        bg_secondary="#0d0d1a",
        bg_tertiary="#2a2a3a",
        bg_input="#05050d",
        bg_terminal="#000008",
        fg_primary="#d0d0ff",
        fg_secondary="#a0a0d0",
        fg_terminal="#8888ff",
        accent_primary="#4488ff",  # Crystal blue
        accent_hover="#66aaff",
        accent_pressed="#2266dd",
        accent_border="#88ccff",
        status_ok="#00ff44",
        status_warning="#ffcc44",
        status_error="#ff4444",
        border_primary="#3a3a4a",
        border_secondary="#4a4a5a",
        heading_color="#88bbff",
        name="Final Fantasy VI",
        description="The crystal's power flows..."
    ),

    # 8. EARTHWORM JIM - Groovy!
    "earthwormjim": ThemeColors(
        bg_primary="#2a4a2a",
        bg_secondary="#1a3a1a",
        bg_tertiary="#3a5a3a",
        bg_input="#0d2a0d",
        bg_terminal="#001100",
        fg_primary="#ffff88",
        fg_secondary="#eeee77",
        fg_terminal="#88ff00",
        accent_primary="#ff8800",  # Orange suit
        accent_hover="#ffaa33",
        accent_pressed="#cc6600",
        accent_border="#ffcc66",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff3333",
        border_primary="#4a6a4a",
        border_secondary="#5a7a5a",
        heading_color="#ffaa00",
        name="Earthworm Jim",
        description="Groovy!"
    ),

    # 9. DONKEY KONG COUNTRY - Jungle Vibes
    "donkeykong": ThemeColors(
        bg_primary="#2a3820",
        bg_secondary="#1a2810",
        bg_tertiary="#3a4830",
        bg_input="#0d1808",
        bg_terminal="#000800",
        fg_primary="#f0e0c0",
        fg_secondary="#d0c0a0",
        fg_terminal="#88ff44",
        accent_primary="#cc6633",  # DK brown
        accent_hover="#ee8855",
        accent_pressed="#aa4411",
        accent_border="#ffaa77",
        status_ok="#ffee00",  # Banana yellow
        status_warning="#ff8800",
        status_error="#ff3333",
        border_primary="#4a5840",
        border_secondary="#5a6850",
        heading_color="#ffcc00",
        name="Donkey Kong Country",
        description="Banana hoard!"
    ),

    # 10. MEGA MAN X - Blue Bomber
    "megamanx": ThemeColors(
        bg_primary="#1a2838",
        bg_secondary="#0d1828",
        bg_tertiary="#2a3848",
        bg_input="#051018",
        bg_terminal="#000810",
        fg_primary="#e0f0ff",
        fg_secondary="#c0d0e0",
        fg_terminal="#00ccff",
        accent_primary="#0088ff",  # Mega blue
        accent_hover="#33aaff",
        accent_pressed="#0066cc",
        accent_border="#66ccff",
        status_ok="#00ff88",
        status_warning="#ffaa00",
        status_error="#ff3344",
        border_primary="#3a4858",
        border_secondary="#4a5868",
        heading_color="#00bbff",
        name="Mega Man X",
        description="Armor up, Maverick Hunter!"
    ),

    # 11. METROID - Alien Isolation
    "metroid": ThemeColors(
        bg_primary="#1a1a28",
        bg_secondary="#0d0d18",
        bg_tertiary="#2a2a38",
        bg_input="#050510",
        bg_terminal="#000008",
        fg_primary="#c0ffc0",
        fg_secondary="#a0e0a0",
        fg_terminal="#00ff88",
        accent_primary="#8844ff",  # Energy purple
        accent_hover="#aa66ff",
        accent_pressed="#6622dd",
        accent_border="#cc88ff",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff3366",
        border_primary="#3a3a48",
        border_secondary="#4a4a58",
        heading_color="#aa66ff",
        name="Metroid",
        description="Samus reporting..."
    ),

    # 12. CASTLEVANIA - Gothic Horror
    "castlevania": ThemeColors(
        bg_primary="#2a1420",
        bg_secondary="#1a0810",
        bg_tertiary="#3a2430",
        bg_input="#0d0408",
        bg_terminal="#080004",
        fg_primary="#e0c0d0",
        fg_secondary="#c0a0b0",
        fg_terminal="#ff88aa",
        accent_primary="#8b0000",  # Blood red
        accent_hover="#a52a2a",
        accent_pressed="#660000",
        accent_border="#cc3333",
        status_ok="#00aa00",
        status_warning="#ff8800",
        status_error="#cc0000",
        border_primary="#4a2440",
        border_secondary="#5a3450",
        heading_color="#cc4466",
        name="Castlevania",
        description="What is a man?"
    ),

    # 13. GOLDENEYE 007 - MI6 Operations
    "goldeneye": ThemeColors(
        bg_primary="#1a2a1a",
        bg_secondary="#0d1a0d",
        bg_tertiary="#2a3a2a",
        bg_input="#051005",
        bg_terminal="#000800",
        fg_primary="#d0e0d0",
        fg_secondary="#a0c0a0",
        fg_terminal="#88ff88",
        accent_primary="#4a7856",  # Military green
        accent_hover="#6a9876",
        accent_pressed="#2a5836",
        accent_border="#8ab896",
        status_ok="#00cc00",
        status_warning="#ffaa00",
        status_error="#cc0000",
        border_primary="#3a4a3a",
        border_secondary="#4a5a4a",
        heading_color="#6a9876",
        name="GoldenEye 007",
        description="For England, James?"
    ),

    # 14. BANJO-KAZOOIE - Bright Adventure
    "banjokazooie": ThemeColors(
        bg_primary="#2a3a5a",
        bg_secondary="#1a2a4a",
        bg_tertiary="#3a4a6a",
        bg_input="#0d1a3a",
        bg_terminal="#000820",
        fg_primary="#ffeecc",
        fg_secondary="#eecc99",
        fg_terminal="#ffdd88",
        accent_primary="#ff6600",  # Banjo orange
        accent_hover="#ff8833",
        accent_pressed="#cc4400",
        accent_border="#ffaa66",
        status_ok="#00ff00",
        status_warning="#ffcc00",
        status_error="#ff3333",
        border_primary="#4a5a7a",
        border_secondary="#5a6a8a",
        heading_color="#ff8833",
        name="Banjo-Kazooie",
        description="Guh-huh!"
    ),

    # 15. CRASH BANDICOOT - Wumpa Island
    "crash": ThemeColors(
        bg_primary="#2a3828",
        bg_secondary="#1a2818",
        bg_tertiary="#3a4838",
        bg_input="#0d1808",
        bg_terminal="#001100",
        fg_primary="#ffe0c0",
        fg_secondary="#e0c0a0",
        fg_terminal="#ffaa44",
        accent_primary="#ff6600",  # Crash orange
        accent_hover="#ff8833",
        accent_pressed="#cc4400",
        accent_border="#ffaa66",
        status_ok="#88ff00",
        status_warning="#ffcc00",
        status_error="#ff3333",
        border_primary="#4a5848",
        border_secondary="#5a6858",
        heading_color="#ff8833",
        name="Crash Bandicoot",
        description="Woah!"
    ),

    # ==================== 80s VIDEO GAME THEMES ====================

    # 16. PAC-MAN - Arcade Classic
    "pacman": ThemeColors(
        bg_primary="#000000",
        bg_secondary="#0a0a0a",
        bg_tertiary="#1a1a1a",
        bg_input="#050505",
        bg_terminal="#000000",
        fg_primary="#ffff00",
        fg_secondary="#ffcc00",
        fg_terminal="#ffff00",
        accent_primary="#ffff00",  # Pac-Man yellow
        accent_hover="#ffff99",
        accent_pressed="#cccc00",
        accent_border="#ffff66",
        status_ok="#00ff00",  # Cherry
        status_warning="#ff8800",  # Orange ghost
        status_error="#ff0000",  # Blinky
        border_primary="#0000ff",  # Maze blue
        border_secondary="#4444ff",
        heading_color="#ffff00",
        name="Pac-Man",
        description="Wakka wakka wakka!"
    ),

    # 17. SPACE INVADERS - Retro Alien Invasion
    "spaceinvaders": ThemeColors(
        bg_primary="#000000",
        bg_secondary="#001100",
        bg_tertiary="#002200",
        bg_input="#000800",
        bg_terminal="#000000",
        fg_primary="#00ff00",
        fg_secondary="#00dd00",
        fg_terminal="#00ff00",
        accent_primary="#00ff00",  # Invader green
        accent_hover="#44ff44",
        accent_pressed="#00cc00",
        accent_border="#88ff88",
        status_ok="#00ff00",
        status_warning="#ffff00",
        status_error="#ff0000",
        border_primary="#00aa00",
        border_secondary="#00cc00",
        heading_color="#00ff00",
        name="Space Invaders",
        description="Pew pew pew!"
    ),

    # 18. DONKEY KONG (Original) - Arcade Girders
    "donkeykongarcade": ThemeColors(
        bg_primary="#0000aa",
        bg_secondary="#000088",
        bg_tertiary="#0000cc",
        bg_input="#000066",
        bg_terminal="#000044",
        fg_primary="#ffffff",
        fg_secondary="#dddddd",
        fg_terminal="#ffaa00",
        accent_primary="#ff0000",  # Red girders
        accent_hover="#ff4444",
        accent_pressed="#cc0000",
        accent_border="#ff6666",
        status_ok="#ffaa00",  # Barrel brown
        status_warning="#ff8800",
        status_error="#ff0000",
        border_primary="#ff0000",
        border_secondary="#ff4444",
        heading_color="#ffaa00",
        name="Donkey Kong (Arcade)",
        description="It's on like Donkey Kong!"
    ),

    # 19. GALAGA - Space Shooter
    "galaga": ThemeColors(
        bg_primary="#000022",
        bg_secondary="#000011",
        bg_tertiary="#000033",
        bg_input="#000008",
        bg_terminal="#000000",
        fg_primary="#ffffff",
        fg_secondary="#ccccff",
        fg_terminal="#00ffff",
        accent_primary="#0088ff",  # Fighter blue
        accent_hover="#44aaff",
        accent_pressed="#0066cc",
        accent_border="#66ccff",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff0000",
        border_primary="#004488",
        border_secondary="#0066aa",
        heading_color="#00aaff",
        name="Galaga",
        description="Challenging stage!"
    ),

    # 20. ASTEROIDS - Vector Graphics
    "asteroids": ThemeColors(
        bg_primary="#000000",
        bg_secondary="#0a0a0a",
        bg_tertiary="#1a1a1a",
        bg_input="#050505",
        bg_terminal="#000000",
        fg_primary="#00ff00",
        fg_secondary="#00dd00",
        fg_terminal="#00ff00",
        accent_primary="#ffffff",  # Vector white
        accent_hover="#dddddd",
        accent_pressed="#bbbbbb",
        accent_border="#ffffff",
        status_ok="#00ff00",
        status_warning="#ffff00",
        status_error="#ff0000",
        border_primary="#ffffff",
        border_secondary="#dddddd",
        heading_color="#00ff00",
        name="Asteroids",
        description="Vector graphics glory!"
    ),

    # 21. CENTIPEDE - Mushroom Forest
    "centipede": ThemeColors(
        bg_primary="#1a1a3a",
        bg_secondary="#0d0d2a",
        bg_tertiary="#2a2a4a",
        bg_input="#05051a",
        bg_terminal="#000010",
        fg_primary="#ffccff",
        fg_secondary="#ffaaff",
        fg_terminal="#ff88ff",
        accent_primary="#ff00ff",  # Centipede magenta
        accent_hover="#ff44ff",
        accent_pressed="#cc00cc",
        accent_border="#ff88ff",
        status_ok="#00ff00",  # Mushroom green
        status_warning="#ffaa00",
        status_error="#ff0000",
        border_primary="#6600cc",
        border_secondary="#8800ff",
        heading_color="#ff00ff",
        name="Centipede",
        description="Mushroom mayhem!"
    ),

    # 22. DEFENDER - Side-Scrolling Space
    "defender": ThemeColors(
        bg_primary="#1a0000",
        bg_secondary="#0d0000",
        bg_tertiary="#2a0000",
        bg_input="#080000",
        bg_terminal="#000000",
        fg_primary="#ffaa00",
        fg_secondary="#ff8800",
        fg_terminal="#ffaa00",
        accent_primary="#ff8800",  # Scanner orange
        accent_hover="#ffaa44",
        accent_pressed="#cc6600",
        accent_border="#ffcc66",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff0000",
        border_primary="#663300",
        border_secondary="#884400",
        heading_color="#ffaa00",
        name="Defender",
        description="Defend the humans!"
    ),

    # 23. DIG DUG - Underground Adventure
    "digdug": ThemeColors(
        bg_primary="#2a1810",
        bg_secondary="#1a0f08",
        bg_tertiary="#3a2820",
        bg_input="#0f0804",
        bg_terminal="#080400",
        fg_primary="#ffeecc",
        fg_secondary="#ffddaa",
        fg_terminal="#ffcc88",
        accent_primary="#0088ff",  # Dig Dug blue
        accent_hover="#44aaff",
        accent_pressed="#0066cc",
        accent_border="#66ccff",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff0000",
        border_primary="#4a3228",
        border_secondary="#5a4238",
        heading_color="#0088ff",
        name="Dig Dug",
        description="Pump 'em up!"
    ),

    # 24. Q*BERT - Isometric Pyramid
    "qbert": ThemeColors(
        bg_primary="#2a1a00",
        bg_secondary="#1a1000",
        bg_tertiary="#3a2a00",
        bg_input="#0d0800",
        bg_terminal="#050200",
        fg_primary="#ffaa00",
        fg_secondary="#ff8800",
        fg_terminal="#ffcc44",
        accent_primary="#ff6600",  # Q*bert orange
        accent_hover="#ff8833",
        accent_pressed="#cc4400",
        accent_border="#ffaa66",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff0000",
        border_primary="#663300",
        border_secondary="#884400",
        heading_color="#ff8833",
        name="Q*bert",
        description="@!#?@!"
    ),

    # 25. FROGGER - Cross the Road
    "frogger": ThemeColors(
        bg_primary="#1a3a1a",
        bg_secondary="#0d2a0d",
        bg_tertiary="#2a4a2a",
        bg_input="#051005",
        bg_terminal="#000800",
        fg_primary="#ffffff",
        fg_secondary="#ddffdd",
        fg_terminal="#00ff00",
        accent_primary="#00aa00",  # Frog green
        accent_hover="#00dd00",
        accent_pressed="#008800",
        accent_border="#44ff44",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff0000",
        border_primary="#0066cc",  # River blue
        border_secondary="#0088ff",
        heading_color="#00dd00",
        name="Frogger",
        description="Ribbit!"
    ),

    # 26. JOUST - Flying Ostriches
    "joust": ThemeColors(
        bg_primary="#3a1a00",
        bg_secondary="#2a1000",
        bg_tertiary="#4a2a00",
        bg_input="#1a0800",
        bg_terminal="#0a0400",
        fg_primary="#ffeecc",
        fg_secondary="#ffddaa",
        fg_terminal="#ffcc88",
        accent_primary="#ff8800",  # Lava orange
        accent_hover="#ffaa33",
        accent_pressed="#cc6600",
        accent_border="#ffcc66",
        status_ok="#ffee00",  # Egg yellow
        status_warning="#ff8800",
        status_error="#ff0000",
        border_primary="#ff6600",
        border_secondary="#ff8833",
        heading_color="#ffaa00",
        name="Joust",
        description="Flap flap flap!"
    ),

    # 27. MISSILE COMMAND - Defend the Cities
    "missilecommand": ThemeColors(
        bg_primary="#000033",
        bg_secondary="#000022",
        bg_tertiary="#000044",
        bg_input="#000011",
        bg_terminal="#000000",
        fg_primary="#00ffff",
        fg_secondary="#00dddd",
        fg_terminal="#00ffff",
        accent_primary="#00ffff",  # Missile cyan
        accent_hover="#44ffff",
        accent_pressed="#00cccc",
        accent_border="#88ffff",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff0000",
        border_primary="#0088aa",
        border_secondary="#00aacc",
        heading_color="#00ffff",
        name="Missile Command",
        description="The end!"
    ),

    # 28. TEMPEST - Tube Shooter
    "tempest": ThemeColors(
        bg_primary="#1a001a",
        bg_secondary="#0d000d",
        bg_tertiary="#2a002a",
        bg_input="#080008",
        bg_terminal="#000000",
        fg_primary="#ffff00",
        fg_secondary="#ffcc00",
        fg_terminal="#ffff00",
        accent_primary="#ff00ff",  # Tempest magenta
        accent_hover="#ff44ff",
        accent_pressed="#cc00cc",
        accent_border="#ff88ff",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff0000",
        border_primary="#660066",
        border_secondary="#880088",
        heading_color="#ff00ff",
        name="Tempest",
        description="Geometric madness!"
    ),

    # 29. TRON - The Grid
    "tron": ThemeColors(
        bg_primary="#000a1a",
        bg_secondary="#000510",
        bg_tertiary="#001a2a",
        bg_input="#000208",
        bg_terminal="#000000",
        fg_primary="#00ffff",
        fg_secondary="#00dddd",
        fg_terminal="#00ffff",
        accent_primary="#00ffff",  # Light cycle cyan
        accent_hover="#44ffff",
        accent_pressed="#00cccc",
        accent_border="#88ffff",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff6600",  # Orange program
        border_primary="#0088aa",
        border_secondary="#00aacc",
        heading_color="#00ffff",
        name="TRON",
        description="I fight for the users!"
    ),

    # 30. BURGER TIME - Chef Adventures
    "burgertime": ThemeColors(
        bg_primary="#4a2810",
        bg_secondary="#3a1808",
        bg_tertiary="#5a3820",
        bg_input="#2a1004",
        bg_terminal="#1a0802",
        fg_primary="#ffffff",
        fg_secondary="#ffeecc",
        fg_terminal="#ffcc88",
        accent_primary="#ff8800",  # Burger orange
        accent_hover="#ffaa33",
        accent_pressed="#cc6600",
        accent_border="#ffcc66",
        status_ok="#ffee00",  # Cheese yellow
        status_warning="#ff8800",
        status_error="#ff0000",  # Ketchup red
        border_primary="#663311",
        border_secondary="#884422",
        heading_color="#ffaa00",
        name="Burger Time",
        description="Hot dog!",
        texture=TEXTURES["fabric"]
    ),

    # ==================== YOUTUBER THEMES ====================

    # 31. NETWORKCHUCK - Coffee Powered Hacking
    "networkchuck": ThemeColors(
        bg_primary="#1a0f0a",  # Dark coffee brown
        bg_secondary="#0f0805",
        bg_tertiary="#2a1f1a",
        bg_input="#050302",
        bg_terminal="#000000",
        fg_primary="#f5deb3",  # Cream color
        fg_secondary="#d4b896",
        fg_terminal="#00ff00",  # Matrix green
        accent_primary="#d2691e",  # Coffee orange
        accent_hover="#e07a2e",
        accent_pressed="#b25a1e",
        accent_border="#f4a460",
        status_ok="#00ff00",
        status_warning="#ffa500",
        status_error="#dc143c",
        border_primary="#3a2f2a",
        border_secondary="#4a3f3a",
        heading_color="#d2691e",
        name="NetworkChuck",
        description="Coffee-powered ethical hacking!",
        texture=TEXTURES["rootweave"],
        youtube_channel="@NetworkChuck"
    ),

    # 32. LINUS TECH TIPS - Orange & Black
    "linustechtips": ThemeColors(
        bg_primary="#1a1a1a",  # Black
        bg_secondary="#0d0d0d",
        bg_tertiary="#2a2a2a",
        bg_input="#050505",
        bg_terminal="#000000",
        fg_primary="#ffffff",
        fg_secondary="#e0e0e0",
        fg_terminal="#ff6600",
        accent_primary="#ff6600",  # LTT orange
        accent_hover="#ff8833",
        accent_pressed="#cc5200",
        accent_border="#ff9944",
        status_ok="#00ff00",
        status_warning="#ffaa00",
        status_error="#ff0000",
        border_primary="#333333",
        border_secondary="#444444",
        heading_color="#ff6600",
        name="Linus Tech Tips",
        description="Tech reviews at ludicrous speed!",
        texture=TEXTURES["tech_mesh"],
        youtube_channel="@LinusTechTips"
    ),

    # 33. DAVID BOMBAL - Network Blue
    "davidbombal": ThemeColors(
        bg_primary="#0a1628",  # Deep navy
        bg_secondary="#050c18",
        bg_tertiary="#1a2638",
        bg_input="#030810",
        bg_terminal="#000508",
        fg_primary="#e0f0ff",
        fg_secondary="#c0d0e0",
        fg_terminal="#00ffff",  # Cyan
        accent_primary="#0066cc",  # Network blue
        accent_hover="#0080ff",
        accent_pressed="#0044aa",
        accent_border="#3399ff",
        status_ok="#00ff88",
        status_warning="#ffaa00",
        status_error="#ff3344",
        border_primary="#1a3050",
        border_secondary="#2a4060",
        heading_color="#0099ff",
        name="David Bombal",
        description="Networking & Cybersecurity mastery!",
        texture=TEXTURES["fine_grid"],
        youtube_channel="@davidbombal"
    ),

    # 34. JOHN HAMMOND - CTF Purple
    "johnhammond": ThemeColors(
        bg_primary="#1a0a1a",  # Deep purple-black
        bg_secondary="#0d050d",
        bg_tertiary="#2a1a2a",
        bg_input="#050205",
        bg_terminal="#000000",
        fg_primary="#e0d0ff",
        fg_secondary="#c0b0e0",
        fg_terminal="#aa88ff",
        accent_primary="#8844ff",  # Purple
        accent_hover="#aa66ff",
        accent_pressed="#6622dd",
        accent_border="#bb88ff",
        status_ok="#00ff44",
        status_warning="#ffcc44",
        status_error="#ff4444",
        border_primary="#3a2a3a",
        border_secondary="#4a3a4a",
        heading_color="#aa66ff",
        name="John Hammond",
        description="CTF challenges & malware analysis!",
        texture=TEXTURES["crosshatch"],
        youtube_channel="@_JohnHammond"
    ),

    # 35. MENTAL OUTLAW - Dark Hacker
    "mentaloutlaw": ThemeColors(
        bg_primary="#0a0a0a",  # Near black
        bg_secondary="#050505",
        bg_tertiary="#151515",
        bg_input="#000000",
        bg_terminal="#000000",
        fg_primary="#00ff00",  # Classic terminal green
        fg_secondary="#00dd00",
        fg_terminal="#00ff00",
        accent_primary="#00aa00",  # Dark green
        accent_hover="#00cc00",
        accent_pressed="#008800",
        accent_border="#00ff00",
        status_ok="#00ff00",
        status_warning="#ffff00",
        status_error="#ff0000",
        border_primary="#1a1a1a",
        border_secondary="#2a2a2a",
        heading_color="#00ff00",
        name="Mental Outlaw",
        description="Privacy, Linux & Digital Freedom!",
        texture=TEXTURES["houndstooth"],
        youtube_channel="@MentalOutlaw"
    ),

    # 36. IPPSEC - Penetration Testing Red
    "ippsec": ThemeColors(
        bg_primary="#1a0808",  # Dark red-black
        bg_secondary="#0d0404",
        bg_tertiary="#2a1818",
        bg_input="#050202",
        bg_terminal="#000000",
        fg_primary="#ffdddd",
        fg_secondary="#eecccc",
        fg_terminal="#ff4444",
        accent_primary="#cc0000",  # Red
        accent_hover="#ee2222",
        accent_pressed="#990000",
        accent_border="#ff4444",
        status_ok="#00ff00",
        status_warning="#ff8800",
        status_error="#ff0000",
        border_primary="#3a1818",
        border_secondary="#4a2828",
        heading_color="#ff3333",
        name="IppSec",
        description="HackTheBox walkthroughs!",
        texture=TEXTURES["carbon"],
        youtube_channel="@ippsec"
    ),
}


def generate_stylesheet(theme_name: str = "sonic") -> str:
    """
    Generate Qt stylesheet for the specified theme

    Args:
        theme_name: Name of the theme to use

    Returns:
        Complete Qt stylesheet string
    """
    theme = THEMES.get(theme_name, THEMES["sonic"])

    # Get texture pattern
    texture_bg = f"background-image: {theme.texture};" if theme.texture and theme.texture != "none" else ""

    return f"""
/* ==================== {theme.name.upper()} THEME ==================== */
/* {theme.description} */

/* Main Application */
QMainWindow {{
    background-color: {theme.bg_primary};
    {texture_bg}
    color: {theme.fg_primary};
}}

QWidget {{
    background-color: {theme.bg_primary};
    color: {theme.fg_primary};
    font-family: "Ubuntu", "Segoe UI", sans-serif;
    font-size: 10pt;
}}

/* Menu Bar */
QMenuBar {{
    background-color: {theme.bg_secondary};
    color: {theme.fg_primary};
    border-bottom: 1px solid {theme.border_primary};
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 5px 10px;
}}

QMenuBar::item:selected {{
    background-color: {theme.accent_primary};
}}

QMenu {{
    background-color: {theme.bg_secondary};
    color: {theme.fg_primary};
    border: 1px solid {theme.border_primary};
}}

QMenu::item:selected {{
    background-color: {theme.accent_primary};
}}

/* Tool Bar */
QToolBar {{
    background-color: {theme.bg_secondary};
    border: none;
    spacing: 3px;
    padding: 5px;
}}

QToolButton {{
    background-color: {theme.bg_tertiary};
    color: {theme.fg_primary};
    border: 1px solid {theme.border_primary};
    border-radius: 3px;
    padding: 5px;
    margin: 2px;
}}

QToolButton:hover {{
    background-color: {theme.border_secondary};
    border: 1px solid {theme.accent_border};
}}

QToolButton:pressed {{
    background-color: {theme.accent_primary};
}}

QToolButton:checked {{
    background-color: {theme.accent_primary};
    border: 1px solid {theme.accent_border};
}}

/* Status Bar */
QStatusBar {{
    background-color: {theme.bg_secondary};
    color: {theme.fg_primary};
    border-top: 1px solid {theme.border_primary};
}}

QStatusBar::item {{
    border: none;
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {theme.border_primary};
    background-color: {theme.bg_primary};
}}

QTabBar::tab {{
    background-color: {theme.bg_secondary};
    color: {theme.fg_secondary};
    border: 1px solid {theme.border_primary};
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {theme.bg_primary};
    color: {theme.fg_primary};
    border-bottom: 2px solid {theme.accent_primary};
}}

QTabBar::tab:hover {{
    background-color: {theme.bg_tertiary};
    color: {theme.fg_primary};
}}

/* Push Button */
QPushButton {{
    background-color: {theme.accent_primary};
    color: {theme.fg_primary};
    border: 1px solid {theme.accent_border};
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {theme.accent_hover};
    border: 1px solid {theme.accent_border};
}}

QPushButton:pressed {{
    background-color: {theme.accent_pressed};
}}

QPushButton:disabled {{
    background-color: {theme.bg_tertiary};
    color: {theme.fg_secondary};
    border: 1px solid {theme.border_primary};
}}

QPushButton[danger="true"] {{
    background-color: {theme.status_error};
    border: 1px solid {theme.status_error};
}}

QPushButton[danger="true"]:hover {{
    background-color: #ff3344;
}}

/* Line Edit */
QLineEdit {{
    background-color: {theme.bg_input};
    color: {theme.fg_primary};
    border: 1px solid {theme.border_primary};
    border-radius: 3px;
    padding: 5px;
    selection-background-color: {theme.accent_primary};
}}

QLineEdit:focus {{
    border: 1px solid {theme.accent_border};
}}

QLineEdit:disabled {{
    background-color: {theme.bg_secondary};
    color: {theme.fg_secondary};
}}

/* Text Edit */
QTextEdit, QPlainTextEdit {{
    background-color: {theme.bg_terminal};
    color: {theme.fg_terminal};
    border: 1px solid {theme.border_primary};
    border-radius: 3px;
    padding: 5px;
    font-family: "Ubuntu Mono", "Courier New", monospace;
    selection-background-color: {theme.accent_primary};
}}

/* Combo Box */
QComboBox {{
    background-color: {theme.bg_input};
    color: {theme.fg_primary};
    border: 1px solid {theme.border_primary};
    border-radius: 3px;
    padding: 5px;
}}

QComboBox:hover {{
    border: 1px solid {theme.accent_border};
}}

QComboBox::drop-down {{
    border: none;
}}

QComboBox::down-arrow {{
    image: url(none);
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {theme.fg_primary};
    margin-right: 5px;
}}

QComboBox QAbstractItemView {{
    background-color: {theme.bg_secondary};
    color: {theme.fg_primary};
    border: 1px solid {theme.border_primary};
    selection-background-color: {theme.accent_primary};
}}

/* Spin Box */
QSpinBox, QDoubleSpinBox {{
    background-color: {theme.bg_input};
    color: {theme.fg_primary};
    border: 1px solid {theme.border_primary};
    border-radius: 3px;
    padding: 5px;
}}

/* Check Box */
QCheckBox {{
    color: {theme.fg_primary};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {theme.border_primary};
    border-radius: 3px;
    background-color: {theme.bg_input};
}}

QCheckBox::indicator:checked {{
    background-color: {theme.accent_primary};
    border: 1px solid {theme.accent_border};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {theme.accent_border};
}}

/* Radio Button */
QRadioButton {{
    color: {theme.fg_primary};
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {theme.border_primary};
    border-radius: 9px;
    background-color: {theme.bg_input};
}}

QRadioButton::indicator:checked {{
    background-color: {theme.accent_primary};
    border: 1px solid {theme.accent_border};
}}

/* Progress Bar */
QProgressBar {{
    background-color: {theme.bg_input};
    border: 1px solid {theme.border_primary};
    border-radius: 3px;
    text-align: center;
    color: {theme.fg_primary};
}}

QProgressBar::chunk {{
    background-color: {theme.accent_primary};
    border-radius: 2px;
}}

/* Slider */
QSlider::groove:horizontal {{
    border: 1px solid {theme.border_primary};
    height: 8px;
    background-color: {theme.bg_input};
    border-radius: 4px;
}}

QSlider::handle:horizontal {{
    background-color: {theme.accent_primary};
    border: 1px solid {theme.accent_border};
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {theme.accent_hover};
}}

/* Scroll Bar */
QScrollBar:vertical {{
    background-color: {theme.bg_secondary};
    width: 12px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {theme.border_secondary};
    border-radius: 6px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {theme.accent_primary};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {theme.bg_secondary};
    height: 12px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {theme.border_secondary};
    border-radius: 6px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {theme.accent_primary};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Table Widget */
QTableWidget, QTableView {{
    background-color: {theme.bg_primary};
    alternate-background-color: {theme.bg_secondary};
    gridline-color: {theme.border_primary};
    border: 1px solid {theme.border_primary};
    selection-background-color: {theme.accent_primary};
}}

QTableWidget::item, QTableView::item {{
    padding: 5px;
    color: {theme.fg_primary};
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {theme.accent_primary};
}}

QHeaderView::section {{
    background-color: {theme.bg_secondary};
    color: {theme.fg_primary};
    padding: 6px;
    border: none;
    border-right: 1px solid {theme.border_primary};
    border-bottom: 1px solid {theme.border_primary};
    font-weight: bold;
}}

/* Tree Widget */
QTreeWidget, QTreeView {{
    background-color: {theme.bg_primary};
    alternate-background-color: {theme.bg_secondary};
    border: 1px solid {theme.border_primary};
    selection-background-color: {theme.accent_primary};
}}

QTreeWidget::item, QTreeView::item {{
    padding: 3px;
    color: {theme.fg_primary};
}}

QTreeWidget::item:selected, QTreeView::item:selected {{
    background-color: {theme.accent_primary};
}}

/* List Widget */
QListWidget, QListView {{
    background-color: {theme.bg_primary};
    alternate-background-color: {theme.bg_secondary};
    border: 1px solid {theme.border_primary};
    selection-background-color: {theme.accent_primary};
}}

QListWidget::item, QListView::item {{
    padding: 5px;
    color: {theme.fg_primary};
}}

QListWidget::item:selected, QListView::item:selected {{
    background-color: {theme.accent_primary};
}}

/* Group Box */
QGroupBox {{
    border: 1px solid {theme.border_primary};
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    color: {theme.fg_primary};
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {theme.border_primary};
}}

QSplitter::handle:hover {{
    background-color: {theme.accent_primary};
}}

/* Dock Widget */
QDockWidget {{
    color: {theme.fg_primary};
}}

QDockWidget::title {{
    background-color: {theme.bg_secondary};
    padding: 5px;
    border: 1px solid {theme.border_primary};
}}

/* Tool Tip */
QToolTip {{
    background-color: {theme.bg_secondary};
    color: {theme.fg_primary};
    border: 1px solid {theme.accent_border};
    padding: 5px;
    border-radius: 3px;
}}

/* Label */
QLabel {{
    color: {theme.fg_primary};
    background-color: transparent;
}}

QLabel[heading="true"] {{
    font-size: 14pt;
    font-weight: bold;
    color: {theme.heading_color};
}}

QLabel[status="ok"] {{
    color: {theme.status_ok};
}}

QLabel[status="warning"] {{
    color: {theme.status_warning};
}}

QLabel[status="error"] {{
    color: {theme.status_error};
}}
"""


def get_theme_list():
    """Get list of all available themes"""
    return [(key, theme.name, theme.description) for key, theme in THEMES.items()]


def get_theme(theme_name: str = "sonic") -> str:
    """
    Get stylesheet for specified theme

    Args:
        theme_name: Theme identifier

    Returns:
        Complete Qt stylesheet
    """
    return generate_stylesheet(theme_name)


# For backwards compatibility
def get_dark_theme() -> str:
    """Get the default dark theme (Sonic)"""
    return generate_stylesheet("sonic")
