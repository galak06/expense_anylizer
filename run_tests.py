#!/usr/bin/env python3
"""
Test runner script for Curser expense analyzer.
"""
import sys
import subprocess
import os

def run_tests():
    """Run all unit tests."""
    print("🧪 Running Curser unit tests...")
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    try:
        # Run pytest
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short",
            "--color=yes"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False
    
    return True

def test_imports():
    """Test that all modules can be imported."""
    print("📦 Testing module imports...")
    
    try:
        from core.io import load_transactions, detect_columns
        from core.clean import normalize_text, coerce_amount
        from core.map import keyword_match, fuzzy_match
        from core.agg import monthly_summary, category_summary
        from core.model import Transaction, MatchResult
        print("✅ All core modules imported successfully!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_sample_data():
    """Test with sample data."""
    print("📊 Testing with sample data...")
    
    try:
        from core.io import load_transactions
        from core.clean import normalize_df
        from core.map import load_mapping
        
        # Test loading sample data
        sample_file = "tests/fixtures/sample_bank_export.csv"
        if os.path.exists(sample_file):
            df = load_transactions(sample_file)
            df = normalize_df(df)
            
            print(f"✅ Loaded {len(df)} transactions from sample file")
            print(f"   Columns: {list(df.columns)}")
            print(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")
            print(f"   Amount range: {df['Amount'].min()} to {df['Amount'].max()}")
            
            # Test mapping loading
            mappings = load_mapping()
            print(f"✅ Loaded {len(mappings)} keyword mappings")
            
            return True
        else:
            print("⚠️ Sample data file not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing sample data: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Curser Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test imports
    success &= test_imports()
    print()
    
    # Test sample data
    success &= test_sample_data()
    print()
    
    # Run unit tests
    success &= run_tests()
    
    print("=" * 50)
    if success:
        print("🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)
