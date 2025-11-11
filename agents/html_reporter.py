"""
HTML briefing reporter.

Generates static HTML pages for web publishing.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from storage.db import EventDatabase
from models.events import Event


class HTMLReporter:
    """
    Generates HTML briefings for web publishing.
    """

    def __init__(self, db_path: str = "ai_pulse.db"):
        """Initialize reporter"""
        self.db = EventDatabase(db_path)

    def generate_briefing(self, days_back: int = 1, min_score: int = 40) -> str:
        """
        Generate HTML briefing.

        Args:
            days_back: Days to look back
            min_score: Minimum significance score

        Returns:
            HTML string
        """
        # Get recent events (convert days to hours)
        hours_back = days_back * 24
        all_events = self.db.get_recent_events(hours=hours_back, limit=1000)

        # Filter analyzed events only
        analyzed_events = [e for e in all_events if e.significance_score is not None]

        # Filter by score
        events = [e for e in analyzed_events if e.significance_score >= min_score]

        # Sort by score descending
        events.sort(key=lambda e: e.significance_score, reverse=True)

        # Get stats
        total_collected = len(all_events)
        total_analyzed = len(analyzed_events)

        sentiment_counts = {}
        for event in analyzed_events:
            sent = event.sentiment or 'unknown'
            sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1

        # Generate HTML
        html = self._generate_html(
            events=events,
            total_collected=total_collected,
            total_analyzed=total_analyzed,
            sentiment_counts=sentiment_counts,
            days_back=days_back,
            min_score=min_score
        )

        return html

    def _generate_html(self, events, total_collected, total_analyzed, sentiment_counts, days_back, min_score) -> str:
        """Generate HTML document"""

        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M UTC')

        # Group events by relevance
        material_events = [e for e in events if e.investment_relevance and 'material' in e.investment_relevance.lower()]
        marginal_events = [e for e in events if e.investment_relevance and 'marginal' in e.investment_relevance.lower() and e not in material_events]
        other_events = [e for e in events if e not in material_events and e not in marginal_events]

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-Pulse Briefing - {date_str}</title>
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <header>
        <h1>🧠 AI-Pulse Intelligence Briefing</h1>
        <p class="date">{date_str} {time_str}</p>
        <nav>
            <a href="../index.html">Latest</a>
            <a href="../archive.html">Archive</a>
            <a href="https://github.com/YOUR_USERNAME/ai-pulse">GitHub</a>
        </nav>
    </header>

    <main>
        <section class="summary">
            <h2>📊 Summary</h2>
            <div class="stats">
                <div class="stat">
                    <span class="stat-value">{total_collected}</span>
                    <span class="stat-label">Events Collected</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{total_analyzed}</span>
                    <span class="stat-label">Analyzed</span>
                </div>
                <div class="stat">
                    <span class="stat-value">{len(events)}</span>
                    <span class="stat-label">Significant (≥{min_score})</span>
                </div>
            </div>

            <div class="sentiment-breakdown">
                <h3>Sentiment Breakdown</h3>
                <ul>
"""

        for sentiment, count in sorted(sentiment_counts.items(), key=lambda x: x[1], reverse=True):
            html += f'                    <li><span class="sentiment-{sentiment}">{sentiment}</span>: {count}</li>\n'

        html += """                </ul>
            </div>
        </section>
"""

        # Material events
        if material_events:
            html += """
        <section class="events material-events">
            <h2>🔴 Material Events</h2>
"""
            for event in material_events:
                html += self._generate_event_card(event)
            html += """        </section>
"""

        # Marginal events
        if marginal_events:
            html += """
        <section class="events marginal-events">
            <h2>🟡 Marginal Events</h2>
"""
            for event in marginal_events:
                html += self._generate_event_card(event)
            html += """        </section>
"""

        # Other events
        if other_events:
            html += """
        <section class="events other-events">
            <h2>⚪ Other Significant Events</h2>
"""
            for event in other_events:
                html += self._generate_event_card(event)
            html += """        </section>
"""

        html += """    </main>

    <footer>
        <p>Generated by AI-Pulse | Data from Hacker News, NewsAPI, SEC EDGAR, GitHub, Company IR</p>
        <p>Analysis powered by Claude (Anthropic)</p>
    </footer>
</body>
</html>
"""
        return html

    def _generate_event_card(self, event: Event) -> str:
        """Generate HTML for single event"""

        sentiment_emoji = {
            'positive': '📈',
            'negative': '📉',
            'neutral': '➡️',
            'mixed': '↕️'
        }.get(event.sentiment, '➡️')

        companies_html = ''
        if event.companies:
            companies_html = f"<span class='companies'>Companies: {', '.join(event.companies)}</span>"

        published_str = event.published_at.strftime('%Y-%m-%d %H:%M') if event.published_at else 'Unknown'

        html = f"""
            <article class="event-card score-{event.significance_score//10}0">
                <div class="event-header">
                    <span class="score">{event.significance_score}/100</span>
                    <span class="sentiment">{sentiment_emoji}</span>
                    <h3>{event.title}</h3>
                </div>

                <div class="event-meta">
                    {companies_html}
                    <span class="published">Published: {published_str}</span>
                    <span class="relevance">{event.investment_relevance or 'N/A'}</span>
                </div>

                <div class="event-content">
"""

        if event.implications:
            html += f"""
                    <div class="implications">
                        <h4>💡 Implications</h4>
                        <p>{self._truncate(event.implications, 500)}</p>
                    </div>
"""

        if event.affected_parties:
            html += f"""
                    <div class="affected-parties">
                        <h4>👥 Affected Parties</h4>
                        <p>{self._truncate(event.affected_parties, 400)}</p>
                    </div>
"""

        if event.key_context:
            html += f"""
                    <div class="context">
                        <h4>📚 Context</h4>
                        <p>{self._truncate(event.key_context, 400)}</p>
                    </div>
"""

        html += f"""
                    <div class="event-link">
                        <a href="{event.source_url}" target="_blank">Read full article →</a>
                    </div>
                </div>
            </article>
"""
        return html

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to max length"""
        if not text:
            return ''
        if len(text) <= max_len:
            return text
        return text[:max_len] + '...'

    def close(self):
        """Close database connection"""
        self.db.close()


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate HTML briefing')
    parser.add_argument('--days', type=int, default=1,
                       help='Days to look back (default: 1)')
    parser.add_argument('--min-score', type=int, default=40,
                       help='Minimum significance score (default: 40)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file path (default: stdout)')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database path (default: ai_pulse.db)')

    args = parser.parse_args()

    reporter = HTMLReporter(db_path=args.db)
    html = reporter.generate_briefing(days_back=args.days, min_score=args.min_score)
    reporter.close()

    if args.output:
        with open(args.output, 'w') as f:
            f.write(html)
        print(f"Briefing saved to: {args.output}")
    else:
        print(html)
