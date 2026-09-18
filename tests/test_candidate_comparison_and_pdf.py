import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from src.api import app
from src.db.session import async_session_factory
from src.services.comparison_service import CandidateComparisonService
from src.services.evidence_interview_generator import EvidenceInterviewGenerator, CommitInterviewPack
from src.services.pdf_export_service import ExecutiveScorecardPdfService
from src.services.interview_service import TechnicalInterviewService
from src.db.models import Candidate, Audit, Organization, Application, JobOpening

@pytest.mark.asyncio
async def test_comparison_service_skill_radar_and_matrix():
    """Verifies that multi-candidate comparison produces 6-axis radar metrics and side-by-side matrix."""
    async with async_session_factory() as db_session:
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Radar Test Org", slug=f"radar-org-{org_id.hex[:6]}")
        db_session.add(org)
        await db_session.flush()

        # Create 2 candidates
        c1 = Candidate(
            id=uuid.uuid4(),
            organization_id=org_id,
            name="Candidate Alpha",
            email="alpha@example.com",
            github_username="alpha-dev",
            tags=["Python", "FastAPI", "Docker", "PostgreSQL"]
        )
        c2 = Candidate(
            id=uuid.uuid4(),
            organization_id=org_id,
            name="Candidate Beta",
            email="beta@example.com",
            github_username="beta-dev",
            tags=["Python", "Django", "AWS", "Redis"]
        )
        db_session.add_all([c1, c2])
        await db_session.flush()

        # Create Applications
        app1 = Application(
            id=uuid.uuid4(),
            organization_id=org_id,
            candidate_id=c1.id,
            job_title="Backend Engineer",
            source="upload",
            status="screened"
        )
        app2 = Application(
            id=uuid.uuid4(),
            organization_id=org_id,
            candidate_id=c2.id,
            job_title="Backend Engineer",
            source="upload",
            status="screened"
        )
        db_session.add_all([app1, app2])
        await db_session.flush()

        # Create Audits for both
        a1 = Audit(
            id=uuid.uuid4(),
            organization_id=org_id,
            application_id=app1.id,
            candidate_id=c1.id,
            overall_score=88,
            code_quality_score=90,
            consistency_score=86,
            skills_match_score=92,
            executive_summary="Strong technical proficiency across all tested competencies.",
            ai_recommendation="STRONG_CANDIDATE"
        )
        a2 = Audit(
            id=uuid.uuid4(),
            organization_id=org_id,
            application_id=app2.id,
            candidate_id=c2.id,
            overall_score=78,
            code_quality_score=75,
            consistency_score=80,
            skills_match_score=82,
            executive_summary="Solid technical background with standard production experience.",
            ai_recommendation="RECOMMENDED"
        )
        db_session.add_all([a1, a2])
        await db_session.commit()

        svc = CandidateComparisonService(db_session, org_id)
        result = await svc.compare_candidates([c1.id, c2.id])

        # Assert basic comparison structure
        assert result["candidate_count"] == 2
        assert len(result["candidates"]) == 2

        # Assert 6-axis skill radar visualization schema
        radar = result["radar_chart"]
        assert radar is not None
        assert "dimensions" in radar
        assert len(radar["dimensions"]) == 6
        assert "Skills Alignment" in radar["dimensions"]
        assert "Code Quality" in radar["dimensions"]
        assert "Consistency" in radar["dimensions"]
        assert "Job Match" in radar["dimensions"]
        assert "Assessment" in radar["dimensions"]
        assert "Interview" in radar["dimensions"]

        assert len(radar["series"]) == 2
        for series in radar["series"]:
            assert "candidate_id" in series
            assert "candidate_name" in series
            assert len(series["data"]) == 6
            assert all(0 <= val <= 100 for val in series["data"])

        # Assert side-by-side matrix table
        matrix = result["side_by_side_matrix"]
        assert len(matrix) >= 8
        metric_names = [m["metric"] for m in matrix]
        assert "Overall Evidence Score" in metric_names
        assert "Composite Evaluator Score" in metric_names
        assert "Code Quality Score" in metric_names
        assert "Consistency & Authorship" in metric_names

        # Assert top candidate verdict with justification
        verdict = result["top_candidate_verdict"]
        assert verdict["winner_id"] == str(c1.id)
        assert verdict["winner_name"] == "Candidate Alpha"
        assert "Alpha" in verdict["rationale"]
        assert len(verdict["dimension_advantages"]) > 0


