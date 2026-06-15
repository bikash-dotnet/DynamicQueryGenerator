"""
Email service for sending export files
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, List, Dict, Any
import asyncio
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Handle email sending for exports"""
    
    def __init__(self):
        self.email_queue = []
        self.is_sending = False
    
    async def send_export_email(
        self,
        to_email: str,
        file_path: str,
        query_info: Dict[str, Any]
    ) -> bool:
        """
        Send email with export file attachment
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = f"Data Export - {query_info.get('collection', 'Query Results')}"
            
            # Email body
            body = f"""
            <html>
            <body>
                <h2>Your Data Export is Ready</h2>
                <p><strong>Query:</strong> {query_info.get('original_text', 'N/A')}</p>
                <p><strong>Records:</strong> {query_info.get('total_count', 0)}</p>
                <p><strong>Collection:</strong> {query_info.get('collection', 'N/A')}</p>
                <p><strong>Generated:</strong> {query_info.get('timestamp', 'N/A')}</p>
                <p><strong>File:</strong> {file_path_obj.name}</p>
                <p>This file will expire in 24 hours.</p>
                <hr>
                <p>Thank you for using MongoDB NLP Query System!</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Attach file
            with open(file_path_obj, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={file_path_obj.name}'
                )
                msg.attach(part)
            
            # Send email
            if settings.SENDGRID_API_KEY:
                return await self._send_with_sendgrid(msg, to_email)
            else:
                return await self._send_with_smtp(msg)
                
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def _send_with_smtp(self, msg: MIMEMultipart) -> bool:
        """Send email using SMTP"""
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email sent via SMTP to {msg['To']}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return False
    
    async def _send_with_sendgrid(self, msg: MIMEMultipart, to_email: str) -> bool:
        """Send email using SendGrid API"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            
            # Convert MIME to SendGrid format
            mail = Mail(
                from_email=settings.EMAIL_FROM,
                to_emails=to_email,
                subject=msg['Subject'],
                html_content=msg.get_payload()[0].get_payload()
            )
            
            response = sg.send(mail)
            logger.info(f"Email sent via SendGrid: {response.status_code}")
            return response.status_code == 202
            
        except ImportError:
            logger.error("SendGrid library not installed")
            return False
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return False
    
    async def send_batch_emails(
        self,
        recipients: List[str],
        file_path: str,
        query_info: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Send email to multiple recipients"""
        results = {}
        
        for email in recipients:
            results[email] = await self.send_export_email(email, file_path, query_info)
            await asyncio.sleep(1)  # Rate limiting
        
        return results
    
    def validate_email(self, email: str) -> bool:
        """Basic email format validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


# Singleton instance
email_service = EmailService()