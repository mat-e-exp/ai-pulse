# AI-Pulse

Real-time intelligence agent for the AI sector. Tracks product launches, funding, technical breakthroughs, market sentiment, and competitive dynamics to provide actionable insights for AI investment decisions.

## What It Does

AI-Pulse autonomously collects and analyzes AI sector news from multiple sources, then uses Claude to assess significance and generate intelligent briefings.

**Key Features:**
- Collects from 5 sources: Hacker News, NewsAPI, SEC EDGAR, GitHub, Company IR
- Autonomous significance scoring (0-100) with reasoning
- Investment relevance classification (Material/Marginal/Noise)
- Competitive impact analysis
- Cost tracking with budget management
- Intelligent daily briefings

## Quick Start

### 1. Install Dependencies

```bash
pip install anthropic requests python-dotenv
```

### 2. Set API Keys

Create `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-...
NEWS_API_KEY=...  # Optional: Get free key from newsapi.org
```

### 3. Collect Data

```bash
# Collect from all 5 sources
python3.9 agents/collector.py

# Custom limits
python3.9 agents/collector.py --hn-limit 20 --news-limit 30 --github-stars 500
```

### 4. Analyze Events

```bash
# Analyze collected events with Claude
python3.9 agents/analyzer.py --limit 10

# Analyze all unanalyzed events
python3.9 agents/analyzer.py
```

### 5. Generate Briefing

```bash
# Daily briefing (last 24 hours)
python3.9 agents/reporter_intelligent.py

# Weekly briefing
python3.9 agents/reporter_intelligent.py --days 7

# Filter by significance
python3.9 agents/reporter_intelligent.py --min-score 70
```

## Data Sources

### Free (No API Key Required)
- **Hacker News**: Tech community AI discussions
- **SEC EDGAR**: Material events from 10 AI companies (8-K filings)
- **GitHub**: Trending AI repositories and releases
- **Company IR**: Press releases from NVIDIA, AMD

### Optional (Free Tier Available)
- **NewsAPI**: Professional news coverage (100 calls/day free)
  - Get key at: https://newsapi.org

## Commands Reference

### Data Collection

```bash
# Basic collection (default limits)
python3.9 agents/collector.py

# All parameters
python3.9 agents/collector.py \
  --hn-limit 20 \          # Hacker News stories
  --news-days 1 \          # NewsAPI days back
  --news-limit 30 \        # NewsAPI articles
  --sec-days 7 \           # SEC EDGAR days back
  --github-days 7 \        # GitHub days back
  --github-stars 500 \     # GitHub minimum stars
  --ir-days 7              # Company IR days back
```

### Analysis

```bash
# Analyze recent events
python3.9 agents/analyzer.py --limit 10

# Show top analyzed events
python3.9 agents/analyzer.py --top --limit 20

# Analyze all unanalyzed events
python3.9 agents/analyzer.py
```

### Briefings

```bash
# Daily briefing
python3.9 agents/reporter_intelligent.py

# Weekly briefing with minimum score
python3.9 agents/reporter_intelligent.py --days 7 --min-score 50

# Top events only
python3.9 agents/reporter_intelligent.py --top
```

### Cost Tracking

```bash
# View today's costs
python3.9 cost_tracking/tracker.py --today

# Weekly costs
python3.9 cost_tracking/tracker.py --week

# Monthly costs
python3.9 cost_tracking/tracker.py --month

# Cost breakdown by operation
python3.9 cost_tracking/tracker.py --breakdown

# Set monthly budget
python3.9 cost_tracking/tracker.py --set-budget 50.0

# View budget status
python3.9 cost_tracking/tracker.py --budget

# 7-day cost trend
python3.9 cost_tracking/tracker.py --trend
```

## How It Works

### 1. Collection Phase
The collector fetches data from all sources and stores in SQLite:
- Deduplicates by source URL
- Extracts companies, products, people
- Classifies event type (news, product launch, funding, etc.)

### 2. Analysis Phase (Agentic)
The analyzer uses Claude to autonomously assess each event:
- **Significance Score** (0-100): How important is this?
- **Reasoning**: Why does this matter?
- **Investment Relevance**: Material/Marginal/Noise
- **Implications**: What does this mean for investors?
- **Affected Parties**: Who wins/loses?
- **Context**: Historical comparisons

### 3. Briefing Phase
The reporter generates intelligent summaries:
- Groups by significance level
- Shows AI reasoning for each event
- Prioritizes material events
- Provides actionable insights

