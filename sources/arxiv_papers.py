"""
ArXiv data source.

Fetches AI/ML research papers from arXiv.org using their free API.
No API key required.

API Docs: https://info.arxiv.org/help/api/index.html
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models.events import Event, EventSource, EventType


class ArXivSource:
    """
    Fetches AI/ML research papers from arXiv.

    Strategy:
    1. Query arXiv API for recent papers in AI categories
    2. Filter by submission date
    3. Extract paper details (title, authors, abstract, link)
    4. Convert to Event objects with type=RESEARCH
    """

    # Use RSS feeds which actually return recent papers (API search is broken)
    RSS_BASE = "http://export.arxiv.org/rss/"

    # ArXiv categories for AI/ML research
    AI_CATEGORIES = [
        'cs.AI',  # Artificial Intelligence
        'cs.CL',  # Computation and Language (NLP)
        'cs.CV',  # Computer Vision and Pattern Recognition
        'cs.LG',  # Machine Learning
        'cs.NE',  # Neural and Evolutionary Computing
        'stat.ML',  # Machine Learning (Statistics)
    ]

    def __init__(self):
        """Initialize ArXiv source"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Pulse/1.0 (AI sector intelligence bot)'
        })

    def fetch_recent_papers(self, days_back: int = 7, max_results: int = 50) -> List[Event]:
        """
        Fetch recent AI/ML papers from arXiv.

        Args:
            days_back: Number of days to look back
            max_results: Maximum number of results per category (will fetch more to ensure recent papers)

        Returns:
            List of Event objects
        """
        events = []
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Fetch more results since we need to filter by date
        # ArXiv's sort parameters don't work reliably
        fetch_limit = max_results * 10  # Fetch 10x to ensure we get recent papers

        print(f"Fetching AI/ML papers from arXiv (last {days_back} days, up to {max_results} per category)...")

        for category in self.AI_CATEGORIES:
            try:
                # Use RSS feed - it actually returns recent papers
                rss_url = f"{self.RSS_BASE}{category}"

                print(f"  Querying {category} RSS...")
                response = self.session.get(rss_url, timeout=30)
                response.raise_for_status()

                # Parse RSS XML
                root = ET.fromstring(response.content)

                # RSS uses different namespace
                entries = root.findall('.//item')
                print(f"    Found {len(entries)} recent entries")

                category_count = 0
                for i, entry in enumerate(entries):
                    # Stop if we have enough for this category
                    if category_count >= max_results:
                        break

                    try:
                        # RSS format: title, link, description
                        title_elem = entry.find('title')
                        link_elem = entry.find('link')
                        desc_elem = entry.find('description')

                        # ElementTree elements evaluate to False if they have no children
                        # Must use "is not None" instead of truthiness check
                        if title_elem is None or not title_elem.text:
                            continue
                        if link_elem is None or not link_elem.text:
                            continue

                        title = title_elem.text.strip().replace('\n', ' ')
                        link = link_elem.text.strip()
                        summary = desc_elem.text.strip().replace('\n', ' ') if (desc_elem is not None and desc_elem.text) else title

                        # RSS doesn't include date - use current time
                        # RSS feeds only contain today's papers anyway
                        published_date = datetime.utcnow()

                        # Skip if older than cutoff (won't happen for RSS but keep logic)
                        if published_date < cutoff_date:
                            continue

                        # Create event
                        event = Event(
                            title=title,
                            summary=summary[:500] if len(summary) > 500 else summary,
                            content=summary,
                            source=EventSource.ARXIV,
                            source_url=link,
                            event_type=EventType.RESEARCH,
                            companies=[],
                            published_at=published_date,
                            collected_at=datetime.utcnow()
                        )

                        events.append(event)
                        category_count += 1

                    except Exception as e:
                        import traceback
                        print(f"  ✗ Error parsing entry: {e}")
                        traceback.print_exc()
                        continue

                print(f"    Kept {category_count} recent papers from {category}")

            except Exception as e:
                print(f"  ✗ Error fetching category {category}: {e}")
                continue

        # Deduplicate by URL (papers might appear in multiple categories)
        seen_urls = set()
        unique_events = []
        for event in events:
            if event.source_url not in seen_urls:
                seen_urls.add(event.source_url)
                unique_events.append(event)

        return unique_events


def test_arxiv_source():
    """Test the arXiv source"""
    source = ArXivSource()
    papers = source.fetch_recent_papers(days_back=7, max_results=10)

    print(f"\nFetched {len(papers)} recent AI/ML papers from arXiv")
    print("=" * 80)

    for i, paper in enumerate(papers[:5], 1):
        print(f"\n[{i}] {paper.title}")
        print(f"    Published: {paper.published_at}")
        print(f"    URL: {paper.source_url}")
        print(f"    Summary: {paper.summary[:150]}...")


if __name__ == "__main__":
    test_arxiv_source()
