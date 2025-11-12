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

    def generate_briefing(self, days_back: int = 1, min_score: int = 40):
        """
        Generate HTML briefing.

        Args:
            days_back: Days to look back
            min_score: Minimum significance score

        Returns:
            Tuple of (HTML string, sentiment_counts dict)
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

        # Get sentiment history for chart (past data)
        sentiment_history = self.db.get_sentiment_history(days=30)

        # Add today's data to history for chart
        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        today_data = {
            'date': date_str,
            'positive': sentiment_counts.get('positive', 0),
            'negative': sentiment_counts.get('negative', 0),
            'neutral': sentiment_counts.get('neutral', 0),
            'mixed': sentiment_counts.get('mixed', 0),
            'total_analyzed': sum(sentiment_counts.values())
        }

        # Remove today's date from history if it exists (will be replaced with fresh data)
        sentiment_history = [row for row in sentiment_history if row['date'] != date_str]

        # Insert today at the beginning (most recent)
        full_history = [today_data] + sentiment_history

        # Generate HTML
        html = self._generate_html(
            events=events,
            total_collected=total_collected,
            total_analyzed=total_analyzed,
            sentiment_counts=sentiment_counts,
            sentiment_history=full_history,
            days_back=days_back,
            min_score=min_score
        )

        return html, sentiment_counts

    def _generate_html(self, events, total_collected, total_analyzed, sentiment_counts, sentiment_history, days_back, min_score) -> str:
        """Generate HTML document"""

        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M UTC')

        # Prepare chart data (reverse chronological order for chart)
        chart_data = self._prepare_chart_data(sentiment_history)

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
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        function toggleEvent(id) {{
            const content = document.getElementById('content-' + id);
            const button = document.getElementById('btn-' + id);
            if (content.style.display === 'none' || content.style.display === '') {{
                content.style.display = 'block';
                button.textContent = '▼';
            }} else {{
                content.style.display = 'none';
                button.textContent = '▶';
            }}
        }}

        // Initialize chart when page loads
        window.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('sentimentChart').getContext('2d');
            const chartData = {chart_data};

            // Generate 30 days of labels starting from 30 days ago
            const labels = [];
            const today = new Date();
            for (let i = 29; i >= 0; i--) {{
                const date = new Date(today);
                date.setDate(date.getDate() - i);
                labels.push(date.toISOString().split('T')[0]);
            }}

            // Map actual data to 30-day scale (fill with null for missing dates)
            const mapDataTo30Days = (dates, values) => {{
                return labels.map(label => {{
                    const index = dates.indexOf(label);
                    return index >= 0 ? values[index] : null;
                }});
            }};

            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Positive',
                            data: mapDataTo30Days(chartData.dates, chartData.positive),
                            borderColor: '#6ee7b7',
                            backgroundColor: 'rgba(110, 231, 183, 0.1)',
                            tension: 0.3,
                            spanGaps: true
                        }},
                        {{
                            label: 'Negative',
                            data: mapDataTo30Days(chartData.dates, chartData.negative),
                            borderColor: '#fca5a5',
                            backgroundColor: 'rgba(252, 165, 165, 0.1)',
                            tension: 0.3,
                            spanGaps: true
                        }},
                        {{
                            label: 'Neutral',
                            data: mapDataTo30Days(chartData.dates, chartData.neutral),
                            borderColor: '#94a3b8',
                            backgroundColor: 'rgba(148, 163, 184, 0.1)',
                            tension: 0.3,
                            spanGaps: true
                        }},
                        {{
                            label: 'Mixed',
                            data: mapDataTo30Days(chartData.dates, chartData.mixed),
                            borderColor: '#fcd34d',
                            backgroundColor: 'rgba(252, 211, 77, 0.1)',
                            tension: 0.3,
                            spanGaps: true
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            labels: {{
                                color: '#e2e8f0'
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                color: '#94a3b8'
                            }},
                            grid: {{
                                color: '#334155'
                            }}
                        }},
                        x: {{
                            ticks: {{
                                color: '#94a3b8',
                                maxRotation: 45,
                                minRotation: 45
                            }},
                            grid: {{
                                color: '#334155'
                            }}
                        }}
                    }}
                }}
            }});
        }});
    </script>
</head>
<body>
    <header>
        <div class="header-stats">
            <div class="stat-item">
                <span class="stat-value-small">{total_collected}</span>
                <span class="stat-label-small">Events</span>
            </div>
            <div class="stat-item">
                <span class="stat-value-small">{total_analyzed}</span>
                <span class="stat-label-small">Analyzed</span>
            </div>
            <div class="stat-item">
                <span class="stat-value-small">{len(events)}</span>
                <span class="stat-label-small">Significant</span>
            </div>
        </div>

        <div class="header-center">
            <h1>🧠 AI-Pulse</h1>
            <p class="date">{date_str} {time_str}</p>
        </div>

        <nav class="header-nav">
            <a href="../index.html">Latest</a>
            <a href="../archive.html">Archive</a>
            <a href="https://github.com/mat-e-exp/ai-pulse">GitHub</a>
        </nav>
    </header>

    <main>
        <section class="sentiment-box">
            <h3>Sentiment Trend (Last 30 Days)</h3>
            <div class="chart-container">
                <canvas id="sentimentChart"></canvas>
            </div>
            <div class="sentiment-current">
                <h4>Today's Breakdown</h4>
                <ul class="sentiment-list">
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
        """Generate HTML for single event - collapsed by default"""

        sentiment_emoji = {
            'positive': '📈',
            'negative': '📉',
            'neutral': '➡️',
            'mixed': '↕️'
        }.get(event.sentiment, '➡️')

        companies_html = ''
        if event.companies:
            companies_html = f" | {', '.join(event.companies)}"

        published_str = event.published_at.strftime('%Y-%m-%d %H:%M') if event.published_at else 'Unknown'

        # Generate unique ID for this event
        event_id = event.id or hash(event.title)

        html = f"""
            <article class="event-card-compact">
                <div class="event-header-compact">
                    <span class="score-compact">{event.significance_score}</span>
                    <h3 class="event-title-compact">{event.title}</h3>
                    <button class="expand-btn" id="btn-{event_id}" onclick="toggleEvent({event_id})">▶</button>
                </div>

                <div class="event-content-expanded" id="content-{event_id}" style="display: none;">
                    <div class="event-meta-compact">
                        <span class="sentiment">{sentiment_emoji} {event.sentiment or 'neutral'}</span>
                        {companies_html}
                        <span> | {published_str}</span>
                        <span> | {event.investment_relevance or 'N/A'}</span>
                    </div>
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

    def _prepare_chart_data(self, sentiment_history: list) -> str:
        """Prepare sentiment history data for Chart.js"""
        import json

        # Reverse to get chronological order (oldest to newest)
        history = list(reversed(sentiment_history))

        chart_data = {
            'dates': [row['date'] for row in history],
            'positive': [row['positive'] for row in history],
            'negative': [row['negative'] for row in history],
            'neutral': [row['neutral'] for row in history],
            'mixed': [row['mixed'] for row in history]
        }

        return json.dumps(chart_data)

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
    html, sentiment_counts = reporter.generate_briefing(days_back=args.days, min_score=args.min_score)
    reporter.close()

    if args.output:
        with open(args.output, 'w') as f:
            f.write(html)
        print(f"Briefing saved to: {args.output}")
    else:
        print(html)
