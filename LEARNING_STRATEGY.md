# AI-Pulse Learning Strategy

## Overview

This document outlines the multi-phase learning strategy for improving prediction accuracy as the AI-Pulse system gathers data over time.

## Why Not Traditional ML? (Current Analysis)

### Traditional ML Limitations for This Use Case

**1. Insufficient Data Volume**
- Traditional ML needs thousands of data points to train reliably
- Current state: ~3 days of correlation data (2-3 points)
- Even after months: 90 days = 90 data points (far too small for neural networks)
- Would need years of data before ML becomes viable

**2. High Dimensionality Problem**
- Features: event_type (10+ categories), sentiment (4 types), sentiment_strength (continuous), companies (100+), keywords (1000+)
- With 90 data points and 100+ features → severe overfitting
- Would learn noise, not patterns

**3. Expensive Infrastructure**
- Requires: model training pipeline, feature engineering, hyperparameter tuning, validation framework
- Cost: Developer time + compute resources >> Claude API costs
- Maintenance: Model retraining, drift detection, versioning

**4. Non-Stationary Data**
- Market dynamics change constantly (new companies, policy shifts, tech breakthroughs)
- Traditional ML models become stale quickly
- Would need continuous retraining

**5. Interpretability Gap**
- Neural networks are black boxes - you can't explain WHY a prediction has high confidence
- Investment decisions require explainable reasoning
- Traditional ML gives probabilities without context

### Why Claude API Is Better (For Now)

**Advantages:**
1. **Few-shot learning** - Claude can identify patterns from small datasets (30-90 points)
2. **Reasoning transparency** - Explains WHY patterns matter
3. **Context awareness** - Understands market dynamics, company relationships, temporal context
4. **Zero infrastructure** - No training pipeline, just API calls
5. **Adaptability** - Naturally handles new companies, events, market conditions
6. **Cost effective** - $0.10/analysis vs $1000s for ML infrastructure

**Current Approach:**
- Weekly: "Here's 30 days of data, what patterns do you see?"
- Claude: "Regulatory events with mixed sentiment show 75% accuracy because..."
- Human: Can validate the reasoning, not just trust a probability

## Multi-Phase Learning Strategy

### Phase 1 (Months 1-6): Pure Claude Learning ✅ *CURRENT*

**Status:** Implemented

**What:**
- Gather data, let Claude analyze weekly/monthly
- Build up dataset while getting useful insights
- Store insights in `prediction_insights` table

**Cost:** ~$5/month in API calls

**Benefits:**
- Immediate actionable confidence scores
- Explainable reasoning for predictions
- No infrastructure overhead

**Implementation:**
```bash
# Run weekly
python3.9 agents/prediction_analyst.py --days 30

# Run monthly for deeper analysis
python3.9 agents/prediction_analyst.py --days 90
```

**Current Capabilities:**
- Pattern recognition (which event types are most predictive)
- Sentiment reliability analysis (which sentiment types are accurate)
- Symbol responsiveness (which stocks react to AI news)
- Momentum pattern detection (continuations vs reversals)
- Confidence factor generation (high/medium/low scenarios)

### Phase 2 (Months 6-12): Statistical + Claude

**Trigger:** 180+ correlation data points

**Add Simple Statistical Models:**
- **Logistic regression** for binary prediction (market up/down)
- **Time series analysis** for sentiment momentum
- **Correlation matrices** for event type effectiveness
- **Baseline comparisons** (vs naive "yesterday's direction" predictor)

**Claude's Role:** Interpret statistical findings

**Cost:** Minimal compute, still cheap (~$10/month)

**Implementation Plan:**
1. Create `analysis/statistical_models.py`
2. Add correlation matrix visualization to briefings
3. Track prediction accuracy by category (event_type + sentiment)
4. Generate confidence intervals (not just high/medium/low)
5. A/B test: Claude predictions vs statistical baseline

**New Metrics to Track:**
- Prediction accuracy by event type
- Prediction accuracy by sentiment type
- Prediction accuracy by sentiment strength bands (0-33, 34-66, 67-100)
- Rolling 7/14/30-day accuracy rates
- Symbol-specific prediction accuracy

### Phase 3 (Year 2+): ML Models for Specific Patterns

**Trigger:** 500+ correlation data points

**Add Narrow ML Models:**
- **Gradient boosting (XGBoost)** for event significance scoring
- **LSTM** for sentiment time-series forecasting
- **Random forest** for multi-factor prediction confidence

