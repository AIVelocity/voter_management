import logging
import os
import sys

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Log file paths
api_log_file = os.path.join("logs", "api.log")
error_log_file = os.path.join("logs", "error.log")

# Create custom logger
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

# Avoid duplicate handlers during reload
if logger.hasHandlers():
    logger.handlers.clear()

# --- Formatters ---

# Formatter for INFO logs (timestamp, module, API name placeholder, message)
info_formatter = logging.Formatter(
    "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)

#  Formatter for ERROR logs (add traceback info)
error_formatter = logging.Formatter(
    "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)

# --- Handlers ---

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(info_formatter)

# File handler for INFO and above (api.log)
file_handler = logging.FileHandler(api_log_file, mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(info_formatter)

# File handler for ERROR only (error.log)
error_handler = logging.FileHandler(error_log_file, mode="a", encoding="utf-8")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(error_formatter)

# Add handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.addHandler(error_handler)

logger.info("Logger initialized — writing to console, api.log, and error.log")
