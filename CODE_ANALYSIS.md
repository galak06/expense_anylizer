# Code Analysis Report

## Summary
Analysis of the expense analyzer codebase to identify unused functions, dead code, and verify data flow.

---

## Unused Functions (Can be Safely Removed)

### core/agg.py
1. **`uncategorized_summary()`** - ❌ UNUSED
   - Not imported or called anywhere
   - Purpose: Summarize uncategorized transactions
   - Recommendation: REMOVE

2. **`export_summary_stats()`** - ❌ UNUSED
   - Not imported or called anywhere
   - Purpose: Export summary statistics
   - Recommendation: REMOVE

### core/io.py
3. **`detect_encoding()`** - ❌ UNUSED
   - Not called outside core/io.py
   - Could be useful for debugging but not actively used
   - Recommendation: KEEP (utility function for future)

4. **`_is_date_column()`** - ⚠️ INTERNAL ONLY
   - Only used within core/io.py by detect_columns()
   - Recommendation: KEEP (internal helper)

5. **`_is_amount_column()`** - ⚠️ INTERNAL ONLY
   - Only used within core/io.py by detect_columns()
   - Recommendation: KEEP (internal helper)

6. **`_detect_column_by_patterns()`** - ⚠️ INTERNAL ONLY
   - Only used within core/io.py
   - Recommendation: KEEP (internal helper)

7. **`detect_columns()`** - ❌ UNUSED EXTERNALLY
   - Only defined in core/io.py
   - Never called in app or tests
   - Recommendation: REMOVE if heuristics is preferred

### core/map.py
8. **`save_mapping()`** - ❌ UNUSED
   - Not imported or called anywhere
   - Purpose: Save mapping to file
   - Recommendation: REMOVE (or keep if needed for future manual editing)

9. **`keyword_match()`** - ⚠️ INTERNAL ONLY
   - Only used within core/map.py by agent_choose_category()
   - Recommendation: KEEP (internal helper)

10. **`fuzzy_match()`** - ⚠️ INTERNAL ONLY
    - Only used within core/map.py by agent_choose_category()
    - Recommendation: KEEP (internal helper)

11. **`llm_match()`** - ⚠️ INTERNAL ONLY
    - Only used within core/map.py by agent_choose_category()
    - Recommendation: KEEP (internal helper)

### core/io_heuristics.py
12. **`first_nonempty_header()`** - ⚠️ INTERNAL ONLY
    - Only used within io_heuristics.py
    - Recommendation: KEEP (internal helper)

13. **`recover_header()`** - ⚠️ INTERNAL ONLY
    - Only used within io_heuristics.py
    - Recommendation: KEEP (internal helper)

14. **`_find_column_by_hints()`** - ⚠️ INTERNAL ONLY
    - Only used within io_heuristics.py
    - Recommendation: KEEP (internal helper)

---

## Data Flow Verification

### 1. File Upload Flow (Streamlit UI)
```
streamlit_app.py:load_uploaded_file()
    ↓
core/io.py:read_any()  # Profile matching
    ↓
core/io.py:load_transactions()  # Load data
    ↓
core/clean.py:normalize_df()  # Clean data
    ↓
core/clean.py:detect_negative_amounts()  # Fix signs
    ↓
core/service.py:import_from_file()  # Import via service
    ↓
core/database.py:save_transactions()  # Save to DB
```

**Status:** ✅ VERIFIED - All functions in use

### 2. Categorization Flow
```
streamlit_app.py:display_suggestions()
    ↓
core/map.py:build_vendor_map()
    ↓
core/map.py:agent_choose_category()
    ├→ keyword_match()  # Try exact match
    ├→ fuzzy_match()  # Try fuzzy match
    └→ llm_match()  # Try AI match
    ↓
core/service.py:apply_category()
    ↓
core/database.py:update_category()
    ↓
core/map.py:learn_from_user_feedback()  # Learn from choice
```

**Status:** ✅ VERIFIED - All functions in use

