"""
Bing News API source.

Tracks AI sector news via Bing News Search API.

Why this matters: Free tier available (3,000 transactions/month).
Complements NewsAPI with Microsoft's news aggregation.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Optional
import sys
from pathlib import Path
import os
sys.path.append(str(Path(__file__).parent.parent))

from models.events import Event, EventSource, EventType


class BingNewsSource:
    """
    Fetches AI sector news from Bing News Search API.

    Free tier: 3,000 transactions per month
    Get API key at: https://portal.azure.com
    """

    BASE_URL = "https://api.bing.microsoft.com/v7.0/news/search"

    # AI-related search queries
    SEARCH_QUERIES = [
        'OpenAI OR Anthropic OR "Google AI"',
        'ChatGPT OR "Claude AI" OR Gemini',
        'NVIDIA AI OR "AMD AI" OR "Intel AI"',
        '"artificial intelligence" funding',
        '"machine learning" breakthrough',
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Bing News source.

        Args:
            api_key: Bing Search API key (or set BING_NEWS_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('BING_NEWS_API_KEY')
        if not self.api_key:
            raise ValueError("Bing News API key required. Set BING_NEWS_API_KEY env var or pass to constructor.")

        self.session = requests.Session()
        self.session.headers.update({
            'Ocp-Apim-Subscription-Key': self.api_key,
        })

    def fetch_query(self, query: str, count: int = 10, freshness: str = 'Day') -> List[dict]:
        """
        Fetch news for a specific query.

        Args:
            query: Search query
            count: Number of results (max 100)
            freshness: Day, Week, or Month

        Returns:
            List of news items
        """
        params = {
            'q': query,
            'count': count,
            'freshness': freshness,
            'mkt': 'en-US',
            'sortBy': 'Date',
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            articles = data.get('value', [])

            items = []
            for article in articles:
                items.append({
                    'title': article.get('name', ''),
                    'url': article.get('url', ''),
                    'description': article.get('description', ''),
                    'published': self._parse_date(article.get('datePublished', '')),
                    'provider': article.get('provider', [{}])[0].get('name', 'Unknown'),
                })

            return items

        except Exception as e:
            print(f"Error fetching Bing News for '{query}': {e}")
            return []

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse ISO 8601 date format"""
        if not date_str:
            return None

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
        """Convert news item to Event object"""
        companies = self.extract_companies(item['title'], item['description'])

        event = Event(
            source=EventSource.BING_NEWS,
            source_id=item['url'],
            source_url=item['url'],
            title=item['title'],
            content=item['description'],
            summary=item['description'][:200] if len(item['description']) > 200 else item['description'],
            event_type=self.classify_article(item['title'], item['description']),
            companies=companies,
            published_at=item['published'],
        )

        return event

    def fetch_ai_news(self, freshness: str = 'Day', limit: int = 30) -> List[Event]:
        """
        Fetch AI news from all queries.

        Args:
            freshness: Day, Week, or Month
            limit: Total articles to collect

        Returns:
            List of Event objects
        """
        print(f"Fetching AI news from Bing News API ({freshness})...")

        all_events = []
        seen_urls = set()

        articles_per_query = max(5, limit // len(self.SEARCH_QUERIES))

        for query in self.SEARCH_QUERIES:
            print(f"  Searching: {query}...", end=' ')

            items = self.fetch_query(query, count=articles_per_query, freshness=freshness)

            # Deduplicate by URL
            unique_items = []
            for item in items:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    unique_items.append(item)

            if unique_items:
                print(f"✓ {len(unique_items)} articles")
                for item in unique_items:
                    event = self.item_to_event(item)
                    all_events.append(event)
                    if len(all_events) >= limit:
                        break
            else:
                print("No articles")

            if len(all_events) >= limit:
                break

        print(f"\nFound {len(all_events)} unique articles from Bing News")
        return all_events


# Test the source
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv('BING_NEWS_API_KEY')
    if not api_key:
        print("Error: BING_NEWS_API_KEY not found in .env")
        print("Get free API key at: https://portal.azure.com")
        exit(1)

    source = BingNewsSource(api_key)

    print("Testing Bing News source...")
    print("=" * 80)

    events = source.fetch_ai_news(freshness='Day', limit=20)

    print(f"\nCollected {len(events)} events:\n")
    for event in events[:10]:  # Show first 10
        print(f"[{event.event_type.value.upper()}] {event.title}")
        if event.companies:
            print(f"  Companies: {', '.join(event.companies)}")
        print(f"  Published: {event.published_at}")
        print(f"  URL: {event.source_url}")
        print()
