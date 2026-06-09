"""
Logging setup for ringforge.

Outputs structured logs to both:
    - console (human-readable, during CLI use)
    - logs/{date}.log (detailed JSON lines for debugging)
"""

import json
import logging
import os
import sys
from datetime import date

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")


def setup(level: str = "INFO"):
    """
    Configure logging. Creates the logs/ directory if needed.
    Logs go to both a dated file and the console.
    """
    os.makedirs(_LOG_DIR, exist_ok=True)

    log_file = os.path.join(_LOG_DIR, f"{date.today().isoformat()}.log")

    # File handler: JSON lines format for machine parsing
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(_JSONFormatter())

    # Console handler: simple human-readable format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(levelname)s  %(message)s"))

    _root = logging.getLogger("ringforge")
    _root.setLevel(getattr(logging, level.upper(), logging.INFO))
    _root.addHandler(file_handler)
    _root.addHandler(console_handler)

    return _root


def get_logger():
    """Return the ringforge logger."""
    return logging.getLogger("ringforge")


class _JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def format(self, record):
        obj = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(obj)
