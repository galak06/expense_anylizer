"""
AI-powered financial analysis and recommendations module.
"""
import pandas as pd
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import openai
from core.config import get_settings


def generate_ai_insights(df: pd.DataFrame, api_key: str) -> Dict[str, Any]:
    """
    Generate AI-powered insights and recommendations per account.
    
    Args:
        df: DataFrame with transactions (must have 'Account', 'Amount', 'Category', 'Date' columns)
        api_key: OpenAI API key
        
    Returns:
        Dict with:
        - overall_summary: High-level spending overview
        - account_analyses: Dict[account_name, analysis] with per-account insights
        - comparative_insights: Cross-account comparisons
    """
    if df.empty:
        raise ValueError("No transactions to analyze")
    
    # Validate required columns
    required_cols = ['Account', 'Amount', 'Category', 'Date']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Prepare data for analysis
    analysis_data = _prepare_analysis_data(df)
    
    # Generate AI insights
    ai_response = _call_openai_api(analysis_data, api_key)
    
    # Parse and structure the response
    insights = _parse_ai_response(ai_response, analysis_data)
    
    return insights


def _prepare_analysis_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Prepare aggregated data for AI analysis."""
    # Convert Date to datetime if needed
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Group by account and prepare data
    accounts_data = {}
    total_spending = 0
    total_income = 0
    
    for account in df['Account'].unique():
        if pd.isna(account):
            continue
            
        account_df = df[df['Account'] == account].copy()
        
        # Calculate spending and income
        expenses = account_df[account_df['Amount'] < 0]
        income = account_df[account_df['Amount'] > 0]
        
        total_spent = abs(expenses['Amount'].sum()) if not expenses.empty else 0
        total_earned = income['Amount'].sum() if not income.empty else 0
        
        total_spending += total_spent
        total_income += total_earned
        
        # Category breakdown
        category_breakdown = {}
        if not expenses.empty:
            category_totals = expenses.groupby('Category')['Amount'].sum().abs()
            category_breakdown = {cat: float(amount) for cat, amount in category_totals.items()}
        
        # Monthly trends (last 6 months)
        monthly_trends = {}
        if not expenses.empty:
            expenses_copy = expenses.copy()
            expenses_copy['Month'] = expenses_copy['Date'].dt.to_period('M')
            monthly_totals = expenses_copy.groupby('Month')['Amount'].sum().abs()
            for month, amount in monthly_totals.items():
                monthly_trends[str(month)] = float(amount)
        
        # Top vendors (by frequency and amount)
        top_vendors = []
        if not expenses.empty:
            vendor_totals = expenses.groupby('Description')['Amount'].sum().abs().sort_values(ascending=False)
            top_vendors = [{'vendor': vendor, 'amount': float(amount)} 
                          for vendor, amount in vendor_totals.head(10).items()]
        
        # Date range
        date_range = {
            'start': account_df['Date'].min().strftime('%Y-%m-%d'),
            'end': account_df['Date'].max().strftime('%Y-%m-%d')
        }
        
        accounts_data[account] = {
            'total_spent': total_spent,
            'total_income': total_earned,
            'category_breakdown': category_breakdown,
            'monthly_trends': monthly_trends,
            'top_vendors': top_vendors,
            'date_range': date_range,
            'transaction_count': len(account_df),
            'expense_count': len(expenses),
            'income_count': len(income)
        }
    
    return {
        'accounts': accounts_data,
        'total_accounts': len(accounts_data),
        'overall_spending': total_spending,
        'overall_income': total_income,
        'analysis_date': datetime.now().strftime('%Y-%m-%d')
    }


def _call_openai_api(analysis_data: Dict[str, Any], api_key: str) -> str:
    """Call OpenAI API to generate insights."""
    client = openai.OpenAI(api_key=api_key)
    
    # Create the prompt
    prompt = _create_analysis_prompt(analysis_data)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective model
            messages=[
                {
                    "role": "system",
                    "content": "אתה יועץ פיננסי מקצועי. נתח את נתוני ההוצאות והכנסות וספק המלצות אישיות לחיסכון כסף. תמיד ענה בעברית. היה ספציפי ופרקטי."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


def _create_analysis_prompt(analysis_data: Dict[str, Any]) -> str:
    """Create the prompt for OpenAI analysis."""
    accounts = analysis_data['accounts']
    
    prompt = f"""
