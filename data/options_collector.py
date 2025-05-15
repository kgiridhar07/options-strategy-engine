import os
import requests
from typing import List, Dict, Any
from utils.alpaca_api import get_option_chain, get_raw_last_trade
from utils.logger import get_logger
from data.corporate_events import get_next_earnings_and_dividend_dates
from datetime import datetime, timedelta
import csv
import re

logger = get_logger(__name__)

ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_API_SECRET = os.getenv('ALPACA_API_SECRET')
ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')


def get_underlying_price(result,symbol):
    """
    Fetch the current (latest) price of a stock using Alpaca's StockHistoricalDataClient.
    Returns the last trade price or None if unavailable.
    """
    try:
        # result is a dict {symbol: trade_obj} or a trade_obj
        if isinstance(result, dict):
            trade = result.get(symbol)
        else:
            trade = result
        if trade and hasattr(trade, 'price'):
            return trade.price
    except Exception as e:
        logger.error(f"Error fetching current price for {symbol}: {e}")
    return None 


def parse_option_symbol(symbol):
    m = re.match(r"([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})", symbol)
    if not m:
        raise ValueError(f"Invalid OCC option symbol: {symbol}")
    underlying = m.group(1)
    year = int(m.group(2)) + 2000
    month = int(m.group(3))
    day = int(m.group(4))
    opt_type = "call" if m.group(5) == "C" else "put"
    strike = int(m.group(6)) / 1000
    exp_date = f"{year:04d}-{month:02d}-{day:02d}"
    return underlying, exp_date, opt_type, strike

def collect_options_data(symbol, expiration_date_gte, expiration_date_lte, output_csv, earnings_info=None):
    # DEBUG: Print the symbol and date range being processed
    logger.info(f"Collecting options for {symbol} from {expiration_date_gte} to {expiration_date_lte}")
    
    # Fetch all option contracts for the symbol in the date range
    contracts = get_option_chain(symbol, expiration_date_gte, expiration_date_lte)
    logger.info(f"Fetched {len(contracts)} contracts for {symbol}")

    # Get the latest underlying price for the symbol
    underlying_price = None
    try:
        underlying_price = get_underlying_price(get_raw_last_trade(symbol_or_symbols=symbol),symbol)
    except Exception as e:
        logger.error(f"Error fetching underlying price for {symbol}: {e}")
    logger.info(f"Underlying price for {symbol}: {underlying_price}")
    # Use passed-in earnings_info if available, else fetch
    if earnings_info is None:
        earnings_info = get_next_earnings_and_dividend_dates(symbol)
    earnings_date = earnings_info.get('earnings_date') if earnings_info else None
    logger.info(f"Earnings info for {symbol}: {earnings_info}")
    
    # Prepare CSV header (removed 'last_price')
    header = [
        'symbol','option_symbol','type','expiration_date','strike','days_to_expiration',
        'bid','ask','mid',
        'delta','gamma','theta','vega','rho','implied_volatility','underlying_price',
        'in_the_money','earnings_within_dte'
    ]
    rows = [header]
    today = datetime.now().date()
    
    # Process each contract and extract required fields
    for c in contracts.values():
        occ_symbol = c.symbol
        underlying, exp_date, opt_type, strike = parse_option_symbol(occ_symbol)
        dte = (datetime.strptime(exp_date, '%Y-%m-%d').date() - today).days
        
        quote = c.latest_quote
        bid = quote.bid_price
        ask = quote.ask_price
        mid = (bid + ask)/2 if bid is not None and ask is not None else None    
        

        greeks = c.greeks or {}
        delta = greeks.delta if hasattr(greeks, 'delta') else None
        gamma = greeks.gamma if hasattr(greeks, 'gamma') else None
        theta = greeks.theta if hasattr(greeks, 'theta') else None
        vega = greeks.vega if hasattr(greeks, 'vega') else None
        rho = greeks.rho if hasattr(greeks, 'rho') else None
        
        iv = c.implied_volatility
        # Calculate in_the_money based on option type, strike, and underlying price
        if opt_type == "call":
            in_the_money = underlying_price is not None and underlying_price > strike
        else:  # put
            in_the_money = underlying_price is not None and underlying_price < strike
        
        earnings_within_dte = False
        if earnings_date:
            earnings_within_dte = (datetime.strptime(earnings_date, '%Y-%m-%d').date() <= datetime.strptime(exp_date, '%Y-%m-%d').date())
        
        row = [
            underlying,
            occ_symbol,
            opt_type,
            exp_date,
            strike,
            dte,
            bid,
            ask,
            mid,
            delta,
            gamma,
            theta,
            vega,
            rho,
            iv,
            underlying_price,
            in_the_money,
            earnings_within_dte
        ]
        rows.append(row)
    
    # Ensure output directory exists and output_csv is in OUTPUT_DIR
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.isabs(output_csv):
        output_csv = os.path.join(OUTPUT_DIR, output_csv)
    
    # Write all rows to the output CSV file
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    logger.info(f"Options data for {symbol} saved to {output_csv}")

