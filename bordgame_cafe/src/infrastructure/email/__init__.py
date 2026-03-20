"""Email service for sending emails."""

from abc import ABC, abstractmethod
from typing import Optional, List
from config import settings


class EmailService(ABC):
    """Abstract email service."""
    
    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send an email."""
        pass
    
    @abstractmethod
    async def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send emails to multiple recipients."""
        pass


class SMTPEmailService(EmailService):
    """Email service using SMTP."""
    
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send an email via SMTP."""
        try:
            # TODO: Implement SMTP email sending
            # import smtplib
            # from email.mime.text import MIMEText
            # from email.mime.multipart import MIMEMultipart
            
            # msg = MIMEMultipart("alternative")
            # msg["Subject"] = subject
            # msg["From"] = self.smtp_user
            # msg["To"] = to
            
            # part1 = MIMEText(body, "plain")
            # msg.attach(part1)
            
            # if html_body:
            #     part2 = MIMEText(html_body, "html")
            #     msg.attach(part2)
            
            # with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            #     server.starttls()
            #     server.login(self.smtp_user, self.smtp_password)
            #     server.sendmail(self.smtp_user, to, msg.as_string())
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    async def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Send emails to multiple recipients."""
        for recipient in recipients:
            success = await self.send_email(recipient, subject, body, html_body)
            if not success:
                return False
        return True


class MockEmailService(EmailService):
    """Mock email service for testing."""
    
    def __init__(self):
        self.sent_emails = []
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Mock send email."""
        self.sent_emails.append({
            "to": to,
            "subject": subject,
            "body": body,
            "html_body": html_body,
        })
        return True
    
    async def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """Mock send bulk email."""
        for recipient in recipients:
            await self.send_email(recipient, subject, body, html_body)
        return True


# Factory to get email service
def get_email_service() -> EmailService:
    """Get email service instance."""
    if settings.debug:
        return MockEmailService()
    return SMTPEmailService()
