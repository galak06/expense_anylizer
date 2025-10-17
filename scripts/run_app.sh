#!/bin/bash
# Script to run the Curser Expense Analyzer

echo "🚀 Starting Curser Expense Analyzer..."

# Activate virtual environment
source .venv/bin/activate

# Start the application
python3 -m streamlit run app/streamlit_app.py --server.port 8501 --server.address localhost --server.headless true
