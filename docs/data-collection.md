# AI-Pulse Data Collection

## Overview

AI-Pulse collects events from **7 data sources** to track AI sector news, research, and market activity:

1. Hacker News (tech community discussions)
2. NewsAPI (professional news coverage)
3. Tech RSS Feeds (tech journalism outlets)
4. ArXiv (AI/ML research papers)
5. SEC EDGAR (material corporate events)
6. GitHub (trending AI repositories)
7. Company IR (direct press releases)

**Collection Frequency**: Twice daily (6am + 1:30pm GMT) via GitHub Actions

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    agents/collector.py                       │
│                  (Orchestrates all sources)                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ sources/│          │ sources/│          │ sources/│
   │ *.py    │          │ *.py    │          │ *.py    │
   └─────────┘          └─────────┘          └─────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌─────────▼────────┐
                    │  Deduplication   │
                    │  (3 layers)      │
                    └─────────┬────────┘
                              │
                    ┌─────────▼────────┐
                    │  storage/db.py   │
                    │  (SQLite)        │
                    └──────────────────┘
```

---

## Source 1: Hacker News

**File**: `sources/hackernews.py`
**API**: https://hacker-news.firebaseio.com/v0/
**Rate Limit**: None (unlimited, free)
**API Key**: Not required

### What It Collects

- Top stories from HN front page
- Stories mentioning AI companies, products, or keywords
- Comments are NOT collected (too noisy)

### Collection Parameters

```bash
--hn-limit 20  # Number of top stories to fetch (default: 50)
```

### API Structure

```
GET https://hacker-news.firebaseio.com/v0/topstories.json
→ Returns: [46020096, 46020095, 46020094, ...]  # Story IDs

GET https://hacker-news.firebaseio.com/v0/item/46020096.json
→ Returns: {
    "id": 46020096,
    "title": "Show HN: AI-powered code review",
    "url": "https://example.com",
    "score": 250,
    "by": "username",
    "time": 1732536000
}
```

### Deduplication

**source_id**: HN item ID (e.g., "46020096")
**UNIQUE constraint**: `('hackernews', '46020096')` prevents re-collection

### Why Hacker News?

- Tech community's pulse on AI developments
- Early signal for trends (often breaks before mainstream news)
- Filters for significance through upvotes
- Free and reliable API

---

## Source 2: NewsAPI

**File**: `sources/newsapi.py`
**API**: https://newsapi.org/
**Rate Limit**: 100 calls/day (free tier)
**API Key**: Required - `NEWS_API_KEY` in `.env`

### What It Collects

- Professional news articles mentioning:
  - AI companies: "OpenAI", "Anthropic", "NVIDIA", "Microsoft", etc.
  - AI keywords: "artificial intelligence", "GPT", "LLM", "machine learning"
- From major outlets: Reuters, Bloomberg, TechCrunch, The Verge, etc.

### Collection Parameters

```bash
--news-limit 30   # Max articles per collection (default: 50)
--news-days 1     # Days back to search (default: 1)
```

### API Structure

```
GET https://newsapi.org/v2/everything?
  q=(OpenAI OR Anthropic OR NVIDIA OR "artificial intelligence")
  &language=en
  &sortBy=publishedAt
  &pageSize=30
  &apiKey=YOUR_KEY
