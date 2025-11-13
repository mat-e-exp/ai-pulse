"""
Market data collector using yfinance.

Collects end-of-day market data for indices and AI stocks to correlate
with sentiment analysis.

Free, unlimited API via Yahoo Finance.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import yfinance as yf
from datetime import datetime, timedelta
from storage.db import EventDatabase
import sqlite3


# Symbols to track
SYMBOLS = {
    'indices': {
        '^IXIC': 'NASDAQ Composite',
        '^GSPC': 'S&P 500',
    },
    'stocks': {
        'NVDA': 'NVIDIA',
        'MSFT': 'Microsoft',
        'GOOGL': 'Alphabet',
        'META': 'Meta',
        'AMD': 'AMD',
    },
    'etfs': {
        'BOTZ': 'AI/Robotics ETF',
    }
}


def ensure_market_table(db_path: str):
    """Create market_data table if it doesn't exist"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            symbol_name TEXT,
            open REAL,
            close REAL,
            high REAL,
            low REAL,
            volume INTEGER,
            change_pct REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, symbol)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_market_date ON market_data(date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_market_symbol ON market_data(symbol)
    """)

    conn.commit()
    conn.close()


def collect_market_data(date_str: str, db_path: str = "ai_pulse.db"):
    """
    Collect market data for a specific date using batch download.

    Args:
        date_str: Date in YYYY-MM-DD format
        db_path: Database path
    """
    print("=" * 80)
    print(f"COLLECTING MARKET DATA - {date_str}")
    print("=" * 80)

    ensure_market_table(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all symbols
    all_symbols = {}
    for category, symbols in SYMBOLS.items():
        all_symbols.update(symbols)

    # Download all symbols in one batch request (more efficient)
    symbol_list = list(all_symbols.keys())
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    start_date = (date_obj - timedelta(days=7)).strftime('%Y-%m-%d')  # Extra days for weekends
    end_date = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"\nFetching {len(symbol_list)} symbols in batch...")

    try:
        # Batch download - much faster and avoids rate limits
        data = yf.download(symbol_list, start=start_date, end=end_date, group_by='ticker', progress=False)
    except Exception as e:
        print(f"✗ Error downloading batch data: {e}")
        conn.close()
        return

    collected = 0
    errors = 0

    for symbol, name in all_symbols.items():
        try:
            # Extract data for this symbol
            if len(symbol_list) == 1:
                hist = data
            else:
                hist = data[symbol]

            if hist.empty:
                print(f"  ✗ {symbol}: No data available")
                errors += 1
                continue

            # Get data for target date
            hist.index = hist.index.tz_localize(None)  # Remove timezone
            target_rows = hist[hist.index.strftime('%Y-%m-%d') == date_str]

            if target_rows.empty:
                print(f"  ✗ {symbol}: No data for {date_str} (market closed?)")
                errors += 1
                continue

            row = target_rows.iloc[0]

            open_price = float(row['Open'])
            close_price = float(row['Close'])
            high_price = float(row['High'])
            low_price = float(row['Low'])
            volume = int(row['Volume'])

            # Calculate change from previous close to today's close
            hist_before = hist[hist.index < target_rows.index[0]]
            if not hist_before.empty:
                prev_close = float(hist_before.iloc[-1]['Close'])
                change_pct = ((close_price - prev_close) / prev_close) * 100
            else:
                # Fallback: use open to close
                change_pct = ((close_price - open_price) / open_price) * 100

            # Insert or update
            cursor.execute("""
                INSERT OR REPLACE INTO market_data
                (date, symbol, symbol_name, open, close, high, low, volume, change_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_str, symbol, name, open_price, close_price, high_price, low_price, volume, change_pct))

            print(f"  ✓ {symbol}: ${close_price:.2f} ({change_pct:+.2f}%)")
            collected += 1

        except Exception as e:
            print(f"  ✗ {symbol}: Error - {e}")
            errors += 1

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print(f"COMPLETE: {collected} symbols collected, {errors} errors")
    print("=" * 80)


def backfill_market_data(days_back: int = 30, db_path: str = "ai_pulse.db"):
    """
    Backfill market data for last N days.

    Args:
        days_back: Number of days to backfill
        db_path: Database path
    """
    print("=" * 80)
    print(f"BACKFILLING MARKET DATA - Last {days_back} days")
    print("=" * 80)

    for i in range(days_back):
        date = datetime.utcnow() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        collect_market_data(date_str, db_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Collect market data')
    parser.add_argument('--date', type=str, help='Date to collect (YYYY-MM-DD). Default: yesterday')
    parser.add_argument('--backfill', type=int, help='Backfill N days of data')
    parser.add_argument('--db', type=str, default='ai_pulse.db', help='Database path')

    args = parser.parse_args()

    if args.backfill:
        backfill_market_data(days_back=args.backfill, db_path=args.db)
    else:
        if args.date:
            date_str = args.date
        else:
            # Default: yesterday (since we want end-of-day data)
            date_str = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

        collect_market_data(date_str, db_path=args.db)
