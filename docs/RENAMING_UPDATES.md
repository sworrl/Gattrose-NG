# Gattrose → Gattrose-NG Renaming Updates

**Date:** 2025-10-31
**Version:** 1.0.0

## Summary

Complete rebranding from "Gattrose" to "Gattrose-NG" throughout the entire codebase, including:
- File path references
- Environment variables
- Database names
- Configuration directories
- Installation paths
- Desktop integration

## Files Modified

### 1. **src/utils/config.py**
- Updated environment variables:
  - `GATTROSE_ROOT` → `GATTROSE_NG_ROOT`
  - `GATTROSE_PORTABLE` → `GATTROSE_NG_PORTABLE`
- Updated config directory:
  - `~/.config/gattrose` → `~/.config/gattrose-ng`

### 2. **src/database/manager.py**
- Updated environment variables:
  - `GATTROSE_ROOT` → `GATTROSE_NG_ROOT`
  - `GATTROSE_PORTABLE` → `GATTROSE_NG_PORTABLE`
- Updated database name:
  - `gattrose.db` → `gattrose-ng.db`
- Updated data directory:
  - `~/.local/share/gattrose/data` → `~/.local/share/gattrose-ng/data`

### 3. **gattrose-ng.py**
- Updated environment variables:
  - `GATTROSE_ROOT` → `GATTROSE_NG_ROOT`
  - `GATTROSE_PORTABLE` → `GATTROSE_NG_PORTABLE`
  - `GATTROSE_VERSION` → `GATTROSE_NG_VERSION`
- Made executable with `chmod +x`
- Already had proper shebang: `#!/usr/bin/env python3`

### 4. **install.py**
- Updated all installation paths:
  - System-wide: `/opt/gattrose` → `/opt/gattrose-ng`
  - User: `~/.local/share/gattrose` → `~/.local/share/gattrose-ng`
  - Data: `/var/lib/gattrose` → `/var/lib/gattrose-ng`
  - Config: `/etc/gattrose` → `/etc/gattrose-ng`
  - Config: `~/.config/gattrose` → `~/.config/gattrose-ng`
- Updated launcher script name:
  - `gattrose` → `gattrose-ng`
- Updated desktop file name:
  - `gattrose.desktop` → `gattrose-ng.desktop`
- Added icon copying to installation
- Updated desktop file to use custom icon
- Added "Run as Root" action to desktop file
- Changed Terminal from `false` to `true`

## New Files Created

### 1. **gattrose-ng.svg**
Custom icon featuring:
- WiFi signal arcs (3 levels) in blue gradient
- Broken lock symbolizing penetration testing
- Terminal elements (green cursor, scan lines)
- "NG" text at bottom
- Dark gradient background
- 256x256 SVG format

### 2. **gattrose-ng.png**
- Rasterized version of SVG icon
- 256x256 PNG format
- RGBA color with transparency
- 20KB file size

### 3. **gattrose-ng.desktop**
Desktop launcher file with:
- Full path to executable launcher
- Custom icon reference
- Terminal mode enabled
- System/Security/Network categories
- Wireless pentesting keywords
- "Run with sudo" action
- Executable permissions

## Path Changes Summary

| Item | Old Path | New Path |
|------|----------|----------|
| **Environment Variables** |
| Root path | `GATTROSE_ROOT` | `GATTROSE_NG_ROOT` |
| Portable mode | `GATTROSE_PORTABLE` | `GATTROSE_NG_PORTABLE` |
| Version | `GATTROSE_VERSION` | `GATTROSE_NG_VERSION` |
| **Database** |
| Database file | `gattrose.db` | `gattrose-ng.db` |
| Data directory (user) | `~/.local/share/gattrose/data` | `~/.local/share/gattrose-ng/data` |
| **Configuration** |
| Config directory (user) | `~/.config/gattrose` | `~/.config/gattrose-ng` |
| Config directory (system) | `/etc/gattrose` | `/etc/gattrose-ng` |
| **Installation** |
| Install directory (user) | `~/.local/share/gattrose` | `~/.local/share/gattrose-ng` |
| Install directory (system) | `/opt/gattrose` | `/opt/gattrose-ng` |
| Data directory (system) | `/var/lib/gattrose` | `/var/lib/gattrose-ng` |
| **Launcher** |
| Launcher script | `gattrose` | `gattrose-ng` |
| Desktop file | `gattrose.desktop` | `gattrose-ng.desktop` |

