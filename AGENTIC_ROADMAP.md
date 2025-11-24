# AI-Pulse Agentic Roadmap

## Vision

Transform AI-Pulse from a scheduled automation into a **self-improving agentic codebase** where:
1. You raise GitHub Issues describing what you want
2. An agent autonomously implements the change
3. The agent tests and validates the change
4. A PR is created for your review (or auto-merged if trusted)
5. The system learns from outcomes and improves its own accuracy

---

## Current State (2025-11-22)

### What's Built

**Phase 1: Automated Data Pipeline** ✅

| Component | Status | Details |
|-----------|--------|---------|
| Scheduled collection | ✅ | GitHub Actions, 1pm GMT daily |
| 6 data sources | ✅ | HackerNews, NewsAPI, SEC, GitHub, Company IR, ArXiv |
| Semantic deduplication | ✅ | Claude Haiku identifies duplicates |
| Significance scoring | ✅ | Claude Sonnet scores 0-100 |
| Sentiment analysis | ✅ | Positive/negative/neutral/mixed |
| HTML briefing generation | ✅ | Automated with charts |
| Market data collection | ✅ | 9:30pm GMT Mon-Fri |
| GitHub Pages publishing | ✅ | Public briefings repo |
| Database persistence | ✅ | Committed to private repo |
| Discord notifications | ⚠️ | Needs /github suffix fix |

**Architecture:**
```
Private Repo: mat-e-exp/ai-pulse
├── Code, config, database
├── GitHub Actions (scheduled)
└── Pushes briefings to ↓

Public Repo: mat-e-exp/ai-pulse-briefings
├── HTML briefings only
└── GitHub Pages serves to web
```

**What It Does Daily:**
```
1pm GMT: Collect → Deduplicate → Analyze → Generate → Publish
9:30pm GMT (Mon-Fri): Collect market data → Update correlation
```

**Phase 4: Issue-Driven Agent** ✅ (2025-11-24)

| Component | Status | Details |
|-----------|--------|---------|
| issue-handler.yml | ✅ | Triggers on `directive:*` labels |
| issue_agent.py | ✅ | Claude parses issue, generates code |
| Preview deployment | ✅ | `/preview/` subdirectory |
| promote-prod.yml | ✅ | `promote:prod` label deploys to root |
| reject-change.yml | ✅ | `rejected` label closes PR + issue |
| Discord notifications | ✅ | DISCORD_WEBHOOK_APPROVALS |

**Label System:**
- `directive:ui` → HTML reporter, CSS
- `directive:source` → News/event sources
- `directive:data` → Market data, charts
- `directive:config` → Parameters, thresholds
- `directive:prompt` → Analysis prompts
- `promote:prod` → Deploy preview to production
- `rejected` → Close PR and issue

### What's NOT Built

- Self-improvement loop (agent improves its own accuracy)
- Outcome tracking (validating predictions)
- Accuracy measurement
- Config-driven parameters (YAML instead of hardcoded)
- Backtest harness

---

## The Ambition

### Issue-Driven Development

**You want:**
```
1. Create GitHub Issue: "Add Reuters as news source"
2. Agent automatically:
   - Reads and understands the issue
   - Writes the code changes
   - Tests the implementation
   - Creates a PR with reasoning
3. You review and approve (or it auto-merges)
```

**Also:**
```
1. Create GitHub Issue: "Regulatory news seems underweighted"
2. Agent automatically:
   - Analyzes historical accuracy for regulatory news
   - Proposes config/prompt changes
   - Backtests against historical data
   - Creates PR showing accuracy improvement
```

### Self-Improving Accuracy

**Weekly cycle:**
```
1. Load 90 days of predictions + actual market outcomes
2. Calculate accuracy: "Did positive sentiment → market up?"
3. Identify systematic errors
4. Propose improvements to prompts/config
5. Backtest improvements
6. Create PR if accuracy improves
7. You approve (or auto-merge if trusted)
```

---

## Roadmap to Get There

