# Gattrose-NG TODO List

## 🔴 Critical / Immediate

### Database & Migrations
- [ ] Add serial columns to `current_scan_networks` and `current_scan_clients` tables in system database
- [ ] Implement automatic migration runner on orchestrator startup
- [ ] Add database schema version tracking
- [ ] Create rollback mechanism for failed migrations

### GUI Stability
- [x] Fix broken symlink handling in CSV loader
- [ ] Add better error handling for missing CSV files
- [ ] Implement GUI crash recovery/auto-restart
- [ ] Add loading states for all data operations

### Orchestrator Core
- [ ] Wire up actual attack execution in queue processor (currently placeholder)
- [ ] Implement attack result persistence to database
- [ ] Add attack retry logic with exponential backoff
- [ ] Implement attack timeout handling

---

## 🟠 High Priority / Core Features

### The Horsemen (Multi-Target Attack Orchestration)
- [ ] **War** - Simultaneous multi-target attack coordinator
  - [ ] Parallel WPS attacks on multiple networks
  - [ ] Load balancing across available wireless adapters
  - [ ] Priority-based target selection
  - [ ] Resource allocation per attack type
- [ ] **Famine** - Resource exhaustion attacks
  - [ ] Deauth floods across multiple targets
  - [ ] Channel saturation detection
  - [ ] Intelligent frequency hopping to avoid detection
- [ ] **Pestilence** - Rogue AP / Evil Twin coordinator
  - [ ] Auto-clone high-value targets
  - [ ] Karma attack automation
  - [ ] Captive portal deployment
  - [ ] Credential harvesting integration
- [ ] **Death** - Final exploitation phase
  - [ ] Post-exploitation automation
  - [ ] Network pivot discovery
  - [ ] Lateral movement suggestions
  - [ ] Data exfiltration helpers

### Attack Service Integration
- [ ] Complete WPS attack execution (_execute_wps_attack)
  - [ ] Integrate with WPSAttackService
  - [ ] Add Pixie Dust attack
  - [ ] Add PIN bruteforce
  - [ ] Track attack progress
- [ ] Complete handshake capture (_execute_handshake_capture)
  - [ ] Integrate with HandshakeService
  - [ ] Add targeted deauth
  - [ ] Verify handshake validity
  - [ ] Store handshake files with metadata
- [ ] Complete WEP crack execution (_execute_wep_crack)
  - [ ] Integrate with WEPCrackService
  - [ ] Monitor IV collection progress
  - [ ] Trigger ARP replay when needed
- [ ] Complete WPA crack execution (_execute_wpa_crack)
  - [ ] Integrate with WPACrackService
  - [ ] Queue hashcat jobs
  - [ ] Monitor GPU utilization
  - [ ] Implement dictionary attack strategies
- [ ] Complete deauth execution (_execute_deauth)
  - [ ] Integrate with DeauthService
  - [ ] Add client targeting
  - [ ] Implement deauth patterns

### Auto-Attack Intelligence
- [ ] Machine learning for attack score calculation
- [ ] Historical success rate tracking per encryption type
- [ ] Time-of-day attack scheduling (avoid detection)
- [ ] Geographic clustering for efficient wardriving routes
- [ ] Client density analysis for handshake capture timing
- [ ] Automatic wordlist generation from SSID/location
- [ ] Rainbow table integration for common passwords

### Queue Management
- [ ] Add queue persistence (survive orchestrator restarts)
- [ ] Implement job dependencies (handshake before crack)
- [ ] Add job scheduling (time-based execution)
- [ ] Queue import/export for multi-system coordination
- [ ] Web-based queue visualization
- [ ] Real-time queue priority adjustment based on results

---

## 🟡 Medium Priority / Enhancement

### Orchestrator Services

#### GPS Service Enhancements
- [ ] Add NMEA sentence parsing for more GPS devices
- [ ] Implement GPS track recording (GPX export)
- [ ] Add altitude-based signal analysis
- [ ] Geofencing for auto-attack zones
- [ ] Speed-based scan rate adjustment
- [ ] GPS fix quality thresholds for attack triggering

