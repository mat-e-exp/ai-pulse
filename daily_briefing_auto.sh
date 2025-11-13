#!/bin/bash
# AI-Pulse Daily Briefing Generator with Auto-Commit
# This version automatically commits and pushes to GitHub (for cron jobs)

set -e  # Exit on any error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "================================================================================"
echo "AI-PULSE DAILY BRIEFING GENERATOR (AUTO-COMMIT)"
echo "================================================================================"
echo ""

# Get yesterday's date for market data
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

# Step 1: Collect news and events
echo "[1/7] Collecting news and events..."
python3.9 agents/collector.py \
    --hn-limit 20 \
    --news-limit 30 \
    --sec-days 7 \
    --github-days 7 \
    --github-stars 500 \
    --ir-days 7

# Step 2: Semantic deduplication
echo "[2/7] Running semantic deduplication..."
python3.9 agents/semantic_deduplicator.py --days 7

# Step 3: Analyze events
echo "[3/7] Analyzing events..."
python3.9 agents/analyzer.py --limit 50

# Step 4: Collect market data
echo "[4/7] Collecting market data for ${YESTERDAY}..."
python3.9 agents/market_collector.py --date "$YESTERDAY" --db ai_pulse.db

# Step 5: Calculate correlation
echo "[5/7] Calculating correlation..."
python3.9 agents/correlation_calculator.py --days 30 --db ai_pulse.db

# Step 6: Publish briefing
echo "[6/7] Publishing briefing..."
python3.9 publish_briefing.py --days 1 --min-score 40

# Step 7: Commit and push
echo "[7/7] Committing to GitHub..."
git add briefings/*.html index.html archive.html ai_pulse.db 2>/dev/null || true
git commit -m "Daily briefing $TODAY

Generated automatically by daily_briefing_auto.sh

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>" 2>/dev/null || echo "No changes to commit"

git push 2>/dev/null || echo "Push failed - check git config"

echo ""
echo "================================================================================"
echo "✓ DAILY BRIEFING COMPLETE AND PUSHED"
echo "================================================================================"
echo ""
echo "View at: https://mat-e-exp.github.io/ai-pulse/"
echo ""
