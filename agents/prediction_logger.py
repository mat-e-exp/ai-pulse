"""
Prediction Logger

Logs daily sentiment predictions based on analyzed events.
Called after briefing generation to record what we predicted.

This runs at 1:30pm GMT BEFORE US market opens (2:30pm GMT).
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from storage.db import EventDatabase
from storage.db_safety import save_prediction_safe


def calculate_prediction(sentiment_pcts: dict, total_events: int) -> tuple[str, str]:
    """
    Calculate prediction and confidence from sentiment percentages.

    Args:
        sentiment_pcts: Dict with positive/negative/neutral/mixed percentages
        total_events: Total number of events analyzed

    Returns:
        Tuple of (prediction, confidence)
        prediction: 'bullish', 'bearish', 'neutral'
        confidence: 'high', 'medium', 'low'
    """
    positive = sentiment_pcts.get('positive', 0)
    negative = sentiment_pcts.get('negative', 0)

    # Calculate net sentiment
    net_sentiment = positive - negative

    # Determine prediction
    if net_sentiment > 10:
        prediction = 'bullish'
    elif net_sentiment < -10:
        prediction = 'bearish'
    else:
        prediction = 'neutral'

    # Determine confidence based on event count
    if total_events >= 40:
        confidence = 'high'
    elif total_events >= 20:
        confidence = 'medium'
    else:
        confidence = 'low'

    return prediction, confidence


def get_sentiment_percentages(db: EventDatabase, date: str) -> dict:
    """
    Get sentiment percentages for a specific date.

    Args:
        db: Database connection
        date: Date string (YYYY-MM-DD)

    Returns:
        Dict with sentiment percentages and total count
    """
    cursor = db.conn.cursor()

    # Get sentiment counts for today (only non-duplicates)
    cursor.execute("""
        SELECT
            sentiment,
            COUNT(*) as count
        FROM events
        WHERE DATE(published_at) = ?
          AND sentiment IS NOT NULL
          AND (is_duplicate IS NULL OR is_duplicate = 0)
          AND (is_semantic_duplicate IS NULL OR is_semantic_duplicate = 0)
        GROUP BY sentiment
    """, (date,))

    rows = cursor.fetchall()

    # Count by sentiment
    counts = {'positive': 0, 'negative': 0, 'neutral': 0, 'mixed': 0}
    for row in rows:
        sentiment = row[0]
        count = row[1]
        if sentiment in counts:
            counts[sentiment] = count

    total = sum(counts.values())

    if total == 0:
        return {
            'positive': 0,
            'negative': 0,
            'neutral': 0,
            'mixed': 0,
            'total': 0
        }

    # Calculate percentages
    percentages = {
        'positive': round((counts['positive'] / total) * 100, 1),
        'negative': round((counts['negative'] / total) * 100, 1),
        'neutral': round((counts['neutral'] / total) * 100, 1),
        'mixed': round((counts['mixed'] / total) * 100, 1),
        'total': total
    }

    return percentages


def get_top_events(db: EventDatabase, date: str, limit: int = 3) -> str:
    """
    Get top significant events for context.

    Args:
        db: Database connection
        date: Date string (YYYY-MM-DD)
        limit: Number of top events to include

    Returns:
        JSON string with top events
    """
    cursor = db.conn.cursor()

    cursor.execute("""
        SELECT title, significance_score, sentiment, companies
        FROM events
        WHERE DATE(published_at) = ?
          AND significance_score IS NOT NULL
          AND (is_duplicate IS NULL OR is_duplicate = 0)
          AND (is_semantic_duplicate IS NULL OR is_semantic_duplicate = 0)
        ORDER BY significance_score DESC
        LIMIT ?
    """, (date, limit))

    rows = cursor.fetchall()

    events = []
    for row in rows:
        events.append({
            'title': row[0],
            'score': row[1],
            'sentiment': row[2],
            'companies': row[3]
        })

    return json.dumps(events)


def log_prediction(db_path: str = "ai_pulse.db", date: str = None):
    """
    Log today's prediction based on sentiment analysis.

    Args:
        db_path: Path to database
        date: Date to log prediction for (defaults to today UTC)
    """
    if date is None:
        date = datetime.utcnow().strftime('%Y-%m-%d')

    print(f"Logging prediction for {date}...")

    db = EventDatabase(db_path=db_path)

    # Get sentiment percentages
    sentiment_data = get_sentiment_percentages(db, date)

    if sentiment_data['total'] == 0:
        print(f"No events found for {date}, skipping prediction")
        db.close()
        return

    # Calculate prediction
    prediction, confidence = calculate_prediction(sentiment_data, sentiment_data['total'])

    # Get top events for context
    top_events_summary = get_top_events(db, date, limit=3)

    # Save to database with safety checks
    result = save_prediction_safe(
        db=db,
        date=date,
        sentiment_data=sentiment_data,
        prediction=prediction,
        confidence=confidence,
        top_events_summary=top_events_summary
    )

    if result['status'] == 'blocked':
        print(f"⚠️  {result['message']}")
        print(f"   Existing prediction: {result['existing_prediction']}")
        print(f"   Attempted prediction: {prediction}")
        db.close()
        return

    print(f"✓ Prediction {result['action']}:")
    print(f"  Sentiment: {sentiment_data['positive']:.1f}% pos, {sentiment_data['negative']:.1f}% neg")
    print(f"  Events: {sentiment_data['total']}")
    print(f"  Prediction: {prediction} (confidence: {confidence})")
    print(f"  First logged: {result['first_logged_at']}")
    if result['is_locked']:
        print(f"  🔒 Prediction is now LOCKED (market opened)")

    db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Log daily prediction')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database path (default: ai_pulse.db)')
    parser.add_argument('--date', type=str, default=None,
                       help='Date to log (YYYY-MM-DD, defaults to today UTC)')

    args = parser.parse_args()

    log_prediction(db_path=args.db, date=args.date)
