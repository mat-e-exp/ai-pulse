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

        # Separate research papers (don't need scoring) from news events (require scoring)
        from models.events import EventType
        research_papers = [e for e in all_events if e.event_type == EventType.RESEARCH]
        news_events_all = [e for e in all_events if e.event_type != EventType.RESEARCH]

        # Filter analyzed news events only
        analyzed_events = [e for e in news_events_all if e.significance_score is not None]

        # Filter by score (news events only)
        news_events = [e for e in analyzed_events if e.significance_score >= min_score]

        # Sort by score descending
        news_events.sort(key=lambda e: e.significance_score, reverse=True)

        # Combine: news events (scored) + research papers (informational)
        events = news_events + research_papers

        # Get stats
        total_collected = len(all_events)
        total_analyzed = len(analyzed_events)

        # Count sentiment only for non-research events
        # Research papers are informational, not sentiment-driven
        sentiment_counts = {}
        for event in analyzed_events:
            # Skip research papers from sentiment calculation
            if event.event_type == EventType.RESEARCH:
                continue
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

        # Get latest prediction insights
        insights = self._get_latest_insights()

        # Get accuracy data
        accuracy_data = self._get_accuracy_data(days=30)
        heatmap_data = self._get_heatmap_data(days=30)

        # Generate HTML
        html = self._generate_html(
            events=events,
            total_collected=total_collected,
            total_analyzed=total_analyzed,
            sentiment_counts=sentiment_counts,
            sentiment_history=full_history,
            market_data=market_data,
            correlation_data=correlation_data,
            insights=insights,
            accuracy_data=accuracy_data,
            heatmap_data=heatmap_data,
            days_back=days_back,
            min_score=min_score
        )

        return html, sentiment_counts

    def _generate_html(self, events, total_collected, total_analyzed, sentiment_counts, sentiment_history, market_data, correlation_data, insights, accuracy_data, heatmap_data, days_back, min_score) -> str:
        """Generate HTML document"""
        from models.events import EventType

        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M UTC')

        # Prepare chart data (reverse chronological order for chart)
        chart_data = self._prepare_chart_data(sentiment_history)
        market_chart_data = self._prepare_market_data(market_data)
        correlation_chart_data = self._prepare_correlation_data(correlation_data)

        # Separate research papers from news/events
        research_papers = [e for e in events if e.event_type == EventType.RESEARCH]
        news_events = [e for e in events if e.event_type != EventType.RESEARCH]

        # Group news events by relevance (Material/Notable/Background)
        material_events = [e for e in news_events if e.investment_relevance and 'material' in e.investment_relevance.lower()]
        notable_events = [e for e in news_events if e.investment_relevance and 'notable' in e.investment_relevance.lower() and e not in material_events]
        background_events = [e for e in news_events if e not in material_events and e not in notable_events]

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
            // Extract closed market dates (needed for both charts)
            const marketData = {market_chart_data};
            const closedDates = marketData._closed_dates || [];

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

            // Plugin to highlight closed market dates (weekends + holidays)
            const sentimentClosedDatesPlugin = {{
                id: 'sentimentClosedDatesHighlight',
                beforeDatasetsDraw: function(chart) {{
                    const ctx = chart.ctx;
                    const xAxis = chart.scales.x;
                    const yAxis = chart.scales.y;
                    const labels = chart.data.labels;

                    // Draw background bars for closed dates (weekends + holidays)
                    labels.forEach((label, index) => {{
                        // Check database for holidays (weekdays marked closed)
                        const isHoliday = closedDates.includes(label);

                        // Check for weekends (client-side detection)
                        const date = new Date(label + 'T12:00:00Z');
                        const dayOfWeek = date.getUTCDay();
                        const isWeekend = (dayOfWeek === 0 || dayOfWeek === 6);

                        if (isHoliday || isWeekend) {{
                            const x = xAxis.getPixelForValue(index);
                            const barWidth = xAxis.width / labels.length;

                            ctx.save();
                            ctx.fillStyle = 'rgba(251, 191, 36, 0.15)';  // Light yellow/amber tint
                            ctx.fillRect(
                                x - barWidth / 2,
                                yAxis.top,
                                barWidth,
                                yAxis.bottom - yAxis.top
                            );
                            ctx.restore();
                        }}
                    }});
                }}
            }};

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
                plugins: [sentimentClosedDatesPlugin],
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{
                        mode: 'index',  // Trigger on x-axis position
                        intersect: false  // Don't require hovering directly on points
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

            // Market Performance Chart
            const marketCtx = document.getElementById('marketChart').getContext('2d');
            const correlationData = {correlation_chart_data};

            // Remove _closed_dates from marketData (already extracted above)
            delete marketData._closed_dates;

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
                {{symbol: 'PLTR', label: 'Palantir', color: '#34d399'}},
                {{symbol: 'BOTZ', label: 'AI/Robotics ETF', color: '#a78bfa'}},
                {{symbol: 'AIQ', label: 'AI Analytics ETF', color: '#f472b6'}},
                {{symbol: 'BTC-USD', label: 'Bitcoin', color: '#f59e0b'}}
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
                    symbol: config.symbol,  // Store symbol for lookup
                    data: mapMarketData(symbolData.dates, symbolData.changes),
                    borderColor: config.color,
                    backgroundColor: 'transparent',
                    tension: 0.3,
                    hidden: false,  // Visible by default (checkboxes are checked)
                    spanGaps: true  // Connect across missing data points
                }};
            }}).filter(d => d !== null);

            // Plugin to highlight closed market dates (weekends + holidays)
            const closedDatesPlugin = {{
                id: 'closedDatesHighlight',
                beforeDatasetsDraw: function(chart) {{
                    const ctx = chart.ctx;
                    const xAxis = chart.scales.x;
                    const yAxis = chart.scales.y;
                    const labels = chart.data.labels;

                    // Draw background bars for closed dates (weekends + holidays)
                    labels.forEach((label, index) => {{
                        // Check database for holidays (weekdays marked closed)
                        const isHoliday = closedDates.includes(label);

                        // Check for weekends (client-side detection)
                        const date = new Date(label + 'T12:00:00Z');
                        const dayOfWeek = date.getUTCDay();
                        const isWeekend = (dayOfWeek === 0 || dayOfWeek === 6);

                        if (isHoliday || isWeekend) {{
                            const x = xAxis.getPixelForValue(index);
                            const barWidth = xAxis.width / labels.length;

                            ctx.save();
                            ctx.fillStyle = 'rgba(251, 191, 36, 0.15)';  // Light yellow/amber tint
                            ctx.fillRect(
                                x - barWidth / 2,
                                yAxis.top,
                                barWidth,
                                yAxis.bottom - yAxis.top
                            );
                            ctx.restore();
                        }}
                    }});
                }}
            }};

            window.marketChart = new Chart(marketCtx, {{
                type: 'line',
                data: {{
                    labels: marketLabels,
                    datasets: marketDatasets
                }},
                plugins: [closedDatesPlugin],
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
                                    const date = context.label;
                                    const isClosed = closedDates.includes(date);
                                    const closedTag = isClosed ? ' (Market Closed)' : '';
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%' + closedTag;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,  // Dynamic scaling
                            afterDataLimits: function(axis) {{
                                // Ensure minimum scale of ±1%
                                const range = axis.max - axis.min;
                                if (range < 2) {{
                                    const center = (axis.max + axis.min) / 2;
                                    axis.max = center + 1;
                                    axis.min = center - 1;
                                }}
                            }},
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
                    const symbol = this.dataset.symbol;
                    // Find dataset by matching symbol directly
                    const datasetIndex = window.marketChart.data.datasets.findIndex(ds => ds.symbol === symbol);

                    if (datasetIndex !== -1) {{
                        window.marketChart.data.datasets[datasetIndex].hidden = !this.checked;
                        window.marketChart.update();
                    }}
                }});
            }});
        }});

        // Toggle all market symbols on/off
        function toggleAllMarketSymbols(checked) {{
            document.querySelectorAll('.market-checkbox:not([disabled])').forEach(checkbox => {{
                checkbox.checked = checked;

                const symbol = checkbox.dataset.symbol;
                // Find dataset by matching symbol directly
                const datasetIndex = window.marketChart.data.datasets.findIndex(ds => ds.symbol === symbol);

                if (datasetIndex !== -1) {{
                    window.marketChart.data.datasets[datasetIndex].hidden = !checked;
                }}
            }});
            window.marketChart.update();
        }}

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
            <a href="../about.html">About</a>
            <a href="../index.html">Latest</a>
            <a href="../archive.html">Archive</a>
            <a href="https://github.com/mat-e-exp/ai-pulse-briefings">GitHub</a>
        </nav>
    </header>

    <main>
        <section class="sentiment-box">
            <h3>Sentiment Trend (Last 30 Days)</h3>
            <div class="chart-container">
                <canvas id="sentimentChart"></canvas>
            </div>
        </section>

        <section class="sentiment-box">
            <h3>Market Performance (Last 30 Days)</h3>
            <div class="chart-container">
                <canvas id="marketChart"></canvas>
            </div>

            <div class="market-controls">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h4 style="margin: 0;">Select Indices & Stocks</h4>
                    <div class="market-control-buttons">
                        <button onclick="toggleAllMarketSymbols(true)" class="market-control-btn">All</button>
                        <button onclick="toggleAllMarketSymbols(false)" class="market-control-btn">None</button>
                    </div>
                </div>
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
            ('Palantir', '#34d399'),
            ('AI/Robotics ETF', '#a78bfa'),
            ('AI Analytics ETF', '#f472b6'),
            ('Bitcoin', '#f59e0b')
        ]

        # Map labels to symbols for checkbox data attributes
        symbol_map = {
            'NASDAQ': '^IXIC',
            'S&P 500': '^GSPC',
            'NVIDIA': 'NVDA',
            'Microsoft': 'MSFT',
            'Alphabet': 'GOOGL',
            'Meta': 'META',
            'AMD': 'AMD',
            'Palantir': 'PLTR',
            'AI/Robotics ETF': 'BOTZ',
            'AI Analytics ETF': 'AIQ',
            'Bitcoin': 'BTC-USD'
        }

        for idx, (label, color) in enumerate(symbol_labels):
            symbol = symbol_map.get(label, '')
            # Check if this symbol has data
            has_data = symbol in market_data
            disabled_attr = '' if has_data else ' disabled'
            disabled_style = '' if has_data else ' opacity: 0.4;'

            checked_attr = ' checked' if has_data else ''
            html += f"""
                    <label class="checkbox-label" style="{disabled_style}">
                        <input type="checkbox" id="symbol-{idx}" class="market-checkbox" data-symbol="{symbol}"{disabled_attr}{checked_attr}>
                        <span style="color: {color}">■</span> {label}
                    </label>
"""

        html += """
                </div>
            </div>
        </section>
"""

        # Prediction insights section (if available)
        if insights:
            full_text = insights['insights']
            lines = full_text.split('\n')

            # Extract executive summary
            exec_summary = []
            in_exec = False
            for line in lines:
                if '## EXECUTIVE SUMMARY' in line or 'EXECUTIVE SUMMARY' in line.upper():
                    in_exec = True
                    continue
                if in_exec:
                    if line.strip().startswith('##'):
                        break
                    if line.strip():
                        exec_summary.append(line.strip())

            exec_summary_text = ' '.join(exec_summary) if exec_summary else 'Analysis of prediction accuracy patterns across historical data.'

            # Extract accuracy stats from text for display
            import re
            accuracy_match = re.search(r'(\d+)%\s+accuracy', full_text)
            accuracy_pct = accuracy_match.group(1) if accuracy_match else '?'

            # Convert full text to HTML with proper formatting
            full_html = self._format_insights_html(full_text)

            html += f"""
        <section class="sentiment-box">
            <h3>📊 Predictive Correlation Analysis</h3>
            <p style="font-size: 0.85rem; color: #94a3b8; margin-top: -5px; margin-bottom: 20px;">
                Analyzing if overnight AI sector sentiment predicts same-day market performance<br>
                <strong>Workflow:</strong> Overnight news (previous close 9pm GMT → 1pm GMT analysis) → Today's market movement (2:30pm-9pm GMT)<br>
                Based on {insights['days']} days of historical data (updated {insights['date']})
            </p>

            <!-- Card-based summary (default view) -->
            <div id="insights-summary">
                <!-- Executive Summary Card -->
                <div style="background: #1e293b; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 4px solid #60a5fa;">
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 10px; font-weight: 600;">KEY FINDINGS</div>
                    <div style="color: #e2e8f0; line-height: 1.7; font-size: 0.95rem;">
                        {exec_summary_text}
                    </div>
                </div>

                <button id="insights-toggle" onclick="toggleInsights()"
                        style="width: 100%; padding: 12px; background: #1e293b; color: #6ee7b7; border: 1px solid #6ee7b7; border-radius: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 600; transition: all 0.2s;">
                    Show Detailed Analysis →
                </button>
            </div>

            <!-- Full analysis view (hidden by default) -->
            <div id="insights-full" style="display: none;">
                <div style="background: #1e293b; padding: 25px; border-radius: 10px; border-left: 4px solid #c084fc;">
                    {full_html}
                </div>

                <button onclick="toggleInsights()"
                        style="width: 100%; padding: 12px; background: #1e293b; color: #6ee7b7; border: 1px solid #6ee7b7; border-radius: 8px; cursor: pointer; font-size: 0.9rem; font-weight: 600; margin-top: 15px; transition: all 0.2s;">
                    ← Show Key Findings
                </button>
            </div>
        </section>

        <script>
        function toggleInsights() {{
            const summary = document.getElementById('insights-summary');
            const full = document.getElementById('insights-full');

            if (full.style.display === 'none') {{
                summary.style.display = 'none';
                full.style.display = 'block';
            }} else {{
                summary.style.display = 'block';
                full.style.display = 'none';
            }}
        }}
        </script>
"""

        # Material events (show top 3, expand for more)
        if material_events:
            html += """
        <section class="sentiment-box">
            <h2>📈 Material Events <span style="font-size: 0.7em; color: #94a3b8; font-weight: normal;">(thesis-changing)</span></h2>
"""
            for idx, event in enumerate(material_events):
                if idx < 3:
                    html += self._generate_event_card(event)
                else:
                    # Hidden by default
                    html += f'<div id="material-hidden-{idx}" style="display: none;">'
                    html += self._generate_event_card(event)
                    html += '</div>'

            if len(material_events) > 3:
                html += f"""
            <button onclick="toggleEventSection('material', {len(material_events)})" id="material-toggle-btn"
                    style="margin: 20px auto; display: block; padding: 8px 20px; background: var(--primary-color); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;">
                Show {len(material_events) - 3} More Events
            </button>
"""
            html += """        </section>
"""

        # Notable events (show top 3, expand for more)
        if notable_events:
            html += """
        <section class="sentiment-box">
            <h2>📊 Notable Events <span style="font-size: 0.7em; color: #94a3b8; font-weight: normal;">(worth tracking)</span></h2>
"""
            for idx, event in enumerate(notable_events):
                if idx < 3:
                    html += self._generate_event_card(event)
                else:
                    html += f'<div id="notable-hidden-{idx}" style="display: none;">'
                    html += self._generate_event_card(event)
                    html += '</div>'

            if len(notable_events) > 3:
                html += f"""
            <button onclick="toggleEventSection('notable', {len(notable_events)})" id="notable-toggle-btn"
                    style="margin: 20px auto; display: block; padding: 8px 20px; background: var(--primary-color); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;">
                Show {len(notable_events) - 3} More Events
            </button>
"""
            html += """        </section>
"""

        # Background events (show top 3, expand for more)
        if background_events:
            html += """
        <section class="sentiment-box">
            <h2>👀 Background <span style="font-size: 0.7em; color: #94a3b8; font-weight: normal;">(general awareness)</span></h2>
"""
            for idx, event in enumerate(background_events):
                if idx < 3:
                    html += self._generate_event_card(event)
                else:
                    html += f'<div id="background-hidden-{idx}" style="display: none;">'
                    html += self._generate_event_card(event)
                    html += '</div>'

            if len(background_events) > 3:
                html += f"""
            <button onclick="toggleEventSection('background', {len(background_events)})" id="background-toggle-btn"
                    style="margin: 20px auto; display: block; padding: 8px 20px; background: var(--primary-color); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;">
                Show {len(background_events) - 3} More Events
            </button>
"""
            html += """        </section>
"""

        # Research Highlights section (separate from sentiment-driven news)
        if research_papers:
            html += """
        <section class="sentiment-box">
            <h2>📚 Research Highlights <span style="font-size: 0.7em; color: #94a3b8; font-weight: normal;">(technical developments)</span></h2>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 20px; font-style: italic;">
                Research papers are not included in sentiment analysis - they represent technical progress rather than market-moving news.
            </p>
"""
            for idx, event in enumerate(research_papers):
                if idx < 5:
                    html += self._generate_event_card(event)
                else:
                    html += f'<div id="research-hidden-{idx}" style="display: none;">'
                    html += self._generate_event_card(event)
                    html += '</div>'

            if len(research_papers) > 5:
                html += f"""
            <button onclick="toggleEventSection('research', {len(research_papers)})" id="research-toggle-btn"
                    style="margin: 20px auto; display: block; padding: 8px 20px; background: var(--primary-color); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;">
                Show {len(research_papers) - 5} More Events
            </button>
"""
            html += """        </section>
"""

        # JavaScript for expand/collapse event sections
        html += """
        <script>
        function toggleEventSection(section, totalCount) {
            const button = document.getElementById(section + '-toggle-btn');
            const isExpanded = button.textContent.includes('Show Less');

            for (let i = 3; i < totalCount; i++) {
                const elem = document.getElementById(section + '-hidden-' + i);
                if (elem) {
                    elem.style.display = isExpanded ? 'none' : 'block';
                }
            }

            if (isExpanded) {
                button.textContent = 'Show ' + (totalCount - 3) + ' More Events';
            } else {
                button.textContent = 'Show Less';
            }
        }
        </script>
"""

        # Add accuracy heat map if data available
        if heatmap_data:
            html += self._render_heatmap(heatmap_data)

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

    def _format_insights_html(self, text: str) -> str:
        """Format insights text to clean HTML with proper visual hierarchy"""
        lines = text.split('\n')
        html_parts = []
        in_list = False

        for line in lines:
            line = line.strip()
            if not line:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                continue

            # Skip executive summary section (already displayed separately)
            if 'EXECUTIVE SUMMARY' in line.upper():
                continue

            # Main section headers (## DETAILED ANALYSIS, etc.)
            if line.startswith('## '):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                header_text = line.replace('## ', '').replace('#', '')
                html_parts.append(f'<div style="margin-top: 30px; padding-bottom: 10px; border-bottom: 2px solid #334155;"><span style="font-size: 1.2em; color: #6ee7b7; font-weight: 700;">{header_text}</span></div>')
            # Numbered section headers (1. Pattern Recognition)
            elif line[0].isdigit() and '. **' in line:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                section_text = line.split('**')[1] if '**' in line else line
                html_parts.append(f'<p style="margin-top: 25px; font-size: 1.1em; color: #60a5fa; font-weight: 600;">{section_text}</p>')
            # Bold subsection headers
            elif line.startswith('**') and line.endswith('**'):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                subheader_text = line.replace('**', '')
                html_parts.append(f'<p style="margin-top: 15px; color: #fbbf24; font-weight: 600;">{subheader_text}</p>')
            # Bullet points
            elif line.startswith('- '):
                if not in_list:
                    html_parts.append('<ul style="margin-left: 20px; line-height: 1.8;">')
                    in_list = True
                bullet_text = line[2:].replace('**', '<strong>').replace('</strong><strong>', '**')
                # Close any unclosed strong tags
                if bullet_text.count('<strong>') != bullet_text.count('</strong>'):
                    bullet_text += '</strong>'
                html_parts.append(f'<li style="color: #e2e8f0; margin-bottom: 8px;">{bullet_text}</li>')
            # Regular paragraphs
            else:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                para_text = line.replace('**', '<strong>').replace('</strong><strong>', '**')
                if para_text.count('<strong>') != para_text.count('</strong>'):
                    para_text += '</strong>'
                html_parts.append(f'<p style="color: #cbd5e1; line-height: 1.7; margin-bottom: 10px;">{para_text}</p>')

        # Close any open list
        if in_list:
            html_parts.append('</ul>')

        return ''.join(html_parts)

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

        # Get closed market dates
        cursor.execute("""
            SELECT DISTINCT date
            FROM predictions
            WHERE date >= date('now', '-' || ? || ' days')
            AND market_status = 'closed'
            ORDER BY date ASC
        """, (days,))

        closed_dates = [row['date'] for row in cursor.fetchall()]
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

        # Add closed dates to data
        data['_closed_dates'] = closed_dates

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

    def _get_latest_insights(self) -> dict:
        """Get the most recent prediction insights analysis"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT analysis_date, days_analyzed, insights, created_at
            FROM prediction_insights
            ORDER BY created_at DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'date': row['analysis_date'],
                'days': row['days_analyzed'],
                'insights': row['insights'],
                'created_at': row['created_at']
            }
        return None

    def _get_accuracy_data(self, days: int = 30) -> dict:
        """Get prediction accuracy data for last N days"""
        accuracy_records = self.db.get_all_accuracy(days=days)

        if not accuracy_records:
            return None

        # Group by symbol
        by_symbol = {}
        for record in accuracy_records:
            symbol = record['symbol']
            if symbol not in by_symbol:
                by_symbol[symbol] = {
                    'correct': 0,
                    'total': 0,
                    'correlation': record.get('sentiment_correlation', 0)
                }
            by_symbol[symbol]['total'] += 1
            if record['correct']:
                by_symbol[symbol]['correct'] += 1

        # Calculate accuracy percentages
        for symbol in by_symbol:
            total = by_symbol[symbol]['total']
            correct = by_symbol[symbol]['correct']
            by_symbol[symbol]['accuracy'] = round((correct / total) * 100, 1) if total > 0 else 0

        return by_symbol

    def _get_heatmap_data(self, days: int = 30) -> dict:
        """
        Get accuracy data formatted for heat map display.

        Returns:
            {
                'dates': ['2025-11-24', '2025-11-25', ...],
                'symbols': [
                    {
                        'symbol': 'NVDA',
                        'name': 'NVIDIA',
                        'type': 'stock',
                        'results': [
                            {'date': '2025-11-24', 'correct': True, 'prediction': 'bullish',
                             'outcome': 'up', 'change_pct': 2.05},
                            {'date': '2025-11-27', 'market_closed': True},
                            ...
                        ]
                    },
                    ...
                ],
                'overall': {'total': 30, 'correct': 18, 'accuracy_pct': 60.0},
                'best_day': {'date': '2025-11-24', 'accuracy': 90.9, 'correct': 10, 'total': 11},
                'worst_day': {'date': '2025-11-28', 'accuracy': 9.1, 'correct': 1, 'total': 11}
            }
        """
        from datetime import datetime, timedelta
        import sqlite3

        # Get date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # Query database for accuracy data (primary source with symbols)
        query = """
        SELECT
            a.date,
            a.symbol,
            a.prediction,
            a.outcome,
            a.correct,
            a.sentiment_correlation,
            o.change_pct
        FROM accuracy_log a
        LEFT JOIN outcomes o ON a.date = o.date AND a.symbol = o.symbol
        WHERE a.date >= ? AND a.date <= ?
        ORDER BY a.date, a.symbol
        """

        cursor = self.db.conn.cursor()
        cursor.execute(query, (str(start_date), str(end_date)))
        rows = cursor.fetchall()

        # Build date list (only dates with predictions)
        dates = sorted(list(set([row[0] for row in rows])))

        # Helper to determine symbol type
        def get_symbol_type(symbol):
            if symbol.startswith('^'):
                return 'index'
            elif '-USD' in symbol:
                return 'crypto'
            else:
                return 'stock'

        # Organize by symbol
        symbol_data = {}
        for row in rows:
            date, symbol, prediction, outcome, correct, correlation, change_pct = row

            if symbol not in symbol_data:
                symbol_data[symbol] = {
                    'symbol': symbol,
                    'name': symbol,  # Use symbol as name
                    'type': get_symbol_type(symbol),
                    'results': {}
                }

            symbol_data[symbol]['results'][date] = {
                'date': date,
                'prediction': prediction,
                'correct': correct == 1 if correct is not None else None,
                'outcome': outcome,
                'change_pct': change_pct,
                'correlation': correlation,
                'market_closed': False  # If we have a record in accuracy_log, market was open
            }

        # Convert to list format with all dates filled
        symbols = []
        for symbol, data in sorted(symbol_data.items(), key=lambda x: (x[1]['type'], x[0])):
            results = []
            for date in dates:
                if date in data['results']:
                    results.append(data['results'][date])
                else:
                    # No prediction for this date
                    results.append({'date': date, 'no_prediction': True})

            symbols.append({
                'symbol': data['symbol'],
                'name': data['name'],
                'type': data['type'],
                'results': results
            })

        # Calculate overall stats
        total_predictions = sum(1 for s in symbols for r in s['results'] if not r.get('market_closed') and not r.get('no_prediction'))
        correct_predictions = sum(1 for s in symbols for r in s['results'] if r.get('correct') == True)
        overall_accuracy = round((correct_predictions / total_predictions * 100), 1) if total_predictions > 0 else 0

        # Calculate best/worst days
        daily_stats = {}
        for date in dates:
            day_total = 0
            day_correct = 0
            for s in symbols:
                for r in s['results']:
                    if r['date'] == date and not r.get('market_closed') and not r.get('no_prediction'):
                        day_total += 1
                        if r.get('correct'):
                            day_correct += 1

            if day_total > 0:
                daily_stats[date] = {
                    'date': date,
                    'correct': day_correct,
                    'total': day_total,
                    'accuracy': round((day_correct / day_total * 100), 1)
                }

        best_day = max(daily_stats.values(), key=lambda x: x['accuracy']) if daily_stats else None
        worst_day = min(daily_stats.values(), key=lambda x: x['accuracy']) if daily_stats else None

        return {
            'dates': dates,
            'symbols': symbols,
            'overall': {
                'total': total_predictions,
                'correct': correct_predictions,
                'accuracy_pct': overall_accuracy
            },
            'best_day': best_day,
            'worst_day': worst_day
        }

    def _render_heatmap(self, heatmap_data: dict) -> str:
        """Render compact accuracy heat map HTML"""
        if not heatmap_data or not heatmap_data['dates']:
            return ""

        overall = heatmap_data['overall']

        # Symbol name mapping
        symbol_names = {
            '^GSPC': 'S&P 500',
            '^DJI': 'Dow Jones',
            '^IXIC': 'NASDAQ',
            '^VIX': 'VIX',
            'NVDA': 'NVIDIA',
            'MSFT': 'Microsoft',
            'GOOGL': 'Google',
            'AMZN': 'Amazon',
            'META': 'Meta',
            'TSLA': 'Tesla',
            'AAPL': 'Apple',
            'QQQ': 'QQQ ETF',
            'SPY': 'SPY ETF',
            'BTC-USD': 'Bitcoin',
            'ETH-USD': 'Ethereum'
        }

        html = """
        <section class="sentiment-box">
            <h2>📊 Prediction Accuracy (Last 30 Days)</h2>
