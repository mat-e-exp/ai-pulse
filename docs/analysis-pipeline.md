# AI-Pulse Analysis Pipeline

## Overview

The analysis pipeline is where AI-Pulse becomes **agentic** - using Claude to autonomously assess event significance, sentiment, and investment implications.

**Core Question**: "How important is this event for AI sector investors?"

**Agent Decisions**:
1. Significance score (0-100)
2. Sentiment (positive/negative/neutral/mixed)
3. Investment relevance (Material/Notable/Background)
4. Affected parties (who wins/loses)
5. Implications (what it means)

---

## Architecture

```
Unanalyzed Events
     ↓
Filter (skip duplicates + research papers)
     ↓
Build Analysis Prompt
     ↓
Claude Haiku (~$0.002/event)
     ↓
Parse Structured Response
     ↓
Save to Database
     ↓
Ready for Publishing
```

**Model**: Claude 3.5 Haiku (beta mode)
**Cost**: ~$0.002 per event = ~$3/month for 50 events/day
**Upgrade Path**: Sonnet ($0.08/event) or Opus ($0.40/event) for higher quality

---

## When Analysis Runs

### Automated (GitHub Actions)

**Morning Collection (6am GMT):**
```bash
python3.9 agents/analyzer.py --limit 50
```
- Analyzes overnight news collected at 6am
- Limit: 50 events max to control costs
- Results sent to Discord (top 10 stories)

**Afternoon Collection (1:30pm GMT):**
```bash
python3.9 agents/analyzer.py --limit 50
```
- Analyzes any new events since morning
- Same 50-event limit
- Results published to HTML briefing

### Manual

```bash
# Analyze recent unanalyzed events
python3.9 agents/analyzer.py --limit 10

# Analyze ALL unanalyzed events
python3.9 agents/analyzer.py

# Show top analyzed events (no new analysis)
python3.9 agents/analyzer.py --top --limit 20

# Re-analyze specific events (rare)
python3.9 agents/analyzer.py --reanalyze
```

---

## What Gets Analyzed

### Included

✅ **News events** (`event_type != research`)
- Hacker News posts
- NewsAPI articles
- Tech RSS feeds
- SEC EDGAR filings
- GitHub trending repos
- Company IR press releases

✅ **Unique events only**
- `is_duplicate = 0`
- `is_semantic_duplicate = 0`

### Excluded

❌ **Research papers** (`event_type = research`)
- ArXiv papers are informational, not market-moving
- Displayed in "Research Highlights" section without analysis
- Not included in sentiment calculations

❌ **Duplicate events**
- String duplicates (`is_duplicate = 1`)
- Semantic duplicates (`is_semantic_duplicate = 1`)
- Already analyzed on first occurrence

---

## Analysis Prompt

### Event Context Provided to Claude

```python
EVENT DETAILS:
Title: OpenAI Launches GPT-5
Type: news
Source: newsapi
Published: 2025-11-25T10:00:00Z
URL: https://techcrunch.com/...
Summary: OpenAI announces GPT-5 with 10x performance improvement...
Content: OpenAI today announced GPT-5, a major leap forward in...
Companies mentioned: OpenAI, Microsoft
```

### Instructions to Claude

```
You are an AI sector investment analyst. Analyze this event for significance.

Provide your analysis in this EXACT format:

SIGNIFICANCE SCORE: [0-100]
SENTIMENT: [positive/negative/neutral/mixed]

REASONING:
[2-3 sentences explaining the score]

IMPLICATIONS:
[What does this mean for AI sector investors?]

AFFECTED PARTIES:
[List companies/sectors that benefit or are harmed]

INVESTMENT RELEVANCE:
[Does this change investment thesis? Material/Notable/Background]

- Material: Affects valuation models, competitive positioning, or strategic investment decisions
- Notable: Worth tracking but doesn't fundamentally change investment thesis
- Background: General sector awareness, no direct investment impact

KEY CONTEXT:
[Any historical comparisons or important context]

Scoring guide:
- 90-100: Thesis-changing (major revenue announcements, key executive departures, major regulation)
- 70-89: Notable strategic moves (important products, significant partnerships, competitive shifts)
- 50-69: Interesting developments (competitive intelligence, market signals, technical advances)
- 30-49: Background information (minor updates, opinion pieces, general news)
- 0-29: Noise, low relevance

Focus on investment implications for public AI stocks (NVDA, MSFT, GOOGL, META, AMD)
and broader AI sector trends.
```

---

## Claude Response Format

