"""
Event data models for AI-Pulse.

An Event represents any piece of information we collect about the AI sector:
- News articles
- Product launches
- Funding announcements
- Technical papers
- Social media posts
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class EventType(Enum):
    """Categories of events we track"""
    NEWS = "news"                    # General news article
    PRODUCT_LAUNCH = "product_launch"  # New model, feature, API
    FUNDING = "funding"              # VC rounds, investments
    RESEARCH = "research"            # ArXiv papers, technical breakthroughs
    SOCIAL = "social"                # Twitter/X, Hacker News, Reddit posts
    MARKET = "market"                # Stock movements, analyst reports
    REGULATION = "regulation"        # Policy, legal developments
    PARTNERSHIP = "partnership"      # Strategic deals, collaborations
    UNKNOWN = "unknown"              # Can't classify yet


class EventSource(Enum):
    """Where did this event come from?"""
    HACKER_NEWS = "hackernews"
    NEWS_API = "newsapi"
    TWITTER = "twitter"
    REDDIT = "reddit"
    ARXIV = "arxiv"
    GITHUB = "github"
    MANUAL = "manual"
    UNKNOWN = "unknown"


@dataclass
class Event:
    """
    Represents a single event in the AI sector.

    This is the core data structure - everything we collect gets stored as an Event.
    """
    # Identity
    id: Optional[int] = None          # Database ID (auto-assigned)

    # Source information
    source: EventSource = EventSource.UNKNOWN
    source_id: Optional[str] = None   # External ID (e.g., HN item ID)
    source_url: str = ""              # Original URL

    # Event content
    title: str = ""                   # Headline/title
    content: Optional[str] = None     # Full text content
    summary: Optional[str] = None     # Brief summary

    # Classification
    event_type: EventType = EventType.UNKNOWN

    # Entities mentioned (companies, products, people)
    companies: List[str] = None       # e.g., ["OpenAI", "Microsoft"]
    products: List[str] = None        # e.g., ["GPT-5", "Claude 4"]
    people: List[str] = None          # e.g., ["Sam Altman"]

    # Metadata
    published_at: Optional[datetime] = None  # When was it published?
    collected_at: datetime = None     # When did we collect it?

    # Analysis (added later by agent)
    significance_score: Optional[float] = None  # 0-100, how important?
    sentiment: Optional[str] = None    # positive, negative, neutral
    analysis: Optional[str] = None     # Agent's reasoning

    def __post_init__(self):
        """Initialize defaults"""
        if self.companies is None:
            self.companies = []
        if self.products is None:
            self.products = []
        if self.people is None:
            self.people = []
        if self.collected_at is None:
            self.collected_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'source': self.source.value,
            'source_id': self.source_id,
            'source_url': self.source_url,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'event_type': self.event_type.value,
            'companies': ','.join(self.companies) if self.companies else None,
            'products': ','.join(self.products) if self.products else None,
            'people': ','.join(self.people) if self.people else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'significance_score': self.significance_score,
            'sentiment': self.sentiment,
            'analysis': self.analysis,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        """Create Event from database row"""
        return cls(
            id=data.get('id'),
            source=EventSource(data['source']) if data.get('source') else EventSource.UNKNOWN,
            source_id=data.get('source_id'),
            source_url=data.get('source_url', ''),
            title=data.get('title', ''),
            content=data.get('content'),
            summary=data.get('summary'),
            event_type=EventType(data['event_type']) if data.get('event_type') else EventType.UNKNOWN,
            companies=data.get('companies').split(',') if data.get('companies') else [],
            products=data.get('products').split(',') if data.get('products') else [],
            people=data.get('people').split(',') if data.get('people') else [],
            published_at=datetime.fromisoformat(data['published_at']) if data.get('published_at') else None,
            collected_at=datetime.fromisoformat(data['collected_at']) if data.get('collected_at') else None,
            significance_score=data.get('significance_score'),
            sentiment=data.get('sentiment'),
            analysis=data.get('analysis'),
        )

    def __repr__(self):
        return f"Event(source={self.source.value}, title='{self.title[:50]}...', type={self.event_type.value})"
