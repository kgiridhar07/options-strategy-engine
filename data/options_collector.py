import os
import requests
from typing import List, Dict, Any

ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_API_SECRET = os.getenv('ALPACA_API_SECRET')
ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_API_SECRET
}


def get_expiration_dates(ticker: str) -> List[str]:
    """
    Return a list of expiration dates for the given ticker using Alpaca REST API.
    """
    url = f"{ALPACA_BASE_URL}/v2/options/contracts?underlying_symbol={ticker}&limit=1000"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    expiries = set()
    for contract in data.get('contracts', []):
        expiries.add(contract['expiration_date'])
    return sorted(expiries)


def get_options_chain(ticker: str, expiry: str) -> List[Dict[str, Any]]:
    """
    Return a list of dicts, each representing an option contract for the given ticker and expiry using Alpaca REST API.
    """
    url = f"{ALPACA_BASE_URL}/v2/options/contracts?underlying_symbol={ticker}&expiration_date={expiry}&limit=1000"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    results = []
    for contract in data.get('contracts', []):
        results.append({
            'expiration_date': contract.get('expiration_date'),
            'strike_price': contract.get('strike_price'),
            'option_type': contract.get('type'),
            'bid': contract.get('bid'),
            'ask': contract.get('ask'),
            'last_price': contract.get('last_price'),
            'open_interest': contract.get('open_interest'),
            'volume': contract.get('volume'),
            'implied_volatility': contract.get('implied_volatility'),
            'delta': contract.get('delta'),
            'theta': contract.get('theta'),
            'gamma': contract.get('gamma'),
            'vega': contract.get('vega'),
            'rho': contract.get('rho')
        })
    return results
