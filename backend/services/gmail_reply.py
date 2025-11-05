"""
Gmail Reply Service - AI-Powered Email Reply Generator
"""
import base64
import re
import os
import logging
import json
import pickle
import tempfile
import email.mime.text
import email.mime.multipart
from typing import Optional, Dict, Any
from datetime import datetime

# Gmail API imports
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
except ImportError:
    pass

# Gemini AI
try:
    import google.generativeai as genai
except ImportError:
    pass

logger = logging.getLogger("gmail_reply")

# Gmail API scopes including send permission
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

# OAuth2 files
# 프로젝트 루트의 telegram-google.json 사용
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # 프로젝트 루트 (backend의 2단계 위)
TOKEN_FILE = os.path.join(BASE_DIR, 'token.pickle')  # 프로젝트 루트에 토큰 저장
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'telegram-google.json')  # 프로젝트 루트의 credentials 사용


class GmailReplyGenerator:
    def __init__(self):
        self.gmail_service = None
        self.gemini_model = None
        self.credentials = None

    def authenticate(self):
        """Authenticate with Gmail API using OAuth2"""
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
                    logger.info("2. Create OAuth 2.0 credentials with gmail.send scope")
                    logger.info("3. Download as gmail_credentials.json")
                    logger.info("4. Place in backend/services directory")
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                # 명시적으로 redirect URI 설정 (Desktop app용)
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)

        self.credentials = creds
        self.gmail_service = build('gmail', 'v1', credentials=creds)

        # Setup Gemini model if available
        try:
            import google.generativeai as genai
            if hasattr(genai, 'GenerativeModel'):
                # Get API key from environment or use a default for testing
                gemini_api_key = os.getenv('GEMINI_API_KEY')
                if gemini_api_key:
                    genai.configure(api_key=gemini_api_key)
                    self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        except Exception as e:
            logger.warning(f"Gemini setup failed: {e}")

        return True

    def get_email_content(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get email content by message ID"""
        if not self.gmail_service:
            logger.error("Gmail service not authenticated")
            return None

        try:
            message = self.gmail_service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = message['payload'].get('headers', [])
            sender = self._extract_header(headers, 'From')
            subject = self._extract_header(headers, 'Subject')
            date = self._extract_header(headers, 'Date')
            to = self._extract_header(headers, 'To')

            # Extract body
            body = self._extract_email_body(message['payload'])

            return {
                'id': message_id,
                'sender': sender,
                'subject': subject,
                'date': date,
                'to': to,
                'body': body,
                'thread_id': message['threadId']
            }

        except Exception as e:
            logger.error(f"Error getting email content: {e}")
            return None

    def _extract_header(self, headers: list, name: str) -> str:
        """Extract specific header value"""
        return next((h['value'] for h in headers if h['name'] == name), 'Unknown')

    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract text body from email payload"""
        body = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html':
                    # Save HTML as fallback
                    data = part['body'].get('data', '')
                    if data and not body:
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        # Simple HTML to text conversion
                        body = re.sub('<[^<]+?>', '', html_body)
        elif 'body' in payload:
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return body.strip()

    def generate_reply_draft(self, email_content: Dict[str, Any], tone: str = "professional") -> Optional[Dict[str, Any]]:
        """Generate AI-powered reply draft"""

        if not self.gemini_model:
            logger.warning("Gemini model not available, using template reply")
            return self._generate_template_reply(email_content, tone)

        try:
            tone_prompts = {
                "professional": "정중하고 업무적인 톤으로",
                "friendly": "친근하고 따뜻한 톤으로",
                "concise": "간결하고 핵심만 담아서",
                "detailed": "자세하고 구체적으로",
                "formal": "격식있고 정중하게",
                "casual": "편안하고 자연스럽게"
            }

            # Truncate body to avoid token limits
            body_preview = email_content['body'][:800] if email_content['body'] else ""

            reply_prompt = f"""
다음 이메일收到了 대한 답장을 작성해주세요:

=== 수신한 이메일 ===
보낸사람: {email_content['sender']}
제목: {email_content['subject']}
내용: {body_preview}

=== 답장 작성 가이드라인 ===
1. 한국어로 작성
2. {tone_prompts.get(tone, tone)} 톤으로 작성
3. 상대방의 요청이나 질문에 구체적으로 답변
4. 필요시 다음 단계나 추가 정보 제안
5. 적절한 인사말과 마무리 포함
6. 300자 이내로 간결하게

답장만 작성해 주세요 (앞뒤 말이나 설명 없이 답장 내용만):
            """

            response = self.gemini_model.generate_content(reply_prompt)
            draft = response.text.strip()

            return {
                'draft': draft,
                'tone': tone,
                'original_subject': email_content['subject'],
                'original_sender': email_content['sender'],
                'thread_id': email_content['thread_id']
            }

        except Exception as e:
            logger.error(f"Reply generation error: {e}")
            return self._generate_template_reply(email_content, tone)

    def _generate_template_reply(self, email_content: Dict[str, Any], tone: str) -> Dict[str, Any]:
        """Generate template-based reply when Gemini is not available"""
        templates = {
            "professional": f"안녕하세요,\n\n이메일 주셔서 감사합니다.\n\n문의하신 사항에 대해 검토 후 회신드리겠습니다.\n\n감사합니다.",
            "friendly": f"안녕하세요!\n\n메일 확인했습니다. 😊\n\n담당자와 상의해서 빠르게 답해드리겠습니다!\n\n감사합니다!",
            "concise": f"안녕하세요.\n\n메일 확인했습니다. 조만간 회신드리겠습니다.\n\n감사합니다.",
            "formal": f"안녕하십니까?\n\n이메일 송부 감사드립니다.\n\n문의하신 건에 대해 검토하여 곧 답변드리겠습니다.\n\n감사합니다."
        }

        return {
            'draft': templates.get(tone, templates["professional"]),
            'tone': tone,
            'original_subject': email_content['subject'],
            'original_sender': email_content['sender'],
            'thread_id': email_content['thread_id']
        }

    def send_reply_email(self, reply_data: Dict[str, Any]) -> Optional[str]:
        """Send reply email"""
        if not self.gmail_service:
            logger.error("Gmail service not authenticated")
            return None

        try:
            # Extract recipient email from sender
            sender = reply_data['original_sender']
            # Extract email address from "Name <email@domain.com>" format
            email_match = re.search(r'<(.+?)>', sender)
            if email_match:
                recipient = email_match.group(1)
            else:
                # Try to extract just the email
                email_match = re.search(r'([\w.-]+@[\w.-]+)', sender)
                recipient = email_match.group(1) if email_match else sender

            # Create reply subject (add Re: if not already there)
            subject = reply_data['original_subject']
            if not subject.startswith('Re:'):
                subject = f"Re: {subject}"

            # Create message
            message = self._create_reply_message(
                reply_data['draft'],
                recipient,
                subject,
                reply_data.get('thread_id', '')
            )

            # Send via Gmail API
            result = self.gmail_service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            logger.info(f"Reply sent successfully: {result['id']}")
            return result['id']

        except Exception as e:
            logger.error(f"Email send error: {e}")
            return None

    def _create_reply_message(self, content: str, recipient: str, subject: str, thread_id: str = '') -> Dict[str, Any]:
        """Create MIME message for reply"""
        import email.mime.text
        import email.mime.multipart

        msg = email.mime.multipart.MIMEMultipart()
        msg['to'] = recipient
        msg['subject'] = subject
        msg['from'] = 'me'

        # Add thread ID if available
        if thread_id:
            msg['In-Reply-To'] = thread_id
            msg['References'] = thread_id

        body = email.mime.text.MIMEText(content, 'plain', 'utf-8')
        msg.attach(body)

        # Encode to base64
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        return {'raw': raw_message}

    def find_recent_emails(self, max_results: int = 10) -> list:
        """Find recent emails for quick reply"""
        if not self.gmail_service:
            logger.error("Gmail service not authenticated")
            return []

        try:
            result = self.gmail_service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q='is:unread'
            ).execute()

            messages = result.get('messages', [])
            logger.info(f"Found {len(messages)} recent emails")
            return messages

        except Exception as e:
            logger.error(f"Error getting recent emails: {e}")
            return []

    def mark_as_read(self, message_id: str) -> bool:
        """Mark email as read"""
        if not self.gmail_service:
            return False

        try:
            self.gmail_service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
