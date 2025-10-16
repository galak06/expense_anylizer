import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.io import load_transactions, get_file_info, read_any
from core.clean import normalize_df, detect_negative_amounts
from core.map import (
    load_mapping, agent_choose_category,
    build_vendor_map, learn_from_user_feedback
)
from core.agg import (
    monthly_summary, category_summary, top5_by_category,
    month_over_month_comparison, category_trends, spending_trends
)
from core.config import get_settings
from core.profiles import save_profile, load_profiles
from core.service import TransactionService
from core.validation import validate_transaction, validate_file_upload, validate_search_query, sanitize_input
from auth_ui import require_auth, render_user_menu, render_change_password_modal, get_current_user_id

DEFAULT_CATEGORIES = [
    "מזון ומכולת", "תחבורה", "אוכל ומסעדות", "שירותים",
    "בריאות", "טיפוח אישי", "שירותים פיננסיים", "בידור",
    "חינוך", "ביטוח", "בית וגינה", "ספורט וכושר", "נסיעות",
    "קניות", "תקשורת", "מתנות", "חיות מחמד", "אחר"
]

# Category icons and colors
CATEGORY_CONFIG = {
    "מזון ומכולת": {"icon": "🛒", "color": "#4CAF50"},
    "תחבורה": {"icon": "🚗", "color": "#2196F3"},
    "אוכל ומסעדות": {"icon": "🍽️", "color": "#FF9800"},
    "שירותים": {"icon": "🔧", "color": "#9C27B0"},
    "בריאות": {"icon": "⚕️", "color": "#F44336"},
    "טיפוח אישי": {"icon": "💇", "color": "#E91E63"},
    "שירותים פיננסיים": {"icon": "🏦", "color": "#3F51B5"},
    "בידור": {"icon": "🎬", "color": "#FF5722"},
    "חינוך": {"icon": "📚", "color": "#00BCD4"},
    "ביטוח": {"icon": "🛡️", "color": "#607D8B"},
    "בית וגינה": {"icon": "🏡", "color": "#8BC34A"},
    "ספורט וכושר": {"icon": "⚽", "color": "#CDDC39"},
    "נסיעות": {"icon": "✈️", "color": "#009688"},
    "קניות": {"icon": "🛍️", "color": "#FFC107"},
    "תקשורת": {"icon": "📱", "color": "#673AB7"},
    "מתנות": {"icon": "🎁", "color": "#FF4081"},
    "חיות מחמד": {"icon": "🐾", "color": "#795548"},
    "אחר": {"icon": "📌", "color": "#9E9E9E"}
}

settings = get_settings()

CUSTOM_CSS = """
<style>
    /* Override Bootstrap CSS from cookie manager */
    .stApp, .stApp * {
        box-sizing: border-box !important;
    }

    /* Global app styling for dark theme */
    .stApp {
        background-color: #0a0a0a !important;
        color: #ffffff !important;
    }

    .main .block-container {
        background-color: transparent !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        color: #ffffff !important;
    }

    /* Dark theme for all text elements */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
        color: #ffffff !important;
    }

    .stApp p, .stApp div, .stApp span {
        color: #ffffff !important;
    }

    /* Modern Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        background: #1a1a1a !important;
        border-radius: 12px !important;
        padding: 4px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        border: 1px solid #333333 !important;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        margin: 0 2px !important;
        transition: all 0.3s ease !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        color: #ffffff !important;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
        transform: translateY(-1px) !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(102, 126, 234, 0.2) !important;
        transform: translateY(-1px) !important;
        color: #ffffff !important;
    }

    /* Floating Action Button */
    .fab {
        position: fixed !important;
        bottom: 20px !important;
        right: 20px !important;
        width: 56px !important;
        height: 56px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4) !important;
        cursor: pointer !important;
        z-index: 1000 !important;
        transition: all 0.3s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 24px !important;
    }

    .fab:hover {
        transform: scale(1.1) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6) !important;
    }

    /* Card-based layouts */
    .card {
        background: #1a1a1a !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        margin-bottom: 1rem !important;
        transition: all 0.3s ease !important;
        border: 1px solid #333333 !important;
        color: #ffffff !important;
    }

    .card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.5) !important;
        transform: translateY(-2px) !important;
        border-color: #444444 !important;
    }

    /* Main header with modern styling */
    .main-header {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-align: center !important;
        margin-bottom: 2rem !important;
        letter-spacing: -0.02em !important;
    }

    /* Enhanced metrics */
    .big-metric {
        font-size: 3rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        text-align: center !important;
        margin: 1rem 0 !important;
        letter-spacing: -0.02em !important;
    }
    .big-metric-label {
        font-size: 1.2rem !important;
        color: #6b7280 !important;
        text-align: center !important;
        margin-bottom: 0.5rem !important;
        font-weight: 500 !important;
    }

    /* Enhanced category badges */
    .category-badge {
        display: inline-block !important;
        padding: 0.4rem 1rem !important;
        border-radius: 20px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        margin: 0.2rem !important;
        transition: all 0.2s ease !important;
    }
    .category-badge:hover {
        transform: scale(1.05) !important;
    }

    /* Quick action buttons with modern styling */
    .quick-action {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        padding: 1rem 1.5rem !important;
        border-radius: 12px !important;
        text-align: center !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
    }
    .quick-action:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4) !important;
    }

    /* Enhanced empty state */
    .empty-state {
        text-align: center !important;
        padding: 4rem 2rem !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-radius: 20px !important;
        margin: 2rem 0 !important;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3) !important;
    }
    .empty-state h2 {
        font-size: 2.5rem !important;
        margin-bottom: 1rem !important;
        color: white !important;
        font-weight: 700 !important;
    }
    .empty-state p {
        font-size: 1.2rem !important;
        opacity: 0.9 !important;
        color: white !important;
        line-height: 1.6 !important;
    }

    /* Enhanced search container */
    .search-container {
        background: #1a1a1a !important;
        padding: 1.5rem !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3) !important;
        margin-bottom: 2rem !important;
        border: 1px solid #333333 !important;
        color: #ffffff !important;
    }

    /* Loading states */
    .loading-skeleton {
        background: linear-gradient(90deg, #333333 25%, #444444 50%, #333333 75%) !important;
        background-size: 200% 100% !important;
        animation: loading 1.5s infinite !important;
        border-radius: 8px !important;
        height: 20px !important;
        margin: 0.5rem 0 !important;
    }

    @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* Confidence indicators */
    .confidence-high { 
        color: #10b981 !important; 
        font-weight: 600 !important; 
        background: rgba(16, 185, 129, 0.1) !important;
        padding: 0.2rem 0.5rem !important;
        border-radius: 6px !important;
    }
    .confidence-medium { 
        color: #f59e0b !important; 
        font-weight: 600 !important; 
        background: rgba(245, 158, 11, 0.1) !important;
        padding: 0.2rem 0.5rem !important;
        border-radius: 6px !important;
    }
    .confidence-low { 
        color: #ef4444 !important; 
        font-weight: 600 !important; 
        background: rgba(239, 68, 68, 0.1) !important;
        padding: 0.2rem 0.5rem !important;
        border-radius: 6px !important;
    }

    /* Keyboard shortcuts help */
    .shortcuts-help {
        position: fixed !important;
        bottom: 20px !important;
        right: 20px !important;
        background: rgba(0,0,0,0.9) !important;
        color: white !important;
        padding: 1.5rem !important;
        border-radius: 12px !important;
        font-size: 0.9rem !important;
        z-index: 1000 !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    .shortcut-key {
        background: rgba(255,255,255,0.2) !important;
        padding: 0.3rem 0.6rem !important;
        border-radius: 6px !important;
        font-family: 'SF Mono', Monaco, monospace !important;
        margin: 0 0.3rem !important;
        color: white !important;
        font-weight: 600 !important;
    }

    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab"] {
            padding: 8px 16px !important;
            font-size: 13px !important;
            min-height: 40px !important;
        }
        
        .main-header {
            font-size: 2rem !important;
        }
        
        .big-metric {
            font-size: 2.5rem !important;
        }
        
        .fab {
            width: 48px !important;
            height: 48px !important;
            bottom: 16px !important;
            right: 16px !important;
        }
    }

    /* Improved typography */
    h1, h2, h3, h4, h5, h6 {
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
    }

    /* Better spacing */
    .stContainer {
        padding: 1rem !important;
    }

    /* Sidebar styling for dark theme */
    .css-1d391kg {
        background-color: #1a1a1a !important;
        border-right: 1px solid #333333 !important;
        color: #ffffff !important;
    }

    /* Ensure consistent dark backgrounds for all containers */
    .stSidebar {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
    }

    /* Sidebar text styling */
    .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar h4, .stSidebar h5, .stSidebar h6 {
        color: #ffffff !important;
    }

    .stSidebar p, .stSidebar div, .stSidebar span {
        color: #ffffff !important;
    }

    /* Enhanced buttons */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px) !important;
    }

    /* Dark theme for Streamlit components */
    .stSelectbox > div > div {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    .stTextInput > div > div > input {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    .stTextArea > div > div > textarea {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    .stNumberInput > div > div > input {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    .stDateInput > div > div > input {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    /* Dark theme for expanders */
    .streamlit-expanderHeader {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 1px solid #333333 !important;
    }

    .streamlit-expanderContent {
        background-color: #0a0a0a !important;
        color: #ffffff !important;
    }
</style>
"""

