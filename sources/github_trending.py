"""
GitHub trending source.

Tracks trending AI/ML repositories and major releases.

Why this matters: Open source releases signal competitive shifts.
Examples: LLaMA (Meta), Stable Diffusion (Stability AI), Whisper (OpenAI)
"""

import requests
from datetime import datetime, timedelta
from typing import List, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from models.events import Event, EventSource, EventType


class GitHubTrendingSource:
    """
    Tracks trending AI/ML repositories on GitHub.

    Signals:
    - New model releases (competitive shifts)
    - Major framework updates
    - Breakthrough implementations
    - Corporate open source activity
    """

    BASE_URL = "https://api.github.com"

    # AI/ML topics to track
    AI_TOPICS = [
        'artificial-intelligence',
        'machine-learning',
        'deep-learning',
        'llm',
        'large-language-models',
        'computer-vision',
        'nlp',
        'transformers',
        'pytorch',
        'tensorflow',
        'stable-diffusion',
        'gpt',
    ]

    # Companies to track (corporate open source)
    COMPANIES = [
        'openai',
        'anthropics',  # Anthropic's GitHub org
        'google',
        'google-research',
        'google-deepmind',
        'facebookresearch',  # Meta
        'microsoft',
        'huggingface',
        'stability-ai',
        'nvidia',
        'apple',
    ]

    def __init__(self):
        """Initialize GitHub source"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Pulse/1.0',
            'Accept': 'application/vnd.github.v3+json',
        })

    def search_trending_repos(self, days_back: int = 7, min_stars: int = 100) -> List[dict]:
        """
        Search for trending AI repositories.

        Args:
            days_back: Look for repos created/updated in last N days
            min_stars: Minimum stars to be considered significant

        Returns:
            List of repository dictionaries
        """
        cutoff = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        # Search for recently created/updated AI repos
        # GitHub search doesn't support OR in topics, so we search for one topic
        query = f"topic:artificial-intelligence created:>={cutoff} stars:>={min_stars}"

        url = f"{self.BASE_URL}/search/repositories"

        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 20,
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('items', [])

        except Exception as e:
            print(f"Error searching GitHub: {e}")
            return []

    def fetch_company_releases(self, org: str, days_back: int = 30) -> List[dict]:
        """
        Fetch recent releases from a company's GitHub org.

        Args:
            org: GitHub organization name
            days_back: Days to look back

        Returns:
            List of release dictionaries
        """
        url = f"{self.BASE_URL}/orgs/{org}/repos"

        params = {
            'type': 'public',
            'sort': 'updated',
            'per_page': 10,
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            repos = response.json()
            releases = []

            cutoff = datetime.utcnow() - timedelta(days=days_back)

            for repo in repos:
                # Check if repo has AI/ML topics
                topics = repo.get('topics', [])
                if not any(topic in self.AI_TOPICS for topic in topics):
                    continue

                # Fetch latest release
                release_url = f"{self.BASE_URL}/repos/{repo['full_name']}/releases/latest"
                try:
                    rel_response = self.session.get(release_url, timeout=5)
                    if rel_response.status_code == 200:
                        release = rel_response.json()

                        # Check if recent
                        published_str = release.get('published_at', '')
                        if published_str:
                            published = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                            if published >= cutoff:
                                releases.append({
                                    'repo': repo,
                                    'release': release,
                                })
                except:
                    pass

            return releases

        except Exception as e:
            print(f"Error fetching {org} releases: {e}")
            return []

    def classify_repo_type(self, repo: dict) -> EventType:
        """Classify repository significance"""
        description = (repo.get('description') or '').lower()
        name = repo.get('name', '').lower()

        if any(word in description + name for word in ['model', 'gpt', 'llm', 'llama']):
            return EventType.PRODUCT_LAUNCH
        elif any(word in description + name for word in ['framework', 'library', 'tool']):
            return EventType.RESEARCH
        else:
            return EventType.NEWS

    def repo_to_event(self, repo: dict, release: Optional[dict] = None) -> Event:
        """Convert GitHub repo/release to Event object"""

        if release:
            title = f"{repo['owner']['login']}/{repo['name']} releases {release['tag_name']}"
            content = release.get('body', '')
            url = release.get('html_url')
            published_at = datetime.fromisoformat(release['published_at'].replace('Z', '+00:00'))
        else:
            title = f"Trending: {repo['owner']['login']}/{repo['name']} ({repo['stargazers_count']} stars)"
            content = repo.get('description', '')
            url = repo.get('html_url')
            published_at = datetime.fromisoformat(repo['created_at'].replace('Z', '+00:00'))

        # Extract company if from known org
        owner = repo['owner']['login']
        companies = []
        company_map = {
            'openai': 'OpenAI',
            'facebookresearch': 'Meta',
            'google': 'Google',
            'google-research': 'Google',
            'google-deepmind': 'Google',
            'microsoft': 'Microsoft',
            'huggingface': 'Hugging Face',
            'stability-ai': 'Stability AI',
            'nvidia': 'NVIDIA',
            'apple': 'Apple',
        }
        if owner.lower() in company_map:
            companies.append(company_map[owner.lower()])

        event = Event(
            source=EventSource.GITHUB,
            source_id=str(repo['id']),
            source_url=url,
            title=title,
            content=content,
            summary=repo.get('description', ''),
            event_type=self.classify_repo_type(repo),
            companies=companies,
            products=[repo['name']],
            published_at=published_at,
        )

        return event

    def fetch_trending_ai(self, days_back: int = 7, min_stars: int = 500) -> List[Event]:
        """
        Fetch trending AI repositories and releases.

        Args:
            days_back: Days to look back
            min_stars: Minimum stars threshold

        Returns:
            List of Event objects
        """
        print(f"Fetching trending AI repositories from GitHub (last {days_back} days, >{min_stars} stars)...")

        events = []

        # 1. Search trending repos
        repos = self.search_trending_repos(days_back=days_back, min_stars=min_stars)
        print(f"  Found {len(repos)} trending repositories")

        for repo in repos[:10]:  # Limit to top 10
            event = self.repo_to_event(repo)
            events.append(event)
            print(f"  ✓ {event.title[:80]}")

        # 2. Check company releases
        print(f"\n  Checking company releases...")
        for company in self.COMPANIES[:5]:  # Limit to avoid rate limits
            releases = self.fetch_company_releases(company, days_back=days_back)
            if releases:
                print(f"  ✓ {company}: {len(releases)} release(s)")
                for item in releases:
                    event = self.repo_to_event(item['repo'], item['release'])
                    events.append(event)
                    print(f"    → {event.title[:80]}")

        print(f"\nFound {len(events)} GitHub events total")
        return events


# Test the source
if __name__ == "__main__":
    source = GitHubTrendingSource()

    print("Testing GitHub Trending source...")
    print("=" * 80)

    events = source.fetch_trending_ai(days_back=30, min_stars=100)

    print(f"\nCollected {len(events)} events:\n")
    for event in events:
        print(f"[{event.event_type.value.upper()}] {event.title}")
        if event.companies:
            print(f"  Companies: {', '.join(event.companies)}")
        print(f"  URL: {event.source_url}")
        print()
