# Version Management Guide

## IMPORTANT: Always Update ALL Version References

When incrementing the version number, you MUST update it in ALL of the following locations:

### 1. VERSION File
```
/VERSION
```
This is the source of truth for the application version.

### 2. Wrapper Script
```python
# File: gattrose-ng.py
VERSION = "X.Y.Z"
```

### 3. Version Module
The `src/version.py` module automatically reads from the VERSION file, but verify it's working correctly.

### 4. About Dialog
The About dialogs now dynamically import from `src.version`, so they should automatically update. Verify by checking:
- Settings tab → About section
- Help menu → About Gattrose-NG dialog

## Version Numbering Scheme

We use Semantic Versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes, major architecture changes
- **MINOR**: New features, enhancements, non-breaking changes
- **PATCH**: Bug fixes, small improvements

### Examples:
- `2.2.2` → `2.2.3`: Bug fix
- `2.2.2` → `2.3.0`: New feature
- `2.2.2` → `3.0.0`: Major rewrite

## Checklist for Version Updates

When releasing a new version:

- [ ] Update `/VERSION` file
- [ ] Update `gattrose-ng.py` VERSION constant
- [ ] Create changelog in `docs/CHANGELOG_vX.Y.Z.md`
- [ ] Update systemd service version metadata (if services changed)
- [ ] Test version displays in GUI:
  - [ ] Settings tab shows correct version
  - [ ] About dialog shows correct version
  - [ ] Launcher script shows correct version
- [ ] Commit changes with message: "Bump version to X.Y.Z"
- [ ] Tag release: `git tag vX.Y.Z`

## Current Version

**Version:** 2.2.2

**Release Date:** 2025-11-01

**Changes:**
- Added unassociated clients group with probe request display
- Centralized version management via `src/version.py`
- Fixed About dialog to show dynamic version
- Enhanced ScanSession schema for live/archived scans
- Added OUI database tables and downloader utility
- Prepared for systemd services integration

## Future: Automated Version Management

Consider implementing:
1. Pre-commit hook to verify all versions match
2. Build script that auto-updates all version references
3. CI/CD pipeline that enforces version consistency
