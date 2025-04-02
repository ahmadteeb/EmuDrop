"""
Main entry point for the Game Downloader application.

This module initializes and runs the main application loop, handling any top-level
exceptions that might occur during execution.
"""
from typing import NoReturn
import sys

from app import GameDownloaderApp
from utils.logger import logger

def main() -> NoReturn:
    """
    Main entry point for the game downloader application.
    
    Initializes the GameDownloaderApp and handles any uncaught exceptions,
    ensuring they are properly logged before the application exits.
    """
    try:
        app = GameDownloaderApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed to start: {e}", exc_info=True)
        print("Application failed to start. Check the log file for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()