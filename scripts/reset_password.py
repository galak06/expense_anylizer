#!/usr/bin/env python3
"""
Script to reset a user's password.
"""
import bcrypt
import sqlite3
from pathlib import Path

def reset_password(username: str, new_password: str):
    """Reset password for a user."""
    db_path = Path("data/transactions.db")

    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False

    # Hash the new password (decode to string for storage)
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    with sqlite3.connect(db_path) as conn:
        # Check if user exists
        cursor = conn.execute("SELECT id, username, email FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if not user:
            print(f"❌ User '{username}' not found")
            return False

        user_id, username, email = user

        # Update password
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (password_hash, user_id)
        )
        conn.commit()

        print("=" * 60)
        print(f"✅ Password reset successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   New Password: {new_password}")
        print("=" * 60)
        print()
        print(f"You can now login with:")
        print(f"   Username: {username}")
        print(f"   Password: {new_password}")

        return True

if __name__ == "__main__":
    # Reset admin password
    username = "admin"
    new_password = "admin123"

    print("Resetting password for admin user...")
    print()
    reset_password(username, new_password)
