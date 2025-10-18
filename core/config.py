"""
Configuration settings for Curser expense analyzer.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # File I/O settings
    encodings_list: List[str] = ["utf-8", "cp1255", "iso-8859-8", "windows-1255"]
    delimiters_list: List[str] = [",", ";", "\t"]
    default_mapping_path: str = "data/mapping.csv"

    # Database settings
    database_path: str = "data/transactions.db"
    database_url: Optional[str] = None
    database_type: str = "sqlite"  # sqlite or postgresql
    
    # Categorization settings
    keyword_confidence: float = 0.95
    fuzzy_match_threshold: int = 86
    fuzzy_confidence_threshold: float = 0.8
    llm_confidence: float = 0.75
    min_word_length: int = 3
    min_learning_confidence: float = 0.9  # Only learn from high-confidence corrections
    enable_multi_strategy_boost: bool = True  # Boost confidence when strategies agree
    
    # OpenAI settings
    openai_api_key: Optional[str] = None
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Security settings
    session_timeout_minutes: int = 60
    
    # File upload limits
    max_file_size_mb: int = 10
    
    # Environment settings
    debug: bool = False
    environment: str = "development"
    secret_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings