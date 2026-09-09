import os
import imaplib
import email
from email import policy
from email.parser import BytesParser
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .email_parser import parse_eml_file, InboundApplication

class EmailConfig(BaseModel):
    provider: str = "gmail"  # gmail, outlook, custom
    imap_server: str = "imap.gmail.com"
    imap_port: int = 993
    username: str = ""
    password: str = ""
    folder: str = "INBOX"
    forwarding_alias: str = "screen-techcorp@auditagent.ai"
    auto_draft_replies: bool = True
    company_name: str = "TechCorp Solutions"
    calendly_link: str = "https://calendly.com/techcorp-hiring/30min"

class CandidateEmailDraft(BaseModel):
    recipient_name: str
    recipient_email: str
    subject: str
    body_text: str
    verdict: str  # SHORTLIST | REJECT | REVIEW

class DraftResponseGenerator:
    """Generates professional, personalized recruiter email drafts based on AI scorecards."""

    @staticmethod
    def create_draft(
        candidate_name: str,
        recipient_email: str,
        verdict: str,
        company_name: str = "TechCorp Solutions",
        role_title: str = "Software Engineer",
        calendly_link: str = "https://calendly.com/techcorp-hiring/30min",
        score: int = 85
    ) -> CandidateEmailDraft:
        first_name = candidate_name.split()[0] if candidate_name else "Candidate"

        if verdict == "SHORTLIST":
            subject = f"Interview Invitation: {role_title} at {company_name}"
            body = (
                f"Hi {first_name},\n\n"
                f"Thank you for applying for the {role_title} position at {company_name}.\n\n"
                f"Our engineering team reviewed your background and verified your technical projects. "
                f"We were very impressed by your work and would love to invite you for a 30-minute introductory conversation.\n\n"
                f"Please choose a time that works best for you using our scheduling link below:\n"
                f"👉 {calendly_link}\n\n"
                f"Looking forward to speaking with you!\n\n"
                f"Best regards,\n"
                f"The Talent Acquisition Team\n"
                f"{company_name}"
            )
        elif verdict == "REJECT":
            subject = f"Update regarding your application at {company_name}"
            body = (
                f"Dear {first_name},\n\n"
                f"Thank you for your interest in the {role_title} role at {company_name} and for taking the time to share your background with us.\n\n"
                f"While we were impressed by your passion, we have decided to move forward with other candidates whose current technical experience more closely matches the specific needs for this opening.\n\n"
                f"We truly appreciate your time and wish you the very best in your job search and ongoing career.\n\n"
                f"Warm regards,\n"
                f"The Talent Team\n"
                f"{company_name}"
            )
        else:
            subject = f"Application Status: {role_title} at {company_name}"
            body = (
                f"Hi {first_name},\n\n"
                f"Thank you for applying to {company_name}. Our engineering leadership is currently reviewing candidate portfolios for the {role_title} role.\n\n"
                f"We will be in touch with next steps shortly.\n\n"
                f"Best,\n"
                f"{company_name} Recruiting"
            )

        return CandidateEmailDraft(
            recipient_name=candidate_name,
            recipient_email=recipient_email,
            subject=subject,
            body_text=body,
            verdict=verdict
        )

class EmailInboxSync:
    """Manages IMAP connection, mailbox search, and applicant extraction."""

    def __init__(self, config: EmailConfig):
        self.config = config

    def fetch_unread_applications(self, limit: int = 15) -> List[InboundApplication]:
        """Fetches unread emails matching recruitment keywords."""
        is_placeholder = (
            not self.config.username 
            or "placeholder" in self.config.username.lower() 
            or not self.config.password 
            or "placeholder" in self.config.password.lower()
        )

        # If placeholder credentials, load from local mock_inbox
        if is_placeholder:
            return self._fetch_mock_inbox()

        try:
            mail = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
            mail.login(self.config.username, self.config.password)
            mail.select(self.config.folder)

            # Search for unread job emails
            search_query = '(UNSEEN OR SUBJECT "Application" OR SUBJECT "Resume")'
            status, messages = mail.search(None, search_query)
            if status != "OK" or not messages[0]:
                mail.logout()
                return []

            email_ids = messages[0].split()[-limit:]
            applications = []

            for eid in email_ids:
                res, data = mail.fetch(eid, '(RFC822)')
                if res == "OK":
                    raw_email = data[0][1]
                    app = parse_eml_file(raw_email)
                    applications.append(app)

            mail.logout()
            return applications

        except Exception as e:
            # Fallback to mock inbox if connection fails
            print(f"IMAP connection warning: {e}. Falling back to demonstration inbox.")
            return self._fetch_mock_inbox()

    def _fetch_mock_inbox(self) -> List[InboundApplication]:
        """Loads demonstration .eml files from mock_inbox directory."""
        mock_dir = os.path.join(os.path.dirname(__file__), "..", "mock_inbox")
        if not os.path.exists(mock_dir):
            from create_batch_mock_data import generate_mock_eml_files
            generate_mock_eml_files(mock_dir)

        applications = []
        files = sorted(os.listdir(mock_dir))[:10]
        for f in files:
            if f.endswith(".eml"):
                p = os.path.join(mock_dir, f)
                with open(p, "rb") as fp:
                    app = parse_eml_file(fp.read())
                    applications.append(app)
        return applications
