"""
Logging configuration — rotating file handler + console output.
"""

import logging
from logging.handlers import RotatingFileHandler
from app.config import LOGS_DIR, DEBUG


def setup_logger(name: str = "app") -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

    # Avoid duplicate handlers on reload
    if logger.handlers:
        return logger

    # Format
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — rotating 5 MB, 3 backups
    log_file = LOGS_DIR / "app.log"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


# Singleton logger
logger = setup_logger()
