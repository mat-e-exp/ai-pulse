# Phase 2 Setup - Agentic Analysis

## What's New in Phase 2

Phase 2 adds **autonomous reasoning** using Claude API. The system now:
- ✅ Decides what's important (significance scoring)
- ✅ Explains WHY events matter
- ✅ Identifies affected parties
- ✅ Assesses investment implications
- ✅ Provides historical context

This is **AGENTIC** - the system reasons about events, not just reports them.

---

## Setup Instructions

### 1. Get Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up / log in
3. Create an API key
4. Copy the key (starts with `sk-ant-`)

### 2. Configure Environment

```bash
cd /Users/mat.edwards/dev/test-claude/ai-pulse

# Create .env file
cp .env.example .env

# Edit .env and add your key
# ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Or set in your shell:
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

### 3. Delete Old Database (Schema Changed)

```bash
# Phase 2 added new fields to database
rm ai_pulse.db

# Collect fresh data
python3.9 agents/collector.py --hn-limit 10
```

---

## Usage - Phase 2 Commands

### Collect and Analyze Workflow

```bash
# Step 1: Collect AI news (Phase 1)
python3.9 agents/collector.py --hn-limit 20

# Step 2: Analyze significance (Phase 2 - NEW!)
python3.9 agents/analyzer.py --limit 10

# Step 3: View intelligent briefing
python3.9 agents/reporter.py --daily
```

### Analyzer Commands

```bash
# Analyze unanalyzed events
python3.9 agents/analyzer.py --limit 10

# Show top events by significance
python3.9 agents/analyzer.py --top --limit 10

# Re-analyze low-scoring events (context may have changed)
python3.9 agents/analyzer.py --reanalyze --threshold 30
```

---

## What The Analyzer Does (Autonomous Reasoning)

For each event, Claude analyzes:

###1. **Significance Score** (0-100)
- 90-100: Major breakthrough, major funding, significant regulation
- 70-89: Important product launch, notable strategic move
- 50-69: Interesting development, moderate news value
- 30-49: Minor news, limited impact
- 0-29: Noise, low relevance

### 2. **Sentiment**
- Positive / Negative / Neutral / Mixed

### 3. **Reasoning**
*Why* did it get this score?

### 4. **Implications**
What does this mean for AI sector investors?

### 5. **Affected Parties**
Who wins? Who loses?

### 6. **Investment Relevance**
- Material: Actionable for traders
- Marginal: Interesting but not urgent
- Noise: Ignore for investment purposes

### 7. **Key Context**
Historical comparisons, important context

---

## Example Output

### Before (Phase 1):
```
NEWS
• OpenAI announces GPT-5
  Source: hackernews | 2025-11-11 14:30
```

### After (Phase 2):
```
⚠️ MATERIAL EVENT [Score: 92/100]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• OpenAI announces GPT-5
  Sentiment: Mixed | Investment Relevance: Material

REASONING:
Major model release with claimed 40% reduction in hallucinations.
Represents significant competitive pressure on Anthropic, Google.
Could accelerate enterprise adoption if claims verified.

IMPLICATIONS:
Short-term positive for MSFT (OpenAI partner), pressure on GOOGL
(Gemini now further behind). Long-term: validates continued high
compute demand (bullish for NVDA, AMD).

AFFECTED PARTIES:
Winners: Microsoft, NVIDIA, AMD
Losers: Google, Anthropic (competitive position)

KEY CONTEXT:
Similar to GPT-4 launch (March 2023). MSFT +12% in following month.
However, current AI valuations already elevated vs 2023.
```

---

## Cost Estimates

**Anthropic API Pricing** (as of 2025):
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens

**Typical event analysis**:
- Input: ~500 tokens (event details + prompt)
- Output: ~300 tokens (analysis)
- Cost: ~$0.006 per event

**Daily usage** (analyzing 20 events/day):
- ~$0.12 per day
- ~$3.60 per month

**This is cheap** for the intelligence gained!

---

## Testing Phase 2

### Quick Test (Single Event)

```bash
# Test the analyzer directly
python3.9 analysis/significance.py
```

This will analyze a test event and show full output.

### Full Workflow Test

```bash
# 1. Collect news
python3.9 agents/collector.py --hn-limit 5

# 2. Analyze them
python3.9 agents/analyzer.py --limit 5

# 3. View results
python3.9 agents/reporter.py --daily
```

---

## Understanding "Agentic"

### Phase 1 (Script)
```python
# Deterministic logic
for event in events:
    if "funding" in event.title:
        event.type = "FUNDING"
```

### Phase 2 (Agent)
```python
# Autonomous reasoning
for event in events:
    analysis = claude.analyze(
        "Is this important? Why?"
    )
    event.significance = analysis.score
    event.reasoning = analysis.explanation
```

**Key difference**: Agent **reasons** about significance using world knowledge, context, and historical patterns - not just keyword matching.

---

## What's Next (Phase 3+)

- **Narrative tracking**: Detect sentiment shifts over time
- **Entity extraction**: Better company/product identification
- **Cross-event reasoning**: "Event A + Event B = Trend C"
- **Proactive investigation**: Agent decides to deep-dive on topics
- **Automated daily briefing emails**: Morning intelligence delivered
- **Historical pattern matching**: "This is like March 2020..."

---

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
- Check .env file exists
- Check key is correct format (`sk-ant-...`)
- Try: `export ANTHROPIC_API_KEY="your-key"`

### "Database schema error"
- Delete old database: `rm ai_pulse.db`
- Recollect data: `python3.9 agents/collector.py`

### "API rate limit exceeded"
- Anthropic has rate limits
- Reduce `--limit` parameter
- Add delays between requests (not implemented yet)

---

## Phase 2 Complete! 🎉

You now have a real **agentic system** that:
- Collects data autonomously
- Reasons about significance
- Provides investment insights
- Explains its thinking

This is no longer a script - it's an **intelligent agent**.