### Phase 2: Outcome Tracking (Foundation for Learning)

**Purpose:** Can't improve what you don't measure.

| Task | Description | Effort |
|------|-------------|--------|
| Prediction logger | Record each day's sentiment prediction | 1 day |
| Outcome collector | Record actual market movement | 1 day |
| Accuracy calculator | Compare predictions vs reality | 1 day |
| Accuracy dashboard | Visualize accuracy over time | 1 day |

**Deliverable:** System knows how accurate its predictions are.

---

### Phase 3: Config-Driven Parameters

**Purpose:** Enable agents to modify behavior without changing code.

| Task | Description | Effort |
|------|-------------|--------|
| `config/sources.yaml` | Source weights, enable/disable | 0.5 day |
| `config/scoring.yaml` | Significance weights by category | 0.5 day |
| `config/thresholds.yaml` | Alert thresholds, dedup settings | 0.5 day |
| `prompts/*.md` | LLM prompts as editable files | 0.5 day |

**Deliverable:** Agents can tune behavior by editing YAML/markdown, not Python.

---

### Phase 4: Issue-Driven Agent

**Purpose:** You create issues, agent implements.

| Task | Description | Effort |
|------|-------------|--------|
| Issue monitor workflow | Triggers on issue creation with label | 0.5 day |
| Issue parser | Claude reads issue, extracts intent | 1 day |
| Code generator | Claude writes implementation | 2 days |
| Test runner | Validates changes don't break things | 1 day |
| PR creator | Commits to branch, opens PR | 0.5 day |

**Deliverable:** Create issue → Agent creates PR.

**Labels for different actions:**
- `directive:ui` - Change output format/styling (HTML, CSS)
- `directive:source` - Add/modify news/event data sources
- `directive:data` - Add/modify market data, charts, metrics
- `directive:config` - Change parameters/thresholds
- `directive:prompt` - Modify analysis prompts

**Promotion labels:**
- `promote:prod` - Deploy previewed changes to production
- `rejected` - Close PR and issue (change not wanted)

---

### Phase 5: Self-Improvement Loop

**Purpose:** Agent improves its own accuracy automatically.

| Task | Description | Effort |
|------|-------------|--------|
| Improvement agent | Analyzes accuracy gaps | 2 days |
| Backtest harness | Test changes against history | 2 days |
| Change validator | Ensure changes are safe | 1 day |
| Auto-PR system | Create PRs with reasoning | 1 day |
| Autonomy controls | Configure auto-merge rules | 0.5 day |

**Deliverable:** Weekly improvement cycle runs automatically.

---

### Phase 6: Security & Guardrails

**Purpose:** Safe autonomous operation.

| Task | Description | Effort |
|------|-------------|--------|
| Sandboxed modifications | Agents can only change prompts/config | 1 day |
| Change validation | Block dangerous code patterns | 1 day |
| Budget enforcement | Hard limits on API costs | 0.5 day |
| Anomaly detection | Alert on unusual behavior | 0.5 day |
| Audit logging | Track all agent actions | 0.5 day |

**Deliverable:** Safe to increase autonomy level.

---

## Autonomy Levels

| Level | What Agent Can Do | Human Role |
|-------|-------------------|------------|
| 1 | Suggest changes only | You implement |
| 2 | Create PRs | You approve every PR |
| 3 | Auto-merge if backtest passes | You review weekly summary |
| 4 | Full autonomy with rollback | You monitor dashboard |

**Current level: 0** (no autonomous changes)

**Target: Level 2** (agent creates PRs, you approve)

---

## Effort Summary

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| 2 | Outcome Tracking | 4 days | None |
| 3 | Config-Driven | 2 days | None |
| 4 | Issue-Driven Agent | 5 days | Phase 3 |
| 5 | Self-Improvement | 6 days | Phase 2, 3, 4 |
| 6 | Security | 4 days | Phase 4, 5 |

**Total: ~21 days of work**

---

## Next Steps

