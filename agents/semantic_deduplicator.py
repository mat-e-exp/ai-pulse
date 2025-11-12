"""
Semantic deduplication using Claude API.

Identifies duplicate stories that string matching misses by understanding
semantic similarity. Critical for accurate sentiment counts.

Example: These are all the same story but <75% string similarity:
- "SoftBank sells entire Nvidia stake for $5.8B"
- "SoftBank profits double on AI investments"
- "Japan's SoftBank exits Nvidia position"

Must run BEFORE analyzer.py to avoid wasting analysis costs and ensure
accurate sentiment percentages.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from datetime import datetime, timedelta
from storage.db import EventDatabase
from models.events import Event
from typing import List, Dict
from cost_tracking.tracker import CostTracker


class SemanticDeduplicator:
    """
    Uses Claude to identify semantically duplicate events that string
    matching misses.

    This ensures accurate sentiment counts by preventing the same story
    from being analyzed multiple times with different wording.
    """

    def __init__(self, db_path: str = "ai_pulse.db", enable_cost_tracking: bool = True):
        """Initialize semantic deduplicator with Claude API"""
        load_dotenv()

        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable. "
                "Get key at: https://console.anthropic.com/"
            )

        self.client = Anthropic(api_key=self.api_key)
        self.db = EventDatabase(db_path)
        self.cost_tracker = CostTracker() if enable_cost_tracking else None

    def find_semantic_duplicates(self, days_back: int = 7) -> Dict:
        """
        Find and mark semantic duplicates in recent unanalyzed events.

        Args:
            days_back: Days to look back for events

        Returns:
            Stats dictionary
        """
        print("=" * 80)
        print("SEMANTIC DEDUPLICATION")
        print("=" * 80)

        # Ensure is_semantic_duplicate column exists
        self._ensure_column_exists()

        # Get unanalyzed events from recent days
        cutoff = datetime.utcnow() - timedelta(days=days_back)

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE significance_score IS NULL
              AND collected_at >= ?
              AND (is_duplicate IS NULL OR is_duplicate = 0)
            ORDER BY published_at DESC
        """, (cutoff.isoformat(),))

        events = [Event.from_dict(dict(row)) for row in cursor.fetchall()]

        if not events:
            print("\n✓ No unanalyzed events found")
            return {'processed': 0, 'duplicates_found': 0}

        print(f"\nFound {len(events)} unanalyzed events to check")

        # Group by date for batch processing
        from collections import defaultdict
        by_date = defaultdict(list)

        for event in events:
            date = event.published_at.date() if event.published_at else event.collected_at.date()
            by_date[date].append(event)

        total_duplicates = 0

        # Process each date
        for date, date_events in sorted(by_date.items()):
            if len(date_events) < 2:
                print(f"\n{date}: Only 1 event, skipping")
                continue

            print(f"\n{date}: Checking {len(date_events)} events for semantic duplicates...")

            duplicates = self._find_duplicates_for_date(date_events)

            if duplicates:
                print(f"  → Found {len(duplicates)} semantic duplicate groups")

                # Mark duplicates in database
                for group in duplicates:
                    # Keep first event (index 0), mark rest as duplicates
                    for event_idx in group[1:]:
                        event = date_events[event_idx]
                        cursor.execute(
                            "UPDATE events SET is_semantic_duplicate = 1 WHERE id = ?",
                            (event.id,)
                        )
                        total_duplicates += 1
                        print(f"  ✓ Marked duplicate: {event.title[:70]}...")

                self.db.conn.commit()
            else:
                print(f"  → No semantic duplicates found")

        print("\n" + "=" * 80)
        print(f"COMPLETE: {total_duplicates} semantic duplicates marked")
        print("=" * 80)

        return {
            'processed': len(events),
            'duplicates_found': total_duplicates
        }

    def _find_duplicates_for_date(self, events: List[Event]) -> List[List[int]]:
        """
        Use Claude to find semantic duplicate groups for a single date.

        Args:
            events: List of events from the same date

        Returns:
            List of duplicate groups, each group is list of event indices
            Example: [[1, 3, 5], [7, 9]] means events 1,3,5 are duplicates, 7,9 are duplicates
        """
        # Build prompt with event titles
        titles_text = ""
        for idx, event in enumerate(events):
            titles_text += f"{idx}. {event.title}\n"

        prompt = f"""You are analyzing news headlines to identify semantic duplicates. Different headlines may report the SAME underlying event with different wording.

Here are headlines from the same day:

{titles_text}

Identify which headlines report the SAME SPECIFIC EVENT (not just the same company or topic).

Rules:
- Only group headlines that describe the EXACT SAME event
- "Company X sells Y" and "Company X profits rise" are DIFFERENT events (even if related)
- "Company X sells Y for $5B" and "Company X exits Y position" are SAME event (just different wording)
- Be conservative - when unsure, consider them different events

Return ONLY valid JSON with this exact structure:
{{"duplicate_groups": [[1,3,5], [7,9]], "reasoning": "brief explanation"}}

If no duplicates found, return:
{{"duplicate_groups": [], "reasoning": "no semantic duplicates found"}}
"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",  # Cheap, fast model for this task
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Track cost
            if self.cost_tracker:
                self.cost_tracker.log_anthropic_call(
                    response,
                    operation='semantic_deduplication',
                    event_id=None
                )

            # Parse response
            response_text = response.content[0].text.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)

            duplicate_groups = result.get('duplicate_groups', [])
            reasoning = result.get('reasoning', 'no reasoning provided')

            if duplicate_groups:
                print(f"  Claude reasoning: {reasoning}")

            return duplicate_groups

        except json.JSONDecodeError as e:
            print(f"  ✗ Error parsing Claude response: {e}")
            print(f"  Response was: {response_text[:200]}...")
            return []
        except Exception as e:
            print(f"  ✗ Error calling Claude API: {e}")
            return []

    def _ensure_column_exists(self):
        """Add is_semantic_duplicate column if it doesn't exist"""
        cursor = self.db.conn.cursor()
        cursor.execute("PRAGMA table_info(events)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'is_semantic_duplicate' not in columns:
            print("\nAdding is_semantic_duplicate column to database...")
            cursor.execute("ALTER TABLE events ADD COLUMN is_semantic_duplicate INTEGER DEFAULT 0")
            self.db.conn.commit()
            print("✓ Column added")

    def close(self):
        """Close database connection"""
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Find semantic duplicates using Claude')
    parser.add_argument('--days', type=int, default=7,
                       help='Days back to check (default: 7)')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database path (default: ai_pulse.db)')

    args = parser.parse_args()

    # Check for API key
    load_dotenv()
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("Get key at: https://console.anthropic.com/")
        sys.exit(1)

    with SemanticDeduplicator(db_path=args.db) as deduplicator:
        deduplicator.find_semantic_duplicates(days_back=args.days)