### 3. Bulk Categorization Flow
```
streamlit_app.py (batch categorize button)
    ↓
core/service.py:bulk_categorize()
    ↓
core/map.py:build_vendor_map()
    ↓
core/map.py:apply_categorization()
    ├→ agent_choose_category()
    └→ [same as categorization flow]
    ↓
core/database.py:update_category()  # Update each transaction
```

**Status:** ✅ VERIFIED - All functions in use

### 4. Display/Analytics Flow
```
streamlit_app.py:display_dashboard()
    ↓
core/service.py:get_transactions()
    ↓
core/database.py:load_transactions()
    ↓
core/agg.py:monthly_summary()  ✅ USED
core/agg.py:category_summary()  ✅ USED
core/agg.py:top5_by_category()  ✅ USED
core/agg.py:spending_trends()  ✅ USED
core/agg.py:month_over_month_comparison()  ✅ USED
core/agg.py:category_trends()  ✅ USED
```

**Status:** ✅ VERIFIED - All display functions in use

---

## Functions Currently in Use

### core/agg.py (7 of 9 functions used)
- ✅ `_ensure_month_column()` - Helper
- ✅ `monthly_summary()` - Used in dashboard
- ✅ `category_summary()` - Used in dashboard
- ✅ `top5_by_category()` - Used in vendor management
- ✅ `spending_trends()` - Used in trends tab
- ✅ `month_over_month_comparison()` - Used in trends tab
- ✅ `category_trends()` - Used in trends tab
- ❌ `uncategorized_summary()` - NOT USED
- ❌ `export_summary_stats()` - NOT USED

### core/clean.py (7 of 7 functions used)
- ✅ `normalize_text()` - Used by normalize_df()
- ✅ `_is_negative_with_parentheses()` - Used by coerce_amount()
- ✅ `_normalize_decimal_separators()` - Used by coerce_amount()
- ✅ `coerce_amount()` - Used by normalize_df()
- ✅ `normalize_df()` - Used in import flow
- ✅ `_is_expense_transaction()` - Used by detect_negative_amounts()
- ✅ `detect_negative_amounts()` - Used in import flow

### core/database.py (11 of 13 functions used)
- ✅ `__init__()` - Constructor
- ✅ `_ensure_db_directory()` - Used by __init__
- ✅ `_init_db()` - Used by __init__
- ✅ `save_transactions()` - Used in import
- ✅ `load_transactions()` - Used everywhere
- ✅ `get_all_categories()` - Used by service
- ✅ `get_all_accounts()` - Used by service
- ✅ `get_date_range()` - Used by service
- ✅ `get_transaction_count()` - Used by service
- ✅ `update_category()` - Used in categorization
- ✅ `get_statistics()` - Used by service
- ✅ `export_to_csv()` - Used by service
- ✅ `clear_all_transactions()` - Used by service

### core/io.py (3 of 9 functions used externally)
- ✅ `read_any()` - Used in file upload
- ✅ `load_transactions()` - Used in import flow
- ✅ `get_file_info()` - Used in file upload
- ⚠️ `detect_encoding()` - Internal utility
- ⚠️ `_try_read_csv_with_combinations()` - Internal helper
- ⚠️ `_is_date_column()` - Internal helper
- ⚠️ `_is_amount_column()` - Internal helper
- ⚠️ `_detect_column_by_patterns()` - Internal helper
- ❌ `detect_columns()` - NOT USED (superseded by profiles)

### core/map.py (5 of 9 functions used externally)
- ✅ `load_mapping()` - Used by service
- ✅ `agent_choose_category()` - Used in categorization
- ✅ `build_vendor_map()` - Used in categorization
- ✅ `apply_categorization()` - Used in bulk categorization
- ✅ `learn_from_user_feedback()` - Used in categorization
- ❌ `save_mapping()` - NOT USED
- ⚠️ `keyword_match()` - Internal (used by agent_choose_category)
- ⚠️ `fuzzy_match()` - Internal (used by agent_choose_category)
- ⚠️ `llm_match()` - Internal (used by agent_choose_category)

