"""
Intelligent reporter - Phase 2.

Shows analyzed events with significance scores and agent reasoning.
This demonstrates the value of agentic analysis.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from storage.db import EventDatabase
from models.events import EventType


class IntelligentReporter:
    """
    Generates intelligent briefings using agent analysis.

    Phase 2 upgrade: Shows WHY events matter, not just WHAT happened.
    """

    def __init__(self, db_path: str = "ai_pulse.db"):
        self.db = EventDatabase(db_path)

    def generate_intelligent_briefing(self, hours: int = 24, min_score: int = 40):
        """
        Generate intelligent briefing focused on significant events.

        Args:
            hours: Look back this many hours
            min_score: Minimum significance score to include
        """
        print("\n" + "=" * 80)
        print(f"🧠 AI-PULSE INTELLIGENT BRIEFING - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print("=" * 80)

        # Get analyzed events
        events = self.db.get_recent_events(limit=100, hours=hours)

        # Filter for analyzed events only
        analyzed = [e for e in events if e.significance_score is not None]
        unanalyzed = [e for e in events if e.significance_score is None]

        if not analyzed and not unanalyzed:
            print(f"\nNo events collected in the last {hours} hours.")
            print("Run: python3.9 agents/collector.py")
            return

        if not analyzed:
            print(f"\n⚠️ {len(unanalyzed)} events collected but none analyzed yet.")
            print("Run: python3.9 agents/analyzer.py --limit 10")
            return

        # Filter by minimum score
        significant = [e for e in analyzed if e.significance_score >= min_score]

        print(f"\nCollected: {len(events)} events | Analyzed: {len(analyzed)} | Significant (>{min_score}): {len(significant)}")

        if not significant:
            print(f"\nNo events scored >= {min_score} in last {hours} hours.")
            if analyzed:
                max_score = max(e.significance_score for e in analyzed)
                print(f"Highest score: {max_score:.0f}/100")
                print(f"\nTry: python3.9 agents/reporter_intelligent.py --min-score {int(max_score)-10}")
            return

        # Sort by significance
        significant.sort(key=lambda e: e.significance_score, reverse=True)

        # Group by relevance
        material = [e for e in significant if (e.investment_relevance or '').lower() == 'material']
        marginal = [e for e in significant if (e.investment_relevance or '').lower() == 'marginal']
        other = [e for e in significant if e not in material and e not in marginal]

        # Display material events first
        if material:
            self._print_events_section("⚠️ MATERIAL EVENTS", material)

        if marginal:
            self._print_events_section("📊 MARGINAL EVENTS", marginal)

        if other:
            self._print_events_section("📰 OTHER SIGNIFICANT EVENTS", other)

        # Show unanalyzed count
        if unanalyzed:
            print(f"\n{'─' * 80}")
            print(f"⏳ UNANALYZED: {len(unanalyzed)} events waiting for analysis")
            print("Run: python3.9 agents/analyzer.py --limit 10")

        # Stats
        print(f"\n{'=' * 80}")
        print("ANALYSIS SUMMARY")
        print('=' * 80)

        if analyzed:
            scores = [e.significance_score for e in analyzed]
            avg_score = sum(scores) / len(scores)

            sentiments = {}
            for e in analyzed:
                s = e.sentiment or 'unknown'
                sentiments[s] = sentiments.get(s, 0) + 1

            print(f"\nAverage significance: {avg_score:.1f}/100")
            print(f"Highest score: {max(scores):.0f}/100")
            print(f"Lowest score: {min(scores):.0f}/100")

            print(f"\nSentiment breakdown:")
            for sentiment, count in sorted(sentiments.items(), key=lambda x: x[1], reverse=True):
                print(f"  {sentiment}: {count}")

        print("\n" + "=" * 80 + "\n")

    def _print_events_section(self, title: str, events: list):
        """Print a section of events with full analysis"""
        print(f"\n{'━' * 80}")
        print(f"{title} ({len(events)})")
        print('━' * 80)

        for event in events:
            score = event.significance_score
            sentiment_emoji = {
                'positive': '📈',
                'negative': '📉',
                'neutral': '➡️',
                'mixed': '↕️',
            }.get(event.sentiment, '')

            print(f"\n[{score:.0f}/100] {sentiment_emoji} {event.title}")

            # Basic metadata
            meta = []
            if event.companies:
                meta.append(f"Companies: {', '.join(event.companies[:3])}")
            if event.published_at:
                meta.append(f"Published: {event.published_at.strftime('%Y-%m-%d %H:%M')}")
            if event.sentiment:
                meta.append(f"Sentiment: {event.sentiment}")
            if event.investment_relevance:
                meta.append(f"Relevance: {event.investment_relevance}")

            if meta:
                print(f"  {' | '.join(meta)}")

            # Agent analysis
            if event.implications:
                print(f"\n  💡 IMPLICATIONS:")
                # Wrap text
                implications = event.implications
                if len(implications) > 200:
                    implications = implications[:200] + "..."
                for line in implications.split('. '):
                    if line.strip():
                        print(f"     {line.strip()}")

            if event.affected_parties:
                print(f"\n  👥 AFFECTED PARTIES:")
                print(f"     {event.affected_parties}")

            if event.key_context:
                print(f"\n  📚 CONTEXT:")
                context = event.key_context
                if len(context) > 150:
                    context = context[:150] + "..."
                print(f"     {context}")

            print(f"\n  🔗 {event.source_url}")

    def show_top_events(self, limit: int = 10, days: int = 7):
        """Show top events by significance from recent period"""
        print(f"\n{'=' * 80}")
        print(f"TOP {limit} MOST SIGNIFICANT EVENTS (Last {days} days)")
        print('=' * 80)

        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE significance_score IS NOT NULL
              AND collected_at >= ?
            ORDER BY significance_score DESC
            LIMIT ?
        """, (cutoff.isoformat(), limit))

        from models.events import Event
        events = [Event.from_dict(dict(row)) for row in cursor.fetchall()]

        if not events:
            print("\nNo analyzed events found in this period.")
            return

        for i, event in enumerate(events, 1):
            score = event.significance_score
            sentiment_emoji = {
                'positive': '📈',
                'negative': '📉',
                'neutral': '➡️',
                'mixed': '↕️',
            }.get(event.sentiment, '')

            print(f"\n{i}. [{score:.0f}/100] {sentiment_emoji} {event.title}")

            if event.implications:
                impl = event.implications[:150]
                if len(event.implications) > 150:
                    impl += "..."
                print(f"   → {impl}")

        print()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='View intelligent AI sector briefing')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours to look back (default: 24)')
    parser.add_argument('--min-score', type=int, default=40,
                       help='Minimum significance score (default: 40)')
    parser.add_argument('--top', action='store_true',
                       help='Show top events by significance')
    parser.add_argument('--days', type=int, default=7,
                       help='Days for top events (default: 7)')
    parser.add_argument('--limit', type=int, default=10,
                       help='Number of top events (default: 10)')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database file path (default: ai_pulse.db)')

    args = parser.parse_args()

    with IntelligentReporter(db_path=args.db) as reporter:
        if args.top:
            reporter.show_top_events(limit=args.limit, days=args.days)
        else:
            reporter.generate_intelligent_briefing(
                hours=args.hours,
                min_score=args.min_score
            )
