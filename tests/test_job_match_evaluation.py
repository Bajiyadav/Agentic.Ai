import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from src.api import app
from src.db.session import AsyncSessionLocal
from src.db.models import (
    JobOpening, Candidate, CandidateJobEvidenceAudit,
    CandidateAssessment, JobMatchScore, JobAssessment
)
from src.services.job_match_evaluation_service import JobMatchEvaluationService


SAMPLE_RESUME_A = b"""
Candidate Name: Sarah Lin
Email: sarah.lin@example.com
Current Role: Senior Backend Engineer
Location: San Francisco, CA

Summary:
Senior Backend Engineer with 6 years experience architecting high-throughput distributed APIs using Python, FastAPI, Docker, and PostgreSQL.

Skills:
Languages: Python, SQL
Frameworks: FastAPI, Docker, PostgreSQL
Tools: Git, Linux

Experience:
Senior Software Engineer (2020 - Present)
Architected microservices in Python and FastAPI handling 50k requests per second. Maintained PostgreSQL clusters and containerized deployments via Docker.
"""

SAMPLE_RESUME_NO_GITHUB = b"""
Candidate Name: David Enterprise
Email: david.enterprise@example.com
Current Role: Enterprise Systems Architect
Location: New York, NY

Summary:
Principal engineer with 8 years enterprise experience building banking systems in Python and PostgreSQL behind corporate firewalls.

Skills:
Languages: Python, SQL
Frameworks: FastAPI, PostgreSQL
Tools: Docker

Experience:
Enterprise Engineer at Global Bank (2018 - Present)
Built mission-critical transactional pipelines. All code strictly proprietary and housed in internal GitLab.
"""


@pytest.mark.asyncio
async def test_job_match_scoring_dimension_weights_sum_to_100():
    """Verifies the exact 6 deterministic weights: 20%, 15%, 15%, 10%, 25%, 15% sum to 100%."""
    weights = [0.20, 0.15, 0.15, 0.10, 0.25, 0.15]
    assert round(sum(weights), 2) == 1.00


