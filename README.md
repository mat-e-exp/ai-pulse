# AI-Pulse

Real-time intelligence agent for AI sector investment decisions.

## What It Does

Monitors the AI ecosystem and generates actionable intelligence:
- **Product launches** (new models, features, benchmarks)
- **Funding activity** (VC rounds, valuations)
- **Technical breakthroughs** (research papers, capabilities)
- **Market sentiment** (news, developer adoption, narrative shifts)
- **Competitive dynamics** (market share, strategic positioning)

## Why Agentic?

This isn't a simple news aggregator. The agent makes autonomous decisions:
- "Is this announcement material?"
- "Who benefits from this development?"
- "How does this compare to historical patterns?"
- "Should I alert the user now or include in daily briefing?"

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run daily briefing
python3 agents/reporter.py --daily
```

## Project Status

**Current**: Phase 1 - Initial setup
**Next**: Build basic news collector

## Architecture

```
Data Sources → Collector → Analyzer (Claude API) → Reporter → You
                     ↓
                  SQLite (event history)
```

## Documentation

See [CLAUDE.md](CLAUDE.md) for complete technical documentation.

## License

Personal learning project - not for commercial use.
