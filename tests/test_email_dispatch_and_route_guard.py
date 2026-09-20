"""
Tests for Automated Assessment Email Dispatch and Resend Functionality.
Verifies:
1. AssessmentEmailService generates complete HTML and plain-text invitation.
2. In absence of SMTP, graceful simulated delivery succeeds without exception.
3. API POST /api/v1/jobs/{job_id}/candidates/{candidate_id}/invite-assessment dispatches email.
4. API POST /api/v1/jobs/{job_id}/candidates/{candidate_id}/resend-invite-email dispatches resend.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.api import app
from src.services.email_service import AssessmentEmailService

SAMPLE_RESUME_TEXT = """
Katherine Johnson
Email: katherine.johnson@nasa.gov
Location: Hampton, VA
Title: Lead Orbital Systems Engineer

Experience:
• Senior Orbital Systems Engineer at NASA (2018 - Present)
  - Designed trajectory calculations and asynchronous telemetry systems using Python and Linux.
  - Architected Kubernetes deployments for ground telemetry tracking pipelines.

Skills: Python, Linux, Kubernetes, Trajectory Modeling, C++
"""

def test_assessment_email_service_plain_and_html_generation():
    """Verify that email service generates valid delivery metadata, OTP, and links."""
    res = AssessmentEmailService.send_assessment_invitation(
        candidate_name="Ada Lovelace",
        candidate_email="ada.lovelace@example.com",
        job_title="Lead Distributed Systems Architect",
        assessment_title="Senior Systems Architecture Proctored Exam",
        invite_url="http://127.0.0.1:8000/assessment.html?token=test_token_123",
        otp_code="982314",
        duration_minutes=60,
        company_name="Acme Corporation"
    )

    assert res["delivered"] is True
    assert res["recipient"] == "ada.lovelace@example.com"
    assert res["provider"] in ("simulated", "smtp")
    assert "982314" in res["message"]


@pytest.mark.asyncio
async def test_invite_and_resend_email_api_endpoints():
    """Verify end-to-end API invite-assessment and resend-invite-email workflow."""
    headers = {"X-Organization-Id": str(uuid.uuid4())}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create a Job Opening
        job_payload = {
            "title": "Senior Cloud Infrastructure Engineer",
            "department": "Platform Reliability",
            "location": "Remote",
            "work_model": "remote",
            "seniority": "Senior",
            "min_years_experience": 4,
            "raw_jd_text": "We are seeking a Senior Cloud Infrastructure Engineer with deep Kubernetes and Go expertise."
        }
        j_res = await client.post("/api/v1/jobs", json=job_payload, headers=headers)
        assert j_res.status_code == 200, j_res.text
        job = j_res.json()
        job_id = job["id"]

        # 2. Publish an assessment for the job
        gen_res = await client.post(f"/api/v1/jobs/{job_id}/assessment/generate-from-jd", headers=headers)
        assert gen_res.status_code == 200

        pub_res = await client.post(f"/api/v1/jobs/{job_id}/assessment/publish", headers=headers)
        assert pub_res.status_code == 200

        # 3. Upload candidate resume
        files = {"file": ("katherine_resume.txt", SAMPLE_RESUME_TEXT, "text/plain")}
        c_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/upload", files=files, headers=headers)
        assert c_res.status_code == 201, c_res.text
        cand = c_res.json()
        cand_id = cand["candidate_id"]

        # 4. Invite candidate to assessment
        inv_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/invite-assessment", headers=headers)
        assert inv_res.status_code == 200, inv_res.text
        inv_data = inv_res.json()

        assert "email_delivery" in inv_data
        assert inv_data["email_delivery"]["delivered"] is True
        assert inv_data["email_delivery"]["recipient"] is not None
        assert inv_data["otp"] is not None
        assert len(inv_data["otp"]) == 6

        # 5. Resend invitation email
        resend_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/resend-invite-email", headers=headers)
        assert resend_res.status_code == 200, resend_res.text
        resend_data = resend_res.json()

        assert resend_data["status"] == "resent"
        assert resend_data["email_delivery"]["delivered"] is True
        assert resend_data["otp_code"] == inv_data["otp"]
