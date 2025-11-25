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


def get_last_trading_day(from_date: datetime = None) -> str:
    """
    Get the most recent trading day (excluding weekends).

    If from_date is a weekend, returns the previous Friday.
    Otherwise returns the same day (market close data available by 9:30pm GMT).

    Args:
        from_date: Date to check from (default: today)

    Returns:
        Date string in YYYY-MM-DD format
    """
    if from_date is None:
        from_date = datetime.utcnow()  # Use today - data available after market close

    # weekday(): Monday=0, Sunday=6
    weekday = from_date.weekday()

    if weekday == 5:  # Saturday -> Friday
        from_date = from_date - timedelta(days=1)
    elif weekday == 6:  # Sunday -> Friday
        from_date = from_date - timedelta(days=2)

    return from_date.strftime('%Y-%m-%d')


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


def fetch_fmp_daily(symbol: str, date_str: str, api_key: str) -> dict:
    """
    Fetch daily OHLCV data from Financial Modeling Prep for a specific date.

    Args:
        symbol: Stock/index symbol (e.g., 'NVDA', '^GSPC')
        date_str: Date in YYYY-MM-DD format
        api_key: FMP API key

    Returns:
        Dictionary with 'open', 'close', 'high', 'low', 'volume', 'change_pct' or None if failed
    """
    import urllib.parse
    encoded_symbol = urllib.parse.quote(symbol)

    url = f'https://financialmodelingprep.com/stable/historical-price-eod/full?symbol={encoded_symbol}&apikey={api_key}'

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or not isinstance(data, list):
            return None

        # Find target date and previous date
        target_data = None
        prev_data = None

        for i, day in enumerate(data):
            if day['date'] == date_str:
                target_data = day
                if i + 1 < len(data):
                    prev_data = data[i + 1]
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
        print(f"  ✗ FMP error for {symbol}: {e}")
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
    Collect market data for a specific date.

    Strategy:
    - Yahoo Finance: Only for indices (^GSPC, ^IXIC) - 2 symbols, less likely to hit rate limits
    - FMP API: For all stocks/ETFs (8 symbols) - reliable, 250 calls/day is plenty

    Fallbacks:
    - If Yahoo indices fail → try Direct Yahoo API → try FMP
    - If FMP stocks fail → try Alpha Vantage

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

    # Separate indices from stocks/ETFs/crypto
    indices = SYMBOLS['indices']
    stocks_etfs = {}
    stocks_etfs.update(SYMBOLS['stocks'])
    stocks_etfs.update(SYMBOLS['etfs'])
    if 'crypto' in SYMBOLS:
        stocks_etfs.update(SYMBOLS['crypto'])

    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    start_date = (date_obj - timedelta(days=4)).strftime('%Y-%m-%d')  # 4 days handles weekends
    end_date = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')

    collected = 0
    errors = 0

    # ============================================================================
    # STEP 1: Fetch indices from Yahoo Finance (only 2 symbols)
    # ============================================================================
    print(f"\n[1/2] Fetching {len(indices)} indices from Yahoo Finance...")
    index_list = list(indices.keys())

    yahoo_indices_failed = []

    try:
        data = yf.download(index_list, start=start_date, end=end_date, group_by='ticker', progress=False)

        if data is None or (hasattr(data, 'empty') and data.empty):
            print(f"  ⚠️ Yahoo returned no data (rate limited)")
            yahoo_indices_failed = list(indices.items())
        else:
            # Process Yahoo index data
            for symbol, name in indices.items():
                try:
                    if len(index_list) == 1:
                        hist = data
                    else:
                        hist = data[symbol]

                    if hist.empty:
                        yahoo_indices_failed.append((symbol, name))
                        continue

                    hist.index = hist.index.tz_localize(None)
                    target_rows = hist[hist.index.strftime('%Y-%m-%d') == date_str]

                    if target_rows.empty:
                        yahoo_indices_failed.append((symbol, name))
                        continue

                    row = target_rows.iloc[0]
                    open_price = float(row['Open'])
                    close_price = float(row['Close'])
                    high_price = float(row['High'])
                    low_price = float(row['Low'])
                    volume = int(row['Volume'])

                    hist_before = hist[hist.index < target_rows.index[0]]
                    if not hist_before.empty:
                        prev_close = float(hist_before.iloc[-1]['Close'])
                        change_pct = ((close_price - prev_close) / prev_close) * 100
                    else:
                        change_pct = ((close_price - open_price) / open_price) * 100

                    cursor.execute("""
                        INSERT OR REPLACE INTO market_data
                        (date, symbol, symbol_name, open, close, high, low, volume, change_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (date_str, symbol, name, open_price, close_price, high_price, low_price, volume, change_pct))

                    print(f"  ✓ {symbol}: ${close_price:.2f} ({change_pct:+.2f}%)")
                    collected += 1

                except Exception as e:
                    print(f"  ✗ {symbol}: {e}")
                    yahoo_indices_failed.append((symbol, name))

    except Exception as e:
        print(f"  ⚠️ Yahoo error: {e}")
        yahoo_indices_failed = list(indices.items())

    # Fallback for failed indices: try Direct Yahoo API, then FMP
    if yahoo_indices_failed:
        print(f"\n  Trying fallbacks for {len(yahoo_indices_failed)} failed indices...")
        still_failed = []

        for symbol, name in yahoo_indices_failed:
            # Try Direct Yahoo API first
            yahoo_data = fetch_yahoo_direct(symbol, date_str)
            if yahoo_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data
                    (date, symbol, symbol_name, open, close, high, low, volume, change_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (date_str, symbol, name, yahoo_data['open'], yahoo_data['close'],
                      yahoo_data['high'], yahoo_data['low'], yahoo_data['volume'], yahoo_data['change_pct']))
                print(f"  ✓ {symbol} (Direct Yahoo): ${yahoo_data['close']:.2f} ({yahoo_data['change_pct']:+.2f}%)")
                collected += 1
            else:
                still_failed.append((symbol, name))

        # Try FMP for remaining failures
        if still_failed:
            fmp_key = os.getenv('FMP_API_KEY')
            if fmp_key:
                print(f"  Trying FMP for {len(still_failed)} indices...")
                for symbol, name in still_failed:
                    fmp_data = fetch_fmp_daily(symbol, date_str, fmp_key)
                    if fmp_data:
                        cursor.execute("""
                            INSERT OR REPLACE INTO market_data
                            (date, symbol, symbol_name, open, close, high, low, volume, change_pct)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (date_str, symbol, name, fmp_data['open'], fmp_data['close'],
                              fmp_data['high'], fmp_data['low'], fmp_data['volume'], fmp_data['change_pct']))
                        print(f"  ✓ {symbol} (FMP): ${fmp_data['close']:.2f} ({fmp_data['change_pct']:+.2f}%)")
                        collected += 1
                    else:
                        print(f"  ✗ {symbol}: All sources failed")
                        errors += 1

    # ============================================================================
    # STEP 2: Fetch stocks/ETFs from FMP API (8 symbols)
    # ============================================================================
    print(f"\n[2/2] Fetching {len(stocks_etfs)} stocks/ETFs from FMP...")
    fmp_key = os.getenv('FMP_API_KEY')

    if not fmp_key:
        print("  ⚠️ FMP_API_KEY not found in environment, falling back to Alpha Vantage")
        fmp_key = None

    fmp_failed = []

    if fmp_key:
        for symbol, name in stocks_etfs.items():
            fmp_data = fetch_fmp_daily(symbol, date_str, fmp_key)
            if fmp_data:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data
                    (date, symbol, symbol_name, open, close, high, low, volume, change_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (date_str, symbol, name, fmp_data['open'], fmp_data['close'],
                      fmp_data['high'], fmp_data['low'], fmp_data['volume'], fmp_data['change_pct']))
                print(f"  ✓ {symbol}: ${fmp_data['close']:.2f} ({fmp_data['change_pct']:+.2f}%)")
                collected += 1
            else:
                fmp_failed.append((symbol, name))
    else:
        fmp_failed = list(stocks_etfs.items())

    # Fallback to Alpha Vantage for failed stocks/ETFs
    if fmp_failed:
        av_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if av_key:
            print(f"\n  Falling back to Alpha Vantage for {len(fmp_failed)} stocks/ETFs...")
            for idx, (symbol, name) in enumerate(fmp_failed):
                if idx > 0 and idx % 5 == 0:
                    print(f"  (Rate limiting: waiting 60 seconds...)")
                    time.sleep(60)

                av_data = fetch_alpha_vantage_daily(symbol, date_str, av_key)
                if av_data:
                    cursor.execute("""
                        INSERT OR REPLACE INTO market_data
                        (date, symbol, symbol_name, open, close, high, low, volume, change_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (date_str, symbol, name, av_data['open'], av_data['close'],
                          av_data['high'], av_data['low'], av_data['volume'], av_data['change_pct']))
                    print(f"  ✓ {symbol} (AV): ${av_data['close']:.2f} ({av_data['change_pct']:+.2f}%)")
                    collected += 1
                else:
                    print(f"  ✗ {symbol}: All sources failed")
                    errors += 1
        else:
            print(f"  ✗ No Alpha Vantage API key - {len(fmp_failed)} symbols failed")
            errors += len(fmp_failed)

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
            # Default: last trading day (handles weekends automatically)
            date_str = get_last_trading_day()
            print(f"Auto-detected last trading day: {date_str}")

        collect_market_data(date_str, db_path=args.db)