### core/profiles.py (2 of 8 functions used externally)
- ✅ `load_profiles()` - Used in UI
- ✅ `save_profile()` - Used in advanced mapping
- ⚠️ `match_profile()` - Internal (used by read_any)
- ⚠️ `get_column_hints()` - Internal
- ⚠️ `get_header_row()` - Internal
- ⚠️ `get_data_start_row()` - Internal
- ⚠️ `get_amount_rules()` - Internal
- ⚠️ `get_transforms()` - Internal

### core/service.py (10 of 16 functions used)
- ✅ `__init__()` - Constructor
- ✅ `import_from_file()` - Used in file upload
- ✅ `get_transactions()` - Used everywhere
- ✅ `apply_category()` - Used in categorization
- ✅ `bulk_categorize()` - Used in batch categorization
- ✅ `get_statistics()` - Used in sidebar
- ⚠️ `categorize_transaction()` - Available but not used in UI (could be useful)
- ⚠️ `get_monthly_summary()` - Service wrapper (UI calls agg directly)
- ⚠️ `get_category_summary()` - Service wrapper (UI calls agg directly)
- ⚠️ `get_top_vendors()` - Service wrapper (UI calls agg directly)
- ⚠️ `export_to_csv()` - Available but not used in UI
- ⚠️ `clear_all_data()` - Available but not used in UI (dangerous)
- ⚠️ `get_available_categories()` - Available but not used
- ⚠️ `get_available_accounts()` - Available but not used
- ⚠️ `get_date_range()` - Available but not used
- ⚠️ `get_transaction_count()` - Available but not used

---

## Recommendations

### HIGH PRIORITY - Remove These Functions (Dead Code)

1. **core/agg.py**
   - Remove `uncategorized_summary()` - NOT USED
   - Remove `export_summary_stats()` - NOT USED

2. **core/map.py**
   - Remove `save_mapping()` - NOT USED (unless needed for manual editing)

3. **core/io.py**
   - Remove `detect_columns()` - SUPERSEDED by profiles system

### MEDIUM PRIORITY - Consider Adding to UI

1. **core/service.py**
   - `export_to_csv()` - Could add export button to UI
   - `get_available_categories()` - Could show category list
   - `get_available_accounts()` - Could show account filter

### LOW PRIORITY - Keep for Future Use

1. **core/io.py**
   - Keep `detect_encoding()` - Useful for debugging encoding issues

2. **Internal helpers** - Keep all `_prefixed` functions as they're internal utilities

---

## Code Quality Issues Found

### 1. Duplicate Functionality
- Service layer has wrappers (`get_monthly_summary`, `get_category_summary`, etc.) that are bypassed
- UI calls `agg` functions directly instead of going through service
- **Recommendation:** Either use service wrappers or remove them

### 2. Unused Import in streamlit_app.py
- Line 227: `from core.io import read_any` is inside a function - already imported at top
- **Recommendation:** Remove duplicate import

### 3. Inconsistent Error Handling
- Some functions return dicts with 'success' key, others raise exceptions
- **Recommendation:** Standardize error handling approach

---

## Files That Are Clean

✅ **core/clean.py** - All 7 functions are actively used
✅ **core/database.py** - 11 of 13 functions actively used (2 wrapper methods)
✅ **core/config.py** - Simple config class, all in use
✅ **core/model.py** - Data models, all in use

---

## Estimated Impact of Cleanup

- **Lines to remove:** ~100-150 lines
- **Files affected:** 3 files (core/agg.py, core/map.py, core/io.py)
- **Risk level:** LOW (removing only unused code)
- **Testing required:** Run existing tests to ensure no hidden dependencies

---

## Next Steps

1. Remove unused functions from core/agg.py (2 functions)
2. Remove unused functions from core/map.py (1 function)
3. Remove unused functions from core/io.py (1 function)
4. Remove duplicate import in streamlit_app.py
5. Run tests to verify nothing breaks
6. Consider adding export and statistics features to UI
