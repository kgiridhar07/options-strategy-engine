from utils.ticker_loader import load_tickers
from data.snapshot_collector import (
    get_all_snapshots,
    get_last_trade_price_from_snapshot,
    get_previous_close_from_snapshot,
    get_percent_change_from_snapshot,
    get_latest_volume_from_snapshot,
    get_latest_quote_from_snapshot,
    get_latest_trade_price
)
from data.history_collector import get_historical_closes
from indicators.rsi import calculate_rsi
from indicators.sma import sma_20, sma_50, sma_200
from indicators.ema import ema_12, ema_20, ema_50, ema_200
from indicators.macd import calculate_macd
from indicators.bollinger import calculate_bollinger_bands
from data.corporate_events import get_next_earnings_and_dividend_dates
from data.options_collector import get_expiration_dates, get_options_chain
import logging
from azure.storage.blob import BlobServiceClient
import os
import csv
from datetime import datetime
from utils.emailer import send_email

# Azure Blob Storage setup
AZURE_CONNECTION_STRING = os.getenv('AZURE_BLOB_CONNECTION_STRING')
AZURE_CONTAINER_NAME = os.getenv('AZURE_BLOB_CONTAINER', 'trading-data')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SEND_EMAIL = False  # Set to True to enable email notifications
COLLECT_STOCK_DATA = False  # Set to True to enable email notifications
COLLECT_OPTIONS_DATA = True  # Set to True to enable email notifications
UPLOAD_TO_BLOB = False  # Set to True to enable Azure Blob upload

def upload_to_blob(filename, data):
    if not AZURE_CONNECTION_STRING:
        logger.error('Azure Blob Storage connection string not set in environment variable AZURE_BLOB_CONNECTION_STRING')
        return
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
        try:
            container_client.create_container()
        except Exception:
            pass  # Container may already exist
        blob_client = container_client.get_blob_client(filename)
        blob_client.upload_blob(data, overwrite=True)
        logger.info(f"Uploaded {filename} to Azure Blob Storage container '{AZURE_CONTAINER_NAME}'")
    except Exception as e:
        logger.error(f"Failed to upload {filename} to Azure Blob Storage: {e}")

def collect_snapshots(tickers):
    return get_all_snapshots(tickers)

def write_csv(filename, csv_rows):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)

def collect_stock_data(tickers, today_str, corporate_events=None):
    snapshots = get_all_snapshots(tickers)
    filename = f"indicators_{today_str}.csv"
    csv_rows = []
    header = [
        "ticker", "current_price", "basic_snapshot", "previous_close", "percent_change", "latest_volume",
        "rsi_14", "sma_20", "sma_50", "sma_200", "ema_12", "ema_20", "ema_50", "ema_200",
        "macd", "macd_signal", "bb_upper", "bb_middle", "bb_lower",
        "earnings_date", "dividend_date", "ex_dividend_date"
    ]
    csv_rows.append(header)
    for ticker in tickers:
        snap = snapshots[ticker]
        current_price = round(get_last_trade_price_from_snapshot(snap), 2) if get_last_trade_price_from_snapshot(snap) is not None else None
        basic_snapshot = get_latest_trade_price(ticker)
        previous_close = round(get_previous_close_from_snapshot(snap), 2) if get_previous_close_from_snapshot(snap) is not None else None
        percent_change = round(get_percent_change_from_snapshot(snap), 2) if get_percent_change_from_snapshot(snap) is not None else None
        latest_volume = round(get_latest_volume_from_snapshot(snap), 2) if get_latest_volume_from_snapshot(snap) is not None else None
        closes = get_historical_closes(ticker, lookback_days=365)
        rsi = calculate_rsi(closes[-150:], period=14)
        sma20 = sma_20(closes)
        sma50 = sma_50(closes)
        sma200 = sma_200(closes)
        ema12 = ema_12(closes)
        ema20 = ema_20(closes)
        ema50 = ema_50(closes)
        ema200 = ema_200(closes)
        macd_line, signal_line = calculate_macd(closes)
        macd_val = macd_line[-1] if macd_line else None
        signal_val = signal_line[-1] if signal_line else None
        upper, middle, lower = calculate_bollinger_bands(closes)
        # Get corporate events for this ticker
        ce = corporate_events[ticker] if corporate_events and ticker in corporate_events else {}
        row = [
            ticker,
            current_price,
            basic_snapshot,
            previous_close,
            percent_change,
            latest_volume,
            round(rsi, 2) if rsi is not None else None,
            round(sma20, 2) if sma20 is not None else None,
            round(sma50, 2) if sma50 is not None else None,
            round(sma200, 2) if sma200 is not None else None,
            round(ema12, 2) if ema12 is not None else None,
            round(ema20, 2) if ema20 is not None else None,
            round(ema50, 2) if ema50 is not None else None,
            round(ema200, 2) if ema200 is not None else None,
            round(macd_val, 2) if macd_val is not None else None,
            round(signal_val, 2) if signal_val is not None else None,
            round(upper, 2) if upper is not None else None,
            round(middle, 2) if middle is not None else None,
            round(lower, 2) if lower is not None else None,
            ce.get('earnings_date'),
            ce.get('dividend_date'),
            ce.get('ex_dividend_date')
        ]
        csv_rows.append(row)
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    # Upload to Azure Blob Storage (controlled by UPLOAD_TO_BLOB flag)
    if UPLOAD_TO_BLOB:
        with open(filename, "rb") as f:
            upload_to_blob(filename, f)
    print("All tickers processed and uploaded as one CSV file.")
    return filename


def main():
    tickers = load_tickers()
    print("Processing tickers:", tickers)
    today_str = datetime.now().strftime("%Y-%m-%d")
    # Collect corporate events for all tickers
    corporate_events = {ticker: get_next_earnings_and_dividend_dates(ticker) for ticker in tickers}
    if COLLECT_STOCK_DATA:
        # Collect and process stock data, passing corporate events
        filename = collect_stock_data(tickers, today_str, corporate_events=corporate_events)

    if COLLECT_OPTIONS_DATA:
        # Collect and process options data using Alpaca
        for ticker in tickers:
            expiries = get_expiration_dates(ticker)
            print(f"{ticker} option expiries: {expiries}")


    # Send email notification using the new emailer (optional)
    if SEND_EMAIL:
        # You can add more details to the email body here as needed
        send_email(
            subject=f"Trading Analytics CSV Uploaded: {filename}",
            plain_text=f"Your daily trading analytics CSV ({filename}) has been processed and is ready.",
            html_content=f"""
            <html>
                <body>
                    <h2>Your daily trading analytics CSV ({filename}) has been processed and is ready.</h2>
                    <!-- Add more details here if needed -->
                </body>
            </html>
            """,
            attachment_path=filename,
            recipients_json="project/config/email_recipients.json"
        )




if __name__ == "__main__":
    main()
