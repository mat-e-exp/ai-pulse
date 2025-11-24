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
        'BTC-USD': 'Bitcoin', # Added BTC-USD symbol
    },
    'etfs': {
        'BOTZ': 'AI/Robotics ETF',
        'AIQ': 'AI Analytics ETF',
    }
}

# Rest of the file remains unchanged...