"""

        # Overall accuracy
        overall_color = "#6ee7b7" if overall['accuracy_pct'] >= 60 else "#fcd34d" if overall['accuracy_pct'] >= 50 else "#fca5a5"
        html += f"""
            <div style="margin-bottom: 20px;">
                <span style="color: #94a3b8;">Overall: </span>
                <span style="color: {overall_color}; font-weight: 700; font-size: 1.3rem;">{overall['accuracy_pct']}%</span>
                <span style="color: #94a3b8; font-size: 0.9rem;"> ({overall['correct']}/{overall['total']} correct)</span>
            </div>

            <div class="heatmap-container">
"""

        from datetime import datetime

        # Date headers
        html += '                <div class="heatmap-header">\n'
        html += '                    <div class="heatmap-symbol-label"></div>\n'
        html += '                    <div class="heatmap-accuracy-label"></div>\n'
        html += '                    <div class="heatmap-dates">\n'

        for date_str in heatmap_data['dates']:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_num = date_obj.strftime('%d')
            html += f'                        <div class="heatmap-date-label" title="{date_str}">{day_num}</div>\n'

        html += '                    </div>\n'
        html += '                </div>\n'

        # Symbol rows
        for symbol_data in heatmap_data['symbols']:
            symbol = symbol_data['symbol']
            name = symbol_names.get(symbol, symbol)

            # Calculate accuracy for this symbol
            total = sum(1 for r in symbol_data['results'] if not r.get('market_closed') and not r.get('no_prediction'))
            correct = sum(1 for r in symbol_data['results'] if r.get('correct') == True)
            accuracy = round((correct / total * 100), 0) if total > 0 else 0

            html += '                <div class="heatmap-row">\n'
            html += f'                    <div class="heatmap-symbol-label" title="{symbol}">{name}</div>\n'
            html += f'                    <div class="heatmap-accuracy-label">{int(accuracy)}%</div>\n'
            html += '                    <div class="heatmap-cells">\n'

            # Daily results - small colored squares
            for result in symbol_data['results']:
                if result.get('market_closed'):
                    html += '                        <div class="heatmap-square heatmap-square-closed" title="Market closed"></div>\n'
                elif result.get('no_prediction'):
                    html += '                        <div class="heatmap-square heatmap-square-none" title="No prediction"></div>\n'
                elif result.get('correct') is True:
                    prediction = result.get('prediction', '')
                    outcome = result.get('outcome', '')
                    change = result.get('change_pct', 0)
                    tooltip = f"✓ {prediction} → {outcome} ({change:+.2f}%)" if change else f"✓ {prediction} → {outcome}"
                    html += f'                        <div class="heatmap-square heatmap-square-correct" title="{tooltip}"></div>\n'
                elif result.get('correct') is False:
                    prediction = result.get('prediction', '')
                    outcome = result.get('outcome', '')
                    change = result.get('change_pct', 0)
                    tooltip = f"✗ {prediction} → {outcome} ({change:+.2f}%)" if change else f"✗ {prediction} → {outcome}"
                    html += f'                        <div class="heatmap-square heatmap-square-incorrect" title="{tooltip}"></div>\n'
                else:
                    html += '                        <div class="heatmap-square heatmap-square-none"></div>\n'

            html += '                    </div>\n'
            html += '                </div>\n'

        html += """
            </div>

            <div style="margin-top: 15px; display: flex; gap: 20px; font-size: 0.85rem; color: #94a3b8;">
                <div style="display: flex; align-items: center; gap: 5px;">
                    <div class="heatmap-square heatmap-square-correct" style="width: 16px; height: 16px;"></div>
                    <span>Correct</span>
                </div>
                <div style="display: flex; align-items: center; gap: 5px;">
                    <div class="heatmap-square heatmap-square-incorrect" style="width: 16px; height: 16px;"></div>
                    <span>Incorrect</span>
                </div>
                <div style="display: flex; align-items: center; gap: 5px;">
                    <div class="heatmap-square heatmap-square-closed" style="width: 16px; height: 16px;"></div>
                    <span>Market closed</span>
                </div>
            </div>
        </section>
"""

        return html

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