def test_evidence_interview_generator_with_commits():
    """Verifies that interview generator inspects commits and cites SHAs, repos, and messages."""
    sample_repos = [
        {
            "name": "payment-orchestrator",
            "detected_frameworks": ["FastAPI", "SQLAlchemy", "PostgreSQL", "Docker"],
            "commit_samples": [
                {
                    "sha": "4f8a12b",
                    "message": "Configure async connection pool with retry backoff and statement timeouts",
                    "date": "2024-02-10"
                }
            ]
        },
        {
            "name": "cache-accelerator",
            "detected_frameworks": ["Redis", "Pydantic"],
            "commit_samples": [
                {
                    "sha": "b2c3d4e",
                    "message": "Add Redis cache layer with probabilistic early expiration",
                    "date": "2024-03-01"
                }
            ]
        }
    ]

    pack = EvidenceInterviewGenerator.generate_from_repo_highlights(
        candidate_name="Elena Rostova",
        job_title="Principal Backend Engineer",
        repo_highlights=sample_repos,
        max_questions=4
    )

    assert isinstance(pack, CommitInterviewPack)
    assert pack.candidate_name == "Elena Rostova"
    assert pack.job_title == "Principal Backend Engineer"
    assert pack.total_questions >= 2

    # Check commit grounding
    q1 = pack.questions[0]
    assert "payment-orchestrator" in q1.repo_name or "cache-accelerator" in q1.repo_name
    assert len(q1.commit_sha) >= 7
    assert q1.grounding_type == "verified_commit"
    assert "4f8a12b" in q1.question or "b2c3d4e" in q1.question
    assert len(q1.evaluation_rubric) >= 2
    assert len(q1.followup_questions) >= 1


def test_evidence_interview_generator_fallback():
    """Verifies graceful fallback to realistic scenario questions when candidate has no public commits."""
    pack = EvidenceInterviewGenerator.generate_from_repo_highlights(
        candidate_name="Anonymous Candidate",
        job_title="Lead Distributed Systems Engineer",
        repo_highlights=[],
        max_questions=3
    )

    assert pack.total_questions >= 2
    for q in pack.questions:
        assert q.grounding_type == "claimed_stack_scenario"
        assert len(q.evaluation_rubric) >= 2
        assert "Lead Distributed Systems Engineer" in q.question or len(q.question) > 50


