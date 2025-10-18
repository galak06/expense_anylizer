import pandas as pd
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process
import openai
from collections import Counter
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


def normalize_vendor_name(description: str) -> str:
    """Normalize vendor name for better matching by removing common suffixes and extra whitespace."""
    # Remove common suffixes in Hebrew and English
    suffixes = ['בע"מ', 'בעמ', "בע''מ", 'ltd', 'inc', 'llc', 'corp', 'limited', 'corporation']
    desc_lower = description.lower()
    
    for suffix in suffixes:
        desc_lower = desc_lower.replace(suffix, '')
    
    # Remove extra whitespace and normalize
    return ' '.join(desc_lower.split())


def keyword_match(description: str, mappings: List[MappingRow]) -> MatchResult:
    """Enhanced keyword matching with word boundary detection and phrase matching."""
    settings = get_settings()
    desc_lower = description.lower()
    desc_words = set(desc_lower.split())
    
    best_match = None
    best_score = 0
    
    for mapping in mappings:
        keyword = mapping.keyword.lower()
        score = 0
        
        # Handle negative keywords (exclusion patterns)
        if keyword.startswith('!'):
            if keyword[1:] in desc_lower:
                continue  # Skip this description entirely
        
        # Multi-word phrase matching (higher priority)
        if ' ' in keyword:
            if keyword in desc_lower:
                # Score based on phrase length - longer phrases are more specific
                word_count = len(keyword.split())
                score = min(0.95 + (word_count * 0.01), 0.98)
        else:
            # Single word matching with word boundaries
            if keyword in desc_words:
                score = 0.95
            # Also check if it's part of a larger word (but with lower confidence)
            elif keyword in desc_lower and len(keyword) > 4:
                score = 0.85
        
        if score > best_score:
            best_score = score
            best_match = mapping
    
    if best_match:
        return MatchResult(
            category=best_match.category,
            strategy='keyword',
            confidence=best_score,
            keyword_used=best_match.keyword,
            note=f"Keyword match: {best_match.keyword} (confidence: {best_score:.2f})"
        )
    
    return MatchResult(
        category=None,
        strategy='keyword',
        confidence=0.0,
        note="No keyword matches found"
    )


def fuzzy_match(description: str, vendor_to_cat: Dict[str, str], threshold: Optional[int] = None) -> MatchResult:
    """Improved fuzzy matching with multiple word combinations and normalization."""
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

    # Normalize description
    desc_normalized = normalize_vendor_name(description)
    words = desc_normalized.split()
    
    # Try multiple word combinations to catch vendor names in different positions
    candidates = []
    if len(words) >= 2:
        candidates.append(' '.join(words[:2]))
    if len(words) >= 3:
        candidates.append(' '.join(words[:3]))
    if len(words) >= 4:
        candidates.append(' '.join(words[:4]))
        candidates.append(' '.join(words[1:4]))  # Skip first word
    
    # Also try the full description for short descriptions
    if len(words) <= 3:
        candidates.append(desc_normalized)
    
    best_result = None
    best_score = 0
    best_vendor = None
    
    for candidate in candidates:
        if not candidate.strip():
            continue
        
        # Use token_set_ratio for better partial matching
        result = process.extractOne(
            candidate,
            vendor_to_cat.keys(),
            scorer=fuzz.token_set_ratio,
            score_cutoff=threshold
        )
        
        if result and result[1] > best_score:
            best_score = result[1]
            best_result = result
            best_vendor = candidate
    
    if best_result:
        vendor, score, _ = best_result
        # Adjust confidence based on match quality (cap at 0.9 for fuzzy matches)
        confidence = min(score / 100.0, 0.9)
        
        # Boost confidence for very high scores
        if score >= 95:
            confidence = min(confidence * 1.05, 0.95)
        
        return MatchResult(
            category=vendor_to_cat[vendor],
            strategy='fuzzy',
            confidence=confidence,
            keyword_used=vendor,
            note=f"Fuzzy match: '{vendor}' from '{best_vendor}' (score: {score})"
        )

    return MatchResult(
        category=None,
        strategy='fuzzy',
        confidence=0.0,
        note=f"No fuzzy matches above threshold {threshold}"
    )