## Understanding Significance Scores

**90-100 (Major)**: Market-moving events
- Major product launches (GPT-5, Claude 4)
- Large funding rounds (>$500M)
- Major acquisitions
- Regulatory decisions

**70-89 (Important)**: Notable developments
- Feature releases
- Mid-size funding ($100M-$500M)
- Strategic partnerships
- Technical breakthroughs

**50-69 (Moderate)**: Worth tracking
- Minor updates
- Smaller funding rounds
- Industry commentary
- Competitive moves

**30-49 (Minor)**: Background noise
- Routine announcements
- Opinion pieces
- Non-material news

**0-29 (Noise)**: Can ignore
- Irrelevant content
- Duplicate news
- Non-AI content

## Investment Relevance

**Material**: Directly impacts company valuations or competitive positioning
- Example: "OpenAI launches GPT-5"

**Marginal**: Interesting but not immediately material
- Example: "Meta releases small efficiency improvement to Llama"

**Noise**: Not investment-relevant
- Example: "AI researcher writes blog post"

## Typical Workflow

```bash
# Morning routine: Collect overnight news
python3.9 agents/collector.py

# Analyze new events
python3.9 agents/analyzer.py --limit 20

# Generate briefing
python3.9 agents/reporter_intelligent.py --min-score 40

# Check API costs
python3.9 cost_tracking/tracker.py --today
```

## Database

All data stored in `ai_pulse.db` (SQLite):
- **events**: Collected news/events with analysis
- **api_calls**: Cost tracking
- **budget**: Monthly budget settings

To reset database: `rm ai_pulse.db`

## Tracked Companies

**Public Companies**:
- NVIDIA, Microsoft, Alphabet (Google), Meta, AMD, Intel, Amazon, Tesla, Oracle, Broadcom

**Private Leaders**:
- OpenAI, Anthropic, Hugging Face, Stability AI

**Organizations**:
- Google Research, Google DeepMind, Meta Research (FAIR)

## Cost Management

Claude API costs approximately:
- **Analysis**: $3 per 1M input tokens, $15 per 1M output tokens
- **Typical event**: ~$0.01-0.02 per analysis
- **20 events/day**: ~$0.20-0.40/day (~$6-12/month)

Set budget alerts:
```bash
python3.9 cost_tracking/tracker.py --set-budget 50.0
```

## Project Structure

```
ai-pulse/
├── agents/              # Agent logic
│   ├── collector.py     # Data collection orchestration
│   ├── analyzer.py      # Significance analysis (agentic)
│   └── reporter*.py     # Briefing generation
├── sources/             # Data source integrations
│   ├── hackernews.py    # Hacker News API
│   ├── newsapi.py       # NewsAPI
│   ├── sec_edgar.py     # SEC EDGAR filings
│   ├── github_trending.py # GitHub trending
│   └── company_ir.py    # Company press releases
├── models/              # Data models
│   └── events.py        # Event types, enums
├── storage/             # Data persistence
│   └── db.py            # SQLite operations
├── analysis/            # Analysis logic
│   └── significance.py  # Claude-based scoring
├── cost_tracking/       # Cost management
│   ├── database.py      # Cost tracking DB
│   └── tracker.py       # Cost CLI
├── .env                 # API keys (not in git)
├── ai_pulse.db          # SQLite database (not in git)
└── README.md            # This file
```

## Limitations

- NewsAPI free tier: 100 calls/day
- GitHub API: 5000 calls/hour (unauthenticated)
- SEC EDGAR: No rate limit but requires proper User-Agent
- Claude API: Pay-per-use (track with cost_tracking)

## Future Enhancements

**Phase 3 (Planned)**:
- Track sentiment over time
- Detect narrative shifts
- Historical pattern matching
- Cross-event reasoning

**Phase 4 (Planned)**:
- Real-time monitoring
- Automated alert prioritization
- Multi-step investigation workflows
- Proactive deep-dives

## Troubleshooting

**"No module named 'anthropic'"**
```bash
pip install anthropic requests python-dotenv
```

**"No events collected"**
- Check internet connection
- Verify API keys in .env
- Try shorter time windows (events may be old)

**"Database locked"**
- Close other processes using ai_pulse.db
- Wait a moment and retry

**High API costs**
- Reduce --limit in analyzer
- Increase --min-score to analyze only top events
- Set budget with cost_tracking/tracker.py

## License

This is a learning project for understanding agentic systems.

## Contributing

This is a personal learning project, but feedback welcome via issues.
