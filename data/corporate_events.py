import logging
import yfinance as yf
from utils.logger import get_logger

logger = get_logger(__name__)

def get_next_earnings_and_dividend_dates(symbol: str):
    """
    Fetch the next earnings date, dividend date, and ex-dividend date for a ticker using Yahoo Finance (yfinance).
    Returns a dict: {'earnings_date': str or None, 'dividend_date': str or None, 'ex_dividend_date': str or None}
    """
    try:
        ticker = yf.Ticker(symbol)
        calendar = ticker.calendar
        # print(calendar)  # Optionally keep for debugging
        earnings_date = None
        dividend_date = None
        ex_dividend_date = None
        # Handle DataFrame (normal case)
        if hasattr(calendar, 'empty') and not calendar.empty:
            # Earnings Date
            if 'Earnings Date' in calendar.index:
                earnings_val = calendar.loc['Earnings Date'].values[0]
                if isinstance(earnings_val, (list, tuple)) and earnings_val:
                    earnings_val = earnings_val[0]
                if hasattr(earnings_val, 'strftime'):
                    earnings_date = earnings_val.strftime('%Y-%m-%d')
                else:
                    earnings_date = str(earnings_val)
            # Dividend Date
            if 'Dividend Date' in calendar.index:
                dividend_val = calendar.loc['Dividend Date'].values[0]
                if hasattr(dividend_val, 'strftime'):
                    dividend_date = dividend_val.strftime('%Y-%m-%d')
                else:
                    dividend_date = str(dividend_val)
            # Ex-Dividend Date
            if 'Ex-Dividend Date' in calendar.index:
                ex_dividend_val = calendar.loc['Ex-Dividend Date'].values[0]
                if hasattr(ex_dividend_val, 'strftime'):
                    ex_dividend_date = ex_dividend_val.strftime('%Y-%m-%d')
                else:
                    ex_dividend_date = str(ex_dividend_val)
        # Handle dict (edge case)
        elif isinstance(calendar, dict):
            # Earnings Date
            if 'Earnings Date' in calendar:
                earnings_val = calendar['Earnings Date']
                if isinstance(earnings_val, (list, tuple)) and earnings_val:
                    earnings_val = earnings_val[0]
                if hasattr(earnings_val, 'strftime'):
                    earnings_date = earnings_val.strftime('%Y-%m-%d')
                else:
                    earnings_date = str(earnings_val)
            # Dividend Date
            if 'Dividend Date' in calendar:
                dividend_val = calendar['Dividend Date']
                if hasattr(dividend_val, 'strftime'):
                    dividend_date = dividend_val.strftime('%Y-%m-%d')
                else:
                    dividend_date = str(dividend_val)
            # Ex-Dividend Date
            if 'Ex-Dividend Date' in calendar:
                ex_dividend_val = calendar['Ex-Dividend Date']
                if hasattr(ex_dividend_val, 'strftime'):
                    ex_dividend_date = ex_dividend_val.strftime('%Y-%m-%d')
                else:
                    ex_dividend_date = str(ex_dividend_val)
        return {
            'earnings_date': earnings_date,
            'dividend_date': dividend_date,
            'ex_dividend_date': ex_dividend_date
        }
    except Exception as e:
        logger.warning(f"Could not fetch dates for {symbol}: {e}")
    return {
        'earnings_date': None,
        'dividend_date': None,
        'ex_dividend_date': None
    }