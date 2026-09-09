import re
import email
from email import policy
from email.parser import BytesParser
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class InboundApplication(BaseModel):
    candidate_name: str
    email_sender: Optional[str] = None
    subject: str
    body_text: str
    github_url: Optional[str] = None
    github_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    pdf_filename: Optional[str] = None
    pdf_bytes: Optional[bytes] = None

def extract_links_from_text(text: str) -> Dict[str, Optional[str]]:
    """Extracts GitHub and LinkedIn links from email text."""
    github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]+)", text)
    github_user = github_match.group(1) if github_match else None
    github_url = f"https://github.com/{github_user}" if github_user else None

    linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)", text)
    linkedin_url = linkedin_match.group(0) if linkedin_match else None

    return {
        "github_username": github_user,
        "github_url": github_url,
        "linkedin_url": linkedin_url
    }

def extract_name_from_subject(subject: str, fallback_email: Optional[str] = None) -> str:
    """Extracts candidate name from common job email subject lines."""
    # Pattern: Application - John Smith, Resume: Sarah Khan, Intern Application: Alex Chen
    patterns = [
        r"(?:application|resume|applying for|candidate)[\s:–-]+([A-Za-z\s]+?)(?:[-–|]|$)",
        r"^([A-Za-z\s]{3,30})\s*(?:-|–|\|)\s*(?:application|resume)",
    ]
    for pat in patterns:
        m = re.search(pat, subject, re.IGNORECASE)
        if m:
            clean = m.group(1).strip()
            if len(clean.split()) >= 2:
                return clean

    if fallback_email and "@" in fallback_email:
        local = fallback_email.split("@")[0].replace(".", " ").replace("_", " ").title()
        return local
    
    return "Candidate Application"

def parse_eml_file(file_bytes: bytes) -> InboundApplication:
    """Parses raw RFC822 .eml email file into a structured InboundApplication."""
    msg = BytesParser(policy=policy.default).parsebytes(file_bytes)

    subject = msg.get("Subject", "Application")
    sender = msg.get("From", "")

    # Extract body
    body_parts = []
    pdf_bytes = None
    pdf_filename = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get_content_disposition())

            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode(errors="ignore"))
            elif content_type == "application/pdf" or (part.get_filename() and part.get_filename().lower().endswith(".pdf")):
                pdf_bytes = part.get_payload(decode=True)
                pdf_filename = part.get_filename() or "resume.pdf"
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_parts.append(payload.decode(errors="ignore"))

    full_body = "\n".join(body_parts)
    candidate_name = extract_name_from_subject(subject, sender)
    links = extract_links_from_text(full_body)

    return InboundApplication(
        candidate_name=candidate_name,
        email_sender=sender,
        subject=subject,
        body_text=full_body,
        github_url=links["github_url"],
        github_username=links["github_username"],
        linkedin_url=links["linkedin_url"],
        pdf_filename=pdf_filename,
        pdf_bytes=pdf_bytes
    )
