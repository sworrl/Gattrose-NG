#!/usr/bin/env python3
"""
Gattrose Main Application Entry Point
Checks prerequisites and launches Qt6 GUI

"Gattrose" - A nickname for a baby gator with a fierce appetite
Developed by REAvER from Falcon Technix
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_prerequisites():
    """Check if all prerequisites are met"""
    try:
        from src.core.prerequisites import PrerequisiteChecker

        checker = PrerequisiteChecker()
        checker.check_all()

        if not checker.all_required_met():
            print("[!] Missing required prerequisites")
            print("[*] Launching prerequisite installer...")
            return False

        print("[+] All required prerequisites are met")
        return True

    except Exception as e:
        print(f"[!] Error checking prerequisites: {e}")
        import traceback
        traceback.print_exc()
        return False


def launch_prerequisite_installer():
    """Launch the prerequisite installer GUI"""
    try:
        from src.gui.prereq_installer import PrerequisiteInstallerGUI

        installer = PrerequisiteInstallerGUI()
        should_continue = installer.run()

        if not should_continue:
            print("[*] User cancelled installation")
            return False

        print("[+] Prerequisites satisfied, continuing to main application...")
        return True

    except Exception as e:
        print(f"[!] Error in prerequisite installer: {e}")
        import traceback
        traceback.print_exc()
        return False


def launch_main_app():
    """Launch the main Qt6 application"""
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication
        from src.gui.main_window import MainWindow

        # IMPORTANT: Set this BEFORE creating QApplication
        # Required for QtWebEngineWidgets to work properly
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

        # Disable Chromium sandbox when running as root
        # QtWebEngine uses Chromium internally which doesn't support running as root with sandbox
        if os.geteuid() == 0:
            os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--no-sandbox'

        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("Gattrose")
        app.setOrganizationName("Gattrose")

        # Create and show main window
        window = MainWindow()
        window.show()

        # Run event loop
        return app.exec()

    except ImportError as e:
        print(f"[!] Failed to import Qt6 modules: {e}")
        print("[!] Please ensure PyQt6 is installed in the virtual environment")
        print("[*] Run: pip install PyQt6")
        return 1
    except Exception as e:
        print(f"[!] Error launching main application: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("  Gattrose - Wireless Penetration Testing Suite")
    print("  Starting application...")
    print("="*60 + "\n")

    # Check for and kill duplicate/stuck processes
    try:
        from src.utils.process_manager import check_and_cleanup_processes

        print("[*] Checking for duplicate or stuck processes...")
        if not check_and_cleanup_processes():
            print("[!] Warning: Process cleanup failed, continuing anyway...")
        else:
            print("[✓] Process check complete\n")

    except Exception as e:
        print(f"[!] Warning: Process manager error: {e}")
        print("[*] Continuing anyway...\n")

    # Run boot-time verification and auto-fix
    try:
        from src.core.boot_verify import verify_at_boot

        print("[*] Running boot-time verification...")
        if not verify_at_boot():
            print("[!] Warning: Boot verification found errors")
            print("[*] Attempting to continue anyway...\n")
        else:
            print("[✓] Boot verification complete\n")
    except Exception as e:
        print(f"[!] Warning: Boot verification error: {e}")
        print("[*] Continuing anyway...\n")

    # Set environment for proper Qt operation
    os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')

    # Check prerequisites
    prereqs_ok = check_prerequisites()

    if not prereqs_ok:
        # Launch installer
        if not launch_prerequisite_installer():
            print("[*] Exiting...")
            return 1

    # Launch main application
    print("[*] Launching Gattrose main application...")
    return launch_main_app()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[*] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
