# 🎉 Gattrose-NG - New Features Added!

## ✅ Feature #1: One-Time Sudo Authentication

**Problem Solved**: Previously, you had to enter your sudo password multiple times during prerequisite installation.

**New Behavior**:
- Gattrose-NG now requests sudo authentication **ONCE** at startup
- Password is cached for the entire session
- No more repeated prompts!

### How It Works

```bash
python3 gattrose-ng.py
```

**What you'll see:**
```
============================================================
  Gattrose-NG requires elevated privileges
  for wireless network operations
============================================================

[*] Requesting sudo authentication...
[sudo] password for user: █

[+] Authentication successful

============================================================
  Gattrose-NG v1.0.0
  Wireless Penetration Testing Suite
============================================================
```

After this one-time authentication:
- Virtual environment setup works seamlessly
- Prerequisite installation proceeds without interruption
- All wireless operations have necessary permissions
- Session remains authenticated until you close Gattrose

### Benefits

✅ **Single password entry** - Authenticate once, use all day
✅ **Better user experience** - No authentication interruptions
✅ **Prerequisite installer works smoothly** - Install all tools without repeated prompts
✅ **Wireless operations ready** - Monitor mode, scanning, everything works

---

## ✅ Feature #2: 15 New 80s Arcade Themes!

**Added**: 15 brand new themes inspired by classic 80s arcade games!

**Total Themes Now**: **30 retro gaming themes**
- 15 Epic 90s Console Themes (Sonic, Mario, DOOM, etc.)
- 15 Classic 80s Arcade Themes (NEW!)

### The New 80s Arcade Collection

| # | Theme | Description | Vibe |
|---|-------|-------------|------|
| 16 | **Pac-Man** 💛 | Wakka wakka wakka! | Yellow on black, classic arcade |
| 17 | **Space Invaders** 👾 | Pew pew pew! | Green CRT monitor aesthetic |
| 18 | **Donkey Kong (Arcade)** 🦍 | It's on! | Blue construction, red girders |
| 19 | **Galaga** 🚀 | Challenging stage! | Deep space shooter |
| 20 | **Asteroids** ☄️ | Vector graphics glory! | White on black vectors |
| 21 | **Centipede** 🐛 | Mushroom mayhem! | Psychedelic magenta |
| 22 | **Defender** 🛸 | Defend the humans! | Orange scanner vibes |
| 23 | **Dig Dug** ⛏️ | Pump 'em up! | Underground brown and blue |
| 24 | **Q*bert** 🎯 | @!#?@! | Isometric pyramid orange |
| 25 | **Frogger** 🐸 | Ribbit! | Forest green, river blue |
| 26 | **Joust** 🦅 | Flap flap flap! | Lava orange and brown |
| 27 | **Missile Command** 🚀 | The end! | Cyan missile tracers |
| 28 | **Tempest** 🌀 | Geometric madness! | Magenta and yellow tubes |
| 29 | **TRON** 💿 | I fight for the users! | The Grid - electric cyan |
| 30 | **Burger Time** 🍔 | Hot dog! | Food colors - browns and cheese |

### Theme Highlights

**🎨 Classic Arcade Aesthetics:**
- **Pac-Man**: Pure yellow on black - maximum nostalgia!
- **Space Invaders**: Green-on-black CRT monitor look - perfect for terminals
- **TRON**: Electric cyan grid - cyberpunk perfection

**🕹️ Retro Color Palettes:**
- **Galaga**: Deep space blues
- **Tempest**: Magenta geometric patterns
- **Missile Command**: Cyan missile tracers on night sky

**🏆 Unique Vibes:**
- **Asteroids**: White vector graphics on black
- **Centipede**: Psychedelic magenta mushroom forest
- **Burger Time**: Fun food-themed colors

### How to Use the New Themes

1. **Launch Gattrose-NG**:
   ```bash
   python3 gattrose-ng.py
   ```

2. **Navigate to Settings** tab

3. **Select a theme** from the dropdown:
   - All 30 themes available instantly
   - Live preview shows description
   - Themes apply immediately

4. **Theme is saved** automatically to your config

### Theme Recommendations

**Want Classic Hacker Vibes?**
→ Try **Space Invaders** (green on black) or **TRON** (cyan grid)

**Maximum Contrast for Readability?**
→ **Pac-Man** (yellow on black) or **Asteroids** (white vectors)

**Cyberpunk Aesthetic?**
→ **TRON**, **Missile Command**, **Tempest**

**Retro Arcade Feel?**
→ **Galaga**, **Donkey Kong Arcade**, **Defender**

**Something Fun?**
→ **Burger Time**, **Q*bert**, **Frogger**

---

## 📊 Summary of Changes

### Files Modified

