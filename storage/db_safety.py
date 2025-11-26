"""
Database safety utilities for prediction accuracy protection.

Extends EventDatabase with safety features:
- Prediction locking after market opens
- Timestamp preservation
- Audit logging
- Duplicate run detection
"""

from datetime import datetime, time, timezone
from typing import Optional, Dict
import json


class PredictionSafety:
    """Safety utilities for prediction management"""

    @staticmethod
    def is_market_open(check_time: datetime = None) -> bool:
        """
        Check if US market is currently open.

        Market hours: 2:30pm - 9pm GMT (9:30am - 4pm ET)

        Args:
            check_time: Time to check (defaults to now UTC)

        Returns:
            True if market is open
        """
        if check_time is None:
            check_time = datetime.utcnow()

        # Market is open 2:30pm - 9pm GMT, Monday-Friday
        market_open = time(14, 30)  # 2:30pm GMT
        market_close = time(21, 0)   # 9pm GMT

        # Check if weekend
        if check_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        current_time = check_time.time()
        return market_open <= current_time < market_close

    @staticmethod
    def should_lock_prediction(date: str, check_time: datetime = None) -> bool:
        """
        Determine if prediction should be locked.

        Lock conditions:
        1. Market has opened (after 2:30pm GMT)
        2. Date is today or in the past

        Args:
            date: Prediction date (YYYY-MM-DD)
            check_time: Time to check (defaults to now UTC)

        Returns:
            True if prediction should be locked
        """
        if check_time is None:
            check_time = datetime.utcnow()

        pred_date = datetime.strptime(date, '%Y-%m-%d').date()
        current_date = check_time.date()

        # Always lock past predictions
        if pred_date < current_date:
            return True

        # Lock today's prediction if market has opened
        if pred_date == current_date:
            return check_time.time() >= time(14, 30)  # After 2:30pm GMT

        # Don't lock future predictions
        return False


