"""
Cost tracking database for AI-Pulse.

Tracks API consumption and costs to help manage budget.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path


class CostDatabase:
    """Manages cost tracking database"""

    def __init__(self, db_path: str = "cost_tracking.db"):
        """
        Initialize cost tracking database.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()

        # API calls table - individual call tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                service TEXT NOT NULL,
                model TEXT NOT NULL,
                operation TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                estimated_cost REAL NOT NULL,
                event_id INTEGER,
                success BOOLEAN DEFAULT 1
            )
        """)

        # Daily summary table - aggregated daily stats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                total_calls INTEGER NOT NULL,
                total_input_tokens INTEGER NOT NULL,
                total_output_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                total_cost REAL NOT NULL,
                by_operation TEXT
            )
        """)

        # Budget configuration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                monthly_limit REAL NOT NULL,
                alert_threshold REAL DEFAULT 0.8,
                updated_at TEXT NOT NULL
            )
        """)

        # Indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON api_calls(timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_date
            ON daily_summary(date DESC)
        """)

        self.conn.commit()

    def log_api_call(self, service: str, model: str, operation: str,
                     input_tokens: int, output_tokens: int,
                     estimated_cost: float, event_id: Optional[int] = None,
                     success: bool = True) -> int:
        """
        Log an API call.

        Args:
            service: Service name (e.g., 'anthropic')
            model: Model name (e.g., 'claude-sonnet-4')
            operation: Operation type (e.g., 'event_analysis')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            estimated_cost: Estimated cost in USD
            event_id: Related event ID (optional)
            success: Whether call succeeded

        Returns:
            Database ID of logged call
        """
        cursor = self.conn.cursor()

        total_tokens = input_tokens + output_tokens
        timestamp = datetime.utcnow().isoformat()

        cursor.execute("""
            INSERT INTO api_calls (
                timestamp, service, model, operation,
                input_tokens, output_tokens, total_tokens,
                estimated_cost, event_id, success
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, service, model, operation,
            input_tokens, output_tokens, total_tokens,
            estimated_cost, event_id, success
        ))

        self.conn.commit()
        return cursor.lastrowid

    def get_today_stats(self) -> Dict:
        """Get today's usage statistics"""
        today = datetime.utcnow().date().isoformat()
        return self._get_date_stats(today)

    def get_week_stats(self) -> Dict:
        """Get this week's usage statistics"""
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)

        return self._get_date_range_stats(
            start_date.isoformat(),
            end_date.isoformat()
        )

    def get_month_stats(self) -> Dict:
        """Get this month's usage statistics"""
        end_date = datetime.utcnow().date()
        start_date = end_date.replace(day=1)

        return self._get_date_range_stats(
            start_date.isoformat(),
            end_date.isoformat()
        )

    def _get_date_stats(self, date: str) -> Dict:
        """Get stats for a specific date"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_calls,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(estimated_cost) as total_cost
            FROM api_calls
            WHERE DATE(timestamp) = ?
        """, (date,))

        row = cursor.fetchone()

        return {
            'date': date,
            'total_calls': row['total_calls'] or 0,
            'input_tokens': row['input_tokens'] or 0,
            'output_tokens': row['output_tokens'] or 0,
            'total_tokens': row['total_tokens'] or 0,
            'total_cost': row['total_cost'] or 0.0,
        }

    def _get_date_range_stats(self, start_date: str, end_date: str) -> Dict:
        """Get stats for a date range"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_calls,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(estimated_cost) as total_cost
            FROM api_calls
            WHERE DATE(timestamp) BETWEEN ? AND ?
        """, (start_date, end_date))

        row = cursor.fetchone()

        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_calls': row['total_calls'] or 0,
            'input_tokens': row['input_tokens'] or 0,
            'output_tokens': row['output_tokens'] or 0,
            'total_tokens': row['total_tokens'] or 0,
            'total_cost': row['total_cost'] or 0.0,
        }

    def get_breakdown_by_operation(self, days: int = 30) -> List[Dict]:
        """Get cost breakdown by operation type"""
        cursor = self.conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                operation,
                COUNT(*) as calls,
                SUM(total_tokens) as tokens,
                SUM(estimated_cost) as cost,
                AVG(estimated_cost) as avg_cost
            FROM api_calls
            WHERE timestamp >= ?
            GROUP BY operation
            ORDER BY cost DESC
        """, (cutoff,))

        return [dict(row) for row in cursor.fetchall()]

    def get_recent_calls(self, limit: int = 20) -> List[Dict]:
        """Get recent API calls"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT * FROM api_calls
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def set_monthly_budget(self, amount: float, alert_threshold: float = 0.8):
        """
        Set monthly budget limit.

        Args:
            amount: Monthly budget in USD
            alert_threshold: Alert when this % of budget is reached (0.0-1.0)
        """
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO budget (id, monthly_limit, alert_threshold, updated_at)
            VALUES (1, ?, ?, ?)
        """, (amount, alert_threshold, datetime.utcnow().isoformat()))

        self.conn.commit()

    def get_budget_status(self) -> Optional[Dict]:
        """Get current budget status"""
        cursor = self.conn.cursor()

        # Get budget settings
        cursor.execute("SELECT * FROM budget WHERE id = 1")
        budget_row = cursor.fetchone()

        if not budget_row:
            return None

        # Get month stats
        month_stats = self.get_month_stats()

        monthly_limit = budget_row['monthly_limit']
        alert_threshold = budget_row['alert_threshold']
        spent = month_stats['total_cost']
        remaining = monthly_limit - spent
        percent_used = (spent / monthly_limit * 100) if monthly_limit > 0 else 0

        # Calculate projection
        today = datetime.utcnow().date()
        days_in_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        days_elapsed = today.day
        days_remaining = days_in_month.day - days_elapsed

        if days_elapsed > 0:
            daily_average = spent / days_elapsed
            projected = daily_average * days_in_month.day
        else:
            projected = 0

        return {
            'monthly_limit': monthly_limit,
            'alert_threshold': alert_threshold,
            'spent': spent,
            'remaining': remaining,
            'percent_used': percent_used,
            'projected_monthly': projected,
            'within_budget': projected <= monthly_limit,
            'alert_triggered': percent_used >= (alert_threshold * 100),
            'days_elapsed': days_elapsed,
            'days_remaining': days_remaining,
        }

    def get_daily_trend(self, days: int = 30) -> List[Dict]:
        """Get daily cost trend"""
        cursor = self.conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=days)).date().isoformat()

        cursor.execute("""
            SELECT
                DATE(timestamp) as date,
                COUNT(*) as calls,
                SUM(total_tokens) as tokens,
                SUM(estimated_cost) as cost
            FROM api_calls
            WHERE DATE(timestamp) >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (cutoff,))

        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Test the database
if __name__ == "__main__":
    with CostDatabase("test_cost.db") as db:
        # Test logging
        call_id = db.log_api_call(
            service='anthropic',
            model='claude-sonnet-4',
            operation='event_analysis',
            input_tokens=500,
            output_tokens=300,
            estimated_cost=0.0061
        )
        print(f"Logged call ID: {call_id}")

        # Test stats
        today = db.get_today_stats()
        print(f"\nToday's stats: {today}")

        # Test budget
        db.set_monthly_budget(10.00, alert_threshold=0.8)
        status = db.get_budget_status()
        print(f"\nBudget status: {status}")
