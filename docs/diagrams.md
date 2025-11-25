# AI-Pulse System Diagrams

## 1. Architecture Component Diagram

Shows the system components and data flow.

```mermaid
flowchart TB
    subgraph Sources["Data Sources"]
        HN[HackerNews]
        NEWS[NewsAPI]
        SEC[SEC EDGAR]
        GH[GitHub Trending]
        IR[Company IR]
        RSS[Tech RSS]
        ARXIV[ArXiv]
    end

    subgraph Collection["Collection Layer"]
        COLL[Collector Agent]
        DEDUP[Deduplicator]
    end

    subgraph Analysis["Analysis Layer"]
        CLAUDE[Claude Haiku]
        SCORE[Significance Scoring]
        SENT[Sentiment Analysis]
    end

    subgraph Storage["Storage"]
        DB[(SQLite Database)]
    end

    subgraph Publishing["Publishing"]
        HTML[HTML Generator]
        PUB[Publisher]
    end

    subgraph External["External Services"]
        DISCORD[Discord Webhooks]
        PAGES[GitHub Pages]
    end

    subgraph Repos["Repositories"]
        PRIVATE[Private Repo<br/>ai-pulse]
        PUBLIC[Public Repo<br/>ai-pulse-briefings]
    end

    Sources --> COLL
    COLL --> DEDUP
    DEDUP --> DB
    DB --> CLAUDE
    CLAUDE --> SCORE
    CLAUDE --> SENT
    SCORE --> DB
    SENT --> DB
    DB --> HTML
    HTML --> PUB
    PUB --> PRIVATE
    PUB --> PUBLIC
    PUBLIC --> PAGES
    PUB --> DISCORD
```

## 2. Daily User Workflow

Shows what happens from a user's perspective through the day.

```mermaid
flowchart LR
    subgraph Morning["6am GMT"]
        A1[Overnight news collected]
        A2[Events analyzed]
        A3[Discord: Top 10 stories]
    end

    subgraph Afternoon["1:30pm GMT"]
        B1[New events collected]
        B2[Delta analyzed]
        B3[Full briefing published]
        B4[Discord: Briefing link]
    end

    subgraph Evening["9:30pm GMT Mon-Fri"]
        C1[Market data collected]
        C2[Correlation calculated]
        C3[Briefing updated]
        C4[Discord: Market update]
    end

    A1 --> A2 --> A3
    A3 -.-> B1
    B1 --> B2 --> B3 --> B4
    B4 -.-> C1
    C1 --> C2 --> C3 --> C4
```

## 3. Data Change Process

How to modify data sources, schema, or analysis logic. Uses Claude Code directly (not the agent).

```mermaid
flowchart TD
    subgraph Developer["Developer Actions"]
        D1[Identify change needed]
        D2[Use Claude Code]
        D3[Edit source files]
        D4[Test locally]
        D5[Commit & push]
    end

    subgraph Files["Files That Can Change"]
        F1[sources/*.py<br/>Data sources]
        F2[agents/analyzer.py<br/>Analysis logic]
        F3[storage/db.py<br/>Database schema]
        F4[agents/collector.py<br/>Collection logic]
    end

    subgraph Automation["Automated Workflows"]
        W1[Next scheduled run<br/>uses new code]
    end

    D1 --> D2
    D2 --> D3
    D3 --> F1 & F2 & F3 & F4
    F1 & F2 & F3 & F4 --> D4
    D4 --> D5
    D5 --> W1
```

## 4. UI Change Process (Issue Agent)

How the issue-driven agent handles UI/visual changes automatically.

```mermaid
flowchart TD
    subgraph Issue["GitHub Issue"]
        I1[Create issue describing UI change]
        I2[Add 'directive:ui' label]
    end

    subgraph Agent["Issue Agent"]
        A1[Agent triggered]
        A2[Reads issue + relevant files]
        A3[Claude generates changes]
        A4[Changes deployed to /preview/]
    end

    subgraph Review["Review Process"]
        R1[Discord notification sent]
        R2[Review preview page]
        R3{Approve?}
    end

    subgraph Outcome["Outcome"]
        O1[Add 'promote:prod' label]
        O2[Changes go live]
        O3[Add 'rejected' label]
        O4[PR + Issue closed]
    end

    I1 --> I2
    I2 --> A1
    A1 --> A2 --> A3 --> A4
    A4 --> R1 --> R2 --> R3
    R3 -->|Yes| O1 --> O2
    R3 -->|No| O3 --> O4
```

## 5. Repository Structure

Shows the split between private and public repositories.

```mermaid
flowchart LR
    subgraph Private["Private: mat-e-exp/ai-pulse"]
        P1[Source code]
        P2[Database]
        P3[Config & secrets]
        P4[GitHub Actions]
    end

    subgraph Public["Public: mat-e-exp/ai-pulse-briefings"]
        PUB1[index.html]
        PUB2[briefings/*.html]
        PUB3[style.css]
        PUB4[preview/]
    end

    subgraph Web["GitHub Pages"]
        W1[mat-e-exp.github.io/ai-pulse-briefings]
    end

    P4 -->|"Pushes HTML only"| Public
    Public --> W1
```

