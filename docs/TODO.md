# Gattrose-NG Improvement TODO List

This document outlines a list of recommended improvements for the Gattrose-NG application.

## High Priority

*   **Implement Centralized Logging:** Replace all `print()` statements with a proper logging framework (e.g., `logging`). This will allow for configurable log levels, log rotation, and structured logging, which is essential for debugging a complex application.
*   **Refactor Database Session Management:** The current implementation of `gattrose-daemon.py` creates a new database session for every single AP discovery or update. This is highly inefficient. Refactor the code to use a single session for a batch of updates or a session scope that is tied to the scanner's lifecycle.
*   **Fix `sys.path` Manipulation:** Remove all instances of `sys.path.insert(0, ...)`. Instead, package the project properly (e.g., with a `pyproject.toml` or `setup.py`) and install it in editable mode (`pip install -e .`). This will ensure that the project's modules are always available on the Python path without manual manipulation.
*   **Address TODOs:**
    *   Implement the Bluetooth scanner.
    *   Implement the SDR scanner.
    *   Implement the client-side database logging in `gattrose-daemon.py`.

## Medium Priority

*   **Eliminate Hardcoded Paths and Commands:**
    *   Make the `airodump-ng` path configurable.
    *   Make the capture output directory configurable.
    *   Remove the `sudo` from the `airodump-ng` command and instruct the user to run the script with `sudo` if necessary.
*   **Review and Fix Race Conditions:** Carefully review the multithreaded code in `wifi_scanner.py` to identify and fix any potential race conditions. Use thread-safe data structures (e.g., `queue.Queue`) and proper locking mechanisms.
*   **Improve `airodump-ng` Parsing:** The current CSV parsing is fragile. Consider using a more robust method to parse the `airodump-ng` output, or add more error handling to the existing parser.
*   **Improve `get_networks_by_location`:** For more accurate location-based searching, consider using a spatial index like GeoAlchemy2 or a geohash-based approach.

## Low Priority

*   **Refactor `main()` functions:** The `main()` functions in `src/main.py` and `bin/gattrose-daemon.py` could be broken down into smaller, more focused functions to improve readability.
*   **Add Asynchronous Support:** For even higher performance, consider migrating the I/O-bound operations (like database access and process management) to an asynchronous framework like `asyncio`.
*   **Add unit tests:** The project is lacking unit tests. Adding unit tests for the core components would improve the code quality and make it easier to refactor the code in the future.