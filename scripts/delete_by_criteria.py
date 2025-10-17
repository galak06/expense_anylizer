#!/usr/bin/env python3
"""
Utility script to delete transactions by date range or description pattern.
"""
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(__file__))

from core.database import TransactionDB
from core.config import get_settings
import sqlite3

def main():
    print("=" * 60)
    print("Delete Transactions by Criteria")
    print("=" * 60)

    # Get user credentials
    username = input("\nEnter your username: ").strip()

    if not username:
        print("❌ Username is required")
        return

    # Get auth manager and find user
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

    # Load all transactions
    df = db.load_transactions()

    if df.empty:
        print("\n❌ No transactions found")
        return

    print(f"\n📊 Total transactions: {len(df)}")
    print(f"📅 Date range: {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")

    # Show sample transactions
    print(f"\n📋 Sample transactions (first 10):")
    for idx, row in df.head(10).iterrows():
        print(f"   {row['Date'].strftime('%Y-%m-%d')} | ₪{row['Amount']:,.2f} | {row['Description'][:50]}")

    print("\n" + "=" * 60)
    print("Deletion Options:")
    print("=" * 60)
    print("1. Delete by date range")
    print("2. Delete by description pattern (contains text)")
    print("3. Delete by date AND description")
    print("4. Show transactions by date range first")
    print("5. Exit")

    choice = input("\nSelect option (1-5): ").strip()

    if choice == "1":
        # Delete by date range
        start_date = input("Enter start date (YYYY-MM-DD): ").strip()
        end_date = input("Enter end date (YYYY-MM-DD): ").strip()

        # Filter by date
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        to_delete = df[mask]

        if to_delete.empty:
            print(f"❌ No transactions found between {start_date} and {end_date}")
            return

        print(f"\n📊 Found {len(to_delete)} transactions to delete:")
        print(f"   Total amount: ₪{to_delete['Amount'].sum():,.2f}")
        print("\nSample:")
        for idx, row in to_delete.head(5).iterrows():
            print(f"   {row['Date'].strftime('%Y-%m-%d')} | ₪{row['Amount']:,.2f} | {row['Description'][:50]}")

        confirm = input(f"\n⚠️  Delete these {len(to_delete)} transactions? (yes/no): ").strip().lower()

        if confirm == "yes":
            # Delete from database
            with sqlite3.connect(settings.database_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM transactions
                    WHERE user_id = ? AND date >= ? AND date <= ?
                """, (user_id, start_date, end_date))
                conn.commit()
                deleted = cursor.rowcount

            print(f"✅ Deleted {deleted} transactions")
        else:
            print("❌ Deletion cancelled")

    elif choice == "2":
        # Delete by description pattern
        pattern = input("Enter text to search in description: ").strip()

        # Filter by description
        mask = df['Description'].str.contains(pattern, case=False, na=False)
        to_delete = df[mask]

        if to_delete.empty:
            print(f"❌ No transactions found matching '{pattern}'")
            return

        print(f"\n📊 Found {len(to_delete)} transactions to delete:")
        print(f"   Total amount: ₪{to_delete['Amount'].sum():,.2f}")
        print("\nSample:")
        for idx, row in to_delete.head(10).iterrows():
            print(f"   {row['Date'].strftime('%Y-%m-%d')} | ₪{row['Amount']:,.2f} | {row['Description'][:50]}")

        confirm = input(f"\n⚠️  Delete these {len(to_delete)} transactions? (yes/no): ").strip().lower()

        if confirm == "yes":
            # Delete from database
            with sqlite3.connect(settings.database_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM transactions
                    WHERE user_id = ? AND description LIKE ?
                """, (user_id, f"%{pattern}%"))
                conn.commit()
                deleted = cursor.rowcount

            print(f"✅ Deleted {deleted} transactions")
        else:
            print("❌ Deletion cancelled")

    elif choice == "3":
        # Delete by both date and description
        start_date = input("Enter start date (YYYY-MM-DD): ").strip()
        end_date = input("Enter end date (YYYY-MM-DD): ").strip()
        pattern = input("Enter text to search in description: ").strip()

        # Filter by both
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date) & df['Description'].str.contains(pattern, case=False, na=False)
        to_delete = df[mask]

        if to_delete.empty:
            print(f"❌ No transactions found")
            return

        print(f"\n📊 Found {len(to_delete)} transactions to delete:")
        print(f"   Total amount: ₪{to_delete['Amount'].sum():,.2f}")
        print("\nSample:")
        for idx, row in to_delete.head(10).iterrows():
            print(f"   {row['Date'].strftime('%Y-%m-%d')} | ₪{row['Amount']:,.2f} | {row['Description'][:50]}")

        confirm = input(f"\n⚠️  Delete these {len(to_delete)} transactions? (yes/no): ").strip().lower()

        if confirm == "yes":
            # Delete from database
            with sqlite3.connect(settings.database_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM transactions
                    WHERE user_id = ? AND date >= ? AND date <= ? AND description LIKE ?
                """, (user_id, start_date, end_date, f"%{pattern}%"))
                conn.commit()
                deleted = cursor.rowcount

            print(f"✅ Deleted {deleted} transactions")
        else:
            print("❌ Deletion cancelled")

    elif choice == "4":
        # Show transactions by date range
        start_date = input("Enter start date (YYYY-MM-DD): ").strip()
        end_date = input("Enter end date (YYYY-MM-DD): ").strip()

        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        filtered = df[mask]

        if filtered.empty:
            print(f"❌ No transactions found between {start_date} and {end_date}")
            return

        print(f"\n📊 Found {len(filtered)} transactions:")
        print(f"   Total amount: ₪{filtered['Amount'].sum():,.2f}")
        print("\nAll transactions:")
        for idx, row in filtered.iterrows():
            print(f"   {row['Date'].strftime('%Y-%m-%d')} | ₪{row['Amount']:,.2f} | {row['Description']}")

    elif choice == "5":
        print("👋 Exiting...")
        return

    else:
        print("❌ Invalid option")
        return

    # Show updated stats
    new_df = db.load_transactions()
    print(f"\n📊 Updated Statistics:")
    print(f"   Total transactions: {len(new_df)}")
    if not new_df.empty:
        print(f"   Date range: {new_df['Date'].min().strftime('%Y-%m-%d')} to {new_df['Date'].max().strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main()
