"""
Test suite for security fixes and improvements.
"""
import pytest
import pandas as pd
from datetime import datetime, date
import tempfile
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database import TransactionDB
from core.service import TransactionService
from core.auth import AuthManager
from core.validation import validate_transaction, validate_file_upload, validate_user_input, sanitize_input


class TestSecurityFixes:
    """Test security fixes and improvements."""

    def test_clear_all_transactions_user_isolation(self):
        """Test that clear_all_transactions only affects the specified user."""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create two users
            auth_manager = AuthManager(db_path)
            user1_id = auth_manager.create_user("user1", "user1@test.com", "password123")[2]
            user2_id = auth_manager.create_user("user2", "user2@test.com", "password123")[2]

            # Create database instances for each user
            db1 = TransactionDB(db_path, user_id=user1_id)
            db2 = TransactionDB(db_path, user_id=user2_id)

            # Add transactions for both users
            df1 = pd.DataFrame([{
                'Date': pd.to_datetime('2024-01-01'),
                'Description': 'User 1 transaction',
                'Amount': -100.0,
                'Category': 'Test',
                'Month': '2024-01'
            }])

            df2 = pd.DataFrame([{
                'Date': pd.to_datetime('2024-01-01'),
                'Description': 'User 2 transaction',
                'Amount': -200.0,
                'Category': 'Test',
                'Month': '2024-01'
            }])

            db1.save_transactions(df1)
            db2.save_transactions(df2)

            # Verify both users have transactions
            assert db1.get_transaction_count() == 1
            assert db2.get_transaction_count() == 1

            # Clear transactions for user1 only
            deleted_count = db1.clear_all_transactions()
            assert deleted_count == 1

            # Verify user1 has no transactions, user2 still has theirs
            assert db1.get_transaction_count() == 0
            assert db2.get_transaction_count() == 1

        finally:
            # Clean up
            os.unlink(db_path)

    def test_clear_all_transactions_requires_user_id(self):
        """Test that clear_all_transactions requires user_id."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            db = TransactionDB(db_path, user_id=None)
            
            with pytest.raises(ValueError, match="user_id must be provided"):
                db.clear_all_transactions()

        finally:
            os.unlink(db_path)

    def test_force_insert_transaction_security(self):
        """Test that force_insert_transaction properly handles user_id."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create user and database
            auth_manager = AuthManager(db_path)
            user_id = auth_manager.create_user("testuser", "test@test.com", "password123")[2]
            db = TransactionDB(db_path, user_id=user_id)

            # Test force insert
            df = pd.DataFrame([{
                'Date': pd.to_datetime('2024-01-01'),
                'Description': 'Test transaction',
                'Amount': -100.0,
                'Category': 'Test',
                'Month': '2024-01'
            }])

            inserted_count = db.force_insert_transaction(df)
            assert inserted_count == 1

            # Verify transaction was inserted for correct user
            transactions = db.load_transactions()
            assert len(transactions) == 1
            assert transactions.iloc[0]['Description'] == 'Test transaction'

        finally:
            os.unlink(db_path)

    def test_bulk_update_category_performance(self):
        """Test that bulk_update_category works correctly."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            # Create user and database
            auth_manager = AuthManager(db_path)
            user_id = auth_manager.create_user("testuser", "test@test.com", "password123")[2]
            db = TransactionDB(db_path, user_id=user_id)

            # Add multiple transactions with same description
            df = pd.DataFrame([
                {
                    'Date': pd.to_datetime('2024-01-01'),
                    'Description': 'Same vendor',
                    'Amount': -100.0,
                    'Category': None,
                    'Month': '2024-01'
                },
                {
                    'Date': pd.to_datetime('2024-01-02'),
                    'Description': 'Same vendor',
                    'Amount': -200.0,
                    'Category': None,
                    'Month': '2024-01'
                }
            ])

            db.save_transactions(df)

            # Bulk update category
            updated_count = db.bulk_update_category('Same vendor', 'New Category')
            assert updated_count == 2

            # Verify both transactions were updated
            transactions = db.load_transactions()
            assert all(transactions['Category'] == 'New Category')

        finally:
            os.unlink(db_path)


class TestInputValidation:
    """Test input validation functions."""

    def test_validate_transaction_valid_input(self):
        """Test validation with valid transaction input."""
        is_valid, errors = validate_transaction(
            date=date(2024, 1, 1),
            description="Valid transaction",
            amount=-100.0,
            category="Test"
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_transaction_invalid_date(self):
        """Test validation with invalid date."""
        is_valid, errors = validate_transaction(
            date=date(2030, 1, 1),  # Future date
            description="Valid transaction",
            amount=-100.0,
            category="Test"
        )
        assert not is_valid
        assert "Date cannot be in the future" in errors

    def test_validate_transaction_empty_description(self):
        """Test validation with empty description."""
        is_valid, errors = validate_transaction(
            date=date(2024, 1, 1),
            description="",
            amount=-100.0,
            category="Test"
        )
        assert not is_valid
        assert "Description is required" in errors

    def test_validate_transaction_zero_amount(self):
        """Test validation with zero amount."""
        is_valid, errors = validate_transaction(
            date=date(2024, 1, 1),
            description="Valid transaction",
            amount=0.0,
            category="Test"
        )
        assert not is_valid
        assert "Amount cannot be zero" in errors

    def test_validate_transaction_large_amount(self):
        """Test validation with amount exceeding limit."""
        is_valid, errors = validate_transaction(
            date=date(2024, 1, 1),
            description="Valid transaction",
            amount=-2000000.0,  # 2 million
            category="Test"
        )
        assert not is_valid
        assert "Amount cannot exceed 1,000,000" in errors

    def test_validate_file_upload_valid(self):
        """Test file upload validation with valid file."""
        is_valid, errors = validate_file_upload("test.csv", 1024)  # 1KB
        assert is_valid
        assert len(errors) == 0

    def test_validate_file_upload_invalid_extension(self):
        """Test file upload validation with invalid extension."""
        is_valid, errors = validate_file_upload("test.txt", 1024)
        assert not is_valid
        assert "File type not supported" in errors

    def test_validate_file_upload_too_large(self):
        """Test file upload validation with file too large."""
        large_size = 20 * 1024 * 1024  # 20MB
        is_valid, errors = validate_file_upload("test.csv", large_size)
        assert not is_valid
        assert "File size cannot exceed" in errors

    def test_validate_user_input_valid(self):
        """Test user input validation with valid data."""
        is_valid, errors = validate_user_input(
            username="testuser",
            email="test@example.com",
            password="password123",
            full_name="Test User"
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_user_input_short_username(self):
        """Test user input validation with short username."""
        is_valid, errors = validate_user_input(
            username="ab",  # Too short
            email="test@example.com",
            password="password123"
        )
        assert not is_valid
        assert "Username must be at least 3 characters" in errors

    def test_validate_user_input_invalid_email(self):
        """Test user input validation with invalid email."""
        is_valid, errors = validate_user_input(
            username="testuser",
            email="invalid-email",
            password="password123"
        )
        assert not is_valid
        assert "Email format is invalid" in errors

    def test_validate_user_input_weak_password(self):
        """Test user input validation with weak password."""
        is_valid, errors = validate_user_input(
            username="testuser",
            email="test@example.com",
            password="123"  # Too short and no letters
        )
        assert not is_valid
        assert "Password must be at least 6 characters" in errors
        assert "Password must contain at least one letter" in errors

    def test_sanitize_input(self):
        """Test input sanitization."""
        # Test with control characters
        input_text = "Hello\x00\x1fWorld"
        sanitized = sanitize_input(input_text)
        assert sanitized == "Hello World"

        # Test with excessive whitespace
        input_text = "  Hello   World  "
        sanitized = sanitize_input(input_text)
        assert sanitized == "Hello World"

        # Test with length limit
        long_text = "A" * 2000
        sanitized = sanitize_input(long_text, max_length=100)
        assert len(sanitized) == 100
        assert sanitized == "A" * 100


class TestAuthenticationSecurity:
    """Test authentication security features."""

    def test_authentication_logging(self):
        """Test that authentication events are logged."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            auth_manager = AuthManager(db_path)
            
            # Create user
            auth_manager.create_user("testuser", "test@test.com", "password123")
            
            # Test failed login (should be logged)
            success, message, user_data = auth_manager.authenticate_user("testuser", "wrongpassword")
            assert not success
            assert "Invalid username or password" in message

            # Test successful login
            success, message, user_data = auth_manager.authenticate_user("testuser", "password123")
            assert success
            assert user_data is not None
            assert user_data['username'] == "testuser"

        finally:
            os.unlink(db_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
