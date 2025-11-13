#!/usr/bin/env python3.9
"""
Prediction Accuracy Analyst

Analyzes historical correlation data to identify patterns and generate
confidence factors for future predictions. Uses Claude API to analyze
patterns in sentiment vs market accuracy.
"""

import argparse
import sqlite3
from datetime import datetime, timedelta
import os
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_historical_data(db_path: str, days: int):
    """Query historical sentiment and market correlation data."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Get correlation data
    cursor.execute("""
        SELECT
            date,
            dominant_sentiment,
            sentiment_strength,
            market_outcome,
            nasdaq_change_pct,
            nvda_change_pct,
            sp500_change_pct,
            prediction_correct
        FROM daily_correlation
        WHERE date >= ?
        ORDER BY date DESC
    """, (cutoff_date,))

    correlations = [dict(row) for row in cursor.fetchall()]

    # Get sentiment breakdown by event type
    cursor.execute("""
        SELECT
            event_type,
            sentiment,
            COUNT(*) as count,
            AVG(significance_score) as avg_significance
        FROM events
        WHERE collected_at >= ?
        AND sentiment IS NOT NULL
        GROUP BY event_type, sentiment
        ORDER BY count DESC
    """, (cutoff_date,))

    event_patterns = [dict(row) for row in cursor.fetchall()]

    # Get per-symbol accuracy (for tracked stocks)
    cursor.execute("""
        SELECT
            symbol,
            symbol_name,
            AVG(change_pct) as avg_change,
            COUNT(*) as days
        FROM market_data
        WHERE date >= ?
        AND symbol IN ('NVDA', 'MSFT', 'GOOGL', 'META', 'AMD', 'PLTR')
        GROUP BY symbol, symbol_name
        ORDER BY avg_change DESC
    """, (cutoff_date,))

    symbol_performance = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        'correlations': correlations,
        'event_patterns': event_patterns,
        'symbol_performance': symbol_performance
    }


def format_data_for_analysis(data: dict, days: int) -> str:
    """Format historical data into a readable prompt."""

    prompt = f"""Analyze the following {days} days of AI sentiment vs market performance data.

# CORRELATION DATA (Daily Predictions)
"""

    # Add correlation summary
    total_days = len(data['correlations'])
    correct_predictions = sum(1 for c in data['correlations'] if c['prediction_correct'] == 1)
    accuracy_rate = (correct_predictions / total_days * 100) if total_days > 0 else 0

    prompt += f"\nTotal Days Analyzed: {total_days}\n"
    prompt += f"Correct Predictions: {correct_predictions} ({accuracy_rate:.1f}% accuracy)\n\n"

    # Recent examples
    prompt += "Recent Predictions (Last 10 Days):\n"
    for c in data['correlations'][:10]:
        prompt += f"  {c['date']}: Sentiment={c['dominant_sentiment']} (strength {c['sentiment_strength']:.2f})"
        prompt += f" → Market={c['market_outcome']} (NASDAQ {c['nasdaq_change_pct']:+.2f}%)"
        prompt += f" {'✓' if c['prediction_correct'] else '✗'}\n"

    # Event type patterns
    prompt += f"\n# EVENT TYPE PATTERNS\n\n"
    for pattern in data['event_patterns'][:20]:  # Top 20 patterns
        prompt += f"  {pattern['event_type']} + {pattern['sentiment']}: "
        prompt += f"{pattern['count']} events (avg significance {pattern['avg_significance']:.1f})\n"

    # Symbol performance
    prompt += f"\n# SYMBOL PERFORMANCE (Avg Daily Change)\n\n"
    for symbol in data['symbol_performance']:
        prompt += f"  {symbol['symbol']} ({symbol['symbol_name']}): "
        prompt += f"{symbol['avg_change']:+.2f}% over {symbol['days']} days\n"

    prompt += """

# ANALYSIS TASKS

Please analyze this data and provide:

1. **Pattern Recognition**: Which types of events (earnings, regulatory, product-launch, etc.)
   show the strongest correlation with market movements?

2. **Sentiment Reliability**: Which sentiment types (positive, negative, neutral, mixed)
   are most predictive? Are there patterns where sentiment strength matters?

3. **Symbol Responsiveness**: Which stocks/indices respond most reliably to AI sentiment?
   Are there symbols that consistently outperform or underperform predictions?

4. **Momentum Patterns**: Do we see multi-day trends (continuations vs reversals)?

5. **Confidence Factors**: Based on these patterns, what confidence levels should we
   assign to different prediction scenarios?

   Example format:
   - High confidence (>70%): [describe conditions]
   - Medium confidence (50-70%): [describe conditions]
   - Low confidence (<50%): [describe conditions]

6. **Recommendations**: What adjustments should be made to improve prediction accuracy?

Please provide specific, actionable insights backed by the data patterns above.
"""

    return prompt


def analyze_with_claude(prompt: str, api_key: str) -> str:
    """Send analysis prompt to Claude API."""
    client = Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    return message.content[0].text


def store_insights(db_path: str, insights: str, days: int):
    """Store analysis insights in database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create insights table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_date TEXT NOT NULL,
            days_analyzed INTEGER NOT NULL,
            insights TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert new insights
    cursor.execute("""
        INSERT INTO prediction_insights (analysis_date, days_analyzed, insights)
        VALUES (?, ?, ?)
    """, (datetime.now().strftime('%Y-%m-%d'), days, insights))

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Analyze prediction accuracy patterns')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days of historical data to analyze (default: 30)')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Path to database (default: ai_pulse.db)')

    args = parser.parse_args()

    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        return

    print(f"\n{'='*80}")
    print("PREDICTION ACCURACY ANALYST")
    print(f"{'='*80}\n")

    # Step 1: Gather historical data
    print(f"📊 Gathering {args.days} days of historical data...")
    data = get_historical_data(args.db, args.days)

    print(f"   Found {len(data['correlations'])} days of correlation data")
    print(f"   Found {len(data['event_patterns'])} event type patterns")
    print(f"   Found {len(data['symbol_performance'])} symbols\n")

    # Step 2: Format for Claude
    print("📝 Formatting analysis prompt...")
    prompt = format_data_for_analysis(data, args.days)

    # Step 3: Analyze with Claude
    print("🤔 Analyzing patterns with Claude API...")
    insights = analyze_with_claude(prompt, api_key)

    # Step 4: Store insights
    print("💾 Storing insights in database...")
    store_insights(args.db, insights, args.days)

    # Step 5: Display results
    print(f"\n{'='*80}")
    print("ANALYSIS RESULTS")
    print(f"{'='*80}\n")
    print(insights)
    print(f"\n{'='*80}")
    print("✓ Analysis complete and stored in database")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
