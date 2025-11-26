# AI-PULSE PROJECT

## What This Does
Real-time intelligence agent for the AI sector - tracks product launches, funding, technical breakthroughs, market sentiment, and competitive dynamics to provide actionable insights for AI investment decisions.

**Live site**: https://mat-e-exp.github.io/ai-pulse-briefings/

## Primary Goal: ACCURACY
**Accuracy is the highest priority** - above speed, cost, or features. The system must provide trustworthy data for investment decisions. This means:
- **No duplicate stories** inflating sentiment counts
- **Accurate sentiment distribution** - each unique story counted once
- **Reliable significance scores** - no re-analyzing the same event
- **Trustworthy percentages** - chart reflects reality, not data collection artifacts
- **Accurate prediction tracking** - predictions logged BEFORE market opens, outcomes AFTER market closes

Investment decisions depend on this data being correct.

### Data Protection Features

The system has multiple safety features to prevent accidental data corruption:

1. **Prediction Locking**: Once market opens (2:30pm GMT), predictions for that day are locked and cannot be updated
2. **Timestamp Preservation**: `first_logged_at` field preserves the original prediction time, even if regenerated
3. **Audit Trail**: `prediction_audit` table tracks every prediction update with reason and timestamp
4. **Duplicate Run Detection**: `workflow_runs` table warns if a workflow runs multiple times in one day
5. **Idempotent Operations**: Running scripts multiple times on same day overwrites (not duplicates) data

**These features protect against:**
- Accidentally logging predictions AFTER market opens (corrupts accuracy tracking)
- Losing evidence of when prediction was first made
- Undetected duplicate workflow runs
- Database corruption from human error

## CRITICAL: NEVER RERUN WORKFLOWS FOR TESTING

**The workflows are for production data collection, NOT testing.**

### FORBIDDEN Actions
❌ **NEVER suggest manually triggering workflows to "test" or "see output"**
❌ **NEVER rerun daily-collection.yml after it has already run that day**
❌ **NEVER rerun any workflow multiple times per day**

### Why This Matters
**Rerunning daily-collection.yml corrupts prediction accuracy data:**
1. First run at 1:30pm: Records prediction "bullish" (50 events)
2. Market opens at 2:30pm GMT, moves up 2%
3. Second run at 3pm: Overwrites with prediction "bullish" (65 events) - but this is AFTER market moved
4. Market closes at 9pm: Accuracy check uses the 3pm prediction
5. **Result**: Not measuring prediction accuracy, measuring reaction accuracy
6. **Data is corrupted and unreliable for investment decisions**

### How to Test Locally (Safe)

**READ-ONLY operations (completely safe):**
- `python3.9 agents/discord_morning.py` - generates Discord message preview (no DB writes)
- `open index.html` - view briefing HTML
- `cat discord_test.txt` - view Discord message text

**HTML-ONLY regeneration (safe for web changes):**
- `python3.9 regenerate_html.py --days 7 --min-score 40` - regenerate HTML from existing database
  - ✅ ONLY reads from database
  - ✅ ONLY writes HTML files
  - ❌ Does NOT collect data
  - ❌ Does NOT log predictions
  - ❌ Does NOT update database
  - **Use for**: Navigation changes, CSS updates, HTML template fixes

**⚠️ DANGEROUS: Full pipeline (database writes):**
- `python3.9 publish_briefing.py --days 7 --min-score 40` - **AVOID RUNNING MANUALLY**
  - Writes: `daily_sentiment` table, `predictions` table, `prediction_audit` table
  - Logs prediction based on current database state
  - **Problem**: If run before scheduled data collection, logs prediction with incomplete data
  - **Only use**: As part of scheduled workflows (1:30pm GMT)
  - **Never use**: For testing web changes or navigation updates

**What the safety features do:**
- `regenerate_html.py`: Completely safe anytime - no database writes
- `publish_briefing.py` after 2:30pm GMT: Prediction won't update (locked), but still logs to audit
- Duplicate workflow runs: Detected and warned, audit trail preserved

**Rule of thumb:**
- **Web/HTML changes?** → Use `regenerate_html.py`
- **Testing data collection?** → Use individual agent scripts
- **Full pipeline?** → Let scheduled workflows handle it

❌ DO NOT trigger GitHub Actions workflows unless:
- User explicitly says "run the workflow" or "trigger the workflow"
- It's the scheduled time for that workflow
- Making a code change that requires testing in production

### Which Workflow Should I Use?

**Decision tree:**
- **Need to deploy web changes (HTML/CSS/new pages)?** → Use `deploy-assets.yml` (safe, manual trigger)
- **Need to test data collection?** → Run scripts locally (see "How to Test Locally")
- **Need to update briefing with new data?** → Wait for scheduled `daily-collection.yml` (1:30pm GMT)
- **Everything else?** → Wait for scheduled workflows

