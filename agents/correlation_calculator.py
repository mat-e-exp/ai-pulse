"""
Calculate correlation between sentiment and market outcomes.

Tracks prediction accuracy: Did morning sentiment match the market close?
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import sqlite3
from datetime import datetime, timedelta


def ensure_correlation_table(db_path: str):
    """Create daily_correlation table if it doesn't exist"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_correlation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            dominant_sentiment TEXT,
            sentiment_strength REAL,
            market_outcome TEXT,
            nasdaq_change_pct REAL,
            nvda_change_pct REAL,
            sp500_change_pct REAL,
            prediction_correct INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_corr_date ON daily_correlation(date)
    """)

    conn.commit()
    conn.close()


def classify_market_outcome(change_pct: float) -> str:
    """
    Classify market movement as positive, negative, or neutral.

    Args:
        change_pct: Percentage change (close-to-close)

    Returns:
        'positive', 'negative', or 'neutral'
    """
    if change_pct > 0.5:
        return 'positive'
    elif change_pct < -0.5:
        return 'negative'
    else:
        return 'neutral'


def is_prediction_correct(sentiment: str, outcome: str) -> bool:
    """
    Check if sentiment prediction matched market outcome.

    Args:
        sentiment: Dominant sentiment ('positive', 'negative', 'neutral', 'mixed')
        outcome: Market outcome ('positive', 'negative', 'neutral')

    Returns:
        True if matched, False if wrong, None if ambiguous (mixed sentiment)
    """
    if sentiment == 'mixed':
        return None  # Ambiguous - don't count as right or wrong

    return sentiment == outcome


def calculate_correlation_for_date(date_str: str, db_path: str = "ai_pulse.db"):
    """
    Calculate correlation between sentiment and market for a specific date.

    Args:
        date_str: Date in YYYY-MM-DD format
        db_path: Database path
    """
    ensure_correlation_table(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get sentiment data for this date
    cursor.execute("""
        SELECT positive, negative, neutral, mixed, total_analyzed
        FROM daily_sentiment
        WHERE date = ?
    """, (date_str,))

    sentiment_row = cursor.fetchone()

    if not sentiment_row:
        print(f"✗ No sentiment data for {date_str}")
        conn.close()
        return

    positive, negative, neutral, mixed, total = sentiment_row

    if total == 0:
        print(f"✗ No analyzed events for {date_str}")
        conn.close()
        return

    # Calculate percentages and find dominant sentiment
    sentiments = {
        'positive': (positive / total) * 100,
        'negative': (negative / total) * 100,
        'neutral': (neutral / total) * 100,
        'mixed': (mixed / total) * 100,
    }

    dominant_sentiment = max(sentiments, key=sentiments.get)
    sentiment_strength = sentiments[dominant_sentiment]

    # Get market data for this date
    cursor.execute("""
        SELECT symbol, change_pct
        FROM market_data
        WHERE date = ?
        AND symbol IN ('^IXIC', 'NVDA', '^GSPC')
    """, (date_str,))

    market_rows = cursor.fetchall()

    if not market_rows:
        print(f"⚠️ No market data for {date_str} (market closed?)")
        conn.close()
        return

    # Extract specific indices/stocks
    nasdaq_change = None
    nvda_change = None
    sp500_change = None

    for symbol, change_pct in market_rows:
        if symbol == '^IXIC':
            nasdaq_change = change_pct
        elif symbol == 'NVDA':
            nvda_change = change_pct
        elif symbol == '^GSPC':
            sp500_change = change_pct

    # Use NASDAQ as primary indicator
    if nasdaq_change is None:
        print(f"⚠️ No NASDAQ data for {date_str}")
        conn.close()
        return

    market_outcome = classify_market_outcome(nasdaq_change)
    prediction_correct = is_prediction_correct(dominant_sentiment, market_outcome)

    # Convert None to NULL for database (ambiguous/mixed)
    if prediction_correct is None:
        prediction_correct_db = None
    else:
        prediction_correct_db = 1 if prediction_correct else 0

    # Insert or update correlation
    cursor.execute("""
        INSERT OR REPLACE INTO daily_correlation
        (date, dominant_sentiment, sentiment_strength, market_outcome,
         nasdaq_change_pct, nvda_change_pct, sp500_change_pct, prediction_correct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (date_str, dominant_sentiment, sentiment_strength, market_outcome,
          nasdaq_change, nvda_change, sp500_change, prediction_correct_db))

    conn.commit()
    conn.close()

    # Print result
    status_emoji = "✅" if prediction_correct else ("⚠️" if prediction_correct is None else "❌")
    print(f"{status_emoji} {date_str}: {dominant_sentiment.upper()} ({sentiment_strength:.0f}%) → Market {market_outcome.upper()} ({nasdaq_change:+.2f}%)")


def calculate_correlation_range(days_back: int = 30, db_path: str = "ai_pulse.db"):
    """
    Calculate correlations for last N days.

    Args:
        days_back: Number of days to calculate
        db_path: Database path
    """
    print("=" * 80)
    print(f"CALCULATING SENTIMENT-MARKET CORRELATION - Last {days_back} days")
    print("=" * 80)

    for i in range(days_back):
        date = datetime.utcnow() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        calculate_correlation_for_date(date_str, db_path)

    # Print summary statistics
    print("\n" + "=" * 80)
    print("ACCURACY SUMMARY")
    print("=" * 80)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN prediction_correct = 1 THEN 1 ELSE 0 END) as correct,
            SUM(CASE WHEN prediction_correct = 0 THEN 1 ELSE 0 END) as wrong,
            SUM(CASE WHEN prediction_correct IS NULL THEN 1 ELSE 0 END) as ambiguous
        FROM daily_correlation
        WHERE date >= date('now', '-' || ? || ' days')
    """, (days_back,))

    stats = cursor.fetchone()
    total, correct, wrong, ambiguous = stats

    if total > 0:
        accuracy = (correct / (correct + wrong)) * 100 if (correct + wrong) > 0 else 0
        print(f"\nTotal days analyzed: {total}")
        print(f"✅ Correct predictions: {correct}")
        print(f"❌ Wrong predictions: {wrong}")
        print(f"⚠️ Ambiguous (mixed sentiment): {ambiguous}")
        print(f"\nAccuracy: {accuracy:.1f}% ({correct}/{correct + wrong})")
    else:
        print("\nNo correlation data available")

    conn.close()
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Calculate sentiment-market correlation')
    parser.add_argument('--date', type=str, help='Calculate for specific date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=30, help='Calculate for last N days')
    parser.add_argument('--db', type=str, default='ai_pulse.db', help='Database path')

    args = parser.parse_args()

    if args.date:
        calculate_correlation_for_date(args.date, db_path=args.db)
    else:
        calculate_correlation_range(days_back=args.days, db_path=args.db)
