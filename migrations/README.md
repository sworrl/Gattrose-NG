# Database Migrations

This directory contains database migration scripts for Gattrose-NG.

## Migration Scripts

- `migrate_add_serials.py` - Adds serial number columns to clients, handshakes, wigle_imports, and oui_updates tables
- `migrate_add_blacklist.py` - Adds blacklist functionality to networks table
- `migrate_add_scan_session_serial.py` - Adds serial column to scan_sessions table

## Running Migrations

From the project root:

```bash
.venv/bin/python migrations/migrate_add_serials.py
.venv/bin/python migrations/migrate_add_blacklist.py
.venv/bin/python migrations/migrate_add_scan_session_serial.py
```

## Notes

- Migrations are idempotent - safe to run multiple times
- Always backup your database before running migrations
- Migrations check if changes already exist before applying them