def test_executive_scorecard_pdf_generation():
    """Verifies that ExecutiveScorecardPdfService builds a valid binary PDF with all executive sections."""
    cand_data = {
        "candidate_id": str(uuid.uuid4()),
        "name": "Dr. Aris Thorne",
        "email": "aris.thorne@example.com",
        "github_username": "thorne-ai",
        "overall_score": 91,
        "recommendation": "STRONG_CANDIDATE",
        "breakdown": {
            "code_quality_score": 93,
            "consistency_score": 89,
            "domain_score": 94
        },
        "verified_skills": ["Python", "C++", "FastAPI", "Docker", "PyTorch"],
        "red_flags": [],
        "highlights": [
            "Verified consistent multi-year commit history.",
            "Exceptional test coverage and strict type annotations."
        ]
    }
    audit_data = {
        "overall_score": 91,
        "ai_recommendation": "STRONG_CANDIDATE",
        "claim_verifications": [
            {
                "claim": "FastAPI",
                "category": "Framework",
                "status": "Verified",
                "evidence_description": "Production REST routes and Pydantic schemas found."
            },
            {
                "claim": "Docker",
                "category": "DevOps",
                "status": "Verified",
                "evidence_description": "Multi-stage Dockerfiles and compose configs verified."
            }
        ],
        "raw_payload": {
            "github_evidence": {
                "repo_highlights": [
                    {
                        "name": "distributed-inference-gateway",
                        "language": "Python",
                        "commit_samples": [
                            {"sha": "a7b8c9d", "message": "Optimize batched tensor serialization and async worker pool"}
                        ]
                    }
                ]
            }
        }
    }

    pdf_bytes = ExecutiveScorecardPdfService.generate_candidate_scorecard_pdf(
        candidate_data=cand_data,
        audit_data=audit_data,
        job_title="Staff ML Platform Engineer"
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2500


@pytest.mark.asyncio
async def test_api_generate_interview_questions_from_commits():
    """Tests POST /api/v1/interviews/generate-from-commits API endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "candidate_name": "Dev Priya",
            "job_title": "Senior Cloud Engineer",
            "repo_highlights": [
                {
                    "name": "cloud-resilience-proxy",
                    "detected_frameworks": ["Go", "Docker", "Redis"],
                    "commit_samples": [
                        {
                            "sha": "99bb11a",
                            "message": "Implement Redis token bucket rate limiter and connection retry backoff",
                            "date": "2024-01-20"
                        }
                    ]
                }
            ],
            "max_questions": 3
        }
        res = await client.post("/api/v1/interviews/generate-from-commits", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["candidate_name"] == "Dev Priya"
        assert data["total_questions"] >= 1
        assert "99bb11a" in data["questions"][0]["question"] or "cloud-resilience-proxy" in data["questions"][0]["question"]


@pytest.mark.asyncio
async def test_api_screenings_pdf_export():
    """Tests GET /api/v1/screenings/{task_id}/pdf endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/screenings/demo-001/pdf")
        assert res.status_code == 200
        assert res.headers.get("content-type") == "application/pdf"
        assert res.content.startswith(b"%PDF-")
        assert len(res.content) > 2000


@pytest.mark.asyncio
async def test_api_candidate_pdf_scorecard_export():
    """Tests GET /api/v1/candidates/{candidate_id}/export/pdf endpoint."""
    async with async_session_factory() as db_session:
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Export PDF Test Org", slug=f"export-pdf-{org_id.hex[:6]}")
        db_session.add(org)
        await db_session.flush()

        c = Candidate(
            id=uuid.uuid4(),
            organization_id=org_id,
            name="Zara Vance",
            email="zara.vance@example.com",
            github_username="zaravance",
            tags=["Python", "FastAPI", "Docker"]
        )
        db_session.add(c)
        await db_session.flush()

        app_rec = Application(
            id=uuid.uuid4(),
            organization_id=org_id,
            candidate_id=c.id,
            job_title="Lead Architect",
            source="upload",
            status="screened"
        )
        db_session.add(app_rec)
        await db_session.flush()

        audit = Audit(
            id=uuid.uuid4(),
            organization_id=org_id,
            application_id=app_rec.id,
            candidate_id=c.id,
            overall_score=89,
            code_quality_score=91,
            consistency_score=88,
            skills_match_score=90,
            executive_summary="Verified production architecture with clean modular structure.",
            ai_recommendation="STRONG_CANDIDATE"
        )
        db_session.add(audit)
        from src.db.models import User, Membership
        from src.security import hash_password, create_access_token

        user = User(
            id=uuid.uuid4(),
            email=f"admin-{org.id.hex[:6]}@example.com",
            hashed_password=hash_password("Password123!"),
            full_name="Admin Recruiter",
            is_active=True
        )
        db_session.add(user)
        await db_session.flush()

        membership = Membership(
            organization_id=org.id,
            user_id=user.id,
            role="owner"
        )
        db_session.add(membership)
        await db_session.commit()

        token = create_access_token(data={"sub": str(user.id)})

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            res = await client.get(
                f"/api/v1/candidates/{c.id}/export/pdf",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert res.status_code == 200
            assert res.headers.get("content-type") == "application/pdf"
            assert res.content.startswith(b"%PDF-")
            assert "Zara_Vance" in res.headers.get("content-disposition", "")