**Core Launcher:**
- `gattrose-ng.py` - Added `request_sudo_at_startup()` function

**Theme System:**
- `src/gui/theme.py` - Added 15 new 80s themes (16-30)
- `src/gui/main_window.py` - Updated About dialog to show "30 themes"

**Documentation:**
- `README.md` - Updated to show 30 themes, one-time sudo
- `THEMES.md` - Added complete 80s themes section
- `NEW_FEATURES.md` - This file!

### New Color Palettes Added

Each of the 15 new 80s themes includes:
- 5 background shades (primary, secondary, tertiary, input, terminal)
- 3 foreground colors (primary, secondary, terminal)
- 4 accent colors (primary, hover, pressed, border)
- 3 status colors (ok, warning, error)
- 3 UI colors (borders, headings)

**Total**: 18+ carefully chosen colors per theme × 15 new themes = 270+ new color definitions!

---

## 🚀 Quick Start with New Features

### Step 1: Launch with One-Time Sudo

```bash
cd /home/eurrl/Documents/Code\ \&\ Scripts/gattrose-ng
python3 gattrose-ng.py
```

**Enter password once** when prompted. That's it!

### Step 2: Try the New Themes

1. Main window opens
2. Go to **Settings** tab
3. Under **Appearance**, open theme dropdown
4. **Try these new 80s themes:**
   - **Pac-Man** for classic arcade
   - **TRON** for cyberpunk grid
   - **Space Invaders** for hacker green
   - **Centipede** for psychedelic vibes
   - **Asteroids** for minimal vectors

### Step 3: Start Hacking!

With sudo authenticated and your favorite retro theme selected:
- Scan wireless networks
- Capture handshakes
- Analyze WiGLE data
- All with nostalgic gaming vibes!

---

## 🎯 Why These Changes Matter

### One-Time Sudo Authentication

**Before:**
```
[!] Failed to install aircrack-ng
    Error: sudo: Authentication failed
[!] Failed to install wireless-tools
    Error: sudo: Authentication failed
[!] Failed to install sqlite3
    Error: sudo: Authentication failed
```

**After:**
```
[*] Requesting sudo authentication...
[+] Authentication successful

[+] aircrack-ng installed successfully
[+] wireless-tools installed successfully
[+] sqlite3 installed successfully
```

### 30 Retro Themes

**Before:** 15 themes (all 90s)

**After:** 30 themes (15 × 90s + 15 × 80s)
- **Double the nostalgia!**
- **Classic arcade aesthetics**
- **More variety for different moods**
- **80s + 90s gaming perfection**

---

## 💡 Pro Tips

### Sudo Authentication

1. **Run directly** - Just `python3 gattrose-ng.py` (no need for sudo prefix)
2. **Authenticate early** - Password prompt happens right at startup
3. **Stay authenticated** - Works for the entire session
4. **Close and restart** - Next session will ask for password again (security!)

### Theme Selection

1. **Experiment** - Try different themes for different tasks
2. **Match your mood** - Arcade vibes for quick scans, dark themes for long sessions
3. **Color contrast** - Pac-Man/Space Invaders for maximum terminal readability
4. **Cyberpunk coding** - TRON theme for that futuristic hacker feel
5. **Nostalgia trip** - Galaga, Defender, Tempest for pure 80s vibes

### Combine Both Features

**The Perfect Gattrose Session:**
```bash
# 1. Launch (authenticate once)
python3 gattrose-ng.py
[sudo] password: ****

# 2. Choose your theme
Settings → Appearance → Select "TRON"

# 3. Install prerequisites (no more password prompts!)
Click "Install Required Tools"
✓ All tools install smoothly

# 4. Start wireless testing with cyberpunk vibes!
Dashboard → Start Network Scan
```

---

## 📚 Full Theme List (All 30)

### 90s Console Era (1-15)
1. Sonic the Hedgehog
2. Super Mario World
3. DOOM
4. Mortal Kombat
5. Street Fighter II
6. Chrono Trigger
7. Final Fantasy VI
8. Earthworm Jim
9. Donkey Kong Country
10. Mega Man X
11. Metroid
12. Castlevania
13. GoldenEye 007
14. Banjo-Kazooie
15. Crash Bandicoot

### 80s Arcade Era (16-30) ⭐ NEW!
16. Pac-Man
17. Space Invaders
18. Donkey Kong (Arcade)
19. Galaga
20. Asteroids
21. Centipede
22. Defender
23. Dig Dug
24. Q*bert
25. Frogger
26. Joust
27. Missile Command
28. Tempest
29. TRON
30. Burger Time

---

## ✨ What's Next?

With these new features, Gattrose-NG is now even more powerful:
- ✅ Seamless authentication
- ✅ 30 retro themes
- ✅ Professional wireless testing
- ✅ Maximum nostalgia