## 6. Deduplication Flow (5 Layers)

Shows how events are deduplicated through multiple layers before publication.

```mermaid
flowchart TD
    subgraph Sources["Data Sources"]
        HN[Hacker News<br/>Item IDs]
        NEWS[NewsAPI<br/>Article URLs]
        ARXIV[ArXiv<br/>Paper URLs]
        RSS[Tech RSS<br/>Article URLs]
    end

    subgraph L1["Layer 1: Database UNIQUE Constraint"]
        DB_CHECK{UNIQUE<br/>(source, source_id)?}
        DB_PASS[✓ New Event]
        DB_BLOCK[✗ Duplicate<br/>Already in DB]
    end

    subgraph L2["Layer 2: Source-Level URL Tracking"]
        URL_CHECK{URL seen<br/>this run?}
        URL_PASS[✓ First occurrence]
        URL_BLOCK[✗ Cross-category<br/>duplicate]
    end

    subgraph L3["Layer 3: Content Similarity (75%)"]
        SIM_CHECK{Title similarity<br/>≥75% OR<br/>≥60% + companies?}
        SIM_PASS[✓ Unique content]
        SIM_BLOCK[✗ Same story<br/>different source]
    end

    subgraph L4["Layer 4: Semantic Dedup (Claude)"]
        SEM_CHECK{Claude: Same<br/>underlying event?}
        SEM_PASS[✓ Unique event]
        SEM_BLOCK[✗ Semantic duplicate<br/>is_semantic_duplicate=1]
    end

    subgraph L5["Layer 5: Publishing Filter"]
        PUB_CHECK{is_duplicate=0<br/>AND<br/>is_semantic_duplicate=0?}
        PUB_PASS[✓ PUBLISHED]
        PUB_BLOCK[✗ Not shown]
    end

    Sources --> DB_CHECK
    DB_CHECK -->|New| DB_PASS
    DB_CHECK -->|Exists| DB_BLOCK
    DB_PASS --> URL_CHECK
    URL_CHECK -->|First| URL_PASS
    URL_CHECK -->|Seen| URL_BLOCK
    URL_PASS --> SIM_CHECK
    SIM_CHECK -->|Unique| SIM_PASS
    SIM_CHECK -->|Similar| SIM_BLOCK
    SIM_PASS --> SEM_CHECK
    SEM_CHECK -->|Unique| SEM_PASS
    SEM_CHECK -->|Duplicate| SEM_BLOCK
    SEM_PASS --> PUB_CHECK
    SEM_BLOCK --> PUB_CHECK
    PUB_CHECK -->|Yes| PUB_PASS
    PUB_CHECK -->|No| PUB_BLOCK
```

