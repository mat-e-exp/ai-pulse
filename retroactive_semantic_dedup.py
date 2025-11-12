"""
Retroactive semantic deduplication for already-analyzed events.

Finds semantic duplicates in historical data and marks them,
then recalculates sentiment to ensure accuracy.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from datetime import datetime, timedelta
from storage.db import EventDatabase
from models.events import Event
from typing import List, Dict
from cost_tracking.tracker import CostTracker
from collections import defaultdict


def find_semantic_duplicates_retroactive(db_path: str = "ai_pulse.db", days_back: int = 7):
    """
    Find and mark semantic duplicates in already-analyzed events.

    Args:
        db_path: Database path
        days_back: Days to look back
    """
    load_dotenv()

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    client = Anthropic(api_key=api_key)
    db = EventDatabase(db_path)
    cost_tracker = CostTracker()

    print("=" * 80)
    print("RETROACTIVE SEMANTIC DEDUPLICATION")
    print("=" * 80)

    # Ensure column exists
    cursor = db.conn.cursor()
    cursor.execute("PRAGMA table_info(events)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'is_semantic_duplicate' not in columns:
        print("\nAdding is_semantic_duplicate column...")
        cursor.execute("ALTER TABLE events ADD COLUMN is_semantic_duplicate INTEGER DEFAULT 0")
        db.conn.commit()
        print("✓ Column added")

    # Get analyzed events from recent days
    cutoff = datetime.utcnow() - timedelta(days=days_back)

    cursor.execute("""
        SELECT * FROM events
        WHERE significance_score IS NOT NULL
          AND collected_at >= ?
          AND (is_duplicate IS NULL OR is_duplicate = 0)
        ORDER BY published_at DESC
    """, (cutoff.isoformat(),))

    events = [Event.from_dict(dict(row)) for row in cursor.fetchall()]

    if not events:
        print("\n✓ No events found")
        db.close()
        return

    print(f"\nFound {len(events)} analyzed events to check")

    # Group by date
    by_date = defaultdict(list)
    for event in events:
        date = event.published_at.date() if event.published_at else event.collected_at.date()
        by_date[date].append(event)

    total_duplicates = 0
    dates_affected = set()

    # Process each date
    for date, date_events in sorted(by_date.items()):
        if len(date_events) < 2:
            print(f"\n{date}: Only 1 event, skipping")
            continue

        print(f"\n{date}: Checking {len(date_events)} events...")

        # Build prompt
        titles_text = ""
        for idx, event in enumerate(date_events):
            titles_text += f"{idx}. {event.title}\n"

        prompt = f"""You are analyzing news headlines to identify semantic duplicates. Different headlines may report the SAME underlying event with different wording.

Here are headlines from {date}:

{titles_text}

Identify which headlines report the SAME SPECIFIC EVENT (not just the same company or topic).

Rules:
- Only group headlines that describe the EXACT SAME event
- "Company X sells Y" and "Company X profits rise" might be SAME event if the profit is FROM selling Y
- "Company X sells Y for $5B" and "Company X exits Y position" are SAME event
- Be conservative but accurate - catch true duplicates

Return ONLY valid JSON with this exact structure:
{{"duplicate_groups": [[1,3,5], [7,9]], "reasoning": "brief explanation"}}

If no duplicates, return:
{{"duplicate_groups": [], "reasoning": "no semantic duplicates found"}}
"""

        try:
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            cost_tracker.log_anthropic_call(response, operation='retroactive_semantic_dedup')

            response_text = response.content[0].text.strip()

            # Extract JSON - find first { and last }
            json_start = response_text.find('{')
            json_end = response_text.rfind('}')

            if json_start != -1 and json_end != -1 and json_end > json_start:
                response_text = response_text[json_start:json_end+1]
            else:
                # Try markdown code blocks
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"  ✗ JSON parse error: {e}")
                print(f"  Response: {response_text[:500]}")
                continue

            duplicate_groups = result.get('duplicate_groups', [])
            reasoning = result.get('reasoning', '')

            if duplicate_groups:
                print(f"  Claude: {reasoning}")
                print(f"  → Found {len(duplicate_groups)} duplicate groups")

                for group in duplicate_groups:
                    # Keep first, mark rest as duplicates
                    print(f"\n  Group: {group}")
                    print(f"    KEEP: {date_events[group[0]].title[:70]}...")
                    for idx in group[1:]:
                        event = date_events[idx]
                        cursor.execute(
                            "UPDATE events SET is_semantic_duplicate = 1 WHERE id = ?",
                            (event.id,)
                        )
                        print(f"    DUP:  {event.title[:70]}...")
                        total_duplicates += 1

                dates_affected.add(str(date))
            else:
                print(f"  → No duplicates found")

        except Exception as e:
            print(f"  ✗ Error: {e}")

    db.conn.commit()

    # Recalculate sentiment for affected dates
    if dates_affected:
        print(f"\n\nRecalculating sentiment for {len(dates_affected)} affected dates...")

        for date_str in sorted(dates_affected):
            cursor.execute("""
                SELECT sentiment FROM events
                WHERE (DATE(published_at) = ? OR DATE(collected_at) = ?)
                  AND significance_score IS NOT NULL
                  AND (is_duplicate IS NULL OR is_duplicate = 0)
                  AND (is_semantic_duplicate IS NULL OR is_semantic_duplicate = 0)
            """, (date_str, date_str))

            sentiments = [row[0] for row in cursor.fetchall() if row[0]]

            if not sentiments:
                continue

            sentiment_counts = {}
            for sent in sentiments:
                sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1

            # Update daily_sentiment
            cursor.execute("DELETE FROM daily_sentiment WHERE date = ?", (date_str,))
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

            print(f"  ✓ {date_str}: {len(sentiments)} unique events")

        db.conn.commit()

    db.close()

    print("\n" + "=" * 80)
    print(f"COMPLETE: {total_duplicates} semantic duplicates marked")
    print(f"Sentiment recalculated for {len(dates_affected)} dates")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Retroactive semantic deduplication')
    parser.add_argument('--days', type=int, default=7, help='Days back to check')
    parser.add_argument('--db', type=str, default='ai_pulse.db', help='Database path')

    args = parser.parse_args()

    find_semantic_duplicates_retroactive(db_path=args.db, days_back=args.days)
