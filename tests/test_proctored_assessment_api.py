import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from src.api import app
from src.db.session import async_session_factory
from src.db.models import Organization, User, Membership, Candidate, CandidateAssessment
from src.security import hash_password, create_access_token

@pytest.mark.asyncio
async def test_proctored_assessment_complete_lifecycle():
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Apex Security Labs",
            slug=f"apex-{org_id.hex[:6]}",
            plan_tier="enterprise",
            is_active=True
        )
        db.add(org)

        user = User(
            id=user_id,
            email=f"recruiter-{user_id.hex[:6]}@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Lead Technical Recruiter",
            is_active=True
        )
        db.add(user)

        membership = Membership(
            user_id=user.id,
            organization_id=org.id,
            role="admin"
        )
        db.add(membership)

        candidate = Candidate(
            id=candidate_id,
            organization_id=org.id,
            name="Priya Patel",
            email=f"priya-{candidate_id.hex[:6]}@example.com",
            tags=["Python", "PostgreSQL", "Docker"]
        )
        db.add(candidate)
        await db.commit()

    token = create_access_token(data={"sub": str(user_id), "org": str(org_id), "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Recruiter generates Proctored Assessment
        gen_res = await ac.post("/api/v1/assessments/generate", headers=headers, json={
            "candidate_id": str(candidate_id),
            "duration_minutes": 30
        })
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assessment_id = gen_data["id"]
        otp_code = gen_data["otp_code"]
        access_token = gen_data["access_token"]
        assert len(otp_code) == 6
        assert gen_data["strike_count"] == 0
        assert gen_data["integrity_score"] == 100
        assert "/assessment.html" in gen_data["invite_url"]

        # 2. Candidate verifies OTP in portal
        verify_res = await ac.post(f"/api/v1/assessments/{assessment_id}/verify-otp", json={
            "otp_or_token": otp_code
        })
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["verified"] is True
        assert verify_data["candidate_name"] == "Priya Patel"

        # 3. Candidate loads Workspace view (verifying both MCQs and Coding problems in same test)
        view_res = await ac.get(f"/api/v1/assessments/{assessment_id}/candidate-view?token={access_token}")
        assert view_res.status_code == 200
        view_data = view_res.json()
        assert len(view_data["questions"]) > 0

        mcq_q = next((q for q in view_data["questions"] if q.get("type") == "mcq"), None)
        assert mcq_q is not None
        assert "options" in mcq_q
        assert len(mcq_q["options"]) >= 2
        # Verify secret answer is not leaked in candidate view
        assert "correct_option" not in mcq_q
        assert "explanation" not in mcq_q

        coding_q = next((q for q in view_data["questions"] if q.get("type") == "coding"), None)
        assert coding_q is not None
        assert "starter_code" in coding_q
        assert "test_cases" in coding_q

        # 4. Candidate executes Sandbox code on the coding problem
        algo_code = """
def solution(requests, limit, window_size):
    allowed = 0
    window = []
    for t in requests:
        while window and window[0] <= t - window_size:
            window.pop(0)
        if len(window) < limit:
            window.append(t)
            allowed += 1
    return allowed
"""
        sb_res = await ac.post(f"/api/v1/assessments/{assessment_id}/sandbox/run", json={
            "question_id": coding_q["id"],
            "language": "python",
            "code": algo_code,
            "token": access_token
        })
        assert sb_res.status_code == 200
        sb_data = sb_res.json()
        assert sb_data["success"] is True
        assert sb_data["tests_passed"] > 0

        # 5. Proctor Heartbeat
        hb_res = await ac.post(f"/api/v1/assessments/{assessment_id}/proctor/heartbeat", json={
            "audio_level_rms": 0.05,
            "token": access_token
        })
        assert hb_res.status_code == 200
        hb_data = hb_res.json()
        assert hb_data["status"] == "ok"
        assert hb_data["strike_count"] == 0

        # 6. Proctor Violation (Copy/Paste Attempt)
        viol_res = await ac.post(f"/api/v1/assessments/{assessment_id}/proctor/violation", json={
            "event_type": "copy_paste_attempt",
            "details": "Attempted unauthorized paste.",
            "token": access_token
        })
        assert viol_res.status_code == 200
        viol_data = viol_res.json()
        assert viol_data["strike_added"] is True
        assert viol_data["strike_count"] == 1
        assert viol_data["integrity_score"] == 75

        # 7. Candidate Submits Assessment (with both MCQ answer and Coding answer)
        sub_res = await ac.post(f"/api/v1/assessments/{assessment_id}/candidate-submit", json={
            "answers": {
                mcq_q["id"]: "2",  # Option index for Serializable
                coding_q["id"]: algo_code
            },
            "token": access_token
        })
        assert sub_res.status_code == 200
        sub_data = sub_res.json()
        assert sub_data["status"] == "completed"
        assert sub_data["score"] > 0
        assert sub_data["integrity_score"] == 75

        # 8. Recruiter Views Proctoring Audit Report
        audit_res = await ac.get(f"/api/v1/assessments/{assessment_id}/proctor/audit", headers=headers)
        assert audit_res.status_code == 200
        audit_data = audit_res.json()
        assert audit_data["strike_count"] == 1
        assert audit_data["integrity_score"] == 75
        assert len(audit_data["proctoring_logs"]) >= 2
        assert any(log["event_type"] == "copy_paste_attempt" for log in audit_data["proctoring_logs"])
