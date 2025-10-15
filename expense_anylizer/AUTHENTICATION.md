# Authentication & Security

This document explains the authentication and data security features of the Expense Analyzer app.

## Features

### User Authentication
- **Secure Login/Signup**: Users must authenticate before accessing the app
- **Password Security**: Passwords are hashed using bcrypt (never stored in plain text)
- **Session Management**: User sessions are managed securely through Streamlit

### Data Isolation
- **User-Specific Data**: Each user can only see and modify their own transactions
- **Database-Level Security**: All queries filter by authenticated user ID
- **Foreign Key Constraints**: Transactions are linked to users with CASCADE delete

### User Management
- **Change Password**: Users can change their password from within the app
- **Logout**: Secure logout that clears all session data
- **User Profile**: View account information in the sidebar

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The authentication system requires:
- `bcrypt>=4.0.0` - For secure password hashing
- `extra-streamlit-components>=0.1.60` - For enhanced UI components

### 2. Initialize Database and Create First User

Run the initialization script to create the authentication tables and your first user:

```bash
python init_auth.py
```

This will:
1. Create the `users` table in your database
2. Prompt you to create an admin/first user account
3. Initialize the authentication system

**Example:**
```
Expense Analyzer - User Initialization
========================================

Creating new user account:
----------------------------------------
Username (min 3 chars): admin
Email: admin@example.com
Full Name (optional): Admin User
Password (min 6 chars): [your-secure-password]
Confirm Password: [your-secure-password]

✅ User created successfully
   User ID: 1
   Username: admin
   Email: admin@example.com
```

### 3. Start the Application

```bash
streamlit run app/streamlit_app.py
```

or use the start script:

```bash
python start_app.py
```

### 4. Login

When you open the app, you'll see the login page:
1. Enter your username and password
2. Click "Login"
3. You'll be redirected to the main app

### 5. Create Additional Users

Additional users can sign up through the "Sign Up" tab on the login page:
1. Click the "Sign Up" tab
2. Fill in username, email, and password
3. Click "Create Account"
4. Login with the new credentials

## Security Features

### Password Requirements
- Minimum 6 characters
- Hashed using bcrypt with salt
- Never stored in plain text

### Username Requirements
- Minimum 3 characters
- Must be unique

### Email Requirements
- Valid email format
- Must be unique

### Data Isolation
All database queries are automatically filtered by the authenticated user ID:

```python
# Example: Loading transactions
df = transaction_service.get_transactions()
# Only returns transactions for current user
```

### Session Security
- User data stored in Streamlit session state
- Cleared on logout
- Requires re-authentication after logout

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
)
```

### Transactions Table (Updated)
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT,
    account TEXT,
    month TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
```

## API Reference

### AuthManager Class

Located in `core/auth.py`

#### Methods:

**create_user(username, email, password, full_name=None)**
- Creates a new user account
- Returns: `(success: bool, message: str, user_id: int)`

**authenticate_user(username, password)**
- Authenticates a user with credentials
- Returns: `(success: bool, message: str, user_data: dict)`

**change_password(user_id, old_password, new_password)**
- Changes user password
- Returns: `(success: bool, message: str)`

**get_user_by_id(user_id)**
- Retrieves user information
- Returns: `dict` or `None`

### TransactionDB Class (Updated)

Located in `core/database.py`

All methods now accept an optional `user_id` parameter or use the instance `user_id`:

- `save_transactions(df, user_id=None)`
- `load_transactions(..., user_id=None)`
- `get_all_categories(user_id=None)`
- `get_all_accounts(user_id=None)`
- `update_category(description, date, category, user_id=None)`
- `get_statistics(user_id=None)`

### TransactionService Class (Updated)

Located in `core/service.py`

Initialized with user_id:
```python
service = TransactionService(user_id=current_user_id)
```

All operations are automatically scoped to the authenticated user.

## UI Components

### auth_ui Module

Located in `app/auth_ui.py`

**require_auth()**
- Place at the start of your Streamlit app
- Shows login page if not authenticated
- Stops execution until user logs in

**render_user_menu()**
- Displays user profile in sidebar
- Shows logout and change password buttons

**get_current_user_id()**
- Returns the authenticated user's ID
- Used to initialize services

**logout()**
- Clears session and logs out user

## Migration from Unprotected App

If you have existing data in your database without user_id:

1. The system will automatically add a `user_id` column with default value of 1
2. Create a user with ID 1 using `init_auth.py`
3. All existing transactions will be associated with this user
4. New users will have isolated data

## Troubleshooting

### "user_id must be provided" Error
This means you're trying to access data without authentication. Make sure:
1. `require_auth()` is called at the start of your app
2. Service is initialized with `user_id` after authentication

### Can't Login
- Check username and password are correct
- Verify user exists in database: run `init_auth.py` to see all users
- Check database file exists and has correct permissions

### Lost Password
Currently, password reset must be done manually:
1. Use `init_auth.py` to create a new account
2. Or contact your administrator to reset password via database

## Best Practices

1. **Never** commit database files with user data to version control
2. Use strong passwords (min 8+ characters with mixed case, numbers, symbols)
3. Regularly backup your database file
4. Keep `requirements.txt` updated
5. Use environment variables for sensitive configuration

## Future Enhancements

Potential improvements for the authentication system:
- Email-based password reset
- Two-factor authentication (2FA)
- Role-based access control (RBAC)
- OAuth integration (Google, GitHub, etc.)
- Session timeout
- Password complexity requirements
- Account deactivation by users
- Admin dashboard for user management
