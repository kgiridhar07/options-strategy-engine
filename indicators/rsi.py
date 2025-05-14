# indicators/rsi.py
import pandas as pd
import pandas_ta as ta

def calculate_rsi(prices, period=14):
    """
    Calculate the Relative Strength Index (RSI) for a list of prices.
    Args:
        prices (list[float]): List of closing prices.
        period (int): Number of periods to use for RSI calculation.
    Returns:
        float or None: Most recent RSI value, or None if not enough data.
    """
    if len(prices) < period:
        return None
    df = pd.DataFrame({'close': prices})
    rsi_series = ta.rsi(df['close'], length=period)
    return rsi_series.iloc[-1] if not rsi_series.empty else None