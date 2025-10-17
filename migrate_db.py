#!/usr/bin/env python3
"""
Database migration script to add user_id support to existing database.
"""
import sqlite3
from pathlib import Path

def migrate_database():
    """Migrate existing database to support multi-user authentication."""
    db_path = "data/transactions.db"

    if not Path(db_path).exists():
        print(f"❌ Database not found at {db_path}")
        return False

    print("=" * 60)
    print("Database Migration - Adding User Support")
    print("=" * 60)
    print()

    try:
        with sqlite3.connect(db_path) as conn:
            # Check if users table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='users'
            """)

            if not cursor.fetchone():
                print("Creating users table...")
                conn.execute("""
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        full_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_username
                    ON users(username)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_email
                    ON users(email)
                """)

                print("✅ Users table created")
            else:
                print("ℹ️  Users table already exists")

            # Check if transactions table has user_id
            cursor = conn.execute("PRAGMA table_info(transactions)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'user_id' not in columns:
                print("Adding user_id column to transactions table...")

                # Add user_id column with default value 1
                conn.execute("""
                    ALTER TABLE transactions
                    ADD COLUMN user_id INTEGER DEFAULT 1 NOT NULL
                """)

                # Create index on user_id
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_id
                    ON transactions(user_id)
                """)

                print("✅ user_id column added to transactions table")
                print("   (All existing transactions assigned to user_id=1)")
            else:
                print("ℹ️  Transactions table already has user_id column")

            conn.commit()

        print()
        print("=" * 60)
        print("✅ Database migration completed successfully!")
        print("=" * 60)
        print()
        print("Next step: Run 'python3 init_auth.py' to create your admin user")
        print()
        return True

    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    migrate_database()
