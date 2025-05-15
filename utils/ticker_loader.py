# Loads tickers from config/tickers.json
import json
import os
from utils.logger import get_logger

logger = get_logger(__name__)

def load_tickers(json_path=None):
    if json_path is None:
        # Default path relative to project root
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'tickers.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data.get('tickers', [])