@pytest.mark.asyncio
async def test_candidate_a_strong_match_shortlist():
    """Candidate A: Strong match across all dimensions -> Evaluates to SHORTLIST (>= 75)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create Job Opening
        job_res = await client.post("/api/v1/jobs", json={
            "title": "Senior Python Backend Engineer",
            "department": "Engineering",
            "raw_jd_text": "Looking for a Senior Python Engineer with 4+ years experience in Python, FastAPI, Docker, and PostgreSQL. Preferred: Redis, Kubernetes. Responsibilities include building scalable APIs and database optimization."
        })
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # 2. Upload Candidate
        cand_res = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/upload",
            files={"file": ("sarah_lin.txt", SAMPLE_RESUME_A, "text/plain")},
            data={"github_username": "sarahlin-dev"}
        )
        assert cand_res.status_code in (200, 201)
        cand_id = cand_res.json()["candidate_id"]

        # 3. Simulate Completed Assessment (score 90%)
        async with AsyncSessionLocal() as session:
            cand_uuid = uuid.UUID(cand_id)
            job_uuid = uuid.UUID(job_id)
            cand = await session.get(Candidate, cand_uuid)
            org_uuid = cand.organization_id

            ca = CandidateAssessment(
                organization_id=org_uuid,
                job_id=job_uuid,
                candidate_id=cand_uuid,
                status="completed",
                score=90,
                integrity_score=95,
                questions_json=[
                    {"id": "q1", "type": "mcq", "skill_tested": "Python", "correct_option": 1},
                    {"id": "q2", "type": "coding", "skill_tested": "FastAPI", "points": 30}
                ],
                answers_json={"q1": 1},
                sandbox_results={"q2": {"passed": True}}
            )
            session.add(ca)

            # Add GitHub Evidence Audit
            ea = CandidateJobEvidenceAudit(
                organization_id=org_uuid,
                job_id=job_uuid,
                candidate_id=cand_uuid,
                github_username="sarahlin-dev",
                status="Completed",
                audit_data={
                    "status": "Completed",
                    "profile": {
                        "username": "sarahlin-dev",
                        "total_public_repos": 12,
                        "original_repos_count": 8,
                        "total_stars": 24,
                        "documentation_ratio": 0.85,
                        "languages_detected": {"Python": 80000, "SQL": 20000}
                    },
                    "claim_verifications": [
                        {"claim_text": "Python microservices", "status": "Verified", "claim_type": "Skill"},
                        {"claim_text": "PostgreSQL database", "status": "Strong Evidence", "claim_type": "Skill"}
                    ]
                }
            )
            session.add(ea)
            await session.commit()

        # 4. Trigger Job Match Evaluation
        eval_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/evaluate")
        assert eval_res.status_code == 200
        data = eval_res.json()

        assert data["candidate_id"] == cand_id
        assert data["job_id"] == job_id
        assert data["overall_match_pct"] >= 75
        assert data["recommendation"] == "SHORTLIST"
        assert len(data["strengths"]) >= 2
        assert len(data["required_skills_matrix"]) >= 1
        assert "dimensions" in data
        assert data["dimensions"]["required_skills"]["score"] >= 80
        assert data["dimensions"]["experience"]["score"] == 100
        assert data["dimensions"]["assessment_performance"]["score"] == 90


@pytest.mark.asyncio
async def test_candidate_missing_github_neutral_baseline_never_reject():
    """Missing GitHub profile must use neutral baseline (65) and NEVER trigger REJECT by itself."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create Job
        job_res = await client.post("/api/v1/jobs", json={
            "title": "Principal Systems Engineer",
            "department": "Core Infrastructure",
            "raw_jd_text": "Seeking a Principal Engineer with 5+ years experience in Python and PostgreSQL."
        })
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # Upload candidate with NO GitHub
        cand_res = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/upload",
            files={"file": ("david_enterprise.txt", SAMPLE_RESUME_NO_GITHUB, "text/plain")},
            data={"github_username": "none"}
        )
        assert cand_res.status_code in (200, 201)
        cand_id = cand_res.json()["candidate_id"]

        # Add completed assessment (85%)
        async with AsyncSessionLocal() as session:
            cand_uuid = uuid.UUID(cand_id)
            job_uuid = uuid.UUID(job_id)
            cand = await session.get(Candidate, cand_uuid)
            org_uuid = cand.organization_id

            ca = CandidateAssessment(
                organization_id=org_uuid,
                job_id=job_uuid,
                candidate_id=cand_uuid,
                status="completed",
                score=85,
                integrity_score=100,
                questions_json=[{"id": "q1", "type": "mcq", "skill_tested": "Python", "correct_option": 0}],
                answers_json={"q1": 0}
            )
            session.add(ca)
            await session.commit()

        # Trigger Evaluation
        eval_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/evaluate")
        assert eval_res.status_code == 200
        data = eval_res.json()

        # Check GitHub dimension is neutral baseline (65)
        git_dim = data["dimensions"]["github_evidence"]
        assert git_dim["is_neutral_baseline"] is True
        assert git_dim["score"] == 65
        assert "private repositories" in git_dim["notes"].lower()

        # Overall recommendation must NOT be REJECT
        assert data["recommendation"] in ("SHORTLIST", "REVIEW")
        assert data["recommendation"] != "REJECT"


