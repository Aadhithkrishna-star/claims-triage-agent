"""
Structured logging setup for the application.
"""
import logging
import sys


def setup_logging() -> logging.Logger:
    """Configure structured logging."""
    logger = logging.getLogger("claims_agent")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


logger = setup_logging()