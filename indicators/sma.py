# indicators/sma.py
import pandas as pd
import pandas_ta as ta

def calculate_sma(prices, period=20):
    """
    Calculate the Simple Moving Average (SMA) for a list of prices and a given period.
    Args:
        prices (list[float]): List of closing prices.
        period (int): Number of periods for the SMA.
    Returns:
        float or None: Most recent SMA value, or None if not enough data.
    """
    if len(prices) < period:
        return None
    df = pd.DataFrame({'close': prices})
    sma_series = ta.sma(df['close'], length=period)
    return sma_series.iloc[-1] if not sma_series.empty else None

def sma_20(prices):
    return calculate_sma(prices, period=20)

def sma_50(prices):
    return calculate_sma(prices, period=50)

def sma_200(prices):
    return calculate_sma(prices, period=200)
