"""
Cost tracker for AI API usage.

Wraps API calls and logs consumption for budget tracking.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Optional
from cost_tracking.database import CostDatabase


class CostTracker:
    """
    Tracks API costs for budget management.

    Usage:
        tracker = CostTracker()
        tracker.log_anthropic_call(response, operation='event_analysis')
    """

    # Current Anthropic pricing (as of 2025)
    # https://docs.anthropic.com/claude/docs/pricing
    PRICING = {
        'anthropic': {
            'claude-sonnet-4-20250514': {
                'input': 3.00 / 1_000_000,   # $3 per 1M input tokens
                'output': 15.00 / 1_000_000,  # $15 per 1M output tokens
            },
            'claude-sonnet-4': {  # Alias
                'input': 3.00 / 1_000_000,
                'output': 15.00 / 1_000_000,
            },
            'claude-3-5-sonnet-20241022': {
                'input': 3.00 / 1_000_000,
                'output': 15.00 / 1_000_000,
            },
        },
        'openai': {
            'gpt-4': {
                'input': 30.00 / 1_000_000,
                'output': 60.00 / 1_000_000,
            },
            'gpt-3.5-turbo': {
                'input': 0.50 / 1_000_000,
                'output': 1.50 / 1_000_000,
            },
        }
    }

    def __init__(self, db_path: str = "cost_tracking.db"):
        """
        Initialize cost tracker.

        Args:
            db_path: Path to cost tracking database
        """
        self.db = CostDatabase(db_path)

    def log_anthropic_call(self, response, operation: str = 'api_call',
                           event_id: Optional[int] = None, success: bool = True) -> float:
        """
        Log an Anthropic API call from response object.

        Args:
            response: Anthropic API response object
            operation: Operation type (e.g., 'event_analysis')
            event_id: Related event ID if applicable
            success: Whether call succeeded

        Returns:
            Estimated cost in USD
        """
        model = response.model
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        cost = self.calculate_cost('anthropic', model, input_tokens, output_tokens)

        self.db.log_api_call(
            service='anthropic',
            model=model,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost,
            event_id=event_id,
            success=success
        )

        return cost

    def log_manual_call(self, service: str, model: str, operation: str,
                       input_tokens: int, output_tokens: int,
                       event_id: Optional[int] = None, success: bool = True) -> float:
        """
        Manually log an API call (when you don't have response object).

        Args:
            service: Service name ('anthropic', 'openai')
            model: Model name
            operation: Operation type
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            event_id: Related event ID
            success: Whether call succeeded

        Returns:
            Estimated cost in USD
        """
        cost = self.calculate_cost(service, model, input_tokens, output_tokens)

        self.db.log_api_call(
            service=service,
            model=model,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=cost,
            event_id=event_id,
            success=success
        )

        return cost

    def calculate_cost(self, service: str, model: str,
                      input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost for API call.

        Args:
            service: Service name
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        if service not in self.PRICING:
            # Unknown service, return 0
            return 0.0

        if model not in self.PRICING[service]:
            # Unknown model, return 0
            return 0.0

        rates = self.PRICING[service][model]
        cost = (input_tokens * rates['input']) + (output_tokens * rates['output'])

        return round(cost, 6)  # Round to 6 decimal places

    def get_today_summary(self) -> dict:
        """Get today's cost summary"""
        return self.db.get_today_stats()

    def get_week_summary(self) -> dict:
        """Get this week's cost summary"""
        return self.db.get_week_stats()

    def get_month_summary(self) -> dict:
        """Get this month's cost summary"""
        return self.db.get_month_stats()

    def get_breakdown(self, days: int = 30) -> list:
        """Get cost breakdown by operation"""
        return self.db.get_breakdown_by_operation(days=days)

    def set_budget(self, monthly_limit: float, alert_threshold: float = 0.8):
        """Set monthly budget limit"""
        self.db.set_monthly_budget(monthly_limit, alert_threshold)

    def check_budget(self) -> Optional[dict]:
        """Check current budget status"""
        return self.db.get_budget_status()

    def get_trend(self, days: int = 30) -> list:
        """Get daily cost trend"""
        return self.db.get_daily_trend(days=days)

    def close(self):
        """Close database connection"""
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# CLI for cost tracking
if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description='AI-Pulse Cost Tracker')
    parser.add_argument('--today', action='store_true', help='Show today\'s costs')
    parser.add_argument('--week', action='store_true', help='Show this week\'s costs')
    parser.add_argument('--month', action='store_true', help='Show this month\'s costs')
    parser.add_argument('--breakdown', action='store_true', help='Show cost breakdown by operation')
    parser.add_argument('--budget', action='store_true', help='Show budget status')
    parser.add_argument('--set-budget', type=float, help='Set monthly budget (USD)')
    parser.add_argument('--trend', action='store_true', help='Show daily trend')
    parser.add_argument('--days', type=int, default=30, help='Days for trend/breakdown (default: 30)')
    parser.add_argument('--db', type=str, default='cost_tracking.db', help='Database path')

    args = parser.parse_args()

    with CostTracker(db_path=args.db) as tracker:

        if args.set_budget:
            tracker.set_budget(args.set_budget)
            print(f"✓ Monthly budget set to ${args.set_budget:.2f}")
            print()

        if args.today:
            print("=" * 80)
            print(f"TODAY'S COSTS - {datetime.utcnow().strftime('%Y-%m-%d')}")
            print("=" * 80)
            stats = tracker.get_today_summary()
            print(f"  API Calls:        {stats['total_calls']}")
            print(f"  Total Tokens:     {stats['total_tokens']:,}")
            print(f"  Input Tokens:     {stats['input_tokens']:,}")
            print(f"  Output Tokens:    {stats['output_tokens']:,}")
            print(f"  Estimated Cost:   ${stats['total_cost']:.4f}")
            print()

        if args.week:
            print("=" * 80)
            print("THIS WEEK'S COSTS")
            print("=" * 80)
            stats = tracker.get_week_summary()
            print(f"  API Calls:        {stats['total_calls']}")
            print(f"  Total Tokens:     {stats['total_tokens']:,}")
            print(f"  Estimated Cost:   ${stats['total_cost']:.4f}")
            print()

        if args.month:
            print("=" * 80)
            print("THIS MONTH'S COSTS")
            print("=" * 80)
            stats = tracker.get_month_summary()
            print(f"  API Calls:        {stats['total_calls']}")
            print(f"  Total Tokens:     {stats['total_tokens']:,}")
            print(f"  Estimated Cost:   ${stats['total_cost']:.4f}")
            print()

        if args.breakdown:
            print("=" * 80)
            print(f"COST BREAKDOWN BY OPERATION (Last {args.days} days)")
            print("=" * 80)
            breakdown = tracker.get_breakdown(days=args.days)

            if breakdown:
                print(f"{'Operation':<25} {'Calls':<10} {'Tokens':<15} {'Cost':<12} {'Avg/Call':<12}")
                print("-" * 80)
                for item in breakdown:
                    print(f"{item['operation']:<25} "
                          f"{item['calls']:<10} "
                          f"{item['tokens']:>14,} "
                          f"${item['cost']:>10.4f} "
                          f"${item['avg_cost']:>10.6f}")
            else:
                print("  No data available")
            print()

        if args.budget:
            print("=" * 80)
            print("BUDGET STATUS")
            print("=" * 80)
            status = tracker.check_budget()

            if status:
                print(f"  Monthly Limit:    ${status['monthly_limit']:.2f}")
                print(f"  Spent:            ${status['spent']:.4f} ({status['percent_used']:.1f}%)")
                print(f"  Remaining:        ${status['remaining']:.4f}")
                print(f"  Projected:        ${status['projected_monthly']:.4f}")
                print()
                print(f"  Days Elapsed:     {status['days_elapsed']}")
                print(f"  Days Remaining:   {status['days_remaining']}")
                print()

                if status['within_budget']:
                    print("  Status:           ✓ Within budget")
                else:
                    print("  Status:           ⚠️ Projected to exceed budget!")

                if status['alert_triggered']:
                    print(f"  Alert:            ⚠️ {status['percent_used']:.0f}% of budget used!")
            else:
                print("  No budget set. Use --set-budget to configure.")
            print()

        if args.trend:
            print("=" * 80)
            print(f"DAILY COST TREND (Last {args.days} days)")
            print("=" * 80)
            trend = tracker.get_trend(days=args.days)

            if trend:
                print(f"{'Date':<12} {'Calls':<10} {'Tokens':<15} {'Cost':<12}")
                print("-" * 50)
                for day in trend:
                    print(f"{day['date']:<12} "
                          f"{day['calls']:<10} "
                          f"{day['tokens']:>14,} "
                          f"${day['cost']:>10.4f}")
            else:
                print("  No data available")
            print()

        # Default: show all summaries
        if not any([args.today, args.week, args.month, args.breakdown,
                   args.budget, args.trend, args.set_budget]):
            print("=" * 80)
            print(f"AI-PULSE COST SUMMARY - {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
            print("=" * 80)

            # Today
            today = tracker.get_today_summary()
            print(f"\nTODAY:")
            print(f"  Calls: {today['total_calls']} | Tokens: {today['total_tokens']:,} | Cost: ${today['total_cost']:.4f}")

            # Week
            week = tracker.get_week_summary()
            print(f"\nTHIS WEEK:")
            print(f"  Calls: {week['total_calls']} | Tokens: {week['total_tokens']:,} | Cost: ${week['total_cost']:.4f}")

            # Month
            month = tracker.get_month_summary()
            print(f"\nTHIS MONTH:")
            print(f"  Calls: {month['total_calls']} | Tokens: {month['total_tokens']:,} | Cost: ${month['total_cost']:.4f}")

            # Budget
            status = tracker.check_budget()
            if status:
                print(f"\nBUDGET STATUS:")
                print(f"  Limit: ${status['monthly_limit']:.2f} | "
                      f"Spent: ${status['spent']:.4f} ({status['percent_used']:.1f}%) | "
                      f"Projected: ${status['projected_monthly']:.4f}")

                if not status['within_budget']:
                    print(f"  ⚠️ WARNING: Projected to exceed budget!")

            print("\n" + "=" * 80)
            print("Use --help for more options")
            print("=" * 80 + "\n")
