"""
Business logic service layer between UI and database.
Handles all transaction operations and business rules.
"""
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from .database import TransactionDB
from .io import load_transactions as load_from_file
from .clean import normalize_df, detect_negative_amounts
from .map import (
    load_mapping, agent_choose_category, build_vendor_map,
    apply_categorization, learn_from_user_feedback
)
from .agg import monthly_summary, category_summary, top5_by_category


class TransactionService:
    """Service layer for transaction operations."""

    def __init__(self, db: Optional[TransactionDB] = None, user_id: Optional[int] = None):
        self.user_id = user_id
        self.db = db or TransactionDB(user_id=user_id)
        self.mappings = load_mapping()

    def import_from_file(self, file_path: str, all_expenses: bool = False, account: Optional[str] = None) -> Dict[str, Any]:
        """
        Import transactions from file, process, and save to database.

        Args:
            file_path: Path to CSV/XLSX file
            all_expenses: If True, treat all positive amounts as expenses (credit cards)
            account: Account name/identifier to tag these transactions with

        Returns:
            Dict with import results including duplicate detection and upload session info
        """
        import os

        # Create upload session
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
        upload_id = self.create_upload_session(filename, file_size, account)

        try:
            # Load and process
            df = load_from_file(file_path)
            df = normalize_df(df)
            df = detect_negative_amounts(df, all_expenses=all_expenses)

            # Add account column if provided
            if account:
                df['Account'] = account

            # Save to database with duplicate detection and upload tracking
            save_result = self.db.save_transactions(df, upload_id=upload_id)

            # Update upload session with final count
            self.update_upload_session(upload_id, save_result['inserted'])

            return {
                'success': True,
                'upload_id': upload_id,
                'filename': filename,
                'total_rows': save_result['total'],
                'inserted': save_result['inserted'],
                'duplicates': save_result['duplicates'],
                'invalid_dates': save_result['invalid_dates'],
                'skipped_rows': save_result.get('skipped_rows', []),  # Include skipped rows for review
                'date_range': {
                    'start': df['Date'].min().strftime('%Y-%m-%d') if not df.empty else None,
                    'end': df['Date'].max().strftime('%Y-%m-%d') if not df.empty else None
                }
            }
        except Exception as e:
            # If import fails, clean up the upload session
            try:
                self.delete_upload_session(upload_id)
            except:
                pass  # Don't fail on cleanup
            raise e

    def get_transactions(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        account: Optional[str] = None,
        description: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        only_uncategorized: bool = False,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get transactions with filtering.

        Args:
            start_date: Filter start date (YYYY-MM-DD)
            end_date: Filter end date (YYYY-MM-DD)
            category: Filter by category
            account: Filter by account
            description: Search in description
            min_amount: Minimum amount
            max_amount: Maximum amount
            only_uncategorized: Only uncategorized transactions
            limit: Limit results

        Returns:
            Filtered DataFrame
        """
        # Load from database
        df = self.db.load_transactions(
            start_date=start_date,
            end_date=end_date,
            category=category,
            account=account,
            limit=limit
        )

        if df.empty:
            return df

        # Apply additional filters
        if only_uncategorized:
            df = df[df['Category'].isna()]

        if description:
            df = df[df['Description'].str.contains(description, case=False, na=False)]

        if min_amount is not None:
            df = df[df['Amount'] >= min_amount]

        if max_amount is not None:
            df = df[df['Amount'] <= max_amount]

        return df

    def categorize_transaction(
        self,
        description: str,
        transaction_date: str,
        categories: List[str],
        llm_api_key: Optional[str] = None,
        fuzzy_threshold: Optional[int] = None,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Suggest category for a single transaction.

        Args:
            description: Transaction description
            transaction_date: Transaction date
            categories: Available categories
            llm_api_key: OpenAI API key
            fuzzy_threshold: Fuzzy match threshold
            amount: Transaction amount for context

        Returns:
            Dict with suggestion details
        """
        # Load existing transactions for vendor map
        df = self.db.load_transactions()
        vendor_map = build_vendor_map(df)

        # Get category suggestion with enhanced context
        result = agent_choose_category(
            description,
            self.mappings,
            vendor_map,
            categories,
            llm_api_key,
            fuzzy_threshold,
            amount,
            transaction_date
        )

        return {
            'category': result.category,
            'confidence': result.confidence,
            'strategy': result.strategy,
            'note': result.note
        }

    def apply_category(
        self,
        description: str,
        transaction_date: str,
        category: str,
        learn: bool = True
    ) -> bool:
        """
        Apply category to transaction and optionally learn from it.

        Args:
            description: Transaction description
            transaction_date: Transaction date (YYYY-MM-DD)
            category: Category to apply
            learn: Whether to learn from this feedback

        Returns:
            Success status
        """
        # Update in database
        updated = self.db.update_category(description, transaction_date, category)

        if updated > 0 and learn:
            # Learn from feedback
            df = self.db.load_transactions()
            vendor_map = build_vendor_map(df)

            self.mappings, vendor_map = learn_from_user_feedback(
                description,
                category,
                self.mappings,
                vendor_map
            )

        return updated > 0

    def bulk_apply_category(
        self,
        description: str,
        category: str,
        learn: bool = True
    ) -> int:
        """
        Apply category to all transactions matching description.

        Args:
            description: Transaction description to match
            category: Category to apply
            learn: Whether to learn from this feedback

        Returns:
            Number of transactions updated
        """
        # Update in database
        updated = self.db.bulk_update_category(description, category)

        if updated > 0 and learn:
            # Learn from feedback
            df = self.db.load_transactions()
            vendor_map = build_vendor_map(df)

            self.mappings, vendor_map = learn_from_user_feedback(
                description,
                category,
                self.mappings,
                vendor_map
            )

        return updated

    def bulk_categorize(
        self,
        categories: List[str],
        llm_api_key: Optional[str] = None,
        fuzzy_threshold: Optional[int] = None,
        only_uncategorized: bool = True
    ) -> Dict[str, Any]:
        """
        Apply categorization to multiple transactions.

        Args:
            categories: Available categories
            llm_api_key: OpenAI API key
            fuzzy_threshold: Fuzzy match threshold
            only_uncategorized: Only categorize uncategorized transactions

        Returns:
            Dict with results
        """
        # Load transactions
        df = self.db.load_transactions()

        if df.empty:
            return {'success': False, 'message': 'No transactions found'}

        # Build vendor map
        vendor_map = build_vendor_map(df)

        # Apply categorization with enhanced context
        df_categorized = apply_categorization(
            df,
            self.mappings,
            vendor_map,
            categories,
            llm_api_key,
            fuzzy_threshold,
            only_uncategorized
        )

        # Update database for categorized transactions
        updated_count = 0
        for _, row in df_categorized.iterrows():
            if pd.notna(row['Category']):
                date_str = row['Date'].strftime('%Y-%m-%d')
                if self.db.update_category(row['Description'], date_str, row['Category']):
                    updated_count += 1

        return {
            'success': True,
            'total_processed': len(df_categorized),
            'updated_count': updated_count
        }

    def get_monthly_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Get monthly summary statistics."""
        df = self.db.load_transactions(start_date=start_date, end_date=end_date)
        return monthly_summary(df)

    def get_category_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Get category summary statistics."""
        df = self.db.load_transactions(start_date=start_date, end_date=end_date)
        return category_summary(df)

    def get_top_vendors(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Get top vendors by category."""
        df = self.db.load_transactions(start_date=start_date, end_date=end_date)
        return top5_by_category(df)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics.

        Returns:
            Dict with various statistics
        """
        db_stats = self.db.get_statistics()

        # Add calculated metrics
        if db_stats['total_transactions'] > 0:
            categorization_rate = (
                db_stats['categorized_count'] / db_stats['total_transactions'] * 100
            )
        else:
            categorization_rate = 0

        return {
            'total_transactions': db_stats['total_transactions'],
            'categorized': db_stats['categorized_count'],
            'uncategorized': db_stats['total_transactions'] - db_stats['categorized_count'],
            'categorization_rate': round(categorization_rate, 1),
            'date_range': {
                'start': db_stats['min_date'],
                'end': db_stats['max_date']
            },
            'total_amount': db_stats['total_amount'],
            'top_categories': db_stats['top_categories']
        }

    def export_to_csv(self, output_path: str) -> int:
        """
        Export all transactions to CSV.

        Args:
            output_path: Output file path

        Returns:
            Number of rows exported
        """
        return self.db.export_to_csv(output_path)

    def force_insert_transaction(self, df: pd.DataFrame) -> int:
        """
        Force insert transactions bypassing duplicate check.
        Use with caution - this should only be used for restoring duplicates.
        
        Args:
            df: DataFrame with transactions to insert
            
        Returns:
            Number of rows inserted
        """
        return self.db.force_insert_transaction(df)

    def clear_all_data(self) -> int:
        """
        Clear all transactions from database. Use with caution!

        Returns:
            Number of transactions deleted
        """
        return self.db.clear_all_transactions()

    def delete_by_account(self, account: str) -> int:
        """
        Delete all transactions for a specific account.
        
        Args:
            account: Account name to delete transactions for
            
        Returns:
            Number of transactions deleted
        """
        return self.db.delete_transactions_by_account(account)

    def create_upload_session(self, filename: str, file_size: int = None, account: str = None) -> str:
        """
        Create a new upload session.
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes
            account: Account name if known
            
        Returns:
            Upload session ID
        """
        return self.db.create_upload_session(filename, file_size, account)

    def update_upload_session(self, upload_id: str, transactions_count: int):
        """
        Update upload session with final transaction count.
        
        Args:
            upload_id: Upload session ID
            transactions_count: Number of transactions imported
        """
        self.db.update_upload_session(upload_id, transactions_count)

    def get_upload_sessions(self) -> List[dict]:
        """
        Get all upload sessions for the current user.
        
        Returns:
            List of upload session dictionaries
        """
        return self.db.get_upload_sessions()

    def delete_upload_session(self, upload_id: str) -> int:
        """
        Delete all transactions from a specific upload session.
        
        Args:
            upload_id: Upload session ID to delete
            
        Returns:
            Number of transactions deleted
        """
        return self.db.delete_upload_session(upload_id)

    def get_available_categories(self) -> List[str]:
        """Get list of categories used in database."""
        return self.db.get_all_categories()

    def generate_ai_analysis(self) -> dict:
        """Generate AI insights per account for current user's transactions."""
        df = self.get_transactions()
        if df.empty:
            raise ValueError("No transactions to analyze")
        
        # Get settings for API key
        from core.config import get_settings
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Import and call the AI analysis function
        from core.ai_analysis import generate_ai_insights
        return generate_ai_insights(df, settings.openai_api_key)

    def estimate_ai_analysis_cost(self) -> float:
        """Estimate the cost of AI analysis in USD."""
        df = self.get_transactions()
        if df.empty:
            return 0.0
        
        from core.ai_analysis import _prepare_analysis_data, estimate_analysis_cost
        analysis_data = _prepare_analysis_data(df)
        return estimate_analysis_cost(analysis_data)

    def get_available_accounts(self) -> List[str]:
        """Get list of accounts used in database."""
        return self.db.get_all_accounts()

    def get_date_range(self) -> tuple:
        """Get min and max dates from database."""
        return self.db.get_date_range()

    def get_transaction_count(self) -> int:
        """Get total number of transactions."""
        return self.db.get_transaction_count()
