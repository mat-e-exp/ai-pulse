# AI-Pulse API Rate Limits and Constraints

## Overview

AI-Pulse uses 7 data sources with varying rate limits. Understanding these limits is critical to avoid breaking workflows.

**IMPORTANT**: Read this before running collector scripts locally.

---

## Data Source APIs

### News & Events APIs

| API | Rate Limit | Resets | Key Required | Cost |
|-----|------------|--------|--------------|------|
| **NewsAPI** | 100 calls/day | Midnight UTC | Yes | Free tier |
| **Hacker News** | Unlimited | - | No | Free |
| **Tech RSS Feeds** | Unlimited | - | No | Free |
| **ArXiv** | Unlimited | - | No | Free |
| **SEC EDGAR** | 10 calls/sec | - | No | Free |
| **GitHub** | 5000/hour | Hourly | Yes (token) | Free |
| **Company IR RSS** | Unlimited | - | No | Free |

**Notes**:
- NewsAPI: 100 calls/day shared across all collection runs
- GitHub: Requires personal access token, 5000 calls/hour
- SEC EDGAR: Rate limiting per IP (10/sec max)
- RSS feeds: No authentication, unlimited

### Market Data APIs

| API | Rate Limit | Resets | Symbols Supported | Cost |
|-----|------------|--------|-------------------|------|
| **Yahoo Finance** | ~100 calls/hour | 1-24 hours | All | Free |
| **Alpha Vantage** | 500/day, 5/min | Midnight UTC | Stocks, ETFs only | Free tier |
| **Twelve Data** | 800/day | Midnight UTC | All | Free tier (unused) |

**Fallback chain**: Yahoo → Alpha Vantage → Twelve Data → Direct Yahoo API

**Alpha Vantage limitations (free tier)**:
- ❌ **Cannot fetch indices**: ^IXIC (NASDAQ), ^GSPC (S&P 500)
- ✅ **Can fetch**: Individual stocks (NVDA, MSFT, etc.), ETFs

**Yahoo Finance quirks**:
- Rate limits vary by IP and usage patterns
- Sometimes 429 errors resolve in 1 hour, sometimes 24 hours
- GitHub Actions use different IP, may work when local doesn't

### Claude API (Anthropic)

| Model | Input | Output | Use Case | Monthly Cost |
|-------|-------|--------|----------|--------------|
| **Haiku** (current) | $0.25/MTok | $1.25/MTok | Analysis, dedup | ~$3/month |
| Sonnet | $3/MTok | $15/MTok | Future features | ~$120/month |
| Opus | $15/MTok | $75/MTok | Premium analysis | ~$600/month |

**Current usage** (Haiku):
- Analysis: ~$0.002 per event
- Semantic dedup: ~$0.002 per date
- 50 events/day = ~$3/month

---

## Rate Limit Handling

### Collection Strategy

**Twice daily collection** (6am + 1:30pm GMT):
- Splits API calls across 2 runs
- NewsAPI: 100 calls/day = 50 per run
- GitHub: 5000/hour easily covers needs
- Yahoo Finance: Minimal calls (1 per symbol)

### What to Do When Rate Limited

**NewsAPI (100/day exceeded)**:
- Wait until midnight UTC
- Or reduce `--news-limit` parameter
- Or disable NewsAPI temporarily (still have 6 other sources)

**Yahoo Finance (429 error)**:
- Wait 1-24 hours for reset
- Or trigger GitHub Actions (different IP may work)
- Or skip market data collection (predictions still work)

**Alpha Vantage (500/day exceeded)**:
- Wait until midnight UTC
- Or switch to Twelve Data
- Or rely on Yahoo Finance alone

**GitHub (5000/hour exceeded)**:
- Extremely rare with current usage
- Wait 1 hour for reset
- Or reduce `--github-days` parameter

---

## Cost Tracking

### Database: `api_costs` Table

```sql
CREATE TABLE api_costs (
    id INTEGER PRIMARY KEY,
    date TEXT,
    api_name TEXT,
    model TEXT,
    operation TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    created_at TEXT
);
```

### Commands

```bash
# View today's costs
python3.9 cost_tracking/tracker.py --today

# View cost breakdown by API
python3.9 cost_tracking/tracker.py --breakdown

# Set monthly budget alert
python3.9 cost_tracking/tracker.py --set-budget 50.0
```

---

## Rules for Local Testing

### ❌ NEVER Do This

