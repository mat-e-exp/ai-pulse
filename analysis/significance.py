"""
Significance analyzer using Claude API.

This is where the system becomes AGENTIC - it uses an LLM to reason about
events and make decisions about their importance.

Key decisions the agent makes:
1. How significant is this event? (0-100 score)
2. Why does it matter?
3. Who is affected?
4. What are the implications?
"""

import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from anthropic import Anthropic
from typing import Optional
from models.events import Event, EventType
from datetime import datetime
from cost_tracking.tracker import CostTracker


class SignificanceAnalyzer:
    """
    Uses Claude to analyze the significance of AI sector events.

    This is the "brain" of the agent - it reasons about what matters and why.

    Now includes cost tracking for budget management.
    """

    def __init__(self, api_key: Optional[str] = None, enable_cost_tracking: bool = True):
        """
        Initialize analyzer with Claude API.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var
            enable_cost_tracking: Whether to track API costs (default: True)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter. Get key at: https://console.anthropic.com/"
            )

        self.client = Anthropic(api_key=self.api_key)

        # Initialize cost tracker
        self.cost_tracker = CostTracker() if enable_cost_tracking else None

    def analyze_event(self, event: Event) -> dict:
        """
        Analyze an event's significance using Claude.

        This is autonomous reasoning - the agent decides what matters.

        Args:
            event: Event to analyze

        Returns:
            Dictionary with:
            - significance_score: 0-100
            - sentiment: positive/negative/neutral
            - reasoning: Why this score?
            - implications: What does it mean?
            - affected_parties: Who cares?
        """

        # Build context for Claude
        prompt = self._build_analysis_prompt(event)

        # Ask Claude to reason about significance
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Track cost
        if self.cost_tracker:
            cost = self.cost_tracker.log_anthropic_call(
                response,
                operation='event_analysis',
                event_id=event.id if hasattr(event, 'id') else None
            )
            # Optional: print cost for transparency
            # print(f"  Cost: ${cost:.6f}")

        # Parse Claude's response
        analysis_text = response.content[0].text

        # Extract structured data from response
        analysis = self._parse_analysis(analysis_text)

        return analysis

    def _build_analysis_prompt(self, event: Event) -> str:
        """
        Build the prompt for Claude to analyze significance.

        This is where we define what "significance" means.
        """

        # Event details
        event_info = f"""
EVENT DETAILS:
Title: {event.title}
Type: {event.event_type.value}
Source: {event.source.value}
Published: {event.published_at or 'Unknown'}
URL: {event.source_url}
"""

        if event.summary:
            event_info += f"\nSummary: {event.summary}"

        if event.content:
            content_preview = event.content[:500]
            if len(event.content) > 500:
                content_preview += "..."
            event_info += f"\nContent: {content_preview}"

        if event.companies:
            event_info += f"\nCompanies mentioned: {', '.join(event.companies)}"

        # Analysis instructions
        prompt = f"""You are an AI sector investment analyst. Analyze this event for significance.

{event_info}

Provide your analysis in this EXACT format:

SIGNIFICANCE SCORE: [0-100]
SENTIMENT: [positive/negative/neutral/mixed]

REASONING:
[2-3 sentences explaining the score]

IMPLICATIONS:
[What does this mean for AI sector investors?]

AFFECTED PARTIES:
[List companies/sectors that benefit or are harmed]

INVESTMENT RELEVANCE:
[Does this change investment thesis? Material/Notable/Background]

- Material: Affects valuation models, competitive positioning, or strategic investment decisions
- Notable: Worth tracking but doesn't fundamentally change investment thesis
- Background: General sector awareness, no direct investment impact

KEY CONTEXT:
[Any historical comparisons or important context]

Scoring guide:
- 90-100: Thesis-changing (major revenue announcements, key executive departures, major regulation)
- 70-89: Notable strategic moves (important products, significant partnerships, competitive shifts)
- 50-69: Interesting developments (competitive intelligence, market signals, technical advances)
- 30-49: Background information (minor updates, opinion pieces, general news)
- 0-29: Noise, low relevance

