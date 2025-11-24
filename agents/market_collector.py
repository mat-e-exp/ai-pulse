"""
Market data collector with three-tier fallback sources.

Collects end-of-day market data for indices and AI stocks to correlate
with sentiment analysis.

Primary: Yahoo Finance (free, unlimited, fast)
Fallback 1: Alpha Vantage (500 calls/day, stocks/ETFs only)
Fallback 2: Twelve Data (800 calls/day, includes indices)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import yfinance as yf
from datetime import datetime, timedelta
from storage.db import EventDatabase
import sqlite3
import os
import time
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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
        'PLTR': 'Palantir',
    },
    'etfs': {
        'BOTZ': 'AI/Robotics ETF',
        'AIQ': 'AI Analytics ETF',
    },
    'crypto': {
        'BTC-USD': 'Bitcoin',
    }
}


def fetch_yahoo_direct(symbol: str, date_str: str) -> dict:
    """
    Fetch daily data directly from Yahoo API (bypasses yfinance rate limit).

    Uses query2.finance.yahoo.com with browser-like headers to avoid rate limiting.

    Args:
        symbol: Stock/index symbol (e.g., 'NVDA', '^IXIC')
        date_str: Date in YYYY-MM-DD format

    Returns:
        Dictionary with 'open', 'close', 'high', 'low', 'volume', 'change_pct' or None if failed
    """
    try:
        # URL encode the symbol (^ becomes %5E)
        import urllib.parse
        encoded_symbol = urllib.parse.quote(symbol)

        url = f'https://query2.finance.yahoo.com/v8/finance/chart/{encoded_symbol}?range=10d&interval=1d'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
            return None

        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]

        # Find the target date
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        target_idx = None
        prev_idx = None

        for i, ts in enumerate(timestamps):
            dt = datetime.fromtimestamp(ts)
            if dt.strftime('%Y-%m-%d') == date_str:
                target_idx = i
                if i > 0:
                    prev_idx = i - 1
                break

        if target_idx is None:
            return None

        open_price = quotes['open'][target_idx]
        close_price = quotes['close'][target_idx]
        high_price = quotes['high'][target_idx]
        low_price = quotes['low'][target_idx]
        volume = quotes['volume'][target_idx]

        if None in [open_price, close_price, high_price, low_price, volume]:
            return None

        # Calculate change from previous close
        if prev_idx is not None:
            prev_close = quotes['close'][prev_idx]
            if prev_close:
                change_pct = ((close_price - prev_close) / prev_close) * 100
            else:
                change_pct = ((close_price - open_price) / open_price) * 100
        else:
            change_pct = ((close_price - open_price) / open_price) * 100

        return {
            'open': float(open_price),
            'close': float(close_price),
            'high': float(high_price),
            'low': float(low_price),
            'volume': int(volume),
            'change_pct': change_pct
        }

    except Exception as e:
        print(f"  ✗ Direct Yahoo API error for {symbol}: {e}")
        return None


def fetch_alpha_vantage_daily(symbol: str, date_str: str, api_key: str) -> dict:
    """
    Fetch daily OHLCV data from Alpha Vantage for a specific date.

    Args:
        symbol: Stock symbol (e.g., 'NVDA', '^IXIC')
        date_str: Date in YYYY-MM-DD format
        api_key: Alpha Vantage API key

    Returns:
        Dictionary with 'open', 'close', 'high', 'low', 'volume', 'change_pct' or None if failed
    """
    # Alpha Vantage doesn't support ^ prefix for indices
    # Need to map to their format
    av_symbol = symbol.replace('^', '')
    if symbol == '^IXIC':
        av_symbol = 'IXIC'  # NASDAQ Composite
    elif symbol == '^GSPC':
        av_symbol = 'INX'  # S&P 500

    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={av_symbol}&apikey={api_key}'

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Check for error messages
        if 'Error Message' in data:
            return None
        if 'Note' in data:  # Rate limit message
            print(f"  ⚠️ Alpha Vantage rate limit hit")
            return None

        # Extract time series data
        time_series = data.get('Time Series (Daily)', {})
        if date_str not in time_series:
            return None

        day_data = time_series[date_str]

        open_price = float(day_data['1. open'])
        high_price = float(day_data['2. high'])
        low_price = float(day_data['3. low'])
        close_price = float(day_data['4. close'])
        volume = int(day_data['5. volume'])

        # Calculate change from previous day
        dates = sorted(time_series.keys(), reverse=True)
        date_index = dates.index(date_str)

        if date_index < len(dates) - 1:
            prev_date = dates[date_index + 1]
            prev_close = float(time_series[prev_date]['4. close'])
            change_pct = ((close_price - prev_close) / prev_close) * 100
        else:
            # Fallback: use open to close
            change_pct = ((close_price - open_price) / open_price) * 100

        return {
            'open': open_price,
            'close': close_price,
            'high': high_price,
            'low': low_price,
            'volume': volume,
            'change_pct': change_pct
        }

    except Exception as e:
        print(f"  ✗ Alpha Vantage error for {symbol}: {e}")
        return None


def fetch_twelve_data_daily(symbol: str, date_str: str, api_key: str) -> dict:
    """
    Fetch daily OHLCV data from Twelve Data for a specific date.

    Args:
        symbol: Stock/index symbol (e.g., 'NVDA', 'IXIC')
        date_str: Date in YYYY-MM-DD format
        api_key: Twelve Data API key

    Returns:
        Dictionary with 'open', 'close', 'high', 'low', 'volume', 'change_pct' or None if failed
    """
    # Twelve Data uses different format for indices
    td_symbol = symbol.replace('^', '')

    # Format date for API (needs end date +1 day to include target date)
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    start_date = (date_obj - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')

    url = f'https://api.twelvedata.com/time_series?symbol={td_symbol}&interval=1day&start_date={start_date}&end_date={end_date}&apikey={api_key}'

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Check for errors
        if 'status' in data and data['status'] == 'error':
            return None
        if 'code' in data and data['code'] == 429:  # Rate limit
            print(f"  ⚠️ Twelve Data rate limit hit")
            return None

        # Extract time series
        values = data.get('values', [])
        if not values:
            return None

        # Find target date
        target_data = None
        prev_data = None
        for i, day in enumerate(values):
            if day['datetime'] == date_str:
                target_data = day
                if i < len(values) - 1:
                    prev_data = values[i + 1]
                break

        if not target_data:
            return None

        open_price = float(target_data['open'])
        close_price = float(target_data['close'])
        high_price = float(target_data['high'])
        low_price = float(target_data['low'])
        volume = int(target_data['volume'])

        # Calculate change from previous close
        if prev_data:
            prev_close = float(prev_data['close'])
            change_pct = ((close_price - prev_close) / prev_close) * 100
        else:
            # Fallback: use open to close
            change_pct = ((close_price - open_price) / open_price) * 100

        return {
            'open': open_price,
            'close': close_price,
            'high': high_price,
            'low': low_price,
            'volume': volume,
            'change_pct': change_pct
        }

    except Exception as e:
        print(f"  ✗ Twelve Data error for {symbol}: {e}")
        return None


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

    # Try Yahoo Finance first (fast, unlimited)
    yahoo_failed = False
    try:
        # Batch download - much faster and avoids rate limits
        data = yf.download(symbol_list, start=start_date, end=end_date, group_by='ticker', progress=False)

        # Check if data is empty (rate limit can cause empty results without raising)
        if data is None or (hasattr(data, 'empty') and data.empty):
            print(f"⚠️ Yahoo Finance returned no data (likely rate limited)")
            print(f"   Falling back to Alpha Vantage...")
            yahoo_failed = True
            data = None

    except Exception as e:
        error_msg = str(e)
        if 'Too Many Requests' in error_msg or 'Rate' in error_msg or 'YFRateLimitError' in str(type(e)):
            print(f"⚠️ Yahoo Finance rate limited: {e}")
            print(f"   Falling back to Alpha Vantage...")
            yahoo_failed = True
            data = None
        else:
            print(f"✗ Error downloading batch data: {e}")
            conn.close()
            return

    # If Yahoo failed, try Alpha Vantage fallback
    if yahoo_failed:
        api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            print("✗ Alpha Vantage API key not found in environment")
            print("  Set ALPHA_VANTAGE_API_KEY or wait for Yahoo rate limit to reset")
            conn.close()
            return

        print(f"  Using Alpha Vantage (5 calls/min limit, {len(symbol_list)} symbols)...")

        collected = 0
        errors = 0
        failed_indices = []  # Track indices that Alpha Vantage can't handle

        for idx, (symbol, name) in enumerate(all_symbols.items()):
            # Rate limiting: Alpha Vantage allows 5 calls/min
            if idx > 0 and idx % 5 == 0:
                print(f"  (Rate limiting: waiting 60 seconds...)")
                time.sleep(60)

            av_data = fetch_alpha_vantage_daily(symbol, date_str, api_key)

            if av_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data
                    (date, symbol, symbol_name, open, close, high, low, volume, change_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (date_str, symbol, name, av_data['open'], av_data['close'],
                      av_data['high'], av_data['low'], av_data['volume'], av_data['change_pct']))

                print(f"  ✓ {symbol}: ${av_data['close']:.2f} ({av_data['change_pct']:+.2f}%)")
                collected += 1
            else:
                # Alpha Vantage free tier doesn't support indices
                if symbol.startswith('^'):
                    failed_indices.append((symbol, name))
                print(f"  ✗ {symbol}: No data available")
                errors += 1

        # Try Direct Yahoo API for failed indices (bypasses yfinance rate limit)
        if failed_indices:
            print(f"\n  Trying Direct Yahoo API for {len(failed_indices)} indices...")
            still_failed = []

            for symbol, name in failed_indices:
                yahoo_data = fetch_yahoo_direct(symbol, date_str)

                if yahoo_data:
                    cursor.execute("""
                        INSERT OR REPLACE INTO market_data
                        (date, symbol, symbol_name, open, close, high, low, volume, change_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (date_str, symbol, name, yahoo_data['open'], yahoo_data['close'],
                          yahoo_data['high'], yahoo_data['low'], yahoo_data['volume'], yahoo_data['change_pct']))

                    print(f"  ✓ {symbol}: ${yahoo_data['close']:.2f} ({yahoo_data['change_pct']:+.2f}%)")
                    collected += 1
                    errors -= 1
                else:
                    still_failed.append((symbol, name))

            # Try Twelve Data for any still-failed indices (as last resort)
            if still_failed:
                td_api_key = os.getenv('TWELVE_DATA_API_KEY')
                if td_api_key:
                    print(f"\n  Trying Twelve Data for {len(still_failed)} remaining indices...")
                    for symbol, name in still_failed:
                        td_data = fetch_twelve_data_daily(symbol, date_str, td_api_key)

                        if td_data:
                            cursor.execute("""
                                INSERT OR REPLACE INTO market_data
                                (date, symbol, symbol_name, open, close, high, low, volume, change_pct)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (date_str, symbol, name, td_data['open'], td_data['close'],
                                  td_data['high'], td_data['low'], td_data['volume'], td_data['change_pct']))

                            print(f"  ✓ {symbol}: ${td_data['close']:.2f} ({td_data['change_pct']:+.2f}%)")
                            collected += 1
                            errors -= 1
                        else:
                            print(f"  ✗ {symbol}: No data available from Twelve Data")

        conn.commit()
        conn.close()

        print("\n" + "=" * 80)
        print(f"COMPLETE (Fallback): {collected} symbols collected, {errors} errors")
        print("=" * 80)
        return

    # Yahoo Finance succeeded - process results
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