st.set_page_config(
    page_title="Expense Analyzer",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Require authentication before anything else
require_auth()

# Get current user ID
current_user_id = get_current_user_id()

# Initialize service with user_id after authentication
if 'service' not in st.session_state or st.session_state.service.user_id != current_user_id:
    st.session_state.service = TransactionService(user_id=current_user_id)

# Load existing transactions from database on startup
if 'transactions_df' not in st.session_state:
    try:
        # Try to load from database
        db_df = st.session_state.service.get_transactions()
        st.session_state.transactions_df = db_df
        if not db_df.empty:
            st.session_state.db_loaded = True
    except Exception:
        # If database is empty or error, start with empty DataFrame
        st.session_state.transactions_df = pd.DataFrame()
        st.session_state.db_loaded = False

if 'mappings' not in st.session_state:
    st.session_state.mappings = load_mapping()
if 'vendor_map' not in st.session_state:
    st.session_state.vendor_map = {}
if 'raw_df' not in st.session_state:
    st.session_state.raw_df = pd.DataFrame()
if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = ""
if 'skipped_duplicates' not in st.session_state:
    st.session_state.skipped_duplicates = []


def get_confidence_color(confidence: float) -> str:
    if confidence >= 0.9:
        return "confidence-high"
    if confidence >= 0.75:
        return "confidence-medium"
    return "confidence-low"


def get_category_icon(category: str) -> str:
    """Get icon for a category."""
    return CATEGORY_CONFIG.get(category, {}).get("icon", "📌")


def get_category_color(category: str) -> str:
    """Get color for a category."""
    return CATEGORY_CONFIG.get(category, {}).get("color", "#9E9E9E")


def format_category_badge(category: str) -> str:
    """Format category with icon and color badge."""
    if not category:
        return ""
    icon = get_category_icon(category)
    color = get_category_color(category)
    return f'<span class="category-badge" style="background-color: {color}20; color: {color}; border: 2px solid {color};">{icon} {category}</span>'


def load_uploaded_file(uploaded_file):
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        # Store raw dataframe for advanced mapping
        raw_df, matched_profile = read_any(temp_path)
        st.session_state.raw_df = raw_df
        st.session_state.uploaded_filename = uploaded_file.name

        # Load and process transactions
        df = load_transactions(temp_path)
        df = normalize_df(df)

        # Detect if this is a credit card file (all amounts are expenses)
        # Check filename OR profile match for credit cards
        profile_id = matched_profile.get('id', '') if isinstance(matched_profile, dict) else (matched_profile or '')
        is_credit_card = (
            'visa' in uploaded_file.name.lower() or
            'adi' in uploaded_file.name.lower() or
            'gil' in uploaded_file.name.lower() or
            'visa' in profile_id.lower()
        )
        df = detect_negative_amounts(df, all_expenses=is_credit_card)

        # Calculate file total BEFORE saving (for verification)
        # Since expenses are negative, we take absolute value of the sum of negative amounts
        file_expenses = abs(df[df['Amount'] < 0]['Amount'].sum())
        file_income = df[df['Amount'] > 0]['Amount'].sum()
        file_transaction_count = len(df)

        st.session_state.transactions_df = df

        # Save to database via service layer
        result = st.session_state.service.import_from_file(
            temp_path,
            all_expenses=is_credit_card
        )

        # Store skipped duplicates for review
        if 'skipped_rows' in result and result['skipped_rows']:
            st.session_state.skipped_duplicates.extend(result['skipped_rows'])

        # Reload from database to ensure UI is synced with DB
        st.session_state.transactions_df = st.session_state.service.get_transactions()

        # Display detailed statistics with file total verification
        msg = f"✅ Loaded {result['total_rows']} transactions"
        if result['inserted'] > 0:
            msg += f" | 💾 Saved {result['inserted']} new"
        if result['duplicates'] > 0:
            msg += f" | ⚠️ Skipped {result['duplicates']} duplicates"
        if result['invalid_dates'] > 0:
            msg += f" | ❌ Dropped {result['invalid_dates']} invalid dates"

        st.success(msg)

        # Show file total for verification
        if file_income > 0:
            st.info(f"📊 **File Total (for verification):** Expenses: ₪{file_expenses:,.2f} | Income: ₪{file_income:,.2f} ({file_transaction_count} transactions)")
        else:
            st.info(f"📊 **File Total (for verification):** ₪{file_expenses:,.2f} ({file_transaction_count} expense transactions)")

        # Calculate and show cumulative database total (expenses only)
        db_df_after = st.session_state.service.get_transactions()
        if not db_df_after.empty:
            cumulative_expenses = abs(db_df_after[db_df_after['Amount'] < 0]['Amount'].sum())
            cumulative_income = db_df_after[db_df_after['Amount'] > 0]['Amount'].sum()
            cumulative_count = len(db_df_after)
            st.success(f"💰 **Cumulative Database Total - Expenses:** ₪{cumulative_expenses:,.2f} | Income: ₪{cumulative_income:,.2f} | Net: ₪{db_df_after['Amount'].sum():,.2f} ({cumulative_count} transactions)")

        file_info = get_file_info(temp_path)
        st.json({
            "Total Rows": file_info.get('total_rows', 0),
            "Detected Columns": file_info.get('detected_columns', {})
        })

        # Clear filtered_df to force refresh with new data
        if 'filtered_df' in st.session_state:
            del st.session_state.filtered_df

        # Auto-categorize if enabled - mark for processing after rerun
        if st.session_state.get('auto_categorize', False):
            # Write flag file that persists across browser refreshes
            flag_file = 'data/.pending_categorization'
            os.makedirs('data', exist_ok=True)
            with open(flag_file, 'w') as f:
                f.write('pending')

        # Auto-refresh the page to show updated data
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error loading file: {str(e)}")
        st.info("💡 Try using Advanced Mapping below to manually specify columns")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def display_advanced_mapping():
    """Display Advanced Mapping UI for manual column selection and profile saving."""
    if st.session_state.raw_df.empty:
        return

    with st.expander("⚙️ Advanced Mapping", expanded=False):
        st.write("Manually configure column mappings and save as a reusable profile.")

        raw_df = st.session_state.raw_df
        columns = list(raw_df.columns)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Column Mapping")
            date_col = st.selectbox("Date Column", options=[""] + columns, key="adv_date_col")
            desc_col = st.selectbox("Description Column", options=[""] + columns, key="adv_desc_col")
            amount_col = st.selectbox("Amount Column", options=[""] + columns, key="adv_amount_col")

        with col2:
            st.subheader("Profile Settings")
            profile_id = st.text_input("Profile ID", value="", placeholder="e.g., my_bank_v1", key="adv_profile_id")
            filename_regex = st.text_input("Filename Pattern", value=st.session_state.uploaded_filename, placeholder="(?i)bank_name", key="adv_filename_regex")
            sheet_regex = st.text_input("Sheet Pattern (optional)", value="", placeholder="e.g., transactions", key="adv_sheet_regex")

        if st.button("💾 Save Profile", type="primary"):
            if not profile_id:
                st.error("Profile ID is required")
                return

            if not all([date_col, desc_col, amount_col]):
                st.error("All column mappings are required")
                return

            # Create profile
            profile = {
                "id": profile_id,
                "match": {
                    "filename_regex": filename_regex or f"(?i){st.session_state.uploaded_filename}",
                },
                "columns": {
                    "date": [date_col],
                    "description": [desc_col],
                    "amount": [amount_col]
                }
            }

            if sheet_regex:
                profile["match"]["sheet_regex"] = sheet_regex

            # Add header_contains for better matching
            profile["match"]["header_contains"] = [date_col, desc_col, amount_col]

            try:
                save_profile(profile)
                st.success(f"✅ Profile '{profile_id}' saved successfully!")
                st.info("🔄 Profile will be automatically applied next time you upload a matching file.")
            except Exception as e:
                st.error(f"Error saving profile: {str(e)}")


def render_sidebar():
    # Render user menu first
    render_user_menu()

    # Render change password modal if requested
    render_change_password_modal()

    st.header("💾 Database")

    # Show database status
    if not st.session_state.transactions_df.empty:
        stats = st.session_state.service.get_statistics()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", stats['total_transactions'])
            st.metric("Categorized", f"{stats['categorization_rate']}%")
        with col2:
            st.metric("Uncategorized", stats['uncategorized'])
            if stats['date_range']['start']:
                st.caption(f"📅 {stats['date_range']['start']} to {stats['date_range']['end']}")

        if st.button("🔄 Refresh from DB", use_container_width=True):
            db_df = st.session_state.service.get_transactions()
            st.session_state.transactions_df = db_df
            # Clear filtered_df to force refresh
            if 'filtered_df' in st.session_state:
                del st.session_state.filtered_df
            st.rerun()
    else:
        st.info("No data in database")

    st.divider()
    st.header("📁 File Upload")

    # Profile selector
    profiles = load_profiles()
    profile_list = profiles.get('profiles', [])

    # Create user-friendly profile names mapping
    profile_display_names = {
        'visa_adi_v1': 'Adi Visa',
        'visa_gil_v1': 'Gil Visa',
        'isracard_v1': 'Isracard',
        'leumi_account_v1': 'Leumi',
        'generic_csv': 'Generic CSV'
    }

    if profile_list:
        st.subheader("🎯 Select Profile")

        # Create display options with user-friendly names
        profile_options = []
        profile_id_to_display = {}

        for profile in profile_list:
            profile_id = profile['id']
            display_name = profile_display_names.get(profile_id, profile_id)
            profile_options.append(display_name)
            profile_id_to_display[display_name] = profile_id

        selected_profile_display = st.selectbox(
            "Choose profile for upload",
            options=profile_options,
            help="Select which profile to use for importing this file",
            key="profile_selector"
        )

        # Get the actual profile ID from the display name
        selected_profile_id = profile_id_to_display[selected_profile_display]
        profile = next((p for p in profile_list if p['id'] == selected_profile_id), None)

        if profile:
            st.session_state.selected_profile = selected_profile_id

            # Show profile info
            with st.expander("ℹ️ Profile Details", expanded=False):
                if 'match' in profile:
                    match_info = profile['match']
                    if 'filename_regex' in match_info:
                        st.caption(f"**Filename pattern:** `{match_info['filename_regex']}`")
                    if 'sheet_regex' in match_info:
                        st.caption(f"**Sheet pattern:** `{match_info['sheet_regex']}`")
                st.caption(f"**Profile ID:** `{selected_profile_id}`")

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="Upload your bank or credit card export file"
    )

    if uploaded_file is not None:
        # Validate file upload
        is_valid, errors = validate_file_upload(uploaded_file.name, uploaded_file.size)
        if not is_valid:
            for error in errors:
                st.error(f"❌ {error}")
            return
        # Auto-categorize option
        auto_categorize = st.checkbox(
            "🤖 Auto-categorize after upload",
            value=True,
            help="Automatically categorize transactions using AI after importing"
        )

        if st.button("📤 Upload & Process", type="primary", use_container_width=True):
            st.session_state.auto_categorize = auto_categorize
            load_uploaded_file(uploaded_file)
            display_advanced_mapping()
        else:
            # Show preview without processing
            st.info(f"👆 Click 'Upload & Process' to import transactions")

    st.header("🔍 Filters")

    if not st.session_state.transactions_df.empty:
        df = st.session_state.transactions_df

        date_range = None
        if 'Date' in df.columns:
            min_date = pd.to_datetime(df['Date']).min().date()
            max_date = pd.to_datetime(df['Date']).max().date()
            date_range = st.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        amount_range = None
        if 'Amount' in df.columns:
            min_amount = float(df['Amount'].min())
            max_amount = float(df['Amount'].max())
            amount_range = st.slider("Amount Range", min_value=min_amount, max_value=max_amount, value=(min_amount, max_amount), format="%.2f")

        text_search = st.text_input("Search in Description", "")

        # Category filter
        selected_categories = []
        if 'Category' in df.columns:
            categories = sorted(df['Category'].dropna().unique().tolist())

            # Initialize session state if not exists
            if 'selected_categories' not in st.session_state:
                st.session_state.selected_categories = []

            # Add Select All / Clear buttons
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("✅ Select All Categories", use_container_width=True, key="select_all_cats"):
                    st.session_state.selected_categories = categories.copy()
                    st.rerun()
            with col2:
                if st.button("❌ Clear Categories", use_container_width=True, key="clear_all_cats"):
                    st.session_state.selected_categories = []
                    st.rerun()

            selected_categories = st.multiselect(
                "🏷️ Filter by Categories",
                categories,
                default=st.session_state.selected_categories,
                help="Select one or more categories to filter transactions"
            )
            st.session_state.selected_categories = selected_categories

        only_uncategorized = st.checkbox("Only Uncategorized", False)

        filtered_df = df.copy()

        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (pd.to_datetime(filtered_df['Date']).dt.date >= start_date) &
                (pd.to_datetime(filtered_df['Date']).dt.date <= end_date)
            ]

        if amount_range:
            min_amt, max_amt = amount_range
            filtered_df = filtered_df[(filtered_df['Amount'] >= min_amt) & (filtered_df['Amount'] <= max_amt)]

        if text_search:
            filtered_df = filtered_df[filtered_df['Description'].str.contains(text_search, case=False, na=False)]

        if selected_categories:
            filtered_df = filtered_df[filtered_df['Category'].isin(selected_categories)]

        if only_uncategorized:
            filtered_df = filtered_df[filtered_df['Category'].isna()]

        st.session_state.filtered_df = filtered_df

        # Store settings in session state for categorization
        if 'llm_api_key' not in st.session_state:
            st.session_state.llm_api_key = settings.openai_api_key
        if 'fuzzy_threshold' not in st.session_state:
            st.session_state.fuzzy_threshold = settings.fuzzy_match_threshold
        if 'categories' not in st.session_state:
            st.session_state.categories = DEFAULT_CATEGORIES
    else:
        st.info("💡 Data will appear here when transactions are loaded")


