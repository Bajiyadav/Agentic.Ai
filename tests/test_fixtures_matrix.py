import json
import pytest
from pathlib import Path
from unittest.mock import patch

from src.services.screening_service import execute_screening_pipeline_core
from src.batch_screener import run_batch_screening

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RESUMES_DIR = FIXTURES_DIR / "resumes"
INVALID_DIR = FIXTURES_DIR / "invalid_documents"
CORRUPTED_DIR = FIXTURES_DIR / "corrupted"
EXPECTED_FILE = FIXTURES_DIR / "expected" / "screening_expectations.json"


@pytest.fixture(scope="module")
def expectations():
    with open(EXPECTED_FILE, "r") as f:
        return json.load(f)


# --- 1. VALID RESUMES ---

def test_fixture_valid_backend_engineer():
    """Alex Mercer: Valid Backend Engineer with Python, FastAPI, Docker, and GitHub profile."""
    pdf_path = RESUMES_DIR / "valid_backend_engineer.pdf"
    assert pdf_path.exists(), f"Missing fixture {pdf_path}"

    res = execute_screening_pipeline_core(
        file_path=str(pdf_path),
        target_role="Senior Backend Engineer",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker"]
    )

    assert res["is_valid_resume"] is True
    assert res["document_type"] == "RESUME"
    assert res["overall_score"] > 0
    assert res["recruiter_recommendation"] in ("STRONG_CANDIDATE", "SHORTLIST", "REVIEW", "REJECT")
    assert res["recruiter_recommendation"] != "INVALID_DOCUMENT"
    assert res["next_action"] in ("SCHEDULE_INTERVIEW", "REVIEW_RECOMMENDED", "DO_NOT_PROCEED")
    assert res["next_action"] != "REQUEST_RESUME"
    assert "Alex Mercer" in res["candidate_name"]
    assert "Python" in res["claims"]["claimed_languages"]
    assert len(res["why_score"]["reasons"]) > 0


def test_fixture_valid_fullstack_engineer():
    """Jordan Taylor: Valid Fullstack Engineer with React, TypeScript, Node.js."""
    pdf_path = RESUMES_DIR / "valid_fullstack_engineer.pdf"
    assert pdf_path.exists()

    res = execute_screening_pipeline_core(
        file_path=str(pdf_path),
        target_role="Fullstack Developer",
        required_skills=["React", "TypeScript", "Node.js"]
    )

    assert res["is_valid_resume"] is True
    assert res["document_type"] == "RESUME"
    assert res["overall_score"] > 0
    assert "Jordan Taylor" in res["candidate_name"]


def test_fixture_valid_resume_no_github():
    """David Vance: Valid resume without GitHub link must evaluate on resume claims alone without fabricating code."""
    pdf_path = RESUMES_DIR / "valid_resume_no_github.pdf"
    assert pdf_path.exists()

    res = execute_screening_pipeline_core(
        file_path=str(pdf_path),
        target_role="Backend Engineer",
        required_skills=["Java", "Spring Boot", "AWS"]
    )

    assert res["is_valid_resume"] is True
    assert res["document_type"] == "RESUME"
    # GitHub evidence must be unavailable, not fabricated
    assert res["evidence"]["profile_found"] is False
    assert res["evidence"]["total_public_repos"] == 0
    assert res["evidence"]["total_stars"] == 0
    assert "David Vance" in res["candidate_name"]


def test_fixture_valid_resume_with_experiment():
    """Elena Rostova: Real resume mentioning A/B 'experiment' projects must NOT be falsely rejected."""
    pdf_path = RESUMES_DIR / "valid_resume_with_experiment.pdf"
    assert pdf_path.exists()

    res = execute_screening_pipeline_core(
        file_path=str(pdf_path),
        target_role="Machine Learning Engineer",
        required_skills=["Python", "PyTorch", "Docker"]
    )

    assert res["is_valid_resume"] is True
    assert res["document_type"] == "RESUME"
    assert "Elena Rostova" in res["candidate_name"]
    assert res["overall_score"] > 0


