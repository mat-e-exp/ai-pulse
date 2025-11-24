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
