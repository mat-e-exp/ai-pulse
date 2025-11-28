# AI-Pulse Development History

## Development Phases

### Phase 1: Basic Collector ✅ COMPLETE

**Goal**: Collect events from multiple sources into SQLite database

**Completed**:
- ✅ Project structure
- ✅ Hacker News integration
- ✅ NewsAPI integration
- ✅ Tech RSS Feeds (TechCrunch, VentureBeat, The Verge, Ars Technica, MIT Tech Review, Wired, AI News)
- ✅ SEC EDGAR integration (8-K filings for material events)
- ✅ GitHub trending integration (AI repos, releases)
- ✅ Company IR RSS integration (NVIDIA, AMD press releases)
- ✅ ArXiv API integration (AI/ML research papers)
- ✅ SQLite storage with UNIQUE constraints
- ✅ Cost tracking database

**Result**: 7 data sources feeding events table

---

### Phase 2: Intelligence Layer ✅ COMPLETE

**Goal**: Add autonomous significance scoring and reasoning

**Completed**:
- ✅ Claude API integration (initially Sonnet)
- ✅ Significance scoring (0-100)
- ✅ Sentiment analysis (positive/negative/neutral/mixed)
- ✅ "Why does this matter?" reasoning
- ✅ Competitive impact analysis
- ✅ Investment implications assessment
- ✅ Intelligent briefing generation
- ✅ Cost tracking with budget management

**Result**: Events analyzed with significance scores and implications

---

### Phase 2.5: Web Publishing & Deduplication ✅ COMPLETE (2025-11-12)

**Goal**: Public-facing briefings with accurate sentiment tracking

**Completed**:
- ✅ Static HTML briefing generation
- ✅ Chart.js sentiment visualization
- ✅ Percentage-based sentiment tracking (0-100% instead of raw counts)
- ✅ 30-day sentiment trend chart with event count tooltips
- ✅ Content-based deduplication at collection time (75% title similarity)
- ✅ Retroactive deduplication script for historical data
- ✅ Automatic publishing workflow (briefings/ + index.html + archive.html)
- ✅ Split repository architecture (private code, public HTML)
- ✅ GitHub Pages hosting
- ✅ Discord notifications

**Result**: Daily briefings published to https://ai-pulse.aifinto.com

---

### Phase 2.6: Semantic Deduplication ✅ COMPLETE (2025-11-12)

**Goal**: Catch duplicates that string matching misses

**Problem**: Same story reported with different wording
- "SoftBank sells Nvidia stake"
- "SoftBank profits double"
- "SoftBank unloads stake"
- "SoftBank rides AI wave"
All 4 are about the same event but have <75% title similarity

**Solution**:
- ✅ Claude-powered semantic dedup using Haiku (cheap, fast)
- ✅ Identifies duplicates string matching misses
- ✅ Runs before analysis to prevent waste and ensure accuracy
- ✅ New field: `is_semantic_duplicate` (separate from `is_duplicate`)

**Testing** (2025-11-11 data):
- Found 4 semantic duplicates in 2 groups
- SoftBank group: 4 events → 1 unique
- Intel CTO group: 2 events → 1 unique
- Sentiment recalculated: 61 events → 57 unique events
- Cost: ~$0.002 per date with Haiku

**Result**: Trustworthy sentiment percentages for investment decisions

---

### Phase 2.7: Haiku Beta Mode ✅ COMPLETE (2025-11-22)

**Goal**: Reduce costs by 98% without sacrificing quality

**Problem**: Running Sonnet for all analysis = ~$120/month

**Solution**:
- ✅ Switch all analysis to Haiku (~$0.002/event)
- ✅ Keep same prompts and quality standards
- ✅ Monitor quality, upgrade to Sonnet/Opus if needed

**Cost Comparison**:
| Model | Per Event | 50 events/day | Monthly |
|-------|-----------|---------------|---------|
| **Haiku (current)** | ~$0.002 | $0.10/day | **~$3/month** |
| Sonnet | ~$0.08 | $4.00/day | ~$120/month |
| Opus | ~$0.40 | $20.00/day | ~$600/month |

**Result**: 98% cost reduction, sustainable economics

---

### Phase 2.8: Prediction Tracking ✅ COMPLETE (2025-11-24)

**Goal**: Test if overnight AI news predicts same-day market

