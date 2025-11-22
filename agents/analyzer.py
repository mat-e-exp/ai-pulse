"""
Analyzer agent - adds autonomous reasoning to collected events.

This agent decides what's important and why. This is what makes the system "agentic".
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

from storage.db import EventDatabase
from analysis.significance import SignificanceAnalyzer


class AnalyzerAgent:
    """
    Autonomous agent that analyzes event significance.

    This is AGENTIC because it:
    1. Decides what to analyze (prioritization)
    2. Reasons about significance (using LLM)
    3. Stores conclusions for later use
    4. Can be run continuously or on-demand

    Beta mode (2025-11-22): Uses Haiku for all analysis (~$0.002/event, ~$3/month)
    Future: Upgrade to Sonnet (~$0.08/event) or Opus (~$0.40/event) for quality
    """

    def __init__(self, db_path: str = "ai_pulse.db"):
        """
        Initialize analyzer agent.

        Args:
            db_path: Path to SQLite database
        """
        load_dotenv()

        self.db = EventDatabase(db_path)
        self.analyzer = SignificanceAnalyzer()

    def analyze_unanalyzed_events(self, limit: int = 10) -> dict:
        """
        Find events that haven't been analyzed yet and analyze them.

        This is autonomous decision-making:
        - Agent decides which events need analysis
        - Prioritizes by type
        - Analyzes and stores results

        Args:
            limit: Max number of events to analyze

        Returns:
            Stats dictionary
        """
        print("\n" + "=" * 80)
        print("AI-PULSE ANALYZER AGENT")
        print("=" * 80)

        # Find unanalyzed events
        print("\nFinding events that need analysis...")

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE significance_score IS NULL
              AND (is_duplicate IS NULL OR is_duplicate = 0)
              AND (is_semantic_duplicate IS NULL OR is_semantic_duplicate = 0)
            ORDER BY collected_at DESC
            LIMIT ?
        """, (limit * 2,))  # Fetch extra in case some fail

        from models.events import Event
        unanalyzed = [Event.from_dict(dict(row)) for row in cursor.fetchall()]

        if not unanalyzed:
            print("✓ All events have been analyzed!")
            return {'analyzed': 0, 'skipped': 0}

        print(f"Found {len(unanalyzed)} unanalyzed events")

        # Analyze them
        result = self.analyzer.analyze_batch(unanalyzed, max_analyze=limit)

        # Store analysis results in database
        print("\nStoring analysis results...")

        for item in result['analyzed']:
            event = item['event']
            analysis = item['analysis']

            if event.id:
                self.db.update_event_analysis(event.id, analysis)
                print(f"  ✓ Stored analysis for: {event.title[:60]}...")

        print("\n" + "=" * 80)
        print(f"COMPLETE: {len(result['analyzed'])} events analyzed")
        print("=" * 80 + "\n")

        return {
            'analyzed': len(result['analyzed']),
            'skipped': len(result['skipped']),
        }

    def reanalyze_low_scores(self, threshold: int = 30, limit: int = 5):
        """
        Re-analyze events that scored low to see if context has changed.

        This demonstrates agent memory and re-evaluation.
        """
        print("\nRe-analyzing low-scoring events...")

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE significance_score IS NOT NULL
              AND significance_score < ?
            ORDER BY collected_at DESC
            LIMIT ?
        """, (threshold, limit))

        from models.events import Event
        low_score_events = [Event.from_dict(dict(row)) for row in cursor.fetchall()]

        if not low_score_events:
            print(f"No events found with score < {threshold}")
            return

        print(f"Found {len(low_score_events)} events with score < {threshold}")

        for event in low_score_events:
            print(f"\nRe-analyzing: {event.title[:60]}...")
            print(f"  Previous score: {event.significance_score}")

            analysis = self.analyzer.analyze_event(event)
            new_score = analysis['significance_score']

            print(f"  New score: {new_score}")

            if abs(new_score - event.significance_score) > 10:
                print(f"  ⚠️ Significant change! Updating database...")
                self.db.update_event_analysis(event.id, analysis)

    def get_top_events(self, limit: int = 10, hours: int = 24) -> list:
        """
        Get most significant events from recent period.

        Returns events sorted by significance score.
        """
        from datetime import timedelta, datetime

        cutoff = datetime.utcnow() - timedelta(hours=hours)

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE significance_score IS NOT NULL
              AND collected_at >= ?
            ORDER BY significance_score DESC
            LIMIT ?
        """, (cutoff.isoformat(), limit))

        from models.events import Event
        return [Event.from_dict(dict(row)) for row in cursor.fetchall()]

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

    parser = argparse.ArgumentParser(description='Analyze AI sector events for significance (Haiku beta)')
    parser.add_argument('--limit', type=int, default=10,
                       help='Max events to analyze (default: 10)')
    parser.add_argument('--reanalyze', action='store_true',
                       help='Re-analyze low-scoring events')
    parser.add_argument('--threshold', type=int, default=30,
                       help='Score threshold for re-analysis (default: 30)')
    parser.add_argument('--top', action='store_true',
                       help='Show top events by significance')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database file path (default: ai_pulse.db)')

    args = parser.parse_args()

    # Check for API key
    load_dotenv()
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("Add to .env file or export in shell")
        print("Get key at: https://console.anthropic.com/")
        sys.exit(1)

    with AnalyzerAgent(db_path=args.db) as agent:
        if args.reanalyze:
            agent.reanalyze_low_scores(threshold=args.threshold, limit=args.limit)
        elif args.top:
            events = agent.get_top_events(limit=args.limit)
            print(f"\nTop {len(events)} most significant events:\n")
            for i, event in enumerate(events, 1):
                print(f"{i}. [{event.significance_score:.0f}/100] {event.title}")
                print(f"   {event.sentiment} | {event.investment_relevance}")
                if event.implications:
                    print(f"   → {event.implications[:100]}...")
                print()
        else:
            agent.analyze_unanalyzed_events(limit=args.limit)