**ArXiv Special Case**: `source_id = NULL` (Layer 1 doesn't protect)
- **Safe because**: Layer 2 URL dedup + Layer 3 content similarity + RSS returns today's papers only

## 7. Database Schema

Shows the core tables and their relationships.

```mermaid
erDiagram
    events {
        INTEGER id PK "Auto-increment"
        TEXT source "hackernews, newsapi, arxiv, etc."
        TEXT source_id "External ID or URL"
        TEXT source_url "Original URL"
        TEXT title "Event title"
        TEXT content "Full content"
        TEXT summary "Brief summary"
        TEXT event_type "news, research, funding, etc."
        TEXT companies "Comma-separated"
        TEXT products "Comma-separated"
        TEXT people "Comma-separated"
        TEXT published_at "ISO datetime"
        TEXT collected_at "ISO datetime"
        REAL significance_score "0-100"
        TEXT sentiment "positive, negative, neutral, mixed"
        TEXT analysis "Claude analysis"
        TEXT implications "Investment implications"
        TEXT affected_parties "Who wins/loses"
        TEXT investment_relevance "material, notable, noise"
        TEXT key_context "Historical context"
        INTEGER is_duplicate "0=unique, 1=string duplicate"
        INTEGER is_semantic_duplicate "0=unique, 1=semantic duplicate"
    }

    market_data {
        INTEGER id PK "Auto-increment"
        TEXT date "YYYY-MM-DD"
        TEXT symbol "^IXIC, NVDA, BTC-USD, etc."
        TEXT symbol_name "Display name"
        REAL open "Opening price"
        REAL close "Closing price"
        REAL high "High price"
        REAL low "Low price"
        REAL volume "Trading volume"
        REAL change_pct "Percent change"
        TEXT collected_at "ISO datetime"
    }

    daily_sentiment {
        INTEGER id PK "Auto-increment"
        TEXT date "YYYY-MM-DD"
        INTEGER positive "Count"
        INTEGER negative "Count"
        INTEGER neutral "Count"
        INTEGER mixed "Count"
        INTEGER total_analyzed "Total events"
        TEXT created_at "ISO datetime"
    }

    api_calls {
        INTEGER id PK "Auto-increment"
        TEXT timestamp "ISO datetime"
        TEXT operation "Collection, analysis, etc."
        INTEGER input_tokens "Tokens in"
        INTEGER output_tokens "Tokens out"
        REAL cost_usd "Dollar cost"
        TEXT model "Claude model used"
    }

    budget {
        INTEGER id PK "Auto-increment"
        REAL monthly_limit_usd "Budget cap"
        TEXT set_at "ISO datetime"
    }

    events ||--o{ daily_sentiment : "aggregated_into"
    market_data ||--o{ daily_sentiment : "correlated_with"
    api_calls ||--|| budget : "tracked_against"
```

**Key Constraints:**
- `events`: `UNIQUE(source, source_id)` - Prevents duplicate collection
- `market_data`: `UNIQUE(date, symbol)` - One entry per symbol per day
- `daily_sentiment`: `UNIQUE(date)` - One aggregate per day

**Indexes:**
- `events`: `idx_collected_at`, `idx_event_type`, `idx_significance`
- Fast queries for recent events, research papers, top-scoring events

## 8. Collection Timing & Workflow

Shows automated workflow schedule and data flow.

```mermaid
gantt
    title Daily Automated Workflows (GMT)
    dateFormat HH:mm
    axisFormat %H:%M

    section Morning (6am)
    Collect News           :a1, 06:00, 3m
    Semantic Dedup         :a2, after a1, 2m
    Analyze Events         :a3, after a2, 5m
    Discord: Top 10        :a4, after a3, 1m

    section Afternoon (1:30pm)
    Collect Delta          :b1, 13:30, 3m
    Semantic Dedup         :b2, after b1, 2m
    Analyze New Events     :b3, after b2, 5m
    Publish Briefing       :b4, after b3, 2m
    Discord: Briefing Link :b5, after b4, 1m

    section Evening (9:30pm Mon-Fri)
    Collect Market Data    :c1, 21:30, 2m
    Update Correlation     :c2, after c1, 1m
    Publish Updated Brief  :c3, after c2, 2m
    Discord: Market Update :c4, after c3, 1m
```

**Flow:**

```
6am GMT (Morning Collection)
  ↓ Collect from 7 sources (HN, NewsAPI, RSS, ArXiv, SEC, GitHub, IR)
  ↓ Semantic deduplication (Layer 4)
  ↓ Analyze with Claude Haiku (significance + sentiment)
  ↓ Discord notification: Top 10 stories
  ↓ Database committed

1:30pm GMT (Afternoon Publish)
  ↓ Collect any new events since 6am
  ↓ Semantic deduplication
  ↓ Analyze new events
  ↓ Publish HTML briefing (--days 7 --min-score 40)
  ↓ Push to GitHub Pages
  ↓ Discord notification: Briefing link

9:30pm GMT Mon-Fri (Market Close)
  ↓ Collect market data (11 symbols: indices, stocks, ETFs, crypto)
  ↓ Calculate sentiment-market correlation
  ↓ Update briefing with market data
  ↓ Push to GitHub Pages
  ↓ Discord notification: Market update
```

## 9. Analysis Pipeline

Shows how events are scored and analyzed by Claude.

```mermaid
flowchart TD
    subgraph Input["Input"]
        DB[(Database)]
        UNANALYZED[Unanalyzed Events<br/>significance_score IS NULL]
    end

    subgraph Filtering["Filtering"]
        SKIP_DUPES{Skip duplicates<br/>is_duplicate=1<br/>is_semantic_duplicate=1?}
        SKIP_RESEARCH{Skip research<br/>event_type=research?}
    end

    subgraph Claude["Claude Analysis"]
        PROMPT[Significance Prompt<br/>+ Event details]
        HAIKU[Claude Haiku<br/>Cost: ~$0.002/event]
        RESPONSE[JSON Response]
    end

    subgraph Parsing["Parse Response"]
        EXTRACT[Extract fields:<br/>- significance_score<br/>- sentiment<br/>- analysis<br/>- implications<br/>- affected_parties<br/>- investment_relevance<br/>- key_context]
    end

    subgraph Save["Save to Database"]
        UPDATE[UPDATE events SET<br/>significance_score=...<br/>sentiment=...<br/>WHERE id=...]
    end

    subgraph Output["Output"]
        ANALYZED[Analyzed Event<br/>Ready for publishing]
    end

    DB --> UNANALYZED
    UNANALYZED --> SKIP_DUPES
    SKIP_DUPES -->|No| SKIP_RESEARCH
    SKIP_DUPES -->|Yes| DB
    SKIP_RESEARCH -->|No| PROMPT
    SKIP_RESEARCH -->|Yes| DB
    PROMPT --> HAIKU
    HAIKU --> RESPONSE
    RESPONSE --> EXTRACT
    EXTRACT --> UPDATE
    UPDATE --> ANALYZED
```

**Key Points:**
- Research papers (ArXiv) are NOT analyzed (informational, not sentiment-driven)
- Duplicates are skipped (analysis already done on first occurrence)
- Haiku model keeps costs low (~$3/month for 50 events/day)
- Analysis stored in database for repeated publishing without re-analysis
