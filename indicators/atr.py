import pandas as pd
import pandas_ta as ta
from utils.logger import get_logger

logger = get_logger(__name__)

def calculate_atr(high, low, close, period=14):
    """
    Calculate the Average True Range (ATR) for a given period.
    Args:
        high (list[float]): List of high prices.
        low (list[float]): List of low prices.
        close (list[float]): List of close prices.
        period (int): Number of periods for ATR calculation.
    Returns:
        float: The most recent ATR value, or None if not enough data.
    """
    if len(high) < period or len(low) < period or len(close) < period:
        logger.warning("Not enough data to calculate ATR.")
        return None
    df = pd.DataFrame({'high': high, 'low': low, 'close': close})
    atr = ta.atr(df['high'], df['low'], df['close'], length=period)
    if atr is None or atr.empty:
        logger.warning("ATR calculation returned empty result.")
        return None
    return atr.iloc[-1]
