import pytest
import asyncio
import io
import uuid
import pypdf
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from src.api import app
from src.db.session import async_session_factory
from src.db.models import Organization, Candidate, Audit, GeneratedReply
from src.services.screening_service import screen_candidate_core
from src.batch_screener import run_batch_screening

from reportlab.pdfgen import canvas

def _create_minimal_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    textobject = c.beginText(50, 750)
    for line in text.split("\n"):
        textobject.textLine(line)
    c.drawText(textobject)
    c.showPage()
    c.save()
    return buf.getvalue()

REAL_RESUME_TEXT = """
Alex Morgan
Senior Backend Engineer
Email: alex.morgan@example.com | Phone: (555) 234-5678 | GitHub: github.com/alexmorgan-dev
Location: San Francisco, CA | LinkedIn: linkedin.com/in/alexmorgan

PROFESSIONAL SUMMARY
Results-driven Senior Backend Engineer with 5+ years of experience designing high-throughput distributed microservices,
RESTful APIs, and cloud-native database architectures. Strong expertise in Python, FastAPI, Docker, and PostgreSQL.

WORK EXPERIENCE
Senior Software Engineer | CloudScale Systems (2022 - Present)
- Designed and built scalable backend APIs handling 15,000+ RPS using FastAPI and Python.
- Containerized microservices with Docker and orchestrated deployment on AWS ECS with PostgreSQL RDS.
- Conducted production A/B experiment evaluation on data caching layers reducing latency by 45%.

Software Engineer | FinTech Innovations (2019 - 2022)
- Developed secure transaction processing pipelines in Python and Django with PostgreSQL.
- Reduced database query times by 35% through indexing and query optimization.

EDUCATION
Bachelor of Science in Computer Science | University of California, Berkeley (2015 - 2019)

TECHNICAL SKILLS
Languages: Python, SQL, TypeScript, Go
Frameworks: FastAPI, Django, Docker, PostgreSQL, Redis, AWS
"""

LAB_MANUAL_TEXT = """
DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING
Database Systems Laboratory Manual
Academic Year: 2025-2026 | Course Code: CS-302

### Experiment 2: Types of Constraints in SQL
Objective:
In this lab exercise, students will implement Primary Key, Foreign Key, Check, and Unique constraints.

Procedure:
1. Open MySQL workbench and create table student_records.
2. Apply NOT NULL constraint to enrollment_id.
3. Observe error output when inserting duplicate values.

Expected Outcome:
Students should understand data integrity and table constraints in relational database systems.
"""

RESUME_WITHOUT_GITHUB = """
Jordan Lee
Senior Frontend Architect
Email: jordan.lee@example.com | Phone: (555) 987-6543 | LinkedIn: linkedin.com/in/jordanlee
Location: Austin, TX

SUMMARY
Architect with 6 years of experience building enterprise web applications with React, TypeScript, and Node.js.

WORK EXPERIENCE
Frontend Lead | NextGen Tech (2021 - Present)
- Architected enterprise SaaS frontend using React, Next.js, and TypeScript.
- Managed design system components used across 8 engineering teams.

EDUCATION
BS in Information Technology | University of Texas (2014 - 2018)

SKILLS
React, TypeScript, JavaScript, CSS, HTML, Webpack, Node.js
"""

@pytest.mark.asyncio
async def test_recruiter_journey_valid_resume():
    """Journey 1: Valid resume screening returns structured assessment, why_score, evidence_items, next_action."""
    org_id = uuid.uuid4()
    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Recruiter Journey Corp",
            slug=f"recruiter-{org_id.hex[:6]}",
            plan_tier="growth",
            monthly_resume_limit=100,
            monthly_resumes_used=0,
            is_active=True
        )
        db.add(org)
        await db.commit()

        pdf_bytes = _create_minimal_pdf(REAL_RESUME_TEXT)
        result = await screen_candidate_core(
            db=db,
            organization_id=org_id,
            file_bytes=pdf_bytes,
            filename="Alex_Morgan_Resume.pdf",
            job_title="Senior Backend Engineer",
            required_skills=["Python", "Docker", "PostgreSQL"]
        )

        # 1. Verification of standardized recruiter assessment contract
        assert result["success"] is True
        assert result["status"] == "completed"
        assert result["is_valid_resume"] is True
        assert result["document_type"] == "RESUME"
        assert result["overall_score"] > 0

        # Assessment sub-object
        assessment = result["assessment"]
        assert assessment["overall_score"] == result["overall_score"]
        assert assessment["recommendation"] in ("STRONG_CANDIDATE", "REVIEW", "REJECT")
        assert "skills_match" in assessment
        assert "experience" in assessment
        assert "projects" in assessment
        assert "technical_evidence" in assessment
        assert "resume_quality" in assessment
        assert assessment["next_action"] in ("SCHEDULE_INTERVIEW", "REVIEW_RECOMMENDED", "DO_NOT_PROCEED")
        assert len(assessment["next_action_label"]) > 0

        # Why score explanation
        why_score = result["why_score"]
        assert why_score["score"] == result["overall_score"]
        assert len(why_score["reasons"]) > 0
        assert len(why_score["areas_to_verify"]) > 0

        # Evidence table
        assert "evidence_items" in result
        assert len(result["evidence_items"]) > 0
        for ev in result["evidence_items"]:
            assert "skill" in ev
            assert ev["status"] in ("Verified", "Partially Verified", "Unverified", "Unavailable")
            assert "evidence" in ev

        # Next action explicit
        assert result["next_action"] == assessment["next_action"]
        assert result["next_action_label"] == assessment["next_action_label"]

