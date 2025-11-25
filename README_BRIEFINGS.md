# AI-Pulse Briefings

**Live Site:** https://mat-e-exp.github.io/ai-pulse-briefings/

## What is AI-Pulse?

AI-Pulse is an automated intelligence system that tracks and analyzes developments in the AI sector to provide actionable insights for investment decisions.

## What's in this repository?

This repository contains the **published briefings only** - the HTML output of the AI-Pulse system:

- **Daily briefings** with AI sector news analysis
- **Sentiment tracking** over the last 30 days
- **Market performance** correlation charts
- **Event categorization**: Material Events, Notable Events, Background, Research Highlights

## How does it work?

The AI-Pulse system (private repository) automatically:

1. **Collects** events from multiple sources (Hacker News, NewsAPI, SEC filings, GitHub, ArXiv, RSS feeds)
2. **Analyzes** events using Claude AI for significance scoring and sentiment analysis
3. **Publishes** HTML briefings to this repository via GitHub Actions
4. **Deploys** to GitHub Pages for public viewing

## Viewing the briefings

- **Latest briefing:** https://mat-e-exp.github.io/ai-pulse-briefings/
- **Archive:** https://mat-e-exp.github.io/ai-pulse-briefings/archive.html

## Technology

- **Static HTML** with Chart.js for visualizations
- **GitHub Pages** for hosting
- **Automated updates** via GitHub Actions (6am and 1:30pm GMT daily)
- **Analysis powered by** Claude (Anthropic)

## Data Sources

- Hacker News API
- NewsAPI
- SEC EDGAR (8-K filings)
- GitHub trending repositories
- Company investor relations (NVIDIA, AMD)
- Tech news RSS feeds (TechCrunch, VentureBeat, The Verge, etc.)
- ArXiv research papers
- Yahoo Finance (market data)

## Event Categories

- 📈 **Material Events** - Thesis-changing developments
- 📊 **Notable Events** - Worth tracking developments
- 👀 **Background** - General awareness items
- 📚 **Research Highlights** - Technical developments from academic papers

## About

This is a learning project exploring agentic AI systems and automated intelligence gathering. The system demonstrates:

- Multi-source data collection and aggregation
- AI-powered analysis and reasoning
- Automated publishing workflows
- Real-time intelligence briefings

---

*Generated automatically by AI-Pulse | Analysis powered by Claude (Anthropic)*
