# Quick Start Guide - Authentication

This guide will help you get started with the secure, authenticated version of the Expense Analyzer app.

## 🚀 Getting Started in 3 Steps

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs the new authentication dependencies:
- `bcrypt` - For secure password hashing
- `extra-streamlit-components` - For enhanced UI

### Step 2: Create Your First User

Run the initialization script:

```bash
python init_auth.py
```

Follow the prompts to create your admin/first user:
- Choose a username (min 3 characters)
- Enter a valid email address
- Enter your full name (optional)
- Create a secure password (min 6 characters)

### Step 3: Start the App

```bash
streamlit run app/streamlit_app.py
```

or

```bash
python start_app.py
```

## 🔐 Login

When you open the app, you'll see the login page:

1. **Login Tab**: Enter your username and password
2. **Sign Up Tab**: Create a new account if needed

## ✨ Key Features

### Secure Login
- Passwords are encrypted with bcrypt
- Never stored in plain text
- Session-based authentication

### Data Isolation
- Each user sees only their own transactions
- No cross-user data leakage
- Database-level security

### User Management
- **Change Password**: Click "🔑 Change Password" in the sidebar
- **Logout**: Click "🚪 Logout" to end your session
- **View Profile**: See your account info in the sidebar

## 📊 Using the App

Once logged in, everything works the same way:

1. **Upload Files**: Import your bank/credit card statements
2. **Categorize**: Auto-categorize or manually assign categories
3. **Analyze**: View dashboards and spending trends
4. **Export**: Download your transaction data

**Important**: All your data is private and isolated from other users.

## 👥 Multiple Users

### Creating Additional Users

Option 1: **Self-Registration**
- Users can sign up through the "Sign Up" tab on the login page

Option 2: **Admin Creation**
- Run `python init_auth.py` to create users via command line

### Each User Gets
- Their own private transaction database
- Independent categories and mappings
- Separate transaction history
- Personal account information

## 🔧 Troubleshooting

### Can't Login?
- Verify your username and password
- Check caps lock is off
- Make sure you created a user with `init_auth.py`

### Forgot Password?
Currently, password reset requires:
1. Running `init_auth.py` to create a new account, OR
2. Having another admin user reset it for you

### "user_id must be provided" Error?
This means authentication isn't working:
1. Make sure you're on the login page first
2. Try refreshing your browser
3. Check that `app/auth_ui.py` exists

### Existing Data Not Showing?
If you had transactions before adding authentication:
1. They're associated with user_id = 1 by default
2. Create a user and it will have ID 1
3. That user will see all existing data

## 🔒 Security Best Practices

1. **Use Strong Passwords**
   - Min 8+ characters
   - Mix of uppercase, lowercase, numbers, symbols

2. **Don't Share Credentials**
   - Each person should have their own account

3. **Backup Your Database**
   - Regularly backup `data/transactions.db`

4. **Keep Dependencies Updated**
   - Run `pip install --upgrade -r requirements.txt` periodically

## 📁 File Structure

```
expense_anylizer/
├── core/
│   ├── auth.py              # Authentication logic
│   ├── database.py          # Database with user isolation
│   ├── service.py           # Business logic with auth
│   └── ...
├── app/
│   ├── streamlit_app.py     # Main app (now with auth)
│   ├── auth_ui.py           # Login/signup UI components
│   └── ...
├── init_auth.py             # User creation script
├── AUTHENTICATION.md        # Detailed auth documentation
└── requirements.txt         # Updated with auth deps
```

## 🎯 Next Steps

- Read [AUTHENTICATION.md](AUTHENTICATION.md) for detailed documentation
- Set up multiple user accounts if needed
- Configure your profiles in `data/profiles.yaml`
- Start importing and analyzing your expenses!

## 💡 Tips

- **Logout when done**: Especially on shared computers
- **Change password regularly**: Use "🔑 Change Password" in sidebar
- **Create accounts for family members**: Each person gets private data
- **Check your profile**: Username and email shown in sidebar

## 🆘 Need Help?

See the full documentation in [AUTHENTICATION.md](AUTHENTICATION.md) for:
- Detailed API reference
- Database schema
- Migration guide
- Advanced troubleshooting
- Security features
