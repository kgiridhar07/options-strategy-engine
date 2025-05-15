# indicators/ema.py
import pandas as pd
import pandas_ta as ta
from utils.logger import get_logger

logger = get_logger(__name__)

def calculate_ema(prices, period=20):
    """
    Calculate the Exponential Moving Average (EMA) for a list of prices and a given period.
    Args:
        prices (list[float]): List of closing prices.
        period (int): Number of periods for the EMA.
    Returns:
        float or None: Most recent EMA value, or None if not enough data.
    """
    if len(prices) < period:
        return None
    df = pd.DataFrame({'close': prices})
    ema_series = ta.ema(df['close'], length=period)
    return ema_series.iloc[-1] if not ema_series.empty else None

def ema_12(prices):
    return calculate_ema(prices, period=12)

def ema_20(prices):
    return calculate_ema(prices, period=20)

def ema_50(prices):
    return calculate_ema(prices, period=50)

def ema_200(prices):
    return calculate_ema(prices, period=200)
