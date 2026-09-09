import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from src.api import app
from src.db.session import async_session_factory
from src.db.models import (
    Organization, User, Membership, Candidate, Audit, Application,
    JobOpening, JobMatchScore, CandidateAssessment,
    TechnicalInterview, PipelineStage
)
from src.security import hash_password, create_access_token
from src.agent_2_code_auditor import GitHubEvidence, RepoHighlight
from src.services.deep_code_auditor import DeepCodeAuditor, analyze_repository_footprint
from src.services.jd_service import JobDescriptionService
from src.services.evidence_graph_service import CandidateEvidenceGraphService
from src.services.assessment_service import AssessmentService
from src.services.interview_service import TechnicalInterviewService
from src.services.comparison_service import CandidateComparisonService
from src.services.pipeline_service import PipelineService
from src.services.analytics_service import RecruitmentAnalyticsEngine
from src.services.copilot_service import RecruiterCopilotService


def test_deep_code_auditor_star_agnostic():
    auditor = DeepCodeAuditor()
    evidence = GitHubEvidence(
        username="dev-pro",
        profile_found=True,
        total_public_repos=6,
        original_repos_count=5,
        forked_repos_count=1,
        total_stars=0,  # Vanity stars = 0, should still score high!
        languages_detected={"Python": 4, "Dockerfile": 2, "Shell": 1},
        documentation_ratio=0.8,
        recent_activity_count=4,
        repo_highlights=[
            RepoHighlight(
                name="high-throughput-gateway",
                description="FastAPI gateway with automated test suites and docker deployment",
                language="Python",
                stars=0,
                forks=0,
                is_fork=False,
                html_url="https://github.com/dev-pro/gateway"
            )
        ]
    )
    result = auditor.audit(evidence)

    assert result.username == "dev-pro"
    assert result.testing_maturity_score >= 75
    assert result.devops_cicd_score >= 75
    assert result.architecture_score >= 75
    # Overall score must reflect engineering practices, not vanity stars
    assert result.overall_engineering_score >= 75
    assert "Automated testing practices observed" in " ".join(result.verified_practices)


