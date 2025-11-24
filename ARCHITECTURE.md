# AI-Pulse Architecture

This document helps the issue-driven agent understand how the system works and how files relate to each other.

## Data Flow

```
External APIs → Collectors → Database → Reporters → HTML Output
```

### Collection Pipeline
```
sources/*.py          → Raw data from APIs (NewsAPI, HackerNews, SEC, etc.)
agents/collector.py   → Orchestrates collection, deduplication
agents/market_collector.py → Market data (stocks, indices, crypto)
    ↓
ai_pulse.db (SQLite)  → events, market_data, daily_sentiment tables
```

### Analysis Pipeline
```
ai_pulse.db           → Raw events
agents/semantic_deduplicator.py → Remove semantic duplicates
agents/analyzer.py    → Score significance, sentiment
analysis/significance.py → Claude prompts for analysis
    ↓
ai_pulse.db           → Updated with scores and sentiment
```

### Publishing Pipeline
```
ai_pulse.db           → Analyzed events + market data
agents/html_reporter.py → Generate HTML with charts
publish_briefing.py   → Orchestrate publishing, fix paths
    ↓
briefings/*.html, index.html → Output files
```

## File Relationships

### Market Data (symbols, charts)
When adding/modifying market symbols:
1. `agents/market_collector.py` - SYMBOLS dict defines what to fetch
2. `agents/html_reporter.py` - symbolConfig array defines what to display

**Both files must be updated together.** The collector fetches data, the reporter displays it.

### News Sources
When adding/modifying news sources:
1. `sources/*.py` - Individual source implementations (newsapi.py, hackernews.py, etc.)
2. `agents/collector.py` - Orchestrates which sources to call

### Analysis/Scoring
When modifying how events are analyzed:
1. `analysis/significance.py` - Claude prompts and scoring logic
2. `agents/analyzer.py` - Orchestrates analysis process

### Display/UI
When modifying visual output:
1. `agents/html_reporter.py` - HTML generation, chart configs, layout
2. `style.css` - Colors, fonts, spacing

## Common Change Patterns

### "Add a new market symbol" (e.g., BTC-USD, new stock)
Files to modify:
- `agents/market_collector.py`: Add to SYMBOLS dict (under appropriate category: stocks, indices, etfs, crypto)
- `agents/html_reporter.py`: Add to symbolConfig array with label and color

Example in market_collector.py:
```python
SYMBOLS = {
    'crypto': {
        'BTC-USD': 'Bitcoin',  # Add new symbol here
    }
}
```

Example in html_reporter.py:
```javascript
const symbolConfig = [
    {symbol: 'BTC-USD', label: 'Bitcoin', color: '#f7931a'},  // Add here too
];
```

### "Add a new news source"
Files to modify:
- `sources/newsource.py`: Create new source file with fetch function
- `agents/collector.py`: Import and call the new source

### "Change how events are scored/analyzed"
Files to modify:
- `analysis/significance.py`: Modify the Claude prompt or scoring logic

### "Change chart appearance or layout"
Files to modify:
- `agents/html_reporter.py`: Modify chart configuration or HTML structure
- `style.css`: Modify colors, spacing, fonts

### "Add a new metric or data display"
Files to modify:
- Collector for the data type (market_collector.py or collector.py)
- `agents/html_reporter.py`: Add display code
- Possibly `publish_briefing.py` if new data queries needed

## Database Schema

### events table
- id, source, source_url, title, content, summary
- event_type, companies, published_at, collected_at
- significance_score, sentiment, implications
- is_duplicate, is_semantic_duplicate

### market_data table
- symbol, date, open, high, low, close, volume, change_pct

### daily_sentiment table
- date, positive, negative, neutral, mixed, total_analyzed

## Color Palette (for charts)
When adding new chart elements, use colors that don't conflict:
- Existing: #6ee7b7, #94a3b8, #c084fc, #60a5fa, #fbbf24, #f87171, #fb923c, #34d399, #a78bfa, #f472b6
- Bitcoin orange: #f7931a
- Ethereum blue: #627eea
- Available pastels: #67e8f9 (cyan), #fda4af (rose), #bef264 (lime)
