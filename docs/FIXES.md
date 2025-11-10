# Fixes Applied to Gattrose-NG

## Issue #1: Project Name Correction ✅

**Problem**: Project was inconsistently named "Gattrose" instead of "Gattrose-NG"

**Fixed**: Updated all references throughout the codebase:

### Files Updated:
- `gattrose-ng.py` - Main launcher
- `src/gui/main_window.py` - Main window title, dashboard header, about dialog
- `src/gui/prereq_installer.py` - Installer window title and header
- `README.md` - Project title and description
- `THEMES.md` - Theme documentation
- `QUICKSTART.md` - Quick start guide

### Changed:
- Window titles: "Gattrose" → "Gattrose-NG"
- Headers and branding
- Documentation titles
- About dialogs
- APP_NAME constant

---

## Issue #2: Sudo Authentication Failures ✅

**Problem**: Prerequisite installer was failing with authentication errors:
```
sudo: Authentication failed, try again.
sudo-rs: Maximum 3 incorrect authentication attempts
```

**Root Cause**: The installer was trying to run multiple `sudo` commands sequentially without proper authentication handling.

### Fixes Applied:

#### 1. **Added pkexec Support** (`src/gui/prereq_installer.py`)
The installer now detects and uses `pkexec` if available (provides graphical password prompt):

```python
# Use pkexec if available (graphical sudo prompt)
sudo_cmd = "pkexec" if shutil.which("pkexec") else "sudo"
```

#### 2. **Pre-Authentication Check**
Before attempting any installations, the installer now:
- Tests sudo/pkexec access with a simple `true` command
- Verifies authentication before proceeding
- Provides clear error messages if authentication fails

```python
# Test sudo access
test_result = subprocess.run(
    [sudo_cmd, "true"],
    capture_output=True,
    text=True,
    timeout=60
)

if test_result.returncode != 0:
    self.log("[!] Failed to authenticate!")
    self.log("[!] Please run the installer with: sudo python3 gattrose-ng.py")
    return
```

#### 3. **Better Error Messages**
- Clear instructions if authentication fails
- Filters out repetitive authentication error spam
- Shows actual package installation errors (not auth failures)

```python
if "Authentication failed" not in error_msg:
    self.log(f"    Error: {error_msg}")
```

#### 4. **Consistent sudo_cmd Usage**
All installation commands now use the determined `sudo_cmd` (either `sudo` or `pkexec`):

```python
# Replace 'sudo' with our determined sudo_cmd
cmd_parts = prereq.install_command.split()
if cmd_parts[0] == "sudo":
    cmd_parts[0] = sudo_cmd
```

---

## How to Use the Fixed Installer

### Option 1: Run with sudo (Recommended)
```bash
sudo python3 gattrose-ng.py
```

This authenticates once at the start and avoids multiple password prompts.

### Option 2: Use pkexec (If Available)
If `pkexec` is installed, the installer will automatically use it and show a graphical password prompt when needed.

### Option 3: Manual Installation
If you prefer to install tools manually:

```bash
# Required tools
sudo apt-get update
sudo apt-get install -y aircrack-ng wireless-tools iw sqlite3 tcpdump

# Optional tools
sudo apt-get install -y reaver bully hashcat hcxtools macchanger
```

Then run Gattrose-NG normally:
```bash
python3 gattrose-ng.py
```

---

## Testing the Fixes

1. **Launch Gattrose-NG**:
   ```bash
   cd /path/to/gattrose-ng
   sudo python3 gattrose-ng.py
   ```

2. **Check Prerequisites**:
   - Installer will open if tools are missing
   - Should show pkexec or sudo being used
   - Authentication should happen once (not repeatedly)

3. **Install Tools**:
   - Click "Install Required Tools" or "Install Optional Tools"
   - Enter password once when prompted
   - Installation should proceed smoothly

4. **Verify**:
   - Re-check will confirm installed tools
   - "Continue to Gattrose-NG" button will enable when ready

---

## Summary of Changes

### Files Modified:
1. `gattrose-ng.py` - Updated APP_NAME to "Gattrose-NG"
2. `src/gui/prereq_installer.py` - Added import for shutil, improved sudo handling, pkexec support
3. `src/gui/main_window.py` - Updated all "Gattrose" to "Gattrose-NG"
4. `README.md` - Updated project title
5. `THEMES.md` - Updated project name
6. `QUICKSTART.md` - Updated title

### New Features:
- ✅ Automatic pkexec detection and usage
- ✅ Pre-authentication testing
- ✅ Better error messages
- ✅ Filtered authentication error spam
- ✅ Single authentication for multiple packages
- ✅ Clear instructions when auth fails

---

## Known Limitations

1. **sudo/pkexec Required**: Installing system packages requires elevated privileges
2. **No Password Storage**: For security, password must be entered each session
3. **Debian/Ubuntu Only**: apt-get based installation (Kali, Ubuntu, Debian)

---

## Future Improvements

Possible enhancements:
- [ ] Add support for other package managers (yum, pacman, etc.)
- [ ] Detect if running in Docker/container (skip system tools)
- [ ] Provide downloadable packages for offline installation
- [ ] Add "skip prerequisites" option for expert users

---

**All issues resolved!** 🎉

Run `sudo python3 gattrose-ng.py` to start using Gattrose-NG with all fixes applied.