### Example Response

```
SIGNIFICANCE SCORE: 88

SENTIMENT: positive

REASONING:
GPT-5 represents a major competitive milestone for OpenAI and Microsoft, demonstrating continued
leadership in frontier models. The 10x performance improvement suggests meaningful differentiation
from competitors like Anthropic and Google. This likely impacts enterprise AI adoption rates and
cloud infrastructure demand (MSFT, NVDA benefit).

IMPLICATIONS:
Investors should view this as confirmation that the AI race remains highly competitive with
rapid innovation cycles. OpenAI's partnership with Microsoft (exclusive cloud provider) means
MSFT gains strategic advantage in enterprise AI. NVDA benefits from increased compute demand
for training and inference. Competitive pressure on GOOGL (Gemini) and META (Llama).

AFFECTED PARTIES:
- Winners: Microsoft (MSFT) - exclusive cloud, OpenAI - market leadership, NVIDIA (NVDA) - compute demand
- Losers: Google (GOOGL) - competitive pressure, Anthropic - market share risk
- Neutral: Meta (META) - focused on open-source, AMD (AMD) - infrastructure play

INVESTMENT RELEVANCE:
Material - Affects competitive positioning and revenue forecasts for MSFT and GOOGL. Signals
accelerating AI adoption which impacts valuation models for infrastructure providers (NVDA).
Notable for tracking competitive dynamics but doesn't fundamentally change thesis unless
performance claims are independently verified.

KEY CONTEXT:
Similar to GPT-4 launch (March 2023) which drove 30% increase in ChatGPT usage and Microsoft
Teams AI integration. Historical pattern: major model launches lead to 3-6 month enterprise
sales cycles. Previous "10x" claims (GPT-3→GPT-4) materialized as ~5-7x in practice.
```

### Parsed Into Database

```python
{
    'significance_score': 88,
    'sentiment': 'positive',
    'reasoning': 'GPT-5 represents a major competitive milestone...',
    'implications': 'Investors should view this as confirmation...',
    'affected_parties': '- Winners: Microsoft (MSFT)...',
    'investment_relevance': 'Material - Affects competitive positioning...',
    'key_context': 'Similar to GPT-4 launch (March 2023)...',
    'full_analysis': '[complete text]'
}
```

---

## Significance Scoring

### Score Ranges

| Range | Category | Examples |
|-------|----------|----------|
| **90-100** | **Thesis-Changing** | Major product launches (GPT-5, Claude 4), large acquisitions ($1B+), CEO departures, major regulation |
| **70-89** | **Notable Strategic** | Feature releases, mid-size funding ($100M-$500M), partnerships, competitive shifts |
| **50-69** | **Interesting Development** | Minor updates, competitive intelligence, technical advances, analyst reports |
| **30-49** | **Background Information** | Opinion pieces, commentary, routine announcements, industry trends |
| **0-29** | **Noise / Low Relevance** | Irrelevant content, duplicate news, non-AI content, clickbait |

### Publishing Thresholds

**HTML Briefing**: `--min-score 40` (default)
- Material Events: All scores (sorted by significance)
- Notable Events: Score ≥ 40
- Background: Not shown (filtered out)

**Discord Morning**: Top 10 by significance (no minimum)

---

## Sentiment Classification

### Categories

**Positive** - Beneficial for AI sector investors
- Product launches, funding rounds, partnerships
- Positive earnings, revenue growth
- Regulatory wins, favorable policy

**Negative** - Harmful for AI sector investors
- Executive departures, lawsuits, fines
- Product failures, security breaches
- Regulatory crackdowns, competitive threats

**Neutral** - Informational, no clear direction
- Research papers, technical updates
- Industry commentary, analysis
- Factual announcements without clear impact

**Mixed** - Both positive and negative aspects
- Layoffs with restructuring (short-term pain, long-term gain)
- Regulatory news with both restrictions and clarifications
- Competitive moves that benefit some companies while harming others

### Sentiment Aggregation

**Daily Sentiment Table**:
```sql
SELECT
    date,
    positive,
    negative,
    neutral,
    mixed,
    total_analyzed
FROM daily_sentiment
WHERE date = '2025-11-25';
```

**Percentage Calculation** (for chart display):
```python
positive_pct = (positive / total_analyzed) * 100
negative_pct = (negative / total_analyzed) * 100
neutral_pct = (neutral / total_analyzed) * 100
mixed_pct = (mixed / total_analyzed) * 100
```

**Chart Display**: 30-day trend showing sentiment distribution over time

