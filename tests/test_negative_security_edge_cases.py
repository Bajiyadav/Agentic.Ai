import pytest
import uuid
import html
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy import select

from src.api import app
from src.db.session import AsyncSessionLocal
from src.db.models import Organization, JobOpening, JobAssessment, Candidate, CandidateAssessment
from src.services.email_service import AssessmentEmailService
from src.services.proctoring_service import ProctoringService

@pytest.mark.asyncio
async def test_token_omission_and_tampering_rejected():
    """Verifies that candidate endpoints strictly reject requests without valid tokens."""
    org_id = uuid.uuid4()
    
    async with AsyncSessionLocal() as db_session:
        org = Organization(
            id=org_id,
            name="Security Org",
            slug=f"sec-org-{org_id.hex[:8]}"
        )
        db_session.add(org)
        await db_session.flush()

        # Create Job & Assessment
        job = JobOpening(
            organization_id=org_id,
            title="Security Engineer",
            raw_jd_text="Experience with AppSec, pentesting, and token auth."
        )
        db_session.add(job)
        await db_session.flush()

        job_ass = JobAssessment(
            organization_id=org_id,
            job_id=job.id,
            title="Security Assessment",
            status="published",
            duration_minutes=30,
            questions_json=[{"id": "q1", "type": "mcq", "prompt": "What is CSRF?", "options": ["A", "B"]}]
        )
        db_session.add(job_ass)
        await db_session.flush()

        cand = Candidate(organization_id=org_id, name="Alice Sec", email="alice@example.com")
        db_session.add(cand)
        await db_session.flush()

        token, otp, expires_at = ProctoringService.generate_invite_credentials()
        cand_ass = CandidateAssessment(
            organization_id=org_id,
            job_id=job.id,
            assessment_id=job_ass.id,
            candidate_id=cand.id,
            duration_minutes=30,
            status="invited",
            questions_json=job_ass.questions_json,
            access_token=token,
            otp_code=otp,
            otp_expires_at=expires_at
        )
        db_session.add(cand_ass)
        await db_session.commit()
        assessment_id = cand_ass.id

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. candidate-view with NO token -> 401
        res1 = await client.get(f"/api/v1/assessments/{assessment_id}/candidate-view")
        assert res1.status_code == 401
        assert "Valid access token is required" in res1.json()["detail"]

        # 2. candidate-view with INVALID token -> 401
        res2 = await client.get(f"/api/v1/assessments/{assessment_id}/candidate-view?token=forged_token_xyz")
        assert res2.status_code == 401
        assert "Invalid or expired access token" in res2.json()["detail"]

        # 3. candidate-submit with NO token -> 401
        res3 = await client.post(
            f"/api/v1/assessments/{assessment_id}/candidate-submit",
            json={"answers": {"q1": "0"}}
        )
        assert res3.status_code == 401
        assert "Valid access token is required" in res3.json()["detail"]

        # 4. candidate-submit with INVALID token -> 401
        res4 = await client.post(
            f"/api/v1/assessments/{assessment_id}/candidate-submit",
            json={"answers": {"q1": "0"}, "token": "tampered_token"}
        )
        assert res4.status_code == 401


