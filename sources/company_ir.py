"""
Company Investor Relations RSS source.

Tracks press releases from AI sector companies' IR pages.

Why this matters: Direct from source, material disclosures, immediate market impact.
Examples: Earnings, product launches, strategic partnerships, acquisitions.
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models.events import Event, EventSource, EventType


class CompanyIRSource:
    """
    Fetches press releases from company IR pages.

    RSS feeds from investor relations pages are the authoritative source
    for material company announcements.
    """

    # Company RSS feeds
    IR_FEEDS = {
        'NVIDIA': 'https://nvidianews.nvidia.com/releases.xml',
        'Microsoft': 'https://www.microsoft.com/en-us/investor/events-and-presentations/default.aspx',  # Note: May need scraping
        'AMD': 'https://ir.amd.com/news-events/press-releases/rss',
        # Note: Many companies don't have RSS feeds anymore
        # We'll focus on those that do, or use alternative methods
    }

    # Additional tech news RSS feeds (company-specific)
    TECH_NEWS_FEEDS = {
        'NVIDIA': 'https://nvidianews.nvidia.com/releases.xml',
        'OpenAI': 'https://openai.com/news/rss',  # If available
        'Anthropic': 'https://www.anthropic.com/news/rss',  # If available
    }

    def __init__(self):
        """Initialize Company IR source"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Pulse/1.0 Investment Research',
        })

    def fetch_rss_feed(self, url: str, company: str, days_back: int = 7) -> List[dict]:
        """
        Fetch and parse RSS feed.

        Args:
            url: RSS feed URL
            company: Company name
            days_back: Days to look back

        Returns:
            List of news items
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            items = self._parse_rss_feed(response.text, company, days_back)
            return items

        except Exception as e:
            print(f"Error fetching {company} RSS: {e}")
            return []

    def _parse_rss_feed(self, xml_content: str, company: str, days_back: int) -> List[dict]:
        """Parse RSS/Atom feed"""
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
                if not published or published < cutoff:
                    continue

                items.append({
                    'company': company,
                    'title': title,
                    'link': link,
                    'description': description,
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
                    if not published or published < cutoff:
                        continue

                    items.append({
                        'company': company,
                        'title': title,
                        'link': link,
                        'description': description,
                        'published': published,
                    })

            return items

        except Exception as e:
            print(f"Error parsing RSS feed: {e}")
            return []

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        if not date_str:
            return None

        # Try various formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',  # RFC 822
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

    def classify_press_release(self, title: str, description: str) -> EventType:
        """Classify type of press release"""
        text = (title + " " + description).lower()

        if any(word in text for word in ['earnings', 'quarterly', 'results', 'revenue', 'profit']):
            return EventType.NEWS
        elif any(word in text for word in ['launch', 'introduces', 'announces', 'unveils', 'releases']):
            if any(word in text for word in ['chip', 'gpu', 'product', 'platform']):
                return EventType.PRODUCT_LAUNCH
            else:
                return EventType.NEWS
        elif any(word in text for word in ['partnership', 'collaboration', 'agreement', 'deal']):
            return EventType.PARTNERSHIP
        elif any(word in text for word in ['acquisition', 'acquires', 'merger']):
            return EventType.PARTNERSHIP
        else:
            return EventType.NEWS

    def item_to_event(self, item: dict) -> Event:
        """Convert RSS item to Event object"""

        event = Event(
            source=EventSource.COMPANY_IR,
            source_id=item['link'],
            source_url=item['link'],
            title=f"{item['company']}: {item['title']}",
            content=item['description'],
            summary=item['description'][:200] if len(item['description']) > 200 else item['description'],
            event_type=self.classify_press_release(item['title'], item['description']),
            companies=[item['company']],
            published_at=item['published'],
        )

        return event

    def fetch_all_companies(self, days_back: int = 7) -> List[Event]:
        """
        Fetch press releases from all tracked companies.

        Args:
            days_back: Days to look back

        Returns:
            List of Event objects
        """
        print(f"Fetching press releases from company IR feeds (last {days_back} days)...")

        all_events = []

        for company, feed_url in self.IR_FEEDS.items():
            print(f"  Checking {company}...", end=' ')

            items = self.fetch_rss_feed(feed_url, company, days_back)

            if items:
                print(f"✓ {len(items)} release(s)")
                for item in items:
                    event = self.item_to_event(item)
                    all_events.append(event)
                    print(f"    → {event.title[:80]}")
            else:
                print("No recent releases")

        print(f"\nFound {len(all_events)} press releases total")
        return all_events


# Test the source
if __name__ == "__main__":
    source = CompanyIRSource()

    print("Testing Company IR source...")
    print("=" * 80)

    events = source.fetch_all_companies(days_back=30)

    print(f"\nCollected {len(events)} events:\n")
    for event in events:
        print(f"[{event.event_type.value.upper()}] {event.title}")
        print(f"  Published: {event.published_at}")
        print(f"  URL: {event.source_url}")
        print()