**Workflow**:
1. **6am GMT**: Morning collection → Analyze → Discord top 10
2. **1:30pm GMT**: Log prediction based on sentiment (BEFORE market opens)
3. **2:30pm GMT**: US market opens
4. **9pm GMT**: US market closes
5. **9:30pm GMT**: Collect market data → Calculate prediction accuracy

**Database**:
- `predictions` table (date, sentiment, prediction, confidence)
- `market_data` table (date, open, close, change_pct)
- `daily_sentiment` table (sentiment aggregates)

**Result**: Foundation for prediction accuracy tracking

---

### Phase 2.9: Safety Features ✅ COMPLETE (2025-11-26)

**Goal**: Protect prediction accuracy data from human error

**Problem**: `publish_briefing.py` couples HTML generation with prediction logging
- If run before data collection completes → logs prediction with incomplete data
- If run after market opens → logs "prediction" AFTER market moved
- No way to regenerate HTML safely for web changes

**Solution**:
- ✅ Prediction locking after market opens (2:30pm GMT)
- ✅ Timestamp preservation (`first_logged_at` never changes)
- ✅ Audit trail (`prediction_audit` table logs every change)
- ✅ Duplicate run detection (`workflow_runs` table)
- ✅ Idempotent operations (safe to rerun)
- ✅ `regenerate_html.py` - safe HTML-only regeneration
- ✅ Database migration with backfill

**Result**: Prediction data protected, safe web publishing workflow

**Details**: See [safety.md](safety.md)

---

## Future Phases

### Phase 3: Narrative Tracking (Planned)

**Goal**: Track sentiment shifts over time

- Detect narrative changes (e.g., "AI hype" → "AI skepticism")
- Historical pattern matching
- Cross-event reasoning
- Trend analysis

### Phase 4: Full Autonomy (Vision)

**Goal**: Self-improving agentic system

- Real-time monitoring (vs twice daily)
- Automated alert prioritization
- Multi-step investigation workflows
- Proactive deep-dives
- Self-improvement loop (agent improves its own accuracy)
- Issue-driven automation (agent implements from GitHub Issues)

**See**: `AGENTIC_ROADMAP.md` for full vision

---

## Key Milestones

| Date | Milestone |
|------|-----------|
| 2025-11-11 | First duplicate events detected (SoftBank story x6) |
| 2025-11-12 | Public briefings live on GitHub Pages |
| 2025-11-12 | Semantic deduplication implemented |
| 2025-11-12 | Split repository architecture (private/public) |
| 2025-11-22 | Switched to Haiku (98% cost reduction) |
| 2025-11-24 | Prediction tracking launched |
| 2025-11-24 | Daily workflow automation complete (6am, 1:30pm, 9:30pm) |
| 2025-11-26 | Safety features implemented |
| 2025-11-26 | Documentation refactored |
| 2025-11-28 | Market status tracking for weekends/holidays |
| 2025-11-28 | Reuters AI news added (8th RSS source via Google News) |
| 2025-11-28 | Server-side database commit validation (branch protection) |
| 2025-11-28 | Database corruption incident: 175 events lost, then restored |

---

## Lessons Learned

### Deduplication is Critical
**Problem**: SoftBank story appeared 6+ times on 2025-11-11
**Impact**: Sentiment skewed to "mixed: 38%" instead of true "mixed: 20%"
**Solution**: 5-layer deduplication (DB constraints, URL tracking, string matching, semantic dedup, publishing filter)

### Cost Matters for Sustainability
**Problem**: Sonnet analysis = $120/month unsustainable for MVP
**Solution**: Haiku provides 90% of quality at 2% of cost
**Result**: $3/month = sustainable for long-term operation

### Prediction Accuracy Requires Protection
**Problem**: Accidentally running `publish_briefing.py` at wrong time corrupts data
**Solution**: Prediction locking, audit trails, safe HTML regeneration
**Result**: Investment-grade data integrity

### Separation of Concerns
**Problem**: Single script doing HTML generation + database writes = dangerous
**Solution**: Split into `regenerate_html.py` (safe) and `publish_briefing.py` (scheduled only)
**Result**: Safe web publishing workflow

### Market Closures Require Graceful Handling
**Problem**: Thanksgiving (and weekends/holidays) cause prediction logging without market outcomes
**Solution**: Automatic market status detection via data collection success/failure (Option 3: graceful degradation)
**Result**: No manual holiday calendar maintenance, self-correcting system, accuracy stats only include trading days

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Operational guide
- [architecture.md](architecture.md) - System design
- [safety.md](safety.md) - Safety features
- [deduplication.md](deduplication.md) - 5-layer dedup system
