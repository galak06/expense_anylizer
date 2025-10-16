"""
Profile loader and matcher for multi-format input support.
"""
import re
import yaml
from typing import Dict, Any, Optional, List
import pandas as pd


def load_profiles(path: str = "data/profiles.yaml") -> Dict[str, Any]:
    """Load profiles from YAML file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            data.setdefault("profiles", [])
            return data
    except FileNotFoundError:
        return {"profiles": []}


def match_profile(file_name: str, sheet_name: Optional[str], df: pd.DataFrame, profiles: Dict[str, Any]) -> Optional[dict]:
    """Match a file to a profile based on filename, sheet name, and headers."""
    for profile in profiles.get("profiles", []):
        match_rules = profile.get("match", {})
        matches = True
        
        # Check filename regex
        if match_rules.get("filename_regex"):
            if not re.search(match_rules["filename_regex"], file_name):
                matches = False
                continue
        
        # Check sheet regex
        if match_rules.get("sheet_regex") and sheet_name is not None:
            if not re.search(match_rules["sheet_regex"], sheet_name):
                matches = False
                continue
        
        # Check header contains
        header_contains = match_rules.get("header_contains", [])
        if header_contains:
            # Try to find the header row
            header_row = None
            for i in range(min(len(df), 10)):  # Check first 10 rows
                row = df.iloc[i]
                # Count non-null and non-empty values
                non_empty_count = sum(1 for val in row if pd.notna(val) and str(val).strip() != '')
                if non_empty_count >= 3:  # At least 3 non-empty values
                    header_row = i
                    break
            
            if header_row is not None:
                header_values = df.iloc[header_row].tolist()
                for token in header_contains:
                    if not any(token in str(val) for val in header_values):
                        matches = False
                        break
            else:
                # Fallback to checking column names
                for token in header_contains:
                    if not any(token in str(col) for col in df.columns):
                        matches = False
                        break
        
        if matches:
            return profile
    
    return None


def get_column_hints(profile: dict) -> Dict[str, List[str]]:
    """Extract column hints from a profile."""
    return profile.get("columns", {})


def get_header_row(profile: dict) -> Optional[int]:
    """Get the header row number from profile, if specified."""
    return profile.get("header_row")


def get_data_start_row(profile: dict) -> Optional[int]:
    """Get the data start row number from profile, if specified."""
    return profile.get("data_start_row")


def get_amount_rules(profile: dict) -> Dict[str, Any]:
    """Get amount processing rules from profile."""
    return profile.get("amount_rules", {})


def get_transforms(profile: dict) -> Dict[str, Any]:
    """Get data transformation rules from profile."""
    return profile.get("transforms", {})


def save_profile(profile: dict, path: str = "data/profiles.yaml") -> None:
    """Save a new profile to the YAML file, avoiding duplicates."""
    profiles_data = load_profiles(path)
    profiles_list = profiles_data.get("profiles", [])
    
    # Check if profile with same ID already exists
    existing_ids = [p.get("id") for p in profiles_list]
    if profile.get("id") not in existing_ids:
        profiles_list.append(profile)
        profiles_data["profiles"] = profiles_list
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(profiles_data, f, default_flow_style=False, allow_unicode=True)