1. **Don't run market_collector.py locally without asking**
   - Burns shared API rate limits
   - Can break evening workflow

2. **Don't run full collection multiple times per day**
   - NewsAPI only has 100 calls/day
   - Wastes Claude API credits

3. **Don't test with large limits**
   - Use `--limit 10` for testing
   - Full collection should only happen in scheduled workflows

### ✅ Safe Local Testing

```bash
# Test collector with small limits
python3.9 agents/collector.py --limit 10

# Test analyzer with small limits
python3.9 agents/analyzer.py --limit 5

# Test semantic deduplicator on single date
python3.9 agents/semantic_deduplicator.py --days 1

# View existing data (no API calls)
open index.html
```

---

## Collector Parameters

### agents/collector.py

```bash
python3.9 agents/collector.py \
  --hn-limit 20 \          # Hacker News stories (unlimited API)
  --news-limit 30 \        # NewsAPI articles (100/day total)
  --rss-limit 20 \         # Tech RSS feeds (unlimited)
  --arxiv-limit 10 \       # ArXiv papers (unlimited)
  --sec-days 7 \           # SEC filings lookback (unlimited)
  --github-days 7 \        # GitHub trending lookback (5000/hour)
  --github-stars 500 \     # Minimum stars for trending repos
  --ir-days 7              # Company IR lookback (unlimited)
```

**Total API calls per run**:
- NewsAPI: 30 calls (from --news-limit)
- GitHub: ~20-50 calls (depends on trending repos)
- Hacker News: ~20 calls
- Others: <10 calls each

**Safe for twice-daily collection**: ✅

---

## Data Source Details

### Active Sources ✅

1. **Hacker News API**
   - Endpoint: `https://hacker-news.firebaseio.com/v0/`
   - Rate limit: Unlimited
   - Key: Not required
   - Returns: Top/new stories with scores

2. **NewsAPI**
   - Endpoint: `https://newsapi.org/v2/everything`
   - Rate limit: 100/day
   - Key: Required (`NEWS_API_KEY`)
   - Query: AI-related keywords

3. **Tech RSS Feeds**
   - Sources: TechCrunch, VentureBeat, The Verge, Ars Technica, MIT Tech Review, Wired, AI News, Reuters (via Google News)
   - Rate limit: Unlimited
   - Key: Not required
   - Format: RSS/Atom XML

4. **ArXiv API**
   - Endpoint: `http://export.arxiv.org/api/query`
   - Rate limit: Unlimited (3 sec delay recommended)
   - Key: Not required
   - Categories: cs.AI, cs.LG, cs.CV, cs.CL

5. **SEC EDGAR**
   - Endpoint: `https://www.sec.gov/cgi-bin/browse-edgar`
   - Rate limit: 10 calls/sec
   - Key: Not required
   - Query: 8-K filings (material events)

6. **GitHub Trending**
   - Endpoint: `https://api.github.com/search/repositories`
   - Rate limit: 5000/hour (authenticated)
   - Key: Required (GitHub token)
   - Query: AI/ML repos by stars

7. **Company IR RSS**
   - Sources: NVIDIA, AMD press releases
   - Rate limit: Unlimited
   - Key: Not required
   - Format: RSS XML

### Disabled Sources ❌

- **Google News RSS**: Feed structure incompatible, returns no results
- **Bing News API**: Requires separate API key, not worth additional cost

---

## Future Sources (Planned)

- **Twitter/X API**: Basic tier, rate limits TBD
- **Reddit API**: Free tier, 60 calls/min
- **Perplexity API**: Research-focused queries

---

## Troubleshooting

**"NewsAPI rate limit exceeded"**:
```bash
# Check usage
sqlite3 ai_pulse.db "SELECT COUNT(*) FROM api_costs
                     WHERE api_name='NewsAPI'
                     AND date=date('now')"

# Solution: Wait until midnight UTC or reduce --news-limit
```

**"Yahoo Finance 429 error"**:
```bash
# Check if Alpha Vantage works
python3.9 agents/market_collector.py --symbol NVDA --source alphavantage

# Solution: Wait 1-24 hours or use GitHub Actions
```

**"Claude API rate limit"**:
```bash
# Check daily costs
python3.9 cost_tracking/tracker.py --today

# Solution: Reduce --limit parameters or wait
```

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Operational guide
- [data-collection.md](data-collection.md) - Collection pipeline details
- [architecture.md](architecture.md) - System architecture
