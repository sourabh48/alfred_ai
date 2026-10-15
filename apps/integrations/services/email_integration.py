"""
Email Integration Service
IMAP scanning for the supported portfolio import workflow. Interactive OAuth is not supported.
"""
import imaplib
import email
from email.header import decode_header
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, BinaryIO

from alfred_ai.services.api_errors import safe_error_details

class EmailIntegrationService:
    """
    Automatic email scanning for financial statements and transaction alerts.
    Supports generic IMAP with attachments returned by each scan.
    """

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
        self.imap_connection = None
        self.logger = logging.getLogger(__name__)


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
            self.disconnect()
            return {
                'success': False,
                **safe_error_details(e, 'Email connection failed. Check the configured account and retry.',
                                     logger_name=__name__, field='error'),
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

        if self.imap_connection:
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
                **safe_error_details(e, 'Email scan failed. Please retry.', logger_name=__name__, field='error'),
                **results
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
        """IMAP scans include attachment bytes; standalone refetch is unsupported."""
        return None


    def disconnect(self):
        """Close all email connections."""
        connection = self.imap_connection
        self.imap_connection = None
        if connection:
            for action in ('close', 'logout'):
                try:
                    getattr(connection, action)()
                except Exception as e:
                    safe_error_details(e, 'Email connection cleanup failed.', logger_name=__name__)


# Singleton instance
email_integration_service = EmailIntegrationService()
