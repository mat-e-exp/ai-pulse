"""
Tech News RSS source.

Direct RSS feeds from major tech news sites.

Why this matters: Direct feeds from TechCrunch, VentureBeat, The Verge, etc.
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


class TechRSSSource:
    """
    Fetches news from tech publication RSS feeds.

    Direct RSS feeds from major tech news sources.
    """

    # Major tech news RSS feeds
    RSS_FEEDS = {
        'TechCrunch AI': 'https://techcrunch.com/category/artificial-intelligence/feed/',
        'VentureBeat AI': 'https://venturebeat.com/category/ai/feed/',
        'The Verge AI': 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml',
        'Ars Technica AI': 'https://feeds.arstechnica.com/arstechnica/technology-lab',
        'MIT Technology Review AI': 'https://www.technologyreview.com/topic/artificial-intelligence/feed',
        'AI News': 'https://www.artificialintelligence-news.com/feed/',
        'InfoWorld AI': 'https://www.infoworld.com/category/artificial-intelligence/index.rss',
    }

    def __init__(self):
        """Initialize Tech RSS source"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Pulse/1.0 Investment Research',
        })

    def fetch_rss_feed(self, url: str, feed_name: str, days_back: int = 1) -> List[dict]:
        """
        Fetch and parse RSS feed.

        Args:
            url: RSS feed URL
            feed_name: Name of the feed
            days_back: Days to look back

        Returns:
            List of news items
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            items = self._parse_rss_feed(response.text, feed_name, days_back)
            return items

        except Exception as e:
            print(f"Error fetching {feed_name}: {e}")
            return []

    def _parse_rss_feed(self, xml_content: str, feed_name: str, days_back: int) -> List[dict]:
        """Parse RSS feed (supports RSS 2.0 and Atom)"""
        try:
            root = ET.fromstring(xml_content)

            items = []
            cutoff = datetime.utcnow() - timedelta(days=days_back)

            # Try RSS 2.0 format first
            for item in root.findall('.//item'):
                title_elem = item.find('title')
                link_elem = item.find('link')
                pubdate_elem = item.find('pubDate')
                description_elem = item.find('description')

                if not all([title_elem, link_elem]):
                    continue

                title = title_elem.text
                link = link_elem.text
                description = description_elem.text if description_elem is not None else ""

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
                    'feed_name': feed_name,
                    'published': published,
                })

            # If no items, try Atom format
            if not items:
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('atom:entry', ns):
                    title_elem = entry.find('atom:title', ns)
                    link_elem = entry.find('atom:link', ns)
                    updated_elem = entry.find('atom:updated', ns)
                    summary_elem = entry.find('atom:summary', ns)

                    if not all([title_elem, link_elem]):
                        continue

                    title = title_elem.text
                    link = link_elem.get('href')
                    description = summary_elem.text if summary_elem is not None else ""

                    published = self._parse_date(updated_elem.text if updated_elem is not None else "")
                    if not published:
                        published = datetime.utcnow()

                    # Check if recent enough
                    if published < cutoff:
                        continue

                    items.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'feed_name': feed_name,
                        'published': published,
                    })

            return items

        except Exception as e:
            print(f"Error parsing RSS feed {feed_name}: {e}")
            return []

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        if not date_str:
            return None

        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 822
            '%a, %d %b %Y %H:%M:%S %Z',  # RFC 822 with timezone name
            '%Y-%m-%dT%H:%M:%S%z',       # ISO 8601
            '%Y-%m-%d',                   # Simple date
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue

        # Try fromisoformat as fallback
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
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
        """Convert RSS item to Event object"""
        companies = self.extract_companies(item['title'], item['description'])

        event = Event(
            source=EventSource.TECH_RSS,
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

    def fetch_all_feeds(self, days_back: int = 1, limit_per_feed: int = 10) -> List[Event]:
        """
        Fetch news from all RSS feeds.

        Args:
            days_back: Days to look back
            limit_per_feed: Max articles per feed

        Returns:
            List of Event objects
        """
        print(f"Fetching AI news from tech RSS feeds (last {days_back} days)...")

        all_events = []
        seen_urls = set()

        for feed_name, feed_url in self.RSS_FEEDS.items():
            print(f"  {feed_name}...", end=' ')

            items = self.fetch_rss_feed(feed_url, feed_name, days_back=days_back)

            # Deduplicate by URL
            unique_items = []
            for item in items:
                if item['link'] not in seen_urls:
                    seen_urls.add(item['link'])
                    unique_items.append(item)

            # Limit per feed
            unique_items = unique_items[:limit_per_feed]

            if unique_items:
                print(f"✓ {len(unique_items)} articles")
                for item in unique_items:
                    event = self.item_to_event(item)
                    all_events.append(event)
            else:
                print("No recent articles")

        print(f"\nFound {len(all_events)} articles from tech RSS feeds")
        return all_events


# Test the source
if __name__ == "__main__":
    source = TechRSSSource()

    print("Testing Tech RSS source...")
    print("=" * 80)

    events = source.fetch_all_feeds(days_back=1, limit_per_feed=5)

    print(f"\nCollected {len(events)} events:\n")
    for event in events[:10]:  # Show first 10
        print(f"[{event.event_type.value.upper()}] {event.title}")
        if event.companies:
            print(f"  Companies: {', '.join(event.companies)}")
        print(f"  Published: {event.published_at}")
        print(f"  URL: {event.source_url}")
        print()