**Ready to hack wireless networks in style!** 🎮🔵💨

Choose your era (80s or 90s), select your theme, and start pwning networks!

---

**All times in 24-hour format. Always.**

**Wakka wakka wakka!** 💛👾

---

## 🆕 Feature #8: Scanner Subtabs (November 2025)

**Enhanced Network Organization**

The Scanner tab now features **two intelligent subtabs** that automatically categorize networks:

### 🎯 Networks with Clients
- **High-priority targets** with active connected devices
- Better for handshake capture (clients provide 4-way handshake)
- Automatically populated when clients associate

### 📡 Networks without Clients  
- **Lower-priority targets** with no connected devices
- Standalone access points
- Good for WPS attacks and reconnaissance

### How It Works
- Networks **automatically move** between tabs based on client activity
- When a client connects → network moves to "with Clients" tab
- When all clients disconnect → network moves to "without Clients" tab
- Real-time categorization as scanning progresses

### Benefits
✅ **Better target selection** - Focus on high-value networks first
✅ **Automatic organization** - No manual sorting needed
✅ **Attack planning** - Choose handshake capture vs WPS attacks
✅ **Clear visualization** - Instant overview of network landscape

---

## 🆕 Feature #9: Animated Signal Strength Bars (November 2025)

**Living, Breathing Signal Indicators**

Signal strength bars now **pulse and shift** with a smooth animation:

### Visual Design
- Progressive bar heights: **▂▃▅▆█** (5 levels)
- Color-coded by signal strength:
  - **Bright cyan/green** (Excellent: -30 to -50 dBm)
  - **Green** (Good: -50 to -60 dBm)
  - **Yellow/Orange** (Fair: -60 to -70 dBm)
  - **Orange** (Poor: -70 to -80 dBm)
  - **Red** (Weak: -80 to -100 dBm)

### Animation Effect
- **Sine wave pulsing** - Smooth breathing effect
- **Brightness modulation** - 70% to 100% brightness cycle
- **150ms refresh rate** - Smooth, non-jarring animation
- **Automatic start/stop** - Only animates during active scans

### Placement
- **SSID column** for Access Points
- **MAC column** for Clients
- Integrated with text display for compact view

---

## 🆕 Feature #10: Channel Frequency Display (November 2025)

**Know Your Frequencies**

Every network now shows both **channel number AND actual frequency**:

### Format
```
6 (2437 MHz)    ← 2.4 GHz band
36 (5180 MHz)   ← 5 GHz band
```

### Band Support
- **2.4 GHz**: Channels 1-14 (2412-2484 MHz)
- **5 GHz**: Channels 36-165 (5180-5825 MHz)
- **6 GHz**: Channels >233 (5955+ MHz)

### Benefits
✅ **Spectrum awareness** - See actual radio frequencies
✅ **Interference analysis** - Identify overlapping channels
✅ **Band identification** - Instantly recognize 2.4 vs 5 GHz
✅ **Professional display** - Matches spectrum analyzer output

---

## 🆕 Feature #11: OUI Database Management (November 2025)

**Complete MAC Vendor Database Control**

Manage the **38,000+ vendor database** directly from Settings:

### Statistics Display
View comprehensive database info:
- **Total vendor count** (IEEE + Wireshark)
- **Record breakdown** by source
- **Last update timestamp** and age
- **Update recommendations** (every 30-60 days)

### Update Button
- **Download latest data** from IEEE and Wireshark
- **Threaded background updates** - UI stays responsive
- **Progress bar** with status updates
- **2-5 MB download** with confirmation dialog
- **Success notifications** with detailed statistics

### Database Sources
1. **IEEE OUI Database** - Official manufacturer assignments
2. **Wireshark Manufacturer DB** - Extended vendor data

### Access
⚙️ **Settings** → Scroll to **"OUI Database (MAC Vendor Lookup)"** section

### Benefits
✅ **Always up-to-date** - Latest vendor assignments
✅ **Accurate identification** - Correct manufacturer names
✅ **Easy management** - One-click updates
✅ **Transparent statistics** - Know what you have

---

## 🆕 Feature #12: Channel Congestion Visualization (November 2025)

**See Channel Usage at a Glance**

Dashboard now shows **channel distribution with visual bars**:

### Display Format
```
Ch 1:  3 ▂▂▂     ← Green (clear)
Ch 6:  15 ██████████ ← Red (congested)
Ch 11: 7 ▆▆▆▆▆   ← Orange (busy)
```

### Color Coding
- **🔴 Red** (█): Very congested (8+ networks)
- **🟠 Orange** (▆): Congested (5-7 networks)  
- **🟡 Yellow** (▄): Moderate (3-4 networks)
- **🟢 Green** (▂): Clear (1-2 networks)

