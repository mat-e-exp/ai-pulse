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
from sources.sec_edgar import SECEdgarSource
from sources.github_trending import GitHubTrendingSource
from sources.company_ir import CompanyIRSource
from storage.db import EventDatabase
from models.events import Event

# DISABLED SOURCES (2025-11-11):
# - Google News RSS: Feed structure incompatible, returns no results
# - Bing News API: Requires separate API key (BING_NEWS_API_KEY)
# - Tech RSS Feeds: Inconsistent/broken feeds, parsing errors
# These sources exist in sources/ directory but not integrated into collector


class DataCollector:
    """
    Collects AI sector data from multiple sources.

    Active sources:
    - Hacker News (always enabled, no API key)
    - NewsAPI (enabled if API key present)
    - SEC EDGAR (always enabled, no API key)
    - GitHub Trending (always enabled, no API key)
    - Company IR RSS (always enabled, no API key)

    Future sources:
    - Twitter/X
    - Reddit
    - ArXiv
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

        # SEC EDGAR (always available)
        self.sources['sec_edgar'] = SECEdgarSource()

        # GitHub (always available)
        self.sources['github'] = GitHubTrendingSource()

        # Company IR (always available)
        self.sources['company_ir'] = CompanyIRSource()

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

    def collect_from_sec_edgar(self, filing_type: str = '8-K', days_back: int = 7) -> dict:
        """
        Collect from SEC EDGAR.

        Args:
            filing_type: Type of filing (8-K, 10-Q, etc.)
            days_back: How many days of history

        Returns:
            Stats dict
        """
        print("\n" + "=" * 80)
        print("COLLECTING FROM SEC EDGAR")
        print("=" * 80)

        source = self.sources['sec_edgar']
        events = source.fetch_all_companies(filing_type=filing_type, days_back=days_back)

        result = self.db.save_events(events)

        print(f"\n✓ SEC EDGAR: {result['saved']} new, {result['duplicates']} duplicates")
        return result

    def collect_from_github(self, days_back: int = 7, min_stars: int = 500) -> dict:
        """
        Collect from GitHub trending.

        Args:
            days_back: How many days of history
            min_stars: Minimum stars threshold

        Returns:
            Stats dict
        """
        print("\n" + "=" * 80)
        print("COLLECTING FROM GITHUB")
        print("=" * 80)

        source = self.sources['github']
        events = source.fetch_trending_ai(days_back=days_back, min_stars=min_stars)

        result = self.db.save_events(events)

        print(f"\n✓ GitHub: {result['saved']} new, {result['duplicates']} duplicates")
        return result

    def collect_from_company_ir(self, days_back: int = 7) -> dict:
        """
        Collect from Company IR feeds.

        Args:
            days_back: How many days of history

        Returns:
            Stats dict
        """
        print("\n" + "=" * 80)
        print("COLLECTING FROM COMPANY IR")
        print("=" * 80)

        source = self.sources['company_ir']
        events = source.fetch_all_companies(days_back=days_back)

        result = self.db.save_events(events)

        print(f"\n✓ Company IR: {result['saved']} new, {result['duplicates']} duplicates")
        return result

    def collect_all(self, hn_limit: int = 20, news_days: int = 1, news_limit: int = 30,
                    sec_days: int = 30, github_days: int = 30, github_stars: int = 100,
                    ir_days: int = 30) -> dict:
        """
        Collect from all available sources.

        Args:
            hn_limit: Hacker News story limit
            news_days: NewsAPI days back
            news_limit: NewsAPI article limit
            sec_days: SEC EDGAR days back
            github_days: GitHub days back
            github_stars: GitHub minimum stars
            ir_days: Company IR days back

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

        # Collect from SEC EDGAR
        sec_stats = self.collect_from_sec_edgar(days_back=sec_days)
        total_saved += sec_stats['saved']
        total_duplicates += sec_stats['duplicates']

        # Collect from GitHub
        github_stats = self.collect_from_github(days_back=github_days, min_stars=github_stars)
        total_saved += github_stats['saved']
        total_duplicates += github_stats['duplicates']

        # Collect from Company IR
        ir_stats = self.collect_from_company_ir(days_back=ir_days)
        total_saved += ir_stats['saved']
        total_duplicates += ir_stats['duplicates']

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
    parser.add_argument('--sec-days', type=int, default=30,
                       help='SEC EDGAR days back (default: 30)')
    parser.add_argument('--github-days', type=int, default=30,
                       help='GitHub days back (default: 30)')
    parser.add_argument('--github-stars', type=int, default=100,
                       help='GitHub minimum stars (default: 100)')
    parser.add_argument('--ir-days', type=int, default=30,
                       help='Company IR days back (default: 30)')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database file path (default: ai_pulse.db)')

    args = parser.parse_args()

    # Run collector
    with DataCollector(db_path=args.db) as collector:
        collector.collect_all(
            hn_limit=args.hn_limit,
            news_days=args.news_days,
            news_limit=args.news_limit,
            sec_days=args.sec_days,
            github_days=args.github_days,
            github_stars=args.github_stars,
            ir_days=args.ir_days
        )
