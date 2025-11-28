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

### Never Commit Database Manually
❌ **NEVER commit ai_pulse.db from your local machine**
- Database is in .gitignore to prevent accidental commits
- Only GitHub Actions commits database (using `git add -f`)
- Your local copy is ALWAYS stale (workflows update it 3x daily: 6am, 1:30pm, 9:30pm)
- **Server-side enforcement**: GitHub will reject any push containing database changes unless from authorized workflows

**Before ANY code changes:**
```bash
git pull  # Get latest database from workflows
```

**When making code changes:**
```bash
# Edit your code
vim agents/something.py

# Commit ONLY code files (database auto-ignored)
git add agents/something.py
git commit -m "Description"
git push
```

**Why**: Committing stale local database overwrites live data from workflows, causing data loss. This happened 2025-11-28: commit 698491d accidentally reverted database from 494 events (through Nov 28) to 273 events (through Nov 26), losing 175 events.

**Emergency database repair** (rare):
If database needs manual fixing (data corruption, backfilling):
1. Make changes locally
2. Commit with `git add -f ai_pulse.db`
3. Push will fail with validation error
4. Go to: GitHub Actions → "Validate Database Commits" → Run workflow
5. Check "Allow database commit" box
6. Push again - will be accepted
7. Document what was changed and why

---

## 🔍 DATABASE QUERY PROTOCOL

### ALWAYS Query Git Database - NEVER Local Copy

**The git database is the single source of truth.** Your local copy is ALWAYS stale.

**MANDATORY command for EVERY database query:**
```bash
git show HEAD:ai_pulse.db > /tmp/git_db.db && sqlite3 /tmp/git_db.db "YOUR QUERY"
```

**Why:**
- GitHub Actions workflows update database 3x daily (6am, 1:30pm, 9:30pm GMT)
- Local `ai_pulse.db` could be hours or days out of date
- Git HEAD contains the live database maintained by workflows
- Local database is in .gitignore and treated as cache only

**Examples:**

❌ **WRONG - queries stale local copy:**
```bash
sqlite3 ai_pulse.db "SELECT COUNT(*) FROM events;"
```

✅ **CORRECT - queries source of truth:**
```bash
git show HEAD:ai_pulse.db > /tmp/git_db.db && sqlite3 /tmp/git_db.db "SELECT COUNT(*) FROM events;"
```

**BEFORE EVERY DATABASE OPERATION:**
1. ✅ Am I using `git show HEAD:ai_pulse.db`?
2. ✅ Am I writing to `/tmp/` not local directory?
3. ❌ Am I querying `ai_pulse.db` directly? (STOP - use git version)

**Exception:** The ONLY time to query local database is when explicitly testing local-only code changes before committing. Never query local database for production state.

---

## 📅 Daily Schedule

| Time (GMT) | Workflow | What Happens |
|------------|----------|--------------|
| 6:00am | morning-collection.yml | Collect overnight news → Analyze → Discord top 10 |
| 1:30pm | daily-collection.yml | Collect more news → Analyze → **Log prediction** → Publish HTML → Discord |
| 2:30pm | Market opens | **Predictions locked** (can't update after this) |
| 9:00pm | Market closes | Outcomes recorded |
| 9:30pm Mon-Fri | market-close.yml | Collect market data → Calculate prediction accuracy → Discord |

**Note**: Workflows run every day including weekends/holidays. Market status is automatically detected - if market is closed, prediction is marked as 'closed' and accuracy calculation is skipped.

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
- **Need to check database state?** → `git show HEAD:ai_pulse.db > /tmp/git_db.db && sqlite3 /tmp/git_db.db "..."`
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
- Check audit trail: `git show HEAD:ai_pulse.db > /tmp/git_db.db && sqlite3 /tmp/git_db.db "SELECT * FROM prediction_audit WHERE date='YYYY-MM-DD'"`
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
