"""
NewsAPI data source.

Fetches AI-related news from NewsAPI.org.
Requires free API key: https://newsapi.org/register

Free tier: 100 requests/day, 1 month of history
"""

import requests
from datetime import datetime, timedelta
from typing import List, Optional
import os
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models.events import Event, EventSource, EventType


class NewsAPISource:
    """
    Fetches AI sector news from NewsAPI.

    Query strategy:
    - Search for AI-related keywords
    - Filter for tech/business sources
    - Focus on major announcements and developments
    """

    BASE_URL = "https://newsapi.org/v2"

    # AI-specific search queries
    SEARCH_QUERIES = [
        'OpenAI OR Anthropic OR "Google AI" OR DeepMind',
        'GPT OR Claude OR Gemini OR LLaMA',
        '"artificial intelligence" AND (launch OR funding OR breakthrough)',
        'NVIDIA AND ("AI chips" OR GPU OR "data center")',
        '"machine learning" AND (startup OR investment)',
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NewsAPI source.

        Args:
            api_key: NewsAPI key. If None, reads from NEWS_API_KEY env var
        """
        self.api_key = api_key or os.getenv('NEWS_API_KEY')
        if not self.api_key:
            raise ValueError(
                "NewsAPI key required. Set NEWS_API_KEY environment variable "
                "or pass api_key parameter. Get free key at https://newsapi.org/register"
            )

        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': self.api_key,
            'User-Agent': 'AI-Pulse/1.0'
        })

    def search_articles(self, query: str, from_date: datetime, to_date: datetime,
                       language: str = 'en', sort_by: str = 'publishedAt') -> List[dict]:
        """
        Search for articles matching query.

        Args:
            query: Search query
            from_date: Start date
            to_date: End date
            language: Article language
            sort_by: Sort order (publishedAt, relevancy, popularity)

        Returns:
            List of article dictionaries
        """
        url = f"{self.BASE_URL}/everything"

        params = {
            'q': query,
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d'),
            'language': language,
            'sortBy': sort_by,
            'pageSize': 100,  # Max per request
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get('status') != 'ok':
                print(f"NewsAPI error: {data.get('message')}")
                return []

            return data.get('articles', [])

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("NewsAPI authentication failed. Check your API key.")
            elif e.response.status_code == 426:
                print("NewsAPI upgrade required. Free tier may have limitations.")
            elif e.response.status_code == 429:
                print("NewsAPI rate limit exceeded. Free tier: 100 requests/day.")
            else:
                print(f"NewsAPI HTTP error: {e}")
            return []

        except Exception as e:
            print(f"Error fetching from NewsAPI: {e}")
            return []

    def classify_event_type(self, title: str, description: str = "") -> EventType:
        """Classify event type from article content"""
        text = (title + " " + description).lower()

        if any(word in text for word in ['announces', 'launches', 'releases', 'unveils', 'introduces', 'debuts']):
            return EventType.PRODUCT_LAUNCH
        elif any(word in text for word in ['raises', 'funding', 'investment', 'series', 'valuation', 'ipo']):
            return EventType.FUNDING
        elif any(word in text for word in ['partners', 'partnership', 'acquisition', 'acquires', 'merger']):
            return EventType.PARTNERSHIP
        elif any(word in text for word in ['regulation', 'regulatory', 'policy', 'law', 'legislation']):
            return EventType.REGULATION
        else:
            return EventType.NEWS

    def article_to_event(self, article: dict) -> Event:
        """
        Convert NewsAPI article to Event object.

        Args:
            article: Raw article data from NewsAPI

        Returns:
            Event object
        """
        # Parse published date
        published_at = None
        if article.get('publishedAt'):
            try:
                # NewsAPI uses ISO 8601 format
                published_at = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
            except:
                pass

        # Extract companies/products from content (basic heuristics)
        # The agent will do better extraction later
        companies = []
        text = (article.get('title', '') + " " + article.get('description', '')).lower()

        company_keywords = {
            'OpenAI': ['openai', 'open ai'],
            'Anthropic': ['anthropic', 'claude'],
            'Google': ['google', 'deepmind', 'gemini'],
            'Microsoft': ['microsoft', 'msft'],
            'Meta': ['meta', 'facebook'],
            'NVIDIA': ['nvidia', 'nvda'],
            'AMD': ['amd', 'advanced micro devices'],
            'Amazon': ['amazon', 'aws'],
        }

        for company, keywords in company_keywords.items():
            if any(kw in text for kw in keywords):
                companies.append(company)

        event = Event(
            source=EventSource.NEWS_API,
            source_id=article.get('url'),  # Use URL as ID
            source_url=article.get('url', ''),
            title=article.get('title', ''),
            content=article.get('content'),
            summary=article.get('description'),
            event_type=self.classify_event_type(
                article.get('title', ''),
                article.get('description', '')
            ),
            companies=companies,
            published_at=published_at,
        )

        return event

    def fetch_ai_news(self, days_back: int = 1, limit: int = 50) -> List[Event]:
        """
        Fetch AI-related news from the last N days.

        Args:
            days_back: How many days of history to fetch
            limit: Maximum number of articles to return

        Returns:
            List of Event objects
        """
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(days=days_back)

        print(f"Fetching AI news from NewsAPI ({days_back} days back)...")

        all_articles = []
        seen_urls = set()

        # Run multiple queries to get diverse coverage
        for query in self.SEARCH_QUERIES:
            print(f"  Searching: {query[:50]}...")

            articles = self.search_articles(query, from_date, to_date)

            # Deduplicate by URL
            for article in articles:
                url = article.get('url')
                if url and url not in seen_urls:
                    all_articles.append(article)
                    seen_urls.add(url)

            if len(all_articles) >= limit:
                break

        print(f"Found {len(all_articles)} unique articles")

        # Convert to Events
        events = []
        for article in all_articles[:limit]:
            event = self.article_to_event(article)
            events.append(event)
            print(f"  ✓ {event.title[:80]}")

        return events


# Test the source
if __name__ == "__main__":
    # Need API key to test
    api_key = os.getenv('NEWS_API_KEY')

    if not api_key:
        print("ERROR: Set NEWS_API_KEY environment variable to test NewsAPI")
        print("Get free key at: https://newsapi.org/register")
        sys.exit(1)

    source = NewsAPISource(api_key)

    print("Testing NewsAPI source...")
    print("=" * 80)

    events = source.fetch_ai_news(days_back=2, limit=10)

    print(f"\nCollected {len(events)} events:\n")
    for event in events:
        print(f"[{event.event_type.value.upper()}] {event.title}")
        print(f"  Companies: {', '.join(event.companies) if event.companies else 'None detected'}")
        print(f"  Published: {event.published_at}")
        print(f"  URL: {event.source_url}")
        print()
