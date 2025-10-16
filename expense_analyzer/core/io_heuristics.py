"""
Robust heuristic column detection for various input formats.
"""
import pandas as pd
import numpy as np
import re
from typing import Tuple, Optional, List


def heuristic_detect_columns(df: pd.DataFrame, seed: Tuple[Optional[str], Optional[str], Optional[str]] = (None, None, None)) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Heuristically detect date, description, and amount columns.
    
    Args:
        df: DataFrame to analyze
        seed: Tuple of (date_col, desc_col, amount_col) hints
    
    Returns:
        Tuple of (date_col, desc_col, amount_col)
    """
    date_seed, desc_seed, amount_seed = seed
    
    # Detect date column
    date_col = date_seed
    if not date_col:
        best_col, best_ratio = None, 0.0
        for col in df.columns:
            try:
                # Try parsing as datetime with various formats
                parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                ratio = parsed.notna().mean()
                if ratio > best_ratio and ratio > 0.2:  # At least 20% valid dates
                    best_col, best_ratio = col, ratio
            except:
                continue
        date_col = best_col
    
    # Detect amount column
    amount_col = amount_seed
    if not amount_col:
        amount_col = max(df.columns, key=lambda c: _amount_score(df[c]))
    
    # Detect description column
    desc_col = desc_seed
    if not desc_col:
        # Look for text columns with high uniqueness
        obj_cols = [c for c in df.columns if df[c].dtype == object] or list(df.columns)
        if obj_cols:
            desc_col = max(obj_cols, key=lambda c: df[c].astype(str).nunique() / max(1, len(df)))
    
    return date_col, desc_col, amount_col


def _amount_score(series: pd.Series) -> float:
    """Score how likely a column contains amounts."""
    try:
        # Clean the series for numeric parsing
        cleaned = _str_series(series)
        numeric_series = pd.to_numeric(cleaned, errors="coerce")
        
        # Score based on valid numeric ratio and magnitude
        valid_ratio = numeric_series.notna().mean()
        total_magnitude = np.nansum(np.abs(numeric_series)) + 1
        magnitude_score = np.log10(total_magnitude)
        
        return valid_ratio * (1 + magnitude_score)
    except:
        return 0.0


def _str_series(series: pd.Series) -> pd.Series:
    """Clean string series for numeric parsing."""
    return (series.astype(str)
            .str.replace("\u200f", "", regex=False)  # RTL mark
            .str.replace("\u200e", "", regex=False)  # LTR mark
            .str.replace(",", "", regex=False)       # Thousands separator
            .str.replace("₪", "", regex=False)       # Currency symbol
            .str.replace("−", "-", regex=False))     # Unicode minus


def first_nonempty_header(df: pd.DataFrame, min_columns: int = 3) -> Optional[int]:
    """
    Find the first row that could be a header (has enough non-null values).
    
    Args:
        df: DataFrame to analyze
        min_columns: Minimum number of non-null values to consider as header
    
    Returns:
        Row index of first potential header, or None
    """
    for i in range(min(len(df), 10)):  # Check first 10 rows
        row = df.iloc[i]
        # Count non-null and non-empty values
        non_empty_count = sum(1 for val in row if pd.notna(val) and str(val).strip() != '')
        if non_empty_count >= min_columns:
            return i
    return None


def recover_header(df: pd.DataFrame, header_row: int) -> pd.DataFrame:
    """
    Recover DataFrame with proper header from specified row.
    
    Args:
        df: DataFrame with shifted headers
        header_row: Row index containing headers
    
    Returns:
        DataFrame with proper headers
    """
    if header_row is None or header_row >= len(df):
        return df
    
    # Set header row as column names
    new_df = df.iloc[header_row + 1:].copy()
    new_df.columns = df.iloc[header_row].values
    new_df.reset_index(drop=True, inplace=True)
    
    return new_df


def detect_columns_with_hints(df: pd.DataFrame, column_hints: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Detect columns using hints from profile.
    
    Args:
        df: DataFrame to analyze
        column_hints: Dict with 'date', 'description', 'amount' lists of possible column names
    
    Returns:
        Tuple of (date_col, desc_col, amount_col)
    """
    date_col = _find_column_by_hints(df, column_hints.get('date', []))
    desc_col = _find_column_by_hints(df, column_hints.get('description', []))
    amount_col = _find_column_by_hints(df, column_hints.get('amount', []))
    
    return date_col, desc_col, amount_col


def _find_column_by_hints(df: pd.DataFrame, hints: List[str]) -> Optional[str]:
    """Find column matching any of the hints."""
    if not hints:
        return None
    
    for hint in hints:
        for col in df.columns:
            if hint.lower() in str(col).lower():
                return col
    return None
