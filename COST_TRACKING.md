# Cost Tracking Guide

## Overview

AI-Pulse now includes **automatic cost tracking** for all API usage. Every Claude API call is logged with token counts and estimated costs.

## Features

✅ **Automatic Logging**: Every API call tracked automatically
✅ **Budget Management**: Set monthly limits and alerts
✅ **Cost Breakdown**: See costs by operation type
✅ **Daily Trends**: Track spending over time
✅ **Forecasting**: Project monthly costs
✅ **Zero Configuration**: Works out of the box

---

## Quick Start

### View Current Costs

```bash
# Show all summaries
python3.9 cost_tracking/tracker.py

# Today only
python3.9 cost_tracking/tracker.py --today

# This week
python3.9 cost_tracking/tracker.py --week

# This month
python3.9 cost_tracking/tracker.py --month
```

### Set Budget

```bash
# Set $10/month budget
python3.9 cost_tracking/tracker.py --set-budget 10.00

# Check budget status
python3.9 cost_tracking/tracker.py --budget
```

### Detailed Reports

```bash
# Cost breakdown by operation
python3.9 cost_tracking/tracker.py --breakdown

# Daily trend (last 30 days)
python3.9 cost_tracking/tracker.py --trend

# Last 7 days
python3.9 cost_tracking/tracker.py --trend --days 7
```

---

## How It Works

### Automatic Tracking

Cost tracking is **built-in** to the analyzer:

```python
# In analysis/significance.py
response = self.client.messages.create(...)

# Automatically logged:
self.cost_tracker.log_anthropic_call(
    response,
    operation='event_analysis',
    event_id=event.id
)
```

**No code changes needed** - it just works!

### What's Tracked

For each API call:
- **Timestamp**: When the call was made
- **Service**: `anthropic` (or `openai` if you add it)
- **Model**: `claude-sonnet-4-20250514`
- **Operation**: `event_analysis`, `test_run`, etc.
- **Input Tokens**: Number of tokens sent to API
- **Output Tokens**: Number of tokens received
- **Estimated Cost**: Calculated from current pricing

### Pricing (Current Rates)

**Anthropic Claude Sonnet 4**:
- Input: $3.00 per 1M tokens
- Output: $15.00 per 1M tokens

**Typical Event Analysis**:
- Input: ~500 tokens (event details + prompt)
- Output: ~300 tokens (analysis)
- **Cost per event: ~$0.006** (less than a penny!)

---

## Example Output

### Summary View

```bash
$ python3.9 cost_tracking/tracker.py

================================================================================
AI-PULSE COST SUMMARY - 2025-11-11 15:30 UTC
================================================================================

TODAY:
  Calls: 15 | Tokens: 12,350 | Cost: $0.0923

THIS WEEK:
  Calls: 87 | Tokens: 71,480 | Cost: $0.5341

THIS MONTH:
  Calls: 203 | Tokens: 166,920 | Cost: $1.2468

BUDGET STATUS:
  Limit: $10.00 | Spent: $1.2468 (12.5%) | Projected: $3.94

================================================================================
```

### Budget Status

```bash
$ python3.9 cost_tracking/tracker.py --budget

================================================================================
BUDGET STATUS
================================================================================
  Monthly Limit:    $10.00
  Spent:            $1.2468 (12.5%)
  Remaining:        $8.7532
  Projected:        $3.94

  Days Elapsed:     11
  Days Remaining:   19

  Status:           ✓ Within budget
```

### Cost Breakdown

```bash
$ python3.9 cost_tracking/tracker.py --breakdown

================================================================================
COST BREAKDOWN BY OPERATION (Last 30 days)
================================================================================
Operation                 Calls      Tokens          Cost        Avg/Call
--------------------------------------------------------------------------------
event_analysis            203        166,920      $1.2468      $0.006140
test_runs                 5          2,450        $0.0183      $0.003660
```

### Daily Trend

