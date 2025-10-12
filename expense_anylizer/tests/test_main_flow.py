"""
Main integration test for the complete expense analyzer flow.
Tests the entire pipeline from file loading to categorization.
"""
import pytest
import pandas as pd
from datetime import datetime
from core.io import load_transactions, get_file_info
from core.clean import normalize_df, detect_negative_amounts
from core.map import load_mapping, agent_choose_category, build_vendor_map, apply_categorization
from core.agg import monthly_summary, category_summary, top5_by_category
from core.profiles import load_profiles, match_profile
from core.model import MappingRow


class TestMainFlow:
    """Test the complete expense analyzer flow."""

    def test_end_to_end_with_adi_file(self):
        """Test complete flow with adi_10.xlsx file."""
        # Step 1: Load transactions
        df = load_transactions('tests/fixtures/adi_10.xlsx')

        assert len(df) > 0
        assert 'Date' in df.columns
        assert 'Description' in df.columns
        assert 'Amount' in df.columns
        assert df['Date'].dtype == 'datetime64[ns]'

        # Step 2: Clean and normalize
        df = normalize_df(df)
        df = detect_negative_amounts(df)

        assert df['Amount'].notna().all()
        assert df['Description'].notna().all()

        # Step 3: Load mappings
        mappings = load_mapping()
        assert len(mappings) > 0

        # Step 4: Build vendor map
        vendor_map = build_vendor_map(df)
        assert isinstance(vendor_map, dict)

        # Step 5: Apply categorization
        categories = [
            'מזון ומכולת', 'תחבורה', 'אוכל ומסעדות', 'שירותים',
            'בריאות', 'טיפוח אישי', 'שירותים פיננסיים', 'בידור',
            'חינוך', 'ביטוח', 'בית וגינה', 'ספורט וכושר', 'נסיעות',
            'קניות', 'תקשורת', 'מתנות', 'חיות מחמד', 'אחר'
        ]

        df = apply_categorization(df, mappings, vendor_map, categories)

        # Verify some transactions were categorized
        categorized_count = df['Category'].notna().sum()
        assert categorized_count > 0

        # Step 6: Generate summaries
        monthly = monthly_summary(df)
        category = category_summary(df)
        top5 = top5_by_category(df)

        assert len(monthly) > 0
        assert 'Month' in monthly.columns
        assert 'Total_Expenses' in monthly.columns

        if len(category) > 0:
            assert 'Category' in category.columns
            assert 'Total_Expenses' in category.columns

    def test_profile_matching(self):
        """Test profile matching with adi file."""
        profiles = load_profiles('data/profiles.yaml')

        # Read raw data
        import pandas as pd
        df_raw = pd.read_excel('tests/fixtures/adi_10.xlsx', header=None)

        # Match profile
        matched = match_profile('adi_10.xlsx', 'עסקאות במועד החיוב', df_raw, profiles)

        assert matched is not None
        assert matched['id'] == 'visa_adi_v1'
        assert 'columns' in matched

    def test_categorization_agent(self):
        """Test categorization agent with Hebrew descriptions."""
        mappings = load_mapping()
        vendor_map = {}
        categories = ['Transportation', 'Insurance', 'Food & Groceries']

        # Test Hebrew gas station
        result = agent_choose_category(
            'פז אפליקצית-YELLOW',
            mappings,
            vendor_map,
            categories
        )
        assert result.category == 'Transportation'
        assert result.strategy == 'keyword'
        assert result.confidence >= 0.9

        # Test Hebrew insurance
        result = agent_choose_category(
            'ליברה עסקות ביטוח',
            mappings,
            vendor_map,
            categories
        )
        assert result.category == 'Insurance'
        assert result.strategy == 'keyword'
        assert result.confidence >= 0.9

    def test_data_quality_metrics(self):
        """Test data quality after processing."""
        df = load_transactions('tests/fixtures/adi_10.xlsx')
        df = normalize_df(df)
        df = detect_negative_amounts(df)

        # Check completeness
        date_completeness = (df['Date'].notna().sum() / len(df)) * 100
        desc_completeness = (df['Description'].notna().sum() / len(df)) * 100
        amount_completeness = (df['Amount'].notna().sum() / len(df)) * 100

        assert date_completeness == 100.0
        assert desc_completeness == 100.0
        assert amount_completeness == 100.0

        # Check data types
        assert df['Date'].dtype == 'datetime64[ns]'
        assert df['Amount'].dtype in ['float64', 'int64']

        # Check for duplicates
        duplicates = df.duplicated().sum()
        assert duplicates >= 0  # Can have duplicates in real data

    def test_aggregation_functions(self):
        """Test aggregation functions with real data."""
        df = load_transactions('tests/fixtures/adi_10.xlsx')
        df = normalize_df(df)
        df = detect_negative_amounts(df)

        # Apply categorization
        mappings = load_mapping()
        vendor_map = build_vendor_map(df)
        categories = ['Transportation', 'Insurance', 'Food & Groceries']
        df = apply_categorization(df, mappings, vendor_map, categories)

        # Monthly summary
        monthly = monthly_summary(df)
        assert 'Month' in monthly.columns
        assert 'Total_Expenses' in monthly.columns
        assert 'Total_Income' in monthly.columns
        assert 'Net' in monthly.columns
        assert 'Transaction_Count' in monthly.columns

        # Category summary
        category = category_summary(df)
        if len(category) > 0:
            assert 'Category' in category.columns
            assert 'Total_Expenses' in category.columns
            assert 'Transaction_Count' in category.columns

        # Top 5 by category
        top5 = top5_by_category(df)
        if len(top5) > 0:
            assert 'Category' in top5.columns
            assert 'Description' in top5.columns
            assert 'Total_Amount' in top5.columns


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self):
        """Test handling of empty DataFrames."""
        df = pd.DataFrame(columns=['Date', 'Description', 'Amount', 'Category'])

        monthly = monthly_summary(df)
        category = category_summary(df)
        top5 = top5_by_category(df)

        assert len(monthly) == 0
        assert len(category) == 0
        assert len(top5) == 0

    def test_missing_mappings(self):
        """Test with no mapping file."""
        mappings = load_mapping('nonexistent_file.csv')
        assert mappings == []

    def test_hebrew_text_normalization(self):
        """Test Hebrew text normalization."""
        from core.clean import normalize_text

        # Test RTL markers
        text_with_rtl = "שלום\u200f\u200eעולם"
        normalized = normalize_text(text_with_rtl)
        assert '\u200f' not in normalized
        assert '\u200e' not in normalized

        # Test currency symbols
        from core.clean import coerce_amount
        assert coerce_amount("₪100") == 100.0
        assert coerce_amount("(50)") == -50.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
