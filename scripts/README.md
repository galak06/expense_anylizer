# Scripts Directory

This directory contains all utility and helper scripts for the Curser Expense Analyzer project.

## 📋 Script Overview

### **Authentication Scripts**
- **`create_user.py`** - Create new user accounts for the application
- **`init_auth.py`** - Initialize the authentication system and database
- **`reset_password.py`** - Reset user passwords

### **Database Scripts**
- **`migrate_db.py`** - Database migration and schema updates
- **`delete_by_criteria.py`** - Delete transactions based on specific criteria
- **`delete_transactions.py`** - Bulk delete transaction data

### **Application Scripts**
- **`start_app.py`** - Start the Streamlit application with proper configuration
- **`run_app.sh`** - Shell script to start the application with virtual environment
- **`run_tests.py`** - Run the test suite for the application

### **Deployment Scripts**
- **`setup_ssl.sh`** - Setup SSL certificates for secure connections

## 🚀 Usage

### **Running Scripts**

All scripts should be run from the project root directory:

```bash
# Authentication
python3 scripts/create_user.py
python3 scripts/init_auth.py
python3 scripts/reset_password.py

# Database operations
python3 scripts/migrate_db.py
python3 scripts/delete_by_criteria.py
python3 scripts/delete_transactions.py

# Application
python3 scripts/start_app.py
./scripts/run_app.sh
python3 scripts/run_tests.py

# SSL Setup
./scripts/setup_ssl.sh
```

### **Prerequisites**

- Python 3.9+ installed
- Virtual environment activated (`.venv`)
- Dependencies installed (`pip install -r requirements.txt`)

## 📝 Notes

- Most scripts require the virtual environment to be activated
- Database scripts may require existing data to be present
- SSL setup script requires appropriate permissions
- Test scripts should be run in a clean environment

## 🔧 Maintenance

When adding new utility scripts:
1. Place them in this `scripts/` directory
2. Update this README with script description
3. Ensure proper permissions are set (`chmod +x` for shell scripts)
4. Test scripts from the project root directory