```bash
$ python3.9 cost_tracking/tracker.py --trend --days 7

================================================================================
DAILY COST TREND (Last 7 days)
================================================================================
Date         Calls      Tokens          Cost
--------------------------------------------------
2025-11-11   15         12,350       $0.0923
2025-11-10   22         18,120       $0.1354
2025-11-09   18         14,810       $0.1107
2025-11-08   14         11,520       $0.0861
2025-11-07   19         15,630       $.1167
2025-11-06   21         17,240       $0.1288
2025-11-05   17         13,980       $0.1044
```

---

## Budget Alerts

### Setting Alerts

```bash
# Set $10/month budget with 80% alert threshold
python3.9 cost_tracking/tracker.py --set-budget 10.00
```

Default alert threshold: **80%**
- Alert triggers when you've spent 80% of budget
- Helps avoid overspending

### Budget Status Indicators

```
✓ Within budget              # Projected < limit
⚠️ Projected to exceed!       # Projected > limit
⚠️ 85% of budget used!        # Alert threshold reached
```

---

## Cost Optimization Tips

### 1. Filter Events Before Analysis

```bash
# Only analyze high-priority events
python3.9 agents/analyzer.py --limit 5  # vs --limit 20
```

Savings: 75% reduction in API calls

### 2. Batch Analysis

Analyzer already batches efficiently - no action needed.

### 3. Adjust Analysis Frequency

```bash
# Daily analysis (20 events)
Cost: ~$0.12/day = $3.60/month

# Every other day (20 events)
Cost: ~$0.12 every 2 days = $1.80/month
```

### 4. Monitor Cost Per Event

```bash
python3.9 cost_tracking/tracker.py --breakdown
```

If average cost > $0.008:
- Prompts may be too long
- Consider shorter summaries

---

## Database Location

**File**: `cost_tracking.db` (in project root)

**Schema**:
```
api_calls         # Individual call records
daily_summary     # Daily aggregates (future)
budget            # Budget configuration
```

**Size**: ~100 KB per 1,000 calls (very small)

---

## Integration Points

Cost tracking is integrated into:

1. **SignificanceAnalyzer** (`analysis/significance.py`)
   - Every `analyze_event()` call is logged
   - Automatic, zero-config

2. **Future Integrations** (easy to add):
   - NewsAPI calls (if you track those)
   - Any other paid APIs

---

## Monthly Cost Examples

### Light Usage (10 events/day)
- 300 events/month
- ~$1.80/month

### Medium Usage (20 events/day)
- 600 events/month
- ~$3.60/month

### Heavy Usage (50 events/day)
- 1,500 events/month
- ~$9.00/month

**All well within reasonable budgets!**

---

## Troubleshooting

### "No data available"

Run some analyses first:
```bash
python3.9 agents/collector.py --hn-limit 10
python3.9 agents/analyzer.py --limit 5
python3.9 cost_tracking/tracker.py
```

### Budget not showing

Set a budget first:
```bash
python3.9 cost_tracking/tracker.py --set-budget 10.00
```

### Costs seem high

Check breakdown:
```bash
python3.9 cost_tracking/tracker.py --breakdown
```

Look for:
- Unusually high token counts
- Repeated test runs
- Failed calls (still cost money)

---

## Comparison: Cost vs Value

### What You Pay
- **AI-Pulse**: ~$3.60/month for 20 events/day
- Autonomous reasoning
- Investment insights
- Historical context

### Alternatives
- **Bloomberg Terminal**: $2,000/month
- **Financial news services**: $50-500/month
- **Manual research**: Hours of your time

**ROI**: If it saves you 1 hour/month, it's worth it!

---

## Privacy & Security

- **Cost data stays local**: SQLite database on your machine
- **No external reporting**: Data never leaves your computer
- **API key security**: Never logged in cost database

---

## Future Enhancements

Planned features:
- 📧 **Email alerts** when budget threshold reached
- 📊 **Web dashboard** for cost visualization
- 🎯 **Cost per insight** metrics (cost vs significance score)
- 💡 **Optimization suggestions** (reduce costs automatically)
- 📈 **Historical comparison** (this month vs last month)

---

## Summary

**Zero-config cost tracking** for AI-Pulse:
- ✅ Automatic logging
- ✅ Budget management
- ✅ Detailed breakdowns
- ✅ Forecasting
- ✅ ~$3.60/month for daily intelligence

Track your spend. Stay in budget. No surprises.
