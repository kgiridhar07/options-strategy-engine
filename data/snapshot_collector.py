# Collects stock and options data using Alpaca
from utils import alpaca_api


def get_full_snapshot(symbol):
    """
    Returns a dict with all relevant info for the given ticker symbol using a single snapshot API call.
    Extracts: last trade price, previous close, percent change, latest volume, latest quote, daily bar, minute bar, etc.
    """
    snap = alpaca_api.get_raw_basic_snapshot(symbol)
    if isinstance(snap, dict):
        snap = snap.get(symbol, snap)
    result = {}
    # Last trade price
    if 'latest_trade' in snap and snap['latest_trade']:
        result['last_trade_price'] = snap['latest_trade'].get('price')
    # Previous close (from previous_daily_bar)
    if 'previous_daily_bar' in snap and snap['previous_daily_bar']:
        result['previous_close'] = snap['previous_daily_bar'].get('close')
    # Percent change
    if result.get('last_trade_price') is not None and result.get('previous_close') not in (None, 0):
        result['percent_change'] = 100.0 * (result['last_trade_price'] - result['previous_close']) / result['previous_close']
    else:
        result['percent_change'] = None
    # Latest volume (from daily_bar)
    if 'daily_bar' in snap and snap['daily_bar']:
        result['latest_volume'] = snap['daily_bar'].get('volume')
    # Latest quote
    if 'latest_quote' in snap and snap['latest_quote']:
        result['latest_quote'] = snap['latest_quote']
    # Daily bar
    if 'daily_bar' in snap and snap['daily_bar']:
        result['daily_bar'] = snap['daily_bar']
    # Minute bar
    if 'minute_bar' in snap and snap['minute_bar']:
        result['minute_bar'] = snap['minute_bar']
    # Add the full raw snapshot for reference
    result['raw_snapshot'] = snap
    return result

def get_all_snapshots(symbols):
    """
    Returns a dict of {symbol: full_snapshot_dict} for all symbols, calling the API only once per symbol.
    """
    return {symbol: get_full_snapshot(symbol) for symbol in symbols}

def get_last_trade_price_from_snapshot(snapshot):
    # Handle dict or object
    if hasattr(snapshot, 'raw_snapshot'):
        raw = snapshot.raw_snapshot
    elif isinstance(snapshot, dict) and 'raw_snapshot' in snapshot:
        raw = snapshot['raw_snapshot']
    else:
        raw = snapshot
    latest_trade = raw.get('latest_trade') if isinstance(raw, dict) else getattr(raw, 'latest_trade', None)
    if latest_trade:
        if isinstance(latest_trade, dict):
            return latest_trade.get('price')
        return getattr(latest_trade, 'price', None)
    return None

def get_previous_close_from_snapshot(snapshot):
    if hasattr(snapshot, 'raw_snapshot'):
        raw = snapshot.raw_snapshot
    elif isinstance(snapshot, dict) and 'raw_snapshot' in snapshot:
        raw = snapshot['raw_snapshot']
    else:
        raw = snapshot
    prev_bar = raw.get('previous_daily_bar') if isinstance(raw, dict) else getattr(raw, 'previous_daily_bar', None)
    if prev_bar:
        if isinstance(prev_bar, dict):
            return prev_bar.get('close')
        return getattr(prev_bar, 'close', None)
    return None

def get_percent_change_from_snapshot(snapshot):
    last = get_last_trade_price_from_snapshot(snapshot)
    prev = get_previous_close_from_snapshot(snapshot)
    if last is None or prev in (None, 0):
        return None
    return 100.0 * (last - prev) / prev

def get_latest_volume_from_snapshot(snapshot):
    if hasattr(snapshot, 'raw_snapshot'):
        raw = snapshot.raw_snapshot
    elif isinstance(snapshot, dict) and 'raw_snapshot' in snapshot:
        raw = snapshot['raw_snapshot']
    else:
        raw = snapshot
    daily_bar = raw.get('daily_bar') if isinstance(raw, dict) else getattr(raw, 'daily_bar', None)
    if daily_bar:
        if isinstance(daily_bar, dict):
            return daily_bar.get('volume')
        return getattr(daily_bar, 'volume', None)
    return None

def get_latest_quote_from_snapshot(snapshot):
    """
    Returns the latest quote from a snapshot dict or object, handling all possible input types.
    """
    if hasattr(snapshot, 'raw_snapshot'):
        raw = snapshot.raw_snapshot
    elif isinstance(snapshot, dict) and 'raw_snapshot' in snapshot:
        raw = snapshot['raw_snapshot']
    else:
        raw = snapshot
    latest_quote = raw.get('latest_quote') if isinstance(raw, dict) else getattr(raw, 'latest_quote', None)
    return latest_quote

def get_basic_snapshot_from_snapshot(snapshot):
    if hasattr(snapshot, 'raw_snapshot'):
        return snapshot.raw_snapshot
    elif isinstance(snapshot, dict):
        return snapshot.get('raw_snapshot', snapshot)
    return snapshot

def get_latest_trade_price(symbol):
    """
    Returns the latest trade price for the given ticker symbol using get_raw_last_trade (direct from trade endpoint, not snapshot).
    """
    trade = alpaca_api.get_raw_last_trade(symbol)
    if isinstance(trade, dict):
        trade = trade.get(symbol)
    if trade is None:
        return None
    if isinstance(trade, dict):
        return trade.get('price')
    return getattr(trade, 'price', None)
