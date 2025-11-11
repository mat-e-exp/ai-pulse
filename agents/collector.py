"""
Data collection agent.

Orchestrates fetching AI sector data from multiple sources and storing in database.

This is NOT yet "agentic" - it's a simple orchestrator.
Phase 2 will add the LLM-based decision making.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
from datetime import datetime
from dotenv import load_dotenv

from sources.hackernews import HackerNewsSource
from sources.newsapi import NewsAPISource
from storage.db import EventDatabase
from models.events import Event


class DataCollector:
    """
    Collects AI sector data from multiple sources.

    Current sources:
    - Hacker News (always enabled, no API key)
    - NewsAPI (enabled if API key present)

    Future sources:
    - Twitter/X
    - Reddit
    - ArXiv
    - GitHub
    """

    def __init__(self, db_path: str = "ai_pulse.db"):
        """
        Initialize collector.

        Args:
            db_path: Path to SQLite database
        """
        load_dotenv()  # Load .env file

        self.db = EventDatabase(db_path)

        # Initialize sources
        self.sources = {}

        # Hacker News (always available)
        self.sources['hackernews'] = HackerNewsSource()

        # NewsAPI (if key available)
        news_api_key = os.getenv('NEWS_API_KEY')
        if news_api_key:
            self.sources['newsapi'] = NewsAPISource(news_api_key)
            print("✓ NewsAPI enabled")
        else:
            print("⚠ NewsAPI disabled (no API key found)")

    def collect_from_hackernews(self, limit: int = 20) -> dict:
        """
        Collect from Hacker News.

        Args:
            limit: Max stories to collect

        Returns:
            Stats dict
        """
        print("\n" + "=" * 80)
        print("COLLECTING FROM HACKER NEWS")
        print("=" * 80)

        source = self.sources['hackernews']
        events = source.fetch_ai_stories(limit=limit, top_n=200)

        result = self.db.save_events(events)

        print(f"\n✓ Hacker News: {result['saved']} new, {result['duplicates']} duplicates")
        return result

    def collect_from_newsapi(self, days_back: int = 1, limit: int = 30) -> dict:
        """
        Collect from NewsAPI.

        Args:
            days_back: How many days of history
            limit: Max articles to collect

        Returns:
            Stats dict
        """
        if 'newsapi' not in self.sources:
            print("⚠ NewsAPI not configured (skipping)")
            return {'saved': 0, 'duplicates': 0}

        print("\n" + "=" * 80)
        print("COLLECTING FROM NEWSAPI")
        print("=" * 80)

        source = self.sources['newsapi']
        events = source.fetch_ai_news(days_back=days_back, limit=limit)

        result = self.db.save_events(events)

        print(f"\n✓ NewsAPI: {result['saved']} new, {result['duplicates']} duplicates")
        return result

    def collect_all(self, hn_limit: int = 20, news_days: int = 1, news_limit: int = 30) -> dict:
        """
        Collect from all available sources.

        Args:
            hn_limit: Hacker News story limit
            news_days: NewsAPI days back
            news_limit: NewsAPI article limit

        Returns:
            Combined stats
        """
        print("\n" + "=" * 80)
        print(f"AI-PULSE DATA COLLECTION - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 80)

        total_saved = 0
        total_duplicates = 0

        # Collect from Hacker News
        hn_stats = self.collect_from_hackernews(limit=hn_limit)
        total_saved += hn_stats['saved']
        total_duplicates += hn_stats['duplicates']

        # Collect from NewsAPI
        news_stats = self.collect_from_newsapi(days_back=news_days, limit=news_limit)
        total_saved += news_stats['saved']
        total_duplicates += news_stats['duplicates']

        # Show database stats
        print("\n" + "=" * 80)
        print("DATABASE SUMMARY")
        print("=" * 80)

        db_stats = self.db.get_stats()
        print(f"Total events in database: {db_stats['total_events']}")
        print(f"Events collected (last 24h): {db_stats['last_24h']}")
        print(f"\nBy source:")
        for source, count in db_stats['by_source'].items():
            print(f"  {source}: {count}")
        print(f"\nBy type:")
        for event_type, count in db_stats['by_type'].items():
            print(f"  {event_type}: {count}")

        print("\n" + "=" * 80)
        print(f"COLLECTION COMPLETE: {total_saved} new events, {total_duplicates} duplicates")
        print("=" * 80 + "\n")

        return {
            'saved': total_saved,
            'duplicates': total_duplicates,
            'total_in_db': db_stats['total_events'],
        }

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

    parser = argparse.ArgumentParser(description='Collect AI sector data')
    parser.add_argument('--hn-limit', type=int, default=20,
                       help='Max Hacker News stories (default: 20)')
    parser.add_argument('--news-days', type=int, default=1,
                       help='NewsAPI days back (default: 1)')
    parser.add_argument('--news-limit', type=int, default=30,
                       help='Max NewsAPI articles (default: 30)')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database file path (default: ai_pulse.db)')

    args = parser.parse_args()

    # Run collector
    with DataCollector(db_path=args.db) as collector:
        collector.collect_all(
            hn_limit=args.hn_limit,
            news_days=args.news_days,
            news_limit=args.news_limit
        )