**NEVER manually trigger:**
- `morning-collection.yml` - Scheduled for 6am GMT only
- `daily-collection.yml` - Scheduled for 1:30pm GMT only (corrupts prediction data if run multiple times)
- `market-close.yml` - Scheduled for 9:30pm GMT only

### Workflow Run Schedule (Automated)
- **6am GMT**: morning-collection.yml (collect overnight news)
- **1:30pm GMT**: daily-collection.yml (publish briefing + log prediction)
- **9:30pm GMT Mon-Fri**: market-close.yml (collect market data + calculate accuracy)

**Each workflow should run ONCE per day at its scheduled time.**

## Architecture

See [docs/diagrams.md](docs/diagrams.md) for visual diagrams including:
- Architecture Component Diagram
- Daily User Workflow
- Data Change Process
- UI Change Process (Issue Agent)
- Repository Structure

## Current Status (2025-11-24)

### Automated Pipeline ✅
- **Morning collection**: 6am GMT - Collect + Analyze + Discord top 10
- **Afternoon publish**: 1:30pm GMT - Collect delta + Publish HTML + Discord
- **Market data**: 9:30pm GMT Mon-Fri via GitHub Actions
- **Publishing**: Automatic to GitHub Pages
- **Discord notifications**: All workflow completions

### What Runs Automatically

| Time (GMT) | Workflow | Actions |
|------------|----------|---------|
| 6am | morning-collection.yml | Collect → Analyze → Discord top 10 stories |
| 1:30pm | daily-collection.yml | Collect delta → Analyze → Publish HTML → Discord |
| 9:30pm Mon-Fri | market-close.yml | Market data → Update correlation → Discord |

### Manual Workflows (When Needed)

| Workflow | Trigger | Purpose | Safe to Run |
|----------|---------|---------|-------------|
| **deploy-assets.yml** | Manual only | Deploy HTML/CSS/style changes without data collection | ✅ YES - Does not corrupt prediction data |

**When to use deploy-assets.yml:**
- After making UI/style changes (CSS, HTML layout, new pages)
- After updating navigation or static content
- When you need web changes live immediately
- **Does NOT**: Collect data, analyze events, log predictions

**How to trigger:**
1. Push code changes to private repo (including regenerated HTML files)
2. Go to GitHub Actions → "Deploy Assets to Public Site"
3. Click "Run workflow" → Select branch "main" → Run
4. Takes ~5 minutes, deploys to public site

**Important:** Always regenerate HTML locally first with `python3.9 publish_briefing.py --days 7 --min-score 40` before deploying.

### Repository Structure
```
Private: mat-e-exp/ai-pulse
├── All code, config, database
├── GitHub Actions workflows
└── Pushes HTML to public repo

Public: mat-e-exp/ai-pulse-briefings
├── HTML briefings only
└── Served via GitHub Pages
```

### CRITICAL: Local/Remote Sync Protocol

**Problem**: Automated workflows run on GitHub (6am, 1:30pm GMT) and update the database + regenerate briefings. This creates conflicts when working locally.

**MANDATORY WORKFLOW when making local changes:**

1. **ALWAYS pull first**: `git pull` before starting any work
2. **Make your changes**: Edit code, styles, HTML, CSS, etc.
3. **Regenerate briefing**: Run `python3.9 publish_briefing.py --days 7 --min-score 40`
4. **Commit and push**: Push all changes together
5. **Deploy to public site** (choose one):
   - **Option A (Wait)**: Next scheduled daily-collection.yml run (1:30pm GMT) will deploy automatically
   - **Option B (Immediate)**: Manually trigger deploy-assets.yml workflow in GitHub Actions

**Why this matters:**
- Automated workflows update `ai_pulse.db`, `index.html`, `briefings/*.html` twice daily
- If you push without pulling first, you'll get merge conflicts
- If you don't regenerate briefings, your UI changes won't appear on the live site

**Files that change automatically:**
- `ai_pulse.db` (database grows with each collection)
- `index.html` (regenerated with latest briefing)
- `briefings/YYYY-MM-DD.html` (regenerated daily)
- `archive.html` (updated with new briefing links)

**NEVER push without:**
1. Pulling latest changes first
2. Regenerating briefings with your changes
3. Verifying the output locally

### What's NOT Built Yet
See `AGENTIC_ROADMAP.md` for the full vision:
- Issue-driven automation (agent implements from GitHub Issues)
- Self-improvement loop (agent improves its own accuracy)
- Outcome tracking and accuracy measurement

## Project Vision

### Core Capabilities (Planned)
1. **Product Launch Tracker**: Monitor new AI models, features, benchmarks
2. **Funding Intelligence**: Track VC rounds, valuations, strategic investments
3. **Technical Signals**: ArXiv papers, GitHub activity, benchmark leaderboards
4. **Market Sentiment**: News analysis, developer adoption, narrative shifts
5. **Competitive Analysis**: Market share changes, strategic positioning
6. **Daily Intelligence Briefing**: Automated morning reports