```

Returns:
```json
{
  "articles": [
    {
      "title": "OpenAI Launches GPT-5",
      "url": "https://techcrunch.com/...",
      "publishedAt": "2025-11-25T10:30:00Z",
      "source": {"name": "TechCrunch"},
      "description": "..."
    }
  ]
}
```

### Deduplication

**source_id**: Full article URL
**UNIQUE constraint**: `('newsapi', 'https://techcrunch.com/...')` prevents re-collection

### Rate Limit Management

**Free tier**: 100 calls/day
**Usage**:
- Morning run (6am): ~1 call
- Afternoon run (1:30pm): ~1 call
- **Total**: ~2 calls/day (well under limit)

**If rate limited**: Collector catches error, continues with other sources

### Why NewsAPI?

- Professional journalism quality
- Broad coverage across outlets
- Structured API with consistent format
- Free tier sufficient for daily briefings

---

## Source 3: Tech RSS Feeds

**File**: `sources/tech_rss.py`
**API**: RSS 2.0 feeds from tech outlets
**Rate Limit**: None (RSS feeds are public)
**API Key**: Not required

### What It Collects

**Outlets covered:**
- TechCrunch: `https://techcrunch.com/tag/artificial-intelligence/feed/`
- VentureBeat: `https://venturebeat.com/category/ai/feed/`
- The Verge: `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml`
- Ars Technica: `https://feeds.arstechnica.com/arstechnica/technology-lab`
- MIT Technology Review: `https://www.technologyreview.com/topic/artificial-intelligence/feed`
- Wired AI: `https://www.wired.com/feed/tag/ai/latest/rss`
- AI News: `https://www.artificialintelligence-news.com/feed/`

### Collection Parameters

```bash
--rss-days 1      # Days back (default: 1)
--rss-limit 10    # Articles per feed (default: 10)
```

### RSS Feed Structure

```xml
<rss version="2.0">
  <channel>
    <item>
      <title>Google DeepMind announces AlphaFold 3</title>
      <link>https://techcrunch.com/...</link>
      <pubDate>Mon, 25 Nov 2025 10:00:00 GMT</pubDate>
      <description>...</description>
    </item>
  </channel>
</rss>
```

### Deduplication

**source_id**: Full article URL
**UNIQUE constraint**: `('tech_rss', 'https://techcrunch.com/...')` prevents re-collection

**Cross-source dedup**: Many tech RSS articles also appear in NewsAPI
- Different source IDs: `('tech_rss', url)` vs `('newsapi', url)`
- Layer 3 (content similarity) catches these as duplicates

### Why Tech RSS?

- No API key required
- More reliable than NewsAPI for specific outlets
- Faster updates (RSS is real-time, NewsAPI can lag)
- Supplements NewsAPI coverage

---

## Source 4: ArXiv

**File**: `sources/arxiv_papers.py`
**API**: http://export.arxiv.org/rss/
**Rate Limit**: None (public RSS feeds)
**API Key**: Not required

### What It Collects

**AI/ML research papers from categories:**
- `cs.AI` - Artificial Intelligence
- `cs.CL` - Computation and Language (NLP)
- `cs.CV` - Computer Vision
- `cs.LG` - Machine Learning
- `cs.NE` - Neural and Evolutionary Computing
- `stat.ML` - Machine Learning (Statistics)

### Collection Parameters

```bash
--arxiv-days 7    # Days back (default: 7)
--arxiv-limit 5   # Max papers total, not per category (default: 5)
```

### RSS Feed Structure

```xml
<rss version="2.0">
  <channel>
    <item>
      <title>Attention Is All You Need</title>
      <link>https://arxiv.org/abs/2511.17673</link>
      <description>We propose a new architecture...</description>
    </item>
  </channel>
</rss>
```

### Special Characteristics

**Daily-only RSS**: ArXiv RSS feeds only contain TODAY's papers
- Yesterday's papers don't reappear in today's feed
- Natural time-based deduplication
- Comment in code: `# RSS feeds only contain today's papers anyway`

**Cross-category duplicates**: Papers can be posted to multiple categories
- Layer 2 deduplication: In-memory `seen_urls` set within collection run
- Code: `sources/arxiv_papers.py:139-147`

### Deduplication

**source_id**: **NULL** (see docs/deduplication.md for explanation)
**Layer 2**: URL-based dedup within collection run
**Layer 3**: Content similarity catches any that slip through

### Event Type

All ArXiv papers tagged as `event_type = EventType.RESEARCH`:
- Displayed separately in "Research Highlights" section
- NOT included in sentiment analysis (informational, not market-moving)
- NOT filtered by significance score (all collected papers published)