---

## Investment Relevance

### Material

**Definition**: Directly impacts company valuations or competitive positioning

**Examples**:
- "OpenAI launches GPT-5" → Affects MSFT revenue forecasts, GOOGL competitive position
- "NVIDIA announces H200 GPU" → Changes infrastructure spend models
- "EU passes AI regulation" → Affects compliance costs and market access

**Usage**: Prioritized in briefings, triggers alerts, influences investment decisions

### Notable

**Definition**: Worth tracking but doesn't fundamentally change investment thesis

**Examples**:
- "Meta releases Llama 3.1 update" → Incremental improvement, expected
- "Anthropic raises $100M" → Validates sector, but doesn't change competitive dynamics
- "Google announces AI search features" → Expected product evolution

**Usage**: Monitored for trends, included in briefings, background context

### Background

**Definition**: General sector awareness, no direct investment impact

**Examples**:
- "AI researcher writes blog post on transformers"
- "University publishes AI ethics study"
- "Opinion piece on future of AI"

**Usage**: Filtered out of briefings (below --min-score threshold)

---

## Affected Parties Analysis

### Categories

**Winners** - Companies/sectors that benefit
- Direct revenue opportunities
- Competitive advantages
- Strategic positioning improvements

**Losers** - Companies/sectors harmed
- Competitive threats
- Market share loss
- Strategic disadvantages

**Neutral** - No clear impact or balanced effects

### Format

```
- Winners: Microsoft (MSFT) - exclusive cloud partnership, NVIDIA (NVDA) - compute demand
- Losers: Google (GOOGL) - competitive pressure on Gemini
- Neutral: AMD (AMD) - infrastructure play but minor impact
```

### Usage

- Identifies sector rotation opportunities
- Highlights competitive dynamics
- Informs portfolio adjustments

---

## Cost Tracking

### Per-Event Cost

**Haiku Beta Mode (current)**:
- Input: ~500 tokens (event details)
- Output: ~300 tokens (analysis)
- Cost: ~$0.002 per event

**Monthly Estimates**:
- 50 events/day × 30 days = 1,500 events/month
- 1,500 × $0.002 = **~$3/month**

### Model Comparison

| Model | Cost/Event | 50 events/day | Monthly |
|-------|------------|---------------|---------|
| **Haiku (current)** | ~$0.002 | $0.10/day | **~$3/month** |
| Sonnet | ~$0.08 | $4.00/day | ~$120/month |
| Opus | ~$0.40 | $20.00/day | ~$600/month |

### Cost Tracking Database

All API calls logged to `api_calls` table:
```sql
SELECT
    date(timestamp) as date,
    COUNT(*) as calls,
    SUM(cost_usd) as total_cost
FROM api_calls
WHERE operation = 'event_analysis'
GROUP BY date(timestamp)
ORDER BY date DESC;
```

### Budget Management

```bash
# Set monthly budget
python3.9 cost_tracking/tracker.py --set-budget 50.0

# Check current spend
python3.9 cost_tracking/tracker.py --month

# View cost breakdown
python3.9 cost_tracking/tracker.py --breakdown
```

---

## Quality Assurance

### Validation Checks

**Score Range**: 0 ≤ score ≤ 100
- Clamped if out of range: `max(0, min(100, score))`

**Sentiment Values**: Must be one of:
- positive, negative, neutral, mixed
- Default: neutral if unrecognized

**Investment Relevance**: Must contain:
- Material, Notable, or Background (case-insensitive)
- Default: "Notable" if unrecognized

### Error Handling

**API Failures**:
```python
try:
    response = client.messages.create(...)
except Exception as e:
    print(f"⚠ Analysis failed: {e}")
    # Event remains unanalyzed (can retry later)
```

**Parsing Failures**:
```python
# Defaults applied if parsing fails:
result = {
    'significance_score': 50,  # Middle score
    'sentiment': 'neutral',
    'reasoning': '',
    'implications': '',
    'affected_parties': '',
    'investment_relevance': 'Notable',
    'key_context': '',
    'full_analysis': analysis_text,
}
```

---

## Database Updates

### SQL Update

After successful analysis:
```sql
UPDATE events SET
    significance_score = 88,
    sentiment = 'positive',
    analysis = 'GPT-5 represents a major competitive milestone...',
    implications = 'Investors should view this as confirmation...',
    affected_parties = '- Winners: Microsoft (MSFT)...',
    investment_relevance = 'Material - Affects competitive positioning...',
    key_context = 'Similar to GPT-4 launch (March 2023)...'
WHERE id = 12345;
```