**Claude's Role:** Strategic reasoning layer on top of ML predictions

**Cost:** ~$100/month compute

**Implementation Plan:**
1. Create `models/ml_predictor.py`
2. Feature engineering pipeline
3. Model training/validation framework
4. Hyperparameter tuning with cross-validation
5. Model versioning and drift detection
6. Claude interprets ML outputs for briefings

**Infrastructure Requirements:**
- Model training pipeline (possibly AWS SageMaker or local GPU)
- Feature store (extended database schema)
- Model registry (MLflow or similar)
- Monitoring dashboard for model performance

**When to Implement:**
- Statistical models show clear predictive signals (>60% accuracy)
- Patterns are stable over 3+ months
- You can afford ML engineer time ($10k+ investment)

### Phase 4 (Year 3+): Hybrid Ensemble

**Trigger:** 1000+ correlation data points, proven ML model accuracy

**Full Architecture:**
```
Data Collection
    ↓
Statistical Models (simple patterns)
    ↓
ML Models (complex patterns)
    ↓
Claude Analysis (reasoning + context)
    ↓
Human Decision (final judgment)
```

**Each Layer's Value:**
- **Statistics**: "Regulatory events correlate 0.72 with market drops"
- **ML**: "This specific regulatory event has 78% probability of market drop"
- **Claude**: "This regulation matters because it affects NVDA's China exports, historically these lead to 3-day selloffs, but current inventory levels suggest limited impact"
- **Human**: "We'll wait 24 hours to see market reaction before adjusting positions"

**Cost:** $200-500/month (compute + API calls)

**Implementation:**
- Ensemble prediction framework
- Model weight optimization
- Confidence interval aggregation
- Disagreement detection (when models conflict)
- Claude explains model disagreements

## Immediate Enhancements (Next 6 Months)

These can be added to Phase 1 without waiting for more data:

