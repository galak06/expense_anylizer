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
from .logging_config import get_logger, log_data_access, log_error, log_security_event

logger = get_logger(__name__)


class TransactionDB:
    """Database handler for transactions."""

    def __init__(self, db_path: Optional[str] = None, user_id: Optional[int] = None):
        settings = get_settings()
        if db_path is None:
            db_path = settings.database_path

        self.db_path = db_path
        self.user_id = user_id  # Current authenticated user
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
                    user_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT,
                    account TEXT,
                    month TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create indexes for better query performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id
                ON transactions(user_id)
            """)

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
            
            # Migration: Add upload_id column if it doesn't exist
            if 'upload_id' not in columns:
                conn.execute("ALTER TABLE transactions ADD COLUMN upload_id TEXT")
            
            # Create upload_sessions table for tracking file imports
            conn.execute("""
                CREATE TABLE IF NOT EXISTS upload_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER,
                    transactions_count INTEGER DEFAULT 0,
                    account TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Create index for upload_sessions
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_upload_sessions_user_id
                ON upload_sessions(user_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_upload_sessions_upload_date
                ON upload_sessions(upload_date)
            """)
            
            # Create index for upload_id in transactions
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_upload_id
                ON transactions(upload_id)
            """)

            # Migration: Add user_id column if it doesn't exist
            if 'user_id' not in columns:
                # For existing databases, add user_id with default value 1
                # This assumes a default user with id=1 exists
                conn.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER DEFAULT 1 NOT NULL")

            # Create index on account column (after ensuring it exists)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_account
                ON transactions(account)
            """)

            conn.commit()

    def save_transactions(self, df: pd.DataFrame, user_id: Optional[int] = None, upload_id: Optional[str] = None) -> Dict[str, any]:
        """
        Save transactions to database with date normalization and duplicate detection.
        Returns dict with statistics: total, inserted, duplicates, invalid_dates, skipped_rows.

        Args:
            df: DataFrame with transactions
            user_id: User ID to associate with transactions (uses self.user_id if not provided)
            upload_id: Upload session ID to associate with transactions
        """
        if df.empty:
            return {'total': 0, 'inserted': 0, 'duplicates': 0, 'invalid_dates': 0, 'skipped_rows': []}

        # Use provided user_id or fall back to instance user_id
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            log_security_event(logger, "MISSING_USER_ID", "Attempted to save transactions without user_id")
            raise ValueError("user_id must be provided or set on the TransactionDB instance")
        
        log_data_access(logger, "CREATE", current_user_id, f"Saving {len(df)} transactions")

        # Prepare DataFrame for insertion
        columns_to_save = ['date', 'description', 'amount', 'category', 'Month']
        if 'account' in df.columns:
            columns_to_save.append('account')

        df_save = df[columns_to_save].copy()

        # Add user_id and upload_id columns
        df_save['user_id'] = current_user_id
        if upload_id:
            df_save['upload_id'] = upload_id

        # Rename columns to match database schema
        column_mapping = {
            'date': 'date',
            'description': 'description',
            'amount': 'amount',
            'category': 'category',
            'Month': 'month',
            'account': 'account',
            'user_id': 'user_id',
            'upload_id': 'upload_id'
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
                    WHERE user_id = ? AND date = ? AND description = ? AND ABS(amount - ?) < 0.01
                """, (current_user_id, row['date'], row['description'], row['amount']))

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
        limit: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Load transactions from database with optional filters.

        Args:
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)
            category: Filter by category
            account: Filter by account
            limit: Limit number of results
            user_id: User ID to filter by (uses self.user_id if not provided)

        Returns:
            DataFrame with transactions
        """
        # Use provided user_id or fall back to instance user_id
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")

        query = "SELECT date, description, amount, category, account, month FROM transactions WHERE user_id = ?"
        params = [current_user_id]

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
            df['date'] = pd.to_datetime(df['date'])
            df['description'] = df['description']
            df['amount'] = df['amount']
            df['category'] = df['category']
            df['account'] = df['account']
            df['Month'] = df['month']
            df = df[['date', 'description', 'amount', 'category', 'account', 'Month']]

        return df

    def get_all_categories(self, user_id: Optional[int] = None) -> List[str]:
        """Get list of all unique categories from database for a user."""
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT category
                FROM transactions
                WHERE user_id = ? AND category IS NOT NULL
                ORDER BY category
            """, (current_user_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_all_accounts(self, user_id: Optional[int] = None) -> List[str]:
        """Get list of all unique accounts from database for a user."""
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT account
                FROM transactions
                WHERE user_id = ? AND account IS NOT NULL
                ORDER BY account
            """, (current_user_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_date_range(self, user_id: Optional[int] = None) -> tuple:
        """Get min and max dates from database for a user."""
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT MIN(date), MAX(date)
                FROM transactions
                WHERE user_id = ?
            """, (current_user_id,))
            result = cursor.fetchone()
            return result if result else (None, None)

    def get_transaction_count(self, user_id: Optional[int] = None) -> int:
        """Get total number of transactions for a user."""
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (current_user_id,))
            return cursor.fetchone()[0]

    def update_category(self, description: str, date: str, category: str, user_id: Optional[int] = None) -> int:
        """
        Update category for a specific transaction.

        Args:
            description: Transaction description
            date: Transaction date (YYYY-MM-DD)
            category: New category
            user_id: User ID to filter by (uses self.user_id if not provided)

        Returns:
            Number of rows updated
        """
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE transactions
                SET category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND description = ? AND date = ?
            """, (category, current_user_id, description, date))
            conn.commit()
            return cursor.rowcount

    def bulk_update_category(self, description: str, category: str, user_id: Optional[int] = None) -> int:
        """
        Update category for all transactions matching description.

        Args:
            description: Transaction description to match
            category: New category
            user_id: User ID to filter by (uses self.user_id if not provided)

        Returns:
            Number of rows updated
        """
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE transactions
                SET category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND description = ?
            """, (category, current_user_id, description))
            conn.commit()
            return cursor.rowcount

    def clear_all_transactions(self, user_id: Optional[int] = None):
        """
        Clear all transactions for a specific user from database. Use with caution!
        
        Args:
            user_id: User ID to clear transactions for (uses self.user_id if not provided)
        """
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            log_security_event(logger, "MISSING_USER_ID", "Attempted to clear transactions without user_id")
            raise ValueError("user_id must be provided or set on the TransactionDB instance")
        
        log_security_event(logger, "DATA_DELETE", f"Clearing all transactions for user {current_user_id}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM transactions WHERE user_id = ?", (current_user_id,))
            conn.commit()
            deleted_count = cursor.rowcount
            log_data_access(logger, "DELETE", current_user_id, f"Deleted {deleted_count} transactions")
            return deleted_count

    def delete_transactions_by_account(self, account: str, user_id: Optional[int] = None) -> int:
        """
        Delete all transactions for a specific account.
        
        Args:
            account: Account name to delete transactions for
            user_id: User ID to filter by (uses self.user_id if not provided)
            
        Returns:
            Number of transactions deleted
        """
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            log_security_event(logger, "MISSING_USER_ID", "Attempted to delete transactions by account without user_id")
            raise ValueError("user_id must be provided or set on the TransactionDB instance")
        
        log_security_event(logger, "DATA_DELETE", f"Deleting transactions for account '{account}' for user {current_user_id}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM transactions WHERE user_id = ? AND account = ?", (current_user_id, account))
            conn.commit()
            deleted_count = cursor.rowcount
            log_data_access(logger, "DELETE", current_user_id, f"Deleted {deleted_count} transactions for account '{account}'")
            return deleted_count

    def get_statistics(self, user_id: Optional[int] = None) -> dict:
        """Get database statistics for a user."""
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")

        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Total transactions
            cursor = conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (current_user_id,))
            stats['total_transactions'] = cursor.fetchone()[0]

            # Categorized count
            cursor = conn.execute("""
                SELECT COUNT(*) FROM transactions
                WHERE user_id = ? AND category IS NOT NULL
            """, (current_user_id,))
            stats['categorized_count'] = cursor.fetchone()[0]

            # Date range
            cursor = conn.execute("""
                SELECT MIN(date), MAX(date) FROM transactions
                WHERE user_id = ?
            """, (current_user_id,))
            min_date, max_date = cursor.fetchone()
            stats['min_date'] = min_date
            stats['max_date'] = max_date

            # Total amount
            cursor = conn.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ?", (current_user_id,))
            stats['total_amount'] = cursor.fetchone()[0] or 0

            # Category counts
            cursor = conn.execute("""
                SELECT category, COUNT(*)
                FROM transactions
                WHERE user_id = ? AND category IS NOT NULL
                GROUP BY category
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, (current_user_id,))
            stats['top_categories'] = [
                {'category': row[0], 'count': row[1]}
                for row in cursor.fetchall()
            ]

            return stats

    def force_insert_transaction(self, df: pd.DataFrame, user_id: Optional[int] = None) -> int:
        """
        Force insert transactions bypassing duplicate check.
        Use with caution - this should only be used for restoring duplicates.
        
        Args:
            df: DataFrame with transactions to insert
            user_id: User ID to associate with transactions (uses self.user_id if not provided)
            
        Returns:
            Number of rows inserted
        """
        if df.empty:
            return 0
            
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")
        
        # Prepare DataFrame for insertion
        columns_to_save = ['date', 'description', 'amount', 'category', 'Month']
        if 'account' in df.columns:
            columns_to_save.append('account')
        
        df_save = df[columns_to_save].copy()
        df_save['user_id'] = current_user_id
        
        # Rename columns to match database schema
        column_mapping = {
            'date': 'date',
            'description': 'description',
            'amount': 'amount',
            'category': 'category',
            'Month': 'month',
            'account': 'account',
            'user_id': 'user_id'
        }
        df_save.columns = [column_mapping.get(col, col.lower()) for col in df_save.columns]
        
        # Normalize dates
        df_save['date'] = pd.to_datetime(df_save['date'], errors='coerce')
        df_save = df_save.dropna(subset=['date'])
        df_save['date'] = df_save['date'].dt.strftime('%Y-%m-%d')
        
        # Normalize month field
        if 'month' in df_save.columns:
            df_save['month'] = pd.to_datetime(df_save['date']).dt.strftime('%Y-%m')
        
        with sqlite3.connect(self.db_path) as conn:
            df_save.to_sql('transactions', conn, if_exists='append', index=False)
            return len(df_save)

    def export_to_csv(self, output_path: str, user_id: Optional[int] = None):
        """Export all transactions to CSV file for a user."""
        df = self.load_transactions(user_id=user_id)
        df.to_csv(output_path, index=False)
        return len(df)

    def create_upload_session(self, filename: str, file_size: int = None, account: str = None, user_id: Optional[int] = None) -> str:
        """
        Create a new upload session and return the upload_id.
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes
            account: Account name if known
            user_id: User ID (uses self.user_id if not provided)
            
        Returns:
            Upload session ID
        """
        import uuid
        from datetime import datetime
        
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")
        
        upload_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO upload_sessions (id, user_id, filename, file_size, account)
                VALUES (?, ?, ?, ?, ?)
            """, (upload_id, current_user_id, filename, file_size, account))
            conn.commit()
        
        log_data_access(logger, "CREATE", current_user_id, f"Created upload session {upload_id} for file {filename}")
        return upload_id

    def update_upload_session(self, upload_id: str, transactions_count: int, user_id: Optional[int] = None):
        """
        Update upload session with final transaction count.
        
        Args:
            upload_id: Upload session ID
            transactions_count: Number of transactions imported
            user_id: User ID (uses self.user_id if not provided)
        """
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE upload_sessions 
                SET transactions_count = ?
                WHERE id = ? AND user_id = ?
            """, (transactions_count, upload_id, current_user_id))
            conn.commit()
        
        log_data_access(logger, "UPDATE", current_user_id, f"Updated upload session {upload_id} with {transactions_count} transactions")

    def get_upload_sessions(self, user_id: Optional[int] = None) -> List[dict]:
        """
        Get all upload sessions for a user.
        
        Args:
            user_id: User ID (uses self.user_id if not provided)
            
        Returns:
            List of upload session dictionaries
        """
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, filename, upload_date, file_size, transactions_count, account
                FROM upload_sessions
                WHERE user_id = ?
                ORDER BY upload_date DESC
            """, (current_user_id,))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'id': row[0],
                    'filename': row[1],
                    'upload_date': row[2],
                    'file_size': row[3],
                    'transactions_count': row[4],
                    'account': row[5]
                })
            
            return sessions

    def delete_upload_session(self, upload_id: str, user_id: Optional[int] = None) -> int:
        """
        Delete all transactions from a specific upload session.
        
        Args:
            upload_id: Upload session ID to delete
            user_id: User ID (uses self.user_id if not provided)
            
        Returns:
            Number of transactions deleted
        """
        current_user_id = user_id if user_id is not None else self.user_id
        if current_user_id is None:
            raise ValueError("user_id must be provided or set on the TransactionDB instance")
        
        log_security_event(logger, "DATA_DELETE", f"Deleting upload session {upload_id} for user {current_user_id}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Delete transactions
            cursor = conn.execute("""
                DELETE FROM transactions 
                WHERE upload_id = ? AND user_id = ?
            """, (upload_id, current_user_id))
            deleted_count = cursor.rowcount
            
            # Delete upload session record
            conn.execute("""
                DELETE FROM upload_sessions 
                WHERE id = ? AND user_id = ?
            """, (upload_id, current_user_id))
            
            conn.commit()
        
        log_data_access(logger, "DELETE", current_user_id, f"Deleted upload session {upload_id} with {deleted_count} transactions")
        return deleted_count
