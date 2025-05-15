# data/history_collector.py
"""
Historical data fetching functions using Alpaca raw data helpers.
"""
from utils.alpaca_api import get_raw_historical_bars
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta, timezone
from utils.logger import get_logger

logger = get_logger(__name__)


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
        logger.error(f"Failed to fetch bars for {symbol}: {e}")
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
            logger.warning(f"Unrecognized bar format for {symbol}: {bar}")
    return closes


def get_historical_ohlc(symbol, lookback_days=30):
    """
    Fetch historical daily OHLC for a symbol.
    Args:
        symbol (str): Ticker symbol
        lookback_days (int): Number of days to look back
    Returns:
        tuple: (closes, highs, lows) as lists (most recent last), or empty lists if not enough data
    """
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=lookback_days)
    try:
        bars = get_raw_historical_bars(symbol, TimeFrame.Day, start, end, feed='iex')
    except Exception as e:
        logger.error(f"Failed to fetch bars for {symbol}: {e}")
        return [], [], []
    closes, highs, lows = [], [], []
    # If bars is a list of dicts with 'close', 'high', 'low', just extract
    if isinstance(bars, list) and bars and isinstance(bars[0], dict):
        for bar in bars:
            if all(k in bar for k in ('close', 'high', 'low')):
                closes.append(bar['close'])
                highs.append(bar['high'])
                lows.append(bar['low'])
            else:
                logger.warning(f"Missing OHLC keys for {symbol}: {bar}")
        return closes, highs, lows
    # Fallback: try to extract from objects
    for bar in bars:
        close = getattr(bar, 'close', None) if hasattr(bar, 'close') else bar.get('close') if isinstance(bar, dict) else None
        high = getattr(bar, 'high', None) if hasattr(bar, 'high') else bar.get('high') if isinstance(bar, dict) else None
        low = getattr(bar, 'low', None) if hasattr(bar, 'low') else bar.get('low') if isinstance(bar, dict) else None
        if close is not None and high is not None and low is not None:
            closes.append(close)
            highs.append(high)
            lows.append(low)
        else:
            logger.warning(f"Unrecognized bar format for {symbol}: {bar}")
    return closes, highs, lows