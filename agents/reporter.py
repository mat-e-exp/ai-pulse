"""
Simple reporter for viewing collected AI sector data.

Generates human-readable summaries of events in the database.

Phase 2 will add LLM-based analysis and significance scoring.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from storage.db import EventDatabase
from models.events import EventType


class SimpleReporter:
    """
    Generates reports from collected data.

    Current capabilities:
    - Show recent events
    - Group by type
    - Show stats

    Future (with LLM agent):
    - Significance analysis
    - Competitive impact
    - Narrative tracking
    - Investment implications
    """

    def __init__(self, db_path: str = "ai_pulse.db"):
        self.db = EventDatabase(db_path)

    def generate_daily_briefing(self, hours: int = 24):
        """
        Generate a simple daily briefing of AI sector activity.

        Args:
            hours: Look back this many hours (default: 24)
        """
        print("\n" + "=" * 80)
        print(f"AI-PULSE DAILY BRIEFING - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print("=" * 80)

        # Get recent events
        events = self.db.get_recent_events(limit=100, hours=hours)

        if not events:
            print("\nNo events collected in the last {hours} hours.")
            print("Run: python3 agents/collector.py")
            return

        print(f"\nCollected {len(events)} events in the last {hours} hours\n")

        # Group by type
        by_type = {}
        for event in events:
            event_type = event.event_type.value
            if event_type not in by_type:
                by_type[event_type] = []
            by_type[event_type].append(event)

        # Display by category
        type_order = [
            EventType.PRODUCT_LAUNCH,
            EventType.FUNDING,
            EventType.PARTNERSHIP,
            EventType.RESEARCH,
            EventType.REGULATION,
            EventType.NEWS,
            EventType.UNKNOWN,
        ]

        for event_type in type_order:
            type_events = by_type.get(event_type.value, [])
            if not type_events:
                continue

            print(f"\n{'─' * 80}")
            print(f"{event_type.value.upper().replace('_', ' ')} ({len(type_events)} events)")
            print('─' * 80)

            for event in type_events[:10]:  # Show max 10 per category
                # Format timestamp
                time_str = ""
                if event.published_at:
                    time_str = event.published_at.strftime("%Y-%m-%d %H:%M")
                elif event.collected_at:
                    time_str = event.collected_at.strftime("%Y-%m-%d %H:%M")

                # Show companies if detected
                companies_str = ""
                if event.companies:
                    companies_str = f" [{', '.join(event.companies)}]"

                print(f"\n• {event.title}")
                if companies_str:
                    print(f"  Companies:{companies_str}")
                print(f"  Source: {event.source.value} | {time_str}")
                print(f"  URL: {event.source_url}")

                if event.summary:
                    summary = event.summary[:200]
                    if len(event.summary) > 200:
                        summary += "..."
                    print(f"  Summary: {summary}")

        # Database stats
        print(f"\n{'=' * 80}")
        print("DATABASE STATISTICS")
        print('=' * 80)

        stats = self.db.get_stats()
        print(f"\nTotal events: {stats['total_events']}")
        print(f"Last 24 hours: {stats['last_24h']}")

        print(f"\nBy source:")
        for source, count in sorted(stats['by_source'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {source}: {count}")

        print(f"\nBy type:")
        for event_type, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {event_type}: {count}")

        print("\n" + "=" * 80 + "\n")

    def show_recent(self, limit: int = 20, hours: int = 24):
        """Show recent events in simple list format"""
        events = self.db.get_recent_events(limit=limit, hours=hours)

        print(f"\n{len(events)} most recent events (last {hours} hours):\n")

        for i, event in enumerate(events, 1):
            time_str = event.collected_at.strftime("%Y-%m-%d %H:%M")
            print(f"{i}. [{event.event_type.value}] {event.title}")
            print(f"   {event.source.value} | {time_str}")
            print(f"   {event.source_url}\n")

    def show_stats(self):
        """Show database statistics"""
        stats = self.db.get_stats()

        print("\n" + "=" * 80)
        print("AI-PULSE DATABASE STATISTICS")
        print("=" * 80)

        print(f"\nTotal events: {stats['total_events']}")
        print(f"Last 24 hours: {stats['last_24h']}")

        print(f"\n{'Source':<20} {'Count':<10}")
        print("─" * 30)
        for source, count in sorted(stats['by_source'].items(), key=lambda x: x[1], reverse=True):
            print(f"{source:<20} {count:<10}")

        print(f"\n{'Event Type':<20} {'Count':<10}")
        print("─" * 30)
        for event_type, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True):
            print(f"{event_type:<20} {count:<10}")

        print("\n" + "=" * 80 + "\n")

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='View collected AI sector data')
    parser.add_argument('--daily', action='store_true',
                       help='Generate daily briefing')
    parser.add_argument('--recent', action='store_true',
                       help='Show recent events')
    parser.add_argument('--stats', action='store_true',
                       help='Show database stats')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours to look back (default: 24)')
    parser.add_argument('--limit', type=int, default=20,
                       help='Max events to show (default: 20)')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database file path (default: ai_pulse.db)')

    args = parser.parse_args()

    with SimpleReporter(db_path=args.db) as reporter:
        if args.daily:
            reporter.generate_daily_briefing(hours=args.hours)
        elif args.recent:
            reporter.show_recent(limit=args.limit, hours=args.hours)
        elif args.stats:
            reporter.show_stats()
        else:
            # Default: show daily briefing
            reporter.generate_daily_briefing(hours=args.hours)