def save_prediction_safe(db, date: str, sentiment_data: dict, prediction: str,
                        confidence: str, top_events_summary: str,
                        workflow_run_id: Optional[int] = None) -> Dict:
    """
    Save prediction with safety checks and audit logging.

    Safety features:
    1. Check if prediction is locked (market already opened)
    2. Preserve first_logged_at timestamp
    3. Log to audit table
    4. Set is_locked flag if appropriate

    Args:
        db: EventDatabase instance
        date: Date string (YYYY-MM-DD)
        sentiment_data: Dict with sentiment percentages
        prediction: 'bullish', 'bearish', or 'neutral'
        confidence: 'high', 'medium', or 'low'
        top_events_summary: JSON string of top events
        workflow_run_id: ID of workflow run (for audit trail)

    Returns:
        Dict with status and message
    """
    cursor = db.conn.cursor()
    now = datetime.utcnow().isoformat()

    # Check if prediction exists and is locked
    cursor.execute("""
        SELECT is_locked, first_logged_at, prediction as old_prediction
        FROM predictions
        WHERE date = ?
    """, (date,))

    existing = cursor.fetchone()

    if existing:
        is_locked = existing[0] if existing[0] is not None else 0
        first_logged_at = existing[1]
        old_prediction = existing[2]

        if is_locked:
            # Prediction is locked - refuse update
            reason = f"Prediction for {date} is locked (market already opened)"

            # Log attempted update to audit
            cursor.execute("""
                INSERT INTO prediction_audit (
                    date, sentiment_positive, sentiment_negative, sentiment_neutral,
                    sentiment_mixed, total_events, prediction, confidence,
                    action, reason, created_at, workflow_run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'BLOCKED', ?, ?, ?)
            """, (
                date,
                sentiment_data.get('positive', 0),
                sentiment_data.get('negative', 0),
                sentiment_data.get('neutral', 0),
                sentiment_data.get('mixed', 0),
                sentiment_data.get('total', 0),
                prediction,
                confidence,
                reason,
                now,
                workflow_run_id
            ))

            db.conn.commit()

            return {
                'status': 'blocked',
                'message': reason,
                'existing_prediction': old_prediction
            }

        # Prediction exists but not locked - update with audit
        action = 'UPDATE'
        reason = 'Prediction updated before market open'

    else:
        # New prediction
        first_logged_at = now
        old_prediction = None
        action = 'INSERT'
        reason = 'Initial prediction logged'

    # Determine if we should lock this prediction now
    should_lock = PredictionSafety.should_lock_prediction(date)

    # Save/update prediction
    cursor.execute("""
        INSERT INTO predictions (
            date, sentiment_positive, sentiment_negative, sentiment_neutral,
            sentiment_mixed, total_events, prediction, confidence,
            top_events_summary, created_at, first_logged_at, is_locked
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            sentiment_positive = excluded.sentiment_positive,
            sentiment_negative = excluded.sentiment_negative,
            sentiment_neutral = excluded.sentiment_neutral,
            sentiment_mixed = excluded.sentiment_mixed,
            total_events = excluded.total_events,
            prediction = excluded.prediction,
            confidence = excluded.confidence,
            top_events_summary = excluded.top_events_summary,
            created_at = excluded.created_at,
            is_locked = excluded.is_locked
    """, (
        date,
        sentiment_data.get('positive', 0),
        sentiment_data.get('negative', 0),
        sentiment_data.get('neutral', 0),
        sentiment_data.get('mixed', 0),
        sentiment_data.get('total', 0),
        prediction,
        confidence,
        top_events_summary,
        now,
        first_logged_at,
        1 if should_lock else 0
    ))

    # Log to audit table
    cursor.execute("""
        INSERT INTO prediction_audit (
            date, sentiment_positive, sentiment_negative, sentiment_neutral,
            sentiment_mixed, total_events, prediction, confidence,
            action, reason, created_at, workflow_run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        date,
        sentiment_data.get('positive', 0),
        sentiment_data.get('negative', 0),
        sentiment_data.get('neutral', 0),
        sentiment_data.get('mixed', 0),
        sentiment_data.get('total', 0),
        prediction,
        confidence,
        action,
        reason,
        now,
        workflow_run_id
    ))

    db.conn.commit()

    return {
        'status': 'success',
        'action': action.lower(),
        'message': f"Prediction {action.lower()}d for {date}",
        'is_locked': should_lock,
        'first_logged_at': first_logged_at
    }


def log_workflow_run(db, workflow_name: str, run_date: str = None,
                     status: str = 'started', notes: str = None) -> int:
    """
    Log workflow run and detect duplicates.

    Args:
        db: EventDatabase instance
        workflow_name: Name of workflow (e.g., 'daily-collection')
        run_date: Date of run (defaults to today)
        status: 'started', 'completed', 'failed'
        notes: Optional notes about the run

    Returns:
        workflow_run_id for this run
    """
    cursor = db.conn.cursor()
    now = datetime.utcnow().isoformat()

    if run_date is None:
        run_date = datetime.utcnow().strftime('%Y-%m-%d')

    # Check for duplicate runs today
    cursor.execute("""
        SELECT COUNT(*) FROM workflow_runs
        WHERE workflow_name = ? AND run_date = ?
    """, (workflow_name, run_date))

    run_count = cursor.fetchone()[0] + 1
    is_duplicate = 1 if run_count > 1 else 0

    # Log the run
    cursor.execute("""
        INSERT INTO workflow_runs (
            workflow_name, run_date, started_at, status,
            run_count_today, is_duplicate_run, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        workflow_name,
        run_date,
        now,
        status,
        run_count,
        is_duplicate,
        notes
    ))

    workflow_run_id = cursor.lastrowid

    db.conn.commit()

    # Warn if duplicate
    if is_duplicate:
        print(f"\n⚠️  WARNING: Duplicate workflow run detected!")
        print(f"   Workflow: {workflow_name}")
        print(f"   Date: {run_date}")
        print(f"   This is run #{run_count} today")
        print(f"   This may corrupt prediction accuracy data!\n")

    return workflow_run_id


def complete_workflow_run(db, workflow_run_id: int, status: str = 'completed',
                         notes: str = None):
    """
    Mark workflow run as completed.

    Args:
        db: EventDatabase instance
        workflow_run_id: ID of workflow run
        status: 'completed' or 'failed'
        notes: Optional notes
    """
    cursor = db.conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        UPDATE workflow_runs
        SET completed_at = ?,
            status = ?,
            notes = COALESCE(?, notes)
        WHERE id = ?
    """, (now, status, notes, workflow_run_id))

    db.conn.commit()