### Why ArXiv?

- Technical signal for AI breakthroughs
- Early indicator of research trends
- Supplements news with academic developments
- Free and reliable RSS feeds

---

## Source 5: SEC EDGAR

**File**: `sources/sec_edgar.py`
**API**: https://www.sec.gov/cgi-bin/browse-edgar
**Rate Limit**: 10 requests/second
**API Key**: Not required (requires User-Agent header)

### What It Collects

**Material events from 8-K filings** for 10 AI companies:
- NVIDIA (NVDA)
- Microsoft (MSFT)
- Alphabet/Google (GOOGL)
- Meta (META)
- AMD (AMD)
- Intel (INTC)
- Amazon (AMZN)
- Tesla (TSLA)
- Oracle (ORCL)
- Broadcom (AVGO)

**8-K filings indicate:**
- Major acquisitions or divestitures
- Leadership changes (CEO, CFO, CTO)
- Material contracts
- Financial restatements
- Bankruptcy or receivership

### Collection Parameters

```bash
--sec-days 7  # Days back (default: 7)
```

### API Structure

```
GET https://www.sec.gov/cgi-bin/browse-edgar?
  action=getcompany
  &CIK=0001045810  # NVIDIA
  &type=8-K
  &dateb=20251125
  &count=10
```

Returns HTML page with filing links:
```html
<a href="/Archives/edgar/data/1045810/000104581025000123/filing.htm">
  8-K - Nov 25, 2025 - Material Event
</a>
```

### Required Header

```python
headers = {
    'User-Agent': 'AI-Pulse Intelligence (contact@example.com)'
}
```

**SEC requires User-Agent** to identify automated requests. Without it, requests are blocked.

### Deduplication

**source_id**: Filing URL
**UNIQUE constraint**: `('sec_edgar', 'https://www.sec.gov/...')` prevents re-collection

### Why SEC EDGAR?

- Official corporate disclosures (legally required)
- Material events that affect stock prices
- Early signal before press releases
- Free and reliable

---

## Source 6: GitHub Trending

**File**: `sources/github_trending.py`
**API**: https://api.github.com/search/repositories
**Rate Limit**: 60/hour unauthenticated, 5000/hour with token
**API Key**: Optional - `GITHUB_TOKEN` in `.env` for higher limits

### What It Collects

**Trending AI/ML repositories:**
- Keywords: "machine-learning", "deep-learning", "LLM", "GPT", "Claude", "AI", "neural-network"
- Minimum stars filter (default: 500)
- Recent activity (pushed within X days)

**Also collects:**
- New releases from tracked repos (OpenAI, Anthropic, Meta, etc.)
- Major version bumps (1.0 → 2.0)

### Collection Parameters

```bash
--github-days 7      # Days of recent activity (default: 7)
--github-stars 500   # Minimum stars (default: 500)
```

### API Structure

```
GET https://api.github.com/search/repositories?
  q=machine-learning+stars:>500+pushed:>2025-11-18
  &sort=stars
  &order=desc
  &per_page=10
```

Returns:
```json
{
  "items": [
    {
      "full_name": "openai/gpt-4",
      "html_url": "https://github.com/openai/gpt-4",
      "description": "Official GPT-4 implementation",
      "stargazers_count": 12500,
      "pushed_at": "2025-11-25T10:00:00Z"
    }
  ]
}
```

### Deduplication

**source_id**: Repository URL
**UNIQUE constraint**: `('github', 'https://github.com/openai/gpt-4')` prevents re-collection

### Rate Limit Management

**Unauthenticated**: 60 requests/hour (sufficient for daily runs)
**With token**: 5000 requests/hour (not needed unless expanding)

**Usage**: ~2-3 API calls per collection run

### Why GitHub?

- Developer community signal
- Open-source AI projects trend
- Early indicator for new tools/frameworks
- Release announcements often before news

---

## Source 7: Company IR

