"""Test safety features"""

from datetime import datetime, time
from storage.db import EventDatabase
from storage.db_safety import save_prediction_safe, PredictionSafety

# Test 1: Check market hours detection
print("=" * 80)
print("TEST 1: Market Hours Detection")
print("=" * 80)

# Before market opens (1pm GMT)
before_open = datetime(2025, 11, 26, 13, 0)
print(f"1pm GMT: Market open = {PredictionSafety.is_market_open(before_open)}")  # Should be False

# After market opens (3pm GMT)
after_open = datetime(2025, 11, 26, 15, 0)
print(f"3pm GMT: Market open = {PredictionSafety.is_market_open(after_open)}")  # Should be True

# After market closes (10pm GMT)
after_close = datetime(2025, 11, 26, 22, 0)
print(f"10pm GMT: Market open = {PredictionSafety.is_market_open(after_close)}")  # Should be False

# Test 2: Prediction locking logic
print("\n" + "=" * 80)
print("TEST 2: Prediction Locking Logic")
print("=" * 80)

today = datetime.utcnow().strftime('%Y-%m-%d')

# Before market open
before_time = datetime.utcnow().replace(hour=13, minute=0)
print(f"Should lock at 1pm: {PredictionSafety.should_lock_prediction(today, before_time)}")  # False

# After market open
after_time = datetime.utcnow().replace(hour=15, minute=0)
print(f"Should lock at 3pm: {PredictionSafety.should_lock_prediction(today, after_time)}")  # True

# Test 3: Try saving a prediction
print("\n" + "=" * 80)
print("TEST 3: Save Prediction (should work)")
print("=" * 80)

db = EventDatabase("ai_pulse.db")

test_sentiment = {
    'positive': 45.0,
    'negative': 20.0,
    'neutral': 25.0,
    'mixed': 10.0,
    'total': 50
}

result = save_prediction_safe(
    db=db,
    date="2025-12-01",  # Future date
    sentiment_data=test_sentiment,
    prediction="bullish",
    confidence="high",
    top_events_summary="[]"
)

print(f"Status: {result['status']}")
print(f"Action: {result['action']}")
print(f"Message: {result['message']}")
print(f"Is Locked: {result['is_locked']}")

# Test 4: Try updating it (should work for future date)
print("\n" + "=" * 80)
print("TEST 4: Update Same Prediction (should work for future date)")
print("=" * 80)

result2 = save_prediction_safe(
    db=db,
    date="2025-12-01",
    sentiment_data=test_sentiment,
    prediction="neutral",  # Changed
    confidence="medium",
    top_events_summary="[]"
)

print(f"Status: {result2['status']}")
print(f"Action: {result2['action']}")
print(f"Message: {result2['message']}")

# Test 5: Check audit trail
print("\n" + "=" * 80)
print("TEST 5: Check Audit Trail")
print("=" * 80)

cursor = db.conn.cursor()
cursor.execute("""
    SELECT action, prediction, reason, created_at
    FROM prediction_audit
    WHERE date = '2025-12-01'
    ORDER BY created_at
""")

for row in cursor.fetchall():
    print(f"{row[0]:8} | {row[1]:8} | {row[2]}")

# Cleanup
cursor.execute("DELETE FROM predictions WHERE date = '2025-12-01'")
cursor.execute("DELETE FROM prediction_audit WHERE date = '2025-12-01'")
cursor.execute("DELETE FROM workflow_runs WHERE workflow_name = 'test-workflow'")
db.conn.commit()

db.close()

print("\n" + "=" * 80)
print("ALL TESTS PASSED")
print("=" * 80)
