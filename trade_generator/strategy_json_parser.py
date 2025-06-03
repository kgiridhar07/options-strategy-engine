import json
import os
import glob

def parse_strategy_json(json_path, filter_earnings_nearby=True, only_strongly_bullish=True):
    """
    Parse a strategy analysis JSON and filter trades.
    Args:
        json_path: Path to the strategy analysis JSON
        filter_earnings_nearby: If True, exclude trades with earnings_nearby == True
        only_strongly_bullish: If True, only include trades with combined_signal.text == 'Strongly Bullish'
    Returns:
        List of filtered trade dicts
    """
    with open(json_path) as f:
        data = json.load(f)
    filtered = []
    for entry in data:
        if filter_earnings_nearby and entry.get('earnings_nearby'):
            continue
        if only_strongly_bullish and (entry.get('combined_signal', {}).get('text') != 'Strongly Bullish'):
            continue
        filtered.append(entry)
    return filtered

def find_latest_analysis_json(folder):
    files = glob.glob(os.path.join(folder, 'bull_bear_analysis_*.json'))
    if not files:
        raise FileNotFoundError(f"No analysis JSON files found in {folder}")
    return max(files, key=os.path.getmtime)

def get_tickers_by_signal(json_path, signal_text, filter_earnings_nearby=True):
    """
    Returns a list of tickers from the analysis JSON with the given signal_text (e.g., 'Strongly Bullish', 'Strongly Bearish'),
    optionally filtering out those with earnings_nearby.
    """
    with open(json_path) as f:
        data = json.load(f)
    return [entry['ticker'] for entry in data if entry.get('combined_signal', {}).get('text') == signal_text and (not filter_earnings_nearby or not entry.get('earnings_nearby'))]

# Optionally, add a function to get all signals in one call

def get_signals_dict(json_path, filter_earnings_nearby=True):
    """
    Returns a dict: {signal_text: [tickers,...], ...}
    """
    with open(json_path) as f:
        data = json.load(f)
    signals = {}
    for entry in data:
        if filter_earnings_nearby and entry.get('earnings_nearby'):
            continue
        sig = entry.get('combined_signal', {}).get('text')
        if sig:
            signals.setdefault(sig, []).append(entry['ticker'])
    return signals
