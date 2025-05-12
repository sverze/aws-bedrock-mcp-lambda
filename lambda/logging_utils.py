import logging
import sys

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove default handlers
for handler in logger.handlers:
    logger.removeHandler(handler)

# Create a handler that writes to stderr (Lambda captures this)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(handler)