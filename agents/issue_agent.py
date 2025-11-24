"""
Issue-Driven Agent

Reads GitHub issues labeled with 'directive:ui' and implements visual changes automatically.
Scope is limited to UI/styling changes only - no data pipeline or schema modifications.

Labels:
- directive:ui - Change output format/styling (HTML, CSS)

For data, source, config, or prompt changes - use Claude Code directly.
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

    Only supports directive:ui - other change types should use Claude Code directly.

    Returns list of dicts with 'path' and 'content'.
    """
    files = []

    if label == 'directive:ui':
        # UI changes - HTML reporter and CSS only
        paths = [
            'agents/html_reporter.py',
            'style.css',
        ]
    else:
        # Unsupported label - exit gracefully
        print(f"ERROR: Label '{label}' not supported by issue agent")
        print("Supported labels: directive:ui")
        print("For other changes, use Claude Code directly")
        sys.exit(1)

    for path in paths:
        full_path = Path(path)
        if full_path.exists():
            content = full_path.read_text()
            files.append({
                'path': path,
                'content': content
            })

    return files


def build_prompt(issue_title: str, issue_body: str, label: str, files: list[dict]) -> str:
    """Build the prompt for Claude to understand and implement the change."""

    files_context = ""
    for f in files:
        files_context += f"\n\n### File: {f['path']}\n```python\n{f['content']}\n```"

    prompt = f"""You are an AI agent that implements UI/visual changes to a web briefing page.

## Scope
You can ONLY make visual/styling changes:
- Colors, fonts, spacing, layout
- Chart appearance and styling
- HTML structure changes
- CSS modifications
- Text, labels, headings

You CANNOT change:
- Data sources or collection logic
- Database schema
- Analysis or scoring logic
- API integrations

## Issue #{ISSUE_NUMBER}
**Title:** {issue_title}
**Description:**
{issue_body}

## Files You Can Modify
{files_context}

## Output Format

For each file you modify, output in this exact format:

===FILE: path/to/file.py===
<complete file content here>
===END FILE===

Rules:
- Output the COMPLETE file content, not just the changes
- Keep changes minimal and focused on the visual request
- Preserve existing functionality
- If the request requires data/schema changes, explain that it's outside your scope

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
        model="claude-3-5-haiku-20241022",  # Haiku is sufficient for UI-only changes
        max_tokens=16000,
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
