#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL
This script will transfer all data from the existing SQLite database to PostgreSQL
"""

import sqlite3
import psycopg2
import os
import sys
from datetime import datetime
import json
from typing import List, Dict, Any

# Database connection settings
SQLITE_DB_PATH = "data/transactions.db"
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "expense_analyzer",
    "user": "postgres",
    "password": "postgres123"
}

def connect_sqlite():
    """Connect to SQLite database"""
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"❌ SQLite database not found at {SQLITE_DB_PATH}")
        sys.exit(1)
    
    return sqlite3.connect(SQLITE_DB_PATH)

def connect_postgres():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        print("Make sure PostgreSQL is running: docker-compose up -d")
        sys.exit(1)

def get_sqlite_schema(sqlite_conn):
    """Get the schema from SQLite database"""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    return tables

def migrate_users(sqlite_conn, postgres_conn):
    """Migrate users data"""
    print("📋 Migrating users...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    # Get users from SQLite (if exists)
    try:
        sqlite_cursor.execute("SELECT * FROM users")
        users = sqlite_cursor.fetchall()
        
        if users:
            for user in users:
                # Insert into PostgreSQL
                # SQLite structure: id, username, email, password_hash, full_name, created_at, last_login, is_active
                postgres_cursor.execute("""
                    INSERT INTO users (username, email, password_hash, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (user[1], user[2], user[3], bool(user[7]), user[5]))
        else:
            # Create a default user if no users exist
            postgres_cursor.execute("""
                INSERT INTO users (username, email, password_hash, is_active)
                VALUES ('admin', 'admin@expense-analyzer.com', 'hashed_password', true)
                ON CONFLICT (username) DO NOTHING
            """)
        
        postgres_conn.commit()
        print(f"✅ Migrated {len(users) if users else 1} users")
        
    except sqlite3.OperationalError:
        # No users table in SQLite, create default user
        postgres_cursor.execute("""
            INSERT INTO users (username, email, password_hash, is_active)
            VALUES ('admin', 'admin@expense-analyzer.com', 'hashed_password', true)
            ON CONFLICT (username) DO NOTHING
        """)
        postgres_conn.commit()
        print("✅ Created default admin user")

def migrate_transactions(sqlite_conn, postgres_conn):
    """Migrate transactions data"""
    print("📋 Migrating transactions...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    # Get user ID (assuming admin user)
    postgres_cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    user_id = postgres_cursor.fetchone()[0]
    
    # Get transactions from SQLite
    try:
        sqlite_cursor.execute("SELECT * FROM transactions")
        transactions = sqlite_cursor.fetchall()
        
        if transactions:
            for transaction in transactions:
                # Map SQLite columns to PostgreSQL
                # SQLite structure: id, date, description, amount, category, account, month, created_at, updated_at, user_id, upload_id
                postgres_cursor.execute("""
                    INSERT INTO transactions (user_id, date, description, amount, category, account, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    transaction[1],  # date
                    transaction[2],  # description
                    transaction[3],  # amount
                    transaction[4],  # category
                    transaction[5],  # account
                    f"Migrated from SQLite (upload_id: {transaction[10]})" if len(transaction) > 10 else "Migrated from SQLite"  # notes
                ))
            
            postgres_conn.commit()
            print(f"✅ Migrated {len(transactions)} transactions")
        else:
            print("ℹ️  No transactions found in SQLite database")
            
    except sqlite3.OperationalError as e:
        print(f"ℹ️  No transactions table in SQLite: {e}")

def migrate_categories(sqlite_conn, postgres_conn):
    """Migrate categories data"""
    print("📋 Migrating categories...")
    
    sqlite_cursor = sqlite_conn.cursor()
    postgres_cursor = postgres_conn.cursor()
    
    # Get user ID
    postgres_cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    user_id = postgres_cursor.fetchone()[0]
    
    try:
        sqlite_cursor.execute("SELECT * FROM categories")
        categories = sqlite_cursor.fetchall()
        
        if categories:
            for category in categories:
                postgres_cursor.execute("""
                    INSERT INTO categories (user_id, name, parent_category, color, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, name) DO NOTHING
                """, (
                    user_id,
                    category[1],  # name
                    category[2] if len(category) > 2 else None,  # parent_category
                    category[3] if len(category) > 3 else None,  # color
                    True
                ))
            
            postgres_conn.commit()
            print(f"✅ Migrated {len(categories)} categories")
        else:
            print("ℹ️  No categories found in SQLite database")
            
    except sqlite3.OperationalError as e:
        print(f"ℹ️  No categories table in SQLite: {e}")

def create_default_profile(postgres_conn):
    """Create default user profile"""
    print("📋 Creating default user profile...")
    
    cursor = postgres_conn.cursor()
    
    # Get user ID
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    user_id = cursor.fetchone()[0]
    
    # Create default profile
    default_profile = {
        "name": "Default Profile",
        "settings": {
            "currency": "USD",
            "date_format": "YYYY-MM-DD",
            "number_format": "US"
        },
        "categories": [
            {"name": "Food & Dining", "color": "#FF6B6B"},
            {"name": "Transportation", "color": "#4ECDC4"},
            {"name": "Shopping", "color": "#45B7D1"},
            {"name": "Entertainment", "color": "#96CEB4"},
            {"name": "Bills & Utilities", "color": "#FFEAA7"}
        ]
    }
    
    cursor.execute("""
        INSERT INTO user_profiles (user_id, profile_name, profile_data, is_default)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, profile_name) DO NOTHING
    """, (user_id, "Default Profile", json.dumps(default_profile), True))
    
    postgres_conn.commit()
    print("✅ Created default user profile")

def main():
    """Main migration function"""
    print("🚀 Starting SQLite to PostgreSQL migration...")
    print("=" * 50)
    
    # Connect to databases
    print("📡 Connecting to databases...")
    sqlite_conn = connect_sqlite()
    postgres_conn = connect_postgres()
    print("✅ Connected to both databases")
    
    try:
        # Get SQLite schema
        tables = get_sqlite_schema(sqlite_conn)
        print(f"📋 Found {len(tables)} tables in SQLite: {', '.join(tables)}")
        
        # Migrate data
        migrate_users(sqlite_conn, postgres_conn)
        migrate_transactions(sqlite_conn, postgres_conn)
        migrate_categories(sqlite_conn, postgres_conn)
        create_default_profile(postgres_conn)
        
        print("=" * 50)
        print("✅ Migration completed successfully!")
        print("\n📊 Summary:")
        
        # Show migration summary
        cursor = postgres_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM transactions")
        transaction_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM categories")
        category_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        profile_count = cursor.fetchone()[0]
        
        print(f"  👥 Users: {user_count}")
        print(f"  💰 Transactions: {transaction_count}")
        print(f"  📂 Categories: {category_count}")
        print(f"  👤 Profiles: {profile_count}")
        
        print("\n🔗 Database connection info:")
        print(f"  Host: {POSTGRES_CONFIG['host']}")
        print(f"  Port: {POSTGRES_CONFIG['port']}")
        print(f"  Database: {POSTGRES_CONFIG['database']}")
        print(f"  User: {POSTGRES_CONFIG['user']}")
        print(f"  Password: {POSTGRES_CONFIG['password']}")
        
        print("\n🌐 Access pgAdmin at: http://localhost:8080")
        print("  Email: admin@expense-analyzer.com")
        print("  Password: admin123")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    
    finally:
        sqlite_conn.close()
        postgres_conn.close()
        print("\n🔌 Database connections closed")

if __name__ == "__main__":
    main()
