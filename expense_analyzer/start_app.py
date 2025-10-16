#!/usr/bin/env python3
"""
Startup script for Curser expense analyzer.
"""
import subprocess
import sys
import os

def main():
    """Start the Streamlit application."""
    print("🚀 Starting Curser Expense Analyzer...")
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Check if streamlit is installed
    try:
        import streamlit
        print("✅ Streamlit is installed")
    except ImportError:
        print("❌ Streamlit not found. Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Start the app
    app_path = os.path.join(project_dir, "app", "streamlit_app.py")
    print(f"📱 Starting app from: {app_path}")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", "8501",
        "--server.address", "localhost"
    ])

if __name__ == "__main__":
    main()
