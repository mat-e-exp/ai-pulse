# AI-PULSE - Operational Guide

Real-time intelligence agent for AI sector investment decisions. Tracks product launches, funding, technical breakthroughs, and market sentiment.

**Live site**: https://ai-pulse.aifinto.com

---

## 🚨 CRITICAL RULES

### Never Rerun Workflows
❌ **NEVER manually trigger scheduled workflows**
- `morning-collection.yml` - 6am GMT only
- `daily-collection.yml` - 1:30pm GMT only
- `market-close.yml` - 9:30pm GMT Mon-Fri only

**Why**: Rerunning workflows corrupts prediction accuracy data (logs predictions AFTER market moves)

### Never Run publish_briefing.py Manually
❌ **NEVER run `publish_briefing.py` outside scheduled workflows**

**Why**: It logs predictions based on current database state. If run before data collection completes, logs prediction with incomplete data.

---

## 📅 Daily Schedule

| Time (GMT) | Workflow | What Happens |
|------------|----------|--------------|
| 6:00am | morning-collection.yml | Collect overnight news → Analyze → Discord top 10 |
| 1:30pm | daily-collection.yml | Collect more news → Analyze → **Log prediction** → Publish HTML → Discord |
| 2:30pm | Market opens | **Predictions locked** (can't update after this) |
| 9:00pm | Market closes | Outcomes recorded |
| 9:30pm Mon-Fri | market-close.yml | Collect market data → Calculate prediction accuracy → Discord |

---

## 🛠️ Common Tasks

### Making Web Changes

**Two types of changes:**

#### 1. Static Files (about.html, style.css, CNAME)
```bash
# 1. Pull latest
git pull

# 2. Edit the file directly
vim about.html  # or style.css

# 3. Commit and push
git add about.html
git commit -m "Update about page"
git push

# 4. Deploy to live site
# Go to: GitHub Actions → "Deploy Assets to Public Site" → Run workflow
```
**No regeneration needed** - these files don't come from database

#### 2. HTML Templates (Navigation, Layout Changes)
```bash
# 1. Pull latest
git pull

# 2. Edit template
vim agents/html_reporter.py  # or publish_briefing.py (archive.html)

# 3. Regenerate HTML from database (safe - no DB writes)
python3.9 regenerate_html.py --days 7 --min-score 40

# 4. Commit and push
git add agents/html_reporter.py index.html briefings/*.html archive.html
git commit -m "Update navigation"
git push

# 5. Deploy to live site
# Go to: GitHub Actions → "Deploy Assets to Public Site" → Run workflow
```
**Regeneration needed** - templates generate index.html, archive.html, briefings/*.html

### Testing Locally

**Safe operations (read-only):**
```bash
# View briefing
open index.html

# Generate Discord preview (no DB writes)
python3.9 agents/discord_morning.py
cat discord_test.txt
```

**HTML regeneration (safe - no DB writes):**
```bash
python3.9 regenerate_html.py --days 7 --min-score 40
```
- ✅ Only reads database
- ✅ Only writes HTML
- ❌ No data collection
- ❌ No prediction logging

**❌ AVOID:**
```bash
# DANGEROUS - writes to database, logs predictions
python3.9 publish_briefing.py --days 7 --min-score 40
```

### Testing Data Collection

**Safe - run individual agents:**
```bash
# Test collector (dry-run mode)
python3.9 agents/collector.py --limit 10

# Test analyzer
python3.9 agents/analyzer.py --limit 5

# Test deduplicator
python3.9 agents/semantic_deduplicator.py --days 1
```

---

## 🔒 Safety Features

The system protects prediction accuracy with:

1. **Prediction Locking** - After market opens (2:30pm GMT), predictions can't be updated
2. **Timestamp Preservation** - `first_logged_at` never changes, even if regenerated
3. **Audit Trail** - Every prediction change logged in `prediction_audit` table
4. **Duplicate Detection** - Warns if workflow runs twice in one day
5. **Idempotent Operations** - Safe to run scripts multiple times (overwrites, not duplicates)

See [docs/safety.md](docs/safety.md) for technical details.

---

## 📂 Repository Structure

```
Private: mat-e-exp/ai-pulse
├── agents/              # Collection, analysis, reporting
├── sources/             # Data source integrations
├── storage/             # Database and safety utilities
├── .github/workflows/   # Scheduled automation
├── ai_pulse.db          # SQLite database
├── index.html           # Latest briefing
├── archive.html         # Briefing list
├── briefings/           # Daily briefings
├── style.css            # Shared styles
└── regenerate_html.py   # Safe HTML regeneration

Public: mat-e-exp/ai-pulse-briefings
├── index.html
├── archive.html
├── briefings/
└── style.css
(Served via GitHub Pages)
```

---

## 🔧 Key Scripts

### regenerate_html.py (Safe)
```bash
python3.9 regenerate_html.py --days 7 --min-score 40
```
- Reads from database
- Generates HTML files
- **No database writes**
- **No prediction logging**
- Use for: Web changes, navigation updates

### publish_briefing.py (Dangerous)
```bash
python3.9 publish_briefing.py --days 7 --min-score 40
```
- ⚠️ **AVOID RUNNING MANUALLY**
- Writes to database tables
- Logs predictions
- Only use: In scheduled workflows
- Never use: For testing or web changes

---

## 📋 Quick Decision Tree

**I changed:**
- **Static file (about.html, style.css)?** → commit → push → `deploy-assets.yml`
- **HTML template (navigation, layout)?** → `regenerate_html.py` → commit → push → `deploy-assets.yml`
- **Just testing locally?** → `regenerate_html.py` (don't commit)
- **Data collection logic?** → Run individual agent scripts for testing
- **Need new data in briefing?** → Wait for 1:30pm workflow (don't run manually)
- **Something urgent/unclear?** → Ask first, check safety implications

---

## 🔗 Related Documentation

- [docs/architecture.md](docs/architecture.md) - System design and data flow
- [docs/safety.md](docs/safety.md) - Database schema and safety utilities
- [docs/api-limits.md](docs/api-limits.md) - API rate limits and constraints
- [docs/history.md](docs/history.md) - Development history and decisions
- [docs/diagrams.md](docs/diagrams.md) - Visual architecture diagrams
- [docs/deduplication.md](docs/deduplication.md) - 5-layer deduplication system

---

## 🆘 Troubleshooting

**Web page has no styling:**
- Check briefings use `href="../style.css"`, index.html uses `href="style.css"`
- Run `regenerate_html.py` to fix paths

**Duplicate events in briefing:**
- Check `is_duplicate` and `is_semantic_duplicate` flags
- Run semantic deduplicator: `python3.9 agents/semantic_deduplicator.py --days 7`

**GitHub Pages not updating:**
- Check deploy-assets.yml ran successfully
- Verify files copied to public repo
- GitHub Pages can take 2-5 minutes to update

**Prediction seems wrong:**
- Check `first_logged_at` timestamp (should be before 2:30pm GMT)
- Check audit trail: `sqlite3 ai_pulse.db "SELECT * FROM prediction_audit WHERE date='YYYY-MM-DD'"`
- Verify market wasn't open when prediction logged

---

## 🔐 Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...     # Claude API for analysis
NEWS_API_KEY=...                  # NewsAPI integration
ALPHA_VANTAGE_API_KEY=...         # Market data fallback

# GitHub Secrets
DISCORD_WEBHOOK_APPROVALS=...     # Discord notifications
BRIEFINGS_DEPLOY_KEY=...          # Deploy to public repo
```

---

## 📊 Primary Goal: ACCURACY

**Accuracy is the highest priority** - above speed, cost, or features.

Investment decisions depend on:
- No duplicate stories inflating sentiment
- Accurate sentiment distribution
- Reliable significance scores
- Predictions logged BEFORE market opens
- Outcomes recorded AFTER market closes

**Data corruption = unreliable investment signals**

---

## 🚦 Status

✅ **Production** - Automated daily pipeline running since 2025-11-12
- Morning collection (6am)
- Afternoon publish (1:30pm)
- Market close tracking (9:30pm Mon-Fri)
- Discord notifications
- Safety features active

See [docs/history.md](docs/history.md) for development timeline.
