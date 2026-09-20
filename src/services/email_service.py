"""
Email dispatch service for AuditAgent.ai.
Supports automated candidate assessment invitation delivery via SMTP,
with robust fallback for local development and test environments.
"""
import os
import html
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AssessmentEmailService:
    """Manages email dispatching for candidate assessment invitations and notifications."""

    @staticmethod
    def _is_smtp_configured() -> bool:
        host = os.environ.get("SMTP_HOST", "").strip()
        user = os.environ.get("SMTP_USER", "").strip()
        return bool(host and user)

    @classmethod
    def send_assessment_invitation(
        cls,
        candidate_name: str,
        candidate_email: str,
        job_title: str,
        assessment_title: str,
        invite_url: str,
        otp_code: str,
        duration_minutes: int = 45,
        company_name: str = "Acme Corporation"
    ) -> Dict[str, Any]:
        """
        Sends a responsive HTML & plain-text assessment invitation email.
        If SMTP credentials are not configured, logs the dispatch and returns simulated delivery.
        """
        clean_name = (candidate_name or "Candidate").strip()
        first_name = clean_name.split()[0] if clean_name else "Candidate"
        timestamp = datetime.now(timezone.utc).isoformat()
        subject = f"Action Required: Technical Assessment for {job_title} at {company_name}"

        # XSS / Template Injection Sanitization
        safe_first_name = html.escape(first_name)
        safe_job_title = html.escape(job_title or "Technical Role")
        safe_assessment_title = html.escape(assessment_title or "Technical Assessment")
        safe_company_name = html.escape(company_name or "Acme Corporation")
        safe_invite_url = html.escape(invite_url or "")
        safe_otp_code = html.escape(str(otp_code or ""))

        # Plain-text version
        plain_body = f"""Dear {first_name},

Thank you for your interest in the {job_title} position at {company_name}.

As the next step in our evaluation process, we invite you to complete our proctored technical assessment:
• Assessment: {assessment_title}
• Duration: {duration_minutes} minutes
• Format: Technical MCQs & Interactive Coding Sandbox

Please access your assessment using the unique link below:
👉 {invite_url}

Your 6-digit Access OTP code:
🔑 {otp_code}

Instructions & Environment Requirements:
1. Please ensure you have a quiet environment and a stable internet connection.
2. Complete the assessment in a desktop browser (Google Chrome or Microsoft Edge recommended).
3. The assessment is proctored (monitoring tab switches and full-screen continuity).
4. This invitation code is valid for 72 hours.

Best of luck!
The Talent Acquisition Team
{company_name}
"""

        # Branded, modern responsive HTML template
        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #1e293b;
      margin: 0;
      padding: 0;
      background-color: #f1f5f9;
    }}
    .email-container {{
      max-width: 600px;
      margin: 30px auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
      border: 1px solid #e2e8f0;
    }}
    .email-header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
      color: #ffffff;
      padding: 32px 28px;
      text-align: center;
    }}
    .email-header h1 {{
      margin: 0 0 6px 0;
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.5px;
    }}
    .email-header p {{
      margin: 0;
      font-size: 14px;
      color: #94a3b8;
    }}
    .email-body {{
      padding: 32px 28px;
    }}
    .role-badge {{
      display: inline-block;
      padding: 4px 12px;
      background: #e0e7ff;
      color: #4338ca;
      font-size: 13px;
      font-weight: 700;
      border-radius: 20px;
      margin-bottom: 16px;
    }}
    .credentials-box {{
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
      padding: 20px;
      margin: 24px 0;
      text-align: center;
    }}
    .otp-code {{
      font-family: ui-monospace, Menlo, Monaco, 'Courier New', monospace;
      font-size: 32px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: 6px;
      padding: 8px 16px;
      background: #ffffff;
      border: 2px dashed #6366f1;
      border-radius: 8px;
      display: inline-block;
      margin: 8px 0;
    }}
    .btn-action {{
      display: block;
      width: fit-content;
      margin: 28px auto 16px auto;
      padding: 14px 32px;
      background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
      color: #ffffff !important;
      text-decoration: none;
      font-size: 16px;
      font-weight: 700;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
      text-align: center;
    }}
    .checklist {{
      background: #fdf4ff;
      border-left: 4px solid #c084fc;
      padding: 14px 18px;
      border-radius: 0 8px 8px 0;
      margin-top: 24px;
      font-size: 13px;
      color: #581c87;
    }}
    .checklist ul {{
      margin: 6px 0 0 0;
      padding-left: 18px;
    }}
    .email-footer {{
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      padding: 20px 28px;
      text-align: center;
      font-size: 12px;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="email-header">
      <h1>AuditAgent.ai</h1>
      <p>Candidate Assessment Portal</p>
    </div>
    <div class="email-body">
      <span class="role-badge">{safe_job_title}</span>
      <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #0f172a;">Hello {safe_first_name},</h2>
      <p style="margin: 0 0 16px 0; font-size: 15px;">
        Thank you for applying to <strong>{safe_company_name}</strong>. We reviewed your profile and would like to invite you to take the next step in our technical interview process:
      </p>

      <div style="background: #f8fafc; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
        <div style="font-size: 14px; margin-bottom: 4px;"><strong>Assessment:</strong> {safe_assessment_title}</div>
        <div style="font-size: 14px; margin-bottom: 4px;"><strong>Estimated Time:</strong> {duration_minutes} minutes</div>
        <div style="font-size: 14px;"><strong>Format:</strong> Multiple Choice &amp; Interactive Code Sandbox</div>
      </div>

      <div class="credentials-box">
        <div style="font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Your Access OTP Code</div>
        <div class="otp-code">{safe_otp_code}</div>
        <div style="font-size: 12px; color: #64748b;">Enter this 6-digit code when prompted on the assessment landing page.</div>
      </div>

      <a href="{safe_invite_url}" class="btn-action">Start Assessment Now →</a>

      <div style="text-align: center; font-size: 12px; color: #64748b; margin-top: 8px;">
        Or copy and paste this link in your browser:<br>
        <span style="color: #6366f1; word-break: break-all;">{safe_invite_url}</span>
      </div>

      <div class="checklist">
        <strong>Before you begin:</strong>
        <ul>
          <li>Use a desktop or laptop computer with Google Chrome or Microsoft Edge.</li>
          <li>Ensure stable internet and a distraction-free environment.</li>
          <li>This session includes proctoring to ensure exam integrity.</li>
          <li>Your invitation is valid for 72 hours from dispatch.</li>
        </ul>
      </div>

      <p style="margin: 24px 0 0 0; font-size: 14px;">
        Warm regards,<br>
        <strong>The Talent Acquisition Team</strong><br>
        {safe_company_name}
      </p>
    </div>
    <div class="email-footer">
      Powered by AuditAgent.ai — Deterministic, Fair, and Verifiable Hiring Intelligence.<br>
      © {datetime.now(timezone.utc).year} {safe_company_name}. All rights reserved.
    </div>
  </div>
</body>
</html>"""

        # Check if live SMTP is configured
        if cls._is_smtp_configured():
            try:
                host = os.environ.get("SMTP_HOST")
                port = int(os.environ.get("SMTP_PORT", 587))
                user = os.environ.get("SMTP_USER")
                password = os.environ.get("SMTP_PASSWORD")
                from_email = os.environ.get("SMTP_FROM_EMAIL", user)
                use_tls = os.environ.get("SMTP_TLS", "true").lower() in ("true", "1", "yes")

                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{company_name} Recruiting <{from_email}>"
                msg["To"] = candidate_email

                msg.attach(MIMEText(plain_body, "plain"))
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(host, port, timeout=10) as server:
                    if use_tls:
                        server.starttls()
                    server.login(user, password)
                    server.sendmail(from_email, [candidate_email], msg.as_string())

                logger.info(f"✅ Assessment invitation sent via SMTP to {candidate_email}")
                return {
                    "delivered": True,
                    "provider": "smtp",
                    "recipient": candidate_email,
                    "timestamp": timestamp,
                    "message": f"Assessment email successfully dispatched to {candidate_email}"
                }
            except Exception as smtp_err:
                logger.error(f"Failed to send email via SMTP ({smtp_err}). Falling back to simulation.", exc_info=True)

        # Fallback simulation
        logger.info(f"📨 [Simulated Delivery] Assessment invite dispatched to {candidate_email} (OTP: {otp_code}, URL: {invite_url})")
        return {
            "delivered": True,
            "provider": "simulated",
            "recipient": candidate_email,
            "timestamp": timestamp,
            "message": f"Assessment invitation generated and recorded for {candidate_email} (OTP: {otp_code})"
        }
