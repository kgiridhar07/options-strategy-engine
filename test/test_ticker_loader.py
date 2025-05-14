import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import json
from utils.ticker_loader import load_tickers

class TestTickerLoader(unittest.TestCase):
    def test_load_tickers_default(self):
        tickers = load_tickers()
        self.assertIsInstance(tickers, list)
        # Dynamically check against the current tickers.json
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'tickers.json')
        with open(json_path, 'r') as f:
            expected = json.load(f).get('tickers', [])
        self.assertEqual(tickers, expected)

    def test_load_tickers_custom_path(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'tickers.json')
        tickers = load_tickers(path)
        with open(path, 'r') as f:
            expected = json.load(f).get('tickers', [])
        self.assertEqual(tickers, expected)

if __name__ == "__main__":
    unittest.main()