### Idempotency

**Analysis is idempotent**:
- Once analyzed, `significance_score IS NOT NULL`
- Analyzer skips events with existing scores
- Re-analysis only if explicitly requested (`--reanalyze`)

**Why**: Prevents cost waste and maintains consistency

---

## Output & Usage

### Analyzer Output

```
================================================================================
ANALYZING EVENTS
================================================================================
Found 15 unanalyzed events
Limit: 50 events (cost control)

[1/15] "OpenAI launches GPT-5" → 88 (positive)
[2/15] "Google announces Gemini 2.0" → 82 (positive)
[3/15] "AI startup raises $50M" → 55 (neutral)
...
[15/15] "Blog post on AI ethics" → 25 (neutral)

✓ Analyzed: 15 events
✓ Total cost: $0.030
✓ Average score: 61.2
```

### Database Query

```bash
# Top events by significance
sqlite3 ai_pulse.db "
SELECT title, significance_score, sentiment, investment_relevance
FROM events
WHERE significance_score IS NOT NULL
ORDER BY significance_score DESC
LIMIT 10;
"
```

### HTML Briefing

**Material Events** (thesis-changing):
- Displayed at top of briefing
- Full analysis shown
- Sorted by significance (highest first)

**Notable Events** (worth tracking):
- Displayed below material events
- Score ≥ 40 (default threshold)
- Full analysis shown

**Background** (filtered out):
- Score < 40 (default threshold)
- Not shown in briefing
- Still in database for reference

---

## Upgrade Paths

### When to Upgrade to Sonnet

**Current**: Haiku (~$0.002/event, ~$3/month)
**Upgrade to Sonnet** (~$0.08/event, ~$120/month) when:
1. Analysis quality insufficient (scores don't match manual assessment)
2. Reasoning too shallow (need deeper context)
3. Budget allows ($120/month acceptable)

**Change**: Update `ANALYSIS_MODEL = "claude-3-5-sonnet-20241022"` in `analysis/significance.py:39`

### When to Upgrade to Opus

**Upgrade to Opus** (~$0.40/event, ~$600/month) when:
1. Investment decisions depend on analysis quality
2. Need highest reasoning capability
3. Budget allows ($600/month acceptable)

**Change**: Update `ANALYSIS_MODEL = "claude-3-opus-20240229"` in `analysis/significance.py:39`

---

## Files Reference

**Core Analysis Code:**
- `analysis/significance.py` - Claude integration, prompt, parsing
- `agents/analyzer.py` - Batch processing, filtering, CLI

**Cost Tracking:**
- `cost_tracking/tracker.py` - API call logging, budget management
- `cost_tracking/database.py` - Cost database operations

**Database:**
- `storage/db.py` - Event updates, query logic
- `models/events.py` - Event data structure

---

## Troubleshooting

### "No events analyzed"

**Check**:
1. Are there unanalyzed events? `SELECT COUNT(*) FROM events WHERE significance_score IS NULL`
2. Are events duplicates? Check `is_duplicate`, `is_semantic_duplicate`
3. Are events research papers? Check `event_type = 'research'`

### "Analysis quality poor"

**Solutions**:
1. Review prompt in `analysis/significance.py:142-178`
2. Upgrade model to Sonnet or Opus
3. Add more context to event details (better summaries)

### "Costs too high"

**Solutions**:
1. Reduce `--limit` parameter (default: 50)
2. Filter events before analysis (higher quality sources only)
3. Increase `--min-score` threshold (analyze fewer events)
4. Check for duplicate analysis (should only run once per event)

### "API rate limited"

**Check**:
1. Anthropic API key valid
2. Account has credits
3. Not hitting rate limits (very unlikely with Haiku)

**Fix**: Wait and retry, or spread analysis over longer period

---

## Summary

The analysis pipeline is the **"brain" of AI-Pulse**:

1. **Filters** unanalyzed unique news events (skips duplicates + research papers)
2. **Builds context** from event title, summary, content, companies
3. **Sends to Claude Haiku** with structured prompt (~$0.002/event)
4. **Parses response** into significance score, sentiment, implications
5. **Saves to database** for repeated publishing without re-analysis
6. **Tracks costs** against monthly budget

**Result**: Autonomous assessment of AI sector events for investment decisions.

**Beta Mode**: Haiku keeps costs at ~$3/month while maintaining good quality.

**Upgrade Path**: Sonnet or Opus available when higher quality needed.
