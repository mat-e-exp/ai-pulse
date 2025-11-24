"""
Issue-Driven Agent

Reads GitHub issues labeled with 'directive:*' and implements changes automatically.
This is the core of the agentic system - autonomous code modification based on user requests.

Labels:
- directive:ui - Change output format/styling (HTML, CSS)
- directive:source - Add/modify news/event data sources
- directive:data - Add/modify market data, charts, metrics (spans collection + display)
- directive:config - Change parameters/thresholds
- directive:prompt - Modify analysis prompts
"""

import os
import sys
from pathlib import Path
from anthropic import Anthropic

# Get issue details from environment
ISSUE_NUMBER = os.environ.get('ISSUE_NUMBER', '')
ISSUE_TITLE = os.environ.get('ISSUE_TITLE', '')
ISSUE_BODY = os.environ.get('ISSUE_BODY', '')
ISSUE_LABEL = os.environ.get('ISSUE_LABEL', '')


def get_relevant_files(label: str) -> list[dict]:
    """
    Get files relevant to the directive type.

    Returns list of dicts with 'path' and 'content'.
    """
    files = []

    if label == 'directive:ui':
        # UI changes - HTML reporter and CSS
        paths = [
            'agents/html_reporter.py',
            'style.css',
        ]
    elif label == 'directive:source':
        # News/event data source changes
        paths = [
            'agents/collector.py',
            'sources/newsapi.py',
            'sources/hackernews.py',
        ]
    elif label == 'directive:data':
        # Market data, charts, metrics (spans collection + display)
        paths = [
            'agents/market_collector.py',
            'agents/html_reporter.py',
            'publish_briefing.py',
        ]
    elif label == 'directive:config':
        # Configuration changes
        paths = [
            'agents/analyzer.py',
            'agents/collector.py',
            'publish_briefing.py',
        ]
    elif label == 'directive:prompt':
        # Prompt changes
        paths = [
            'analysis/significance.py',
            'agents/semantic_deduplicator.py',
        ]
    else:
        # Unknown label - provide key files
        paths = [
            'agents/html_reporter.py',
            'style.css',
        ]

    for path in paths:
        full_path = Path(path)
        if full_path.exists():
            content = full_path.read_text()
            files.append({
                'path': path,
                'content': content
            })

    return files


def load_architecture_context() -> str:
    """Load the ARCHITECTURE.md file for system context."""
    arch_path = Path('ARCHITECTURE.md')
    if arch_path.exists():
        return arch_path.read_text()
    return ""


def build_prompt(issue_title: str, issue_body: str, label: str, files: list[dict]) -> str:
    """Build the prompt for Claude to understand and implement the change."""

    # Load architecture context
    architecture = load_architecture_context()

    files_context = ""
    for f in files:
        files_context += f"\n\n### File: {f['path']}\n```python\n{f['content']}\n```"

    prompt = f"""You are an AI agent that implements code changes based on GitHub issues.

## System Architecture
Understanding how files relate to each other is critical. Read this carefully:

{architecture}

## Issue #{ISSUE_NUMBER}
**Title:** {issue_title}
**Label:** {label}
**Description:**
{issue_body}

## Relevant Files
{files_context}

## Your Task

1. Understand what the user is requesting
2. Determine which file(s) need to be modified
3. Output the COMPLETE modified file(s)

## Output Format

For each file you modify, output in this exact format:

===FILE: path/to/file.py===
<complete file content here>
===END FILE===

Rules:
- CRITICAL: Read the "Common Change Patterns" section in System Architecture FIRST
- For market symbol changes: YOU MUST modify BOTH market_collector.py AND html_reporter.py
- Output the COMPLETE file content, not just the changes
- Modify ALL related files - partial changes will break the system
- Keep changes minimal and focused on the request
- Preserve existing functionality
- If you cannot implement the request, explain why

Now implement the requested change:"""

    return prompt


def parse_response(response_text: str) -> list[dict]:
    """Parse Claude's response to extract file changes."""
    changes = []

    # Split by file markers
    parts = response_text.split('===FILE:')

    for part in parts[1:]:  # Skip first empty part
        if '===END FILE===' in part:
            # Extract path
            path_end = part.find('===')
            path = part[:path_end].strip()

            # Extract content
            content_start = part.find('===') + 3
            content_end = part.find('===END FILE===')
            content = part[content_start:content_end].strip()

            # Remove leading/trailing code fence if present
            if content.startswith('```'):
                first_newline = content.find('\n')
                content = content[first_newline+1:]
            if content.endswith('```'):
                content = content[:-3].rstrip()

            changes.append({
                'path': path,
                'content': content
            })

    return changes


def apply_changes(changes: list[dict]):
    """Write changes to files."""
    for change in changes:
        path = Path(change['path'])
        print(f"Writing changes to: {path}")
        path.write_text(change['content'])


def main():
    # Validate environment
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    if not ISSUE_TITLE:
        print("ERROR: No issue details provided")
        sys.exit(1)

    print(f"Processing issue #{ISSUE_NUMBER}: {ISSUE_TITLE}")
    print(f"Label: {ISSUE_LABEL}")
    print("=" * 60)

    # Get relevant files
    files = get_relevant_files(ISSUE_LABEL)
    print(f"Found {len(files)} relevant files")

    # Build prompt
    prompt = build_prompt(ISSUE_TITLE, ISSUE_BODY, ISSUE_LABEL, files)

    # Call Claude
    print("Sending to Claude for analysis...")
    client = Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",  # Use Sonnet for better code generation
        max_tokens=16000,  # Increased to handle multi-file changes (e.g., collector + reporter)
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    response_text = response.content[0].text
    print("Received response from Claude")

    # Parse changes
    changes = parse_response(response_text)

    if not changes:
        print("No file changes detected in response")
        print("Claude's response:")
        print(response_text[:500])
        sys.exit(0)

    print(f"Detected {len(changes)} file changes")

    # Apply changes
    apply_changes(changes)

    print("=" * 60)
    print("Changes applied successfully")


if __name__ == "__main__":
    main()
