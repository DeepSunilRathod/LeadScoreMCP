"""
lib/db.py — MySQL database helper functions
Provides simple query(), scalar(), and execute() functions
"""

import sys
import os

# Add parent directory to path so we can import config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from config import DB_CONFIG


def get_conn():
    """Create a new database connection"""
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=None):
    """Run a SELECT query, returns list of dicts"""
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or [])
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def scalar(sql, params=None):
    """Run a query and return a single value (first column of first row)"""
    rows = query(sql, params)
    if not rows:
        return None
    return list(rows[0].values())[0]


def execute(sql, params=None):
    """Run INSERT / UPDATE / DELETE, returns last inserted row id"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or [])
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    conn.close()
    return last_id


def execute_many(sql, params_list):
    """Run the same INSERT/UPDATE for many rows at once (fast bulk insert)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(sql, params_list)
    conn.commit()
    affected = cur.rowcount
    cur.close()
    conn.close()
    return affected


# Quick self-test when running this file directly
if __name__ == "__main__":
    print("Testing database connection...")
    try:
        result = scalar("SELECT 1")
        print(f"✅ Connection successful! Test query returned: {result}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")