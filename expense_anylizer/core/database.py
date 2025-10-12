"""
Database module for storing and retrieving transactions.
Uses SQLite for local storage.
"""
import sqlite3
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path
from .config import get_settings


class TransactionDB:
    """Database handler for transactions."""

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        if db_path is None:
            db_path = settings.database_path

        self.db_path = db_path
        self._ensure_db_directory()
        self._init_db()

    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        """Initialize database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT,
                    account TEXT,
                    month TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for better query performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_date
                ON transactions(date)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_category
                ON transactions(category)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_month
                ON transactions(month)
            """)

            # Migration: Add account column if it doesn't exist
            cursor = conn.execute("PRAGMA table_info(transactions)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'account' not in columns:
                conn.execute("ALTER TABLE transactions ADD COLUMN account TEXT")

            # Create index on account column (after ensuring it exists)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_account
                ON transactions(account)
            """)

            conn.commit()

    def save_transactions(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Save transactions to database with date normalization and duplicate detection.
        Returns dict with statistics: total, inserted, duplicates, invalid_dates, skipped_rows.
        """
        if df.empty:
            return {'total': 0, 'inserted': 0, 'duplicates': 0, 'invalid_dates': 0, 'skipped_rows': []}

        # Prepare DataFrame for insertion
        columns_to_save = ['Date', 'Description', 'Amount', 'Category', 'Month']
        if 'Account' in df.columns:
            columns_to_save.append('Account')

        df_save = df[columns_to_save].copy()

        # Rename columns to match database schema
        column_mapping = {
            'Date': 'date',
            'Description': 'description',
            'Amount': 'amount',
            'Category': 'category',
            'Month': 'month',
            'Account': 'account'
        }
        df_save.columns = [column_mapping.get(col, col.lower()) for col in df_save.columns]

        total_rows = len(df_save)

        # Normalize dates before saving
        df_save['date'] = pd.to_datetime(df_save['date'], errors='coerce')

        # Drop rows with invalid dates
        invalid_dates = df_save['date'].isna().sum()
        if invalid_dates > 0:
            print(f"Warning: Dropping {invalid_dates} rows with invalid dates")
            df_save = df_save.dropna(subset=['date'])

        # Convert to YYYY-MM-DD format
        df_save['date'] = df_save['date'].dt.strftime('%Y-%m-%d')

        # Normalize month field
        if 'month' in df_save.columns:
            # Ensure month is in YYYY-MM format
            df_save['month'] = pd.to_datetime(df_save['date']).dt.strftime('%Y-%m')

        with sqlite3.connect(self.db_path) as conn:
            # Check for existing transactions (duplicates)
            # A transaction is considered duplicate if it has the same date, description, and amount
            duplicates = 0
            rows_to_insert = []
            skipped_rows = []

            for _, row in df_save.iterrows():
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM transactions
                    WHERE date = ? AND description = ? AND ABS(amount - ?) < 0.01
                """, (row['date'], row['description'], row['amount']))

                count = cursor.fetchone()[0]
                if count == 0:
                    rows_to_insert.append(row)
                else:
                    duplicates += 1
                    # Store skipped duplicate for review
                    skipped_rows.append(row.to_dict())

            # Insert only non-duplicate transactions
            if rows_to_insert:
                df_to_insert = pd.DataFrame(rows_to_insert)
                df_to_insert.to_sql('transactions', conn, if_exists='append', index=False)

            inserted = len(rows_to_insert)

            return {
                'total': total_rows,
                'inserted': inserted,
                'duplicates': duplicates,
                'invalid_dates': invalid_dates,
                'skipped_rows': skipped_rows
            }

    def load_transactions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        account: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Load transactions from database with optional filters.

        Args:
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)
            category: Filter by category
            account: Filter by account
            limit: Limit number of results

        Returns:
            DataFrame with transactions
        """
        query = "SELECT date, description, amount, category, account, month FROM transactions WHERE 1=1"
        params = []

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        if category:
            query += " AND category = ?"
            params.append(category)

        if account:
            query += " AND account = ?"
            params.append(account)

        query += " ORDER BY date DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if not df.empty:
            df['Date'] = pd.to_datetime(df['date'])
            df['Description'] = df['description']
            df['Amount'] = df['amount']
            df['Category'] = df['category']
            df['Account'] = df['account']
            df['Month'] = df['month']
            df = df[['Date', 'Description', 'Amount', 'Category', 'Account', 'Month']]

        return df

    def get_all_categories(self) -> List[str]:
        """Get list of all unique categories from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT category
                FROM transactions
                WHERE category IS NOT NULL
                ORDER BY category
            """)
            return [row[0] for row in cursor.fetchall()]

    def get_all_accounts(self) -> List[str]:
        """Get list of all unique accounts from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT account
                FROM transactions
                WHERE account IS NOT NULL
                ORDER BY account
            """)
            return [row[0] for row in cursor.fetchall()]

    def get_date_range(self) -> tuple:
        """Get min and max dates from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT MIN(date), MAX(date)
                FROM transactions
            """)
            result = cursor.fetchone()
            return result if result else (None, None)

    def get_transaction_count(self) -> int:
        """Get total number of transactions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM transactions")
            return cursor.fetchone()[0]

    def update_category(self, description: str, date: str, category: str) -> int:
        """
        Update category for a specific transaction.

        Args:
            description: Transaction description
            date: Transaction date (YYYY-MM-DD)
            category: New category

        Returns:
            Number of rows updated
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE transactions
                SET category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE description = ? AND date = ?
            """, (category, description, date))
            conn.commit()
            return cursor.rowcount

    def clear_all_transactions(self):
        """Clear all transactions from database. Use with caution!"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM transactions")
            conn.commit()

    def get_statistics(self) -> dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Total transactions
            cursor = conn.execute("SELECT COUNT(*) FROM transactions")
            stats['total_transactions'] = cursor.fetchone()[0]

            # Categorized count
            cursor = conn.execute("""
                SELECT COUNT(*) FROM transactions
                WHERE category IS NOT NULL
            """)
            stats['categorized_count'] = cursor.fetchone()[0]

            # Date range
            cursor = conn.execute("""
                SELECT MIN(date), MAX(date) FROM transactions
            """)
            min_date, max_date = cursor.fetchone()
            stats['min_date'] = min_date
            stats['max_date'] = max_date

            # Total amount
            cursor = conn.execute("SELECT SUM(amount) FROM transactions")
            stats['total_amount'] = cursor.fetchone()[0] or 0

            # Category counts
            cursor = conn.execute("""
                SELECT category, COUNT(*)
                FROM transactions
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            stats['top_categories'] = [
                {'category': row[0], 'count': row[1]}
                for row in cursor.fetchall()
            ]

            return stats

    def export_to_csv(self, output_path: str):
        """Export all transactions to CSV file."""
        df = self.load_transactions()
        df.to_csv(output_path, index=False)
        return len(df)
