import logging
import os
from utils.config import Config

def setup_logger():
    """Configure and return a logger for the application"""
    # Ensure log directory exists
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=Config.LOG_FILE,
        filemode='w'
    )

    # Create a console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)

    # Get the root logger and add the console handler
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)

    return logging.getLogger(__name__)

# Create a module-level logger
logger = setup_logger() 