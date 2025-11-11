"""
Hacker News data source.

Fetches AI-related stories from Hacker News using their free API.
No API key required.

API Docs: https://github.com/HackerNews/API
"""

import requests
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models.events import Event, EventSource, EventType


class HackerNewsSource:
    """
    Fetches AI-related stories from Hacker News.

    Strategy:
    1. Get top stories IDs
    2. Fetch details for each story
    3. Filter for AI-related content (keywords in title)
    4. Convert to Event objects
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    # Keywords that indicate AI-related content
    AI_KEYWORDS = [
        'ai', 'artificial intelligence', 'machine learning', 'ml',
        'gpt', 'claude', 'gemini', 'llm', 'language model',
        'openai', 'anthropic', 'google ai', 'deepmind',
        'nvidia', 'nvda', 'gpu', 'neural', 'transformer',
        'chatgpt', 'copilot', 'bard', 'llama',
        'dall-e', 'midjourney', 'stable diffusion',
        'agi', 'generative ai', 'foundation model',
    ]

    def __init__(self):
        """Initialize Hacker News source"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Pulse/1.0 (AI sector intelligence bot)'
        })

    def fetch_top_stories(self, limit: int = 100) -> List[int]:
        """
        Get IDs of top stories from Hacker News.

        Args:
            limit: Maximum number of story IDs to fetch

        Returns:
            List of story IDs
        """
        url = f"{self.BASE_URL}/topstories.json"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()

        story_ids = response.json()
        return story_ids[:limit]

    def fetch_story(self, story_id: int) -> Optional[dict]:
        """
        Fetch details for a specific story.

        Args:
            story_id: Hacker News story ID

        Returns:
            Story data as dictionary, or None if failed
        """
        url = f"{self.BASE_URL}/item/{story_id}.json"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching story {story_id}: {e}")
            return None

    def is_ai_related(self, title: str, url: str = "") -> bool:
        """
        Check if a story is AI-related based on keywords.

        Args:
            title: Story title
            url: Story URL (optional)

        Returns:
            True if AI-related, False otherwise
        """
        text = (title + " " + url).lower()

        for keyword in self.AI_KEYWORDS:
            if keyword in text:
                return True

        return False

    def classify_event_type(self, title: str, url: str = "") -> EventType:
        """
        Try to classify the type of event from title/URL.

        This is basic heuristic matching - the agent will do better later.
        """
        text = (title + " " + url).lower()

        if any(word in text for word in ['announces', 'launches', 'releases', 'unveils', 'introduces']):
            return EventType.PRODUCT_LAUNCH
        elif any(word in text for word in ['raises', 'funding', 'investment', 'series', 'valuation']):
            return EventType.FUNDING
        elif 'arxiv' in text or 'paper' in text or 'research' in text:
            return EventType.RESEARCH
        else:
            return EventType.NEWS

    def story_to_event(self, story: dict) -> Event:
        """
        Convert HN story data to Event object.

        Args:
            story: Raw story data from HN API

        Returns:
            Event object
        """
        title = story.get('title', '')
        url = story.get('url', f"https://news.ycombinator.com/item?id={story['id']}")

        # Parse timestamp (HN uses Unix timestamp)
        published_at = None
        if story.get('time'):
            published_at = datetime.fromtimestamp(story['time'])

        event = Event(
            source=EventSource.HACKER_NEWS,
            source_id=str(story['id']),
            source_url=url,
            title=title,
            content=story.get('text'),  # Story text if it's a self-post
            event_type=self.classify_event_type(title, url),
            published_at=published_at,
        )

        return event

    def fetch_ai_stories(self, limit: int = 50, top_n: int = 200) -> List[Event]:
        """
        Fetch AI-related stories from Hacker News.

        Args:
            limit: Maximum number of AI stories to return
            top_n: Number of top stories to scan for AI content

        Returns:
            List of Event objects
        """
        print(f"Fetching top {top_n} stories from Hacker News...")
        story_ids = self.fetch_top_stories(limit=top_n)

        print(f"Scanning {len(story_ids)} stories for AI content...")
        ai_events = []

        for story_id in story_ids:
            if len(ai_events) >= limit:
                break

            story = self.fetch_story(story_id)
            if not story:
                continue

            # Skip jobs, polls, etc - only want stories
            if story.get('type') != 'story':
                continue

            title = story.get('title', '')
            url = story.get('url', '')

            if self.is_ai_related(title, url):
                event = self.story_to_event(story)
                ai_events.append(event)
                print(f"  ✓ Found: {title[:80]}")

        print(f"\nFound {len(ai_events)} AI-related stories")
        return ai_events


# Test the source
if __name__ == "__main__":
    source = HackerNewsSource()

    print("Testing Hacker News source...")
    print("=" * 80)

    events = source.fetch_ai_stories(limit=10, top_n=100)

    print(f"\nCollected {len(events)} events:\n")
    for event in events:
        print(f"[{event.event_type.value.upper()}] {event.title}")
        print(f"  URL: {event.source_url}")
        print(f"  Published: {event.published_at}")
        print()
