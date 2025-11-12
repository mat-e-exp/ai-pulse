"""
Retroactive deduplication script for historical data.

Finds duplicate events in the database and marks them as duplicates
without deleting them (preserving history).
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from storage.db import EventDatabase
from models.events import Event
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from collections import defaultdict


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two text strings."""
    t1 = text1.lower().strip()
    t2 = text2.lower().strip()
    return SequenceMatcher(None, t1, t2).ratio()


def find_duplicates(db_path: str = "ai_pulse.db", days_back: int = 30, similarity_threshold: float = 0.75):
    """
    Find and mark duplicate events in database.

    Args:
        db_path: Database path
        days_back: How many days back to check
        similarity_threshold: Minimum similarity to consider duplicates
    """
    print("=" * 80)
    print("RETROACTIVE DEDUPLICATION")
    print("=" * 80)

    db = EventDatabase(db_path)

    # First, add is_duplicate column if it doesn't exist
    cursor = db.conn.cursor()
    cursor.execute("PRAGMA table_info(events)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'is_duplicate' not in columns:
        print("\nAdding is_duplicate column to database...")
        cursor.execute("ALTER TABLE events ADD COLUMN is_duplicate INTEGER DEFAULT 0")
        db.conn.commit()
        print("✓ Column added")

    # Get events from last N days
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    print(f"\nFinding duplicates in events from last {days_back} days...")

    cursor.execute("""
        SELECT * FROM events
        WHERE collected_at >= ?
        ORDER BY collected_at DESC
    """, (cutoff.isoformat(),))

    all_events = [Event.from_dict(dict(row)) for row in cursor.fetchall()]
    print(f"Found {len(all_events)} events to check")

    # Group by date
    by_date = defaultdict(list)
    for event in all_events:
        date = event.published_at.date() if event.published_at else event.collected_at.date()
        by_date[date].append(event)

    total_duplicates = 0
    duplicate_ids = set()

    # Process each date
    for date, date_events in sorted(by_date.items()):
        print(f"\nChecking {date}: {len(date_events)} events")
        date_duplicates = 0

        # Mark duplicates within this date
        for i in range(len(date_events)):
            if date_events[i].id in duplicate_ids:
                continue

            for j in range(i + 1, len(date_events)):
                if date_events[j].id in duplicate_ids:
                    continue

                # Calculate similarity
                similarity = calculate_similarity(date_events[i].title, date_events[j].title)

                # Check companies match
                companies_match = False
                if date_events[i].companies and date_events[j].companies:
                    common = set(date_events[i].companies) & set(date_events[j].companies)
                    companies_match = len(common) > 0

                # Mark as duplicate if criteria met
                if similarity >= similarity_threshold or (similarity >= 0.6 and companies_match):
                    # Mark the later one (j) as duplicate
                    duplicate_ids.add(date_events[j].id)
                    date_duplicates += 1
                    print(f"  ✓ Duplicate found (similarity: {similarity:.2f})")
                    print(f"    Original: {date_events[i].title[:70]}...")
                    print(f"    Duplicate: {date_events[j].title[:70]}...")

        if date_duplicates > 0:
            print(f"  → {date_duplicates} duplicates on {date}")
            total_duplicates += date_duplicates

    # Mark duplicates in database
    if duplicate_ids:
        print(f"\nMarking {len(duplicate_ids)} events as duplicates in database...")
        for event_id in duplicate_ids:
            cursor.execute("UPDATE events SET is_duplicate = 1 WHERE id = ?", (event_id,))
        db.conn.commit()
        print("✓ Database updated")

    # Recalculate daily sentiment aggregates
    print("\nRecalculating daily sentiment aggregates...")

    # Get all dates that need recalculation
    dates_to_recalc = set()
    for event_id in duplicate_ids:
        cursor.execute("SELECT published_at, collected_at FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        if row:
            pub_date = row[0]
            col_date = row[1]
            date_str = pub_date.split('T')[0] if pub_date else col_date.split('T')[0]
            dates_to_recalc.add(date_str)

    # Recalculate for each affected date
    for date_str in sorted(dates_to_recalc):
        print(f"  Recalculating {date_str}...")

        # Get non-duplicate, analyzed events for this date
        cursor.execute("""
            SELECT sentiment FROM events
            WHERE (DATE(published_at) = ? OR DATE(collected_at) = ?)
              AND significance_score IS NOT NULL
              AND (is_duplicate IS NULL OR is_duplicate = 0)
        """, (date_str, date_str))

        sentiments = [row[0] for row in cursor.fetchall() if row[0]]

        # Count sentiments
        sentiment_counts = {}
        for sent in sentiments:
            sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1

        # Update or insert daily sentiment
        cursor.execute("DELETE FROM daily_sentiment WHERE date = ?", (date_str,))

        if sentiment_counts:
            cursor.execute("""
                INSERT INTO daily_sentiment (date, positive, negative, neutral, mixed, total_analyzed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str,
                sentiment_counts.get('positive', 0),
                sentiment_counts.get('negative', 0),
                sentiment_counts.get('neutral', 0),
                sentiment_counts.get('mixed', 0),
                len(sentiments),
                datetime.utcnow().isoformat()
            ))
            print(f"    ✓ {date_str}: {len(sentiments)} events")

    db.conn.commit()
    db.close()

    print("\n" + "=" * 80)
    print(f"COMPLETE: {total_duplicates} duplicates marked")
    print(f"Recalculated sentiment for {len(dates_to_recalc)} dates")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Find and mark duplicate events in database')
    parser.add_argument('--days', type=int, default=30,
                       help='Days back to check (default: 30)')
    parser.add_argument('--threshold', type=float, default=0.75,
                       help='Similarity threshold (default: 0.75)')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database path (default: ai_pulse.db)')

    args = parser.parse_args()

    find_duplicates(
        db_path=args.db,
        days_back=args.days,
        similarity_threshold=args.threshold
    )