**File**: `sources/company_ir.py`
**API**: RSS feeds from company investor relations pages
**Rate Limit**: None (public RSS)
**API Key**: Not required

### What It Collects

**Press releases from:**
- NVIDIA: `https://nvidianews.nvidia.com/releases.xml`
- AMD: `https://ir.amd.com/news-events/press-releases/rss`

### Collection Parameters

```bash
--ir-days 7  # Days back (default: 7)
```

### RSS Structure

```xml
<rss version="2.0">
  <channel>
    <item>
      <title>NVIDIA Announces Q4 2025 Financial Results</title>
      <link>https://nvidianews.nvidia.com/...</link>
      <pubDate>Thu, 21 Nov 2025 16:00:00 EST</pubDate>
      <description>...</description>
    </item>
  </channel>
</rss>
```

### Deduplication

**source_id**: Press release URL
**UNIQUE constraint**: `('company_ir', 'https://nvidianews.nvidia.com/...')` prevents re-collection

### Why Company IR?

- Official first-party announcements
- Earnings reports, product launches
- Often ahead of news aggregators
- Reliable and structured

---

## Market Data Collection

**File**: `agents/market_collector.py`
**Separate workflow**: Runs at 9:30pm GMT Mon-Fri only

### Symbols Tracked

| Category | Symbols |
|----------|---------|
| **Indices** | ^IXIC (NASDAQ), ^GSPC (S&P 500) |
| **Stocks** | NVDA, MSFT, GOOGL, META, AMD, PLTR |
| **ETFs** | BOTZ (AI/Robotics), AIQ (AI Analytics) |
| **Crypto** | BTC-USD (Bitcoin) |

### Data Sources (Fallback Chain)

**Primary: Yahoo Finance (yfinance)**
- Fast batch download (all symbols at once)
- Free and unlimited under normal use
- Occasionally rate limited (resets in 1-24 hours)

**Fallback 1: Financial Modeling Prep (FMP)**
- API key: `FMP_API_KEY` in `.env`
- Used for stocks, ETFs, crypto
- Does NOT support indices on free tier

**Fallback 2: Alpha Vantage**
- API key: `ALPHA_VANTAGE_API_KEY` in `.env`
- 500 calls/day, 5 calls/minute
- Used for stocks and crypto
- Does NOT support indices on free tier
- Bitcoin uses special DIGITAL_CURRENCY_DAILY endpoint

**Fallback 3: Twelve Data**
- API key: `TWELVE_DATA_API_KEY` in `.env`
- 800 calls/day
- Last resort if others fail

### Split-Source Strategy

To avoid Yahoo rate limits:
```python
# Step 1: Yahoo Finance for indices only (2 symbols)
indices = yfinance.download(['^IXIC', '^GSPC'])

# Step 2: FMP API for stocks/ETFs/crypto (9 symbols)
for symbol in ['NVDA', 'MSFT', 'GOOGL', 'META', 'AMD', 'PLTR', 'BOTZ', 'AIQ', 'BTC-USD']:
    data = fetch_fmp_daily(symbol)
    if not data:
        data = fetch_alpha_vantage_daily(symbol)  # Fallback
```

**Reduces Yahoo load by 80%** (2 symbols instead of 11)

### Collection Command

```bash
# Collect yesterday's market data (automatic date calculation)
python3.9 agents/market_collector.py

# Specific date
python3.9 agents/market_collector.py --date 2025-11-24

# Backfill 7 days
python3.9 agents/market_collector.py --backfill 7
```

### Data Collected

For each symbol:
- **Date**: Trading day
- **Open, High, Low, Close** prices
- **Volume**: Shares/units traded
- **Change %**: `(close - previous_close) / previous_close * 100`

### Deduplication

**UNIQUE constraint**: `(date, symbol)` in `market_data` table
- Can't insert same symbol for same date twice
- Backfill operations are idempotent (safe to re-run)

### Why Split from News Collection?

