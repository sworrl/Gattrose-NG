# Status Bar AttributeError Fix

**Date:** 2025-10-31
**Error:** `AttributeError: 'MainWindow' object has no attribute 'status_bar'`
**Location:** `src/gui/main_window.py:627`

---

## The Problem

When launching Gattrose-NG, the application crashed with:

```
[!] Error launching main application: 'MainWindow' object has no attribute 'status_bar'
Traceback (most recent call last):
  File "/home/eurrl/Documents/Code & Scripts/gattrose-ng/src/main.py", line 73, in launch_main_app
    window = MainWindow()
  File "/home/eurrl/Documents/Code & Scripts/gattrose-ng/src/gui/main_window.py", line 405, in __init__
    self.init_ui()
  File "/home/eurrl/Documents/Code & Scripts/gattrose-ng/src/gui/main_window.py", line 434, in init_ui
    self.apply_theme(self.current_theme, save=False)
  File "/home/eurrl/Documents/Code & Scripts/gattrose-ng/src/gui/main_window.py", line 627, in apply_theme
    self.status_bar.showMessage(f"Theme changed to: {theme.name}", 3000)
AttributeError: 'MainWindow' object has no attribute 'status_bar'
```

---

## Root Cause

**Initialization Order Problem:**

In `init_ui()`, the original order was:

```python
def init_ui(self):
    self.setWindowTitle("Gattrose-NG - Wireless Penetration Testing Suite")
    self.setMinimumSize(1200, 800)

    # ❌ PROBLEM: Apply theme FIRST
    self.apply_theme(self.current_theme, save=False)  # Line 434

    self.create_menu_bar()
    self.create_toolbar()
    self.create_tabs()

    # ❌ PROBLEM: Create status bar AFTER theme is applied
    self.create_status_bar()  # Line 446

    self.center_on_screen()
```

**The issue:**
1. `apply_theme()` is called at line 434
2. `apply_theme()` tries to use `self.status_bar` at line 627
3. But `create_status_bar()` isn't called until line 446
4. So `self.status_bar` doesn't exist yet!

---

## The Fix

**Reorder initialization to create UI elements BEFORE applying theme:**

```python
def init_ui(self):
    self.setWindowTitle("Gattrose-NG - Wireless Penetration Testing Suite")
    self.setMinimumSize(1200, 800)

    # ✅ Create all UI elements FIRST
    self.create_menu_bar()
    self.create_toolbar()
    self.create_tabs()
    self.create_status_bar()

    # ✅ Apply theme AFTER UI elements exist
    self.apply_theme(self.current_theme, save=False)

    self.center_on_screen()
```

**Now:**
1. All UI elements (menu bar, toolbar, tabs, status bar) are created
2. `self.status_bar` exists
3. `apply_theme()` can safely use `self.status_bar.showMessage()`

---

## File Changed

**File:** `src/gui/main_window.py`

**Lines Modified:** 428-449 (init_ui method)

**Change Type:** Reordering of method calls (no logic changes)

---

## Testing

After the fix:

```bash
$ sudo ./gattrose-ng.py
[+] Running with elevated privileges

============================================================
  Gattrose-NG v1.0.0
  Wireless Penetration Testing Suite
============================================================

[*] Project root: /home/eurrl/Documents/Code & Scripts/gattrose-ng
[*] Mode: Portable
[*] Virtual environment: /home/eurrl/Documents/Code & Scripts/gattrose-ng/.venv

[+] Virtual environment found
[*] Launching Gattrose-NG...
[+] All required prerequisites are met
[*] Launching Gattrose main application...
[✅ SUCCESS - Application launches with theme applied]
```

---

## Why This Happened

This is a classic **initialization order bug**. It happens when:

1. A method called early in initialization uses an attribute
2. That attribute is created later in initialization
3. The order matters!

**Lesson:** Always create UI elements before trying to use/style them.

---

## Related Changes

This bug was discovered during the double-click launcher fix. The reason double-clicking didn't work in the GUI was actually **two separate issues**:

1. ❌ File was named `gattrose.py` instead of `gattrose-ng.py` (inconsistent branding)
2. ❌ Status bar initialization order bug (this fix)

Both are now fixed! ✅

---

**All times in 24-hour format. Always.**
