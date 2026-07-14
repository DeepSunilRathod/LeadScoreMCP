"""
lib/auth.py — Simple role-based authentication (Admin / Manager / Sales Executive)
"""

import sys
import os
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import query, execute

ROLES = ["admin", "manager", "executive"]


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username, password, role):
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}")
    execute(
        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
        [username, hash_password(password), role],
    )
    return True


def verify_login(username, password):
    rows = query("SELECT * FROM users WHERE username = %s", [username])
    if not rows:
        return None
    user = rows[0]
    if user["password_hash"] == hash_password(password):
        return {"id": user["id"], "username": user["username"], "role": user["role"]}
    return None


if __name__ == "__main__":
    # Create default users for testing
    try:
        create_user("admin", "admin123", "admin")
        print("Created admin / admin123")
    except Exception as e:
        print(f"admin: {e}")

    try:
        create_user("manager1", "manager123", "manager")
        print("Created manager1 / manager123")
    except Exception as e:
        print(f"manager1: {e}")

    try:
        create_user("sales1", "sales123", "executive")
        print("Created sales1 / sales123")
    except Exception as e:
        print(f"sales1: {e}")