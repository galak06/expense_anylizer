import pandas as pd
from typing import Dict, Any
import numpy as np


SUMMARY_COLUMNS = ['Month', 'Total_Expenses', 'Total_Income', 'Net', 'Transaction_Count']
CATEGORY_COLUMNS = ['category', 'Total_Expenses', 'Total_Income', 'Transaction_Count', 'Avg_Amount']


def _ensure_month_column(df: pd.DataFrame) -> pd.DataFrame:
    if 'Month' not in df.columns and 'date' in df.columns:
        df = df.copy()
        df['Month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
    return df


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    df = _ensure_month_column(df)

    monthly = pd.DataFrame({
        'Total_Expenses': df[df['amount'] < 0].groupby('Month')['amount'].sum().abs(),
        'Total_Income': df[df['amount'] > 0].groupby('Month')['amount'].sum(),
        'Net': df.groupby('Month')['amount'].sum(),
        'Transaction_Count': df.groupby('Month')['amount'].count()
    }).fillna(0).round(2).reset_index().sort_values('Month')

    return monthly[SUMMARY_COLUMNS]


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or df['category'].notna().sum() == 0:
        return pd.DataFrame(columns=CATEGORY_COLUMNS)

    categorized_df = df[df['category'].notna()]

    # Separate expenses and income BEFORE aggregating
    expenses_df = categorized_df[categorized_df['amount'] < 0]
    income_df = categorized_df[categorized_df['amount'] > 0]

    # Calculate expenses (sum of negative amounts, converted to positive)
    expenses_by_category = expenses_df.groupby('category')['amount'].sum().abs()

    # Calculate income (sum of positive amounts)
    income_by_category = income_df.groupby('category')['amount'].sum()

    # Calculate transaction counts and averages
    counts_by_category = categorized_df.groupby('category')['amount'].count()
    avg_by_category = categorized_df.groupby('category')['amount'].mean()

    # Combine into summary DataFrame
    summary = pd.DataFrame({
        'Total_Expenses': expenses_by_category,
        'Total_Income': income_by_category,
        'Transaction_Count': counts_by_category,
        'Avg_Amount': avg_by_category
    }).fillna(0).round(2)

    return summary.reset_index().sort_values('Total_Expenses', ascending=False)[CATEGORY_COLUMNS]


TOP5_COLUMNS = ['category', 'description', 'Total_Amount', 'Transaction_Count']


def top5_by_category(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or df['category'].notna().sum() == 0:
        return pd.DataFrame(columns=TOP5_COLUMNS)

    categorized_df = df[df['category'].notna()]

    vendor_summary = categorized_df.groupby(['category', 'description']).agg({
        'amount': ['sum', 'count']
    }).round(2)

    vendor_summary.columns = ['Total_Amount', 'Transaction_Count']
    vendor_summary = vendor_summary.reset_index()

    top5_results = [
        vendor_summary[vendor_summary['category'] == category]
        .sort_values('Total_Amount', key=abs, ascending=False)
        .head(5)
        for category in vendor_summary['category'].unique()
    ]

    if not top5_results:
        return pd.DataFrame(columns=TOP5_COLUMNS)

    return pd.concat(top5_results, ignore_index=True)[TOP5_COLUMNS]


def spending_trends(df: pd.DataFrame, months: int = 6) -> pd.DataFrame:
    """
    Get spending trends over time by category.

    Args:
        df: DataFrame with transactions
        months: Number of recent months to include

    Returns:
        Pivoted DataFrame with months as rows and categories as columns
    """
    if df.empty:
        return pd.DataFrame(columns=['Month', 'category', 'amount'])

    df = _ensure_month_column(df)

    unique_months = sorted(df['Month'].unique())
    if len(unique_months) > months:
        recent_months = unique_months[-months:]
        df = df[df['Month'].isin(recent_months)]

    trends = df.groupby(['Month', 'category']).agg({'amount': 'sum'}).round(2)
    trends['amount'] = trends['amount'].abs()

    return trends.reset_index().pivot(index='Month', columns='category', values='amount').fillna(0)


def month_over_month_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate month-over-month spending changes.

    Returns:
        DataFrame with current month, previous month, change amount, and change percentage
    """
    if df.empty:
        return pd.DataFrame(columns=['Month', 'Current_Spending', 'Previous_Spending', 'Change_Amount', 'Change_Percent'])

    df = _ensure_month_column(df)

    # Get monthly totals (expenses only, as positive values)
    monthly = df[df['amount'] < 0].groupby('Month')['amount'].sum().abs().reset_index()
    monthly.columns = ['Month', 'Spending']
    monthly = monthly.sort_values('Month')

    # Ensure numeric types
    monthly['Spending'] = pd.to_numeric(monthly['Spending'], errors='coerce')

    # Calculate changes
    monthly['Previous_Spending'] = monthly['Spending'].shift(1)
    monthly['Change_Amount'] = monthly['Spending'] - monthly['Previous_Spending']
    
    # Handle division by zero and ensure numeric types
    monthly['Change_Percent'] = monthly['Change_Amount'] / monthly['Previous_Spending'].replace(0, np.nan) * 100
    monthly['Change_Percent'] = monthly['Change_Percent'].round(1)

    # Rename columns for clarity
    monthly = monthly.rename(columns={'Spending': 'Current_Spending'})

    return monthly[['Month', 'Current_Spending', 'Previous_Spending', 'Change_Amount', 'Change_Percent']].round(2)


def category_trends(df: pd.DataFrame) -> pd.DataFrame:
    """
    Show spending trends by category with month-over-month changes.

    Returns:
        DataFrame with categories and their spending trends
    """
    if df.empty or df['category'].notna().sum() == 0:
        return pd.DataFrame(columns=['category', 'Latest_Month', 'Previous_Month', 'Change_Percent', 'Trend'])

    df = _ensure_month_column(df)
    categorized_df = df[df['category'].notna()]

    # Get latest two months
    unique_months = sorted(categorized_df['Month'].unique())
    if len(unique_months) < 2:
        return pd.DataFrame(columns=['category', 'Latest_Month', 'Previous_Month', 'Change_Percent', 'Trend'])

    latest_month = unique_months[-1]
    previous_month = unique_months[-2]

    # Calculate spending by category for each month
    latest = categorized_df[categorized_df['Month'] == latest_month].groupby('category')['amount'].sum().abs()
    previous = categorized_df[categorized_df['Month'] == previous_month].groupby('category')['amount'].sum().abs()

    # Combine into single DataFrame
    trends = pd.DataFrame({
        'Latest_Month': latest,
        'Previous_Month': previous
    }).fillna(0)

    # Ensure numeric types
    trends['Latest_Month'] = pd.to_numeric(trends['Latest_Month'], errors='coerce')
    trends['Previous_Month'] = pd.to_numeric(trends['Previous_Month'], errors='coerce')

    trends['Change_Amount'] = trends['Latest_Month'] - trends['Previous_Month']
    
    # Handle division by zero and ensure numeric types
    trends['Change_Percent'] = trends['Change_Amount'] / trends['Previous_Month'].replace(0, np.nan) * 100
    trends['Change_Percent'] = trends['Change_Percent'].round(1)
    trends['Change_Percent'] = trends['Change_Percent'].replace([np.inf, -np.inf, np.nan], 0)

    # Add trend indicator
    trends['Trend'] = trends['Change_Percent'].apply(
        lambda x: '📈 Growing' if x > 10 else ('📉 Declining' if x < -10 else '➡️ Stable')
    )

    return trends.reset_index().sort_values('Latest_Month', ascending=False).round(2)


