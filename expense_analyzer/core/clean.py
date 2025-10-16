import pandas as pd
import re
from typing import Union


RTL_MARKERS = '\u200f\u200e\u202a\u202b\u202c\u202d\u202e'
INVISIBLE_SPACES = '\u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a'


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return str(text)

    for char in RTL_MARKERS + INVISIBLE_SPACES:
        text = text.replace(char, ' ')

    return re.sub(r'\s+', ' ', text.strip())


CURRENCY_SYMBOLS = '₪$€£¥₹₽₩₦₡₨₴₸₺₼₾₿'
UNICODE_MINUS = '−–—‐‑‒'


def _is_negative_with_parentheses(amount_str: str) -> tuple[bool, str]:
    has_parentheses = '(' in amount_str and ')' in amount_str
    cleaned = amount_str.replace('(', '').replace(')', '') if has_parentheses else amount_str
    return has_parentheses, cleaned


def _normalize_decimal_separators(amount_str: str) -> str:
    if '.' in amount_str and ',' in amount_str:
        return amount_str.replace(',', '')

    if ',' in amount_str:
        parts = amount_str.split(',')
        return amount_str.replace(',', '.') if len(parts) == 2 and len(parts[1]) <= 2 else amount_str.replace(',', '')

    if '.' in amount_str:
        parts = amount_str.split('.')
        return amount_str if len(parts) == 2 and len(parts[1]) <= 2 else amount_str.replace('.', '')

    return amount_str


def coerce_amount(amount: Union[str, float, int]) -> float:
    if pd.isna(amount):
        return 0.0

    if isinstance(amount, (int, float)):
        return float(amount)

    amount_str = str(amount).strip()
    if not amount_str:
        return 0.0

    is_negative, amount_str = _is_negative_with_parentheses(amount_str)

    for symbol in CURRENCY_SYMBOLS:
        amount_str = amount_str.replace(symbol, '')

    amount_str = _normalize_decimal_separators(amount_str)
    amount_str = amount_str.replace(' ', '')

    if is_negative:
        amount_str = '-' + amount_str

    for minus_char in UNICODE_MINUS:
        amount_str = amount_str.replace(minus_char, '-')

    numeric_match = re.search(r'-?\d+\.?\d*', amount_str)
    if numeric_match:
        try:
            return float(numeric_match.group())
        except ValueError:
            return 0.0

    return 0.0


TEXT_COLUMNS = ['Description', 'Category', 'Account']


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    result_df = df.copy()

    for col in TEXT_COLUMNS:
        if col in result_df.columns:
            result_df[col] = result_df[col].apply(
                lambda x: normalize_text(x) if pd.notna(x) else None
            )

    if 'Amount' in result_df.columns:
        result_df['Amount'] = result_df['Amount'].apply(coerce_amount)

    return result_df


EXPENSE_KEYWORDS = [
    'חיוב', 'debit', 'withdrawal', 'payment', 'purchase', 'transfer out',
    'קנייה', 'רכישה', 'תשלום', 'העברה', 'משיכה'
]

INCOME_KEYWORDS = [
    'זיכוי', 'credit', 'deposit', 'transfer in', 'salary', 'refund',
    'הפקדה', 'העברה', 'משכורת', 'החזר', 'בונוס'
]


def _is_expense_transaction(description: str) -> bool:
    description_lower = description.lower()
    has_expense_keyword = any(keyword in description_lower for keyword in EXPENSE_KEYWORDS)
    has_income_keyword = any(keyword in description_lower for keyword in INCOME_KEYWORDS)
    return has_expense_keyword and not has_income_keyword


def detect_negative_amounts(df: pd.DataFrame, amount_col: str = 'Amount', all_expenses: bool = False) -> pd.DataFrame:
    """
    Convert positive amounts to negative for expense transactions.

    Args:
        df: DataFrame with transactions
        amount_col: Name of the amount column
        all_expenses: If True, treat all positive amounts as expenses (for credit cards)

    Returns:
        DataFrame with corrected signs
    """
    if amount_col not in df.columns:
        return df

    result_df = df.copy()

    if all_expenses:
        # Credit card mode: all positive amounts are expenses
        mask = result_df[amount_col] > 0
        result_df.loc[mask, amount_col] = -result_df.loc[mask, amount_col].abs()
    else:
        # Bank account mode: use keywords to detect expenses
        for idx, row in result_df.iterrows():
            amount = row[amount_col]
            if amount <= 0:
                continue

            description = str(row.get('Description', ''))
            if _is_expense_transaction(description):
                result_df.at[idx, amount_col] = -abs(amount)

    return result_df
