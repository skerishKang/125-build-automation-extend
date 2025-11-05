"""
Gmail AI Reply Generator - Automatic email reply generation with Gemini
"""
import os
import logging
import pickle
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("gmail_reply_generator")

# Gmail API scopes - includes send permission for replies
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

# Token and credentials files (project root)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Project root (2 levels up from backend)
TOKEN_FILE = os.path.join(BASE_DIR, 'gmail_token.pickle')
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'gmail_credentials.json')


class GmailReplyGenerator:
    """AI-powered Gmail reply generator using Gemini"""

    def __init__(self):
        self.gmail_service = None
        self.gemini_model = None
        self.credentials = None

    def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth2"""
        # Local imports to avoid circular imports
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        creds = None

        # Load existing token
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    logger.error(f"Gmail credentials file not found: {CREDENTIALS_FILE}")
                    logger.info("To enable Gmail integration:")
                    logger.info("1. Go to https://console.cloud.google.com/")
                    logger.info("2. Create OAuth 2.0 credentials (Desktop Application)")
                    logger.info("3. Download as gmail_credentials.json")
                    logger.info("4. Place in project root directory")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                # Desktop app uses out-of-band redirect
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                creds = flow.run_local_server(port=8888)

            # Save credentials for next run
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)

        self.credentials = creds
        self.gmail_service = build('gmail', 'v1', credentials=creds)
        return True

    def get_email_content(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get full content of an email"""
        if not self.gmail_service:
            logger.error("Gmail service not authenticated")
            return None

        try:
            import base64
            import re

            message = self.gmail_service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            to = next((h['value'] for h in headers if h['name'] == 'To'), '')

            # Extract body
            body = self._extract_email_body(message['payload'])

            return {
                'id': message_id,
                'subject': subject,
                'sender': sender,
                'date': date,
                'to': to,
                'body': body[:3000]  # Limit to 3000 chars
            }

        except Exception as e:
            logger.error(f"Error getting email content: {e}")
            return None

    def _extract_email_body(self, payload) -> str:
        """Recursively extract email body from payload"""
        import base64
        import re

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
                        body = re.sub('<[^<]+?>', '', html_body)
        elif 'body' in payload:
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return body

    def generate_reply_draft(self, email_content: Dict[str, Any],
                             tone: str = "professional",
                             custom_instructions: str = "") -> str:
        """Generate AI reply draft using Gemini"""

        if not self.gemini_model:
            logger.error("Gemini model not initialized")
            return "Gemini model not available. Please check GEMINI_API_KEY."

        try:
            # Analyze tone
            tone_instructions = {
                "professional": "격식있고 정중한 비즈니스 톤으로",
                "friendly": "친근하고 캐주얼한 톤으로",
                "concise": "간결하고 요점을 명확하게",
                "detailed": "구체적이고 상세하게",
                "formal": "매우 정식적이고 공식적인 톤으로",
                "casual": "편하고 자연스러운 톤으로"
            }

            tone_guide = tone_instructions.get(tone, tone_instructions["professional"])

            # Create prompt
            prompt = f"""
다음 이메일의 답장을 작성해주세요:

보낸 사람: {email_content['sender']}
제목: {email_content['subject']}
내용: {email_content['body']}

답장 요구사항:
- {tone_guide} 답장 작성
- 원본 이메일의 모든 질문에 답변
- 필요한 경우 적절한 추가 정보 제공
- 한국어로 작성
- 3-5문장 내외의 적절한 길이

{f"특별 지시사항: {custom_instructions}" if custom_instructions else ""}

답장만 작성해주세요 (SALUTATION이나 추가 설명 없이 순수 답장 내용만).
            """

            response = self.gemini_model.generate_content(prompt)
            reply = response.text.strip()

            # Clean up reply
            reply = reply.replace('```', '').strip()

            return reply

        except Exception as e:
            logger.error(f"Error generating reply: {e}")
            return f"답장 생성 중 오류가 발생했습니다: {str(e)}"

    def send_reply(self, original_message_id: str, reply_body: str) -> bool:
        """Send reply email"""
        if not self.gmail_service:
            logger.error("Gmail service not authenticated")
            return False

        try:
            import base64
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # Get original email to extract threading headers
            original = self.gmail_service.users().messages().get(
                userId='me',
                id=original_message_id,
                format='metadata',
                metadataHeaders=['Subject', 'From', 'To', 'Message-ID', 'In-Reply-To', 'References']
            ).execute()

            headers = original['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
            in_reply_to = next((h['value'] for h in headers if h['name'] == 'In-Reply-To'), '')
            references = next((h['value'] for h in headers if h['name'] == 'References'), '')

            # Create reply
            reply_subject = f"Re: {subject}" if not subject.startswith('Re:') else subject

            # Create message
            message = MIMEText(reply_body, 'plain', 'utf-8')
            message['Subject'] = reply_subject
            message['From'] = 'me'
            message['To'] = next((h['value'] for h in headers if h['name'] == 'From'), '')

            # Threading headers
            if message_id:
                message['In-Reply-To'] = message_id
                message['References'] = message_id

            # Encode and send
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(f"Reply sent successfully for message {original_message_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            return False

    def set_gemini_model(self, model):
        """Set Gemini model for AI generation"""
        self.gemini_model = model

    def get_thread_messages(self, thread_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get messages in a thread for context"""
        if not self.gmail_service:
            logger.error("Gmail service not authenticated")
            return []

        try:
            thread = self.gmail_service.users().threads().get(
                userId='me',
                id=thread_id,
                maxResults=max_results
            ).execute()

            messages = []
            for msg in thread['messages']:
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                body = self._extract_email_body(msg['payload'])

                messages.append({
                    'id': msg['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body[:1000]
                })

            return messages

        except Exception as e:
            logger.error(f"Error getting thread messages: {e}")
            return []


def test_authentication():
    """Test Gmail authentication"""
    print("=== Gmail OAuth2 Authentication Test ===")

    generator = GmailReplyGenerator()

    try:
        result = generator.authenticate()
        if result:
            print("SUCCESS: Gmail authentication passed")
            print("You can now use Gmail reply generation")
            return True
        else:
            print("FAILED: Gmail authentication failed")
            print("Please check:")
            print("1. gmail_credentials.json exists in project root")
            print("2. OAuth2 client is configured as 'Desktop application'")
            return False
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_authentication()
