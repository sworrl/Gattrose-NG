# Gattrose-NG System Services

## Overview

Gattrose-NG uses systemd services for 24/7 operation and automated tasks:

1. **gattrose-scanner.service** - Continuous WiFi scanning
2. **gattrose-attacker.service** - Automated attack execution
3. **gattrose-maintenance.service** - Database maintenance
4. **gattrose-maintenance.timer** - Scheduled maintenance runs

## Installation

### 1. Install Services

```bash
cd "/home/eurrl/Documents/Code & Scripts/gattrose-ng"

# Copy service files to systemd directory
sudo cp services/*.service /etc/systemd/system/
sudo cp services/*.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload
```

### 2. Enable Services

```bash
# Enable scanner service (starts on boot)
sudo systemctl enable gattrose-scanner.service

# Enable attacker service (optional - for 24/7 attacks)
sudo systemctl enable gattrose-attacker.service

# Enable maintenance timer (runs daily at 3 AM)
sudo systemctl enable gattrose-maintenance.timer
```

### 3. Start Services

```bash
# Start scanner
sudo systemctl start gattrose-scanner.service

# Start attacker
sudo systemctl start gattrose-attacker.service

# Start maintenance timer
sudo systemctl start gattrose-maintenance.timer
```

## Service Descriptions

### Scanner Service (`gattrose-scanner.service`)

**Purpose:** Continuously scan for WiFi networks and clients

**Features:**
- Runs 24/7 in headless mode
- Auto-restarts on failure (10s delay)
- Stores data in live_scans database table
- Archives previous scan when new scan starts
- Location-aware (tracks GPS if available)
- Resource limited: 50% CPU, 512MB RAM

**Status:**
```bash
sudo systemctl status gattrose-scanner.service
```

**Logs:**
```bash
sudo journalctl -u gattrose-scanner -f
```

### Attacker Service (`gattrose-attacker.service`)

**Purpose:** Automatically attack discovered networks based on scoring

**Features:**
- Runs 24/7 in headless mode
- Depends on scanner service
- Prioritizes targets by attack score
- Captures handshakes automatically
- WPS attack support
- Resource limited: 75% CPU, 1GB RAM

**Status:**
```bash
sudo systemctl status gattrose-attacker.service
```

**Logs:**
```bash
sudo journalctl -u gattrose-attacker -f
```

### Maintenance Service (`gattrose-maintenance.service`)

**Purpose:** Perform database maintenance tasks

**Tasks:**
- Vacuum and optimize database
- Archive old scans
- Update OUI database (if needed)
- Clean up orphaned records
- Generate statistics
- Purge old temporary files

**Runs:** Daily at 3 AM + 10 minutes after boot

**Manual Run:**
```bash
sudo systemctl start gattrose-maintenance.service
```

**Timer Status:**
```bash
sudo systemctl status gattrose-maintenance.timer
```

**Logs:**
```bash
sudo journalctl -u gattrose-maintenance -f
```

## Service Management

### Stop Services

```bash
sudo systemctl stop gattrose-scanner.service
sudo systemctl stop gattrose-attacker.service
sudo systemctl stop gattrose-maintenance.timer
```

### Disable Services

```bash
sudo systemctl disable gattrose-scanner.service
sudo systemctl disable gattrose-attacker.service
sudo systemctl disable gattrose-maintenance.timer
```

### Restart Services

```bash
sudo systemctl restart gattrose-scanner.service
sudo systemctl restart gattrose-attacker.service
```

## Service Version Management

Services check their version at startup and auto-update if needed (useful during development).

Each service includes version in environment:
```
Environment="GATTROSE_NG_VERSION=2.2.2"
```

When code is updated, services detect version mismatch and reload.

## Resource Limits

Services have resource limits to prevent system overload:

| Service | CPU Quota | Memory Limit |
|---------|-----------|--------------|
| Scanner | 50% | 512MB |
| Attacker | 75% | 1GB |
| Maintenance | 25% | 256MB |

Adjust in service files if needed.

## Logs and Monitoring

All services log to systemd journal:

```bash
# View all Gattrose logs
sudo journalctl -t gattrose-scanner -t gattrose-attacker -t gattrose-maintenance -f

# View only errors
sudo journalctl -t gattrose-scanner -p err -f

# View logs since boot
sudo journalctl -b -t gattrose-scanner
```

## Troubleshooting

### Service Won't Start

1. Check service status:
   ```bash
   sudo systemctl status gattrose-scanner.service
   ```

2. Check logs for errors:
   ```bash
   sudo journalctl -xe -u gattrose-scanner
   ```

3. Verify Python environment:
   ```bash
   /home/eurrl/Documents/Code\ &\ Scripts/gattrose-ng/.venv/bin/python --version
   ```

4. Check file permissions:
   ```bash
   ls -la /home/eurrl/Documents/Code\ &\ Scripts/gattrose-ng/src/services/
   ```

### Service Keeps Restarting

Check for errors in logs:
```bash
sudo journalctl -u gattrose-scanner -n 100
```

Common issues:
- Missing wireless interface
- Permission denied (needs root)
- Database locked
- Out of memory

### High Resource Usage

Monitor resources:
```bash
systemctl status gattrose-scanner.service gattrose-attacker.service
```

Adjust CPU/Memory limits in service files.

## Service Scripts Location

Service Python scripts are in:
```
src/services/
├── scanner_service.py       # Scanner daemon
├── attacker_service.py      # Attacker daemon
├── maintenance_service.py   # Maintenance tasks
└── service_manager.py       # Service management utilities
```

## Development Mode

During development, services auto-detect version changes:

1. Update code
2. Increment version in `/VERSION`
3. Services detect mismatch on next startup
4. Services reload automatically

Or manually restart:
```bash
sudo systemctl restart gattrose-scanner.service
```

## Production Deployment

For production systems:

1. Disable auto-update in services
2. Use fixed version numbers
3. Set restart limit:
   ```
   StartLimitBurst=5
   StartLimitIntervalSec=300
   ```
4. Enable email notifications on failure
5. Set up monitoring (Prometheus, Grafana, etc.)

## Security Considerations

- Services run as root (required for wireless operations)
- Logs may contain sensitive data (SSIDs, MACs)
- Captured handshakes stored in database
- Restrict access to database file
- Consider encrypting database at rest
- Rotate logs regularly

## Next Steps

1. Implement service Python scripts (scanner_service.py, etc.)
2. Add service manager GUI in Settings tab
3. Implement service version checking
4. Add service health monitoring
5. Create notification system for service events
