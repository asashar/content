
import logging
import os
from time import sleep

def setup_logger(log_file="log.txt", level=logging.DEBUG):
    """
    Configures the root logger to write to both the console and a log file.

    Parameters:
        log_file (str): The path to the log file.
    """
    # Delete the existing log file if it exists
    try:
        if os.path.exists(log_file):
            os.remove(log_file)
        sleep(1)
    except PermissionError:
        print("Unable to delete existing log file")

    # Create a logger
    logger = logging.getLogger("dual_logger")
    logger.setLevel(level)  # Set the lowest level to capture all logs

    # Create a file handler for logging to a file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Log all levels to the file
    file_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_format)

    # Create a stream handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Show INFO and above in the console
    console_format = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_format)

    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
