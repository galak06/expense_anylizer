# Input Profiles Guide

This guide explains how to use and create input profiles for handling multiple Excel and CSV formats in Curser.

## Overview

Input profiles are YAML configurations that tell Curser how to recognize and parse different bank/credit card export formats. Profiles include:

- **Match rules**: Filename, sheet name, and header patterns
- **Column mappings**: Which columns contain date, description, and amount
- **Transform rules**: How to handle currency symbols, negative amounts, etc.

## Using Existing Profiles

Curser comes with built-in profiles for common Israeli banks:

### Visa/Adi (Max)
```yaml
id: visa_adi_v1
match:
  filename_regex: "(?i)adi|visa|ויזה"
  header_contains: ["תאריך עסקה", "שם בית העסק", "סכום חיוב"]
```

### Bank Leumi
```yaml
id: leumi_charge_v1
match:
  filename_regex: "(?i)leumi|לאומי"
  sheet_regex: "עסקאות במועד החיוב"
```

### Isracard
```yaml
id: isracard_v1
match:
  filename_regex: "(?i)isracard|ישראכרט|max"
```

## Creating Custom Profiles

### Method 1: Using the UI

1. Upload your file in Curser
2. If auto-detection fails, expand **Advanced Mapping**
3. Select correct columns from dropdowns
4. Enter a profile ID and filename pattern
5. Click **Save Profile**

The profile will be saved to `data/profiles.yaml` and auto-applied for future files.

### Method 2: Manual YAML

Create a new profile in `data/profiles.yaml`:

```yaml
- id: my_bank_v1                    # Unique identifier
  match:
    filename_regex: "(?i)my_bank"   # Case-insensitive filename match
    header_contains: ["date", "amt"] # Required header tokens
  columns:
    date: ["Transaction Date", "Date"]         # Try these columns for date
    description: ["Details", "Merchant Name"]  # Try these for description
    amount: ["Amount", "Debit", "Credit"]     # Try these for amount
  header_row: 2                      # Optional: header is on row 2 (0-indexed)
  data_start_row: 3                  # Optional: data starts on row 3
  amount_rules:
    parentheses_to_negative: true    # Convert (123) -> -123
  transforms:
    strip_currency: ["$", "₪"]       # Remove these symbols
    unicode_minus: true              # Convert − to -
```

## Regex Cheat Sheet

### Common Patterns

| Pattern | Matches |
|---------|---------|
| `(?i)leumi` | "leumi", "LEUMI", "Leumi" (case-insensitive) |
| `visa\|max` | "visa" OR "max" |
| `bank.*2024` | "bank" followed by anything, then "2024" |
| `^export_` | Starts with "export_" |
| `\.xlsx$` | Ends with ".xlsx" |

### Hebrew Patterns

```yaml
filename_regex: "(?i)לאומי|leumi"          # Match Hebrew or English
sheet_regex: "עסקאות.*חיוב"               # Partial sheet name match
header_contains: ["תאריך", "סכום"]         # Must have both headers
```

## Column Hints

Profiles list multiple possible column names. Curser tries them in order:

```yaml
columns:
  date: ["תאריך עסקה", "תאריך", "date"]      # Try Hebrew first, then English
  amount: ["סכום חיוב", "סכום", "amount"]
```

## Header Recovery

Some exports have metadata rows before the header:

```
Row 0: Bank Name
Row 1: Account Number
Row 2: [EMPTY]
Row 3: Date | Description | Amount    <- Actual header
Row 4: 01/01/2024 | Store | 100       <- Data starts here
```

Set `header_row: 3` and `data_start_row: 4` in the profile.

## Amount Rules

### Negative Amounts

```yaml
amount_rules:
  sign_logic: negative_on_debit           # Expenses are negative
  parentheses_to_negative: true           # (100) -> -100
```

### Currency Cleaning

```yaml
transforms:
  strip_currency: ["₪", "$", ","]         # Remove these before parsing
  unicode_minus: true                     # Normalize minus signs
```

## Troubleshooting

### Profile Not Matching

**Problem**: File uploads but profile isn't applied.

**Solutions**:
1. Check `filename_regex` matches your filename
2. Verify `header_contains` tokens exist in headers (case-sensitive)
3. For Excel: check `sheet_regex` matches sheet name

### Wrong Columns Detected

**Problem**: Auto-detection picks wrong columns.

**Solutions**:
1. Add more specific column hints to profile
2. Use `header_row` if headers are on non-standard row
3. Use Advanced Mapping UI to manually select and save

### All Columns are "Unnamed"

**Problem**: Excel file shows "Unnamed: 0", "Unnamed: 1"...

**Solutions**:
- Set `header_row` to the actual header row number (0-indexed)
- Curser will automatically try to recover headers from first 10 rows

### Encoding Errors (CSV)

**Problem**: Hebrew text appears as gibberish.

**Solutions**:
- Curser tries `utf-8`, `cp1255`, `iso-8859-8`, `windows-1255` automatically
- If still failing, convert CSV to Excel (XLSX) format

## Testing Profiles

After creating a profile, test it:

```bash
# Run tests
pytest tests/test_profiles_match.py -v

# Test with fixture
python -c "
from core.io import load_transactions
df = load_transactions('tests/fixtures/visa_sample.csv')
print(df.head())
"
```

## Profile Priority

When multiple profiles match:
1. First match wins
2. More specific patterns (longer regex) recommended
3. Put more specific profiles before generic ones

```yaml
profiles:
  - id: specific_bank_v1        # This matches first
    match:
      filename_regex: "(?i)special_bank_credit"

  - id: generic_bank_v1         # This matches second
    match:
      filename_regex: "(?i)bank"
```

## Examples

### Example 1: Bank with Header Row 5

```yaml
- id: custom_bank_v1
  match:
    filename_regex: "(?i)mybank"
  columns:
    date: ["Trans Date"]
    description: ["Merchant"]
    amount: ["Amt"]
  header_row: 5              # Header is on row 5
  data_start_row: 6          # Data starts on row 6
```

### Example 2: Multi-Sheet Excel

```yaml
- id: bank_statements_v1
  match:
    filename_regex: "(?i)statement"
    sheet_regex: "(?i)transactions"    # Only match "Transactions" sheet
  columns:
    date: ["Date"]
    description: ["Description"]
    amount: ["Amount"]
```

### Example 3: Pepper-style Format

```yaml
- id: pepper_v1
  match:
    filename_regex: "(?i)pepper"
  columns:
    date: ["תאריך רכישה"]
    description: ["שם בית עסק"]
    amount: ["סכום"]
  amount_rules:
    parentheses_to_negative: true
  transforms:
    strip_currency: ["₪", ","]
    unicode_minus: true
```

## Best Practices

1. **Use descriptive IDs**: `bank_name_version` format
2. **Test regex patterns**: Use [regex101.com](https://regex101.com/)
3. **Add header_contains**: Improves match reliability
4. **Multiple column hints**: List both Hebrew and English names
5. **Version profiles**: Add `_v1`, `_v2` when format changes
6. **Document changes**: Add comments in YAML

## Support

For issues or questions:
- Check logs in Streamlit app
- Run tests: `pytest tests/ -v`
- GitHub issues: [Report a problem](https://github.com/your-repo/issues)
