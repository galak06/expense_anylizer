# Curser - Expense Analyzer

A privacy-first personal finance tool that ingests bank/credit-card exports, provides powerful filtering, and uses an intelligent agent to suggest expense categories with continuous learning.

## Features

- **Multi-format Import**: Supports XLSX/CSV exports from multiple providers (Bank Leumi, Visa/Max, Isracard, and generic CSVs)
- **Hebrew/RTL Support**: Normalizes Hebrew text and RTL formatting
- **Smart Categorization**: Three-tier agent system (keyword → fuzzy → LLM)
- **Continuous Learning**: Learns from user confirmations and improves over time
- **Powerful Filtering**: Date range, amount, text search, category filters
- **Rich Analytics**: Monthly summaries, category breakdowns, top vendors
- **Export Options**: Clean CSV exports for all data and summaries

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key (optional)
   ```

3. **Run the Application**:
   ```bash
   streamlit run app/streamlit_app.py
   ```

4. **Upload Your Data**:
   - Upload CSV or XLSX files from your bank/credit card
   - The app will auto-detect columns (Date, Description, Amount)
   - Supports Hebrew column names and mixed Hebrew/English data

5. **Categorize Expenses**:
   - Use the built-in keyword mappings
   - Apply fuzzy matching for similar vendor names
   - Optionally use OpenAI API for LLM-powered suggestions
   - Accept/reject suggestions to train the system

## Architecture

```
curser/
├─ app/                      # Streamlit UI
├─ core/                     # Core business logic
│  ├─ io.py                  # File reading & column detection
│  ├─ clean.py               # Data normalization
│  ├─ map.py                 # Categorization agent
│  ├─ agg.py                 # Aggregations & analytics
│  └─ model.py               # Data models
├─ data/
│  └─ mapping.csv            # Keyword→category mappings
└─ tests/                    # Unit tests
```

## Multi-Format Input Support

Curser uses a profile-based adapter system to handle various bank and credit card export formats:

- **Profile matching**: Automatic detection based on filename, sheet name, and headers
- **Heuristic fallback**: Robust column detection when no profile matches
- **Advanced mapping**: Manual column selection with profile saving
- **Header recovery**: Automatic detection of header rows in complex Excel files

### Supported Formats

Built-in profiles for:
- Visa/Adi (Max)
- Bank Leumi
- Isracard
- Generic CSV/XLSX

See [Input Profiles Guide](docs/INPUT_PROFILES.md) for details on creating custom profiles.

## 📚 Documentation

All project documentation is organized in the [`docs/`](docs/) folder:

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get started quickly
- **[Deployment Plan](docs/DEPLOYMENT_PLAN.md)** - Complete Render deployment guide
- **[Authentication Setup](docs/AUTHENTICATION.md)** - User authentication system
- **[Docker Setup](docs/DOCKER.md)** - Container deployment
- **[Security Guide](docs/SECURITY_IMPLEMENTATION.md)** - Security features
- **[Full Documentation Index](docs/README.md)** - Complete documentation overview

## Categorization Agent

The system uses a three-tier approach:

1. **Keyword Matching** (95% confidence): Exact substring matches from `mapping.csv`
2. **Fuzzy Matching** (86%+ confidence): Similar vendor names using RapidFuzz
3. **LLM Matching** (75% confidence): OpenAI GPT for complex descriptions

## Configuration

All configuration is managed through `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key for LLM categorization |
| `DEFAULT_MAPPING_PATH` | `data/mapping.csv` | Path to keyword mappings |
| `FUZZY_MATCH_THRESHOLD` | `86` | Threshold for fuzzy matching (70-95) |
| `MIN_WORD_LENGTH` | `3` | Minimum word length for keywords |
| `KEYWORD_CONFIDENCE` | `0.95` | Confidence for keyword matches |
| `FUZZY_CONFIDENCE_THRESHOLD` | `0.8` | Threshold for fuzzy matches |
| `LLM_CONFIDENCE` | `0.75` | Confidence for LLM matches |

See `.env.example` for full configuration options.

## Data Privacy

- All processing happens locally in your session
- No data is sent to external services unless you provide an LLM API key
- Mapping rules are stored locally in `data/mapping.csv`

## Supported File Formats

- **CSV**: Comma, semicolon, or tab-separated
- **XLSX**: Excel files
- **Encodings**: UTF-8, CP1255, ISO-8859-8, Windows-1255
- **Column Detection**: Auto-detects Date, Description, Amount columns
- **Hebrew Support**: Full RTL and Hebrew text normalization

## Example Usage

```python
from core.io import load_transactions
from core.clean import normalize_df
from core.map import apply_categorization

# Load and clean data
df = load_transactions('bank_export.csv')
df = normalize_df(df)

# Apply categorization
categorized_df = apply_categorization(df)

# Export results
categorized_df.to_csv('categorized_expenses.csv', index=False)
```

## Development

Run tests:
```bash
python -m pytest tests/
```

## License

MIT License - see LICENSE file for details.
