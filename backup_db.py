"""
backup_db.py — Export the entire leads_db database to a SQL dump file.
Run manually or schedule via Task Scheduler.
"""

import subprocess
import os
from datetime import datetime
from config import DB_CONFIG

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")


def backup_database():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(BACKUP_DIR, f"leads_db_backup_{timestamp}.sql")

    cmd = [
        "mysqldump",
        f"-h{DB_CONFIG['host']}",
        f"-u{DB_CONFIG['user']}",
        f"-p{DB_CONFIG['password']}",
        DB_CONFIG["database"],
    ]

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            subprocess.run(cmd, stdout=f, check=True)
        print(f"Backup created: {filepath}")
        return filepath
    except FileNotFoundError:
        print("ERROR: 'mysqldump' not found. Make sure MySQL bin folder is in your system PATH.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Backup failed: {e}")
        return None


if __name__ == "__main__":
    backup_database()