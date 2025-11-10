# Gattrose-NG File Manifest Report

**App Version:** 2.2.3
**Manifest Version:** 1.0.0
**Last Updated:** 2025-11-01
**Total Files:** 29

## Root Files

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `VERSION` | FILE-00001 | 2.2.3 | 2025-11-01 | Application version number |
| `gattrose-ng.desktop` | FILE-00003 | 1.0.1 | 2025-11-01 | Desktop launcher file |
| `gattrose-ng.py` | FILE-00002 | 2.2.1 | 2025-11-01 | Main launcher with venv management |

## Core Source

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `src/main.py` | FILE-00010 | 2.1.3 | 2025-11-01 | Application entry point |
| `src/version.py` | FILE-00011 | 1.0.0 | 2025-11-01 | Centralized version management |

## Database

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `src/database/models.py` | FILE-00020 | 2.2.3 | 2025-11-01 | Database models with OUI tables |

## GUI

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `src/gui/main_window.py` | FILE-00030 | 2.2.3 | 2025-11-01 | Main window with all tabs |
| `src/gui/theme.py` | FILE-00031 | 2.2.3 | 2025-11-01 | Theme system with textures |

## Tools

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `src/tools/wifi_monitor.py` | FILE-00041 | 2.1.3 | 2025-11-01 | Monitor mode management |
| `src/tools/wifi_scanner.py` | FILE-00040 | 2.1.0 | 2025-10-30 | WiFi scanner classes |

## Utils

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `src/utils/location.py` | FILE-00052 | 1.0.0 | 2025-10-31 | GPS and GeoIP location services |
| `src/utils/mac_vendor.py` | FILE-00051 | 2.0.0 | 2025-10-29 | MAC vendor lookup |
| `src/utils/oui_downloader.py` | FILE-00053 | 1.0.0 | 2025-11-01 | OUI database downloader (IEEE + Wireshark) |
| `src/utils/process_manager.py` | FILE-00050 | 2.1.3 | 2025-11-01 | Process management with race condition fix |

## Services

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `src/services/attacker_service.py` | FILE-00061 | 1.0.0 | 2025-11-01 | 24/7 automated attack daemon |
| `src/services/maintenance_service.py` | FILE-00062 | 1.0.0 | 2025-11-01 | Database maintenance service |
| `src/services/scanner_service.py` | FILE-00060 | 1.0.0 | 2025-11-01 | 24/7 WiFi scanning daemon |

## Scripts

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `bin/com.gattrose.pkexec.policy` | FILE-00072 | 1.0.0 | 2025-11-01 | PolicyKit policy for GUI elevation |
| `bin/gattrose-gui.sh` | FILE-00070 | 1.0.2 | 2025-11-01 | GUI wrapper script (Stage 2) |
| `bin/gattrose-launcher.sh` | FILE-00071 | 1.0.0 | 2025-11-01 | Desktop launcher (Stage 1) |

## Systemd

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `services/README.md` | FILE-00084 | 1.0.0 | 2025-11-01 | Services documentation |
| `services/gattrose-attacker.service` | FILE-00081 | 1.0.0 | 2025-11-01 | Attacker systemd service |
| `services/gattrose-maintenance.service` | FILE-00082 | 1.0.0 | 2025-11-01 | Maintenance systemd service |
| `services/gattrose-maintenance.timer` | FILE-00083 | 1.0.0 | 2025-11-01 | Maintenance timer (daily 3 AM) |
| `services/gattrose-scanner.service` | FILE-00080 | 1.0.0 | 2025-11-01 | Scanner systemd service |

## Documentation

| File | Serial | Version | Last Modified | Description |
|------|--------|---------|---------------|-------------|
| `docs/CHANGELOG_v2.1.3.md` | FILE-00091 | 1.0.0 | 2025-11-01 | Race condition fix changelog |
| `docs/CHANGELOG_v2.2.3.md` | FILE-00092 | 1.0.0 | 2025-11-01 | Infrastructure overhaul changelog |
| `docs/PROCESS_MANAGEMENT.md` | FILE-00093 | 1.0.0 | 2025-11-01 | Process management documentation |
| `docs/VERSION_MANAGEMENT.md` | FILE-00090 | 1.0.0 | 2025-11-01 | Version management guide |

