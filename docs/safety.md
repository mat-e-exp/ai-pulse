# AI-Pulse Safety Features

## Purpose

Protect prediction accuracy data for investment decisions. Prevent accidental corruption from:
- Logging predictions AFTER market opens
- Losing evidence of original prediction time
- Undetected duplicate workflow runs
- Human error when running scripts

**Added**: 2025-11-26

---

## The Problem

**Prediction accuracy tracking requires**:
1. Prediction logged BEFORE market opens (1:30pm GMT)
2. Market opens at 2:30pm GMT
3. Market closes at 9pm GMT
4. Accuracy calculated by comparing prediction to outcome

**Without safety features**:
- Accidentally rerun workflow at 3pm → logs "prediction" AFTER market moved
- Now measuring reaction accuracy, not prediction accuracy
- Data corrupted, unreliable for investment decisions

---

## 5 Safety Features

### 1. Prediction Locking

**When market opens (2:30pm GMT), predictions for that day are locked.**

```python
# storage/db_safety.py
def should_lock_prediction(date: str, check_time: datetime = None) -> bool:
    """
    Lock conditions:
    1. Market has opened (after 2:30pm GMT)
    2. Date is today or in the past
    """
    market_open = time(14, 30)  # 2:30pm GMT

    # Always lock past predictions
    if pred_date < current_date:
        return True

    # Lock today's prediction if market has opened
    if pred_date == current_date:
        return check_time.time() >= market_open

    # Don't lock future predictions
    return False
```

**Behavior**:
- Before 2:30pm GMT: Predictions can be inserted/updated
- After 2:30pm GMT: Prediction updates BLOCKED
- Blocked attempts logged to `prediction_audit` with action='BLOCKED'

### 2. Timestamp Preservation

**`first_logged_at` field preserves original prediction time, even if regenerated.**

```sql
predictions (
  date PRIMARY KEY,
  ...
  created_at,          -- Last update timestamp
  first_logged_at,     -- Original prediction timestamp (NEVER changes)
  is_locked            -- 1 = locked, 0 = can update
)
```

**Behavior**:
- First prediction: `first_logged_at` = `created_at`
- Subsequent updates: `first_logged_at` preserved, `created_at` updated
- Audit trail can verify prediction was logged before market opened

### 3. Audit Trail

**Every prediction change logged in `prediction_audit` table.**

```sql
prediction_audit (
  id, date,
  sentiment_positive, sentiment_negative, sentiment_neutral, sentiment_mixed,
  total_events, prediction, confidence,
  action,              -- 'INSERT', 'UPDATE', 'BLOCKED'
  reason,              -- Why this action occurred
  created_at,
  workflow_run_id      -- Links to workflow_runs table
)
```

**Actions logged**:
- `INSERT` - Initial prediction
- `UPDATE` - Prediction updated (before market open)
- `BLOCKED` - Update attempt after market open

**Example audit query**:
```bash
sqlite3 ai_pulse.db "SELECT date, action, prediction, reason, created_at
                     FROM prediction_audit
                     WHERE date='2025-11-26'
                     ORDER BY created_at"
```

### 4. Duplicate Run Detection

**Warns if workflow runs multiple times in one day.**

```sql
workflow_runs (
  id, workflow_name,
  run_date,
  started_at, completed_at,
  status,              -- 'started', 'completed', 'failed'
  run_count_today,     -- Increments for each run on same day
  is_duplicate_run,    -- 1 = duplicate detected
  notes
)
```

**Behavior**:
- First run today: `run_count_today=1`, `is_duplicate_run=0`
- Second run today: `run_count_today=2`, `is_duplicate_run=1`, **WARNING printed**
- Helps detect accidental manual triggers

### 5. Idempotent Operations

**Safe to run scripts multiple times - overwrites, not duplicates.**

- `daily_sentiment`: ON CONFLICT(date) DO UPDATE
- `predictions`: ON CONFLICT(date) DO UPDATE (if not locked)
- `events`: UNIQUE(source, source_id) prevents duplicates

---

## Database Schema

### predictions Table

```sql
CREATE TABLE predictions (
    date TEXT PRIMARY KEY,
    sentiment_positive REAL,
    sentiment_negative REAL,
    sentiment_neutral REAL,
    sentiment_mixed REAL,
    total_events INTEGER,
    prediction TEXT,              -- 'bullish', 'bearish', 'neutral'
    confidence TEXT,              -- 'high', 'medium', 'low'
    top_events_summary TEXT,      -- JSON of top 3 events
    created_at TEXT,              -- Last update
    first_logged_at TEXT,         -- Original timestamp (preserved)
    is_locked INTEGER DEFAULT 0   -- 1 after market opens
);
```

### prediction_audit Table

```sql
CREATE TABLE prediction_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    sentiment_positive REAL,
    sentiment_negative REAL,
    sentiment_neutral REAL,
    sentiment_mixed REAL,
    total_events INTEGER,
    prediction TEXT,
    confidence TEXT,
    action TEXT NOT NULL,         -- 'INSERT', 'UPDATE', 'BLOCKED'
    reason TEXT,
    created_at TEXT NOT NULL,
    workflow_run_id INTEGER,
    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id)
);
```

