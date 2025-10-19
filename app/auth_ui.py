"""
Authentication UI components for Streamlit app.
"""
import streamlit as st
import sys
import os
import extra_streamlit_components as stx

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.auth import AuthManager

# Initialize cookie manager
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()


def render_login_page():
    """Render login/signup page."""
    st.markdown("""
        <style>
        .auth-container {
            max-width: 500px;
            margin: auto;
            padding: 2rem;
        }
        .auth-header {
            text-align: center;
            color: #1f77b4;
            margin-bottom: 2rem;
        }
        .auth-form {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="auth-header">💰 Expense Analyzer</h1>', unsafe_allow_html=True)

    # Tabs for login, signup, and forgot password
    tab1, tab2, tab3 = st.tabs(["🔐 Login", "📝 Sign Up", "🔑 Forgot Password"])

    with tab1:
        render_login_form()

    with tab2:
        render_signup_form()

    with tab3:
        render_forgot_password_form()

    st.markdown('</div>', unsafe_allow_html=True)


def render_login_form():
    """Render login form."""
    st.markdown("### Welcome Back!")

    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        submit = st.form_submit_button("Login", use_container_width=True, type="primary")

        if submit:
            if not username or not password:
                st.error("❌ Please enter both username and password")
                return

            # Initialize auth manager
            auth_manager = AuthManager()

            # Authenticate user
            success, message, user_data = auth_manager.authenticate_user(username, password)

            if success:
                # Store user data in session state
                st.session_state.authenticated = True
                st.session_state.user = user_data

                # Store session token in cookie for persistent login (7 days)
                if 'session_token' in user_data:
                    cookie_manager.set('session_token', user_data['session_token'], max_age=7*24*60*60)

                st.success(f"✅ {message}")
                st.rerun()
            else:
                st.error(f"❌ {message}")


def render_signup_form():
    """Render signup form."""
    st.markdown("### Create New Account")

    with st.form("signup_form"):
        username = st.text_input(
            "Username",
            key="signup_username",
            help="At least 3 characters"
        )
        email = st.text_input(
            "Email",
            key="signup_email",
            help="Valid email address"
        )
        full_name = st.text_input(
            "Full Name (optional)",
            key="signup_fullname"
        )
        password = st.text_input(
            "Password",
            type="password",
            key="signup_password",
            help="At least 6 characters"
        )
        password_confirm = st.text_input(
            "Confirm Password",
            type="password",
            key="signup_password_confirm"
        )

        submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")

        if submit:
            # Validate inputs
            if not username or not email or not password:
                st.error("❌ Please fill in all required fields")
                return

            if password != password_confirm:
                st.error("❌ Passwords do not match")
                return

            # Initialize auth manager
            auth_manager = AuthManager()

            # Create user
            success, message, user_id = auth_manager.create_user(
                username=username,
                email=email,
                password=password,
                full_name=full_name if full_name else None
            )

            if success:
                st.success(f"✅ {message}")
                st.info("👉 Please login with your new credentials")
            else:
                st.error(f"❌ {message}")


def render_forgot_password_form():
    """Render forgot password / password reset form."""
    st.markdown("### Reset Your Password")
    st.markdown("Enter your username and email to reset your password.")

    with st.form("forgot_password_form"):
        username = st.text_input(
            "Username",
            key="forgot_username",
            help="Your account username"
        )
        email = st.text_input(
            "Email",
            key="forgot_email",
            help="Email address associated with your account"
        )
        new_password = st.text_input(
            "New Password",
            type="password",
            key="forgot_new_password",
            help="At least 6 characters"
        )
        confirm_password = st.text_input(
            "Confirm New Password",
            type="password",
            key="forgot_confirm_password"
        )

        submit = st.form_submit_button("Reset Password", use_container_width=True, type="primary")

        if submit:
            # Validate inputs
            if not username or not email or not new_password:
                st.error("❌ Please fill in all fields")
                return

            if new_password != confirm_password:
                st.error("❌ Passwords do not match")
                return

            # Initialize auth manager
            auth_manager = AuthManager()

            # Reset password
            success, message = auth_manager.reset_password(
                username=username,
                email=email,
                new_password=new_password
            )

            if success:
                st.success(f"✅ {message}")
                st.info("👉 Go to the Login tab to sign in with your new password")
            else:
                st.error(f"❌ {message}")


def render_user_menu():
    """Render user menu in sidebar."""
    if 'user' not in st.session_state:
        return

    user = st.session_state.user

    with st.sidebar:
        st.divider()
        st.markdown("### 👤 User Profile")

        # Display user info
        st.write(f"**Username:** {user.get('username')}")
        st.write(f"**Email:** {user.get('email')}")
        if user.get('full_name'):
            st.write(f"**Name:** {user.get('full_name')}")

        st.divider()

        # User actions
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔑 Change Password", use_container_width=True):
                st.session_state.show_change_password = True

        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                logout()


def render_change_password_modal():
    """Render change password modal."""
    if not st.session_state.get('show_change_password', False):
        return

    with st.expander("🔑 Change Password", expanded=True):
        with st.form("change_password_form"):
            old_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password", help="At least 6 characters")
            confirm_password = st.text_input("Confirm New Password", type="password")

            col1, col2 = st.columns([1, 3])

            with col1:
                submit = st.form_submit_button("💾 Save", type="primary")

            with col2:
                cancel = st.form_submit_button("❌ Cancel")

            if cancel:
                st.session_state.show_change_password = False
                st.rerun()

            if submit:
                if not old_password or not new_password or not confirm_password:
                    st.error("❌ Please fill in all fields")
                    return

                if new_password != confirm_password:
                    st.error("❌ New passwords do not match")
                    return

                # Initialize auth manager
                auth_manager = AuthManager()
                user_id = st.session_state.user.get('id')

                # Change password
                success, message = auth_manager.change_password(
                    user_id=user_id,
                    old_password=old_password,
                    new_password=new_password
                )

                if success:
                    st.success(f"✅ {message}")
                    st.session_state.show_change_password = False
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def logout():
    """Logout user and clear session."""
    # Invalidate session token in database if exists
    if 'user' in st.session_state and 'session_token' in st.session_state.user:
        auth_manager = AuthManager()
        auth_manager.invalidate_session_token(st.session_state.user['session_token'])

    # Clear session token cookie
    cookie_manager.delete('session_token')

    # Clear user-related session state
    keys_to_clear = [
        'authenticated', 'user', 'service', 'transactions_df',
        'mappings', 'vendor_map', 'raw_df', 'filtered_df',
        'skipped_duplicates', 'suggestions', 'show_change_password'
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    st.success("✅ Logged out successfully")
    st.rerun()


def require_auth():
    """
    Check if user is authenticated. If not, show login page and stop execution.
    Use this at the top of your main app.
    """
    # First, check if already authenticated in session state
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        return

    # If not authenticated, try to restore session from cookie
    try:
        cookies = cookie_manager.get_all()
        
        if cookies and 'session_token' in cookies:
            session_token = cookies['session_token']
            
            if session_token and session_token.strip():
                # Show loading message while validating
                with st.spinner('🔐 Restoring session...'):
                    # Validate session token
                    auth_manager = AuthManager()
                    user_data = auth_manager.validate_session_token(session_token)

                    if user_data:
                        # Restore session
                        st.session_state.authenticated = True
                        user_data['session_token'] = session_token  # Keep token in session
                        st.session_state.user = user_data
                        st.rerun()
                        return
                    else:
                        # Invalid token, clear cookie
                        cookie_manager.delete('session_token')
    except Exception as e:
        # If there's any error with cookies, just continue to login
        pass

    # If no valid session, show login page
    render_login_page()
    st.stop()


def get_current_user_id() -> int:
    """Get current authenticated user ID."""
    if 'user' in st.session_state:
        return st.session_state.user.get('id')
    return None
