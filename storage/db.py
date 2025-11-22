"""
SQLite database for storing AI sector events.

Simple, file-based storage - no external database needed.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models.events import Event, EventSource, EventType


class EventDatabase:
    """Manages storage and retrieval of AI sector events"""

    def __init__(self, db_path: str = "ai_pulse.db"):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries

    def _create_tables(self):
        """Create database schema if it doesn't exist"""
        cursor = self.conn.cursor()

        # Events table - stores all collected information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT,
                source_url TEXT,
                title TEXT NOT NULL,
                content TEXT,
                summary TEXT,
                event_type TEXT,
                companies TEXT,
                products TEXT,
                people TEXT,
                published_at TEXT,
                collected_at TEXT NOT NULL,
                significance_score REAL,
                sentiment TEXT,
                analysis TEXT,
                implications TEXT,
                affected_parties TEXT,
                investment_relevance TEXT,
                key_context TEXT,
                is_duplicate INTEGER DEFAULT 0,
                is_semantic_duplicate INTEGER DEFAULT 0,
                UNIQUE(source, source_id)
            )
        """)

        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_collected_at
            ON events(collected_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type
            ON events(event_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_significance
            ON events(significance_score DESC)
        """)

        # Daily sentiment aggregates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_sentiment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                positive INTEGER DEFAULT 0,
                negative INTEGER DEFAULT 0,
                neutral INTEGER DEFAULT 0,
                mixed INTEGER DEFAULT 0,
                total_analyzed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_date
            ON daily_sentiment(date DESC)
        """)

        self.conn.commit()

    def save_event(self, event: Event) -> int:
        """
        Save an event to the database.

        Args:
            event: Event object to save

        Returns:
            Database ID of saved event

        Note:
            If event with same source+source_id exists, it will be skipped (UNIQUE constraint)
        """
        cursor = self.conn.cursor()

        data = event.to_dict()
        del data['id']  # Don't insert ID, let database auto-generate

        try:
            cursor.execute("""
                INSERT INTO events (
                    source, source_id, source_url, title, content, summary,
                    event_type, companies, products, people,
                    published_at, collected_at, significance_score, sentiment, analysis,
                    implications, affected_parties, investment_relevance, key_context
                ) VALUES (
                    :source, :source_id, :source_url, :title, :content, :summary,
                    :event_type, :companies, :products, :people,
                    :published_at, :collected_at, :significance_score, :sentiment, :analysis,
                    :implications, :affected_parties, :investment_relevance, :key_context
                )
            """, data)

            self.conn.commit()
            return cursor.lastrowid

        except sqlite3.IntegrityError:
            # Event already exists (duplicate source + source_id)
            return None

    def save_events(self, events: List[Event]) -> dict:
        """
        Save multiple events.

        Args:
            events: List of Event objects

        Returns:
            Dictionary with counts: {'saved': 5, 'duplicates': 2}
        """
        saved = 0
        duplicates = 0

        for event in events:
            result = self.save_event(event)
            if result:
                saved += 1
            else:
                duplicates += 1

        return {'saved': saved, 'duplicates': duplicates}

    def get_recent_events(self, limit: int = 50, hours: int = 24) -> List[Event]:
        """
        Get recent events by published date.

        Uses published_at instead of collected_at to ensure events are dated
        by when they were published, not when they were fetched.

        For predictive model (Model B):
        - Run at 1pm GMT: Captures overnight news (previous 9pm → now)
        - Compare with today's market close (collected later at 9pm GMT)
        - Question: "Does overnight news predict today's market movement?"

        Args:
            limit: Maximum number of events to return
            hours: Only return events published in last N hours
                   Default 24 captures overnight window when run at 1pm GMT

        Returns:
            List of Event objects
        """
        cursor = self.conn.cursor()

        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        cursor.execute("""
            SELECT * FROM events
            WHERE published_at >= ?
            ORDER BY published_at DESC
            LIMIT ?
        """, (cutoff.isoformat(), limit))

        rows = cursor.fetchall()
        return [Event.from_dict(dict(row)) for row in rows]

    def get_events_by_type(self, event_type: EventType, limit: int = 50) -> List[Event]:
        """Get events of a specific type"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM events
            WHERE event_type = ?
            ORDER BY collected_at DESC
            LIMIT ?
        """, (event_type.value, limit))

        rows = cursor.fetchall()
        return [Event.from_dict(dict(row)) for row in rows]

    def get_event_by_id(self, event_id: int) -> Optional[Event]:
        """Get a specific event by database ID"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()

        if row:
            return Event.from_dict(dict(row))
        return None

    def get_stats(self) -> dict:
        """Get database statistics"""
        cursor = self.conn.cursor()

        # Total events
        cursor.execute("SELECT COUNT(*) FROM events")
        total = cursor.fetchone()[0]

        # Events by source
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM events
            GROUP BY source
            ORDER BY count DESC
        """)
        by_source = {row[0]: row[1] for row in cursor.fetchall()}

        # Events by type
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM events
            GROUP BY event_type
            ORDER BY count DESC
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # Recent activity (last 24h)
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)

        cursor.execute("""
            SELECT COUNT(*) FROM events
            WHERE collected_at >= ?
        """, (cutoff.isoformat(),))
        last_24h = cursor.fetchone()[0]

        return {
            'total_events': total,
            'by_source': by_source,
            'by_type': by_type,
            'last_24h': last_24h,
        }

    def update_event_analysis(self, event_id: int, analysis_data: dict):
        """
        Update an event with agent analysis.

        This is called after the agent has analyzed an event's significance.

        Args:
            event_id: Database ID of event
            analysis_data: Dictionary with analysis fields
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            UPDATE events
            SET significance_score = ?,
                sentiment = ?,
                analysis = ?,
                implications = ?,
                affected_parties = ?,
                investment_relevance = ?,
                key_context = ?
            WHERE id = ?
        """, (
            analysis_data.get('significance_score'),
            analysis_data.get('sentiment'),
            analysis_data.get('full_analysis'),  # Store full text
            analysis_data.get('implications'),
            analysis_data.get('affected_parties'),
            analysis_data.get('investment_relevance'),
            analysis_data.get('key_context'),
            event_id
        ))

        self.conn.commit()

    def save_daily_sentiment(self, date: str, sentiment_counts: dict):
        """
        Save or update daily sentiment aggregates.

        Args:
            date: Date string (YYYY-MM-DD)
            sentiment_counts: Dict with sentiment counts
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO daily_sentiment (
                date, positive, negative, neutral, mixed, total_analyzed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                positive = excluded.positive,
                negative = excluded.negative,
                neutral = excluded.neutral,
                mixed = excluded.mixed,
                total_analyzed = excluded.total_analyzed
        """, (
            date,
            sentiment_counts.get('positive', 0),
            sentiment_counts.get('negative', 0),
            sentiment_counts.get('neutral', 0),
            sentiment_counts.get('mixed', 0),
            sum(sentiment_counts.values()),
            datetime.utcnow().isoformat()
        ))

        self.conn.commit()

    def get_sentiment_history(self, days: int = 30) -> List[dict]:
        """
        Get sentiment history for last N days.

        Args:
            days: Number of days to retrieve

        Returns:
            List of dicts with date and sentiment counts
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT date, positive, negative, neutral, mixed, total_analyzed
            FROM daily_sentiment
            ORDER BY date DESC
            LIMIT ?
        """, (days,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection when exiting context"""
        self.close()


# Example usage
if __name__ == "__main__":
    # Test the database
    with EventDatabase("test.db") as db:
        # Create a test event
        event = Event(
            source=EventSource.HACKER_NEWS,
            source_id="12345",
            source_url="https://news.ycombinator.com/item?id=12345",
            title="OpenAI announces GPT-5",
            content="OpenAI has announced GPT-5 with major improvements...",
            event_type=EventType.PRODUCT_LAUNCH,
            companies=["OpenAI"],
            products=["GPT-5"],
            published_at=datetime.utcnow(),
        )

        # Save it
        event_id = db.save_event(event)
        print(f"Saved event with ID: {event_id}")

        # Get recent events
        recent = db.get_recent_events(limit=10)
        print(f"\nRecent events: {len(recent)}")
        for e in recent:
            print(f"  - {e.title}")

        # Get stats
        stats = db.get_stats()
        print(f"\nDatabase stats:")
        print(f"  Total events: {stats['total_events']}")
        print(f"  By source: {stats['by_source']}")
        print(f"  By type: {stats['by_type']}")
