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
    """Prepare aggregated data for AI analysis with enhanced metrics."""
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

        # Category breakdown with percentages
        category_breakdown = {}
        category_percentages = {}
        if not expenses.empty:
            category_totals = expenses.groupby('Category')['Amount'].sum().abs()
            category_breakdown = {cat: float(amount) for cat, amount in category_totals.items()}
            # Calculate percentages
            for cat, amount in category_breakdown.items():
                category_percentages[cat] = round((amount / total_spent * 100), 1) if total_spent > 0 else 0

        # Monthly trends with growth rates
        monthly_trends = {}
        month_over_month_change = None
        if not expenses.empty:
            expenses_copy = expenses.copy()
            expenses_copy['Month'] = expenses_copy['Date'].dt.to_period('M')
            monthly_totals = expenses_copy.groupby('Month')['Amount'].sum().abs()

            # Sort by month
            monthly_totals = monthly_totals.sort_index()

            for month, amount in monthly_totals.items():
                monthly_trends[str(month)] = float(amount)

            # Calculate month-over-month change for last 2 months
            if len(monthly_totals) >= 2:
                recent_months = monthly_totals.tail(2)
                old_val = recent_months.iloc[0]
                new_val = recent_months.iloc[1]
                if old_val > 0:
                    month_over_month_change = round(((new_val - old_val) / old_val * 100), 1)

        # Average monthly spending
        avg_monthly_spending = 0
        if monthly_trends:
            avg_monthly_spending = round(sum(monthly_trends.values()) / len(monthly_trends), 2)

        # Top vendors with transaction count
        top_vendors = []
        if not expenses.empty:
            vendor_stats = expenses.groupby('Description').agg({
                'Amount': ['sum', 'count']
            }).reset_index()
            vendor_stats.columns = ['vendor', 'total', 'count']
            vendor_stats['total'] = vendor_stats['total'].abs()
            vendor_stats = vendor_stats.sort_values('total', ascending=False)

            top_vendors = [
                {
                    'vendor': row['vendor'],
                    'amount': float(row['total']),
                    'transaction_count': int(row['count']),
                    'avg_per_transaction': round(float(row['total']) / int(row['count']), 2)
                }
                for _, row in vendor_stats.head(10).iterrows()
            ]

        # Spending statistics
        spending_stats = {}
        if not expenses.empty:
            spending_stats = {
                'avg_transaction': round(float(expenses['Amount'].abs().mean()), 2),
                'median_transaction': round(float(expenses['Amount'].abs().median()), 2),
                'largest_transaction': round(float(expenses['Amount'].abs().max()), 2),
                'smallest_transaction': round(float(expenses['Amount'].abs().min()), 2)
            }

        # Calculate days covered and daily average
        date_range = {
            'start': account_df['Date'].min().strftime('%Y-%m-%d'),
            'end': account_df['Date'].max().strftime('%Y-%m-%d')
        }
        days_covered = (account_df['Date'].max() - account_df['Date'].min()).days + 1
        daily_avg_spending = round(total_spent / days_covered, 2) if days_covered > 0 else 0

        # Calculate savings rate
        savings_rate = 0
        if total_earned > 0:
            savings_rate = round(((total_earned - total_spent) / total_earned * 100), 1)

        accounts_data[account] = {
            'total_spent': total_spent,
            'total_income': total_earned,
            'category_breakdown': category_breakdown,
            'category_percentages': category_percentages,
            'monthly_trends': monthly_trends,
            'month_over_month_change': month_over_month_change,
            'avg_monthly_spending': avg_monthly_spending,
            'top_vendors': top_vendors,
            'spending_stats': spending_stats,
            'date_range': date_range,
            'days_covered': days_covered,
            'daily_avg_spending': daily_avg_spending,
            'savings_rate': savings_rate,
            'transaction_count': len(account_df),
            'expense_count': len(expenses),
            'income_count': len(income)
        }

    # Calculate overall savings rate
    overall_savings_rate = 0
    if total_income > 0:
        overall_savings_rate = round(((total_income - total_spending) / total_income * 100), 1)

    return {
        'accounts': accounts_data,
        'total_accounts': len(accounts_data),
        'overall_spending': total_spending,
        'overall_income': total_income,
        'overall_savings_rate': overall_savings_rate,
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
                    "content": """אתה יועץ פיננסי מקצועי מומחה בניתוח הוצאות אישיות ומשפחתיות בישראל.

המטרה שלך: לספק המלצות מעשיות וספציפיות לחיסכון כסף, מבוססות על נתוני הוצאות אמיתיים.

עקרונות עבודה:
1. תן המלצות קונקרטיות ופרקטיות - לא כלליות
2. התמקד בהזדמנויות חיסכון עם השפעה גבוהה (20/80)
3. זהה דפוסי הוצאה חריגים או בלתי רגילים
4. השווה הוצאות לממוצעים סבירים במשק הישראלי
5. תן עדיפות להמלצות שקל ליישם מיד
6. השתמש בשפה ברורה וידידותית
7. תמיד כלול מספרים ספציפיים בהמלצות

תמיד ענה בעברית בלבד."""
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
    """Create the prompt for OpenAI analysis with enhanced context."""
    accounts = analysis_data['accounts']

    prompt = f"""
נתח את נתוני ההוצאות והכנסות הבאים וספק המלצות אישיות וספציפיות לחיסכון כסף.

📊 **נתונים כלליים:**
- סך הוצאות: ₪{analysis_data['overall_spending']:,.0f}
- סך הכנסות: ₪{analysis_data['overall_income']:,.0f}
- שיעור חיסכון כולל: {analysis_data['overall_savings_rate']}%
- מספר חשבונות: {analysis_data['total_accounts']}
- תאריך ניתוח: {analysis_data['analysis_date']}

"""

    for account_name, data in accounts.items():
        prompt += f"""
{'='*60}
🏦 **חשבון: {account_name}**

💰 **סיכום פיננסי:**
- סך הוצאות: ₪{data['total_spent']:,.0f}
- סך הכנסות: ₪{data['total_income']:,.0f}
- שיעור חיסכון: {data['savings_rate']}%
- תקופה: {data['date_range']['start']} עד {data['date_range']['end']} ({data['days_covered']} ימים)
- ממוצע יומי: ₪{data['daily_avg_spending']:,.2f}
- ממוצע חודשי: ₪{data['avg_monthly_spending']:,.2f}
"""

        # Add month-over-month change if available
        if data['month_over_month_change'] is not None:
            trend_emoji = "📈" if data['month_over_month_change'] > 0 else "📉"
            prompt += f"- שינוי חודש-על-חודש: {trend_emoji} {data['month_over_month_change']:+.1f}%\n"

        prompt += f"""
📊 **סטטיסטיקות עסקאות:**
- סך עסקאות: {data['transaction_count']} (הוצאות: {data['expense_count']}, הכנסות: {data['income_count']})
"""

        if data['spending_stats']:
            stats = data['spending_stats']
            prompt += f"""- ממוצע לעסקה: ₪{stats['avg_transaction']:,.2f}
- חציון: ₪{stats['median_transaction']:,.2f}
- עסקה גדולה ביותר: ₪{stats['largest_transaction']:,.2f}
- עסקה קטנה ביותר: ₪{stats['smallest_transaction']:,.2f}
"""

        prompt += f"""
🏷️ **הוצאות לפי קטגוריה:**
"""
        # Sort categories by amount
        sorted_cats = sorted(data['category_breakdown'].items(), key=lambda x: x[1], reverse=True)
        for category, amount in sorted_cats:
            percentage = data['category_percentages'].get(category, 0)
            prompt += f"  • {category}: ₪{amount:,.0f} ({percentage}%)\n"

        prompt += f"""
🏪 **ספקים מובילים (Top 5):**
"""
        for i, vendor in enumerate(data['top_vendors'][:5], 1):
            prompt += f"  {i}. {vendor['vendor']}: ₪{vendor['amount']:,.0f} ({vendor['transaction_count']} עסקאות, ממוצע ₪{vendor['avg_per_transaction']:,.2f})\n"

        if data['monthly_trends']:
            prompt += f"""
📈 **מגמות חודשיות:**
"""
            for month, amount in list(data['monthly_trends'].items())[-3:]:  # Last 3 months
                prompt += f"  • {month}: ₪{amount:,.0f}\n"

        prompt += "\n"

    prompt += f"""
{'='*60}

🎯 **משימה:**
נא לספק ניתוח מעמיק וממוקד תוצאות עם ההמלצות הבאות:

1. **סיכום כללי מבוסס-נתונים:**
   - מה המצב הפיננסי הכולל? האם שיעור החיסכון בריא?
   - מה הקטגוריות הדומיננטיות?
   - האם יש מגמות מדאיגות או חיוביות?

2. **ניתוח לכל חשבון:**
   - זהה את 3 הקטגוריות עם פוטנציאל החיסכון הגבוה ביותר
   - תן המלצות תקציב **ספציפיות** (סכומים בש"ח) לכל קטגוריה מרכזית
   - ספק 3-5 פעולות **קונקרטיות** לחיסכון עם חיסכון משוער (למשל: "העבר לספק אחר - חיסכון של ₪200/חודש")
   - זהה הוצאות **חריגות או חשודות** (גבוהות במיוחד או תדירות גבוהה)
   - נתח מגמות חודשיות - האם ההוצאות עולות/יורדות?

3. **השוואות והמלצות אסטרטגיות:**
   - איזה חשבון יעיל יותר בכל קטגוריה?
   - האם יש כפילויות מיותרות (למשל, 2 חשבונות עם מינויים דומים)?
   - המלצות לאופטימיזציה של משק הבית

⚠️ **חשוב:**
- כל המלצה חייבת להיות ספציפית עם מספרים
- התמקד בהמלצות שקל ליישם ועם השפעה גבוהה
- השתמש בהקשר ישראלי (מחירים, ספקים)

📋 **פורמט תשובה JSON:**
```json
{{
  "overall_summary": "סיכום מפורט של המצב הפיננסי, מגמות עיקריות, והזדמנויות חיסכון מרכזיות",
  "account_analyses": {{
    "שם_חשבון": {{
      "spending_assessment": "הערכה מפורטת של דפוסי ההוצאה עם נתונים ספציפיים",
      "budget_recommendations": {{
        "קטגוריה_1": "₪X,XXX/חודש (הסבר קצר)",
        "קטגוריה_2": "₪X,XXX/חודש (הסבר קצר)"
      }},
      "savings_opportunities": [
        "פעולה ספציפית 1 - חיסכון משוער: ₪XXX/חודש",
        "פעולה ספציפית 2 - חיסכון משוער: ₪XXX/חודש",
        "פעולה ספציפית 3 - חיסכון משוער: ₪XXX/חודש"
      ],
      "unusual_alerts": [
        "התראה על הוצאה חריגה עם פרטים ספציפיים"
      ],
      "monthly_insights": "ניתוח מגמות חודשיות עם ממצאים קונקרטיים"
    }}
  }},
  "comparative_insights": {{
    "highest_spending_by_category": {{
      "קטגוריה_1": "שם_החשבון - ₪XXX",
      "קטגוריה_2": "שם_החשבון - ₪XXX"
    }},
    "consolidation_opportunities": [
      "הזדמנות לאיחוד/אופטימיזציה עם חיסכון משוער"
    ],
    "household_recommendations": [
      "המלצה אסטרטגית 1 עם השפעה משוערת",
      "המלצה אסטרטגית 2 עם השפעה משוערת"
    ]
  }}
}}
```
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