נתח את נתוני ההוצאות והכנסות הבאים וספק המלצות אישיות לחיסכון כסף.

נתונים כלליים:
- סך הוצאות: ₪{analysis_data['overall_spending']:,.0f}
- סך הכנסות: ₪{analysis_data['overall_income']:,.0f}
- מספר חשבונות: {analysis_data['total_accounts']}

נתונים לפי חשבון:
"""
    
    for account_name, data in accounts.items():
        prompt += f"""
חשבון: {account_name}
- סך הוצאות: ₪{data['total_spent']:,.0f}
- סך הכנסות: ₪{data['total_income']:,.0f}
- מספר עסקאות: {data['transaction_count']}
- תקופה: {data['date_range']['start']} עד {data['date_range']['end']}

הוצאות לפי קטגוריה:
"""
        for category, amount in data['category_breakdown'].items():
            prompt += f"  - {category}: ₪{amount:,.0f}\n"
        
        prompt += f"""
ספקים מובילים:
"""
        for vendor in data['top_vendors'][:5]:
            prompt += f"  - {vendor['vendor']}: ₪{vendor['amount']:,.0f}\n"
        
        prompt += "\n"
    
    prompt += """
בבקשה ספק:

1. סיכום כללי של מצב ההוצאות
2. עבור כל חשבון בנפרד:
   - הערכה של דפוסי ההוצאות
   - המלצות תקציב לקטגוריות
   - 3-5 פעולות ספציפיות לחיסכון כסף
   - התראות על הוצאות חריגות
   - תובנות חודשיות
3. השוואות בין חשבונות:
   - איזה חשבון מוציא הכי הרבה בכל קטגוריה
   - הזדמנויות לאיחוד או אופטימיזציה
   - המלצות כלליות לחיסכון משק הבית

ענה בפורמט JSON עם המבנה הבא:
{
  "overall_summary": "סיכום כללי",
  "account_analyses": {
    "שם_חשבון": {
      "spending_assessment": "הערכת הוצאות",
      "budget_recommendations": {"קטגוריה": "תקציב מומלץ"},
      "savings_opportunities": ["הזדמנות 1", "הזדמנות 2"],
      "unusual_alerts": ["התראה 1"],
      "monthly_insights": "תובנות חודשיות"
    }
  },
  "comparative_insights": {
    "highest_spending_by_category": {"קטגוריה": "חשבון"},
    "consolidation_opportunities": ["הזדמנות 1"],
    "household_recommendations": ["המלצה 1"]
  }
}
"""
    
    return prompt


def _parse_ai_response(response: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the AI response and structure it."""
    try:
        # Try to extract JSON from response
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON found in response")
        
        json_str = response[start_idx:end_idx]
        parsed = json.loads(json_str)
        
        # Add metadata
        parsed['metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'accounts_analyzed': list(analysis_data['accounts'].keys()),
            'total_accounts': analysis_data['total_accounts'],
            'overall_spending': analysis_data['overall_spending'],
            'overall_income': analysis_data['overall_income']
        }
        
        return parsed
        
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback: create a basic structure with the raw response
        return {
            'overall_summary': response[:500] + "..." if len(response) > 500 else response,
            'account_analyses': {},
            'comparative_insights': {},
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'accounts_analyzed': list(analysis_data['accounts'].keys()),
                'total_accounts': analysis_data['total_accounts'],
                'overall_spending': analysis_data['overall_spending'],
                'overall_income': analysis_data['overall_income'],
                'parse_error': str(e)
            }
        }


def estimate_analysis_cost(analysis_data: Dict[str, Any]) -> float:
    """Estimate the cost of the analysis in USD."""
    # Rough estimation based on token count
    # GPT-4o-mini: $0.00015 per 1K input tokens, $0.0006 per 1K output tokens
    
    # Estimate input tokens (roughly 4 characters per token)
    prompt = _create_analysis_prompt(analysis_data)
    input_tokens = len(prompt) / 4
    
    # Estimate output tokens (assuming 2000 tokens response)
    output_tokens = 2000
    
    # Calculate cost
    input_cost = (input_tokens / 1000) * 0.00015
    output_cost = (output_tokens / 1000) * 0.0006
    
    return round(input_cost + output_cost, 4)