#### Scanner Service Enhancements
- [ ] Multi-adapter support (parallel scanning)
- [ ] Channel-specific scanning modes
- [ ] 5GHz band support
- [ ] Bluetooth LE scanning integration
- [ ] SDR spectrum analysis integration
- [ ] Hidden network detection heuristics

#### Triangulation Service
- [ ] Implement TDOA triangulation
- [ ] Add signal strength heatmap generation
- [ ] Multi-observation fusion algorithm
- [ ] Confidence score calculation
- [ ] Export to KML for Google Earth
- [ ] Integration with WiGLE API for AP location validation

### Database Enhancements
- [ ] Implement database sharding for large datasets
- [ ] Add full-text search on SSIDs
- [ ] Create materialized views for common queries
- [ ] Implement database replication for backup
- [ ] Add database vacuum/optimize scheduler
- [ ] Export to SQLite/PostgreSQL/MySQL formats
- [ ] Import from Kismet/Airodump CSV formats

### API Layer
- [ ] RESTful API v2 with versioning
- [ ] WebSocket support for real-time updates
- [ ] GraphQL endpoint for complex queries
- [ ] API authentication (JWT tokens)
- [ ] Rate limiting per client
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Client SDKs (Python, JavaScript, Go)

### Web Interface
- [ ] Real-time dashboard with live map
- [ ] Attack queue visualization
- [ ] Service health monitoring
- [ ] Configuration management UI
- [ ] Log viewer with filtering
- [ ] Export reports (PDF/HTML)
- [ ] Mobile-responsive design

### CLI Tool
- [ ] Interactive shell mode (cmd2 based)
- [ ] Batch command execution
- [ ] Command history and completion
- [ ] Colored output and progress bars
- [ ] Remote orchestrator control
- [ ] Script automation support

---

## 🟢 Low Priority / Nice-to-Have

### Security & Hardening
- [ ] Implement orchestrator API authentication
- [ ] Add RBAC (Role-Based Access Control)
- [ ] Encrypt sensitive data at rest (passwords, handshakes)
- [ ] Secure IPC between services (TLS)
- [ ] Audit logging for all attacks
- [ ] Implement rate limiting to avoid detection
- [ ] Add VPN/proxy support for remote operations
- [ ] Secure erase for captured data

### Monitoring & Alerting
- [ ] Prometheus metrics export
- [ ] Grafana dashboard templates
- [ ] Email/SMS/Telegram notifications
- [ ] Attack success/failure alerts
- [ ] Service health alerts
- [ ] Disk space monitoring
- [ ] Temperature monitoring (prevent overheating)
- [ ] Battery level alerts (laptop/phone)

### Reporting & Analytics
- [ ] Generate attack success statistics
- [ ] Encryption type distribution charts
- [ ] Vendor analysis reports
- [ ] Time-series analysis of network density
- [ ] Crack time prediction models
- [ ] ROI analysis (time vs success rate)
- [ ] Comparative analysis between locations

### Dictionary Management
- [ ] Automatic dictionary merging
- [ ] Deduplication across sources
- [ ] Frequency-based sorting
- [ ] Per-target custom dictionaries
- [ ] Integration with Have I Been Pwned
- [ ] Dictionary generation from OSINT
- [ ] Markov chain password generation

### WiGLE Integration
- [ ] Auto-upload discovered networks
- [ ] Download surrounding network data
- [ ] Compare local DB with WiGLE
- [ ] Identify moved/relocated APs
- [ ] Historical location tracking

### Bluetooth Enhancements
- [ ] BLE device discovery
- [ ] Bluetooth Classic enumeration
- [ ] Device pairing attacks
- [ ] Service discovery
- [ ] Bluetooth mesh network mapping

### SDR Features
- [ ] Spectrum waterfall visualization
- [ ] Signal classification (WiFi/Bluetooth/ZigBee)
- [ ] Frequency hopping detection
- [ ] Interference analysis
- [ ] Custom protocol decoding

### Plugin System
- [ ] Plugin API for custom attacks
- [ ] Hot-reloadable plugins
- [ ] Plugin marketplace/repository
- [ ] Sandboxed plugin execution
- [ ] Plugin dependency management

