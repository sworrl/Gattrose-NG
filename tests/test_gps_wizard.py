#!/usr/bin/env python3
"""
Test GPS Setup Wizard
Run this to test the GPS setup dialog standalone
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from src.gui.gps_setup_dialog import show_gps_setup_wizard


def main():
    app = QApplication(sys.argv)

    print("=" * 70)
    print("GPS Setup Wizard Test")
    print("=" * 70)
    print()
    print("This will launch the GPS setup wizard.")
    print("Follow the on-screen instructions to set up Android phone GPS.")
    print()

    # Show the wizard
    result = show_gps_setup_wizard()

    if result:
        print()
        print("=" * 70)
        print("✅ Setup completed successfully!")
        print("=" * 70)
        print()
        print("Your Android phone GPS is ready to use.")
        print("The GPS service will now use phone GPS with ±10-20m accuracy.")
    else:
        print()
        print("=" * 70)
        print("Setup was skipped or cancelled.")
        print("=" * 70)
        print()
        print("You can run this wizard again anytime:")
        print("  python3 test_gps_wizard.py")
        print()
        print("Or from the GUI: Click the GPS status in the status bar")

    return 0


if __name__ == "__main__":
    sys.exit(main())
