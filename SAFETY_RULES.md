# CRITICAL SAFETY RULES FOR CLAUDE CODE

## ⚠️ HOME FOLDER PROTECTION ⚠️

### ABSOLUTE RULE: NEVER DELETE FILES FROM /home/eurrl WITHOUT EXPLICIT USER PERMISSION

This rule applies to:
- ALL files and directories under `/home/eurrl/`
- Source code repositories
- Configuration files
- User data directories
- Development files

## Source Code vs Installed Files

### SOURCE CODE LOCATIONS (NEVER DELETE):
```
/home/eurrl/Documents/Code & Scripts/gattrose-ng/    ← Primary source code
/home/eurrl/Documents/GitHub/Gattrose-NG/            ← Git repository
/home/eurrl/codes-and-scripts/                       ← Other projects
/home/eurrl/Documents/Code & Scripts/                ← Development workspace
```

### INSTALLED/PRODUCTION LOCATIONS (OK to delete for reinstall):
```
/opt/gattrose-ng/                    ← Production installation
/usr/local/bin/gattrose*             ← Installed binaries
/etc/systemd/system/gattrose-*       ← System services
/home/eurrl/.local/bin/gattrose-ng   ← User binaries (ASK FIRST)
```

### USER DATA (NEVER DELETE without explicit permission):
```
/home/eurrl/.local/share/            ← Application data
/home/eurrl/.config/                 ← Configuration files
/home/eurrl/data/                    ← User databases
/home/eurrl/.local/share/applications/  ← Desktop files (ASK FIRST)
```

## Installation Workflow Pattern

1. **Source Code** is stored in `/home/eurrl/Documents/Code & Scripts/<project>/`
2. **Installation** copies files from source to `/opt/<project>/` or system directories
3. **Updates/Reinstalls** use the source code to refresh the installed version
4. **Only delete INSTALLED versions**, never SOURCE CODE

## Key Distinctions

| Location | Type | Can Delete? |
|----------|------|-------------|
| `/home/eurrl/Documents/Code & Scripts/gattrose-ng/` | SOURCE CODE | **NEVER** |
| `/opt/gattrose-ng/` | INSTALLED | Yes (for clean reinstall) |
| `/home/eurrl/.local/` | USER DATA | **ASK FIRST** |
| `/home/eurrl/.config/` | USER CONFIG | **ASK FIRST** |
| `/etc/systemd/system/gattrose-*` | SYSTEM FILES | Yes (for uninstall) |
| `/usr/local/bin/gattrose*` | BINARIES | Yes (for uninstall) |

## Before Deleting ANYTHING from /home/eurrl:

1. **STOP** - Is this in `/home/eurrl/`?
2. **ASK** - Get explicit user permission
3. **VERIFY** - Confirm the exact path with user
4. **CHECK** - Is there a backup/snapshot available?

## Recovery Options

### ZFS Snapshots
- Available at: `/home/.zfs/snapshot/`
- List snapshots: `zfs list -t snapshot | grep home`
- Hourly snapshots maintained automatically
- Restore with: `cp -a /home/.zfs/snapshot/<snapshot-name>/eurrl/path/to/file /home/eurrl/path/to/file`

### Git Repositories
- Check for git repos: `find /home/eurrl -name ".git" -type d`
- Use git to recover deleted files if in a repository

## Examples of What Went Wrong

### Incident: 2025-11-06
**What happened:**
- Deleted `/home/eurrl/Documents/Code & Scripts/gattrose-ng/` during cleanup
- This was the SOURCE CODE, not an installed version
- Should have only deleted `/opt/gattrose-ng/`

**Why it was wrong:**
- Source code lives in `/home/eurrl/Documents/Code & Scripts/`
- This directory is used to INSTALL/UPDATE programs to system locations
- Deleting it removed the ability to reinstall or update

**How it was recovered:**
- Restored from ZFS snapshot: `zfs-auto-snap_hourly-2025-11-06-0117`
- Used: `sudo cp -a "/home/.zfs/snapshot/zfs-auto-snap_hourly-2025-11-06-0117/eurrl/Documents/Code & Scripts/gattrose-ng" "/home/eurrl/Documents/Code & Scripts/"`

**Lesson learned:**
- ALWAYS ask before deleting from `/home/eurrl/`
- Distinguish between source code and installed files
- Check if path is under `/home/eurrl/` before any delete operation

## Checklist Before Any Delete Operation

- [ ] Is the path under `/home/eurrl/`?
  - If YES → **STOP and ASK USER**
- [ ] Is this source code vs installed files?
  - Source: `/home/eurrl/Documents/Code & Scripts/` → **NEVER DELETE**
  - Installed: `/opt/`, `/usr/local/bin/`, etc. → OK to delete
- [ ] Did user explicitly say to delete this specific path?
  - If NO → **ASK FOR CONFIRMATION**
- [ ] Is there a backup/snapshot available?
  - Check: `zfs list -t snapshot | grep home`
- [ ] Have I confirmed the exact path with the user?
  - If NO → **CONFIRM PATH**

## Remember

**When in doubt, ASK THE USER. It takes 5 seconds to ask, but hours to recover from a mistake.**

---

**Created:** 2025-11-06
**Last Updated:** 2025-11-06
**Reason:** To prevent accidental deletion of source code from /home/eurrl/