@pytest.mark.asyncio
async def test_platform_services_and_api_suite():
    # Setup test organization and recruiter
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    slug = f"test-platform-{org_id.hex[:6]}"

    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Apex Platform Labs",
            slug=slug,
            plan_tier="enterprise",
            monthly_resume_limit=500,
            monthly_resumes_used=2,
            is_active=True
        )
        db.add(org)

        user = User(
            id=user_id,
            email=f"head-recruiter-{user_id.hex[:6]}@example.com",
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

        # Candidate A
        candidate_a = Candidate(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="Aarav Sharma",
            email="aarav@example.com",
            github_username="aaravsharma",
            tags=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"]
        )
        db.add(candidate_a)

        app_a = Application(
            id=uuid.uuid4(),
            organization_id=org.id,
            candidate_id=candidate_a.id,
            job_title="Senior Engineer",
            source="upload",
            status="screened"
        )
        db.add(app_a)

        audit_a = Audit(
            id=uuid.uuid4(),
            organization_id=org.id,
            application_id=app_a.id,
            candidate_id=candidate_a.id,
            overall_score=86,
            consistency_score=90,
            code_quality_score=85,
            skills_match_score=88,
            ai_recommendation="SHORTLIST",
            executive_summary="Candidate has strong production repository depth."
        )
        db.add(audit_a)

        # Candidate B
        candidate_b = Candidate(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="Elena Rostova",
            email="elena@example.com",
            github_username="elenarostova",
            tags=["Python", "Distributed Systems", "Kubernetes", "PostgreSQL"]
        )
        db.add(candidate_b)

        app_b = Application(
            id=uuid.uuid4(),
            organization_id=org.id,
            candidate_id=candidate_b.id,
            job_title="Staff Engineer",
            source="upload",
            status="screened"
        )
        db.add(app_b)

        audit_b = Audit(
            id=uuid.uuid4(),
            organization_id=org.id,
            application_id=app_b.id,
            candidate_id=candidate_b.id,
            overall_score=91,
            consistency_score=94,
            code_quality_score=92,
            skills_match_score=90,
            ai_recommendation="SHORTLIST",
            executive_summary="Candidate demonstrates exceptional distributed systems architecture."
        )
        db.add(audit_b)

        await db.commit()

    token = create_access_token(data={"sub": str(user_id), "email": user.email})
    auth_headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Test POST /api/v1/jobs & GET /api/v1/jobs
        job_payload = {
            "title": "Principal Distributed Systems Engineer",
            "department": "Core Infrastructure",
            "min_years_experience": 5,
            "raw_jd_text": "Seeking a Principal Engineer with expertise in Python, Distributed Systems, PostgreSQL, Docker, and Redis."
        }
        res = await client.post("/api/v1/jobs", json=job_payload, headers=auth_headers)
        assert res.status_code == 200, res.text
        job_data = res.json()
        job_id = job_data["id"]
        assert job_data["title"] == "Principal Distributed Systems Engineer"
        assert len(job_data["required_skills"]) > 0

        res = await client.get("/api/v1/jobs", headers=auth_headers)
        assert res.status_code == 200
        jobs_list = res.json()
        assert any(j["id"] == job_id for j in jobs_list)

        # 2. Test GET /api/v1/candidates
        res = await client.get("/api/v1/candidates", headers=auth_headers)
        assert res.status_code == 200
        candidates = res.json()
        assert len(candidates) >= 2

        # 3. Test Match Candidate to Job: POST /api/v1/jobs/{job_id}/match/{candidate_id}
        res = await client.post(f"/api/v1/jobs/{job_id}/match/{candidate_a.id}", headers=auth_headers)
        assert res.status_code == 200
        match_data = res.json()
        assert "match_score" in match_data
        assert match_data["fit_category"] in ["STRONG_MATCH", "POTENTIAL_MATCH", "POOR_MATCH", "PERFECT_MATCH"]

        # 4. Test GET /api/v1/jobs/{job_id}/matches
        res = await client.get(f"/api/v1/jobs/{job_id}/matches", headers=auth_headers)
        assert res.status_code == 200
        matches_list = res.json()
        assert len(matches_list) >= 1
        assert matches_list[0]["candidate_id"] == str(candidate_a.id)

        # 5. Test GET /api/v1/evidence-graph/{audit_id}
        res = await client.get(f"/api/v1/evidence-graph/{audit_a.id}", headers=auth_headers)
        assert res.status_code == 200
        graph_data = res.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert len(graph_data["nodes"]) >= 3

        # 6. Test Assessments: POST /api/v1/assessments/generate & submit
        assess_gen = {
            "candidate_id": str(candidate_a.id),
            "job_id": job_id,
            "duration_minutes": 20
        }
        res = await client.post("/api/v1/assessments/generate", json=assess_gen, headers=auth_headers)
        assert res.status_code == 200
        assess_data = res.json()
        assessment_id = assess_data["id"]
        assert len(assess_data["problem_set"]) > 0

        # Submit assessment
        submit_payload = {
            "answers": {
                "solution": "We use Redis distributed locks with exponential backoff for high-throughput rate limiting."
            }
        }
        res = await client.post(f"/api/v1/assessments/{assessment_id}/submit", json=submit_payload, headers=auth_headers)
        assert res.status_code == 200
        graded = res.json()
        assert "score" in graded
        assert "rubric_breakdown" in graded

        # 7. Test AI Interviewer: POST /api/v1/interviews/start & respond
        int_start = {
            "candidate_id": str(candidate_a.id),
            "job_id": job_id
        }
        res = await client.post("/api/v1/interviews/start", json=int_start, headers=auth_headers)
        assert res.status_code == 200
        interview_data = res.json()
        interview_id = interview_data["id"]
        assert "current_question" in interview_data

        # Respond to interview
        int_resp = {
            "candidate_answer": "In our database layer, we used partitioned tables and read replicas with connection pooling."
        }
        res = await client.post(f"/api/v1/interviews/{interview_id}/respond", json=int_resp, headers=auth_headers)
        assert res.status_code == 200
        int_followup = res.json()
        assert "probing_question" in int_followup or "next_question" in int_followup

        # 8. Test Candidate Comparison: POST /api/v1/compare
        comp_payload = {
            "candidate_ids": [str(candidate_a.id), str(candidate_b.id)],
            "job_id": job_id
        }
        res = await client.post("/api/v1/compare", json=comp_payload, headers=auth_headers)
        assert res.status_code == 200
        comp_data = res.json()
        assert len(comp_data["candidates"]) == 2
        assert "recommendation_summary" in comp_data
        assert "winner_name" in comp_data["recommendation_summary"]

        # 9. Test Pipeline Kanban: POST /api/v1/pipeline/transition & GET /api/v1/pipeline/board
        trans_payload = {
            "candidate_id": str(candidate_a.id),
            "new_stage": "interview",
            "notes": "Technical screening passed with 86/100"
        }
        res = await client.post("/api/v1/pipeline/transition", json=trans_payload, headers=auth_headers)
        assert res.status_code == 200

        res = await client.get("/api/v1/pipeline/board", headers=auth_headers)
        assert res.status_code == 200
        board_stages = res.json()
        assert len(board_stages) >= 6
        interview_col = next(s for s in board_stages if s["stage"] == "interview")
        assert any(c["id"] == str(candidate_a.id) for c in interview_col["candidates"])

        # 10. Test Analytics: GET /api/v1/analytics
        res = await client.get("/api/v1/analytics", headers=auth_headers)
        assert res.status_code == 200
        analytics_data = res.json()
        assert "total_candidates_screened" in analytics_data
        assert "estimated_hours_saved" in analytics_data
        assert "funnel_stages" in analytics_data

        # 11. Test Recruiter Copilot: POST /api/v1/copilot/chat
        copilot_payload = {
            "query": "Who is our top candidate with Python and PostgreSQL experience?"
        }
        res = await client.post("/api/v1/copilot/chat", json=copilot_payload, headers=auth_headers)
        assert res.status_code == 200
        copilot_data = res.json()
        assert "answer" in copilot_data
        assert len(copilot_data["answer"]) > 10