@pytest.mark.asyncio
async def test_double_submission_score_immutability():
    """Verifies that submitting answers a second time returns 409 and protects score immutability."""
    org_id = uuid.uuid4()
    
    async with AsyncSessionLocal() as db_session:
        org = Organization(
            id=org_id,
            name="Score Org",
            slug=f"score-org-{org_id.hex[:8]}"
        )
        db_session.add(org)
        await db_session.flush()

        job = JobOpening(organization_id=org_id, title="Backend Engineer", raw_jd_text="Python Engineer")
        db_session.add(job)
        await db_session.flush()

        job_ass = JobAssessment(
            organization_id=org_id,
            job_id=job.id,
            title="Backend Exam",
            status="published",
            duration_minutes=30,
            questions_json=[{"id": "q1", "type": "mcq", "prompt": "Python GIL", "options": ["Opt1", "Opt2"], "correct_option": 0, "points": 100}]
        )
        db_session.add(job_ass)
        await db_session.flush()

        cand = Candidate(organization_id=org_id, name="Bob Dev", email="bob@example.com")
        db_session.add(cand)
        await db_session.flush()

        token, otp, expires_at = ProctoringService.generate_invite_credentials()
        cand_ass = CandidateAssessment(
            organization_id=org_id,
            job_id=job.id,
            assessment_id=job_ass.id,
            candidate_id=cand.id,
            duration_minutes=30,
            status="in_progress",
            questions_json=job_ass.questions_json,
            access_token=token,
            otp_code=otp,
            otp_expires_at=expires_at
        )
        db_session.add(cand_ass)
        await db_session.commit()
        assessment_id = cand_ass.id

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # First submission succeeds
        first_sub = await client.post(
            f"/api/v1/assessments/{assessment_id}/candidate-submit",
            json={"answers": {"q1": "0"}, "token": token}
        )
        assert first_sub.status_code == 200
        first_data = first_sub.json()
        assert first_data["status"] == "completed"
        initial_score = first_data["score"]

        # Second submission MUST be rejected with 409 Conflict
        second_sub = await client.post(
            f"/api/v1/assessments/{assessment_id}/candidate-submit",
            json={"answers": {"q1": "1"}, "token": token}
        )
        assert second_sub.status_code == 409
        assert "already been submitted" in second_sub.json()["detail"]

    # Confirm score in DB did not change
    async with AsyncSessionLocal() as db_session:
        res = await db_session.execute(select(CandidateAssessment).where(CandidateAssessment.id == assessment_id))
        refreshed = res.scalar_one()
        assert refreshed.score == initial_score
        assert refreshed.status == "completed"


@pytest.mark.asyncio
async def test_otp_brute_force_lockout():
    """Verifies that 5 consecutive failed OTP attempts triggers 429 Too Many Requests lockout."""
    org_id = uuid.uuid4()
    
    async with AsyncSessionLocal() as db_session:
        org = Organization(
            id=org_id,
            name="OTP Org",
            slug=f"otp-org-{org_id.hex[:8]}"
        )
        db_session.add(org)
        await db_session.flush()

        cand = Candidate(organization_id=org_id, name="Charlie Test", email="charlie@example.com")
        db_session.add(cand)
        await db_session.flush()

        token, otp, expires_at = ProctoringService.generate_invite_credentials()
        cand_ass = CandidateAssessment(
            organization_id=org_id,
            candidate_id=cand.id,
            duration_minutes=30,
            status="invited",
            questions_json=[],
            access_token=token,
            otp_code="987654",  # Real secret OTP
            otp_expires_at=expires_at
        )
        db_session.add(cand_ass)
        await db_session.commit()
        assessment_id = cand_ass.id

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Attempts 1 to 4 should fail with 401 and report remaining attempts
        for attempt in range(1, 5):
            res = await client.post(
                f"/api/v1/assessments/{assessment_id}/verify-otp",
                json={"otp_or_token": f"00000{attempt}"}
            )
            assert res.status_code == 401
            assert f"{5 - attempt} attempts remaining" in res.json()["detail"]

        # 5th attempt must trigger 429 Too Many Requests
        res5 = await client.post(
            f"/api/v1/assessments/{assessment_id}/verify-otp",
            json={"otp_or_token": "000005"}
        )
        assert res5.status_code == 429
        assert "Too many failed passcode attempts. Assessment access locked." in res5.json()["detail"]

        # 6th attempt (even with the REAL correct OTP!) must still be locked out
        res6 = await client.post(
            f"/api/v1/assessments/{assessment_id}/verify-otp",
            json={"otp_or_token": "987654"}
        )
        assert res6.status_code == 429
        assert "Assessment access locked" in res6.json()["detail"]


