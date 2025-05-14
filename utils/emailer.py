import os
import base64
import logging
from azure.communication.email import EmailClient
from config import AZURE_EMAIL_CONNECTION_STRING, AZURE_EMAIL_SENDER
import json

logger = logging.getLogger(__name__)

def load_recipients(json_path):
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data.get('to', [])
    except Exception as e:
        logger.error(f"Failed to load recipients from {json_path}: {e}")
        return []

def send_email(subject, plain_text, html_content, attachment_path=None, recipients_json='config/email_recipients.json'):
    connection_string = AZURE_EMAIL_CONNECTION_STRING
    sender_address = AZURE_EMAIL_SENDER
    if not connection_string or not sender_address:
        logger.error("Azure Email connection string or sender address not set in environment variables.")
        return
    recipients = load_recipients(recipients_json)
    if not recipients:
        logger.error(f"No recipients found in {recipients_json}")
        return
    try:
        client = EmailClient.from_connection_string(connection_string)
        message = {
            "senderAddress": sender_address,
            "recipients": {"to": [{"address": r} for r in recipients]},
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
        logger.info(f"Email sent: {result['id']}")
        print("Email sent: ", result['id'])
    except Exception as ex:
        logger.error(f"Failed to send email: {ex}")
        print(ex)