- Market data available after 4pm ET (9pm GMT)
- News collection runs 6am + 1:30pm GMT
- Separate timing ensures data completeness
- Correlation calculated after both exist

---

## Collection Workflow

### Automated Schedule (GitHub Actions)

**Morning Collection (6am GMT):**
```bash
python3.9 agents/collector.py \
  --hn-limit 20 \
  --news-limit 50 \
  --sec-days 1 \
  --github-days 1 \
  --github-stars 500 \
  --ir-days 1 \
  --rss-days 1 \
  --rss-limit 10
# ArXiv uses defaults: --arxiv-days 7 --arxiv-limit 5

python3.9 agents/semantic_deduplicator.py --days 1
python3.9 agents/analyzer.py --limit 50
```

**Afternoon Collection (1:30pm GMT):**
```bash
# Same as morning (catches any new events since 6am)
python3.9 agents/collector.py ...
python3.9 agents/semantic_deduplicator.py --days 7
python3.9 agents/analyzer.py --limit 50
python3.9 publish_briefing.py --days 7 --min-score 40
```

**Market Data (9:30pm GMT, Mon-Fri only):**
```bash
python3.9 agents/market_collector.py
python3.9 publish_briefing.py --days 7 --min-score 40  # Update with market data
```

### Manual Collection

```bash
# Collect from all sources with defaults
python3.9 agents/collector.py

# Custom limits
python3.9 agents/collector.py \
  --hn-limit 20 \
  --news-limit 30 \
  --sec-days 7 \
  --github-days 7 \
  --github-stars 500 \
  --ir-days 7 \
  --rss-days 1 \
  --rss-limit 10 \
  --arxiv-days 7 \
  --arxiv-limit 5
```

---

## Deduplication During Collection

All sources go through **3-layer deduplication** during collection:

### Layer 1: Database UNIQUE Constraint
```python
try:
    db.execute("INSERT INTO events (...) VALUES (...)")
except sqlite3.IntegrityError:
    # Duplicate (source, source_id) - skip
    duplicates += 1
```

### Layer 2: Source-Level URL Tracking
```python
# ArXiv only - prevents cross-category duplicates
seen_urls = set()
for event in events:
    if event.source_url not in seen_urls:
        seen_urls.add(event.source_url)
        unique_events.append(event)
```

### Layer 3: Content Similarity
```python
# In collector.py before database save
events, content_dupes = deduplicate_events(events, similarity_threshold=0.75)
result = db.save_events(events)
```

**See**: [docs/deduplication.md](deduplication.md) for complete details

---

## Collection Stats Output

```
================================================================================
COLLECTING FROM HACKER NEWS
================================================================================
Fetching top 20 stories from HN API...
  ⚡ Removed 2 content duplicates

✓ Hacker News: 15 new, 5 URL duplicates, 2 content duplicates

================================================================================
COLLECTING FROM NEWSAPI
================================================================================
Searching NewsAPI for AI mentions...
  ⚡ Removed 4 content duplicates

✓ NewsAPI: 23 new, 8 URL duplicates, 4 content duplicates

================================================================================
COLLECTION COMPLETE
================================================================================
Total saved: 38 events
Total duplicates: 13 events (8 URL, 5 content)
```

**URL duplicates**: Already in database (Layer 1 caught them)
**Content duplicates**: Same story, different source (Layer 3 caught them)

High duplicate count = **deduplication working correctly**

---

## Error Handling

### NewsAPI Rate Limit

```python
try:
    response = requests.get(newsapi_url)
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if response.status_code == 429:
        print("⚠ NewsAPI rate limit hit (100/day) - skipping")
        return {'saved': 0, 'duplicates': 0}
```

**Impact**: Collection continues with other sources

### SEC EDGAR Access Denied

```python
headers = {'User-Agent': 'AI-Pulse/1.0'}
response = requests.get(sec_url, headers=headers)

if response.status_code == 403:
    print("⚠ SEC access denied - check User-Agent header")
```

