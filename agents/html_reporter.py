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
import sqlite3


class HTMLReporter:
    """
    Generates HTML briefings for web publishing.
    """

    def __init__(self, db_path: str = "ai_pulse.db"):
        """Initialize reporter"""
        self.db = EventDatabase(db_path)
        self.db_path = db_path

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

        # Filter out duplicates (both string and semantic)
        all_events = [e for e in all_events if not getattr(e, 'is_duplicate', False) and not getattr(e, 'is_semantic_duplicate', False)]

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

        # Get market data and correlation data
        market_data = self._get_market_data(days=30)
        correlation_data = self._get_correlation_data(days=30)

        # Generate HTML
        html = self._generate_html(
            events=events,
            total_collected=total_collected,
            total_analyzed=total_analyzed,
            sentiment_counts=sentiment_counts,
            sentiment_history=full_history,
            market_data=market_data,
            correlation_data=correlation_data,
            days_back=days_back,
            min_score=min_score
        )

        return html, sentiment_counts

    def _generate_html(self, events, total_collected, total_analyzed, sentiment_counts, sentiment_history, market_data, correlation_data, days_back, min_score) -> str:
        """Generate HTML document"""

        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M UTC')

        # Prepare chart data (reverse chronological order for chart)
        chart_data = self._prepare_chart_data(sentiment_history)
        market_chart_data = self._prepare_market_data(market_data)
        correlation_chart_data = self._prepare_correlation_data(correlation_data)

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

        // Initialize charts when page loads
        window.addEventListener('DOMContentLoaded', function() {{
            // Sentiment Chart
            const ctx = document.getElementById('sentimentChart').getContext('2d');
            const chartData = {chart_data};

            // If we have data, generate labels from first data date to 30 days ahead
            let labels = chartData.dates;
            let positiveData = chartData.positive;
            let negativeData = chartData.negative;
            let neutralData = chartData.neutral;
            let mixedData = chartData.mixed;
            let totalData = chartData.totals;

            // If we have at least one data point, extend to show future 30 days
            if (chartData.dates.length > 0) {{
                const firstDate = new Date(chartData.dates[0]);
                const today = new Date();
                const endDate = new Date(today);
                endDate.setDate(endDate.getDate() + 30);

                // Generate all dates from first data point to 30 days ahead
                labels = [];
                const current = new Date(firstDate);
                while (current <= endDate) {{
                    labels.push(current.toISOString().split('T')[0]);
                    current.setDate(current.getDate() + 1);
                }}

                // Map data to full date range
                const mapData = (dates, values) => {{
                    return labels.map(label => {{
                        const index = dates.indexOf(label);
                        return index >= 0 ? values[index] : null;
                    }});
                }};

                positiveData = mapData(chartData.dates, chartData.positive);
                negativeData = mapData(chartData.dates, chartData.negative);
                neutralData = mapData(chartData.dates, chartData.neutral);
                mixedData = mapData(chartData.dates, chartData.mixed);
                totalData = mapData(chartData.dates, chartData.totals);
            }}

            const sentimentChart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Positive',
                            data: positiveData,
                            borderColor: '#6ee7b7',
                            backgroundColor: 'rgba(110, 231, 183, 0.1)',
                            tension: 0.3,
                            spanGaps: true
                        }},
                        {{
                            label: 'Negative',
                            data: negativeData,
                            borderColor: '#fca5a5',
                            backgroundColor: 'rgba(252, 165, 165, 0.1)',
                            tension: 0.3,
                            spanGaps: true
                        }},
                        {{
                            label: 'Neutral',
                            data: neutralData,
                            borderColor: '#94a3b8',
                            backgroundColor: 'rgba(148, 163, 184, 0.1)',
                            tension: 0.3,
                            spanGaps: true
                        }},
                        {{
                            label: 'Mixed',
                            data: mixedData,
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
                    onHover: function(event, activeElements) {{
                        if (activeElements.length > 0) {{
                            const index = activeElements[0].index;
                            updateSentimentBreakdown(index, labels[index], positiveData[index], negativeData[index], neutralData[index], mixedData[index], totalData[index]);
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            labels: {{
                                color: '#e2e8f0'
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                title: function(context) {{
                                    const index = context[0].dataIndex;
                                    const total = totalData[index];
                                    return context[0].label + ' (Total: ' + (total || 0) + ' events)';
                                }},
                                label: function(context) {{
                                    return context.dataset.label + ': ' + context.parsed.y + '%';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: 100,
                            ticks: {{
                                color: '#94a3b8',
                                callback: function(value) {{
                                    return value + '%';
                                }}
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

            // Function to update sentiment breakdown display
            function updateSentimentBreakdown(index, date, positive, negative, neutral, mixed, total) {{
                document.getElementById('breakdown-date').textContent = date;
                document.getElementById('breakdown-positive-pct').textContent = (positive || 0).toFixed(1) + '%';
                document.getElementById('breakdown-negative-pct').textContent = (negative || 0).toFixed(1) + '%';
                document.getElementById('breakdown-neutral-pct').textContent = (neutral || 0).toFixed(1) + '%';
                document.getElementById('breakdown-mixed-pct').textContent = (mixed || 0).toFixed(1) + '%';

                // Calculate actual counts from percentages
                const posCount = total > 0 ? Math.round(positive * total / 100) : 0;
                const negCount = total > 0 ? Math.round(negative * total / 100) : 0;
                const neuCount = total > 0 ? Math.round(neutral * total / 100) : 0;
                const mixCount = total > 0 ? Math.round(mixed * total / 100) : 0;

                document.getElementById('breakdown-positive-count').textContent = posCount;
                document.getElementById('breakdown-negative-count').textContent = negCount;
                document.getElementById('breakdown-neutral-count').textContent = neuCount;
                document.getElementById('breakdown-mixed-count').textContent = mixCount;
                document.getElementById('breakdown-total').textContent = total || 0;

                // Highlight the breakdown section
                const breakdownSection = document.getElementById('sentiment-breakdown');
                breakdownSection.style.backgroundColor = 'rgba(110, 231, 183, 0.05)';
                setTimeout(() => {{
                    breakdownSection.style.backgroundColor = '';
                }}, 200);
            }}

            // Market Performance Chart
            const marketCtx = document.getElementById('marketChart').getContext('2d');
            const marketData = {market_chart_data};
            const correlationData = {correlation_chart_data};

            // Use same date range as sentiment chart (reuse labels from sentiment chart)
            const marketLabels = labels;

            // Define symbol display order and colors
            const symbolConfig = [
                {{symbol: '^IXIC', label: 'NASDAQ', color: '#6ee7b7'}},
                {{symbol: '^GSPC', label: 'S&P 500', color: '#94a3b8'}},
                {{symbol: 'NVDA', label: 'NVIDIA', color: '#c084fc'}},
                {{symbol: 'MSFT', label: 'Microsoft', color: '#60a5fa'}},
                {{symbol: 'GOOGL', label: 'Alphabet', color: '#fbbf24'}},
                {{symbol: 'META', label: 'Meta', color: '#f87171'}},
                {{symbol: 'AMD', label: 'AMD', color: '#fb923c'}},
                {{symbol: 'BOTZ', label: 'AI/Robotics ETF', color: '#a78bfa'}}
            ];

            // Map market data to full date range (align with sentiment chart dates)
            const mapMarketData = (symbolDates, symbolChanges) => {{
                const dataMap = {{}};
                symbolDates.forEach((date, idx) => {{
                    dataMap[date] = symbolChanges[idx];
                }});
                return marketLabels.map(label => dataMap[label] !== undefined ? dataMap[label] : null);
            }};

            // Build datasets for each symbol
            const marketDatasets = symbolConfig.map(config => {{
                const symbolData = marketData[config.symbol];
                if (!symbolData) return null;

                return {{
                    label: config.label,
                    data: mapMarketData(symbolData.dates, symbolData.changes),
                    borderColor: config.color,
                    backgroundColor: 'transparent',
                    tension: 0.3,
                    hidden: true,  // All hidden by default
                    spanGaps: true  // Connect across missing data points
                }};
            }}).filter(d => d !== null);

            window.marketChart = new Chart(marketCtx, {{
                type: 'line',
                data: {{
                    labels: marketLabels,
                    datasets: marketDatasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false  // Using custom checkboxes instead
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,  // Dynamic scaling
                            ticks: {{
                                color: '#94a3b8',
                                callback: function(value) {{
                                    return value.toFixed(1) + '%';
                                }}
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

            // Checkbox toggle functionality
            document.querySelectorAll('.market-checkbox').forEach(checkbox => {{
                checkbox.addEventListener('change', function() {{
                    const datasetIndex = parseInt(this.dataset.index);
                    window.marketChart.data.datasets[datasetIndex].hidden = !this.checked;
                    window.marketChart.update();
                }});
            }});
        }});

        // Toggle visibility function for market checkboxes
        function toggleMarketSymbol(index) {{
            const checkbox = document.getElementById('symbol-' + index);
            checkbox.checked = !checkbox.checked;
            checkbox.dispatchEvent(new Event('change'));
        }}
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
            <div class="sentiment-current" id="sentiment-breakdown">
                <h4>Sentiment Breakdown <span id="breakdown-date" style="color: #6ee7b7; font-weight: normal;">(Hover over chart)</span></h4>
                <ul class="sentiment-list">
"""

        # Calculate initial percentages for display
        total_events = sum(sentiment_counts.values()) if sentiment_counts.values() else 1
        html += f"""                    <li>
                        <span class="sentiment-positive">positive</span>:
                        <span id="breakdown-positive-pct">{(sentiment_counts.get('positive', 0) / total_events * 100):.1f}%</span>
                        <span style="color: #94a3b8; font-size: 0.9em;">(<span id="breakdown-positive-count">{sentiment_counts.get('positive', 0)}</span> events)</span>
                    </li>
                    <li>
                        <span class="sentiment-negative">negative</span>:
                        <span id="breakdown-negative-pct">{(sentiment_counts.get('negative', 0) / total_events * 100):.1f}%</span>
                        <span style="color: #94a3b8; font-size: 0.9em;">(<span id="breakdown-negative-count">{sentiment_counts.get('negative', 0)}</span> events)</span>
                    </li>
                    <li>
                        <span class="sentiment-neutral">neutral</span>:
                        <span id="breakdown-neutral-pct">{(sentiment_counts.get('neutral', 0) / total_events * 100):.1f}%</span>
                        <span style="color: #94a3b8; font-size: 0.9em;">(<span id="breakdown-neutral-count">{sentiment_counts.get('neutral', 0)}</span> events)</span>
                    </li>
                    <li>
                        <span class="sentiment-mixed">mixed</span>:
                        <span id="breakdown-mixed-pct">{(sentiment_counts.get('mixed', 0) / total_events * 100):.1f}%</span>
                        <span style="color: #94a3b8; font-size: 0.9em;">(<span id="breakdown-mixed-count">{sentiment_counts.get('mixed', 0)}</span> events)</span>
                    </li>
                    <li style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #334155;">
                        <strong>Total:</strong> <span id="breakdown-total">{sum(sentiment_counts.values())}</span> events analyzed
                    </li>
"""

        html += """                </ul>
            </div>
        </section>

        <section class="sentiment-box">
            <h3>Market Performance (Last 30 Days)</h3>
"""

        # Add accuracy badge if we have correlation data
        if correlation_data['total'] > 0:
            html += f"""
            <div class="accuracy-badge">
                <span class="badge-label">Sentiment Prediction Accuracy (Last 30 days):</span>
                <span class="badge-value">✅ {correlation_data['correct']}/{correlation_data['correct'] + correlation_data['wrong']} ({correlation_data['accuracy_pct']}%)</span>
            </div>
"""

        html += """
            <div class="chart-container">
                <canvas id="marketChart"></canvas>
            </div>

            <div class="market-controls">
                <h4>Select Indices & Stocks</h4>
                <div class="checkbox-grid">
"""

        # Generate checkboxes for each symbol
        symbol_labels = [
            ('NASDAQ', '#6ee7b7'),
            ('S&P 500', '#94a3b8'),
            ('NVIDIA', '#c084fc'),
            ('Microsoft', '#60a5fa'),
            ('Alphabet', '#fbbf24'),
            ('Meta', '#f87171'),
            ('AMD', '#fb923c'),
            ('AI/Robotics ETF', '#a78bfa')
        ]

        for idx, (label, color) in enumerate(symbol_labels):
            html += f"""
                    <label class="checkbox-label">
                        <input type="checkbox" id="symbol-{idx}" class="market-checkbox" data-index="{idx}">
                        <span style="color: {color}">■</span> {label}
                    </label>
"""

        html += """
                </div>
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

        # Calculate percentages and keep totals
        dates = []
        positive_pct = []
        negative_pct = []
        neutral_pct = []
        mixed_pct = []
        totals = []

        for row in history:
            total = row['positive'] + row['negative'] + row['neutral'] + row['mixed']
            dates.append(row['date'])
            totals.append(total)

            if total > 0:
                positive_pct.append(round((row['positive'] / total) * 100, 1))
                negative_pct.append(round((row['negative'] / total) * 100, 1))
                neutral_pct.append(round((row['neutral'] / total) * 100, 1))
                mixed_pct.append(round((row['mixed'] / total) * 100, 1))
            else:
                positive_pct.append(0)
                negative_pct.append(0)
                neutral_pct.append(0)
                mixed_pct.append(0)

        chart_data = {
            'dates': dates,
            'positive': positive_pct,
            'negative': negative_pct,
            'neutral': neutral_pct,
            'mixed': mixed_pct,
            'totals': totals
        }

        return json.dumps(chart_data)

    def _prepare_market_data(self, market_data: dict) -> str:
        """Prepare market data for Chart.js"""
        import json
        return json.dumps(market_data)

    def _prepare_correlation_data(self, correlation_data: dict) -> str:
        """Prepare correlation data for display"""
        import json
        return json.dumps(correlation_data)

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to max length"""
        if not text:
            return ''
        if len(text) <= max_len:
            return text
        return text[:max_len] + '...'

    def _get_market_data(self, days: int = 30) -> dict:
        """Get market data for last N days, keeping dates with each symbol"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get data for each symbol
        cursor.execute("""
            SELECT date, symbol, symbol_name, change_pct
            FROM market_data
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date ASC
        """, (days,))

        rows = cursor.fetchall()
        conn.close()

        # Group by symbol, keeping dates
        data = {}
        for row in rows:
            symbol = row['symbol']
            if symbol not in data:
                data[symbol] = {
                    'name': row['symbol_name'],
                    'dates': [],
                    'changes': []
                }
            data[symbol]['dates'].append(row['date'])
            data[symbol]['changes'].append(round(row['change_pct'], 2))

        return data

    def _get_correlation_data(self, days: int = 30) -> dict:
        """Get sentiment-market correlation data"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, dominant_sentiment, market_outcome, prediction_correct
            FROM daily_correlation
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date ASC
        """, (days,))

        rows = cursor.fetchall()
        conn.close()

        # Build accuracy stats
        total = len(rows)
        correct = sum(1 for r in rows if r['prediction_correct'] == 1)
        wrong = sum(1 for r in rows if r['prediction_correct'] == 0)
        ambiguous = sum(1 for r in rows if r['prediction_correct'] is None)

        accuracy_pct = round((correct / (correct + wrong)) * 100) if (correct + wrong) > 0 else 0

        # Build timeline data
        timeline = []
        for row in rows:
            timeline.append({
                'date': row['date'],
                'sentiment': row['dominant_sentiment'],
                'outcome': row['market_outcome'],
                'correct': row['prediction_correct']
            })

        return {
            'total': total,
            'correct': correct,
            'wrong': wrong,
            'ambiguous': ambiguous,
            'accuracy_pct': accuracy_pct,
            'timeline': timeline
        }

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