### Features
- **Relative bar width** - Scaled to max channel usage
- **Real-time updates** - Changes as networks appear/disappear
- **Instant visualization** - No counting needed

### Use Cases
✅ **Channel selection** - Choose least congested for rogue AP
✅ **Interference analysis** - Identify crowded spectrum
✅ **Network planning** - Optimize channel allocation
✅ **Attack strategy** - Target isolated vs crowded channels

---

## 🆕 Feature #13: WPS Attack Integration (November 2025)

**Automated WPS PIN Recovery**

Full integration of **Reaver and Bully** for WPS attacks:

### Attack Methods
1. **Reaver** - Primary WPS PIN brute-force tool
2. **Bully** - Alternative attack with different strategies

### Features
- **Auto-launch** from WPS Networks tab
- **Progress tracking** with attempt counter
- **PIN recovery** - Extracts WPS PIN from AP
- **PSK recovery** - Derives WPA password from PIN
- **Auto-save** - Stores PIN/PSK in database
- **Status updates** - Real-time attack progress

### Workflow
1. Scanner detects WPS-enabled network
2. Network auto-added to WPS Networks tab
3. Right-click → "Launch WPS Attack"
4. Attack runs in Auto Attack tab
5. PIN/PSK saved when cracked

---

## 🆕 Feature #14: Auto-Cracking Feature (November 2025)

**Automatic Password Cracking**

Captured handshakes **automatically crack** with wordlists:

### Features
- **CPU-based** - aircrack-ng integration
- **Auto-detection** - Finds rockyou.txt and common wordlists
- **Progress monitoring** - Keys tested, ETA calculation
- **Auto-save** - Cracked passwords stored in database
- **Configurable** - Enable/disable in Auto Attack tab

### Supported Wordlists
1. `/usr/share/wordlists/rockyou.txt` (Kali default)
2. `/usr/share/dict/words`
3. `data/wordlists/common-passwords.txt`

### Workflow
1. Handshake captured automatically
2. If auto-crack enabled → starts immediately
3. Progress shown in Auto Attack tab
4. Password saved when found
5. Notification on success/failure

---

## 🆕 Feature #15: Bluetooth Scanner (November 2025)

**Full Bluetooth Device Discovery**

Complete Bluetooth scanning with multiple tools:

### Scanning Methods
1. **bluetoothctl** (primary) - Full device info
2. **hcitool** (fallback) - Basic scanning
3. **btmgmt** (alternative) - Management interface

### Extracted Information
- **Device name** and MAC address
- **RSSI** signal strength
- **Service profiles** (A2DP, AVRCP, HFP, etc.)
- **Device type** classification
- **Manufacturer** data

### Features
- **Thread-safe updates** - Background scanning
- **Auto-fallback** - Tries multiple tools
- **Context menu** - Pair, info, copy MAC
- **Visual indicators** - Device type icons

### Access
🔵 **Bluetooth** tab → **"Start Bluetooth Scan"**

---

## 🆕 Feature #16: Web Server & API (November 2025)

**Remote Control via HTTP**

Full Flask-based web interface and REST API:

### Features
- **Web Interface** - Access at http://localhost:5000
- **REST API** - JSON endpoints for all features
- **Auto-documentation** - /api/docs lists all endpoints
- **CORS enabled** - Use from any client
- **Easy launcher** - `./bin/start-webserver.sh`

### Key Endpoints
- `/api/dashboard/stats` - Statistics
- `/api/networks` - Network listing (paginated)
- `/api/clients` - Client listing
- `/api/handshakes` - Capture management
- `/api/attacks/queue` - Attack queue status
- `/api/export/*` - CSV exports

### Use Cases
✅ **Mobile access** - Control from phone/tablet
✅ **Remote monitoring** - Check scans from anywhere on network
✅ **API integration** - Build custom tools
✅ **Automation** - Script attacks and data collection

---

## 🆕 Feature #17: WiGLE Upload Support (November 2025)

**Contribute to Global WiFi Database**

Export and upload networks to WiGLE:

### Features
- **CSV export** - WiGLE format (WigleWifi-1.4)
- **Proper encryption mapping** - Correct AuthMode values
- **Auto-switch** - Opens WiGLE tab after export
- **GPS support** - Includes coordinates if available

### Workflow
1. Scanner → Right-click network → "Upload to WiGLE"
2. CSV created in `data/exports/`
3. Auto-switch to WiGLE tab
4. Upload manually to wigle.net

### Benefits
✅ **Global contribution** - Help map world's WiFi
✅ **Wardriving** - Track discovered networks
✅ **Geolocation** - Compare with WiGLE database

---

**🎉 All features ready to use! Restart Gattrose-NG to activate.**

