#!/bin/bash
# AI-Pulse Daily Briefing Generator
# Run this once per day to generate a complete briefing with sentiment and market data

set -e  # Exit on any error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "AI-PULSE DAILY BRIEFING GENERATOR"
echo "================================================================================"
echo ""

# Get yesterday's date for market data (market closes after briefing runs)
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

# Step 1: Collect news and events
echo -e "${BLUE}[1/6] Collecting news and events...${NC}"
python3.9 agents/collector.py \
    --hn-limit 20 \
    --news-limit 30 \
    --sec-days 7 \
    --github-days 7 \
    --github-stars 500 \
    --ir-days 7

echo ""

# Step 2: Semantic deduplication
echo -e "${BLUE}[2/6] Running semantic deduplication...${NC}"
python3.9 agents/semantic_deduplicator.py --days 7

echo ""

# Step 3: Analyze events with Claude
echo -e "${BLUE}[3/6] Analyzing events for significance...${NC}"
python3.9 agents/analyzer.py --limit 50

echo ""

# Step 4: Collect market data
echo -e "${BLUE}[4/6] Collecting market data for ${YESTERDAY}...${NC}"
python3.9 agents/market_collector.py --date "$YESTERDAY" --db ai_pulse.db

echo ""

# Step 5: Calculate sentiment-market correlation
echo -e "${BLUE}[5/6] Calculating sentiment-market correlation...${NC}"
python3.9 agents/correlation_calculator.py --days 30 --db ai_pulse.db

echo ""

# Step 6: Publish briefing
echo -e "${BLUE}[6/6] Publishing briefing...${NC}"
python3.9 publish_briefing.py --days 1 --min-score 40

echo ""
echo "================================================================================"
echo -e "${GREEN}✓ DAILY BRIEFING COMPLETE${NC}"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "  1. Review the briefing at: file://$SCRIPT_DIR/index.html"
echo "  2. Commit and push to GitHub:"
echo "     git add ."
echo "     git commit -m \"Daily briefing $TODAY\""
echo "     git push"
echo ""