def test_fixture_valid_low_score_resume_proves_score_not_equal_invalidity():
    """
    CRITICAL SCORE RULE:
    Kevin Miller: Structurally valid resume with weak candidate evidence.
    Must remain is_valid_resume == True, even if overall_score is low / zero!
    Must be classified as REJECT / DO_NOT_PROCEED, NOT INVALID_DOCUMENT / REQUEST_RESUME.
    """
    pdf_path = RESUMES_DIR / "valid_low_score_resume.pdf"
    assert pdf_path.exists()

    res = execute_screening_pipeline_core(
        file_path=str(pdf_path),
        target_role="Principal Distributed Systems Architect",
        required_skills=["Rust", "Kubernetes", "Distributed Consensus", "eBPF"],
        min_experience=10.0
    )

    # Document validity assertion
    assert res["is_valid_resume"] is True
    assert res["document_type"] == "RESUME"
    assert res["candidate"]["name"] == "Kevin Miller"

    # Candidate quality assertion: poor candidate, NOT an invalid document
    assert res["recommendation"] == "REJECT"
    assert res["recruiter_recommendation"] in ("REJECT", "NOT_RECOMMENDED")
    assert res["recruiter_recommendation"] != "INVALID_DOCUMENT"
    assert res["next_action"] == "DO_NOT_PROCEED"
    assert res["next_action"] != "REQUEST_RESUME"


# --- 2. INVALID DOCUMENTS & DOWNSTREAM-CALL SUPPRESSION ---

def test_fixture_academic_lab_manual_downstream_suppression():
    """Academic lab manual must halt at Document Gate and NEVER call GitHub or LLM consensus."""
    pdf_path = INVALID_DIR / "academic_lab_manual.pdf"
    assert pdf_path.exists()

    with patch("src.services.screening_service.audit_github") as mock_github, \
         patch("src.services.screening_service.run_consensus_evaluation") as mock_consensus:

        res = execute_screening_pipeline_core(file_path=str(pdf_path))

        # Downstream expensive calls must NEVER be invoked
        mock_github.assert_not_called()
        mock_consensus.assert_not_called()

        assert res["is_valid_resume"] is False
        assert res["overall_score"] == 0
        assert res["document_type"] == "ACADEMIC_LAB_OR_EXERCISE"
        assert res["recommendation"] == "REJECT"
        assert res["recruiter_recommendation"] == "INVALID_DOCUMENT"
        assert res["next_action"] == "REQUEST_RESUME"
        assert res["draft_reply_data"]["reply_type"] == "resubmission_request"


def test_fixture_coursework_assignment_downstream_suppression():
    """Coursework homework assignment must halt without downstream calls."""
    pdf_path = INVALID_DIR / "coursework_assignment.pdf"
    assert pdf_path.exists()

    with patch("src.services.screening_service.audit_github") as mock_github, \
         patch("src.services.screening_service.run_consensus_evaluation") as mock_consensus:

        res = execute_screening_pipeline_core(file_path=str(pdf_path))

        mock_github.assert_not_called()
        mock_consensus.assert_not_called()

        assert res["is_valid_resume"] is False
        assert res["overall_score"] == 0
        assert res["document_type"] == "ASSIGNMENT_OR_HOMEWORK"
        assert res["recruiter_recommendation"] == "INVALID_DOCUMENT"


def test_fixture_question_paper_downstream_suppression():
    """Question paper must halt with 0 score and request resume action."""
    pdf_path = INVALID_DIR / "question_paper.pdf"
    assert pdf_path.exists()

    with patch("src.services.screening_service.audit_github") as mock_github, \
         patch("src.services.screening_service.run_consensus_evaluation") as mock_consensus:

        res = execute_screening_pipeline_core(file_path=str(pdf_path))

        mock_github.assert_not_called()
        mock_consensus.assert_not_called()

        assert res["is_valid_resume"] is False
        assert res["overall_score"] == 0
        assert res["document_type"] == "QUESTION_PAPER"
        assert res["recruiter_recommendation"] == "INVALID_DOCUMENT"


def test_fixture_unrelated_document_downstream_suppression():
    """Unrelated document (menu) must halt at Document Gate."""
    pdf_path = INVALID_DIR / "unrelated_document.pdf"
    assert pdf_path.exists()

    with patch("src.services.screening_service.audit_github") as mock_github, \
         patch("src.services.screening_service.run_consensus_evaluation") as mock_consensus:

        res = execute_screening_pipeline_core(file_path=str(pdf_path))

        mock_github.assert_not_called()
        mock_consensus.assert_not_called()

        assert res["is_valid_resume"] is False
        assert res["overall_score"] == 0
        assert res["recruiter_recommendation"] == "INVALID_DOCUMENT"