1. **Decide priority**: Issue-driven agent (Phase 4) or accuracy tracking (Phase 2) first?
2. **Phase 3 (Config)** is quick and unblocks both paths
3. Start building incrementally

---

## Files That Will Be Added

```
ai-pulse/
├── .github/workflows/
│   ├── daily-collection.yml      # ✅ Exists
│   ├── market-close.yml          # ✅ Exists
│   ├── issue-handler.yml         # 🔲 Phase 4
│   └── weekly-improvement.yml    # 🔲 Phase 5
├── config/
│   ├── sources.yaml              # 🔲 Phase 3
│   ├── scoring.yaml              # 🔲 Phase 3
│   └── thresholds.yaml           # 🔲 Phase 3
├── prompts/
│   ├── significance.md           # 🔲 Phase 3
│   └── sentiment.md              # 🔲 Phase 3
├── agents/
│   ├── collector.py              # ✅ Exists
│   ├── analyzer.py               # ✅ Exists
│   ├── improvement_agent.py      # 🔲 Phase 5
│   └── issue_agent.py            # 🔲 Phase 4
├── evaluation/
│   ├── outcome_tracker.py        # 🔲 Phase 2
│   ├── accuracy_calculator.py    # 🔲 Phase 2
│   └── backtest.py               # 🔲 Phase 5
└── data/
    ├── outcomes/                  # 🔲 Phase 2
    └── metrics/                   # 🔲 Phase 2
```

---

## Key Design Decisions

### Why GitHub Issues for Directives?

- Familiar interface (you already use GitHub)
- Built-in tracking and history
- Labels for categorization
- Comments for discussion
- Links to PRs for traceability

### Why Config Files for Parameters?

- Git-tracked (history, rollback)
- Easy for agents to modify
- Human-readable
- No code changes for parameter tweaks

### Why Weekly Improvement Cycle?

- Daily is too noisy
- Monthly is too slow to learn
- Weekly balances responsiveness with stability
- Enough data accumulates between cycles

### Why Human Approval Gate?

- Trust must be earned
- Start supervised, increase autonomy over time
- Catch systematic errors early
- Maintain human accountability for investment decisions

---

## Model Options & Upgrade Path

### Current: Haiku Beta (2025-11-22)

All analysis uses Claude Haiku 3.5 for cost optimization during beta phase.

| Model | Input/Output (per 1M tokens) | Per Event* | 50/day | Monthly |
|-------|------------------------------|------------|--------|---------|
| **Haiku 3.5 (current)** | $0.80 / $4.00 | ~$0.002 | $0.10 | **~$3** |
| Sonnet 3.5/4 | $3.00 / $15.00 | ~$0.08 | $4.00 | ~$120 |
| Opus 3/4 | $15.00 / $75.00 | ~$0.40 | $20.00 | ~$600 |

*Estimated per event: ~500 input tokens, ~800 output tokens

### When to Upgrade

**Stay with Haiku if:**
- Sentiment accuracy is acceptable
- Significance scores are reasonable
- Cost is primary concern

**Upgrade to Sonnet if:**
- Analysis reasoning seems shallow
- Significance scores are inconsistent
- Need better investment implications
- Budget allows ~$120/month

**Upgrade to Opus if:**
- Need highest quality reasoning
- Complex multi-factor analysis required
- Budget allows ~$600/month

### How to Upgrade

Change `ANALYSIS_MODEL` in `analysis/significance.py`:

```python
# Current (Haiku beta)
ANALYSIS_MODEL = "claude-3-5-haiku-20241022"

# Upgrade to Sonnet
ANALYSIS_MODEL = "claude-sonnet-4-20250514"

# Upgrade to Opus
ANALYSIS_MODEL = "claude-opus-4-20250514"
```

### Hybrid Approach (Future)

Could implement selective upgrades:
- Haiku for initial filtering
- Sonnet for high-priority events only
- Manual Sonnet re-analysis on demand

This would give quality where needed while keeping costs low.
