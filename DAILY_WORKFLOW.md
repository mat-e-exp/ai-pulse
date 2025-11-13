# Daily Briefing Workflow

## Quick Start

### Option 1: Manual Run (Review Before Pushing)
```bash
./daily_briefing.sh
```
This runs the complete workflow and tells you to manually commit/push.

### Option 2: Auto Run (For Cron)
```bash
./daily_briefing_auto.sh
```
This runs everything AND automatically commits/pushes to GitHub.

## What These Scripts Do

Both scripts run the complete daily workflow:

1. **Collect news** from 5 sources (HN, NewsAPI, SEC, GitHub, Company IR)
2. **Semantic deduplication** to remove duplicate stories
3. **Analyze events** with Claude API for significance and sentiment
4. **Collect market data** for yesterday's trading day (10 symbols)
5. **Calculate correlation** between sentiment and market outcomes
6. **Publish briefing** to index.html with both charts
7. **Auto version only:** Commit and push to GitHub

## Scheduling with Cron

To run automatically every morning at 8 AM:

```bash
# Edit crontab
crontab -e

# Add this line:
0 8 * * * cd /Users/mat.edwards/dev/test-claude/ai-pulse && ./daily_briefing_auto.sh >> logs/daily_$(date +\%Y-\%m-\%d).log 2>&1
```

**Note:** Make sure to set up git credentials for passwordless push:
```bash
git config credential.helper store
git push  # Enter credentials once, then they're cached
```

## Manual Usage

If you prefer to run steps individually:

```bash
# 1. Collect & analyze sentiment
python3.9 agents/collector.py --hn-limit 20 --news-limit 30 --sec-days 7 --github-days 7 --github-stars 500 --ir-days 7
python3.9 agents/semantic_deduplicator.py --days 7
python3.9 agents/analyzer.py --limit 50

# 2. Collect market data (use yesterday's date)
python3.9 agents/market_collector.py --date 2025-11-13 --db ai_pulse.db

# 3. Calculate correlations
python3.9 agents/correlation_calculator.py --days 30 --db ai_pulse.db

# 4. Publish
python3.9 publish_briefing.py --days 1 --min-score 40

# 5. Commit
git add . && git commit -m "Daily briefing YYYY-MM-DD" && git push
```

## Troubleshooting

### Yahoo Finance Rate Limiting
If market data collection fails with "Too Many Requests":
- Wait 2-3 hours
- Try again with single date: `python3.9 agents/market_collector.py --date YYYY-MM-DD`

### No New Events
If analyzer finds 0 events:
- Check collector output - may be API limits
- Run collector again with same command
- Semantic dedup may have marked everything as duplicate (check with `--days 1` instead)

### Git Push Fails
Ensure git credentials are configured:
```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
git config credential.helper store
```

## Files Generated

- `briefings/YYYY-MM-DD.html` - Dated briefing
- `index.html` - Latest briefing (root)
- `archive.html` - List of all past briefings
- `ai_pulse.db` - Updated with new events and market data

## Optional: Prediction Insights (Weekly/Monthly)

To improve prediction accuracy over time, run the prediction analyst agent:

```bash
python3.9 agents/prediction_analyst.py --days 30
```

**What it does:**
- Analyzes historical sentiment vs market accuracy patterns
- Identifies which event types are most predictive
- Generates confidence factors for predictions
- Insights displayed in daily briefing

**When to run:**
- Weekly: Analyze last 30 days
- Monthly: Analyze last 90 days
- Cost: ~$0.10 per analysis (one Claude API call)

## Environment Variables Required

Create `.env` file with:
```bash
ANTHROPIC_API_KEY=sk-ant-...
NEWS_API_KEY=...  # Optional
```

## Viewing Results

**Local:**
- `file:///Users/mat.edwards/dev/test-claude/ai-pulse/index.html`

**GitHub Pages (after push):**
- `https://mat-e-exp.github.io/ai-pulse/`
- Wait 1-2 minutes for GitHub Pages to rebuild
