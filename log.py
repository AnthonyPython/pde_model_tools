# log.py
import logging


def setup_logger():
    """Configure logging."""
    logger = logging.getLogger("PMT")
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        # logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(name)s: %(levelname)s: %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger


log = setup_logger()
"""PMT log instance."""
