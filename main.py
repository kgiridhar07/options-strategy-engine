# Add the project root to sys.path before any other imports that use local packages
import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from utils.ticker_loader import load_tickers
from data.corporate_events import get_next_earnings_and_dividend_dates
from data.options_collector import collect_options_data
import logging
from azure.storage.blob import BlobServiceClient
from datetime import datetime, timedelta
import calendar
from email_utils.email_formatter import send_email, format_email_body
from utils.logger import get_logger
from indicators.process_indicators import process_indicators
import subprocess

# Ensure logs and output directories exist (relative to project root)
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f"main_{datetime.now().strftime('%Y-%m-%d')}.log")
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
logger = get_logger(__name__)
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.addHandler(file_handler)

# Azure Blob Storage setup
AZURE_CONNECTION_STRING = os.getenv('AZURE_BLOB_CONNECTION_STRING')
AZURE_CONTAINER_NAME = os.getenv('AZURE_BLOB_CONTAINER', 'trading-data')

SEND_EMAIL = True  # Set to True to enable email notifications
COLLECT_STOCK_DATA = True  # Set to True to enable email notifications
COLLECT_OPTIONS_DATA = False  # Set to True to enable email notifications
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

def main():
    tickers = load_tickers()
    print("Processing tickers:", tickers)
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    weekday = today.weekday()  # Monday=0, ..., Friday=4

    # Collect corporate events for all tickers
    corporate_events = {ticker: get_next_earnings_and_dividend_dates(ticker) for ticker in tickers}
    # Use process_indicators for all indicator/stock data creation
    indicator_csv = process_indicators(tickers=tickers, today_str=today_str, corporate_events=corporate_events)
    print(f"Indicator CSV generated: {indicator_csv}")
    filename = indicator_csv  # For downstream usage (email, etc.)

    # Always run bull_bear_indicator_analysis.py (Mon-Fri)
    print("Running bull_bear_indicator_analysis.py ...")
    subprocess.run(["python3", os.path.join(PROJECT_ROOT, "strategy/bull_bear_indicator_analysis.py")], check=True)

    trade_csv_path = None
    trade_json_path = None
    # Only run trades and attach trade files on Friday
    if weekday == 4:  # Friday
        print("Running bull_bear_credit_trades.py ...")
        subprocess.run(["python3", os.path.join(PROJECT_ROOT, "trade_generator/bull_bear_credit_trades.py")], check=True)
        # Find latest trade files for attachment
        trades_dir = os.path.join(PROJECT_ROOT, "output/bull_bear_trades_out")
        trade_json_path = None
        trade_csv_path = None
        if os.path.isdir(trades_dir):
            files = os.listdir(trades_dir)
            trade_jsons = sorted([f for f in files if f.endswith(".json") and f.startswith("bull_bear_trades_")], reverse=True)
            trade_csvs = sorted([f for f in files if f.endswith(".csv") and f.startswith("bull_bear_trades_summary_")], reverse=True)
            if trade_jsons:
                trade_json_path = os.path.join(trades_dir, trade_jsons[0])
            if trade_csvs:
                trade_csv_path = os.path.join(trades_dir, trade_csvs[0])

    # Send summary email with tables if enabled
    if SEND_EMAIL:
        subject, plain_text, html_content, attachments = format_email_body()
        # On Friday, attach both the latest trades JSON and CSV if available
        if weekday == 4:
            extra_attachments = []
            if trade_json_path:
                extra_attachments.append(trade_json_path)
            if trade_csv_path:
                extra_attachments.append(trade_csv_path)
            # Always include the analysis JSON as the first attachment
            if attachments:
                all_attachments = [attachments[0]] + extra_attachments
            else:
                all_attachments = extra_attachments
            send_email(
                subject=subject,
                plain_text=plain_text,
                html_content=html_content,
                attachment_path=all_attachments[0] if all_attachments else None,
                recipients_json=os.path.join(PROJECT_ROOT, "config/email_recipients.json")
            )
        else:
            # Mon-Thu: just send the daily signal mail with analysis JSON
            send_email(
                subject=subject,
                plain_text=plain_text,
                html_content=html_content,
                attachment_path=attachments[0] if attachments else None,
                recipients_json=os.path.join(PROJECT_ROOT, "config/email_recipients.json")
            )


if __name__ == "__main__":
    main()
