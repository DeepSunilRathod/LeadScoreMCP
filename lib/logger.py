"""
lib/logger.py — Simple file-based logging for errors and info messages.
Writes to logs/app.log so issues can be reviewed after Claude Desktop closes.
"""

import os
import sys
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def _write_log(level, message):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] {message}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # never let logging itself crash the app


def log_info(message):
    _write_log("INFO", message)
    print(f"[INFO] {message}", file=sys.stderr)


def log_error(message):
    _write_log("ERROR", message)
    print(f"[ERROR] {message}", file=sys.stderr)


def log_warning(message):
    _write_log("WARNING", message)
    print(f"[WARNING] {message}", file=sys.stderr)