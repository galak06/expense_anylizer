"""
Input validation utilities for the expense analyzer.
"""
from datetime import datetime, date
from typing import List, Optional, Tuple
import re
from .config import get_settings


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_transaction(
    transaction_date: date,
    description: str,
    amount: float,
    category: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """
    Validate transaction inputs.
    
    Args:
        transaction_date: Transaction date
        description: Transaction description
        amount: Transaction amount
        category: Transaction category (optional)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Date validation
    if not isinstance(transaction_date, date):
        errors.append("Date must be a valid date")
    elif transaction_date > datetime.now().date():
        errors.append("Date cannot be in the future")
    elif transaction_date < date(2000, 1, 1):
        errors.append("Date cannot be before year 2000")
    
    # Description validation
    if not description or not description.strip():
        errors.append("Description is required")
    elif len(description.strip()) > 500:
        errors.append("Description cannot exceed 500 characters")
    elif len(description.strip()) < 2:
        errors.append("Description must be at least 2 characters")
    
    # Amount validation
    if not isinstance(amount, (int, float)):
        errors.append("Amount must be a number")
    elif amount == 0:
        errors.append("Amount cannot be zero")
    elif abs(amount) > 1000000:  # 1 million limit
        errors.append("Amount cannot exceed 1,000,000")
    elif abs(amount) < 0.01:  # Minimum 1 cent
        errors.append("Amount must be at least 0.01")
    
    # Category validation (if provided)
    if category is not None and category.strip():
        if len(category.strip()) > 100:
            errors.append("Category cannot exceed 100 characters")
        # Check for potentially harmful characters
        if re.search(r'[<>"\']', category):
            errors.append("Category contains invalid characters")
    
    return len(errors) == 0, errors


def validate_user_input(
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """
    Validate user registration input.
    
    Args:
        username: Username
        email: Email address
        password: Password
        full_name: Full name (optional)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Username validation
    if not username or not username.strip():
        errors.append("Username is required")
    elif len(username.strip()) < 3:
        errors.append("Username must be at least 3 characters")
    elif len(username.strip()) > 50:
        errors.append("Username cannot exceed 50 characters")
    elif not re.match(r'^[a-zA-Z0-9_-]+$', username.strip()):
        errors.append("Username can only contain letters, numbers, underscores, and hyphens")
    
    # Email validation
    if not email or not email.strip():
        errors.append("Email is required")
    elif len(email.strip()) > 254:
        errors.append("Email cannot exceed 254 characters")
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email.strip()):
        errors.append("Email format is invalid")
    
    # Password validation
    if not password:
        errors.append("Password is required")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters")
    elif len(password) > 128:
        errors.append("Password cannot exceed 128 characters")
    elif not re.search(r'[A-Za-z]', password):
        errors.append("Password must contain at least one letter")
    elif not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one number")
    
    # Full name validation (optional)
    if full_name is not None and full_name.strip():
        if len(full_name.strip()) > 100:
            errors.append("Full name cannot exceed 100 characters")
        if re.search(r'[<>"\']', full_name):
            errors.append("Full name contains invalid characters")
    
    return len(errors) == 0, errors


def validate_file_upload(filename: str, file_size: int) -> Tuple[bool, List[str]]:
    """
    Validate file upload.
    
    Args:
        filename: Name of the uploaded file
        file_size: Size of the file in bytes
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    settings = get_settings()
    
    # File extension validation
    allowed_extensions = ['.csv', '.xlsx', '.xls']
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if not file_ext or f'.{file_ext}' not in allowed_extensions:
        errors.append(f"File type not supported. Allowed types: {', '.join(allowed_extensions)}")
    
    # File size validation (configurable limit)
    max_size = settings.max_file_size_mb * 1024 * 1024  # Convert MB to bytes
    if file_size > max_size:
        errors.append(f"File size cannot exceed {settings.max_file_size_mb}MB")
    
    # Filename validation
    if len(filename) > 255:
        errors.append("Filename cannot exceed 255 characters")
    
    # Check for potentially harmful characters in filename
    if re.search(r'[<>:"/\\|?*]', filename):
        errors.append("Filename contains invalid characters")
    
    return len(errors) == 0, errors


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input by removing potentially harmful characters.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum length of the text
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove control characters and normalize whitespace
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(text))
    sanitized = re.sub(r'\s+', ' ', sanitized.strip())
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()
    
    return sanitized


def validate_search_query(query: str) -> Tuple[bool, List[str]]:
    """
    Validate search query input.
    
    Args:
        query: Search query string
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not query or not query.strip():
        errors.append("Search query cannot be empty")
    elif len(query.strip()) > 200:
        errors.append("Search query cannot exceed 200 characters")
    
    # Check for potentially harmful patterns
    if re.search(r'[<>"\']', query):
        errors.append("Search query contains invalid characters")
    
    return len(errors) == 0, errors