### Why Agentic
This requires autonomous decision-making:
- **Significance scoring**: Is this news material or noise?
- **Multi-source reasoning**: Connect dots across news, funding, technical developments
- **Historical context**: Compare current events to past patterns
- **Narrative detection**: Track sentiment shifts over time
- **Impact analysis**: Who wins/loses from each development?

## Target Sectors
- **Public Companies**: NVDA, MSFT, GOOGL, META, AMZN, AMD, ARM, TSMC, ASML
- **Private Leaders**: OpenAI, Anthropic, Mistral, Cohere, xAI, Perplexity
- **Infrastructure**: Cloud providers, chip makers, data centers
- **Applications**: Enterprise AI, developer tools, consumer AI

## Architecture (Planned)

```
ai-pulse/
├── agents/              # Agent logic
│   ├── collector.py    # Data collection orchestration
│   ├── analyzer.py     # Significance scoring, reasoning
│   └── reporter.py     # Briefing generation
├── sources/            # Data source integrations
│   ├── news.py         # News APIs (NewsAPI, etc)
│   ├── social.py       # Twitter/X, Hacker News, Reddit
│   ├── technical.py    # ArXiv, GitHub, HuggingFace
│   └── market.py       # Stock prices, options flow
├── models/             # Data models
│   ├── events.py       # Event types (launch, funding, etc)
│   └── entities.py     # Companies, products, people
├── storage/            # Data persistence
│   ├── db.py           # Database operations
│   └── cache.py        # Caching layer
├── analysis/           # Analysis logic
│   ├── significance.py # Event importance scoring
│   ├── narrative.py    # Sentiment tracking over time
│   └── impact.py       # Competitive impact analysis
├── web/                # Web interface (future)
│   └── dashboard.html
├── .env.example        # Environment variables template
├── requirements.txt    # Python dependencies
└── README.md           # User documentation
```

## Data Sources

**Active ✅**:
- Hacker News API (unlimited, free)
- NewsAPI (100 calls/day free)
- SEC EDGAR (unlimited, free) - 8-K filings, material events
- GitHub API (5000 calls/hour free) - trending AI repos, releases
- Company IR RSS (unlimited, free) - NVIDIA, AMD press releases
- Yahoo Finance via yfinance (free) - Market data, primary source
- Alpha Vantage (500 calls/day free) - Market data, fallback when Yahoo rate limited
- Tech RSS Feeds (unlimited, free) - TechCrunch, VentureBeat, The Verge, Ars Technica, MIT Tech Review, Wired, AI News

**Disabled (2025-11-11)**:
- Google News RSS - Feed structure incompatible, returns no results
- Bing News API - Requires separate API key, not worth additional cost

**Future Sources**:
- Twitter/X API (basic tier)
- Reddit API (free tier)
- ArXiv API (unlimited, free)

## Technology Stack

**Core**:
- Python 3.9+
- Claude API (via Anthropic SDK) for reasoning
- SQLite for storage (start simple)

**Libraries**:
- `anthropic` - LLM reasoning
- `requests` - HTTP requests
- `beautifulsoup4` - Web scraping if needed
- `pandas` - Data analysis
- `yfinance` - Market data
- `python-dateutil` - Date handling

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Required for market data correlation
ALPHA_VANTAGE_API_KEY=...  # Get free key at https://www.alphavantage.co/support/#api-key
                           # Used as fallback when Yahoo Finance is rate limited

