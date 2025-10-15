"""
Logging configuration for the expense analyzer.
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        log_format: Optional custom log format
        
    Returns:
        Configured logger instance
    """
    # Default log format
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[]
    )
    
    # Get root logger
    logger = logging.getLogger()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Security-related logging
def log_security_event(logger: logging.Logger, event_type: str, details: str, user_id: Optional[int] = None):
    """
    Log security-related events.
    
    Args:
        logger: Logger instance
        event_type: Type of security event
        details: Event details
        user_id: Optional user ID
    """
    user_info = f" (User: {user_id})" if user_id else ""
    logger.warning(f"SECURITY_EVENT: {event_type}{user_info} - {details}")


def log_data_access(logger: logging.Logger, operation: str, user_id: int, details: str = ""):
    """
    Log data access operations.
    
    Args:
        logger: Logger instance
        operation: Type of operation (CREATE, READ, UPDATE, DELETE)
        user_id: User ID performing the operation
        details: Additional details
    """
    logger.info(f"DATA_ACCESS: {operation} by user {user_id} - {details}")


def log_error(logger: logging.Logger, error: Exception, context: str = "", user_id: Optional[int] = None):
    """
    Log errors with context.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context
        user_id: Optional user ID
    """
    user_info = f" (User: {user_id})" if user_id else ""
    logger.error(f"ERROR{user_info} in {context}: {str(error)}", exc_info=True)


def log_performance(logger: logging.Logger, operation: str, duration: float, details: str = ""):
    """
    Log performance metrics.
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration: Duration in seconds
        details: Additional details
    """
    logger.info(f"PERFORMANCE: {operation} took {duration:.3f}s - {details}")