**Fix**: Ensure User-Agent is set correctly

### GitHub Rate Limit

```python
response = requests.get(github_url)
if response.status_code == 403:
    rate_limit_reset = response.headers.get('X-RateLimit-Reset')
    print(f"⚠ GitHub rate limited - resets at {rate_limit_reset}")
```

**Fix**: Add `GITHUB_TOKEN` to `.env` for 5000/hour limit

### Market Data Failures

```python
# Try Yahoo first
data = yfinance.download(symbols)
if data.empty:
    # Fallback to FMP
    data = fetch_fmp_daily(symbol)
    if not data:
        # Fallback to Alpha Vantage
        data = fetch_alpha_vantage_daily(symbol)
```

**Impact**: Most symbols collected via fallback chain

---

## API Keys Setup

**Required:**
```bash
# In .env file
ANTHROPIC_API_KEY=sk-ant-...        # For analysis (required)
```

**Optional (improves coverage):**
```bash
NEWS_API_KEY=...                    # Free: 100 calls/day
FMP_API_KEY=...                     # Free: Market data primary
ALPHA_VANTAGE_API_KEY=...           # Free: 500 calls/day (market fallback)
TWELVE_DATA_API_KEY=...             # Free: 800 calls/day (last resort)
GITHUB_TOKEN=...                    # Optional: Raises rate limit to 5000/hour
```

---

## Troubleshooting

### "No events collected"

**Check:**
1. Internet connection
2. API keys in `.env` file (for NewsAPI)
3. Time window not too narrow (`--hn-limit`, `--news-limit`)

### "High duplicate count"

**This is normal** - indicates deduplication is working:
- URL duplicates = events already in database
- Content duplicates = same story from multiple sources

### "NewsAPI returns old articles"

**NewsAPI free tier limitation:**
- Only returns articles from last 30 days
- Sorted by relevance, not always by date
- Use `--news-days 1` to get most recent

### "ArXiv returns no papers"

**ArXiv RSS is daily-only:**
- Only returns TODAY's papers
- If run twice same day, second run finds 0 new (expected)
- Check RSS feed directly: http://export.arxiv.org/rss/cs.AI

### "Market data collection fails"

**Check fallback chain:**
1. Yahoo Finance rate limit? (Wait 1-24 hours or trigger GitHub Actions from different IP)
2. FMP API key set? (Required for stocks/ETFs)
3. Alpha Vantage API key set? (Fallback for stocks + crypto)
4. Indices fail on Alpha Vantage free tier (expected)

---

## Files Reference

**Core Collector:**
- `agents/collector.py` - Orchestrates all sources
- `agents/market_collector.py` - Market data only

**Source Integrations:**
- `sources/hackernews.py` - Hacker News API
- `sources/newsapi.py` - NewsAPI integration
- `sources/tech_rss.py` - Tech RSS feeds
- `sources/arxiv_papers.py` - ArXiv RSS
- `sources/sec_edgar.py` - SEC EDGAR filings
- `sources/github_trending.py` - GitHub API
- `sources/company_ir.py` - Company IR RSS

**Models:**
- `models/events.py` - Event data structure

**Storage:**
- `storage/db.py` - Database operations

---

## Summary

AI-Pulse collects from **7 diverse sources** to provide comprehensive AI sector coverage:

- **News**: NewsAPI, Tech RSS, Company IR (professional journalism + official announcements)
- **Community**: Hacker News (tech community pulse)
- **Research**: ArXiv (academic AI/ML papers)
- **Corporate**: SEC EDGAR (material events, legally required disclosures)
- **Developer**: GitHub (trending repos, releases)
- **Market**: Yahoo Finance, FMP, Alpha Vantage (stock prices, indices, crypto)

**Automated**: Runs twice daily (6am + 1:30pm GMT) + market data at 9:30pm GMT

**Deduplication**: 3 layers during collection prevent duplicate storage

**Fallbacks**: Multi-tier API strategy ensures data collection even when primary sources fail
