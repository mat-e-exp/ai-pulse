"""
Discord Morning Briefing

Generates a Discord message with top 10 overnight AI stories.
Called by the 6am workflow after collection and analysis.
"""

import sqlite3
import sys
from datetime import datetime


def get_top_stories(db_path: str = "ai_pulse.db", limit: int = 10) -> list:
    """
    Get top stories by significance score from today's collection.

    Args:
        db_path: Path to database
        limit: Number of stories to return

    Returns:
        List of story dicts with title, score, sentiment, url
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title, significance_score, sentiment, source_url
        FROM events
        WHERE significance_score IS NOT NULL
          AND date(collected_at) = date('now')
          AND (is_duplicate IS NULL OR is_duplicate = 0)
          AND (is_semantic_duplicate IS NULL OR is_semantic_duplicate = 0)
        ORDER BY significance_score DESC
        LIMIT ?
    """, (limit,))

    stories = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return stories


def format_discord_message(stories: list) -> str:
    """
    Format stories as a Discord message.

    Args:
        stories: List of story dicts

    Returns:
        Formatted message string
    """
    if not stories:
        return "🌅 **Morning AI Briefing**\n\nNo significant stories collected overnight."

    # Build message
    lines = ["🌅 **Top 10 Overnight AI Stories**\n"]

    # Sentiment emoji mapping
    sentiment_emoji = {
        'positive': '📈',
        'negative': '📉',
        'neutral': '➖',
        'mixed': '🔀'
    }

    for i, story in enumerate(stories, 1):
        score = int(story['significance_score']) if story['significance_score'] else 0
        sentiment = story['sentiment'] or 'neutral'
        emoji = sentiment_emoji.get(sentiment, '➖')
        title = story['title'][:80] + '...' if len(story['title']) > 80 else story['title']
        url = story['source_url']

        lines.append(f"{i}. [{score}] {emoji} {title}")
        lines.append(f"   {url}\n")

    # Add summary
    sentiments = [s['sentiment'] for s in stories if s['sentiment']]
    pos = sentiments.count('positive')
    neg = sentiments.count('negative')
    neu = sentiments.count('neutral')
    mix = sentiments.count('mixed')

    lines.append(f"**Sentiment**: {pos} positive, {neg} negative, {neu} neutral, {mix} mixed")

    return '\n'.join(lines)


def main():
    """Generate and print Discord message."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate Discord morning briefing')
    parser.add_argument('--db', type=str, default='ai_pulse.db', help='Database path')
    parser.add_argument('--limit', type=int, default=10, help='Number of stories')
    parser.add_argument('--output', type=str, help='Output file (default: stdout)')

    args = parser.parse_args()

    stories = get_top_stories(db_path=args.db, limit=args.limit)
    message = format_discord_message(stories)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(message)
        print(f"Message written to {args.output}")
    else:
        print(message)


if __name__ == "__main__":
    main()
