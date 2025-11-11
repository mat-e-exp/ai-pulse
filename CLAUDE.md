# AI-PULSE PROJECT

## What This Does
Real-time intelligence agent for the AI sector - tracks product launches, funding, technical breakthroughs, market sentiment, and competitive dynamics to provide actionable insights for AI investment decisions.

## Current Status
- ✅ **Phase 1 Complete**: Basic news collector working
- ✅ **Phase 2 Complete**: Agentic significance analysis with Claude API

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

## Data Sources (Free/Low-Cost)

**News & Social**:
- NewsAPI (100 calls/day free)
- Twitter/X API (basic tier)
- Hacker News API (unlimited, free)
- Reddit API (free tier)

**Technical**:
- ArXiv API (unlimited, free)
- GitHub API (5000 calls/hour free)
- HuggingFace (free)

**Financial**:
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

## Commands (Phase 1 + Phase 2)

```bash
# PHASE 1: Data Collection
python3.9 agents/collector.py --hn-limit 20
python3.9 agents/reporter.py --daily

# PHASE 2: Agentic Analysis (NEW!)
python3.9 agents/analyzer.py --limit 10
python3.9 agents/reporter_intelligent.py --min-score 40

# Show top events by significance
python3.9 agents/reporter_intelligent.py --top --days 7

# Show top events from analyzer
python3.9 agents/analyzer.py --top --limit 10
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
- ✅ NewsAPI integration (optional)
- ✅ SQLite storage with deduplication
- ✅ Simple daily summaries

### Phase 2: Intelligence Layer ✅ COMPLETE
- ✅ Claude API integration
- ✅ Significance scoring (0-100)
- ✅ "Why does this matter?" reasoning
- ✅ Competitive impact analysis
- ✅ Investment implications assessment
- ✅ Intelligent briefing generation

### Phase 3: Narrative Tracking (NEXT)
- Track sentiment over time
- Detect narrative shifts
- Historical pattern matching
- Cross-event reasoning

### Phase 4: Full Autonomy
- Real-time monitoring
- Automated alert prioritization
- Multi-step investigation workflows
- Proactive deep-dives

## Related Projects
- None (standalone project)

## Notes
- This is a learning project to understand agentic systems
- Focus on AI sector specifically (narrow scope, deep coverage)
- Start simple, add complexity incrementally
- Agent should explain its reasoning, not just present conclusions
