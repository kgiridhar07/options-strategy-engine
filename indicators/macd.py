# indicators/macd.py
import pandas as pd
import pandas_ta as ta

def calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate MACD and signal line for a list of prices using pandas_ta.
    Args:
        prices (list[float]): List of closing prices.
        fast_period (int): Fast EMA period.
        slow_period (int): Slow EMA period.
        signal_period (int): Signal line EMA period.
    Returns:
        tuple: (macd_line, signal_line)
    """
    if len(prices) < slow_period:
        return [], []
    df = pd.DataFrame({'close': prices})
    macd_df = ta.macd(df['close'], fast=fast_period, slow=slow_period, signal=signal_period)
    if macd_df is None or macd_df.empty:
        return [], []
    macd_line = macd_df['MACD_12_26_9'].tolist() if f'MACD_{fast_period}_{slow_period}_{signal_period}' in macd_df else macd_df.iloc[:,0].tolist()
    signal_line = macd_df['MACDs_12_26_9'].tolist() if f'MACDs_{fast_period}_{slow_period}_{signal_period}' in macd_df else macd_df.iloc[:,1].tolist()
    return macd_line, signal_line
