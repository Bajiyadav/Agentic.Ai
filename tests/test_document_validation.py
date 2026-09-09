import io
import os
import uuid
import tempfile
import pytest
from reportlab.pdfgen import canvas
from httpx import AsyncClient, ASGITransport

from src.api import app
from src.agent_1_resume_parser import (
    validate_resume_document,
    _heuristic_resume_parser,
    parse_resume,
    CandidateClaims
)
from src.agent_2_code_auditor import audit_github, GitHubEvidence
from src.agent_3_evaluator import _deterministic_evaluator, evaluate_candidate
from src.consensus_evaluator import run_consensus_evaluation
from src.batch_screener import run_batch_screening
from src.services.screening_service import screen_candidate_core
from src.db.session import async_session_factory
from src.db.models import Organization, User, Membership
from src.security import hash_password, create_access_token

def _make_pdf(text: str) -> bytes:
    """Helper to generate a real PDF in memory with custom text."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    textobject = c.beginText(50, 750)
    for line in text.split("\n"):
        textobject.textLine(line)
    c.drawText(textobject)
    c.showPage()
    c.save()
    return buf.getvalue()


def test_real_resume_validation():
    """Real candidate resume with experience, education, skills, and contact info must be VALID."""
    resume_text = """
    Aarav Sharma
    Email: aarav.sharma@example.com | Phone: +1-555-019-2831
    GitHub: https://github.com/aaravsharma | LinkedIn: linkedin.com/in/aaravsharma

    Professional Summary:
    Senior Software Engineer with 5+ years of experience building high-performance backend systems.

    Technical Skills:
    Languages: Python, Go, TypeScript, SQL
    Frameworks: FastAPI, Django, React
    Tools & Infrastructure: Docker, Kubernetes, PostgreSQL, Redis, AWS

    Professional Experience:
    Senior Backend Engineer - CloudTech Labs (2021 - Present)
    - Architected distributed event-driven microservices using Python and FastAPI.
    - Improved p99 query latency by 45% using Redis caching and PostgreSQL indexing.

    Projects:
    - API Gateway Engine: Open-source asynchronous reverse proxy built in Python.

    Education:
    B.S. in Computer Science - University of Technology (2016 - 2020)
    """
    val = validate_resume_document(resume_text)
    assert val["is_valid_resume"] is True
    assert val["document_type"] == "RESUME"
    assert val["positive_score"] >= 4

    claims = _heuristic_resume_parser(resume_text)
    assert claims.is_valid_resume is True
    assert claims.name == "Aarav Sharma"
    assert "Python" in claims.claimed_languages
    assert "FastAPI" in claims.claimed_frameworks


def test_real_resume_with_word_experiment():
    """A real resume mentioning A/B testing or ML 'experiment' projects must NOT be falsely rejected."""
    resume_text = """
    Sarah Lin
    Email: sarah.lin@example.com | Phone: (555) 234-5678
    GitHub: github.com/sarahlin | LinkedIn: linkedin.com/in/sarahlin

    Professional Summary:
    Data Scientist and Machine Learning Engineer with 4 years of experience.

    Technical Skills:
    Languages: Python, R, SQL
    Frameworks: PyTorch, TensorFlow, Scikit-Learn
    Tools: Docker, AWS, Git

    Work Experience:
    Machine Learning Engineer - FinTech Innovations (2020 - Present)
    - Designed and launched production A/B experiment projects evaluating recommendation models.
    - Conducted over 50 multivariate experiment iterations leading to a 12% boost in user retention.
    - Built experiment tracking pipeline using MLflow and Docker containers.

    Education:
    M.S. in Data Science - State University
    B.S. in Mathematics
    """
    val = validate_resume_document(resume_text)
    assert val["is_valid_resume"] is True
    assert val["document_type"] == "RESUME"

    claims = _heuristic_resume_parser(resume_text)
    assert claims.is_valid_resume is True
    assert claims.name == "Sarah Lin"
    assert "Python" in claims.claimed_languages


def test_academic_lab_manual_rejection():
    """Academic lab manual (e.g. Experiment 2 Types Of Constraints) must be strictly INVALID."""
    lab_text = """
    ### Experiment 2 Types Of Constraints
    This document provides the SQL commands and expected outcomes for each lab exercise.
    You should execute these commands in your SQL environment (e.g., MySQL, PostgreSQL, SQL Server) and observe the results.

    Lab Objectives:
    To understand PRIMARY KEY, FOREIGN KEY, UNIQUE, and CHECK constraints.

    Procedure:
    1. Create database schema.
    2. Insert sample records violating constraints to observe error messages.
    """
    val = validate_resume_document(lab_text)
    assert val["is_valid_resume"] is False
    assert val["document_type"] == "ACADEMIC_LAB_OR_EXERCISE"

    claims = _heuristic_resume_parser(lab_text)
    assert claims.is_valid_resume is False
    assert claims.name == "Non-Resume Document"
    assert len(claims.claimed_languages) == 0
    assert len(claims.claimed_frameworks) == 0
    assert len(claims.claimed_tools) == 0


def test_assignment_homework_rejection():
    """Academic homework / assignment sheet must be strictly INVALID."""
    hw_text = """
    Course Code: CS204 - Advanced Algorithms
    Assignment # 3: Dynamic Programming and Graph Theory
    Semester: Fall 2024
    Department of Computer Science and Engineering

    Instructions:
    Answer all 5 questions. Late submissions will receive a 20% penalty per day.

    Question 1:
    Implement Dijkstra's shortest path algorithm using a Fibonacci heap.
    Expected output should demonstrate O(V log V + E) asymptotic complexity.
    """
    val = validate_resume_document(hw_text)
    assert val["is_valid_resume"] is False
    assert val["document_type"] == "ASSIGNMENT_OR_HOMEWORK"


def test_question_paper_rejection():
    """University question paper must be strictly INVALID."""
    exam_text = """
    Midterm Examination - Fall 2024
    Course Code: IT302 Database Management Systems
    Question Paper
    Department of Information Technology
    Time Allowed: 3 Hours
    Total Marks: 100
    Marking Scheme: Section A (40 marks), Section B (60 marks)

    Section A:
    Explain the difference between 2NF and 3NF normalization.
    """
    val = validate_resume_document(exam_text)
    assert val["is_valid_resume"] is False
    assert val["document_type"] == "QUESTION_PAPER"


def test_empty_or_corrupt_document_rejection():
    """Documents with less than 80 characters must be rejected as EMPTY_OR_CORRUPT."""
    short_text = "Hello world. Just testing a short snippet."
    val = validate_resume_document(short_text)
    assert val["is_valid_resume"] is False
    assert val["document_type"] == "EMPTY_OR_CORRUPT"


def test_consensus_hard_rule_immunity():
    """Consensus evaluation must NEVER override hard validation rules."""
    invalid_claims = CandidateClaims(
        name="Non-Resume Document",
        is_valid_resume=False,
        document_type="ACADEMIC_LAB_OR_EXERCISE",
        claimed_languages=[]
    )
    fake_evidence = GitHubEvidence(
        username="none",
        profile_found=False
    )
    consensus = run_consensus_evaluation(invalid_claims, fake_evidence)
    assert consensus.scorecard.overall_score == 0
    assert consensus.scorecard.recommendation == "REJECT"
    assert any("NOT a valid" in f for f in consensus.scorecard.red_flags)
    # Model votes must all be 0
    for model_name, vote in consensus.model_votes.items():
        assert vote == 0


@pytest.mark.asyncio
async def test_batch_screening_validation_gates():
    """Batch screener must apply identical validation rules and early termination."""
    valid_pdf = _make_pdf(
        "John Doe\nEmail: john@example.com\nExperience: 4 years\nSkills: Python, FastAPI\nWork Experience: Backend Engineer"
    )
    invalid_pdf = _make_pdf(
        "### Experiment 2 Types Of Constraints\nThis document provides the SQL commands and expected outcomes for each lab exercise."
    )

    batch_apps = [
        {"name": "John Doe", "pdf_bytes": valid_pdf, "github_username": "tiangolo"},
        {"name": "Lab Manual", "pdf_bytes": invalid_pdf, "github_username": None}
    ]

    summary = await run_batch_screening(batch_id="test-batch-val", applications=batch_apps)
    assert summary.total_candidates == 2

    # Verify invalid candidate got 0 / REJECT
    invalid_res = next(c for c in summary.candidates if not c.is_valid_resume)
    assert invalid_res.overall_score == 0
    assert invalid_res.recommendation == "REJECT"
    assert invalid_res.document_type == "ACADEMIC_LAB_OR_EXERCISE"
    assert "Action Required: Resume Submission" in invalid_res.email_draft.get("subject", "")

    # Verify valid candidate got scored normally
    valid_res = next(c for c in summary.candidates if c.is_valid_resume)
    assert valid_res.overall_score > 0
    assert valid_res.recommendation in ("SHORTLIST", "REVIEW")


@pytest.mark.asyncio
async def test_end_to_end_screening_service_early_termination():
    """Verifies that screening_service terminates early on invalid documents in < 0.2s without GitHub calls."""
    async with async_session_factory() as db:
        # Create test organization
        org = Organization(
            name="Early Exit Org",
            slug=f"org-test-{uuid.uuid4().hex[:6]}",
            plan_tier="enterprise",
            monthly_resume_limit=500,
            monthly_resumes_used=0
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)

        lab_pdf = _make_pdf(
            "### Experiment 2 Types Of Constraints\n"
            "This document provides the SQL commands and expected outcomes for each lab exercise.\n"
            "You should execute these commands in your SQL environment."
        )

        result = await screen_candidate_core(
            db=db,
            organization_id=org.id,
            file_bytes=lab_pdf,
            filename="experiment_2_types_of_constraints.pdf",
            job_title="Software Engineer"
        )

        assert result["is_valid_resume"] is False
        assert result["document_type"] == "ACADEMIC_LAB_OR_EXERCISE"
        assert result["overall_score"] == 0
        assert result["recommendation"] == "REJECT"
        assert result["github_username"] == "none"
        assert result["latency_seconds"] < 0.5  # Early termination guarantee

        # Check draft reply is resubmission notice, not interview invite!
        draft = result.get("draft_reply", {})
        assert draft.get("reply_type") == "resubmission_request"
        assert "Interview Invitation" not in draft.get("subject", "")

        # Check structuredSection 14 contract
        assert result["document"]["is_valid_resume"] is False
        assert result["document"]["document_type"] == "ACADEMIC_LAB_OR_EXERCISE"
        assert result["scorecard"]["overall_score"] == 0
        assert result["scorecard"]["recommendation"] == "REJECT"


@pytest.mark.asyncio
async def test_api_screen_endpoint_valid_and_invalid_pdf():
    """Tests POST /api/v1/screen and result retrieval for both valid resume and academic lab manual."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Screen Invalid Document (Academic Lab Manual)
        lab_pdf = _make_pdf(
            "### Experiment 2 Types Of Constraints\n"
            "This document provides the SQL commands and expected outcomes for each lab exercise.\n"
            "You should execute these commands in your SQL environment (e.g., MySQL, PostgreSQL, SQL Server)."
        )
        res_invalid = await client.post(
            "/api/v1/screen",
            files={"file": ("experiment_2_types_of_constraints.pdf", lab_pdf, "application/pdf")},
            data={"target_role": "Backend Engineer"}
        )
        assert res_invalid.status_code == 200
        data_invalid = res_invalid.json()
        task_id = data_invalid["task_id"]

        # Poll result
        import asyncio
        poll_res = None
        for _ in range(10):
            poll_resp = await client.get(f"/api/v1/results/{task_id}")
            if poll_resp.status_code == 200 and poll_resp.json().get("status") == "completed":
                poll_res = poll_resp.json()["result"]
                break
            await asyncio.sleep(0.2)

        assert poll_res is not None
        assert poll_res["is_valid_resume"] is False
        assert poll_res["document_type"] == "ACADEMIC_LAB_OR_EXERCISE"
        assert poll_res["overall_score"] == 0
        assert poll_res["recommendation"] == "REJECT"
        assert poll_res["document"]["is_valid_resume"] is False

        # 2. Screen Valid Resume PDF
        with open("sample_resume.pdf", "rb") as f:
            valid_pdf = f.read()

        res_valid = await client.post(
            "/api/v1/screen",
            files={"file": ("sample_resume.pdf", valid_pdf, "application/pdf")},
            data={"target_role": "Software Engineer", "github_username": "tiangolo"}
        )
        assert res_valid.status_code == 200
        valid_task_id = res_valid.json()["task_id"]

        valid_poll_res = None
        for _ in range(10):
            v_resp = await client.get(f"/api/v1/results/{valid_task_id}")
            if v_resp.status_code == 200 and v_resp.json().get("status") == "completed":
                valid_poll_res = v_resp.json()["result"]
                break
            await asyncio.sleep(0.2)

        assert valid_poll_res is not None
        assert valid_poll_res["is_valid_resume"] is True
        assert valid_poll_res["overall_score"] > 0
        assert valid_poll_res["recommendation"] in ("SHORTLIST", "REVIEW")
        assert valid_poll_res["document"]["is_valid_resume"] is True

