"""
Gmail API Service - Monitor and Read Gmail Messages
"""
import os
import logging
import json
import base64
import pickle
import time
import tempfile
from datetime import datetime
from typing import List, Dict, Optional, Any
from email.mime.text import MIMEText

# Gmail API imports
try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
except ImportError:
    logging.warning("Gmail API libraries not installed")

logger = logging.getLogger("gmail_service")

# Load .env file from project root
def load_env():
    """Manually load .env file from project root"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if os.getenv(key) is None:
                        os.environ[key] = value

# Load env on module import
load_env()

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Token pickle file for OAuth2
TOKEN_FILE = os.path.join(tempfile.gettempdir(), 'gmail_token.pickle')
DEFAULT_CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gmail_credentials.json')
DEFAULT_SERVICE_ACCOUNT_FILE = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'service_account.json'))

GMAIL_SERVICE_ACCOUNT_FILE = os.getenv('GMAIL_SERVICE_ACCOUNT_FILE') or DEFAULT_SERVICE_ACCOUNT_FILE
GMAIL_SERVICE_ACCOUNT_SUBJECT = os.getenv('GMAIL_SERVICE_ACCOUNT_SUBJECT') or os.getenv('GMAIL_IMPERSONATION_EMAIL')
GMAIL_OAUTH_CLIENT_FILE = os.getenv('GMAIL_OAUTH_CLIENT_FILE') or DEFAULT_CREDENTIALS_FILE

# Track processed emails
PROCESSED_EMAILS_FILE = os.path.join(tempfile.gettempdir(), 'gmail_processed.json')


class GmailService:
    def __init__(self):
        self.service = None
        self.credentials = None
        self.processed_emails = self.load_processed_emails()

    def authenticate(self):
        """Authenticate with Gmail API using OAuth2"""
        # Check if service account should be bypassed
        use_sa = os.getenv('GMAIL_USE_SERVICE_ACCOUNT', 'true').lower() == 'true'

        # 1) Try service account credentials first (for background/daemon usage)
        sa_path = GMAIL_SERVICE_ACCOUNT_FILE if GMAIL_SERVICE_ACCOUNT_FILE and os.path.exists(GMAIL_SERVICE_ACCOUNT_FILE) else None
        if sa_path and use_sa:
            try:
                creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
                if GMAIL_SERVICE_ACCOUNT_SUBJECT:
                    creds = creds.with_subject(GMAIL_SERVICE_ACCOUNT_SUBJECT)
                    logger.info("Gmail service account impersonation enabled for %s", GMAIL_SERVICE_ACCOUNT_SUBJECT)
                else:
                    logger.info("Gmail service account authentication without impersonation subject")

                self.credentials = creds
                self.service = build('gmail', 'v1', credentials=creds)
                logger.info("Gmail authenticated via service account %s", os.path.basename(sa_path))
                return True
            except Exception as e:
                logger.error(f"Service account authentication failed: {e}")
                logger.info("Falling back to OAuth client credentials.")

        creds = None

        # 2) Fallback to OAuth client workflow (interactive)
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                logger.warning(f"Failed to load Gmail token cache: {e}. Re-authenticating.")
                creds = None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh Gmail token: {e}")
                creds = None

        if not creds:
            if not os.path.exists(GMAIL_OAUTH_CLIENT_FILE):
                logger.error(f"Gmail credentials file not found: {GMAIL_OAUTH_CLIENT_FILE}")
                logger.info("To enable Gmail integration:")
                logger.info("1. Go to https://console.cloud.google.com/")
                logger.info("2. Create OAuth 2.0 credentials")
                logger.info("3. Download JSON and set GMAIL_OAUTH_CLIENT_FILE or place gmail_credentials.json in backend directory")
                return False

            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_OAUTH_CLIENT_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

            # Save credentials for next run
            try:
                with open(TOKEN_FILE, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                logger.warning(f"Failed to cache Gmail token: {e}")

        self.credentials = creds
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail authenticated via OAuth client credentials")
        return True

    def get_recent_emails(self, max_results: int = 10, unread_only: bool = True) -> List[Dict[str, Any]]:
        """Get recent emails from Gmail."""
        if not self.service:
            logger.error("Gmail service not authenticated")
            return []

        try:
            # Get recent messages
            params = {
                'userId': 'me',
                'maxResults': max_results,
            }
            if unread_only:
                params['q'] = 'is:unread'

            result = self.service.users().messages().list(**params).execute()

            messages = result.get('messages', [])
            logger.info(f"Found {len(messages)} unread emails")
            return messages

        except Exception as e:
            logger.error(f"Error getting emails: {e}")
            return []

    def get_email_content(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get full content of an email"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

            # Extract body
            body = self._extract_email_body(message['payload'])

            return {
                'id': message_id,
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body[:2000]  # Limit to 2000 chars
            }

        except Exception as e:
            logger.error(f"Error getting email content: {e}")
            return None

    def _extract_email_body(self, payload) -> str:
        """Recursively extract email body from payload"""
        body = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html':
                    # Save HTML version as fallback
                    data = part['body'].get('data', '')
                    if data and not body:
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        # Simple HTML to text conversion
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
        elif 'body' in payload:
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return body

    def mark_as_read(self, message_id: str) -> bool:
        """Mark email as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False

    def fetch_email_details(self, max_results: int = 3, mark_as_read: bool = False, unread_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve detailed information for emails."""
        details: List[Dict[str, Any]] = []

        messages = self.get_recent_emails(max_results=max_results, unread_only=unread_only)
        for message in messages:
            message_id = message.get('id')
            if not message_id:
                continue

            content = self.get_email_content(message_id)
            if content:
                details.append(content)
                if mark_as_read and unread_only:
                    self.mark_as_read(message_id)

        return details

    def load_processed_emails(self) -> set:
        """Load set of already processed email IDs"""
        try:
            if os.path.exists(PROCESSED_EMAILS_FILE):
                with open(PROCESSED_EMAILS_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_ids', []))
        except Exception as e:
            logger.error(f"Error loading processed emails: {e}")
        return set()

    def save_processed_emails(self):
        """Save set of processed email IDs"""
        try:
            with open(PROCESSED_EMAILS_FILE, 'w') as f:
                json.dump({
                    'processed_ids': list(self.processed_emails),
                    'last_update': datetime.now().isoformat()
                }, f)
        except Exception as e:
            logger.error(f"Error saving processed emails: {e}")

    def get_unread_count(self) -> int:
        """Get count of unread emails"""
        try:
            result = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=1
            ).execute()
            return result.get('resultSizeEstimate', 0)
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