### workflow_runs Table

```sql
CREATE TABLE workflow_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_name TEXT NOT NULL,
    run_date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,         -- 'started', 'completed', 'failed'
    run_count_today INTEGER,
    is_duplicate_run INTEGER DEFAULT 0,
    notes TEXT
);
```

---

## Safety Utilities

### Location: `storage/db_safety.py`

**Key Functions**:

```python
class PredictionSafety:
    @staticmethod
    def is_market_open(check_time: datetime = None) -> bool:
        """Check if US market is open (2:30pm - 9pm GMT, Mon-Fri)"""

    @staticmethod
    def should_lock_prediction(date: str, check_time: datetime = None) -> bool:
        """Determine if prediction should be locked"""

def save_prediction_safe(db, date, sentiment_data, prediction,
                        confidence, top_events_summary,
                        workflow_run_id=None) -> Dict:
    """
    Save prediction with safety checks.
    Returns: {'status': 'success'|'blocked', 'action': 'insert'|'update', ...}
    """

def log_workflow_run(db, workflow_name, run_date=None,
                    status='started', notes=None) -> int:
    """
    Log workflow start and detect duplicates.
    Returns: workflow_run_id
    """

def complete_workflow_run(db, workflow_run_id, status='completed', notes=None):
    """Mark workflow as completed"""
```

---

## Wrapper Scripts

### workflow_safety.py

```bash
# Start workflow (returns workflow_run_id to stdout)
WORKFLOW_ID=$(python3.9 workflow_safety.py start daily-collection)

# Do work...

# Complete workflow
python3.9 workflow_safety.py complete $WORKFLOW_ID completed "Successful run"
```

**Used in GitHub Actions workflows** to track runs and detect duplicates.

---

## Testing

### test_safety.py

```bash
python3.9 test_safety.py
```

**Tests**:
1. Market hours detection (2:30pm - 9pm GMT)
2. Prediction locking logic
3. Save/update predictions
4. Audit trail logging
5. Duplicate detection

---

## Migration

### migrations/add_safety_features.py

**Run once to add safety features:**
```bash
python3.9 migrations/add_safety_features.py
```

**Actions**:
1. Add `first_logged_at` column to predictions
2. Add `is_locked` column to predictions
3. Backfill `first_logged_at` from `created_at` for existing predictions
4. Create `prediction_audit` table
5. Create `workflow_runs` table

---

## Usage Examples

### Safe Prediction Logging

```python
from storage.db import EventDatabase
from storage.db_safety import save_prediction_safe

db = EventDatabase("ai_pulse.db")

sentiment_data = {
    'positive': 35.0,
    'negative': 15.0,
    'neutral': 40.0,
    'mixed': 10.0,
    'total': 50
}

result = save_prediction_safe(
    db=db,
    date="2025-11-26",
    sentiment_data=sentiment_data,
    prediction="bullish",
    confidence="high",
    top_events_summary='[...]'
)

if result['status'] == 'blocked':
    print(f"⚠️ {result['message']}")
    print(f"Existing: {result['existing_prediction']}")
else:
    print(f"✓ {result['message']}")
    print(f"Locked: {result['is_locked']}")
```

### Workflow Tracking

```python
from storage.db import EventDatabase
from storage.db_safety import log_workflow_run, complete_workflow_run

db = EventDatabase("ai_pulse.db")

# Start workflow
workflow_run_id = log_workflow_run(db, "daily-collection")

try:
    # Do work...
    complete_workflow_run(db, workflow_run_id, "completed")
except Exception as e:
    complete_workflow_run(db, workflow_run_id, "failed", str(e))
```

---

## Market Hours

**US Market**: 9:30am - 4:00pm ET
**Converted to GMT**: 2:30pm - 9:00pm GMT (UTC)

**Prediction Schedule**:
- **1:30pm GMT**: Log prediction (1 hour before market)
- **2:30pm GMT**: Market opens, predictions LOCKED
- **9:00pm GMT**: Market closes
- **9:30pm GMT**: Calculate accuracy

**Weekends**: Market closed, predictions can be updated anytime

---

## Troubleshooting

**Prediction won't update**:
```bash
# Check if locked
sqlite3 ai_pulse.db "SELECT date, is_locked, first_logged_at
                     FROM predictions
                     WHERE date='2025-11-26'"
```

**Check audit trail**:
```bash
# See all prediction changes for a date
sqlite3 ai_pulse.db "SELECT action, prediction, reason, created_at
                     FROM prediction_audit
                     WHERE date='2025-11-26'
                     ORDER BY created_at"
```

**Check for duplicate runs**:
```bash
sqlite3 ai_pulse.db "SELECT workflow_name, run_count_today, is_duplicate_run, started_at
                     FROM workflow_runs
                     WHERE run_date='2025-11-26'
                     ORDER BY started_at"
```

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Operational guide with safety rules
- [database-schema.md](database-schema.md) - Full database schema
- [architecture.md](architecture.md) - System architecture overview
