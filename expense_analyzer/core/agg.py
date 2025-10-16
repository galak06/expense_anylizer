import pandas as pd
from typing import Dict, Any
import numpy as np


SUMMARY_COLUMNS = ['Month', 'Total_Expenses', 'Total_Income', 'Net', 'Transaction_Count']
CATEGORY_COLUMNS = ['Category', 'Total_Expenses', 'Total_Income', 'Transaction_Count', 'Avg_Amount']


def _ensure_month_column(df: pd.DataFrame) -> pd.DataFrame:
    if 'Month' not in df.columns and 'Date' in df.columns:
        df = df.copy()
        df['Month'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m')
    return df


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    df = _ensure_month_column(df)

    monthly = pd.DataFrame({
        'Total_Expenses': df[df['Amount'] < 0].groupby('Month')['Amount'].sum().abs(),
        'Total_Income': df[df['Amount'] > 0].groupby('Month')['Amount'].sum(),
        'Net': df.groupby('Month')['Amount'].sum(),
        'Transaction_Count': df.groupby('Month')['Amount'].count()
    }).fillna(0).round(2).reset_index().sort_values('Month')

    return monthly[SUMMARY_COLUMNS]


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or df['Category'].notna().sum() == 0:
        return pd.DataFrame(columns=CATEGORY_COLUMNS)

    categorized_df = df[df['Category'].notna()]

    # Separate expenses and income BEFORE aggregating
    expenses_df = categorized_df[categorized_df['Amount'] < 0]
    income_df = categorized_df[categorized_df['Amount'] > 0]

    # Calculate expenses (sum of negative amounts, converted to positive)
    expenses_by_category = expenses_df.groupby('Category')['Amount'].sum().abs()

    # Calculate income (sum of positive amounts)
    income_by_category = income_df.groupby('Category')['Amount'].sum()

    # Calculate transaction counts and averages
    counts_by_category = categorized_df.groupby('Category')['Amount'].count()
    avg_by_category = categorized_df.groupby('Category')['Amount'].mean()

    # Combine into summary DataFrame
    summary = pd.DataFrame({
        'Total_Expenses': expenses_by_category,
        'Total_Income': income_by_category,
        'Transaction_Count': counts_by_category,
        'Avg_Amount': avg_by_category
    }).fillna(0).round(2)

    return summary.reset_index().sort_values('Total_Expenses', ascending=False)[CATEGORY_COLUMNS]


TOP5_COLUMNS = ['Category', 'Description', 'Total_Amount', 'Transaction_Count']


def top5_by_category(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or df['Category'].notna().sum() == 0:
        return pd.DataFrame(columns=TOP5_COLUMNS)

    categorized_df = df[df['Category'].notna()]

    vendor_summary = categorized_df.groupby(['Category', 'Description']).agg({
        'Amount': ['sum', 'count']
    }).round(2)

    vendor_summary.columns = ['Total_Amount', 'Transaction_Count']
    vendor_summary = vendor_summary.reset_index()

    top5_results = [
        vendor_summary[vendor_summary['Category'] == category]
        .sort_values('Total_Amount', key=abs, ascending=False)
        .head(5)
        for category in vendor_summary['Category'].unique()
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
        return pd.DataFrame(columns=['Month', 'Category', 'Amount'])

    df = _ensure_month_column(df)

    unique_months = sorted(df['Month'].unique())
    if len(unique_months) > months:
        recent_months = unique_months[-months:]
        df = df[df['Month'].isin(recent_months)]

    trends = df.groupby(['Month', 'Category']).agg({'Amount': 'sum'}).round(2)
    trends['Amount'] = trends['Amount'].abs()

    return trends.reset_index().pivot(index='Month', columns='Category', values='Amount').fillna(0)


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
    monthly = df[df['Amount'] < 0].groupby('Month')['Amount'].sum().abs().reset_index()
    monthly.columns = ['Month', 'Spending']
    monthly = monthly.sort_values('Month')

    # Calculate changes
    monthly['Previous_Spending'] = monthly['Spending'].shift(1)
    monthly['Change_Amount'] = monthly['Spending'] - monthly['Previous_Spending']
    monthly['Change_Percent'] = ((monthly['Spending'] - monthly['Previous_Spending']) / monthly['Previous_Spending'] * 100).round(1)

    # Rename columns for clarity
    monthly = monthly.rename(columns={'Spending': 'Current_Spending'})

    return monthly[['Month', 'Current_Spending', 'Previous_Spending', 'Change_Amount', 'Change_Percent']].round(2)


def category_trends(df: pd.DataFrame) -> pd.DataFrame:
    """
    Show spending trends by category with month-over-month changes.

    Returns:
        DataFrame with categories and their spending trends
    """
    if df.empty or df['Category'].notna().sum() == 0:
        return pd.DataFrame(columns=['Category', 'Latest_Month', 'Previous_Month', 'Change_Percent', 'Trend'])

    df = _ensure_month_column(df)
    categorized_df = df[df['Category'].notna()]

    # Get latest two months
    unique_months = sorted(categorized_df['Month'].unique())
    if len(unique_months) < 2:
        return pd.DataFrame(columns=['Category', 'Latest_Month', 'Previous_Month', 'Change_Percent', 'Trend'])

    latest_month = unique_months[-1]
    previous_month = unique_months[-2]

    # Calculate spending by category for each month
    latest = categorized_df[categorized_df['Month'] == latest_month].groupby('Category')['Amount'].sum().abs()
    previous = categorized_df[categorized_df['Month'] == previous_month].groupby('Category')['Amount'].sum().abs()

    # Combine into single DataFrame
    trends = pd.DataFrame({
        'Latest_Month': latest,
        'Previous_Month': previous
    }).fillna(0)

    trends['Change_Amount'] = trends['Latest_Month'] - trends['Previous_Month']
    trends['Change_Percent'] = ((trends['Latest_Month'] - trends['Previous_Month']) / trends['Previous_Month'] * 100).round(1)
    trends['Change_Percent'] = trends['Change_Percent'].replace([np.inf, -np.inf], 0)

    # Add trend indicator
    trends['Trend'] = trends['Change_Percent'].apply(
        lambda x: '📈 Growing' if x > 10 else ('📉 Declining' if x < -10 else '➡️ Stable')
    )

    return trends.reset_index().sort_values('Latest_Month', ascending=False).round(2)


