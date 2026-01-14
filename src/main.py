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

from src.utils.logger import main_logger



def check_prerequisites():

    """Check if all prerequisites are met"""

    try:

        from src.core.prerequisites import PrerequisiteChecker



        checker = PrerequisiteChecker()

        checker.check_all()



        if not checker.all_required_met():

            main_logger.warning("Missing required prerequisites")

            main_logger.info("Launching prerequisite installer...")

            return False



        main_logger.info("All required prerequisites are met")

        return True



    except Exception as e:

        main_logger.exception(f"Error checking prerequisites: {e}")

        return False





def launch_prerequisite_installer():

    """Launch the prerequisite installer GUI"""

    try:

        from src.gui.prereq_installer import PrerequisiteInstallerGUI



        installer = PrerequisiteInstallerGUI()

        should_continue = installer.run()



        if not should_continue:

            main_logger.info("User cancelled installation")

            return False



        main_logger.info("Prerequisites satisfied, continuing to main application...")

        return True



    except Exception as e:

        main_logger.exception(f"Error in prerequisite installer: {e}")

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

            main_logger.info("Running as root, disabling Chromium sandbox for QtWebEngine.")



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

        main_logger.error(f"Failed to import Qt6 modules: {e}")

        main_logger.error("Please ensure PyQt6 is installed in the virtual environment. Run: pip install PyQt6")

        return 1

    except Exception as e:

        main_logger.exception(f"Error launching main application: {e}")

        return 1





def main():

    """Main entry point"""

    main_logger.info("="*60)

    main_logger.info("  Gattrose - Wireless Penetration Testing Suite")

    main_logger.info("  Starting application...")

    main_logger.info("="*60)



    # Check for and kill duplicate/stuck processes

    try:

        from src.utils.process_manager import check_and_cleanup_processes



        main_logger.info("Checking for duplicate or stuck processes...")

        if not check_and_cleanup_processes():

            main_logger.warning("Process cleanup failed, continuing anyway...")

        else:

            main_logger.info("Process check complete")



    except Exception as e:

        main_logger.exception(f"Warning: Process manager error: {e}. Continuing anyway...")



    # Run boot-time verification and auto-fix

    try:

        from src.core.boot_verify import verify_at_boot



        main_logger.info("Running boot-time verification...")

        if not verify_at_boot():

            main_logger.warning("Boot verification found errors. Attempting to continue anyway...")

        else:

            main_logger.info("Boot verification complete")

    except Exception as e:

        main_logger.exception(f"Warning: Boot verification error: {e}. Continuing anyway...")



    # Set environment for proper Qt operation

    os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')



    # Check prerequisites

    prereqs_ok = check_prerequisites()



    if not prereqs_ok:

        # Launch installer

        if not launch_prerequisite_installer():

            main_logger.info("Exiting...")

            return 1



    # Launch main application

    main_logger.info("Launching Gattrose main application...")

    return launch_main_app()





if __name__ == "__main__":

    try:

        sys.exit(main())

    except KeyboardInterrupt:

        main_logger.info("Interrupted by user")

        sys.exit(0)

    except Exception as e:

        main_logger.exception(f"Fatal error: {e}")

        sys.exit(1)
