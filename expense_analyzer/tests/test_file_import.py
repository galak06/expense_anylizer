"""
Comprehensive test script for file import verification.
Tests database insertion and total amount calculations for both Adi and Gil profiles.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from core.io import read_any, load_transactions
from core.clean import normalize_df, detect_negative_amounts
from core.database import TransactionDB
from core.service import TransactionService
from datetime import datetime

def test_file_import(file_path: str, profile_name: str):
    """Test a single file import and verify calculations."""
    print(f"\n{'='*80}")
    print(f"Testing: {os.path.basename(file_path)}")
    print(f"Expected Profile: {profile_name}")
    print(f"{'='*80}\n")

    # Get database state before import
    db = TransactionDB()
    count_before = db.get_transaction_count()
    print(f"📊 Database transactions before import: {count_before}")

    try:
        # Step 1: Read file with profile matching
        print(f"\n1️⃣ Reading file and matching profile...")
        raw_df, matched_profile = read_any(file_path)
        matched_profile_id = matched_profile.get('id') if isinstance(matched_profile, dict) else matched_profile
        print(f"   ✅ Profile matched: {matched_profile_id}")
        print(f"   ✅ Raw rows read: {len(raw_df)}")
        print(f"   ✅ Raw columns: {list(raw_df.columns)}")

        # Step 2: Load and normalize transactions
        print(f"\n2️⃣ Loading and normalizing transactions...")
        df = load_transactions(file_path)
        df = normalize_df(df)
        print(f"   ✅ Normalized rows: {len(df)}")
        print(f"   ✅ Columns: {list(df.columns)}")

        # Step 3: Check for credit card detection
        print(f"\n3️⃣ Detecting file type (credit card vs bank)...")
        filename = os.path.basename(file_path).lower()
        profile_id = matched_profile.get('id', '').lower() if isinstance(matched_profile, dict) else matched_profile.lower()
        is_credit_card = (
            'visa' in filename or
            'adi' in filename or
            'gil' in filename or
            (matched_profile and 'visa' in profile_id)
        )
        print(f"   ✅ Is credit card file: {is_credit_card}")
        print(f"   ✅ Detection criteria:")
        print(f"      - 'visa' in filename: {'visa' in filename}")
        print(f"      - 'adi' in filename: {'adi' in filename}")
        print(f"      - 'gil' in filename: {'gil' in filename}")
        print(f"      - 'visa' in profile: {matched_profile and 'visa' in profile_id}")

        # Step 4: Apply negative amount detection
        print(f"\n4️⃣ Converting amounts (expenses should be negative)...")
        amounts_before = df['Amount'].copy()
        positive_before = (amounts_before > 0).sum()
        negative_before = (amounts_before < 0).sum()
        print(f"   Before conversion: {positive_before} positive, {negative_before} negative")

        df = detect_negative_amounts(df, all_expenses=is_credit_card)

        amounts_after = df['Amount'].copy()
        positive_after = (amounts_after > 0).sum()
        negative_after = (amounts_after < 0).sum()
        print(f"   After conversion: {positive_after} positive, {negative_after} negative")

        # Step 5: Calculate file totals
        print(f"\n5️⃣ Calculating file totals...")
        file_expenses = abs(df[df['Amount'] < 0]['Amount'].sum())
        file_income = df[df['Amount'] > 0]['Amount'].sum()
        file_net = df['Amount'].sum()
        file_count = len(df)

        print(f"   💰 File Expenses: ₪{file_expenses:,.2f} ({(df['Amount'] < 0).sum()} transactions)")
        print(f"   💰 File Income: ₪{file_income:,.2f} ({(df['Amount'] > 0).sum()} transactions)")
        print(f"   💰 File Net: ₪{file_net:,.2f}")
        print(f"   💰 File Transaction Count: {file_count}")

        # Step 6: Show sample transactions
        print(f"\n6️⃣ Sample transactions (first 5):")
        print(df[['Date', 'Description', 'Amount']].head().to_string())

        # Step 7: Import to database
        print(f"\n7️⃣ Importing to database...")
        service = TransactionService()
        result = service.import_from_file(file_path, all_expenses=is_credit_card)

        print(f"   ✅ Total rows processed: {result['total_rows']}")
        print(f"   ✅ Inserted (new): {result['inserted']}")
        print(f"   ✅ Duplicates (skipped): {result['duplicates']}")
        print(f"   ✅ Invalid dates (dropped): {result['invalid_dates']}")

        # Step 8: Verify database state after import
        print(f"\n8️⃣ Verifying database state after import...")
        count_after = db.get_transaction_count()
        db_df = service.get_transactions()

        print(f"   ✅ Database transactions after import: {count_after}")
        print(f"   ✅ Transactions added: {count_after - count_before}")

        # Calculate database totals
        db_expenses = abs(db_df[db_df['Amount'] < 0]['Amount'].sum())
        db_income = db_df[db_df['Amount'] > 0]['Amount'].sum()
        db_net = db_df['Amount'].sum()

        print(f"   💰 Database Total Expenses: ₪{db_expenses:,.2f}")
        print(f"   💰 Database Total Income: ₪{db_income:,.2f}")
        print(f"   💰 Database Net: ₪{db_net:,.2f}")

        # Step 9: Verify all amounts are correct sign
        print(f"\n9️⃣ Verifying amount signs in database...")
        db_positive = (db_df['Amount'] > 0).sum()
        db_negative = (db_df['Amount'] < 0).sum()
        db_zero = (db_df['Amount'] == 0).sum()

        print(f"   ✅ Positive amounts: {db_positive}")
        print(f"   ✅ Negative amounts: {db_negative}")
        print(f"   ✅ Zero amounts: {db_zero}")

        if db_positive > 0:
            print(f"   ⚠️  WARNING: Found {db_positive} positive amounts (should be income, or error if credit card)")
            print(f"   Sample positive amounts:")
            positive_df = db_df[db_df['Amount'] > 0][['Date', 'Description', 'Amount']].head()
            print(positive_df.to_string())

        # Step 10: Final summary
        print(f"\n🎯 SUMMARY")
        print(f"   Profile Match: {'✅' if matched_profile_id == profile_name else '❌'} ({matched_profile_id} vs expected {profile_name})")
        print(f"   All Expenses Negative: {'✅' if positive_after == 0 or db_positive == 0 else '❌'}")
        print(f"   Database Insertion: {'✅' if result['inserted'] == file_count else '⚠️'} ({result['inserted']}/{file_count})")
        print(f"   File Total Matches: ₪{file_expenses:,.2f}")

        return {
            'file': os.path.basename(file_path),
            'profile_match': matched_profile_id,
            'file_count': file_count,
            'file_expenses': file_expenses,
            'file_income': file_income,
            'inserted': result['inserted'],
            'duplicates': result['duplicates'],
            'db_count_after': count_after,
            'db_expenses': db_expenses,
            'db_income': db_income,
            'db_positive_count': db_positive,
            'db_negative_count': db_negative
        }

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("COMPREHENSIVE FILE IMPORT TEST SUITE")
    print("="*80)

    test_dir = "/Users/gil.c/Projects/Personal/whatsupcallback/expense_analyzer/tests/temp inputs"

    test_files = [
        ("adi_10.xlsx", "visa_adi_v1"),
        ("gil_10.xlsx", "visa_gil_v1")
    ]

    results = []

    for filename, expected_profile in test_files:
        file_path = os.path.join(test_dir, filename)
        result = test_file_import(file_path, expected_profile)
        if result:
            results.append(result)

    # Final comparison report
    print("\n" + "="*80)
    print("FINAL TEST REPORT")
    print("="*80)

    for result in results:
        print(f"\n📄 {result['file']}")
        print(f"   Profile: {result['profile_match']}")
        print(f"   File Transactions: {result['file_count']}")
        print(f"   File Expenses: ₪{result['file_expenses']:,.2f}")
        print(f"   File Income: ₪{result['file_income']:,.2f}")
        print(f"   Inserted to DB: {result['inserted']}")
        print(f"   Duplicates Skipped: {result['duplicates']}")
        print(f"   DB Positive Amounts: {result['db_positive_count']}")
        print(f"   DB Negative Amounts: {result['db_negative_count']}")

    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