## How to Use

### Double-Click Launcher (Now Working!)

You can now launch Gattrose-NG by:

1. **Double-clicking the .desktop file:**
   ```
   /path/to/gattrose-ng/gattrose-ng.desktop
   ```

2. **Double-clicking gattrose-ng.py:**
   ```
   /path/to/gattrose-ng/gattrose-ng.py
   ```
   (Now has executable permissions and proper shebang)

3. **From terminal:**
   ```bash
   ./gattrose-ng.py
   # or
   python3 gattrose-ng.py
   ```

### Desktop Integration

To add Gattrose-NG to your application menu:

**Option 1: Copy desktop file to applications directory**
```bash
cp gattrose-ng.desktop ~/.local/share/applications/
```

**Option 2: Use the installer**
```bash
sudo python3 install.py
```

This will:
- Install to `~/.local/share/gattrose-ng/`
- Add launcher to `~/.local/bin/gattrose-ng`
- Create desktop entry with icon
- Set up virtual environment

Then you can:
- Find "Gattrose-NG" in your application menu
- Right-click for "Run with sudo" option
- Run from terminal with: `gattrose-ng`

## Icon Design

The custom icon features:
- **WiFi arcs**: Three levels representing signal strength scanning
- **Broken lock**: Symbolizing penetration testing and security auditing
- **Terminal elements**: Green blinking cursor and scan lines
- **Color scheme**:
  - Blue/cyan gradients for wireless signals
  - Red gradients for the lock (security)
  - Dark background for hacker aesthetic
  - Green terminal accents
- **"NG" badge**: Next Generation branding

## Testing

All changes have been applied. To verify:

1. **Check file permissions:**
   ```bash
   ls -la gattrose-ng.py gattrose-ng.desktop gattrose-ng.png
   ```

2. **Test launcher:**
   ```bash
   ./gattrose-ng.py
   ```

3. **Test desktop file:**
   Double-click `gattrose-ng.desktop` in your file manager

4. **Verify icon:**
   View `gattrose-ng.png` or `gattrose-ng.svg`

## Backwards Compatibility

⚠️ **Important:** These changes affect data and configuration paths. If you have existing data:

**Old data locations:**
- Database: `data/gattrose.db`
- Config: `config/config.yaml` or `~/.config/gattrose/config.yaml`

**New data locations:**
- Database: `data/gattrose-ng.db`
- Config: `config/config.yaml` or `~/.config/gattrose-ng/config.yaml`

**Migration (if needed):**
```bash
# Backup old data
cp data/gattrose.db data/gattrose-ng.db

# If installed mode, migrate config
cp -r ~/.config/gattrose ~/.config/gattrose-ng
cp -r ~/.local/share/gattrose ~/.local/share/gattrose-ng
```

## Summary of Improvements

✅ **Double-click support** - Both .py and .desktop files are now executable
✅ **Custom branding** - Unique icon representing wireless pentesting
✅ **Consistent naming** - All references use "gattrose-ng"
✅ **Desktop integration** - Proper .desktop file with icon
✅ **Sudo action** - Right-click option to run with elevated privileges
✅ **Terminal mode** - Runs in terminal to show output and request sudo
✅ **Updated paths** - All directories now use "gattrose-ng"

---

**Ready to use!** 🎮🔵💨

All times in 24-hour format. Always.
