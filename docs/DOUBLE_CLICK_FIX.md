# How to Enable Double-Click Launching

**Issue:** Double-clicking `gattrose-ng.py` or `gattrose-ng.desktop` doesn't launch the app.

**Why:** Linux file managers require explicit permission to run executable files for security.

---

## ✅ Fixed Status Bar Error

The status bar error has been fixed:
```
AttributeError: 'MainWindow' object has no attribute 'status_bar'
```

This was caused by the theme selector trying to update the status bar before it was created. Now includes a safety check.

---

## 🚀 Three Ways to Launch Gattrose-NG

### Option 1: Terminal (Always Works)

```bash
cd "/home/eurrl/Documents/Code & Scripts/gattrose-ng"
sudo ./gattrose-ng.py
```

This is the **most reliable method** and shows all output.

---

### Option 2: Install Desktop Launcher (Recommended for GUI)

Run this **one-time** setup:

```bash
cd "/home/eurrl/Documents/Code & Scripts/gattrose-ng"
cp gattrose-ng.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/gattrose-ng.desktop
update-desktop-database ~/.local/share/applications/
```

Then:
1. Open your application menu (Super key / Windows key)
2. Search for "Gattrose"
3. Click the icon to launch!

The desktop launcher will:
- Use `pkexec` for graphical password prompt
- Open a terminal window
- Launch with proper permissions
- Show the awesome alligator icon 🐊

---

### Option 3: Trust and Double-Click Desktop File

**For GNOME/Ubuntu:**
1. Right-click `gattrose-ng.desktop`
2. Select "Allow Launching" or "Properties"
3. Check "Allow executing file as program"
4. Double-click to run

**For KDE/Kubuntu:**
1. Right-click `gattrose-ng.desktop`
2. Select "Properties"
3. Go to "Permissions" tab
4. Check "Is executable"
5. Close and double-click to run

**For XFCE:**
1. Right-click `gattrose-ng.desktop`
2. Select "Properties"
3. Go to "Permissions" tab
4. Check "Allow this file to run as a program"
5. Click "Mark Executable"
6. Double-click to run

---

## 🔧 Why .py Files Don't Double-Click by Default

Python `.py` files are **text files** by default. When you double-click:
- Some file managers open them in a text editor
- Some try to run them without a terminal
- Some don't run them at all for security

The `.desktop` file is the proper way to launch GUI applications on Linux.

---

## 📝 Alternative: Create System Command

To launch with just `gattrose-ng` from anywhere:

```bash
sudo ln -s "/home/eurrl/Documents/Code & Scripts/gattrose-ng/gattrose-ng.py" /usr/local/bin/gattrose-ng
```

Then from any terminal:
```bash
sudo gattrose-ng
```

---

## ✅ Verification

After installing the desktop launcher, verify it works:

```bash
# Check desktop file is installed
ls -la ~/.local/share/applications/gattrose-ng.desktop

# Test launching from command line
gtk-launch gattrose-ng.desktop
# or
gio launch ~/.local/share/applications/gattrose-ng.desktop
```

You should see:
1. Graphical password prompt (pkexec)
2. Terminal window opens
3. Gattrose-NG launches with monitor mode enabled
4. Scanner tab shows your WiFi interface ready!

---

## 🐊 Quick Install Script

Copy and paste this entire block:

```bash
cd "/home/eurrl/Documents/Code & Scripts/gattrose-ng"
cp gattrose-ng.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/gattrose-ng.desktop
update-desktop-database ~/.local/share/applications/
echo "✅ Desktop launcher installed!"
echo "🐊 Search for 'Gattrose' in your application menu"
```

---

## 🎯 Summary

**Best Method:** Install desktop launcher (Option 2)
- One-time setup
- GUI password prompt
- Shows in app menu
- Professional integration

**Fastest Method:** Terminal launch (Option 1)
- No setup needed
- Full output visible
- Most reliable

**Not Recommended:** Double-clicking .py files
- Inconsistent across file managers
- Often opens in text editor
- Doesn't work well for apps requiring sudo

---

**All times in 24-hour format. Always.**

**Chomp chomp!** 🐊
