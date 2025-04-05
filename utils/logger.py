import logging
import os
from utils.config import Config

def setup_logger():
    """Configure and return a logger for the application"""
    # Ensure log directory exists
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging with a basic configuration
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE, mode='w'),
            logging.StreamHandler()  # Simple console output without fancy formatting
        ]
    )

    return logging.getLogger(__name__)

# Create a module-level logger
logger = setup_logger() 