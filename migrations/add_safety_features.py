"""
Database migration: Add safety features for prediction accuracy tracking.

This migration adds:
1. first_logged_at to predictions table (never changes)
2. is_locked flag to prevent updates after market opens
3. prediction_audit table for tracking all updates
4. workflow_runs table for detecting duplicate runs
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

def migrate(db_path: str = "ai_pulse.db"):
    """Run migration to add safety features"""

    print("=" * 80)
    print("MIGRATION: Adding Safety Features")
    print("=" * 80)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Add columns to predictions table
    print("\n1. Adding first_logged_at and is_locked to predictions table...")
    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN first_logged_at TEXT")
        print("   ✓ Added first_logged_at column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("   - first_logged_at already exists, skipping")
        else:
            raise

    try:
        cursor.execute("ALTER TABLE predictions ADD COLUMN is_locked INTEGER DEFAULT 0")
        print("   ✓ Added is_locked column")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("   - is_locked already exists, skipping")
        else:
            raise

    # Set first_logged_at for existing records (use created_at as fallback)
    cursor.execute("""
        UPDATE predictions
        SET first_logged_at = created_at
        WHERE first_logged_at IS NULL
    """)
    rows_updated = cursor.rowcount
    if rows_updated > 0:
        print(f"   ✓ Set first_logged_at for {rows_updated} existing predictions")

    # 2. Create prediction_audit table
    print("\n2. Creating prediction_audit table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            sentiment_positive REAL,
            sentiment_negative REAL,
            sentiment_neutral REAL,
            sentiment_mixed REAL,
            total_events INTEGER,
            prediction TEXT,
            confidence TEXT,
            action TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            workflow_run_id INTEGER
        )
    """)
    print("   ✓ Created prediction_audit table")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_date
        ON prediction_audit(date DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_created
        ON prediction_audit(created_at DESC)
    """)
    print("   ✓ Created indexes on prediction_audit")

    # 3. Create workflow_runs table
    print("\n3. Creating workflow_runs table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflow_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_name TEXT NOT NULL,
            run_date TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT,
            run_count_today INTEGER DEFAULT 1,
            is_duplicate_run INTEGER DEFAULT 0,
            notes TEXT
        )
    """)
    print("   ✓ Created workflow_runs table")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_workflow_date
        ON workflow_runs(run_date DESC, workflow_name)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_workflow_started
        ON workflow_runs(started_at DESC)
    """)
    print("   ✓ Created indexes on workflow_runs")

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print("\nSafety features added:")
    print("  ✓ predictions.first_logged_at - preserves original prediction time")
    print("  ✓ predictions.is_locked - prevents updates after market opens")
    print("  ✓ prediction_audit - tracks all prediction updates")
    print("  ✓ workflow_runs - detects duplicate workflow runs")
    print("\nDatabase is now protected against accidental overwrites.")
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Add safety features to database')
    parser.add_argument('--db', type=str, default='ai_pulse.db',
                       help='Database path (default: ai_pulse.db)')

    args = parser.parse_args()

    migrate(args.db)
