import pandas as pd
import chardet
from typing import Tuple, Optional, Dict, Any
import re
from .config import get_settings
from .profiles import load_profiles, match_profile, get_column_hints, get_header_row, get_data_start_row
from .io_heuristics import heuristic_detect_columns, first_nonempty_header, recover_header, detect_columns_with_hints


def detect_encoding(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        return result.get('encoding', 'utf-8')


def _try_read_csv_with_combinations(file_path: str) -> Optional[pd.DataFrame]:
    settings = get_settings()
    for encoding in settings.encodings_list:
        for delimiter in settings.delimiters_list:
            try:
                df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)
                if len(df.columns) > 1:
                    return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
    return None


def read_any(file_path: str, sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, Optional[dict]]:
    """Read any supported file format with profile-based processing."""
    file_ext = file_path.lower().split('.')[-1]
    file_name = file_path.split('/')[-1]
    
    # Load profiles
    profiles = load_profiles()
    
    # Try to match a profile first
    matched_profile = None
    df = None
    
    if file_ext == 'xlsx':
        # For Excel files, try to read with potential header recovery
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        
        # Handle case where read_excel returns a dict (multiple sheets)
        if isinstance(df, dict):
            if sheet_name is None:
                # Use the first sheet
                sheet_name = list(df.keys())[0]
            df = df[sheet_name]
        
        # Try to match profile
        matched_profile = match_profile(file_name, sheet_name, df, profiles)
        
        if matched_profile:
            # Apply profile-specific processing
            header_row = get_header_row(matched_profile)
            data_start_row = get_data_start_row(matched_profile)
            
            if header_row is not None:
                # Use specified header row
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
                if data_start_row is not None and data_start_row > header_row:
                    df = df.iloc[data_start_row - header_row - 1:]
            else:
                # Try to recover header automatically
                header_row_idx = first_nonempty_header(df)
                if header_row_idx is not None:
                    df = recover_header(df, header_row_idx)
                else:
                    # Fallback to default Excel reading
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            # No profile match, try to recover header
            header_row_idx = first_nonempty_header(df)
            if header_row_idx is not None:
                df = recover_header(df, header_row_idx)
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name)

    elif file_ext == 'csv':
        df = _try_read_csv_with_combinations(file_path)
        if df is None:
            encoding = detect_encoding(file_path)
            df = pd.read_csv(file_path, encoding=encoding)
        
        # Try to match profile
        matched_profile = match_profile(file_name, sheet_name, df, profiles)
        
        if matched_profile:
            header_row = get_header_row(matched_profile)
            if header_row is not None:
                df = pd.read_csv(file_path, encoding=detect_encoding(file_path), header=header_row)
        else:
            # Try to recover header automatically
            header_row_idx = first_nonempty_header(df)
            if header_row_idx is not None:
                df = recover_header(df, header_row_idx)

    else:
        raise ValueError(f"Unsupported file format: {file_ext}")
    
    return df, matched_profile


DATE_PATTERNS = [
    r'date|תאריך|תאור|תאור.*תאריך',
    r'תאריך.*עסקה',
    r'transaction.*date'
]

DESC_PATTERNS = [
    r'description|תיאור|תאור|פרט|פרטי.*עסקה',
    r'merchant|ספק|חנות',
    r'details|פרטים'
]

AMOUNT_PATTERNS = [
    r'amount|סכום|sum|total',
    r'credit|debit|חיוב|זיכוי',
    r'balance|יתרה'
]


def _is_date_column(df: pd.DataFrame, col: str) -> bool:
    if pd.api.types.is_datetime64_any_dtype(df[col]):
        return True
    sample_values = df[col].dropna().head(5)
    return any(str(val).count('/') >= 2 or str(val).count('-') >= 2 for val in sample_values)


def _is_amount_column(df: pd.DataFrame, col: str) -> bool:
    if pd.api.types.is_numeric_dtype(df[col]):
        return True
    sample_values = df[col].dropna().head(5)
    return any(re.search(r'[\d,.-]', str(val)) for val in sample_values)


def _detect_column_by_patterns(df: pd.DataFrame, patterns: list[str], validator=None) -> Optional[str]:
    for col in df.columns:
        col_lower = str(col).lower()
        for pattern in patterns:
            if re.search(pattern, col_lower):
                if validator is None or validator(df, col):
                    return col
    return None


def detect_columns(df: pd.DataFrame, column_hints: Optional[Dict[str, list]] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Detect columns with optional hints from profile."""
    
    # First try with hints if provided
    if column_hints:
        date_col, desc_col, amount_col = detect_columns_with_hints(df, column_hints)
        if all([date_col, desc_col, amount_col]):
            return date_col, desc_col, amount_col
    
    # Fallback to pattern-based detection
    date_col = _detect_column_by_patterns(df, DATE_PATTERNS, _is_date_column)
    desc_col = _detect_column_by_patterns(df, DESC_PATTERNS)
    amount_col = _detect_column_by_patterns(df, AMOUNT_PATTERNS, _is_amount_column)

    # Final fallback to heuristics
    if not all([date_col, desc_col, amount_col]):
        heuristic_result = heuristic_detect_columns(df, (date_col, desc_col, amount_col))
        date_col, desc_col, amount_col = heuristic_result

    # Last resort: positional heuristics
    if date_col is None and len(df.columns) >= 1:
        if pd.api.types.is_datetime64_any_dtype(df.iloc[:, 0]):
            date_col = df.columns[0]

    if desc_col is None and len(df.columns) >= 2:
        desc_col = df.columns[1]

    if amount_col is None and len(df.columns) >= 3:
        amount_col = df.columns[2]

    return date_col, desc_col, amount_col


def load_transactions(file_path: str) -> pd.DataFrame:
    """Load transactions with profile-based processing."""
    # Read file with profile support
    df, matched_profile = read_any(file_path)
    
    # Get column hints from matched profile
    column_hints = None
    if matched_profile:
        column_hints = get_column_hints(matched_profile)
    
    # Detect columns with hints
    date_col, desc_col, amount_col = detect_columns(df, column_hints)

    if not all([date_col, desc_col, amount_col]):
        raise ValueError(f"Could not detect required columns. Found: date={date_col}, desc={desc_col}, amount={amount_col}")

    result_df = pd.DataFrame({
        'Date': pd.to_datetime(df[date_col], errors='coerce', dayfirst=True),
        'Description': df[desc_col].astype(str),
        'Amount': df[amount_col],
        'Category': None,
        'Month': pd.to_datetime(df[date_col], errors='coerce', dayfirst=True).dt.strftime('%Y-%m')
    })

    return result_df.dropna(subset=['Date'])


def get_file_info(file_path: str) -> Dict[str, Any]:
    try:
        df, matched_profile = read_any(file_path)
        date_col, desc_col, amount_col = detect_columns(df)

        return {
            'file_path': file_path,
            'total_rows': len(df),
            'columns': list(df.columns),
            'detected_columns': {
                'date': date_col,
                'description': desc_col,
                'amount': amount_col
            },
            'sample_data': df.head(3).to_dict('records') if len(df) > 0 else []
        }
    except Exception as e:
        return {
            'file_path': file_path,
            'error': str(e)
        }
