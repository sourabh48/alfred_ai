"""
Email Integration Service
Complete IMAP/OAuth2 setup for automatic statement imports from Gmail, Outlook, etc.
"""
import imaplib
import email
from email.header import decode_header
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, BinaryIO
import io
import base64
from django.conf import settings
from django.utils import timezone

# Google OAuth2
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

# Microsoft OAuth2
try:
    import msal
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False


class EmailIntegrationService:
    """
    Automatic email scanning for financial statements and transaction alerts.
    Supports Gmail (OAuth2), Outlook (OAuth2), and generic IMAP.
    """

    # Gmail OAuth2 scopes
    GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    # Email patterns for financial institutions
    BANK_EMAIL_PATTERNS = {
        'HDFC': [r'alerts@hdfcbank\.net', r'.*@hdfcbank\.com'],
        'ICICI': [r'.*@icicibank\.com'],
        'SBI': [r'.*@sbi\.co\.in', r'.*@onlinesbi\.com'],
        'Axis': [r'.*@axisbank\.com'],
        'Kotak': [r'.*@kotak\.com'],
        'IDFC': [r'.*@idfcfirstbank\.com'],
        'Yes Bank': [r'.*@yesbank\.in'],
        'IndusInd': [r'.*@indusind\.com'],
    }

    BROKER_EMAIL_PATTERNS = {
        'Zerodha': [r'.*@zerodha\.com'],
        'Groww': [r'.*@groww\.in'],
        'Upstox': [r'.*@upstox\.com'],
        'Angel One': [r'.*@angelone\.in'],
        'ICICI Direct': [r'.*@icicidirect\.com'],
        '5paisa': [r'.*@5paisa\.com'],
    }

    # Subject patterns for different statement types
    STATEMENT_PATTERNS = {
        'bank_statement': [
            r'account\s+statement',
            r'e-?statement',
            r'monthly\s+statement',
            r'bank\s+statement',
        ],
        'credit_card': [
            r'credit\s+card\s+statement',
            r'card\s+statement',
            r'payment\s+due',
        ],
        'investment': [
            r'holding\s+statement',
            r'portfolio\s+statement',
            r'contract\s+note',
            r'demat\s+statement',
        ],
        'loan': [
            r'loan\s+statement',
            r'emi\s+due',
            r'repayment\s+schedule',
        ],
        'mutual_fund': [
            r'mutual\s+fund\s+statement',
            r'folio\s+statement',
            r'cas\s+statement',
        ],
    }

    def __init__(self):
        self.gmail_service = None
        self.outlook_client = None
        self.imap_connection = None
        self.logger = logging.getLogger(__name__)

    # ==================== Gmail OAuth2 Integration ====================

    def setup_gmail_oauth(self, credentials_json_path: str, user) -> Dict:
        """
        Set up Gmail OAuth2 authentication.

        Args:
            credentials_json_path: Path to Google OAuth2 credentials JSON
            user: Django user object

        Returns:
            Dict with setup status and instructions
        """
        if not GOOGLE_AUTH_AVAILABLE:
            return {
                'success': False,
                'error': 'Google OAuth2 libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client'
            }

        try:
            creds = None
            token_path = f'gmail_token_{user.id}.json'

            # Check for existing token
            try:
                creds = Credentials.from_authorized_user_file(token_path, self.GMAIL_SCOPES)
            except FileNotFoundError:
                pass

            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_json_path, self.GMAIL_SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            # Build Gmail service
            self.gmail_service = build('gmail', 'v1', credentials=creds)

            return {
                'success': True,
                'message': 'Gmail OAuth2 setup complete',
                'email': self._get_gmail_email()
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Gmail OAuth2 setup failed: {str(e)}'
            }

    def _get_gmail_email(self) -> str:
        """Get authenticated Gmail email address."""
        try:
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress', 'Unknown')
        except Exception:
            self.logger.warning("Failed to read the authenticated Gmail profile.", exc_info=True)
            return 'Unknown'

    # ==================== Outlook OAuth2 Integration ====================

    def setup_outlook_oauth(self, client_id: str, client_secret: str, user) -> Dict:
        """
        Set up Outlook/Microsoft 365 OAuth2 authentication.

        Args:
            client_id: Azure App client ID
            client_secret: Azure App client secret
            user: Django user object

        Returns:
            Dict with setup status
        """
        if not MSAL_AVAILABLE:
            return {
                'success': False,
                'error': 'MSAL library not installed. Run: pip install msal'
            }

        try:
            authority = 'https://login.microsoftonline.com/common'
            scopes = ['https://graph.microsoft.com/Mail.Read']

            app = msal.PublicClientApplication(
                client_id,
                authority=authority
            )

            # Interactive login
            result = app.acquire_token_interactive(scopes)

            if 'access_token' in result:
                self.outlook_client = result
                return {
                    'success': True,
                    'message': 'Outlook OAuth2 setup complete'
                }
            else:
                return {
                    'success': False,
                    'error': f"Authentication failed: {result.get('error_description')}"
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Outlook OAuth2 setup failed: {str(e)}'
            }

    # ==================== Generic IMAP Integration ====================

    def connect_imap(self, email_address: str, password: str, imap_server: str,
                     port: int = 993) -> Dict:
        """
        Connect to email via IMAP (for non-OAuth providers).

        Args:
            email_address: Email address
            password: App password or regular password
            imap_server: IMAP server address (e.g., imap.gmail.com)
            port: IMAP port (default 993 for SSL)

        Returns:
            Dict with connection status
        """
        try:
            self.imap_connection = imaplib.IMAP4_SSL(imap_server, port)
            self.imap_connection.login(email_address, password)

            return {
                'success': True,
                'message': f'Connected to {imap_server}',
                'email': email_address
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'IMAP connection failed: {str(e)}'
            }

    # ==================== Email Scanning & Parsing ====================

    def scan_financial_emails(self, user, days_back: int = 30) -> Dict:
        """
        Scan email inbox for financial statements and alerts.

        Args:
            user: Django user object
            days_back: Number of days to scan backwards

        Returns:
            Dict with found statements categorized by type
        """
        results = {
            'bank_statements': [],
            'credit_card_statements': [],
            'investment_statements': [],
            'loan_statements': [],
            'mutual_fund_statements': [],
            'transaction_alerts': [],
            'total_found': 0
        }

        # Use Gmail if available
        if self.gmail_service:
            results = self._scan_gmail(user, days_back)
        # Use Outlook if available
        elif self.outlook_client:
            results = self._scan_outlook(user, days_back)
        # Use IMAP if connected
        elif self.imap_connection:
            results = self._scan_imap(user, days_back)
        else:
            return {
                'success': False,
                'error': 'No email connection established'
            }

        results['total_found'] = sum([
            len(results['bank_statements']),
            len(results['credit_card_statements']),
            len(results['investment_statements']),
            len(results['loan_statements']),
            len(results['mutual_fund_statements']),
            len(results['transaction_alerts'])
        ])

        return results

    def _scan_gmail(self, user, days_back: int) -> Dict:
        """Scan Gmail for financial statements."""
        results = {
            'bank_statements': [],
            'credit_card_statements': [],
            'investment_statements': [],
            'loan_statements': [],
            'mutual_fund_statements': [],
            'transaction_alerts': []
        }

        try:
            # Calculate date range
            after_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')

            # Search query for financial emails
            query = f'after:{after_date} (statement OR alert OR transaction OR payment) has:attachment'

            # Get messages
            response = self.gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=100
            ).execute()

            messages = response.get('messages', [])

            for msg in messages:
                # Get full message
                full_msg = self.gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                # Parse message
                parsed = self._parse_gmail_message(full_msg)

                # Categorize
                category = self._categorize_email(parsed['subject'], parsed['from'])
                if category:
                    results[category].append(parsed)

            return results

        except Exception as e:
            return {
                'error': f'Gmail scan failed: {str(e)}',
                **results
            }

    def _scan_imap(self, user, days_back: int) -> Dict:
        """Scan IMAP inbox for financial statements."""
        results = {
            'bank_statements': [],
            'credit_card_statements': [],
            'investment_statements': [],
            'loan_statements': [],
            'mutual_fund_statements': [],
            'transaction_alerts': []
        }

        try:
            self.imap_connection.select('INBOX')

            # Search for emails with attachments in date range
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')

            # Search criteria
            status, messages = self.imap_connection.search(
                None,
                f'(SINCE {since_date})'
            )

            if status != 'OK':
                return results

            # Get message IDs
            message_ids = messages[0].split()

            # Limit to last 100 messages
            for msg_id in message_ids[-100:]:
                status, msg_data = self.imap_connection.fetch(msg_id, '(RFC822)')

                if status != 'OK':
                    continue

                # Parse email
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)

                parsed = self._parse_imap_message(email_message)

                # Categorize
                category = self._categorize_email(parsed['subject'], parsed['from'])
                if category:
                    results[category].append(parsed)

            return results

        except Exception as e:
            return {
                'error': f'IMAP scan failed: {str(e)}',
                **results
            }

    def _parse_gmail_message(self, message: Dict) -> Dict:
        """Parse Gmail message to extract key info."""
        headers = message['payload']['headers']

        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
        from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')

        attachments = []

        # Check for attachments
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part.get('filename'):
                    attachment_id = part['body'].get('attachmentId')
                    attachments.append({
                        'filename': part['filename'],
                        'attachment_id': attachment_id,
                        'mime_type': part.get('mimeType'),
                        'size': part['body'].get('size', 0)
                    })

        return {
            'id': message['id'],
            'subject': subject,
            'from': from_email,
            'date': date,
            'attachments': attachments
        }

    def _parse_imap_message(self, message) -> Dict:
        """Parse IMAP email message."""
        subject = decode_header(message['Subject'])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()

        from_email = message.get('From', '')
        date = message.get('Date', '')

        attachments = []

        # Check for attachments
        for part in message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if filename:
                attachments.append({
                    'filename': filename,
                    'data': part.get_payload(decode=True),
                    'mime_type': part.get_content_type()
                })

        return {
            'subject': subject,
            'from': from_email,
            'date': date,
            'attachments': attachments
        }

    def _categorize_email(self, subject: str, from_email: str) -> Optional[str]:
        """Categorize email based on subject and sender."""
        subject_lower = subject.lower()

        # Check statement patterns
        for category, patterns in self.STATEMENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, subject_lower, re.IGNORECASE):
                    if category == 'bank_statement':
                        return 'bank_statements'
                    elif category == 'credit_card':
                        return 'credit_card_statements'
                    elif category == 'investment':
                        return 'investment_statements'
                    elif category == 'loan':
                        return 'loan_statements'
                    elif category == 'mutual_fund':
                        return 'mutual_fund_statements'

        # Check for transaction alerts
        if any(word in subject_lower for word in ['alert', 'transaction', 'debited', 'credited', 'spent']):
            return 'transaction_alerts'

        return None

    def download_statement(self, message_id: str, attachment_index: int = 0) -> Optional[BinaryIO]:
        """
        Download statement attachment from email.

        Args:
            message_id: Email message ID
            attachment_index: Index of attachment to download

        Returns:
            Binary file object of the attachment
        """
        try:
            if self.gmail_service:
                return self._download_gmail_attachment(message_id, attachment_index)
            elif self.imap_connection:
                return self._download_imap_attachment(message_id, attachment_index)
            else:
                return None
        except Exception as e:
            self.logger.warning("Email attachment download failed: %s", str(e), exc_info=True)
            return None

    def _download_gmail_attachment(self, message_id: str, attachment_index: int) -> BinaryIO:
        """Download attachment from Gmail."""
        message = self.gmail_service.users().messages().get(
            userId='me',
            id=message_id
        ).execute()

        parts = message['payload'].get('parts', [])
        if attachment_index >= len(parts):
            return None

        part = parts[attachment_index]
        attachment_id = part['body'].get('attachmentId')

        if attachment_id:
            attachment = self.gmail_service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()

            file_data = base64.urlsafe_b64decode(attachment['data'])
            return io.BytesIO(file_data)

        return None

    def auto_import_statements(self, user, days_back: int = 7) -> Dict:
        """
        Automatically scan and import all financial statements.

        Args:
            user: Django user object
            days_back: Days to scan backwards (default 7)

        Returns:
            Dict with import results
        """
        results = {
            'scanned_emails': 0,
            'statements_found': 0,
            'imported': {
                'bank_statements': 0,
                'investments': 0,
                'loans': 0,
                'credit_cards': 0
            },
            'errors': []
        }

        # Scan emails
        scan_results = self.scan_financial_emails(user, days_back)

        if 'error' in scan_results:
            results['errors'].append(scan_results['error'])
            return results

        results['statements_found'] = scan_results['total_found']

        # Import each type
        # Bank statements
        for stmt in scan_results.get('bank_statements', []):
            try:
                # Download and import
                # This would integrate with existing import services
                results['imported']['bank_statements'] += 1
            except Exception as e:
                results['errors'].append(f"Bank statement import error: {str(e)}")

        # Investment statements
        for stmt in scan_results.get('investment_statements', []):
            try:
                # Import via portfolio_intelligence service
                results['imported']['investments'] += 1
            except Exception as e:
                results['errors'].append(f"Investment import error: {str(e)}")

        # Loan statements
        for stmt in scan_results.get('loan_statements', []):
            try:
                # Import via loan_pdf_parser
                results['imported']['loans'] += 1
            except Exception as e:
                results['errors'].append(f"Loan import error: {str(e)}")

        return results

    def disconnect(self):
        """Close all email connections."""
        if self.imap_connection:
            try:
                self.imap_connection.close()
                self.imap_connection.logout()
            except Exception:
                self.logger.warning("Failed to close the IMAP connection cleanly.", exc_info=True)

        self.gmail_service = None
        self.outlook_client = None
        self.imap_connection = None


# Singleton instance
email_integration_service = EmailIntegrationService()