### Mobile App
- [ ] Android companion app
- [ ] iOS companion app
- [ ] Remote control via mobile
- [ ] Mobile GPS integration
- [ ] Push notifications
- [ ] Offline mode with sync

### Multi-System Coordination
- [ ] Distributed attack coordination
- [ ] Load balancing across multiple systems
- [ ] Shared queue across systems
- [ ] Centralized result aggregation
- [ ] Master/slave architecture
- [ ] Conflict resolution for duplicate work

---

## 🔵 Research / Experimental

### AI/ML Integration
- [ ] Neural network for encryption detection
- [ ] Reinforcement learning for attack strategy
- [ ] Anomaly detection for IDS evasion
- [ ] NLP for SSID-based wordlist generation
- [ ] Computer vision for physical recon (camera integration)

### Advanced Attacks
- [ ] KRACK attack implementation
- [ ] DragonBlood (WPA3 attacks)
- [ ] PMKID attack without clients
- [ ] FragAttacks implementation
- [ ] Evil twin with SSL stripping
- [ ] DNS hijacking automation

### Stealth & Evasion
- [ ] MAC address randomization per attack
- [ ] Packet injection timing randomization
- [ ] Channel hopping patterns to avoid detection
- [ ] Power level adjustment for stealth
- [ ] Mimicry of legitimate clients

### Hardware Integration
- [ ] Flipper Zero integration (already started)
- [ ] WiFi Pineapple integration
- [ ] HackRF SDR support
- [ ] LimeSDR support
- [ ] Ubertooth One for Bluetooth
- [ ] RTL-SDR for receive-only operations

---

## 🛠️ Technical Debt

### Code Quality
- [ ] Add type hints to all functions
- [ ] Comprehensive unit test coverage (>80%)
- [ ] Integration tests for attack workflows
- [ ] Performance profiling and optimization
- [ ] Memory leak detection and fixes
- [ ] Code style enforcement (black/flake8)
- [ ] Documentation generation (Sphinx)

### Architecture
- [ ] Refactor attack services into separate processes
- [ ] Implement proper dependency injection
- [ ] Use async/await for I/O operations
- [ ] Reduce coupling between services
- [ ] Implement event sourcing for state management
- [ ] Add circuit breakers for external services

### Infrastructure
- [ ] Docker containerization
- [ ] Kubernetes deployment manifests
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Automated release process
- [ ] Package for apt/yum repositories
- [ ] Snap/Flatpak packages

---

## 📋 Documentation

- [ ] Architecture decision records (ADR)
- [ ] API reference documentation
- [ ] User manual with screenshots
- [ ] Video tutorials
- [ ] Troubleshooting guide
- [ ] Security best practices
- [ ] Legal disclaimer and usage policy
- [ ] Contribution guidelines
- [ ] Roadmap and milestones

---

## 🐛 Known Issues

- [x] GUI crashes on missing CSV files (broken symlinks)
- [x] WEP service false positive health check
- [x] Database queries using wrong tables (Network vs CurrentScanNetwork)
- [ ] Scanner service process detection fails sometimes
- [ ] GPS phone battery reporting delays
- [ ] Concurrent database writes cause locks
- [ ] Memory usage grows over time (need periodic cleanup)
- [ ] Tray icon doesn't always update status colors

---

## 🎯 Version Milestones

### v1.0 - Foundation (Current)
- [x] Basic scanning and database storage
- [x] Tray icon with service monitoring
- [x] Manual attack queue
- [x] Basic GPS integration
- [x] Auto-attack cycle
- [ ] Complete attack execution

### v1.5 - Automation
- [ ] The Horsemen multi-attack framework
- [ ] Full attack service integration
- [ ] Web interface v1
- [ ] CLI tool v1
- [ ] Dictionary manager

### v2.0 - Intelligence
- [ ] ML-based attack scoring
- [ ] Predictive analytics
- [ ] Advanced reporting
- [ ] Multi-system coordination
- [ ] Plugin system

### v3.0 - Enterprise
- [ ] RBAC and multi-tenancy
- [ ] Distributed architecture
- [ ] Professional reporting
- [ ] Compliance features
- [ ] Commercial support

---

**Last Updated:** 2025-11-03
**Maintainer:** Gattrose-NG Development Team
