# AI-Pulse Usage Guide

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/mat.edwards/dev/test-claude/ai-pulse
pip3 install -r requirements.txt
```

### 2. Collect Data

```bash
# Collect from Hacker News (no API key needed)
python3.9 agents/collector.py

# Collect with custom limits
python3.9 agents/collector.py --hn-limit 50

# If you have NewsAPI key (optional)
# Add NEWS_API_KEY to .env file first
cp .env.example .env
# Edit .env and add your key
python3.9 agents/collector.py --news-days 2 --news-limit 50
```

### 3. View Results

```bash
# Generate daily briefing
python3.9 agents/reporter.py --daily

# Show recent events
python3.9 agents/reporter.py --recent --limit 20

# Show database stats
python3.9 agents/reporter.py --stats
```

## What You Built

### Phase 1: Basic News Collector ✅ (COMPLETE)

**Components**:
- `models/events.py` - Event data model
- `storage/db.py` - SQLite database layer
- `sources/hackernews.py` - Hacker News integration
- `sources/newsapi.py` - NewsAPI integration (optional)
- `agents/collector.py` - Collection orchestrator
- `agents/reporter.py` - Simple reporter

**What It Does**:
- Fetches AI-related stories from Hacker News
- Optionally fetches from NewsAPI (if key provided)
- Stores in SQLite database
- Detects duplicates (won't re-add same story)
- Generates daily briefings
- Basic event classification (product launch, funding, news, etc.)

**What It Doesn't Do Yet** (Phase 2):
- ❌ Significance analysis ("Is this important?")
- ❌ LLM-based reasoning
- ❌ Competitive impact analysis
- ❌ Investment implications
- ❌ Narrative tracking over time
- ❌ Entity extraction (companies, products)

## Current Limitations

### Not Agentic Yet
This is a **simple data pipeline**, not an agent. It:
- Runs fixed logic (no decision making)
- Uses keyword matching (not reasoning)
- Doesn't understand context
- Doesn't adapt to findings

### Why This Matters
You built the **foundation** for an agent:
- ✓ Data collection infrastructure
- ✓ Storage layer
- ✓ Multiple source integration
- ✓ Deduplication
- ✓ Basic classification

**Next**: Add Claude API to make it reason about what it finds.

## Example Workflow

```bash
# Morning routine: collect overnight AI news
python3.9 agents/collector.py

# Generate briefing
python3.9 agents/reporter.py --daily

# Output shows:
# - Product launches (if any detected)
# - Funding announcements (if any)
# - General AI news
# - Database stats
```

## Files Created

```
ai-pulse/
├── ai_pulse.db          # SQLite database (created on first run)
├── agents/
│   ├── collector.py     # Data collection
│   └── reporter.py      # Reporting
├── sources/
│   ├── hackernews.py    # HN integration
│   └── newsapi.py       # NewsAPI integration
├── models/
│   └── events.py        # Event data model
└── storage/
    └── db.py            # Database layer
```

## Next Steps (Phase 2)

To make this truly "agentic", you'll add:

1. **Significance Analyzer** (`analysis/significance.py`)
   - Use Claude API to score each event (0-100)
   - Ask: "Why does this matter? Who is affected?"
   - Store analysis in database

2. **Narrative Tracker** (`analysis/narrative.py`)
   - Track themes over time
   - Detect sentiment shifts
   - Compare to historical patterns

3. **Smart Reporter** (upgrade `agents/reporter.py`)
   - Generate insights, not just lists
   - Explain WHY things are important
   - Provide context and implications

4. **Autonomous Collector** (upgrade `agents/collector.py`)
   - Decide which sources to query based on what's happening
   - Adjust collection frequency based on activity
   - Investigate specific topics when needed

Want to build Phase 2? That's where it gets agentic!