def test_fixture_empty_document_downstream_suppression():
    """Empty or unreadable text (<80 chars) must halt immediately."""
    pdf_path = INVALID_DIR / "empty_document.pdf"
    assert pdf_path.exists()

    with patch("src.services.screening_service.audit_github") as mock_github, \
         patch("src.services.screening_service.run_consensus_evaluation") as mock_consensus:

        res = execute_screening_pipeline_core(file_path=str(pdf_path))

        mock_github.assert_not_called()
        mock_consensus.assert_not_called()

        assert res["is_valid_resume"] is False
        assert res["overall_score"] == 0
        assert res["document_type"] == "EMPTY_OR_CORRUPT"


def test_fixture_corrupt_pdf_file():
    """Corrupt file not starting with %PDF- must trigger early security exit."""
    corrupt_path = CORRUPTED_DIR / "corrupt_pdf.pdf"
    assert corrupt_path.exists()

    with patch("src.services.screening_service.audit_github") as mock_github, \
         patch("src.services.screening_service.run_consensus_evaluation") as mock_consensus:

        res = execute_screening_pipeline_core(file_path=str(corrupt_path))

        mock_github.assert_not_called()
        mock_consensus.assert_not_called()

        assert res["is_valid_resume"] is False
        assert res["overall_score"] == 0
        assert res["document_type"] == "CORRUPT_OR_UNREADABLE_FILE"


# --- 3. SINGLE VS BATCH FIXTURE PARITY ---

@pytest.mark.asyncio
async def test_single_vs_batch_fixture_parity():
    """
    Verifies that single screening and batch screening produce identical decisions
    for the exact same test fixture inputs.
    """
    fixtures_to_test = [
        ("Alex Mercer", RESUMES_DIR / "valid_backend_engineer.pdf"),
        ("David Vance", RESUMES_DIR / "valid_resume_no_github.pdf"),
        ("Kevin Miller", RESUMES_DIR / "valid_low_score_resume.pdf"),
        ("Lab Manual", INVALID_DIR / "academic_lab_manual.pdf"),
        ("Assignment", INVALID_DIR / "coursework_assignment.pdf"),
        ("Question Paper", INVALID_DIR / "question_paper.pdf"),
        ("Corrupt File", CORRUPTED_DIR / "corrupt_pdf.pdf")
    ]

    # 1. Run Single Screenings
    single_decisions = {}
    batch_apps = []

    for name, path in fixtures_to_test:
        with open(path, "rb") as f:
            pdf_bytes = f.read()
        single_res = execute_screening_pipeline_core(file_bytes=pdf_bytes, file_name=path.name)
        single_decisions[name] = {
            "is_valid_resume": single_res["is_valid_resume"],
            "document_type": single_res["document_type"],
            "recommendation": single_res["recommendation"]
        }
        batch_apps.append({
            "name": name,
            "pdf_bytes": pdf_bytes,
            "github_username": None
        })

    # 2. Run Batch Screening
    batch_summary = await run_batch_screening(
        batch_id="fixture-parity-test",
        applications=batch_apps
    )

    # 3. Assert Core Decision Parity
    for name, single in single_decisions.items():
        if single["is_valid_resume"]:
            matching = [c for c in batch_summary.candidates if c.candidate_name == name]
        else:
            matching = [c for c in batch_summary.candidates if c.document_type == single["document_type"]]

        assert len(matching) > 0, f"Candidate {name} ({single['document_type']}) missing from batch results"
        cand = matching[0]

        assert cand.is_valid_resume == single["is_valid_resume"], (
            f"Parity mismatch for '{name}': single.is_valid_resume={single['is_valid_resume']} vs batch={cand.is_valid_resume}"
        )
        assert cand.document_type == single["document_type"], (
            f"Parity mismatch for '{name}': single.document_type={single['document_type']} vs batch={cand.document_type}"
        )
        assert cand.recommendation == single["recommendation"], (
            f"Parity mismatch for '{name}': single.recommendation={single['recommendation']} vs batch={cand.recommendation}"
        )
