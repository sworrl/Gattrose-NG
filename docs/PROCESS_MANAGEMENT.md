# Gattrose-NG Process Management

## Overview

Gattrose-NG v2.1.2 includes automatic process management to prevent duplicate instances and clean up orphaned processes.

## Features

### 1. **Automatic Startup Cleanup**
When Gattrose-NG starts, it automatically:
- Detects any duplicate/stuck Gattrose-NG instances
- Kills duplicate processes gracefully (SIGTERM first, then SIGKILL if needed)
- Cleans up orphaned wireless tool processes (airodump-ng, aireplay-ng, etc.)
- Registers exit handlers for cleanup on shutdown

### 2. **Automatic Shutdown Cleanup**
When Gattrose-NG closes, it automatically:
- Cleans up orphaned wireless tool processes
- Ensures no background processes are left running
- Properly terminates all threads and subprocesses

### 3. **Manual Cleanup Script**
If the application crashes or gets stuck, use the manual cleanup script:

```bash
# Run the cleanup script
sudo ./bin/gattrose-cleanup.sh
```

This will:
- Force kill all Gattrose-NG Python processes
- Kill all orphaned wireless tools (airodump-ng, aireplay-ng, aircrack-ng, reaver, wash)
- Restart NetworkManager to restore normal network functionality

## Process Detection

The process manager detects Gattrose-NG processes by:
1. Finding all Python processes
2. Checking if they're running `gattrose` or `main.py`
3. Excluding the current process from duplicate detection

## Orphaned Process Cleanup

The following background processes are automatically cleaned up:
- `airodump-ng` - Wireless packet capture
- `aireplay-ng` - Packet injection
- `aircrack-ng` - Key cracking
- `reaver` - WPS PIN attacks
- `wash` - WPS network detection

## Using the Process Manager Programmatically

```python
from src.utils.process_manager import ProcessManager, check_and_cleanup_processes

# Quick cleanup at startup
check_and_cleanup_processes()

# Manual process management
manager = ProcessManager()

# Find duplicate processes
processes = manager.find_gattrose_processes()
print(f"Found {len(processes)} duplicate processes")

# Kill duplicates
killed = manager.kill_duplicate_processes()
print(f"Killed {killed} processes")

# Cleanup orphaned tools
orphaned = manager.cleanup_orphaned_processes()
print(f"Cleaned up {orphaned} orphaned processes")

# Register cleanup on exit
manager.register_exit_handler()
```

## Troubleshooting

### Application Won't Start
If Gattrose-NG won't start and you see "Another instance is running":
```bash
# Force cleanup
sudo ./bin/gattrose-cleanup.sh

# Or manually
cd /path/to/gattrose-ng
sudo .venv/bin/python -m src.utils.process_manager --force-cleanup
```

### NetworkManager Not Working
If your network icon disappears after a crash:
```bash
# Restart NetworkManager
sudo systemctl restart NetworkManager

# Or use the cleanup script
sudo ./bin/gattrose-cleanup.sh
```

### Orphaned Processes Still Running
Check for orphaned processes:
```bash
ps aux | grep -E 'airodump|aireplay|aircrack|reaver|wash'
```

Kill them manually:
```bash
sudo killall -9 airodump-ng aireplay-ng aircrack-ng reaver wash
```

## Implementation Details

### Files
- `src/utils/process_manager.py` - Main process management module
- `bin/gattrose-cleanup.sh` - Emergency cleanup script
- `src/main.py` - Integrated startup cleanup
- `src/gui/main_window.py` - Integrated shutdown cleanup (closeEvent)

### Process Cleanup Flow

**At Startup:**
1. Check for duplicate Gattrose-NG processes
2. Send SIGTERM to gracefully terminate them
3. Wait 0.5 seconds
4. Send SIGKILL if they're still alive
5. Clean up orphaned wireless tool processes
6. Register exit handlers

**At Shutdown:**
1. Stop all QThreads (status monitor, etc.)
2. Kill orphaned wireless tool processes
3. Exit cleanly

### Exit Handlers
The process manager registers handlers for:
- `atexit` - Normal Python exit
- `SIGINT` - Ctrl+C
- `SIGTERM` - Kill signal
- Qt `closeEvent` - Window close

## Safety Features

1. **Never kills itself** - Current process is always excluded from cleanup
2. **Graceful termination first** - SIGTERM before SIGKILL
3. **NetworkManager preservation** - Doesn't kill NetworkManager (unlike old `airmon-ng check kill`)
4. **Non-blocking** - Process checks don't hang the application
5. **Error handling** - Continues even if cleanup fails

## Configuration

Process management is always enabled and cannot be disabled. This ensures:
- No duplicate instances causing conflicts
- No orphaned processes wasting resources
- Clean shutdown every time

## Performance Impact

- Startup: +0.1-0.3 seconds (process detection)
- Shutdown: +0.1-0.2 seconds (cleanup)
- Runtime: No impact (cleanup runs on exit)

## Known Limitations

1. **Root processes** - Cannot kill processes owned by other users without sudo
2. **Zombie processes** - Some crashed processes may become zombies and require manual cleanup
3. **Permission errors** - Some system processes may require elevated privileges to terminate

## Version History

- **v2.1.2** - Initial process management implementation
  - Automatic duplicate detection
  - Startup/shutdown cleanup
  - Manual cleanup script
  - Exit handler registration
