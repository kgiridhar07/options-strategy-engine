import os
import glob
import json
from datetime import datetime
import base64
import logging
from azure.communication.email import EmailClient
from config import AZURE_EMAIL_CONNECTION_STRING, AZURE_EMAIL_SENDER

def find_latest_file(folder, pattern):
    files = glob.glob(os.path.join(folder, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def extract_reason(signals, signal_type):
    # Return a comma-separated list of strategy names where the signal matches the type (e.g., 'strongly bullish')
    reasons = [name for name, v in signals.items() if signal_type in v.get('signal', '').lower()]
    return ', '.join(reasons) if reasons else 'N/A'

def format_signal_table(entries, signal_type, color):
    # entries: list of dicts for a given signal_type
    if not entries:
        return f'<p style="color:gray;">No {signal_type.title()} stocks today.</p>'
    table = f"""
    <style>
    @media only screen and (max-width: 700px) {{
        table.responsive-table, table.responsive-table thead, table.responsive-table tbody, table.responsive-table th, table.responsive-table td, table.responsive-table tr {{
            display: block;
        }}
        table.responsive-table thead tr {{
            display: none;
        }}
        table.responsive-table tr {{ margin-bottom: 15px; }}
        table.responsive-table td {{
            border: none;
            position: relative;
            padding-left: 50%;
            min-height: 40px;
            box-sizing: border-box;
        }}
        table.responsive-table td:before {{
            position: absolute;
            top: 8px;
            left: 8px;
            width: 45%;
            white-space: nowrap;
            font-weight: bold;
            color: #333;
        }}
        table.responsive-table td:nth-of-type(1):before {{ content: 'Ticker'; }}
        table.responsive-table td:nth-of-type(2):before {{ content: 'Current Price'; }}
        table.responsive-table td:nth-of-type(3):before {{ content: '52W High'; }}
        table.responsive-table td:nth-of-type(4):before {{ content: '52W Low'; }}
        table.responsive-table td:nth-of-type(5):before {{ content: 'Reason'; }}
    }}
    </style>
    <table class="responsive-table" style="border-collapse:collapse;width:100%;margin-bottom:20px;font-family:'Segoe UI',sans-serif;font-size:14px;">
    <thead>
    <tr style="background:{color};color:white;font-weight:bold;text-align:left;">
        <th style='border:1px solid #ddd;padding:8px;'>Ticker</th>
        <th style='border:1px solid #ddd;padding:8px;'>Current Price</th>
        <th style='border:1px solid #ddd;padding:8px;'>52W High</th>
        <th style='border:1px solid #ddd;padding:8px;'>52W Low</th>
        <th style='border:1px solid #ddd;padding:8px;'>Reason</th>
    </tr>
    </thead>
    <tbody>
    """
    for entry in entries:
        ticker = entry.get('ticker', '')
        price = entry.get('current_price', '')
        high = entry.get('high_52w', '')
        low = entry.get('low_52w', '')
        reason = extract_reason(entry.get('signals', {}), signal_type.lower())
        table += f"""
        <tr style="background:#fff;">
            <td style='border:1px solid #ddd;padding:8px;'>{ticker}</td>
            <td style='border:1px solid #ddd;padding:8px;'>{price}</td>
            <td style='border:1px solid #ddd;padding:8px;'>{high}</td>
            <td style='border:1px solid #ddd;padding:8px;'>{low}</td>
            <td style='border:1px solid #ddd;padding:8px;'>{reason}</td>
        </tr>
        """
    table += "</tbody></table>"
    return table

def load_recipients(json_path):
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        # Hide email addresses in logs and errors
        return data.get('to', [])
    except Exception as e:
        print(f"Failed to load recipients from {json_path}: {e}")
        return []

def send_email(subject, plain_text, html_content, attachment_path=None, recipients_json='config/email_recipients.json'):
    connection_string = AZURE_EMAIL_CONNECTION_STRING
    sender_address = AZURE_EMAIL_SENDER
    if not connection_string or not sender_address:
        print("Azure Email connection string or sender address not set in environment variables.")
        return
    recipients = load_recipients(recipients_json)
    if not recipients:
        print(f"No recipients found in {recipients_json}")
        return
    try:
        client = EmailClient.from_connection_string(connection_string)
        message = {
            "senderAddress": sender_address,
            # Use BCC so recipients are not visible to each other
            "recipients": {"bcc": [{"address": r} for r in recipients]},
            "content": {
                "subject": subject,
                "plainText": plain_text,
                "html": html_content
            },
        }
        if attachment_path:
            with open(attachment_path, "rb") as f:
                file_bytes = f.read()
                encoded = base64.b64encode(file_bytes).decode("utf-8")
            message["attachments"] = [
                {
                    "name": os.path.basename(attachment_path),
                    "contentType": "text/csv",
                    "contentInBase64": encoded
                }
            ]
        poller = client.begin_send(message)
        result = poller.result()
        print(f"Email sent: {result['id']}")
    except Exception as ex:
        # Hide recipient emails in error output
        print(f"Failed to send email: {str(ex).replace(str(recipients), '[HIDDEN]')}")

def format_email_body():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    analysis_dir = os.path.join(project_root, 'output/bull_bear_analysis')
    today_str = datetime.now().strftime('%Y-%m-%d')
    analysis_json = find_latest_file(analysis_dir, f'bull_bear_analysis_{today_str}.json')
    if not analysis_json:
        return ("No Analysis", "No analysis file found for today.", "<p>No analysis file found for today.</p>", [])
    with open(analysis_json) as f:
        data = json.load(f)
    strongly_bullish = [d for d in data if d.get('combined_signal', {}).get('text') == 'Strongly Bullish']
    strongly_bearish = [d for d in data if d.get('combined_signal', {}).get('text') == 'Strongly Bearish']
    neutral = [d for d in data if d.get('combined_signal', {}).get('text') == 'Neutral']
    # Build tables
    bull_table = format_signal_table(strongly_bullish, 'strongly bullish', '#2e8b57')
    bear_table = format_signal_table(strongly_bearish, 'strongly bearish', '#b22222')
    neutral_table = format_signal_table(neutral, 'neutral', '#4682b4')
    # Logo and header
    logo = '<div style="font-size:2em;font-weight:bold;color:#4682b4;margin-bottom:10px;">🐂📈 Bull & Bear Daily Signal Report 📉🐻</div>'
    html_content = f"""
    <html>
        <body style='font-family:sans-serif;'>
            {logo}
            <h2 style='color:#333;'>Strongly Bullish Stocks</h2>
            {bull_table}
            <h2 style='color:#333;'>Strongly Bearish Stocks</h2>
            {bear_table}
            <h2 style='color:#333;'>Neutral Stocks</h2>
            {neutral_table}
            <p style='font-size:0.9em;color:#888;'>Generated on {today_str}</p>
        </body>
    </html>
    """
    subject = f"Bull & Bear Daily Signal Report - {today_str}"
    plain_text = f"See attached HTML for today's signal tables."
    attachments = [analysis_json]
    return subject, plain_text, html_content, attachments
