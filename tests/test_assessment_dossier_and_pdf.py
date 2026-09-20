import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.api import app
from src.db.session import async_session_factory
from src.db.models import Organization, User, Membership, JobOpening, Candidate, CandidateAssessment
from src.security import hash_password, create_access_token


@pytest.mark.asyncio
async def test_assessment_audit_json_and_pdf():
    # 1. Setup Tenant and Recruiter
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    assessment_id = uuid.uuid4()

    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Dossier Test Enterprise Corp",
            slug=f"dossier-{org_id.hex[:6]}",
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
            role="recruiter"
        )
        db.add(membership)

        job = JobOpening(
            id=job_id,
            organization_id=org_id,
            title="Senior Distributed Systems Architect",
            raw_jd_text="Build low latency microservices in Go and Python",
            status="active"
        )
        db.add(job)

        candidate = Candidate(
            id=candidate_id,
            organization_id=org_id,
            job_id=job_id,
            name="Dr. Elena Rostova",
            email="elena.rostova@example.com"
        )
        db.add(candidate)

        assessment = CandidateAssessment(
            id=assessment_id,
            organization_id=org_id,
            candidate_id=candidate_id,
            job_id=job_id,
            duration_minutes=30,
            status="completed",
            score=95,
            integrity_score=88,
            strengths=["Optimal O(1) LRU eviction policy", "Clean lock concurrency patterns"],
            weaknesses=["Could include more explicit unit test docstrings"],
            feedback="Exceptional algorithmic complexity awareness and production-ready Python structures.",
            questions_json=[
                {
                    "id": "q1",
                    "title": "LRU Cache Implementation",
                    "type": "code",
                    "description": "Implement an O(1) LRU Cache with capacity constraints.",
                    "starter_code": "class LRUCache:\n    pass",
                    "test_cases": [
                        {"input": "get(1)", "expected": "-1"},
                        {"input": "put(1, 10); get(1)", "expected": "10"}
                    ]
                }
            ],
            answers_json={
                "q1": "class LRUCache:\n    def __init__(self, cap):\n        self.cap = cap\n        self.cache = {}\n    def get(self, k):\n        return self.cache.get(k, -1)"
            },
            sandbox_results={
                "q1": {
                    "stdout": "All tests passed in 12ms",
                    "tests_passed": 2,
                    "tests_total": 2,
                    "success": True,
                    "duration_ms": 12
                }
            },
            proctoring_logs=[
                {"event_type": "assessment_started", "timestamp": "2026-09-20T10:00:00Z", "details": {"ip": "192.168.1.1"}},
                {"event_type": "tab_blur", "timestamp": "2026-09-20T10:15:32Z", "details": {"duration_s": 4}, "strike_added": True},
                {"event_type": "fullscreen_restored", "timestamp": "2026-09-20T10:15:36Z", "details": {}},
                {"event_type": "final_submission", "timestamp": "2026-09-20T10:45:00Z", "details": {"strikes": 1}}
            ]
        )
        db.add(assessment)
        await db.commit()

    token = create_access_token(data={"sub": str(user_id), "email": user.email})
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(org_id)
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Audit JSON dossier endpoint
        resp = await client.get(f"/api/v1/assessments/{assessment_id}/proctor/audit", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["assessment_id"] == str(assessment_id)
        assert data["candidate_name"] == "Dr. Elena Rostova"
        assert data["candidate_email"] == "elena.rostova@example.com"
        assert data["job_title"] == "Senior Distributed Systems Architect"
        assert len(data["questions"]) == 1
        assert data["answers"]["q1"].startswith("class LRUCache")
        assert data["sandbox_results"]["q1"]["tests_passed"] == 2
        assert len(data["proctoring_events"]) == 4
        assert data["integrity_score"] == 88
        assert data["score"] == 95
        assert "Optimal O(1) LRU eviction policy" in data["strengths"]

        # 2. Test PDF export endpoint
        pdf_resp = await client.get(f"/api/v1/assessments/{assessment_id}/proctor/audit/pdf", headers=auth_headers)
        assert pdf_resp.status_code == 200, pdf_resp.text
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert "Assessment_Audit_" in pdf_resp.headers.get("content-disposition", "")
        assert f"{str(assessment_id)[:8]}.pdf" in pdf_resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_assessment_audit_tenant_isolation():
    # Setup two distinct tenants
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()
    user1_id = uuid.uuid4()
    assessment2_id = uuid.uuid4()

    async with async_session_factory() as db:
        # Tenant 1
        org1 = Organization(id=org1_id, name="Tenant One", slug=f"t1-{org1_id.hex[:6]}")
        user1 = User(id=user1_id, email=f"user1-{user1_id.hex[:6]}@example.com", hashed_password=hash_password("Pass1!"), full_name="User One")
        mem1 = Membership(user_id=user1_id, organization_id=org1_id, role="recruiter")
        db.add_all([org1, user1, mem1])

        # Tenant 2
        org2 = Organization(id=org2_id, name="Tenant Two", slug=f"t2-{org2_id.hex[:6]}")
        cand2 = Candidate(organization_id=org2_id, name="Candidate Two", email="cand2@example.com")
        db.add_all([org2, cand2])
        await db.flush()

        assessment2 = CandidateAssessment(
            id=assessment2_id,
            organization_id=org2_id,
            candidate_id=cand2.id,
            duration_minutes=30,
            status="completed",
            score=70,
            integrity_score=95,
            questions_json=[],
            answers_json={},
            sandbox_results={},
            proctoring_logs=[]
        )
        db.add(assessment2)
        await db.commit()

    # User 1 tries to access Tenant 2's assessment audit
    token = create_access_token(data={"sub": str(user1_id), "email": user1.email})
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(org1_id)
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try JSON dossier
        resp = await client.get(f"/api/v1/assessments/{assessment2_id}/proctor/audit", headers=auth_headers)
        assert resp.status_code == 404

        # Try PDF
        pdf_resp = await client.get(f"/api/v1/assessments/{assessment2_id}/proctor/audit/pdf", headers=auth_headers)
        assert pdf_resp.status_code == 404
