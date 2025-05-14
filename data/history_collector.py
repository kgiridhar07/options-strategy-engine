# data/history_collector.py
"""
Historical data fetching functions using Alpaca raw data helpers.
"""
from utils.alpaca_api import get_raw_historical_bars
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta, timezone


def get_historical_closes(symbol, lookback_days=30):
    """
    Fetch historical daily closes for a symbol.
    Args:
        symbol (str): Ticker symbol
        lookback_days (int): Number of days to look back
    Returns:
        list[float]: List of close prices (most recent last), or empty list if not enough data
    """
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=lookback_days)
    try:
        bars = get_raw_historical_bars(symbol, TimeFrame.Day, start, end, feed='iex')
    except Exception as e:
        print(f"[ERROR] Failed to fetch bars for {symbol}: {e}")
        return []
    # If bars is a list of dicts with 'close', just extract closes
    if isinstance(bars, list) and bars and isinstance(bars[0], dict) and 'close' in bars[0]:
        closes = [bar['close'] for bar in bars if 'close' in bar]
        return closes
    # Fallback: try to extract closes from objects
    closes = []
    for bar in bars:
        if hasattr(bar, 'close'):
            closes.append(bar.close)
        elif isinstance(bar, dict) and 'close' in bar:
            closes.append(bar['close'])
        else:
            print(f"[WARN] Unrecognized bar format for {symbol}: {bar}")
    return closes