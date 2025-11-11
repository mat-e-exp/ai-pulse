"""
Google News RSS source.

Tracks AI sector news via Google News RSS feeds.

Why this matters: Google aggregates news from hundreds of sources.
Free, no API key required.
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models.events import Event, EventSource, EventType


class GoogleNewsSource:
    """
    Fetches AI sector news from Google News RSS feeds.

    Google News RSS provides free access to aggregated news from many sources.
    """

    BASE_URL = "https://news.google.com/rss/search"

    # AI-related search queries
    SEARCH_QUERIES = [
        'artificial intelligence',
        'OpenAI',
        'Anthropic',
        'Google AI',
        'ChatGPT',
        'Claude AI',
        'machine learning',
        'GPT',
        'large language model',
        'AI chips NVIDIA',
    ]

    def __init__(self):
        """Initialize Google News source"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Pulse/1.0 Investment Research',
        })

    def fetch_query(self, query: str, days_back: int = 1) -> List[dict]:
        """
        Fetch news for a specific query.

        Args:
            query: Search query
            days_back: Days to look back

        Returns:
            List of news items
        """
        params = {
            'q': query,
            'hl': 'en-US',
            'gl': 'US',
            'ceid': 'US:en',
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            items = self._parse_rss_feed(response.text, days_back)
            return items

        except Exception as e:
            print(f"Error fetching Google News for '{query}': {e}")
            return []

    def _parse_rss_feed(self, xml_content: str, days_back: int) -> List[dict]:
        """Parse Google News RSS feed"""
        try:
            root = ET.fromstring(xml_content)

            items = []
            cutoff = datetime.utcnow() - timedelta(days=days_back)

            # Google News uses RSS 2.0 format
            for item in root.findall('.//item'):
                title_elem = item.find('title')
                link_elem = item.find('link')
                pubdate_elem = item.find('pubDate')
                description_elem = item.find('description')
                source_elem = item.find('source')

                if not all([title_elem, link_elem]):
                    continue

                title = title_elem.text
                link = link_elem.text
                description = description_elem.text if description_elem is not None else ""
                source_name = source_elem.text if source_elem is not None else "Google News"

                # Parse date
                published = self._parse_date(pubdate_elem.text if pubdate_elem is not None else "")
                if not published:
                    published = datetime.utcnow()

                # Check if recent enough
                if published < cutoff:
                    continue

                items.append({
                    'title': title,
                    'link': link,
                    'description': description,
                    'source_name': source_name,
                    'published': published,
                })

            return items

        except Exception as e:
            print(f"Error parsing Google News RSS: {e}")
            return []

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse RFC 822 date format"""
        if not date_str:
            return None

        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 822
            '%a, %d %b %Y %H:%M:%S %Z',  # RFC 822 with timezone name
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue

        return datetime.utcnow()

    def classify_article(self, title: str, description: str) -> EventType:
        """Classify article type"""
        text = (title + " " + description).lower()

        if any(word in text for word in ['funding', 'raises', 'investment', 'valuation', 'ipo']):
            return EventType.FUNDING
        elif any(word in text for word in ['launches', 'releases', 'unveils', 'announces new']):
            return EventType.PRODUCT_LAUNCH
        elif any(word in text for word in ['partnership', 'collaboration', 'deal', 'acquisition']):
            return EventType.PARTNERSHIP
        elif any(word in text for word in ['regulation', 'policy', 'law', 'legal', 'court']):
            return EventType.REGULATION
        elif any(word in text for word in ['research', 'paper', 'study', 'breakthrough']):
            return EventType.RESEARCH
        else:
            return EventType.NEWS

    def extract_companies(self, title: str, description: str) -> List[str]:
        """Extract company mentions"""
        text = title + " " + description
        companies = []

        company_names = [
            'OpenAI', 'Anthropic', 'Google', 'Microsoft', 'Meta', 'Amazon',
            'NVIDIA', 'AMD', 'Intel', 'Apple', 'Tesla', 'Oracle',
            'Hugging Face', 'Stability AI', 'Cohere', 'Mistral',
        ]

        for company in company_names:
            if company.lower() in text.lower():
                companies.append(company)

        return companies

    def item_to_event(self, item: dict) -> Event:
        """Convert news item to Event object"""
        companies = self.extract_companies(item['title'], item['description'])

        event = Event(
            source=EventSource.GOOGLE_NEWS,
            source_id=item['link'],
            source_url=item['link'],
            title=item['title'],
            content=item['description'],
            summary=item['description'][:200] if len(item['description']) > 200 else item['description'],
            event_type=self.classify_article(item['title'], item['description']),
            companies=companies,
            published_at=item['published'],
        )

        return event

    def fetch_all_queries(self, days_back: int = 1, limit_per_query: int = 10) -> List[Event]:
        """
        Fetch news from all tracked queries.

        Args:
            days_back: Days to look back
            limit_per_query: Max articles per query

        Returns:
            List of Event objects
        """
        print(f"Fetching AI news from Google News (last {days_back} days)...")

        all_events = []
        seen_urls = set()

        for query in self.SEARCH_QUERIES:
            print(f"  Searching: {query}...", end=' ')

            items = self.fetch_query(query, days_back=days_back)

            # Deduplicate by URL
            unique_items = []
            for item in items:
                if item['link'] not in seen_urls:
                    seen_urls.add(item['link'])
                    unique_items.append(item)

            # Limit per query
            unique_items = unique_items[:limit_per_query]

            if unique_items:
                print(f"✓ {len(unique_items)} articles")
                for item in unique_items:
                    event = self.item_to_event(item)
                    all_events.append(event)
            else:
                print("No articles")

        print(f"\nFound {len(all_events)} unique articles from Google News")
        return all_events


# Test the source
if __name__ == "__main__":
    source = GoogleNewsSource()

    print("Testing Google News source...")
    print("=" * 80)

    events = source.fetch_all_queries(days_back=1, limit_per_query=5)

    print(f"\nCollected {len(events)} events:\n")
    for event in events[:10]:  # Show first 10
        print(f"[{event.event_type.value.upper()}] {event.title}")
        if event.companies:
            print(f"  Companies: {', '.join(event.companies)}")
        print(f"  Published: {event.published_at}")
        print(f"  URL: {event.source_url}")
        print()
