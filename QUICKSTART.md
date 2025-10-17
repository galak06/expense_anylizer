# Curser - Quick Start Guide

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python start_app.py
```
Or directly with Streamlit:
```bash
streamlit run app/streamlit_app.py
```

### 3. Upload Your Data
- Upload CSV or XLSX files from your bank/credit card
- The app auto-detects columns (Date, Description, Amount)
- Supports Hebrew column names and mixed Hebrew/English data

### 4. Use the Features
- **Filter**: Date range, amount, text search, categories
- **Categorize**: Accept/reject AI suggestions to train the system
- **Export**: Download categorized data and summaries
- **Learn**: System improves with each user interaction

## 📊 Sample Data
Test with the included sample file: `tests/fixtures/sample_bank_export.csv`

## 🧪 Run Tests
```bash
python run_tests.py
```

## 🏗️ Architecture
- **Core modules**: Business logic for I/O, cleaning, categorization, aggregation
- **Streamlit UI**: Web interface for file upload and visualization
- **Three-tier agent**: Keyword → Fuzzy → LLM categorization
- **Privacy-first**: All processing happens locally

## 🔧 Configuration
- Set `OPENAI_API_KEY` environment variable for LLM features
- Adjust fuzzy matching threshold in the UI
- Customize categories in the sidebar

## 📁 Project Structure
```
curser/
├─ app/streamlit_app.py     # Main UI
├─ core/                    # Business logic
├─ data/mapping.csv         # Keyword mappings
├─ tests/                   # Unit tests
└─ requirements.txt         # Dependencies
```

## 🎯 Key Features
✅ Multi-format file import (CSV/XLSX)  
✅ Hebrew/RTL text support  
✅ Smart categorization with learning  
✅ Rich analytics and visualizations  
✅ Export capabilities  
✅ Privacy-first design  
✅ Comprehensive test coverage  

Ready to analyze your expenses! 💰
