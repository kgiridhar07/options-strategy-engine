import pandas as pd
from datetime import datetime
import yfinance as yf

def compute_ytd_52w_indicators(df: pd.DataFrame, today: str = None):
    """
    Compute YTD % return, 52-week low, 52-week high, and range position for a stock.
    Args:
        df: DataFrame with columns ['date', 'close'] (date as string YYYY-MM-DD)
        today: Optional, override today's date (YYYY-MM-DD)
    Returns:
        dict with keys: ytd_return, low_52w, high_52w, range_pos_pct, pct_from_52w_high, pct_from_52w_low
    """
    if today is None:
        today = datetime.today().strftime('%Y-%m-%d')
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    today_dt = pd.to_datetime(today)
    # Filter to last 1 year (52 weeks)
    one_year_ago = today_dt - pd.Timedelta(days=365)
    df_52w = df[df['date'] >= one_year_ago]
    # YTD return
    ytd_start = pd.Timestamp(year=today_dt.year, month=1, day=1)
    df_ytd = df[df['date'] >= ytd_start]
    if not df_ytd.empty:
        ytd_first = df_ytd.iloc[0]['close'].item() if hasattr(df_ytd.iloc[0]['close'], 'item') else float(df_ytd.iloc[0]['close'])
        ytd_last = df_ytd.iloc[-1]['close'].item() if hasattr(df_ytd.iloc[-1]['close'], 'item') else float(df_ytd.iloc[-1]['close'])
        ytd_return = ((ytd_last - ytd_first) / ytd_first) * 100
    else:
        ytd_return = None
    # 52w low/high
    if not df_52w.empty:
        low_52w = df_52w['close'].min().item() if hasattr(df_52w['close'].min(), 'item') else float(df_52w['close'].min())
        high_52w = df_52w['close'].max().item() if hasattr(df_52w['close'].max(), 'item') else float(df_52w['close'].max())
        last_close = df_52w.iloc[-1]['close'].item() if hasattr(df_52w.iloc[-1]['close'], 'item') else float(df_52w.iloc[-1]['close'])
        # Range position: 0% = 52w low, 100% = 52w high
        if high_52w != low_52w:
            range_pos_pct = ((last_close - low_52w) / (high_52w - low_52w)) * 100
        else:
            range_pos_pct = 100.0
        pct_from_52w_high = ((last_close - high_52w) / high_52w) * 100
        pct_from_52w_low = ((last_close - low_52w) / low_52w) * 100
    else:
        low_52w = high_52w = range_pos_pct = pct_from_52w_high = pct_from_52w_low = None
    return {
        'ytd_return': round(ytd_return, 2) if ytd_return is not None else None,
        'low_52w': round(low_52w, 2) if low_52w is not None else None,
        'high_52w': round(high_52w, 2) if high_52w is not None else None,
        'range_pos_pct': round(range_pos_pct, 2) if range_pos_pct is not None else None,
        'pct_from_52w_high': round(pct_from_52w_high, 2) if pct_from_52w_high is not None else None,
        'pct_from_52w_low': round(pct_from_52w_low, 2) if pct_from_52w_low is not None else None,
    }

def get_ytd_52w_indicators_for_ticker(ticker: str, today: str = None):
    """
    Fetch historical data for the ticker and compute YTD/52W indicators.
    Args:
        ticker: Stock symbol
        today: Optional, override today's date (YYYY-MM-DD)
    Returns:
        dict with indicator values
    """
    df = yf.download(ticker, period='2y', interval='1d', progress=False, auto_adjust=True)
    if df.empty:
        return {k: None for k in ['ytd_return', 'low_52w', 'high_52w', 'range_pos_pct', 'pct_from_52w_high', 'pct_from_52w_low']}
    df = df.reset_index()[['Date', 'Close']]
    df = df.rename(columns={'Date': 'date', 'Close': 'close'})
    return compute_ytd_52w_indicators(df, today)