def render_quick_actions():
    """Render quick action buttons at the top of the page."""
    st.markdown("### ⚡ Quick Actions")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("➕ Add Transaction", use_container_width=True, type="primary"):
            st.session_state.show_add_transaction = True

    with col2:
        if st.button("🤖 Batch Categorize", use_container_width=True):
            st.session_state.show_batch_categorize = True

    with col3:
        if st.button("📊 Quick Stats", use_container_width=True):
            st.session_state.show_quick_stats = True

    with col4:
        if st.button("❓ Keyboard Shortcuts", use_container_width=True):
            st.session_state.show_shortcuts = not st.session_state.get('show_shortcuts', False)


def render_add_transaction_modal():
    """Render modal for adding manual transactions."""
    if not st.session_state.get('show_add_transaction', False):
        return

    with st.expander("➕ Add Manual Transaction", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            date_input = st.date_input("Date", value=datetime.now())
            amount_input = st.number_input("Amount (₪)", value=0.0, step=10.0)

        with col2:
            description_input = st.text_input("Description")
            category_input = st.selectbox("Category", options=[""] + DEFAULT_CATEGORIES)

        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("💾 Save", type="primary"):
                # Validate inputs
                is_valid, errors = validate_transaction(
                    date_input, 
                    description_input, 
                    amount_input, 
                    category_input if category_input else None
                )
                
                if not is_valid:
                    for error in errors:
                        st.error(f"❌ {error}")
                else:
                    # Sanitize inputs
                    sanitized_description = sanitize_input(description_input)
                    sanitized_category = sanitize_input(category_input) if category_input else None
                    
                    # Create transaction
                    new_transaction = pd.DataFrame([{
                        'Date': date_input,
                        'Description': sanitized_description,
                        'Amount': -abs(amount_input) if amount_input > 0 else amount_input,
                        'Category': sanitized_category,
                        'Month': date_input.strftime('%Y-%m')
                    }])

                    # Save to database with explicit user_id
                    current_user_id = get_current_user_id()
                    result = st.session_state.service.db.save_transactions(new_transaction, user_id=current_user_id)

                    if result['inserted'] > 0:
                        st.success("✅ Transaction added successfully!")
                        # Reload data
                        st.session_state.transactions_df = st.session_state.service.get_transactions()
                        if 'filtered_df' in st.session_state:
                            del st.session_state.filtered_df
                        st.session_state.show_add_transaction = False
                        st.rerun()
                    else:
                        st.error("❌ Failed to add transaction")

        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_add_transaction = False
                st.rerun()


def render_batch_categorize_modal():
    """Render modal for batch categorization."""
    if not st.session_state.get('show_batch_categorize', False):
        return

    with st.expander("🤖 Batch Categorize Uncategorized Transactions", expanded=True):
        df = st.session_state.transactions_df
        uncategorized_count = df['Category'].isna().sum()

        st.write(f"**Uncategorized transactions:** {uncategorized_count}")

        if uncategorized_count == 0:
            st.success("🎉 All transactions are already categorized!")
            if st.button("Close"):
                st.session_state.show_batch_categorize = False
                st.rerun()
            return

        st.info("This will automatically categorize all uncategorized transactions using AI.")

        col1, col2 = st.columns([1, 3])

        with col1:
            if st.button("🚀 Start Categorization", type="primary"):
                with st.spinner(f"Categorizing {uncategorized_count} transactions..."):
                    result = st.session_state.service.bulk_categorize(
                        categories=DEFAULT_CATEGORIES,
                        llm_api_key=settings.openai_api_key,
                        fuzzy_threshold=settings.fuzzy_match_threshold,
                        only_uncategorized=True
                    )

                    st.success(f"✅ Categorized {result['updated_count']} transactions!")

                    # Reload data
                    st.session_state.transactions_df = st.session_state.service.get_transactions()
                    if 'filtered_df' in st.session_state:
                        del st.session_state.filtered_df

                    st.session_state.show_batch_categorize = False
                    st.rerun()

        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_batch_categorize = False
                st.rerun()


def render_keyboard_shortcuts():
    """Render keyboard shortcuts help."""
    if not st.session_state.get('show_shortcuts', False):
        return

    st.markdown("""
    <div class="shortcuts-help">
        <h4>⌨️ Keyboard Shortcuts</h4>
        <p><span class="shortcut-key">Ctrl</span> + <span class="shortcut-key">K</span> - Quick Search</p>
        <p><span class="shortcut-key">Ctrl</span> + <span class="shortcut-key">U</span> - Upload File</p>
        <p><span class="shortcut-key">Ctrl</span> + <span class="shortcut-key">T</span> - Add Transaction</p>
        <p><span class="shortcut-key">Ctrl</span> + <span class="shortcut-key">B</span> - Batch Categorize</p>
        <p><span class="shortcut-key">Esc</span> - Close This Help</p>
        <p style="margin-top: 1rem; opacity: 0.7; font-size: 0.75rem;">Click anywhere to close</p>
    </div>
    """, unsafe_allow_html=True)


def render_floating_action_button():
    """Render floating action button for quick actions."""
    if st.session_state.transactions_df.empty:
        return
    
    # Create FAB container
    st.markdown("""
    <div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
        <div class="fab" onclick="showFabMenu()">⚡</div>
    </div>
    
    <script>
    function showFabMenu() {
        // This would show a menu of quick actions
        // For now, we'll use Streamlit's built-in functionality
        console.log('FAB clicked');
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Add FAB actions as invisible buttons that can be triggered
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("➕", key="fab_add", help="Add Transaction", use_container_width=True):
            st.session_state.show_add_transaction = True
            st.rerun()
    
    with col2:
        if st.button("🤖", key="fab_categorize", help="Batch Categorize", use_container_width=True):
            st.session_state.show_batch_categorize = True
            st.rerun()
    
    with col3:
        if st.button("🔍", key="fab_search", help="Quick Search", use_container_width=True):
            st.session_state.show_quick_search = True
            st.rerun()


def render_global_search():
    """Render global search bar at the top."""
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    search_query = st.text_input(
        "🔍 Search transactions...",
        placeholder="Search by description, category, or amount...",
        key="global_search",
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if search_query:
        # Validate search query
        is_valid, errors = validate_search_query(search_query)
        if not is_valid:
            for error in errors:
                st.error(f"❌ {error}")
        else:
            # Sanitize search query
            sanitized_query = sanitize_input(search_query, max_length=200)
            
            # Apply search filter
            df = st.session_state.transactions_df
            mask = (
                df['Description'].str.contains(sanitized_query, case=False, na=False) |
                df['Category'].str.contains(sanitized_query, case=False, na=False)
            )

            # Try to search by amount
            try:
                amount = float(sanitized_query.replace('₪', '').replace(',', ''))
                mask = mask | (df['Amount'].abs() == abs(amount))
            except:
                pass

            st.session_state.filtered_df = df[mask]

            if mask.sum() > 0:
                st.info(f"🔍 Found {mask.sum()} transactions matching '{sanitized_query}'")
            else:
                st.warning(f"No transactions found matching '{sanitized_query}'")


def display_actions():
    """Display quick actions and management tools."""
    st.subheader("⚡ Quick Actions")

    # Quick action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Add Transaction", use_container_width=True, type="primary", key="action_add"):
            st.session_state.show_add_transaction = True

    with col2:
        if st.button("🤖 Batch Categorize", use_container_width=True, key="action_batch"):
            st.session_state.show_batch_categorize = True

    with col3:
        if st.button("📊 Quick Stats", use_container_width=True, key="action_stats"):
            st.session_state.show_quick_stats = True

    st.divider()

    # Add transaction modal
    render_add_transaction_modal()

    # Batch categorize modal
    render_batch_categorize_modal()

    # Quick stats
    if st.session_state.get('show_quick_stats', False):
        with st.expander("📊 Quick Statistics", expanded=True):
            df = st.session_state.transactions_df

            if not df.empty:
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Transactions", len(df))
                    categorized = df['Category'].notna().sum()
                    st.metric("Categorized", f"{categorized} ({(categorized/len(df)*100):.1f}%)")

                with col2:
                    total_expenses = df[df['Amount'] < 0]['Amount'].sum()
                    st.metric("Total Expenses", f"₪{abs(total_expenses):,.2f}")
                    total_income = df[df['Amount'] > 0]['Amount'].sum()
                    st.metric("Total Income", f"₪{total_income:,.2f}")

                with col3:
                    net_amount = df['Amount'].sum()
                    st.metric("Net Amount", f"₪{net_amount:,.2f}")
                    if 'Date' in df.columns:
                        date_range = f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}"
                        st.caption(f"📅 {date_range}")

                if st.button("Close", key="close_quick_stats"):
                    st.session_state.show_quick_stats = False
                    st.rerun()
            else:
                st.info("No data available")


def display_duplicates():
    """Display duplicate transactions that were skipped during import with option to restore."""
    st.subheader("🔄 Duplicate Transactions Review")

    if not st.session_state.skipped_duplicates:
        st.success("✅ No duplicate transactions were skipped!")
        st.info("💡 Duplicates are detected when a transaction has the same date, description, and amount as an existing transaction in the database.")
        return

    st.markdown(f"""
    **{len(st.session_state.skipped_duplicates)} duplicate transaction(s)** were skipped during import.

    Review these transactions below. If any were incorrectly marked as duplicates, you can add them to the database.
    """)

    st.divider()

    # Display duplicates with option to restore
    for idx, dup in enumerate(st.session_state.skipped_duplicates):
        date = dup.get('date', 'Unknown')
        description = dup.get('description', 'Unknown')
        amount = dup.get('amount', 0)
        category = dup.get('category', None)
        account = dup.get('account', None)

        # Get category icon if available
        category_icon = get_category_icon(category) if category else "❓"

        with st.expander(
            f"{category_icon} 📅 {date} | ₪{abs(amount):,.2f} | {description[:50]}",
            expanded=False
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**Description:** {description}")
                st.write(f"**Amount:** ₪{amount:,.2f}")
                st.write(f"**Date:** {date}")
                if category:
                    st.markdown(f"**Category:** {format_category_badge(category)}", unsafe_allow_html=True)
                if account:
                    st.write(f"**Account:** {account}")

                st.caption("⚠️ This transaction was marked as duplicate because an identical transaction (same date, description, and amount) already exists in the database.")

            with col2:
                if st.button(f"➕ Add to Database", key=f"restore_dup_{idx}", type="primary"):
                    # Create DataFrame for this transaction
                    restore_df = pd.DataFrame([{
                        'Date': pd.to_datetime(date),
                        'Description': description,
                        'Amount': amount,
                        'Category': category,
                        'Account': account,
                        'Month': pd.to_datetime(date).strftime('%Y-%m')
                    }])

                    # Use the secure force insert method
                    try:
                        inserted_count = st.session_state.service.force_insert_transaction(restore_df)
                        
                        if inserted_count > 0:
                            st.success(f"✅ Transaction added to database!")

                            # Remove from skipped duplicates
                            st.session_state.skipped_duplicates.pop(idx)

                            # Reload data
                            st.session_state.transactions_df = st.session_state.service.get_transactions()
                            if 'filtered_df' in st.session_state:
                                del st.session_state.filtered_df

                            st.rerun()
                        else:
                            st.error("❌ Failed to add transaction")
                    except Exception as e:
                        st.error(f"❌ Failed to add transaction: {str(e)}")

                if st.button(f"✓ Keep Skipped", key=f"keep_dup_{idx}"):
                    # Remove from list without adding to database
                    st.session_state.skipped_duplicates.pop(idx)
                    st.success("✅ Marked as reviewed")
                    st.rerun()

    st.divider()

    # Bulk actions
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Clear All Reviewed", use_container_width=True):
            st.session_state.skipped_duplicates = []
            st.success("✅ All duplicate records cleared")
            st.rerun()

    with col2:
        if st.button("➕ Add All to Database", use_container_width=True, type="primary"):
            # Add all duplicates to database
            added_count = 0
            failed_count = 0
            
            for dup in st.session_state.skipped_duplicates:
                try:
                    restore_df = pd.DataFrame([{
                        'Date': pd.to_datetime(dup.get('date')),
                        'Description': dup.get('description'),
                        'Amount': dup.get('amount'),
                        'Category': dup.get('category'),
                        'Account': dup.get('account'),
                        'Month': pd.to_datetime(dup.get('date')).strftime('%Y-%m')
                    }])

                    # Use the secure force insert method
                    inserted = st.session_state.service.force_insert_transaction(restore_df)
                    if inserted > 0:
                        added_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    st.warning(f"⚠️ Failed to add one transaction: {str(e)}")

            if added_count > 0:
                st.success(f"✅ Added {added_count} transactions to database!")
            if failed_count > 0:
                st.warning(f"⚠️ Failed to add {failed_count} transactions")
                
            st.session_state.skipped_duplicates = []

            # Reload data
            st.session_state.transactions_df = st.session_state.service.get_transactions()
            if 'filtered_df' in st.session_state:
                del st.session_state.filtered_df

            st.rerun()


def main():
    st.markdown('<h1 class="main-header">💰 Expense Analyzer</h1>', unsafe_allow_html=True)

    # Process pending categorization if flag file exists (persists across browser refreshes)
    flag_file = 'data/.pending_categorization'
    if os.path.exists(flag_file):
        try:
            os.remove(flag_file)  # Delete flag file after reading
        except Exception:
            pass  # Ignore if file already deleted

        with st.spinner("🤖 Auto-categorizing transactions... (you can safely refresh the browser)"):
            try:
                categorize_result = st.session_state.service.bulk_categorize(
                    categories=DEFAULT_CATEGORIES,
                    llm_api_key=settings.openai_api_key,
                    fuzzy_threshold=settings.fuzzy_match_threshold,
                    only_uncategorized=True
                )

                if categorize_result['updated_count'] > 0:
                    st.success(f"✅ Categorized {categorize_result['updated_count']} transactions")
                    # Reload after categorization
                    st.session_state.transactions_df = st.session_state.service.get_transactions()
                    if 'filtered_df' in st.session_state:
                        del st.session_state.filtered_df
                    # Trigger UI refresh to update dashboard
                    st.rerun()
                else:
                    st.info("ℹ️ No transactions needed categorization")
            except Exception as e:
                st.warning(f"⚠️ Auto-categorization failed: {str(e)}")

    # Render keyboard shortcuts help if enabled
    render_keyboard_shortcuts()

    # Global search
    render_global_search()

    # Floating Action Button (FAB)
    render_floating_action_button()

    with st.sidebar:
        render_sidebar()


def display_dashboard():
    if st.session_state.transactions_df.empty:
        # Enhanced empty state with onboarding
        st.markdown("""
        <div class="empty-state">
            <h2>👋 Welcome to Expense Analyzer!</h2>
            <p>Transform your financial data into actionable insights</p>
            <br>
            <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 2rem;">
                <div style="text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📁</div>
                    <h3 style="color: white; margin-bottom: 0.5rem;">Upload Data</h3>
                    <p style="opacity: 0.9;">Click "Upload & Process" in the sidebar</p>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">➕</div>
                    <h3 style="color: white; margin-bottom: 0.5rem;">Add Manually</h3>
                    <p style="opacity: 0.9;">Use Quick Actions to add transactions</p>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🤖</div>
                    <h3 style="color: white; margin-bottom: 0.5rem;">AI Insights</h3>
                    <p style="opacity: 0.9;">Get personalized recommendations</p>
                </div>
            </div>
            <div style="margin-top: 2rem; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 10px;">
                <p style="margin: 0; font-size: 1.1rem;"><strong>💡 Pro Tip:</strong> Start by uploading your most recent bank or credit card statement to see the magic happen!</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    df = st.session_state.get('filtered_df', st.session_state.transactions_df)

    if df.empty:
        st.warning("⚠️ No transactions match the current filters")
        return

    # Large, prominent total expenses metric - ALWAYS show database total, not filtered
    db_df = st.session_state.transactions_df
    total_expenses_db = db_df[db_df['Amount'] < 0]['Amount'].sum()

    # Show if filters are active
    filters_active = 'filtered_df' in st.session_state and len(df) != len(db_df)

    st.markdown(f"""
    <div class="big-metric-label">💸 Total Expenses (All Transactions in DB)</div>
    <div class="big-metric">₪{abs(total_expenses_db):,.2f}</div>
    """, unsafe_allow_html=True)

    # Show filtered total if filters are active
    if filters_active:
        total_expenses_filtered = df[df['Amount'] < 0]['Amount'].sum()
        st.info(f"🔍 Filtered View: ₪{abs(total_expenses_filtered):,.2f} ({len(df)} of {len(db_df)} transactions)")

    st.divider()

    # Secondary metrics in a clean row - showing DB totals
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_income_db = db_df[db_df['Amount'] > 0]['Amount'].sum()
        st.metric("💰 Income (DB Total)", f"₪{total_income_db:,.2f}")

    with col2:
        net_amount_db = db_df['Amount'].sum()
        st.metric("📊 Net (DB Total)", f"₪{net_amount_db:,.2f}")

    with col3:
        categorized_pct_db = (db_df['Category'].notna().sum() / len(db_df)) * 100 if len(db_df) > 0 else 0
        st.metric("🏷️ Categorized (DB)", f"{categorized_pct_db:.1f}%")

    with col4:
        st.metric("📋 Total in DB", len(db_df))

    st.divider()

    # Main visualizations - side by side
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Monthly Expenses")
        monthly_df = monthly_summary(df)
        if not monthly_df.empty:
            fig = px.bar(
                monthly_df,
                x='Month',
                y='Total_Expenses',
                title="",
                labels={'Total_Expenses': 'Amount (₪)', 'Month': 'Month'}
            )
            fig.update_traces(marker_color='#1f77b4')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🥧 Top Categories")
        category_df = category_summary(df)
        if not category_df.empty:
            fig = px.pie(
                category_df.head(8),
                values='Total_Expenses',
                names='Category',
                title="",
                color='Category',
                color_discrete_map={cat: get_category_color(cat) for cat in category_df['Category'].head(8)}
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)


def display_suggestions():
    if st.session_state.transactions_df.empty:
        return

    df = st.session_state.get('filtered_df', st.session_state.transactions_df)
    uncategorized_df = df[df['Category'].isna()]

    if uncategorized_df.empty:
        st.success("🎉 All transactions are categorized!")
        return

    st.subheader("🤖 Categorization Suggestions")

    llm_api_key = st.session_state.get('llm_api_key', '')
    fuzzy_threshold = st.session_state.get('fuzzy_threshold', 86)
    categories = st.session_state.get('categories', [])
    
    if st.button("🔄 Generate Suggestions"):
        with st.spinner("Generating suggestions..."):
            vendor_map = build_vendor_map(df)
            st.session_state.vendor_map = vendor_map

            suggestions = []
            for idx, row in uncategorized_df.head(20).iterrows():
                match_result = agent_choose_category(
                    row['Description'],
                    st.session_state.mappings,
                    vendor_map,
                    categories,
                    llm_api_key,
                    fuzzy_threshold
                )

                suggestions.append({
                    'index': idx,
                    'description': row['Description'],
                    'amount': row['Amount'],
                    'date': row['Date'],
                    'suggested_category': match_result.category,
                    'confidence': match_result.confidence,
                    'strategy': match_result.strategy,
                    'note': match_result.note
                })

            st.session_state.suggestions = suggestions

    if 'suggestions' in st.session_state:
        for i, suggestion in enumerate(st.session_state.suggestions):
            with st.expander(f"Transaction {i+1}: {suggestion['description'][:50]}..."):
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.write(f"**Description:** {suggestion['description']}")
                    st.write(f"**Amount:** ₪{suggestion['amount']:,.2f}")
                    st.write(f"**Date:** {suggestion['date']}")

                with col2:
                    confidence_class = get_confidence_color(suggestion['confidence'])
                    st.markdown(f"**Confidence:** <span class='{confidence_class}'>{suggestion['confidence']:.2f}</span>", unsafe_allow_html=True)
                    st.write(f"**Method:** {suggestion['strategy']}")

                with col3:
                    if suggestion['suggested_category']:
                        selected_category = st.selectbox(
                            "Category",
                            options=[suggestion['suggested_category']] + [cat for cat in categories if cat != suggestion['suggested_category']],
                            key=f"category_{suggestion['index']}"
                        )

                        if st.button("✅ Apply", key=f"apply_{suggestion['index']}"):
                            # Update in memory
                            df.at[suggestion['index'], 'Category'] = selected_category
                            st.session_state.transactions_df.at[suggestion['index'], 'Category'] = selected_category

                            # Save to database
                            date_str = suggestion['date'].strftime('%Y-%m-%d') if hasattr(suggestion['date'], 'strftime') else str(suggestion['date'])
                            st.session_state.service.apply_category(
                                suggestion['description'],
                                date_str,
                                selected_category,
                                learn=True
                            )

                            # Learn from feedback
                            st.session_state.mappings, st.session_state.vendor_map = learn_from_user_feedback(
                                suggestion['description'],
                                selected_category,
                                st.session_state.mappings,
                                st.session_state.vendor_map
                            )

                            st.success("✅ Category applied, saved to database, and learned!")
                            st.rerun()
                    else:
                        st.write("No suggestion available")


def display_trends():
    if st.session_state.transactions_df.empty:
        return

    df = st.session_state.get('filtered_df', st.session_state.transactions_df)

    if df.empty:
        st.warning("⚠️ No transactions match the current filters")
        return

    st.subheader("📈 Spending Trends Analysis")

    # Month-over-month comparison
    st.subheader("📊 Month-over-Month Comparison")
    mom_df = month_over_month_comparison(df)

    if not mom_df.empty and len(mom_df) > 1:
        # Display comparison table
        st.dataframe(mom_df, use_container_width=True)

        # Create line chart for spending over time
        fig = px.line(
            mom_df,
            x='Month',
            y='Current_Spending',
            title="Total Spending Trend",
            labels={'Current_Spending': 'Total Spending (₪)', 'Month': 'Month'}
        )
        fig.update_traces(mode='lines+markers')
        st.plotly_chart(fig, use_container_width=True)

        # Show latest month comparison
        latest = mom_df.iloc[-1]
        if pd.notna(latest['Change_Percent']):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Latest Month",
                    f"₪{latest['Current_Spending']:,.2f}",
                    f"{latest['Change_Amount']:,.2f} ₪"
                )
            with col2:
                st.metric(
                    "Previous Month",
                    f"₪{latest['Previous_Spending']:,.2f}"
                )
            with col3:
                delta_color = "normal" if latest['Change_Percent'] < 0 else "inverse"
                st.metric(
                    "Change",
                    f"{latest['Change_Percent']:.1f}%",
                    f"{latest['Change_Amount']:,.2f} ₪",
                    delta_color=delta_color
                )
    else:
        st.info("Need at least 2 months of data for comparison")

    st.divider()

    # Category trends
    st.subheader("🏷️ Category Trends")
    cat_trends_df = category_trends(df)

    if not cat_trends_df.empty:
        st.dataframe(cat_trends_df, use_container_width=True)

        # Show top growing and declining categories
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**📈 Top Growing Categories**")
            growing = cat_trends_df[cat_trends_df['Change_Percent'] > 0].head(5)
            if not growing.empty:
                for _, row in growing.iterrows():
                    st.write(f"• {row['Category']}: +{row['Change_Percent']:.1f}% (₪{row['Latest_Month']:,.2f})")
            else:
                st.write("No growing categories")

        with col2:
            st.markdown("**📉 Top Declining Categories**")
            declining = cat_trends_df[cat_trends_df['Change_Percent'] < 0].head(5)
            if not declining.empty:
                for _, row in declining.iterrows():
                    st.write(f"• {row['Category']}: {row['Change_Percent']:.1f}% (₪{row['Latest_Month']:,.2f})")
            else:
                st.write("No declining categories")
    else:
        st.info("Need at least 2 months of data for category trends")

    st.divider()

    # Spending trends by category over time
    st.subheader("📉 Category Spending Over Time")
    trends_df = spending_trends(df, months=6)

    if not trends_df.empty:
        # Select top categories to display
        top_categories = category_summary(df).head(5)['Category'].tolist()

        if top_categories:
            # Create line chart for top categories
            trends_melted = trends_df.reset_index().melt(
                id_vars='Month',
                value_vars=[cat for cat in top_categories if cat in trends_df.columns],
                var_name='Category',
                value_name='Spending'
            )

            fig = px.line(
                trends_melted,
                x='Month',
                y='Spending',
                color='Category',
                title="Top 5 Categories Spending Trend",
                labels={'Spending': 'Amount (₪)', 'Month': 'Month'}
            )
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data for trend analysis")


def display_transactions():
    """Display and edit transaction categories."""
    if st.session_state.transactions_df.empty:
        st.info("📋 No transactions to display. Upload a file to get started.")
        return

    df = st.session_state.get('filtered_df', st.session_state.transactions_df)

    if df.empty:
        st.warning("⚠️ No transactions match the current filters")
        return

    st.subheader("📋 Transactions")

    # Summary info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Transactions", len(df))
    with col2:
        categorized = df['Category'].notna().sum()
        st.metric("Categorized", f"{categorized} ({(categorized/len(df)*100):.1f}%)")
    with col3:
        uncategorized = df['Category'].isna().sum()
        st.metric("Uncategorized", uncategorized)

    st.divider()

    # Pagination
    items_per_page = 20
    total_pages = (len(df) - 1) // items_per_page + 1

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input(
            f"Page (1-{total_pages})",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.current_page,
            step=1,
            key="page_selector"
        )
        st.session_state.current_page = page

    # Calculate page slice
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(df))
    page_df = df.iloc[start_idx:end_idx].copy()

    # Display transactions with editable categories
    for idx, row in page_df.iterrows():
        # Get category icon for the expander title
        category = row['Category'] if pd.notna(row['Category']) else None
        category_icon = get_category_icon(category) if category else "❓"

        with st.expander(
            f"{category_icon} 📅 {row['Date'].strftime('%Y-%m-%d') if hasattr(row['Date'], 'strftime') else str(row['Date'])} | "
            f"₪{abs(row['Amount']):,.2f} | {row['Description'][:50]}"
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**Description:** {row['Description']}")
                st.write(f"**Amount:** ₪{row['Amount']:,.2f}")
                st.write(f"**Date:** {row['Date']}")

                # Show current category with badge
                if category:
                    st.markdown(f"**Current Category:** {format_category_badge(category)}", unsafe_allow_html=True)

            with col2:
                # Category selector
                current_category = row['Category'] if pd.notna(row['Category']) else None

                # Create options list with icons
                if current_category:
                    category_options_display = [f"{get_category_icon(current_category)} {current_category}"] + \
                                                [f"{get_category_icon(cat)} {cat}" for cat in DEFAULT_CATEGORIES if cat != current_category]
                    category_options_values = [current_category] + [cat for cat in DEFAULT_CATEGORIES if cat != current_category]
                else:
                    category_options_display = ["(Select Category)"] + \
                                                [f"{get_category_icon(cat)} {cat}" for cat in DEFAULT_CATEGORIES]
                    category_options_values = ["(Select Category)"] + DEFAULT_CATEGORIES

                selected_index = st.selectbox(
                    "Category",
                    options=range(len(category_options_display)),
                    format_func=lambda i: category_options_display[i],
                    key=f"cat_edit_{idx}",
                    help="Select a category for this transaction"
                )

                selected_category = category_options_values[selected_index]

                # Update button
                if selected_category != "(Select Category)" and selected_category != current_category:
                    if st.button("💾 Save", key=f"save_{idx}", type="primary"):
                        # Update in database
                        date_str = row['Date'].strftime('%Y-%m-%d') if hasattr(row['Date'], 'strftime') else str(row['Date'])
                        success = st.session_state.service.apply_category(
                            row['Description'],
                            date_str,
                            selected_category,
                            learn=True
                        )

                        if success:
                            # Update in session state
                            st.session_state.transactions_df.at[idx, 'Category'] = selected_category
                            if 'filtered_df' in st.session_state:
                                del st.session_state.filtered_df

                            # Learn from feedback
                            st.session_state.mappings, st.session_state.vendor_map = learn_from_user_feedback(
                                row['Description'],
                                selected_category,
                                st.session_state.mappings,
                                st.session_state.vendor_map
                            )

                            st.success(f"✅ Updated to: {selected_category}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to update category")

                # Show current category if exists
                if current_category:
                    st.caption(f"Current: {current_category}")


def display_vendor_management():
    """Display vendor category management interface."""
    if st.session_state.transactions_df.empty:
        st.info("📋 No data available. Upload transactions to manage vendors.")
        return

    df = st.session_state.get('filtered_df', st.session_state.transactions_df)

    if df.empty:
        st.warning("⚠️ No transactions match the current filters")
        return

    st.subheader("🏪 Vendor Category Management")
    st.markdown("Update categories for multiple transactions from the same vendor at once")

    # Get top vendors
    top5_df = top5_by_category(df)

    if top5_df.empty:
        st.info("No categorized transactions found")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Vendors", len(top5_df))
    with col2:
        unique_categories = top5_df['Category'].nunique()
        st.metric("Categories", unique_categories)
    with col3:
        total_transactions = top5_df['Transaction_Count'].sum()
        st.metric("Total Transactions", total_transactions)

    st.divider()

    # Display editable vendor list
    for idx, row in top5_df.iterrows():
        vendor = row['Description']
        current_category = row['Category']
        total_amount = row['Total_Amount']
        transaction_count = row['Transaction_Count']

        with st.expander(
            f"{get_category_icon(current_category)} {vendor[:60]} | {current_category} | ₪{abs(total_amount):,.2f} ({transaction_count} transactions)",
            expanded=False
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**Vendor:** {vendor}")
                st.write(f"**Current Category:** {format_category_badge(current_category)}", unsafe_allow_html=True)
                st.write(f"**Total Amount:** ₪{abs(total_amount):,.2f}")
                st.write(f"**Transaction Count:** {transaction_count}")

            with col2:
                # Category selector with icons
                category_options_display = [f"{get_category_icon(current_category)} {current_category}"] + \
                                            [f"{get_category_icon(cat)} {cat}" for cat in DEFAULT_CATEGORIES if cat != current_category]
                category_options_values = [current_category] + [cat for cat in DEFAULT_CATEGORIES if cat != current_category]

                # Add option for custom category
                category_options_display.append("➕ Create New Category")
                category_options_values.append("__CREATE_NEW__")

                selected_index = st.selectbox(
                    "Change Category",
                    options=range(len(category_options_display)),
                    format_func=lambda i: category_options_display[i],
                    key=f"vendor_cat_{idx}_{vendor}",
                    help="Select a new category for this vendor"
                )

                selected_category = category_options_values[selected_index]

                # Handle custom category creation
                if selected_category == "__CREATE_NEW__":
                    new_category = st.text_input(
                        "New Category Name",
                        key=f"new_cat_{idx}_{vendor}",
                        placeholder="Enter new category name"
                    )
                    if new_category:
                        selected_category = new_category.strip()

                # Update button
                if selected_category != current_category and selected_category != "__CREATE_NEW__":
                    if st.button("💾 Update All Transactions", key=f"update_vendor_{idx}_{vendor}", type="primary"):
                        # Use the new bulk update method for better performance
                        updated_count = st.session_state.service.bulk_apply_category(
                            vendor,
                            selected_category,
                            learn=True
                        )

                        if updated_count > 0:
                            # Reload data
                            st.session_state.transactions_df = st.session_state.service.get_transactions()
                            if 'filtered_df' in st.session_state:
                                del st.session_state.filtered_df

                            st.success(f"✅ Updated {updated_count} transactions from '{vendor}' to category '{selected_category}'")
                            st.rerun()
                        else:
                            st.error("❌ Failed to update transactions")


def display_analytics():
    """Display detailed analytics including category details and top vendors."""
    if st.session_state.transactions_df.empty:
        st.info("📊 No data available. Upload transactions to see analytics.")
        return

    df = st.session_state.get('filtered_df', st.session_state.transactions_df)

    if df.empty:
        st.warning("⚠️ No transactions match the current filters")
        return

    st.subheader("📊 Detailed Analytics")

    # Category details with icons
    st.markdown("### 🏷️ Category Breakdown")
    category_df = category_summary(df)
    if not category_df.empty:
        # Display as expandable cards
        for idx, row in category_df.iterrows():
            icon = get_category_icon(row['Category'])
            color = get_category_color(row['Category'])
            amount = abs(row['Total_Expenses'])
            count = row['Transaction_Count']

            with st.expander(
                f"{icon} {row['Category']} - ₪{amount:,.2f} ({count} transactions)",
                expanded=idx < 5  # Expand top 5 by default
            ):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Spent", f"₪{amount:,.2f}")
                with col2:
                    st.metric("Transactions", count)
                with col3:
                    avg_amount = amount / count if count > 0 else 0
                    st.metric("Avg per Transaction", f"₪{avg_amount:,.2f}")
    else:
        st.info("No categorized transactions found")

    st.divider()

    # Top vendors table
    st.markdown("### 🏆 Top Vendors by Category")
    top5_df = top5_by_category(df)
    if not top5_df.empty:
        # Add icon column
        top5_df_display = top5_df.copy()
        top5_df_display['Icon'] = top5_df_display['Category'].apply(get_category_icon)

        # Reorder columns
        cols = ['Icon', 'Category', 'Description', 'Total_Amount', 'Transaction_Count']
        top5_df_display = top5_df_display[cols]

        # Format amounts
        top5_df_display['Total_Amount'] = top5_df_display['Total_Amount'].apply(lambda x: f"₪{abs(x):,.2f}")

        st.dataframe(
            top5_df_display,
            use_container_width=True,
            column_config={
                "Icon": st.column_config.TextColumn("", width="small"),
                "Category": st.column_config.TextColumn("Category", width="medium"),
                "Description": st.column_config.TextColumn("Vendor", width="large"),
                "Total_Amount": st.column_config.TextColumn("Total", width="medium"),
                "Transaction_Count": st.column_config.NumberColumn("Count", width="small")
            }
        )
    else:
        st.info("No categorized transactions found")


def display_manage_uploads():
    """Display upload session management interface."""
    st.subheader("📁 Manage Upload History")
    st.markdown("View and manage all your uploaded files. You can delete specific uploads if needed.")

    # Get all upload sessions
    sessions = st.session_state.service.get_upload_sessions()

    if not sessions:
        st.info("📋 No upload history found. Upload some files to see them here!")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Uploads", len(sessions))
    with col2:
        total_transactions = sum(s['transactions_count'] or 0 for s in sessions)
        st.metric("Total Transactions", total_transactions)
    with col3:
        # Get most recent upload date
        recent_upload = max(sessions, key=lambda x: x['upload_date'])
        st.metric("Latest Upload", recent_upload['upload_date'][:10])

    st.divider()

    # Display upload sessions
    st.markdown("### 📂 Upload Sessions")

    for idx, session in enumerate(sessions):
        upload_id = session['id']
        filename = session['filename']
        upload_date = session['upload_date']
        trans_count = session['transactions_count'] or 0
        account = session['account'] or "Unknown"
        file_size = session['file_size']

        # Format file size
        if file_size:
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
        else:
            size_str = "Unknown"

        # Determine icon based on filename
        if 'visa' in filename.lower() or 'credit' in filename.lower():
            file_icon = "💳"
        elif 'leumi' in filename.lower() or 'bank' in filename.lower():
            file_icon = "🏦"
        else:
            file_icon = "📄"

        with st.expander(
            f"{file_icon} {filename} - {upload_date[:16]} ({trans_count} transactions)",
            expanded=False
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**Filename:** {filename}")
                st.write(f"**Upload Date:** {upload_date}")
                st.write(f"**Transactions:** {trans_count}")
                st.write(f"**Account:** {account}")
                st.write(f"**File Size:** {size_str}")
                st.write(f"**Upload ID:** `{upload_id[:8]}...`")

            with col2:
                st.markdown("### Actions")

                # Delete button with confirmation
                if st.button(f"🗑️ Delete Upload", key=f"delete_upload_{idx}", type="secondary"):
                    st.session_state[f'confirm_delete_{idx}'] = True

                # Show confirmation if requested
                if st.session_state.get(f'confirm_delete_{idx}', False):
                    st.warning(f"⚠️ This will delete **{trans_count}** transactions from this upload!")

                    col_yes, col_no = st.columns(2)

                    with col_yes:
                        if st.button("✅ Confirm", key=f"confirm_yes_{idx}", type="primary"):
                            try:
                                # Delete the upload session and its transactions
                                deleted_count = st.session_state.service.delete_upload_session(upload_id)

                                st.success(f"✅ Deleted {deleted_count} transactions from upload '{filename}'")

                                # Reload data
                                st.session_state.transactions_df = st.session_state.service.get_transactions()
                                if 'filtered_df' in st.session_state:
                                    del st.session_state.filtered_df

                                # Clear confirmation flag
                                del st.session_state[f'confirm_delete_{idx}']

                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error deleting upload: {str(e)}")

                    with col_no:
                        if st.button("❌ Cancel", key=f"confirm_no_{idx}"):
                            del st.session_state[f'confirm_delete_{idx}']
                            st.rerun()

    st.divider()

    # Bulk actions section
    st.markdown("### 🔧 Bulk Actions")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Clear All Uploads**")
        st.caption("Delete all upload history and transactions (⚠️ Use with extreme caution!)")

        if st.button("🗑️ Delete All Uploads", type="secondary"):
            st.session_state.show_delete_all_confirm = True

    with col2:
        if st.session_state.get('show_delete_all_confirm', False):
            st.warning("⚠️ **WARNING**: This will delete ALL your transaction data!")

            col_yes, col_no = st.columns(2)

            with col_yes:
                if st.button("✅ Yes, Delete Everything", type="primary", key="delete_all_confirm"):
                    try:
                        # Delete all transactions for current user
                        deleted = st.session_state.service.clear_all_data()

                        st.success(f"✅ Deleted all data ({deleted} transactions)")

                        # Reload empty data
                        st.session_state.transactions_df = st.session_state.service.get_transactions()
                        if 'filtered_df' in st.session_state:
                            del st.session_state.filtered_df

                        st.session_state.show_delete_all_confirm = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error deleting data: {str(e)}")

            with col_no:
                if st.button("❌ Cancel", key="delete_all_cancel"):
                    st.session_state.show_delete_all_confirm = False
                    st.rerun()


def display_exports():
    if st.session_state.transactions_df.empty:
        return

    st.subheader("📤 Export Data")

    df = st.session_state.get('filtered_df', st.session_state.transactions_df)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.download_button(
            label="📄 Transactions CSV",
            data=df.to_csv(index=False),
            file_name=f"transactions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    with col2:
        st.download_button(
            label="📊 Monthly Summary",
            data=monthly_summary(df).to_csv(index=False),
            file_name=f"monthly_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    with col3:
        st.download_button(
            label="🥧 Category Summary",
            data=category_summary(df).to_csv(index=False),
            file_name=f"category_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    with col4:
        st.download_button(
            label="🏆 Top 5 Vendors",
            data=top5_by_category(df).to_csv(index=False),
            file_name=f"top5_vendors_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )


def display_ai_insights():
    """Display AI-powered financial insights and recommendations."""
    st.header("🤖 AI Financial Insights")
    
    # Force refresh the service to ensure we have the latest methods
    current_user_id = get_current_user_id()
    st.session_state.service = TransactionService(user_id=current_user_id)
    
    if st.session_state.transactions_df.empty:
        st.info("No transactions to analyze. Please upload some data first.")
        return
    
    # Check if OpenAI API key is configured
    settings = get_settings()
    if not settings.openai_api_key:
        st.warning("⚠️ OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
        st.info("💡 You can get an API key from https://platform.openai.com/api-keys")
        return
    
    # Hero section
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 2rem; border-radius: 15px; margin-bottom: 2rem;">
        <h2 style="color: white; margin-bottom: 1rem;">🔮 AI Financial Analysis</h2>
        <p style="font-size: 1.1rem; margin-bottom: 0;">
            Get personalized money-saving recommendations based on your spending patterns across all accounts.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show estimated cost
    try:
        estimated_cost = st.session_state.service.estimate_ai_analysis_cost()
        st.info(f"💰 Estimated cost: ~${estimated_cost:.4f} USD per analysis")
    except Exception as e:
        st.warning(f"Could not estimate cost: {str(e)}")
    
    # Generate Analysis button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔮 Generate Analysis for All Accounts", 
                    use_container_width=True, 
                    type="primary",
                    help="This will analyze all your accounts and provide personalized recommendations"):
            
            # Check if we have cached results
            if 'ai_insights' in st.session_state and st.session_state.ai_insights:
                if st.button("🔄 Regenerate Analysis", use_container_width=True):
                    _generate_and_display_insights()
            else:
                _generate_and_display_insights()
    
    # Display results if available
    if 'ai_insights' in st.session_state and st.session_state.ai_insights:
        _display_insights_results(st.session_state.ai_insights)


def _generate_and_display_insights():
    """Generate AI insights and cache them in session state."""
    with st.spinner("🤖 Analyzing your spending patterns... This may take 30-60 seconds."):
        try:
            insights = st.session_state.service.generate_ai_analysis()
            st.session_state.ai_insights = insights
            st.success("✅ Analysis complete!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Analysis failed: {str(e)}")
            st.info("💡 Make sure your OpenAI API key is valid and you have sufficient credits.")


def _display_insights_results(insights: dict):
    """Display the AI insights results."""
    metadata = insights.get('metadata', {})
    
    # Overall Summary
    st.markdown("### 📊 Overall Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Spending", f"₪{metadata.get('overall_spending', 0):,.0f}")
    with col2:
        st.metric("Total Income", f"₪{metadata.get('overall_income', 0):,.0f}")
    with col3:
        st.metric("Accounts Analyzed", metadata.get('total_accounts', 0))
    with col4:
        st.metric("Generated", metadata.get('generated_at', 'Unknown')[:10])
    
    # Overall summary text
    if 'overall_summary' in insights:
        st.markdown("#### 💡 Key Insights")
        st.markdown(f"**{insights['overall_summary']}**")
    
    # Account selector
    accounts = list(insights.get('account_analyses', {}).keys())
    if accounts:
        st.markdown("### 🏦 Account Analysis")
        
        # Create tabs for each account
        if len(accounts) > 1:
            account_tabs = st.tabs([f"💳 {acc}" for acc in accounts])
            for i, account in enumerate(accounts):
                with account_tabs[i]:
                    _display_account_analysis(account, insights['account_analyses'][account])
        else:
            # Single account - display directly
            account = accounts[0]
            _display_account_analysis(account, insights['account_analyses'][account])
    
    # Comparative insights
    if 'comparative_insights' in insights:
        st.markdown("### 🔄 Cross-Account Insights")
        comp_insights = insights['comparative_insights']
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'highest_spending_by_category' in comp_insights:
                st.markdown("#### 📈 Highest Spending by Category")
                for category, account in comp_insights['highest_spending_by_category'].items():
                    st.write(f"• **{category}**: {account}")
        
        with col2:
            if 'consolidation_opportunities' in comp_insights:
                st.markdown("#### 🔗 Consolidation Opportunities")
                for opportunity in comp_insights['consolidation_opportunities']:
                    st.write(f"• {opportunity}")
        
        if 'household_recommendations' in comp_insights:
            st.markdown("#### 🏠 Household Recommendations")
            for rec in comp_insights['household_recommendations']:
                st.write(f"• {rec}")


def _display_account_analysis(account_name: str, analysis: dict):
    """Display analysis for a specific account."""
    st.markdown(f"#### 💳 {account_name}")
    
    # Spending assessment
    if 'spending_assessment' in analysis:
        st.markdown("**📊 Spending Assessment:**")
        st.write(analysis['spending_assessment'])
    
    # Budget recommendations
    if 'budget_recommendations' in analysis and analysis['budget_recommendations']:
        st.markdown("**📋 Budget Recommendations:**")
        budget_df = pd.DataFrame([
            {"Category": cat, "Recommended Budget": budget}
            for cat, budget in analysis['budget_recommendations'].items()
        ])
        st.dataframe(budget_df, use_container_width=True, hide_index=True)
    
    # Savings opportunities
    if 'savings_opportunities' in analysis and analysis['savings_opportunities']:
        st.markdown("**💡 Top Savings Opportunities:**")
        for i, opportunity in enumerate(analysis['savings_opportunities'], 1):
            # Color code by priority
            if i <= 2:
                color = "#28a745"  # Green for high priority
            elif i <= 4:
                color = "#ffc107"  # Yellow for medium priority
            else:
                color = "#dc3545"  # Red for lower priority
            
            st.markdown(f"""
            <div style="background-color: {color}20; padding: 1rem; border-radius: 8px; 
                        border-left: 4px solid {color}; margin: 0.5rem 0;">
                <strong>{i}. {opportunity}</strong>
            </div>
            """, unsafe_allow_html=True)
    
    # Unusual alerts
    if 'unusual_alerts' in analysis and analysis['unusual_alerts']:
        st.markdown("**⚠️ Unusual Spending Alerts:**")
        for alert in analysis['unusual_alerts']:
            st.warning(f"⚠️ {alert}")
    
    # Monthly insights
    if 'monthly_insights' in analysis:
        st.markdown("**📅 Monthly Insights:**")
        st.write(analysis['monthly_insights'])


def display_unified_home():
    """Unified Home tab combining dashboard, quick stats, and recent activity."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    # Main dashboard content
    display_dashboard()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Quick actions section
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ Add Transaction", use_container_width=True, type="primary"):
            st.session_state.show_add_transaction = True
    
    with col2:
        if st.button("🤖 Batch Categorize", use_container_width=True):
            st.session_state.show_batch_categorize = True
    
    with col3:
        if st.button("📊 Quick Stats", use_container_width=True):
            st.session_state.show_quick_stats = True
    
    with col4:
        if st.button("❓ Keyboard Shortcuts", use_container_width=True):
            st.session_state.show_shortcuts = not st.session_state.get('show_shortcuts', False)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Render modals
    render_add_transaction_modal()
    render_batch_categorize_modal()
    
    # Quick stats
    if st.session_state.get('show_quick_stats', False):
        with st.expander("📊 Quick Statistics", expanded=True):
            df = st.session_state.transactions_df

            if not df.empty:
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Transactions", len(df))
                    categorized = df['Category'].notna().sum()
                    st.metric("Categorized", f"{categorized} ({(categorized/len(df)*100):.1f}%)")

                with col2:
                    total_expenses = df[df['Amount'] < 0]['Amount'].sum()
                    st.metric("Total Expenses", f"₪{abs(total_expenses):,.2f}")
                    total_income = df[df['Amount'] > 0]['Amount'].sum()
                    st.metric("Total Income", f"₪{total_income:,.2f}")

                with col3:
                    net_amount = df['Amount'].sum()
                    st.metric("Net Amount", f"₪{net_amount:,.2f}")
                    if 'Date' in df.columns:
                        date_range = f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}"
                        st.caption(f"📅 {date_range}")

                if st.button("Close", key="close_quick_stats"):
                    st.session_state.show_quick_stats = False
                    st.rerun()
            else:
                st.info("No data available")


def display_unified_analytics():
    """Unified Analytics tab combining detailed analysis and spending trends."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Detailed Analytics")
    display_analytics()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📈 Spending Trends")
    display_trends()
    st.markdown('</div>', unsafe_allow_html=True)


def display_unified_transactions():
    """Unified Transactions tab with inline categorization suggestions."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 All Transactions")
    display_transactions()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🤖 Auto-Categorize Suggestions")
    display_suggestions()
    st.markdown('</div>', unsafe_allow_html=True)


def display_unified_manage():
    """Unified Manage tab combining all management functions."""
    # Create sub-tabs for different management areas
    manage_tab1, manage_tab2, manage_tab3, manage_tab4 = st.tabs([
        "🏪 Vendors", 
        "📁 Uploads", 
        "🔄 Duplicates", 
        "📤 Export"
    ])
    
    with manage_tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        display_vendor_management()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with manage_tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        display_manage_uploads()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with manage_tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        display_duplicates()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with manage_tab4:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        display_exports()
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()

    # Main content tabs - Consolidated from 11 to 5 tabs
    if not st.session_state.transactions_df.empty:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏠 Home",
            "📊 Analytics", 
            "📋 Transactions",
            "⚙️ Manage",
            "🤖 AI Insights"
        ])

        with tab1:
            display_unified_home()

        with tab2:
            display_unified_analytics()

        with tab3:
            display_unified_transactions()

        with tab4:
            display_unified_manage()

        with tab5:
            display_ai_insights()
