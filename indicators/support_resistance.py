import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)

def calculate_support_resistance(prices, window=20):
    """
    Calculate support (recent min) and resistance (recent max) levels for a list of prices.
    Args:
        prices (list[float]): List of closing prices.
        window (int): Number of periods to look back for support/resistance.
    Returns:
        tuple: (support, resistance) for the most recent window, or (None, None) if not enough data.
    """
    if len(prices) < window:
        logger.warning("Not enough data to calculate support/resistance.")
        return None, None
    recent = prices[-window:]
    support = min(recent)
    resistance = max(recent)
    return support, resistance

def find_strong_support_resistance(prices, window=20, min_rejections=2, swing_lookback=3):
    """
    Find strong support and resistance levels using swing highs/lows and multiple rejections.
    Args:
        prices (list[float]): List of closing prices.
        window (int): Number of periods to look back for support/resistance.
        min_rejections (int): Minimum number of rejections required to consider a level strong.
        swing_lookback (int): Number of bars on each side to consider a swing high/low.
    Returns:
        tuple: (strongest_support, strongest_resistance) or (None, None) if not enough data.
    """
    if len(prices) < window:
        logger.warning("Not enough data to calculate strong support/resistance.")
        return None, None
    import numpy as np
    s = pd.Series(prices[-window:])
    swing_highs = []
    swing_lows = []
    for i in range(swing_lookback, len(s) - swing_lookback):
        window_slice = s[(i - swing_lookback):(i + swing_lookback + 1)]
        if s[i] == window_slice.max():
            swing_highs.append((i, s[i]))
        if s[i] == window_slice.min():
            swing_lows.append((i, s[i]))
    # Count rejections (touches) for each swing level
    def count_rejections(level, arr, tol=0.005):
        # tol is a percent of price (e.g., 0.5%)
        return np.sum(np.abs(arr - level) / level < tol)
    closes = s.values
    strong_resistances = [(level, count_rejections(level, closes)) for _, level in swing_highs]
    strong_supports = [(level, count_rejections(level, closes)) for _, level in swing_lows]
    # Filter by min_rejections
    strong_resistances = [x for x in strong_resistances if x[1] >= min_rejections]
    strong_supports = [x for x in strong_supports if x[1] >= min_rejections]
    # Pick the most recent strong level (last in window), else fallback to min/max
    strongest_resistance = strong_resistances[-1][0] if strong_resistances else s.max()
    strongest_support = strong_supports[-1][0] if strong_supports else s.min()
    return strongest_support, strongest_resistance

def find_strong_swing_levels_from_arrays(high, low, swing_window=3, rejection_window=20, tolerance=0.5, min_rejections=2):
    """
    Identifies strong support and resistance levels by combining swing highs/lows with multiple rejections.

    Parameters:
        high: list or np.array of high prices
        low: list or np.array of low prices
        swing_window: int, number of bars before/after to define a swing point
        rejection_window: int, lookback period to count rejections
        tolerance: float, price tolerance to consider a rejection
        min_rejections: int, minimum touches to confirm a strong level

    Returns:
        strong_supports: list of (index, price) tuples for support
        strong_resistances: list of (index, price) tuples for resistance
    """
    import pandas as pd
    lows = pd.Series(low)
    highs = pd.Series(high)
    df = pd.DataFrame({'low': lows, 'high': highs})
    # Step 1: Find swing lows and swing highs
    swing_lows = df[(lows.shift(swing_window) > lows) & (lows.shift(-swing_window) > lows)]
    swing_highs = df[(highs.shift(swing_window) < highs) & (highs.shift(-swing_window) < highs)]
    # Step 2: Count rejections near those swing levels
    strong_supports = []
    for idx, row in swing_lows.iterrows():
        level = row['low']
        start = max(0, idx - rejection_window)
        end = idx
        count = ((df['low'][start:end] - level).abs() < tolerance).sum()
        if count >= min_rejections:
            strong_supports.append((idx, level))
    strong_resistances = []
    for idx, row in swing_highs.iterrows():
        level = row['high']
        start = max(0, idx - rejection_window)
        end = idx
        count = ((df['high'][start:end] - level).abs() < tolerance).sum()
        if count >= min_rejections:
            strong_resistances.append((idx, level))
    return strong_supports, strong_resistances
