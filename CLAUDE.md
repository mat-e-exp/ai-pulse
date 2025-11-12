# AI-PULSE PROJECT

## What This Does
Real-time intelligence agent for the AI sector - tracks product launches, funding, technical breakthroughs, market sentiment, and competitive dynamics to provide actionable insights for AI investment decisions.

## Primary Goal: ACCURACY
**Accuracy is the highest priority** - above speed, cost, or features. The system must provide trustworthy data for investment decisions. This means:
- **No duplicate stories** inflating sentiment counts
- **Accurate sentiment distribution** - each unique story counted once
- **Reliable significance scores** - no re-analyzing the same event
- **Trustworthy percentages** - chart reflects reality, not data collection artifacts

Investment decisions depend on this data being correct.

## Current Status
- ✅ **Phase 1 Complete**: Basic news collector working
- ✅ **Phase 2 Complete**: Agentic significance analysis with Claude API
- ✅ **Phase 2.5 Complete**: Web publishing with sentiment tracking and deduplication (2025-11-12)
- ✅ **Phase 2.6 Complete**: Semantic deduplication with Claude for accurate sentiment (2025-11-12)

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

**Disabled (2025-11-11)**:
- Google News RSS - Feed structure incompatible, returns no results
- Bing News API - Requires separate API key, not worth additional cost
- Tech RSS Feeds - Inconsistent/broken feeds with parsing errors
- Files exist in `sources/` but not integrated into collector

**Future Sources**:
- Twitter/X API (basic tier)
- Reddit API (free tier)
- ArXiv API (unlimited, free)
- Yahoo Finance via yfinance (free)
- Alpha Vantage (500 calls/day free)

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

# Optional (for expanded features)
NEWS_API_KEY=...
TWITTER_API_KEY=...
ALPHA_VANTAGE_API_KEY=...
```

## Commands

```bash
# RECOMMENDED DAILY WORKFLOW (accurate sentiment)
python3.9 agents/collector.py --hn-limit 20 --news-limit 30 --sec-days 7 --github-days 7 --github-stars 500 --ir-days 7
python3.9 agents/semantic_deduplicator.py --days 7  # NEW: Claude-powered semantic dedup
python3.9 agents/analyzer.py --limit 10
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

### Daily Workflow (Manual - For Accurate Sentiment)
1. **Collect Data**: `python3.9 agents/collector.py` fetches from 5 sources with string deduplication
2. **Semantic Dedup**: `python3.9 agents/semantic_deduplicator.py` uses Claude to catch semantic duplicates
3. **Analyze Events**: `python3.9 agents/analyzer.py` uses Claude to score significance and sentiment (skips duplicates)
4. **Publish Briefing**: `python3.9 publish_briefing.py` generates HTML, updates index.html, saves sentiment history
5. **Push to Git**: `git add . && git commit && git push` publishes to GitHub Pages

**Critical**: Step 2 (semantic dedup) must run BEFORE step 3 (analysis) for trustworthy sentiment data.

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

**Critical for Accuracy**: Duplicates skew sentiment counts and waste analysis costs.

**Problem**: Same story reported by multiple sources
- Example: "SoftBank sells Nvidia stake" appeared 6+ times on 2025-11-11
- Each duplicate analyzed separately by Claude
- Each gets sentiment score (e.g., all "mixed")
- Inflates that sentiment in daily count: "mixed: 38%" instead of true "mixed: 20%"
- **Result**: Untrustworthy sentiment percentages

**Current Implementation: String-Based Deduplication (Partial Solution)**

**Phase 1: Collection-Time (Forward)**:
- Location: `agents/collector.py` - `deduplicate_events()` function
- Runs after fetching from each source, before database storage
- Groups events by published date
- Compares titles using `SequenceMatcher` similarity (0-1 score)
- Marks as duplicate if:
  - Title similarity ≥ 75%, OR
  - Title similarity ≥ 60% AND same companies mentioned
- Keeps first occurrence, discards duplicates
- **Limitation**: Misses semantic duplicates with different wording

**Phase 2: Retroactive (Historical)**:
- Location: `retroactive_dedup.py` script
- Run once after implementing deduplication
- Scans existing database for duplicates (default: last 30 days)
- Uses same similarity logic as forward deduplication
- Adds `is_duplicate` column to database if missing
- Marks duplicate events with `is_duplicate = 1`
- Recalculates `daily_sentiment` table excluding duplicates
- Preserves history (doesn't delete), just marks and excludes

**Filtering in Reports**:
- `agents/html_reporter.py` filters: `if not getattr(e, 'is_duplicate', False)`
- Sentiment counts only include non-duplicate events
- Chart displays accurate sentiment distribution

**Known Gap: Semantic Duplicates Still Slip Through**

String matching misses these duplicates (all about same event):
- "SoftBank sells entire Nvidia stake for $5.8B"
- "SoftBank profits double on AI investments"
- "Japan's SoftBank exits Nvidia position"
→ All <75% string similarity but **same underlying event**

**Impact on Accuracy**:
- 3-6 semantic duplicates per major news day
- Each analyzed separately (~$0.15 wasted)
- Each counted in sentiment (inflates by 3-6 votes)
- Percentages skewed by 5-15%

**Solution Implemented: Semantic Deduplication (Phase 2.6) ✅**

**How it works**:
1. After collection, before analysis
2. `agents/semantic_deduplicator.py` groups events by date
3. Sends titles to Claude Haiku: "Which report the same event?"
4. Claude returns semantic duplicate groups using understanding not string matching
5. Marks `is_semantic_duplicate = 1` in database
6. Analyzer skips semantic duplicates
7. Each unique story analyzed once
8. Sentiment counts accurate

**Results on 2025-11-11**:
- Found 2 duplicate groups (4 events total):
  - SoftBank group: "sells Nvidia" + "profits double" + "unloads stake" + "rides AI wave"
  - Intel CTO group: "Sachin Katti departs" + "Sachin Katti joins"
- Before: 61 events analyzed
- After: 57 unique events
- Sentiment percentages now trustworthy

**Cost**: ~$0.002 per date with Haiku (very cheap), saves ~$0.20 in wasted Sonnet analysis calls.

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

## GitHub Pages Hosting

**Repository**: `mat-e-exp/ai-pulse`
**Typical URL**: `https://mat-e-exp.github.io/ai-pulse/` (if Pages enabled)

**Setup**:
1. Go to repository Settings → Pages
2. Source: Deploy from branch `main`
3. Folder: `/ (root)`
4. Save and wait for deployment

**Publishing**:
```bash
python3.9 publish_briefing.py --days 1 --min-score 40
git add briefings/*.html index.html archive.html
git commit -m "Daily briefing YYYY-MM-DD"
git push
# Wait 1-2 minutes for GitHub Pages to rebuild
```

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