### 1. Baseline Tracking
Compare Claude predictions to naive baseline (yesterday's market direction).

**Implementation:**
```python
# agents/baseline_tracker.py
# Store naive predictions alongside Claude predictions
# Weekly comparison report
```

### 2. Category-Specific Learning
Separate analysis for each event type (regulatory, funding, product-launch, etc.).

**Implementation:**
```bash
# Run monthly
python3.9 agents/prediction_analyst.py --days 90 --event-type regulation
python3.9 agents/prediction_analyst.py --days 90 --event-type funding
```

### 3. Rolling Window Analysis
Analyze last 30/60/90 days separately to spot trend changes.

**Implementation:**
```bash
# Compare across windows
python3.9 agents/prediction_analyst.py --days 30 > insights_30d.txt
python3.9 agents/prediction_analyst.py --days 60 > insights_60d.txt
python3.9 agents/prediction_analyst.py --days 90 > insights_90d.txt
```

### 4. Prediction Confidence Database
Store Claude's confidence levels, track which were accurate.

**Schema Addition:**
```sql
CREATE TABLE prediction_confidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    event_type TEXT,
    sentiment TEXT,
    predicted_outcome TEXT,
    confidence_level TEXT, -- high/medium/low
    actual_outcome TEXT,
    was_accurate INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 5. Meta-Learning
Have Claude analyze its own prediction accuracy monthly.

**Implementation:**
```bash
# New agent
python3.9 agents/meta_analyst.py --days 30
# Analyzes prediction_confidence table
# Identifies which confidence factors were accurate
# Refines confidence scoring methodology
```

## Optimal Learning Architecture (Long-term Vision)

### Component Breakdown

**Data Collection Layer:**
- News sources (HN, NewsAPI, SEC, GitHub, IR)
- Market data (yfinance)
- Deduplication (string + semantic)
- Event metadata storage

**Pattern Detection Layer:**
- Statistical models (correlations, baselines)
- ML models (XGBoost, LSTM, Random Forest)
- Outputs: probabilities, confidence scores, feature importance

**Reasoning Layer:**
- Claude API analysis
- Interprets model outputs
- Adds market context and temporal dynamics
- Explains WHY patterns matter

**Decision Layer:**
- Human review
- Final investment decisions
- Feedback loop to improve models

### Data Flow

```
[Raw Events] → [Deduplication] → [Sentiment Analysis] → [Significance Scoring]
                                            ↓
                                    [Daily Aggregation]
                                            ↓
                                    [Market Data Collection]
                                            ↓
                                    [Correlation Calculation]
                                            ↓
                        [Statistical Models] + [ML Models] + [Claude Analysis]
                                            ↓
                                    [Confidence Scoring]
                                            ↓
                                    [Briefing Generation]
                                            ↓
                                    [Human Decision]
                                            ↓
                                    [Accuracy Tracking]
                                            ↓
                                    [Meta-Learning Loop]
```

## The Fundamental Trade-off

### Traditional ML
**Requires:**
- Large data (500+ points)
- Engineering resources
- Maintenance infrastructure

**Provides:**
- Precise probabilities
- Automated predictions
- High-frequency capability

**Best for:**
- Established patterns
- High-frequency trading
- Large datasets

### Claude API Learning
**Requires:**
- API key
- Small dataset
- Weekly analysis

**Provides:**
- Explainable reasoning
- Adaptive insights
- Context awareness

**Best for:**
- New systems (like AI-Pulse now)
- Small datasets (<500 points)
- Strategic decisions

## Concrete Recommendations

### Current Priority (Phase 1)

**Keep the current Claude-based system** - it's objectively the better choice for months 1-6.

**Focus on:**
1. ✅ Data quality - accurate deduplication, proper sentiment labeling
2. ✅ Data volume - daily collection is more valuable than complex models
3. ✅ Tracking everything - event metadata, market context, prediction accuracy

**Add these enhancements:**
4. Baseline tracking (compare to naive predictor)
5. Category-specific analysis (by event type)
6. Rolling window analysis (30/60/90 days)
7. Prediction confidence database
8. Meta-learning (Claude analyzes its own accuracy)

### When to Move to Phase 2

**Criteria:**
- 180+ correlation data points (6 months of daily data)
- Phase 1 enhancements implemented
- Patterns appear stable over 90+ days
- Accuracy baseline established

**Don't rush to ML.** Build data volume first. The learning happens automatically through Claude's pattern recognition.

### When to Build ML Models (Phase 3)

**Required conditions:**
- 500+ correlation data points (18+ months)
- Statistical models show clear signals (>60% accuracy)
- Patterns stable over 3+ months
- Budget for ML engineer time ($10k+)

**Don't build ML earlier** - you'll overfit to noise and waste resources.

## Success Metrics

### Phase 1 (Current)
- Data collection uptime (>95% daily collection success)
- Deduplication accuracy (semantic duplicates caught)
- Analysis coverage (>80% events analyzed)
- Prediction insights generated (weekly)

### Phase 2
- Statistical model accuracy vs baseline (>55% to be useful)
- Correlation strength by event type (r > 0.5 for useful categories)
- Rolling accuracy trends (improving over time)

### Phase 3
- ML model accuracy (>65% to beat statistical baseline)
- Model calibration (predicted probabilities match actual outcomes)
- Feature importance stability (top features consistent over time)

### Phase 4
- Ensemble accuracy (>70%)
- Disagreement resolution (Claude explanations for model conflicts)
- Human decision quality (post-decision analysis)

## Cost Projections

### Phase 1 (Months 1-6)
- Claude API: $5/month
- Total: **$5/month**

### Phase 2 (Months 6-12)
- Claude API: $5/month
- Statistical compute: $5/month
- Total: **$10/month**

### Phase 3 (Year 2+)
- Claude API: $10/month
- ML compute: $100/month
- Total: **$110/month**

### Phase 4 (Year 3+)
- Claude API: $20/month
- ML compute: $200/month
- Infrastructure: $80/month
- Total: **$300/month**

## Timeline Summary

| Phase | Timeline | Data Points | Approach | Cost/mo |
|-------|----------|-------------|----------|---------|
| 1 | Months 1-6 | 0-180 | Claude only | $5 |
| 2 | Months 6-12 | 180-365 | Statistics + Claude | $10 |
| 3 | Year 2+ | 500+ | ML + Claude | $110 |
| 4 | Year 3+ | 1000+ | Ensemble + Claude | $300 |

## Conclusion

**Current state:** Phase 1 is the right approach.

**Key insight:** You need 12-24 months of data collection before ML becomes worthwhile.

**Focus:** Data quality and volume over model complexity.

**Learning strategy:** Let Claude identify patterns from small datasets while building the foundation for future ML models.

The system learns continuously through Claude's analysis, which is sufficient until you have 500+ correlation data points. Then transition to hybrid statistical + Claude approach, and eventually to full ML ensemble when data volume supports it.
