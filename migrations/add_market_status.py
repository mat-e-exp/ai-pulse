"""
Add market_status column to predictions table for weekend/holiday handling.

This migration adds automatic market closure detection without manual calendar maintenance.

Run once:
    python3.9 migrations/add_market_status.py

What it does:
    - Adds market_status column to predictions table ('open', 'closed', 'unknown')
    - Defaults existing predictions to 'unknown'
    - Market-close workflow will set status based on data collection success
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))


def add_market_status_column(db_path: str = "ai_pulse.db"):
    """Add market_status column to predictions table"""

    print("=" * 80)
    print("MIGRATION: Add market_status column to predictions table")
    print("=" * 80)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(predictions)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'market_status' in columns:
        print("✓ market_status column already exists - migration already applied")
        conn.close()
        return

    print("\n1. Adding market_status column to predictions table...")
    try:
        cursor.execute("""
            ALTER TABLE predictions
            ADD COLUMN market_status TEXT DEFAULT 'unknown'
        """)
        print("   ✓ Column added")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        conn.close()
        return

    print("\n2. Verifying column was added...")
    cursor.execute("PRAGMA table_info(predictions)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'market_status' in columns:
        print("   ✓ market_status column verified")
    else:
        print("   ✗ Column not found after adding")
        conn.close()
        return

    print("\n3. Checking existing predictions...")
    cursor.execute("SELECT COUNT(*) FROM predictions")
    count = cursor.fetchone()[0]
    print(f"   Found {count} existing predictions")

    if count > 0:
        cursor.execute("""
            SELECT date, market_status
            FROM predictions
            ORDER BY date DESC
            LIMIT 5
        """)
        print("\n   Recent predictions:")
        for row in cursor.fetchall():
            print(f"   - {row[0]}: market_status='{row[1]}'")

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("- market-close.yml workflow will set market_status='open' or 'closed'")
    print("- Existing predictions remain 'unknown' until next market-close run")
    print("- Accuracy calculations automatically exclude 'closed' and 'unknown' days")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Add market_status column to predictions table')
    parser.add_argument('--db', type=str, default='ai_pulse.db', help='Database path')

    args = parser.parse_args()

    add_market_status_column(args.db)