@pytest.mark.asyncio
async def test_expired_invitation_rejected():
    """Verifies that expired invitations (>72 hours in the past) are rejected."""
    org_id = uuid.uuid4()
    
    async with AsyncSessionLocal() as db_session:
        org = Organization(
            id=org_id,
            name="Expire Org",
            slug=f"expire-org-{org_id.hex[:8]}"
        )
        db_session.add(org)
        await db_session.flush()

        cand = Candidate(organization_id=org_id, name="Diana Expired", email="diana@example.com")
        db_session.add(cand)
        await db_session.flush()

        # Expired 24 hours ago
        expired_time = datetime.now(timezone.utc) - timedelta(hours=24)
        token, otp, _ = ProctoringService.generate_invite_credentials()
        cand_ass = CandidateAssessment(
            organization_id=org_id,
            candidate_id=cand.id,
            duration_minutes=30,
            status="invited",
            questions_json=[],
            access_token=token,
            otp_code=otp,
            otp_expires_at=expired_time
        )
        db_session.add(cand_ass)
        await db_session.commit()
        assessment_id = cand_ass.id

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Verify OTP on expired assessment -> 401
        res = await client.post(
            f"/api/v1/assessments/{assessment_id}/verify-otp",
            json={"otp_or_token": otp}
        )
        assert res.status_code == 401

        # Candidate view with expired token -> 401
        res_view = await client.get(f"/api/v1/assessments/{assessment_id}/candidate-view?token={token}")
        assert res_view.status_code == 401


def test_email_template_xss_sanitization():
    """Verifies that XSS attack vectors in candidate names or job titles are escaped."""
    malicious_name = "<script>alert('XSS_ATTACK')</script>"
    malicious_job = "DevSecOps & Cloud '><img src=x onerror=alert(1)>"
    malicious_company = "<iframe src='evil.com'></iframe>"

    # Send invitation
    result = AssessmentEmailService.send_assessment_invitation(
        candidate_name=malicious_name,
        candidate_email="victim@example.com",
        job_title=malicious_job,
        assessment_title="Security Screening",
        invite_url="http://localhost:8000/assessment.html?token=safe",
        otp_code="123456",
        company_name=malicious_company
    )
    assert result["delivered"] is True

    # Check html.escape behavior directly
    escaped_name = html.escape(malicious_name)
    escaped_job = html.escape(malicious_job)
    escaped_company = html.escape(malicious_company)

    assert "<script>" not in escaped_name
    assert "&lt;script&gt;" in escaped_name
    assert "<img" not in escaped_job
    assert "&lt;img" in escaped_job
    assert "<iframe" not in escaped_company
    assert "&lt;iframe" in escaped_company


@pytest.mark.asyncio
async def test_resend_email_rate_limit():
    """Verifies that rapid consecutive resend requests are rate limited."""
    headers = {"X-Organization-Id": str(uuid.uuid4())}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create a Job Opening
        job_payload = {
            "title": "Rate Limit Test Job",
            "raw_jd_text": "Software engineer with testing background."
        }
        j_res = await client.post("/api/v1/jobs", json=job_payload, headers=headers)
        assert j_res.status_code == 200
        job_id = j_res.json()["id"]

        # 2. Publish assessment
        await client.post(f"/api/v1/jobs/{job_id}/assessment/generate-from-jd", headers=headers)
        await client.post(f"/api/v1/jobs/{job_id}/assessment/publish", headers=headers)

        # 3. Upload candidate
        files = {"file": ("test_cand.txt", "Alice Engineer\nalice@rate.com\nPython, Docker", "text/plain")}
        c_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/upload", files=files, headers=headers)
        assert c_res.status_code == 201
        cand_id = c_res.json()["candidate_id"]

        # 4. Invite candidate
        inv_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/invite-assessment", headers=headers)
        assert inv_res.status_code == 200

        # 5. First resend succeeds
        res1 = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{cand_id}/resend-invite-email",
            headers=headers
        )
        assert res1.status_code == 200

        # 6. Immediate second resend triggers 429 Too Many Requests
        res2 = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{cand_id}/resend-invite-email",
            headers=headers
        )
        assert res2.status_code == 429
        assert "Please wait" in res2.json()["detail"]

