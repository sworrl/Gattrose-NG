# Recent Updates - November 1, 2025

## Summary of Changes

### 1. Directory Cleanup
- Created `archive/docs/` directory
- Moved 13 development documentation files to archive to keep the main directory clean

### 2. Fixed Missing Import
- Added `QGridLayout` import to fix application crash on startup

### 3. Historical Data Loading Feature
**NEW FEATURE**: The scanner now automatically loads the most recent scan data when you open the app!

- When you launch Gattrose-NG, it will automatically display data from your most recent scan
- You'll see all previously captured APs and clients immediately
- A new "Load History" button has been added to the Scanner tab to manually reload historical data
- Debug output is shown in the terminal to help troubleshoot loading issues

**How it works:**
- The app looks in `data/captures/` for CSV files
- It loads the most recent `scan_*-01.csv` file
- All access points and clients are displayed in the tree view
- You can see the last scan's data even if the scanner isn't running

### 4. Desktop Launcher Improvements
- Updated `gattrose-ng.desktop` file for better double-click support
- Made the desktop file executable
- Note: On first double-click, you may need to right-click and select "Allow Launching" or "Trust"

## How to Use

### Running the Application

**Method 1: Terminal (Recommended for now)**
```bash
sudo ./gattrose-ng.py
```

**Method 2: Double-Click (If configured)**
- Double-click `gattrose-ng.desktop`
- Or double-click `gattrose-ng.py` directly
- May require right-clicking and selecting "Allow Launching" first

### Viewing Historical Scan Data

1. **Automatic Loading**: When the app starts, look for a message in the Scanner Log:
   ```
   Loading recent scan data from scan_YYYYMMDD_HHMMSS-01.csv
   Loaded X APs and Y clients from history
   ```

2. **Manual Loading**: Click the "Load History" button in the Scanner tab to reload the most recent scan data

3. **Terminal Debug Output**: When running from terminal, you'll see debug messages like:
   ```
   [DEBUG] Loading data from: /path/to/scan_file.csv
   [DEBUG] Found 3 sections in CSV
   [DEBUG] AP section has 63 lines
   [DEBUG] Loaded 61 APs
   [DEBUG] Client section has 54 lines
   [DEBUG] Loaded 52 clients
   ```

### Understanding the Data Display

- **Access Points (APs)** are shown in **bold** at the root level of the tree
- **Clients** are shown as child items under their associated AP
- **Unassociated clients** appear at the root level with "CLIENT" in the info column

### Troubleshooting

If historical data doesn't load:

1. **Check Terminal Output**: Look for `[DEBUG]` and `[ERROR]` messages
2. **Verify Data Exists**: Check if `data/captures/` contains CSV files
3. **Click "Load History"**: Manually trigger the load to see debug output
4. **Check Permissions**: Ensure the CSV files are readable (should be created by root)

## File Structure

```
gattrose-ng/
├── archive/
│   └── docs/           # Archived development documentation
├── data/
│   └── captures/       # Scan data (CSV files)
├── src/
│   ├── gui/           # GUI components
│   ├── tools/         # Scanner and monitoring tools
│   └── ...
├── gattrose-ng.py     # Main launcher
└── gattrose-ng.desktop # Desktop launcher file
```

## Known Issues

1. **Launcher Still Opens Terminal**: The application requires sudo privileges, so it opens a terminal window for password entry. This is by design for security.

2. **Data Only Shows in Terminal**: If the GUI shows "0 APs" but the terminal shows debug output with data being loaded, there may be an issue with the widget update. Use the "Load History" button after the app fully loads.

## Next Steps

If you're still not seeing data in the GUI:
1. Run the app from terminal: `sudo ./gattrose-ng.py`
2. Click the "Load History" button
3. Watch the terminal output for `[DEBUG]` messages
4. Report any `[ERROR]` messages you see
