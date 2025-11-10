# Updating Gattrose-NG Installation

## Quick Update

After making changes to the code in this dev directory, run:

```bash
cd "/home/eurrl/Documents/Code & Scripts/gattrose-ng"
sudo python3 update_install.py
```

This will:
1. Sync all changes from dev directory → `/opt/gattrose-ng`
2. Copy launcher to `/usr/local/bin/gattrose-ng`
3. Set proper permissions
4. Optionally restart services

## What Gets Synced

- `src/` → Source code
- `bin/` → Scripts and launchers
- `assets/` → Icons and resources
- `docs/` → Documentation
- `*.desktop` → Desktop entries to `/usr/share/applications/`
- `bin/gattrose-ng` → Main launcher to `/usr/local/bin/`

## After Update

Run from anywhere:
```bash
gattrose-ng
```

Or use the tray icon to launch GUI.

## Manual Service Restart

If you didn't restart during update:

```bash
# Restart orchestrator (as sudo)
sudo systemctl restart gattrose-orchestrator.service

# Restart tray (as user)
systemctl --user restart gattrose-tray.service
```