# Optional (for expanded features)
NEWS_API_KEY=...
TWITTER_API_KEY=...
```

### Discord Webhooks (GitHub Secrets)

Two webhooks for different audiences:

| Secret | Audience | Used For |
|--------|----------|----------|
| `DISCORD_WEBHOOK` | Users | Page updates, daily briefings, production deploys |
| `DISCORD_WEBHOOK_APPROVALS` | Devs | Code changes, PR reviews, preview ready, approvals |

**Workflow usage:**
- `daily-collection.yml` → `DISCORD_WEBHOOK` (daily briefing published)
- `issue-handler.yml` → `DISCORD_WEBHOOK_APPROVALS` (preview ready for review)
- `promote-prod.yml` → Both (devs: code deployed, users: page updated)
- `reject-change.yml` → `DISCORD_WEBHOOK_APPROVALS` (change rejected)

## API Rate Limits and Constraints

**IMPORTANT: Read this before running any collector scripts locally.**

### Market Data APIs (market_collector.py)

| API | Rate Limit | Resets | What Works | What Doesn't |
|-----|------------|--------|------------|--------------|
| Yahoo Finance | ~100 calls/hour | 1-24 hours | All symbols | - |
| Alpha Vantage | 500/day, 5/min | Midnight UTC | Stocks, ETFs | **Indices (free tier)** |
| Twelve Data | 800/day | Midnight UTC | All symbols | - |

**Fallback order:** Yahoo → Alpha Vantage → Twelve Data → Direct Yahoo API

### News/Event APIs (collector.py)

| API | Rate Limit | Resets | Notes |
|-----|------------|--------|-------|
| NewsAPI | 100 calls/day | Midnight UTC | Free tier |
| HackerNews | Unlimited | - | No key needed |
| SEC EDGAR | 10 calls/sec | - | No key needed |
| GitHub | 5000/hour | Hourly | With token |

### Rules for Claude Code

1. **NEVER run market_collector.py locally** without asking user first
   - Burns shared API rate limits
   - Prefer triggering GitHub Actions (different IP for Yahoo)

2. **If Yahoo is rate limited:**
   - Wait 1-24 hours for reset
   - GitHub Actions workflow may work (different IP)
   - Alpha Vantage fallback won't get indices

3. **Alpha Vantage free tier limitations:**
   - Cannot fetch ^IXIC (NASDAQ) or ^GSPC (S&P 500)
   - Only stocks and ETFs work

4. **Before any API call, ask:**
   - Is this necessary?
   - Can we use cached/existing data?
   - Should the user trigger a workflow instead?

## Commands

```bash
# RECOMMENDED DAILY WORKFLOW (accurate sentiment, cost-optimized with Haiku)
python3.9 agents/collector.py --hn-limit 20 --news-limit 30 --sec-days 7 --github-days 7 --github-stars 500 --ir-days 7
python3.9 agents/semantic_deduplicator.py --days 7  # Claude-powered semantic dedup
python3.9 agents/analyzer.py --limit 50  # Haiku beta (~$0.002/event, ~$3/month)
python3.9 publish_briefing.py --days 1 --min-score 40

# ONE-TIME SETUP: Retroactive deduplication for existing data
python3.9 retroactive_dedup.py --days 30 --threshold 0.75  # String-based
python3.9 retroactive_semantic_dedup.py --days 30  # Semantic (Claude-powered)

# Show top events by significance
python3.9 agents/analyzer.py --top --limit 10

# Cost tracking
python3.9 cost_tracking/tracker.py --today
python3.9 cost_tracking/tracker.py --breakdown
python3.9 cost_tracking/tracker.py --set-budget 50.0
```

## Autonomous Capabilities (Phase 2)

**Agent Decides Automatically** ✅:
- Which events are significant (0-100 scoring)
- Why events matter (reasoning)
- Who is affected (winners/losers)
- Investment implications (material/marginal/noise)
- Historical context and comparisons
- Sentiment analysis (positive/negative/neutral/mixed)

**Requires Human Input**:
- Trading decisions (agent provides analysis only)
- Priority adjustments (which topics to emphasize)
- Final investment thesis validation

## Development Phases

### Phase 1: Basic Collector ✅ COMPLETE
- ✅ Project structure
- ✅ Hacker News integration
- ✅ NewsAPI integration
- ✅ SEC EDGAR integration (8-K filings)
- ✅ GitHub trending integration (AI repos, releases)
- ✅ Company IR RSS integration (NVIDIA, AMD)
- ✅ SQLite storage with deduplication
- ✅ Simple daily summaries
- ✅ Cost tracking database

### Phase 2: Intelligence Layer ✅ COMPLETE
- ✅ Claude API integration
- ✅ Significance scoring (0-100)
- ✅ "Why does this matter?" reasoning
- ✅ Competitive impact analysis
- ✅ Investment implications assessment
- ✅ Intelligent briefing generation
- ✅ Cost tracking with budget management

### Phase 2.5: Web Publishing & Deduplication ✅ COMPLETE (2025-11-12)
- ✅ Static HTML briefing generation with Chart.js sentiment visualization
- ✅ Percentage-based sentiment tracking (0-100% instead of raw counts)
- ✅ 30-day sentiment trend chart with event count tooltips
- ✅ Content-based deduplication at collection time (75% title similarity)
- ✅ Retroactive deduplication script for historical data
- ✅ Automatic publishing workflow (briefings/ + index.html + archive.html)
- ✅ Git-based hosting (push to GitHub, view on GitHub Pages)

### Phase 2.6: Semantic Deduplication ✅ COMPLETE (2025-11-12)
- ✅ Claude-powered semantic dedup using Haiku (cheap, fast)
- ✅ Identifies duplicates string matching misses (e.g., "sells Nvidia" vs "profits double")
- ✅ Runs before analysis to prevent waste and ensure accuracy
- ✅ Tested on 2025-11-11: Found 4 semantic duplicates (SoftBank group, Intel CTO group)
- ✅ Sentiment recalculated: 61 events → 57 unique events
- ✅ Trustworthy sentiment percentages for investment decisions

### Phase 2.7: Haiku Beta Mode ✅ COMPLETE (2025-11-22)
- ✅ All analysis uses Haiku (~$0.002/event)
- ✅ ~$3/month for 50 events/day (98% cheaper than Sonnet)
- ✅ Good quality for basic scoring and sentiment
- ✅ Upgrade path to Sonnet/Opus when needed

**Cost Comparison**:
| Model | Per Event | 50 events/day | Monthly |
|-------|-----------|---------------|---------|
| **Haiku (current)** | ~$0.002 | $0.10/day | **~$3/month** |
| Sonnet | ~$0.08 | $4.00/day | ~$120/month |
| Opus | ~$0.40 | $20.00/day | ~$600/month |

### Phase 3: Narrative Tracking (AFTER PHASE 2.6)
- Track sentiment over time
- Detect narrative shifts
- Historical pattern matching
- Cross-event reasoning

### Phase 4: Full Autonomy
- Real-time monitoring
- Automated alert prioritization
- Multi-step investigation workflows
- Proactive deep-dives

## How It Works

### Predictive Model - Overnight News → Same-Day Market

**Goal**: Use overnight AI sector sentiment to predict same-day US market performance.

**Automated Workflow (GMT)**:
1. **9pm (previous day)**: US market closes
2. **6am**: Morning collection + analysis → Discord top 10 stories
3. **1:30pm**: Full briefing published (before US market opens at 2:30pm)
4. **2:30pm**: US market opens
5. **9pm**: US market closes
6. **9:30pm**: Market data collected → Briefing updated with correlation

**Question answered**: "Does overnight AI news sentiment predict same-day market behavior?"

### Manual Workflow (If Needed)

All steps are automated via GitHub Actions. Manual commands for testing:

```bash
# Collect from all sources
python3.9 agents/collector.py --hn-limit 20 --news-limit 30

