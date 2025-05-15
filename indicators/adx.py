import pandas as pd
import pandas_ta as ta
from utils.logger import get_logger

logger = get_logger(__name__)

def calculate_adx(high, low, close, period=14):
    """
    Calculate the Average Directional Index (ADX) for a given period.
    Args:
        high (list[float]): List of high prices.
        low (list[float]): List of low prices.
        close (list[float]): List of close prices.
        period (int): Number of periods for ADX calculation.
    Returns:
        float: The most recent ADX value, or None if not enough data.
    """
    if len(high) < period or len(low) < period or len(close) < period:
        logger.warning("Not enough data to calculate ADX.")
        return None
    df = pd.DataFrame({'high': high, 'low': low, 'close': close})
    adx = ta.adx(df['high'], df['low'], df['close'], length=period)
    if adx is None or adx.empty or 'ADX_' + str(period) not in adx:
        logger.warning("ADX calculation returned empty result.")
        return None
    return adx.iloc[-1][f'ADX_{period}']
