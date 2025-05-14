# Configuration for tickers, thresholds, and environment
import os
from dotenv import load_dotenv

load_dotenv()
# Load environment variables from the .env file
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL")
ALPACA_TRADE_URL = os.getenv("ALPACA_TRADE_URL")
ALPACA_OPTION_SNAPSHOT_URL = os.getenv("ALPACA_OPTION_SNAPSHOT_URL")
AZURE_EMAIL_CONNECTION_STRING = os.getenv("AZURE_EMAIL_CONNECTION_STRING")
AZURE_EMAIL_SENDER = os.getenv("AZURE_EMAIL_SENDER")
