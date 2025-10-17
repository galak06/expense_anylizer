import pandas as pd
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process
import openai
from .model import MatchResult, MappingRow
from .config import get_settings


def load_mapping(mapping_path: Optional[str] = None) -> List[MappingRow]:
    settings = get_settings()
    if mapping_path is None:
        mapping_path = settings.default_mapping_path
    try:
        df = pd.read_csv(mapping_path)
        return [
            MappingRow(
                keyword=str(row['keyword']).strip().lower(),
                category=str(row['category']).strip()
            )
            for _, row in df.iterrows()
        ]
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error loading mapping file: {e}")
        return []


def save_mapping(mappings: List[MappingRow], mapping_path: Optional[str] = None) -> None:
    settings = get_settings()
    if mapping_path is None:
        mapping_path = settings.default_mapping_path

    df = pd.DataFrame([(m.keyword, m.category) for m in mappings], columns=['keyword', 'category'])
    df.drop_duplicates().to_csv(mapping_path, index=False)


def keyword_match(description: str, mappings: List[MappingRow]) -> MatchResult:
    settings = get_settings()
    desc_lower = description.lower()

    for mapping in mappings:
        if mapping.keyword in desc_lower:
            return MatchResult(
                category=mapping.category,
                strategy='keyword',
                confidence=settings.keyword_confidence,
                keyword_used=mapping.keyword,
                note=f"Exact keyword match: {mapping.keyword}"
            )

    return MatchResult(
        category=None,
        strategy='keyword',
        confidence=0.0,
        note="No keyword matches found"
    )


def fuzzy_match(description: str, vendor_to_cat: Dict[str, str], threshold: Optional[int] = None) -> MatchResult:
    settings = get_settings()
    if threshold is None:
        threshold = settings.fuzzy_match_threshold
    if not vendor_to_cat:
        return MatchResult(
            category=None,
            strategy='fuzzy',
            confidence=0.0,
            note="No vendor mappings available"
        )

    potential_vendor = ' '.join(description.split()[:3])

    result = process.extractOne(
        potential_vendor,
        vendor_to_cat.keys(),
        scorer=fuzz.WRatio,
        score_cutoff=threshold
    )

    if result:
        vendor, score, _ = result
        return MatchResult(
            category=vendor_to_cat[vendor],
            strategy='fuzzy',
            confidence=score / 100.0,
            keyword_used=vendor,
            note=f"Fuzzy match: {vendor} (score: {score})"
        )

    return MatchResult(
        category=None,
        strategy='fuzzy',
        confidence=0.0,
        note=f"No fuzzy matches above threshold {threshold}"
    )


def llm_match(description: str, categories: List[str], api_key: Optional[str] = None) -> MatchResult:
    settings = get_settings()

    if not api_key:
        api_key = settings.openai_api_key

    if not api_key:
        return MatchResult(
            category=None,
            strategy='llm',
            confidence=0.0,
            note="No API key provided for LLM"
        )

    try:
        # Use new OpenAI API (>= 1.0.0)
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        categories_str = ", ".join(categories)
        prompt = f"""Categorize this transaction description into one of these categories: {categories_str}

Transaction: "{description}"

IMPORTANT: You must return EXACTLY one category name from the list above. If any categories are in Hebrew, return the Hebrew name exactly as it appears. Return only the category name, nothing else."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.1
        )

        suggested_category = response.choices[0].message.content.strip()

        if suggested_category in categories:
            return MatchResult(
                category=suggested_category,
                strategy='llm',
                confidence=settings.llm_confidence,
                note=f"LLM suggestion: {suggested_category}"
            )

        return MatchResult(
            category=None,
            strategy='llm',
            confidence=0.0,
            note=f"LLM returned invalid category: {suggested_category}"
        )

    except Exception as e:
        return MatchResult(
            category=None,
            strategy='llm',
            confidence=0.0,
            note=f"LLM error: {str(e)}"
        )


def agent_choose_category(
    description: str,
    mappings: List[MappingRow],
    vendor_to_cat: Dict[str, str],
    categories: List[str],
    llm_api_key: Optional[str] = None,
    fuzzy_threshold: Optional[int] = None
) -> MatchResult:
    settings = get_settings()

    keyword_result = keyword_match(description, mappings)
    if keyword_result.confidence >= 0.9:
        return keyword_result

    fuzzy_result = fuzzy_match(description, vendor_to_cat, fuzzy_threshold)
    if fuzzy_result.confidence >= settings.fuzzy_confidence_threshold:
        return fuzzy_result

    if llm_api_key:
        llm_result = llm_match(description, categories, llm_api_key)
        if llm_result.confidence >= 0.7:
            return llm_result

    results = [keyword_result, fuzzy_result]
    if llm_api_key:
        results.append(llm_match(description, categories, llm_api_key))

    return max(results, key=lambda r: r.confidence)


def build_vendor_map(df: pd.DataFrame, desc_col: str = 'Description', cat_col: str = 'Category') -> Dict[str, str]:
    vendor_map = {}

    for _, row in df.iterrows():
        if pd.notna(row[cat_col]) and pd.notna(row[desc_col]):
            vendor = ' '.join(str(row[desc_col]).split()[:3]).lower()

            if vendor and len(vendor) > 2:
                vendor_map[str(row[desc_col]).lower()] = str(row[cat_col])

    return vendor_map


def apply_categorization(
    df: pd.DataFrame,
    mappings: List[MappingRow],
    vendor_to_cat: Dict[str, str],
    categories: List[str],
    llm_api_key: Optional[str] = None,
    fuzzy_threshold: Optional[int] = None,
    only_uncategorized: bool = True
) -> pd.DataFrame:
    result_df = df.copy()

    for idx, row in result_df.iterrows():
        if only_uncategorized and pd.notna(row.get('Category')):
            continue

        description = str(row.get('Description', ''))
        if not description:
            continue

        match_result = agent_choose_category(
            description, mappings, vendor_to_cat, categories,
            llm_api_key, fuzzy_threshold
        )

        if match_result.confidence >= 0.7:
            result_df.at[idx, 'Category'] = match_result.category

    return result_df


def learn_from_user_feedback(
    description: str,
    category: str,
    mappings: List[MappingRow],
    vendor_to_cat: Dict[str, str],
    mapping_path: Optional[str] = None
) -> Tuple[List[MappingRow], Dict[str, str]]:
    settings = get_settings()
    words = description.lower().split()

    for word in words:
        if len(word) > settings.min_word_length:
            new_mapping = MappingRow(keyword=word, category=category)
            if new_mapping not in mappings:
                mappings.append(new_mapping)

    vendor = ' '.join(words[:3])
    if vendor:
        vendor_to_cat[vendor] = category

    save_mapping(mappings, mapping_path)

    return mappings, vendor_to_cat
