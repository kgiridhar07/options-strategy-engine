# indicators/bollinger.py
import pandas as pd
import pandas_ta as ta
from utils.logger import get_logger

logger = get_logger(__name__)

def calculate_bollinger_bands(prices, period=20, std=2):
    """
    Calculate Bollinger Bands for a list of prices.
    Args:
        prices (list[float]): List of closing prices.
        period (int): Number of periods for the moving average.
        std (int): Number of standard deviations for the bands.
    Returns:
        tuple: (upper_band, middle_band, lower_band) for the most recent value, or (None, None, None) if not enough data.
    """
    if len(prices) < period:
        return None, None, None
    df = pd.DataFrame({'close': prices})
    bbands = ta.bbands(df['close'], length=period, std=std)
    if bbands is None or bbands.empty:
        return None, None, None
    upper = bbands.iloc[-1][f'BBU_{period}_{std}.0'] if f'BBU_{period}_{std}.0' in bbands else bbands.iloc[-1,0]
    middle = bbands.iloc[-1][f'BBM_{period}_{std}.0'] if f'BBM_{period}_{std}.0' in bbands else bbands.iloc[-1,1]
    lower = bbands.iloc[-1][f'BBL_{period}_{std}.0'] if f'BBL_{period}_{std}.0' in bbands else bbands.iloc[-1,2]
    return upper, middle, lower
