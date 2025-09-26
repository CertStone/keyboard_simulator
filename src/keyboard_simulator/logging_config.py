"""Centralized logging configuration for the Keyboard Simulator project."""

import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_dir: Path | str = "logs") -> None:
    """
    Set up logging to both console and a file.

    Args:
        log_level: The minimum logging level to capture (e.g., "DEBUG", "INFO").
        log_dir: The directory where log files will be stored.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "keyboard_simulator.log"

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Clear existing handlers to avoid duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create a file handler
    # Use 'a' for append mode. Use a rotating file handler for long-running apps.
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Capture all levels in the file
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level.upper())
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.info("Logging configured: Level=%s, File=%s", log_level, log_file)

def disable_logging() -> None:
    """Disable all logging by removing handlers and adding a NullHandler."""
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(logging.NullHandler())
    root_logger.setLevel(logging.CRITICAL + 1)  # Effectively silence the root logger

# Example of getting a logger for a specific module
# In other files, you would just do:
# import logging
# logger = logging.getLogger(__name__)
# logger.info("This is a test message.")
