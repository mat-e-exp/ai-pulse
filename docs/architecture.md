# AI-Pulse Architecture Overview

## System Purpose

Real-time intelligence agent for AI sector investment decisions. Autonomously collects, analyzes, and publishes daily briefings on AI industry developments.

**Live site**: https://ai-pulse.aifinto.com

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  DATA SOURCES (7 sources, collected 2x daily)               │
├─────────────────────────────────────────────────────────────┤
│  Hacker News │ NewsAPI │ Tech RSS │ ArXiv │ SEC │ GitHub │ IR│
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │  COLLECTION LAYER    │
         │  agents/collector.py │
         │  sources/*.py        │
         └──────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  DEDUPLICATION (5x)  │
         │  1. DB constraints   │
         │  2. URL tracking     │
         │  3. String similarity│
         │  4. Claude semantic  │
         │  5. Publishing filter│
         └──────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  ANALYSIS LAYER      │
         │  agents/analyzer.py  │
         │  Claude Haiku        │
         │  (significance,      │
         │   sentiment, impact) │
         └──────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  STORAGE LAYER       │
         │  storage/db.py       │
         │  SQLite database     │
         │  (with safety utils) │
         └──────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  PUBLISHING LAYER    │
         │  agents/html_reporter│
         │  publish_briefing.py │
         │  regenerate_html.py  │
         └──────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  DEPLOYMENT          │
         │  GitHub Actions      │
         │  GitHub Pages        │
         └─────────────────────┘
```

---

## Component Details

### Collection Layer
**Purpose**: Fetch events from 7 data sources
**Frequency**: 6am GMT (overnight news) + 1:30pm GMT (delta)
**Implementation**: `agents/collector.py` orchestrates `sources/*.py` modules
**Details**: See [data-collection.md](data-collection.md)

### Deduplication Layer
**Purpose**: Ensure each unique story counted once
**5-Layer System**:
1. Database UNIQUE constraints (source + ID)
2. Source-level URL tracking (ArXiv cross-category)
3. Content similarity (75% title match)
4. Semantic deduplication (Claude Haiku)
5. Publishing filter (exclude marked duplicates)

**Details**: See [deduplication.md](deduplication.md)

### Analysis Layer
**Purpose**: Autonomous significance scoring and sentiment analysis
**Model**: Claude Haiku (cost-optimized)
**Outputs**: Significance (0-100), sentiment, implications, affected parties
**Details**: See [analysis-pipeline.md](analysis-pipeline.md)

### Storage Layer
**Database**: SQLite (`ai_pulse.db`)
**Key Tables**:
- `events` - collected and analyzed events
- `predictions` - daily market predictions (locked after 2:30pm GMT)
- `prediction_audit` - full audit trail
- `workflow_runs` - duplicate detection
- `daily_sentiment` - sentiment aggregates
- `market_data` - S&P 500 tracking

**Details**: See [database-schema.md](database-schema.md), [safety.md](safety.md)

### Publishing Layer
**Two modes**:
1. **Full pipeline** (`publish_briefing.py`) - Logs predictions, writes DB
2. **HTML-only** (`regenerate_html.py`) - Safe, no DB writes

**Output**: HTML briefings with sentiment charts
**Deployment**: GitHub Actions → GitHub Pages

---

## Data Flow

### Morning Collection (6am GMT - Daily)
```
sources → collector → dedup → analyzer → database
                                            ↓
                                      Discord (top 10)
```
**Runs:** Every day (Mon-Sun)

### Afternoon Publish (1:30pm GMT - Daily)
```
sources → collector → dedup → analyzer → database
                                            ↓
                                    publish_briefing.py
                                            ↓
                            ┌───────────────┼───────────────┐
                            ↓               ↓               ↓
                  predictions (Mon-Fri)  HTML files    Discord
                      (locked)                         (link)
                            ↓               ↓
                      audit trail     GitHub Pages
```
**Runs:** Every day (Mon-Sun)
**Predictions:** Only created Mon-Fri (trading days)
**Weekends:** News collected/analyzed, webpage published, but no prediction created

### Market Close (9:30pm GMT - Mon-Fri Only)
```
market APIs → market_data table
                    ↓
            calculate accuracy
                    ↓
               Discord
```
**Runs:** Mon-Fri only
**Purpose:** Collect closing prices, compare predictions to outcomes

---

## Technology Stack

**Language**: Python 3.9+
**LLM**: Claude API (Anthropic SDK)
  - Haiku: Analysis, deduplication (cost-optimized)
  - Sonnet: Future features

**Storage**: SQLite
**Automation**: GitHub Actions (cron schedules)
**Publishing**: GitHub Pages (static HTML)
**Notifications**: Discord webhooks

**Key Libraries**:
- `anthropic` - LLM reasoning
- `requests` - HTTP calls
- `yfinance` - Market data
- `feedparser` - RSS parsing
- `beautifulsoup4` - Web scraping

---

## Repository Structure

```
ai-pulse/
├── agents/                    # Agent logic
│   ├── collector.py          # Data collection orchestration
│   ├── analyzer.py           # Significance scoring
│   ├── semantic_deduplicator.py  # Claude-powered dedup
│   ├── html_reporter.py      # Briefing generation
│   ├── prediction_logger.py  # Prediction tracking
│   └── discord_morning.py    # Discord formatting
├── sources/                   # Data source integrations
│   ├── hackernews.py
│   ├── newsapi.py
│   ├── rss_feeds.py
│   ├── arxiv_papers.py
│   ├── sec_edgar.py
│   ├── github_trending.py
│   └── company_ir.py
├── storage/                   # Data persistence
│   ├── db.py                 # Database operations
│   └── db_safety.py          # Safety utilities
├── migrations/                # Database migrations
├── .github/workflows/         # Automation
│   ├── morning-collection.yml
│   ├── daily-collection.yml
│   ├── market-close.yml
│   └── deploy-assets.yml
├── briefings/                 # Generated HTML
├── docs/                      # Documentation
├── ai_pulse.db               # SQLite database
├── index.html                # Latest briefing
├── archive.html              # Briefing list
├── style.css                 # Shared styles
├── publish_briefing.py       # Full pipeline (dangerous)
├── regenerate_html.py        # HTML-only (safe)
└── CLAUDE.md                 # Operational guide
```

---

## Safety & Accuracy

**Primary Goal**: Accuracy above speed, cost, or features

**Key Safety Features**:
1. **Prediction Locking** - Can't update after market opens (2:30pm GMT)
2. **Timestamp Preservation** - `first_logged_at` never changes
3. **Audit Trail** - Every prediction change logged
4. **Duplicate Detection** - Warns on duplicate workflow runs
5. **Idempotent Operations** - Safe to rerun (overwrites, not duplicates)

**See**: [safety.md](safety.md)

---

## Target Sectors

**Public Companies**: NVDA, MSFT, GOOGL, META, AMZN, AMD, ARM, TSMC, ASML
**Private Leaders**: OpenAI, Anthropic, Mistral, Cohere, xAI, Perplexity
**Infrastructure**: Cloud providers, chip makers, data centers
**Applications**: Enterprise AI, developer tools, consumer AI

---

## Development Status

✅ **Production** (since 2025-11-12)
- Automated daily pipeline
- Morning collection (6am)
- Afternoon publish (1:30pm)
- Market tracking (9:30pm Mon-Fri)
- Safety features active

**See**: [history.md](history.md) for development timeline
