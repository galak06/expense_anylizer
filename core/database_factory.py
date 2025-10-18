"""
Database factory for creating the appropriate database handler.
Supports both SQLite and PostgreSQL databases.
"""
import os
from typing import Union, Optional
from .database import TransactionDB
from .database_postgres import PostgreSQLTransactionDB
from .config import get_settings
from .logging_config import get_logger

logger = get_logger(__name__)


def create_database(user_id: Optional[int] = None) -> Union[TransactionDB, PostgreSQLTransactionDB]:
    """
    Create the appropriate database handler based on configuration.
    
    Args:
        user_id: Current user ID for multi-user support
        
    Returns:
        Database handler instance (SQLite or PostgreSQL)
    """
    settings = get_settings()
    
    # Check database type from configuration
    if settings.database_type == "postgresql":
        logger.info("🐘 Using PostgreSQL database (configured)")
        return PostgreSQLTransactionDB(user_id=user_id)
    
    # Check for PostgreSQL connection URL
    if settings.database_url and settings.database_url.startswith("postgresql://"):
        logger.info("🐘 Using PostgreSQL database (from DATABASE_URL)")
        return PostgreSQLTransactionDB(user_id=user_id)
    
    # Check for environment variable
    if os.getenv('DATABASE_URL'):
        logger.info("🐘 Using PostgreSQL database (from environment)")
        return PostgreSQLTransactionDB(user_id=user_id)
    
    # Check for local PostgreSQL (fallback)
    try:
        import psycopg2
        # Try to connect to local PostgreSQL
        psycopg2.connect(
            host="localhost",
            port=5432,
            database="expense_analyzer",
            user="postgres",
            password="postgres123"
        )
        logger.info("🐘 Using local PostgreSQL database (auto-detected)")
        return PostgreSQLTransactionDB(user_id=user_id)
    except:
        pass
    
    # Fallback to SQLite
    logger.info("🗃️ Using SQLite database (fallback)")
    return TransactionDB(user_id=user_id)


def get_database_info() -> dict:
    """
    Get information about the current database configuration.
    
    Returns:
        Dictionary with database information
    """
    info = {
        "type": "unknown",
        "host": None,
        "port": None,
        "database": None,
        "user": None,
        "path": None
    }
    
    if os.getenv('DATABASE_URL'):
        # PostgreSQL from environment
        info["type"] = "postgresql"
        info["host"] = "external"
        info["database"] = "external"
        info["user"] = "external"
    else:
        try:
            import psycopg2
            psycopg2.connect(
                host="localhost",
                port=5432,
                database="expense_analyzer",
                user="postgres",
                password="postgres123"
            )
            info["type"] = "postgresql"
            info["host"] = "localhost"
            info["port"] = 5432
            info["database"] = "expense_analyzer"
            info["user"] = "postgres"
        except:
            # SQLite fallback
            settings = get_settings()
            info["type"] = "sqlite"
            info["path"] = settings.database_path
    
    return info


def test_database_connection() -> bool:
    """
    Test the database connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        db = create_database()
        # Try a simple operation
        if hasattr(db, 'get_user_id'):
            db.get_user_id()
        else:
            # For SQLite, try to get transactions
            db.get_transactions(limit=1)
        logger.info("✅ Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False


def migrate_from_sqlite_to_postgres(sqlite_path: str) -> bool:
    """
    Migrate data from SQLite to PostgreSQL.
    
    Args:
        sqlite_path: Path to SQLite database file
        
    Returns:
        True if migration successful, False otherwise
    """
    try:
        # This would run the migration script
        import subprocess
        result = subprocess.run([
            "python3", "scripts/migrate_to_postgres.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Migration completed successfully")
            return True
        else:
            logger.error(f"❌ Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration error: {e}")
        return False
