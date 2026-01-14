import logging
import os
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler

def setup_logging(name: str, log_level=logging.INFO, log_dir: Optional[Path] = None) -> logging.Logger:
    """
    Sets up a centralized logger for the application.

    Args:
        name: The name of the logger (e.g., __name__ for module-specific logging).
        log_level: The minimum logging level to capture (e.g., logging.INFO, logging.DEBUG).
        log_dir: Optional. The directory where log files should be stored.
                 If None, logs to console only.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Prevent adding multiple handlers if setup_logging is called multiple times
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler (if log_dir is provided)
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{name}.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10 MB
                backupCount=5
            )
            file_handler.setLevel(log_level)
            file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    return logger

# Global logger for general application messages
# This can be configured by the main application
app_log_dir = Path.cwd() / "logs" # Default log directory
main_logger = setup_logging("gattrose-ng", log_dir=app_log_dir)

# Example usage:
# from src.utils.logger import main_logger
# main_logger.info("Application started")
