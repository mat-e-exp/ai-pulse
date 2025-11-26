"""
Workflow safety wrapper - tracks workflow runs and detects duplicates.

Usage:
    python3.9 workflow_safety.py start <workflow-name>
    # ... run workflow steps ...
    python3.9 workflow_safety.py complete <workflow-run-id>
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from storage.db import EventDatabase
from storage.db_safety import log_workflow_run, complete_workflow_run


def start_workflow(workflow_name: str, db_path: str = "ai_pulse.db") -> int:
    """
    Log workflow start and check for duplicates.

    Args:
        workflow_name: Name of workflow
        db_path: Database path

    Returns:
        workflow_run_id to use in complete_workflow
    """
    db = EventDatabase(db_path)
    workflow_run_id = log_workflow_run(db, workflow_name, status='started')
    db.close()

    return workflow_run_id


def complete(workflow_run_id: int, status: str = 'completed',
            notes: str = None, db_path: str = "ai_pulse.db"):
    """
    Mark workflow as completed.

    Args:
        workflow_run_id: ID from start_workflow
        status: 'completed' or 'failed'
        notes: Optional notes
        db_path: Database path
    """
    db = EventDatabase(db_path)
    complete_workflow_run(db, workflow_run_id, status, notes)
    db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3.9 workflow_safety.py start <workflow-name>")
        print("  python3.9 workflow_safety.py complete <workflow-run-id> [status] [notes]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "start":
        if len(sys.argv) < 3:
            print("Error: workflow name required")
            print("Usage: python3.9 workflow_safety.py start <workflow-name>")
            sys.exit(1)

        workflow_name = sys.argv[2]
        workflow_run_id = start_workflow(workflow_name)
        print(workflow_run_id)  # Print ID for capture in workflow

    elif command == "complete":
        if len(sys.argv) < 3:
            print("Error: workflow run ID required")
            print("Usage: python3.9 workflow_safety.py complete <workflow-run-id> [status] [notes]")
            sys.exit(1)

        workflow_run_id = int(sys.argv[2])
        status = sys.argv[3] if len(sys.argv) > 3 else 'completed'
        notes = sys.argv[4] if len(sys.argv) > 4 else None

        complete(workflow_run_id, status, notes)
        print(f"Workflow run {workflow_run_id} marked as {status}")

    else:
        print(f"Unknown command: {command}")
        print("Valid commands: start, complete")
        sys.exit(1)
