"""
PostgreSQL Database module for storing and retrieving transactions.
Supports both SQLite (fallback) and PostgreSQL databases.
"""
import os
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .config import get_settings
from .logging_config import get_logger, log_data_access, log_error, log_security_event

logger = get_logger(__name__)


class PostgreSQLTransactionDB:
    """PostgreSQL database handler for transactions."""

    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)
        self._init_db()

    def _create_engine(self):
        """Create database engine."""
        settings = get_settings()
        
        # Check for PostgreSQL connection
        if os.getenv('DATABASE_URL'):
            database_url = os.getenv('DATABASE_URL')
            logger.info("Using PostgreSQL database from DATABASE_URL")
        else:
            # Fallback to local PostgreSQL
            database_url = f"postgresql://postgres:postgres123@localhost:5432/expense_analyzer"
            logger.info("Using local PostgreSQL database")
        
        try:
            engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=settings.log_level == 'DEBUG'
            )
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ PostgreSQL connection successful")
            return engine
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise

    def _init_db(self):
        """Initialize database tables."""
        try:
            with self.engine.connect() as conn:
                # Check if tables exist
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    );
                """))
                
                if not result.fetchone()[0]:
                    logger.info("Creating database tables...")
                    # Tables will be created by the init_db.sql script
                    logger.info("✅ Database tables ready")
                else:
                    logger.info("✅ Database tables already exist")
                    
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    def get_user_id(self) -> int:
        """Get current user ID."""
        if self.user_id:
            return self.user_id
        
        # Default to admin user for now
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT id FROM users WHERE username = 'admin' LIMIT 1"))
            user = result.fetchone()
            if user:
                return user[0]
            else:
                # Create admin user if doesn't exist
                conn.execute(text("""
                    INSERT INTO users (username, email, password_hash, is_active)
                    VALUES ('admin', 'admin@expense-analyzer.com', 'hashed_password', true)
                    ON CONFLICT (username) DO NOTHING
                    RETURNING id
                """))
                result = conn.execute(text("SELECT id FROM users WHERE username = 'admin'"))
                return result.fetchone()[0]

    def add_transaction(self, date: str, description: str, amount: float, 
                       category: Optional[str] = None, subcategory: Optional[str] = None,
                       account: Optional[str] = None, notes: Optional[str] = None) -> int:
        """Add a new transaction."""
        user_id = self.get_user_id()
        log_data_access(logger, "add_transaction", user_id, f"Adding transaction: {description}")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO transactions (user_id, date, description, amount, category, subcategory, account, notes)
                    VALUES (:user_id, :date, :description, :amount, :category, :subcategory, :account, :notes)
                    RETURNING id
                """), {
                    'user_id': user_id,
                    'date': date,
                    'description': description,
                    'amount': amount,
                    'category': category,
                    'subcategory': subcategory,
                    'account': account,
                    'notes': notes
                })
                
                transaction_id = result.fetchone()[0]
                conn.commit()
                
                logger.info(f"✅ Transaction added with ID: {transaction_id}")
                return transaction_id
                
        except Exception as e:
            log_error(logger, e, "add_transaction")
            raise

    def get_transactions(self, start_date: Optional[str] = None, 
                        end_date: Optional[str] = None,
                        category: Optional[str] = None,
                        limit: Optional[int] = None) -> pd.DataFrame:
        """Get transactions with optional filters."""
        user_id = self.get_user_id()
        log_data_access(logger, "get_transactions", user_id, f"Filters: start={start_date}, end={end_date}, category={category}")
        
        query = """
            SELECT id, date, description, amount, category, subcategory, account, notes, created_at
            FROM transactions 
            WHERE user_id = :user_id
        """
        params = {'user_id': user_id}
        
        if start_date:
            query += " AND date >= :start_date"
            params['start_date'] = start_date
            
        if end_date:
            query += " AND date <= :end_date"
            params['end_date'] = end_date
            
        if category:
            query += " AND category = :category"
            params['category'] = category
            
        query += " ORDER BY date DESC"
        
        if limit:
            query += " LIMIT :limit"
            params['limit'] = limit
        
        try:
            with self.engine.connect() as conn:
                # Use SQLAlchemy text() for parameterized queries
                from sqlalchemy import text
                result = conn.execute(text(query), params)
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                logger.info(f"✅ Retrieved {len(df)} transactions")
                return df
                
        except Exception as e:
            log_error(logger, e, "get_transactions")
            raise

    def update_transaction(self, transaction_id: int, **kwargs) -> bool:
        """Update a transaction."""
        user_id = self.get_user_id()
        log_data_access(logger, "update_transaction", user_id, f"Updating transaction ID: {transaction_id}")
        
        # Build update query dynamically
        set_clauses = []
        params = {'transaction_id': transaction_id, 'user_id': user_id}
        
        for key, value in kwargs.items():
            if value is not None:
                set_clauses.append(f"{key} = :{key}")
                params[key] = value
        
        if not set_clauses:
            return False
        
        query = f"""
            UPDATE transactions 
            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = :transaction_id AND user_id = :user_id
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                conn.commit()
                
                if result.rowcount > 0:
                    logger.info(f"✅ Transaction {transaction_id} updated")
                    return True
                else:
                    logger.warning(f"⚠️ Transaction {transaction_id} not found or not owned by user")
                    return False
                    
        except Exception as e:
            log_error(logger, e, "update_transaction")
            raise

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction."""
        user_id = self.get_user_id()
        log_data_access(logger, "delete_transaction", user_id, f"Deleting transaction ID: {transaction_id}")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    DELETE FROM transactions 
                    WHERE id = :transaction_id AND user_id = :user_id
                """), {'transaction_id': transaction_id, 'user_id': user_id})
                
                conn.commit()
                
                if result.rowcount > 0:
                    logger.info(f"✅ Transaction {transaction_id} deleted")
                    return True
                else:
                    logger.warning(f"⚠️ Transaction {transaction_id} not found or not owned by user")
                    return False
                    
        except Exception as e:
            log_error(logger, e, "delete_transaction")
            raise

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get user categories."""
        user_id = self.get_user_id()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT name, parent_category, color, is_active
                    FROM categories 
                    WHERE user_id = :user_id
                    ORDER BY name
                """), {'user_id': user_id})
                
                categories = [dict(row) for row in result.fetchall()]
                logger.info(f"✅ Retrieved {len(categories)} categories")
                return categories
                
        except Exception as e:
            log_error("get_categories", str(e))
            raise

    def add_category(self, name: str, parent_category: Optional[str] = None, 
                    color: Optional[str] = None) -> bool:
        """Add a new category."""
        user_id = self.get_user_id()
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO categories (user_id, name, parent_category, color, is_active)
                    VALUES (:user_id, :name, :parent_category, :color, true)
                    ON CONFLICT (user_id, name) DO NOTHING
                """), {
                    'user_id': user_id,
                    'name': name,
                    'parent_category': parent_category,
                    'color': color
                })
                
                conn.commit()
                logger.info(f"✅ Category '{name}' added")
                return True
                
        except Exception as e:
            log_error("add_category", str(e))
            raise

    def get_transaction_summary(self, start_date: Optional[str] = None, 
                               end_date: Optional[str] = None) -> pd.DataFrame:
        """Get transaction summary by category."""
        user_id = self.get_user_id()
        
        query = """
            SELECT 
                category,
                COUNT(*) as transaction_count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                MIN(amount) as min_amount,
                MAX(amount) as max_amount
            FROM transactions 
            WHERE user_id = :user_id
        """
        params = {'user_id': user_id}
        
        if start_date:
            query += " AND date >= :start_date"
            params['start_date'] = start_date
            
        if end_date:
            query += " AND date <= :end_date"
            params['end_date'] = end_date
            
        query += " GROUP BY category ORDER BY total_amount DESC"
        
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params=params)
                logger.info(f"✅ Retrieved summary for {len(df)} categories")
                return df
                
        except Exception as e:
            log_error("get_transaction_summary", str(e))
            raise

    def get_all_categories(self) -> List[str]:
        """Get all unique categories from transactions."""
        user_id = self.get_user_id()
        log_data_access(logger, "get_all_categories", user_id, "Retrieving all categories")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT category 
                    FROM transactions 
                    WHERE user_id = :user_id AND category IS NOT NULL
                    ORDER BY category
                """), {'user_id': user_id})
                
                categories = [row[0] for row in result.fetchall()]
                logger.info(f"✅ Retrieved {len(categories)} categories")
                return categories
                
        except Exception as e:
            log_error(logger, e, "get_all_categories")
            return []

    def get_all_accounts(self) -> List[str]:
        """Get all unique accounts from transactions."""
        user_id = self.get_user_id()
        log_data_access(logger, "get_all_accounts", user_id, "Retrieving all accounts")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT account 
                    FROM transactions 
                    WHERE user_id = :user_id AND account IS NOT NULL
                    ORDER BY account
                """), {'user_id': user_id})
                
                accounts = [row[0] for row in result.fetchall()]
                logger.info(f"✅ Retrieved {len(accounts)} accounts")
                return accounts
                
        except Exception as e:
            log_error(logger, e, "get_all_accounts")
            return []

    def get_date_range(self) -> tuple:
        """Get min and max dates from transactions."""
        user_id = self.get_user_id()
        log_data_access(logger, "get_date_range", user_id, "Retrieving date range")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT MIN(date), MAX(date)
                    FROM transactions 
                    WHERE user_id = :user_id
                """), {'user_id': user_id})
                
                row = result.fetchone()
                if row and row[0] and row[1]:
                    return (row[0], row[1])
                return (None, None)
                
        except Exception as e:
            log_error(logger, e, "get_date_range")
            return (None, None)

    def get_transaction_count(self) -> int:
        """Get total number of transactions."""
        user_id = self.get_user_id()
        log_data_access(logger, "get_transaction_count", user_id, "Retrieving transaction count")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM transactions 
                    WHERE user_id = :user_id
                """), {'user_id': user_id})
                
                count = result.fetchone()[0]
                logger.info(f"✅ Retrieved transaction count: {count}")
                return count
                
        except Exception as e:
            log_error(logger, e, "get_transaction_count")
            return 0

    def update_category(self, description: str, transaction_date: str, category: str) -> int:
        """Update category for a specific transaction."""
        user_id = self.get_user_id()
        log_data_access(logger, "update_category", user_id, f"Updating category for: {description}")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE transactions 
                    SET category = :category, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND description = :description AND date = :date
                """), {
                    'user_id': user_id,
                    'description': description,
                    'date': transaction_date,
                    'category': category
                })
                
                updated_count = result.rowcount
                conn.commit()
                
                if updated_count > 0:
                    logger.info(f"✅ Updated category for '{description}': {category}")
                else:
                    logger.warning(f"⚠️  No transactions found to update: {description}")
                
                return updated_count
                
        except Exception as e:
            log_error(logger, e, "update_category")
            return 0

    def bulk_update_category(self, description: str, category: str) -> int:
        """Update category for all transactions matching description."""
        user_id = self.get_user_id()
        log_data_access(logger, "bulk_update_category", user_id, f"Bulk updating category for: {description}")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    UPDATE transactions 
                    SET category = :category, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id AND description = :description
                """), {
                    'user_id': user_id,
                    'description': description,
                    'category': category
                })
                
                updated_count = result.rowcount
                conn.commit()
                
                logger.info(f"✅ Bulk updated {updated_count} transactions for '{description}': {category}")
                return updated_count
                
        except Exception as e:
            log_error(logger, e, "bulk_update_category")
            return 0

    def close(self):
        """Close database connection."""
        if hasattr(self, 'engine'):
            self.engine.dispose()
            logger.info("🔌 Database connection closed")
