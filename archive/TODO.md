# Gattrose-NG Development TODO

## Current Status
Working on fixing attack queue and attack system integration.

## Recently Completed ✓
- ✅ BATCH 1: Quick UI Cleanup
  - Removed 'Refresh Statistics' button
  - Combined BSSID/MAC display
  - Object-oriented attack queue display
- ✅ BATCH 2: Dashboard Improvements
  - Clickable statistics cards
  - View AP history by BSSID
  - Batch selection for attack queue
- ✅ FIX: WPS Detection
  - Extended CSV format with WPS data
  - Persistent WPS info across sessions
- ✅ BATCH 3: Database Features
  - Export database to CSV
  - Backup database functionality
  - Network blacklist system
- ✅ Created AttackQueue database model

## Recently Completed (This Session) ✓
- ✅ **FIX: Attack Queue Integration** (COMPLETED)
  - [x] Created AttackQueue database table (src/database/models.py line 391-433)
  - [x] Updated `src/gui/auto_attack_tab.py::queue_target()` method to save to database (line 571-599)
  - [x] Updated `src/services/attacker_service.py` to process AttackQueue from database:
    - Added `get_queued_attacks()` method (line 137-169)
    - Added `update_queue_status()` method (line 171-192)
    - Modified main loop to prioritize database queue over automatic target selection (line 428-513)
  - [ ] **TODO**: Test end-to-end: Add target from GUI → Check database → Verify attacker service processes it

- ✅ **FIX: Database Serial Columns**
  - [x] Added serial column to scan_sessions table (migration already present)
  - [x] Verified all models have serial fields

- ✅ **FIX: Service Manager**
  - [x] Added ServiceManager.uninstall() method (src/core/service_manager.py line 418-493)
  - Stops, disables, and removes all services from systemd

- ✅ **NEW FEATURE: MAC Spoofing Status Indicator**
  - [x] Added MAC spoofing status label to Dashboard System Status group
  - [x] Implemented update_mac_spoofing_status() method with:
    - Real-time MAC address checking
    - Permanent hardware MAC detection via ethtool
    - Green display when spoofed (shows current + real MAC)
    - Red flashing display when NOT spoofed (security warning)
  - [x] Setup 500ms timer for flashing effect

- ✅ **REFINEMENTS**
  - [x] Fixed desktop launcher icon path (gattrose-ng.desktop)
  - [x] Created professional 512x512 SVG icon with modern design
  - [x] Generated high-quality PNG from SVG

## In Progress 🔄
- [ ] **Testing Attack Queue Integration**
  - Need to test: Add target from GUI → Check database → Verify attacker service processes it

## Pending Batches
- [ ] BATCH 4: Scanner Enhancements (3 hours)
  - Scanner filters (encryption/signal/vendor)
  - Drag-and-drop queue reordering
  - Keyboard shortcuts

- [ ] BATCH 5: Attack System Core (1 day)
  - WPS attacks (reaver/bully)
  - Auto-cracking handshakes
  - Handshake quality validation
  - Deauth-only attack mode

- [ ] BATCH 6: Notifications & Feedback (3 hours)
  - Desktop notification system
  - Sound alerts for events
  - System tray icon

- [ ] BATCH 7: Advanced Scanning (2 days)
  - Redesign scan page (object-oriented)
  - Mesh AP detection
  - Multiple MAC same SSID detection
  - Duplicate network detection

- [ ] BATCH 8: Attack Management (1 day)
  - Attack priority system
  - Attack history/audit log
  - Wordlist management

- [ ] BATCH 9: Integration & Reporting (2 days)
  - WiGLE search and upload
  - Import handshakes from files
  - PDF/HTML report generation

- [ ] BATCH 10: Advanced Features (2-3 days)
  - PMKID attacks
  - Live channel hopping
  - Scheduled attacks
  - Attack statistics dashboard

- [ ] BATCH 11: Professional Features (1 week)
  - Online hash lookup
  - Preferences/Settings dialog
  - Advanced networking tools

- [ ] BATCH 12: Expert Systems (months)
  - GPS/Location tracking
  - Email/webhook notifications
  - Bluetooth scanning
  - SDR integration
  - Evil Twin AP attacks
  - Multi-GPU cracking

## Notes
- Database has 65 networks stored
- Attack queue table created but not yet integrated with GUI/service
- WPS detection now works correctly with extended CSV format
- All serialization fields added (Network, Client, Handshake, WiGLEImport, OUIUpdate)
- Database persistence works: APs/clients saved via `save_ap_to_database()` and `save_client_to_database()`

## Key Files to Modify Next
1. `src/gui/auto_attack_tab.py` - Update `queue_target()` method
2. `src/services/attacker_service.py` - Add database queue processing
3. `src/database/models.py` - AttackQueue model already created (line 391-433)
