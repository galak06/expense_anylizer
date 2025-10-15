"""
Authentication module for user management and secure access.
"""
import sqlite3
import bcrypt
import secrets
from typing import Optional, Dict, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from .config import get_settings
from .logging_config import get_logger, log_security_event, log_data_access, log_error

logger = get_logger(__name__)


class AuthManager:
    """Handles user authentication and authorization."""

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        if db_path is None:
            db_path = settings.database_path

        self.db_path = db_path
        self._ensure_db_directory()
        self._init_auth_tables()

    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _init_auth_tables(self):
        """Initialize authentication tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)

            # Session tokens table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_valid BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_username
                ON users(username)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_email
                ON users(email)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_token
                ON session_tokens(token)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_user_id
                ON session_tokens(user_id)
            """)

            conn.commit()

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new user account.

        Returns:
            Tuple of (success: bool, message: str, user_id: Optional[int])
        """
        # Validate input
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long", None

        if not email or '@' not in email:
            return False, "Invalid email address", None

        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long", None

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if username or email already exists
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM users
                    WHERE username = ? OR email = ?
                """, (username, email))

                if cursor.fetchone()[0] > 0:
                    return False, "Username or email already exists", None

                # Hash password and create user
                password_hash = self._hash_password(password)

                cursor = conn.execute("""
                    INSERT INTO users (username, email, password_hash, full_name)
                    VALUES (?, ?, ?, ?)
                """, (username, email, password_hash, full_name))

                conn.commit()
                user_id = cursor.lastrowid

                return True, "User created successfully", user_id

        except sqlite3.IntegrityError as e:
            return False, f"Database error: {str(e)}", None
        except Exception as e:
            return False, f"Error creating user: {str(e)}", None

    def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Authenticate a user with username and password.

        Returns:
            Tuple of (success: bool, message: str, user_data: Optional[Dict])
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, username, email, password_hash, full_name, is_active
                    FROM users
                    WHERE username = ?
                """, (username,))

                user = cursor.fetchone()

                if not user:
                    log_security_event(logger, "LOGIN_FAILED", f"Invalid username: {username}")
                    return False, "Invalid username or password", None

                user_id, username, email, password_hash, full_name, is_active = user

                # Check if account is active
                if not is_active:
                    log_security_event(logger, "LOGIN_FAILED", f"Disabled account: {username}")
                    return False, "Account is disabled", None

                # Verify password
                if not self._verify_password(password, password_hash):
                    log_security_event(logger, "LOGIN_FAILED", f"Invalid password for user: {username}")
                    return False, "Invalid username or password", None

                # Update last login
                conn.execute("""
                    UPDATE users
                    SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user_id,))
                conn.commit()

                log_data_access(logger, "LOGIN", user_id, f"Successful login for {username}")

                # Return user data (without password hash)
                user_data = {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name
                }

                # Create session token for persistent login
                session_token = self.create_session_token(user_id)
                if session_token:
                    user_data['session_token'] = session_token

                return True, "Login successful", user_data

        except Exception as e:
            log_error(logger, e, f"Authentication error for user: {username}")
            return False, f"Authentication error: {str(e)}", None

    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Change user password.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not new_password or len(new_password) < 6:
            return False, "New password must be at least 6 characters long"

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get current password hash
                cursor = conn.execute("""
                    SELECT password_hash FROM users WHERE id = ?
                """, (user_id,))

                result = cursor.fetchone()
                if not result:
                    return False, "User not found"

                current_hash = result[0]

                # Verify old password
                if not self._verify_password(old_password, current_hash):
                    return False, "Current password is incorrect"

                # Hash new password and update
                new_hash = self._hash_password(new_password)

                conn.execute("""
                    UPDATE users
                    SET password_hash = ?
                    WHERE id = ?
                """, (new_hash, user_id))

                conn.commit()

                return True, "Password changed successfully"

        except Exception as e:
            return False, f"Error changing password: {str(e)}"

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user information by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, username, email, full_name, created_at, last_login
                    FROM users
                    WHERE id = ?
                """, (user_id,))

                user = cursor.fetchone()
                if user:
                    return {
                        'id': user[0],
                        'username': user[1],
                        'email': user[2],
                        'full_name': user[3],
                        'created_at': user[4],
                        'last_login': user[5]
                    }
                return None

        except Exception:
            return None

    def get_all_users(self) -> list:
        """Get list of all users (admin function)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, username, email, full_name, created_at, last_login, is_active
                    FROM users
                    ORDER BY created_at DESC
                """)

                users = []
                for row in cursor.fetchall():
                    users.append({
                        'id': row[0],
                        'username': row[1],
                        'email': row[2],
                        'full_name': row[3],
                        'created_at': row[4],
                        'last_login': row[5],
                        'is_active': row[6]
                    })
                return users

        except Exception:
            return []

    def deactivate_user(self, user_id: int) -> Tuple[bool, str]:
        """Deactivate a user account."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE users
                    SET is_active = 0
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
                return True, "User deactivated successfully"
        except Exception as e:
            return False, f"Error deactivating user: {str(e)}"

    def activate_user(self, user_id: int) -> Tuple[bool, str]:
        """Activate a user account."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE users
                    SET is_active = 1
                    WHERE id = ?
                """, (user_id,))
                conn.commit()
                return True, "User activated successfully"
        except Exception as e:
            return False, f"Error activating user: {str(e)}"

    def reset_password(
        self,
        username: str,
        email: str,
        new_password: str
    ) -> Tuple[bool, str]:
        """
        Reset user password using username and email verification.

        Args:
            username: Username of the account
            email: Email address of the account (for verification)
            new_password: New password to set

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not new_password or len(new_password) < 6:
            return False, "New password must be at least 6 characters long"

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verify username and email match
                cursor = conn.execute("""
                    SELECT id FROM users
                    WHERE username = ? AND email = ?
                """, (username, email))

                result = cursor.fetchone()
                if not result:
                    return False, "Username and email do not match any account"

                user_id = result[0]

                # Hash new password and update
                new_hash = self._hash_password(new_password)

                conn.execute("""
                    UPDATE users
                    SET password_hash = ?
                    WHERE id = ?
                """, (new_hash, user_id))

                conn.commit()

                return True, "Password reset successfully. You can now login with your new password."

        except Exception as e:
            return False, f"Error resetting password: {str(e)}"

    def create_session_token(
        self,
        user_id: int,
        expiry_days: int = 7
    ) -> Optional[str]:
        """
        Create a new session token for a user.

        Args:
            user_id: User ID
            expiry_days: Number of days until token expires (default 7)

        Returns:
            Session token string or None if failed
        """
        try:
            # Generate secure random token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=expiry_days)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO session_tokens (user_id, token, expires_at)
                    VALUES (?, ?, ?)
                """, (user_id, token, expires_at))
                conn.commit()

            log_security_event(logger, "SESSION_CREATED", f"Session token created for user_id: {user_id}")
            return token

        except Exception as e:
            log_error(logger, e, f"Error creating session token for user_id: {user_id}")
            return None

    def validate_session_token(self, token: str) -> Optional[Dict]:
        """
        Validate a session token and return user data if valid.

        Args:
            token: Session token to validate

        Returns:
            User data dictionary or None if invalid
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT st.user_id, st.expires_at, u.username, u.email, u.full_name, u.is_active
                    FROM session_tokens st
                    JOIN users u ON st.user_id = u.id
                    WHERE st.token = ? AND st.is_valid = 1
                """, (token,))

                result = cursor.fetchone()

                if not result:
                    return None

                user_id, expires_at, username, email, full_name, is_active = result

                # Check if token has expired
                expires_at_dt = datetime.fromisoformat(expires_at)
                if datetime.now() > expires_at_dt:
                    # Invalidate expired token
                    conn.execute("""
                        UPDATE session_tokens
                        SET is_valid = 0
                        WHERE token = ?
                    """, (token,))
                    conn.commit()
                    log_security_event(logger, "SESSION_EXPIRED", f"Expired token for user: {username}")
                    return None

                # Check if account is active
                if not is_active:
                    log_security_event(logger, "SESSION_REJECTED", f"Disabled account: {username}")
                    return None

                # Update last login
                conn.execute("""
                    UPDATE users
                    SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user_id,))
                conn.commit()

                log_data_access(logger, "SESSION_VALIDATED", user_id, f"Session validated for {username}")

                return {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name
                }

        except Exception as e:
            log_error(logger, e, "Error validating session token")
            return None

    def invalidate_session_token(self, token: str) -> bool:
        """
        Invalidate a session token (logout).

        Args:
            token: Session token to invalidate

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE session_tokens
                    SET is_valid = 0
                    WHERE token = ?
                """, (token,))
                conn.commit()

            log_security_event(logger, "SESSION_INVALIDATED", "Session token invalidated")
            return True

        except Exception as e:
            log_error(logger, e, "Error invalidating session token")
            return False

    def invalidate_all_user_sessions(self, user_id: int) -> bool:
        """
        Invalidate all session tokens for a user.

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE session_tokens
                    SET is_valid = 0
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()

            log_security_event(logger, "ALL_SESSIONS_INVALIDATED", f"All sessions invalidated for user_id: {user_id}")
            return True

        except Exception as e:
            log_error(logger, e, f"Error invalidating sessions for user_id: {user_id}")
            return False

    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired session tokens from database.

        Returns:
            Number of tokens removed
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM session_tokens
                    WHERE expires_at < CURRENT_TIMESTAMP
                """)
                conn.commit()
                removed_count = cursor.rowcount

            if removed_count > 0:
                log_security_event(logger, "TOKENS_CLEANED", f"Removed {removed_count} expired tokens")

            return removed_count

        except Exception as e:
            log_error(logger, e, "Error cleaning up expired tokens")
            return 0
