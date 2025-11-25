"""
Outcome Logger

Records market outcomes and calculates accuracy against predictions.
Called after market_collector.py collects daily market data.

This runs at 9:30pm GMT AFTER US market closes.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

sys.path.append(str(Path(__file__).parent.parent))

from storage.db import EventDatabase


# Direction thresholds
DIRECTION_THRESHOLD = 0.5  # % change to count as "up" or "down"

# Magnitude thresholds
STRONG_MAGNITUDE = 2.0  # % change for "strong" move
MODERATE_MAGNITUDE = 0.5  # % change for "moderate" move


def classify_direction(change_pct: float) -> str:
    """
    Classify market direction based on % change.

    Args:
        change_pct: Percentage change

    Returns:
        'up', 'down', or 'flat'
    """
    if change_pct > DIRECTION_THRESHOLD:
        return 'up'
    elif change_pct < -DIRECTION_THRESHOLD:
        return 'down'
    else:
        return 'flat'


def classify_magnitude(change_pct: float) -> str:
    """
    Classify magnitude of market move.

    Args:
        change_pct: Percentage change (absolute value)

    Returns:
        'strong', 'moderate', or 'weak'
    """
    abs_change = abs(change_pct)

    if abs_change >= STRONG_MAGNITUDE:
        return 'strong'
    elif abs_change >= MODERATE_MAGNITUDE:
        return 'moderate'
    else:
        return 'weak'


def get_market_data_for_date(db: EventDatabase, date: str) -> List[dict]:
    """
    Get market data for all symbols on a specific date.

    Args:
        db: Database connection
        date: Date string (YYYY-MM-DD)

    Returns:
        List of dicts with symbol and change_pct
    """
    cursor = db.conn.cursor()

    cursor.execute("""
        SELECT symbol, symbol_name, change_pct
        FROM market_data
        WHERE date = ?
    """, (date,))

    rows = cursor.fetchall()

    return [
        {
            'symbol': row[0],
            'symbol_name': row[1],
            'change_pct': row[2]
        }
        for row in rows
    ]


def prediction_matches_outcome(prediction: str, direction: str) -> bool:
    """
    Check if prediction matches outcome.

    Args:
        prediction: 'bullish', 'bearish', or 'neutral'
        direction: 'up', 'down', or 'flat'

    Returns:
        True if they match
    """
    matches = {
        ('bullish', 'up'): True,
        ('bearish', 'down'): True,
        ('neutral', 'flat'): True,
    }

    return matches.get((prediction, direction), False)


def calculate_correlation(db: EventDatabase, symbol: str, days: int = 30) -> float:
    """
    Calculate correlation between sentiment and symbol performance over N days.

    Args:
        db: Database connection
        symbol: Stock symbol
        days: Number of days to look back

    Returns:
        Correlation coefficient (Pearson's r)
    """
    cursor = db.conn.cursor()

    # Get predictions and outcomes for last N days
    cursor.execute("""
        SELECT
            p.date,
            p.sentiment_positive - p.sentiment_negative as net_sentiment,
            o.change_pct
        FROM predictions p
        JOIN outcomes o ON p.date = o.date
        WHERE o.symbol = ?
        ORDER BY p.date DESC
        LIMIT ?
    """, (symbol, days))

    rows = cursor.fetchall()

    if len(rows) < 5:  # Need at least 5 data points
        return 0.0

    # Extract sentiment and market change arrays
    sentiments = [row[1] for row in rows]
    changes = [row[2] for row in rows]

    # Calculate Pearson correlation
    try:
        import numpy as np
        correlation = np.corrcoef(sentiments, changes)[0, 1]
        return round(correlation, 3)
    except:
        # If numpy not available or calculation fails, return 0
        return 0.0


def log_outcomes(db_path: str = "ai_pulse.db", date: str = None):
    """
    Log market outcomes and calculate accuracy.

    Args:
        db_path: Path to database
        date: Date to log outcomes for (defaults to today UTC)
    """
    if date is None:
        date = datetime.utcnow().strftime('%Y-%m-%d')

    print(f"Logging outcomes for {date}...")

    db = EventDatabase(db_path=db_path)

    # Get market data for this date
    market_data = get_market_data_for_date(db, date)

    if not market_data:
        print(f"No market data found for {date}, skipping")
        db.close()
        return

    # Get prediction for this date
    prediction_record = db.get_prediction(date)

    if not prediction_record:
        print(f"No prediction found for {date}, logging outcomes only")
        prediction = None
    else:
        prediction = prediction_record['prediction']
        print(f"Prediction: {prediction}")

    # Process each symbol
    outcomes_logged = 0
    accuracy_logged = 0

    for data in market_data:
        symbol = data['symbol']
        change_pct = data['change_pct']

        if change_pct is None:
            print(f"  {symbol}: No change data, skipping")
            continue

        # Classify outcome
        direction = classify_direction(change_pct)
        magnitude = classify_magnitude(change_pct)

        # Save outcome
        db.save_outcome(
            date=date,
            symbol=symbol,
            change_pct=change_pct,
            direction=direction,
            magnitude=magnitude
        )
        outcomes_logged += 1

        print(f"  {symbol}: {change_pct:+.2f}% ({direction}, {magnitude})")

        # If we have a prediction, calculate accuracy
        if prediction:
            correct = prediction_matches_outcome(prediction, direction)

            # Calculate correlation (requires historical data)
            correlation = calculate_correlation(db, symbol, days=30)

            # Save accuracy
            db.save_accuracy(
                date=date,
                symbol=symbol,
                prediction=prediction,
                outcome=direction,
                correct=correct,
                correlation=correlation
            )
            accuracy_logged += 1

            status = "✓" if correct else "✗"
            print(f"    {status} Prediction: {prediction} vs Outcome: {direction} (r={correlation:.3f})")

    print(f"\n✓ Logged {outcomes_logged} outcomes")
    if accuracy_logged > 0:
        print(f"✓ Logged {accuracy_logged} accuracy records")

    db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Log market outcomes and accuracy')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database path (default: ai_pulse.db)')
    parser.add_argument('--date', type=str, default=None,
                       help='Date to log (YYYY-MM-DD, defaults to today UTC)')

    args = parser.parse_args()

    log_outcomes(db_path=args.db, date=args.date)
