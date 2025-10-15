#!/usr/bin/env python3
"""
Utility script to delete transactions from the database.
"""
import sys
import os

sys.path.append(os.path.dirname(__file__))

from core.database import TransactionDB
from core.auth import AuthManager

def main():
    print("=" * 60)
    print("Transaction Deletion Utility")
    print("=" * 60)

    # Get user credentials
    username = input("\nEnter your username: ").strip()

    if not username:
        print("❌ Username is required")
        return

    # Get auth manager and find user
    auth_manager = AuthManager()

    # Get user by username
    import sqlite3
    from core.config import get_settings

    settings = get_settings()

    with sqlite3.connect(settings.database_path) as conn:
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()

        if not result:
            print(f"❌ User '{username}' not found")
            return

        user_id = result[0]

    print(f"✅ Found user: {username} (ID: {user_id})")

    # Initialize database
    db = TransactionDB(user_id=user_id)

    # Show current stats
    stats = db.get_statistics()
    print(f"\n📊 Current Statistics:")
    print(f"   Total transactions: {stats['total_transactions']}")
    print(f"   Date range: {stats['min_date']} to {stats['max_date']}")

    # Show available accounts
    accounts = db.get_all_accounts()

    if accounts:
        print(f"\n🏦 Available accounts:")
        for i, account in enumerate(accounts, 1):
            print(f"   {i}. {account if account else '(No account name)'}")

    # Show upload sessions
    sessions = db.get_upload_sessions()

    if sessions:
        print(f"\n📁 Upload sessions:")
        for i, session in enumerate(sessions, 1):
            print(f"   {i}. {session['filename']} - {session['upload_date']} ({session['transactions_count']} transactions)")

    print("\n" + "=" * 60)
    print("Deletion Options:")
    print("=" * 60)
    print("1. Delete by account name")
    print("2. Delete by upload session")
    print("3. Delete ALL transactions (⚠️  Use with caution!)")
    print("4. Exit")

    choice = input("\nSelect option (1-4): ").strip()

    if choice == "1":
        # Delete by account
        if not accounts:
            print("❌ No accounts found")
            return

        print("\nEnter account name to delete (or number from list above):")
        account_input = input("Account: ").strip()

        # Check if it's a number
        try:
            account_num = int(account_input)
            if 1 <= account_num <= len(accounts):
                account_to_delete = accounts[account_num - 1]
            else:
                print("❌ Invalid account number")
                return
        except ValueError:
            account_to_delete = account_input

        # Confirm
        confirm = input(f"\n⚠️  Delete all transactions for account '{account_to_delete}'? (yes/no): ").strip().lower()

        if confirm == "yes":
            deleted = db.delete_transactions_by_account(account_to_delete)
            print(f"✅ Deleted {deleted} transactions from account '{account_to_delete}'")
        else:
            print("❌ Deletion cancelled")

    elif choice == "2":
        # Delete by upload session
        if not sessions:
            print("❌ No upload sessions found")
            return

        print("\nEnter upload session number to delete:")
        try:
            session_num = int(input("Session: ").strip())
            if 1 <= session_num <= len(sessions):
                session = sessions[session_num - 1]

                # Confirm
                confirm = input(f"\n⚠️  Delete upload session '{session['filename']}' ({session['transactions_count']} transactions)? (yes/no): ").strip().lower()

                if confirm == "yes":
                    deleted = db.delete_upload_session(session['id'])
                    print(f"✅ Deleted {deleted} transactions from upload session")
                else:
                    print("❌ Deletion cancelled")
            else:
                print("❌ Invalid session number")
        except ValueError:
            print("❌ Invalid input")

    elif choice == "3":
        # Delete all
        confirm = input(f"\n⚠️  ⚠️  ⚠️  Delete ALL {stats['total_transactions']} transactions? This cannot be undone! (yes/no): ").strip().lower()

        if confirm == "yes":
            second_confirm = input("Are you absolutely sure? Type 'DELETE ALL' to confirm: ").strip()

            if second_confirm == "DELETE ALL":
                deleted = db.clear_all_transactions()
                print(f"✅ Deleted {deleted} transactions")
            else:
                print("❌ Deletion cancelled")
        else:
            print("❌ Deletion cancelled")

    elif choice == "4":
        print("👋 Exiting...")
        return

    else:
        print("❌ Invalid option")
        return

    # Show updated stats
    new_stats = db.get_statistics()
    print(f"\n📊 Updated Statistics:")
    print(f"   Total transactions: {new_stats['total_transactions']}")
    if new_stats['min_date']:
        print(f"   Date range: {new_stats['min_date']} to {new_stats['max_date']}")
    else:
        print(f"   No transactions remaining")

if __name__ == "__main__":
    main()