def llm_match(description: str, categories: List[str], api_key: Optional[str] = None, 
              amount: Optional[float] = None, date: Optional[str] = None) -> MatchResult:
    """Enhanced LLM matching with context-aware prompting."""
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

        # Build context-aware prompt
        context = f"Transaction: {description}"
        if amount is not None:
            context += f"\nAmount: {amount}"
        if date:
            context += f"\nDate: {date}"
        
        categories_str = ", ".join(categories)
        prompt = f"""You are a financial transaction categorization expert.

{context}

Available categories: {categories_str}

Instructions:
1. Analyze the transaction description carefully
2. Consider the merchant name, transaction type, and any provided context
3. Return EXACTLY ONE category name from the list above
4. If categories are in Hebrew, return the Hebrew name exactly as shown
5. Return ONLY the category name, nothing else

Category:"""

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
    fuzzy_threshold: Optional[int] = None,
    amount: Optional[float] = None,
    date: Optional[str] = None
) -> MatchResult:
    """Enhanced category selection with multi-strategy voting and confidence boosting."""
    settings = get_settings()

    # Get all strategy results
    keyword_result = keyword_match(description, mappings)
    fuzzy_result = fuzzy_match(description, vendor_to_cat, fuzzy_threshold)
    llm_result = None
    if llm_api_key:
        llm_result = llm_match(description, categories, llm_api_key, amount, date)
    
    # Collect all results
    results = [keyword_result, fuzzy_result]
    if llm_result:
        results.append(llm_result)
    
    # Check for agreement between strategies (confidence boost)
    categories_suggested = [r.category for r in results if r.category]
    if len(categories_suggested) >= 2:
        category_counts = Counter(categories_suggested)
        most_common = category_counts.most_common(1)[0]
        if most_common[1] >= 2:  # At least 2 strategies agree
            # Boost confidence for agreeing strategies
            for result in results:
                if result.category == most_common[0]:
                    result.confidence = min(result.confidence * 1.2, 0.98)
    
    # Return highest confidence result
    best_result = max(results, key=lambda r: r.confidence)
    
    # Apply minimum confidence threshold
    if best_result.confidence < 0.7:
        return MatchResult(
            category=None,
            strategy='none',
            confidence=0.0,
            note="No high-confidence match found (all strategies below 0.7 threshold)"
        )
    
    return best_result


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

        # Extract context for enhanced categorization
        amount = row.get('Amount')
        date = row.get('Date')
        if hasattr(date, 'strftime'):
            date = date.strftime('%Y-%m-%d')
        elif date is not None:
            date = str(date)

        match_result = agent_choose_category(
            description, mappings, vendor_to_cat, categories,
            llm_api_key, fuzzy_threshold, amount, date
        )

        if match_result.confidence >= 0.7:
            result_df.at[idx, 'Category'] = match_result.category

    return result_df


def learn_from_user_feedback(
    description: str,
    category: str,
    mappings: List[MappingRow],
    vendor_to_cat: Dict[str, str],
    mapping_path: Optional[str] = None,
    confidence: float = 1.0
) -> Tuple[List[MappingRow], Dict[str, str]]:
    """Smarter learning mechanism that extracts meaningful keywords and avoids noise."""
    settings = get_settings()
    
    # Hebrew and English stopwords to avoid learning
    stopwords = {
        # Hebrew
        'של', 'את', 'על', 'עם', 'אל', 'מן', 'כי', 'אם', 'לא', 'או', 'גם', 'רק',
        # English
        'the', 'and', 'for', 'with', 'from', 'ltd', 'inc', 'llc', 'corp', 'limited',
        # Hebrew company suffixes
        'בע"מ', 'בעמ', "בע''מ", 'בעמ', 'חפ', 'עמ', 'ושות',
        # Common words
        'company', 'corporation', 'group', 'international'
    }
    
    words = description.lower().split()
    
    # Extract vendor name (first 2-3 meaningful words)
    vendor_words = []
    for word in words[:5]:  # Check first 5 words
        # Clean word
        word_clean = word.strip('.,;:!?()[]{}"\'-')
        if len(word_clean) > 2 and word_clean not in stopwords:
            vendor_words.append(word_clean)
            if len(vendor_words) >= 3:
                break
    
    # Add vendor phrase to mappings (more specific than individual words)
    if vendor_words:
        # Add 2-word and 3-word phrases
        if len(vendor_words) >= 2:
            vendor_phrase_2 = ' '.join(vendor_words[:2])
            new_mapping_2 = MappingRow(keyword=vendor_phrase_2, category=category)
            if not any(m.keyword == vendor_phrase_2 for m in mappings):
                mappings.append(new_mapping_2)
        
        if len(vendor_words) >= 3:
            vendor_phrase_3 = ' '.join(vendor_words[:3])
            new_mapping_3 = MappingRow(keyword=vendor_phrase_3, category=category)
            if not any(m.keyword == vendor_phrase_3 for m in mappings):
                mappings.append(new_mapping_3)
        
        # Also add single most distinctive word if it's long enough
        for word in vendor_words:
            if len(word) > 5:  # Only longer, more distinctive words
                new_mapping = MappingRow(keyword=word, category=category)
                if not any(m.keyword == word for m in mappings):
                    mappings.append(new_mapping)
                break  # Only add one single word
    
    # Update vendor map with normalized name
    vendor_key = ' '.join(words[:3])
    if vendor_key:
        vendor_to_cat[vendor_key] = category
    
    # Also add normalized version
    normalized_key = normalize_vendor_name(' '.join(words[:3]))
    if normalized_key and normalized_key != vendor_key:
        vendor_to_cat[normalized_key] = category
    
    save_mapping(mappings, mapping_path)
    
    return mappings, vendor_to_cat