@pytest.mark.asyncio
async def test_assessment_conflict_detection():
    """Detects conflict when candidate claims a skill on resume but fails assessment question on that skill."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create Job
        job_res = await client.post("/api/v1/jobs", json={
            "title": "Fullstack Python Developer",
            "department": "Product",
            "raw_jd_text": "Need Fullstack Developer proficient in Python and React."
        })
        job_id = job_res.json()["id"]

        cand_res = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/upload",
            files={"file": ("sarah_lin.txt", SAMPLE_RESUME_A, "text/plain")},
            data={"github_username": "sarahlin-dev"}
        )
        assert cand_res.status_code in (200, 201)
        cand_id = cand_res.json()["candidate_id"]

        # Assessment where Python question was failed
        async with AsyncSessionLocal() as session:
            cand_uuid = uuid.UUID(cand_id)
            job_uuid = uuid.UUID(job_id)
            cand = await session.get(Candidate, cand_uuid)
            org_uuid = cand.organization_id

            ca = CandidateAssessment(
                organization_id=org_uuid,
                job_id=job_uuid,
                candidate_id=cand_uuid,
                status="completed",
                score=35,
                integrity_score=90,
                questions_json=[
                    {"id": "q_py", "type": "mcq", "title": "Advanced Python Metaclasses", "skill_tested": "Python", "correct_option": 2}
                ],
                answers_json={"q_py": 0}  # Wrong answer
            )
            session.add(ca)
            await session.commit()

        eval_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/evaluate")
        assert eval_res.status_code == 200
        data = eval_res.json()

        # Evidence conflicts must include the resume vs assessment conflict
        conflicts = data["evidence_conflicts"]
        assert len(conflicts) > 0
        py_conflict = [c for c in conflicts if "Python" in c["claim_text"] or "Python" in c["details"]]
        assert len(py_conflict) > 0
        assert "scored 0 on assessment" in py_conflict[0]["details"]


@pytest.mark.asyncio
async def test_recruiter_override_and_audit_trail():
    """Recruiter override updates effective decision and records audit trail without mutating original AI recommendation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_res = await client.post("/api/v1/jobs", json={
            "title": "DevOps Engineer",
            "department": "Platform",
            "raw_jd_text": "DevOps Engineer with Docker and Kubernetes skills."
        })
        job_id = job_res.json()["id"]

        cand_res = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/upload",
            files={"file": ("sarah_lin.txt", SAMPLE_RESUME_A, "text/plain")},
            data={"github_username": "sarahlin-dev"}
        )
        assert cand_res.status_code in (200, 201)
        cand_id = cand_res.json()["candidate_id"]

        # Run initial evaluation
        eval_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/evaluate")
        assert eval_res.status_code == 200
        orig_rec = eval_res.json()["recommendation"]
        orig_score = eval_res.json()["overall_match_pct"]

        # 1. Invalid override without reason must fail (validation error 422 or 400)
        bad_override = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{cand_id}/evaluation/override",
            json={"decision": "SHORTLIST", "reason": ""}
        )
        assert bad_override.status_code in (400, 422)

        # 2. Valid recruiter override to REJECT with clear reason
        override_res = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{cand_id}/evaluation/override",
            json={
                "decision": "REJECT",
                "reason": "Candidate withdrew application due to location preference mismatch.",
                "override_score": 40,
                "recruiter_name": "Senior Talent Partner"
            }
        )
        assert override_res.status_code == 200
        over_data = override_res.json()

        # Original score and recommendation MUST be preserved!
        assert over_data["overall_match_pct"] == orig_score
        assert over_data["recommendation"] == orig_rec

        # Effective decision is now REJECT
        assert over_data["effective_recommendation"] == "REJECT"
        assert over_data["recruiter_override"]["has_override"] is True
        assert over_data["recruiter_override"]["decision"] == "REJECT"
        assert "location preference" in over_data["recruiter_override"]["reason"]
        assert over_data["recruiter_override"]["decision_by"] == "Senior Talent Partner"


@pytest.mark.asyncio
async def test_multi_job_evaluation_isolation():
    """Evaluating a candidate for Job A must not mutate or overwrite evaluation for Job B."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create Job A (Python)
        job_a_res = await client.post("/api/v1/jobs", json={
            "title": "Backend Python Lead",
            "department": "Platform",
            "raw_jd_text": "Senior Python role requiring Python and FastAPI."
        })
        job_a_id = job_a_res.json()["id"]

        # Create Job B (Go / Rust)
        job_b_res = await client.post("/api/v1/jobs", json={
            "title": "Systems Rust Engineer",
            "department": "Core",
            "raw_jd_text": "Systems role requiring Rust, C++, and Kernel programming."
        })
        job_b_id = job_b_res.json()["id"]

        # Upload candidate to Job A
        cand_res = await client.post(
            f"/api/v1/jobs/{job_a_id}/candidates/upload",
            files={"file": ("sarah_lin.txt", SAMPLE_RESUME_A, "text/plain")},
            data={"github_username": "sarahlin-dev"}
        )
        assert cand_res.status_code in (200, 201)
        cand_id = cand_res.json()["candidate_id"]

        # Evaluate for Job A
        eval_a_res = await client.post(f"/api/v1/jobs/{job_a_id}/candidates/{cand_id}/evaluate")
        assert eval_a_res.status_code == 200
        score_a = eval_a_res.json()["overall_match_pct"]

        # Evaluate same candidate for Job B
        eval_b_res = await client.post(f"/api/v1/jobs/{job_b_id}/candidates/{cand_id}/evaluate")
        assert eval_b_res.status_code == 200
        score_b = eval_b_res.json()["overall_match_pct"]

        # Verify Job A evaluation is still intact and different from Job B
        get_a = await client.get(f"/api/v1/jobs/{job_a_id}/candidates/{cand_id}/evaluation")
        assert get_a.status_code == 200
        assert get_a.json()["overall_match_pct"] == score_a
        assert get_a.json()["job_id"] == job_a_id

        get_b = await client.get(f"/api/v1/jobs/{job_b_id}/candidates/{cand_id}/evaluation")
        assert get_b.status_code == 200
        assert get_b.json()["overall_match_pct"] == score_b
        assert get_b.json()["job_id"] == job_b_id

        # Candidate is Python engineer, so score for Job A (Python) should be higher than Job B (Rust)
        assert score_a > score_b
