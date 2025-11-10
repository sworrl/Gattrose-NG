"""
Gattrose-NG Version Management
Central version constant used throughout the application
"""

import os
from pathlib import Path

# Try to read from VERSION file
VERSION_FILE = Path(__file__).parent.parent / "VERSION"

if VERSION_FILE.exists():
    with open(VERSION_FILE, 'r') as f:
        VERSION = f.read().strip()
else:
    # Fallback version
    VERSION = "2.2.5"

# Also try environment variable (set by wrapper script)
VERSION = os.environ.get("GATTROSE_NG_VERSION", VERSION)

# Application metadata
APP_NAME = "Gattrose-NG"
APP_DESCRIPTION = "Wireless Penetration Testing Suite"
APP_AUTHOR = "Gattrose Team"
APP_LICENSE = "For authorized security testing only"

def get_version() -> str:
    """Get current version string"""
    return VERSION

def get_version_info() -> dict:
    """Get version information as dictionary"""
    return {
        "version": VERSION,
        "name": APP_NAME,
        "description": APP_DESCRIPTION,
        "author": APP_AUTHOR,
        "license": APP_LICENSE
    }