Focus on investment implications for public AI stocks (NVDA, MSFT, GOOGL, META, AMD)
and broader AI sector trends."""

        return prompt

    def _parse_analysis(self, analysis_text: str) -> dict:
        """
        Parse Claude's structured response into a dictionary.

        Args:
            analysis_text: Claude's response

        Returns:
            Structured analysis dictionary
        """
        lines = analysis_text.split('\n')

        result = {
            'significance_score': 50,  # Default middle score
            'sentiment': 'neutral',
            'reasoning': '',
            'implications': '',
            'affected_parties': '',
            'investment_relevance': 'Notable',
            'key_context': '',
            'full_analysis': analysis_text,
        }

        current_section = None

        for line in lines:
            line = line.strip()

            # Parse score
            if line.startswith('SIGNIFICANCE SCORE:'):
                score_text = line.replace('SIGNIFICANCE SCORE:', '').strip()
                try:
                    # Extract just the number
                    score = int(''.join(filter(str.isdigit, score_text)))
                    result['significance_score'] = max(0, min(100, score))
                except:
                    pass

            # Parse sentiment
            elif line.startswith('SENTIMENT:'):
                sentiment = line.replace('SENTIMENT:', '').strip().lower()
                if sentiment in ['positive', 'negative', 'neutral', 'mixed']:
                    result['sentiment'] = sentiment

            # Section headers
            elif line.startswith('REASONING:'):
                current_section = 'reasoning'
            elif line.startswith('IMPLICATIONS:'):
                current_section = 'implications'
            elif line.startswith('AFFECTED PARTIES:'):
                current_section = 'affected_parties'
            elif line.startswith('INVESTMENT RELEVANCE:'):
                current_section = 'investment_relevance'
            elif line.startswith('KEY CONTEXT:'):
                current_section = 'key_context'

            # Accumulate content for current section
            elif current_section and line and not line.endswith(':'):
                if result[current_section]:
                    result[current_section] += ' ' + line
                else:
                    result[current_section] = line

        return result

    def analyze_batch(self, events: list[Event], max_analyze: int = 10) -> dict:
        """
        Analyze multiple events, prioritizing by basic heuristics.

        Args:
            events: List of events to analyze
            max_analyze: Maximum number to analyze (Claude API has costs)

        Returns:
            Dictionary with analysis results and stats
        """

        print(f"\nAnalyzing significance of {len(events)} events...")
        print("=" * 80)

        analyzed = []
        skipped = []

        # Prioritize certain event types
        priority_order = [
            EventType.PRODUCT_LAUNCH,
            EventType.FUNDING,
            EventType.PARTNERSHIP,
            EventType.REGULATION,
            EventType.RESEARCH,
            EventType.NEWS,
        ]

        # Sort events by type priority
        sorted_events = sorted(
            events,
            key=lambda e: priority_order.index(e.event_type)
                         if e.event_type in priority_order else 99
        )

        for i, event in enumerate(sorted_events):
            if len(analyzed) >= max_analyze:
                skipped.append(event)
                continue

            print(f"\n[{i+1}/{len(events)}] Analyzing: {event.title[:70]}...")

            try:
                analysis = self.analyze_event(event)

                analyzed.append({
                    'event': event,
                    'analysis': analysis,
                })

                # Show score
                score = analysis['significance_score']
                sentiment = analysis['sentiment']
                print(f"  → Score: {score}/100 | Sentiment: {sentiment}")

            except Exception as e:
                print(f"  ✗ Error analyzing event: {e}")
                skipped.append(event)

        print("\n" + "=" * 80)
        print(f"Analysis complete: {len(analyzed)} analyzed, {len(skipped)} skipped")

        return {
            'analyzed': analyzed,
            'skipped': skipped,
        }


# Test the analyzer
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable")
        print("Get your key at: https://console.anthropic.com/")
        sys.exit(1)

    # Create test event
    test_event = Event(
        title="OpenAI Announces GPT-5 with Major Reasoning Improvements",
        summary="OpenAI has released GPT-5, claiming significant advances in reasoning capabilities and a 40% reduction in hallucinations.",
        event_type=EventType.PRODUCT_LAUNCH,
        companies=["OpenAI", "Microsoft"],
        published_at=datetime.utcnow(),
    )

    # Analyze it
    analyzer = SignificanceAnalyzer()

    print("\nTesting Significance Analyzer")
    print("=" * 80)
    print(f"Event: {test_event.title}")
    print("=" * 80)

    analysis = analyzer.analyze_event(test_event)

    print(f"\nSignificance Score: {analysis['significance_score']}/100")
    print(f"Sentiment: {analysis['sentiment']}")
    print(f"\nReasoning:\n{analysis['reasoning']}")
    print(f"\nImplications:\n{analysis['implications']}")
    print(f"\nAffected Parties:\n{analysis['affected_parties']}")
    print(f"\nInvestment Relevance: {analysis['investment_relevance']}")
    if analysis['key_context']:
        print(f"\nKey Context:\n{analysis['key_context']}")
