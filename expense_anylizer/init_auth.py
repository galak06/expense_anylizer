#!/usr/bin/env python3
"""
Initialization script to create the first user account.
Run this script once to create an admin/default user.
"""
from core.auth import AuthManager
from core.database import TransactionDB


def init_auth():
    """Initialize authentication system and create first user."""
    print("=" * 60)
    print("Expense Analyzer - User Initialization")
    print("=" * 60)
    print()

    # Initialize auth manager
    auth_manager = AuthManager()

    # Initialize database (creates users table)
    db = TransactionDB()

    print("✅ Database and authentication tables initialized")
    print()

    # Check if any users exist
    users = auth_manager.get_all_users()
    if users:
        print(f"ℹ️  Found {len(users)} existing user(s)")
        for user in users:
            print(f"   - {user['username']} ({user['email']})")
        print()

        response = input("Do you want to create another user? (y/n): ").lower()
        if response != 'y':
            print("Exiting...")
            return

    # Create new user
    print("Creating new user account:")
    print("-" * 40)

    username = input("Username (min 3 chars): ").strip()
    email = input("Email: ").strip()
    full_name = input("Full Name (optional): ").strip()
    password = input("Password (min 6 chars): ").strip()
    password_confirm = input("Confirm Password: ").strip()

    if password != password_confirm:
        print("❌ Passwords do not match!")
        return

    # Create user
    success, message, user_id = auth_manager.create_user(
        username=username,
        email=email,
        password=password,
        full_name=full_name if full_name else None
    )

    if success:
        print()
        print("=" * 60)
        print(f"✅ {message}")
        print(f"   User ID: {user_id}")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print("=" * 60)
        print()
        print("You can now login to the Expense Analyzer with these credentials")
        print()
        print("Run: streamlit run app/streamlit_app.py")
    else:
        print()
        print(f"❌ {message}")


if __name__ == "__main__":
    init_auth()