@pytest.mark.asyncio
async def test_recruiter_journey_invalid_document_early_halt():
    """Journey 2: Lab manual / non-resume stops immediately with score 0, INVALID_DOCUMENT, and resubmission draft."""
    org_id = uuid.uuid4()
    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Invalid Doc Corp",
            slug=f"inv-{org_id.hex[:6]}",
            plan_tier="growth",
            monthly_resume_limit=100,
            monthly_resumes_used=0,
            is_active=True
        )
        db.add(org)
        await db.commit()

        pdf_bytes = _create_minimal_pdf(LAB_MANUAL_TEXT)
        result = await screen_candidate_core(
            db=db,
            organization_id=org_id,
            file_bytes=pdf_bytes,
            filename="CS302_Lab_Manual_Exp2.pdf",
            job_title="Software Engineer"
        )

        assert result["success"] is True
        assert result["is_valid_resume"] is False
        assert result["document_type"] == "ACADEMIC_LAB_OR_EXERCISE"
        assert result["overall_score"] == 0
        assert result["recommendation"] == "REJECT"

        # Assessment object for invalid doc
        assessment = result["assessment"]
        assert assessment["overall_score"] == 0
        assert assessment["recommendation"] == "INVALID_DOCUMENT"
        assert assessment["next_action"] == "REQUEST_RESUME"
        assert assessment["next_action_label"] == "Request a valid resume"

        # Zero candidate assessment metrics
        assert assessment["skills_match"] == 0
        assert assessment["experience"] == 0
        assert assessment["projects"] == 0

        # Evidence items must be empty for invalid doc
        assert result["evidence_items"] == []

        # Auto-draft reply must be resubmission request, NEVER interview invite
        assert result["draft_reply"]["reply_type"] == "resubmission_request"
        assert "Resubmission" in result["draft_reply"]["subject"]

@pytest.mark.asyncio
async def test_recruiter_journey_resume_without_github():
    """Journey 3: Resume without GitHub is evaluated without penalties and marks GitHub as Unavailable."""
    org_id = uuid.uuid4()
    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="No GitHub Corp",
            slug=f"nogit-{org_id.hex[:6]}",
            plan_tier="starter",
            monthly_resume_limit=50,
            monthly_resumes_used=0,
            is_active=True
        )
        db.add(org)
        await db.commit()

        pdf_bytes = _create_minimal_pdf(RESUME_WITHOUT_GITHUB)
        result = await screen_candidate_core(
            db=db,
            organization_id=org_id,
            file_bytes=pdf_bytes,
            filename="Jordan_Lee_Resume.pdf",
            github_user_override=""
        )

        assert result["is_valid_resume"] is True
        assert result["overall_score"] > 0
        assert result["github_username"] == "none"

        # Evidence items show Unavailable for GitHub
        for ev in result["evidence_items"]:
            assert ev["status"] == "Unavailable"
            assert "unavailable" in ev["evidence"].lower()

@pytest.mark.asyncio
async def test_dashboard_stats_endpoint():
    """Tests the new /api/v1/dashboard/stats aggregation endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/dashboard/stats")
        assert res.status_code == 200
        data = res.json()
        assert "screened_today" in data
        assert "total_screened" in data
        assert "strong_count" in data
        assert "review_count" in data
        assert "rejected_count" in data
        assert "invalid_count" in data
        assert "credits_available" in data
        assert "recent_screenings" in data
        assert isinstance(data["recent_screenings"], list)

@pytest.mark.asyncio
async def test_screenings_search_and_filter():
    """Tests candidate history filtering and search."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # All screenings
        res_all = await client.get("/api/v1/screenings?filter_status=ALL")
        assert res_all.status_code == 200
        assert isinstance(res_all.json(), list)

        # Invalid only
        res_inv = await client.get("/api/v1/screenings?filter_status=INVALID")
        assert res_inv.status_code == 200
        for item in res_inv.json():
            assert not item.get("is_valid_resume", True) or item.get("overall_score") == 0

        # Strong only
        res_strong = await client.get("/api/v1/screenings?filter_status=STRONG")
        assert res_strong.status_code == 200
        for item in res_strong.json():
            assert item.get("overall_score") >= 80

@pytest.mark.asyncio
async def test_batch_screening_recruiter_parity():
    """Journey 6: Batch screening summary includes invalid_count and candidate recruiter recommendations."""
    batch_id = str(uuid.uuid4())
    valid_pdf = _create_minimal_pdf(REAL_RESUME_TEXT)
    lab_pdf = _create_minimal_pdf(LAB_MANUAL_TEXT)

    apps = [
        {"name": "Valid Candidate", "pdf_bytes": valid_pdf, "github_username": "tiangolo", "linkedin_url": None},
        {"name": "Lab Manual Student", "pdf_bytes": lab_pdf, "github_username": "none", "linkedin_url": None}
    ]

    summary = await run_batch_screening(batch_id, apps)
    assert summary.total_candidates == 2
    assert summary.invalid_count == 1
    assert summary.shortlisted_count + summary.review_count == 1

    # Candidate 1: valid
    cand_valid = next(c for c in summary.candidates if c.is_valid_resume)
    assert cand_valid.overall_score > 0
    assert cand_valid.recruiter_recommendation in ("STRONG_CANDIDATE", "REVIEW")
    assert cand_valid.next_action in ("SCHEDULE_INTERVIEW", "REVIEW_RECOMMENDED")

    # Candidate 2: invalid
    cand_invalid = next(c for c in summary.candidates if not c.is_valid_resume)
    assert cand_invalid.overall_score == 0
    assert cand_invalid.recruiter_recommendation == "INVALID_DOCUMENT"
    assert cand_invalid.next_action == "REQUEST_RESUME"
    assert cand_invalid.email_draft["subject"].startswith("Action Required:")
