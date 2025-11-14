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

    BASE_URL = "http://export.arxiv.org/api/query"

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
            max_results: Maximum number of results per category

        Returns:
            List of Event objects
        """
        events = []
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        print(f"Fetching AI/ML papers from arXiv (last {days_back} days, max {max_results} per category)...")

        for category in self.AI_CATEGORIES:
            try:
                # Build query: search category, sort by submission date
                query = f'cat:{category}'
                params = {
                    'search_query': query,
                    'start': 0,
                    'max_results': max_results,
                    'sortBy': 'submittedDate',
                    'sortOrder': 'descending'
                }

                response = self.session.get(self.BASE_URL, params=params, timeout=15)
                response.raise_for_status()

                # Parse XML response
                root = ET.fromstring(response.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom',
                      'arxiv': 'http://arxiv.org/schemas/atom'}

                for entry in root.findall('atom:entry', ns):
                    try:
                        # Extract paper details
                        title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                        summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                        link = entry.find('atom:id', ns).text
                        published_str = entry.find('atom:published', ns).text

                        # Parse published date
                        published_date = datetime.strptime(published_str, '%Y-%m-%dT%H:%M:%SZ')

                        # Skip if older than cutoff
                        if published_date < cutoff_date:
                            continue

                        # Extract authors
                        authors = []
                        for author in entry.findall('atom:author', ns):
                            name = author.find('atom:name', ns).text
                            authors.append(name)

                        # Extract primary category
                        primary_cat = entry.find('arxiv:primary_category', ns).attrib.get('term', category)

                        # Determine company/institution from authors (simplified - just take first author's affiliation if available)
                        companies = []

                        # Create event
                        event = Event(
                            title=title,
                            summary=summary[:500] if len(summary) > 500 else summary,  # Truncate long abstracts
                            content=summary,
                            source=EventSource.RESEARCH,
                            source_url=link,
                            event_type=EventType.RESEARCH,
                            companies=companies,
                            published_at=published_date,
                            collected_at=datetime.utcnow()
                        )

                        events.append(event)

                    except Exception as e:
                        print(f"  ✗ Error parsing entry: {e}")
                        continue

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