# Deduplicate
python3.9 agents/semantic_deduplicator.py --days 1

# Analyze
python3.9 agents/analyzer.py --limit 50

# Publish
python3.9 publish_briefing.py --days 7 --min-score 0
```

**Note**: Avoid running `market_collector.py` locally - burns shared API rate limits.

### Web Publishing System

**File Structure**:
```
ai-pulse/
├── index.html              # Latest briefing (copied from briefings/)
├── archive.html            # List of all past briefings
├── style.css               # Dark theme with pastel accents
├── briefings/
│   ├── 2025-11-11.html    # Dated briefing (href="../style.css")
│   └── 2025-11-12.html    # Dated briefing
└── publish_briefing.py    # Orchestrates generation + path fixing
```

**Publishing Flow**:
1. `html_reporter.py` generates briefing HTML with `href="../style.css"` (for briefings/ subdirectory)
2. Saves to `briefings/YYYY-MM-DD.html`
3. Copies to `index.html` and fixes paths: `../style.css` → `style.css`
4. Updates `archive.html` with list of all briefings
5. Saves daily sentiment aggregate to database

**Path Handling**:
- `briefings/*.html` uses `href="../style.css"` (relative to subdirectory)
- `index.html` uses `href="style.css"` (relative to root)
- `publish_briefing.py` automatically handles path translation

### Sentiment Tracking System

**Percentage-Based Chart**:
- Displays sentiment as % distribution (0-100%) instead of raw counts
- Makes comparison across days meaningful regardless of event volume
- Example: 35 events on Day 1 vs 82 events on Day 2 - percentages show true sentiment shift

**Chart Features**:
- 30-day x-axis (shows gaps for days without data)
- Y-axis labeled with % symbols (0%, 25%, 50%, 75%, 100%)
- Hover tooltips show: "2025-11-12 (Total: 82 events)" + "Positive: 19.1%"
- Chart.js line chart with 4 colored lines (positive/negative/neutral/mixed)

**Data Flow**:
1. Each event analyzed by Claude gets sentiment label (positive/negative/neutral/mixed)
2. Daily aggregation counts sentiments for non-duplicate events
3. HTML generator calculates percentages: `(count / total) * 100`
4. Chart displays percentages with event count in tooltip

### Deduplication System

**See [docs/deduplication.md](docs/deduplication.md) for complete technical documentation.**

**Critical for Accuracy**: Duplicates skew sentiment counts and waste analysis costs.

**Problem**: Same story reported by multiple sources
- Example: "SoftBank sells Nvidia stake" appeared 6+ times on 2025-11-11
- Each duplicate analyzed separately by Claude
- Each gets sentiment score (e.g., all "mixed")
- Inflates that sentiment in daily count: "mixed: 38%" instead of true "mixed: 20%"
- **Result**: Untrustworthy sentiment percentages

**5-Layer Deduplication Architecture:**

**Layer 1: Database UNIQUE Constraint**
- Location: `storage/db.py` - SQLite schema
- Constraint: `UNIQUE(source, source_id)` prevents same source+ID twice
- Blocks: HN item IDs, NewsAPI URLs, RSS URLs, SEC filings, GitHub repos
- **ArXiv gap**: `source_id = NULL` (constraint allows multiple NULLs)
- **Why safe**: ArXiv RSS only returns today's papers + Layer 2-3 backup

**Layer 2: Source-Level URL Tracking**
- Location: `sources/arxiv_papers.py:139-147`
- ArXiv papers can appear in multiple categories (cs.AI, cs.LG, cs.CV)
- In-memory `seen_urls` set deduplicates within single collection run
- Prevents cross-category duplicates

**Layer 3: Content Similarity (75% threshold)**
- Location: `agents/collector.py:93-160` - `deduplicate_events()`
- Runs after fetching from each source, before database storage
- Groups events by published date
- Compares titles using `SequenceMatcher` similarity (0-1 score)
- Marks as duplicate if:
  - Title similarity ≥ 75%, OR
  - Title similarity ≥ 60% AND same companies mentioned
- Keeps first occurrence, discards duplicates
- **Limitation**: Misses semantic duplicates with different wording

**Layer 4: Semantic Duplicate Detection (Claude-powered)**
- Location: `agents/semantic_deduplicator.py`
- After collection, before analysis (in workflows)
- Sends titles to Claude Haiku: "Which report the same event?"
- Marks `is_semantic_duplicate = 1` in database
- Catches semantic duplicates string matching misses
- Cost: ~$0.002 per date with Haiku
- **Results on 2025-11-11**:
  - Found 2 duplicate groups (4 events total)
  - SoftBank: "sells Nvidia" + "profits double" + "unloads stake" + "rides AI wave"
  - Intel CTO: "Sachin Katti departs" + "Sachin Katti joins"
  - Before: 61 events → After: 57 unique events

**Layer 5: Publishing Filter**
- Location: `agents/html_reporter.py:70-71, 134-140`
- Filters: `WHERE is_duplicate = 0 AND is_semantic_duplicate = 0`
- Ensures duplicates never shown even if in database
- Sentiment counts only include non-duplicates

**Daily Publishing Flow (No Re-Duplication):**

When `publish_briefing.py --days 7` runs daily:
1. **Reads from database** (doesn't re-collect events)
2. **Shows last 7 days** (rolling window: Nov 18-24 → Nov 19-25 → Nov 20-26)
3. **Old events stay in database** (never re-collected due to UNIQUE constraint)
4. **New events protected** (Layer 1-4 prevent duplicates during collection)
5. **Result**: No duplication across daily publishes

**Retroactive Cleanup (Historical Data):**
- `retroactive_dedup.py` - String-based (75% similarity)
- `retroactive_semantic_dedup.py` - Semantic (Claude-powered)
- Run once after implementing deduplication (2025-11-12)
- Marks historical duplicates with flags
- Recalculates `daily_sentiment` table

### Market Data Collection with Fallback

**Two-Tier Strategy** (2025-11-13):

**Primary: Yahoo Finance (yfinance)**
- Fast batch download (all 10 symbols at once)
- Free and unlimited under normal use
- Occasionally rate limited after heavy use (backfills, multiple runs)
- Rate limit resets after ~24 hours

**Fallback: Alpha Vantage**
- Activates automatically when Yahoo returns "Too Many Requests"
- Free tier: 500 calls/day, 5 calls/minute
- Fetches symbols sequentially with rate limiting (waits 60 seconds every 5 calls)
- Takes ~2 minutes to collect all 10 symbols
- Requires `ALPHA_VANTAGE_API_KEY` in `.env`
- **Limitation**: Free tier doesn't support index symbols (^IXIC, ^GSPC) - only stocks/ETFs work

**How Fallback Works**:
1. `market_collector.py` tries Yahoo Finance batch download first
2. If Yahoo raises rate limit error, switches to Alpha Vantage
3. Alpha Vantage fetches each symbol individually with rate limiting
4. Data stored in same database schema regardless of source
5. Next run will try Yahoo again (may have reset)

**Symbol Mapping**:
- Yahoo uses `^IXIC` for NASDAQ, Alpha Vantage uses `IXIC`
- Yahoo uses `^GSPC` for S&P 500, Alpha Vantage uses `INX`
- Code handles translation automatically

**Usage**:
```bash
# Collect yesterday's data (tries Yahoo, falls back to Alpha Vantage if rate limited)
python3.9 agents/market_collector.py

# Collect specific date
python3.9 agents/market_collector.py --date 2025-11-12

# Backfill 7 days (may trigger Yahoo rate limit, will use Alpha Vantage)
python3.9 agents/market_collector.py --backfill 7
```

### Database Schema

**Key Tables**:
```sql
events (
  id, source, source_url, title, content, summary,
  event_type, companies, published_at, collected_at,
  significance_score, sentiment, implications,
  affected_parties, investment_relevance, key_context,
  is_duplicate  -- Added 2025-11-12
)

daily_sentiment (
  date, positive, negative, neutral, mixed,
  total_analyzed, created_at
)
```

**Deduplication Fields**:
- `is_duplicate`: 0 = unique, 1 = string duplicate (75% title similarity)
- `is_semantic_duplicate`: 0 = unique, 1 = semantic duplicate (Claude-identified)
- Reports query: `WHERE (is_duplicate IS NULL OR is_duplicate = 0) AND (is_semantic_duplicate IS NULL OR is_semantic_duplicate = 0)`

**Safety Tables** (added 2025-11-26):
```sql
predictions (
  date PRIMARY KEY,
  sentiment_positive, sentiment_negative, sentiment_neutral, sentiment_mixed,
  total_events, prediction, confidence,
  top_events_summary,
  created_at,          -- Last update timestamp
  first_logged_at,     -- Original prediction timestamp (preserved)
  is_locked            -- 1 = locked after market open, 0 = can update
)

prediction_audit (
  id, date,
  sentiment_positive, sentiment_negative, sentiment_neutral, sentiment_mixed,
  total_events, prediction, confidence,
  action,              -- 'INSERT', 'UPDATE', 'BLOCKED'
  reason,              -- Why this action occurred
  created_at,
  workflow_run_id      -- Links to workflow_runs table
)

workflow_runs (
  id, workflow_name,
  run_date,
  started_at, completed_at,
  status,              -- 'started', 'completed', 'failed'
  run_count_today,     -- Increments for each run on same day
  is_duplicate_run,    -- 1 = duplicate run detected
  notes
)
```

### Safety Utilities

**Location**: `storage/db_safety.py`

**Key Functions**:
- `PredictionSafety.is_market_open(check_time)` - Check if US market is currently open (2:30pm - 9pm GMT)
- `PredictionSafety.should_lock_prediction(date, check_time)` - Determine if prediction should be locked
- `save_prediction_safe(db, date, sentiment_data, prediction, confidence, top_events_summary, workflow_run_id)` - Save prediction with safety checks
- `log_workflow_run(db, workflow_name, run_date, status, notes)` - Log workflow start and detect duplicates
- `complete_workflow_run(db, workflow_run_id, status, notes)` - Mark workflow as completed

**Wrapper Script**: `workflow_safety.py`
```bash
# Start workflow (returns workflow_run_id)
python3.9 workflow_safety.py start <workflow-name>

# Complete workflow
python3.9 workflow_safety.py complete <workflow-run-id> [status] [notes]
```

**Testing**: `test_safety.py`
```bash
# Run all safety feature tests
python3.9 test_safety.py

# Tests:
# - Market hours detection
# - Prediction locking logic
# - Save/update predictions
# - Audit trail logging
```

**Migration**: `migrations/add_safety_features.py`
- Adds safety columns to predictions table
- Creates prediction_audit and workflow_runs tables
- Backfills first_logged_at for existing predictions
- Run once: `python3.9 migrations/add_safety_features.py`

### Publishing Scripts

**`regenerate_html.py`** - Safe HTML regeneration (READ-ONLY)
```bash
python3.9 regenerate_html.py --days 7 --min-score 40
```
- ✅ Safe to run anytime
- ✅ Only reads from database
- ✅ Only writes HTML files
- ❌ Does NOT collect data
- ❌ Does NOT log predictions
- **Use for**: Web changes, navigation updates, CSS fixes

**`publish_briefing.py`** - Full pipeline (DATABASE WRITES)
```bash
python3.9 publish_briefing.py --days 7 --min-score 40
```
- ⚠️ **AVOID RUNNING MANUALLY**
- Writes to database: `daily_sentiment`, `predictions`, `prediction_audit`
- Logs prediction based on current database state
- **Risk**: If run before data collection, logs prediction with incomplete data
- **Only use**: As part of scheduled workflows (called by daily-collection.yml at 1:30pm GMT)
- **Never use**: For testing or web changes

**When to use which:**
- **Changing navigation/CSS/layout?** → `regenerate_html.py` then commit + deploy-assets.yml
- **Testing data collection?** → Run individual agent scripts, not publishing scripts
- **Full daily pipeline?** → Let scheduled workflows handle it automatically

## GitHub Pages Hosting

### Split Repository Architecture (Privacy)

**Private Repository**: `mat-e-exp/ai-pulse`
- Contains all code, config, prompts, database
- GitHub Actions run here
- Not publicly visible

**Public Repository**: `mat-e-exp/ai-pulse-briefings`
- Contains HTML briefings only
- Served via GitHub Pages
- **Live URL**: `https://mat-e-exp.github.io/ai-pulse-briefings/`

### How Publishing Works (Automated)

GitHub Actions automatically:
1. Runs collection and analysis in private repo
2. Generates HTML briefings
3. Pushes briefings to public repo via deploy key
4. GitHub Pages serves the public repo

**No manual publishing required** - the daily workflow handles everything.

### Manual Publishing (If Needed)

```bash
# Generate briefing locally
python3.9 publish_briefing.py --days 7 --min-score 0

# Commit to private repo
git add briefings/*.html index.html archive.html ai_pulse.db
git commit -m "Manual briefing"
git push

# The workflow will push to public repo on next run,
# or trigger the workflow manually in GitHub Actions
```

### Making Changes

Code changes go to the **private** repo only:
```bash
git add [changed-files]
git commit -m "Description"
git push
# Next scheduled run uses updated code
```

## Git Commit Security - CRITICAL

**NEVER commit files containing secrets or credentials:**
- NEVER include `.env` files in `git add` commands
- NEVER commit files with API keys (ANTHROPIC_API_KEY, NEWS_API_KEY, ALPHA_VANTAGE_API_KEY)
- NEVER use `git add .` - always specify files explicitly
- ALWAYS verify .gitignore is protecting sensitive files
- Before any git commit, verify you are NOT adding:
  - .env or *.env files
  - ai_pulse.db (database with collected data)
  - config files with credentials
  - Any file containing API keys or tokens
- If uncertain about a file, ASK the user before committing it

**Safe files to commit:**
- Python source code (*.py)
- HTML/CSS/JS files (briefings/*.html, index.html, style.css)
- Documentation (*.md, README)
- Configuration templates (.env.example - without actual keys)

## Related Projects
- None (standalone project)

## Troubleshooting

### Web Page Has No Styling
**Problem**: index.html displays without CSS
**Cause**: Stylesheet path is incorrect (likely `href="../style.css"` instead of `href="style.css"`)
**Fix**: Always use `publish_briefing.py` instead of `html_reporter.py` directly. The publish script fixes paths automatically.

### Duplicate Events in Briefing
**Problem**: Same story appears multiple times
**Cause**: Duplicates exist in database from before deduplication was implemented
**Fix**: Run `python3.9 retroactive_dedup.py --days 30` to mark historical duplicates

### Sentiment Chart Shows Raw Counts Instead of Percentages
**Problem**: Chart y-axis shows numbers like 28, 23 instead of percentages
**Cause**: Old version of HTML reporter
**Fix**: Regenerate with `python3.9 publish_briefing.py` - chart should show 0-100% scale

### Missing Event Count in Chart Tooltip
**Problem**: Hovering over chart doesn't show "Total: X events"
**Cause**: Chart data doesn't include totals array
**Fix**: Ensure using latest `html_reporter.py` with `totals` in chart data

### GitHub Pages Not Updating
**Problem**: Changes pushed but site shows old content
**Solutions**:
1. Wait 2-5 minutes for GitHub Pages rebuild
2. Check repository Settings → Pages shows green checkmark
3. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)
4. Check Pages URL is correct: `https://mat-e-exp.github.io/ai-pulse/`

### Collector Shows Many Duplicates
**Problem**: `python3.9 agents/collector.py` reports high duplicate count
**This is normal**: Shows both URL duplicates (already in DB) and content duplicates (same story, different URL)

## Key Files Reference

**Core Scripts**:
- `agents/collector.py` - Fetch events from sources, string deduplication
- `agents/semantic_deduplicator.py` - Claude-powered semantic deduplication
- `agents/analyzer.py` - Analyze events with Claude API (skips duplicates)
- `agents/html_reporter.py` - Generate HTML briefings
- `publish_briefing.py` - Orchestrate publishing workflow
- `retroactive_dedup.py` - Mark historical string duplicates
- `retroactive_semantic_dedup.py` - Mark historical semantic duplicates

**Data Files**:
- `ai_pulse.db` - SQLite database with events and sentiment history
- `briefings/YYYY-MM-DD.html` - Dated briefings (href="../style.css")
- `index.html` - Latest briefing (href="style.css")
- `archive.html` - List of all briefings
- `style.css` - Dark theme styling

**Models**:
- `models/events.py` - Event data structure with `is_duplicate` field
- `storage/db.py` - Database operations
- `analysis/significance.py` - Claude API integration

## Notes
- This is a learning project to understand agentic systems
- Focus on AI sector specifically (narrow scope, deep coverage)
- Start simple, add complexity incrementally
- Agent should explain its reasoning, not just present conclusions
- Web interface hosted via git (no separate web server needed)
- Always use `publish_briefing.py` for publishing (not html_reporter.py directly)
