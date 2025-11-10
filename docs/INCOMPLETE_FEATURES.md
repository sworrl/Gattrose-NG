# Gattrose-NG - Incomplete Features List
**Generated:** November 1, 2025

This document tracks all incomplete/unimplemented features, TODOs, and placeholders in Gattrose-NG.

---

## 🚨 High Priority Incomplete Features

### 1. **Attack Implementation**
**Location:** `src/gui/main_window.py`

- **Evil Twin Attack** (line 3979-3982)
  - Create rogue AP cloning target network
  - Captive portal for credential capture
  - Status: Placeholder only

- **Karma Attack** (line 3988-3991)
  - Respond to all probe requests
  - Auto-associate clients
  - Status: Placeholder only

- **Single Deauth Burst** (line 4002-4005)
  - Quick deauth from context menu
  - Status: Placeholder only

### 2. **WPS Attacks**
**Location:** `src/gui/auto_attack_tab.py`

- **WPS PIN Attacks** (line 401-404)
  - Reaver integration
  - Bully integration
  - Status: Not implemented

- **Auto-Cracking** (line 419-421)
  - Automatic password cracking for captured handshakes
  - Hashcat/aircrack-ng integration
  - Status: Not implemented

### 3. **Database Integration**
**Location:** `bin/gattrose-daemon.py`

- **Client Database Storage** (line 207-208)
  - Save client discoveries to database
  - Status: Empty pass statement

- **Client Database Updates** (line 211-213)
  - Update client information in database
  - Status: Empty pass statement

### 4. **Attacker Service**
**Location:** `src/services/attacker_service.py`

- **Save WPS PIN/PSK** (multiple locations)
  - Save cracked WPS credentials to database
  - Status: TODO comments only

---

## 📊 Medium Priority Incomplete Features

### 5. **Scanner Integration**
**Location:** `bin/gattrose-daemon.py`

- **Bluetooth Scanning** (line 140-146)
  - Bluetooth device discovery
  - BLE scanning
  - Status: Stub function only

- **SDR Scanning** (line 145-147)
  - Software Defined Radio support
  - Frequency scanning
  - Status: Stub function only

### 6. **Web API Features**
**Location:** `src/services/web_api.py`

- **Scanner Service Integration** (multiple locations)
  - `/api/system/scan/start` endpoint
  - `/api/system/scan/stop` endpoint
  - Status: Placeholder responses only

- **Actual Scanning Status** (line ~100)
  - Real-time scanner status
  - Currently returns hardcoded `False`

**Location:** `web/js/app.js`

- **Clear Queue Endpoint** (line 502-503)
  - API endpoint to clear attack queue
  - Status: Not implemented

### 7. **Manual Attack Tab**
**Location:** `src/gui/manual_attack_tab.py`

- **Get Selected AP from Scanner**
  - Auto-populate target from scanner tab selection
  - Status: TODO comment

### 8. **WiGLE Integration**
**Location:** `src/gui/wigle_tab.py`

- **Export Results** (line 423-425)
  - Export WiGLE search results to file
  - Status: TODO comment

**Location:** `src/gui/main_window.py`

- **WiGLE Tab Search Integration** (line 2441-2443)
  - Open WiGLE tab with BSSID search pre-filled
  - Status: Shows info dialog only

- **WiGLE Upload** (line 2447-2449)
  - Upload captured networks to WiGLE
  - Status: Shows info dialog only

### 9. **Bluetooth Tab**
**Location:** `src/gui/bluetooth_tab.py`

- **Bluetooth Scanning** (line 118-120)
  - bluetoothctl integration
  - hcitool integration
  - btscanner integration
  - Status: Commented examples only

### 10. **Auto Attack Queue**
**Location:** `src/gui/auto_attack_tab.py`

- **Add from Scanner** (line 648-650)
  - Add selected APs from scanner tab to attack queue
  - Status: TODO comment

---

## 📝 Low Priority / Enhancement TODOs

### 11. **Database Tab Filtering**
**Location:** `src/gui/main_window.py`

- **Apply Cracked Filter** (line 875-876)
  - When clicking "Cracked" in dashboard, filter database tab
  - Status: Tab switch only, no filter applied

- **Set Encryption Filter** (line 983-984)
  - When clicking encryption type in dashboard, filter database tab
  - Status: Tab switch only, no filter applied

### 12. **Network History View**
**Location:** `src/gui/main_window.py`

- **View History** (line 2290-2292)
  - Open database tab with filter for specific BSSID
  - View historical scan data for network
  - Status: Shows info dialog only

---

## 🧪 Testing TODOs

### 13. **End-to-End Testing**
**Location:** `TODO.md`

- **Attack Queue E2E Test** (line 32)
  - Test: Add target from GUI → Check database → Verify attacker service processes it
  - Status: Not tested

---

## 📚 Documentation TODOs

### 14. **Database Logging Documentation**
**Location:** `docs/WIFI_SCANNER_IMPLEMENTATION.md`

- **Database Persistence Guide** (section: "Next Steps")
  - Document how to add database persistence
  - Current implementation captures in memory only
  - Status: Section header exists, content minimal

---

## 🎯 Feature Category Summary

| Category | Total TODOs | Priority |
|----------|-------------|----------|
| Attack Implementation | 5 | High |
| Database Integration | 4 | High |
| Scanner Integration | 2 | Medium |
| Web API | 3 | Medium |
| WiGLE Integration | 3 | Medium |
| Bluetooth | 1 | Medium |
| UI Filtering/Navigation | 4 | Low |
| Testing | 1 | Low |
| Documentation | 1 | Low |
| **TOTAL** | **24** | - |

---

## 🚀 Next Actions Recommended

### Immediate (High Priority)
1. Implement WPS attack functionality (Reaver/Bully)
2. Complete database integration for clients
3. Implement auto-cracking for handshakes

### Short-term (Medium Priority)
4. Complete web API scanner integration
5. Implement database tab filtering
6. Add WiGLE upload functionality

### Long-term (Low Priority)
7. Bluetooth scanning integration
8. SDR scanning integration
9. Advanced attack implementations (Evil Twin, Karma)

---

## 📊 Implementation Status

- ✅ **Complete:** Core WiFi scanning, database models, web server, attack queue, device fingerprinting
- 🟡 **Partial:** Attack implementations (deauth works, others pending), WiGLE (search works, upload pending)
- ❌ **Not Started:** Bluetooth scanning, SDR scanning, auto-cracking, advanced attacks

---

**Last Updated:** November 1, 2025
**Total Incomplete Features:** 24
**Critical Blockers:** 0 (all features have working alternatives or are optional enhancements)
