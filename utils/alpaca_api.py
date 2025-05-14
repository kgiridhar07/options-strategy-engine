# Alpaca credentials and clients setup
from config import (
    ALPACA_API_KEY,
    ALPACA_API_SECRET,
    ALPACA_BASE_URL,
    ALPACA_TRADE_URL,
    ALPACA_OPTION_SNAPSHOT_URL
)

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest
from alpaca.data.requests import StockSnapshotRequest
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime

# Instantiate clients
trade_client = TradingClient(api_key=ALPACA_API_KEY, secret_key=ALPACA_API_SECRET, paper=True)
stock_data_client = StockHistoricalDataClient(api_key=ALPACA_API_KEY, secret_key=ALPACA_API_SECRET)

# Raw helpers

def get_account_info():
    return trade_client.get_account()

def get_raw_last_trade(symbol_or_symbols):
    """
    Makes the raw call to get the latest trade(s) for one or more symbols.
    Returns either a Trade object or dict of symbol: Trade.
    """
    req = StockLatestTradeRequest(symbol_or_symbols=symbol_or_symbols)
    return stock_data_client.get_stock_latest_trade(req)

def get_raw_basic_snapshot(symbol):
    req = StockSnapshotRequest(symbol_or_symbols=symbol)
    return stock_data_client.get_stock_snapshot(req)

def get_raw_historical_bars(symbol, timeframe, start, end, feed=None):
    """
    Fetch raw historical bars for a symbol using Alpaca SDK.
    Args:
        symbol (str): Ticker symbol
        timeframe (TimeFrame): Alpaca TimeFrame object (e.g., TimeFrame.Day)
        start (datetime): Start datetime (UTC)
        end (datetime): End datetime (UTC)
        feed (str, optional): Data feed to use ('iex' or 'sip').
    Returns:
        list: List of bar objects for the symbol
    """
    req_kwargs = dict(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start,
        end=end
    )
    if feed:
        req_kwargs['feed'] = feed
    req = StockBarsRequest(**req_kwargs)
    bars = stock_data_client.get_stock_bars(req)
    return bars[symbol]

