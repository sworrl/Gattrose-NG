# Gattrose-NG Project Structure

## Project Root Files (Keep These Only)

### Essential Files
- `gattrose-ng.py` - Main launcher script
- `gattrose-ng.desktop` - Desktop application launcher
- `README.md` - Project documentation
- `LICENSE` - License file
- `VERSION` - Version number
- `.gitignore` - Git ignore rules
- `TODO.md` - Development roadmap and progress tracking
- `PROJECT_STRUCTURE.md` - This file

### Directories
- `src/` - Source code
- `bin/` - Shell scripts and executables
- `data/` - Database, captures, configs
- `assets/` - Icons, images, resources
- `migrations/` - Database migration scripts
- `docs/` - Documentation
- `tests/` - Test files
- `.venv/` - Python virtual environment (git ignored)

## What NOT to Keep in Project Root

❌ Migration scripts (moved to `migrations/`)
❌ Test scripts
❌ Temporary files
❌ Build artifacts
❌ Log files
❌ Cache files

## Clean Project Root Command

```bash
# Remove temporary/unwanted files
find . -maxdepth 1 -type f -name "*.pyc" -delete
find . -maxdepth 1 -type f -name "*.log" -delete
find . -maxdepth 1 -type f -name "*.tmp" -delete
find . -maxdepth 1 -type f -name "test_*.py" -delete
```

## Notes

- Keep the project root clean and organized
- Only essential launcher/config files belong in root
- Use appropriate subdirectories for everything else
- Migration scripts go in `migrations/`
- Documentation goes in `docs/` or stays as root-level .md files
