#!/usr/bin/env python3
"""
Quick script to create a user without interactive prompts.
"""
from core.auth import AuthManager

# User details
username = "testuser"
email = "testuser@example.com"
password = "password123"
full_name = "Test User"

auth_manager = AuthManager()
success, message, user_id = auth_manager.create_user(
    username=username,
    email=email,
    password=password,
    full_name=full_name
)

if success:
    print(f"✅ User created successfully!")
    print(f"   User ID: {user_id}")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print()
    print(f"Login at http://localhost:8501 with:")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
else:
    print(f"❌ Error: {message}")
